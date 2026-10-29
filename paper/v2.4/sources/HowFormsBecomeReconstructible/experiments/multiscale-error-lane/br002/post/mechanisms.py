"""Post-hoc descriptive read of BR002's saved development records (outside the frozen glob; not registered):
python -m br002.post.mechanisms --root DEV --out results/br002

A. the coarse code against minorities: inside lesion patches, the record kept at cells whose target sign is a
   minority in their 4 x 4 code region (the code's even shift pushes them the wrong way) and at majority cells,
   for the relational record with and without the code, in every panel R regime
B. where a window with tags loses the record: under a scar inside an open window, the record's agreement
   outside the patch, window alone and window + tags, conserved and open bodies
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from br002 import design as D  # noqa: E402
from mse.ops import block_projection  # noqa: E402

BLOCKS = range(*D.IDENTITIES["development"])


def raw(root, panel, r, b):
    return np.load(root / "raw" / panel / r / f"{b}.npz")


def code_minorities(root):
    out = {}
    cr = [c.name for c in D.COND_R]
    for r in D.PANELS["R"]["regimes"]:
        row = {}
        for cond in ("both-6x6", "both-8x8", "kill-8x8"):
            ci = cr.index(cond)
            acc = {a: {"minority": [], "majority": []} for a in ("rel", "rel+code", "rel+code+relink")}
            frac = []
            for b in BLOCKS:
                z = raw(root, "R", r, b)
                T, m = z["targets"], z["mask"][ci]
                minority = np.sign(T) != np.sign(block_projection(T, 4) + 1e-12)
                frac.append(float((minority & m).sum() / m.sum()))
                for a in acc:
                    ok = (z[f"{a}/R"][ci] > 0) == (T > 0)
                    for key, sel in (("minority", minority & m), ("majority", ~minority & m)):
                        if sel.any():
                            acc[a][key].append(float(ok[sel].mean()))
            row[cond] = {"minority_share_of_patch": round(float(np.mean(frac)), 4),
                         **{a: {k: round(float(np.mean(v)), 4) if v else None for k, v in d.items()} for a, d in acc.items()}}
        out[r] = row
    return out


def window_leak(root):
    out = {}
    cc = [c.name for c in D.COND_C]
    ci = cc.index("window-scar-6x6")
    for r in D.PANELS["C"]["regimes"]:
        row = {a: [] for a in ("phase", "phase+tags", "none")}
        for b in BLOCKS:
            z = raw(root, "C", r, b)
            T, m = z["targets"], z["mask"][ci]
            for a in row:
                ok = ((z[f"{a}/R"][ci] > 0) == (T > 0)) & ~m
                row[a].append(float((ok.sum((-2, -1)) / (~m).sum((-2, -1))).mean()))
        out[r] = {f"{a}_record_agree_outside_patch": round(float(np.mean(v)), 4) for a, v in row.items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = {"note": "post-hoc, descriptive, not registered; final arrays of the development run",
           "A_code_against_minorities": code_minorities(a.root), "B_window_leak": window_leak(a.root)}
    (a.out / "mechanisms.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
