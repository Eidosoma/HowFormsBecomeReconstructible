"""The batched window loop with per-branch events, the fresh reader, and the endpoint functions.

A branch is one (condition, case) or (environment, case). Events are applied before the update
they are scheduled at: damage adds an addressed band field to V and/or R (clipped to +-2, as
mse.assay.injure); an imposition overwrites V with the foreign template before every update of
its span (the L15 full-field hold). A clamp (privileged protected backup) restores R's content at
one resolution before every update: R <- R + (P(R_backup) - P(R)), and R <- R_backup at site
resolution. Everything else is mse.engine.step,
unchanged: the controller sees V-tilde, ema and R only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from mse import score
from mse.assay import REFERENCE_BOUND, Noise, acquire, birth, enrol
from mse.engine import ROUTES, Channel, Ledger, Route, State, run, step
from mse.native import NATIVE, address
from mse.ops import Op, bands, block_projection

from . import design as D

READ_ROUTE = Route(reference=None, capture=None)
OFF_ROUTE = Route(body=None, reference=None, capture=None)
CLAMP_SIZE = {"site": 1, "region": 4, "sheet": 8}


def params(name):
    family, sigma, g = D.parse(name)
    return family, replace(NATIVE, sigma=sigma, coupling=g)


def channel(spec):
    if spec is None:
        return None
    sl, so, al, ao, decision = spec
    return Channel(Op(sl, tuple(so)), Op(al, tuple(ao)), decision, 0.0, None)


def route(arm):
    return Route(body=channel(arm.body), reference=channel(arm.reference), capture="body")


def targets(family, cases):
    T = D.TEMPLATES[family]
    return T[[c.message for c in cases]], T[[D.FOREIGN[c.message] for c in cases]]


def prepare(name, blocks, purpose):
    """Acquired, released, pre-damage state with Q = 0 (ME001's acquisition and release), its
    theta, params, own and foreign targets. Teaching imposes the family template."""
    family, p = params(name)
    cases = enrol(blocks, D.MESSAGES, D.PARENTS, purpose)
    T, Tf = targets(family, cases)
    th = _theta(cases, p)
    V = birth(D.TAG, cases, "birth")
    s = State(V, V.copy(), V.copy(), np.zeros_like(V))
    s = run(s, th, Noise(D.TAG, cases, "settle"), Route(capture=None), D.SETTLE, p)
    s = run(s, th, Noise(D.TAG, cases, "teach"), Route(capture=None), D.TEACH, p, imposed=T)
    s = run(s, th, Noise(D.TAG, cases, "release"), ROUTES["body"], D.RELEASE, p)
    return cases, State(s.V, s.ema, s.R, np.zeros_like(s.V)), th, p, T, Tf


def _theta(cases, p):
    from mse.assay import theta
    return theta(D.TAG, cases, p, per_tissue=D.PER_TISSUE_THETA)


def draws(cases, *stream, updates):
    """Standard normals shaped (updates, cases, 16, 16) from each case's addressed stream."""
    return np.stack([address(D.TAG, *c.key(), *stream).standard_normal((updates, 16, 16)) for c in cases], 1)


def onsets(cases, kind):
    if kind == "start":
        return np.ones(len(cases), int)
    return np.array([int(address(D.TAG, *c.key(), "onset").integers(*D.ONSET)) for c in cases])


def band_field(cases, target, band, rms, *stream):
    """One unit Gaussian field per case projected into one band, scaled to pre-clipping RMS.
    Without `stream` the address equals mse.assay.band_damage's (case, 'damage', target, band)."""
    out = []
    for c in cases:
        x = bands(address(D.TAG, *c.key(), *stream, "damage", target, band).standard_normal((16, 16)))[band]
        out.append(x * (rms / np.sqrt((x ** 2).mean())))
    return np.stack(out)


@dataclass
class Program:
    """Per-branch events for n branches: damage slots and at most one imposition. A slot is
    (time (n,), dV, dR, dR2), each field (n,16,16) or None; dR2 injures a second record, which
    only two-record arms carry (for a one-record arm a 'reference2' injury is its dR alone)."""
    n: int
    slots: list = field(default_factory=list)
    imp_start: np.ndarray | None = None
    imp_stop: np.ndarray | None = None
    pattern: np.ndarray | None = None

    def apply(self, t, V, R, R2=None):
        for time, dV, dR, dR2 in self.slots:
            m = time == t
            if m.any():
                m3 = m[:, None, None]
                if dV is not None:
                    V = np.where(m3, np.clip(V + dV, -NATIVE.bound, NATIVE.bound), V)
                if dR is not None:
                    R = np.where(m3, np.clip(R + dR, -REFERENCE_BOUND, REFERENCE_BOUND), R)
                if dR2 is not None and R2 is not None:
                    R2 = np.where(m3, np.clip(R2 + dR2, -REFERENCE_BOUND, REFERENCE_BOUND), R2)
        if self.imp_start is not None:
            m = (self.imp_start <= t) & (t < self.imp_stop)
            if m.any():
                V = np.where(m[:, None, None], self.pattern, V)
        return (V, R) if R2 is None else (V, R, R2)


def vote(V, R, R2):
    """Two records and the body vote: in every 4 x 4 region where the records differ, both take
    the values of the record closer to the body there (mean square over the region). Records that
    agree are never touched, so the vote is an exact no-op until a record is injured."""
    n = len(V)
    blk = lambda x: x.reshape(n, 4, 4, 4, 4)
    differ = np.abs(blk(R - R2)).max(axis=(2, 4)) > 0
    if not differ.any():
        return R, R2
    e1 = blk((R - V) ** 2).mean(axis=(2, 4))
    e2 = blk((R2 - V) ** 2).mean(axis=(2, 4))
    take2 = differ & (e2 < e1)
    take1 = differ & ~take2
    up = lambda m: np.repeat(np.repeat(m, 4, axis=-2), 4, axis=-1)
    return np.where(up(take2), R2, R), np.where(up(take1), R, R2)


def condition_program(conditions, cases, tau, Tf, L):
    """Program for every (condition, case) branch, condition-major."""
    nc, k = len(conditions), len(cases)
    n = nc * k
    times = [np.full(n, -1) for _ in range(2)]
    fields = [[np.zeros((n, 16, 16)) for _ in range(3)] for _ in range(2)]
    used = [[False, False, False] for _ in range(2)]
    imp_start, imp_stop = np.full(n, -1), np.full(n, -1)
    for ci, cond in enumerate(conditions):
        sl = slice(ci * k, (ci + 1) * k)
        slot = 0
        for ev in cond.events:
            if ev.kind == "impose":
                imp_start[sl] = tau
                imp_stop[sl] = tau + ev.duration if ev.duration else L + 1
                continue
            times[slot][sl] = tau + ev.delay
            for j, (who, hit) in enumerate((("body", ("body", "both")), ("reference", ("reference", "both", "reference2")),
                                            ("reference2", ("reference2",)))):
                if ev.target in hit:
                    fields[slot][j][sl] = band_field(cases, who, ev.band, ev.rms)
                    used[slot][j] = True
            slot += 1
    prog = Program(n)
    for s in range(2):
        if (times[s] > 0).any():
            prog.slots.append((times[s], *(fields[s][j] if used[s][j] else None for j in range(3))))
    if (imp_start > 0).any():
        prog.imp_start, prog.imp_stop, prog.pattern = imp_start, imp_stop, np.tile(Tf, (nc, 1, 1))
    return prog


def oracle_schedule(conditions, tau, k, L):
    """(L, n) bursts for the event oracle (privileged): at each reference-only injury instant, and
    20 updates after the onset of an imposition that lasts to the window's end."""
    n = len(conditions) * k
    on = np.zeros((L, n), bool)
    for ci, cond in enumerate(conditions):
        for j in range(k):
            b = ci * k + j
            starts = []
            for ev in cond.events:
                if ev.kind == "damage" and ev.target == "reference":
                    starts.append(tau[j] + ev.delay)
                if ev.kind == "impose" and ev.duration == 0:
                    starts.append(tau[j] + D.BURST_UPDATES)
            for t0 in starts:
                on[t0 - 1:t0 - 1 + D.BURST_UPDATES, b] = True
    return on


def simulate(s, theta, Z, idx, p, L, rt, controller=None, prog=None, clamp=None, sentinels=None, ledger=None,
             copy2=None, out=None):
    """Advance n branches L updates. Z[t-1][idx] are the update-t draws; clamp = (level, backup R);
    copy2: the second record of a two-record arm (voted with R and the body before each update;
    its final value goes to out['R2']). The third return value is the L1 of record writes made
    outside the step (clamp restorations or votes)."""
    early = {k: np.full_like(s.V, np.nan) for k in (sentinels or {})}
    clamp_l1 = np.zeros(len(s.V))
    V, ema, R, Q, R2 = s.V, s.ema, s.R, s.Q, copy2
    for t in range(1, L + 1):
        if prog is not None:
            if R2 is None:
                V, R = prog.apply(t, V, R)
            else:
                V, R, R2 = prog.apply(t, V, R, R2)
        if R2 is not None:
            Rv, R2 = vote(V, R, R2)
            clamp_l1 += np.abs(Rv - R).sum(axis=(-2, -1))
            R = Rv
        if clamp is not None:
            level, backup = clamp
            size = CLAMP_SIZE[level]
            # exact no-op while R's projection equals the backup (sham, body-only damage)
            R2 = backup.copy() if size == 1 else R + (backup - block_projection(R, size))
            clamp_l1 += np.abs(R2 - R).sum(axis=(-2, -1))
            R = R2
        st = step(State(V, ema, R, Q), theta, Z[t - 1][idx], rt, p, ledger, policy=controller)
        V, ema, R, Q = st.V, st.ema, st.R, st.Q
        for k, times in (sentinels or {}).items():
            m = times == t
            if m.any():
                early[k][m] = V[m]
    if out is not None:
        out["R2"] = R2
    return State(V, ema, R, Q), early, clamp_l1


def recipients(cases):
    births = np.stack([birth(D.TAG, cases, "recipient", r, "birth") for r in range(D.RECIPIENTS)], 1)
    Z = np.stack([draws(cases, "recipient", r, "read", updates=D.READ_UPDATES) for r in range(D.RECIPIENTS)], 2)
    return births, Z


def read_batch(packets, idx, th, births, Z, p, rt=READ_ROUTE):
    """Fresh recipients hold each packet as their reference for READ_UPDATES (mse.assay.read)."""
    n, k = len(packets), D.RECIPIENTS
    V = births[idx].reshape(n * k, 16, 16)
    s = State(V, V.copy(), np.repeat(packets, k, axis=0), np.zeros_like(V))
    s = run(s, np.repeat(th[idx], k, axis=0), lambda t: Z[t - 1][idx].reshape(n * k, 16, 16), rt, D.READ_UPDATES, p)
    return s.V.reshape(n, k, 16, 16)


def body_endpoints(V, T, prefix):
    m, a = (V > 0) == (T > 0), np.abs(V) > score.ELIGIBLE
    return {f"{prefix}_sign": m.mean((-2, -1)), f"{prefix}_amp": a.mean((-2, -1)), f"{prefix}_qual": (m & a).mean((-2, -1)),
            f"{prefix}_margin": (np.sign(T) * V).mean((-2, -1))}


def fresh_endpoints(F, T, prefix):
    """F (n, recipients, 16, 16) against T (n, 16, 16); averaged over recipients."""
    Tt = T[:, None]
    m, a = (F > 0) == (Tt > 0), np.abs(F) > score.ELIGIBLE
    out = {"sign": m.mean((-2, -1)), "amp": a.mean((-2, -1)), "qual": (m & a).mean((-2, -1)),
           "margin": (np.sign(Tt) * F).mean((-2, -1))}
    return {f"{prefix}_{k}": v.mean(1) for k, v in out.items()}
