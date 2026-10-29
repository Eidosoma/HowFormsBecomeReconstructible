"""NP001's frozen reader: block means of every endpoint, the registered statements, paired contrasts.

python -m np001.analyze --root RUN_ROOT --stage {preflight,development} [--out DIR] [--blocks LO,HI]

Levels are block means: each block's mean over its 8 cases, then the mean (and SD) over blocks. The statements are scored
on these unrounded means; the written summaries round to 6 decimals. Contrasts are paired within block (the same cases,
acquisitions and noise), with 95% t intervals over blocks, at the last reads (stage 1 at 4,000, stage 2 at 2,000):
every stage-1 condition against 'alone' and against 'intact' within its task; every stage-2 branch against the
successor's no-record control ('none'); each successor body against the stage-1 body's own kind reading the same records
(own against foreign); and the records only bodies write between stage-1 bodies (the same pattern and cases).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from np001 import design as D  # noqa: E402
from np001.predict import score  # noqa: E402
from np001.sim import ENDS1, ENDS2  # noqa: E402
from np001.worker import BRANCHES2  # noqa: E402


def load(root, blocks):
    """data[(body, unit)][key] = (blocks, reads, branches) array of case means."""
    data = {}
    for body, u in D.tasks():
        arrs = {}
        for b in blocks:
            with np.load(root / "shards" / body / u / f"{b}.npz") as z:
                for k in z.files:
                    if k != "__meta__":
                        arrs.setdefault(k, []).append(z[k])
        data[(body, u)] = {k: np.stack(v).mean(-1) for k, v in arrs.items()}
    return data


def ms(v):
    return [float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else None]


def levels(data):
    """L[body][unit]['s1'][cond][endpoint] and L[body][unit]['s2'][successor][branch][endpoint] = [[mean, SD] over blocks
    at each read]. Unrounded."""
    out = {}
    for (b, u), arrs in data.items():
        node = out.setdefault(b, {}).setdefault(u, {"s1": {}, "s2": {}})
        for ci, c in enumerate(D.CONDNAMES):
            node["s1"][c] = {e: [ms(arrs[f"s1/{e}"][:, ti, ci]) for ti in range(len(D.READS))] for e in ENDS1}
        for B in D.SUCC_BODIES:
            node["s2"][B] = {c: {e: [ms(arrs[f"s2/{B}/{e}"][:, ti, ci]) for ti in range(len(D.READS2))] for e in ENDS2}
                             for ci, c in enumerate(BRANCHES2)}
    return out


def rounded(x, d=6):
    if isinstance(x, dict):
        return {k: rounded(v, d) for k, v in x.items()}
    if isinstance(x, list):
        return [rounded(v, d) for v in x]
    return None if x is None else round(x, d)


def row(unit, contrast, ep, t, v):
    n = len(v)
    half = float(stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    m = float(v.mean())
    return [unit, contrast, ep, t, round(m, 4), round(m - half, 4), round(m + half, 4), int((v > 0).sum()),
            int((v < 0).sum()), n]


def contrasts(data, out):
    """contrasts_stage1.csv: every condition against 'alone' and against 'intact' (align, r_align; for a conflict also
    align_b and r_align_b, against the body's initial phase). contrasts_stage2.csv: every branch against the successor's
    no-record control (align; for a conflict also align_b), each foreign successor against the stage-1 body's own kind
    reading the same records (align), and the records only bodies write (body1, body, body3) between stage-1 bodies."""
    head = ["unit", "contrast", "endpoint", "t", "mean", "lo95", "hi95", "blocks_pos", "blocks_neg", "blocks"]
    rows1, rows2, t1, t2 = [], [], D.READS[-1], D.READS2[-1]
    written = ("body1", "body", "body3")
    for (b, u), arrs in data.items():
        e1 = ("align", "r_align", "align_b", "r_align_b") if D.is_conflict(u) else ("align", "r_align")
        for e in e1:
            x = arrs[f"s1/{e}"][:, -1]
            for ci, c in enumerate(D.CONDNAMES):
                for ref in ("alone", "intact"):
                    if c != ref and not (ref == "alone" and e.startswith("r_")):
                        rows1.append(row(u, f"{b}/s1:{c}-{ref}", e, t1, x[:, ci] - x[:, D.CONDNAMES.index(ref)]))
        e2 = ("align", "align_b") if D.is_conflict(u) else ("align",)
        for e in e2:
            for B in D.SUCC_BODIES:
                x = arrs[f"s2/{B}/{e}"][:, -1]
                for ci, c in enumerate(BRANCHES2[:-1]):
                    rows2.append(row(u, f"{b}/s2/{B}:{c}-none", e, t2, x[:, ci] - x[:, -1]))
                    if B != b and e == "align":
                        own = arrs[f"s2/{b}/{e}"][:, -1]
                        rows2.append(row(u, f"{b}/s2:{c}:{B}-{b}(own)", e, t2, x[:, ci] - own[:, ci]))
        for b2 in D.BODIES[D.BODIES.index(b) + 1:]:
            for B in D.SUCC_BODIES:
                x, y = arrs[f"s2/{B}/align"][:, -1], data[(b2, u)][f"s2/{B}/align"][:, -1]
                for c in written:
                    ci = BRANCHES2.index(c)
                    rows2.append(row(u, f"s2/{B}:{c}:{b}-{b2}", "align", t2, x[:, ci] - y[:, ci]))
    for name, rows in (("contrasts_stage1.csv", rows1), ("contrasts_stage2.csv", rows2)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--out", type=Path, default=LANE / "results" / "np001")
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    data = load(root, blocks)
    L = levels(data)
    S = score(L)
    head = {"stage": a.stage, "blocks": [blocks[0], blocks[-1] + 1], "design_digest": D.digest(), "reads": D.READS,
            "reads2": D.READS2, "conds": D.CONDNAMES, "branches2": BRANCHES2}
    for b in D.BODIES:                          # one summary per stage-1 body: every git file < 256 KB
        (a.out / f"summary_{b}.json").write_text(json.dumps(dict(head, levels=rounded(L[b])), separators=(",", ":")) + "\n")
    (a.out / "predictions_scored.json").write_text(json.dumps(S, indent=1) + "\n")
    contrasts(data, a.out)
    print(json.dumps({k: v["verdict"] for k, v in S.items()}))


if __name__ == "__main__":
    main()
