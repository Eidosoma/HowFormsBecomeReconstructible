"""Engineering probe P10 (python probes/p10_gw001_design_inputs.py CPUS): GW001's worker on two probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for GW001's registered statements, run before the freeze.

Every (panel, unit) task of gw001/design.py on engineering blocks 900852-900853 (16 cases) under GW001's tag.
Shards go to scratch; this script prints and saves block-mean levels: panel R kept at t = 2000, 4000 and 8000,
the median time to keep 95% (t95), committed kept and undecided sites; panel B's body endpoints.
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

from gw001 import design as D  # noqa: E402
from gw001 import sim  # noqa: E402
from gw001 import worker as W  # noqa: E402
from gw001.run import cost  # noqa: E402

ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p10")
OUT = LANE / "probes" / "results" / "p10_gw001_design_inputs_v1.json"
BLOCKS = (900852, 900853)


def job(args):
    panel, unit, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    rec = W.run_task(panel, unit, block, "engineering", str(ROOT))
    return panel, unit, block, rec["wall_s"]


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    jobs = sorted([(p, u, b) for p, u in D.tasks() for b in BLOCKS], key=lambda j: -cost(j[0], j[1]))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        walls = list(ex.map(job, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    snaps = {t: t // D.EVERY_R - 1 for t in D.READS_R}
    levels = {"R": {}, "B": {}}
    for unit in D.PANELS["R"]["units"]:
        conds = [c.name for c in D.GEOMETRIES[unit]]
        sh = [dict(np.load(ROOT / "shards" / "R" / unit / f"{b}.npz")) for b in BLOCKS]
        for arm in D.ARMS_R:
            curve = np.concatenate([s[f"{arm.name}/kept_curve"] for s in sh], axis=2)          # (snap, cond, cases)
            rs = np.concatenate([s[f"{arm.name}/rsign_curve"] for s in sh], axis=2)
            com = np.concatenate([s[f"{arm.name}/committed"] for s in sh], axis=1)
            und = np.concatenate([s[f"{arm.name}/undecided"] for s in sh], axis=1)
            t95 = sim.t95(curve, D.EVERY_R)
            row = {}
            for ci, c in enumerate(conds):
                if c == "sham":
                    row[c] = {f"rsign@{t}": round(float(rs[i, ci].mean()), 4) for t, i in snaps.items()}
                else:
                    row[c] = {**{f"kept@{t}": round(float(curve[i, ci].mean()), 4) for t, i in snaps.items()},
                              "t95_median": float(np.median(t95[ci])), "committed@8000": round(float(com[ci].mean()), 4),
                              "undecided@8000": round(float(und[ci].mean()), 4)}
            levels["R"].setdefault(unit, {})[arm.name] = row
    for unit in D.PANELS["B"]["units"]:
        conds = [c.name for c in D.COND_B]
        sh = [dict(np.load(ROOT / "shards" / "B" / unit / f"{b}.npz")) for b in BLOCKS]
        for arm in D.ARMS_B:
            levels["B"].setdefault(unit, {})[arm.name] = {
                ep: {c: round(float(np.concatenate([s[f"{arm.name}/{ep}"] for s in sh], axis=1)[ci].mean()), 4)
                     for ci, c in enumerate(conds)} for ep in ("v_qual", "v_out", "les_v", "les_r")}
    OUT.write_text(json.dumps({"probe": "P10", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "blocks": list(BLOCKS),
                               "design_digest_at_probe": D.digest(), "wall_s": round(time.time() - t0, 1),
                               "task_wall_s": round(sum(w[3] for w in walls), 1),
                               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "levels": levels},
                              indent=1) + "\n")
    print(f"wrote {OUT} in {time.time() - t0:.0f} s; task CPU {sum(w[3] for w in walls):.0f} s")


if __name__ == "__main__":
    main()
