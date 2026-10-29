"""Engineering probe P11 (python probes/p11_en001_design_inputs.py CPUS): EN001's worker on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for EN001's registered statements, run before the freeze.

Every (panel, regime) task of en001/design.py on engineering blocks 900880-900883 (32 cases) under EN001's tag,
with en001/frozen/calibration.json's store unit for panel E. Shards go to scratch; this script prints and saves
block-mean levels of every endpoint.
v1 (21:37Z) averaged the store's wound availability over t <= 500 against the sheet's over the whole
starvation, two different windows; v2 compares inside and outside the wound over the same window (t <= REPAIR).
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

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from en001 import design as D  # noqa: E402
from en001 import worker as W  # noqa: E402

ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p11v2")
CALIB = json.loads((LANE / "en001" / "frozen" / "calibration.json").read_text())
OUT = LANE / "probes" / "results" / "p11_en001_design_inputs_v2.json"


def job(args):
    panel, name, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    rec = W.run_task(panel, name, block, "engineering", CALIB, str(ROOT))
    return panel, name, block, rec["wall_s"]


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    jobs = [(p, r, b) for p, r in D.tasks() for b in range(*D.PROBE_BLOCKS)]
    jobs.sort(key=lambda j: {"G": 0, "E": 1, "P": 2}[j[0]])
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        walls = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    levels = {}
    conds = [c.name for c in D.CONDS]
    for p, spec in D.PANELS.items():
        for r in spec["regimes"]:
            shards = [dict(np.load(ROOT / "shards" / p / r / f"{b}.npz")) for b in range(*D.PROBE_BLOCKS)]
            for arm, b in D.branches(p):
                for ep in D.ENDPOINTS:
                    x = np.stack([s[f"{arm}/{b.name}/{ep}"] for s in shards])          # (blocks, conds, cases)
                    if ep == "t95":
                        x = np.where(np.isinf(x), D.WINDOW + D.SNAP, x)                # never healed: WINDOW + SNAP
                    m = np.nanmean(x, axis=2).mean(0) if not np.isnan(x).all() else np.full(len(conds), np.nan)
                    levels.setdefault(p, {}).setdefault(r, {}).setdefault(arm, {}).setdefault(b.name, {})[ep] = {
                        c: (None if not np.isfinite(m[i]) else round(float(m[i]), 4)) for i, c in enumerate(conds)}
    OUT.write_text(json.dumps({"probe": "P11", "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                               "blocks": list(D.PROBE_BLOCKS), "design_digest_at_probe": D.digest(),
                               "wall_s": round(time.time() - t0, 1), "task_wall_s": round(sum(w[3] for w in walls), 1),
                               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "levels": levels}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} in {time.time() - t0:.0f} s; task wall {sum(w[3] for w in walls):.0f} s")


if __name__ == "__main__":
    main()
