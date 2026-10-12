"""Exact contingent planning with persistent and changing observation mappings."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import exp, fsum, inf, isfinite, log, log1p
from typing import Callable

STATES = tuple(product((0, 1), repeat=6))  # x1,r1,a1,sensor_flip,route_flip,x2
NULL = 2
TOL = 1e-12
Belief = dict[tuple[int, ...], float]


def entropy(probabilities) -> float:
    return -fsum(p*log(p) for p in probabilities if p > 0.0)


def normalize(weights: Belief) -> Belief:
    if any(not isfinite(p) or p < 0.0 for p in weights.values()):
        raise ValueError("Invalid probability weights")
    total = fsum(weights.values())
    if total <= 0.0:
        raise ValueError("Impossible evidence")
    return {s: p/total for s, p in weights.items() if p > 0.0}


@dataclass(frozen=True)
class Model:
    delta: float
    nu: float
    shared_flip: bool = False

    def __post_init__(self):
        if any(not isfinite(v) or not 0.0 <= v <= 0.5 for v in (self.delta, self.nu)):
            raise ValueError("Flip probabilities must lie in [0, 0.5]")
        if self.shared_flip and self.delta != self.nu:
            raise ValueError("Shared flips require matching marginal flip rates")

    def prior(self) -> Belief:
        if self.shared_flip:
            return {s: 0.0625 * (self.delta if s[3] else 1-self.delta)
                    * int(s[3] == s[4]) for s in STATES}
        return {s: 0.0625 * (self.delta if s[3] else 1-self.delta)
                * (self.nu if s[4] else 1-self.nu) for s in STATES}

    def posterior(self, y1: int) -> Belief:
        if y1 not in (0, 1):
            raise ValueError("Initial observation must be binary")
        return normalize({s: p for s, p in self.prior().items() if s[0] ^ s[1] == y1})


@dataclass(frozen=True)
class Policy:
    probe: bool
    d0: int
    d1: int

    def __post_init__(self):
        if self.d0 not in (0, 1) or self.d1 not in (0, 1):
            raise ValueError("Responses must be binary")
        if not self.probe and self.d0 != self.d1:
            raise ValueError("Skipping requires a constant response")

    def response(self, z: int) -> int:
        return self.d1 if z == 1 else self.d0


POLICIES = (Policy(False, 0, 0), Policy(False, 1, 1)) + tuple(
    Policy(True, d0, d1) for d0, d1 in product((0, 1), repeat=2)
)


def round_bits(s: tuple[int, ...], stage: int) -> tuple[int, int, int]:
    if stage == 1:
        return s[0], s[1], s[2]
    if stage == 2:
        return s[5], s[1] ^ s[3], s[2] ^ s[4]
    raise ValueError("Use round 1 or 2")


def second_reading(s: tuple[int, ...]) -> int:
    x, r, a = round_bits(s, 2)
    return x ^ r


def outcome(s: tuple[int, ...], policy: Policy, stage: int) -> tuple[int, int, int]:
    x, r, a = round_bits(s, stage)
    z = r ^ a if policy.probe else NULL
    return z, int(policy.response(z) == x), int(policy.probe)


def partition(q: Belief, observation: Callable) -> dict:
    groups = {}
    for s, p in q.items():
        obs = observation(s)
        groups.setdefault(obs, {})[s] = p
    return {obs: (fsum(masses.values()), normalize(masses)) for obs, masses in groups.items()}


def target_entropy(q: Belief, target: str) -> float:
    if target == "none":
        return 0.0
    if target == "all":
        return entropy(q.values())
    if target != "task":
        raise ValueError("Unknown epistemic target")
    masses = {}
    for s, p in q.items():
        key = (s[0], s[5])
        masses[key] = masses.get(key, 0.0)+p
    return entropy(masses.values())


def information(q: Belief, branches: dict, target: str) -> float:
    return target_entropy(q, target)-fsum(p*target_entropy(post, target)
                                        for p, post in branches.values())


@dataclass
class Plan:
    first: Policy
    second: dict[tuple[int, int, int], Policy]  # z1,g1,y2; own first action is known


@dataclass
class Solution:
    plan: Plan
    utility: float
    information: float
    value: float  # beta*utility + information; EFE omits a common constant


def _validate_scales(beta: float, cost: float) -> None:
    if not isfinite(beta) or beta <= 0 or not isfinite(cost) or cost < 0:
        raise ValueError("Use finite positive beta and nonnegative cost")


def solve(model: Model, y1: int, beta: float, cost: float, target: str) -> Solution:
    """Search all first policies and all conditional second-round policies."""
    _validate_scales(beta, cost)
    if target not in ("all", "task", "none"):
        raise ValueError("Unknown target")

    @lru_cache(None)
    def last(q_items: tuple) -> tuple:
        q = dict(q_items)
        best, best_value = None, -inf
        for policy in POLICIES:
            branches = partition(q, lambda s: outcome(s, policy, 2))
            utility = fsum(p*(obs[1]-cost*obs[2]) for obs, (p, post) in branches.items())
            gain = information(q, branches, target)
            value = beta*utility+gain
            if value > best_value+TOL:
                best, best_value = (policy, utility, gain), value
        return best

    q = model.posterior(y1)
    best, best_value = None, -inf
    for first in POLICIES:
        branches = partition(q, lambda s: outcome(s, first, 1))
        utility = fsum(p*(obs[1]-cost*obs[2]) for obs, (p, post) in branches.items())
        gain = information(q, branches, target)
        second = {}
        for obs1, (p1, q1) in branches.items():
            readings = partition(q1, second_reading)
            gain += p1*information(q1, readings, target)
            for y2, (p2, q2) in readings.items():
                policy, u2, i2 = last(tuple(q2.items()))
                second[(obs1[0], obs1[1], y2)] = policy
                utility += p1*p2*u2
                gain += p1*p2*i2
        value = beta*utility+gain
        if value > best_value+TOL:
            best, best_value = Solution(Plan(first, second), utility, gain, value), value
    return best


def map_report(q: Belief, stage: int, probe: bool) -> Policy:
    """Independent binary decision rule; no EFE scores or terminal feedback."""
    responses = []
    for z in ((0, 1) if probe else (NULL,)):
        masses = [0.0, 0.0]
        for s, p in q.items():
            x, r, a = round_bits(s, stage)
            observed = r ^ a if probe else NULL
            if observed == z:
                masses[x] += p
        responses.append(int(masses[1] > masses[0]+TOL))
    return Policy(probe, responses[0], responses[-1])


def schedule_plan(model: Model, y1: int, first_probe: bool, second_probe: bool) -> Plan:
    q = model.posterior(y1)
    first = map_report(q, 1, first_probe)
    second = {}
    for obs1, (p1, q1) in partition(q, lambda s: outcome(s, first, 1)).items():
        for y2, (p2, q2) in partition(q1, second_reading).items():
            second[(obs1[0], obs1[1], y2)] = map_report(q2, 2, second_probe)
    return Plan(first, second)


def bayesian_reference(model: Model, y1: int, cost: float) -> Plan:
    """Task-only backward values: first probe enables a second gain D-c."""
    _validate_scales(1.0, cost)
    future_gain = max(model.delta-model.nu, 0.0)
    first_probe = max(future_gain-cost, 0.0)-cost > TOL
    second_probe = first_probe and future_gain-cost > TOL
    return schedule_plan(model, y1, first_probe, second_probe)


def forgetting_plan(model: Model, y1: int) -> Plan:
    plan = schedule_plan(model, y1, False, False)
    plan.second = {key: Policy(False, key[2], key[2]) for key in plan.second}
    return plan


def trajectory_joint(model: Model, y1: int, plan: Plan) -> dict:
    joint = {}
    for s, probability in model.posterior(y1).items():
        o1 = outcome(s, plan.first, 1)
        y2 = second_reading(s)
        key = (o1[0], o1[1], y2)
        if key not in plan.second:
            raise ValueError("Policy lacks a reachable observable history")
        o2 = outcome(s, plan.second[key], 2)
        joint[(s, (*o1, y2, *o2))] = probability
    return joint


def _softplus(value: float) -> float:
    return max(value, 0.0)+log1p(exp(-abs(value)))


def log_preference(obs: tuple, beta: float, cost: float) -> float:
    _validate_scales(beta, cost)
    z1, g1, k1, y2, z2, g2, k2 = obs
    if (z1 not in (NULL, 0, 1) or z2 not in (NULL, 0, 1)
            or any(b not in (0, 1) for b in (g1, k1, y2, g2, k2))):
        raise ValueError("Invalid outcome")
    constant = 2*(log(3)+_softplus(beta)+_softplus(-beta*cost))+log(2)
    return beta*(g1+g2-cost*(k1+k2))-constant


def evaluate(model: Model, y1: int, plan: Plan, beta: float, cost: float) -> dict:
    """Score a fixed policy under the specified physical model, without replanning."""
    _validate_scales(beta, cost)
    joint = trajectory_joint(model, y1, plan)
    q = model.posterior(y1)
    obs_masses, world_joint, world_marginal = {}, {}, {}
    for (s, obs), p in joint.items():
        obs_masses[obs] = obs_masses.get(obs, 0.0)+p
        world = (s[0], s[5])
        world_joint[(world, obs)] = world_joint.get((world, obs), 0.0)+p
        world_marginal[world] = world_marginal.get(world, 0.0)+p
    # The observation sequence is deterministic conditional on the full trajectory.
    all_info = entropy(obs_masses.values())
    task_info = fsum(p*(log(p)-log(world_marginal[w])-log(obs_masses[o]))
                     for (w, o), p in world_joint.items())
    a1 = fsum(p*o[1] for (s, o), p in joint.items())
    a2 = fsum(p*o[5] for (s, o), p in joint.items())
    n_probes = fsum(p*(o[2]+o[6]) for (s, o), p in joint.items())
    utility = a1+a2-cost*n_probes
    cross = -fsum(p*log_preference(o, beta, cost) for (s, o), p in joint.items())
    direct = fsum(p*(log(q[s])-log(p/obs_masses[o])-log_preference(o, beta, cost))
                  for (s, o), p in joint.items())
    risk = fsum(p*(log(p)-log_preference(o, beta, cost)) for o, p in obs_masses.items())
    second_flags = {plan.second[(o[0], o[1], o[3])].probe for s, o in joint}
    schedule = f"{int(plan.first.probe)}{int(next(iter(second_flags)))}" if len(second_flags) == 1 else f"{int(plan.first.probe)}*"
    return {"schedule": schedule, "accuracy_round1": a1, "accuracy_round2": a2,
            "expected_probes": n_probes, "utility": utility,
            "state_information": all_info, "task_information": task_info,
            "preference_cross_entropy": cross, "efe_all": cross-all_info,
            "efe_task": cross-task_info, "efe_direct": direct,
            "risk_plus_ambiguity": risk,
            "trajectory_mass": fsum(joint.values()), "observation_branches": len(obs_masses)}


def analytic_schedules(model: Model, beta: float, cost: float) -> dict:
    _validate_scales(beta, cost)
    d = max(model.delta-model.nu, 0.0)
    u0 = 1.5-model.delta
    base_info = 2*log(2)+entropy((model.delta, 1-model.delta))
    route_change = 0.0 if model.shared_flip else entropy((model.nu, 1-model.nu))
    result = {}
    for k1, k2 in product((0, 1), repeat=2):
        gain = d if k1 and k2 else 0.0
        extra_info = k1*log(2)+k2*(route_change if k1 else log(2))
        result[f"{k1}{k2}"] = {
            "utility": u0+gain-cost*(k1+k2),
            "state_information": base_info+extra_info,
            "efe_relative": beta*(cost*(k1+k2)-gain)-extra_info,
        }
    return result


def analytic_choice(model: Model, beta: float, cost: float) -> str:
    best, value = None, inf
    for schedule, item in analytic_schedules(model, beta, cost).items():
        if item["efe_relative"] < value-TOL:
            best, value = schedule, item["efe_relative"]
    return best


def vfe(q: Belief, joint: Belief) -> float:
    if abs(fsum(q.values())-1.0) > TOL or any(p < 0 or not isfinite(p) for p in q.values()):
        raise ValueError("q must be normalized")
    if any(joint.get(s, 0.0) <= 0 for s, p in q.items() if p > 0):
        return inf
    return fsum(p*(log(p)-log(joint[s])) for s, p in q.items() if p > 0)
