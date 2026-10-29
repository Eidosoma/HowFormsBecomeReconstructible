"""Engineering probe P22b (python probes/p22b_sc001_revised.py CPUS): SC001's revised panel G on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; run before any freeze.

After P22 (same blocks 900780-900783 and tag mse-p22), the draft's panel G was revised: two diffusion arms (decay
lengths 1.5 and 6, P22's lambda jobs) instead of one at 3, front/200 and grow/200 kept, and a front-roughness trace
added. P22b runs the revised panel G (S4 at theta x0 and x0.5; perp and par; both bodies). Panel R is unchanged since
P22. Writes block means to probes/results/p22b_sc001_revised.json and, with SDs, to the lane's scratch probes folder.
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

OUT = LANE / "probes" / "results" / "p22b_sc001_revised.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p22b_sc001_revised_full.json")


def job(args):
    unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    ends, raw, timing, cases = W.task("G", unit, block, "engineering", tag=D.PROBE_TAG)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        means = {k: np.nanmean(v, axis=-1) if k.split("/")[-1] != "profile" else np.nanmean(v, axis=1)
                 for k, v in ends.items()}
    return unit, block, means, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    work = [(u, b) for u in D.UNITS["G"] for b in blocks]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*w, cpus[i % len(cpus)]) for i, w in enumerate(work)]))
    levels, full = {}, {}
    for unit in D.UNITS["G"]:
        rows = sorted((r for r in res if r[0] == unit), key=lambda r: r[1])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for key in rows[0][2]:
                x = np.stack([r[2][key] for r in rows])
                m, s = np.nanmean(x, 0), np.nanstd(x, 0, ddof=1)
                full.setdefault(unit, {})[key] = {"mean": np.round(m, 4).tolist(), "sd": np.round(s, 4).tolist()}
                if not key.endswith("/t_sign"):
                    levels.setdefault(unit, {})[key] = np.round(m, 3).tolist()
    head = {"probe": "P22b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "draft_digest": D.digest(), "arms": [a.name for a in D.ARMS_G], "geoms": D.GEOMS, "snaps": D.SNAPS,
            "trace": D.TRACE, "layout": "levels[unit]['body/geo/endpoint']: snaps x arms, traces every TRACE updates "
            "x arms, function endpoints per arm, profile arms x distance 0..DMAX; block means of case means (NaN-aware)",
            "task_wall_s": {f"{r[0]}/{r[1]}": r[3] for r in res},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps({**head, "levels": levels}, separators=(",", ":")) + "\n")
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
