"""Engineering probe P13 (python probes/p13_lr001_design_inputs.py CPUS): design inputs for LR001, relations that
learn and check themselves. ENGINEERING_PROBE_NOT_EVIDENCE.

The relational record of BR002 on the 16 x 16 sheet (msegrid.record_step, writing off), with bonds held as edges:
H[i, j] joins (i, j)-(i, j+1) and W[i, j] joins (i, j)-(i+1, j); J (BR002's four halves) is built from them.
Every plaquette's flux F = H . W(right) . H(below) . W is +1 for any pattern's bonds (J_ij = s_i s_j), so a
corrupted bond shows as two frustrated plaquettes: a free, local syndrome (the logic of Kitaev's toric code).
Cases: engineering blocks 900868-900871 (32 cases), tag mse-p13, side 16, ME002's families; records acquired as
BR002 (msegrid.acquire equals br001's acquisition at side 16).
Panels:
  A  Hebbian acquisition: bonds learned as a running average of the body's co-activity during teaching
     (b <- b + eta (Vt_i Vt_j / 1.44 - b)); bond accuracy by teaching noise and length;
  E  bond errors: each bond's sign flips at rate p_b per update; repairs none, Hebbian relearning from the
     record (b <- b + eta_b (r_i r_j / 1.44 - b)), plaquette parity (flip a bond whose two plaquettes are
     both frustrated), or both; bond error fraction and record agreement;
  G  a gauge-frame code: the coarse code applied in each 4 x 4 region's frame u = sigma r, where sigma is the
     product of bond signs along a path from the region's corner cell; against BR002's plain code, on flipped
     and killed patches, read separately at region-minority and majority cells. 'hybrid' uses the gauge frame
     where a cell is reachable through live bonds and the plain code where it is not.
v2 (26 Oct, before any registration): adds 'hybrid' and takes the gauge code's region mean over reachable cells
only (v1 averaged the unreachable cells in as zeros). v1's other numbers are unchanged.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from me002.families import templates  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE, address, sheet  # noqa: E402
from msegrid.core import Stream, acquire, bonds, bproj, kill_bonds, record_step, theta  # noqa: E402

TAG = "mse-p13"
SIDE = 16
BLOCKS = tuple(range(900868, 900872))
MESSAGES, PARENTS = (0, 1, 2, 3), (0, 1)
SETTLE, TEACH, RELEASE, AMPLITUDE, SIGMA_ACQ = 120, 1000, 200, 1.2, 0.1
EPS, KR, SIGMA_R, KC, R2 = 0.05, 1.0, 0.02, 0.02, 1.44
FAMILIES = ("F0", "BL", "S4", "IS")
TPL = {f: templates(f, "mse-me002", AMPLITUDE) for f in FAMILIES}
ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p13")
OUT = LANE / "probes" / "results" / "p13_lr001_design_inputs_v2.json"


def cases():
    return enrol(list(BLOCKS), MESSAGES, PARENTS, "engineering")


def acquisition(family):
    path = ROOT / f"acq_{family}.npz"
    if path.exists():
        z = np.load(path)
        return z["R"], z["T"]
    cs = cases()
    T = TPL[family][[c.message for c in cs]]
    _, _, R, _ = acquire(TAG, cs, T, replace(NATIVE, sigma=SIGMA_ACQ), SIDE, settle=SETTLE, teach=TEACH, release=RELEASE)
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".acq_{family}.{os.getpid()}.npz"
    np.savez(tmp, R=R, T=T)
    os.replace(tmp, path)
    return R, T


# bonds as edges ------------------------------------------------------------------------------------------------

def edges_from(J):
    return J[3].copy(), J[1].copy()                     # H: right neighbour, W: lower neighbour


def halves(H, W):
    return [np.roll(W, 1, -2), W, np.roll(H, 1, -1), H]   # BR002's order: up, down, left, right


def flux(H, W):
    return H * np.roll(W, -1, -1) * np.roll(H, -1, -2) * W


def parity_repair(H, W):
    F = flux(H, W)
    fh = (F < 0) & (np.roll(F, 1, -2) < 0)               # H[i, j] borders plaquettes (i, j) and (i-1, j)
    fw = (F < 0) & (np.roll(F, 1, -1) < 0)               # W[i, j] borders plaquettes (i, j) and (i, j-1)
    return np.where(fh, -H, H), np.where(fw, -W, W), int(fh.sum() + fw.sum())


def gauge_frame(H, W):
    """sigma per 4 x 4 region: +1 at the region's corner, then along its first row by H, down each column by W."""
    s = np.zeros_like(H)
    for i0 in range(0, SIDE, 4):
        for j0 in range(0, SIDE, 4):
            s[..., i0, j0] = 1.0
            for j in range(j0, j0 + 3):
                s[..., i0, j + 1] = s[..., i0, j] * H[..., i0, j]
            for i in range(i0, i0 + 3):
                s[..., i + 1, j0:j0 + 4] = s[..., i, j0:j0 + 4] * W[..., i, j0:j0 + 4]
    return s


def minority(T):
    m = bproj(T, 4)
    return (np.sign(T) != np.sign(m)) & (m != 0), (np.sign(T) == np.sign(m)) & (m != 0)


def frac(mask, ok):
    """Share of the masked sites that are right; NaN for a case with no masked site."""
    n = mask.sum((-2, -1))
    return np.where(n > 0, (ok & mask).sum((-2, -1)) / np.maximum(n, 1), np.nan)


def summarise(x):
    """[mean over the cases that have the sites, SD of the 4 block means, number of such cases]."""
    a = np.asarray(x, float).reshape(len(BLOCKS), -1)
    n = int(np.isfinite(a).sum())
    if n == 0:
        return [None, None, 0]
    bm = np.array([np.nanmean(b) if np.isfinite(b).any() else np.nan for b in a])
    sd = float(np.nanstd(bm, ddof=1)) if np.isfinite(bm).sum() > 1 else None
    return [round(float(np.nanmean(a)), 4), None if sd is None else round(sd, 4), n]


# panels --------------------------------------------------------------------------------------------------------

def panel_A(family, sigma, teach):
    """Bonds learned from the body's co-activity while the teacher holds it at T (BR001's teaching step)."""
    cs = cases()
    T = TPL[family][[c.message for c in cs]]
    p = replace(NATIVE, sigma=sigma)
    th = theta(TAG, cs, p, SIDE)
    st = Stream(TAG, cs, "p13-teach", side=SIDE)
    Hb, Wb = np.zeros_like(T), np.zeros_like(T)
    eta = 0.002
    buf = None
    for t in range(1, teach + 1):
        i = (t - 1) % 100
        if i == 0:
            buf = st.take(100)
        Vt = sheet(T, th, buf[i], p)
        Hb += eta * (Vt * np.roll(Vt, -1, -1) / R2 - Hb)
        Wb += eta * (Vt * np.roll(Vt, -1, -2) / R2 - Wb)
    H0, W0 = edges_from(bonds(T, True))
    acc = ((np.sign(Hb) == H0).mean((-2, -1)) + (np.sign(Wb) == W0).mean((-2, -1))) / 2
    return {"bond_accuracy": summarise(acc)}


def run_record(R0, T, J, updates, stream, kc=0.0, gauge=False, hebb=0.0, parity=False, p_b=0.0, kill=None,
               mask=None, snaps=(1000, 4000)):
    cs = cases()
    st = Stream(TAG, cs, "p13", stream, side=SIDE)
    flip_st = Stream(TAG, cs, "p13-bondnoise", stream, side=SIDE) if p_b else None
    H, W = edges_from(J)
    H0, W0 = edges_from(bonds(R0, True))
    Hb, Wb = H * 0.8, W * 0.8                            # bond strengths for Hebbian relearning
    B = bproj(R0, 4)
    sig0 = gauge_frame(H0, W0)
    Bg = bproj(sig0 * R0, 4)
    r = R0.copy()
    if mask is not None:
        r = np.where(mask, -r, r) if kill is None else np.where(mask, 0.0, r)
    if kill is not None:
        Jk = kill_bonds(halves(H, W), mask, kill == "relink")
        H, W = edges_from(Jk)
        Hb, Wb = H * 0.8, W * 0.8
    mn, mj = minority(T)
    cut = np.sqrt(2) * erfinv_1m(2 * p_b) if p_b else None   # P(z > cut) = P(z < -cut) = p_b
    out, nfix, buf, fbuf = {}, 0, None, None
    for t in range(1, updates + 1):
        i = (t - 1) % 100
        if i == 0:
            buf = st.take(100)
            if p_b:
                fbuf = flip_st.take(100)
        if p_b:
            hit_h, hit_w = fbuf[i] > cut, fbuf[i] < -cut     # each site's H and W bonds flip at rate p_b
            H, W = np.where(hit_h, -H, H), np.where(hit_w, -W, W)
            Hb, Wb = np.where(hit_h, -Hb, Hb), np.where(hit_w, -Wb, Wb)
        J = halves(H, W)
        r = record_step(r, buf[i], EPS, KR, SIGMA_R, 0.0, None, J)
        if kc:
            if gauge:
                sg = gauge_frame(H, W)
                live = sg != 0
                mean_u = bproj(sg * r, 4) * 16 / np.maximum(bproj(live * 1.0, 4) * 16, 1)
                inc = kc * sg * (Bg - mean_u)
                if gauge == "hybrid":
                    inc = np.where(live, inc, kc * (B - bproj(r, 4)))
                r = r + inc
            else:
                r = r + kc * (B - bproj(r, 4))
            r = np.clip(r, -2.0, 2.0)
        if hebb:
            Hb = Hb + hebb * (np.clip(r * np.roll(r, -1, -1) / R2, -1, 1) - Hb)
            Wb = Wb + hebb * (np.clip(r * np.roll(r, -1, -2) / R2, -1, 1) - Wb)
            H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
        if parity:
            H, W, n = parity_repair(H, W)
            Hb, Wb = np.where(np.sign(Hb) != H, -Hb, Hb), np.where(np.sign(Wb) != W, -Wb, Wb)
            nfix += n
        if t in snaps:
            ok = (r > 0) == (T > 0)
            berr = ((H != H0).mean((-2, -1)) + (W != W0).mean((-2, -1))) / 2
            res = {"sign": summarise(ok.mean((-2, -1))), "bond_err": summarise(berr),
                   "minority": summarise(frac(mn, ok)), "majority": summarise(frac(mj, ok))}
            if mask is not None:
                res["kept"] = summarise(frac(mask, ok))
                res["kept_min"] = summarise(frac(mask & mn, ok))
                res["kept_maj"] = summarise(frac(mask & mj, ok))
            out[t] = res
    out["parity_flips_per_update"] = round(nfix / updates / len(cs), 3)
    return out


def erfinv_1m(p):
    """x with P(|N(0,1)| > sqrt 2 x) = p (so a per-site normal draw selects a flip with probability p)."""
    from math import erf
    lo, hi = 0.0, 6.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - erf(mid) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def patch(cs, size, stream):
    m = np.zeros((len(cs), SIDE, SIDE), bool)
    for j, c in enumerate(cs):
        a, b = address(TAG, *c.key(), "lesion", stream).integers(0, SIDE, 2)
        m[j][np.ix_(np.arange(a, a + size) % SIDE, np.arange(b, b + size) % SIDE)] = True
    return m


def task(args):
    panel, family, a, b, c, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    if panel == "A":
        res = panel_A(family, a, b)
    else:
        R0, T = acquisition(family)
        J0 = bonds(R0, True)
        if panel == "E":
            p_b, repair = a, b
            res = run_record(R0, T, J0, 4000, "E", hebb=0.01 if repair in ("hebb", "both") else 0.0,
                             parity=repair in ("parity", "both"), p_b=p_b)
        else:                                            # G: code kind a in (none, plain, gauge), wound b, size c
            m = patch(cases(), c, "G")
            kill = None if b == "flip" else b            # 'kill' (bonds lost) or 'relink' (re-formed as +1)
            res = run_record(R0, T, J0, 4000, "G", kc=0.0 if a == "none" else KC,
                             gauge={"gauge": True, "hybrid": "hybrid"}.get(a, False), kill=kill, mask=m)
    res = {str(k): v for k, v in res.items()}
    return {"panel": panel, "family": family, "a": a, "b": b, "c": c, "res": res, "wall_s": round(time.time() - t0, 1)}


def main():
    cpus = [int(x) for x in sys.argv[1].split(",")]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(len(cpus), len(FAMILIES))) as ex:
        list(ex.map(acquisition, FAMILIES))
    jobs = []
    for fam in ("F0", "IS"):
        for s in (0.1, 0.3, 0.6):
            for n in (20, 100, 1000):
                jobs.append(("A", fam, s, n, ""))
    for fam in ("F0", "BL", "IS"):
        for p_b in (0.0003, 0.001, 0.003):
            for rep in ("none", "hebb", "parity", "both"):
                jobs.append(("E", fam, p_b, rep, ""))
    for fam in FAMILIES:
        for code in ("none", "plain", "gauge", "hybrid"):
            for wound in ("flip", "kill", "relink"):
                for size in (4, 8):
                    jobs.append(("G", fam, code, wound, size))
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P13", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS), "side": SIDE,
           "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
           "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
