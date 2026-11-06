"""AR005's guarded pooled detector (vguard) and the vote-default run that carries it.

detect(): ar002.sim.detect, imported unchanged, for every configuration without a guard (the vote, vms, vpool). With
cfg['guard'] it is the same update for the cue channel alone (DET_POOL's: boxes 2-12, n 3, q 1, ring 2, ring_max 1,
dwell 1), its windows from guarded_windows: ar002.sim.cue_windows_multi's counts (the same integral images) and
criterion, and one guard more, counted over the same window:
  body:  the confident body disagrees with the record at a share of at least f of the window's disagreeing live anchors;
  dense: the window holds live anchors at a density of at least delta (k >= delta b^2).
The dwell is counted per box, the zone is every cell of the windows held at that update, and the detector fires once
per case through ar002.sim.fire, as in ar002.sim.detect. With a pass-all guard (f 0, delta 0) the windows are
cue_windows_multi's exactly.

run_vg: ar003.sim.run_vd's own source, compiled in a copy of ar003.sim's namespace with its one detector call routed
through detect() (the substitution is asserted to apply exactly once). For the vote, vms and vpool it is run_vd bit for
bit (checks Q3: the bridge against AR004's outputs).
"""
from __future__ import annotations

import inspect

import numpy as np

from ar002 import sim as A2S
from ar003 import sim as S3
from lr005 import sim as L5S

ENDS, SCALARS, DET_SCALARS = S3.ENDS, S3.SCALARS, S3.DET_SCALARS
RUN_VD_CALL = "A2S.detect(sta, V[sl], r[sl], P, cfgs[ai], t, m)"


def guarded_windows(V, r, P, ch, guard):
    """{box: (k, n, n) bool}: cue_windows_multi's windows at every box in ch['boxes'] that also pass the guard."""
    n = r.shape[-1]
    sr = L5S.vote_sign(r)
    ca = np.where(P["am"], P["aval"], 0.0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    g = ch.get("ring", 0)
    lo, hi = g, max(ch["boxes"]) + g
    Sd, Sl = A2S.integral(dis, lo, hi), A2S.integral(live, lo, hi)
    if guard["kind"] == "body":
        sv = L5S.vote_sign(V)
        Sb = A2S.integral(dis & (sv != 0) & (sv != sr), lo, hi)
    elif guard["kind"] != "dense":
        raise ValueError(guard["kind"])
    out = {}
    for b in ch["boxes"]:
        nd, nl = A2S.window_sums(Sd, lo, b, 0, n), A2S.window_sums(Sl, lo, b, 0, n)
        f = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
        if g:
            f &= (A2S.window_sums(Sd, lo, b + 2 * g, -g, n) - nd) <= ch["ring_max"]
        if guard["kind"] == "body":
            f &= A2S.window_sums(Sb, lo, b, 0, n) >= guard["f"] * nd
        else:
            f &= nl >= guard["delta"] * b * b
        out[b] = f
    return out


def detect(state, V, r, P, cfg, t, m=None):
    """One update of an arm's detector, before the targets: ar002.sim.detect for a configuration without a guard;
    with cfg['guard'], ar002.sim.detect's arithmetic for the cue channel with guarded_windows' windows."""
    if "guard" not in cfg:
        return A2S.detect(state, V, r, P, cfg, t, m)
    waiting = state["t_on"] == 0
    if not waiting.any():
        return
    ch = cfg["cue"]
    held = []
    for b, f in guarded_windows(V, r, P, ch, cfg["guard"]).items():
        cnt = state["count"].get(("cue", b))
        cnt = np.where(f, (np.zeros(f.shape, np.int32) if cnt is None else cnt) + 1, 0)
        state["count"][("cue", b)] = cnt
        held.append((b, cnt >= ch["dwell"]))
    by = np.zeros(len(V), int)
    nwin = np.zeros(len(V), int)
    for b, ready in held:
        by |= np.where(ready.any((-2, -1)), 1, 0)
        nwin += ready.sum((-2, -1))
    new = (by > 0) & waiting
    if new.any():
        zone = np.zeros(V.shape, bool)
        for b, ready in held:
            zone |= A2S.cover(ready, b)
        for j in np.flatnonzero(new):
            A2S.fire(state, j, zone[j], t, int(nwin[j]), int(by[j]))


def derive(fn, namespace, old=None, new=None):
    """fn's own source (with `old` replaced by `new`, which must occur exactly once), compiled in `namespace`."""
    src = inspect.getsource(fn)
    if old is not None:
        if src.count(old) != 1:
            raise RuntimeError(f"{fn.__module__}.{fn.__name__}: '{old}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    exec(compile(src, f"<{fn.__module__}.{fn.__name__}, routed by ar005>", "exec"), namespace)
    return namespace[fn.__name__]


run_vg = derive(S3.run_vd, dict(vars(S3), detect=detect), RUN_VD_CALL, "detect(sta, V[sl], r[sl], P, cfgs[ai], t, m)")
