"""Qualification of AR003C on its debug run (AR003's spare engineering blocks 900162-900163); criteria fixed in advance.

python -m ar003c.checks --root DEBUG_ROOT --cpus LIST [--receipt-to-frozen]
    (writes ROOT/debug_qualification_receipt.json; with --receipt-to-frozen, ar003c/frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every reduced run's endpoints at its declared shape (reads x arms x 8
    cases; r_in_old exactly in change@0; r_in_L2 and r_in_L8 exactly in none@0 and cue@0), its trace, scalars, detector
    scalars, n_anc and n_mis, and its raw states (V, r, H, W per arm, the detectors' zone and footprint, the vote's and
    vms's second records); every value finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  the bridge: on every debug task of the reference block (900162), every reduced branch equals AR003's full development
    task's corresponding branch bit for bit, against this package's reference stage (ar003.worker.run_task, unchanged,
    all 63 arm-runs): every endpoint at every read, the trace, every scalar and detector scalar, n_anc and n_mis, the
    size-free scorings (r_in_L2, r_in_L8), the final V, r, H, W, the detectors' zone and footprint, both records' second
    record (rB, HB, WB), the acquisition (V0, R0, T) and each arm's signal updates in the meta
Q4  the detectors' firing, onset and footprint: in every run of those tasks, det's and vms's onset, zone, footprint, their
    patch coverage, window count and channel, BE001's onset fraction and hit, and the raw zone and footprint equal the
    reference's
Q5  aliases (every debug task): (a) vms equals the vote at every read and trace point before its onset, and throughout
    (final states and both records included) where it never fires, per case; (b) u(new) + u(old) = 1 exactly for every
    branch of change@0; (c) det and vms are on for exactly min(1,000, 8,001 - onset) updates where they fired and never
    where they did not; (d) the vote, which never reads the cue, is bit-identical across none@0, cue@0 and change@0
    (its second record included)
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states and the events (at each run's patch
    side), and the size-free scorings from the final record and each side's patch, equal the saved ones; each detector's
    footprint is its saved zone dilated by 2, and its scalars follow from them
Q7  the declaration and the boundary: AR003's frozen design and sources are unchanged; every reduced run is AR003's run
    with a subset of its arms, the arms are the vote, det and vms only, and ms, vdial and the misread runs are left out;
    det and vms's detector are AR003's frozen ones; the tag, BEST, the controller, the harm bounds and the weights are
    those REGISTRATION_AR003.md declared; the development values behind the size recompute from AR003's development
    shards, and so do the rule's block counts; the 16 confirmation blocks lie in mse.assay.RANGES['confirmation'],
    920365-920380, clear of AR001C's and AR002C's 920000-920147, and the reserve beside them; no shard, raw state or
    completion record of any block from 920000 on exists in AR003's or AR003C's run roots
Q8  pairing: vms run alone equals vms run beside vdial and the vote; det run alone equals det run beside ms; an arm listed
    twice gives bit-identical branches
Q9  resources: the confirmation (16 blocks x 8 pairs) forecast within 20 CPU-hours and 3 h of wall on 12 workers, worker
    memory within 2 GB, memory and disk headroom
Q10 reader dry run: ar003c.analyze, ar003c.predict and ar003c.tables complete on the debug shards; C1, C2 and C3 are
    computed with their bounds and a verdict is formed (not read); every output and every AR003C git file is 256 KB
    or less
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from ar001 import sim as A1S  # noqa: E402
from ar002 import sim as A2S  # noqa: E402
from ar003 import analyze as AZ  # noqa: E402
from ar003 import design as A3  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar003 import worker as AW  # noqa: E402
from ar003c import design as D  # noqa: E402
from ar003c import worker as W  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.assay import RANGES  # noqa: E402

FROZEN = LANE / "ar003c" / "frozen"
RUN_ROOTS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
AR003_RUNS = RUN_ROOTS / "ar003"
AR003C_RUNS = RUN_ROOTS / "ar003c"
REF_ROOT = AR003C_RUNS / "reference"
WORKERS = 12
EPS = AW.ENDS + ("trace",)                                     # (reads or points, arms, cases): the arm axis is 1
SCAL = AW.SCALARS + AW.DET_SCALARS                             # (arms, cases): the arm axis is 0
LSIZES = tuple(L for L in D.SIZES if L != D.SIZE)


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
    """The arm's index in a run's zone/fp raw arrays (det arms, then vote-default arms)."""
    a1, det, vd = parts
    return (list(det) + list(vd)).index(arm)


def rb_index(parts, arm):
    """The arm's index in a run's rB/HB/WB raw arrays (the vote from ar001.sim.run first, then the vote-default arms)."""
    a1, det, vd = parts
    return ((["vote"] if "vote" in a1 else []) + list(vd)).index(arm)


def bridge_one(root, body, unit, block):
    """Every reduced branch of one task against AR003's full task's, bit for bit: (mismatches, arrays, arm slices)."""
    rel = Path(body) / unit / f"{block}.npz"
    e, r = npz(root / "shards" / rel), npz(root / "raw" / rel)
    E, R = npz(REF_ROOT / "shards" / rel), npz(REF_ROOT / "raw" / rel)
    me, mE = meta_of(root / "shards" / rel), meta_of(REF_ROOT / "shards" / rel)
    ra, rA, pa, pA = runs_of(me), runs_of(mE), me["parts"], mE["parts"]
    bad, n_arr, n_sl = [], 0, 0
    for x in ("V0", "R0", "T"):
        n_arr += 1
        bad += [] if same(r[x], R[x]) else [x]
    for rn in D.RUNNAMES:
        arms, full = ra[rn], rA[rn]
        idx = [full.index(a) for a in arms]
        for ep in EPS:
            key = f"{rn}/{ep}"
            if (key in e) != (key in E):
                bad.append(f"{key}: present in one only")
                continue
            if key not in e:
                continue
            n_arr += 1
            for i, j in enumerate(idx):
                n_sl += 1
                bad += [] if same(e[key][:, i], E[key][:, j]) else [f"{key}/{arms[i]}"]
        for sc in SCAL + tuple(f"r_in_L{L}" for L in LSIZES):
            key = f"{rn}/{sc}"
            if (key in e) != (key in E):
                bad.append(f"{key}: present in one only")
                continue
            if key not in e:
                continue
            n_arr += 1
            for i, j in enumerate(idx):
                n_sl += 1
                bad += [] if same(e[key][i], E[key][j]) else [f"{key}/{arms[i]}"]
        for x in ("n_anc", "n_mis"):
            n_arr += 1
            bad += [] if same(e[f"{rn}/{x}"], E[f"{rn}/{x}"]) else [f"{rn}/{x}"]
        for x in ("V", "r", "H", "W"):
            n_arr += 1
            for i, j in enumerate(idx):
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][i], R[f"{rn}/{x}"][j]) else [f"{rn}/{x}/{arms[i]}"]
        for x in ("zone", "fp"):
            n_arr += 1
            for a in (q for q in arms if q in ("det", "vms")):
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][det_index(pa[rn], a)], R[f"{rn}/{x}"][det_index(pA[rn], a)]) else [f"{rn}/{x}/{a}"]
        for x in ("rB", "HB", "WB"):
            n_arr += 1
            for a in (q for q in arms if q in ("vote", "vms")):
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][rb_index(pa[rn], a)], R[f"{rn}/{x}"][rb_index(pA[rn], a)]) else [f"{rn}/{x}/{a}"]
        for a in arms:
            n_sl += 1
            bad += [] if me["signal_updates"][rn][a] == mE["signal_updates"][rn][a] else [f"{rn}/signal_updates/{a}"]
    return bad, n_arr, n_sl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--receipt-to-frozen", action="store_true")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("debug")
    manifest = json.loads((root / "manifest.json").read_text())
    receipt_path = FROZEN / "qualification_receipt.json" if a.receipt_to_frozen else root / "debug_qualification_receipt.json"
    shard = lambda b_, u_, blk: npz(root / "shards" / b_ / u_ / f"{blk}.npz")
    rawf = lambda b_, u_, blk: npz(root / "raw" / b_ / u_ / f"{blk}.npz")
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
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(D.arms_of(run))
                nz, nb = len(run[3]) + len(run[4]), (1 if "vote" in run[2] else 0) + len(run[4])
                for x in AW.ENDS:
                    if x == "r_in_old" and run[0] != "change":
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
    W.run_task(body, u, blocks[0], D.PURPOSE["debug"], str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{blocks[0]}.npz"), npz(serial / kind / body / u / f"{blocks[0]}.npz")
        sm[f"{kind}/{body}/{u}/{blocks[0]}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[q], y[q]) for q in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(sm.values()), "tasks": sm}

    mism, n_t, n_arr, n_sl = {}, 0, 0, 0
    for body, u in D.tasks():
        for blk in D.REFERENCE_BLOCKS:
            bad, na_, ns_ = bridge_one(root, body, u, blk)
            n_t, n_arr, n_sl = n_t + 1, n_arr + na_, n_sl + ns_
            if bad:
                mism[f"{body}/{u}/{blk}"] = bad[:10]
    checks["Q3_bridge_bit_for_bit"] = {"pass": not mism and n_t == len(D.tasks()) * len(D.REFERENCE_BLOCKS), "tasks_compared": n_t,
                                       "arrays_compared": n_arr, "arm_slices_compared": n_sl,
                                       "branches_compared": n_t * D.ARM_RUNS,
                                       "reference": "AR003's full development task (ar003.worker.run_task, unchanged) on 900162",
                                       "mismatched": mism}

    q4, fired, n_cmp = {}, {"det": 0, "vms": 0}, 0
    for body, u in D.tasks():
        for blk in D.REFERENCE_BLOCKS:
            rel = Path(body) / u / f"{blk}.npz"
            e, E, r, R = shard(body, u, blk), npz(REF_ROOT / "shards" / rel), rawf(body, u, blk), npz(REF_ROOT / "raw" / rel)
            me, mE = meta_of(root / "shards" / rel), meta_of(REF_ROOT / "shards" / rel)
            ra, rA = runs_of(me), runs_of(mE)
            for rn in D.RUNNAMES:
                for arm in (q for q in ra[rn] if q in ("det", "vms")):
                    i, j = ra[rn].index(arm), rA[rn].index(arm)
                    ok = all(same(e[f"{rn}/{x}"][i], E[f"{rn}/{x}"][j]) for x in AW.DET_SCALARS + ("onset", "hit"))
                    ok &= same(r[f"{rn}/zone"][det_index(me["parts"][rn], arm)], R[f"{rn}/zone"][det_index(mE["parts"][rn], arm)])
                    ok &= same(r[f"{rn}/fp"][det_index(me["parts"][rn], arm)], R[f"{rn}/fp"][det_index(mE["parts"][rn], arm)])
                    fired[arm] += int((e[f"{rn}/det_on"][i] > 0).sum())
                    n_cmp += 1
                    if not ok:
                        q4[f"{body}/{u}/{blk}/{rn}/{arm}"] = False
    checks["Q4_detectors_firing_onset_footprint"] = {"pass": not q4 and n_cmp > 0, "arm_runs_compared": n_cmp,
                                                     "lineage_cases_fired": fired, "lineage_cases": n_cmp * k,
                                                     "mismatched": list(q4)[:10]}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, u in D.tasks():
        for blk in blocks:
            e, raw = shard(body, u, blk), rawf(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            for rn in D.RUNNAMES:
                arms = ra[rn]
                jv, jm = arms.index("vote"), arms.index("vms")
                on = e[f"{rn}/det_on"][jm]
                okc = True
                for c in range(k):
                    first = on[c] if on[c] > 0 else D.WINDOW + 1
                    before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                    ntb = int((first - 1) // D.TRACE)
                    okc &= all(np.array_equal(e[f"{rn}/{q}"][before, jm, c], e[f"{rn}/{q}"][before, jv, c]) for q in EP)
                    okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, jm, c], e[f"{rn}/trace"][:ntb, jv, c]))
                    if on[c] < 0:
                        okc &= all(np.array_equal(raw[f"{rn}/{x}"][jm, c], raw[f"{rn}/{x}"][jv, c]) for x in ("V", "r", "H", "W"))
                        okc &= all(np.array_equal(raw[f"{rn}/{x}"][rb_index(pa[rn], 'vms'), c], raw[f"{rn}/{x}"][rb_index(pa[rn], 'vote'), c])
                                   for x in ("rB", "HB", "WB"))
                items[f"{body}/{u}/{blk}/{rn}: vms = the vote before its onset"] = bool(okc)
                for arm in (q for q in arms if q in ("det", "vms")):
                    o = e[f"{rn}/det_on"][arms.index(arm)]
                    want = sum(min(A3.SIG["duration"], D.WINDOW + 1 - int(x)) for x in o if x > 0)
                    items[f"{body}/{u}/{blk}/{rn}: {arm} on min(1,000, 8,001 - onset)"] = meta["signal_updates"][rn][arm] == want
                if rn.startswith("change@"):
                    items[f"{body}/{u}/{blk}/{rn}: u(new) + u(old) = 1"] = bool((e[f"{rn}/r_in"] + e[f"{rn}/r_in_old"] == 1.0).all())
            j0 = ra["none@0"].index("vote")
            for other in ("cue@0", "change@0"):
                j1 = ra[other].index("vote")
                ok = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"{other}/{x}"][j1]) for x in ("V", "r", "H", "W"))
                ok &= all(np.array_equal(raw[f"none@0/{x}"][rb_index(pa["none@0"], "vote")], raw[f"{other}/{x}"][rb_index(pa[other], "vote")])
                          for x in ("rB", "HB", "WB"))
                if other == "cue@0":
                    ok &= all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in EP)
                else:
                    ok &= bool(np.array_equal(e["none@0/r_in"][:, j0], e[f"{other}/r_in_old"][:, j1]))
                items[f"{body}/{u}/{blk}/vote: none@0 = {other}"] = bool(ok)
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "n_items": len(items),
                                  "failed": [x for x, v in items.items() if not v][:10]}

    bad = []
    for body, u in D.tasks():
        pattern, theta = A3.parse_unit(u)
        for blk in blocks:
            raw, e = rawf(body, u, blk), shard(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, D.PURPOSE["debug"])
            for run in D.RUNS:
                rn = D.run_name(*run)
                na = len(ra[rn])
                ev = A1S.event(run[0], run[5], run[1], cases, V0, ema0, R0, T, D.TAG)
                m, tgt, fp = ev["m"], ev["target"], B2S.footprint(ev["m"], A3.SIG["d"])
                tile = lambda x: np.tile(x, (na, 1, 1))
                rf = raw[f"{rn}/r"].reshape(na * k, D.SIDE, D.SIDE)
                Vf = raw[f"{rn}/V"].reshape(na * k, D.SIDE, D.SIDE)
                post = tile(ev["r"] > 0)
                got = {"r_in": L5S.inside(rf, tile(tgt), tile(m)), "r_all": S.sign(rf, tile(tgt)),
                       "r_fp": L5S.inside(rf, tile(tgt), tile(fp)), "r_out": L5S.inside(rf, tile(tgt), tile(~fp)),
                       "v_in": L5S.inside(Vf, tile(tgt), tile(m)), "v_all": S.sign(Vf, tile(tgt)),
                       "r_dose": ((rf > 0) != post).mean((-2, -1)),
                       "r_dose_in": (((rf > 0) != post) & tile(m)).sum((-2, -1)) / tile(m).sum((-2, -1))}
                if ev["old"] is not None:
                    got["r_in_old"] = L5S.inside(rf, tile(ev["old"]), tile(m))
                for x, v in got.items():
                    if not np.array_equal(v.reshape(na, k), e[f"{rn}/{x}"][-1]):
                        bad.append(f"{body}/{u}/{blk}/{rn}/{x}")
                for L in LSIZES:
                    if f"{rn}/r_in_L{L}" in e:
                        mL = tile(B1S.patch(cases, L, D.TAG))
                        if not np.array_equal(L5S.inside(rf, tile(tgt), mL).reshape(na, k), e[f"{rn}/r_in_L{L}"]):
                            bad.append(f"{body}/{u}/{blk}/{rn}/r_in_L{L}")
                for arm in (q for q in ra[rn] if q in ("det", "vms")):
                    i, z = ra[rn].index(arm), det_index(pa[rn], arm)
                    zone, fpd, on = raw[f"{rn}/zone"][z], raw[f"{rn}/fp"][z], e[f"{rn}/det_on"][i]
                    okf = np.array_equal(B2S.footprint(zone, A3.SIG["d"]) & (on > 0)[:, None, None], fpd)
                    okf &= np.array_equal(zone.sum((-2, -1)).astype(float), e[f"{rn}/det_zone"][i])
                    okf &= np.array_equal(fpd.sum((-2, -1)).astype(float), e[f"{rn}/det_fp"][i])
                    okf &= np.array_equal((fpd & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_fp_in"][i])
                    okf &= np.array_equal((zone & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_zone_in"][i])
                    bad += [] if okf else [f"{body}/{u}/{blk}/{rn}/{arm} footprint"]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    q7 = {}
    fz = json.loads((LANE / "ar003" / "frozen" / "design.json").read_text())
    q7["ar003_frozen_design_unchanged"] = fz["digest"] == A3.digest() and fz["sources"] == A3.sources(LANE)
    full = {A3.run_name(*x): x for x in A3.RUNS}
    q7["every_reduced_run_is_ar003s_run_with_a_subset_of_its_arms"] = all(
        D.run_name(*x) in full and set(x[2]) <= set(full[D.run_name(*x)][2]) and set(x[3]) <= set(full[D.run_name(*x)][3])
        and set(x[4]) <= set(full[D.run_name(*x)][4]) and x[:2] == full[D.run_name(*x)][:2] and x[5] == full[D.run_name(*x)][5]
        for x in D.RUNS)
    q7["arms_are_vote_det_vms_only_and_no_misread_run"] = (
        set(a_ for x in D.RUNS for a_ in D.arms_of(x)) == {"vote", "det", "vms"} and all(x[1] == 0.0 for x in D.RUNS))
    q7["runs_are_those_c1_c3_need"] = (
        set(D.RUNNAMES) == {A3.run_name(s, 0.0, size=L) for s in ("none", "body", "memory", "correlated", "shared", "cue", "change")
                            for L in (4,)} | {A3.run_name(s, 0.0, size=L) for s in ("memory", "correlated", "body", "shared") for L in (2, 8)}
        and all("vote" in D.arms_of(x) and "vms" in D.arms_of(x) for x in D.RUNS)
        and {D.run_name(*x) for x in D.RUNS if "det" in D.arms_of(x)} == {"none@0", "cue@0"} | {A3.run_name(s, 0.0, size=8)
                                                                                                for s in ("memory", "correlated", "body", "shared")})
    q7["det_and_vms_detectors_are_ar003s_frozen"] = (
        D.DETECTORS["det"] == A3.DETECTORS["det"] and D.VD_DETECTORS["vms"] == A3.VD_DETECTORS["vms"] == A3.DET_STAR
        and json.loads(json.dumps(A3.DET_STAR, default=list)) == fz["design"]["vd_detectors"]["vms"]
        and json.loads(json.dumps(A3.DETECTORS["det"], default=list)) == fz["design"]["detectors"]["det"])
    q7["tag_best_controller_harm_weights"] = (
        D.TAG == A3.TAG == "mse-ar003" and D.BEST == A3.BEST == "vote" and D.CONTROLLER == A3.CONTROLLER == "vms"
        and D.HARM == {"cue@0": 0.01, "none@0": 0.002} and all(abs(w - 1 / 8) < 1e-15 for w in D.WEIGHTS.values())
        and D.SIZES == (2, 4, 8) and all(abs(w - 1 / 3) < 1e-15 for w in D.SIZE_WEIGHTS.values()))
    dev = AZ.load(AR003_RUNS / "development")
    xs = {"c1": AZ.U_mix(dev, "vms") - AZ.U_mix(dev, "vote"), "c2": AZ.U_L(dev, "vms", 8) - AZ.U_L(dev, "det", 8),
          "sham_cue": AZ.sham(dev, "cue@0", "vms"), "sham_none": AZ.sham(dev, "none@0", "vms")}
    sd = lambda x: (float(x.mean(1).std(ddof=1)), float(x.ravel().std(ddof=1) / math.sqrt(x.shape[-1])))
    rec = {}
    for key, x in xs.items():
        sb, sc = sd(x)
        rec[key] = (round(float(x.mean()), 6) == D.DEV[key]["value"] and round(max(sb, sc), 6) == D.DEV[key]["sd"]
                    and round(sb, 6) == D.DEV[key]["sd_block"] and round(sc, 6) == D.DEV[key]["sd_case8"])

    def nmin(v, s):
        return next(n for n in range(2, 500) if stats.t.ppf(0.975, n - 1) * s / math.sqrt(n) <= v / 3)
    rule = {key: (nmin(D.DEV[key]["value"], D.DEV[key]["sd"]), nmin(D.DEV[key]["value"], D.DEV[key]["sd"] * D.SD_UPPER))
            for key in ("c1", "c2")}
    q7["development_values_recompute"] = all(rec.values()) and len(AZ.blocks_of(dev)) == 16
    q7["the_rules_block_counts_recompute"] = (all(rule[key] == (D.N_RULE[key], D.N_UPPER[key]) for key in rule)
                                              and abs(math.sqrt(15 / stats.chi2.ppf(0.025, 15)) - D.SD_UPPER) < 5e-5)
    blocks_c = D.IDENTITIES["confirmation"]
    q7["confirmation_blocks_in_range_and_clear"] = (
        blocks_c == tuple(range(920365, 920381)) and len(set(blocks_c)) == 16
        and all(b in RANGES["confirmation"] for b in blocks_c + D.RESERVE) and min(blocks_c) > 920147
        and not set(blocks_c) & set(D.RESERVE) and D.RESERVE == tuple(range(920381, 920387)))
    drawn = [str(f) for rr in (AR003_RUNS, AR003C_RUNS) for f in rr.rglob("*")
             if f.is_file() and f.parent.name not in ("tools",) and f.stem.isdigit() and int(f.stem) >= 920000]
    q7["no_block_from_920000_drawn"] = not drawn
    checks["Q7_declaration_and_boundary"] = {"pass": all(q7.values()), "items": q7, "development_recompute": rec,
                                             "rule_counts": rule, "drawn": drawn[:5]}

    q8 = {}
    pattern, theta = A3.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blocks[1], D.PURPOSE["debug"])
    blk_ = lambda o, i, xs_: [o[x][i * k:(i + 1) * k] for x in xs_]
    VX = ("V", "r", "H", "W", "rB", "HB", "WB", "zone", "fp")
    DX = ("V", "r", "H", "W", "zone", "fp")
    for s_, L in (("memory", 8), ("cue", 4)):
        o1 = S3.run_vd("li4", s_, 0.0, ("vms",), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L)
        o2 = S3.run_vd("li4", s_, 0.0, ("vdial", "vote", "vms"), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L)
        o3 = S3.run_vd("li4", s_, 0.0, ("vms", "vms"), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L)
        q8[f"{s_}@L{L}: vms alone = vms beside vdial and the vote"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0, VX), blk_(o2, 2, VX)))
        q8[f"{s_}@L{L}: vms listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o3, 0, VX), blk_(o3, 1, VX)))
        d1 = A2S.run_det("li4", s_, 0.0, ("det",), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L,
                         detectors=A3.DETECTORS)
        d2 = A2S.run_det("li4", s_, 0.0, ("det", "ms"), cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600, size=L,
                         detectors=A3.DETECTORS)
        q8[f"{s_}@L{L}: det alone = det beside ms"] = all(np.array_equal(x, y) for x, y in zip(blk_(d1, 0, DX), blk_(d2, 0, DX)))
    checks["Q8_pairing"] = {"pass": all(q8.values()), "items": q8}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, u_ = key.split("/")[:2]
        walls.setdefault((b_, u_), []).append((t["cpu_s"], t["wall_s"]))
    n_c = len(D.IDENTITIES["confirmation"])
    cpu = sum(np.mean([c for c, _ in v]) * n_c for v in walls.values())
    wall_h = (cpu / WORKERS * 1.15 + max(w for v in walls.values() for _, w in v)) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    rss = manifest["worker_maxrss_mb_peak"]
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 20 and wall_h <= 3 and rss <= 2048 and rss * 2 ** 20 * WORKERS <= 0.8 * avail
                                           and per_task * n_c * len(D.tasks()) <= 0.8 * free),
                              "cpu_s_per_task": round(cpu / (n_c * len(D.tasks())), 1), "forecast_cpu_h": round(cpu / 3600, 2),
                              "forecast_wall_h_12": round(float(wall_h), 2), "tasks": n_c * len(D.tasks()),
                              "worker_rss_mb": rss, "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar003c.{mod}", "--root", str(root), "--out", str(dst)], cwd=LANE,
                            capture_output=True, text=True, env=env)
             for mod, dst in (("analyze", out), ("predict", out / "confirmation.json"), ("tables", out / "TABLES.md"))]
    files = [out / "summary.json", out / "confirmation.json", out / "TABLES.md"]
    got = json.loads(files[1].read_text()) if files[1].exists() else {}
    crit = got.get("criteria", {})
    computed = (sorted(crit) == ["C1", "C2", "C3"] and "lower_bound" in crit["C1"] and "lower_bound" in crit["C2"]
                and "upper_bound_cue" in crit["C3"] and "upper_bound_none" in crit["C3"] and "verdict" in got)
    sizes = {q.name: q.stat().st_size for q in files if q.exists()}
    git_files = [f for f in list((LANE / "ar003c").rglob("*")) + [LANE / "tests" / "test_ar003c.py", LANE / "REGISTRATION_AR003C.md"]
                 if f.is_file()]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in files) and computed
                                    and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big,
                                    "criteria_computed": computed, "verdict_read": False}

    failed = [x for x, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "ar003_digest": A3.digest(), "root": str(root), "blocks": blocks, "tag": D.TAG,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
