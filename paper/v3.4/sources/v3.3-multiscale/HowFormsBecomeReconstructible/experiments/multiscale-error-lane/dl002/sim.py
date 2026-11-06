"""DL002's tissue: DL001's body (dl001.sim.body, unchanged) reading one of five records, on a 32-site sheet.

A run advances every record of one body as branches (record-major: index = record x cases + case), all reading the
case's noise stream, so records and bodies are paired within a case. In each update the body reads the current
record, then the relational record takes its own step (msegrid.record_step: self-correction through the bonds, the
coarse code, clipping); every other record is held. The relational record never reads the body.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from mse.assay import BIRTH_SCALE, enrol
from mse.native import NATIVE, address, center
from msegrid.core import Stream, acquire, base, bonds, bproj, record_step

from . import design as D


def labyrinth(block, j):
    """li4 grown from newborn noise in a clean sheet without a record for LB_GROW updates; its sign."""
    alpha, L = DL.BODIES["li4"]
    G = S.ghat(D.SIDE, L)
    V = BIRTH_SCALE * center(address(D.TAG, "family", "LB", block, j).standard_normal((D.SIDE, D.SIDE)))[None]
    g = address(D.TAG, "family", "LB-noise", block, j)
    p = replace(NATIVE, sigma=D.SIGMA)
    zero = np.zeros_like(V)
    for _ in range(D.LB_GROW):
        V = S.body(V, V, zero, zero, g.standard_normal((1, D.SIDE, D.SIDE)), p, 0.0, alpha, G)[0]
    return np.where(V[0] >= 0, 1.0, -1.0)


def template(family, kind, block):
    if family == "S4":
        return S.template("S4", kind, D.SIDE, block)
    if family == "LB":
        f = labyrinth(block, kind % 2)
        return f if kind < 2 else -f
    return base(family, kind, D.SIDE, D.TAG, block)


def prepare(pattern, block, purpose):
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = np.stack([D.AMPLITUDE * template(pattern, c.message, block) for c in cases])
    V, ema, R0, th = acquire(D.TAG, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), D.SIDE,
                             settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T


def anchors(cases, density):
    return np.stack([address(D.TAG, *c.key(), "anchors", density).random((D.SIDE, D.SIDE)) < 1.0 / density for c in cases])


def wound_mask(cases):
    out = np.zeros((len(cases), D.SIDE, D.SIDE), bool)
    for j, c in enumerate(cases):
        a, b = address(D.TAG, *c.key(), "wound").integers(0, D.SIDE, 2)
        out[j][np.ix_(np.arange(a, a + 8) % D.SIDE, np.arange(b, b + 8) % D.SIDE)] = True
    return out


def newborn_values(cases):
    return np.stack([D.KILL_SD * address(D.TAG, *c.key(), "newborn").standard_normal((D.SIDE, D.SIDE)) for c in cases])


def branches(records, cases, V0, ema0, R0, wound):
    """Initial V, ema, record and per-site gain for every record (record-major), and the wound mask."""
    k, nb = len(cases), len(records)
    V, E, r = np.tile(V0, (nb, 1, 1)), np.tile(ema0, (nb, 1, 1)), np.tile(R0, (nb, 1, 1))
    gain = np.zeros((nb * k, D.SIDE, D.SIDE))
    m = wound_mask(cases) if wound else np.zeros((k, D.SIDE, D.SIDE), bool)
    nbv = newborn_values(cases) if wound == "reset" else None
    for i, rec in enumerate(records):
        sl = slice(i * k, (i + 1) * k)
        if rec.kind in ("full", "rel"):
            gain[sl] = rec.gain
        elif rec.kind == "anchors":
            gain[sl] = rec.gain * anchors(cases, rec.density)
        if wound == "flip":
            V[sl] = np.where(m, -V[sl], V[sl])
        elif wound == "reset":
            V[sl], E[sl] = np.where(m, nbv, V[sl]), np.where(m, nbv, E[sl])
        if wound and rec.kind == "anchors":
            gain[sl] = np.where(m, 0.0, gain[sl])              # anchors inside the wound are lost
        if wound and rec.kind == "rel":                        # the relational record is wounded with the body
            r[sl] = np.where(m, -R0, R0) if wound == "flip" else np.where(m, 0.0, R0)
    return V, E, r, gain, m


def run(body, records, cases, V0, ema0, R0, th, T, theta, wound, snaps):
    """Advance one body under every record for D.WINDOW updates; endpoints per snapshot, work, final V and record."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, nb = len(cases), len(records)
    idx = np.tile(np.arange(k), nb)
    V, E, r, gain, m = branches(records, cases, V0, ema0, R0, wound)
    mb, Tb, thb = np.tile(m, (nb, 1, 1)), np.tile(T, (nb, 1, 1)), (th * theta)[idx]
    rel = [i for i, rec in enumerate(records) if rec.kind == "rel"]
    rs = slice(rel[0] * k, (rel[0] + 1) * k) if rel else None
    J, B = bonds(R0, True), bproj(R0, 4)
    p = replace(NATIVE, sigma=D.SIGMA)
    st = Stream(D.TAG, cases, "future", side=D.SIDE)
    xs = Stream(D.TAG, cases, "record-noise", side=D.SIDE)
    out = {"sign": [], "patch": [], "shift": [], "spacing": [], "r_sign": [], "r_patch": []}
    wc, nwork, buf, xbuf = np.zeros(nb * k), 0, None, None
    for t in range(1, D.WINDOW + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        if rs is not None:
            r[rs] = record_step(r[rs], xbuf[i], D.EPS, D.KR, D.SIGMA_R, D.KC, B, J)
        if t > D.WINDOW // 2:
            wc += np.abs(p.dt * d).mean((-2, -1))
            nwork += 1
        if t in snaps:
            out["sign"].append(S.sign(V, Tb))
            out["patch"].append(S.patch(V, Tb, mb) if wound else np.zeros(nb * k))
            out["shift"].append(S.best_shift(V, Tb))
            out["spacing"].append(S.spacing(V))
            out["r_sign"].append(S.sign(r[rs], T) if rs is not None else np.zeros(k))
            out["r_patch"].append(S.patch(r[rs], T, m) if (rs is not None and wound) else np.zeros(k))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(w_corr=wc / nwork, qual=S.qual(V, Tb), final=V, r_rel=r[rs] if rs is not None else None)
    return res
