"""Engineering probe P22c (python probes/p22c_sc001_final.py CPUS): SC001's revised draft on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; run before any freeze.

After P22 and P22b (same blocks 900780-900783 and tag mse-p22), the draft was revised on the lead's decisions of
28 October: panel G at theta x0 only, with a smooth-growth arm (smooth/100: division at one line per 100 updates
with a flat margin); panel R with both regrowth speeds (0.04 and 0.01) as conditions. P22c runs the whole revised
draft: panel G (S4 x0; perp and par; both bodies; 12 arms) and panel R (S4 and F0 x0; both bodies; 24 conditions).
Writes block means to probes/results/p22c_sc001_final.json and, with SDs over blocks, to the lane's scratch probes
folder.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from sc001 import design as D  # noqa: E402
from sc001 import worker as W  # noqa: E402

OUT = LANE / "probes" / "results" / "p22c_sc001_final.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p22c_sc001_final_full.json")


def job(args):
    panel, unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    ends, raw, timing, cases = W.task(panel, unit, block, "engineering", tag=D.PROBE_TAG)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        means = {k: np.nanmean(v, axis=-1) if k.split("/")[-1] != "profile" else np.nanmean(v, axis=1)
                 for k, v in ends.items()}
    return panel, unit, block, means, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    work = sorted(((p, u, b) for p, u in D.tasks() for b in blocks), key=lambda w: w[0] != "R")
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*w, cpus[i % len(cpus)]) for i, w in enumerate(work)]))
    levels, full = {}, {}
    for panel, unit in D.tasks():
        rows = sorted((r for r in res if r[:2] == (panel, unit)), key=lambda r: r[2])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for key in rows[0][3]:
                x = np.stack([r[3][key] for r in rows])
                m, s = np.nanmean(x, 0), np.nanstd(x, 0, ddof=1)
                full.setdefault(panel, {}).setdefault(unit, {})[key] = {"mean": np.round(m, 4).tolist(),
                                                                         "sd": np.round(s, 4).tolist()}
                if not key.endswith(("/t_sign", "/t_r_patch")):
                    levels.setdefault(panel, {}).setdefault(unit, {})[key] = np.round(m, 3).tolist()
    head = {"probe": "P22c", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "draft_digest": D.digest(), "arms": [a.name for a in D.ARMS_G], "conds": [c.name for c in D.CONDS_R],
            "geoms": D.GEOMS, "snaps": D.SNAPS, "reads_r": D.READS_R, "trace": D.TRACE,
            "layout": "levels[panel][unit]: G 'body/geo/endpoint' (snaps x arms; traces every TRACE updates x arms; "
                      "function per arm; profile arms x distance 0..DMAX), R 'body/endpoint' (reads x conds; traces x "
                      "conds; function per cond); block means of case means (NaN-aware)",
            "task_wall_s": {f"{r[0]}/{r[1]}/{r[2]}": r[4] for r in res},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps({**head, "levels": levels}, separators=(",", ":")) + "\n")
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
