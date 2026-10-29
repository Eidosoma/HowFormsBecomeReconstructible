"""Qualification of LR001 on the preflight (engineering) shards; criteria fixed in advance.

python -m lr001.checks --root PREFLIGHT_ROOT --cpus LIST [--blocks LO,HI]   (writes frozen/qualification_receipt.json)

Q1  complete and finite (NaN only where a case has no scored sites)
Q2  serial = parallel: one task per panel rerun in-process gives bit-identical shards
Q3  engine equivalence, bit for bit: panel C's 'none' and 'plain' codes equal gw001.sim.simulate_R's rel and rel+code
    arms (flipped and killed 8 x 8 patches); panel L without scar and learning equals gw001.sim.simulate_B with a rel arm
Q4  independent replay: per-site loops with their own bonds, flux, parity, Hebbian learning, gauge frame, codes, turnover
    and body reproduce four branches (E, C, T, L) within 1e-9 (record and body) and exactly (bonds)
Q5  units and aliases: template bonds have no flux; one flipped bond gives two frustrated plaquettes and parity restores
    it; the gauge frame on intact bonds is s_i s_corner; 'hybrid+trust' equals 'hybrid' exactly on flips and kills
Q6  bond noise: each E branch's empirical flip rate per bond per update is within 3 SE of p_b
Q7  reanalysis: final-read endpoints recomputed from the saved final states equal the saved ones
Q8  efficacy: every patch covers its declared sites; wounds act as declared; turnover counts equal the scheduled events
Q9  resources: forecast development wall <= 12 h on 12 workers with RAM and disk headroom
Q10 reader dry run: analyze and tables complete, every statement scored, every git file <= 256 KB
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
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

from gw001 import design as GD  # noqa: E402
from gw001 import sim as GS  # noqa: E402
from lr001 import design as D  # noqa: E402
from lr001 import sim  # noqa: E402
from lr001 import worker as W  # noqa: E402
from mse.native import NATIVE, address, center  # noqa: E402

FROZEN = LANE / "lr001" / "frozen"
BLOCK = D.IDENTITIES["preflight"][0]
WORKERS = 12
N = D.SIDE
NAN_OK = {"minority", "majority", "kept", "kept_min", "kept_maj", "record_kept", "body_kept"}


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


# Independent per-site implementations ------------------------------------------------------------------------------

def s_record(r, xi, H, W, code=None, B=None, Bg=None, frame=None):
    """One record step per site: self-correction through the edge bonds, then the code, one clip."""
    n = N
    out = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            ns = (W[(i - 1) % n, j] * r[(i - 1) % n, j] + W[i, j] * r[(i + 1) % n, j]
                  + H[i, (j - 1) % n] * r[i, (j - 1) % n] + H[i, j] * r[i, (j + 1) % n]) / 4.0
            x = r[i, j]
            out[i, j] = x + D.EPS * (x * (1 - (x / D.R_STAR) ** 2) + D.KR * (ns - x)) + D.SIGMA_R * xi[i, j]
    if code in ("plain", "hybrid"):
        res = out.copy()
        for i0 in range(0, n, 4):
            for j0 in range(0, n, 4):
                blk = out[i0:i0 + 4, j0:j0 + 4]
                plain_mean = blk.mean()
                fr = frame[i0:i0 + 4, j0:j0 + 4]
                live = fr != 0
                mean_u = (fr * blk).sum() / max(live.sum(), 1)
                for a in range(4):
                    for b in range(4):
                        pl = D.KC * (B[i0 + a, j0 + b] - plain_mean)
                        if code == "plain" or not live[a, b]:
                            res[i0 + a, j0 + b] = blk[a, b] + pl
                        else:
                            res[i0 + a, j0 + b] = blk[a, b] + D.KC * fr[a, b] * (Bg[i0 + a, j0 + b] - mean_u)
        out = res
    return np.clip(out, -2.0, 2.0)


def s_frame(H, W):
    fr = np.zeros((N, N))
    for i0 in range(0, N, 4):
        for j0 in range(0, N, 4):
            fr[i0, j0] = 1.0
            for j in range(j0, j0 + 3):
                fr[i0, j + 1] = fr[i0, j] * H[i0, j]
            for i in range(i0, i0 + 3):
                for j in range(j0, j0 + 4):
                    fr[i + 1, j] = fr[i, j] * W[i, j]
    return fr


def s_flux(H, W):
    F = np.empty((N, N))
    for i in range(N):
        for j in range(N):
            F[i, j] = H[i, j] * W[i, (j + 1) % N] * H[(i + 1) % N, j] * W[i, j]
    return F


def s_parity(H, W):
    F = s_flux(H, W)
    H2, W2 = H.copy(), W.copy()
    for i in range(N):
        for j in range(N):
            if F[i, j] < 0 and F[(i - 1) % N, j] < 0:
                H2[i, j] = -H[i, j]
            if F[i, j] < 0 and F[i, (j - 1) % N] < 0:
                W2[i, j] = -W[i, j]
    return H2, W2


def s_bonds(R0):
    s = np.where(R0 >= 0, 1.0, -1.0)
    H, W = np.empty((N, N)), np.empty((N, N))
    for i in range(N):
        for j in range(N):
            H[i, j] = s[i, j] * s[i, (j + 1) % N]
            W[i, j] = s[i, j] * s[(i + 1) % N, j]
    return H, W


def s_hebb(Hb, Wb, x, eta, scale):
    for i in range(N):
        for j in range(N):
            Hb[i, j] += eta * (min(1.0, max(-1.0, x[i, j] * x[i, (j + 1) % N] / scale)) - Hb[i, j])
            Wb[i, j] += eta * (min(1.0, max(-1.0, x[i, j] * x[(i + 1) % N, j] / scale)) - Wb[i, j])
    return Hb, Wb


def s_block_mean(x):
    out = np.empty_like(x)
    for i0 in range(0, N, 4):
        for j0 in range(0, N, 4):
            out[i0:i0 + 4, j0:j0 + 4] = x[i0:i0 + 4, j0:j0 + 4].mean()
    return out


def replay_E(case, R0, rate, ci):
    """Branch 'rate/both', one case: bond noise, record step, Hebbian relearning from the record, parity."""
    H, W = s_bonds(R0)
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    r = R0.copy()
    gx, gz = address(D.TAG, *case.key(), "record-noise", "E"), address(D.TAG, *case.key(), "bond-noise")
    from scipy.special import ndtri
    cut = float(ndtri(1.0 - rate))
    for t in range(1, D.E_WINDOW + 1):
        i = (t - 1) % 100
        if i == 0:
            xs, zs = gx.standard_normal((100, N, N)), gz.standard_normal((100, N, N))
        for a in range(N):
            for b in range(N):
                if zs[i, a, b] > cut:
                    H[a, b], Hb[a, b] = -H[a, b], -Hb[a, b]
                if zs[i, a, b] < -cut:
                    W[a, b], Wb[a, b] = -W[a, b], -Wb[a, b]
        r = s_record(r, xs[i], H, W)
        Hb, Wb = s_hebb(Hb, Wb, r, D.ETA, D.R_STAR ** 2)
        H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
        H, W = s_parity(H, W)
        Hb = np.where(np.sign(Hb) * H < 0, -Hb, Hb)
        Wb = np.where(np.sign(Wb) * W < 0, -Wb, Wb)
    return r, H, W


def replay_C(case, R0, mask, wound, code, trust):
    H, W = s_bonds(R0)
    Bc = s_block_mean(R0)
    Bg = s_block_mean(s_frame(H, W) * R0)
    r = R0.copy()
    tH, tW = np.ones((N, N), bool), np.ones((N, N), bool)
    for a in range(N):
        for b in range(N):
            if mask[a, b]:
                r[a, b] = -r[a, b] if wound == "flip" else 0.0
    if wound in ("kill", "relink"):
        for a in range(N):
            for b in range(N):
                if mask[a, b] and mask[a, (b + 1) % N]:
                    H[a, b] = 1.0 if wound == "relink" else 0.0
                    tH[a, b] = False
                if mask[a, b] and mask[(a + 1) % N, b]:
                    W[a, b] = 1.0 if wound == "relink" else 0.0
                    tW[a, b] = False
    Hf = np.where(tH, H, 0.0) if trust else H
    Wf = np.where(tW, W, 0.0) if trust else W
    frame = s_frame(Hf, Wf)
    gx = address(D.TAG, *case.key(), "record-noise")
    for t in range(1, D.C_WINDOW + 1):
        i = (t - 1) % 250
        if i == 0:
            xs = gx.standard_normal((250, N, N))
        r = s_record(r, xs[i], H, W, code, Bc, Bg, frame)
    return r


def replay_T(case, R0, rate, mode):
    """Branch 'rate/mode' under the hybrid code with trust flags (mode inherit or default)."""
    H, W = s_bonds(R0)
    Bc = s_block_mean(R0)
    Bg = s_block_mean(s_frame(H, W) * R0)
    tH, tW = np.ones((N, N), bool), np.ones((N, N), bool)
    r = R0.copy()
    g = address(D.TAG, *case.key(), "turnover", f"{rate:g}")
    n = int(g.poisson(rate * D.T_WINDOW * N * N))
    tt, site = g.integers(1, D.T_WINDOW + 1, n), g.integers(0, N * N, n)
    o = np.argsort(tt, kind="stable")
    tt, site = tt[o], site[o]
    gx = address(D.TAG, *case.key(), "record-noise", "T")
    k = 0
    for t in range(1, D.T_WINDOW + 1):
        i = (t - 1) % 250
        if i == 0:
            xs = gx.standard_normal((250, N, N))
        frame = s_frame(np.where(tH, H, 0.0), np.where(tW, W, 0.0))
        r = s_record(r, xs[i], H, W, "hybrid", Bc, Bg, frame)
        while k < len(tt) and tt[k] == t:
            a, b = divmod(int(site[k]), N)
            r[a, b] = 0.0
            if mode == "default":
                for x, y, is_h in ((a, b, True), (a, (b - 1) % N, True), (a, b, False), ((a - 1) % N, b, False)):
                    if is_h:
                        H[x, y], tH[x, y] = 1.0, False
                    else:
                        W[x, y], tW[x, y] = 1.0, False
            k += 1
    return r, H, W


def s_body(V, ema, r, th, z, p, gain):
    drift = np.empty((N, N))
    for i in range(N):
        for j in range(N):
            nb = (V[(i - 1) % N, j] + V[(i + 1) % N, j] + V[i, (j - 1) % N] + V[i, (j + 1) % N]) / 4.0
            drift[i, j] = V[i, j] - V[i, j] ** 3 + p.well_asym + th[i, j] + p.coupling * (nb - V[i, j])
    Vt = np.clip(V + p.dt * center(drift) + center(p.sigma * z), -2.0, 2.0)
    ema = (1 - p.ema_rate) * ema + p.ema_rate * Vt
    d = center(gain * (r - Vt))
    return np.clip(Vt + p.dt * d, -2.0, 2.0), ema


def replay_L(case, V, ema, R0, th, T, mask, learn):
    H, W = s_bonds(R0)
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    p = replace(NATIVE, sigma=D.L_SIGMA)
    eta = {"none": 0.0, "record": D.ETA, "body": D.ETA, "body_slow": D.ETA_SLOW}[learn]
    v, e, r = V.copy(), ema.copy(), R0.copy()
    gz, gx = address(D.TAG, *case.key(), "future"), address(D.TAG, *case.key(), "record-noise")
    for t in range(1, D.L_WINDOW + 1):
        i = (t - 1) % 500
        if i == 0:
            zs, xs = gz.standard_normal((500, N, N)), gx.standard_normal((500, N, N))
        if t <= D.L_SCAR_UNTIL:
            v = np.where(mask, -T, v)
        v, e = s_body(v, e, r, th, zs[i], p, NATIVE.gain)
        r = s_record(r, xs[i], H, W)
        if eta:
            x = v if learn.startswith("body") else r / D.R_STAR
            Hb, Wb = s_hebb(Hb, Wb, x, eta, 1.0)
            H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
    return v, r, H, W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--blocks", default=None)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("preflight", None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    lo, hi = blocks[0], blocks[-1] + 1
    global BLOCK
    BLOCK = lo
    receipt_path = FROZEN / "qualification_receipt.json" if a.blocks is None else root / "debug_qualification_receipt.json"
    manifest = json.loads((root / "manifest.json").read_text())
    rawf = lambda p, u, b=lo: npz(root / "raw" / p / u / f"{b}.npz")
    shard = lambda p, u, b=lo: npz(root / "shards" / p / u / f"{b}.npz")
    checks = {}

    missing = []
    for p, u in D.tasks():
        nb = len(D.branches(p))
        for b in range(lo, hi):
            path = root / "shards" / p / u / f"{b}.npz"
            if not path.exists():
                missing.append(f"{p}/{u}/{b}")
                continue
            e = npz(path)
            for k, v in e.items():
                ep = k.split("/")[-1]
                if np.isinf(v).any() or (np.isnan(v).any() and ep not in NAN_OK):
                    missing.append(f"{p}/{u}/{b}/{k}")
                if p != "A" and v.ndim == 3 and v.shape[1:] != (nb, D.NCASE):
                    missing.append(f"{p}/{u}/{b}/{k}/shape")
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10]}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    for p in D.PANELS:
        u = D.PANELS[p]["units"][-1]
        W.run_task(p, u, lo, "engineering", str(serial))
        x, y = npz(root / "shards" / p / u / f"{lo}.npz"), npz(serial / "shards" / p / u / f"{lo}.npz")
        same[f"{p}/{u}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k], equal_nan=True) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    eq = {}
    for fam in ("F0", "IS"):
        cases, V, ema, R0, th, T = sim.prepare(fam, lo, "engineering")
        k = len(cases)
        m8 = sim.patch(cases, 8)
        cg = (GD.Cond("f8", "flip", 8), GD.Cond("k8", "kill", 8))
        conds = (D.Cond("flip8", "flip", 8), D.Cond("kill8", "kill", 8))
        _, fin = sim.simulate_C(cases, R0, T, {8: m8}, window=2000, reads=(2000,), codes=("none", "plain"), conds=conds)
        for ci, (code, garm) in enumerate((("none", GD.Arm("rel", eps=GD.EPS, rel=True)),
                                           ("plain", GD.Arm("rel+code", eps=GD.EPS, kc=GD.KC, rel=True)))):
            rg, _, _ = GS.simulate_R(garm, cg, k, R0, T, [m8, m8], cases, 2000, 250, tag=D.TAG)
            eq[f"{fam}/C_{code}=gw001_{garm.name}"] = bool(np.array_equal(fin["r"][2 * ci:2 * ci + 2].reshape(-1, N, N), rg))
        p = replace(NATIVE, sigma=D.L_SIGMA)
        vb, _, rb, _ = GS.simulate_B(GD.Arm("rel", eps=GD.EPS, rel=True), (GD.Cond("sham"),), k, V, ema, R0, th, T, p, True,
                                     [None], [None], cases, 1000, 500, tag=D.TAG)
        _, finL = sim.simulate_L(cases, V, ema, R0, th, T, window=1000, reads=(1000,), learns=("none",), scar_until=0)
        eq[f"{fam}/L_none_noscar=gw001_simulate_B_rel"] = bool(np.array_equal(finL["v"][0], vb) and np.array_equal(finL["r"][0], rb))
    checks["Q3_engine_equivalence"] = {"pass": all(eq.values()), "items": eq}

    worst, items = 0.0, {}
    bond_ok = True
    from mse.assay import enrol
    cases_all = enrol([lo], D.MESSAGES, D.PARENTS, "engineering")
    # E
    cases, V, ema, R0, th, T = sim.prepare("IS", lo, "engineering")
    ci, br = 0, "0.001/both"
    r, H, W_ = replay_E(cases[ci], R0[ci], 0.001, ci)
    raw = rawf("E", "IS")
    bi = D.branches("E").index(br)
    d = float(np.abs(r - raw["r"][bi, ci]).max())
    bond_ok &= bool(np.array_equal(H, raw["H"][bi, ci]) and np.array_equal(W_, raw["W"][bi, ci]))
    items[f"E/IS/{br}/case{ci}"], worst = d, max(worst, d)
    # C
    ci, br = 1, "hybrid+trust/relink8"
    m8 = sim.patch(cases, 8)
    r = replay_C(cases[ci], R0[ci], m8[ci], "relink", "hybrid", True)
    raw = rawf("C", "IS")
    bi = D.branches("C").index(br)
    d = float(np.abs(r - raw["r"][bi, ci]).max())
    items[f"C/IS/{br}/case{ci}"], worst = d, max(worst, d)
    # T
    casesB, VB, emaB, R0B, thB, TB = sim.prepare("BL", lo, "engineering")
    ci, br = 2, "0.003/default"
    r, H, W_ = replay_T(casesB[ci], R0B[ci], 0.003, "default")
    raw = rawf("T", "BL")
    bi = D.branches("T").index(br)
    d = float(np.abs(r - raw["r"][bi, ci]).max())
    bond_ok &= bool(np.array_equal(H, raw["H"][bi, ci]) and np.array_equal(W_, raw["W"][bi, ci]))
    items[f"T/BL/{br}/case{ci}"], worst = d, max(worst, d)
    # L
    casesF, VF, emaF, R0F, thF, TF = sim.prepare("F0", lo, "engineering")
    ci, br = 3, "body"
    mask = sim.patch(casesF, D.L_SCAR)[ci]
    v, r, H, W_ = replay_L(casesF[ci], VF[ci], emaF[ci], R0F[ci], thF[ci], TF[ci], mask, "body")
    raw = rawf("L", "F0")
    bi = D.branches("L").index(br)
    d = max(float(np.abs(r - raw["r"][bi, ci]).max()), float(np.abs(v - raw["v"][bi, ci]).max()))
    bond_ok &= bool(np.array_equal(H, raw["H"][bi, ci]) and np.array_equal(W_, raw["W"][bi, ci]))
    items[f"L/F0/{br}/case{ci}"], worst = d, max(worst, d)
    checks["Q4_independent_replay"] = {"pass": worst <= 1e-9 and bond_ok, "max_abs_difference": worst, "bonds_exact": bond_ok,
                                       "items": items}

    units = {}
    for fam in D.FAMILIES:
        cases, V, ema, R0, th, T = sim.prepare(fam, lo, "engineering")
        H, W_ = sim.edges_from(sim.bonds(R0, True))
        units[f"{fam}/flux_all_plus_one"] = bool((sim.flux(H, W_) == 1).all())
        H2 = H.copy()
        H2[0, 5, 7] *= -1
        units[f"{fam}/one_flip_two_frustrated"] = bool(int((sim.flux(H2, W_)[0] < 0).sum()) == 2)
        H3, W3 = sim.parity_repair(H2, W_)
        units[f"{fam}/parity_restores"] = bool(np.array_equal(H3, H) and np.array_equal(W3, W_))
        s = np.sign(R0)
        corner = np.repeat(np.repeat(s[:, ::4, ::4], 4, 1), 4, 2)
        units[f"{fam}/frame=s*s_corner"] = bool(np.array_equal(sim.gauge_frame(H, W_), s * corner))
        raw = rawf("C", fam)
        brs = D.branches("C")
        for c in D.C_CONDS:
            if c.wound in ("flip", "kill"):
                units[f"{fam}/hybrid+trust=hybrid/{c.name}"] = bool(np.array_equal(raw["r"][brs.index(f"hybrid+trust/{c.name}")],
                                                                                raw["r"][brs.index(f"hybrid/{c.name}")]))
    checks["Q5_units_aliases"] = {"pass": all(units.values()), "items": len(units), "failed": [k for k, v in units.items() if not v]}

    rates, flips, same_units = {}, {}, True
    for b in range(lo, hi):                       # each case's bond noise is shared by all its branches and families
        fr0 = shard("E", D.E_UNITS[0], b)["flip_rate"]
        same_units &= all(np.array_equal(fr0, shard("E", u, b)["flip_rate"]) for u in D.E_UNITS[1:])
        for i, br in enumerate(D.branches("E")):
            flips.setdefault(br, []).append(fr0[i])
    ok6 = same_units
    for br, xs in flips.items():
        p_b = float(br.split("/")[0])
        x = np.concatenate(xs)                    # one value per distinct case
        se = np.sqrt(p_b * (1 - p_b) / (D.E_WINDOW * 2 * N * N * len(x)))
        rates[br] = round(float(x.mean()), 7)
        ok6 &= abs(x.mean() - p_b) <= 3 * se + 1e-12
    checks["Q6_bond_noise_rate"] = {"pass": bool(ok6), "shared_across_families": bool(same_units), "rates": rates}

    bad = []
    for p, u in D.tasks():
        if p == "A":
            continue
        raw, e = rawf(p, u), shard(p, u)
        nb, k = len(D.branches(p)), D.NCASE
        T = np.tile(raw["T"], (nb, 1, 1)).reshape(nb, k, N, N)
        r = raw["r"]
        ok = (r > 0) == (T > 0)
        mn, mj = sim.minority(T)
        got = {}
        if p in ("E", "T"):
            H0, W0 = sim.edges_from(sim.bonds(raw["R0"], True))
            got = {"sign": ok.mean((-2, -1)), "minority": sim.frac(mn, ok), "majority": sim.frac(mj, ok),
                   "bond_err": sim.bond_err(raw["H"], raw["W"], H0[None], W0[None])}
        elif p == "C":
            m = raw["mask"]
            got = {"kept": sim.frac(m, ok), "kept_min": sim.frac(m & mn, ok), "kept_maj": sim.frac(m & mj, ok),
                   "sign": ok.mean((-2, -1)), "minority": sim.frac(mn, ok), "majority": sim.frac(mj, ok)}
        elif p == "L":
            m = raw["mask"]
            okv = (raw["v"] > 0) == (T > 0)
            H0, W0 = sim.edges_from(sim.bonds(raw["R0"], True))
            got = {"record_kept": sim.frac(m, ok), "body_kept": sim.frac(m, okv), "record_sign": ok.mean((-2, -1)),
                   "body_sign": okv.mean((-2, -1)), "bond_err": sim.bond_err(raw["H"], raw["W"], H0[None], W0[None])}
        bad += [f"{p}/{u}/{k_}" for k_, v in got.items() if not np.array_equal(v, e[k_][-1], equal_nan=True)]
    checks["Q7_reanalysis"] = {"pass": not bad, "mismatched": bad[:10]}

    eff = []
    for u in D.C_UNITS:
        for b in range(lo, hi):
            ps = shard("C", u, b)["events/patch_sites"]
            for ci, c in enumerate(D.C_CONDS):
                if not (ps[ci] == c.size ** 2).all():
                    eff.append(f"C/{u}/{b}/{c.name}/patch")
    cases, V, ema, R0, th, T = sim.prepare("IS", lo, "engineering")
    m = sim.patch(cases, 8)
    for wound in ("flip", "kill", "relink"):
        r0, H, W_, tH, tW = sim.wound_state(R0, m, np.array([wound] * len(cases)), np.arange(len(cases)))
        Hc, Wc = sim.edges_from(sim.bonds(R0, True))
        both_h, both_w = m & np.roll(m, -1, -1), m & np.roll(m, -1, -2)
        if wound == "flip":
            ok8 = np.array_equal(r0, np.where(m, -R0, R0)) and np.array_equal(H, Hc) and tH.all()
        else:
            val = 1.0 if wound == "relink" else 0.0
            ok8 = (np.array_equal(r0, np.where(m, 0.0, R0)) and np.array_equal(H, np.where(both_h, val, Hc))
                   and np.array_equal(W_, np.where(both_w, val, Wc)) and np.array_equal(~tH, both_h) and np.array_equal(~tW, both_w))
        if not ok8:
            eff.append(f"wound/{wound}")
    for u in D.T_UNITS:
        for b in range(lo, hi):
            tv = shard("T", u, b)["turnovers"]
            cs = enrol([b], D.MESSAGES, D.PARENTS, "engineering")
            for i, (rate, mode) in enumerate(D.T_BRANCHES):
                want = [len(ev[0]) for ev in sim.turnover_events(cs, rate, D.T_WINDOW)] if rate > 0 else [0] * len(cs)
                if not np.array_equal(tv[i], np.array(want, float)):
                    eff.append(f"T/{u}/{b}/{rate:g}/{mode}/turnovers")
    checks["Q8_efficacy"] = {"pass": not eff, "failed": eff[:10]}

    walls = {}
    for key, t in manifest["tasks"].items():
        p, u = key.split("/")[:2]
        walls.setdefault((p, u), []).append(t["wall_s"])
    n_dev = D.IDENTITIES["development"][1] - D.IDENTITIES["development"][0]
    cpu = sum(np.mean(v) * n_dev for v in walls.values())
    forecast_h = (cpu / WORKERS * 1.15 + max(max(v) for v in walls.values())) / 3600
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    rss = manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(forecast_h <= 12 and rss <= 0.8 * avail and per_task * len(D.tasks()) * n_dev <= 0.8 * free),
                              "forecast_wall_h": round(float(forecast_h), 3), "forecast_cpu_h": round(cpu / 3600, 3)}

    out = root / "analysis_dry_run"
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-m", "lr001.analyze", "--root", str(root), "--stage", "preflight", "--out", str(out)]
                          + ([] if a.blocks is None else ["--blocks", a.blocks]), cwd=LANE, capture_output=True, text=True, env=env)
    proc2 = subprocess.run([sys.executable, "-m", "lr001.tables", "--out", str(out)], cwd=LANE, capture_output=True, text=True, env=env)
    expected = [out / "contrasts_C.csv", out / "contrasts_E.csv", out / "contrasts_T.csv", out / "summary.json",
                out / "predictions_scored.json", out / "TABLES.md"]
    stmts = [s["id"] for s in json.loads((FROZEN / "predictions.json").read_text())["statements"]]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    sizes = {q.name: q.stat().st_size for q in expected if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and proc2.returncode == 0 and all(q.exists() for q in expected)
                                    and set(got) == set(stmts) and max(sizes.values(), default=0) <= 262144,
                                    "stderr": (proc.stderr + proc2.stderr)[-600:], "sizes": sizes}

    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
