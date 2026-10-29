"""Render TABLES.md from the reader's compact outputs.

python -m me002.tables --out OUT_DIR   (reads OUT_DIR/contrasts_*.csv, summary.json, predictions_scored.json)

Cells are block-mean contrasts with their reading: B benefit, H harm, = no meaningful difference,
? undecided. Every number comes from the reader's files; nothing is recomputed here.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from me002 import design as D  # noqa: E402

A_SHOW = ("sham", "reference-regional-2", "reference-collective-2", "reference-fine-2", "body-collective-2",
          "both-collective-2", "ref-then-body-10", "ref-then-body-300", "body-then-ref-10", "impose-50",
          "impose-300", "impose-inf")


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def table(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in body]
    return "\n".join(out)


def index(rs):
    return {(r["arm"], r["ref"], r["regime"], r["condition"], r["endpoint"]): r for r in rs}


def cell(r):
    return "" if r is None else f"{float(r['point']):+.3f} {r['reading']}"


def contrast_table(ix, pairs, regime, conds, ep):
    body = [[c] + [cell(ix.get((a, b, regime, c, ep))) for a, b in pairs] for c in conds]
    return table(["condition"] + [f"{a} − {b}" for a, b in pairs], body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    out = a.out
    summ = json.loads((out / "summary.json").read_text())
    verdicts = json.loads((out / "predictions_scored.json").read_text())
    md = [f"# ME002 tables ({summ['stage']}, blocks {summ['blocks'][0]}–{summ['blocks'][1] - 1})", "",
          "Block-mean paired contrasts with readings: B benefit, H harm, = no meaningful difference (±0.02), ? undecided.", "",
          "## Registered statements", "", table(["id", "verdict"], [[k, v["verdict"]] for k, v in verdicts.items()]), ""]
    if (out / "contrasts_A_fQ_qual.csv").exists():
        pairs = [("arbiter", "hold_site"), ("arbiter_me001", "hold_site"), ("arbiter", "oracle"), ("changepoint", "hold_site"),
                 ("write20_t0", "hold_site"), ("periodic20", "hold_site")]
        var = [(x, "arbiter") for x in ("arbiter_W300", "arbiter_W100", "arbiter_abort", "arbiter_pooled", "arbiter_site")]
        for ep in ("fQ_qual", "fR_qual", "v_qual"):
            ix = index(rows(out / f"contrasts_A_{ep}.csv"))
            for r in D.PANELS["A"]["regimes"]:
                md += [f"## A. Random onset: {r}, {ep}", "", contrast_table(ix, pairs, r, A_SHOW, ep), "",
                       contrast_table(ix, var, r, A_SHOW, ep), ""]
        tel = summ["panels"]["A"]["telemetry"]
        for r in D.PANELS["A"]["regimes"]:
            body = []
            for arm, row in tel[r].items():
                for c in ("sham", "reference-collective-2", "body-then-ref-10", "impose-inf"):
                    x = row[c]
                    body.append([arm, c, x["any_burst"], x["win20"], x["median_after"], x["after2_none_frac"], x.get("latched_frac", "")])
            md += [f"## A. Telemetry: {r}", "", table(["arm", "condition", "any burst", "burst ≤20 after onset", "median latency",
                                                        "no burst after 2nd event", "latched fraction"], body), ""]
        lv, ci = summ["panels"]["A"]["levels"], summ["panels"]["A"]["conditions"].index
        for r in D.PANELS["A"]["regimes"]:
            body = []
            for arm in ("hold_site", "reciprocal", "changepoint", "arbiter", "arbiter_W300", "arbiter_W100", "oracle"):
                body.append([arm] + [lv[r]["fR_qual"][arm][ci(c)] for c in ("impose-50", "impose-300", "impose-inf")]
                            + [lv[r]["fQ_qual"][arm][ci(c)] for c in ("impose-50", "impose-300", "impose-inf")])
            md += [f"## A. Sustained change, successor qualified agreement vs the own target: {r}", "",
                   table(["arm", "R pkt 50", "R pkt 300", "R pkt inf", "Q pkt 50", "Q pkt 300", "Q pkt inf"], body), ""]
    if (out / "contrasts_B_fQ_qual.csv").exists():
        ix = index(rows(out / "contrasts_B_fQ_qual.csv"))
        ivq = index(rows(out / "contrasts_B_v_qual.csv"))
        conds = [c.name for c in D.COND_B]
        pairs = [("arbiter_site", "hold_site"), ("arbiter", "hold_site"), ("arbiter_sheet", "hold_site"), ("oracle", "hold_site")]
        for r in D.PANELS["B"]["regimes"]:
            md += [f"## B. Trigger scale: {r}, fQ_qual", "", contrast_table(ix, pairs, r, conds, "fQ_qual"), ""]
        body = []
        for f in ("F0", "F4"):
            for s in (0.3, 0.1):
                for g in (0.25, 1.0, 2.5):
                    r = D.regime(f, s, g)
                    body.append([r] + [cell(ivq.get(("hold_site", "inactive", r, c, "v_qual"))) for c in ("sham",)]
                                + [cell(ivq.get(("hold_region", "hold_site", r, c, "v_qual"))) for c in ("sham",)])
        md += ["## B. Setpoint value and resolution by coupling (v_qual, sham)", "",
               table(["regime", "hold_site − inactive", "hold_region − hold_site"], body), ""]
    if "C" in summ["panels"]:
        ph = summ["panels"]["C"]["phase"]
        for key, vals in ph.items():
            body = []
            for f in ("F0", "F4", "S4", "BL", "IS"):
                body.append([f] + [" ".join(str(x) for x in vals[D.regime(f, s)]) for s in (0.05, 0.1, 0.2, 0.3, 0.4)])
            md += [f"## C. Phase table: {key}", "", table(["family", "σ 0.05", "0.1", "0.2", "0.3", "0.4"], body), ""]
    if (out / "contrasts_D_fQ_qual.csv").exists():
        conds = [c.name for c in D.COND_D]
        pairs = [("clamp_region", "clamp_site"), ("clamp_sheet", "clamp_site"), ("clamp_site", "hold_site"),
                 ("arbiter", "hold_site"), ("dual_vote", "hold_site"), ("dual_vote", "clamp_site"),
                 ("backup_region", "protected"), ("backup_sheet", "protected")]
        for ep in ("v_qual", "fQ_qual"):
            ix = index(rows(out / f"contrasts_D_{ep}.csv"))
            for r in D.PANELS["D"]["regimes"]:
                md += [f"## D. Storage: {r}, {ep}", "", contrast_table(ix, pairs, r, conds, ep), ""]
    if (out / "contrasts_E_v_qual.csv").exists():
        ix = index(rows(out / "contrasts_E_v_qual.csv"))
        conds = [c.name for c in D.COND_E]
        lv = D.LEVELS if hasattr(D, "LEVELS") else ("site", "region", "sheet")
        for r in D.PANELS["E"]["regimes"]:
            pairs = [(f"sign_{s}_{a}_eq", f"hold_{D.coarser(s, a)}") for s in lv for a in ("site",)]
            pairs += [(f"sign_{s}_site_eq", f"sign_{s}_site") for s in lv]
            md += [f"## E. Equal-dose votes: {r}, v_qual", "", contrast_table(ix, pairs, r, conds, "v_qual"), ""]
    if "F" in summ["panels"]:
        curves = summ["panels"]["F"]["curves"]
        for r, arms in curves.items():
            for env in D.ENVIRONMENTS:
                body = [[arm] + vals["v_qual"][env] for arm, vals in arms.items()]
                md += [f"## F. Heredity: {r}, environment {env}, body qualified agreement by generation", "",
                       table(["arm"] + [f"g{g}" for g in range(D.GENERATIONS + 1)], body), ""]
        ix = index(rows(out / "contrasts_F.csv"))
        pairs = [(a, b) for p, fam, a, b in D.CONTRASTS if p == "F"]
        for r in D.PANELS["F"]["regimes"]:
            conds = [f"{env}/{read}" for env in D.ENVIRONMENTS for read in ("gen8", "mean1_8")]
            md += [f"## F. Heredity contrasts: {r}, v_qual", "", contrast_table(ix, pairs[:6], r, conds, "v_qual"), "",
                   contrast_table(ix, pairs[6:], r, conds, "v_qual"), ""]
    (out / "TABLES.md").write_text("\n".join(md) + "\n")
    print(f"wrote {out / 'TABLES.md'}")


if __name__ == "__main__":
    main()
