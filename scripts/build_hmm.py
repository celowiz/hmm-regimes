"""Regimes do Ibovespa e do S&P 500 com HMM gaussiano (hmmlearn), exportados como JSON estático.

Features: retorno log do período e volatilidade realizada (janela curta), padronizados.
Seleção: várias sementes fixas, fica o maior log-likelihood. Rótulos por volatilidade
(maior = queda/estresse, menor = alta/calmo). Exporta probabilidades FILTRADAS (forward, só usam dados até t)
e SUAVIZADAS (forward-backward, usam o futuro) para comparação didática.
"""
import datetime as dt, json, math, os, sys
import numpy as np, pandas as pd, yfinance as yf
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data")
START = "2000-01-01"
SEEDS = [7, 11, 23, 42, 101]

MARKETS = {"ibov": ("^BVSP", "Ibovespa"), "spx": ("^GSPC", "S&P 500")}

def load(sym):
    s = yf.download(sym, start="1999-06-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return drop_intraday(s)

BRT = dt.timezone(dt.timedelta(hours=-3))

def drop_intraday(s, now=None):
    """Remove o candle de hoje antes das 18:30 BRT (preço ainda intradiário)."""
    now = now or dt.datetime.now(BRT)
    if len(s) and s.index[-1].date() >= now.date() and (now.hour, now.minute) < (18, 30):
        s = s[s.index.date < now.date()]
    return s

def features(px, freq):
    if freq == "w":
        px = px.resample("W-FRI").last().dropna()
        win, ann = 8, 52
    else:
        win, ann = 21, 252
    r = np.log(px).diff()
    vol = r.rolling(win).std() * math.sqrt(ann)
    df = pd.DataFrame({"px": px, "r": r, "vol": vol}).dropna()
    df = df[df.index >= START]
    return df, ann

def forward_filter(model, X):
    """P(estado_t | x_1..x_t): recursão forward normalizada (sem olhar o futuro)."""
    ll = model._compute_log_likelihood(X)
    logA = np.log(model.transmat_ + 1e-300)
    la = np.log(model.startprob_ + 1e-300) + ll[0]
    out = np.empty_like(ll)
    out[0] = la - logsumexp(la)
    for t in range(1, len(X)):
        la = logsumexp(out[t - 1][:, None] + logA, axis=0) + ll[t]
        out[t] = la - logsumexp(la)
    return np.exp(out)

def fit(X, k):
    best = None
    for s in SEEDS:
        m = GaussianHMM(n_components=k, covariance_type="full", n_iter=500, tol=1e-5, random_state=s)
        m.fit(X)
        sc = m.score(X)
        if best is None or sc > best[0]:
            best = (sc, m, s)
    return best

def episodes(lab):
    eps, start = [], 0
    for i in range(1, len(lab) + 1):
        if i == len(lab) or lab[i] != lab[start]:
            eps.append((lab[start], start, i - 1)); start = i
    return eps

def run(px, freq, k):
    df, ann = features(px, freq)
    mu, sd = df[["r", "vol"]].mean(), df[["r", "vol"]].std()
    X = ((df[["r", "vol"]] - mu) / sd).values
    score, m, seed = fit(X, k)
    # rótulos guiados pela volatilidade (mais estável entre sementes e janelas):
    # maior vol = "queda" (estresse), menor vol = "alta" (calmo), intermediária = "lateral".
    # Ordenar por retorno médio é instável: o estado de estresse tem repiques fortes.
    mean_r = m.means_[:, 0] * sd["r"] + mu["r"]
    mean_v = m.means_[:, 1] * sd["vol"] + mu["vol"]
    # ordem final por volatilidade decrescente: estresse -> intermediário -> calmo
    order = np.argsort(-mean_v)
    names = {2: ["queda", "alta"], 3: ["queda", "lateral", "alta"]}[k]
    filt = forward_filter(m, X)[:, order]
    smooth = m.predict_proba(X)[:, order]
    A = m.transmat_[np.ix_(order, order)]
    lab = filt.argmax(1)
    r = df["r"].values
    stats = []
    eps = episodes(lab)
    for j, nm in enumerate(names):
        mask = lab == j
        rr = r[mask]
        dds = []
        for (s_, a, b) in eps:
            if s_ != j: continue
            seg = df["px"].values[max(a - 1, 0):b + 1]
            dds.append(float((seg / np.maximum.accumulate(seg) - 1).min()))
        durs = [b - a + 1 for (s_, a, b) in eps if s_ == j]
        stats.append({
            "name": nm, "pct_time": float(mask.mean()),
            "ret_ann": float(np.expm1(rr.mean() * ann)) if len(rr) else None,
            "vol_ann": float(rr.std() * math.sqrt(ann)) if len(rr) > 1 else None,
            "avg_dd": float(np.mean(dds)) if dds else None, "worst_dd": float(min(dds)) if dds else None,
            "avg_dur": float(np.mean(durs)) if durs else None, "n_episodes": len(durs),
            "exp_dur": float(1 / (1 - A[j, j])) if A[j, j] < 1 else None,
            "model_mean_r_ann": float(mean_r[order][j] * ann), "model_vol": float(mean_v[order][j]),
        })
    # estabilidade de rótulo: % de períodos em que filtrado e suavizado concordam
    agree = float((filt.argmax(1) == smooth.argmax(1)).mean())
    r4 = lambda a: [round(float(v), 4) for v in a]
    return {
        "freq": freq, "k": k, "names": names, "seed": seed, "loglik": float(score),
        "dates": [d.strftime("%Y-%m-%d") for d in df.index], "px": [round(float(v), 1) for v in df["px"]],
        "filt": [r4(row) for row in filt], "smooth": [r4(row) for row in smooth],
        "transmat": [r4(row) for row in A], "stats": stats, "agree": agree,
        "last": {"date": df.index[-1].strftime("%Y-%m-%d"), "px": float(df["px"].iloc[-1]), "probs": r4(filt[-1]),
                 "regime": names[int(filt[-1].argmax())], "since": next((df.index[a].strftime("%Y-%m-%d") for (s_, a, b) in reversed(eps)), None)},
    }

def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {"generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "start": START, "markets": {}}
    for mk, (sym, label) in MARKETS.items():
      px = load(sym)
      meta["markets"][mk] = {"symbol": sym, "label": label, "source": f"Yahoo Finance ({sym})", "last_date": px.index[-1].strftime("%Y-%m-%d"), "models": []}
      for freq in ("d", "w"):
        for k in (2, 3):
            res = run(px, freq, k)
            json.dump(res, open(os.path.join(OUT, f"hmm_{mk}_{freq}{k}.json"), "w"), separators=(",", ":"))
            meta["markets"][mk]["models"].append({"id": f"{freq}{k}", "agree": res["agree"], "seed": res["seed"], "n": len(res["dates"])})
            print(mk, freq, k, "seed", res["seed"], "agree %.3f" % res["agree"], [(s["name"], round(s["pct_time"], 2), round(s["ret_ann"] or 0, 3), round(s["vol_ann"] or 0, 3), round(s["exp_dur"] or 0, 1)) for s in res["stats"]], "now", res["last"]["regime"], res["last"]["probs"])
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
