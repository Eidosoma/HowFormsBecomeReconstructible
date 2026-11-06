"""SM001's tissue: BE006's at clock F (be006.sim.sig_targets unchanged and imported; be002.sim's footprint, conductances,
sparse LU and be001.sim's cable kernel; DL001's body; LR004's record of relations through msegrid's record step; LR005's
anchors and arbiter), on a side x side periodic sheet of any side, with the coupling lengths, the signal's delay and the
commitment's decay time set per arm, and the patch and footprint set per run. Then NP001's fresh successor
(np001.sim.successor's arithmetic) at the same side.

BE001-BE006's own code reads the module constant SIDE (32) in its patch, anchor and state builders, so those builders
are rewritten here with the side as an argument, with identical arithmetic and identical addressed draws. With side 32,
clock F, lam_rest 3, lam_sig 1, tau_c 300, a footprint dilation of 2 and LR005's random patch, a run equals
be006.sim.run's dial-F and never-F bit for bit, and the successor equals np001.sim.successor bit for bit (checks Q3).

Branches are arm-major (index = arm x cases + case). One update, in order, as in be006.sim.run: the body reads the
record; bond noise (one rate for every arm); the record steps through its bonds; the trusted targets
(be006.sim.sig_targets: the arbiter outside commitment, the cable detector with each arm's coupling lengths, the
commitment decaying by exp(-1 / tau_c)); the pull toward committed signs; Hebbian relearning at one rate (the arbiter's
rate equal to every other bond's, so be006's eta_a branch is idle).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from be001.sim import cable_kernel
from be002 import sim as B2S
from be006 import design as B6
from be006.sim import sig_targets
from dl001 import design as DL
from dl001 import sim as S
from dl002 import design as D2
from lr001.sim import cut_for, edges_from, halves
from lr002 import sim as L2S
from lr005 import sim as L5S
from mse.assay import enrol
from mse.native import NATIVE, address
from msegrid.core import R_STAR, Stream, acquire, base, birth, bonds, record_step

from . import design as D

ENDS = ("r_in", "r_all", "v_in", "r_fp", "n_anc_ok")
ENDS2 = ("in", "in_gen", "align", "r_align", "shape", "spacing", "agree")


# the patterns, the acquisition and the event, at any side ---------------------------------------------------------

def template(pattern, kind, side, block):
    """+-1 stripes of width w (pattern 'W<w>'), across columns for kinds 0 and 2 and transposed for 1 and 3, negated for
    kinds 2 and 3. At side 32, W4 equals dl001.sim.template('S4'), W8 msegrid.base('S8') and W16 msegrid.base('F0')."""
    w = int(pattern[1:])
    f = np.tile(np.where((np.arange(side) // w) % 2 == 0, 1.0, -1.0), (side, 1))
    if kind % 2 == 1:
        f = f.T.copy()
    return f if kind < 2 else -f


def prepare(pattern, side, block, purpose):
    """dl002.sim.prepare at any side (DL002's tag, messages, parents, amplitude and acquisition, unchanged)."""
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, purpose)
    T = np.stack([D2.AMPLITUDE * template(pattern, c.message, side, block) for c in cases])
    V, ema, R0, th = acquire(D2.TAG, cases, T, replace(NATIVE, sigma=D2.SIGMA_ACQ), side,
                             settle=D2.SETTLE, teach=D2.TEACH, release=D2.RELEASE)
    return cases, V, ema, R0, th, T


def wall_axis(kind):
    """The axis along which the stripes change sign: columns (-1) for kinds 0 and 2, rows (-2) for 1 and 3."""
    return -1 if kind % 2 == 0 else -2


def patch(cases, size, side, w, place, tag):
    """The patch. 'random': LR005's draw (address(tag, case, 'patch'), uniform corner on the torus). 'mid': centred in a
    stripe across its width at a random stripe and position along it; 'cross': straddling a wall symmetrically (size
    even). Both draw from address(tag, case, 'place')."""
    out = np.zeros((len(cases), side, side), bool)
    for j, c in enumerate(cases):
        if place == "random":
            a, b = address(tag, *c.key(), "patch").integers(0, side, 2)
            out[j][np.ix_(np.arange(a, a + size) % side, np.arange(b, b + size) % side)] = True
            continue
        g = address(tag, *c.key(), "place")
        stripe, along = int(g.integers(0, side // w)), int(g.integers(0, side))
        a = stripe * w + (w - size) // 2 if place == "mid" else (stripe + 1) * w - size // 2
        ia, ib = np.arange(a, a + size) % side, np.arange(along, along + size) % side
        if wall_axis(c.message) == -1:
            out[j][np.ix_(ib, ia)] = True
        else:
            out[j][np.ix_(ia, ib)] = True
    return out


def wall_distance(T, m, w, kind):
    """-1 if the patch straddles a wall, else the distance (sites) from the patch to the nearest wall."""
    inside = T[m]
    if (inside > 0).any() and (inside < 0).any():
        return -1
    rows, cols = np.where(m)
    across = cols if wall_axis(kind) == -1 else rows
    return int(min(min(x % w, w - 1 - x % w) for x in across))


def anchor_mask(cases, side, tag):
    """lr005.sim.anchor_mask at any side: a quarter of the cells, addressed per case."""
    n = side * side
    out = np.zeros((len(cases), side, side), bool)
    for j, c in enumerate(cases):
        out[j].flat[address(tag, *c.key(), "anchors", D.DENSITY).permutation(n)[: n // D.DENSITY]] = True
    return out


def memory_event(size, cases, V0, ema0, R0, T, side, w, place, tag):
    """be001.sim.event('memory') at any side: the patch's record flipped, its bonds rebuilt consistent with it."""
    m = patch(cases, size, side, w, place, tag)
    am = anchor_mask(cases, side, tag)
    V, E, r = V0.copy(), ema0.copy(), np.where(m, -R0, R0)
    H, W = edges_from(bonds(r, True))
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    aval = np.where(R0 > 0, 1.0, -1.0)
    return dict(V=V, E=E, r=r, H=H, W=W, Hb=Hb, Wb=Wb, aval=aval, am=am, m=m)


def new_state(k, fp, lam_rest, lam_sig, side):
    """be005.sim.new_state at any side, with the arm's coupling lengths."""
    z = np.zeros((k, side, side))
    return {"v": z.copy(), "s": z.copy(), "sgn": z.copy(), "lus": None, "fp": fp,
            "g": B2S.conductances(fp, lam_rest, lam_sig), "kernel": cable_kernel(lam_rest, n=side),
            "onset": np.full(k, -1.0), "hit": np.zeros((k, side, side), bool)}


# the episode -------------------------------------------------------------------------------------------------------

def run(size, arms, cases, V0, ema0, R0, th, T, side, w, place="random", dil=D.DIL, tag=D.TAG, window=D.WINDOW,
        reads=D.READS, body=D.BODY, theta=D.THETA, gain=D.GAIN, rate=D.P_B, eta=D.ETA):
    """One episode: the memory event, then every arm (dicts with lam_rest, lam_sig, delay, tau_c, never) for `window`
    updates, each arm's signal on from delay + 1 to delay + DURATION unless never. Returns the reads and the final
    states."""
    alpha, L = DL.BODIES[body]
    G = S.ghat(side, L) if alpha else None
    k, na = len(cases), len(arms)
    ev = memory_event(size, cases, V0, ema0, R0, T, side, w, place, tag)
    m = ev["m"]
    fp = B2S.footprint(m, dil)
    idx = np.tile(np.arange(k), na)
    V, E, r = ev["V"][idx].copy(), ev["E"][idx].copy(), ev["r"][idx].copy()
    H, W, Hb, Wb = (ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb"))
    Tb, thb, mb, fpb = T[idx], (th * theta)[idx], m[idx], fp[idx]
    ab = (m & ev["am"])[idx]
    P = {"am": ev["am"], "aval": ev["aval"]}
    cut = cut_for(rate)
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs, zs = (Stream(tag, cases, s, side=side) for s in ("future", "record-noise", "bond-noise"))
    out = {key: [] for key in ENDS}
    states = [new_state(k, fp, a["lam_rest"], a["lam_sig"], side) for a in arms]
    prms = [{"tau_c": a["tau_c"]} for a in arms]
    first = [a["delay"] + 1 for a in arms]
    last = [a["delay"] + D.DURATION for a in arms]
    signal_updates = [0] * na
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(D.CHUNK), xs.take(D.CHUNK), zs.take(D.CHUNK)
        V, E, Vt, drift, dd = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], D.EPS, D.KR, D.SIGMA_R, D.KC, None, halves(H, W))
        for ai, a in enumerate(arms):
            sl = slice(ai * k, (ai + 1) * k)
            on = (first[ai] <= t <= last[ai]) and not a["never"]
            signal_updates[ai] += int(on)
            onset_m = m if (t == first[ai] and not a["never"]) else None
            xh, xw, extra, fix = sig_targets(prms[ai], V[sl], r[sl], P, states[ai], on, onset_m)
            zone, tt = extra
            r[sl] = np.where(zone, r[sl] + D.EPS * D.PULL * (tt * R_STAR - r[sl]), r[sl])
            lh, lw = xh != 0, xw != 0
            Hn, Wn = Hb[sl] + eta * (xh - Hb[sl]), Wb[sl] + eta * (xw - Wb[sl])
            Hb[sl], Wb[sl] = np.where(lh, Hn, Hb[sl]), np.where(lw, Wn, Wb[sl])
            H[sl] = np.where(lh & (Hb[sl] != 0), np.sign(Hb[sl]), H[sl])
            W[sl] = np.where(lw & (Wb[sl] != 0), np.sign(Wb[sl]), W[sl])
        if t in reads:
            out["r_in"].append(L5S.inside(r, Tb, mb))
            out["r_all"].append(S.sign(r, Tb))
            out["v_in"].append(L5S.inside(V, Tb, mb))
            out["r_fp"].append(L5S.inside(r, Tb, fpb))
            out["n_anc_ok"].append((((r > 0) == (Tb > 0)) & ab).sum((-2, -1)).astype(float))
    res = {key: np.array(v) for key, v in out.items()}
    hit = np.concatenate([(states[ai]["hit"] & m).sum((-2, -1)) / m.sum((-2, -1)) for ai in range(na)])
    onset = np.concatenate([states[ai]["onset"] for ai in range(na)])
    res.update(hit=hit, onset=onset, signal_updates=signal_updates, m=m, fp=fp, V=V, r=r, H=H, W=W)
    return res


# the successor -----------------------------------------------------------------------------------------------------

class _Protected:
    """No bond noise, no relearning, no parity: the record steps through its bonds only (np001.sim._Protected)."""
    rate, learn, parity = 0.0, "", False


def in_generic(V, T, m, w):
    """The best agreement inside the patch over every shift of the template across its stripes (any phase): generic
    stripe recovery, whatever the placement."""
    best = np.zeros(len(V))
    for ax in (-1, -2):
        for s in range(2 * w):
            best = np.maximum(best, L5S.inside(V, np.roll(T, s, ax), m))
    return best


def successor(r, H, W, cases, th, T, m, side, w, gains, tag=D.TAG, window=D.WINDOW2, reads=D.READS2, body=D.BODY,
              theta=D.THETA, stream=None):
    """np001.sim.successor at any side: a fresh body of kind `body`, born from newborn noise, reading each record (r, H,
    W: (nb x k, side, side), branch-major) at gains[branch] (0 for the no-record control), the record protected. Every
    branch of a case shares the birth and the noise. stream: the body name in the stream addresses (np001's uses the
    body)."""
    stream = body if stream is None else stream
    alpha, L = DL.BODIES[body]
    G = S.ghat(side, L) if alpha else None
    k, nb = len(cases), len(gains)
    idx = np.tile(np.arange(k), nb)
    V = birth(tag, cases, "successor", stream, side=side)[idx].copy()
    E = V.copy()
    r, H, W = r.copy(), H.copy(), W.copy()
    Hb, Wb = D.STRENGTH0 * H, D.STRENGTH0 * W
    Tb, thb, mb = T[idx], (th * theta)[idx], m[idx]
    P = L2S.params([_Protected()] * nb, k)
    gain = np.repeat(np.asarray(gains, float), k)[:, None, None]
    p = replace(NATIVE, sigma=D.SIGMA)
    st, xs = (Stream(tag, cases, s, stream, side=side) for s in ("successor-future", "successor-record-noise"))
    zero = np.zeros_like(V)
    out = {key: [] for key in ENDS2}
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf, xbuf = st.take(D.CHUNK), xs.take(D.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        H, W, Hb, Wb, r = L2S.relations(H, W, Hb, Wb, r, xbuf[i][idx], zero, V, P, D.KC, None)
        if t in reads:
            out["in"].append(L5S.inside(V, Tb, mb))
            out["in_gen"].append(in_generic(V, Tb, mb, w))
            out["align"].append(S.sign(V, Tb))
            out["r_align"].append(S.sign(r, Tb))
            out["shape"].append(S.best_shift(V, Tb))
            out["spacing"].append(S.spacing(V))
            out["agree"].append(((V > 0) == (r > 0)).mean((-2, -1)))
    res = {key: np.array(v) for key, v in out.items()}
    res.update(V=V)
    return res
