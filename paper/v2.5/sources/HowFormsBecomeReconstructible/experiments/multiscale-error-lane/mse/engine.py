"""One update of the reference sheet with separable sensing, decision and action.

Order (PROTOCOL section 2): (1) native sheet -> V-tilde; (2) moving average from V-tilde;
(3) body channel reads R - V-tilde and acts on V, then native mean removal and clipping;
(4) reference channel reads R - V and acts on R, without mean removal; (5) passive capture
Q += rho (source - Q), Q starting at zero and never feeding V or R.

A Channel is sensor -> decision -> actuator. With a linear decision and aligned grids the
pair reduces to one projection (ops.canonical), so sensing and actuation are separately
identifiable only through displaced grids, a nonlinear decision, or noise between them.
The controller sees R, V-tilde (or V) and nothing else: no target, label, mask or score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .native import NATIVE, Params, moving_average, sheet
from .ops import MESSAGES, PATCH, Op, canonical

DECISIONS = ("linear", "zero", "reverse", "permute", "sign")


def _permute(s: np.ndarray, level: str, permutation: np.ndarray) -> np.ndarray:
    """Move whole messages at the sensor's resolution, preserving their values."""
    size = PATCH[level]
    n = 16 // size
    coarse = s.reshape(*s.shape[:-2], n, size, n, size)[..., :, 0, :, 0]
    flat = coarse.reshape(*coarse.shape[:-2], n * n)[..., permutation]
    return np.repeat(np.repeat(flat.reshape(coarse.shape), size, -2), size, -1)


@dataclass(frozen=True)
class Channel:
    sensor: Op = Op("site")
    actuator: Op = Op("site")
    decision: str = "linear"
    threshold: float = 0.0          # 'sign': act where |sensed| > threshold, else 0
    permutation: tuple | None = None

    def __post_init__(self):
        if self.decision not in DECISIONS:
            raise ValueError(f"Unknown decision: {self.decision}")
        if (self.decision == "permute") != (self.permutation is not None):
            raise ValueError("A permutation is given exactly for the permute decision")

    @property
    def messages(self) -> int:
        return MESSAGES[self.sensor.level]

    def __call__(self, d: np.ndarray) -> np.ndarray:
        if self.decision in ("linear", "zero", "reverse"):
            op = canonical(self.sensor, self.actuator)
            s = op(d) if op is not None else self.actuator(self.sensor(d))
            if self.decision == "zero":
                return np.zeros_like(s)
            return -s if self.decision == "reverse" else s
        s = self.sensor(d)
        if self.decision == "permute":
            s = _permute(s, self.sensor.level, np.asarray(self.permutation))
        else:
            s = np.where(np.abs(s) > self.threshold, np.sign(s), 0.0)
        return self.actuator(s)


@dataclass(frozen=True)
class Route:
    """body=None: comparison into V off. reference=None: working R held.
    capture: 'body' (passive Q from V), 'snapshot' (Q from a held body snapshot) or None."""
    body: Channel | None = field(default_factory=Channel)
    reference: Channel | None = field(default_factory=Channel)
    capture: str | None = "body"


ROUTES = {
    "inactive": Route(body=None, reference=None),
    "body": Route(reference=None),
    "reference": Route(body=None),
    "reciprocal": Route(),
}


@dataclass
class State:
    V: np.ndarray
    ema: np.ndarray
    R: np.ndarray
    Q: np.ndarray
    snapshot: np.ndarray | None = None

    def copy(self) -> "State":
        return State(self.V.copy(), self.ema.copy(), self.R.copy(), self.Q.copy(),
                     None if self.snapshot is None else self.snapshot.copy())


@dataclass
class Ledger:
    """Intervention dose and communication, summed per case over updates."""
    body_l1: np.ndarray
    body_l2: np.ndarray
    body_sites: np.ndarray
    ref_l1: np.ndarray
    ref_l2: np.ndarray
    messages: int = 0
    updates: int = 0

    @classmethod
    def zeros(cls, batch: int) -> "Ledger":
        z = lambda: np.zeros(batch)
        return cls(z(), z(), z(), z(), z())

    def as_dict(self) -> dict:
        return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in vars(self).items()}


def step(s: State, theta, z, route: Route, p: Params = NATIVE,
         ledger: Ledger | None = None, sense_log: list | None = None, policy=None) -> State:
    """policy(V-tilde, ema, R) -> (body gain, reference rate), scalars or (B, 1, 1) arrays.

    A policy sees only the controller's permitted signals, never Q, targets or labels.
    Without one the native constants apply and the identity route stays bit-exact.
    """
    Vt = sheet(s.V, theta, z, p)
    ema = moving_average(s.ema, Vt, p)
    gain, rate = (p.gain, p.rho) if policy is None else policy(Vt, ema, s.R)
    V, R, Q = Vt, s.R, s.Q
    if route.body is not None:
        sensed = route.body(R - Vt)
        drift = gain * sensed
        drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
        V = np.clip(Vt + p.dt * drift, -p.bound, p.bound)
        if sense_log is not None:
            sense_log.append(sensed)
    if route.reference is not None:
        R = R - rate * route.reference(R - V)
    if route.capture == "body":
        Q = Q + p.rho * (V - Q)
    elif route.capture == "snapshot":
        Q = Q + p.rho * (s.snapshot - Q)
    if ledger is not None:
        db, dr = V - Vt, R - s.R
        ledger.body_l1 += np.abs(db).sum(axis=(-2, -1))
        ledger.body_l2 += (db ** 2).sum(axis=(-2, -1))
        ledger.body_sites += (db != 0).sum(axis=(-2, -1))
        ledger.ref_l1 += np.abs(dr).sum(axis=(-2, -1))
        ledger.ref_l2 += (dr ** 2).sum(axis=(-2, -1))
        ledger.messages += sum(c.messages for c in (route.body, route.reference) if c is not None)
        ledger.updates += 1
    return State(V, ema, R, Q, s.snapshot)


def run(s: State, theta, noise, route: Route, updates: int, p: Params = NATIVE,
        ledger: Ledger | None = None, imposed: np.ndarray | None = None,
        every: int = 0, record=None, policy=None) -> State:
    """Advance `updates` steps. noise(t) returns standard normals shaped like V.

    imposed: body overwritten with this field before each step (L15 full-field hold).
    record(t, state) is called at t = 0 and every `every` updates when every > 0.
    """
    if record is not None:
        record(0, s)
    for t in range(1, updates + 1):
        if imposed is not None:
            s = State(np.broadcast_to(imposed, s.V.shape).copy(), s.ema, s.R, s.Q, s.snapshot)
        s = step(s, theta, noise(t), route, p, ledger, policy=policy)
        if record is not None and every and t % every == 0:
            record(t, s)
    return s
