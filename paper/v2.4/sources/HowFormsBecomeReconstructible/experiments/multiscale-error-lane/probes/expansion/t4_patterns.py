"""T4: is 'consensus erases fine detail' a property of BL or of its two fixed patterns? ENGINEERING_PROBE_NOT_EVIDENCE.

Every BR001 block uses the same two BL base patterns (me002.families.blobs under the tag 'mse-me002'), so the
16-block intervals carry no pattern-to-pattern variation. Here: the record alone (BR001's 'self' arm, k_r 0.5,
1 and 2, no lesion), R0 = A sign(P) with A = 0.911 (T1), for the two BR001 BL bases and 16 fresh balanced blob
patterns drawn under the tag 'mse-expansion' (block 900840) with the same recipe (Gaussian smoothing sd 2,
median threshold), 8 record-noise replicates each, 2000 updates. Endpoints: the record's sign agreement with
its own pattern; the loss at minority sites (br001/post/mechanisms.py's definition) and at the other sites; the
loss by the number of the four neighbours whose sign differs.
"""
from __future__ import annotations

import time

import numpy as np

import xcommon as X
from xcommon import address, neighbours

from br001 import design as D
from me002.families import blobs

UPDATES, REPS, AMP = 2000, 8, 0.9109


def main():
    t0 = time.time()
    b0, b1, _ = blobs("mse-me002")
    fresh = [X.balanced_blob(address(X.TAG, X.BLOCKS[8], "t4-pattern", j)) for j in range(16)]
    pats = np.stack([b0, b1, *fresh])
    names = ["BR001-BL0", "BR001-BL1", *[f"fresh{j}" for j in range(16)]]
    npat = len(pats)
    P = np.repeat(pats, REPS, axis=0)
    minority = np.sign(P) != np.sign(neighbours(np.sign(P)) + 1e-12)
    ndiff = sum((np.roll(np.sign(P), sh, ax) != np.sign(P)).astype(int) for sh, ax in ((1, -2), (-1, -2), (1, -1), (-1, -1)))
    out = {"test": "T4 patterns", "updates": UPDATES, "reps": REPS, "patterns": names, "by_kr": {}}
    for kr in (0.5, 1.0, 2.0):
        g = address(X.TAG, X.BLOCKS[8], "t4-record-noise")
        r = AMP * P.copy()
        for t in range(UPDATES):
            r = X.record_step(r, g.standard_normal(r.shape), D.EPS, kr, D.SIGMA_R, 0.0, None)
        lost = (r > 0) != (P > 0)
        per = []
        for i in range(npat):
            sl = slice(i * REPS, (i + 1) * REPS)
            per.append({"pattern": names[i],
                        "r_sign": round(float(1 - lost[sl].mean()), 4),
                        "minority_fraction": round(float(minority[sl].mean()), 4),
                        "lost_minority": round(float((lost[sl] & minority[sl]).sum() / max(minority[sl].sum(), 1)), 4),
                        "lost_other": round(float((lost[sl] & ~minority[sl]).sum() / (~minority[sl]).sum()), 4)})
        by_n = {str(n): round(float(lost[ndiff == n].mean()), 4) if (ndiff == n).any() else None for n in range(5)}
        frac_n = {str(n): round(float((ndiff == n).mean()), 4) for n in range(5)}
        fr = [x for x in per if x["pattern"].startswith("fresh")]
        summ = {k: {"BR001": [x[k] for x in per[:2]],
                    "fresh_mean": round(float(np.mean([x[k] for x in fr])), 4),
                    "fresh_min": round(float(np.min([x[k] for x in fr])), 4),
                    "fresh_max": round(float(np.max([x[k] for x in fr])), 4),
                    "fresh_sd": round(float(np.std([x[k] for x in fr], ddof=1)), 4)}
                for k in ("r_sign", "minority_fraction", "lost_minority", "lost_other")}
        # spread over the 8 noise replicates of one pattern (what block intervals can see when the pattern is fixed)
        rep_sd = float(np.mean([np.std(1 - lost[i * REPS:(i + 1) * REPS].mean((-2, -1)), ddof=1) for i in range(npat)]))
        out["by_kr"][str(kr)] = {"per_pattern": per, "summary": summ, "lost_by_differing_neighbours": by_n,
                                 "site_fraction_by_differing_neighbours": frac_n, "replicate_sd_r_sign": round(rep_sd, 5)}
        print(f"kr {kr} {time.time() - t0:.0f}s", summ, "by n", by_n, "frac", frac_n, "rep sd", round(rep_sd, 5), flush=True)
        X.save("t4_patterns.json", out)
    print(f"done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
