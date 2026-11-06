"""AR006's split guard (vtol) and the vote-default run that carries it.

windows(): ar005.sim.guarded_windows, imported unchanged, for every guard but the split. The split guard (vtol) holds,
at every box of DET_POOL's cue channel, the windows held with at most guard['free_ring_max'] (0, DET_STAR's) disagreeing
live anchors in the surround, unguarded, united with the windows held at the channel's ring_max (1) whose disagreeing
live anchors the confident body disagrees with the record at a share of at least guard['f'] (0.5, AR005's g-body-f05):
DET_STAR's windows united with the guarded pooled windows, by the same integral-image counts (ar002.sim.integral,
window_sums), computed once.

detect(): ar005.sim.detect's own source, compiled in a copy of ar005.sim's namespace with its one windows call routed
through windows() (the substitution is asserted to apply exactly once): ar002.sim.detect for a configuration without a
guard, ar005's guarded update otherwise.

run_vt: ar003.sim.run_vd's own source, compiled by ar005.sim.derive with its one detector call routed through detect().
For the vote, vms, vpool and vguard it is AR005's run_vg bit for bit (checks Q3: the bridge against AR005's outputs).
"""
from __future__ import annotations

import numpy as np

from ar002 import sim as A2S
from ar003 import sim as S3
from ar005 import sim as S5
from lr005 import sim as L5S

ENDS, SCALARS, DET_SCALARS = S5.ENDS, S5.SCALARS, S5.DET_SCALARS
WINDOWS_CALL = 'guarded_windows(V, r, P, ch, cfg["guard"])'


def windows(V, r, P, ch, guard):
    """{box: (k, n, n) bool}: the guard's windows at every box in ch['boxes']."""
    if guard["kind"] != "split":
        return S5.guarded_windows(V, r, P, ch, guard)
    n = r.shape[-1]
    sr, sv = L5S.vote_sign(r), L5S.vote_sign(V)
    ca = np.where(P["am"], P["aval"], 0.0)
    live = (ca != 0) & (sr != 0)
    dis = live & (ca != sr)
    g = ch["ring"]
    lo, hi = g, max(ch["boxes"]) + g
    Sd, Sl = A2S.integral(dis, lo, hi), A2S.integral(live, lo, hi)
    Sb = A2S.integral(dis & (sv != 0) & (sv != sr), lo, hi)
    out = {}
    for b in ch["boxes"]:
        nd, nl = A2S.window_sums(Sd, lo, b, 0, n), A2S.window_sums(Sl, lo, b, 0, n)
        base = (nd >= ch["n"]) & (nd >= ch["q"] * nl)
        ring = A2S.window_sums(Sd, lo, b + 2 * g, -g, n) - nd
        free = base & (ring <= guard["free_ring_max"])
        pooled = base & (ring <= ch["ring_max"])
        out[b] = free | (pooled & (A2S.window_sums(Sb, lo, b, 0, n) >= guard["f"] * nd))
    return out


detect = S5.derive(S5.detect, dict(vars(S5), windows=windows), WINDOWS_CALL, 'windows(V, r, P, ch, cfg["guard"])')
run_vt = S5.derive(S3.run_vd, dict(vars(S3), detect=detect), S5.RUN_VD_CALL, "detect(sta, V[sl], r[sl], P, cfgs[ai], t, m)")
