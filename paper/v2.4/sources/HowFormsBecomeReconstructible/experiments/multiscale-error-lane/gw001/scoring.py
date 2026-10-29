"""Scores GW001's registered statements (gw001/predict.py) from the reader's levels. Block means; t95 medians."""
from __future__ import annotations

import numpy as np

from gw001 import design as D


def score(data, summary):
    R = summary["panels"]["R"]["levels"]
    B = summary["panels"]["B"]["levels"]
    k = lambda u, a, c, key: R[u][a][c][key]
    rnd = lambda d: {kk: (round(v, 4) if np.isfinite(v) else "inf") for kk, v in d.items()}
    verdict = lambda ok: "HOLDS" if ok else "FAILS"
    out = {}

    closed = [("F0_32", c) for c in ("f4-mid", "f6-mid", "f8-mid", "f10-mid")] + [("F0_64", c) for c in ("f4-mid", "f8-mid", "f12-mid")]
    touch = [(u, "f8-d0") for u in ("F0_16", "F0_32", "F0_64")]
    v1 = {f"{u}/{c}": k(u, "self", c, "kept@8000") for u, c in closed}
    v2 = {f"{u}/{c}": k(u, "self", c, "kept@8000") for u, c in touch}
    out["G1"] = {"verdict": verdict(all(x >= 0.95 for x in v1.values()) and all(x <= 0.7 for x in v2.values())),
                 "closed_kept@8000": rnd(v1), "touching_kept@8000": rnd(v2)}

    vals, ok = {}, True
    for u in ("F0_32", "F0_64"):
        for c in (x.name for x in D.GEOMETRIES[u]):
            if c.startswith("r") and c.endswith(("-mid", "-d2")):
                kept, t = k(u, "self", c, "kept@2000"), k(u, "self", c, "t95_median")
                vals[f"{u}/{c}"] = [round(kept, 4), t]
                ok &= kept >= 0.95 and t <= 1000
    out["G2"] = {"verdict": verdict(ok), "reset_kept@2000_t95": vals}

    def slope(u, sizes):
        t = [k(u, "self", f"f{s}-mid", "t95_median") for s in sizes]
        if not all(np.isfinite(t)):
            return float("nan"), t
        return float(np.polyfit(np.log(sizes), np.log(t), 1)[0]), t
    s32, t32 = slope("F0_32", (4, 6, 8, 10))
    s64, t64 = slope("F0_64", (4, 8, 12))
    big = k("F0_64", "self", "f16-mid", "kept@8000")
    out["G3"] = {"verdict": verdict(np.isfinite(s32) and np.isfinite(s64) and s32 >= 2.0 and s64 >= 2.0 and big <= 0.7),
                 "slope_side32": round(s32, 3) if np.isfinite(s32) else "censored", "t95_side32": t32,
                 "slope_side64": round(s64, 3) if np.isfinite(s64) else "censored", "t95_side64": t64,
                 "f16-mid_side64_kept@8000": round(big, 4)}

    gain = lambda u, c, t: k(u, "multi", c, f"kept@{t}") - k(u, "self", c, f"kept@{t}")
    d0 = np.mean([gain("F0_32", c, 2000) for c in ("f4-d0", "f8-d0")])
    mid = np.mean([gain("F0_32", c, 2000) for c in ("f4-mid", "f8-mid")])
    big = {f"{u}@{t}": gain(u, "f12-mid", t) for u in ("F0_32", "F0_64") for t in (2000, 8000)}
    ok = d0 - mid >= 0.3 and all(big[f"{u}@2000"] >= 0.5 and big[f"{u}@8000"] <= 0.1 for u in ("F0_32", "F0_64"))
    out["G4"] = {"verdict": verdict(ok), "code_gain_d0": round(float(d0), 4), "code_gain_mid": round(float(mid), 4),
                 "code_gain_f12-mid": rnd(big)}

    t_kr2, t_self = k("F0_64", "self_kr2", "f12-mid", "t95_median"), k("F0_64", "self", "f12-mid", "t95_median")
    pin, heal = k("F0_32", "self_kr2", "f12-mid", "kept@8000"), k("F0_32", "self", "f12-mid", "kept@8000")
    ok = np.isfinite(t_kr2) and t_kr2 <= 0.5 * t_self and pin <= 0.1 and heal >= 0.9
    out["G5"] = {"verdict": verdict(ok), "t95_side64_kr2": t_kr2, "t95_side64_self": t_self,
                 "side32_kept@8000_kr2": round(pin, 4), "side32_kept@8000_self": round(heal, 4)}

    shared = [c.name for c in D.GEOMETRIES["S8_32"] if c.wound == "flip" and c.name in {x.name for x in D.GEOMETRIES["F0_16"]}]
    diffs = {c: k("S8_32", "self", c, "kept@2000") - k("F0_16", "self", c, "kept@2000") for c in shared}
    out["G6"] = {"verdict": verdict(all(abs(x) <= 0.08 for x in diffs.values())), "S8_32_minus_F0_16_kept@2000": rnd(diffs)}

    sh = lambda u, key: R[u]["self"]["sham"][key]
    a, b, c2 = sh("BL_16", "rsign@2000"), sh("BL_32", "rsign@2000"), sh("BLx2_32", "rsign@2000")
    bsd, psd = sh("BL_16", "rsign@2000_block_sd"), sh("BL_16", "rsign@2000_parent_sd")
    ok = abs(b - a) <= 0.03 and c2 - b >= 0.08 and bsd >= 2.5 * psd
    out["G7"] = {"verdict": verdict(ok), "BL_16": a, "BL_32": b, "BLx2_32": c2, "block_sd": bsd, "parent_sd": psd}

    low, ok = {}, True
    for u in ("F0_16", "F0_32", "F0_64", "S8_32"):
        for c in D.GEOMETRIES[u]:
            if c.wound in ("flip", "reset"):
                x = k(u, "rel+code", c.name, "kept@8000")
                ok &= x >= 0.98
                if x < 0.99:
                    low[f"{u}/{c.name}"] = round(x, 4)
    detail = {u: R[u]["rel"]["sham"]["rsign@8000"] for u in ("BL_16", "BL_32", "BLx2_32", "BLx4_64")}
    ok &= all(x >= 0.98 for x in detail.values())
    out["G8"] = {"verdict": verdict(ok), "rel+code_below_0.99": low, "rel_detail@8000": detail}

    bb = lambda unit, arm, ep, c: B[unit][arm][ep][c]
    dv16 = bb("F0_16_s0.1_c", "protected", "les_v", "f8-d0") - bb("F0_16_s0.1_o", "protected", "les_v", "f8-d0")
    dv32 = bb("F0_32_s0.1_c", "protected", "les_v", "f8-d0") - bb("F0_32_s0.1_o", "protected", "les_v", "f8-d0")
    do16 = bb("F0_16_s0.1_c", "protected", "v_out", "f8-d0") - bb("F0_16_s0.1_o", "protected", "v_out", "f8-d0")
    do32 = bb("F0_32_s0.1_c", "protected", "v_out", "f8-d0") - bb("F0_32_s0.1_o", "protected", "v_out", "f8-d0")
    ok = dv16 <= -0.3 and dv32 >= -0.15 and do16 <= -0.05 and do32 >= -0.04
    out["G9"] = {"verdict": verdict(ok), "les_v_conserved_minus_open": {"side16": round(dv16, 4), "side32": round(dv32, 4)},
                 "v_out_conserved_minus_open": {"side16": round(do16, 4), "side32": round(do32, 4)}}

    g = {b_: bb(f"F0_32_s0.1_{b_}", "static", "les_v", "r8-d0") - bb(f"F0_32_s0.1_{b_}", "static", "les_v", "f8-d0") for b_ in ("c", "o")}
    out["G10"] = {"verdict": verdict(all(x >= 0.4 for x in g.values())), "static_les_v_reset_minus_flip": rnd(g)}
    return out
