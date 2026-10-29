"""Engineering probe P25 (python probes/p25_sc002_design_inputs.py CPUS): SC002's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for SC002's registered statements, run before the freeze.

SC002's draft (sc002/design.py, sc002/sim.py, sc002/theory.py) on engineering blocks 900650-900653 (32 cases) under the
probe's tag mse-p25. Blocks 900650-900657 lie in the span ENGINE.md reserved for P1-P4c (900000-900699) but were never
drawn (a scan of the lane's .py, .md and .json files on 28 October 2026 found only 900600-900615 in the 9006xx range).
  Part S (static, no dynamics): for each turnover rate mu and maturation time tau_m, the stationary contact ages of the
  32 cases; the bond-EMT coupling lam_eff; the response spread lam_rms at 16 sites per case; the share of cells young
  enough to read only their own cue (measured: total conductance below (kappa - theta) / (1 + theta)); the static voltage
  map's false alarms under scattered corruption of a quarter of the anchors (the share of all cells below -theta, and of
  the corrupted anchored cells) and its adoption shares for a changed patch of side 4, 8 and 12; the same for uniform
  coupling at lam_eff, 1.5 and 3.
  Part D (dynamics): the draft's runs (both bodies; S4 and F0 in quiet tissue; 14 runs; 5 arms; reads at t = 250, 1,000,
  2,000 and 4,000), block means over each block's 8 cases.
Writes means and SDs over blocks to probes/results/p25_sc002_design_inputs.json and every block's values to the lane's
scratch probes folder.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be001 import sim as B1S  # noqa: E402
from cellpop import core as C  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from sc002 import design as D  # noqa: E402
from sc002 import sim  # noqa: E402
from sc002 import theory as TH  # noqa: E402
from sc002.cable import Cable  # noqa: E402

OUT = LANE / "probes" / "results" / "p25_sc002_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p25_sc002_design_inputs_full.json")
TAG = D.PROBE_TAG
BLOCKS = list(range(*D.PROBE_BLOCKS))
GROUPS = {"base": [x for x in D.RUNS if x[1] == 0.0], **{f"mu{m:g}": [x for x in D.RUNS if x[1] == m] for m in D.MUS if m > 0}}
SIZES = (4, 8, 12)


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def static_part():
    """Static maps on the 32 probe cases (S4's acquired records; anchors, ages and corruption under the probe's tag)."""
    cases = enrol(BLOCKS, D.MESSAGES, D.PARENTS, "engineering")
    R0 = np.concatenate([sim.prepare("S4", b, "engineering")[3] for b in BLOCKS])
    k = len(cases)
    cab = Cable(k)
    occ = np.ones((k, D.SIDE, D.SIDE), bool)
    am = L5S.anchor_mask(cases, TAG)
    base = np.where(R0 > 0, 1.0, -1.0)
    sr = L5S.vote_sign(R0)
    bad = L5S.scattered(cases, am, TAG)
    cue_bad = np.where(bad, -base, base)
    patches = {z: B1S.patch(cases, z, TAG) for z in SIZES}
    rng = np.random.default_rng(20261028)
    sites = [tuple(x) for x in rng.integers(0, D.SIDE, (16, 2))]

    def shares(gH, gW):
        v = TH.static_map(cab, np.where(am, cue_bad, 0.0), sr, gH, gW, occ)
        trig = (v < -D.THETA) & (sr != 0)
        out = {"false_alarms": float(trig.mean()), "false_alarms_at_corrupted": float(trig[bad].mean()),
               "false_alarms_elsewhere": float(trig[~bad].mean())}
        for z, m in patches.items():
            vz = TH.static_map(cab, np.where(am, np.where(m, -base, base), 0.0), sr, gH, gW, occ)
            out[f"change{z}"] = float((((vz < -D.THETA) & (sr != 0)) & m).sum() / m.sum())
        return out

    res = {"cases": k, "g_star": TH.g_star(), "uniform": {}, "regimes": {}}
    for lam in (1.5, 2.0, 3.0):
        g = np.full((k, D.SIDE, D.SIDE), lam ** 2)
        res["uniform"][f"{lam:g}"] = shares(g, g)
    for mu in [m for m in D.MUS if m > 0]:
        aH, aW = sim.contact_ages(sim.cell_ages(cases, mu, TAG))
        for arm, prm in D.JUNCTIONS.items():
            if prm["tau_m"] == 0:
                continue
            tau = prm["tau_m"]
            gH, gW = sim.conductance(arm, aH, aW, occ)
            tot = gH + np.roll(gH, 1, -1) + gW + np.roll(gW, 1, -2)
            le = TH.lam_eff(mu, tau)
            gu = np.full(gH.shape, le ** 2)
            rms = TH.lam_rms(cab, gH, gW, occ, sites)
            res["regimes"][f"{mu:g}/{arm}"] = {
                "beta": 2 * mu * tau, "mean_m_theory": 1 / (1 + 2 * mu * tau),
                "mean_m": float((gH.sum() + gW.sum()) / (2 * gH.size * prm["lam"] ** 2)),
                "lam_eff_emt": le, "lam_rms_mean": float(np.sqrt((rms ** 2).mean())), "lam_rms_median": float(np.median(rms)),
                "self_young_theory": TH.self_young(mu, tau), "self_young": float((tot < TH.g_star()).mean()),
                "self_young_anchored": float((tot[am] < TH.g_star()).mean()),
                "population": shares(gH, gW), "uniform_lam_eff": shares(gu, gu)}
    return res


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(args):
    unit, body, block, group = args
    t0 = time.time()
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, na, nr = len(cases), len(D.ARMS), len(D.READS)
    res = {}
    for panel, mu, s, z in GROUPS[group]:
        o = sim.run(body, mu, s, z, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=TAG)
        key = f"{body}/{D.run_name(panel, mu, s, z)}"
        for e in sim.ENDS:
            if e in o:
                res[f"{key}/{e}"] = np.nanmean(o[e].reshape(nr, na, k), -1).tolist()
        res[f"{key}/opened"] = o["opened"].reshape(na, k).mean(-1).tolist()
        res[f"{key}/trace"] = np.nanmean(o["trace"].reshape(-1, na, k), -1).tolist()
        res[f"{key}/trace_all"] = np.nanmean(o["trace_all"].reshape(-1, na, k), -1).tolist()
        res[f"{key}/solvers"] = o["solvers"]
    return unit, body, block, group, res, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    print(f"{utc()} P25 start on cpus {cpus}", flush=True)
    jobs = [(u, b, blk, g) for g in ("mu0.001", "mu0.00025", "base") for u in D.UNITS for b in D.BODIES for blk in BLOCKS]
    os.sched_setaffinity(0, cpus[:1])
    stat = static_part()
    print(f"{utc()} static part done: " + json.dumps({k_: {x: round(v[x], 3) for x in ("lam_eff_emt", "lam_rms_mean", "self_young")}
                                                       for k_, v in stat["regimes"].items()}), flush=True)
    os.sched_setaffinity(0, cpus)
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    full, walls = {}, {}
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futs = [pool.submit(job, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            u, b, blk, g, res, w = f.result()
            for key, v in res.items():
                full.setdefault(u, {}).setdefault(key, {})[blk] = v
            walls[f"{u}/{b}/{blk}/{g}"] = w
            print(f"{utc()} done {i}/{len(jobs)} {u} {b} {blk} {g} {w} s", flush=True)
    summary = {}
    for u, node in full.items():
        for key, per in node.items():
            if key.endswith("/solvers"):
                continue
            x = np.array([per[blk] for blk in BLOCKS], float)
            summary.setdefault(u, {})[key] = {"mean": np.round(x.mean(0), 4).tolist(),
                                              "sd": np.round(x.std(0, ddof=1), 4).tolist()}
    head = {"probe": "P25", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": BLOCKS,
            "design_digest_draft": D.digest(), "arms": D.ARMS, "reads": D.READS, "runs": list(D.RUNNAMES),
            "finished_utc": utc(), "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(walls.values()), 1),
            "job_wall_s": walls}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps(dict(head, static=stat, blocks_values=full), separators=(",", ":")) + "\n")
    drop = ("/trace", "/trace_all", "/v_in", "/v_in_old", "/v_all")
    slim = {u: {k_: v for k_, v in node.items() if not k_.endswith(drop)} for u, node in summary.items()}
    OUT.write_text(json.dumps(dict(head, static=stat, summary=slim), separators=(",", ":")) + "\n")
    print(f"{utc()} wrote {OUT} ({OUT.stat().st_size} B) and {FULL}", flush=True)


if __name__ == "__main__":
    main()
