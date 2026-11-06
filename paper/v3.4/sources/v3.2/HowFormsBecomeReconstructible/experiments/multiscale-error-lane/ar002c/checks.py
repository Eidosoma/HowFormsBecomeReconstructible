"""Qualification of AR002C on its debug run (AR002's engineering blocks 900356-900359); criteria fixed in advance.

python -m ar002c.checks --root DEBUG_ROOT --cpus LIST [--receipt-to-frozen]
    (writes ROOT/debug_qualification_receipt.json; with --receipt-to-frozen, ar002c/frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every reduced run's endpoints at its declared shape (reads x 4 arms x 8
    cases; r_in_old exactly in change@0), its trace, scalars, detector scalars, n_anc and n_mis, and its raw states (V,
    r, H, W for the 4 arms, det's zone and footprint, the vote's second record); every value finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  the bridge: on every debug task, every reduced branch equals AR002's full task's corresponding branch bit for bit,
    against AR002's own preflight (900356-900357) and debug (900358-900359) outputs, drawn under the frozen digest:
    every endpoint at every read, the trace, every scalar and detector scalar, n_anc and n_mis, the final V, r, H, W,
    det's zone and footprint, the vote's second record (rB, HB, WB), the acquisition (V0, R0, T) and each arm's signal
    updates in the meta
Q4  det's firing, onset and footprint: in every run and task, det's onset, zone, footprint, their patch coverage, its
    window count and channel, BE001's onset fraction and hit, and the raw zone and footprint equal AR002's
Q5  aliases: (a) det equals rest at every read and trace point before its onset, and throughout (final states included)
    where it never fires, per case; (b) u(new) + u(old) = 1 exactly for every branch of change@0; (c) the dial is on for
    exactly 1,000 updates in every case and its onset is recorded; det is on for exactly min(1,000, 8,001 - onset)
    updates where it fired and never where it did not; (d) the vote, which never reads the cue, is bit-identical across
    none@0, cue@0 and change@0
Q6  reanalysis: the endpoints at the last read recomputed from the saved final states, the events and the footprints
    equal the saved ones; det's footprint is its saved zone dilated by 2, and its scalars follow from them
Q7  the declaration and the boundary: AR002's frozen design and sources are unchanged; AR002C's runs, arms, detector,
    tag, BEST, point, harm bounds and weights are those REGISTRATION_AR002.md declared; the development values behind
    the targets recompute from AR002's development shards; the 20 confirmation blocks lie in mse.assay.RANGES
    ['confirmation'], from 920128, clear of AR001's 920000-920127; no shard, raw state or completion record of any
    block from 920000 on exists in AR002's or AR002C's run roots
Q8  pairing: det run alone equals det run beside det-v and det-ms, and det listed twice gives bit-identical branches
Q9  resources: the confirmation (20 blocks x 8 pairs) forecast within 20 CPU-hours and 3 h of wall on 12 workers,
    worker memory within 2 GB, memory and disk headroom
Q10 reader dry run: ar002c.analyze, ar002c.predict and ar002c.tables complete on the debug shards; C1, C2 and C3 are
    computed with their bounds and a verdict is formed (not read); every output and every AR002C git file is 256 KB
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

from ar001 import design as A1  # noqa: E402
from ar002 import analyze as AZ  # noqa: E402
from ar002 import design as A2  # noqa: E402
from ar002 import predict as AP  # noqa: E402
from ar002 import sim as S2  # noqa: E402
from ar002 import worker as AW  # noqa: E402
from ar002c import design as D  # noqa: E402
from ar002c import worker as W  # noqa: E402
from be002 import sim as B2S  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.assay import RANGES  # noqa: E402

FROZEN = LANE / "ar002c" / "frozen"
RUN_ROOTS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
AR002_RUNS = RUN_ROOTS / "ar002"
AR002C_RUNS = RUN_ROOTS / "ar002c"
WORKERS = 12
EPS = AW.ENDS + ("trace",)                                     # (reads or points, arms, cases): the arm axis is 1
SCAL = AW.SCALARS + AW.DET_SCALARS                             # (arms, cases): the arm axis is 0


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def meta_of(path):
    return json.loads(str(np.load(path)["__meta__"]))


def runs_of(meta):
    return {r: list(a) for r, a in meta["runs"]}


def same(x, y):
    return bool(x.dtype == y.dtype and x.shape == y.shape and np.array_equal(x, y))


def bridge_one(root, body, unit, block):
    """Every reduced branch of one task against AR002's full task's, bit for bit: (mismatches, arrays, arm slices)."""
    ref = AR002_RUNS / D.BRIDGE_ROOTS[block]
    rel = Path(body) / unit / f"{block}.npz"
    e, r = npz(root / "shards" / rel), npz(root / "raw" / rel)
    E, R = npz(ref / "shards" / rel), npz(ref / "raw" / rel)
    me, mE = meta_of(root / "shards" / rel), meta_of(ref / "shards" / rel)
    ra, rA = runs_of(me), runs_of(mE)
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
        for sc in SCAL:
            key = f"{rn}/{sc}"
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
        dets, dfull = [a for a in arms if a in A2.DET_ARMS], [a for a in full if a in A2.DET_ARMS]
        for x in ("zone", "fp"):
            n_arr += 1
            for i, a in enumerate(dets):
                n_sl += 1
                bad += [] if same(r[f"{rn}/{x}"][i], R[f"{rn}/{x}"][dfull.index(a)]) else [f"{rn}/{x}/{a}"]
        for x in ("rB", "HB", "WB"):
            n_arr += 1
            bad += [] if same(r[f"{rn}/{x}"], R[f"{rn}/{x}"]) else [f"{rn}/{x}"]
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
    na, k, ntr = len(D.ARMS), D.NCASE, D.WINDOW // D.TRACE

    missing = []
    for body, u in D.tasks():
        for blk in blocks:
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e, r = npz(path), rawf(body, u, blk)
            bad = [x for x, v in list(e.items()) + list(r.items()) if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all()]
            for situation, sigma, a1, det, size in D.RUNS:
                rn = D.run_name(situation, sigma)
                for x in AW.ENDS:
                    want = (len(D.READS), na, k) if (x != "r_in_old" or situation == "change") else None
                    got = e[f"{rn}/{x}"].shape if f"{rn}/{x}" in e else None
                    bad += [] if got == want else [f"{rn}/{x}"]
                bad += [f"{rn}/{x}" for x in SCAL if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, k)]
                bad += [f"{rn}/{x}" for x in ("n_anc", "n_mis") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (k,)]
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, k) else []
                bad += [f"{rn}/{x}" for x in ("V", "r", "H", "W") if r.get(f"{rn}/{x}", np.zeros(0)).shape != (na, k, D.SIDE, D.SIDE)]
                bad += [f"{rn}/{x}" for x in ("zone", "fp") if r.get(f"{rn}/{x}", np.zeros(0)).shape != (len(det), k, D.SIDE, D.SIDE)]
                bad += [f"{rn}/{x}" for x in ("rB", "HB", "WB") if r.get(f"{rn}/{x}", np.zeros(0)).shape != (k, D.SIDE, D.SIDE)]
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
        for blk in blocks:
            bad, na_, ns_ = bridge_one(root, body, u, blk)
            n_t, n_arr, n_sl = n_t + 1, n_arr + na_, n_sl + ns_
            if bad:
                mism[f"{body}/{u}/{blk}"] = bad[:10]
    checks["Q3_bridge_bit_for_bit"] = {"pass": not mism and n_t == len(D.tasks()) * len(blocks), "tasks_compared": n_t,
                                       "arrays_compared": n_arr, "arm_slices_compared": n_sl,
                                       "branches_compared": n_t * len(D.RUNS) * na,
                                       "reference": "AR002's preflight (900356-900357) and debug (900358-900359) outputs",
                                       "mismatched": mism}

    q4, fired, n_cmp = {}, 0, 0
    for body, u in D.tasks():
        for blk in blocks:
            ref = AR002_RUNS / D.BRIDGE_ROOTS[blk]
            rel = Path(body) / u / f"{blk}.npz"
            e, E, r, R = shard(body, u, blk), npz(ref / "shards" / rel), rawf(body, u, blk), npz(ref / "raw" / rel)
            ra, rA = runs_of(meta_of(root / "shards" / rel)), runs_of(meta_of(ref / "shards" / rel))
            for rn in D.RUNNAMES:
                i, j = ra[rn].index("det"), rA[rn].index("det")
                ok = all(same(e[f"{rn}/{x}"][i], E[f"{rn}/{x}"][j]) for x in AW.DET_SCALARS + ("onset", "hit"))
                dj = [x for x in rA[rn] if x in A2.DET_ARMS].index("det")
                ok &= same(r[f"{rn}/zone"][0], R[f"{rn}/zone"][dj]) and same(r[f"{rn}/fp"][0], R[f"{rn}/fp"][dj])
                fired += int((e[f"{rn}/det_on"][i] > 0).sum())
                n_cmp += 1
                if not ok:
                    q4[f"{body}/{u}/{blk}/{rn}"] = False
    checks["Q4_det_firing_onset_footprint"] = {"pass": not q4, "runs_compared": n_cmp, "lineage_cases_fired": fired,
                                               "lineage_cases": n_cmp * k, "mismatched": list(q4)[:10]}

    items = {}
    EP = ("r_in", "r_all", "r_fp", "r_out", "v_in", "v_all", "r_dose", "r_dose_in")
    for body, u in D.tasks():
        for blk in blocks:
            e, raw = shard(body, u, blk), rawf(body, u, blk)
            meta = meta_of(root / "shards" / body / u / f"{blk}.npz")
            ra = runs_of(meta)
            for rn in D.RUNNAMES:
                arms = ra[rn]
                jd, jr, jl = arms.index("det"), arms.index("rest"), arms.index("dial")
                on = e[f"{rn}/det_on"][jd]
                okc = True
                for c in range(k):
                    first = on[c] if on[c] > 0 else D.WINDOW + 1
                    before = [ti for ti, t_ in enumerate(D.READS) if t_ < first]
                    ntb = int((first - 1) // D.TRACE)
                    okc &= all(np.array_equal(e[f"{rn}/{q}"][before, jd, c], e[f"{rn}/{q}"][before, jr, c]) for q in EP)
                    okc &= bool(np.array_equal(e[f"{rn}/trace"][:ntb, jd, c], e[f"{rn}/trace"][:ntb, jr, c]))
                    if on[c] < 0:
                        okc &= all(np.array_equal(raw[f"{rn}/{x}"][jd, c], raw[f"{rn}/{x}"][jr, c]) for x in ("V", "r", "H", "W"))
                items[f"{body}/{u}/{blk}/{rn}: det = rest before its onset"] = bool(okc)
                want = sum(min(A2.SIG["duration"], D.WINDOW + 1 - int(x)) for x in on if x > 0)
                items[f"{body}/{u}/{blk}/{rn}: det on min(1,000, 8,001 - onset)"] = meta["signal_updates"][rn]["det"] == want
                items[f"{body}/{u}/{blk}/{rn}: dial on exactly 1,000 updates"] = bool(
                    meta["signal_updates"][rn]["dial"] == A2.SIG["duration"] * k and (e[f"{rn}/onset"][jl] >= 0).all())
                if rn.startswith("change@"):
                    items[f"{body}/{u}/{blk}/{rn}: u(new) + u(old) = 1"] = bool((e[f"{rn}/r_in"] + e[f"{rn}/r_in_old"] == 1.0).all())
            j0 = ra["none@0"].index("vote")
            for other in ("cue@0", "change@0"):
                j1 = ra[other].index("vote")
                ok = all(np.array_equal(raw[f"none@0/{x}"][j0], raw[f"{other}/{x}"][j1]) for x in ("V", "r", "H", "W"))
                ok &= all(np.array_equal(raw[f"none@0/{x}"], raw[f"{other}/{x}"]) for x in ("rB", "HB", "WB"))
                if other == "cue@0":
                    ok &= all(np.array_equal(e[f"none@0/{q}"][:, j0], e[f"{other}/{q}"][:, j1]) for q in EP)
                else:
                    ok &= bool(np.array_equal(e["none@0/r_in"][:, j0], e[f"{other}/r_in_old"][:, j1]))
                items[f"{body}/{u}/{blk}/vote: none@0 = {other}"] = bool(ok)
    checks["Q5_aliases_exact"] = {"pass": all(items.values()), "n_items": len(items),
                                  "failed": [x for x, v in items.items() if not v][:10]}

    bad = []
    for body, u in D.tasks():
        pattern, theta = A2.parse_unit(u)
        for blk in blocks:
            raw, e = rawf(body, u, blk), shard(body, u, blk)
            ra = runs_of(meta_of(root / "shards" / body / u / f"{blk}.npz"))
            cases, V0, ema0, R0, th, T = S2.prepare(pattern, blk, D.PURPOSE["debug"])
            for situation, sigma, a1, det, size in D.RUNS:
                rn = D.run_name(situation, sigma)
                ev = S2.event(situation, size, sigma, cases, V0, ema0, R0, T, D.TAG)
                m, tgt, fp = ev["m"], ev["target"], B2S.footprint(ev["m"], A2.SIG["d"])
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
                i = ra[rn].index("det")
                zone, fpd, on = raw[f"{rn}/zone"][0], raw[f"{rn}/fp"][0], e[f"{rn}/det_on"][i]
                okf = np.array_equal(B2S.footprint(zone, A2.SIG["d"]) & (on > 0)[:, None, None], fpd)
                okf &= np.array_equal(zone.sum((-2, -1)).astype(float), e[f"{rn}/det_zone"][i])
                okf &= np.array_equal(fpd.sum((-2, -1)).astype(float), e[f"{rn}/det_fp"][i])
                okf &= np.array_equal((fpd & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_fp_in"][i])
                okf &= np.array_equal((zone & m).sum((-2, -1)) / m.sum((-2, -1)), e[f"{rn}/det_zone_in"][i])
                bad += [] if okf else [f"{body}/{u}/{blk}/{rn}/det footprint"]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    q7 = {}
    fz = json.loads((LANE / "ar002" / "frozen" / "design.json").read_text())
    q7["ar002_frozen_design_unchanged"] = fz["digest"] == A2.digest() and fz["sources"] == A2.sources(LANE)
    q7["runs_are_the_seven_sigma0_situations_with_vote_rest_dial_det"] = (
        [x[0] for x in D.RUNS] == list(A2.SITUATIONS)
        and all(x[1] == 0.0 and x[2] == ("vote", "rest", "dial") and x[3] == ("det",) and x[4] == A2.SIZE for x in D.RUNS))
    full = {A2.run_name(*x): set(x[2]) | set(x[3]) for x in A2.RUNS}
    q7["every_reduced_arm_is_in_ar002s_run"] = all(set(D.ARMS) <= full[rn] for rn in D.RUNNAMES)
    q7["det_is_ar002s_frozen_detector"] = D.DETECTOR == A2.DETECTORS["det"] == fz["design"]["detectors"]["det"]
    q7["tag_best_point_harm_weights"] = (D.TAG == A2.TAG == "mse-ar002" and D.BEST == A2.BEST == "vote"
                                         and D.POINT == (0.9, 0.1) and D.HARM == {"cue@0": 0.01, "none@0": 0.002}
                                         and all(abs(w - 1 / 8) < 1e-15 for w in A2.WEIGHTS.values()))
    dev = AZ.load(AR002_RUNS / "development")
    a_dev, b_dev = AZ.U(dev, "det") - AZ.U(dev, "vote"), AP.kept("det")(dev)
    sd = lambda x: max(float(x.mean(1).std(ddof=1)), float(x.ravel().std(ddof=1) / math.sqrt(x.shape[-1])))
    q7["development_values_recompute"] = all(
        round(float(x.mean()), 6) == D.DEV[key]["value"] and round(sd(x), 6) == D.DEV[key]["sd"]
        for key, x in (("a", a_dev), ("b", b_dev))) and len(AZ.blocks_of(dev)) == 16
    blocks_c = D.IDENTITIES["confirmation"]
    q7["confirmation_blocks_in_range_and_clear_of_ar001"] = (
        len(blocks_c) == 20 == len(set(blocks_c)) and blocks_c[0] == A2.CONFIRMATION_FROM == 920128
        and all(b in RANGES["confirmation"] for b in blocks_c) and min(blocks_c) >= A1.CONFIRMATION_RESERVED[1])
    drawn = [str(f) for rr in (AR002_RUNS, AR002C_RUNS) for f in rr.rglob("*")
             if f.is_file() and f.parent.name not in ("tools",) and f.stem.isdigit() and int(f.stem) >= 920000]
    q7["no_block_from_920000_drawn"] = not drawn
    checks["Q7_declaration_and_boundary"] = {"pass": all(q7.values()), "items": q7, "drawn": drawn[:5]}

    q8 = {}
    pattern, theta = A2.parse_unit("F0_t1")
    cases, V0, ema0, R0, th, T = S2.prepare(pattern, blocks[2], D.PURPOSE["debug"])
    blk_ = lambda o, i: [o[x][i * k:(i + 1) * k] for x in ("V", "r", "H", "W", "zone", "fp")]
    for s in ("memory", "cue"):
        o1 = S2.run_det("li4", s, 0.0, ("det",), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        o2 = S2.run_det("li4", s, 0.0, ("det", "det-v", "det-ms"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        o3 = S2.run_det("li4", s, 0.0, ("det", "det"), cases, V0, ema0, R0, th, T, theta, {600}, window=600)
        q8[f"{s}: det alone = det beside det-v and det-ms"] = all(np.array_equal(x, y) for x, y in zip(blk_(o1, 0), blk_(o2, 0)))
        q8[f"{s}: det listed twice is bit-identical"] = all(np.array_equal(x, y) for x, y in zip(blk_(o3, 0), blk_(o3, 1)))
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
    procs = [subprocess.run([sys.executable, "-m", f"ar002c.{mod}", "--root", str(root), "--out", str(dst)], cwd=LANE,
                            capture_output=True, text=True, env=env)
             for mod, dst in (("analyze", out), ("predict", out / "confirmation.json"), ("tables", out / "TABLES.md"))]
    files = [out / "summary.json", out / "confirmation.json", out / "TABLES.md"]
    got = json.loads(files[1].read_text()) if files[1].exists() else {}
    crit = got.get("criteria", {})
    computed = (sorted(crit) == ["C1", "C2", "C3"] and "lower_bound" in crit["C1"] and "lower_bound" in crit["C2"]
                and "upper_bound_cue" in crit["C3"] and "upper_bound_none" in crit["C3"] and "verdict" in got)
    sizes = {q.name: q.stat().st_size for q in files if q.exists()}
    git_files = [f for f in list((LANE / "ar002c").rglob("*")) + [LANE / "tests" / "test_ar002c.py", LANE / "REGISTRATION_AR002C.md"]
                 if f.is_file()]
    big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
    checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and all(q.exists() for q in files) and computed
                                    and max(sizes.values(), default=0) <= 262144 and not big,
                                    "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big,
                                    "criteria_computed": computed, "verdict_read": False}

    failed = [x for x, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "ar002_digest": A2.digest(), "root": str(root), "blocks": blocks, "tag": D.TAG,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
