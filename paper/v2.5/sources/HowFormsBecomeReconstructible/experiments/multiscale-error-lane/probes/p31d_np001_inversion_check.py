"""P31d (python probes/p31d_np001_inversion_check.py ROOT): the lead's post-hoc check of NP001's record preference.
LEAD_CHECK_NOT_REGISTERED; written and run by the lead on 29 October 2026 after the NP002 fork found that a record of
relations cannot tell phase K from phase K + 4 (its inverse); no simulation.

NP001's record preference q = (r_align - r_align_b) / (K/4) reads +1 for a record rewritten to the body's relations
in the inverted state (phase 4 against the body's phase 0), the same as for a record that kept its own phase K. This
check scores every case with an inversion-invariant preference,
    q_inv = (max(a, 1 - a) - max(a_b, 1 - a_b)) / (1 - c),   c = max(1 - K/4, K/4),
which is +1 for a record at phase K or K + 4 and -1 for one at the body's phase 0 or 4, then takes block means and item
means as NP001's reader does, for the registered condition (body) and body3 (reported). It also lists the cases below
0.5 with both alignments, which tell a degraded record (a_b near 1 - K/4) from an inverted rewrite (a_b near 0).
ROOT is NP001's development root. Output: probes/results/p31d_np001_inversion_check.txt.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
CON = {"C4s1": 1, "C4s2": 2, "C4s3": 3}
BODIES = ("dw", "li2", "li4", "li16")
BLOCKS = list(range(*json.load(open(ROOT / "manifest.json"))["blocks"]))


def qinv(a, ab, K):
    c = max(1 - K / 4, K / 4)
    return (np.maximum(a, 1 - a) - np.maximum(ab, 1 - ab)) / (1 - c)


for cond in ("body", "body3"):
    items, low = {}, []
    for b in BODIES:
        for u, K in CON.items():
            qi, qs = [], []
            for k in BLOCKS:
                with np.load(ROOT / "shards" / b / u / f"{k}.npz") as z:
                    c1 = json.loads(str(z["__meta__"]))["conds"]
                    a = z["s1/r_align"][-1, c1.index(cond)]
                    ab = z["s1/r_align_b"][-1, c1.index(cond)]
                q = qinv(a, ab, K)
                qi.append(q.mean())
                qs.append(((a - ab) / (K / 4)).mean())
                low += [(b, u, k, int(j), round(float(a[j]), 4), round(float(ab[j]), 4), round(float(q[j]), 3)) for j in np.where(q < 0.5)[0]]
            items[(b, u)] = (np.mean(qi), np.mean(qs), np.std(qi, ddof=1))
    print(f"== {cond}: the record's preference at t = 4,000 by item, inversion-invariant | signed (NP001's) | SD over blocks")
    for (b, u), (qi, qs, sd) in items.items():
        print(f"   {b:5s} {u}: {qi:+.6f} | {qs:+.6f} | {sd:.4f}")
    print(f"   inversion-invariant: {min(v[0] for v in items.values()):+.6f} to {max(v[0] for v in items.values()):+.6f}; "
          f"every item >= 0.5: {all(v[0] >= 0.5 for v in items.values())}")
    print(f"   cases below 0.5: {len(low)} of {len(BODIES) * len(CON) * len(BLOCKS) * 8} (body, unit, block, case, r_align, r_align_b, q_inv):")
    for w in low[:40]:
        print("     ", w)
    inverted = [w for w in low if w[5] < 0.15]
    print(f"   of these, with r_align_b < 0.15 (an inverted rewrite's signature): {len(inverted)}")
print("done")
