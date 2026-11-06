"""NL002's qualification checks, fixed before their results: python -m nl002.checks --root RUN_ROOT [--blocks LO,HI]
[--receipt PATH]. Run on the preflight blocks (900808-900809) at the full shape; on the debug blocks for rehearsal.

Q1  complete and finite at the declared shapes (Amendment 1, 30 October 2026, the lead): every endpoint finite except
    k_spec_reg, where NaN falls exactly on the cases whose killed square holds no region in which A and B differ (the
    registration's undefined cases, from nl002.sim.masks on the case's templates and kill square), at every read and
    branch of those cases, and nowhere else; the receipt lists the undefined (unit, block, case) and their count.
Q2  serial equals parallel: one task (the store-only unit, the first block) rerun in this process equals its saved
    shards bit for bit.
Q3  the engine, bit for bit: (a) with NL001's exact references (R0 = AMPLITUDE x T, its frame codes, no read noise) and
    no cap, the store-only unit's own-k1 and off arms under none, R and (codes kept apart) equal nl001.sim.run's L1L2L3
    and L1 arms under none and R over the full window; (b) the bond relearning equals lr002.sim.relations' 'body'
    learning (no bond noise) on the dw unit's states; (c) the body step is dl001.sim.body, unchanged (imported).
Q4  the replay: one case of copy-k0.75 under K (dw) and of foreign-k2 under R (dw), stepped with explicit per-site loops
    (the record step with both codes and the cap, the frame, the relearning; dl001.sim.body for the body) for 30
    updates from the event's state, equals the batched run within 1e-12.
Q5  the aliases: the recipients reading A's acquired record, B's, and nothing are identical in both units (the same
    inputs and noise); with the cap removed, own-k0.25 under none equals its capped run bit for bit (the cap does not
    bind at the bottom of the sweep), while foreign-k2 under none differs (it binds at the top); the coded recipient of
    every 'off' branch equals its L1-only recipient bit for bit ('off' passes no codes).
Q6  reanalysis: the last read's endpoints recomputed from the saved final records (and bodies) equal the shards'.
Q7  efficacy: the templates (A = nl001.sim.template; B with A's block signs and the same minority counts); the codes
    (L2 exactly +-R*; the corrupt count equal to A's and B's sign-difference count); the events' exact effects (R: the
    four regions' record, body, moving average and boundary bonds flipped, nothing else; K: the square's record 0, its
    internal bonds 0, its body newborn, the codes untouched); the recipient's record unchanged in its bonds.
Q8  pairing: a label run alone equals its run in the full batch (50 updates, both units).
Q9  resources: the development forecast from this run's CPU per task.
Q10 the reader dry run, with every git file at 256 KB or less.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl001 import sim as DS  # noqa: E402
from lr001.sim import edges_from, halves  # noqa: E402
from lr002 import sim as L2S  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msegrid.core import Stream, bonds, bproj  # noqa: E402
from nl001 import design as N1  # noqa: E402
from nl001 import sim as N1S  # noqa: E402
from nl002 import design as D  # noqa: E402
from nl002 import sim  # noqa: E402
from nl002.worker import BRANCHES2, task  # noqa: E402

N = D.SIDE


def shard(root, unit, block):
    with np.load(root / "shards" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files if k != "__meta__"}


def rawfile(root, unit, block):
    with np.load(root / "raw" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files if k != "__meta__"}


UNDEF = "k_spec_reg"          # the one endpoint the registration declares undefined in some cases (Amendment 1)


def q1_shard(s, unit, kd_empty):
    """Amendment 1's Q1 on one shard: every endpoint at its declared shape and finite, except the k_spec_reg keys, where
    NaN must fall exactly on the cases whose killed square holds no region in which A and B differ (kd_empty, (cases,),
    from nl002.sim.masks on the case's templates and kill square), at every read and branch, and every other value must
    be finite. Returns the problems found."""
    nl, n2 = len(D.LABELS), len(BRANCHES2)
    bad = []
    for e in sim.ENDS:
        keys = [(f"t/r/{e}", (len(D.READS), nl, 8)), (f"s/{e}", (len(D.READS2), n2, 8)), (f"c/{e}", (len(D.READS2), nl, 8))]
        if unit == "dw":
            keys.append((f"t/v/{e}", (len(D.READS), nl, 8)))
        for key, shape in keys:
            if key not in s or s[key].shape != shape:
                bad.append((key, "shape", None if key not in s else s[key].shape))
                continue
            x = s[key]
            if e == UNDEF:
                want = np.broadcast_to(np.asarray(kd_empty, bool)[None, None, :], x.shape)
                if not np.array_equal(np.isnan(x), want) or not np.isfinite(x[~want]).all():
                    bad.append((key, "undefined cases differ from the empty kdreg masks"))
            elif not np.isfinite(x).all():
                bad.append((key, "non-finite"))
    if s["dose"].shape != (nl, 8) or not np.isfinite(s["dose"]).all():
        bad.append(("dose", "shape or non-finite"))
    return bad


def q1(root, blocks, purpose):
    bad, undefined = [], []
    for u in D.UNITS:
        for b in blocks:
            cases = sim.cases_for(b, purpose)
            TA, TB = sim.templates(cases, D.TAG)
            kd_empty = sim.masks(TA, TB, N1S.event_units(cases, D.TAG))["kdreg"].sum((-2, -1)) == 0
            undefined += [[u, b, int(j)] for j in np.where(kd_empty)[0]]
            bad += [(u, b) + tuple(x) for x in q1_shard(shard(root, u, b), u, kd_empty)]
    return {"pass": not bad, "bad": bad[:10], "undefined_unit_block_case": undefined, "n_undefined": len(undefined)}


def q2(root, blocks, purpose):
    ends, _, _, _ = task("none", blocks[0], purpose)
    s = shard(root, "none", blocks[0])
    diff = [k for k, v in ends.items() if not np.array_equal(np.asarray(v), s[k], equal_nan=True)]
    return {"pass": not diff, "differ": diff[:10]}


def bridge_prep(cases, tag):
    """NL001's exact references for the store-only unit."""
    T, R0, H0, W0, sigma, Bg0, Brel0, B30 = N1S.prepare(cases, tag)
    TA = np.sign(T)
    _, TB = sim.templates(cases, tag)
    refs = {x: (Bg0, B30) for x in ("own", "copy", "foreign", "corrupt", "off")}
    return {"TA": TA, "TB": TB, "V0": None, "E0": None, "R0": R0, "RB": R0, "th": np.zeros_like(R0), "refs": refs,
            "ncorrupt": np.zeros(len(cases), int)}


def q3(blocks, purpose):
    tag = D.TAG
    cases = sim.cases_for(blocks[0], purpose)
    P = bridge_prep(cases, tag)
    labels = [("own-k1", "none"), ("own-k1", "R"), ("off", "none"), ("off", "R")]
    _, _, final, _ = sim.run(cases, "none", labels=labels, prep=P, tag=tag, cap=np.inf)
    ref_labels = [(N1.ARM["L1L2L3"], "none"), (N1.ARM["L1L2L3"], "R"), (N1.ARM["L1"], "none"), (N1.ARM["L1"], "R")]
    _, r1 = N1S.run(cases, ref_labels, tag=tag)
    a = bool(np.array_equal(final["r"], r1))
    # (b) relearning against lr002.sim.relations' 'body' learning, no bond noise
    Pd = sim.prepare(cases, tag)
    rng = np.random.default_rng(0)
    H, W = edges_from(bonds(Pd["R0"], True))
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    V = Pd["V0"] + 0.3 * rng.standard_normal(Pd["V0"].shape)
    class C:
        rate, learn, parity = 0.0, "body", False
    PP = L2S.params([C()], len(cases))
    H2, W2, Hb2, Wb2, _ = L2S.relations(H, W, Hb, Wb, Pd["R0"], np.zeros_like(V), np.zeros_like(V), V, PP, 0.0, None, D.ETA)
    H3, W3, Hb3, Wb3 = sim.relearn(H, W, Hb, Wb, V)
    b = bool(all(np.array_equal(x, y) for x, y in ((H2, H3), (W2, W3), (Hb2, Hb3), (Wb2, Wb3))))
    c = sim.S.body is DS.body
    return {"pass": a and b and c, "nl001_bridge": a, "relearn_equals_lr002": b, "body_is_dl001": c}


def replay_case(unit, label, block, purpose, j=0, window=30, tag=D.TAG):
    """One case of one label stepped with explicit per-site loops, against the batched run."""
    cases = sim.cases_for(block, purpose)
    P = sim.prepare(cases, tag)
    out, _, final, _ = sim.run(cases, unit, labels=[label], prep=P, window=window, reads=(window,), tag=tag)
    arm, event = D.ARM[label[0]], label[1]
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    Bg, B3 = (x[j] for x in P["refs"][arm.ref])
    r, H, W, V, E = P["R0"][j], H0[j], W0[j], P["V0"][j], P["E0"][j]
    body = unit == "dw"
    if event == "R":
        r, H, W, V, E = sim.apply_R(units[j], r, H, W, V if body else None, E if body else None)
    elif event == "K":
        r, H, W, V, E = sim.apply_K(units[j], P["TA"][j], cases[j], r, H, W, V if body else None, E if body else None, tag)
    r, H, W = r.copy(), H.copy(), W.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    k2, k3 = arm.k2 * D.KC, arm.k3 * D.KC
    p = replace(NATIVE, sigma=D.SIGMA)
    xs = Stream(tag, cases, "record-noise", side=N)
    zs = Stream(tag, cases, "future", side=N)
    xb, zb = xs.take(window), zs.take(window)
    zero = np.zeros((N, N))
    for t in range(window):
        if body:
            V, E, _, _, _ = DS.body(V, E, r, zero, zb[t][j], p, D.GAIN, 0.0, None)
        sig = N1S.gauge_frame(H, W)
        J = halves(H, W)
        # the record step, site by site
        rn = np.empty_like(r)
        for i in range(N):
            for c in range(N):
                up, dn, lf, rt = r[(i - 1) % N, c], r[(i + 1) % N, c], r[i, (c - 1) % N], r[i, (c + 1) % N]
                bs = (J[0][i, c] * up + J[1][i, c] * dn + J[2][i, c] * lf + J[3][i, c] * rt) / 4.0
                rn[i, c] = r[i, c] + D.EPS * (r[i, c] * (1 - (r[i, c] / D.R_STAR) ** 2) + D.KR * (bs - r[i, c])) + D.SIGMA_R * xb[t][j][i, c]
        out_r = np.empty_like(r)
        for i in range(N):
            for c in range(N):
                ri, rj = i // D.REGION, c // D.REGION
                sl = (slice(ri * D.REGION, (ri + 1) * D.REGION), slice(rj * D.REGION, (rj + 1) * D.REGION))
                live = (sig[sl] != 0).mean()
                mean_u = (sig[sl] * rn[sl]).mean() / max(live, 1.0 / D.REGION ** 2)
                bi, bj = i // D.BLOCK, c // D.BLOCK
                bm = rn[bi * D.BLOCK:(bi + 1) * D.BLOCK, bj * D.BLOCK:(bj + 1) * D.BLOCK].mean()
                inc = k2 * sig[i, c] * (Bg[i, c] - mean_u) + k3 * (B3[i, c] - bm)
                inc = min(max(inc, -D.CAP), D.CAP)
                out_r[i, c] = min(max(rn[i, c] + inc, -2.0), 2.0)
        r = out_r
        if body:
            for i in range(N):
                for c in range(N):
                    xh = min(max(V[i, c] * V[i, (c + 1) % N], -1), 1)
                    xw = min(max(V[i, c] * V[(i + 1) % N, c], -1), 1)
                    Hb[i, c] = Hb[i, c] + D.ETA * (xh - Hb[i, c])
                    Wb[i, c] = Wb[i, c] + D.ETA * (xw - Wb[i, c])
                    if Hb[i, c] != 0:
                        H[i, c] = np.sign(Hb[i, c])
                    if Wb[i, c] != 0:
                        W[i, c] = np.sign(Wb[i, c])
    dr = float(np.abs(r - final["r"][0, j]).max())
    dv = float(np.abs(V - final["V"][0, j]).max()) if body else 0.0
    db = int((H != final["H"][0, j]).sum() + (W != final["W"][0, j]).sum())
    return dr, dv, db


def q4(blocks, purpose):
    res = {}
    for label in (("copy-k0.75", "K"), ("foreign-k2", "R")):
        dr, dv, db = replay_case("dw", label, blocks[0], purpose)
        res["/".join(label)] = {"max_dr": dr, "max_dv": dv, "bonds_differ": db}
    ok = all(v["max_dr"] <= 1e-12 and v["max_dv"] <= 1e-12 and v["bonds_differ"] == 0 for v in res.values())
    return {"pass": ok, **res}


def q5(root, blocks, purpose):
    i2 = {nm: i for i, nm in enumerate(BRANCHES2)}
    same = True
    for b in blocks:
        sw, sn = shard(root, "dw", b), shard(root, "none", b)
        for e in sim.ENDS:
            for nm in ("acqA", "acqB", "none"):
                if not np.array_equal(sw[f"s/{e}"][:, i2[nm]], sn[f"s/{e}"][:, i2[nm]], equal_nan=True):
                    same = False
    cases = sim.cases_for(blocks[0], purpose)
    P = sim.prepare(cases, D.TAG)
    lab_lo, lab_hi = [("own-k0.25", "none")], [("foreign-k2", "none")]
    _, _, f1, _ = sim.run(cases, "none", labels=lab_lo, prep=P, window=200, reads=(200,))
    _, _, f2, _ = sim.run(cases, "none", labels=lab_lo, prep=P, window=200, reads=(200,), cap=np.inf)
    _, _, f3, _ = sim.run(cases, "none", labels=lab_hi, prep=P, window=200, reads=(200,))
    _, _, f4, _ = sim.run(cases, "none", labels=lab_hi, prep=P, window=200, reads=(200,), cap=np.inf)
    lo_same, hi_differs = bool(np.array_equal(f1["r"], f2["r"])), bool(not np.array_equal(f3["r"], f4["r"]))
    coded_off = True
    for u in D.UNITS:
        for b in blocks:
            s_ = shard(root, u, b)
            for e in sim.ENDS:
                for ev in D.EVENTS:
                    j = D.LABELS.index(("off", ev))
                    if not np.array_equal(s_[f"c/{e}"][:, j], s_[f"s/{e}"][:, j], equal_nan=True):
                        coded_off = False
    return {"pass": same and lo_same and hi_differs and coded_off, "recipients_alike_across_units": same,
            "cap_idle_at_k0.25": lo_same, "cap_binds_at_k2": hi_differs, "coded_off_equals_l1_only": coded_off}


def q6(root, blocks, purpose):
    worst = 0.0
    for u in D.UNITS:
        b = blocks[0]
        s, raw = shard(root, u, b), rawfile(root, u, b)
        cases = sim.cases_for(b, purpose)
        TA, TB = raw["TA"].astype(float), raw["TB"].astype(float)
        mk = sim.masks(TA, TB, N1S.event_units(cases, D.TAG))
        nb = len(D.LABELS)
        mkb = {k: np.concatenate([v] * nb) for k, v in mk.items()}
        for w, x in (("r", raw["r"]),) + ((("v", raw["V"]),) if u == "dw" else ()):
            sc = sim.score(x.reshape(nb * 8, N, N).astype(float), mkb)
            for e, v in sc.items():
                d = np.nanmax(np.abs(v.reshape(nb, 8) - s[f"t/{w}/{e}"][-1]))
                worst = max(worst, 0.0 if np.isnan(d) else float(d))
    # the saved records are float32: a sign flip at |r| < 1e-6 is the only possible difference
    return {"pass": worst <= 1e-9, "max_abs_diff": worst}


def q7(blocks, purpose):
    tag, b = D.TAG, blocks[0]
    cases = sim.cases_for(b, purpose)
    TA, TB = sim.templates(cases, tag)
    ok = {}
    ok["A_is_nl001"] = bool(all(np.array_equal(TA[j], N1S.template(c, tag)) for j, c in enumerate(cases)))
    ok["B_blocks_match"] = bool(np.array_equal(N1S.unit_sign(TA, D.BLOCK), N1S.unit_sign(TB, D.BLOCK)))
    regA, regB = N1S.unit_sign(TA, D.REGION), N1S.unit_sign(TB, D.REGION)
    up = D.BLOCK // D.REGION
    blk = np.repeat(np.repeat(N1S.unit_sign(TA, D.BLOCK), up, -2), up, -1)
    cnt = lambda reg: (reg != blk).reshape(len(cases), 4, up, 4, up).sum(axis=(2, 4))
    ok["minority_regions_4_each"] = bool((cnt(regA) == 4).all() and (cnt(regB) == 4).all())
    mc = lambda T, reg: (np.sign(T) != np.repeat(np.repeat(reg, D.REGION, -2), D.REGION, -1)).reshape(len(cases), 16, 4, 16, 4).sum(axis=(2, 4))
    ok["minority_cells_2_each"] = bool((mc(TA, regA) == 2).all() and (mc(TB, regB) == 2).all())
    P = sim.prepare(cases, tag)
    BgA, BgB, BgC = P["refs"]["own"][0], P["refs"]["foreign"][0], P["refs"]["corrupt"][0]
    ok["L2_is_pm_Rstar"] = bool(all(np.allclose(np.abs(x), D.R_STAR) for x in (BgA, BgB, BgC, P["refs"]["copy"][0])))
    nd = (np.sign(BgA[:, ::4, ::4]) != np.sign(BgB[:, ::4, ::4])).sum((1, 2))
    nc = (np.sign(BgA[:, ::4, ::4]) != np.sign(BgC[:, ::4, ::4])).sum((1, 2))
    ok["corrupt_count_matched"] = bool(np.array_equal(nd, nc) and np.array_equal(nd, P["ncorrupt"]))
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    j = 0
    r, H, W, V, E = sim.apply_R(units[j], P["R0"][j], H0[j], W0[j], P["V0"][j], P["E0"][j])
    m = np.zeros((N, N), bool)
    for (ri, rj) in units[j]["regions"]:
        m |= N1S.unit_mask(ri, rj, D.REGION)
    bh, bw = m ^ np.roll(m, -1, -1), m ^ np.roll(m, -1, -2)
    ok["R_exact"] = bool(np.array_equal(r, np.where(m, -P["R0"][j], P["R0"][j])) and np.array_equal(V, np.where(m, -P["V0"][j], P["V0"][j]))
                         and np.array_equal(E, np.where(m, -P["E0"][j], P["E0"][j])) and np.array_equal(H, np.where(bh, -H0[j], H0[j]))
                         and np.array_equal(W, np.where(bw, -W0[j], W0[j])))
    r, H, W, V, E = sim.apply_K(units[j], P["TA"][j], cases[j], P["R0"][j], H0[j], W0[j], P["V0"][j], P["E0"][j], tag)
    km = N1S.kill_mask(units[j], P["TA"][j])
    ok["K_exact"] = bool((r[km] == 0).all() and np.array_equal(r[~km], P["R0"][j][~km])
                         and (H[km & np.roll(km, -1, -1)] == 0).all() and (W[km & np.roll(km, -1, -2)] == 0).all()
                         and np.array_equal(V[~km], P["V0"][j][~km]) and not np.array_equal(V[km], P["V0"][j][km])
                         and bool(N1S.unit_sign(km * 1.0, D.REGION).sum() == 4))
    return {"pass": all(ok.values()), **ok}


def q8(blocks, purpose):
    cases = sim.cases_for(blocks[0], purpose)
    P = sim.prepare(cases, D.TAG)
    res = {}
    for u in D.UNITS:
        _, _, fa, _ = sim.run(cases, u, prep=P, window=50, reads=(50,))
        pick = D.LABELS.index(("copy-k0.75", "K"))
        _, _, f1, _ = sim.run(cases, u, labels=[D.LABELS[pick]], prep=P, window=50, reads=(50,))
        res[u] = bool(np.array_equal(fa["r"][pick], f1["r"][0]))
    return {"pass": all(res.values()), **res}


def q9(root, blocks):
    man = json.loads((root / "manifest.json").read_text())
    per_block = man["cpu_s_total"] / len(blocks)
    dev = len(range(*D.IDENTITIES["development"])) * per_block / 3600
    return {"pass": dev <= 35.0, "forecast_cpu_h": round(dev, 2), "forecast_wall_h_12": round(dev / 12 * 1.15, 2),
            "worker_rss_mb": man["worker_maxrss_mb_peak"], "bytes_per_task": man["bytes_written"] // max(len(man["tasks"]), 1)}


def q10(root, stage, blocks):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, "-m", "nl002.analyze", "--root", str(root), "--stage", stage, "--out", tmp]
        if stage == "preflight" and blocks[0] >= D.DEBUG_BLOCKS[0]:
            cmd += ["--blocks", f"{blocks[0]},{blocks[-1] + 1}"]
        p = subprocess.run(cmd, cwd=LANE, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        sizes = {f.name: f.stat().st_size for f in Path(tmp).iterdir()}
    git = [*(LANE / "nl002").rglob("*.py"), LANE / "tests" / "test_nl002.py", *(LANE / "probes").glob("p40*.py"),
           *(LANE / "probes" / "results").glob("p40*")]
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
    checks = {"Q1_complete_finite": q1(root, blocks, purpose), "Q2_serial_equals_parallel": q2(root, blocks, purpose),
              "Q3_engine": q3(blocks, purpose), "Q4_replay": q4(blocks, purpose), "Q5_aliases": q5(root, blocks, purpose),
              "Q6_reanalysis": q6(root, blocks, purpose), "Q7_efficacy": q7(blocks, purpose),
              "Q8_pairing": q8(blocks, purpose), "Q9_resources": q9(root, blocks),
              "Q10_reader_dry_run": q10(root, "preflight", blocks)}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(),
               "root": str(root), "blocks": blocks, "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    out = a.receipt or (root / "qualification_receipt.json")
    out.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}))


if __name__ == "__main__":
    main()
