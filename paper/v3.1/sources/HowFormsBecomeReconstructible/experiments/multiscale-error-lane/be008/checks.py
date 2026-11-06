"""Qualification of BE008 on the preflight (engineering) shards; criteria fixed in advance.

python -m be008.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite, every endpoint at its declared shape (each run at its own reads and window)
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  engine: BE008's clocks AL and SL are BE006's AL and SL (the same parameters, exactly), and their dial and never arms
    equal be006.sim.run's with be006.design's own arms bit for bit (body, record and bonds), from the saved final states,
    in memory4@0 and memory4@1959; two units, both bodies
Q4  independent replay: be006.checks.s_replay's per-site loops (the event, the body, bond noise at each arm's own p_b, the
    record's bond sums, LR004's arbiter, the cable equation by sparse LU, the trigger, the commitment, the pull and the
    Hebbian learners at the arbiter's rate and the arm's), run with BE008's tag, arms and windows set in the replaying
    process's memory only (be006's files unchanged), reproduce five full branches (dial-AL-n in memory4@979, never-SL-m in
    memory4@0, dial-AL-m in memory4@1959, dial-SL in memory4@3918, never-AL in memory4@0) within 1e-8 (bonds exactly)
Q5  aliases: with the signal never on, every dial-X equals its never-X bit for bit over 1,200 updates
Q6  reanalysis: the endpoints at each run's last read recomputed from the saved final states, the events and the regions
    equal the saved ones
Q7  efficacy: the delayed runs hold every clock's dial at round(m T*(3e-4)); every dial on for exactly its 1,000 updates
    and every never arm for none; onset recorded for the dials only, hit and the sensors for every arm; a bond at +s0
    relearning toward -1 at rate eta crosses zero after ceil(T*(eta)) updates (eta 0.01 and 3e-4); the arbiter cells are
    exactly the anchored, uncommitted cells whose body and record disagree; every clock commits for 15,000 updates; the
    bond-noise cut of each clock flips a bond with probability p_b (exact normal quantiles) and a quieter clock's flips are
    a subset of a noisier clock's on the same draws (3e-5 within 1e-4 within 1e-3)
Q8  the static map on the cases' own draw (BE005's Amendment 1 construction): for every preflight case the prompt dial-AL's
    onset share (memory4@0) equals within 1e-6 the static share on that case's own anchors and patch; reported, not gated:
    the other dials' onsets against the same
Q9  resources: forecast development wall <= 12 h on 12 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement is scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
from statistics import NormalDist  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be002 import sim as B2S  # noqa: E402
from be006 import design as B6  # noqa: E402
from be006 import sim as B6S  # noqa: E402
from be008 import design as D  # noqa: E402
from be008 import sim  # noqa: E402
from be008 import worker as W  # noqa: E402
from dl001 import sim as S  # noqa: E402
from lr001.sim import cut_for  # noqa: E402
from lr005 import sim as L5S  # noqa: E402

FROZEN = LANE / "be008" / "frozen"
WORKERS = 12
RUNS = {D.run_name(*x): x for x in D.RUNS}
Q4_PICKS = (("F0_t0", "dw", "memory", 4, D.DELAYS[0], "dial-AL-n", 0),
            ("S4_t1", "li4", "memory", 4, 0, "never-SL-m", 1),
            ("LB_t0", "dw", "memory", 4, D.DELAYS[1], "dial-AL-m", 2),
            ("F0_t1", "li4", "memory", 4, D.DELAYS[2], "dial-SL", 3),
            ("S4_t0", "dw", "memory", 4, 0, "never-AL", 4))
Q3_RUNS = ("memory4@0", f"memory4@{D.DELAYS[1]}")


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def static_onset(cases):
    """Q8: per case, the static share on its own anchors and patch (BE005's Amendment 1 construction, BE008's tag)."""
    am = L5S.anchor_mask(cases, D.TAG)
    m = sim.patch(cases, 4, D.TAG)
    lus = B2S.factor(*B2S.conductances(sim.footprint(m), D.SIG["lam_rest"], D.SIG["lam_sig"]))
    v = B2S.solve(lus, D.KAPPA * am * np.where(m, -1.0, 1.0))
    return ((v < -D.SIG["theta"]) & m).sum((-2, -1)) / m.sum((-2, -1))


def replay_job(args):
    """Q4: be006.checks.s_replay with BE008's tag, arms and windows set in this process's memory only."""
    pick, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    from be006 import checks as B6C
    B6.TAG = D.TAG
    B6.SIGNAL_ARMS = dict(B6.SIGNAL_ARMS, **D.SIGNAL_ARMS)
    B6.run_window = D.run_window
    return pick, B6C.s_replay(*pick, block)


def q3_job(args):
    """BE008's AL and SL against be006.sim.run with be006.design's own arms, bit for bit, from the saved final states."""
    unit, body, block, root, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k = len(cases)
    raw = npz(Path(root) / "raw" / body / unit / f"{block}.npz")
    ok = {}
    for rn in Q3_RUNS:
        situation, size, delay, mine = RUNS[rn]
        theirs = tuple(a for a in mine if a.split("-", 1)[1] in ("AL", "SL"))
        wdw = D.run_window(*RUNS[rn])
        o = B6S.run(body, situation, size, delay, theirs, cases, V0, ema0, R0, th, T, theta, {wdw}, tag=D.TAG, window=wdw,
                    params=B6.SIGNAL_ARMS)
        good = True
        for j, arm in enumerate(theirs):
            i = mine.index(arm)
            for x in ("V", "r", "H", "W"):
                want = o[x][j * k:(j + 1) * k]
                got = raw[f"{rn}/{x}"][i]
                good &= bool(np.array_equal(got, want.astype(got.dtype)) and (x in ("H", "W") or np.array_equal(got, want)))
        ok[f"{unit}/{body}/{rn}"] = good
    return ok


def q5_job(args):
    """With the signal never on, every dial-X equals its never-X (bit for bit), over 1,200 updates."""
    unit, body, block, cpu = args
    os.sched_setaffinity(0, [cpu])
    pattern, theta = D.parse_unit(unit)
    cases, V0, ema0, R0, th, T = sim.prepare(pattern, block, "engineering")
    k, out = len(cases), {}
    arms = D.ARMS
    o = sim.run(body, "memory", 4, 0, arms, cases, V0, ema0, R0, th, T, theta, {1200}, window=1200, on_window=(0, -1))
    for j in range(0, len(arms), 2):
        out[f"{unit}/{body}/memory4,no signal:{arms[j]}={arms[j + 1]}"] = all(
            np.array_equal(o[x][j * k:(j + 1) * k], o[x][(j + 1) * k:(j + 2) * k]) for x in ("V", "r", "H", "W"))
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
    rawf = lambda u, b_, blk=lo: npz(root / "raw" / b_ / u / f"{blk}.npz")
    shard = lambda u, b_, blk=lo: npz(root / "shards" / b_ / u / f"{blk}.npz")
    checks = {}
    q3_picks = [(u_, b_) for u_ in ("S4_t1", "LB_t0") for b_ in D.BODIES]
    q5_picks = [("F0_t0", b_) for b_ in D.BODIES]
    pool = ProcessPoolExecutor(max_workers=max(1, min(len(Q4_PICKS) + len(q3_picks) + len(q5_picks), len(cpus) - 1)))
    cpu_of = lambda i: cpus[(i + 1) % len(cpus)]
    q4 = pool.map(replay_job, [(pk, lo, cpu_of(i)) for i, pk in enumerate(Q4_PICKS)])
    q3 = pool.map(q3_job, [(u_, b_, lo, str(root), cpu_of(len(Q4_PICKS) + i)) for i, (u_, b_) in enumerate(q3_picks)])
    q5 = pool.map(q5_job, [(u_, b_, lo, cpu_of(len(Q4_PICKS) + len(q3_picks) + i)) for i, (u_, b_) in enumerate(q5_picks)])

    missing = []
    for body, u in D.tasks():
        for blk in range(lo, hi):
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for run in D.RUNS:
                rn, na = D.run_name(*run), len(run[3])
                nr, ntr = len(D.run_reads(*run)), D.run_window(*run) // D.TRACE
                eps = [x for x in W.ENDS if x != "r_in_old"]
                bad += [f"{rn}/{x}" for x in eps if e.get(f"{rn}/{x}", np.zeros(0)).shape != (nr, na, D.NCASE)]
                bad += [f"{rn}/{x}" for x in W.SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, D.NCASE)]
                bad += [f"{rn}/n_anc"] if e.get(f"{rn}/n_anc", np.zeros(0)).shape != (D.NCASE,) else []
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, D.NCASE) else []
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

    eq = {"params_AL_equal_be006": D.SIGNAL_ARMS["dial-AL"] == B6.SIGNAL_ARMS["dial-AL"]
          and D.SIGNAL_ARMS["never-AL"] == B6.SIGNAL_ARMS["never-AL"],
          "params_SL_equal_be006": D.SIGNAL_ARMS["dial-SL"] == B6.SIGNAL_ARMS["dial-SL"]
          and D.SIGNAL_ARMS["never-SL"] == B6.SIGNAL_ARMS["never-SL"]}
    for d_ in q3:
        eq.update(d_)
    checks["Q3_engine"] = {"pass": all(eq.values()), "items": eq}

    alias = {}
    for d_ in q5:
        alias.update(d_)
    checks["Q5_aliases_exact"] = {"pass": bool(alias) and all(alias.values()), "items": alias}

    bad = []
    for body, uu in D.tasks():
        raw, e = rawf(uu, body), shard(uu, body)
        pattern, _ = D.parse_unit(uu)
        cases, V0, ema0, R0, th, T = sim.prepare(pattern, lo, "engineering")
        for run in D.RUNS:
            rn = D.run_name(*run)
            ev = sim.event(run[0], run[1], cases, V0, ema0, R0, T, D.TAG)
            m, tgt = ev["m"], ev["target"]
            na = len(run[3])
            tile = lambda x: np.tile(x, (na, 1, 1))
            rf = raw[f"{rn}/r"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            Vf = raw[f"{rn}/V"].reshape(na * D.NCASE, D.SIDE, D.SIDE)
            got = {"r_all": S.sign(rf, tile(tgt)), "r_in": L5S.inside(rf, tile(tgt), tile(m)),
                   "v_in": L5S.inside(Vf, tile(tgt), tile(m)),
                   "n_anc_ok": (((rf > 0) == (tile(tgt) > 0)) & tile(m & ev["am"])).sum((-2, -1)).astype(float),
                   "r_out8": L5S.inside(rf, tile(tgt), tile(~B2S.footprint(m, 8)))}
            for dd in (0, 2, 4, 8):
                got[f"r_fp{dd}"] = L5S.inside(rf, tile(tgt), tile(B2S.footprint(m, dd)))
            for x, v in got.items():
                if not np.array_equal(v.reshape(na, D.NCASE), e[f"{rn}/{x}"][-1]):
                    bad.append(f"{uu}/{body}/{rn}/{x}")
    checks["Q6_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = {}
    eff["delays_round_m_t_star"] = all(RUNS[D.where(c, m_)[0]][2] == int(round(m_ * D.t_star(D.ETA_CAL)))
                                       and f"dial-{c}" in RUNS[D.where(c, m_)[0]][3] for c in D.CLOCKS for m_ in D.MULTS)
    sig_ok, rec_ok = True, True
    for body, uu in D.tasks():
        for blk in range(lo, hi):
            meta = json.loads(str(np.load(root / "shards" / body / uu / f"{blk}.npz")["__meta__"]))
            e = shard(uu, body, blk)
            for run in D.RUNS:
                rn = D.run_name(*run)
                for i, arm in enumerate(run[3]):
                    on, hit, anc = e[f"{rn}/onset"][i], e[f"{rn}/hit"][i], e[f"{rn}/anc_on"][i]
                    n_on = meta["signal_updates"][rn][arm] / D.NCASE
                    if D.SIGNAL_ARMS[arm]["never"]:
                        sig_ok &= n_on == 0
                        rec_ok &= bool((on == -1).all())
                    else:
                        sig_ok &= n_on == D.SIG["duration"]
                        rec_ok &= bool(((on >= 0) & (on <= 1)).all())
                    rec_ok &= bool(((hit >= 0) & (hit <= 1)).all() and (anc >= 0).all())
    eff["signal_on_for_exactly_its_updates"] = bool(sig_ok)
    eff["onset_for_dials_hit_and_sensors_for_all"] = bool(rec_ok)
    clock = True
    for e_ in (D.ETA, D.ETA_CAL):
        hb, nsteps = D.STRENGTH0, 0
        while hb > 0:
            hb, nsteps = hb + e_ * (-1.0 - hb), nsteps + 1
        clock &= nsteps == math.ceil(D.t_star(e_))
    eff["bond_crosses_zero_after_ceil_t_star"] = bool(clock)
    Tq = np.where((np.arange(D.SIDE) // 4) % 2 == 0, 1.2, -1.2)[None, :].repeat(D.SIDE, 0)[None]
    amq = np.zeros_like(Tq, bool)
    amq[0, ::2, ::2] = True
    mq = np.zeros(Tq.shape, bool)
    mq[0, 12:16, 12:16] = True
    Vq, rq = Tq.copy(), np.where(mq, -Tq, Tq)                   # a damaged record under a body that holds the pattern
    st = sim.new_state(1, mq)
    _, _, (comm, _), fix = sim.sig_targets(D.SIGNAL_ARMS["dial-AL-n"], Vq, rq, {"am": amq, "aval": np.sign(Tq)}, st, False)
    want = amq & mq & ~comm                                      # anchored, body and record disagree, not committed
    eff["arbiter_cells_are_the_anchored_disagreeing_uncommitted"] = bool(want.any() and np.array_equal(fix, want))
    eff["every_clock_commits_for_15000"] = all(p["tau_c"] == D.TAU_LONG for p in D.CLOCKS.values())
    zq = np.random.default_rng(1).standard_normal(2_000_000)
    cuts = {c: cut_for(p["rate"]) for c, p in D.CLOCKS.items()}
    eff["cuts_are_exact_quantiles"] = all(abs(NormalDist().cdf(-cuts[c]) - D.CLOCKS[c]["rate"]) <= 1e-12 for c in cuts)
    eff["quieter_flips_are_a_subset"] = bool(np.all(~(zq > cuts["AL-n"]) | (zq > cuts["AL-m"]))
                                             and np.all(~(zq > cuts["AL-m"]) | (zq > cuts["AL"])))
    checks["Q7_efficacy"] = {"pass": all(eff.values()), "items": eff}

    k0 = {c: RUNS["memory4@0"][3].index(f"dial-{c}") for c in D.CLOCKS}
    onsets, matched, own = {c: [] for c in k0}, [], {}
    for body, uu in D.tasks():
        pattern, _ = D.parse_unit(uu)
        for blk in range(lo, hi):
            e = shard(uu, body, blk)
            if (pattern, blk) not in own:
                own[(pattern, blk)] = static_onset(sim.prepare(pattern, blk, "engineering")[0])
            for c in k0:
                onsets[c].append(e["memory4@0/onset"][k0[c]])
            matched.append(own[(pattern, blk)])
    st8 = np.concatenate(matched)
    worst = {c: float(np.abs(np.concatenate(v) - st8).max()) for c, v in onsets.items()}
    checks["Q8_static_case_matched"] = {"pass": worst["AL"] <= 1e-6, "max_abs_onset_minus_case_static": worst["AL"],
                                        "reported_not_gated": {c: worst[c] for c in worst if c != "AL"},
                                        "prompt_onset_mean": float(np.concatenate(onsets["AL"]).mean()),
                                        "case_static_mean": float(st8.mean())}

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
    if not pred.exists():                       # before the freeze (debug runs): the draft statements, written to the root
        from be008.predict import STATEMENTS
        pred = root / "predictions_draft.json"
        pred.write_text(json.dumps({"status": "DRAFT_NOT_FROZEN", "statements": STATEMENTS}, indent=1) + "\n")
    proc = subprocess.run([sys.executable, "-m", "be008.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "be008.tables", "--out", str(out), "--predictions", str(pred)],
                           cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / f for f in ("contrasts_arms.csv", "summary_dw.json", "summary_li4.json", "traces.json",
                                  "predictions_scored.json", "TABLES.md")]
    stmts = [s["id"] for s in json.loads(pred.read_text())["statements"]] if pred.exists() else []
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and bool(stmts) and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes, "predictions": str(pred)}

    worst4, items4 = 0.0, {}
    for (uu, body, s, z, dl, arm, ci), (Vr, rr_, Hr_, Wr_) in q4:
        raw = rawf(uu, body)
        rn = D.run_name(s, z, dl)
        kk = RUNS[rn][3].index(arm)
        d = max(float(np.abs(Vr - raw[f"{rn}/V"][kk, ci]).max()), float(np.abs(rr_ - raw[f"{rn}/r"][kk, ci]).max()),
                float(np.abs(Hr_ - raw[f"{rn}/H"][kk, ci]).max()), float(np.abs(Wr_ - raw[f"{rn}/W"][kk, ci]).max()))
        items4[f"{uu}/{body}/{rn}/{arm}/case{ci}"], worst4 = d, max(worst4, d)
    pool.shutdown()
    checks["Q4_independent_replay"] = {"pass": worst4 <= 1e-8, "max_abs_difference": worst4, "items": items4}

    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_engine", "Q4_independent_replay", "Q5_aliases_exact",
             "Q6_reanalysis", "Q7_efficacy", "Q8_static_case_matched", "Q9_resources", "Q10_reader_dry_run"]
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
