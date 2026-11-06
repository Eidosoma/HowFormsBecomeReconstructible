"""SM009's recipients: SM008's update and layout, with the response chosen per arm (PLAN_SM009.md).

The update is sm008.sim.run's (sm007.sim.run's over SM008's mixed layout), line for line, with sm007.sim's own stress,
emission and media and SM007's birth and noise names (sm007 and sm008 are frozen and imported, never edited). Every arm's
group has its medium; the response at update t reads, per branch:
  P ("field")     driver x_i                                   gain = G_DIST x (1 + KAPPA   x driver)   SM008's arithmetic
  O ("own")       driver s_i                                   gain = G_DIST x (1 + KAPPA_O x driver)
  R ("relative")  driver max(0, s_i - GAMMA x_i / f_i)         gain = G_DIST x (1 + KAPPA_R x driver)
with x_i the exposure after update t - 1's step (0 at t = 1) and s_i the sheet's stress at update t - 1 (0 at t = 1), and
f_i the field factor of the sheet's position in its medium (its steady exposure under a uniform emission GAMMA, in units of
the boundary-free level). With every kappa 0 the update is dl001.sim.run's bit for bit; a P arm is sm008.sim.run's bit for
bit (P65s; Q3). drivers=True accumulates all three drivers on every branch (P65k, at kappa 0, reads nothing).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from mse.native import NATIVE
from msegrid.core import Stream, birth
from sm007 import sim as S7
from sm008 import sim as S8

from . import design as D

FIELD_KINDS = ("field", "own", "relative")
inv = S7.inv
layout = S8.layout                       # SM008's layout, unchanged: (g + p) mod 8 of each position's role; iso8
members = S8.members
_FF = {}


def field_factor(shape, boundary, lam):
    """Each sheet's steady exposure under a uniform emission GAMMA (the boundary-free level 1): sm007.sim.field_factor."""
    k_ = (shape, boundary, lam)
    if k_ not in _FF:
        _FF[k_] = np.asarray(S7.field_factor(shape, boundary, lam), dtype=float)
    return _FF[k_]


def run(body, arrangements, cases, R0, th_case, T, tag, kappa=None, kappa_o=None, kappa_r=None, future=0, window=D.WINDOW,
        reads=D.READS, keep_final=True, stream=None, V_init=None, trace_until=0, drivers=False):
    """Every arrangement's groups of recipients for `window` updates under their arms' responses. Returns the branch maps,
    the reads of every branch (a_v and sign at each read), the window means of gain, exposure and stress, and the final
    bodies. stream and V_init (per case) override the noise and the newborns (the bridges only)."""
    kappa = D.KAPPA if kappa is None else kappa
    k = len(cases)
    br_case, br_arr, br_group, br_pos, groups = layout(arrangements)
    assert br_case.max() < k
    n = len(br_case)
    kind = np.empty(n, dtype=object)
    for g in groups:
        assert g["kind"] in FIELD_KINDS, g["kind"]
        kind[g["branches"]] = g["kind"]
    isP, isO, isR = (kind == "field"), (kind == "own"), (kind == "relative")
    if isO.any():
        kappa_o = D.KAPPA_O if kappa_o is None else kappa_o
        if kappa_o is None:
            raise RuntimeError("KAPPA_O is fixed by P65k (engineering only) before any outcome value: not yet set")
    if isR.any():
        kappa_r = D.KAPPA_R if kappa_r is None else kappa_r
        if kappa_r is None:
            raise RuntimeError("KAPPA_R is fixed by P65k (engineering only) before any outcome value: not yet set")
    kap = np.where(isP, kappa, np.where(isO, kappa_o if isO.any() else 0.0, kappa_r if isR.any() else 0.0))
    ff = np.ones(n)
    for g in groups:
        ff[g["branches"]] = field_factor(g["shape"], g["boundary"], g["lam"])
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    V0 = birth(tag, cases, *S7.BIRTH_NAMES(future), side=D.SIDE) if V_init is None else np.asarray(V_init, dtype=float)
    V = V0[br_case].copy()
    E = V.copy()
    r = np.asarray(R0, dtype=float)[br_case]
    r_before = r.copy()
    thb = np.asarray(th_case, dtype=float)[br_case]
    Tb = np.asarray(T, dtype=float)[br_case]
    st = Stream(tag, cases, *S7.NOISE_NAMES(future), side=D.SIDE) if stream is None else stream
    base = np.full(n, D.G_DIST)
    for g in groups:
        g["medium"] = S7.medium(g["shape"], g["boundary"], g["lam"])
    c = np.zeros(n)
    s_prev = np.zeros(n)
    gsum, xsum, ssum = np.zeros(n), np.zeros(n), np.zeros(n)
    dsum = {a: np.zeros(n) for a in ("P", "O", "R")} if drivers else None
    out = {"reads": [], "a_v": [], "sign": []}
    trace = {"gain": [], "emission": [], "exposure": [], "driver": []}
    buf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        rel = np.maximum(0.0, s_prev - D.GAMMA * c / ff)
        if drivers:                                  # every arm's driver as the response at t would read it
            dsum["P"] += c
            dsum["O"] += s_prev
            dsum["R"] += rel
        driver = np.where(isP, c, np.where(isO, s_prev, rel))
        gain = base * (1.0 + kap * driver)          # P: sm007.sim.respond's arithmetic, gain x (1 + kappa x exposure)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][br_case], p, gain.reshape(n, 1, 1), alpha, G)
        s = S7.stress(V, Vt, drift, d, r)
        e = S7.emission(s)
        for g in groups:
            b = g["branches"]
            c[b] = g["medium"].step(e[b])
        gsum += gain
        xsum += c
        ssum += s
        if t <= trace_until:
            trace["gain"].append(gain.copy())
            trace["emission"].append(e.copy())
            trace["exposure"].append(c.copy())
            trace["driver"].append(driver.copy())
        if t in reads:
            sg = S.sign(V, Tb)
            out["reads"].append(t)
            out["sign"].append(sg)
            out["a_v"].append(inv(sg))
        s_prev = s
    assert np.array_equal(r, r_before), "the inherited record was written"
    res = {k_: np.array(v) for k_, v in out.items()}
    res.update(br_case=br_case, br_arr=br_arr, br_group=br_group, br_pos=br_pos, gain_mean=gsum / window,
               expo_mean=xsum / window, stress_mean=ssum / window, n_groups=len(groups), kappa=float(kappa),
               kappa_o=None if kappa_o is None else float(kappa_o), kappa_r=None if kappa_r is None else float(kappa_r))
    if drivers:
        res["driver_means"] = {a_: v / window for a_, v in dsum.items()}
    if trace_until:
        res["trace"] = {k_: np.array(v) for k_, v in trace.items()}
    if keep_final:
        res["V"] = V
    return res
