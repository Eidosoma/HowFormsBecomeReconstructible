"""Qualification of NP002 on the preflight (engineering) shards; criteria fixed in advance.

python -m np002.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape (stage 2 only for the spacing conflicts)
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: the preparations of C4s2 equal np001.sim.prepare('C4s2')'s and of C84 and C48 the S8 and S4 acquisitions'
    (np001.sim.prepare) bit for bit, and S4's equals dl002.sim.prepare's; stage 1's five reading conditions at gain 0.2
    (intact, body1, record1, body, body3) equal lr002.sim.run's (0/none, 0.001/body, 0.001/record+parity, 0.01/body,
    0.03/body) bit for bit (body, record and bonds, from the saved final states) on C4s2, C84 and C48 for every body
Q4  replay: one case of one branch at a time, with no batching and no lr002.sim.relations: stage 1's 'alone' (the body
    with no record: dl001.sim.body at gain 0), two protected race branches (the body reading at a low gain a record that
    steps through its bonds by msegrid.core.record_step, no bond noise, no relearning) and four successor branches of
    the spacing conflicts (the protected record; the no-record control) reproduce the saved final bodies within 1e-12
Q5  aliases: the records no body writes ('alone', 'intact', 'record1' and every 'intact@g') are bit-identical across the
    four stage-1 bodies, 'alone''s and every 'intact@g''s record is 'intact''s (the body never writes them, whatever the
    gain), for every unit; for the spacing conflicts every successor's no-record control is bit-identical whichever body
    and unit handed the records, and every successor of the 'intact' record ends bit-identical across stage-1 bodies
Q6  reanalysis: the endpoints at the last reads (with abs, abs_b, r_abs, r_abs_b and bond_b) recomputed from the saved
    final states equal the saved ones
Q7  efficacy: each unit's two templates agree in sign on exactly design.A0 of the sheet in every case (C4sK 1 - K/4;
    C84, C48 1/2), and their relations (bonds) on exactly design.B0; every acquired record agrees with its own template on every site of every case; each acquired body
    aligns >= 0.90 with its initial template (block mean); C84's body, moving average and theta are S8's acquisition's
    and its record S4's, and C48's the reverse, bit for bit; T0 is the body's pattern's template; the successors' newborn
    bodies align with every template within 0.15 of 0.5 (block mean)
Q8  pairing, case-matched: a race branch (intact@0.02 and body@0.05) run on its own equals the same branch of the full
    run (stage 1 at the first read); stage 1 with 'intact' twice gives bit-identical branches; a successor with every
    branch reading the same record at the same gain gives bit-identical branches (every successor body)
Q9  resources: forecast development wall <= 12 h on 12 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from dl002 import sim as S2  # noqa: E402
from lr001.sim import bond_err, edges_from, halves  # noqa: E402
from lr002 import design as L2  # noqa: E402
from lr002 import sim as L2S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msegrid.core import Stream, birth, bonds, record_step  # noqa: E402
from np001 import sim as N1S  # noqa: E402
from np002 import design as D  # noqa: E402
from np002 import sim  # noqa: E402
from np002 import worker as W  # noqa: E402

FROZEN = LANE / "np002" / "frozen"
WORKERS = 12
LR2_CONDS = tuple(L2.Cond(c.rate, c.repair) for c in D.HANDED)
Q4_S1 = (("li16", "C84", "alone", 1), ("li2", "C4s3", "intact@0.02", 4), ("li4", "C48", "intact@0.005", 6))
Q4_S2 = (("li4", "C48", "li4", "intact", 0), ("dw", "C84", "li16", "body", 3), ("li16", "C48", "dw", "none", 5),
         ("li2", "C84", "li2", "body3", 7))


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def _cases(block, purpose="engineering"):
    return enrol([block], D.MESSAGES, D.PARENTS, purpose)


def q3_job(args):
    body, unit, block, root, cpu = args
    os.sched_setaffinity(0, {cpu})
    cases, V0, ema0, R0, th, T = sim.prepare(unit, block, "engineering")
    o = L2S.run(body, LR2_CONDS, cases, V0, ema0, R0, th, T, D.THETA, set(D.READS), tag=D.TAG, kc=D.KC, window=D.WINDOW)
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    ok = {}
    for x in ("V", "r", "H", "W"):
        mine = raw[f"s1/{x}"][W.HANDED_IX].reshape(-1, D.SIDE, D.SIDE)
        ok[f"{body}/{unit}/{x}"] = bool(np.array_equal(mine, o[x].astype(mine.dtype)) and
                                        (x not in ("H", "W") or np.array_equal(np.abs(o[x]), np.ones_like(o[x]))))
    if body == D.BODIES[0]:
        if unit == "C4s2":
            a, b = sim.prepare("C4s2", block, "engineering"), N1S.prepare("C4s2", block, "engineering")
            ok["prepare_C4s2_is_np001s"] = all(np.array_equal(x, y) for x, y in zip(a[1:], b[1:]))
            a, b = N1S.prepare("S4", block, "engineering"), S2.prepare("S4", block, "engineering")
            ok["prepare_S4_is_dl002s"] = all(np.array_equal(x, y) for x, y in zip(a[1:], b[1:]))
        if unit in D.SPACING:
            bp, rp = D.PAIRS[unit]
            a, pb, pr = sim.prepare(unit, block, "engineering"), N1S.prepare(bp, block, "engineering"), N1S.prepare(rp, block, "engineering")
            ok[f"prepare_{unit}_body_is_{bp}s_record_is_{rp}s"] = bool(
                np.array_equal(a[1], pb[1]) and np.array_equal(a[2], pb[2]) and np.array_equal(a[4], pb[4])
                and np.array_equal(a[3], pr[3]) and np.array_equal(a[5], pr[5]))
    return ok


def replay_s1(body, unit, block, cond, ci, cpu):
    """One stage-1 branch of one case with no batching: dl001.sim.body reading a protected record that steps through
    its bonds by record_step (gain 0 for 'alone', whose record no body reads)."""
    os.sched_setaffinity(0, {cpu})
    cases, V0, ema0, R0, th, T = sim.prepare(unit, block, "engineering")
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    c = [cases[ci]]
    gain = D.gain_of(cond)
    V, E, r = V0[[ci]].copy(), ema0[[ci]].copy(), R0[[ci]].copy()
    H, Wb = edges_from(bonds(R0[[ci]], True))
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs = Stream(D.TAG, c, "future", side=D.SIDE), Stream(D.TAG, c, "record-noise", side=D.SIDE)
    th0 = (th * D.THETA)[[ci]]
    for t in range(1, D.WINDOW + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, *_ = S.body(V, E, r, th0, buf[i], p, gain, alpha, G)
        r = record_step(r, xbuf[i], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, Wb))
    return V[0]


def replay_s2(body, unit, block, B, branch, ci, raw, cpu):
    """One successor branch of one case: a newborn B reading the handed record, which steps through its bonds by
    record_step (no bond noise, no relearning, no parity), or nothing for the control."""
    os.sched_setaffinity(0, {cpu})
    cases = _cases(block)
    alpha, L = DL.BODIES[B]
    G = S.ghat(D.SIDE, L) if alpha else None
    c = [cases[ci]]
    src = "intact" if branch == "none" else branch
    j = D.CONDNAMES.index(src)
    r = raw["s1/r"][j, [ci]].astype(float)
    H, Wb = raw["s1/H"][j, [ci]].astype(float), raw["s1/W"][j, [ci]].astype(float)
    gain = 0.0 if branch == "none" else D.GAIN
    V = birth(D.TAG, c, "successor", B, side=D.SIDE).copy()
    E = V.copy()
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs = Stream(D.TAG, c, "successor-future", B, side=D.SIDE), Stream(D.TAG, c, "successor-record-noise", B, side=D.SIDE)
    th = np.zeros((1, D.SIDE, D.SIDE))
    for t in range(1, D.WINDOW2 + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, *_ = S.body(V, E, r, th, buf[i], p, gain, alpha, G)
        r = record_step(r, xbuf[i], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, Wb))
    return V[0]


def replay_job(args):
    kind, pick, block, root, cpu = args
    if kind == "s1":
        body, unit, cond, ci = pick
        mine = npz(Path(root) / "raw" / body / unit / f"{block}.npz")["s1/V"][D.CONDNAMES.index(cond), ci]
        return f"s1/{body}/{unit}/{cond}/case{ci}", float(np.abs(replay_s1(body, unit, block, cond, ci, cpu) - mine).max())
    body, unit, B, branch, ci = pick
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    mine = raw[f"s2/{B}/V"][W.BRANCHES2.index(branch), ci]
    return (f"s2/{body}/{unit}/{B}/{branch}/case{ci}",
            float(np.abs(replay_s2(body, unit, block, B, branch, ci, raw, cpu) - mine).max()))


def q8_job(args):
    block, root, cpu = args
    os.sched_setaffinity(0, {cpu})
    out, t1 = {}, D.READS[0]
    for body, unit, cond in (("li4", "C4s2", "intact@0.02"), ("dw", "C84", "body@0.05")):
        cases, V0, ema0, R0, th, T = sim.prepare(unit, block, "engineering")
        T0 = sim.initial(unit, cases, block)
        c = D.CONDS[D.CONDNAMES.index(cond)]
        one = sim.stage1(body, (c,), cases, V0, ema0, R0, th, T, {t1}, tag=D.TAG, window=t1, theta=D.THETA, T0=T0)
        full = npz(Path(root) / "shards" / body / unit / f"{block}.npz")
        ci = D.CONDNAMES.index(cond)
        out[f"{body}/{unit}/{cond}_alone_equals_full_run"] = all(
            bool(np.array_equal(one[e][0], full[f"s1/{e}"][0, ci])) for e in sim.ENDS1)
    cases, V0, ema0, R0, th, T = sim.prepare("C48", block, "engineering")
    k = len(cases)
    intact = D.CONDS[D.CONDNAMES.index("intact")]
    o = sim.stage1("li4", (intact, intact), cases, V0, ema0, R0, th, T, {t1}, tag=D.TAG, window=t1, theta=D.THETA)
    out["stage1_li4_intact_twice"] = all(bool(np.array_equal(o[x][:k], o[x][k:])) for x in ("V", "r", "H", "W"))
    r, H, Wb = (np.tile(o[x][:k], (3, 1, 1)) for x in ("r", "H", "W"))
    for B in D.SUCC_BODIES:
        o2 = sim.successor(B, r, H, Wb, cases, th, T, {D.READS2[0]}, [D.GAIN] * 3, tag=D.TAG, window=D.READS2[0],
                           theta=D.THETA)
        out[f"successor_{B}_same_record_thrice"] = bool(np.array_equal(o2["V"][:k], o2["V"][k:2 * k])
                                                         and np.array_equal(o2["V"][:k], o2["V"][2 * k:]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    receipt_path = FROZEN / "qualification_receipt.json" if a.blocks is None else root / "debug_qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda b_, u, blk=lo: npz(root / "raw" / b_ / u / f"{blk}.npz")
    shard = lambda b_, u, blk=lo: npz(root / "shards" / b_ / u / f"{blk}.npz")
    checks = {}
    q3_picks = [(b_, u) for u in ("C4s2", "C84", "C48") for b_ in D.BODIES]
    jobs = len(q3_picks) + len(Q4_S1) + len(Q4_S2) + 1
    pool = ProcessPoolExecutor(max_workers=max(1, min(jobs, len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q3 = pool.map(q3_job, [(b_, u, lo, str(root), cpu_of(i)) for i, (b_, u) in enumerate(q3_picks)])
    q4 = pool.map(replay_job, [("s1", pk, lo, str(root), cpu_of(len(q3_picks) + i)) for i, pk in enumerate(Q4_S1)]
                  + [("s2", pk, lo, str(root), cpu_of(len(q3_picks) + len(Q4_S1) + i)) for i, pk in enumerate(Q4_S2)])
    q8 = pool.map(q8_job, [(lo, str(root), cpu_of(jobs - 1))])
    nr, nr2, nc, nb2 = len(D.READS), len(D.READS2), len(D.CONDS), len(W.BRANCHES2)

    missing = []
    for body, u in D.tasks():
        for blk in range(lo, hi):
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            bad += [f"s1/{x}" for x in sim.ENDS1 + ("abs", "abs_b", "r_abs", "r_abs_b")
                    if e.get(f"s1/{x}", np.zeros(0)).shape != (nr, nc, D.NCASE)]
            bad += [] if e.get("s1/bond_b", np.zeros(0)).shape == (1, nc, D.NCASE) else ["s1/bond_b"]
            if D.has_successors(u):
                bad += [f"s2/{B}/{x}" for B in D.SUCC_BODIES for x in sim.ENDS2
                        if e.get(f"s2/{B}/{x}", np.zeros(0)).shape != (nr2, nb2, D.NCASE)]
            else:
                bad += [k for k in e if k.startswith("s2/")]
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for body, u in (("li4", "C48"), ("dw", "C4s1")):
        W.run_task(body, u, lo, "engineering", str(serial))
        for kind in ("shards", "raw"):
            x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
            same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for d_ in q3:
        eq.update(d_)
    need = {"prepare_C4s2_is_np001s", "prepare_S4_is_dl002s", "prepare_C84_body_is_S8s_record_is_S4s",
            "prepare_C48_body_is_S4s_record_is_S8s"}
    checks["Q3_engine"] = {"pass": bool(eq) and need <= set(eq) and all(eq.values()), "items": eq}

    alias = {}
    protected = ["alone", "intact", "record1"] + [f"intact@{g:g}" for g in D.RACE_GAINS]
    for u in D.UNITS:
        raws = {b_: rawf(b_, u) for b_ in D.BODIES}
        for c in protected:
            j = D.CONDNAMES.index(c)
            alias[f"{u}/{c}_record_same_every_body"] = all(
                np.array_equal(raws[D.BODIES[0]][f"s1/{x}"][j], raws[b_][f"s1/{x}"][j]) for b_ in D.BODIES[1:] for x in ("r", "H", "W"))
        ji = D.CONDNAMES.index("intact")
        for c in ["alone"] + [f"intact@{g:g}" for g in D.RACE_GAINS]:
            j = D.CONDNAMES.index(c)
            alias[f"{u}/{c}_record_is_intact"] = all(np.array_equal(raws[b_][f"s1/{x}"][j], raws[b_][f"s1/{x}"][ji])
                                                     for b_ in D.BODIES for x in ("r", "H", "W"))
        if D.has_successors(u):
            for B in D.SUCC_BODIES:
                ii = W.BRANCHES2.index("intact")
                alias[f"{u}/{B}/intact_successor_same_every_body"] = all(
                    np.array_equal(raws[D.BODIES[0]][f"s2/{B}/V"][ii], raws[b_][f"s2/{B}/V"][ii]) for b_ in D.BODIES[1:])
    ref = rawf(D.BODIES[0], D.SPACING[0])
    for B in D.SUCC_BODIES:
        alias[f"{B}/control_same_every_body_and_unit"] = all(
            np.array_equal(ref[f"s2/{B}/V"][-1], rawf(b_, u)[f"s2/{B}/V"][-1]) for b_ in D.BODIES for u in D.SPACING)
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for body, u in D.tasks():
        raw, e = rawf(body, u), shard(body, u)
        T, T0 = raw["T"], raw["T0"]
        H0, W0 = edges_from(bonds(raw["R0"], True))
        Hb0, Wb0 = edges_from(bonds(T0, True))
        for ci, c in enumerate(D.CONDNAMES):
            V, r = raw["s1/V"][ci], raw["s1/r"][ci]
            H, Wb = raw["s1/H"][ci].astype(float), raw["s1/W"][ci].astype(float)
            al, alb, ra, rab = S.sign(V, T), S.sign(V, T0), S.sign(r, T), S.sign(r, T0)
            got = {"align": al, "r_align": ra, "shape": S.best_shift(V, T), "r_shape": S.best_shift(r, T),
                   "spacing": S.spacing(V), "agree": ((V > 0) == (r > 0)).mean((-2, -1)), "bond_err": bond_err(H, Wb, H0, W0),
                   "align_b": alb, "r_align_b": rab, "abs": np.abs(2 * al - 1), "abs_b": np.abs(2 * alb - 1),
                   "r_abs": np.abs(2 * ra - 1), "r_abs_b": np.abs(2 * rab - 1)}
            bad += [f"{body}/{u}/s1/{c}/{x}" for x, v in got.items() if not np.array_equal(v, e[f"s1/{x}"][-1, ci])]
            if not np.array_equal(bond_err(H, Wb, Hb0, Wb0), e["s1/bond_b"][0, ci]):
                bad.append(f"{body}/{u}/s1/{c}/bond_b")
        if D.has_successors(u):
            for B in D.SUCC_BODIES:
                for bi, c in enumerate(W.BRANCHES2):
                    V = raw[f"s2/{B}/V"][bi]
                    got = {"align": S.sign(V, T), "shape": S.best_shift(V, T), "spacing": S.spacing(V), "align_b": S.sign(V, T0)}
                    bad += [f"{body}/{u}/s2/{B}/{c}/{x}" for x, v in got.items() if not np.array_equal(v, e[f"s2/{B}/{x}"][-1, bi])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    cases = _cases(lo)
    for u in D.UNITS:
        raw = rawf(D.BODIES[0], u)
        bp, rp = D.PAIRS[u]
        eff[f"{u}/templates_agree_on_a0"] = bool(np.allclose(S.sign(raw["T"], raw["T0"]), D.A0[u], rtol=0, atol=1e-12))
        Ht, Wt = edges_from(bonds(raw["T"], True))
        Hb, Wb_ = edges_from(bonds(raw["T0"], True))
        eff[f"{u}/relations_agree_on_b0"] = bool(np.allclose(1 - bond_err(Ht, Wt, Hb, Wb_), D.B0[u], rtol=0, atol=1e-12))
        eff[f"{u}/record_exact"] = bool(np.array_equal(S.sign(raw["R0"], raw["T"]), np.ones(D.NCASE)))
        eff[f"{u}/acquired_aligned"] = float(S.sign(raw["V0"], raw["T0"]).mean())
        pb, pr = N1S.prepare(bp, lo, "engineering"), N1S.prepare(rp, lo, "engineering")
        eff[f"{u}/body_is_{bp}s"] = bool(np.array_equal(raw["V0"], pb[1]) and np.array_equal(raw["T0"], pb[5]))
        eff[f"{u}/record_is_{rp}s"] = bool(np.array_equal(raw["R0"], pr[3]) and np.array_equal(raw["T"], pr[5]))
        if D.has_successors(u):
            for B in D.SUCC_BODIES:
                eff[f"{u}/{B}/newborn_align"] = float(S.sign(birth(D.TAG, cases, "successor", B, side=D.SIDE), raw["T"]).mean())
    okq7 = all(v for k, v in eff.items() if isinstance(v, bool))
    okq7 &= all(v >= 0.90 for k, v in eff.items() if k.endswith("acquired_aligned"))
    okq7 &= all(abs(v - 0.5) <= 0.15 for k, v in eff.items() if k.endswith("newborn_align"))
    checks["Q7_efficacy"] = {"pass": bool(okq7), "items": eff}

    q8r = {}
    for d_ in q8:
        q8r.update(d_)
    checks["Q8_pairing_case_matched"] = {"pass": bool(q8r) and all(q8r.values()), "items": q8r}

    walls = {}
    for key, t in manifest["tasks"].items():
        b_, uu = key.split("/")[:2]
        walls.setdefault((b_, uu), []).append(t["wall_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 2), "forecast_cpu_h": round(cpu / 3600, 2),
                              "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    pred = FROZEN / "predictions.json"
    if not pred.exists():                      # before the freeze: the draft's statements, written to the run root
        pred = root / "predictions_draft.json"
        subprocess.run([sys.executable, "-c", "import json,sys; sys.path.insert(0, '.'); from np002 import predict as P; "
                        f"open('{pred}', 'w').write(json.dumps({{'statements': P.STATEMENTS}}))"], cwd=LANE, env=env, check=True)
    proc = subprocess.run([sys.executable, "-m", "np002.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "np002.tables", "--out", str(out), "--predictions", str(pred)], cwd=LANE,
                           capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_stage1.csv", "contrasts_stage2.csv", *(f"summary_{b_}.json" for b_ in D.BODIES),
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads(pred.read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and bool(stmts) and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    worst, items = 0.0, {}
    for name, d in q4:
        items[name], worst = d, max(worst, d)
    pool.shutdown()
    checks["Q4_replay"] = {"pass": worst <= 1e-12, "max_abs_difference": worst, "items": items}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_pairing_case_matched", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
