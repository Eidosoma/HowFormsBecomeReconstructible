"""Qualification of AR006 on engineering shards; criteria fixed in advance.

python -m ar006.checks --root ROOT --cpus LIST [--debug]
  (with --debug, on the debug stage's block 900948, ROOT/debug_qualification_receipt.json; otherwise on the preflight
  blocks 900929-900947, ar006/frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every run's endpoints at its declared shape (reads x arms x cases;
    r_in_L2 and r_in_L8 exactly in the 4 x 4 none and cue runs), its trace, scalars, detector scalars, n_anc and n_mis,
    and its raw states; every value finite; nothing else
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  the bridge: the bridge stage's two tasks (AR005's registered runs of AR006's nine situations and sizes, with AR005's
    arms and vtol, under AR005's tag on AR005's debug block 900799) equal AR005's own debug outputs there bit for bit, for
    the vote, vms, vpool and vguard in every run both studies have: every endpoint at every read, the trace, every scalar
    and detector scalar, n_anc and n_mis, the size-free scorings, the final V, r, H, W, the detectors' zones and
    footprints, the second records and every arm's signal updates; and run_vt, detect and the task are their sources
    with exactly one routed call each
Q4  the vote-default identity: vms, vpool, vguard and vtol equal the vote at every read and trace point before their
    onsets, and throughout (final states and both second records included) where they never fire, per case; at sigma 1
    against the vote's sigma-0 run of the same situation and size
Q5  aliases: the vote is bit-identical across none@0 and cue@0 (its second record included); every vote-default arm is
    on for exactly min(1,000, 8,001 - onset) updates where it fired and never where it did not; the vote under the
    misread equals the vote without it (in-process, 1,000 updates)
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states and the events, and the
    size-free scorings from the final record, equal the saved ones; each detector's footprint is its saved zone
    dilated by 2, and its scalars follow from them
Q7  efficacy: DET_STAR, DET_POOL and VGUARD are AR003's, AR004's and AR005's frozen detectors, and DET_STAR and DET_POOL
    differ in ring_max alone; VTOL is DET_POOL with the split guard at VGUARD's f and DET_STAR's ring_max; the split on
    synthetic states (a window DET_STAR holds passes with the body agreeing; a window held only with one disagreeing
    anchor in the surround passes with the body confirming and not without; a window neither holds fails); on random
    states its windows equal DET_STAR's (cue_windows_multi) united with the guarded pooled windows
    (ar005.sim.guarded_windows) at every box; the routed detector equals ar005.sim.detect for vguard and ar002.sim.detect
    for DET_POOL update for update; the misread changes the anchors only; correlated damage is memory damage with the
    body flipped on the patch; the clock
Q8  pairing and the split's limits: vtol run alone equals vtol beside vms, vpool and vguard; an arm listed twice gives
    bit-identical branches; the split with a free surround of 1 equals vpool, and with a body share no window can meet
    (f 1.01) equals vms, bit for bit
Q9  resources: the development forecast within 30 CPU-hours and 12 h of wall on 12 workers, worker memory within 2 GB,
    memory and disk headroom
Q10 reader dry run: analyze, predict and tables complete on the shards, every statement is scored, and every AR006 git
    file is 256 KB or less
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
from statistics import NormalDist  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from ar001 import sim as A1S  # noqa: E402
from ar002 import sim as A2S  # noqa: E402
from ar003 import design as A3  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar003 import worker as AW  # noqa: E402
from ar004 import design as A4  # noqa: E402
from ar005 import design as A5  # noqa: E402
from ar005 import sim as S5  # noqa: E402
from ar006 import design as D  # noqa: E402
from ar006 import sim as S  # noqa: E402
from ar006 import worker as W  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import sim as DS  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

FROZEN = LANE / "ar006" / "frozen"
RUN_ROOTS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
AR005_DEBUG = RUN_ROOTS / "ar005" / "debug"
BRIDGE_ROOT = RUN_ROOTS / "ar006" / "bridge"
WORKERS = 12
EPS = AW.ENDS + ("trace",)
SCAL = AW.SCALARS + AW.DET_SCALARS
LSIZES = tuple(L for L in A3.SIZES if L != A3.SIZE)
VD = ("vms", "vpool", "vguard", "vtol")
BRIDGED = ("vote", "vms", "vpool", "vguard")


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def meta_of(path):
    return json.loads(str(np.load(path)["__meta__"]))


def runs_of(meta):
    return {r: list(a) for r, a in meta["runs"]}


def same(x, y):
    return bool(x.dtype == y.dtype and x.shape == y.shape and np.array_equal(x, y))


def det_index(parts, arm):
    a1, det, vd = parts
    return (list(det) + list(vd)).index(arm)


def rb_index(parts, arm):
    a1, det, vd = parts
    return ((["vote"] if "vote" in a1 else []) + list(vd)).index(arm)


def bridge_one(body, unit, block, root=BRIDGE_ROOT, ref=AR005_DEBUG):
    """The vote's, vms's, vpool's and vguard's branches of one bridge task against AR005's debug outputs: (mismatches,
    arrays, slices, runs)."""
    rel = Path(body) / unit / f"{block}.npz"
    e, r = npz(root / "shards" / rel), npz(root / "raw" / rel)
    E, R = npz(ref / "shards" / rel), npz(ref / "raw" / rel)
    me, mE = meta_of(root / "shards" / rel), meta_of(ref / "shards" / rel)
    ra, rA, pa, pA = runs_of(me), runs_of(mE), me["parts"], mE["parts"]
    bad, n_arr, n_sl, n_runs = [], 0, 0, 0
    for x in ("V0", "R0", "T"):
        n_arr += 1
        bad += [] if same(r[x], R[x]) else [x]
    for rn in ra:
        if rn not in rA:
            continue
        n_runs += 1
        arms = [a for a in ra[rn] if a in BRIDGED and a in rA[rn]]
        for ep in EPS + SCAL + tuple(f"r_in_L{L}" for L in LSIZES):
            key = f"{rn}/{ep}"
            if key not in e or key not in E:
                bad += [] if (key in e) == (key in E) else [f"{key}: present in one only"]
                continue
            n_arr += 1
            for a in arms:
                i, j = ra[rn].index(a), rA[rn].index(a)
                n_sl += 1
                x, y = (e[key][:, i], E[key][:, j]) if ep in EPS else (e[key][i], E[key][j])
                bad += [] if same(x, y) else [f"{key}/{a}"]
        for x in ("n_anc", "n_mis"):
            n_arr += 1
            bad += [] if same(e[f"{rn}/{x}"], E[f"{rn}/{x}"]) else [f"{rn}/{x}"]
        for x in ("V", "r", "H", "W"):
            n_arr += 1
            for a in arms:
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][ra[rn].index(a)], R[f"{rn}/{x}"][rA[rn].index(a)]) else [f"{rn}/{x}/{a}"]
        for a in [x for x in arms if x != "vote"]:
            for x in ("zone", "fp"):
                n_arr += 1
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][det_index(pa[rn], a)], R[f"{rn}/{x}"][det_index(pA[rn], a)]) else [f"{rn}/{x}/{a}"]
        for x in ("rB", "HB", "WB"):
            n_arr += 1
            for a in arms:
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][rb_index(pa[rn], a)], R[f"{rn}/{x}"][rb_index(pA[rn], a)]) else [f"{rn}/{x}/{a}"]
        for a in [x for x in arms if x != "vote"]:
            n_sl += 1
            bad += [] if me["signal_updates"][rn][a] == mE["signal_updates"][rn][a] else [f"{rn}/signal_updates/{a}"]
    return bad, n_arr, n_sl, n_runs


def synthetic(n=D.SIDE, bx=6):
    """A sheet whose record is confident (+1.2), anchors on two sublattices, cue +1 everywhere; an island (bx x bx at
    8, 8) whose anchors all disagree (cue -1); the body +1 (agreeing with the record) everywhere."""
    r = np.ones((1, n, n)) * 1.2
    am = np.zeros((1, n, n), bool)
    am[0, ::2, ::2] = True
    am[0, 1::2, 1::2] = True
    isl = np.zeros((1, n, n), bool)
    isl[0, 8:8 + bx, 8:8 + bx] = True
    aval = np.where(isl, -1.0, 1.0)
    return r, am, aval, isl, np.ones((1, n, n))


def split_items():
    """Q7's split-guard items on synthetic and random states."""
    eff = {}
    n, bx = D.SIDE, 6
    r, am, aval, isl, V = synthetic(n, bx)
    ch = dict(D.VTOL["cue"], boxes=(bx,))
    w = lambda Vx, av: bool(S.windows(Vx, r, {"am": am, "aval": av}, ch, D.VTOL["guard"])[bx][0, 8, 8])
    conf = np.where(isl, -1.0, V)                               # the body disagrees with the record over the island
    eff["a_window_det_star_holds_passes_with_the_body_agreeing"] = w(V, aval)
    ring_cells = [(6, j) for j in range(8, 8 + bx) if am[0, 6, j]]   # in the surround of width 2, above the window
    ring_cell, ring2 = ring_cells[0], ring_cells[1]
    av1 = aval.copy()
    av1[0, ring_cell[0], ring_cell[1]] = -1.0                   # one disagreeing anchor in the surround: pooled only
    conf1 = conf.copy()
    eff["a_pooled_only_window_passes_with_the_body_confirming"] = w(conf1, av1)
    eff["a_pooled_only_window_fails_with_the_body_agreeing"] = not w(V, av1)
    av2 = av1.copy()
    av2[0, ring2[0], ring2[1]] = -1.0                           # two in the surround: held by neither
    eff["a_window_neither_holds_fails_with_the_body_confirming"] = not w(conf1, av2)
    rng = np.random.default_rng(20261103)
    rr = 1.2 * np.where(rng.random((8, n, n)) < 0.97, 1.0, 0.0) * np.where(rng.random((8, n, n)) < 0.5, 1.0, -1.0)
    Vr = np.where(rng.random((8, n, n)) < 0.9, rr, -rr) * rng.uniform(0.0, 2.0, (8, n, n))
    avr = np.where(rr >= 0, 1.0, -1.0)
    for j in range(8):
        for side in (int(rng.integers(2, 12)) for _ in range(3)):   # cue damage: the cue flipped, body and record agree
            a_, b0 = rng.integers(0, n, 2)
            avr[j][np.ix_(np.arange(a_, a_ + side) % n, np.arange(b0, b0 + side) % n)] *= -1.0
        for side in (int(rng.integers(3, 9)) for _ in range(2)):    # memory damage: the record flipped, the body right
            a_, b0 = rng.integers(0, n, 2)
            rr[j][np.ix_(np.arange(a_, a_ + side) % n, np.arange(b0, b0 + side) % n)] *= -1.0
        avr[j][rng.random((n, n)) < 0.05] *= -1.0
    Pr = {"am": rng.random((8, n, n)) < 0.25, "aval": avr}
    star = A2S.cue_windows_multi(rr, Pr, D.DET_STAR["cue"])
    guarded = S5.guarded_windows(Vr, rr, Pr, D.VGUARD["cue"], D.VGUARD["guard"])
    split = S.windows(Vr, rr, Pr, D.VTOL["cue"], D.VTOL["guard"])
    eff["split_equals_det_star_united_with_the_guarded_pooled_windows_at_every_box"] = bool(
        all(np.array_equal(split[b], star[b] | guarded[b]) for b in D.VTOL["cue"]["boxes"]))
    eff["the_split_adds_windows_beyond_det_star_and_beyond_vguard"] = bool(
        any((split[b] & ~star[b]).any() for b in split) and any((split[b] & ~guarded[b]).any() for b in split))
    ok = True
    for cfg, ref in ((D.VGUARD, S5.detect), (D.DET_POOL, A2S.detect)):
        sa, sb = A2S.new_det(8), A2S.new_det(8)
        for t in range(1, 6):
            Pt = {"am": Pr["am"], "aval": np.where(rng.random((8, n, n)) < 0.02, -avr, avr)}
            ref(sa, Vr, rr, Pt, cfg, t)
            S.detect(sb, Vr, rr, Pt, cfg, t)
            ok &= all(np.array_equal(sa[x], sb[x]) for x in ("t_on", "zone", "fp", "windows", "by"))
            ok &= sa["count"].keys() == sb["count"].keys() and all(np.array_equal(sa["count"][x], sb["count"][x]) for x in sa["count"])
    eff["the_routed_detector_equals_ar005_for_vguard_and_ar002_for_det_pool"] = bool(ok)
    return eff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    stage = "debug" if a.debug else "preflight"
    blocks, runs = D.stage_blocks(stage), D.STAGE_RUNS[stage]
    RUNS = {D.run_name(*x): x for x in runs}
    receipt_path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
    shard = lambda b_, u_, blk: npz(root / "shards" / b_ / u_ / f"{blk}.npz")
    rawf = lambda b_, u_, blk: npz(root / "raw" / b_ / u_ / f"{blk}.npz")
    tag = D.stage_tag(stage)
    checks = {}
    k, ntr = D.NCASE, D.WINDOW // D.TRACE

    missing = []
    for body, u in D.tasks():
        for blk in blocks:
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e, r = npz(path), rawf(body, u, blk)
            bad = [x for x, v in list(e.items()) + list(r.items()) if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all()]
            want_e, want_r = set(), {"V0", "R0", "T"}
            for run in runs:
                rn, na = D.run_name(*run), len(D.arms_of(run))
                nz, nb = len(run[3]) + len(run[4]), (1 if "vote" in run[2] else 0) + len(run[4])
                for x in AW.ENDS:
                    if x == "r_in_old":
                        continue
                    want_e.add(f"{rn}/{x}")
                    bad += [] if e.get(f"{rn}/{x}", np.zeros(0)).shape == (len(D.READS), na, k) else [f"{rn}/{x}"]
                for x in SCAL:
                    want_e.add(f"{rn}/{x}")
                    bad += [] if e.get(f"{rn}/{x}", np.zeros(0)).shape == (na, k) else [f"{rn}/{x}"]
                for x in ("n_anc", "n_mis"):
                    want_e.add(f"{rn}/{x}")
                    bad += [] if e.get(f"{rn}/{x}", np.zeros(0)).shape == (k,) else [f"{rn}/{x}"]
                want_e.add(f"{rn}/trace")
                bad += [] if e.get(f"{rn}/trace", np.zeros(0)).shape == (ntr, na, k) else [f"{rn}/trace"]
                if run[0] in A3.SIZE_FREE and run[5] == D.SIZE:
                    for L in LSIZES:
                        want_e.add(f"{rn}/r_in_L{L}")
                        bad += [] if e.get(f"{rn}/r_in_L{L}", np.zeros(0)).shape == (na, k) else [f"{rn}/r_in_L{L}"]
                for x, n_ in (("V", na), ("r", na), ("H", na), ("W", na), ("zone", nz), ("fp", nz), ("rB", nb), ("HB", nb), ("WB", nb)):
                    want_r.add(f"{rn}/{x}")
                    bad += [] if r.get(f"{rn}/{x}", np.zeros(0)).shape == (n_, k, D.SIDE, D.SIDE) else [f"{rn}/{x}"]
            bad += [f"unexpected {x}" for x in (set(e) - want_e) | (set(r) - want_r)]
            missing += [f"{body}/{u}/{blk}/{x}" for x in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10], "tasks": len(manifest["tasks"])}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    sm = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, blocks[0], D.PURPOSE[stage], str(serial), tag, runs, D.stage_detectors(stage))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{blocks[0]}.npz"), npz(serial / kind / body / u / f"{blocks[0]}.npz")
        sm[f"{kind}/{body}/{u}/{blocks[0]}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[q], y[q]) for q in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(sm.values()), "tasks": sm}

    mism, n_t, n_arr, n_sl, n_runs = {}, 0, 0, 0, 0
    for body, u in D.BRIDGE_TASKS:
        for blk in D.BRIDGE_BLOCKS:
            bad, na_, ns_, nr_ = bridge_one(body, u, blk)
            n_t, n_arr, n_sl, n_runs = n_t + 1, n_arr + na_, n_sl + ns_, n_runs + nr_
            if bad:
                mism[f"{body}/{u}/{blk}"] = bad[:10]
    routed = {"run_vt": inspect.getsource(S3.run_vd).count(S5.RUN_VD_CALL) == 1 and S.run_vt.__globals__["detect"] is S.detect,
              "detect": inspect.getsource(S5.detect).count(S.WINDOWS_CALL) == 1 and S.detect.__globals__["windows"] is S.windows,
              "one": inspect.getsource(AW.one).count("sim.run_vd(") == 1 and W.one.__globals__["run_vt"] is S.run_vt,
              "task_calls_the_routed_one": W.task.__globals__["one"] is W.one}
    checks["Q3_bridge_bit_for_bit"] = {"pass": not mism and n_t == len(D.BRIDGE_TASKS) and n_runs > 0 and all(routed.values()),
                                       "tasks_compared": n_t, "runs_compared": n_runs, "arrays_compared": n_arr,
                                       "arm_slices_compared": n_sl, "routed": routed,
                                       "reference": "AR005's debug outputs on 900799 (tag mse-ar005, frozen digest)",
                                       "mismatched": mism}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, u in D.tasks():
        for blk in blocks:
            e, raw = shard(body, u, blk), rawf(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            for rn, run in RUNS.items():
                ref = rn if run[1] == 0.0 else D.run_name(run[0], 0.0, size=run[5])
                jv = ra[ref].index("vote")
                for arm in [x for x in VD if x in ra[rn]]:
                    jm = ra[rn].index(arm)
                    on = e[f"{rn}/det_on"][jm]
                    okc = True
                    for c in range(k):
                        first = on[c] if on[c] > 0 else D.WINDOW + 1
                        before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                        ntb = int((first - 1) // D.TRACE)
                        okc &= all(np.array_equal(e[f"{rn}/{q}"][before, jm, c], e[f"{ref}/{q}"][before, jv, c]) for q in EP)
                        okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, jm, c], e[f"{ref}/trace"][:ntb, jv, c]))
                        if on[c] < 0:
                            okc &= all(np.array_equal(raw[f"{rn}/{x}"][jm, c], raw[f"{ref}/{x}"][jv, c]) for x in ("V", "r", "H", "W"))
                            okc &= all(np.array_equal(raw[f"{rn}/{x}"][rb_index(pa[rn], arm), c], raw[f"{ref}/{x}"][rb_index(pa[ref], "vote"), c])
                                       for x in ("rB", "HB", "WB"))
                    items[f"{body}/{u}/{blk}/{rn}/{arm} = the vote before its onset"] = bool(okc)
    checks["Q4_vote_default_identity"] = {"pass": all(items.values()), "n_items": len(items),
                                          "failed": [x for x, v in items.items() if not v][:10]}

    q5 = {}
    for body, u in D.tasks():
        for blk in blocks:
            e, raw = shard(body, u, blk), rawf(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            j0, j1 = ra["none@0"].index("vote"), ra["cue@0"].index("vote")
            ok = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"cue@0/{x}"][j1]) for x in ("V", "r", "H", "W"))
            ok &= all(np.array_equal(raw[f"none@0/{x}"][rb_index(pa["none@0"], "vote")], raw[f"cue@0/{x}"][rb_index(pa["cue@0"], "vote")])
                      for x in ("rB", "HB", "WB"))
            ok &= all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"cue@0/{q}"][:, j1]) for q in EP)
            q5[f"{body}/{u}/{blk}/vote: none@0 = cue@0"] = bool(ok)
            for rn in RUNS:
                for arm in [x for x in VD if x in ra[rn]]:
                    o = e[f"{rn}/det_on"][ra[rn].index(arm)]
                    want = sum(min(A3.SIG["duration"], D.WINDOW + 1 - int(x)) for x in o if x > 0)
                    q5[f"{body}/{u}/{blk}/{rn}: {arm} on min(1,000, 8,001 - onset)"] = meta["signal_updates"][rn][arm] == want
    pattern, theta = D.parse_unit("S4_t1")
    prep = A1S.prepare(pattern, blocks[0], D.PURPOSE[stage])
    for s_ in ("none", "memory"):
        a0 = A1S.run("dw", s_, 0.0, ("vote",), *prep, theta, {1000}, tag=tag, window=1000)
        a1 = A1S.run("dw", s_, D.MISREAD_SIGMA, ("vote",), *prep, theta, {1000}, tag=tag, window=1000)
        q5[f"{s_}: the vote under the misread = without it"] = all(np.array_equal(a0[x], a1[x]) for x in ("V", "r", "H", "W", "rB", "r_in", "r_all"))
    checks["Q5_aliases_exact"] = {"pass": all(q5.values()), "n_items": len(q5), "failed": [x for x, v in q5.items() if not v][:10]}

    bad = []
    for body, u in D.tasks():
        pattern, theta = D.parse_unit(u)
        for blk in blocks:
            raw, e = rawf(body, u, blk), shard(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, D.PURPOSE[stage])
            for run in runs:
                rn = D.run_name(*run)
                na = len(ra[rn])
                ev = A1S.event(run[0], run[5], run[1], cases, V0, ema0, R0, T, tag)
                m, tgt, fp = ev["m"], ev["target"], B2S.footprint(ev["m"], A3.SIG["d"])
                tile = lambda x: np.tile(x, (na, 1, 1))
                rf = raw[f"{rn}/r"].reshape(na * k, D.SIDE, D.SIDE)
                Vf = raw[f"{rn}/V"].reshape(na * k, D.SIDE, D.SIDE)
                post = tile(ev["r"] > 0)
                got = {"r_in": L5S.inside(rf, tile(tgt), tile(m)), "r_all": DS.sign(rf, tile(tgt)),
                       "r_fp": L5S.inside(rf, tile(tgt), tile(fp)), "r_out": L5S.inside(rf, tile(tgt), tile(~fp)),
                       "v_in": L5S.inside(Vf, tile(tgt), tile(m)), "v_all": DS.sign(Vf, tile(tgt)),
                       "r_dose": ((rf > 0) != post).mean((-2, -1)),
                       "r_dose_in": (((rf > 0) != post) & tile(m)).sum((-2, -1)) / tile(m).sum((-2, -1))}
                for x, v in got.items():
                    if not np.array_equal(v.reshape(na, k), e[f"{rn}/{x}"][-1]):
                        bad.append(f"{body}/{u}/{blk}/{rn}/{x}")
                for L in LSIZES:
                    if f"{rn}/r_in_L{L}" in e:
                        mL = tile(B1S.patch(cases, L, tag))
                        if not np.array_equal(L5S.inside(rf, tile(tgt), mL).reshape(na, k), e[f"{rn}/r_in_L{L}"]):
                            bad.append(f"{body}/{u}/{blk}/{rn}/r_in_L{L}")
                for arm in [x for x in VD if x in ra[rn]]:
                    i, z = ra[rn].index(arm), det_index(pa[rn], arm)
                    zone, fpd, on = raw[f"{rn}/zone"][z], raw[f"{rn}/fp"][z], e[f"{rn}/det_on"][i]
                    okf = np.array_equal(B2S.footprint(zone, A3.SIG["d"]) & (on > 0)[:, None, None], fpd)
                    okf &= np.array_equal(zone.sum((-2, -1)).astype(float), e[f"{rn}/det_zone"][i])
                    okf &= np.array_equal(fpd.sum((-2, -1)).astype(float), e[f"{rn}/det_fp"][i])
                    okf &= np.array_equal((fpd & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_fp_in"][i])
                    okf &= np.array_equal((zone & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_zone_in"][i])
                    bad += [] if okf else [f"{body}/{u}/{blk}/{rn}/{arm} footprint"]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    fz3 = json.loads((LANE / "ar003" / "frozen" / "design.json").read_text())
    fz4 = json.loads((LANE / "ar004" / "frozen" / "design.json").read_text())
    fz5 = json.loads((LANE / "ar005" / "frozen" / "design.json").read_text())
    eff["ar003_frozen_design_unchanged"] = fz3["digest"] == A3.digest() and fz3["sources"] == A3.sources(LANE)
    eff["ar004_frozen_design_unchanged"] = fz4["digest"] == A4.digest() and fz4["sources"] == A4.sources(LANE)
    eff["ar005_frozen_design_unchanged"] = fz5["digest"] == A5.digest() and fz5["sources"] == A5.sources(LANE)
    eff["det_star_is_ar003s_frozen"] = (D.DET_STAR == A3.DET_STAR == D.VD_DETECTORS["vms"]
                                        and json.loads(json.dumps(A3.DET_STAR)) == fz3["design"]["vd_detectors"]["vms"])
    eff["det_pool_is_ar004s_frozen"] = (D.DET_POOL == A4.DET_POOL == D.VD_DETECTORS["vpool"]
                                        and json.loads(json.dumps(A4.DET_POOL)) == fz4["design"]["det_pool"])
    eff["vguard_is_ar005s_frozen"] = (D.VGUARD == A5.VGUARD == D.VD_DETECTORS["vguard"]
                                      and json.loads(json.dumps(A5.VGUARD)) == fz5["design"]["vguard"])
    eff["det_star_and_det_pool_differ_in_ring_max_alone"] = dict(D.DET_POOL["cue"], ring_max=D.DET_STAR["cue"]["ring_max"]) == D.DET_STAR["cue"]
    eff["vtol_is_det_pool_with_the_split_at_vguards_f"] = (D.VTOL == dict(D.DET_POOL, guard={"kind": "split", "f": D.VGUARD["guard"]["f"],
                                                                                          "free_ring_max": D.DET_STAR["cue"]["ring_max"]})
                                                           and D.VD_DETECTORS["vtol"] == D.VTOL)
    eff.update(split_items())
    pattern, theta = D.parse_unit("S4_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blocks[0], D.PURPOSE[stage])
    e0, e1 = (A1S.event("memory", 4, z, cases, V0, ema0, R0, T, tag) for z in (0.0, D.MISREAD_SIGMA))
    eff["the_misread_changes_the_anchors_only"] = bool(all(np.array_equal(e0[x], e1[x]) for x in ("V", "r", "H", "W", "am", "m", "target"))
                                                       and (e0["aval"] != e1["aval"]).any() and e1["mis"].any())
    ec, en, eb = (A1S.event(s_, 4, 0.0, cases, V0, ema0, R0, T, tag) for s_ in ("correlated", "none", "body"))
    eff["correlated_is_memory_with_the_body_flipped_on_the_patch"] = bool(
        np.array_equal(ec["V"], np.where(e0["m"], -e0["V"], e0["V"])) and all(np.array_equal(ec[x], e0[x]) for x in ("r", "aval", "am", "m")))
    eff["body_damage_is_the_body_flipped_alone"] = bool(
        np.array_equal(eb["V"], np.where(en["m"], -en["V"], en["V"])) and all(np.array_equal(eb[x], en[x]) for x in ("r", "aval", "am")))
    eff["the_clock"] = (A3.CLOCK["eta"] == 3e-4 and abs(A3.CLOCK["rate"] - 3e-5) <= 1e-18 and A3.CLOCK["tau_c"] == 15000
                        and round(A3.T_STAR) == 1959)
    eff["cut_is_the_exact_quantile"] = abs(NormalDist().cdf(-cut_for(A3.CLOCK["rate"])) - A3.CLOCK["rate"]) <= 1e-12
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    q8 = {}
    pattern, theta = D.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blocks[0], D.PURPOSE[stage])
    dets = dict(D.VD_DETECTORS, vfree1=dict(D.VTOL, guard=dict(D.VTOL["guard"], free_ring_max=1)),
                vnobody=dict(D.VTOL, guard=dict(D.VTOL["guard"], f=1.01)))
    blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W", "rB", "HB", "WB", "zone", "fp")]
    for s_, z, L in (("correlated", 0.0, 4), ("memory", D.MISREAD_SIGMA, 8), ("cue", 0.0, 4)):
        run = lambda arms: S.run_vt("li4", s_, z, arms, cases, V0, ema0, R0, th, T, theta, {600}, tag=tag, window=600,
                                    size=L, detectors=dets)
        o1, o2, o3 = run(("vtol",)), run(("vms", "vpool", "vguard", "vtol")), run(("vtol", "vtol"))
        o4, o5 = run(("vpool", "vfree1")), run(("vms", "vnobody"))
        q8[f"{s_}@{z:g}-L{L}: vtol alone = vtol beside vms, vpool and vguard"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o2, 3)))
        q8[f"{s_}@{z:g}-L{L}: vtol listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o3, 0), blk_(o3, 1)))
        q8[f"{s_}@{z:g}-L{L}: the split with a free surround of 1 = vpool"] = all(np.array_equal(x, y) for x, y in zip(blk_(o4, 0), blk_(o4, 1)))
        q8[f"{s_}@{z:g}-L{L}: the split with no body confirmation possible = vms"] = all(np.array_equal(x, y) for x, y in zip(blk_(o5, 0), blk_(o5, 1)))
    checks["Q8_pairing"] = {"pass": all(q8.values()), "items": q8}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, u_ = key.split("/")[:2]
        walls.setdefault((b_, u_), []).append((t["cpu_s"], t["wall_s"]))
    n_dev = len(D.DEVELOPMENT_BLOCKS)
    cpu = sum(np.mean([c for c, _ in v]) * n_dev for v in walls.values())
    wall_h = (cpu / WORKERS * 1.15 + max(w_ for v in walls.values() for _, w_ in v)) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    rss = manifest["worker_maxrss_mb_peak"]
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 30 and wall_h <= 12 and rss <= 2048 and rss * 2 ** 20 * WORKERS <= 0.8 * avail
                                           and per_task * n_dev * len(D.tasks()) <= 0.8 * free),
                              "cpu_s_per_task": round(cpu / (n_dev * len(D.tasks())), 1), "forecast_cpu_h": round(cpu / 3600, 2),
                              "forecast_wall_h_12": round(float(wall_h), 2), "worker_rss_mb": rss, "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar006.{mod}"] + args_, cwd=LANE, capture_output=True, text=True, env=env)
             for mod, args_ in (("analyze", ["--root", str(root), "--out", str(out)]),
                                ("predict", ["--root", str(root), "--out", str(out / "predictions_scored.json")]),
                                ("tables", ["--res", str(out)]))]
    expected = [out / f for f in ("summary.json", "detectors.json", "utilities.json", "predictions_scored.json", "TABLES.md")]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from ar006 import predict as PR
    stmts = sorted({p["stmt"] for p in PR.PARTS})
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    git_files = [f for f in list((LANE / "ar006").rglob("*")) + list((LANE / "probes").rglob("*p57*"))
                 + [LANE / "tests" / "test_ar006.py", LANE / "PLAN_AR006.md", LANE / "REGISTRATION_AR006.md"] if f.is_file()]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in expected)
                                    and sorted(got) == stmts and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridge_bit_for_bit", "Q4_vote_default_identity",
             "Q5_aliases_exact", "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {x: checks[x] for x in order}
    failed = [x for x, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "ar005_digest": A5.digest(), "ar003_digest": A3.digest(), "root": str(root), "blocks": blocks, "tag": tag,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
