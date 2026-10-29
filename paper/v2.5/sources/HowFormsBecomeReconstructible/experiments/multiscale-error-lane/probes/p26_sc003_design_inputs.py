"""Engineering probe P26 (python probes/p26_sc003_design_inputs.py CPUS): SC003's draft tissue on its probe blocks.
ENGINEERING_PROBE_NOT_EVIDENCE; the design input for SC003's registered statements, run before the freeze.

SC003's draft (sc003/design.py, sc003/sim.py, sc003/theory.py) on engineering blocks 900660-900663 (32 cases) under the
probe's tag mse-p26. Blocks 900660-900667 lie in the span ENGINE.md reserved for P1-P4c (900000-900699) but were never
drawn (a scan of the lane's .py, .md and .json files on 28 October 2026 found 900600-900616, 900640-900648 and
900650-900658 in the 9006xx range; BE003 holds 900670-900677).
  Part S (static, no dynamics): for each turnover rate mu and maturation time T, the stationary conductances of the 32
  cases (mat-T and gate-T at the stationary start; sister-T after the population process alone has forgotten its start)
  and each arm's bond-EMT coupling; the static voltage maps' trigger shares under scattered corruption of a quarter of
  the anchors (all cells; corrupted anchored cells) and for a changed 4 x 4 patch (the patch's cells), for mat-T, mat-T
  gated at G*, sister-T and uniform sheets at lam 3 and at each emt arm's lam.
  Part D (dynamics): the draft's runs (both bodies; S4 and F0 in quiet tissue; reads at t = 250, 1,000, 2,000 and
  4,000; traces every 100 updates), block means over each block's 8 cases; and the probe-only laws gate-300 and
  sister-300 on cue8 and change4 at mu = 1e-3.
Writes means and SDs over blocks to probes/results/p26_sc003_design_inputs.json and every block's values to the lane's
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
from lr005 import sim as L5S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from sc003 import design as D  # noqa: E402
from sc003 import sim  # noqa: E402
from sc003 import theory as TH  # noqa: E402
from sc002.cable import Cable  # noqa: E402

OUT = LANE / "probes" / "results" / "p26_sc003_design_inputs.json"
FULL = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p26_sc003_design_inputs_full.json")
TAG = D.PROBE_TAG
BLOCKS = list(range(*D.PROBE_BLOCKS))
EXTRA = ("gate-300", "sister-300")
EXTRA_RUNS = (("T", 1e-3, "cue", 8), ("T", 1e-3, "change", 4))
TAUS = (300.0, 1000.0)


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def arms_for(run):
    return D.arms_of(run) + (EXTRA if run in EXTRA_RUNS else ())


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
    m4 = B1S.patch(cases, 4, TAG)
    cue_chg = np.where(m4, -base, base)

    def shares(gH, gW, occ_=occ, gate=False):
        tb = TH.static_triggers(cab, np.where(am & occ_, cue_bad, 0.0), sr * occ_, gH, gW, occ_, gate)
        tc = TH.static_triggers(cab, np.where(am & occ_, cue_chg, 0.0), sr * occ_, gH, gW, occ_, gate)
        return {"false_alarms": float(tb.mean()), "false_alarms_at_corrupted": float(tb[bad].mean()),
                "change4": float((tc & m4).sum() / m4.sum())}

    res = {"cases": k, "g_star": D.G_STAR, "uniform": {}, "regimes": {}}
    for lam in sorted({3.0, *D.EMT_LAM.values()}):
        g = np.full((k, D.SIDE, D.SIDE), lam ** 2)
        res["uniform"][f"{lam:g}"] = shares(g, g)
    for mu in D.MUS:
        aH, aW = sim.contact_ages(sim.cell_ages(cases, mu, TAG))
        burn = int(round(4.0 / (2.0 * mu)))                       # four contact lifetimes
        occ_s, sH_age, sW_age, sisH, sisW = TH.stationary_sisters(cases, mu, burn, TAG)
        for tau in TAUS:
            arm = f"mat-{tau:g}"
            gH, gW = sim.conductance(arm, aH, aW, occ, mu=mu)
            tot = sim.own(gH, gW)
            node = {"beta": 2 * mu * tau, "mean_m_theory": 1 / (1 + 2 * mu * tau),
                    "mean_m": float((gH.sum() + gW.sum()) / (2 * gH.size * 9.0)),
                    "lam_eff_emt": TH.lam_eff(arm, mu), "emt_lam_registered": D.EMT_LAM[(mu, tau)],
                    "self_young_theory": TH.self_young(mu, tau), "self_young": float((tot < D.G_STAR).mean()),
                    "population": shares(gH, gW), "population_gated": shares(gH, gW, gate=True)}
            if tau == 300.0:
                prm = dict(D.LAWS["sister-300"])
                ch, cw = sim.C.contacts(occ_s)
                mH, mW = sim.law(prm, sH_age, sW_age, sisH, sisW)
                gHs, gWs = np.where(ch, 9.0 * mH, 0.0), np.where(cw, 9.0 * mW, 0.0)
                node["sister"] = {"burn_in_updates": burn, "sister_share_of_contacts": float((sisH & ch).sum() + (sisW & cw).sum())
                                  / float(ch.sum() + cw.sum()), "mean_m": float((mH * ch).sum() + (mW * cw).sum()) / float(ch.sum() + cw.sum()),
                                  "lam_eff_emt": TH.lam_eff("sister-300", mu), "shares": shares(gHs, gWs, occ_s)}
            res["regimes"][f"{mu:g}/{tau:g}"] = node
    return res


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def job(args):
    unit, body, block, run = args
    t0 = time.time()
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, nr = len(cases), len(D.READS)
    arms = arms_for(run)
    na = len(arms)
    panel, mu, s, z = run
    o = sim.run(body, mu, s, z, cases, V0, ema0, R0, th, T, theta, set(D.READS), tag=TAG, arms=arms)
    key = f"{body}/{D.run_name(*run)}"
    res = {}
    for e in sim.ENDS:
        if e in o:
            res[f"{key}/{e}"] = np.nanmean(o[e].reshape(nr, na, k), -1).tolist()
    res[f"{key}/opened"] = o["opened"].reshape(na, k).mean(-1).tolist()
    res[f"{key}/newc"] = (o["newc"].reshape(len(D.AGE_BINS), na, k).mean(-1) * D.SIDE * D.SIDE).tolist()  # per case
    res[f"{key}/births"] = float(o["births"].mean())
    res[f"{key}/trace"] = np.nanmean(o["trace"].reshape(-1, na, k), -1).tolist()
    res[f"{key}/trace_all"] = np.nanmean(o["trace_all"].reshape(-1, na, k), -1).tolist()
    res[f"{key}/solvers"] = o["solvers"]
    res[f"{key}/arms"] = list(arms)
    return unit, body, block, run, res, round(time.time() - t0, 1)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    print(f"{utc()} P26 start on cpus {cpus}", flush=True)
    cost = {r: len(arms_for(r)) - 1 for r in D.RUNS}
    jobs = sorted(((u, b, blk, r) for r in D.RUNS for u in D.UNITS for b in D.BODIES for blk in BLOCKS),
                  key=lambda j: -cost[j[3]])
    os.sched_setaffinity(0, cpus[:1])
    stat = static_part()
    print(f"{utc()} static part done: " + json.dumps({k_: {x: (round(v[x], 4) if isinstance(v[x], float) else v[x])
                                                           for x in ("lam_eff_emt", "self_young", "population", "population_gated")}
                                                       for k_, v in stat["regimes"].items()}), flush=True)
    os.sched_setaffinity(0, cpus)
    queue = mp.get_context("fork").Queue()
    for c in cpus:
        queue.put(c)
    full, walls = {}, {}
    with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
        futs = [pool.submit(job, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            u, b, blk, r, res, w = f.result()
            for key, v in res.items():
                full.setdefault(u, {}).setdefault(key, {})[blk] = v
            walls[f"{u}/{b}/{blk}/{D.run_name(*r)}"] = w
            print(f"{utc()} done {i}/{len(jobs)} {u} {b} {blk} {D.run_name(*r)} {w} s", flush=True)
    summary = {}
    for u, node in full.items():
        for key, per in node.items():
            if key.endswith(("/solvers", "/arms")):
                summary.setdefault(u, {})[key] = per[BLOCKS[0]] if key.endswith("/arms") else None
                continue
            x = np.array([per[blk] for blk in BLOCKS], float)
            summary.setdefault(u, {})[key] = {"mean": x.mean(0).tolist(), "sd": x.std(0, ddof=1).tolist()}
    head = {"probe": "P26", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": BLOCKS,
            "design_digest_draft": D.digest(), "runs": list(D.RUNNAMES), "arms_t": D.ARMS_T, "arms_w": D.ARMS_W,
            "extra_arms": EXTRA, "extra_runs": [D.run_name(*r) for r in EXTRA_RUNS], "reads": D.READS,
            "finished_utc": utc(), "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(walls.values()), 1),
            "job_wall_s": walls}
    FULL.parent.mkdir(parents=True, exist_ok=True)
    FULL.write_text(json.dumps(dict(head, static=stat, blocks_values=full), separators=(",", ":")) + "\n")
    drop = ("/trace", "/trace_all", "/v_in", "/v_in_old", "/v_all", "/solvers")
    slim = {u: {k_: ({"mean": np.round(v["mean"], 5).tolist(), "sd": np.round(v["sd"], 5).tolist()}
                     if isinstance(v, dict) else v) for k_, v in node.items() if not k_.endswith(drop)}
            for u, node in summary.items()}
    OUT.write_text(json.dumps(dict(head, static=stat, summary=slim), separators=(",", ":")) + "\n")
    print(f"{utc()} wrote {OUT} ({OUT.stat().st_size} B) and {FULL}", flush=True)


if __name__ == "__main__":
    main()
