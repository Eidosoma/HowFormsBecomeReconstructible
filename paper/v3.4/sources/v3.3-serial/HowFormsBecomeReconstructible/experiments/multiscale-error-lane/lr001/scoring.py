"""Scores LR001's registered statements (lr001/predict.py) from the reader's levels (block means)."""
from __future__ import annotations


def score(levels):
    lv = lambda p, u, b, key: levels[p][u][b][key]
    r4 = lambda x: None if x is None else round(float(x), 4)
    verdict = lambda ok: "HOLDS" if ok else "FAILS"
    out = {}

    v = {f"{u}/s{s:g}": lv("A", u, f"s{s:g}", "bond_accuracy@20") for u in ("F0", "IS") for s in (0.1, 0.3, 0.6)}
    out["L1"] = {"verdict": verdict(all(x >= 0.99 for x in v.values())), "bond_accuracy@20": {k: r4(x) for k, x in v.items()}}

    v = {u: {"bond_err@4000": lv("E", u, "0.0003/none", "bond_err@4000"), "sign@4000": lv("E", u, "0.0003/none", "sign@4000")}
         for u in ("F0", "BL", "IS")}
    ok = all(x["bond_err@4000"] >= 0.40 and x["sign@4000"] <= 0.65 for x in v.values())
    out["L2"] = {"verdict": verdict(ok), "none_at_3e-4": {u: {k: r4(y) for k, y in x.items()} for u, x in v.items()}}

    v, ok = {}, True
    for u in ("F0", "BL", "IS"):
        both = (lv("E", u, "0.001/both", "bond_err@4000"), lv("E", u, "0.001/both", "sign@4000"))
        hebb, par = lv("E", u, "0.001/hebb", "bond_err@4000"), lv("E", u, "0.001/parity", "bond_err@4000")
        v[u] = {"both_bond_err": r4(both[0]), "both_sign": r4(both[1]), "hebb_bond_err": r4(hebb), "parity_bond_err": r4(par)}
        ok &= both[0] <= 0.06 and both[1] >= 0.95 and hebb >= 0.20 and par >= 0.08
    out["L3"] = {"verdict": verdict(ok), "at_1e-3_t4000": v}

    v = {f"{u}/{rep}": lv("E", u, f"0.003/{rep}", "sign@8000") for u in ("F0", "BL", "IS") for rep in ("none", "hebb", "parity", "both")}
    out["L4"] = {"verdict": verdict(all(x <= 0.75 for x in v.values())), "sign@8000_at_3e-3": {k: r4(x) for k, x in v.items()}}

    g = {c: (lv("C", "IS", f"{c}/flip8", "kept@4000"), lv("C", "IS", f"{c}/flip8", "kept_min@4000")) for c in ("gauge", "hybrid", "plain")}
    ok = all(g[c][0] >= 0.99 and g[c][1] >= 0.98 for c in ("gauge", "hybrid")) and g["plain"][1] <= 0.98
    worst = {}
    for u in ("F0", "BL", "S4", "IS"):
        for s in (2, 4, 6, 8):
            pl = lv("C", u, f"plain/flip{s}", "kept@4000")
            for c in ("gauge", "hybrid"):
                d = lv("C", u, f"{c}/flip{s}", "kept@4000") - pl
                worst[f"{u}/{c}/flip{s}"] = d
                ok &= d >= -0.005
    out["L5"] = {"verdict": verdict(ok), "IS_flip8": {c: {"kept@4000": r4(x[0]), "kept_min@4000": r4(x[1])} for c, x in g.items()},
                 "worst_gauge_or_hybrid_minus_plain_on_flips": r4(min(worst.values()))}

    v, ok = {}, True
    for u in ("F0", "BL", "S4", "IS"):
        pl, hy, ga = (lv("C", u, f"{c}/kill8", "kept@4000") for c in ("plain", "hybrid", "gauge"))
        v[u] = {"plain": r4(pl), "hybrid": r4(hy), "gauge": r4(ga)}
        ok &= hy >= pl - 0.02 and ga <= pl - 0.10
    out["L6"] = {"verdict": verdict(ok), "kill8_kept@4000": v}

    v, ok = {}, True
    for u in ("F0", "BL", "S4", "IS"):
        pl, hy, tr = (lv("C", u, f"{c}/relink8", "kept@4000") for c in ("plain", "hybrid", "hybrid+trust"))
        v[u] = {"plain": r4(pl), "hybrid": r4(hy), "hybrid+trust": r4(tr)}
        ok &= tr >= pl - 0.02
        if u in ("BL", "IS"):
            ok &= hy <= pl - 0.03
    out["L7"] = {"verdict": verdict(ok), "relink8_kept@4000": v}

    v = {f"{u}/{c}/{w}": lv("C", u, f"{c}/{w}", "kept_min@4000") for u in ("BL", "IS")
         for c in ("none", "plain", "gauge", "hybrid", "hybrid+trust") for w in ("kill8", "relink8")}
    out["L8"] = {"verdict": verdict(all(x is not None and x <= 0.92 for x in v.values())),
                 "kept_min@4000": {k: r4(x) for k, x in v.items()}}

    v, ok = {}, True
    for u in ("BL", "IS"):
        for rate in ("0.001", "0.003"):
            inh = (lv("T", u, f"{rate}/inherit", "sign@8000"), lv("T", u, f"{rate}/inherit", "minority@8000"))
            rel, dfl = lv("T", u, f"{rate}/relearn", "minority@8000"), lv("T", u, f"{rate}/default", "minority@8000")
            v[f"{u}/{rate}"] = {"inherit_sign": r4(inh[0]), "inherit_minority": r4(inh[1]), "relearn_minority": r4(rel),
                                "default_minority": r4(dfl)}
            ok &= inh[0] >= 0.99 and inh[1] >= 0.98 and rel <= 0.85 and dfl <= 0.85
    out["L9"] = {"verdict": verdict(ok), "t8000": v}

    v, ok = {}, True
    for u in ("F0", "IS"):
        x = {b: lv("L", u, b, "record_kept@2000") for b in ("none", "record", "body", "body_slow")}
        v[u] = {b: r4(y) for b, y in x.items()}
        ok &= x["body"] <= 0.85 and x["record"] >= 0.99 and x["none"] >= 0.99 and x["body_slow"] > x["body"]
    out["L10"] = {"verdict": verdict(ok), "record_kept@2000": v}
    return out
