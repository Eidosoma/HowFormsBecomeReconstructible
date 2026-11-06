"""SM008's recipients: SM007's update over a mixed layout (PLAN_SM008.md).

The update is sm007.sim.run's, line for line, with sm007.sim's own stress, emission, response, preprint stress and media
and SM007's birth and noise names (sm007 is frozen and is imported, never edited). Only the layout differs: a task's 16
cases are the healthy unit's 8 (indices 0-7) and the struggling unit's 8 (8-15); in a 2 x 4 composition group g's
position p holds case (g + p) mod 8 of the struggling unit if p is a struggling position, of the healthy unit otherwise;
iso8 puts each unit's 8 cases on SM007's isolated cells. With kappa 0 the update is dl001.sim.run's bit for bit, and where
the layouts coincide (the pure compositions' group 0, iso8) it is sm007.sim.run's bit for bit (P64s; Q3).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from mse.native import NATIVE
from msegrid.core import Stream, birth
from sm007 import design as D7
from sm007 import sim as S7

from . import design as D

FIELD_KINDS = ("field", "paper")
inv = S7.inv


def members(comp, g):
    """Group g's case index at each position p = 0..7: (g + p) mod 8, plus 8 where p is a struggling position."""
    P = set(D.COMPOSITIONS[comp])
    return [(g + p) % D.NCASE + (D.NCASE if p in P else 0) for p in range(8)]


def layout(arrangements):
    """The task's branches: br_case (0-15), br_arr, br_group, br_pos, and the groups. A group is {"arr", "label", "kind",
    "comp", "shape", "boundary", "lam", "branches", "cases"}."""
    br_case, br_arr, br_group, br_pos, groups = [], [], [], [], []
    for ai, (label, comp, boundary, kind, lam) in enumerate(arrangements):
        if comp == "iso8":
            gs, shape = [(0, list(range(D.NCASE))), (1, list(range(D.NCASE, 2 * D.NCASE)))], "iso8"
        else:
            gs, shape = [(g, members(comp, g)) for g in range(D.NGROUPS)], D.GROUP
        for gi, mem in gs:
            b0 = len(br_case)
            br_case += mem
            br_arr += [ai] * len(mem)
            br_group += [gi] * len(mem)
            br_pos += list(range(len(mem)))
            groups.append({"arr": ai, "label": label, "kind": kind, "comp": comp, "shape": shape, "boundary": boundary,
                           "lam": lam, "branches": np.arange(b0, b0 + len(mem)), "cases": np.array(mem)})
    return np.array(br_case), np.array(br_arr), np.array(br_group), np.array(br_pos), groups


def run(body, arrangements, cases, R0, th_case, T, tag, kappa=None, future=0, window=D.WINDOW, reads=D.READS,
        keep_final=True, stream=None, V_init=None, trace_until=0, kappa_paper=None):
    """Every arrangement's groups of recipients for `window` updates: sm007.sim.run's update over SM008's layout. Returns
    the branch maps, the reads of every branch (a_v and sign at each read), the window means of gain, exposure and stress,
    and the final bodies. stream and V_init (per case) override the noise and the newborns (the bridges only)."""
    kappa = D.KAPPA if kappa is None else kappa
    k = len(cases)
    br_case, br_arr, br_group, br_pos, groups = layout(arrangements)
    assert br_case.max() < k
    n = len(br_case)
    paper = np.zeros(n, bool)
    for g in groups:
        paper[g["branches"]] = g["kind"] == "paper"
    S_paper = None
    if paper.any():
        kappa_paper = D.KAPPA_PAPER if kappa_paper is None else kappa_paper
        S_paper = S7.paper_trajectory(tag, cases, future, window)
    kap = np.where(paper, kappa_paper if paper.any() else kappa, kappa)
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
    field = np.zeros(n, bool)
    for g in groups:
        g["medium"] = S7.medium(g["shape"], g["boundary"], g["lam"]) if g["kind"] in FIELD_KINDS else None
        field[g["branches"]] = g["kind"] in FIELD_KINDS
    mediums = [g for g in groups if g["medium"] is not None]
    c = np.zeros(n)
    gsum, xsum, ssum = np.zeros(n), np.zeros(n), np.zeros(n)
    out = {"reads": [], "a_v": [], "sign": []}
    trace = {"gain": [], "emission": [], "exposure": []}
    buf = None
    for t in range(1, window + 1):
        i = (t - 1) % D.CHUNK
        if i == 0:
            buf = st.take(D.CHUNK)
        gain = np.where(field, S7.respond(c, kap, base), base)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][br_case], p, gain.reshape(n, 1, 1), alpha, G)
        s = S7.stress(V, Vt, drift, d, r)
        if S_paper is not None:
            s = np.where(paper, S_paper[t - 1][br_case], s)
        e = S7.emission(s)
        for g in mediums:
            b = g["branches"]
            c[b] = g["medium"].step(e[b])
        gsum += gain
        xsum += c
        ssum += s
        if t <= trace_until:
            trace["gain"].append(gain.copy())
            trace["emission"].append(e.copy())
            trace["exposure"].append(c.copy())
        if t in reads:
            sg = S.sign(V, Tb)
            out["reads"].append(t)
            out["sign"].append(sg)
            out["a_v"].append(inv(sg))
    assert np.array_equal(r, r_before), "the inherited record was written"
    res = {k_: np.array(v) for k_, v in out.items()}
    res.update(br_case=br_case, br_arr=br_arr, br_group=br_group, br_pos=br_pos, gain_mean=gsum / window,
               expo_mean=xsum / window, stress_mean=ssum / window, n_groups=len(groups), kappa=float(kappa),
               kappa_paper=None if S_paper is None else float(kappa_paper))
    if trace_until:
        res["trace"] = {k_: np.array(v) for k_, v in trace.items()}
    if keep_final:
        res["V"] = V
    return res


def sm007_twin(label):
    """Where SM008's layout coincides with SM007's: (SM007's arrangement, which unit's cases, SM008's group) or None."""
    comp, boundary, *rest = label.split("/")
    if rest or boundary not in ("absorbing", "sealed"):
        return None
    if comp == "k0":
        return (f"{D.GROUP}/{boundary}", "healthy", 0)
    if comp == "k8":
        return (f"{D.GROUP}/{boundary}", "struggling", 0)
    if comp == "iso8" and boundary == "absorbing":
        return ("iso8/absorbing", "both", None)
    return None


assert D7.SHAPES[D.GROUP] == D.POSITIONS
