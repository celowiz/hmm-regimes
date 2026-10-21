import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import summary as S


def fake(k=3, n=80, regime_idx=1):
    names = {2: ["queda", "alta"], 3: ["queda", "lateral", "alta"]}[k]
    p = [0.0] * k; p[regime_idx] = 1.0
    filt = [[1.0] + [0.0] * (k - 1)] * (n - 10) + [p] * 10
    dates = [f"2026-{6 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    return {"names": names, "filt": filt, "dates": dates,
            "stats": [{"name": nm, "vol_ann": .2 + i / 10, "ret_ann": .1, "exp_dur": 30.0 + i, "pct_time": 1 / k} for i, nm in enumerate(names)],
            "last": {"date": dates[-1], "px": 1234.56, "probs": p, "regime": names[regime_idx], "since": dates[-10]}}


def test_market_summary_fields_and_strip():
    m = S.market_summary(fake(), fake(k=2, regime_idx=0), "Ibovespa", "^BVSP")
    assert m["regime"] == "lateral" and m["prob"] == 1.0 and m["label"] == "Ibovespa"
    assert len(m["hist"]["regimes"]) == S.HIST
    assert m["hist"]["regimes"][-10:] == ["lateral"] * 10 and m["hist"]["regimes"][0] == "queda"
    assert m["hist"]["to"] == m["date"] and m["k2"]["regime"] == "queda"
    assert set(m["stats"]) == {"queda", "lateral", "alta"}


def test_build_summary_small_and_deterministic(tmp_path):
    models = {"ibov": {"d3": fake(), "d2": fake(k=2)}, "spx": {"d3": fake(regime_idx=2), "d2": None}}
    a = S.build_summary(models, {"generated_at": "2026-10-20T22:40:00Z", "markets": {"ibov": {"label": "Ibovespa"}}})
    b = S.build_summary(models, {"generated_at": "2026-10-20T22:40:00Z", "markets": {"ibov": {"label": "Ibovespa"}}})
    assert a == b and a["schema"] == 1 and a["as_of"] == models["ibov"]["d3"]["last"]["date"]
    assert a["markets"]["spx"]["regime"] == "alta" and "k2" not in a["markets"]["spx"]
    assert len(json.dumps(a, separators=(",", ":"))) < 20_000
