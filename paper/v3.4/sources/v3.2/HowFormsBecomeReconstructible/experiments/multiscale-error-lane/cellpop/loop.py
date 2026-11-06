"""cellpop's run loop: one body over many branches, with an optional relational record and population events.

A branch is described by arrays, so every condition runs vectorised (branch index = condition x cases + case, as in
the lane's other studies; every branch of a case reads that case's streams). One update, in order:
  1. the body reads its reference (dl001.sim.body via cellpop.core.body_step), plus a diffusing signal as a field;
  2. with a record: bond noise, the record's step through its contacts, relearning (the record's or the body's
     co-activity), the plaquette rule;
  3. the diffusing signal's step;
  4. events: deaths, exchanges, divisions, scheduled divisions, and a prescribed front (DL003's activation rule).
With a full sheet, no events and no signal, steps 1-2 are dl001.sim.run's and lr004.sim.run's, bit for bit.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from lr001.sim import cut_for, parity_repair
from mse.native import NATIVE
from msegrid.core import R_STAR, Stream

from . import core as C


@dataclass
class Branches:
    """Per-branch settings, each (n, 1, 1) unless noted. Zero rates switch an event off."""
    gain: np.ndarray                          # (n, side, side): the body's read gain on its reference
    read: np.ndarray | None = None            # (n, side, side): a fixed reference (anchors); None: the record
    learn_record: np.ndarray | None = None    # relearn from the record's co-activity
    learn_body: np.ndarray | None = None      # relearn from the body's co-activity
    parity: np.ndarray | None = None          # the plaquette rule
    p_div: np.ndarray | None = None
    inherit: np.ndarray | None = None
    newborn: np.ndarray | None = None         # (n, side, side): daughters' values when they do not inherit
    p_die: np.ndarray | None = None
    p_swap: np.ndarray | None = None
    protected: np.ndarray | None = None       # (n, side, side): cells that never die or move
    fdist: np.ndarray | None = None           # (n, side, side): a prescribed front's distance map (-1: none)
    every: np.ndarray | None = None           # (n,): updates per line of the front
    tfill: np.ndarray | None = None           # (n, side, side): the update at which a scheduled division fills a site
    pdir: np.ndarray | None = None            # (n, side, side): the direction from that site to its parent
    kappa: np.ndarray | None = None           # the diffusing signal: coupling, decay, source mask and value, read gain
    decay: np.ndarray | None = None
    src: np.ndarray | None = None             # (n, side, side) bool: cells clamped to the source value
    src_val: np.ndarray | None = None         # (n, side, side)
    g_sig: np.ndarray | None = None
    extra: dict = field(default_factory=dict)


def evolve(body, st, br, cases, th, tag, stream, window, rate=0.0, eps=None, kr=None, sigma_r=None, kc=0.0,
           eta=None, sigma=0.1, chunk=250, observe=None, event_tag=None):
    """Advance the state `st` (dict of (n, side, side) arrays: occ, V, E and optionally r, H, W, Hb, Wb) for `window`
    updates. th: (n, side, side) environmental field per branch. stream: the address parts of the body's noise
    (e.g. ("future",)); the record's streams are ("record-noise",) and ("bond-noise",), the events' (*stream, "div"),
    ... under event_tag (default tag). observe(t, st, sig) is called after every update. Returns the final state and
    the signal."""
    alpha, L = DL.BODIES[body]
    side, n = st["V"].shape[-1], len(st["V"])
    k = len(cases)
    idx = np.tile(np.arange(k), n // k)
    G = S.ghat(side, L) if alpha else None
    p = replace(NATIVE, sigma=sigma)
    rec = C.has_record(st)
    cut = cut_for(rate)
    on_r = br.learn_record if br.learn_record is not None else np.zeros((n, 1, 1), bool)
    on_b = br.learn_body if br.learn_body is not None else np.zeros((n, 1, 1), bool)
    on_learn = on_r | on_b
    events = any(x is not None and np.any(x > 0) for x in (br.p_div, br.p_die, br.p_swap))
    front = br.fdist is not None and np.any(br.fdist >= 0)
    sched = br.tfill is not None and np.any(br.tfill > 0)
    signal = br.kappa is not None and np.any(br.kappa > 0)
    prot = br.protected if br.protected is not None else np.zeros_like(st["occ"])
    zero = np.zeros((n, 1, 1))
    st_bd = Stream(tag, cases, *stream, side=side)
    if rec:
        xs, zs = Stream(tag, cases, "record-noise", side=side), Stream(tag, cases, "bond-noise", side=side)
    if events:
        et = event_tag or tag
        us = {e: C.UStream(et, cases, *stream, e, side=side) for e in ("div", "dir", "die", "swap")}
    sig = np.zeros(st["V"].shape) if signal else None
    live = st["occ"].copy() if front else None
    for t in range(1, window + 1):
        i = (t - 1) % chunk
        if i == 0:
            buf = st_bd.take(chunk)
            if rec:
                xbuf, zbuf = xs.take(chunk), zs.take(chunk)
            if events:
                ubuf = {e: s.take(chunk) for e, s in us.items()}
        thb = th + br.g_sig * sig if signal else th
        st, _ = C.body_step(st, st["r"] if br.read is None else br.read, thb, buf[i][idx], p, br.gain, alpha, G)
        if rec:
            st = C.bond_noise(st, zbuf[i][idx], cut)
            st = C.record_on(st, xbuf[i][idx], eps, kr, sigma_r, kc)
            if on_learn.any():
                rh, rw = C.targets_record(st["r"], R_STAR)
                bh, bw = C.targets_body(st["V"])
                st = C.learn(st, np.where(on_b, bh, rh), np.where(on_b, bw, rw), eta, on_learn)
            if br.parity is not None and br.parity.any():
                st = C.parity(st, br.parity, parity_repair)
        if signal:
            sig = C.diffuse(sig, st["occ"], br.kappa, br.decay, 0.0)
            sig = np.where(br.src & st["occ"], br.src_val, sig)
        if events:
            u = {e: b[i][idx] for e, b in ubuf.items()}
            if br.p_die is not None:
                st, _ = C.die(st, br.p_die if br.p_die is not None else zero, u["die"], prot)
            if br.p_swap is not None:
                st, _ = C.swap(st, br.p_swap, u["swap"], t, prot)
            if br.p_div is not None:
                st, _ = C.divide(st, br.p_div, u["div"], u["dir"], br.inherit, br.newborn)
        if sched:
            st, _ = C.fill(st, br.tfill == t, br.pdir, br.inherit, br.newborn)
        if front:
            now = (br.fdist < 0) | (br.fdist * br.every[:, None, None] <= t)
            frontal = br.fdist >= 0
            born = now & ~live & frontal
            st = dict(st)
            st["V"] = np.where(born, br.newborn, np.where(now | ~frontal, st["V"], 0.0))
            st["E"] = np.where(born, br.newborn, np.where(now | ~frontal, st["E"], 0.0))
            st["occ"] = np.where(frontal, now, st["occ"])
            live = now
        if observe is not None:
            observe(t, st, sig)
    return st, sig
