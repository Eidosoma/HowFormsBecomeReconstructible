"""GC001's tissue: BE001's (be001.sim, imported, arithmetic unchanged) with anchored cells reading the cue field at a
quenched noisy position.

Branches are arm-major (index = arm x cases + case). One update, in order, exactly as in be001.sim.run: the body reads
the first record; bond noise; the record steps through its bonds; the trusted targets (the cue arm by lr005.sim.targets,
the bioelectric arms by be001.sim.bio_targets); the pull toward committed signs; Hebbian relearning. Only the anchors'
cue values differ. With sigma 0 a run equals be001.sim.run bit for bit (checks Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy import ndimage

from be001 import sim as B1S
from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, halves
from lr002.sim import prepare  # noqa: F401  (DL002's preparation, unchanged)
from lr005 import sim as L5S
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, record_step

from . import design as D

ENDS = ("r_all", "r_in", "v_all", "v_in", "r_in_old", "v_in_old", "r_band", "r_int", "walls")


def unit_normals(cases, tag=D.TAG):
    """The quenched unit normals g (case, axis, i, j), shared by every sigma."""
    return np.stack([address(tag, *c.key(), "gc-eps").standard_normal((2, D.SIDE, D.SIDE)) for c in cases])


def offsets(g, sigma):
    return np.rint(sigma * g[:, 0]).astype(int), np.rint(sigma * g[:, 1]).astype(int)


def read_at(field, g, sigma):
    """Each site reads field at its own displaced site (i + dx, j + dy), periodic; sigma 0 returns field unchanged."""
    if sigma == 0:
        return field
    dx, dy = offsets(g, sigma)
    i, j = np.meshgrid(np.arange(D.SIDE), np.arange(D.SIDE), indexing="ij")
    return np.stack([field[c][(i + dx[c]) % D.SIDE, (j + dy[c]) % D.SIDE] for c in range(field.shape[0])])


def matched_flips(cases, am, counts, tag=D.TAG):
    """In each case, counts[c] anchors chosen uniformly at random (one permutation per case, nested across sigma)."""
    out = np.zeros_like(am)
    for c, case in enumerate(cases):
        idx = np.flatnonzero(am[c])
        pick = address(tag, *case.key(), "gc-scatter").permutation(len(idx))[: int(counts[c])]
        out[c].flat[idx[pick]] = True
    return out


def boundary_distance(T):
    """Taxicab distance from every site to the nearest site of the other target sign, on the periodic sheet."""
    out = np.empty(T.shape, int)
    n = D.SIDE
    for c in range(T.shape[0]):
        pos = np.tile(T[c] > 0, (3, 3))
        d_in = ndimage.distance_transform_cdt(pos, metric="taxicab")         # positive sites: distance to a negative one
        d_out = ndimage.distance_transform_cdt(~pos, metric="taxicab")
        out[c] = np.where(pos, d_in, d_out)[n:2 * n, n:2 * n]
    return out


def walls(x):
    """Nearest-neighbour pairs of opposite sign (x > 0 against x <= 0), periodic, per branch."""
    s = x > 0
    return (s != np.roll(s, 1, -1)).sum((-2, -1)) + (s != np.roll(s, 1, -2)).sum((-2, -1))


def event(situation, size, sigma, cases, V0, ema0, R0, T, tag=D.TAG):
    """be001.sim.event (unchanged) for the base situation; then the anchors' noisy read of the event's cue field, or for
    scatter the matched random flips. Adds mis (misread anchors), dist (boundary distance of the event's target)."""
    base = "none" if situation == "scatter" else situation
    ev = B1S.event(base, size, cases, V0, ema0, R0, T, tag)
    exact = ev["aval"]
    g = unit_normals(cases, tag)
    if situation == "scatter":
        counts = ((read_at(exact, g, sigma) != exact) & ev["am"]).sum((-2, -1))
        ev["aval"] = np.where(matched_flips(cases, ev["am"], counts, tag), -exact, exact)
    else:
        ev["aval"] = read_at(exact, g, sigma)
    ev["mis"] = (ev["aval"] != exact) & ev["am"]
    ev["dist"] = boundary_distance(ev["target"])
    return ev


def run(body, situation, size, sigma, cases, V0, ema0, R0, th, T, theta, reads, gain=D.GAIN, rate=D.RATE, tag=D.TAG,
        window=D.WINDOW, arms=D.ARMS):
    """be001.sim.run's loop, unchanged, on GC001's event."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = event(situation, size, sigma, cases, V0, ema0, R0, T, tag)
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb = ev["target"][idx], (th * theta)[idx], ev["m"][idx]
    band, interior = (ev["dist"] == D.BAND)[idx], (ev["dist"] > D.BAND)[idx]
    wall_t = walls(ev["target"])[idx]
    oldb = None if ev["old"] is None else ev["old"][idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=D.SIDE) for s in ("future", "record-noise", "bond-noise"))
    bio = [a for a in arms if a in B1S.D.BIO]
    vs = Stream(tag, cases, "voltage-noise", side=D.SIDE) if bio else None
    out = {key: [] for key in ENDS}
    trace, trace_all = [], []
    opened = np.zeros(na * k)
    latches = {ai: (np.zeros((k, D.SIDE, D.SIDE), int), np.zeros((k, D.SIDE, D.SIDE))) for ai, a in enumerate(arms)
               if a.startswith("community")}
    states = {ai: {"v": np.zeros((k, D.SIDE, D.SIDE)), "s": np.zeros((k, D.SIDE, D.SIDE)),
                   "sgn": np.zeros((k, D.SIDE, D.SIDE)), "kernel": B1S.cable_kernel(B1S.D.BIO[a]["lam"])}
              for ai, a in enumerate(arms) if a in B1S.D.BIO}
    vbuf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
            if vs is not None:
                vbuf = vs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], B1S.D.EPS, B1S.D.KR, B1S.D.SIGMA_R, B1S.D.KC, None, halves(H, W))
        for ai, arm in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            if arm in B1S.D.BIO:
                xh, xw, extra = B1S.bio_targets(arm, V[sl], r[sl], P, states[ai], vbuf[i])
            else:
                xh, xw, extra = L5S.targets(arm, V[sl], r[sl], None, P, latches.get(ai))
            if extra is not None:
                zone, tt = extra
                opened[sl] += zone.mean((-2, -1))
                r[sl] = np.where(zone, r[sl] + B1S.D.EPS * B1S.D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + B1S.D.ETA * (xh - Hb[sl]), Wb[sl] + B1S.D.ETA * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if t % D.TRACE == 0:
            trace.append(L5S.inside(r, Tb, mb))
            trace_all.append(S.sign(r, Tb))
        if t in reads:
            out["r_all"].append(S.sign(r, Tb))
            out["v_all"].append(S.sign(V, Tb))
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            out["r_band"].append(L5S.inside(r, Tb, band))
            out["r_int"].append(L5S.inside(r, Tb, interior))
            out["walls"].append(walls(r) / wall_t - 1.0)
            if oldb is not None:
                out["r_in_old"].append(L5S.inside(r, oldb, mb))
                out["v_in_old"].append(L5S.inside(V, oldb, mb))
    res = {key: np.array(v) for key, v in out.items() if v}
    res.update(trace=np.array(trace), trace_all=np.array(trace_all), opened=opened / window, V=V, r=r, H=H, W=W,
               misread=ev["mis"].sum((-2, -1)) / ev["am"].sum((-2, -1)),
               misread_band=(ev["mis"] & (ev["dist"] == D.BAND)).sum((-2, -1)) / np.maximum(ev["mis"].sum((-2, -1)), 1))
    return res
