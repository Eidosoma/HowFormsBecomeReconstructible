"""GW001's tissue on a sheet of any side, through msegrid/.

Panel R advances the record alone (writing off: the record never reads the body), so a run needs only the
acquired record. Panel B advances body and record together with br001.sim.body_step (side-agnostic) and
msegrid's record step. Wounds act at the start of update 1:
    flip   r -> -r (and v -> -v in panel B): an inverted, stable wrong state
    reset  r -> 0, the record's unstable point (panel B: v and ema -> newborn states); bonds kept
    kill   reset, and the bonds with both ends among the dead cells lost (0)
At side 16, panel B's flip and reset equal br002.sim.simulate's both-lesion and (for J = 1) kill bit for bit,
and panel R's record equals br002's record path (tests/test_gw001.py).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from br001.sim import body_step, masked_sign, qual, sign  # noqa: F401  (side-agnostic, unchanged)
from mse.assay import enrol
from mse.native import NATIVE, address
from msegrid.core import Stream, acquire, base, bonds, bproj, kill_bonds, place_mask, record_step

from . import design as D


def templates(family, side, cases, block):
    return np.stack([D.AMPLITUDE * base(family, c.message, side, D.TAG, block) for c in cases])


def prepare_R(unit, block, purpose):
    """Cases, acquired record R0 and the +-AMPLITUDE templates of one panel R geometry."""
    family, side = D.parse_geometry(unit)
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = templates(family, side, cases, block)
    _, _, R0, _ = acquire(D.TAG, cases, T, replace(NATIVE, sigma=D.SIGMA_ACQ), side,
                          settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, R0, T


def prepare_B(unit, block, purpose):
    family, side, sigma, body = D.parse_regime(unit)
    p = replace(NATIVE, sigma=sigma)
    cases = enrol([block], D.MESSAGES, D.PARENTS, purpose)
    T = templates(family, side, cases, block)
    V, ema, R0, th = acquire(D.TAG, cases, T, p, side, settle=D.SETTLE, teach=D.TEACH, release=D.RELEASE)
    return cases, V, ema, R0, th, T, p, body == "c"


def masks_for(cases, conds, family, side):
    """One (cases, side, side) patch per wounded condition, addressed by (case, 'lesion', place): every size and
    every wound kind at the same placement share the same draws, so contrasts across them are paired."""
    out = []
    for c in conds:
        if not c.size:
            out.append(None)
            continue
        out.append(np.stack([place_mask(family, cs.message, side, c.size, c.place, address(D.TAG, *cs.key(), "lesion", c.place))
                             for cs in cases]))
    return out


def newborn(cases, size, side):
    return np.stack([D.KILL_SD * address(D.TAG, *c.key(), "kill", f"{size}").standard_normal((side, side)) for c in cases])


def _wound_fields(conds, k, masks, side):
    nc = len(conds)
    mask = np.concatenate([m if m is not None else np.zeros((k, side, side), bool) for m in masks])
    wound = np.repeat([c.wound for c in conds], k)
    return mask, wound


def simulate_R(arm, conds, k, R0, T, masks, cases, window, every, tag=D.TAG):
    """The record alone. Returns the final r and, at every `every` updates, kept (patch sign agreement) and
    r_sign (whole sheet), each (snapshots, conditions x cases)."""
    nc = len(conds)
    side = R0.shape[-1]
    idx = np.tile(np.arange(k), nc)
    R0b, Tb = R0[idx], T[idx]
    B = bproj(R0, 4)[idx]
    J = bonds(R0b, arm.rel)
    mask, wound = _wound_fields(conds, k, masks, side)
    r = R0b.copy()
    r = np.where(mask & (wound == "flip")[:, None, None], -r, r)
    r = np.where(mask & np.isin(wound, ("reset", "kill"))[:, None, None], 0.0, r)
    if arm.rel:
        J = kill_bonds(J, mask & (wound == "kill")[:, None, None], False)
    xi_stream = Stream(tag, cases, "record-noise", side=side)
    kept, rsign, buf = [], [], None
    for t in range(1, window + 1):
        i = (t - 1) % every
        if i == 0:
            buf = xi_stream.take(every)
        r = record_step(r, buf[i][idx], arm.eps, arm.kr, D.SIGMA_R, arm.kc, B, J)
        if arm.clamp:
            r = R0b.copy()
        if t % every == 0:
            kept.append(masked_sign(r, Tb, mask))
            rsign.append(sign(r, Tb))
    return r, np.array(kept), np.array(rsign)


def simulate_B(arm, conds, k, V, ema, R0, th, T, p, conserved, masks, born, cases, window, every, tag=D.TAG):
    """Body and record together. Returns final v, e, r and, every `every` updates, the body's sign agreement
    inside the patch, (snapshots, conditions x cases)."""
    nc = len(conds)
    side = R0.shape[-1]
    idx = np.tile(np.arange(k), nc)
    thb, R0b, Tb = th[idx], R0[idx], T[idx]
    B = bproj(R0, 4)[idx]
    J = bonds(R0b, arm.rel)
    mask, wound = _wound_fields(conds, k, masks, side)
    nb = np.concatenate([born[c] if born[c] is not None else np.zeros((k, side, side)) for c in range(nc)])
    v, e, r = V[idx].copy(), ema[idx].copy(), R0b.copy()
    flip = mask & (wound == "flip")[:, None, None]
    reset = mask & np.isin(wound, ("reset", "kill"))[:, None, None]
    v, r = np.where(flip, -v, v), np.where(flip, -r, r)
    v, e, r = np.where(reset, nb, v), np.where(reset, nb, e), np.where(reset, 0.0, r)
    if arm.rel:
        J = kill_bonds(J, mask & (wound == "kill")[:, None, None], False)
    z_stream = Stream(tag, cases, "future", side=side)
    xi_stream = Stream(tag, cases, "record-noise", side=side)
    gain = NATIVE.gain
    les_v, zb, xb = [], None, None
    for t in range(1, window + 1):
        i = (t - 1) % every
        if i == 0:
            zb, xb = z_stream.take(every), xi_stream.take(every)
        v, e, _ = body_step(v, e, r, thb, zb[i][idx], p, conserved, gain)
        r = record_step(r, xb[i][idx], arm.eps, arm.kr, D.SIGMA_R, arm.kc, B, J)
        if arm.clamp:
            r = R0b.copy()
        if t % every == 0:
            les_v.append(masked_sign(v, Tb, mask))
    return v, e, r, np.array(les_v)


def committed_kept(r, T, m):
    return ((((r > 0) == (T > 0)) & (np.abs(r) > D.COMMIT) & m).sum((-2, -1)) / np.maximum(m.sum((-2, -1)), 1))


def outside_agree(v, T, m):
    out = ~m
    return (((v > 0) == (T > 0)) & out).sum((-2, -1)) / np.maximum(out.sum((-2, -1)), 1)


def t95(curve, every):
    """First snapshot time at which kept >= 0.95, per branch; np.inf if never within the window."""
    hit = curve >= 0.95
    first = np.argmax(hit, axis=0)
    return np.where(hit.any(axis=0), (first + 1) * every, np.inf)
