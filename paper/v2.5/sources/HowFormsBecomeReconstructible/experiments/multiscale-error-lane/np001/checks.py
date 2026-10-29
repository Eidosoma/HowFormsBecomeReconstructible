"""Qualification of NP001 on the preflight (engineering) shards; criteria fixed in advance.

python -m np001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: stage 1's five reading conditions equal lr002.sim.run's (0/none, 0.001/body, 0.001/record+parity, 0.01/body,
    0.03/body) bit for bit (body, record and bonds, from the saved final states), on S4, F0 and C4s2 and every body;
    the preparation of S4 equals dl002.sim.prepare's bit for bit
Q4  replay: one case of one branch at a time, with no batching and no lr002.sim.relations: stage 1's 'alone' (the body
    with no record: dl001.sim.body at gain 0), and three successor branches (the body reading a protected record that
    steps through its bonds by msegrid.core.record_step with no bond noise and no relearning; the no-record control)
    reproduce the saved final bodies within 1e-12
Q5  aliases: the records no body writes ('alone', 'intact', 'record1') are bit-identical across the three stage-1
    bodies, and 'alone''s record is 'intact''s, for every pattern; every successor's no-record control is bit-identical
    whichever body and pattern handed the records; every successor of the 'intact' record ends bit-identical across the
    stage-1 bodies
Q6  reanalysis: the endpoints at the last reads recomputed from the saved final states equal the saved ones
Q7  efficacy: S4sX agrees with S4 in sign on exactly 1 - X/4 of the sheet (X = 1, 2, 3; every message kind) and S4sX's
    best shifted agreement with S4 is 1; every acquired record agrees in sign with its own template on every site of
    every case and, for S4sX, with S4's on exactly 1 - X/4 of the sheet; each acquired body aligns >= 0.90 with its own
    initial template (block mean; P31's lowest block 0.940); a conflict C4sK's body, moving average and theta are S4's
    and its record and history S4sK's, bit for bit, and its T0 is S4's template; the successors' newborn bodies align
    with every template within 0.15 of 0.5 (block mean; 8 cases of 1,024 sites: the SE is about 0.006)
Q8  pairing, case-matched: stage 1 with 'intact' run twice as two branches gives bit-identical branches; a successor
    with every branch reading the same record at the same gain gives bit-identical branches (every successor body)
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
from np001 import design as D  # noqa: E402
from np001 import sim  # noqa: E402
from np001 import worker as W  # noqa: E402

FROZEN = LANE / "np001" / "frozen"
WORKERS = 12
LR2_CONDS = tuple(L2.Cond(c.rate, c.repair) for c in D.HANDED)
Q4_S1 = (("li4", "S8", 1), ("dw", "S4s3", 6), ("li2", "C4s2", 4))               # stage 1 'alone': body, unit, case
Q4_S2 = (("li4", "F0", "li4", "intact", 0), ("dw", "S8", "li16", "body", 3),     # body, unit, successor, branch, case
         ("li16", "S4s2", "dw", "none", 5), ("li4", "S4s1", "li16", "body3", 7), ("li2", "C4s1", "li2", "body", 2),
         ("dw", "C4s3", "li4", "record1", 6))


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
    k, sel = len(cases), W.HANDED_IX
    ok = {}
    for x in ("V", "r", "H", "W"):
        mine = raw[f"s1/{x}"][sel].reshape(-1, D.SIDE, D.SIDE)
        ok[f"{body}/{unit}/{x}"] = bool(np.array_equal(mine, o[x].astype(mine.dtype)) and
                                        (x not in ("H", "W") or np.array_equal(np.abs(o[x]), np.ones_like(o[x]))))
    if unit == "S4" and body == D.BODIES[0]:
        a, b = sim.prepare("S4", block, "engineering"), S2.prepare("S4", block, "engineering")
        ok["prepare_S4"] = all(np.array_equal(x, y) for x, y in zip(a[1:], b[1:]))
    return ok


def replay_s1(body, unit, block, ci, cpu):
    """Stage 1's 'alone' branch of one case: dl001.sim.body at gain 0 reading a zero record, one case, no batching."""
    os.sched_setaffinity(0, {cpu})
    cases, V0, ema0, R0, th, T = sim.prepare(unit, block, "engineering")
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    c = [cases[ci]]
    V, E, r0 = V0[[ci]].copy(), ema0[[ci]].copy(), np.zeros((1, D.SIDE, D.SIDE))
    p = replace(NATIVE, sigma=D.SIGMA)
    st = Stream(D.TAG, c, "future", side=D.SIDE)
    for t in range(1, D.WINDOW + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        V, E, *_ = S.body(V, E, r0, (th * D.THETA)[[ci]], buf[i], p, 0.0, alpha, G)
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
        body, unit, ci = pick
        mine = npz(Path(root) / "raw" / body / unit / f"{block}.npz")["s1/V"][D.CONDNAMES.index("alone"), ci]
        return f"s1/{body}/{unit}/alone/case{ci}", float(np.abs(replay_s1(body, unit, block, ci, cpu) - mine).max())
    body, unit, B, branch, ci = pick
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    mine = raw[f"s2/{B}/V"][W.BRANCHES2.index(branch), ci]
    return (f"s2/{body}/{unit}/{B}/{branch}/case{ci}",
            float(np.abs(replay_s2(body, unit, block, B, branch, ci, raw, cpu) - mine).max()))


def q8_job(args):
    block, cpu = args
    os.sched_setaffinity(0, {cpu})
    cases, V0, ema0, R0, th, T = sim.prepare("F0", block, "engineering")
    k, out = len(cases), {}
    intact = D.CONDS[D.CONDNAMES.index("intact")]
    o = sim.stage1("li4", (intact, intact), cases, V0, ema0, R0, th, T, {D.READS[0]}, window=D.READS[0])
    out["stage1_li4_intact_twice"] = all(bool(np.array_equal(o[x][:k], o[x][k:])) for x in ("V", "r", "H", "W"))
    r, H, Wb = (np.tile(o[x][:k], (3, 1, 1)) for x in ("r", "H", "W"))
    for B in D.SUCC_BODIES:
        o2 = sim.successor(B, r, H, Wb, cases, th, T, {D.READS2[0]}, [D.GAIN] * 3, window=D.READS2[0])
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
    q3_picks = [(b_, u) for u in ("S4", "F0", "C4s2") for b_ in D.BODIES]
    jobs = len(q3_picks) + len(Q4_S1) + len(Q4_S2) + 1
    pool = ProcessPoolExecutor(max_workers=max(1, min(jobs, len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q3 = pool.map(q3_job, [(b_, u, lo, str(root), cpu_of(i)) for i, (b_, u) in enumerate(q3_picks)])
    q4 = pool.map(replay_job, [("s1", pk, lo, str(root), cpu_of(len(q3_picks) + i)) for i, pk in enumerate(Q4_S1)]
                  + [("s2", pk, lo, str(root), cpu_of(len(q3_picks) + len(Q4_S1) + i)) for i, pk in enumerate(Q4_S2)])
    q8 = pool.map(q8_job, [(lo, cpu_of(jobs - 1))])
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
            bad += [f"s1/{x}" for x in sim.ENDS1 if e.get(f"s1/{x}", np.zeros(0)).shape != (nr, nc, D.NCASE)]
            bad += [f"s2/{B}/{x}" for B in D.SUCC_BODIES for x in sim.ENDS2
                    if e.get(f"s2/{B}/{x}", np.zeros(0)).shape != (nr2, nb2, D.NCASE)]
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, lo, "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{lo}.npz"), npz(serial / kind / body / u / f"{lo}.npz")
        same[f"{kind}/{body}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for d_ in q3:
        eq.update(d_)
    checks["Q3_engine"] = {"pass": bool(eq) and "prepare_S4" in eq and all(eq.values()), "items": eq}

    alias = {}
    for u in D.UNITS:
        raws = {b_: rawf(b_, u) for b_ in D.BODIES}
        for c in ("alone", "intact", "record1"):
            j = D.CONDNAMES.index(c)
            alias[f"{u}/{c}_record_same_every_body"] = all(
                np.array_equal(raws[D.BODIES[0]][f"s1/{x}"][j], raws[b_][f"s1/{x}"][j]) for b_ in D.BODIES[1:] for x in ("r", "H", "W"))
        ja, ji = D.CONDNAMES.index("alone"), D.CONDNAMES.index("intact")
        alias[f"{u}/alone_record_is_intact"] = all(np.array_equal(raws[b_][f"s1/{x}"][ja], raws[b_][f"s1/{x}"][ji])
                                                   for b_ in D.BODIES for x in ("r", "H", "W"))
        for B in D.SUCC_BODIES:
            ii = W.BRANCHES2.index("intact")
            alias[f"{u}/{B}/intact_successor_same_every_body"] = all(
                np.array_equal(raws[D.BODIES[0]][f"s2/{B}/V"][ii], raws[b_][f"s2/{B}/V"][ii]) for b_ in D.BODIES[1:])
    ref = rawf(D.BODIES[0], D.UNITS[0])
    for B in D.SUCC_BODIES:
        alias[f"{B}/control_same_every_body_and_pattern"] = all(
            np.array_equal(ref[f"s2/{B}/V"][-1], rawf(b_, u)[f"s2/{B}/V"][-1]) for b_, u in D.tasks())
    checks["Q5_aliases_exact"] = {"pass": all(alias.values()), "items": alias}

    bad = []
    for body, u in D.tasks():
        raw, e = rawf(body, u), shard(body, u)
        k = D.NCASE
        T, T0 = raw["T"], raw["T0"]
        H0, W0 = edges_from(bonds(raw["R0"], True))
        for ci, c in enumerate(D.CONDNAMES):
            V, r = raw["s1/V"][ci], raw["s1/r"][ci]
            H, Wb = raw["s1/H"][ci].astype(float), raw["s1/W"][ci].astype(float)
            got = {"align": S.sign(V, T), "r_align": S.sign(r, T), "shape": S.best_shift(V, T), "r_shape": S.best_shift(r, T),
                   "spacing": S.spacing(V), "agree": ((V > 0) == (r > 0)).mean((-2, -1)), "bond_err": bond_err(H, Wb, H0, W0),
                   "align_b": S.sign(V, T0), "r_align_b": S.sign(r, T0)}
            bad += [f"{body}/{u}/s1/{c}/{x}" for x, v in got.items() if not np.array_equal(v, e[f"s1/{x}"][-1, ci])]
        for B in D.SUCC_BODIES:
            for bi, c in enumerate(W.BRANCHES2):
                V = raw[f"s2/{B}/V"][bi]
                got = {"align": S.sign(V, T), "shape": S.best_shift(V, T), "spacing": S.spacing(V), "align_b": S.sign(V, T0)}
                bad += [f"{body}/{u}/s2/{B}/{c}/{x}" for x, v in got.items() if not np.array_equal(v, e[f"s2/{B}/{x}"][-1, bi])]
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    for X in (1, 2, 3):
        for kind in range(4):
            a_, b_ = sim.template(f"S4s{X}", kind, lo), sim.template("S4", kind, lo)
            eff[f"S4s{X}/kind{kind}/agreement_with_S4"] = bool(abs(float((a_ == b_).mean()) - (1 - X / 4)) < 1e-12)
            eff[f"S4s{X}/kind{kind}/best_shift_with_S4"] = bool(abs(float(S.best_shift(a_[None], b_[None])[0]) - 1) < 1e-12)
    cases = _cases(lo)
    for u in D.UNITS:
        raw = rawf(D.BODIES[0], u)
        eff[f"{u}/acquired_aligned"] = float(S.sign(raw["V0"], raw["T0"]).mean())
        if D.is_conflict(u):
            s4, s4k = rawf(D.BODIES[0], "S4"), rawf(D.BODIES[0], f"S4s{D.shift_of(u)}")
            eff[f"{u}/body_is_S4s"] = bool(np.array_equal(raw["V0"], s4["V0"]) and np.array_equal(raw["T0"], s4["T"]))
            eff[f"{u}/record_is_S4sK"] = bool(np.array_equal(raw["R0"], s4k["R0"]) and np.array_equal(raw["T"], s4k["T"]))
        else:
            eff[f"{u}/T0_is_T"] = bool(np.array_equal(raw["T0"], raw["T"]))
        eff[f"{u}/record_exact"] = bool(np.array_equal(S.sign(raw["R0"], raw["T"]), np.ones(D.NCASE)))
        if u.startswith("S4s"):
            T4 = np.stack([sim.template("S4", c.message, lo) for c in cases])
            eff[f"{u}/record_vs_S4"] = bool(np.allclose(S.sign(raw["R0"], T4), 1 - D.shift_of(u) / 4, rtol=0, atol=1e-12))
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
        subprocess.run([sys.executable, "-c", "import json,sys; sys.path.insert(0, '.'); from np001 import predict as P; "
                        f"open('{pred}', 'w').write(json.dumps({{'statements': P.STATEMENTS}}))"], cwd=LANE, env=env, check=True)
    proc = subprocess.run([sys.executable, "-m", "np001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "np001.tables", "--out", str(out), "--predictions", str(pred)], cwd=LANE,
                           capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_stage1.csv", "contrasts_stage2.csv", *(f"summary_{b_}.json" for b_ in D.BODIES),
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads(pred.read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
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
