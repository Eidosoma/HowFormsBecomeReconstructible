"""E2E005's successors: E2E004's batched generation with a per-cell rule mask set by a controller in each newborn.

generation  e2e004.sim.generation's own source (AR001's update for branches that start from their own states), compiled
            in a copy of e2e004.sim's namespace with two declared substitutions, each asserted to apply exactly once:
              (1) TARGETS: its targets call is routed through route_targets(). For a fixed route (body, vote, record) it
                  is lr005.sim.targets with the route's own target, unchanged. For a switched route (ctl, ctl:<candidate>,
                  oracle) the group's switch first reads the group's own bodies and records (the controller's detector,
                  at its read updates, after the record's step and before the targets, where AR002's detector reads);
                  then the targets are the body's co-activity (AR001's "body") on the bonds touching an open footprint
                  and the record's own relations (AR001's "record", LR001's record+parity) elsewhere.
              (2) PARITY: its record-route parity block is opened to the switched routes through route_parity(): LR001's
                  parity repair, kept on the record-rule bonds only (a bond touching an open footprint keeps its
                  body-rule sign and strength).
            So a switched branch with no switch open is the record route bit for bit, and one whose whole sheet is open
            from update 1 is the body route bit for bit (P62s, Q3); the fixed routes are E2E004's own arithmetic, and a
            branch's arithmetic does not depend on the other groups in its call (Q8).
Switch      one switched group's state in one generation, made fresh at every birth (no detector state, count or
            footprint crosses a boundary). Per branch: the onset t_on (0 until it fires), the zone (the cells of the
            windows held at the firing read), the footprint (the zone dilated by d, BE002's square dilation) and the
            open bonds (BE002's junctions touching the footprint), open from t_on to the generation's end (duration None)
            or for `duration` updates. The controller's detector (windows) reads V and r only. The oracle opens over the
            inherited patch at read_from; the patch reaches the switch only for the oracle and for the diagnostics, which
            are reporting quantities and never feed back.
lineage     e2e004.sim.lineage's loop (births, the vote's second record a copy of the incoming one, the reads at the
            horizons, the kept states, sr001.sim.handoff), with fresh switches for every generation and every generation's
            switch diagnostics.
packets     e2e004.sim.packets, unchanged: identical (packet, route) rows run once, every label they stand for named.
"""
from __future__ import annotations

import inspect

import numpy as np

from ar002 import sim as A2S
from be002 import sim as B2S
from e2e004 import sim as E4
from lr001.sim import parity_repair
from lr005 import sim as L5S
from msegrid.core import birth
from sr001 import sim as SRS

from . import design as D

score, protected, post_damage, packets = E4.score, E4.protected, E4.post_damage, E4.packets
BIRTH_NAMES, GEN_NAMES = E4.BIRTH_NAMES, E4.GEN_NAMES
TARGETS_OLD = "xh, xw, _extra = L5S.targets(TARGET[route], Vs, rs, second, None, None)"
TARGETS_NEW = "xh, xw, _extra = route_targets(route, ix, t, Vs, rs, second)"
PARITY_OLD = 'if route == "record":\n                H2, W2 = parity_repair(Hs, Ws)'
PARITY_NEW = "if takes_parity(route):\n                H2, W2 = route_parity(route, _extra, Hs, Ws)"
SUBSTITUTIONS = ((TARGETS_OLD, TARGETS_NEW), (PARITY_OLD, PARITY_NEW))
DIAGS = ("fired", "t_on", "zone", "fp", "zone_in", "fp_in", "bonds", "nwin", "box_min", "box_max")
_SWITCHES = None                          # the switches of the generation now running ({route: Switch})


# the detector --------------------------------------------------------------------------------------------------------

def confident(x, c):
    """+1, -1 or 0: the sign of a value at least c in magnitude (lr005.sim.vote_sign at c = VMIN = 0.2)."""
    return np.where(x >= c, 1.0, np.where(x <= -c, -1.0, 0.0))


def windows(V, r, cfg):
    """{box: (k, n, n) bool}: by top-left corner (periodic), the windows where the newborn's confident body disagrees
    with its confident record in at least cfg['n'] cells and in at least a fraction cfg['q'] of the cells where both are
    confident (q 1: every one), with at most cfg['ring_max'] disagreeing cells in the ring of width cfg['ring'] around
    the window. ar002.sim.cue_windows_multi's counts (the same integral images and window sums, exact integers), with the
    body's disagreement with the record in place of the anchors'. It reads V and r only."""
    n = r.shape[-1]
    sv, sr = confident(V, cfg["c"]), confident(r, cfg["c"])
    both = (sv != 0) & (sr != 0)
    dis = both & (sv != sr)
    g = cfg["ring"]
    lo, hi = g, max(cfg["boxes"]) + g
    Sd, Sb = A2S.integral(dis, lo, hi), A2S.integral(both, lo, hi)
    out = {}
    for b in cfg["boxes"]:
        nd, nb = A2S.window_sums(Sd, lo, b, 0, n), A2S.window_sums(Sb, lo, b, 0, n)
        f = (nd >= cfg["n"]) & (nd >= cfg["q"] * nb)
        if g:
            f &= (A2S.window_sums(Sd, lo, b + 2 * g, -g, n) - nd) <= cfg["ring_max"]
        out[b] = f
    return out


class Switch:
    """One switched group's switches for one generation (see the module's docstring). m: (branches, n, n), the
    inherited patch, read by the oracle and the diagnostics only."""

    def __init__(self, route, cfg, m):
        self.route, self.cfg = route, cfg
        self.m = np.asarray(m, bool)
        nb = len(self.m)
        self.t_on = np.zeros(nb, int)
        self.zone = np.zeros(self.m.shape, bool)
        self.fp = np.zeros(self.m.shape, bool)
        self.nwin = np.zeros(nb, int)
        self.box_min = np.zeros(nb, int)
        self.box_max = np.zeros(nb, int)
        self.count = {}
        self.reads = 0
        self._key, self._masks = None, None

    def fire(self, j, zone, t, nwin=0, bmin=0, bmax=0):
        self.t_on[j], self.zone[j] = t, zone
        self.fp[j] = B2S.footprint(zone[None], self.cfg["d"])[0]
        self.nwin[j], self.box_min[j], self.box_max[j] = nwin, bmin, bmax

    def read(self, t, V, r):
        """The update's read, after the record's step and before the targets: the oracle's or the full switch's
        opening, or the controller's detector."""
        cfg = self.cfg
        if cfg.get("never"):
            return
        waiting = self.t_on == 0
        if not waiting.any():
            return
        if cfg.get("full"):                       # a bridge's switch only: the whole sheet from update 1
            if t == 1:
                for j in np.flatnonzero(waiting):
                    self.fire(j, np.ones(self.m.shape[1:], bool), 1)
            return
        t0 = cfg["read_from"]
        if cfg.get("oracle"):
            if t == t0:
                for j in np.flatnonzero(waiting):
                    self.fire(j, self.m[j], t)
            return
        if t < t0 or (t - t0) % cfg["read_every"]:
            return
        self.reads += 1
        w = np.flatnonzero(waiting)
        held = []
        for b, f in windows(V[w], r[w], cfg).items():
            cnt = self.count.get(b)
            if cnt is None:
                cnt = self.count[b] = np.zeros((len(self.t_on),) + f.shape[1:], np.int32)
            cnt[w] = np.where(f, cnt[w] + 1, 0)
            held.append((b, cnt[w] >= cfg["dwell"]))
        ready = np.zeros(len(w), bool)
        for _b, rd in held:
            ready |= rd.any((-2, -1))
        for jj in np.flatnonzero(ready):
            zone = np.zeros(self.m.shape[1:], bool)
            nwin, boxes = 0, []
            for b, rd in held:
                if rd[jj].any():
                    zone |= A2S.cover(rd[jj][None], b)[0]
                    nwin += int(rd[jj].sum())
                    boxes.append(b)
            self.fire(w[jj], zone, t, nwin, min(boxes), max(boxes))

    def masks(self, t):
        """(mh, mw): the open bonds (BE002's junctions touching an open footprint), or None when none is open."""
        on = (self.t_on > 0) & (t >= self.t_on)
        if self.cfg.get("duration") is not None:
            on &= t < self.t_on + self.cfg["duration"]
        if not on.any():
            return None
        key = on.tobytes()
        if key != self._key:
            fp = self.fp & on[:, None, None]
            self._key, self._masks = key, (fp | np.roll(fp, -1, -1), fp | np.roll(fp, -1, -2))
        return self._masks

    def diagnostics(self):
        """Per branch, at the generation's end: fired, the onset (-1 if not), the zone's and the footprint's cells, those
        inside the patch, the open mask's size (bonds: BE002's junctions touching the footprint, open from the onset to
        the generation's end), and the windows held at the firing with their smallest and largest box."""
        fired = self.t_on > 0
        fp = self.fp
        bonds = (fp | np.roll(fp, -1, -1)).sum((-2, -1)) + (fp | np.roll(fp, -1, -2)).sum((-2, -1))
        return {"fired": fired.astype(float), "t_on": np.where(fired, self.t_on, -1).astype(float),
                "zone": self.zone.sum((-2, -1)).astype(float), "fp": fp.sum((-2, -1)).astype(float),
                "zone_in": (self.zone & self.m).sum((-2, -1)).astype(float),
                "fp_in": (fp & self.m).sum((-2, -1)).astype(float), "bonds": bonds.astype(float),
                "nwin": self.nwin.astype(float), "box_min": self.box_min.astype(float),
                "box_max": self.box_max.astype(float)}


# the routed generation ------------------------------------------------------------------------------------------------

def takes_parity(route):
    return route in D.PARITY or route.startswith("ctl:")


def route_targets(route, ix, t, Vs, rs, second):
    """The bond targets (xh, xw) of one group at update t, and the open bonds (None for a fixed route or with no switch
    open)."""
    if route in D.FIXED:
        return L5S.targets(E4.TARGET[route], Vs, rs, second, None, None)
    sw = _SWITCHES[route]
    sw.read(t, Vs, rs)
    rh, rw, _x = L5S.targets("record+parity", Vs, rs, None, None, None)
    mk = sw.masks(t)
    if mk is None:
        return rh, rw, None
    bh, bw, _x = L5S.targets("body", Vs, rs, None, None, None)
    mh, mw = mk
    return np.where(mh, bh, rh), np.where(mw, bw, rw), mk


def route_parity(route, extra, Hs, Ws):
    """LR001's parity repair, kept on the record-rule bonds only."""
    H2, W2 = parity_repair(Hs, Ws)
    if extra is None:
        return H2, W2
    mh, mw = extra
    return np.where(mh, Hs, H2), np.where(mw, Ws, W2)


def _derive(fn, namespace, subs):
    """fn's own source with every (old, new) substitution applied (each old must occur exactly once), compiled in
    namespace."""
    src = inspect.getsource(fn)
    for old, new in subs:
        if src.count(old) != 1:
            raise RuntimeError(f"{fn.__module__}.{fn.__name__}: '{old}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    exec(compile(src, f"<{fn.__module__}.{fn.__name__}, routed by e2e005>", "exec"), namespace)
    return namespace[fn.__name__]


_NS = dict(vars(E4), route_targets=route_targets, route_parity=route_parity, takes_parity=takes_parity)
generation = _derive(E4.generation, _NS, SUBSTITUTIONS)


def route_order():
    return list(D.FIXED) + ["ctl"] + [f"ctl:{c}" for c in D.CANDIDATES] + ["oracle"]


def groups_of(routes, k):
    """[(route, branch indices)] for rows' route names (row-major branches), in route_order()."""
    out = []
    for name in route_order():
        rows = [j for j, p in enumerate(routes) if p == name]
        if rows:
            out.append((name, np.concatenate([np.arange(j * k, (j + 1) * k) for j in rows])))
    if sum(len(ix) for _r, ix in out) != len(routes) * k:
        raise ValueError(f"a route without a definition: {sorted(set(routes) - set(route_order()))}")
    return out


def run_generation(body, groups, cases, V, E, A_, B_, thb, tag, names, window=D.T_GEN, m=None, cfgs=None):
    """The routed generation with fresh switches for its switched groups (cfgs: {route: cfg} overrides, for the bridges
    and checks). Returns (V, E, A, B) and the switches."""
    global _SWITCHES
    sw = {}
    for route, ix in groups:
        if route in D.FIXED:
            continue
        cfg = (cfgs or {}).get(route) or D.route_cfg(route)
        sw[route] = Switch(route, cfg, np.zeros((len(ix), D.SIDE, D.SIDE), bool) if m is None else m[ix])
    if _SWITCHES is not None:
        raise RuntimeError("a generation is already running in this process")
    _SWITCHES = sw
    try:
        out = generation(body, groups, cases, V, E, A_, B_, thb, tag, names, window)
    finally:
        _SWITCHES = None
    return out, sw


def lineage(body, rows, cases, thf, T, Tf, m, tag, gen_names, birth_names, t_gen=D.T_GEN, horizons=D.HORIZONS, keep=(),
            cfgs=None):
    """rows: dicts {"packet": (H, W, r) each (cases, side, side), "route", "stop"}. Returns the reads at the horizons
    ({g: {endpoint: (rows alive, cases)}}), the rows alive at each generation, the states kept at the generations in
    `keep`, and every generation's switch diagnostics ({g: {diag: (rows alive, cases)}}; 0 or -1 for a fixed route)."""
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, kept, diags = {}, {}, {}, {}
    for g in range(1, max(row["stop"] for row in rows) + 1):
        still = [i for i in alive if rows[i]["stop"] >= g]
        if still != alive:
            sel = np.concatenate([np.arange(alive.index(i) * k, (alive.index(i) + 1) * k) for i in still])
            A_ = tuple(x[sel] for x in A_)
            alive = still
        idx = np.tile(np.arange(k), len(alive))
        V = birth(tag, cases, *birth_names(g), side=D.SIDE)[idx].copy()
        E = V.copy()
        groups = groups_of([rows[i]["route"] for i in alive], k)
        ixv = dict(groups).get("vote")
        B_ = None if ixv is None else tuple(x[ixv].copy() for x in A_)
        (V, E, A_, _B), sw = run_generation(body, groups, cases, V, E, A_, B_, thf[idx], tag, gen_names(g), t_gen,
                                            m=m[idx], cfgs=cfgs)
        dg = {key: np.zeros(len(alive) * k) for key in DIAGS}
        dg["t_on"][:] = -1.0
        for route, ix in groups:
            if route in sw:
                for key, v in sw[route].diagnostics().items():
                    dg[key][ix] = v
        diags[g] = {key: v.reshape(len(alive), k) for key, v in dg.items()}
        if g in horizons:
            sc = score(V, A_[4], T[idx], Tf[:, idx], m[idx])
            reads[g] = {key: v.reshape(len(alive), k) for key, v in sc.items()}
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        A_, _ = SRS.handoff(A_, None)
    return reads, alive_at, kept, diags
