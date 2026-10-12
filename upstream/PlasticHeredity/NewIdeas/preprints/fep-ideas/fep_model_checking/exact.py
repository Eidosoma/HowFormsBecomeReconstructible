"""Visible-history inference, a calibrated monitor, and independent physical paths."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import fsum, isfinite, log

from fep_model_learning.exact import Policy, POLICIES, entropy, normalize, preference_constant, vfe

MODELS = ('S', 'V', 'C', 'P')
STATES = tuple(product(range(4), (0, 1), (0, 1)))  # class, sensor, route
INDEX = {s: i for i, s in enumerate(STATES)}
CLOSED = (1/3, 1/3, 1/3, 0)
EXTENDED = (.3, .3, .3, .1)
TARGETS = ('all', 'model', 'task', 'none')
TOL = 1e-12


@dataclass(frozen=True)
class History:
    sensor_changes: tuple[int, ...]
    first_route_change: int

    def __post_init__(self):
        if not self.sensor_changes or any(b not in (0, 1) for b in self.sensor_changes):
            raise ValueError('History needs at least one binary sensor transition')
        if self.first_route_change not in (0, 1):
            raise ValueError('Route transition must be binary')

    @property
    def last_sensor(self):
        return sum(self.sensor_changes) % 2

    @property
    def label(self):
        return ''.join(str(b) for b in self.sensor_changes)+':'+str(self.first_route_change)


@dataclass(frozen=True)
class Truth:
    name: str
    rho: float
    route: str
    terminal_route: str | None = None

    def __post_init__(self):
        if not isfinite(self.rho) or not 0 <= self.rho <= 1:
            raise ValueError('Sensor flip rate must be a probability')
        if self.route not in ('stable', 'volatile', 'shared') or self.terminal_route not in (None, 'stable', 'volatile', 'shared'):
            raise ValueError('Unknown route mechanism')


NULLS = (Truth('null_S', .5, 'stable'), Truth('null_V', .5, 'volatile'), Truth('null_C', .5, 'shared'))
PERSISTENT = Truth('sensor_rho_0', 0, 'volatile')
TRUTHS = NULLS+(PERSISTENT, Truth('sensor_rho_0.1', .1, 'volatile'),
                Truth('sensor_rho_0.25', .25, 'volatile'), Truth('sensor_rho_0.75', .75, 'volatile'),
                Truth('unannounced_route_break', .5, 'stable', 'volatile'))
MODEL_TRUTHS = NULLS+(PERSISTENT,)


def histories(n):
    if not isinstance(n, int) or not 1 <= n <= 10:
        raise ValueError('History length must be 1..10')
    return tuple(History(bs, v) for bs, v in product(product((0, 1), repeat=n), (0, 1)))


def history_probability(truth: Truth, h: History):
    b0, v = h.sensor_changes[0], h.first_route_change
    route = (float(v == 0) if truth.route == 'stable' else
             .5 if truth.route == 'volatile' else float(v == b0))
    changes = sum(h.sensor_changes)
    return truth.rho**changes * (1-truth.rho)**(len(h.sensor_changes)-changes) * route


def class_joint(prior, h):
    if len(prior) != 4 or any(not isfinite(p) or p < 0 for p in prior) or abs(fsum(prior)-1) > TOL:
        raise ValueError('Class prior must be a normalized nonnegative quadruple')
    return tuple(p*history_probability(truth, h) for p, truth in zip(prior, MODEL_TRUTHS))


def class_posterior(prior, h):
    return normalize(class_joint(prior, h))


def terminal_distribution(truth: Truth, h: History, origin=(0, 0)):
    """Analytic conditional distribution of the next sensor and route mappings."""
    r0, a0 = origin
    if r0 not in (0, 1) or a0 not in (0, 1):
        raise ValueError('Initial mappings must be binary')
    last = r0 ^ h.last_sensor
    route = truth.terminal_route or truth.route
    result = {}
    for b in (0, 1):
        p = truth.rho if b else 1-truth.rho
        if p == 0:
            continue
        r = last ^ b
        options = ((a0, 1.0),) if route == 'stable' else ((0, .5), (1, .5)) if route == 'volatile' else ((a0 ^ h.last_sensor ^ b, 1.0),)
        for a, weight in options:
            result[r, a] = result.get((r, a), 0)+p*weight
    return result


def prediction(prior, h, origin=(0, 0)):
    posterior = class_posterior(prior, h)
    q = [0.0]*16
    for m, weight in enumerate(posterior):
        if not weight:
            continue
        for (r, a), p in terminal_distribution(MODEL_TRUTHS[m], h, origin).items():
            q[INDEX[m, r, a]] += weight*p
    return tuple(q)


def class_marginal(q):
    return tuple(fsum(q[i] for i, s in enumerate(STATES) if s[0] == m) for m in range(4))


def branches(q, policy):
    weights = {}
    for i, (m, r, a) in enumerate(STATES):
        if not q[i]:
            continue
        z = r ^ a if policy.probe else 2
        observation = z, int(policy.guess(z) == r)
        weights.setdefault(observation, [0.0]*16)[i] = q[i]
    return {obs: (fsum(w), normalize(w)) for obs, w in weights.items()}


def score(q, policy, beta, cost):
    if not isfinite(beta) or beta <= 0 or not isfinite(cost) or cost < 0:
        raise ValueError('Require positive finite beta and nonnegative finite cost')
    groups = branches(q, policy)
    accuracy = fsum(p*obs[1] for obs, (p, post) in groups.items())
    utility = accuracy-cost*policy.probe
    info = {'all': entropy(p for p, post in groups.values()),
            'model': entropy(class_marginal(q))-fsum(p*entropy(class_marginal(post)) for p, post in groups.values()),
            'task': entropy(fsum(q[i] for i, s in enumerate(STATES) if s[1] == r) for r in (0, 1)),
            'none': 0.0}
    constant = preference_constant(1, beta, cost)
    direct = fsum(qi*(log(qi)-log(post[i])+constant-beta*(obs[1]-cost*policy.probe))
                  for obs, (p, post) in groups.items() for i, qi in enumerate(q) if post[i] > 0)
    return {'accuracy': accuracy, 'utility': utility, 'information': info,
            'efe': {target: constant-beta*utility-gain for target, gain in info.items()},
            'efe_direct_all': direct}


@dataclass(frozen=True)
class Choice:
    policies: tuple[Policy, ...]

    def __post_init__(self):
        if not self.policies or any(p.probe != self.policies[0].probe for p in self.policies):
            raise ValueError('A choice must contain report maps with the same probe choice')

    @property
    def probe(self):
        return self.policies[0].probe

    def serialized(self):
        return {'probe': self.probe, 'equally_weighted_report_maps': [[p.r0, p.r1] for p in self.policies]}


@lru_cache(None)
def choose(q, beta, cost, target):
    if target not in TARGETS:
        raise ValueError('Unknown EFE target')
    values = [(p, score(q, p, beta, cost)['efe'][target]) for p in POLICIES]
    best = min(v for p, v in values)
    candidates = [p for p, v in values if v <= best+TOL]
    probe = all(p.probe for p in candidates)  # Skip if both probe choices tie.
    return Choice(tuple(p for p in candidates if p.probe == probe))


def monitor(h, alpha):
    if not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('Use a false-alarm tolerance strictly between zero and one')
    value, first = 1.0, None
    trace = [value]
    for t, b in enumerate(h.sensor_changes, 1):
        value *= 2*(1-b)
        trace.append(value)
        if first is None and value >= 1/alpha:
            first = t
    return {'alarm': first is not None, 'first_crossing': first, 'terminal_value': value, 'trace': trace}


def crossing_length(alpha):
    if not isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('Invalid false-alarm tolerance')
    k = 0
    while 2**k < 1/alpha:
        k += 1
    return k


def copy_last(h, origin=(0, 0)):
    r = origin[0] ^ h.last_sensor
    return Choice((Policy(False, r, r),))


def gate(choice, h, alpha, origin=(0, 0)):
    return copy_last(h, origin) if monitor(h, alpha)['alarm'] else choice


def physical_score(distribution, choice, cost):
    """Independent world/report simulation; no planner posterior or true class label."""
    accuracy = 0.0
    for (r, a), p in distribution.items():
        for x in (0, 1):
            y = x ^ r
            for policy in choice.policies:
                z = r ^ a if policy.probe else 2
                report = y ^ policy.guess(z)
                accuracy += p/2/len(choice.policies)*int(report == x)
    probes = float(choice.probe)
    return {'accuracy': accuracy, 'probes': probes, 'utility': accuracy-cost*probes,
            'utility_including_audit_probes': accuracy-cost*(probes+2)}


def bayesian_reference(q, cost):
    distribution = {(r, a): fsum(q[INDEX[m, r, a]] for m in range(4)) for r, a in product((0, 1), repeat=2)}
    return max(physical_score(distribution, Choice((p,)), cost)['utility'] for p in POLICIES)


def kernel(truth, terminal=False):
    route = (truth.terminal_route or truth.route) if terminal else truth.route
    result = []
    for b in (0, 1):
        pb = truth.rho if b else 1-truth.rho
        for v in (0, 1):
            pv = float(v == 0) if route == 'stable' else .5 if route == 'volatile' else float(v == b)
            if pb*pv:
                result.append((b, v, pb*pv))
    return tuple(result)


@lru_cache(None)
def physical_history_joint(truth, n, origin=(0, 0)):
    """Enumerate actual transitions, then marginalize unobserved route changes."""
    histories(n)  # Validate length.
    states = {((), None, origin[0], origin[1]): 1.0}
    for stage in range(n):
        next_states = {}
        for (bs, first_v, r, a), weight in states.items():
            for b, v, p in kernel(truth):
                key = (bs+(b,), v if stage == 0 else first_v, r ^ b, a ^ v)
                next_states[key] = next_states.get(key, 0)+weight*p
        states = next_states
    result = {}
    for (bs, first_v, r, a), weight in states.items():
        h = History(bs, first_v)
        for b, v, p in kernel(truth, terminal=True):
            endpoint = r ^ b, a ^ v
            group = result.setdefault(h, {})
            group[endpoint] = group.get(endpoint, 0)+weight*p
    return result


def posterior_evidence(prior, h):
    joint = class_joint(prior, h)
    post = normalize(joint)
    return {'posterior': post, 'evidence': fsum(joint), 'entropy': entropy(post),
            'max_class_probability': max(post), 'exact_vfe': vfe(post, joint)}
