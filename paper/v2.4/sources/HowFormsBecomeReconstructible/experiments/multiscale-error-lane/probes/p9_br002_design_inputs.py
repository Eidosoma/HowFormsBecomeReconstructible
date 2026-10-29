"""Engineering probe P9 (python probes/p9_br002_design_inputs.py CPUS): BR002's worker on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for BR002's registered statements, run before the freeze.

Every (panel, regime) task of br002/design.py on engineering blocks 900824-900827 (32 cases) under BR002's tag,
with BR001's frozen panel-P write thresholds for panel C. Shards go to scratch; this script prints and saves
block-mean levels of the endpoints the statements will use.
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

from br002 import design as D  # noqa: E402
from br002 import worker as W  # noqa: E402

ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p9")
CALIB = json.loads((LANE / "br001" / "frozen" / "calibration.json").read_text())
OUT = LANE / "probes" / "results" / "p9_br002_design_inputs_v1.json"
SHOW = {"C": ("les_r", "adopt_flip", "rg_sign", "r_sign", "w_l1"), "R": ("les_r", "r_sign", "v_qual"), "G": ("les_r",)}


def job(args):
    panel, name, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    rec = W.run_task(panel, name, block, "engineering", CALIB, str(ROOT))
    return panel, name, block, rec["wall_s"]


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    jobs = [(p, r, b) for p, r in D.tasks() for b in range(*D.PROBE_BLOCKS)]
    jobs.sort(key=lambda j: {"C": 0, "R": 1, "G": 2}[j[0]])
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        walls = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    levels = {}
    for p, spec in D.PANELS.items():
        conds = [c.name for c in spec["conditions"]]
        for r in spec["regimes"]:
            shards = [dict(np.load(ROOT / "shards" / p / r / f"{b}.npz")) for b in range(*D.PROBE_BLOCKS)]
            for arm in spec["arms"]:
                for ep in SHOW[p]:
                    x = np.stack([s[f"{arm.name}/{ep}"] for s in shards]).mean(2)      # (blocks, conditions)
                    levels.setdefault(p, {}).setdefault(r, {}).setdefault(ep, {})[arm.name] = {
                        c: round(float(x[:, i].mean()), 4) for i, c in enumerate(conds)}
    OUT.write_text(json.dumps({"probe": "P9", "status": "ENGINEERING_PROBE_NOT_EVIDENCE",
                               "blocks": list(D.PROBE_BLOCKS), "design_digest_at_probe": D.digest(),
                               "wall_s": round(time.time() - t0, 1), "task_wall_s": round(sum(w[3] for w in walls), 1),
                               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "levels": levels}, indent=1) + "\n")
    for p, regs in levels.items():
        conds = [c.name for c in D.PANELS[p]["conditions"]]
        for r, eps in regs.items():
            for ep, arms in eps.items():
                print(f"\n{p} {r} {ep}: " + " | ".join(conds))
                for arm, d in arms.items():
                    print(f"  {arm:16s} " + " ".join(f"{d[c]:7.3f}" if ep != "w_l1" else f"{d[c]:7.0f}" for c in conds))
    print(f"\nwrote {OUT} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
