"""Engineering probe P22 (python probes/p22_sc001_design_inputs.py CPUS): SC001's draft on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for SC001's registered statements, run before any freeze.

SC001's draft worker (sc001/) on engineering blocks 900780-900783 (32 cases) under the probe's tag mse-p22:
  main      the draft grid: panel G (S4 at theta x0 and x0.5; perp and par; both bodies; the draft arms plus front/200
            and grow/200) and panel R (S4 and F0, theta x0; both bodies; the 16 conditions);
  lambda    panel G's diff/100 arm at decay lengths 1.5 and 6 (the draft's is 3), S4 x0;
  turnover  panel G's turn/100 arm at 0.0003 and 0.003 deaths and exchanges per cell and update (the draft's 0.001);
  regrow    panel R's regrowth conditions with division at 0.01 per update (the draft's 0.04).
Writes block means to probes/results/p22_sc001_design_inputs.json and, with SDs over blocks, to the lane's scratch
probes folder.

Ran once, 28 October 2026 (23:34:02-23:40:12Z), against the first draft (digest ac44025d2df7, recorded in the output),
which had one diffusion length (LAMBDA, 3) and no front-roughness readout. The revised draft replaces LAMBDA with two
diff arms (decay lengths 1.5 and 6) and adds the readout; panel G's revised grid is probe P22b
(p22b_sc001_revised.py). This script is kept as it ran and needs the first draft to run again.
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

OUT = LANE / "probes" / "results" / "p22_sc001_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p22_sc001_design_inputs_full.json")
DEFAULTS = {"LAMBDA": D.LAMBDA, "TURN": D.TURN, "P_REGROW": D.P_REGROW}
ARMS_MAIN = D.ARMS_G + (D.GArm("front", 200), D.GArm("grow", 200))
JOBS = ([("main", "G", u, {}, ARMS_MAIN, None) for u in D.UNITS["G"]]
        + [("main", "R", u, {}, None, D.CONDS_R) for u in D.UNITS["R"]]
        + [(f"lambda{lam:g}", "G", "S4_t0", {"LAMBDA": lam}, (D.GArm("diff", 100),), None) for lam in (1.5, 6.0)]
        + [(f"turn{tr:g}", "G", "S4_t0", {"TURN": tr}, (D.GArm("turn", 100),), None) for tr in (0.0003, 0.003)]
        + [("regrow0.01", "R", u, {"P_REGROW": 0.01}, None, tuple(c for c in D.CONDS_R if c.mode.startswith("regrow")))
           for u in D.UNITS["R"]])


def job(args):
    (name, panel, unit, over, arms, conds), block, cpu = args
    os.sched_setaffinity(0, [cpu])
    for key, val in DEFAULTS.items():                     # every job starts from the draft's constants
        setattr(D, key, over.get(key, val))
    t0 = time.time()
    kw = {"arms": arms} if panel == "G" else {"conds": conds}
    ends, raw, timing, cases = W.task(panel, unit, block, "engineering", tag=D.PROBE_TAG, **kw)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        means = {k: np.nanmean(v, axis=-1) if k.split("/")[-1] != "profile" else np.nanmean(v, axis=1)
                 for k, v in ends.items()}                 # case means within the block
    return name, panel, unit, block, means, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    blocks = list(range(*D.PROBE_BLOCKS))
    work = [(j, b) for j in JOBS for b in blocks]
    work.sort(key=lambda x: -(len(x[0][4]) if x[0][4] else 1.5 * len(x[0][5])))
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        res = list(ex.map(job, [(*w, cpus[i % len(cpus)]) for i, w in enumerate(work)]))
    levels, full = {}, {}
    for name, panel, unit in {(r[0], r[1], r[2]) for r in res}:
        rows = sorted((r for r in res if r[:3] == (name, panel, unit)), key=lambda r: r[3])
        node, fnode = levels.setdefault(name, {}).setdefault(panel, {}).setdefault(unit, {}), \
            full.setdefault(name, {}).setdefault(panel, {}).setdefault(unit, {})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for key in rows[0][4]:
                x = np.stack([r[4][key] for r in rows])
                m, s = np.nanmean(x, 0), np.nanstd(x, 0, ddof=1)
                fnode[key] = {"mean": np.round(m, 4).tolist(), "sd": np.round(s, 4).tolist()}
                if not key.endswith("/t_sign") and not key.endswith("/t_r_patch"):
                    node[key] = np.round(m, 3).tolist()
    jobs = {f"{j[0]}/{j[1]}/{j[2]}": {"overrides": j[3], "arms": [a.name for a in j[4]] if j[4] else None,
                                      "conds": [c.name for c in j[5]] if j[5] else None} for j in JOBS}
    head = {"probe": "P22", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": D.PROBE_TAG, "blocks": blocks,
            "draft_digest": D.digest(), "jobs": jobs, "snaps": D.SNAPS, "reads_r": D.READS_R, "trace": D.TRACE,
            "layout": "levels[job][panel][unit]['body/geo/endpoint'] (G) or ['body/endpoint'] (R): G snaps x arms, "
                      "R reads x conds, traces every TRACE updates x arms/conds, function endpoints per arm/cond, "
                      "G profile arms x distance 0..DMAX; block means of case means (NaN-aware)",
            "task_wall_s": {f"{r[0]}/{r[1]}/{r[2]}/{r[3]}": r[5] for r in res},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({**head, "levels": levels}, separators=(",", ":")) + "\n")
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps({**head, "levels": full}, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) and {FULL} in {head['wall_s']} s")


if __name__ == "__main__":
    main()
