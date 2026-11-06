"""LR001's simulators: the relational record of BR002 on msegrid/, with bonds held as edges.

Branches are batched label-major (index = branch x cases + case), each case's noise shared by all its branches
(paired). One update, in order: bond noise (E); the record step (self-correction through the bonds, then the code,
one clip: msegrid.record_step's arithmetic); Hebbian learning; plaquette parity (E); turnover (T). Panel L adds
br001.sim.body_step (unchanged) before the record step, with BR001's held scar.
With no bond noise, no repair and the plain code or none, the record equals msegrid.record_step, so panel C's plain
code equals gw001.sim.simulate_R's rel+code arm bit for bit (and none its rel arm); panel L with no scar and no
learning equals gw001.sim.simulate_B with a rel arm (tests/test_lr001.py, checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.special import ndtri

from br001.sim import body_step
from mse.assay import enrol
from mse.native import NATIVE, address, sheet
from msegrid.core import Stream, acquire, bond_sum, bonds, bproj, kill_bonds, record_step, theta

from . import design as D

N = D.SIDE


# bonds as edges ------------------------------------------------------------------------------------------------

def edges_from(J):
    """BR002's four halves -> H (right neighbour) and W (lower neighbour)."""
    return J[3].copy(), J[1].copy()


def halves(H, W):
    """H, W -> BR002's four halves in mse.native.neighbours' order: up, down, left, right."""
    return [np.roll(W, 1, -2), W, np.roll(H, 1, -1), H]


def flux(H, W):
    """The product of bond signs around each plaquette (i, j)-(i, j+1)-(i+1, j+1)-(i+1, j); +1 for any pattern."""
    return H * np.roll(W, -1, -1) * np.roll(H, -1, -2) * W


def parity_repair(H, W):
    """Flip every bond whose two plaquettes are both frustrated."""
    F = flux(H, W)
    fh = (F < 0) & (np.roll(F, 1, -2) < 0)          # H[i, j] borders plaquettes (i, j) and (i-1, j)
    fw = (F < 0) & (np.roll(F, 1, -1) < 0)          # W[i, j] borders plaquettes (i, j) and (i, j-1)
    return np.where(fh, -H, H), np.where(fw, -W, W)


def gauge_frame(H, W):
    """sigma per 4 x 4 region: +1 at the region's corner, then along its first row by H and down each column by W
    (the product of the bond signs along that path; 0 beyond a missing bond)."""
    s = np.zeros_like(H)
    for i0 in range(0, N, D.REGION):
        for j0 in range(0, N, D.REGION):
            s[..., i0, j0] = 1.0
            for j in range(j0, j0 + D.REGION - 1):
                s[..., i0, j + 1] = s[..., i0, j] * H[..., i0, j]
            for i in range(i0, i0 + D.REGION - 1):
                s[..., i + 1, j0:j0 + D.REGION] = s[..., i, j0:j0 + D.REGION] * W[..., i, j0:j0 + D.REGION]
    return s


def minority(T):
    """Region-minority and majority cells: the template's sign against its 4 x 4 region's mean (ties excluded)."""
    m = bproj(T, D.REGION)
    return (np.sign(T) != np.sign(m)) & (m != 0), (np.sign(T) == np.sign(m)) & (m != 0)


def frac(mask, ok):
    """Share of the masked sites that are right, per sheet; NaN for a sheet with no masked site."""
    n = mask.sum((-2, -1))
    return np.where(n > 0, (ok & mask).sum((-2, -1)) / np.maximum(n, 1), np.nan)


def bond_err(H, W, H0, W0):
    return ((H != H0).mean((-2, -1)) + (W != W0).mean((-2, -1))) / 2


def cut_for(p_b):
    """z > cut (and z < -cut) with probability p_b for a standard normal z; inf for p_b = 0."""
    return np.inf if p_b <= 0 else float(ndtri(1.0 - p_b))


# preparation ---------------------------------------------------------------------------------------------------

def cases_for(block, purpose):
    return enrol([block], D.MESSAGES, D.PARENTS, purpose)


def prepare(family, block, purpose, tag=D.TAG):
    """Cases, the acquired body V, ema, record R0, theta and the +-AMPLITUDE templates (msegrid.acquire, conserved
    body, sigma SIGMA_ACQ)."""
    from me002.families import templates
    cases = cases_for(block, purpose)
    T = templates(family, "mse-me002", D.AMPLITUDE)[[c.message for c in cases]]
    V, ema, R0, th = acquire(tag, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), N, settle=D.SETTLE, teach=D.TEACH,
                             release=D.RELEASE)
    return cases, V, ema, R0, th, T


def patch(cases, size, tag=D.TAG):
    """(cases, 16, 16): a size x size patch at the case's addressed corner, shared by every size and wound kind."""
    m = np.zeros((len(cases), N, N), bool)
    if size == 0:
        return m
    for i, c in enumerate(cases):
        a, b = address(tag, *c.key(), "lesion").integers(0, N, 2)
        m[i][np.ix_(np.arange(a, a + size) % N, np.arange(b, b + size) % N)] = True
    return m


def turnover_events(cases, rate, updates, tag=D.TAG):
    """Per case: (times, flat sites) of cell replacements, addressed by (case, 'turnover', rate), shared by every mode."""
    out = []
    for c in cases:
        g = address(tag, *c.key(), "turnover", f"{rate:g}")
        n = int(g.poisson(rate * updates * N * N)) if rate > 0 else 0
        t = g.integers(1, updates + 1, n)
        site = g.integers(0, N * N, n)
        o = np.argsort(t, kind="stable")
        out.append((t[o], site[o]))
    return out


# the record step with a code -------------------------------------------------------------------------------------

def step(r, xi, J, code=None, B=None, Bg=None, frame=None):
    """msegrid.record_step's arithmetic with a per-branch code. code: (n,) ints, 0 none, 1 plain, 2 gauge, 3 hybrid
    (4 = hybrid with trust flags; the caller passes the trusted frame). frame: (n,16,16) sigma or None."""
    r = r + D.EPS * (r * (1 - (r / D.R_STAR) ** 2) + D.KR * (bond_sum(J, r) - r)) + D.SIGMA_R * xi
    if code is not None and (code > 0).any():
        plain = D.KC * (B - bproj(r, D.REGION))
        inc = np.where((code == 1)[:, None, None], plain, 0.0)
        if (code >= 2).any():
            live = frame != 0
            mean_u = bproj(frame * r, D.REGION) / np.maximum(bproj(live * 1.0, D.REGION), 1.0 / D.REGION ** 2)
            gauge = D.KC * frame * (Bg - mean_u)
            hyb = np.where(live, gauge, plain)
            inc = np.where((code == 2)[:, None, None], gauge, np.where((code >= 3)[:, None, None], hyb, inc))
        r = r + inc
    return np.clip(r, -2.0, 2.0)


# panels ----------------------------------------------------------------------------------------------------------

def simulate_A(cases, T, th, sigma, reads, tag=D.TAG):
    """Bonds learned as a running average of the body's co-activity while the teacher holds it at T (BR001's
    teaching step: V <- T, then the native sheet step). Returns bond accuracy at each read, (reads, cases)."""
    p = replace(NATIVE, sigma=sigma)
    st = Stream(tag, cases, "teach-learn", f"{sigma:g}", side=N)
    Hb, Wb = np.zeros_like(T), np.zeros_like(T)
    H0, W0 = edges_from(bonds(T, True))
    out, buf = [], None
    for t in range(1, max(reads) + 1):
        i = (t - 1) % 100
        if i == 0:
            buf = st.take(100)
        Vt = sheet(T, th, buf[i], p)
        Hb = Hb + D.ETA_TEACH * (Vt * np.roll(Vt, -1, -1) / D.R_STAR ** 2 - Hb)
        Wb = Wb + D.ETA_TEACH * (Vt * np.roll(Vt, -1, -2) / D.R_STAR ** 2 - Wb)
        if t in reads:
            out.append(((np.sign(Hb) == H0).mean((-2, -1)) + (np.sign(Wb) == W0).mean((-2, -1))) / 2)
    return np.array(out)


def simulate_E(cases, R0, T, window=D.E_WINDOW, reads=D.E_READS, tag=D.TAG):
    """Relation errors: every bond flips at rate p_b; repairs by branch. Returns endpoints (reads, branches, cases)
    and the final r, H, W (branches, cases, 16, 16)."""
    labels = [(r_, rep) for r_ in D.E_RATES for rep in D.E_REPAIRS]
    nb, k = len(labels), len(cases)
    idx = np.tile(np.arange(k), nb)
    cut = np.repeat([cut_for(r_) for r_, _ in labels], k)[:, None, None]
    hebb = np.repeat([rep in ("hebb", "both") for _, rep in labels], k)[:, None, None]
    par = np.repeat([rep in ("parity", "both") for _, rep in labels], k)[:, None, None]
    Tb = T[idx]
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    r = R0[idx].copy()
    mn, mj = minority(Tb)
    xs = Stream(tag, cases, "record-noise", "E", side=N)
    zs = Stream(tag, cases, "bond-noise", side=N)
    ends = {k_: [] for k_ in ("sign", "bond_err", "minority", "majority")}
    flips = np.zeros(nb * k)
    xb = zb = None
    for t in range(1, window + 1):
        i = (t - 1) % 100
        if i == 0:
            xb, zb = xs.take(100), zs.take(100)
        z = zb[i][idx]
        hh, hw = z > cut, z < -cut
        flips += hh.sum((-2, -1)) + hw.sum((-2, -1))
        H, W = np.where(hh, -H, H), np.where(hw, -W, W)
        Hb, Wb = np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xb[i][idx], D.EPS, D.KR, D.SIGMA_R, 0.0, None, halves(H, W))
        if hebb.any():
            Hn = Hb + D.ETA * (np.clip(r * np.roll(r, -1, -1) / D.R_STAR ** 2, -1, 1) - Hb)
            Wn = Wb + D.ETA * (np.clip(r * np.roll(r, -1, -2) / D.R_STAR ** 2, -1, 1) - Wb)
            Hb, Wb = np.where(hebb, Hn, Hb), np.where(hebb, Wn, Wb)
            H = np.where(hebb & (Hb != 0), np.sign(Hb), H)
            W = np.where(hebb & (Wb != 0), np.sign(Wb), W)
        if par.any():
            H2, W2 = parity_repair(H, W)
            H, W = np.where(par, H2, H), np.where(par, W2, W)
            Hb = np.where(par & (np.sign(Hb) * H < 0), -Hb, Hb)
            Wb = np.where(par & (np.sign(Wb) * W < 0), -Wb, Wb)
        if t in reads:
            ok = (r > 0) == (Tb > 0)
            ends["sign"].append(ok.mean((-2, -1)))
            ends["bond_err"].append(bond_err(H, W, H0, W0))
            ends["minority"].append(frac(mn, ok))
            ends["majority"].append(frac(mj, ok))
    out = {k_: np.array(v).reshape(len(reads), nb, k) for k_, v in ends.items()}
    out["flip_rate"] = (flips / (window * 2 * N * N)).reshape(nb, k)
    return out, {"r": r.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N), "W": W.reshape(nb, k, N, N)}


CODE_ID = {"none": 0, "plain": 1, "gauge": 2, "hybrid": 3, "hybrid+trust": 4}


def wound_state(R0, masks, wounds, idx):
    """Initial r, H, W and the trust flags for each branch: flip r -> -r; kill r -> 0 and the bonds between two dead
    cells lost (0); relink r -> 0 and those bonds re-formed as +1 (untrusted)."""
    r = R0[idx].copy()
    H, W = edges_from(bonds(R0, True))
    H, W = H[idx], W[idx]
    m = masks
    fl = m & (wounds == "flip")[:, None, None]
    dead = m & np.isin(wounds, ("kill", "relink"))[:, None, None]
    r = np.where(fl, -r, r)
    r = np.where(dead, 0.0, r)
    J = halves(H, W)
    J = kill_bonds(J, m & (wounds == "kill")[:, None, None], False)
    J = kill_bonds(J, m & (wounds == "relink")[:, None, None], True)
    H, W = edges_from(J)
    tH = ~(dead & np.roll(dead, -1, -1))
    tW = ~(dead & np.roll(dead, -1, -2))
    return r, H, W, tH, tW


def simulate_C(cases, R0, T, masks_by_size, window=D.C_WINDOW, reads=D.C_READS, tag=D.TAG, codes=D.C_CODES,
               conds=D.C_CONDS):
    """Codes against wounds. Branches: codes x conditions. Returns endpoints (reads, branches, cases) and finals."""
    labels = [(code, c) for code in codes for c in conds]
    nb, k = len(labels), len(cases)
    idx = np.tile(np.arange(k), nb)
    code = np.repeat([CODE_ID[cd] for cd, _ in labels], k)
    wounds = np.repeat([c.wound for _, c in labels], k)
    mask = np.concatenate([masks_by_size[c.size] for _, c in labels])
    Tb = T[idx]
    r, H, W, tH, tW = wound_state(R0, mask, wounds, idx)
    trust = (code == 4)[:, None, None]
    Hf, Wf = np.where(trust & ~tH, 0.0, H), np.where(trust & ~tW, 0.0, W)
    frame = gauge_frame(Hf, Wf)                       # bonds never change in panel C, so the frame is fixed
    H0, W0 = edges_from(bonds(R0, True))
    B = bproj(R0, D.REGION)[idx]
    Bg = bproj(gauge_frame(H0, W0) * R0, D.REGION)[idx]
    J = halves(H, W)
    mn, mj = minority(Tb)
    xs = Stream(tag, cases, "record-noise", side=N)
    ends = {k_: [] for k_ in ("kept", "kept_min", "kept_maj", "sign", "minority", "majority")}
    xb = None
    for t in range(1, window + 1):
        i = (t - 1) % 250
        if i == 0:
            xb = xs.take(250)
        r = step(r, xb[i][idx], J, code, B, Bg, frame)
        if t in reads:
            ok = (r > 0) == (Tb > 0)
            ends["kept"].append(frac(mask, ok))
            ends["kept_min"].append(frac(mask & mn, ok))
            ends["kept_maj"].append(frac(mask & mj, ok))
            ends["sign"].append(ok.mean((-2, -1)))
            ends["minority"].append(frac(mn, ok))
            ends["majority"].append(frac(mj, ok))
    out = {k_: np.array(v).reshape(len(reads), nb, k) for k_, v in ends.items()}
    return out, {"r": r.reshape(nb, k, N, N), "mask": mask.reshape(nb, k, N, N)}


def simulate_T(cases, R0, T, window=D.T_WINDOW, reads=D.T_READS, tag=D.TAG, labels=D.T_BRANCHES):
    """Turnover under the hybrid code with trust flags. A newborn's record starts at 0; its four bonds are kept
    (inherit), reset to strength 0 and relearned by Hebbian learning from the record (relearn: a bond counts once
    |b| >= COUNT and is trusted once |b| >= TRUST), or re-formed as +1 untrusted (default)."""
    nb, k = len(labels), len(cases)
    idx = np.tile(np.arange(k), nb)
    Tb = T[idx]
    Hc, Wc = edges_from(bonds(R0, True))
    H0, W0 = Hc[idx], Wc[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    tH, tW = np.ones(H.shape, bool), np.ones(W.shape, bool)
    relearn = np.repeat([m == "relearn" for _, m in labels], k)[:, None, None]
    code = np.full(nb * k, 4)
    B = bproj(R0, D.REGION)[idx]
    Bg = bproj(gauge_frame(Hc, Wc) * R0, D.REGION)[idx]
    r = R0[idx].copy()
    mn, mj = minority(Tb)
    events = {rate: turnover_events(cases, rate, window, tag) for rate in sorted({r_ for r_, _ in labels if r_ > 0})}
    xs = Stream(tag, cases, "record-noise", "T", side=N)
    ends = {k_: [] for k_ in ("sign", "minority", "majority", "bond_err")}
    nturn = np.zeros(nb * k)
    xb = None
    for t in range(1, window + 1):
        i = (t - 1) % 250
        if i == 0:
            xb = xs.take(250)
        frame = gauge_frame(np.where(tH, H, 0.0), np.where(tW, W, 0.0))
        r = step(r, xb[i][idx], halves(H, W), code, B, Bg, frame)
        if relearn.any():
            Hn = Hb + D.ETA * (np.clip(r * np.roll(r, -1, -1) / D.R_STAR ** 2, -1, 1) - Hb)
            Wn = Wb + D.ETA * (np.clip(r * np.roll(r, -1, -2) / D.R_STAR ** 2, -1, 1) - Wb)
            Hb, Wb = np.where(relearn, Hn, Hb), np.where(relearn, Wn, Wb)
            H = np.where(relearn, np.where(np.abs(Hb) >= D.COUNT, np.sign(Hb), 0.0), H)
            W = np.where(relearn, np.where(np.abs(Wb) >= D.COUNT, np.sign(Wb), 0.0), W)
            tH = np.where(relearn, np.abs(Hb) >= D.TRUST, tH)
            tW = np.where(relearn, np.abs(Wb) >= D.TRUST, tW)
        for b, (rate, mode) in enumerate(labels):
            if rate <= 0:
                continue
            for j in range(k):
                tt, site = events[rate][j]
                lo, hi = np.searchsorted(tt, t, "left"), np.searchsorted(tt, t, "right")
                n_ = b * k + j
                for s in site[lo:hi]:
                    a, c = divmod(int(s), N)
                    r[n_, a, c] = 0.0
                    nturn[n_] += 1
                    if mode == "inherit":
                        continue
                    for arr, strength, tr, x, y in ((H, Hb, tH, a, c), (H, Hb, tH, a, (c - 1) % N),
                                                     (W, Wb, tW, a, c), (W, Wb, tW, (a - 1) % N, c)):
                        if mode == "relearn":
                            arr[n_, x, y], strength[n_, x, y], tr[n_, x, y] = 0.0, 0.0, False
                        else:
                            arr[n_, x, y], strength[n_, x, y], tr[n_, x, y] = 1.0, D.STRENGTH0, False
        if t in reads:
            ok = (r > 0) == (Tb > 0)
            ends["sign"].append(ok.mean((-2, -1)))
            ends["minority"].append(frac(mn, ok))
            ends["majority"].append(frac(mj, ok))
            ends["bond_err"].append(bond_err(H, W, H0, W0))
    out = {k_: np.array(v).reshape(len(reads), nb, k) for k_, v in ends.items()}
    out["turnovers"] = nturn.reshape(nb, k)
    return out, {"r": r.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N), "W": W.reshape(nb, k, N, N)}


def simulate_L(cases, V, ema, R0, th, T, window=D.L_WINDOW, reads=D.L_READS, tag=D.TAG, learns=D.L_LEARN,
               scar_until=D.L_SCAR_UNTIL):
    """Learning in life. The body (br001.sim.body_step, conserved, sigma L_SIGMA, gain c) reads the relational record;
    BR001's scar holds a 6 x 6 body patch at -T for t <= scar_until; bonds keep learning from the record's (r / 1.2)
    or the body's (V) co-activity at ETA (body_slow: ETA_SLOW), or not at all."""
    nb, k = len(learns), len(cases)
    idx = np.tile(np.arange(k), nb)
    Tb, thb = T[idx], th[idx]
    p = replace(NATIVE, sigma=D.L_SIGMA)
    eta = np.repeat([{"none": 0.0, "record": D.ETA, "body": D.ETA, "body_slow": D.ETA_SLOW}[x] for x in learns], k)[:, None, None]
    from_body = np.repeat([x.startswith("body") for x in learns], k)[:, None, None]
    learn = eta > 0
    H0, W0 = edges_from(bonds(R0, True))
    H0, W0 = H0[idx], W0[idx]
    H, W = H0.copy(), W0.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    mask = np.tile(patch(cases, D.L_SCAR, tag), (nb, 1, 1)) if scar_until > 0 else np.zeros((nb * k, N, N), bool)
    v, e, r = V[idx].copy(), ema[idx].copy(), R0[idx].copy()
    zs, xs = Stream(tag, cases, "future", side=N), Stream(tag, cases, "record-noise", side=N)
    ends = {k_: [] for k_ in ("record_kept", "body_kept", "record_sign", "body_sign", "bond_err")}
    zb = xb = None
    for t in range(1, window + 1):
        i = (t - 1) % 500
        if i == 0:
            zb, xb = zs.take(500), xs.take(500)
        if t <= scar_until:
            v = np.where(mask, -Tb, v)
        v, e, _ = body_step(v, e, r, thb, zb[i][idx], p, True, NATIVE.gain)
        r = record_step(r, xb[i][idx], D.EPS, D.KR, D.SIGMA_R, 0.0, None, halves(H, W))
        if learn.any():
            x = np.where(from_body, v, r / D.R_STAR)
            Hn = Hb + eta * (np.clip(x * np.roll(x, -1, -1), -1, 1) - Hb)
            Wn = Wb + eta * (np.clip(x * np.roll(x, -1, -2), -1, 1) - Wb)
            Hb, Wb = np.where(learn, Hn, Hb), np.where(learn, Wn, Wb)
            H = np.where(learn & (Hb != 0), np.sign(Hb), H)
            W = np.where(learn & (Wb != 0), np.sign(Wb), W)
        if t in reads:
            okr, okv = (r > 0) == (Tb > 0), (v > 0) == (Tb > 0)
            ends["record_kept"].append(frac(mask, okr))
            ends["body_kept"].append(frac(mask, okv))
            ends["record_sign"].append(okr.mean((-2, -1)))
            ends["body_sign"].append(okv.mean((-2, -1)))
            ends["bond_err"].append(bond_err(H, W, H0, W0))
    out = {k_: np.array(v_).reshape(len(reads), nb, k) for k_, v_ in ends.items()}
    return out, {"r": r.reshape(nb, k, N, N), "v": v.reshape(nb, k, N, N), "H": H.reshape(nb, k, N, N),
                 "W": W.reshape(nb, k, N, N), "mask": mask.reshape(nb, k, N, N)}
