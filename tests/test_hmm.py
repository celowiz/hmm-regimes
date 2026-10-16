import datetime as dt, os, sys
import numpy as np, pandas as pd, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_hmm as B
from hmmlearn.hmm import GaussianHMM


def synth_px(n=1500, seed=0):
    """Preço sintético alternando blocos calmos e turbulentos."""
    rng = np.random.default_rng(seed)
    vols = np.where((np.arange(n) // 150) % 3 == 2, 0.035, 0.008)
    r = rng.normal(0.0003, vols)
    idx = pd.bdate_range("2000-01-03", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx)


@pytest.fixture(scope="module")
def model():
    rng = np.random.default_rng(1)
    X = np.r_[rng.normal(0, 1, (300, 2)), rng.normal(3, 2, (200, 2)), rng.normal(0, 1, (300, 2))]
    m = GaussianHMM(n_components=2, covariance_type="full", n_iter=200, random_state=7).fit(X)
    return m, X


def test_filtered_rows_are_probabilities(model):
    m, X = model
    f = B.forward_filter(m, X)
    assert f.shape == (len(X), 2)
    assert np.all(f >= 0) and np.allclose(f.sum(1), 1)


def test_filtered_has_no_lookahead(model):
    """Probabilidade filtrada em t não muda quando chegam dados depois de t."""
    m, X = model
    full = B.forward_filter(m, X)
    for t in (10, 299, 450, 799):
        assert np.allclose(B.forward_filter(m, X[: t + 1]), full[: t + 1])


def test_filtered_last_equals_smoothed_last(model):
    """No último ponto, filtrada e suavizada coincidem (não há futuro)."""
    m, X = model
    assert np.allclose(B.forward_filter(m, X)[-1], m.predict_proba(X)[-1], atol=1e-6)


def test_filtered_matches_bruteforce(model):
    """Recursão em log-espaço = recursão direta em probabilidades."""
    m, X = model
    lik = np.exp(m._compute_log_likelihood(X[:50]))
    a = m.startprob_ * lik[0]; a /= a.sum(); out = [a]
    for t in range(1, 50):
        a = (a @ m.transmat_) * lik[t]; a /= a.sum(); out.append(a)
    assert np.allclose(B.forward_filter(m, X[:50]), np.array(out), atol=1e-8)


def test_episodes():
    assert B.episodes([0, 0, 1, 1, 1, 0]) == [(0, 0, 1), (1, 2, 4), (0, 5, 5)]


def test_drop_intraday():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-10-15", "2026-10-16"]))
    assert len(B.drop_intraday(s, dt.datetime(2026, 10, 16, 15, 0, tzinfo=B.BRT))) == 1
    assert len(B.drop_intraday(s, dt.datetime(2026, 10, 16, 19, 0, tzinfo=B.BRT))) == 2
    assert len(B.drop_intraday(s, dt.datetime(2026, 10, 17, 10, 0, tzinfo=B.BRT))) == 2


@pytest.mark.parametrize("freq,k", [("d", 2), ("d", 3), ("w", 2)])
def test_run_output(freq, k):
    res = B.run(synth_px(), freq, k)
    n = len(res["dates"])
    assert len(res["px"]) == len(res["filt"]) == len(res["smooth"]) == n
    assert np.allclose(np.array(res["filt"]).sum(1), 1, atol=1e-3)
    assert np.allclose(np.array(res["transmat"]).sum(1), 1, atol=1e-3)
    assert res["names"][0] == "queda" and res["names"][-1] == "alta"
    vols = [s["vol_ann"] for s in res["stats"]]
    assert vols[0] == max(vols)  # estresse = maior volatilidade
    assert abs(sum(s["pct_time"] for s in res["stats"]) - 1) < 1e-6
    assert res["last"]["regime"] in res["names"] and 0.9 < res["agree"] <= 1
