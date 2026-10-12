"""Compact belief planning and an independent full-trajectory reference."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import exp, fsum, inf, isfinite, log, log1p

MODELS = ("stable", "volatile", "shared")
STATES = tuple(product(range(3), (0, 1), (0, 1)))
INDEX = {s: i for i, s in enumerate(STATES)}
KERNELS = (((0, 0, 0.5), (1, 0, 0.5)),
           tuple((b, v, 0.25) for b, v in product((0, 1), repeat=2)),
           ((0, 0, 0.5), (1, 1, 0.5)))
NULL = 2
TOL = 1e-12


def entropy(values) -> float:
    return -fsum(p*log(p) for p in values if p > 0)


def normalize(values) -> tuple[float, ...]:
    values = tuple(values)
    if any(not isfinite(p) or p < 0 for p in values) or fsum(values) <= 0:
        raise ValueError("Invalid weights or impossible evidence")
    total = fsum(values)
    return tuple(p/total for p in values)


def validate_prior(prior) -> tuple[float, float, float]:
    prior = tuple(prior)
    if len(prior) != 3 or any(not isfinite(p) or p < 0 for p in prior) or abs(fsum(prior)-1) > TOL:
        raise ValueError("Class prior must be a normalized nonnegative triple")
    return prior


def initial_belief(prior) -> tuple[float, ...]:
    prior = validate_prior(prior)
    return tuple(prior[m]/4 for m, r, a in STATES)


def model_marginal(q) -> tuple[float, float, float]:
    return tuple(fsum(q[i] for i, (m, r, a) in enumerate(STATES) if m == target) for target in range(3))


def transition(q) -> tuple[float, ...]:
    result = [0.0]*12
    for (m, r, a), p in zip(STATES, q):
        for b, v, probability in KERNELS[m]:
            result[INDEX[m, r ^ b, a ^ v]] += p*probability
    return tuple(result)


@dataclass(frozen=True)
class Policy:
    probe: bool
    r0: int
    r1: int

    def __post_init__(self):
        if self.r0 not in (0, 1) or self.r1 not in (0, 1):
            raise ValueError("Mapping reports must be binary")
        if not self.probe and self.r0 != self.r1:
            raise ValueError("Skipping requires a constant mapping report")

    def guess(self, z: int) -> int:
        return self.r1 if z == 1 else self.r0


POLICIES = (Policy(False, 0, 0), Policy(False, 1, 1)) + tuple(
    Policy(True, a, b) for a, b in product((0, 1), repeat=2)
)


def round_branches(q, policy: Policy) -> dict:
    weights = {}
    for i, (m, r, a) in enumerate(STATES):
        if q[i] == 0:
            continue
        z = r ^ a if policy.probe else NULL
        obs = z, int(policy.guess(z) == r)
        weights.setdefault(obs, [0.0]*12)[i] = q[i]
    return {obs: (fsum(v), normalize(v)) for obs, v in weights.items()}


def update(q, policy: Policy, obs: tuple[int, int]):
    branches = round_branches(q, policy)
    if obs not in branches:
        raise ValueError("Observation has zero evidence under the supplied model")
    return branches[obs][1]


def information(q, branches, target: str) -> float:
    if target == "all":
        return entropy(p for p, post in branches.values())
    if target == "model":
        return entropy(model_marginal(q))-fsum(p*entropy(model_marginal(post)) for p, post in branches.values())
    if target == "task":
        marginal = [fsum(q[i] for i, s in enumerate(STATES) if s[1] == r) for r in (0, 1)]
        # Each report's feedback identifies r, and y XOR r identifies the current x.
        return entropy(marginal)
    if target == "none":
        return 0.0
    raise ValueError("Unknown information target")


@dataclass
class Node:
    policy: Policy
    children: dict[tuple[int, int], Node]


@dataclass
class Solution:
    node: Node
    utility: float
    information: float
    value: float


def solve(prior, horizon: int, beta: float, cost: float, target: str,
          schedule: tuple[bool, ...] | None = None, belief=None) -> Solution:
    validate_prior(prior)
    if horizon not in (1, 2, 3) or not isfinite(beta) or beta <= 0 or not isfinite(cost) or cost < 0:
        raise ValueError("Use horizon 1..3, positive finite beta, and nonnegative finite cost")
    if target not in ("all", "model", "task", "none"):
        raise ValueError("Unknown target")
    if schedule is not None and len(schedule) != horizon:
        raise ValueError("Schedule length must match horizon")

    @lru_cache(None)
    def backward(q, remaining):
        best = None
        for policy in POLICIES:
            if schedule is not None and policy.probe != schedule[horizon-remaining]:
                continue
            branches = round_branches(q, policy)
            utility = fsum(p*obs[1] for obs, (p, post) in branches.items())-cost*policy.probe
            gain = information(q, branches, target)
            children = {}
            if remaining > 1:
                if target == "all":
                    gain += log(2)  # The next passive world reading, once only.
                for obs, (p, post) in branches.items():
                    child = backward(transition(post), remaining-1)
                    utility += p*child.utility
                    gain += p*child.information
                    children[obs] = child.node
            value = beta*utility+gain
            if best is None or value > best.value+TOL:
                best = Solution(Node(policy, children), utility, gain, value)
        return best

    q = initial_belief(prior) if belief is None else normalize(belief)
    if len(q) != 12:
        raise ValueError("Belief must contain twelve states")
    return backward(q, horizon)


def trajectories(prior, horizon: int, y1: int = 0) -> dict:
    """Independent physical path distribution conditional on the first reading."""
    prior = validate_prior(prior)
    if horizon not in (1, 2, 3) or y1 not in (0, 1):
        raise ValueError("Invalid horizon or initial reading")
    paths = {(m, (y1 ^ r,), (r,), (a,)): prior[m]/4
             for m, r, a in STATES if prior[m] > 0}
    for t in range(1, horizon):
        expanded = {}
        for (m, xs, rs, aas), p in paths.items():
            for b, v, likelihood in KERNELS[m]:
                for x in (0, 1):
                    key = m, xs+(x,), rs+(rs[-1] ^ b,), aas+(aas[-1] ^ v,)
                    expanded[key] = expanded.get(key, 0.0)+p*likelihood/2
        paths = expanded
    return paths


def path_observation(state, policy: Policy, stage: int) -> tuple[int, int]:
    m, xs, rs, aas = state
    z = rs[stage] ^ aas[stage] if policy.probe else NULL
    return z, int(policy.guess(z) == rs[stage])


def observable_trajectory(state, node: Node) -> tuple:
    m, xs, rs, aas = state
    observations = []
    for t in range(len(xs)):
        if t:
            observations.append(xs[t] ^ rs[t])
        z, g = path_observation(state, node.policy, t)
        observations.extend((z, g, int(node.policy.probe)))
        if t < len(xs)-1:
            if (z, g) not in node.children:
                raise ValueError("Policy has no branch for a physically possible history")
            node = node.children[z, g]
    return tuple(observations)


def _softplus(x):
    return max(x, 0)+log1p(exp(-abs(x)))


def preference_constant(horizon: int, beta: float, cost: float) -> float:
    return horizon*(log(3)+_softplus(beta)+_softplus(-beta*cost))+(horizon-1)*log(2)


def mutual_information(joint: dict, target: str) -> float:
    if target not in ("all", "model", "task"):
        raise ValueError("Unknown information target")
    pairs, marg, obs_marg = {}, {}, {}
    for (state, obs), p in joint.items():
        key = state if target == "all" else state[0] if target == "model" else state[1]
        pairs[key, obs] = pairs.get((key, obs), 0.0)+p
        marg[key] = marg.get(key, 0.0)+p
        obs_marg[obs] = obs_marg.get(obs, 0.0)+p
    return fsum(p*(log(p)-log(marg[key])-log(obs_marg[obs])) for (key, obs), p in pairs.items())


def evaluate(prior, horizon: int, node: Node, beta: float, cost: float, y1: int = 0) -> dict:
    paths = trajectories(prior, horizon, y1)
    joint = {(s, observable_trajectory(s, node)): p for s, p in paths.items()}
    obs_marg = {}
    for (state, obs), p in joint.items():
        obs_marg[obs] = obs_marg.get(obs, 0.0)+p
    accuracy = [fsum(p*o[4*t+1] for (s, o), p in joint.items()) for t in range(horizon)]
    probes = [fsum(p*o[4*t+2] for (s, o), p in joint.items()) for t in range(horizon)]
    utility = fsum(accuracy)-cost*fsum(probes)
    constant = preference_constant(horizon, beta, cost)
    cross = constant-beta*utility
    infos = {t: mutual_information(joint, t) for t in ("all", "model", "task")}
    direct = fsum(p*(log(paths[s])-log(p/obs_marg[o])
                    +constant-beta*fsum(o[4*t+1]-cost*o[4*t+2] for t in range(horizon)))
                  for (s, o), p in joint.items())
    risk = fsum(p*(log(p)+constant-beta*fsum(o[4*t+1]-cost*o[4*t+2] for t in range(horizon)))
                for o, p in obs_marg.items())
    final_class_entropy = entropy(prior)-infos["model"]
    return {"utility": utility, "accuracy_by_round": accuracy, "probes_by_round": probes,
            "expected_probes": fsum(probes), "root_probe": node.policy.probe,
            "information": infos, "preference_cross_entropy": cross,
            "efe": {t: cross-i for t, i in infos.items()}, "efe_direct_all": direct,
            "risk_plus_ambiguity_all": risk, "final_class_entropy": final_class_entropy,
            "trajectory_mass": fsum(paths.values()), "physical_paths": len(paths),
            "observation_histories": len(obs_marg)}


def trajectory_bayesian_reference(prior, horizon: int, cost: float, y1: int = 0) -> float:
    """Task-only recursion on complete paths, independent of the compact filter."""
    paths = trajectories(prior, horizon, y1)

    @lru_cache(None)
    def recurse(items: tuple, stage: int):
        q = dict(items)
        best = -inf
        for policy in POLICIES:
            grouped = {}
            utility = -cost*policy.probe
            for state, p in q.items():
                obs = path_observation(state, policy, stage)
                utility += p*obs[1]
                grouped.setdefault(obs, {})[state] = p
            if stage+1 < horizon:
                for group in grouped.values():
                    probability = fsum(group.values())
                    posterior = tuple((s, p/probability) for s, p in group.items())
                    # Future y is independent and can only relabel the world response;
                    # policies guess the mapping and decode d=y XOR r_hat.
                    utility += probability*recurse(posterior, stage+1)
            best = max(best, utility)
        return best
    return recurse(tuple(paths.items()), 0)


def best_fixed_schedule(prior, horizon: int, cost: float) -> tuple:
    best = None
    rows = []
    for schedule in product((False, True), repeat=horizon):
        solution = solve(prior, horizon, 1.0, cost, "none", schedule=schedule)
        label = "".join(str(int(k)) for k in schedule)
        rows.append({"schedule": label, "utility": solution.utility})
        if best is None or solution.utility > best[1].utility+TOL:
            best = label, solution
    return best[0], best[1], rows


def posterior_from_transition(prior, b: int, v: int) -> tuple[float, ...]:
    prior = validate_prior(prior)
    if b not in (0, 1) or v not in (0, 1):
        raise ValueError("Observed changes must be binary")
    return normalize(prior[m]*fsum(p for bb, vv, p in KERNELS[m] if (bb, vv) == (b, v))
                     for m in range(3))


def vfe(q, joint) -> float:
    q, joint = tuple(q), tuple(joint)
    if len(q) != len(joint) or abs(fsum(q)-1) > TOL or any(p < 0 or not isfinite(p) for p in q):
        raise ValueError("q must be normalized and match the joint support")
    if any(p < 0 or not isfinite(p) for p in joint):
        raise ValueError("Joint evidence weights must be finite and nonnegative")
    if any(qi > 0 and pi <= 0 for qi, pi in zip(q, joint)):
        return inf
    return fsum(qi*(log(qi)-log(pi)) for qi, pi in zip(q, joint) if qi > 0)


def node_summary(node: Node, q, remaining: int) -> dict:
    result = {"class_posterior": model_marginal(q), "probe": node.policy.probe,
              "mapping_reports_z0_z1": (node.policy.r0, node.policy.r1), "branches": []}
    for obs, (p, post) in round_branches(q, node.policy).items():
        branch = {"z": obs[0], "success_feedback": obs[1], "probability": p,
                  "class_posterior_after_feedback": model_marginal(post)}
        if remaining > 1:
            branch["next"] = node_summary(node.children[obs], transition(post), remaining-1)
        result["branches"].append(branch)
    return result
