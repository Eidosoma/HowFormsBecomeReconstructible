"""Qualification of AR006C on engineering shards; criteria fixed in advance.

python -m ar006c.checks --root ROOT --cpus LIST [--debug]
  (with --debug, on the debug stage's blocks 900948 and 900929, ROOT/debug_qualification_receipt.json; otherwise on the
  preflight blocks 900969 and 900989, ar006c/frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every reduced run's endpoints at its declared shape (reads x arms x 8
    cases; r_in_L2 and r_in_L8 exactly in none@0 and cue@0), its trace, scalars, detector scalars, n_anc and n_mis, and
    its raw states (V, r, H, W per arm, the detectors' zones and footprints, the second records, V0, R0 and T); every
    value finite; nothing else
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  the bridge: every task of the debug root (AR006C's reduced task on 900948 and 900929) equals AR006's full development
    task's corresponding branches bit for bit, against AR006's own outputs there (its debug root on 900948, its preflight
    root on 900929; tag mse-ar006, AR006's frozen digest): every endpoint at every read, the trace, every scalar and
    detector scalar, n_anc and n_mis, the size-free scorings, the final V, r, H, W, the detectors' zones and footprints,
    the second records, the acquisition (V0, R0, T) and every arm's signal updates; and one bridge task run in-process
    under the sources in force (on the debug stage, Q2's rerun) equals AR006's outputs the same way
Q4  the vote-default identity: in none@0 and cue@0, vms and vtol equal the vote at every read and trace point before their
    onsets, and throughout (final states and both second records included) where they never fire, per case; in memory@1
    and correlated@0, which carry no vote, vms and vtol equal each other before the earlier of their onsets, and
    throughout where neither fires
Q5  aliases: the vote, which never reads the cue, is bit-identical across none@0 and cue@0 (its second record included);
    every vote-default arm is on for exactly min(1,000, 8,001 - onset) updates where it fired and never where it did not
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states and the events, and the size-free
    scorings from the final record, equal the saved ones; each detector's footprint is its saved zone dilated by 2, and
    its scalars follow from them
Q7  the declaration and the boundary: AR006's frozen design and sources are unchanged (digest 963f47e2cf71); every
    reduced run is AR006's registered run with a subset of its arms, the arms are the vote, vms and vtol only (vpool and
    vguard left out); vms and vtol are AR006's frozen detectors, and the tag, BEST and the controller AR006's; the task
    is AR006's routed task; the thresholds are AR006's registered ones (K3 (a) 0.04, K5 (a) -0.005, K2 (a)'s 0.002 for
    the no-event part, and the confirmed 0.01 of AR006's dropped K1); the development values recompute from AR006's
    development shards; the 24 confirmation blocks are 920387-920410 in RANGES['confirmation'], within the confirmations'
    920000-924999, clear of 920000-920147 (AR001C, AR002C) and 920365-920386 (AR003C and its reserve), with the reserve
    920411-920416 beside them and the halves the first and the last twelve; the debug and preflight blocks are AR006's
    engineering blocks; mse.assay.enrol takes each stage's blocks under its purpose and refuses the confirmation blocks
    under the development purpose; no shard, raw state or completion record of any of the 30 blocks exists in any run
    root
Q8  pairing: vtol run alone equals vtol beside vms; vms run alone equals vms beside vtol; an arm listed twice gives
    bit-identical branches
Q9  resources: the confirmation (24 blocks x 8 pairs) forecast within 20 CPU-hours and 3 h of wall on 12 workers, worker
    memory within 2 GB, memory and disk headroom
Q10 reader dry run: ar006c.analyze, ar006c.predict and ar006c.tables complete on the shards; K1, K3 (a) and K5 (a) are
    computed with their bounds and a verdict is formed (not read); every output and every AR006C git file is 256 KB or
    less
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from ar001 import sim as A1S  # noqa: E402
from ar003 import design as A3  # noqa: E402
from ar003 import worker as AW  # noqa: E402
from ar006 import design as A6  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from ar006 import worker as W6  # noqa: E402
from ar006c import analyze as AN  # noqa: E402
from ar006c import design as D  # noqa: E402
from ar006c import worker as W  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import sim as DS  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse import assay  # noqa: E402

FROZEN = LANE / "ar006c" / "frozen"
RUN_ROOTS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
DEBUG_ROOT = RUN_ROOTS / "ar006c" / "debug"
WORKERS = 12
EPS = AW.ENDS + ("trace",)
SCAL = AW.SCALARS + AW.DET_SCALARS
LSIZES = tuple(L for L in A3.SIZES if L != A3.SIZE)
VD = ("vms", "vtol")
BRIDGED = ("vote", "vms", "vtol")
EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")


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


def bridge_one(root, ref, body, unit, block):
    """Every branch of one reduced task against AR006's full task's outputs: (mismatches, arrays, slices, runs)."""
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
            bad.append(f"{rn}: not in AR006's task")
            continue
        n_runs += 1
        arms = list(ra[rn])
        bad += [f"{rn}/{a}: not in AR006's run" for a in arms if a not in rA[rn] or a not in BRIDGED]
        arms = [a for a in arms if a in rA[rn]]
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
    blocks, purpose = D.stage_blocks(stage), D.PURPOSE[stage]
    RUNS = {D.run_name(*x): x for x in D.RUNS}
    receipt_path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
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
    l4 = {D.run_name(*x) for x in D.RUNS if x[0] in A3.SIZE_FREE and x[5] == D.SIZE}
    checks["Q1_complete_finite"] = {"pass": not missing and l4 == {"none@0", "cue@0"}, "missing": missing[:10],
                                    "tasks": len(manifest["tasks"]), "size_free_runs": sorted(l4)}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    sm = {}
    body0, u0 = D.tasks()[0]
    W.run_task(body0, u0, blocks[0], purpose, str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body0 / u0 / f"{blocks[0]}.npz"), npz(serial / kind / body0 / u0 / f"{blocks[0]}.npz")
        sm[f"{kind}/{body0}/{u0}/{blocks[0]}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[q], y[q]) for q in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(sm.values()), "tasks": sm}

    mism, n_t, n_arr, n_sl, n_runs = {}, 0, 0, 0, 0
    for body, u in D.tasks():
        for blk in D.DEBUG_BLOCKS:
            ref = RUN_ROOTS / D.REFERENCE_ROOTS[blk]
            if not (DEBUG_ROOT / "shards" / body / u / f"{blk}.npz").exists():
                mism[f"{body}/{u}/{blk}"] = ["missing from the debug root"]
                continue
            bad, na_, ns_, nr_ = bridge_one(DEBUG_ROOT, ref, body, u, blk)
            n_t, n_arr, n_sl, n_runs = n_t + 1, n_arr + na_, n_sl + ns_, n_runs + nr_
            if bad:
                mism[f"{body}/{u}/{blk}"] = bad[:10]
    if stage == "debug":
        fresh = serial
    else:
        fresh = root / "bridge_check"
        shutil.rmtree(fresh, ignore_errors=True)
        W.run_task(body0, u0, D.DEBUG_BLOCKS[0], D.PURPOSE["debug"], str(fresh))
    fb, _, _, fr = bridge_one(fresh, RUN_ROOTS / D.REFERENCE_ROOTS[D.DEBUG_BLOCKS[0]], body0, u0, D.DEBUG_BLOCKS[0])
    ref_digests = {str(b): json.loads((RUN_ROOTS / D.REFERENCE_ROOTS[b] / "manifest.json").read_text())["design_digest"]
                   for b in D.DEBUG_BLOCKS}
    checks["Q3_bridge_bit_for_bit"] = {"pass": not mism and not fb and n_t == len(D.tasks()) * len(D.DEBUG_BLOCKS)
                                       and n_runs == n_t * len(D.RUNS) and fr == len(D.RUNS)
                                       and all(v == A6.digest() for v in ref_digests.values()),
                                       "tasks_compared": n_t, "runs_compared": n_runs, "arrays_compared": n_arr,
                                       "arm_slices_compared": n_sl, "fresh_task": f"{body0}/{u0}/{D.DEBUG_BLOCKS[0]}",
                                       "fresh_mismatches": fb[:10], "reference_digests": ref_digests,
                                       "reference": "AR006's full development task on 900948 (its debug root) and 900929 "
                                                    "(its preflight root), tag mse-ar006, AR006's frozen digest",
                                       "mismatched": mism}

    items = {}
    for body, u in D.tasks():
        for blk in blocks:
            e, raw = shard(body, u, blk), rawf(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            for rn in RUNS:
                if "vote" in ra[rn]:
                    pairs_ = [(arm, "vote") for arm in VD]
                else:
                    pairs_ = [("vtol", "vms")]
                for arm, refa in pairs_:
                    jm, jv = ra[rn].index(arm), ra[rn].index(refa)
                    on = e[f"{rn}/det_on"][jm]
                    on2 = e[f"{rn}/det_on"][jv]
                    okc = True
                    for c in range(k):
                        fa = on[c] if on[c] > 0 else D.WINDOW + 1
                        fb_ = on2[c] if (refa != "vote" and on2[c] > 0) else D.WINDOW + 1
                        first = min(fa, fb_)
                        before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                        ntb = int((first - 1) // D.TRACE)
                        okc &= all(np.array_equal(e[f"{rn}/{q}"][before, jm, c], e[f"{rn}/{q}"][before, jv, c]) for q in EP)
                        okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, jm, c], e[f"{rn}/trace"][:ntb, jv, c]))
                        if first > D.WINDOW:
                            okc &= all(np.array_equal(raw[f"{rn}/{x}"][jm, c], raw[f"{rn}/{x}"][jv, c]) for x in ("V", "r", "H", "W"))
                            okc &= all(np.array_equal(raw[f"{rn}/{x}"][rb_index(pa[rn], arm), c], raw[f"{rn}/{x}"][rb_index(pa[rn], refa), c])
                                       for x in ("rB", "HB", "WB"))
                    items[f"{body}/{u}/{blk}/{rn}/{arm} = {refa} before the onset"] = bool(okc)
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
    checks["Q5_aliases_exact"] = {"pass": all(q5.values()), "n_items": len(q5), "failed": [x for x, v in q5.items() if not v][:10]}

    bad = []
    for body, u in D.tasks():
        pattern, theta = A6.parse_unit(u)
        for blk in blocks:
            raw, e = rawf(body, u, blk), shard(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra, pa = runs_of(meta), meta["parts"]
            cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, purpose)
            for run in D.RUNS:
                rn = D.run_name(*run)
                na = len(ra[rn])
                ev = A1S.event(run[0], run[5], run[1], cases, V0, ema0, R0, T, D.TAG)
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
                        mL = tile(B1S.patch(cases, L, D.TAG))
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

    q7 = {}
    fz6 = json.loads((LANE / "ar006" / "frozen" / "design.json").read_text())
    pr6 = json.loads((LANE / "ar006" / "frozen" / "predictions.json").read_text())
    q7["ar006_frozen_design_and_sources_unchanged"] = (fz6["digest"] == A6.digest() and fz6["digest"].startswith("963f47e2cf71")
                                                      and fz6["sources"] == A6.sources(LANE))
    full = {A6.run_name(*x): x for x in A6.RUNS}
    q7["every_run_is_ar006s_registered_run_with_a_subset_of_its_arms"] = all(
        D.run_name(*x) in full and x[:2] == full[D.run_name(*x)][:2] and x[5] == full[D.run_name(*x)][5]
        and all(set(x[i]) <= set(full[D.run_name(*x)][i]) for i in (2, 3, 4)) for x in D.RUNS)
    arms = [q for x in D.RUNS for q in D.arms_of(x)]
    q7["the_arms_are_the_vote_vms_and_vtol_only"] = (set(arms) == {"vote", "vms", "vtol"} and D.ARM_RUNS == 12 == len(arms)
                                                    and set(full) - set(D.RUNNAMES) == {"memory@0", "memory@0-L8", "none@1", "correlated@1"})
    q7["vms_and_vtol_are_ar006s_frozen_detectors"] = all(
        D.VD_DETECTORS[x] == A6.VD_DETECTORS[x] and json.loads(json.dumps(D.VD_DETECTORS[x])) == fz6["design"]["vd_detectors"][x]
        for x in VD) and set(D.VD_DETECTORS) == set(VD)
    q7["the_tag_best_and_controller_are_ar006s"] = (D.TAG == A6.TAG == "mse-ar006" and D.BEST == A6.BEST == "vote"
                                                   and D.CONTROLLER == A6.CONTROLLER == "vtol")
    q7["the_task_is_ar006s_routed_task"] = (W.W6.task is W6.task and W6.task.__globals__["one"] is W6.one
                                           and W6.one.__globals__["run_vt"] is S6.run_vt)
    dropped = {p["key"]: p for p in pr6["dropped"]}
    q7["the_thresholds_are_ar006s_registered_ones"] = (
        D.THRESHOLDS["k3a"] == ("ge", pr6["thresholds"]["K3a"]) == ("ge", 0.04)
        and D.THRESHOLDS["k5a"] == ("ge", pr6["thresholds"]["K5a"]) == ("ge", -0.005)
        and D.THRESHOLDS["k1_none"] == ("le", pr6["thresholds"]["K2a"]) == ("le", 0.002)
        and D.THRESHOLDS["k1_cue"] == ("le", dropped["K1"]["threshold"]) == ("le", 0.01))
    Zd = AN.load(RUN_ROOTS / "ar006" / "development")
    Xd = dict(AN.contrasts(Zd), vtol_less_vms_cue=AN.vtol_less_vms(Zd))
    dev_ok = AN.blocks_of(Zd) == list(A6.DEVELOPMENT_BLOCKS) and len(AN.blocks_of(Zd)) == D.DEV_BLOCKS
    for key, x in Xd.items():
        iv = AN.interval(x)
        dev_ok &= all(abs(iv[q] - D.DEV[key][q2]) <= 5e-7 for q, q2 in (("mean", "value"), ("sd", "sd"), ("sd_block", "sd_block"),
                                                                       ("sd_case8", "sd_case8")))
    q7["the_development_values_recompute_from_ar006s_development"] = bool(dev_ok)
    cb, rs = D.CONFIRMATION_BLOCKS, D.RESERVE
    q7["the_confirmation_blocks_reserve_and_halves"] = (
        cb == tuple(range(920387, 920411)) and len(cb) == 24 and rs == tuple(range(920411, 920417))
        and all(b in assay.RANGES["confirmation"] and 920000 <= b <= 924999 for b in cb + rs) and not set(cb) & set(rs)
        and not any(lo <= b <= hi for b in cb + rs for lo, hi in D.TAKEN.values())
        and D.HALVES == (cb[:12], cb[12:]))
    q7["the_debug_and_preflight_blocks_are_ar006s_engineering_blocks"] = (
        D.DEBUG_BLOCKS == (A6.DEBUG_BLOCKS[0], A6.PREFLIGHT_BLOCKS[0]) and D.PREFLIGHT_BLOCKS == A6.SPARE_ENGINEERING
        and all(b in assay.RANGES["engineering"] for b in D.DEBUG_BLOCKS + D.PREFLIGHT_BLOCKS)
        and set(D.REFERENCE_ROOTS) == set(D.DEBUG_BLOCKS))
    try:
        assay.enrol(list(cb), purpose="development")
        refused = False
    except ValueError:
        refused = True
    q7["enrol_takes_each_stage_under_its_purpose"] = (
        D.PURPOSE == {"debug": "engineering", "preflight": "engineering", "confirmation": "confirmation"}
        and len(assay.enrol(list(cb), purpose="confirmation")) == 24 * 8
        and len(assay.enrol(list(D.DEBUG_BLOCKS + D.PREFLIGHT_BLOCKS), purpose="engineering")) == 4 * 8 and refused)
    named = set(cb + rs)
    drawn = []
    for dirpath, dirnames, filenames in os.walk(RUN_ROOTS):
        for f in filenames:
            stem = f.split(".")[0]
            if stem.isdigit() and int(stem) in named:
                drawn.append(os.path.join(dirpath, f))
    q7["no_shard_raw_state_or_record_of_any_of_the_30_blocks_exists"] = not drawn
    checks["Q7_declaration_and_boundary"] = {"pass": all(q7.values()), "items": q7, "drawn": drawn[:10]}

    q8 = {}
    pattern, theta = A6.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blocks[0], purpose)
    blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W", "rB", "HB", "WB", "zone", "fp")]
    for s_, z, L in (("memory", D.S1, 8), ("cue", 0.0, 4), ("correlated", 0.0, 4)):
        run = lambda arms_: S6.run_vt("li4", s_, z, arms_, cases, V0, ema0, R0, th, T, theta, {600}, tag=D.TAG, window=600,
                                      size=L, detectors=D.VD_DETECTORS)
        o1, o2, o3, o4 = run(("vtol",)), run(("vms", "vtol")), run(("vtol", "vtol")), run(("vms",))
        q8[f"{s_}@{z:g}-L{L}: vtol alone = vtol beside vms"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o2, 1)))
        q8[f"{s_}@{z:g}-L{L}: vms alone = vms beside vtol"] = all(np.array_equal(x, y) for x, y in zip(blk_(o4, 0), blk_(o2, 0)))
        q8[f"{s_}@{z:g}-L{L}: vtol listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o3, 0), blk_(o3, 1)))
    checks["Q8_pairing"] = {"pass": all(q8.values()), "items": q8}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, u_ = key.split("/")[:2]
        walls.setdefault((b_, u_), []).append((t["cpu_s"], t["wall_s"]))
    n_c = len(D.CONFIRMATION_BLOCKS)
    cpu = sum(np.mean([c for c, _ in v]) * n_c for v in walls.values())
    wall_h = (cpu / WORKERS * 1.15 + max(w_ for v in walls.values() for _, w_ in v)) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    rss = manifest["worker_maxrss_mb_peak"]
    checks["Q9_resources"] = {"pass": bool(cpu / 3600 <= 20 and wall_h <= 3 and rss <= 2048 and rss * 2 ** 20 * WORKERS <= 0.8 * avail
                                           and per_task * n_c * len(D.tasks()) <= 0.8 * free),
                              "cpu_s_per_task": round(cpu / (n_c * len(D.tasks())), 1), "forecast_cpu_h": round(cpu / 3600, 2),
                              "forecast_wall_h_12": round(float(wall_h), 2), "worker_rss_mb": rss, "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"ar006c.{mod}"] + args_, cwd=LANE, capture_output=True, text=True, env=env)
             for mod, args_ in (("analyze", ["--root", str(root), "--out", str(out)]),
                                ("predict", ["--root", str(root), "--out", str(out / "confirmation.json")]),
                                ("tables", ["--root", str(root), "--out", str(out / "TABLES.md")]))]
    expected = [out / f for f in ("summary.json", "confirmation.json", "TABLES.md")]
    got = json.loads((out / "confirmation.json").read_text()) if (out / "confirmation.json").exists() else {}
    crit = got.get("criteria", {})
    computed = (sorted(crit) == ["K1", "K3a", "K5a"] and all(np.isfinite(crit["K1"][x]) for x in ("upper_bound_cue", "upper_bound_none"))
                and all(np.isfinite(crit[x]["lower_bound"]) for x in ("K3a", "K5a")) and "verdict" in got)
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    git_files = [f for f in list((LANE / "ar006c").rglob("*")) + list((LANE / "probes").rglob("*p57e*"))
                 + [LANE / "tests" / "test_ar006c.py", LANE / "REGISTRATION_AR006C.md"] if f.is_file()]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in expected) and computed
                                    and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridge_bit_for_bit", "Q4_vote_default_identity",
             "Q5_aliases_exact", "Q6_reanalysis", "Q7_declaration_and_boundary", "Q8_pairing", "Q9_resources",
             "Q10_reader_dry_run"]
    checks = {x: checks[x] for x in order}
    failed = [x for x, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "ar006_digest": A6.digest(), "root": str(root), "stage": stage, "blocks": blocks, "tag": D.TAG,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
