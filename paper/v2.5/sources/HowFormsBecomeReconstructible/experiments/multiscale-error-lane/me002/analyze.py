"""Reader: registered contrasts, readings, telemetry, generational curves and statement scores.

python -m me002.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR [--blocks LO,HI]

Units are source blocks. An endpoint is paired within case (same acquired state, onset, injury
and draws), averaged over the block's 8 cases, and summarised over block means with a 95% t
interval. ME002 is development: no multiplicity allocation. Positive = better for the first arm.
Readings: BENEFIT (lower bound > 0), HARM (upper bound < 0), NO MEANINGFUL DIFFERENCE (interval
inside +-MARGIN), otherwise UNDECIDED. Compact tables go to OUT_DIR (for git, each file under
256 KB); the full per-endpoint tables go to RUN_ROOT/analysis.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from scipy.stats import t as student  # noqa: E402

from me002 import design as D  # noqa: E402

FROZEN = Path(__file__).resolve().parent / "frozen"
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}
GEN_READ = ("gen8", "mean1_8")


def load(root, panel, regimes, blocks):
    data = {}
    for r in regimes:
        per = [dict(np.load(root / "shards" / panel / r / f"{b}.npz")) for b in blocks]
        keys = set(per[0]) - {"__meta__"}
        data[r] = {k: np.stack([p[k] for p in per]) for k in keys}
    return data


def get(dr, panel, name, ep):
    """(blocks, conditions, cases) for an arm or a packet; packets answer fQ_/fR_ with fP_."""
    if name not in D.ARM[panel]:
        ep = ep.replace("fQ_", "fP_").replace("fR_", "fP_").replace("gQ_", "gP_").replace("gR_", "gP_")
    x = dr.get(f"{name}/{ep}")
    if x is None:
        return None
    nc = len(D.PANELS[panel]["conditions"])
    return np.broadcast_to(x, (x.shape[0], nc, x.shape[2])).astype(float) if x.shape[1] == 1 else x.astype(float)


def reading(lo, hi):
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "UNDECIDED"
    if lo > 0:
        return "BENEFIT"
    if hi < 0:
        return "HARM"
    if lo >= -D.MARGIN and hi <= D.MARGIN:
        return "NO MEANINGFUL DIFFERENCE"
    return "UNDECIDED"


def interval(b):
    """b: (blocks,) block means -> point, lo, hi."""
    nb = len(b)
    point = float(b.mean())
    half = float(student.ppf(0.975, nb - 1) * b.std(ddof=1) / np.sqrt(nb)) if nb > 1 else float("nan")
    return point, point - half, point + half


def summarize_cases(d):
    """d: (blocks, cases) paired differences -> one row."""
    point, lo, hi = interval(d.mean(1))
    b = d.mean(1)
    return {"point": point, "lo": lo, "hi": hi, "blocks_pos": int((b > 0).sum()), "blocks_neg": int((b < 0).sum()),
            "case_rescue": int((d > D.MARGIN).sum()), "case_harm": int((d < -D.MARGIN).sum()), "reading": reading(lo, hi)}


def window_contrasts(panel, data, endpoints):
    rows = []
    conds = [c.name for c in D.PANELS[panel]["conditions"]]
    for p, fam, a, b in D.CONTRASTS:
        if p != panel:
            continue
        for r, dr in data.items():
            for ep in endpoints:
                x, y = get(dr, panel, a, ep), get(dr, panel, b, ep)
                if x is None or y is None:
                    continue
                for ci, c in enumerate(conds):
                    rows.append({"panel": panel, "family": fam.split()[0], "arm": a, "ref": b, "regime": r,
                                 "condition": c, "endpoint": ep, **summarize_cases(x[:, ci] - y[:, ci])})
    return rows


def chain_contrasts(data, endpoints):
    rows = []
    for p, fam, a, b in D.CONTRASTS:
        if p != "F":
            continue
        for r, dr in data.items():
            for ep in endpoints:
                x, y = dr.get(f"{a}/{ep}"), dr.get(f"{b}/{ep}")
                if x is None or y is None:
                    continue
                d = x - y                                   # (blocks, generations + 1, envs, cases)
                for ei, env in enumerate(D.ENVIRONMENTS):
                    for read, dd in (("gen8", d[:, D.GENERATIONS, ei]), ("mean1_8", d[:, 1:, ei].mean(1))):
                        rows.append({"panel": "F", "family": fam.split()[0], "arm": a, "ref": b, "regime": r,
                                     "condition": f"{env}/{read}", "endpoint": ep, **summarize_cases(dd)})
    return rows


def levels(panel, dr, endpoints):
    """Block means per endpoint and arm or packet, as lists in the panel's condition order."""
    out = {}
    names = [a.name for a in D.PANELS[panel]["arms"]] + list(D.PANELS[panel].get("packets", ()))
    for ep in endpoints:
        for nm in names:
            x = get(dr, panel, nm, ep)
            if x is not None:
                out.setdefault(ep, {})[nm] = [rnd(float(v)) for v in x.mean((0, 2))]
    return out


def telemetry(panel, dr):
    out = {}
    conds = [c.name for c in D.PANELS[panel]["conditions"]]
    for arm in D.PANELS[panel]["arms"]:
        if f"{arm.name}/a_bursts" not in dr:
            continue
        b, after = dr[f"{arm.name}/a_bursts"], dr[f"{arm.name}/a_after"]
        row = {}
        for ci, c in enumerate(conds):
            r = {"any_burst": rnd(float((b[:, ci] > 0).mean())), "burst_after_onset": rnd(float((after[:, ci] >= 0).mean())),
                 "win20": rnd(float(dr[f"{arm.name}/a_win20"][:, ci].mean()))}
            a2 = dr[f"{arm.name}/a_after2"][:, ci]
            hit = after[:, ci][after[:, ci] >= 0]
            r["median_after"] = float(np.median(hit)) if hit.size else None
            r["after2_none_frac"] = rnd(float((a2 < 0).mean()))
            if f"{arm.name}/a_latched" in dr:
                r["latched_frac"] = rnd(float(dr[f"{arm.name}/a_latched"][:, ci].mean()))
                r["aborts"] = rnd(float(dr[f"{arm.name}/a_aborts"][:, ci].mean()))
            row[c] = r
        out[arm.name] = row
    return out


def chain_curves(dr):
    out = {}
    for arm in D.PANELS["F"]["arms"]:
        row = {}
        for ep in ("v_qual", "v_sign", "p_sign"):
            x = dr[f"{arm.name}/{ep}"].mean(-1)              # (blocks, generations + 1, envs)
            row[ep] = {env: [rnd(float(v)) for v in x[:, :, ei].mean(0)] for ei, env in enumerate(D.ENVIRONMENTS)}
        if f"{arm.name}/a_bursts" in dr:
            row["bursts_per_life"] = {env: [rnd(float(v)) for v in dr[f"{arm.name}/a_bursts"][:, :, ei].mean((0, -1))]
                                      for ei, env in enumerate(D.ENVIRONMENTS)}
        out[arm.name] = row
    return out


def rnd(x, digits=4):
    if x is None or not np.isfinite(x):
        return None
    return round(float(x), digits)


# ---------------------------------------------------------------- statement scoring
def score_statements(data, pred):
    stmts = {s["id"]: s for s in pred["statements"]}
    theory = pred["theory"]
    out = {}
    block_mean = lambda dr, panel, arm, ep, cond: float(get(dr, panel, arm, ep)[:, cond].mean())
    cidx = lambda panel, name: [c.name for c in D.PANELS[panel]["conditions"]].index(name)
    hold3 = ("hold_site", "hold_region", "hold_sheet")

    def hits(panel, regimes):
        cells = []
        for r in regimes:
            dr, th = data[panel][r], theory[f"{panel}/{r}"]["qsl"]
            for arm in hold3:
                for ci, c in enumerate(D.PANELS[panel]["conditions"]):
                    obs, prd = block_mean(dr, panel, arm, "v_sign", ci), th[arm][c.name][0]
                    cells.append(abs(obs - prd) <= 0.05)
        return float(np.mean(cells)), len(cells)

    if "B" in data:
        h, n = hits("B", stmts["PB8"]["regimes"])
        out["PB8"] = {"verdict": "HOLDS" if h >= 0.5 else "FAILS", "hit_fraction": rnd(h), "cells": n}
        harm = lambda r, band: (block_mean(data["B"][r], "B", "hold_site", "v_sign", 0)
                                - block_mean(data["B"][r], "B", "hold_site", "v_sign", cidx("B", f"reference-{band}-2")))
        mono, agree, series = 0, 0, {}
        for f in ("F0", "F4"):
            for s in (0.3, 0.1):
                for band in ("fine", "regional"):
                    hs = [harm(D.regime(f, s, g), band) for g in (0.25, 1.0, 2.5)]
                    m = hs[1] <= hs[0] + 0.01 and hs[2] <= hs[1] + 0.01
                    diff = hs[0] - hs[2]
                    obs_sign = 0 if abs(diff) <= 0.01 else int(np.sign(diff))
                    key = f"{f}_s{s:g}_{band}"
                    ps = stmts["PB10t"]["predicted"][key]["predicted_sign_g0.25_minus_g2.5"]
                    mono += m
                    agree += obs_sign == ps
                    series[key] = {"observed_harm": [rnd(x) for x in hs], "monotone": bool(m), "observed_sign": obs_sign,
                                   "predicted_sign": ps}
        out["PB10"] = {"verdict": "HOLDS" if mono >= 6 else "FAILS", "monotone_series": mono, "series": series}
        out["PB10t"] = {"verdict": "HOLDS" if agree >= 6 else "FAILS", "agreeing_series": agree}
        value = lambda r: (block_mean(data["B"][r], "B", "hold_site", "v_sign", 0)
                           - block_mean(data["B"][r], "B", "inactive", "v_sign", 0))
        vals = {f"{f}_s{s:g}": [rnd(value(D.regime(f, s, g))) for g in (0.25, 1.0, 2.5)] for f in ("F0", "F4") for s in (0.1, 0.3)}
        ok = all(v[0] < v[1] < v[2] for k, v in vals.items() if k.endswith("s0.1"))
        out["PB12"] = {"verdict": "HOLDS" if ok else "FAILS", "observed_value_g0.25_g1_g2.5": vals,
                       "predicted": stmts["PB12"]["predicted"]}
    if "C" in data:
        hs = {s: hits("C", [D.regime(f, s) for f in ("F0", "F4", "S4", "BL", "IS")])[0] for s in (0.05, 0.1, 0.2, 0.3, 0.4)}
        seq = [hs[s] for s in (0.05, 0.1, 0.2, 0.3, 0.4)]
        ok = hs[0.1] >= 0.5 and hs[0.3] < 0.5 and all(b <= a + 0.05 for a, b in zip(seq, seq[1:]))
        out["PB9"] = {"verdict": "HOLDS" if ok else "FAILS", "hit_fraction_by_sigma": {f"{s:g}": rnd(h) for s, h in hs.items()}}
        fa = {}
        for r in stmts["PC1"]["regimes"]:
            fa[r] = rnd(float((data["C"][r]["arbiter_pooled/a_bursts"][:, 0] > 0).mean()))
        out["PC1"] = {"verdict": "HOLDS" if all(v <= 0.05 for v in fa.values()) else "FAILS", "sham_false_alarm_rate": fa}
    if "D" in data:
        reads = []
        for pair, conds in stmts["PB11"]["contrasts"].items():
            a, b = [x.strip() for x in pair.split("-")]
            for r, dr in data["D"].items():
                for c in conds:
                    for ep in ("v_qual", "fQ_qual"):
                        ci = cidx("D", c)
                        row = summarize_cases(get(dr, "D", a, ep)[:, ci] - get(dr, "D", b, ep)[:, ci])
                        reads.append((pair, r, c, ep, row["reading"], rnd(row["point"])))
        ok = all(x[4] == "NO MEANINGFUL DIFFERENCE" for x in reads)
        out["PB11"] = {"verdict": "HOLDS" if ok else "FAILS", "contrasts": len(reads),
                       "not_equal": [x for x in reads if x[4] != "NO MEANINGFUL DIFFERENCE"][:20]}
        dr, rd = data["D"][D.PRIMARY], {}
        for c in stmts["PD1"]["conditions"]:
            ci = cidx("D", c)
            row = summarize_cases(get(dr, "D", "dual_vote", "fQ_qual")[:, ci] - get(dr, "D", "hold_site", "fQ_qual")[:, ci])
            rd[c] = {k: (rnd(v) if isinstance(v, float) else v) for k, v in row.items()}
        out["PD1"] = {"verdict": "HOLDS" if all(x["reading"] == "BENEFIT" for x in rd.values()) else "FAILS", "contrasts": rd}
    if "A" in data:
        rates, ok = {}, True
        for r in stmts["PA1"]["regimes"]:
            dr = data["A"][r]
            for c in stmts["PA1"]["conditions"]:
                ci = cidx("A", c)
                m001, v2 = float(dr["arbiter_me001/a_win20"][:, ci].mean()), float(dr["arbiter/a_win20"][:, ci].mean())
                rates[f"{r}/{c}"] = {"arbiter_me001": rnd(m001), "arbiter": rnd(v2)}
                ok &= m001 <= 0.5 and v2 >= 0.9
        out["PA1"] = {"verdict": "HOLDS" if ok else "FAILS", "win20_rates": rates}
        vals, ok = {}, True
        for r in stmts["PA2"]["regimes"]:
            dr = data["A"][r]
            ii, i50 = cidx("A", "impose-inf"), cidx("A", "impose-50")
            v = {f"{a}/impose-inf/rg_sign": block_mean(dr, "A", a, "rg_sign", ii) for a in ("arbiter", "arbiter_W300", "arbiter_W100")}
            v.update({f"{a}/impose-50/r_sign": block_mean(dr, "A", a, "r_sign", i50) for a in ("arbiter", "arbiter_W300")})
            v["changepoint/impose-50/rg_sign"] = block_mean(dr, "A", "changepoint", "rg_sign", i50)
            ok &= all(x >= 0.8 for x in v.values())
            vals[r] = {k: rnd(x) for k, x in v.items()}
        out["PA2"] = {"verdict": "HOLDS" if ok else "FAILS", "values": vals}
        dr = data["A"][D.PRIMARY]
        rd = {}
        for c in ("ref-then-body-10", "ref-then-body-300"):
            ci = cidx("A", c)
            rd[c] = summarize_cases(get(dr, "A", "arbiter_abort", "fR_qual")[:, ci] - get(dr, "A", "arbiter", "fR_qual")[:, ci])
        ok = rd["ref-then-body-10"]["reading"] == "BENEFIT" and rd["ref-then-body-300"]["reading"] == "NO MEANINGFUL DIFFERENCE"
        out["PA3"] = {"verdict": "HOLDS" if ok else "FAILS",
                      "contrasts": {c: {k: (rnd(v) if isinstance(v, float) else v) for k, v in row.items()} for c, row in rd.items()}}
        fr, ok = {}, True
        for r in stmts["PA4"]["regimes"]:
            dr = data["A"][r]
            ci = cidx("A", "body-then-ref-10")
            for a, W in (("arbiter", 1000), ("arbiter_W300", 300)):
                a2 = dr[f"{a}/a_after2"][:, ci]
                frac = float(((a2 < 0) | (a2 >= W - 50)).mean())
                fr[f"{r}/{a}"] = rnd(frac)
                ok &= frac >= 0.8
        out["PA4"] = {"verdict": "HOLDS" if ok else "FAILS", "no_early_burst_fraction": fr}
    if "E" in data:
        dr = data["E"][D.PRIMARY]
        row = summarize_cases(get(dr, "E", "sign_sheet_site_eq", "v_qual")[:, 0] - get(dr, "E", "hold_site", "v_qual")[:, 0])
        out["PE1"] = {"verdict": "HOLDS" if row["reading"] == "BENEFIT" else "FAILS",
                      "contrast": {k: (rnd(v) if isinstance(v, float) else v) for k, v in row.items()}}
    if "F" in data:
        G, env = D.GENERATIONS, D.ENVIRONMENTS.index
        dr = data["F"][D.PRIMARY]
        x = dr["hold_Q/v_qual"][:, :, env("none")].mean(-1)
        p, lo, hi = interval(x[:, G] - x[:, 1])
        out["PF1"] = {"verdict": "HOLDS" if p < -0.05 and hi < 0 else "FAILS",
                      "gen1": rnd(float(x[:, 1].mean())), "gen8": rnd(float(x[:, G].mean())), "diff": [rnd(p), rnd(lo), rnd(hi)]}
        a = dr["arbiter_R/v_qual"][:, :, env("reference")].mean(-1)
        h = dr["hold_R/v_qual"][:, :, env("reference")].mean(-1)
        p, lo, hi = interval((a[:, G] - a[:, 1]) - (h[:, G] - h[:, 1]))
        out["PF2"] = {"verdict": "HOLDS" if p >= 0.05 and lo > 0 else "FAILS", "d": [rnd(p), rnd(lo), rnd(hi)]}
        reads = {}
        for r in stmts["PF3"]["regimes"]["equal"] + stmts["PF3"]["regimes"]["worse"]:
            d = data["F"][r]["germline_region/v_qual"] - data["F"][r]["germline_site/v_qual"]
            reads[r] = summarize_cases(d[:, G, env("none")])["reading"]
        ok = all(reads[r] == "NO MEANINGFUL DIFFERENCE" for r in stmts["PF3"]["regimes"]["equal"]) and \
            all(reads[r] == "HARM" for r in stmts["PF3"]["regimes"]["worse"])
        out["PF3"] = {"verdict": "HOLDS" if ok else "FAILS", "readings": reads}
    return out


def write_csv(path, rows):
    cols = ["panel", "family", "arm", "ref", "regime", "condition", "endpoint", "point", "lo", "hi",
            "blocks_pos", "blocks_neg", "case_rescue", "case_harm", "reading"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] if c not in ("point", "lo", "hi") else f"{r[c]:.4f}" for c in cols[:-1]] + [SHORT[r["reading"]]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--blocks", default=None)
    ap.add_argument("--panels", default="all")
    a = ap.parse_args()
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    panels = list(D.PANELS) if a.panels == "all" else a.panels.split(",")
    pred = json.loads((FROZEN / "predictions.json").read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    full = root / "analysis"
    full.mkdir(exist_ok=True)
    data = {p: load(root, p, D.PANELS[p]["regimes"], blocks) for p in panels}
    summary = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "panels": {}}
    for p in panels:
        prim, sec = D.PRIMARY_ENDPOINTS[p], D.SECONDARY_ENDPOINTS[p]
        if p == "F":
            rows = chain_contrasts(data[p], prim)
            write_csv(a.out / "contrasts_F.csv", rows)
            write_csv(full / "contrasts_F_all.csv", chain_contrasts(data[p], prim + sec))
            summary["panels"][p] = {"curves": {r: chain_curves(dr) for r, dr in data[p].items()}}
            continue
        for ep in prim:
            write_csv(a.out / f"contrasts_{p}_{ep}.csv", window_contrasts(p, data[p], (ep,)))
        write_csv(full / f"contrasts_{p}_all.csv", window_contrasts(p, data[p], prim + sec))
        keep = D.PANELS[p]["regimes"] if p in ("A", "D", "E") else [r for r in D.PANELS[p]["regimes"]
                                                                   if r == D.PRIMARY or D.parse(r)[1] in (0.1, 0.3)]
        summary["panels"][p] = {"conditions": [c.name for c in D.PANELS[p]["conditions"]],
                                "levels": {r: levels(p, data[p][r], prim) for r in keep},
                                "telemetry": {r: telemetry(p, data[p][r]) for r in keep}}
        if p == "C":
            summary["panels"][p]["phase"] = phase_table(data[p])
    summary["statements"] = score_statements(data, pred)
    (a.out / "predictions_scored.json").write_text(json.dumps(summary["statements"], indent=1) + "\n")
    (full / "summary_full.json").write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    (a.out / "summary.json").write_text(json.dumps(trim(summary), separators=(",", ":")) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in summary["statements"].items()}, indent=1))


TEL_SHOW = ("sham", "reference-regional-2", "reference-collective-2", "body-collective-2", "both-collective-2",
            "ref-then-body-10", "ref-then-body-300", "body-then-ref-10", "body-then-ref-300", "impose-50", "impose-300",
            "impose-inf")


def trim(summary):
    """The git copy of the summary: telemetry for the listed conditions, in every regime of panel A
    and the primary regime elsewhere; the full summary stays in RUN_ROOT/analysis."""
    out = json.loads(json.dumps(summary))
    for p, v in out["panels"].items():
        if "telemetry" in v:
            v["telemetry"] = {r: {arm: {c: x for c, x in rows.items() if c in TEL_SHOW} for arm, rows in t.items()}
                              for r, t in v["telemetry"].items() if p == "A" or r == D.PRIMARY}
    return out


def phase_table(data):
    """Panel C: block means of key contrasts across sigma x family (the phase picture)."""
    rows = {}
    picks = (("hold_site", "inactive", "sham", "v_qual"), ("hold_site", "inactive", "sham", "fQ_qual"),
             ("arbiter", "hold_site", "reference-collective-2", "fQ_qual"),
             ("arbiter", "hold_site", "reference-regional-2", "fQ_qual"),
             ("hold_sheet", "hold_site", "reference-regional-2", "v_qual"),
             ("arbiter_pooled", "arbiter", "sham", "fQ_qual"))
    cond = [c.name for c in D.COND_C]
    for a, b, c, ep in picks:
        key = f"{a}-{b}|{c}|{ep}"
        rows[key] = {}
        for r, dr in data.items():
            row = summarize_cases(get(dr, "C", a, ep)[:, cond.index(c)] - get(dr, "C", b, ep)[:, cond.index(c)])
            rows[key][r] = [rnd(row["point"]), SHORT[row["reading"]]]
    return rows


if __name__ == "__main__":
    main()
