"""SM007's recipients: groups of newborn bodies, each reading a fixed inherited record, coupled by a shared field.

One update, for every branch of a task at once (PLAN_SM007.md; E2E006's order, e2e006.sim.Coupling.body):
  1. each field branch's reading gain is respond(c, KAPPA, G_DIST), c its exposure sampled at the previous update (0
     before the first); "nofield" branches read at G_DIST and "undisturbed" ones at G_LANE;
  2. every body takes dl001.sim.body's update with its own gain, its fixed record R0 and its case's noise;
  3. each branch's stress (its mean |r - V-tilde|) is its emission; every group's medium steps with its sheets'
     emissions (msefield.Medium.step) and returns their exposures; a "uniform" group's sheets all take the group's mean
     exposure, a "rearranged" group's sheet i takes sheet perm[i]'s.
The inherited record is never written. With KAPPA 0 the update is dl001.sim.run's bit for bit (Q3; probes/p61s).
Amendment 2: a "paper" group emits its cases' stress from Manicka and Levin's Eq. 1 (paper_trajectory: exogenous, never
reading the body) instead of the mismatch, and responds with KAPPA_PAPER; everything else is the same update.
stress, emission and respond are E2E006's (e2e006.sim.FieldAdapter), the lead's ruling for both field studies; Q3 checks
them against E2E006's bit for bit.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from dl001 import design as DL
from dl001 import sim as S
from mse.native import NATIVE, address
from msefield.core import Medium
from msegrid.core import Stream, birth

from . import design as D

BIRTH_NAMES = lambda f: ("sm007", "fut", f, "birth")
NOISE_NAMES = lambda f: ("sm007", "fut", f, "noise")
FIELD_KINDS = ("field", "uniform", "rearranged", "paper")
inv = lambda a: np.maximum(a, 1.0 - a)


def stress(V, Vt, drift, d, r):
    """The lead's ruling (12:26:39Z): a sheet's mean |r - V-tilde| over its cells (the record's pull on its body)."""
    return np.abs(r - Vt).mean((-2, -1))


def emission(s):
    """The lead's ruling: emission = stress."""
    return s


def respond(c, kappa, gain):
    """The lead's ruling: the body's reading gain x (1 + kappa x exposure) (E2E006's, its window always open)."""
    return gain * (1.0 + kappa * c)


def paper_init(tag, cases, future):
    """S_i(0) ~ N(mu0, sd0) redrawn until at least the separatrix S* (Eq. 1's initial stress), per case and future."""
    out = []
    for c in cases:
        g = address(tag, *c.key(), "sm007", "paper-stress0", future)
        while True:
            v = D.PAPER["mu0"] + D.PAPER["sd0"] * g.standard_normal()
            if v >= D.PAPER_SSTAR:
                break
        out.append(v)
    return np.array(out)


def paper_rate(S):
    """Eq. 1's right-hand side, per second: P_max S^n / (K^n + S^n) - delta_S S."""
    P = D.PAPER
    Sn = S ** P["n"]
    return P["P_max"] * Sn / (P["K"] ** P["n"] + Sn) - P["delta_S"] * S


def paper_update(S):
    """One bio-step (one tissue update): k Euler sub-steps of dt_sub."""
    for _ in range(D.PAPER["k"]):
        S = S + D.PAPER["dt_sub"] * paper_rate(S)
    return S


def paper_trajectory(tag, cases, future, window):
    """(window, k): each case's stress after each update. Once an update leaves every case's stress bitwise unchanged,
    it is a fixed point of the update, so the rest of the window holds it exactly."""
    S = paper_init(tag, cases, future)
    out = np.empty((window, len(cases)))
    for t in range(window):
        S2 = paper_update(S)
        out[t] = S2
        if np.array_equal(S2, S):
            out[t + 1:] = S2
            break
        S = S2
    return out


def medium(shape, boundary, lam):
    return Medium(D.SHAPES[shape], D.d_field(lam), D.GAMMA, D.LEAKS[boundary], dt=1.0, m=D.SITES[lam], margin=D.MARGIN)


def groups_of(n, k):
    """ceil(k / n) groups of n cases, taken cyclically, so that every case sits in at least one group."""
    return [[(g * n + i) % k for i in range(n)] for g in range(math.ceil(k / n))]


def derangement(tag, n, label, gi):
    """A fixed permutation of n sheets with no fixed point (n > 1), addressed by the arrangement and group."""
    if n == 1:
        return np.zeros(1, np.int64)
    g = address(tag, "sm007", "rearranged", label, gi)
    while True:
        p = g.permutation(n)
        if not np.any(p == np.arange(n)):
            return p


def layout(arrangements, k, tag):
    """The task's branches: (branch -> case, branch -> arrangement, groups). A group is {"arr", "label", "kind", "shape",
    "boundary", "lam", "branches", "cases", "perm"}; a nofield or undisturbed arrangement is one group of k sheets with
    no medium."""
    br_case, br_arr, groups = [], [], []
    for ai, (label, shape, boundary, kind, lam) in enumerate(arrangements):
        members = [list(range(k))] if kind not in FIELD_KINDS else groups_of(len(D.SHAPES[shape]), k)
        for gi, mem in enumerate(members):
            b0 = len(br_case)
            br_case += mem
            br_arr += [ai] * len(mem)
            groups.append({"arr": ai, "label": label, "kind": kind, "shape": shape, "boundary": boundary, "lam": lam,
                           "branches": np.arange(b0, b0 + len(mem)), "cases": np.array(mem),
                           "perm": derangement(tag, len(mem), label, gi) if kind == "rearranged" else None})
    return np.array(br_case), np.array(br_arr), groups


def run(body, arrangements, cases, R0, th_case, T, tag, kappa=None, future=0, window=D.WINDOW, reads=D.READS,
        keep_final=True, stream=None, V_init=None, trace_until=0, kappa_paper=None):
    """Every arrangement's groups of recipients for `window` updates. Returns the branch maps, the reads of every branch
    (a_v and sign at each read), the window means of gain, exposure and stress, and the final bodies. kappa defaults to
    D.KAPPA (refused while unset); stream and V_init (per case) override the noise and the newborns (the bridge to
    dl001.sim.run only); trace_until > 0 records each update's gain, emission and exposure up to then (Q4)."""
    kappa = D.KAPPA if kappa is None else kappa
    if kappa is None:
        raise RuntimeError("KAPPA is fixed by P61k (engineering only) before any outcome value: not yet set")
    k = len(cases)
    br_case, br_arr, groups = layout(arrangements, k, tag)
    n = len(br_case)
    paper = np.zeros(n, bool)
    for g in groups:
        paper[g["branches"]] = g["kind"] == "paper"
    S_paper = None
    if paper.any():
        kappa_paper = D.KAPPA_PAPER if kappa_paper is None else kappa_paper
        if kappa_paper is None:
            raise RuntimeError("KAPPA_PAPER is fixed by P61p (engineering only) before any value of the arm: not yet set")
        S_paper = paper_trajectory(tag, cases, future, window)
    kap = np.where(paper, kappa_paper if paper.any() else kappa, kappa)
    alpha, L = DL.BODIES[body]
    G = S.ghat(D.SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=D.SIGMA)
    V0 = birth(tag, cases, *BIRTH_NAMES(future), side=D.SIDE) if V_init is None else np.asarray(V_init, dtype=float)
    V = V0[br_case].copy()
    E = V.copy()
    r = np.asarray(R0, dtype=float)[br_case]
    r_before = r.copy()
    thb = np.asarray(th_case, dtype=float)[br_case]
    Tb = np.asarray(T, dtype=float)[br_case]
    st = Stream(tag, cases, *NOISE_NAMES(future), side=D.SIDE) if stream is None else stream
    base = np.full(n, D.G_DIST)
    field = np.zeros(n, bool)
    for g in groups:
        g["medium"] = medium(g["shape"], g["boundary"], g["lam"]) if g["kind"] in FIELD_KINDS else None
        field[g["branches"]] = g["kind"] in FIELD_KINDS
        if g["kind"] == "undisturbed":
            base[g["branches"]] = D.G_LANE
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
        gain = np.where(field, respond(c, kap, base), base)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][br_case], p, gain.reshape(n, 1, 1), alpha, G)
        s = stress(V, Vt, drift, d, r)
        if S_paper is not None:
            s = np.where(paper, S_paper[t - 1][br_case], s)
        e = emission(s)
        for g in mediums:
            b = g["branches"]
            x = g["medium"].step(e[b])
            if g["kind"] == "uniform":
                x = np.full(len(x), x.mean())
            elif g["kind"] == "rearranged":
                x = x[g["perm"]]
            c[b] = x
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
    res.update(br_case=br_case, br_arr=br_arr, gain_mean=gsum / window, expo_mean=xsum / window,
               stress_mean=ssum / window, n_groups=len(groups), kappa=float(kappa),
               kappa_paper=None if S_paper is None else float(kappa_paper))
    if trace_until:
        res["trace"] = {k_: np.array(v) for k_, v in trace.items()}
    if keep_final:
        res["V"] = V
    return res


def l_eff(shape, m=8):
    """The shape's effective extent 1 / sqrt(mu_1), mu_1 the least eigenvalue of -lap on its absorbing domain (spacings);
    iso8's is one isolated cell's."""
    M = Medium(D.SHAPES[shape], D=1.0, gamma=0.0, leak=1.0, m=m)
    A, _sites = M._operator()
    w = np.linalg.eigvalsh(-A.toarray())
    return 1.0 / math.sqrt(float(w.min()))


def field_factor(shape, boundary, lam):
    """Each sheet's steady exposure under a uniform emission, in units of the boundary-free level emission / GAMMA."""
    M = medium(shape, boundary, lam)
    return M.sample(M.steady_state(np.full(M.n_sheets, D.GAMMA)))
