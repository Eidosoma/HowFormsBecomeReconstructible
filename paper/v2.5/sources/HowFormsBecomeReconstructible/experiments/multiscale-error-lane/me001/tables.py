"""Markdown tables for the report, rendered from the reader's outputs (no number is typed).

python -m me001.tables --results RESULTS_DIR > RESULTS_DIR/TABLES.md
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from me001 import design as D  # noqa: E402

SHOW = ("sham", "body-collective-2", "body-regional-2", "reference-fine-2", "reference-regional-2",
        "reference-collective-2", "reference-collective-1", "both-regional-2")
CNAME = [D.condition_name(i) for i in D.FULL]
SHORT = {"BENEFIT": "B", "HARM": "H", "NO MEANINGFUL DIFFERENCE": "=", "UNDECIDED": "?"}


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in body]
    return "\n".join(out)


def cell(row):
    if row is None:
        return ""
    return f"{float(row['point']):+.3f} {SHORT[row['reading']]} ({row['blocks_pos']}/{int(row['blocks_pos']) + int(row['blocks_neg'])})"


def index(rs):
    return {(r["arm"], r["reference"], r["condition"]): r for r in rs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    a = ap.parse_args()
    res = a.results
    summary = json.loads((res / "summary.json").read_text())
    scored = json.loads((res / "predictions_scored.json").read_text())
    p = summary["regimes"][D.PRIMARY]
    print(f"# Tables ({summary['stage']}, blocks {summary['blocks'][0]}-{summary['blocks'][1] - 1})\n")
    print("Cells: point estimate over blocks, reading (B benefit, H harm, = no meaningful difference within "
          f"±{D.MARGIN}, ? undecided), blocks positive / blocks non-zero.\n")

    print("## Acquisition (block means)\n")
    body = []
    for r, x in summary["regimes"].items():
        acq = x["acquisition"]
        body.append([r, f"{acq['taught_r_sign']:.3f}", f"{acq['r_sign']:.3f}", f"{acq['v0_sign']:.3f}", f"{acq['v0_qual']:.3f}"])
    print(table(["regime", "taught R sign", "R sign at damage", "body sign at damage", "body qualified at damage"], body))

    print("\n## Damage as delivered (primary regime, means over cases)\n")
    dmg = p["damage"]
    body = []
    for c in CNAME[1:]:
        if not c.endswith("-2") and not c.endswith("-0.5"):
            continue
        body.append([c, f"{dmg['v_rms'][c]:.3f}", f"{dmg['r_rms'][c]:.3f}", f"{dmg['v_mean_shift'][c]:+.4f}",
                     f"{dmg['v_flips'][c]:.3f}", f"{dmg['r_flips'][c]:.3f}"])
    print(table(["condition", "realised body RMS", "realised R RMS", "body mean shift", "body sign flips", "R sign flips"], body))

    print(f"\n## Levels, primary regime ({D.PRIMARY}): body qualified at t = 1000 / fresh qualified\n")
    lv = p["levels"]
    arms = ("inactive", "body_site", "body_region", "body_sheet", "reciprocal_site", "reciprocal_region",
            "write20_site", "write500_site", "snapshot", "arbiter_region", "changepoint_region", "oracle_location",
            "copy_post", "protected", "target", "zero", "off_reader")
    body = []
    for arm in arms:
        row = [arm]
        for c in SHOW:
            i = CNAME.index(c)
            v = lv[arm].get("v1000_qual", [None] * len(CNAME))[i]
            f = lv[arm]["f_qual"][i]
            row.append(("" if v is None else f"{v:.3f} / ") + ("" if f is None else f"{f:.3f}"))
        body.append(row)
    print(table(["arm"] + list(SHOW), body))

    for ep in D.PRIMARY_ENDPOINTS:
        idx = index(rows(res / f"contrasts_{D.PRIMARY}_{ep}.csv"))
        print(f"\n## Key contrasts, primary regime, {ep}\n")
        pairs = [("body_site", "inactive"), ("body_region", "inactive"), ("body_sheet", "inactive"),
                 ("reciprocal_site", "body_site"), ("body_region", "body_site"), ("body_sheet", "body_site"),
                 ("write20_site", "wait20_site"), ("write500_site", "wait500_site"),
                 ("arbiter_region", "body_site"), ("arbiter_region", "changepoint_region"),
                 ("arbiter_region", "oracle_location"), ("changepoint_region", "body_site"),
                 ("snapshot", "body_site"), ("protected", "copy_post"), ("body_site", "copy_post"),
                 ("arbiter_region", "copy_post")]
        body = []
        for x, y in pairs:
            if not any((x, y, c) in idx for c in SHOW):
                continue
            body.append([f"{x} − {y}"] + [cell(idx.get((x, y, c))) for c in SHOW])
        print(table(["contrast"] + list(SHOW), body))

    print("\n## Across regimes: arbiter_region − body_site, f_qual\n")
    body = []
    conds = ("sham", "body-collective-2", "reference-fine-2", "reference-regional-2", "reference-collective-2",
             "reference-collective-1", "both-regional-2")
    for r in D.REGIMES:
        idx = index(rows(res / f"contrasts_{r}_f_qual.csv"))
        body.append([r] + [cell(idx.get(("arbiter_region", "body_site", c))) for c in conds])
    print(table(["regime"] + list(conds), body))

    print("\n## Across regimes: resolution of the hold route, v1000_qual\n")
    body = []
    for r in D.REGIMES:
        idx = index(rows(res / f"contrasts_{r}_v1000_qual.csv"))
        for x, y in (("body_region", "body_site"), ("body_sheet", "body_site"), ("body_sheet", "inactive")):
            body.append([r, f"{x} − {y}"] + [cell(idx.get((x, y, c))) for c in ("sham", "body-regional-2", "reference-regional-2", "reference-collective-2")])
    print(table(["regime", "contrast", "sham", "body-regional-2", "reference-regional-2", "reference-collective-2"], body))

    print("\n## Sign factorial, primary regime, sham: sign_s_a − body_(coarser), v1000_qual\n")
    idx = index(rows(res / f"contrasts_{D.PRIMARY}_v1000_qual.csv"))
    body = []
    for s in ("site", "region", "sheet"):
        row = [s]
        for act in ("site", "region", "sheet"):
            coarser = max(s, act, key=("site", "region", "sheet").index)
            row.append(cell(idx.get((f"sign_{s}_{act}", f"body_{coarser}", "sham"))))
        body.append(row)
    print(table(["sensor \\ actuator", "site", "region", "sheet"], body))

    print("\n## Detection AUC, primary regime, inactive arm (sensor logged, actuator off), mean of t = 1-3\n")
    det = p["detection"]["inactive"]
    conds = ("body-fine-0.5", "body-collective-2", "reference-fine-0.5", "reference-fine-2", "reference-regional-0.5",
             "reference-regional-2", "reference-collective-1", "both-regional-2")
    print(table(["feature"] + list(conds), [[f] + [f"{det[f][c]:.2f}" for c in conds] for f in det]))
    loss = p["detection"]["information_loss_inactive_sensor"]
    print("\nInformation-loss detection (consequential vs inconsequential damaged cases, inactive-arm sensors):\n")
    feats = [k for k in next(iter(loss.values())) if k not in ("consequential_cases", "damaged_cases")]
    print(table(["location", "consequential / damaged"] + feats,
                [[loc, f"{v['consequential_cases']}/{v['damaged_cases']}"] + ["" if v[f] is None else f"{v[f]:.2f}" for f in feats]
                 for loc, v in loss.items()]))

    print("\n## Arbiter telemetry, primary regime\n")
    tel = p["telemetry"]
    body = []
    for arm in ("arbiter_region", "changepoint_region"):
        for c in ("sham", "body-collective-2", "reference-fine-2", "reference-regional-2", "reference-collective-2", "both-regional-2"):
            t = tel[arm][c]
            body.append([arm, c, f"{t['cases_bursting']:.3f}", t["median_first_burst"], f"{t['first_decision_agrees_with_oracle']:.3f}",
                         f"{t['missed_when_oracle_helps']}/{t['oracle_helps_cases']}"])
    print(table(["arm", "condition", "cases bursting", "median first burst", "first decision = oracle's", "missed / oracle helps"], body))

    print("\n## Track B predictions\n")
    body = [[k, v["verdict"], json.dumps({x: y for x, y in v.items() if x not in ("verdict", "cells", "aucs", "regimes")})[:160]]
            for k, v in scored.items()]
    print(table(["statement", "verdict", "detail"], body))

    print("\n## Dose, primary regime (mean over conditions run)\n")
    dose = p["dose"]
    print(table(["arm", "body L1 per case", "reference L1 per case", "messages per update"],
                [[k, f"{v['d_body_l1']:.1f}", f"{v['d_ref_l1']:.2f}", f"{v['d_messages_per_update']:.0f}"]
                 for k, v in dose.items() if k in arms or k.startswith("sign_")]))


if __name__ == "__main__":
    main()
