"""Gera data/summary.json: um resumo pequeno (~2 KB) do estado atual dos modelos diários,
lido pela página Mercado Hoje do portfólio (celowiz.github.io/mercado-hoje/).

Só reorganiza o que scripts/build_hmm.py já gravou em <out>/hmm_*_d3.json e hmm_*_d2.json;
nenhum cálculo novo. Determinístico: a mesma entrada gera o mesmo arquivo.
Uso: python scripts/summary.py _site/data
"""
import json, os, sys

SCHEMA = 1
HIST = 60  # pregões da faixa de regimes
MARKETS = ("ibov", "spx")


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def market_summary(d3, d2=None, label=None, symbol=None):
    names, last = d3["names"], d3["last"]
    filt = d3["filt"][-HIST:]
    out = {
        "label": label, "symbol": symbol, "model": "d3",
        "date": last["date"], "px": _r(last["px"], 2),
        "regime": last["regime"], "prob": _r(max(last["probs"])), "probs": [_r(p) for p in last["probs"]],
        "since": last["since"], "names": names,
        "stats": {s["name"]: {"vol_ann": _r(s["vol_ann"]), "ret_ann": _r(s["ret_ann"]), "exp_dur": _r(s["exp_dur"], 1),
                              "pct_time": _r(s["pct_time"])} for s in d3["stats"]},
        "hist": {"from": d3["dates"][-len(filt)], "to": d3["dates"][-1],
                 "regimes": [names[max(range(len(p)), key=lambda i: p[i])] for p in filt]},
    }
    if d2:
        l2 = d2["last"]
        out["k2"] = {"regime": l2["regime"], "since": l2["since"], "date": l2["date"], "prob": _r(max(l2["probs"]))}
    return out


def build_summary(models, meta):
    """models: {mk: {"d3": dict, "d2": dict|None}}; meta: conteúdo de meta.json."""
    mk_meta = meta.get("markets", {})
    markets = {mk: market_summary(m["d3"], m.get("d2"), mk_meta.get(mk, {}).get("label"), mk_meta.get(mk, {}).get("symbol"))
               for mk, m in models.items() if m.get("d3")}
    return {"schema": SCHEMA, "project": "hmm-regimes", "url": "https://celowiz.github.io/hmm-regimes/",
            "as_of": max((m["date"] for m in markets.values()), default=None),
            "generated_at": meta.get("generated_at"), "markets": markets}


def main(out):
    load = lambda f: json.load(open(os.path.join(out, f))) if os.path.exists(os.path.join(out, f)) else None
    models = {mk: {"d3": load(f"hmm_{mk}_d3.json"), "d2": load(f"hmm_{mk}_d2.json")} for mk in MARKETS}
    s = build_summary(models, load("meta.json") or {})
    if not s["markets"]:
        sys.exit("summary: nenhum modelo d3 encontrado em " + out)
    path = os.path.join(out, "summary.json")
    json.dump(s, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"summary.json: {os.path.getsize(path)} bytes, " + ", ".join(f"{k}={v['regime']} desde {v['since']}" for k, v in s["markets"].items()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data"))
