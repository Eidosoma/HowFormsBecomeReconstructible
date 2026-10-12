"""An eight-state generative model; no simulation, fitting or random sampling."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import exp, fsum, inf, isclose, isfinite, log, log1p
from typing import Iterable

STATES = tuple(product((0, 1), repeat=3))  # world, sensory reversal, route reversal
NULL = 2
OUTCOMES = tuple(product((NULL, 0, 1), (0, 1), (0, 1)))
TOLERANCE = 1e-12


def entropy(probabilities: Iterable[float]) -> float:
    return -fsum(p * log(p) for p in probabilities if p > 0.0)


def _validate_weights(weights: tuple[float, ...], normalized: bool = False) -> None:
    if not weights or any(not isfinite(p) or p < 0.0 for p in weights):
        raise ValueError("Weights must be finite and nonnegative")
    total = fsum(weights)
    if total <= 0.0:
        raise ValueError("Zero evidence or empty support")
    if normalized and not isclose(total, 1.0, abs_tol=TOLERANCE, rel_tol=0.0):
        raise ValueError("Distribution must sum to one")


def normalize(weights: tuple[float, ...]) -> tuple[float, ...]:
    _validate_weights(weights)
    total = fsum(weights)
    return tuple(p / total for p in weights)


def kl(q: tuple[float, ...], p: tuple[float, ...]) -> float:
    _validate_weights(q, normalized=True)
    _validate_weights(p, normalized=True)
    if len(q) != len(p):
        raise ValueError("Distributions have different sizes")
    if any(qi > 0.0 and pi == 0.0 for qi, pi in zip(q, p)):
        return inf
    return fsum(qi * (log(qi) - log(pi)) for qi, pi in zip(q, p) if qi > 0.0)


def vfe(q: tuple[float, ...], joint: tuple[float, ...]) -> float:
    """F against a fixed, possibly subnormalized joint p(s, history)."""
    _validate_weights(q, normalized=True)
    _validate_weights(joint)
    if len(q) != len(joint):
        raise ValueError("Distributions have different sizes")
    if any(qi > 0.0 and pi == 0.0 for qi, pi in zip(q, joint)):
        return inf
    return fsum(qi * (log(qi) - log(pi)) for qi, pi in zip(q, joint) if qi > 0.0)


@dataclass(frozen=True)
class Model:
    prior: tuple[float, ...]
    noise: float = 0.0
    sham: bool = False

    def __post_init__(self) -> None:
        if len(self.prior) != len(STATES):
            raise ValueError("Prior must have eight states")
        _validate_weights(self.prior, normalized=True)
        if not isfinite(self.noise) or not 0.0 <= self.noise <= 0.5:
            raise ValueError("Diagnostic noise must lie in [0, 0.5]")

    @classmethod
    def independent(cls, alpha: float = 0.5, rho: float = 0.0,
                    noise: float = 0.0, sham: bool = False) -> Model:
        if any(not isfinite(p) or not 0.0 <= p <= 1.0 for p in (alpha, rho)):
            raise ValueError("Prior probabilities must lie in [0, 1]")
        prior = tuple(0.5 * (alpha if r else 1.0-alpha)
                      * (rho if a else 1.0-rho) for x, r, a in STATES)
        return cls(prior, noise, sham)

    @classmethod
    def common_fault(cls, noise: float = 0.0) -> Model:
        return cls(tuple(0.5 if s in ((0, 0, 0), (1, 1, 1)) else 0.0
                         for s in STATES), noise)

    def initial_joint(self, y: int) -> tuple[float, ...]:
        if y not in (0, 1):
            raise ValueError("Initial reading must be binary")
        return tuple(p if x ^ r == y else 0.0
                     for p, (x, r, a) in zip(self.prior, STATES))

    def posterior(self, y: int) -> tuple[float, ...]:
        return normalize(self.initial_joint(y))

    def diagnostic(self, state: tuple[int, int, int], probe: bool,
                   z: int) -> float:
        if not probe:
            return float(z == NULL)
        if z not in (0, 1):
            return 0.0
        if self.sham:
            return 0.5
        x, r, a = state
        return 1.0-self.noise if z == r ^ a else self.noise

    def history_joint(self, y: int, z: int) -> tuple[float, ...]:
        return tuple(p * self.diagnostic(s, True, z)
                     for p, s in zip(self.initial_joint(y), STATES))


@dataclass(frozen=True)
class Policy:
    probe: bool
    d0: int
    d1: int

    def __post_init__(self) -> None:
        if self.d0 not in (0, 1) or self.d1 not in (0, 1):
            raise ValueError("Reports must be binary")
        if not self.probe and self.d0 != self.d1:
            raise ValueError("A skip policy must have a constant report")

    @property
    def name(self) -> str:
        return f"probe_{self.d0}{self.d1}" if self.probe else f"skip_{self.d0}"

    def response(self, z: int) -> int:
        return self.d1 if z == 1 else self.d0


POLICIES = (Policy(False, 0, 0), Policy(False, 1, 1)) + tuple(
    Policy(True, d0, d1) for d0, d1 in product((0, 1), repeat=2)
)


def predictive_joint(model: Model, y: int, policy: Policy) -> dict:
    joint = {}
    for state, mass in zip(STATES, model.posterior(y)):
        if mass == 0.0:
            continue
        for z in ((0, 1) if policy.probe else (NULL,)):
            probability = mass * model.diagnostic(state, policy.probe, z)
            if probability > 0.0:
                g = int(policy.response(z) == state[0])
                joint[(state, (z, g, int(policy.probe)))] = probability
    return joint


def mutual_information(joint: dict, world_only: bool = False) -> float:
    pairs, states, outcomes = {}, {}, {}
    for (state, outcome), probability in joint.items():
        target = state[0] if world_only else state
        key = (target, outcome)
        pairs[key] = pairs.get(key, 0.0) + probability
        states[target] = states.get(target, 0.0) + probability
        outcomes[outcome] = outcomes.get(outcome, 0.0) + probability
    return fsum(p * (log(p)-log(states[s])-log(outcomes[o]))
                for (s, o), p in pairs.items() if p > 0.0)


def _log1pexp(value: float) -> float:
    return max(value, 0.0) + log1p(exp(-abs(value)))


def log_preference(outcome: tuple[int, int, int], beta: float, cost: float) -> float:
    if not isfinite(beta) or beta <= 0.0 or not isfinite(cost) or cost < 0.0:
        raise ValueError("Use positive finite beta and nonnegative finite cost")
    z, g, k = outcome
    if outcome not in OUTCOMES:
        raise ValueError("Invalid outcome")
    return -log(3.0) + beta*g - _log1pexp(beta) - beta*cost*k - _log1pexp(-beta*cost)


@dataclass(frozen=True)
class Score:
    policy: str
    accuracy: float
    cost: float
    utility: float
    preference_cross_entropy: float
    state_information: float
    task_information: float
    efe_all: float
    efe_task: float
    efe_direct: float
    risk_plus_ambiguity: float


def score(model: Model, y: int, policy: Policy, beta: float, cost: float) -> Score:
    joint = predictive_joint(model, y, policy)
    q = dict(zip(STATES, model.posterior(y)))
    observations = {}
    for (state, outcome), probability in joint.items():
        observations[outcome] = observations.get(outcome, 0.0) + probability
    cross_entropy = -fsum(p * log_preference(o, beta, cost)
                          for (s, o), p in joint.items())
    information = mutual_information(joint)
    task_information = mutual_information(joint, world_only=True)
    direct = fsum(p * (log(q[s]) - log(p / observations[o])
                      - log_preference(o, beta, cost))
                  for (s, o), p in joint.items())
    risk = fsum(p * (log(p) - log_preference(o, beta, cost))
                for o, p in observations.items())
    ambiguity = entropy(joint.values()) - entropy(q.values())
    accuracy = fsum(p * o[1] for (s, o), p in joint.items())
    paid = cost * int(policy.probe)
    return Score(policy.name, accuracy, paid, accuracy-paid, cross_entropy,
                 information, task_information, cross_entropy-information,
                 cross_entropy-task_information, direct, risk+ambiguity)


def choose(model: Model, y: int, beta: float, cost: float, objective: str) -> Policy:
    if objective not in ("efe_all", "efe_task", "preference_cross_entropy"):
        raise ValueError("Unknown objective")
    best, value = POLICIES[0], inf
    for policy in POLICIES:
        candidate = getattr(score(model, y, policy, beta, cost), objective)
        if candidate < value-TOLERANCE:
            best, value = policy, candidate
    return best


def bayesian_plan(model: Model, y: int, cost: float,
                  force_probe: bool = False) -> Policy:
    """Backward induction, independent of EFE and terminal-feedback scoring."""
    if not isfinite(cost) or cost < 0.0:
        raise ValueError("Cost must be finite and nonnegative")
    q = model.posterior(y)
    masses = [fsum(p for s, p in zip(STATES, q) if s[0] == x) for x in (0, 1)]
    skip_d = int(masses[1] > masses[0]+TOLERANCE)
    skip_value = masses[skip_d]
    responses = []
    probe_value = -cost
    for z in (0, 1):
        masses = [fsum(p * model.diagnostic(s, True, z)
                       for s, p in zip(STATES, q) if s[0] == x) for x in (0, 1)]
        response = int(masses[1] > masses[0]+TOLERANCE)
        responses.append(response)
        probe_value += masses[response]
    if force_probe or probe_value > skip_value+TOLERANCE:
        return Policy(True, *responses)
    return Policy(False, skip_d, skip_d)


def misspecification_example() -> dict:
    assumed = Model.independent(noise=0.1)
    truth = Model.common_fault(noise=0.1)
    before = assumed.posterior(0)
    joint = assumed.history_joint(0, 0)
    after = normalize(joint)
    true_posterior = normalize(truth.history_joint(0, 0))
    def world_marginal(distribution: tuple[float, ...]) -> tuple[float, float]:
        return tuple(fsum(p for s, p in zip(STATES, distribution) if s[0] == x)
                     for x in (0, 1))
    p_before, p_after, p_true = map(world_marginal, (before, after, true_posterior))
    return {
        "history": {"y": 0, "z": 0},
        "noise": 0.1,
        "vfe_before": vfe(before, joint),
        "vfe_after": vfe(after, joint),
        "kl_before_to_exact": kl(before, after),
        "negative_log_evidence": -log(fsum(joint)),
        "assumed_world_before": p_before,
        "assumed_world_after": p_after,
        "true_world_posterior": p_true,
        "external_log_loss_before": -fsum(p * log(q) for p, q in zip(p_true, p_before)),
        "external_log_loss_after": -fsum(p * log(q) for p, q in zip(p_true, p_after)),
    }
