"""Reader: registered contrasts, readings, detection, arbiter telemetry and prediction scores.

python -m me001.analyze --root RUN_ROOT --stage {preflight,development} --out OUT_DIR

Units are source blocks. An endpoint is first paired within case (same acquired state,
injury and draws), then averaged over the block's 8 cases (recipients are already averaged
within case); intervals are 95% t intervals over the block means. ME001 is development, so
no multiplicity allocation is made. Positive = better for the first arm. Readings: BENEFIT
(lower bound > 0), HARM (upper bound < 0), NO MEANINGFUL DIFFERENCE (interval inside
+-MARGIN), otherwise UNDECIDED. Compact tables go to OUT_DIR (for git); full per-block and
per-case tables go to RUN_ROOT/analysis.
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

from me001 import design as D  # noqa: E402
from me001.policies import FEATURES  # noqa: E402
from me001.worker import edges  # noqa: E402
from mse.assay import enrol, templates  # noqa: E402

FROZEN = Path(__file__).resolve().parent / "frozen"
NC = len(D.CONDITIONS)
HOLD = ("inactive", "body_site", "body_region", "body_sheet")
CNAME = [D.condition_name(i) for i in range(NC)]
SHAM = 0


def load(root, regimes, blocks):
    data = {}
    for r in regimes:
        per = [dict(np.load(root / "shards" / r / f"{b}.npz")) for b in blocks]
        keys = set(per[0]) - {"__meta__"}
        data[r] = {k: np.stack([p[k] for p in per]) for k in keys}
        data[r]["__meta__"] = [json.loads(str(p["__meta__"])) for p in per]
    return data


def get(dr, name, ep):
    """(blocks, 28 conditions, 8 cases), NaN where the arm was not run under a condition."""
    x = dr.get(f"{name}/{ep}")
    if x is None:
        return None
    if name in D.ARM:
        conds = D.arm_conditions(D.ARM[name])
    elif D.PACKET_CONDITIONS[name] == "full":
        conds = D.FULL
    else:
        return np.broadcast_to(x, (x.shape[0], NC, x.shape[2])).copy()
    out = np.full((x.shape[0], NC, x.shape[2]), np.nan)
    out[:, list(conds)] = x
    return out


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


def summarize(diff):
    """diff (blocks, conditions, cases) -> per-condition rows; None where nothing was run."""
    nb = diff.shape[0]
    tq = student.ppf(0.975, nb - 1)
    blocks = diff.mean(2)
    rows = []
    for c in range(diff.shape[1]):
        b = blocks[:, c]
        if not np.isfinite(b).any():
            rows.append(None)
            continue
        point = float(b.mean())
        half = float(tq * b.std(ddof=1) / np.sqrt(nb)) if nb > 1 else float("nan")
        lo, hi = point - half, point + half
        d = diff[:, c]
        rows.append({"point": point, "lo": lo, "hi": hi, "blocks_pos": int((b > 0).sum()),
                     "blocks_neg": int((b < 0).sum()), "case_rescue": int((d > D.MARGIN).sum()),
                     "case_harm": int((d < -D.MARGIN).sum()), "reading": reading(lo, hi)})
    return rows


def contrast(dr, a, b, ep):
    x, y = get(dr, a, ep), get(dr, b, ep)
    if x is None or y is None:
        return None
    return summarize(x - y)


def auc(pos, neg):
    pos, neg = np.ravel(pos)[:, None], np.ravel(neg)[None, :]
    return float((pos > neg).mean() + 0.5 * (pos == neg).mean())


def early(dr, arm, feature):
    return np.mean([get(dr, arm, f"tr_{feature}_{t}") for t in (1, 2, 3)], axis=0)


def detection(dr):
    out = {}
    for arm in (a.name for a in D.ARMS if a.traced):
        feats = {f: early(dr, arm, f) for f in FEATURES}
        out[arm] = {f: {CNAME[c]: auc(x[:, c], x[:, SHAM]) for c in D.FULL if c != SHAM} for f, x in feats.items()}
    loss = {}
    fq = get(dr, "body_site", "f_qual")
    for loc in D.LOCATIONS:
        cs = [i for i, c in enumerate(D.CONDITIONS) if c[0] == loc]
        consequential = np.concatenate([(fq[:, c] - fq[:, SHAM] < -D.MARGIN).ravel() for c in cs])
        row = {"consequential_cases": int(consequential.sum()), "damaged_cases": int(consequential.size)}
        for f in FEATURES:
            x = early(dr, "inactive", f)
            vals = np.concatenate([x[:, c].ravel() for c in cs])
            row[f] = auc(vals[consequential], vals[~consequential]) if 0 < consequential.sum() < consequential.size else None
        loss[loc] = row
    out["information_loss_inactive_sensor"] = loss
    return out


def telemetry(dr):
    out = {}
    fq_hold, fq_or = get(dr, "body_site", "f_qual"), get(dr, "oracle_location", "f_qual")
    for arm in ("arbiter_region", "changepoint_region", "oracle_location"):
        bursts, first = get(dr, arm, "a_bursts"), get(dr, arm, "a_first")
        rows = {}
        for c in D.FULL:
            ref_only = D.CONDITIONS[c][0] == "reference"
            decided = (first[:, c] >= 1) & (first[:, c] <= D.BURST_UPDATES)
            row = {"cases_bursting": float((bursts[:, c] > 0).mean()), "mean_bursts": float(bursts[:, c].mean()),
                   "first_decision_agrees_with_oracle": float((decided == ref_only).mean())}
            f = first[:, c][first[:, c] > 0]
            row["median_first_burst"] = float(np.median(f)) if f.size else None
            helps = fq_or[:, c] - fq_hold[:, c] > D.MARGIN
            row["oracle_helps_cases"] = int(helps.sum())
            row["missed_when_oracle_helps"] = int((helps & (bursts[:, c] == 0)).sum())
            rows[CNAME[c]] = row
        out[arm] = rows
    return out


def boundary_fraction(dr, regime):
    family = D.REGIMES[regime][0]
    cases = enrol([D.IDENTITIES["development"][0]], D.MESSAGES, D.PARENTS, "development")
    ne = edges(templates(cases, D.AMPLITUDE, D.FAMILIES[family])).sum((-2, -1))
    sb, si = get(dr, "body_site", "v1000_sign_boundary")[:, SHAM], get(dr, "body_site", "v1000_sign_interior")[:, SHAM]
    eb, ei = (1 - sb) * ne, (1 - si) * (256 - ne)
    tot = (eb + ei).sum(1)
    return float(np.mean(np.where(tot > 0, eb.sum(1) / np.where(tot > 0, tot, 1), np.nan)))


def transfer_ratio(root, regime, blocks):
    """Paired body displacement over realised reference change (body_site, R held), per block."""
    per = {band: [] for band in D.BANDS}
    for b in blocks:
        with np.load(root / "raw" / regime / f"{b}.npz") as raw:
            V, R, R0 = raw["body_site/V"], raw["body_site/R"], raw["s0/R"]
        for band in D.BANDS:
            c = CNAME.index(f"reference-{band}-0.5")
            per[band].append(((V[c] - V[SHAM]) ** 2).sum() / ((R[c] - R0) ** 2).sum())
    return {band: float(np.mean(v)) for band, v in per.items()}


def score_predictions(data, root, blocks, pred):
    res = {}
    obs = {r: {a: get(dr, a, "v1000_sign").mean(2).mean(0) for a in HOLD} for r, dr in data.items()}
    for sid, sigma in (("PB1a", 0.1), ("PB1b", 0.3)):
        hits = total = 0
        worst = []
        for r in data:
            if D.REGIMES[r][1] != sigma:
                continue
            for a in HOLD[1:]:
                for c in D.FULL:
                    p = pred[r]["qsl"][a][CNAME[c]][0]
                    total += 1
                    hits += abs(obs[r][a][c] - p) <= 0.05
                    worst.append(abs(obs[r][a][c] - p))
        res[sid] = {"hits": int(hits), "cells": total, "median_abs_error": float(np.median(worst)) if worst else None,
                    "verdict": ("HOLDS" if hits >= 0.5 * total else "FAILS") if total else "UNDECIDED"}
    cells = {r: pred[r]["qsl"]["inactive"]["sham"][0] - obs[r]["inactive"][SHAM]
             for r in data if D.REGIMES[r][1] == 0.3}
    res["PB1c"] = {"predicted_minus_observed": cells,
                   "verdict": ("HOLDS" if all(v > 0.20 for v in cells.values()) else "FAILS") if len(cells) == 3 else "UNDECIDED"}
    match = decided = 0
    for r, dr in data.items():
        for i, a in enumerate(HOLD):
            for b in HOLD[i + 1:]:
                rows = contrast(dr, a, b, "v1000_sign")
                for c, row in enumerate(rows):
                    if row is None or row["reading"] not in ("BENEFIT", "HARM"):
                        continue
                    decided += 1
                    pd = pred[r]["qsl"][a][CNAME[c]][0] - pred[r]["qsl"][b][CNAME[c]][0]
                    match += (pd > 0) == (row["reading"] == "BENEFIT")
    res["PB2"] = {"matching": int(match), "decided_pairs": int(decided),
                  "verdict": ("HOLDS" if match >= 0.8 * decided else "FAILS") if decided else "UNDECIDED"}
    cells = []
    for r, dr in data.items():
        for cond, arms in (("reference-fine-0.5", ("body_region", "body_sheet")), ("reference-regional-0.5", ("body_sheet",))):
            c = CNAME.index(cond)
            for a in arms:
                for ep in ("v1000_qual", "f_qual"):
                    x = get(dr, a, ep)
                    cells.append({"regime": r, "arm": a, "condition": cond, "endpoint": ep,
                                  "point": float((x[:, c] - x[:, SHAM]).mean(1).mean())})
    res["PB3"] = {"cells": cells, "max_abs": float(max(abs(c["point"]) for c in cells)),
                  "verdict": "HOLDS" if all(abs(c["point"]) <= 0.01 for c in cells) else "FAILS"}
    ok, detail = True, {}
    for r, dr in data.items():
        f = {lvl: early(dr, "inactive", f"mismatch_{lvl}") for lvl in ("site", "region", "sheet")}
        a = lambda lvl, cond: auc(f[lvl][:, CNAME.index(cond)], f[lvl][:, SHAM])
        row = {"region_fine": a("region", "reference-fine-0.5"), "sheet_fine": a("sheet", "reference-fine-0.5"),
               "sheet_regional": a("sheet", "reference-regional-0.5"),
               "site_min_rms_ge_1": min(a("site", f"reference-{b}-{x:g}") for b in D.BANDS for x in (1.0, 2.0))}
        ok &= row["region_fine"] <= 0.65 and row["sheet_fine"] <= 0.65 and row["sheet_regional"] <= 0.65 \
            and row["site_min_rms_ge_1"] >= 0.95
        detail[r] = row
    res["PB4"] = {"aucs": detail, "verdict": "HOLDS" if ok else "FAILS"}
    detail = {r: {"observed": boundary_fraction(dr, r), "predicted": pred[r]["boundary_error_fraction"]["body_site"]}
              for r, dr in data.items()}
    res["PB5"] = {"regimes": detail,
                  "verdict": "HOLDS" if all(abs(v["observed"] - v["predicted"]) <= 0.15 for v in detail.values()) else "FAILS"}
    worst = {}
    for r, dr in data.items():
        start = dr["damage/v_mean_start"]
        for arm in D.ARMS:
            m = get(dr, arm.name, "v1000_mean")
            d = np.abs(m - start)[:, list(D.arm_conditions(arm))]
            worst[f"{r}/{arm.name}"] = float((d <= 0.01).mean())
    res["PB6"] = {"lowest_fraction_within_0.01": min(worst.values()),
                  "arm_lowest": min(worst, key=worst.get),
                  "verdict": "HOLDS" if min(worst.values()) >= 0.99 else "FAILS"}
    detail = {r: {"observed": transfer_ratio(root, r, blocks), "theory_static_transfer": pred[r]["transfer"]["body_site"]}
              for r in data}
    res["PB7"] = {"regimes": detail, "verdict": "HOLDS" if all(
        v["observed"]["fine"] < v["observed"]["regional"] < v["observed"]["collective"] for v in detail.values()) else "FAILS"}
    return res


def write_csv(path, rows, header):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def fmt(x):
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f"{x:.4f}" if isinstance(x, float) else x)


def rnd(x, digits=4):
    """Round floats for the compact git summary; non-finite values become null."""
    if isinstance(x, (float, np.floating)):
        return round(float(x), digits) if np.isfinite(x) else None
    if isinstance(x, dict):
        return {k: rnd(v, digits) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, digits) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--regimes", default="all")
    ap.add_argument("--blocks", default=None, help="LO,HI: preflight debugging on design.DEBUG_BLOCKS only")
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    regimes = list(D.REGIMES) if a.regimes == "all" else a.regimes.split(",")
    data = load(a.root, regimes, blocks)
    for r, dr in data.items():
        digests = {m["design_digest"] for m in dr["__meta__"]}
        if digests != {D.digest()}:
            sys.exit(f"{r}: shards from another design digest {digests}")
    pred = json.loads((FROZEN / "predictions.json").read_text())["regimes"]
    a.out.mkdir(parents=True, exist_ok=True)
    full = a.root / "analysis"
    full.mkdir(exist_ok=True)
    header = ["family", "arm", "reference", "condition", "point", "lo", "hi", "blocks_pos", "blocks_neg",
              "case_rescue", "case_harm", "reading"]
    summary = {"stage": a.stage, "design_digest": D.digest(), "blocks": [lo, hi], "margin": D.MARGIN, "regimes": {}}
    allrows = []
    for r, dr in data.items():
        for ep in D.PRIMARY_ENDPOINTS + D.SECONDARY_ENDPOINTS:
            rows = []
            for fam, x, y in D.CONTRASTS:
                res = contrast(dr, x, y, ep)
                if res is None:
                    continue
                for c, row in enumerate(res):
                    if row is not None:
                        rows.append([fam, x, y, CNAME[c]] + [fmt(row[k]) for k in header[4:]])
            if not rows:
                continue
            if ep in D.PRIMARY_ENDPOINTS:
                write_csv(a.out / f"contrasts_{r}_{ep}.csv", rows, header)
            allrows += [[r, ep] + row for row in rows]
        acq = {k.split("/", 1)[1]: float(v.mean()) for k, v in dr.items() if k.startswith("acq/")}
        dmg = {k.split("/", 1)[1]: {CNAME[c]: float(v[:, c].mean()) for c in D.FULL}
               for k, v in dr.items() if k.startswith("damage/")}
        dose = {}
        for arm in D.ARMS:
            conds = list(D.arm_conditions(arm))
            dose[arm.name] = {k: float(get(dr, arm.name, k)[:, conds].mean())
                              for k in ("d_body_l1", "d_ref_l1", "d_messages_per_update")}
        levels = {}
        for name in [x.name for x in D.ARMS] + list(D.PACKETS):
            row = {}
            for ep in ("v1000_qual", "f_qual", "v1000_sign", "f_sign", "x_qual"):
                v = get(dr, name, ep)
                if v is not None:
                    row[ep] = [float(z) for z in v.mean(2).mean(0)]
            levels[name] = row
        summary["regimes"][r] = {"acquisition": acq, "damage": dmg, "dose": dose, "detection": detection(dr),
                                 "telemetry": telemetry(dr), "levels": levels}
        bl = []
        for name in ("inactive", "body_site", "reciprocal_site", "arbiter_region", "oracle_location", "copy_post", "protected"):
            vq, fq = get(dr, name, "v1000_qual"), get(dr, name, "f_qual")
            for bi, b in enumerate(blocks):
                for c in D.FULL:
                    v = None if vq is None else float(vq[bi, c].mean())
                    bl.append([r, b, name, CNAME[c], fmt(v), fmt(float(fq[bi, c].mean()))])
        target = a.out if r == D.PRIMARY else full
        write_csv(target / f"blocks_{r}.csv", bl, ["regime", "block", "arm", "condition", "v1000_qual", "f_qual"])
    write_csv(full / "contrasts_all_endpoints.csv", allrows, ["regime", "endpoint"] + header)
    for r, dr in data.items():
        np.savez(full / f"cases_{r}.npz", **{k: v for k, v in dr.items() if k != "__meta__"})
    scored = score_predictions(data, a.root, blocks, pred)
    (a.out / "predictions_scored.json").write_text(json.dumps(rnd(scored, 5), indent=1) + "\n")
    (full / "summary_full.json").write_text(json.dumps(rnd(summary, 6), separators=(",", ":")) + "\n")
    # The git copy keeps the registered views; every arm's traces and all damage fields stay in summary_full.json.
    keep_damage = ("v_rms", "r_rms", "v_mean_shift", "v_flips", "r_flips", "v_at_bound", "r_at_bound")
    for r, x in summary["regimes"].items():
        if r != D.PRIMARY:
            x.pop("levels")
        x["damage"] = {k: v for k, v in x["damage"].items() if k in keep_damage}
        x["detection"] = {k: v for k, v in x["detection"].items() if k in ("inactive", "information_loss_inactive_sensor")}
        x["telemetry"] = {k: v for k, v in x["telemetry"].items() if k != "oracle_location"}
    (a.out / "summary.json").write_text(json.dumps(rnd(summary), separators=(",", ":")) + "\n")
    print(json.dumps({k: v["verdict"] for k, v in scored.items()}, indent=1))


if __name__ == "__main__":
    main()
