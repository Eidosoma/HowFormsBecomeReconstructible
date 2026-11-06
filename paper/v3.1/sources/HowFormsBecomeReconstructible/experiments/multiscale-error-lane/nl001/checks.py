"""NL001's qualification checks, fixed before their results: python -m nl001.checks --root RUN_ROOT [--blocks LO,HI]
[--receipt PATH]. Run on the preflight blocks (900564-900565) at the full shape; on the debug blocks for rehearsal.

Q1  complete and finite at the declared shapes.
Q2  serial equals parallel: one task rerun in this process equals its saved shards bit for bit.
Q3  the engine: over 100 updates on a real case, L1 equals msegrid.record_step without a code and the absolute region
    code equals lr001.sim.step's gauge code (code 2, the same frame), bit for bit; the frame equals
    lr001.sim.gauge_frame on each 16 x 16 quarter's bonds.
Q4  the replay: one case of one branch (L1L2rL3 under B, and L1L2L3-k3x8 under C3), stepped site by site with explicit
    loops for 30 updates from the event's state, equals the batched run within 1e-12.
Q5  the aliases: with the block store right (none, F, R, K) the relative arm's final records equal the absolute arm's
    bit for bit; under none, F and R the derived arm's equal the absolute arm's within 1e-9 (its target is the same
    mean, summed apart; K zeroes the killed regions' codes, so there it differs by design).
Q6  reanalysis: the last read's endpoints recomputed from the saved final records equal the shards'.
Q7  efficacy: the templates (balanced blocks; 4 minority regions a block; 2 minority cells a region; content in the
    fine, regional and block bands) and every event's effect on the state (exact cells, bonds and stores changed; the
    frames unchanged except where K kills).
Q8  pairing, case-matched: a branch run twice in one batch ends identical, and a branch run alone equals its run in the
    full batch.
Q9  resources: the development forecast from this run's CPU per task.
Q10 the reader dry run, with every git file at 256 KB or less.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from lr001 import sim as LS  # noqa: E402
from msegrid.core import Stream, bproj, record_step  # noqa: E402
from nl001 import design as D  # noqa: E402
from nl001 import sim  # noqa: E402
from nl001.worker import task  # noqa: E402

N = D.SIDE


def load(root, event, block):
    with np.load(root / "shards" / event / f"{block}.npz") as z:
        ends = {k.split("/", 1)[1]: z[k] for k in z.files if k != "__meta__"}
    with np.load(root / "raw" / event / f"{block}.npz") as z:
        r = z[f"{event}/r"]
    return ends, r


def q1(root, blocks):
    missing, bad = [], []
    for e in D.EVENTS:
        for b in blocks:
            try:
                ends, r = load(root, e, b)
            except FileNotFoundError:
                missing.append(f"{e}/{b}")
                continue
            na = len(D.RUNS[e])
            if r.shape != (na, D.NCASE, N, N) or not np.isfinite(r).all():
                bad.append(f"{e}/{b}/r")
            for k in sim.ENDS:
                if ends[k].shape != (len(D.READS), na, D.NCASE) or not np.isfinite(ends[k]).all():
                    bad.append(f"{e}/{b}/{k}")
    return {"pass": not missing and not bad, "missing": missing, "bad": bad}


def q2(root, blocks, purpose):
    e, b = "C3", blocks[0]
    ends, raw, _ = task(e, b, purpose)
    se, sr = load(root, e, b)
    same = all(np.array_equal(ends[k], se[k], equal_nan=True) for k in sim.ENDS) and np.array_equal(raw["r"], sr)
    return {"pass": bool(same), "task": f"{e}/{b}"}


def q3(blocks, purpose):
    cases = sim.cases_for(blocks[0], purpose)[:1]
    T, R0, H, W, sigma, Bg, Brel, B3 = sim.prepare(cases)
    J = LS.halves(H, W)
    xs = Stream(D.TAG, cases, "record-noise", side=N).take(100)
    one = lambda v: np.full((1, 1, 1), v)
    a = b = c = d = R0.copy()
    for t in range(100):
        a = sim.step(a, xs[t], J, sigma, Bg, Brel, B3, one(0), one(0), one(D.KC), one(D.KC))
        b = record_step(b, xs[t], D.EPS, D.KR, D.SIGMA_R, 0.0, None, J)
        c = sim.step(c, xs[t], J, sigma, Bg, Brel, B3, one(1), one(0), one(D.KC), one(D.KC))
        d = LS.step(d, xs[t], J, np.full(1, 2), bproj(R0, D.REGION), Bg, sigma)
    frames = []
    for i in range(0, N, 16):
        for j in range(0, N, 16):
            h, w = H[..., i:i + 16, j:j + 16], W[..., i:i + 16, j:j + 16]
            frames.append(bool(np.array_equal(sim.gauge_frame(h, w), LS.gauge_frame(h, w))))
    items = {"L1_vs_record_step": bool(np.array_equal(a, b)), "L2abs_vs_lr001_gauge": bool(np.array_equal(c, d)),
             "frame_vs_lr001_quarters": all(frames)}
    return {"pass": all(items.values()), "items": items}


def replay(arm, event, block, purpose, window=30):
    """Site-by-site loops of one branch (case 0) from the event's state; returns the final records."""
    cases = sim.cases_for(block, purpose)
    T, R0, H0, W0, sigma0, Bg0, Brel0, B30 = sim.prepare(cases)
    u = sim.event_units(cases)[0]
    r, H, W, Bg, Brel, B3 = sim.apply_event(event, u, R0[0], H0[0], W0[0], Bg0[0], Brel0[0], B30[0], T[0])
    sigma = sim.gauge_frame(H, W)
    xs = Stream(D.TAG, cases, "record-noise", side=N).take(window)[:, 0]
    l2, l3 = sim.L2_ID[arm.l2], sim.L3_ID[arm.l3]
    R, Bk = D.REGION, D.BLOCK
    for t in range(window):
        new = np.empty_like(r)
        for i in range(N):
            for j in range(N):
                s = (W[(i - 1) % N, j] * r[(i - 1) % N, j] + W[i, j] * r[(i + 1) % N, j]
                     + H[i, (j - 1) % N] * r[i, (j - 1) % N] + H[i, j] * r[i, (j + 1) % N]) / 4.0
                new[i, j] = r[i, j] + D.EPS * (r[i, j] * (1 - (r[i, j] / D.R_STAR) ** 2) + D.KR * (s - r[i, j])) + D.SIGMA_R * xs[t, i, j]
        inc = np.zeros_like(r)
        if l2:
            for i0 in range(0, N, R):
                for j0 in range(0, N, R):
                    sl = (slice(i0, i0 + R), slice(j0, j0 + R))
                    live = (sigma[sl] != 0).sum()
                    mu = (sigma[sl] * new[sl]).sum() / max(live, 1.0)
                    tgt = Bg[i0, j0] if l2 == 1 else Brel[i0, j0] * np.sign(B3[i0, j0])
                    inc[sl] += arm.k2 * sigma[sl] * (tgt - mu)
        if l3:
            for i0 in range(0, N, Bk):
                for j0 in range(0, N, Bk):
                    sl = (slice(i0, i0 + Bk), slice(j0, j0 + Bk))
                    tgt = B3[i0, j0] if l3 == 1 else (sigma[sl] * Bg[sl]).mean()
                    inc[sl] += arm.k3 * (tgt - new[sl].mean())
        r = np.clip(new + inc, -2.0, 2.0)
    return r


def q4(blocks, purpose):
    items = {}
    for name, event in (("L1L2rL3", "B"), ("L1L2L3-k3x8", "C3")):
        arm = D.ARM[name]
        cases = sim.cases_for(blocks[0], purpose)
        _, rb = sim.run(cases, [(arm, event)], window=30, reads=(30,))
        rr = replay(arm, event, blocks[0], purpose)
        items[f"{name}/{event}"] = float(np.abs(rb[0, 0] - rr).max())
    return {"pass": all(v <= 1e-12 for v in items.values()), "max_abs_difference": max(items.values()), "items": items}


def q5(root, blocks):
    items = {}
    for e in ("none", "F", "R", "K"):
        for b in blocks:
            _, r = load(root, e, b)
            arms = list(D.RUNS[e])
            ra, rr, rd = r[arms.index("L1L2L3")], r[arms.index("L1L2rL3")], r[arms.index("L1L2L3d")]
            items[f"{e}/{b}/rel_is_abs"] = bool(np.array_equal(ra, rr))
            if e != "K":                       # K zeroes the killed regions' codes, so the derived mean differs there
                items[f"{e}/{b}/derived_near_abs"] = bool(np.abs(ra - rd).max() <= 1e-9)
    return {"pass": all(items.values()), "items": items}


def q6(root, blocks, purpose):
    mism = []
    for e in D.EVENTS:
        for b in blocks:
            ends, r = load(root, e, b)
            cases = sim.cases_for(b, purpose)
            T = D.AMPLITUDE * np.stack([sim.template(c) for c in cases])
            mk0 = sim.masks(T, sim.event_units(cases))
            na = len(D.RUNS[e])
            mk = {k: np.concatenate([v] * na) for k, v in mk0.items()}
            got = sim.read(r.reshape(na * D.NCASE, N, N), np.concatenate([T] * na), mk)
            for k in sim.ENDS:
                if not np.array_equal(got[k].reshape(na, D.NCASE), ends[k][-1], equal_nan=True):
                    mism.append(f"{e}/{b}/{k}")
    return {"pass": not mism, "mismatched": mism}


def q7(blocks, purpose):
    items = {}
    for b in blocks:
        cases = sim.cases_for(b, purpose)
        T, R0, H, W, sigma, Bg, Brel, B3 = sim.prepare(cases)
        units = sim.event_units(cases)
        for j, (c, u) in enumerate(zip(cases, units)):
            s = np.sign(T[j])
            blk = sim.unit_sign(T[j], D.BLOCK)
            reg = sim.unit_sign(T[j], D.REGION)
            key = f"{b}/{j}"
            items[f"{key}/balanced_blocks"] = int((blk > 0).sum()) == 8 and int((blk < 0).sum()) == 8
            up = D.BLOCK // D.REGION
            items[f"{key}/minority_regions"] = all(int((reg[bi * up:(bi + 1) * up, bj * up:(bj + 1) * up] != blk[bi, bj]).sum()) == D.MINORITY_REGIONS
                                                   for bi in range(4) for bj in range(4))
            regcells = np.repeat(np.repeat(reg, D.REGION, 0), D.REGION, 1)
            items[f"{key}/minority_cells"] = all(int((s[i:i + 4, k:k + 4] != regcells[i:i + 4, k:k + 4]).sum()) == D.MINORITY_CELLS
                                                 for i in range(0, N, 4) for k in range(0, N, 4))
            p4, p16 = bproj(s, D.REGION), bproj(s, D.BLOCK)
            items[f"{key}/bands"] = bool(((s - p4) ** 2).mean() > 0 and ((p4 - p16) ** 2).mean() > 0 and ((p16 - s.mean()) ** 2).mean() > 0)
            m_b = sim.unit_mask(*u["block"], D.BLOCK)
            items[f"{key}/R_outside_B"] = all(not m_b[ri * 4, rj * 4] for ri, rj in u["regions"]) and len(u["regions"]) == D.N_REGIONS
            items[f"{key}/F_count"] = int(u["fine"].sum()) == int(round(D.FINE_SHARE * N * N))
            for e in ("B", "R", "F", "C3", "C2", "K"):
                r, h, w, bg, brel, b3 = sim.apply_event(e, u, R0[j], H[j], W[j], Bg[j], Brel[j], B3[j], T[j])
                dr, dh, dw = (r != R0[j]), (h != H[j]), (w != W[j])
                dbg, drel, db3 = (bg != Bg[j]), (brel != Brel[j]), (b3 != B3[j])
                fr_same = np.array_equal(sim.gauge_frame(h, w), sigma[j])
                if e == "B":
                    ok = (np.array_equal(dr, m_b) and int(dh.sum() + dw.sum()) == 4 * D.BLOCK and np.array_equal(dbg, m_b)
                          and not drel.any() and not db3.any() and fr_same)
                elif e == "R":
                    m = np.zeros((N, N), bool)
                    for ri, rj in u["regions"]:
                        m |= sim.unit_mask(ri, rj, D.REGION)
                    ok = np.array_equal(dr, m) and int(dh.sum() + dw.sum()) <= 4 * D.REGION * D.N_REGIONS and not dbg.any() and fr_same
                elif e == "F":
                    ok = np.array_equal(dr, u["fine"]) and not dh.any() and not dw.any() and not dbg.any() and fr_same
                elif e == "C3":
                    ok = np.array_equal(db3, m_b) and not dr.any() and not dbg.any() and not drel.any() and fr_same
                elif e == "C2":
                    m = sim.unit_mask(*u["regions"][0], D.REGION)
                    ok = np.array_equal(dbg, m) and np.array_equal(drel, m) and not dr.any() and not db3.any() and fr_same
                else:
                    m = sim.kill_mask(u, T[j])
                    kr_ = sim.unit_sign(m * 1.0, D.REGION) > 0
                    ok = (int(m.sum()) == (D.KILL * D.REGION) ** 2 and bool((r[m] == 0).all()) and bool((bg[m] == 0).all())
                          and bool((kr_ & (reg != np.repeat(np.repeat(blk, up, 0), up, 1))).any()))
                items[f"{key}/{e}"] = bool(ok)
    return {"pass": all(items.values()), "n_items": len(items), "failed": [k for k, v in items.items() if not v]}


def q8(blocks, purpose):
    cases = sim.cases_for(blocks[0], purpose)
    arm = D.ARM["L1L2rL3"]
    ends2, r2 = sim.run(cases, [(arm, "FRB"), (arm, "FRB")], window=200, reads=(200,))
    full, rf = sim.run(cases, [(D.ARM[a], "FRB") for a in D.RUNS["FRB"]], window=200, reads=(200,))
    alone, ra = sim.run(cases, [(D.ARM["L1L2L3-k3x5"], "FRB")], window=200, reads=(200,))
    items = {"twice_identical": bool(np.array_equal(r2[0], r2[1])),
             "alone_equals_batch": bool(np.array_equal(ra[0], rf[list(D.RUNS["FRB"]).index("L1L2L3-k3x5")]))}
    return {"pass": all(items.values()), "items": items}


def q9(root, blocks):
    man = json.loads((root / "manifest.json").read_text())
    per_block = man["cpu_s_total"] / len(blocks)
    dev = len(range(*D.IDENTITIES["development"])) * per_block / 3600
    return {"pass": dev <= 25.0, "forecast_cpu_h": round(dev, 2), "forecast_wall_h": round(dev / 12 * 1.15, 2),
            "worker_rss_mb": man["worker_maxrss_mb_peak"], "bytes_per_task": man["bytes_written"] // max(len(man["tasks"]), 1)}


def q10(root, stage, blocks):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, "-m", "nl001.analyze", "--root", str(root), "--stage", stage, "--out", tmp]
        if stage == "preflight" and blocks[0] >= D.DEBUG_BLOCKS[0]:
            cmd += ["--blocks", f"{blocks[0]},{blocks[-1] + 1}"]
        p = subprocess.run(cmd, cwd=LANE, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        sizes = {f.name: f.stat().st_size for f in Path(tmp).iterdir()}
    git = [*(LANE / "nl001").rglob("*.py"), LANE / "tests" / "test_nl001.py", *(LANE / "probes").glob("p34*.py"),
           *(LANE / "probes" / "results").glob("p34*")]
    big = {str(f.relative_to(LANE)): f.stat().st_size for f in git if f.exists() and f.stat().st_size > 256_000}
    big.update({k: v for k, v in sizes.items() if v > 256_000})
    return {"pass": p.returncode == 0 and not big, "stderr": p.stderr[-2000:], "sizes": sizes, "too_big": big}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--blocks", default=None)
    ap.add_argument("--receipt", type=Path, default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    purpose = D.PURPOSE["preflight"]
    t0 = time.time()
    checks = {"Q1_complete_finite": q1(root, blocks), "Q2_serial_equals_parallel": q2(root, blocks, purpose),
              "Q3_engine": q3(blocks, purpose), "Q4_replay": q4(blocks, purpose), "Q5_aliases": q5(root, blocks),
              "Q6_reanalysis": q6(root, blocks, purpose), "Q7_efficacy": q7(blocks, purpose),
              "Q8_pairing_case_matched": q8(blocks, purpose), "Q9_resources": q9(root, blocks),
              "Q10_reader_dry_run": q10(root, "preflight", blocks)}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(),
               "root": str(root), "blocks": blocks, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    out = a.receipt or (root / "qualification_receipt.json")
    out.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}))


if __name__ == "__main__":
    main()
