"""Trajectory-mask planning and independent physical evaluation for paid audits."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import exp, fsum, inf, isfinite, log, log1p

from fep_model_learning.exact import entropy, mutual_information
from fep_model_checking.exact import MODEL_TRUTHS, TRUTHS, kernel

CLOSED = (1/3, 1/3, 1/3, 0)
EXTENDED = (.3, .3, .3, .1)
TARGETS = ('all', 'model', 'family', 'task', 'none')
ALPHAS = (.5, .25, .125, .05)
NULL = 2
TOL = 1e-12


@dataclass(frozen=True)
class Action:
    probe: bool
    audit0: bool
    audit1: bool

    def audit(self, z):
        return self.audit1 if z == 1 else self.audit0


ACTIONS = (Action(False, False, False), Action(False, True, True)) + tuple(
    Action(True, a, b) for a, b in product((False, True), repeat=2))
FIXED_ACTIONS = (ACTIONS[0], ACTIONS[1], ACTIONS[2], ACTIONS[5])


def physical_paths(truth, horizon, label=0):
    if horizon not in (1, 2, 3, 4):
        raise ValueError('Use horizon 1..4')
    paths = {(label, (r,), (a,)): .25 for r, a in product((0, 1), repeat=2)}
    for t in range(1, horizon):
        result = {}
        for (m, rs, aas), p in paths.items():
            for b, v, probability in kernel(truth, terminal=t == horizon-1):
                state = m, rs+(rs[-1] ^ b,), aas+(aas[-1] ^ v,)
                result[state] = result.get(state, 0)+p*probability
        paths = result
    return paths


@dataclass
class Node:
    stage: int
    mask: int
    action: Action
    reports: tuple[tuple[int, ...], tuple[int, ...]]
    children: dict

    def guesses(self, z):
        return self.reports[1] if z == 1 else self.reports[0]


@dataclass
class Solution:
    node: Node
    utility: float
    information: float
    value: float


def preference_constant(horizon, beta, cost, audit_cost):
    def softplus(x):
        return max(x, 0)+log1p(exp(-abs(x)))
    return horizon*(softplus(beta)+softplus(-beta*cost)+softplus(-beta*audit_cost))


class Engine:
    def __init__(self, prior, horizon, models=MODEL_TRUTHS):
        if len(prior) != len(models) or any(not isfinite(p) or p < 0 for p in prior) or abs(fsum(prior)-1) > TOL:
            raise ValueError('Prior must be normalized and match the candidate mechanisms')
        self.prior, self.horizon, self.models = tuple(prior), horizon, tuple(models)
        self.paths, self.base = [], []
        for m, truth in enumerate(models):
            for state, p in physical_paths(truth, horizon, m).items():
                self.paths.append(state)
                self.base.append(p)
        self.weights = tuple(prior[s[0]]*p for s, p in zip(self.paths, self.base))
        self.root = (1 << len(self.paths))-1  # Keep zero-prior alternatives for the diagnostic readout.
        self.r_masks = tuple(tuple(self._mask(lambda s: s[1][t] == r) for r in (0, 1)) for t in range(horizon))
        self.z_masks = tuple(tuple(self._mask(lambda s: s[1][t] ^ s[2][t] == z) for z in (0, 1)) for t in range(horizon))
        self._mass_cache, self._entropy_cache, self._round_cache = {}, {}, {}

    def _mask(self, predicate):
        return sum(1 << i for i, state in enumerate(self.paths) if predicate(state))

    @staticmethod
    def indices(mask):
        while mask:
            bit = mask & -mask
            yield bit.bit_length()-1
            mask ^= bit

    def mass(self, mask):
        if mask not in self._mass_cache:
            self._mass_cache[mask] = fsum(self.weights[i] for i in self.indices(mask))
        return self._mass_cache[mask]

    def entropies(self, mask):
        if mask not in self._entropy_cache:
            mass = self.mass(mask)
            if mass <= 0:
                raise ValueError('History has zero evidence under the planning prior')
            groups = {t: {} for t in ('all', 'model', 'family', 'task')}
            for i in self.indices(mask):
                p = self.weights[i]/mass
                if not p:
                    continue
                state = self.paths[i]
                keys = {'all': i, 'model': state[0], 'family': int(state[0] == 3), 'task': state[1]}
                for name, key in keys.items():
                    groups[name][key] = groups[name].get(key, 0)+p
            self._entropy_cache[mask] = {t: entropy(g.values()) for t, g in groups.items()} | {'none': 0.0}
        return self._entropy_cache[mask]

    def filter_mask(self, mask, stage, obs):
        z, r = obs
        if z != NULL:
            mask &= self.z_masks[stage][z]
        if r != NULL:
            mask &= self.r_masks[stage][r]
        return mask

    def round(self, mask, stage, action):
        key = mask, stage, action
        if key not in self._round_cache:
            mass = self.mass(mask)
            if mass <= 0:
                raise ValueError('Impossible planning history')
            accuracy, audit_probability = 0.0, 0.0
            reports = [(0, 1), (0, 1)]
            branches = []
            for z in ((0, 1) if action.probe else (NULL,)):
                zmask = mask if z == NULL else mask & self.z_masks[stage][z]
                zp = self.mass(zmask)
                if not zp:
                    continue
                counts = [self.mass(zmask & self.r_masks[stage][r]) for r in (0, 1)]
                maximum = max(counts)
                guesses = tuple(r for r in (0, 1) if counts[r] >= maximum-TOL*zp)
                reports[1 if z == 1 else 0] = guesses
                accuracy += maximum/mass
                audit_probability += zp/mass*action.audit(z)
                for r in ((0, 1) if action.audit(z) else (NULL,)):
                    child = zmask if r == NULL else zmask & self.r_masks[stage][r]
                    probability = self.mass(child)/mass
                    if probability:
                        branches.append(((z, r), child, probability))
            self._round_cache[key] = accuracy, audit_probability, tuple(reports), tuple(branches)
        return self._round_cache[key]

    def information_constant(self, target):
        if target == 'all':
            return (self.horizon-1)*log(2)
        if target == 'task':
            return self.horizon*log(2)-self.entropies(self.root)['task']
        return 0.0

    def solve(self, beta, cost, audit_cost, target, schedule=None, force_audits=False):
        if target not in TARGETS or not isfinite(beta) or beta <= 0 or any(not isfinite(v) or v < 0 for v in (cost, audit_cost)):
            raise ValueError('Invalid objective or preference scale/cost')
        if schedule is not None and len(schedule) != self.horizon:
            raise ValueError('Schedule must span the horizon')

        @lru_cache(None)
        def backward(mask, stage):
            best = None
            actions = (schedule[stage],) if schedule is not None else ACTIONS
            for action in actions:
                if force_audits and not (action.audit0 and action.audit1):
                    continue
                accuracy, audits, reports, groups = self.round(mask, stage, action)
                utility = accuracy-cost*action.probe-audit_cost*audits
                gain = 0.0 if target == 'none' else self.entropies(mask)[target]-fsum(p*self.entropies(child)[target] for obs, child, p in groups)
                children = {}
                if stage+1 < self.horizon:
                    for obs, child, p in groups:
                        future = backward(child, stage+1)
                        utility += p*future.utility
                        gain += p*future.information
                        children[obs] = future.node
                value = beta*utility+gain
                if best is None or value > best.value+TOL:
                    best = Solution(Node(stage, mask, action, reports, children), utility, gain, value)
            return best

        solution = backward(self.root, 0)
        constant = self.information_constant(target)
        return Solution(solution.node, solution.utility, solution.information+constant, solution.value+constant)

    def best_fixed(self, cost, audit_cost):
        @lru_cache(None)
        def value(mask, stage, schedule):
            action = schedule[0]
            accuracy, audits, reports, groups = self.round(mask, stage, action)
            result = accuracy-cost*action.probe-audit_cost*audits
            if len(schedule) > 1:
                result += fsum(p*value(child, stage+1, schedule[1:]) for obs, child, p in groups)
            return result
        rows, best = [], None
        for schedule in product(FIXED_ACTIONS, repeat=self.horizon):
            utility = value(self.root, 0, schedule)
            label = ''.join(str(FIXED_ACTIONS.index(a)) for a in schedule)
            rows.append({'schedule': label, 'utility': utility})
            if best is None or utility > best[0]+TOL:
                best = utility, schedule, label
        solution = self.solve(1, cost, audit_cost, 'none', schedule=best[1])
        return {'utility': best[0], 'schedule': best[2], 'rows': rows}, solution.node

    def baseline(self, name):
        if name not in ('no_measurements', 'one_audit_memory', 'audit_memory'):
            raise ValueError('Unknown baseline')
        def build(stage, mask, remembered):
            audit = (name == 'one_audit_memory' and stage == 0) or (name == 'audit_memory' and stage < self.horizon-1)
            action = ACTIONS[int(audit)]
            guesses = (0, 1) if remembered is None else (remembered,)
            groups = self.round(mask, stage, action)[3]
            children = {}
            if stage+1 < self.horizon:
                for obs, child, p in groups:
                    children[obs] = build(stage+1, child, obs[1] if obs[1] != NULL else remembered)
            return Node(stage, mask, action, (guesses, guesses), children)
        return build(0, self.root, None)

    def family_ratio(self, mask):
        if self.models != MODEL_TRUTHS:
            raise ValueError('Family readout requires the declared four candidates')
        likelihoods = [0.0]*4
        for i in self.indices(mask):
            likelihoods[self.paths[i][0]] += self.base[i]
        denominator = max(likelihoods[:3])
        return likelihoods[3]/denominator if denominator else inf

    def prior_paths(self):
        return {state: p for state, p in zip(self.paths, self.weights) if p}


def path_trace(state, node, engine=None):
    m, rs, aas = state
    trace, accuracy, probes, audits, ratios = [], [], [], [], []
    for stage, r in enumerate(rs):
        z = r ^ aas[stage] if node.action.probe else NULL
        audit = node.action.audit(z)
        guesses = node.guesses(z)
        accuracy.append(float(r in guesses)/len(guesses))
        probes.append(int(node.action.probe))
        audits.append(int(audit))
        obs = z, r if audit else NULL
        trace.append((obs[0], obs[1], int(node.action.probe), int(audit)))
        if engine is not None:
            ratios.append(engine.family_ratio(engine.filter_mask(node.mask, stage, obs)))
        if stage+1 < len(rs):
            if obs not in node.children:
                raise ValueError('Policy has no branch for an observable physical history')
            node = node.children[obs]
    return tuple(trace), accuracy, probes, audits, ratios


def evaluate(paths, node, cost, audit_cost, engine=None):
    horizon = len(next(iter(paths))[1])
    accuracy, probes, audits = [0.0]*horizon, [0.0]*horizon, [0.0]*horizon
    alarm, timely = {str(a): 0.0 for a in ALPHAS}, {str(a): 0.0 for a in ALPHAS}
    maximum = 0.0
    for state, p in paths.items():
        trace, correct, k, a, ratios = path_trace(state, node, engine)
        for t in range(horizon):
            accuracy[t] += p*correct[t]
            probes[t] += p*k[t]
            audits[t] += p*a[t]
        if engine is not None:
            maximum = max(maximum, *ratios)
            for alpha in ALPHAS:
                alarm[str(alpha)] += p*int(max(ratios) >= 1/alpha-TOL)
                timely[str(alpha)] += p*int(bool(ratios[:-1]) and max(ratios[:-1]) >= 1/alpha-TOL)
    utility = fsum(accuracy)-cost*fsum(probes)-audit_cost*fsum(audits)
    return {'utility': utility, 'expected_correct': fsum(accuracy),
            'accuracy_by_round': accuracy, 'probes_by_round': probes, 'audits_by_round': audits,
            'expected_probes': fsum(probes), 'expected_audits': fsum(audits),
            'probe_cost_paid': cost*fsum(probes), 'audit_cost_paid': audit_cost*fsum(audits),
            'alarm_probability': alarm if engine is not None else None,
            'timely_alarm_probability': timely if engine is not None else None,
            'maximum_family_ratio': maximum if engine is not None else None}


def information_reference(engine, node):
    paths = engine.prior_paths()
    joint = {(s, path_trace(s, node)[0]): p for s, p in paths.items()}
    info_r = mutual_information(joint, 'task')
    family_joint = {((int(s[0] == 3), s[1], s[2], s[0]), obs): p for (s, obs), p in joint.items()}
    return {'all': mutual_information(joint, 'all')+(engine.horizon-1)*log(2),
            'model': mutual_information(joint, 'model'),
            'family': mutual_information(family_joint, 'model'),
            'task': engine.horizon*log(2)-engine.entropies(engine.root)['task']+info_r,
            'none': 0.0}


def world_information_reference(engine, node, y1=0):
    joint = {}
    for state, p in engine.prior_paths().items():
        obs = path_trace(state, node)[0]
        m, rs, aas = state
        for later_y in product((0, 1), repeat=engine.horizon-1):
            ys = (y1,)+later_y
            xs = tuple(y ^ r for y, r in zip(ys, rs))
            latent = m, xs, rs, aas
            joint[latent, (later_y, obs)] = p/2**(engine.horizon-1)
    return {t: mutual_information(joint, t) for t in ('all', 'model', 'task')}


def bayesian_reference(prior, horizon, cost, audit_cost, models=MODEL_TRUTHS):
    """Separate recursion on weighted complete physical paths, without support masks."""
    paths = {}
    for m, truth in enumerate(models):
        if prior[m]:
            paths.update({s: prior[m]*p for s, p in physical_paths(truth, horizon, m).items()})

    @lru_cache(None)
    def recurse(items, stage):
        best = -inf
        for action in ACTIONS:
            z_groups = {}
            for state, p in items:
                z = state[1][stage] ^ state[2][stage] if action.probe else NULL
                z_groups.setdefault(z, []).append((state, p))
            utility = -cost*action.probe
            groups = {}
            for z, values in z_groups.items():
                mass = fsum(p for s, p in values)
                utility += max(fsum(p for s, p in values if s[1][stage] == r) for r in (0, 1))
                utility -= audit_cost*action.audit(z)*mass
                for state, p in values:
                    obs = z, state[1][stage] if action.audit(z) else NULL
                    groups.setdefault(obs, []).append((state, p))
            if stage+1 < horizon:
                for values in groups.values():
                    mass = fsum(p for s, p in values)
                    utility += mass*recurse(tuple((s, p/mass) for s, p in values), stage+1)
            best = max(best, utility)
        return best
    return recurse(tuple(paths.items()), 0)


def serialize_policy(node):
    records = {}
    def visit(current):
        name = f'{current.stage}:{current.mask:x}'
        if name not in records:
            records[name] = {'round': current.stage+1, 'probe': current.action.probe,
                             'audit_z0_or_null': current.action.audit0, 'audit_z1': current.action.audit1,
                             'equally_weighted_reports': current.reports, 'children': {}}
            for obs, child in current.children.items():
                records[name]['children'][f'{obs[0]},{obs[1]}'] = visit(child)
        return name
    root = visit(node)
    return {'root': root, 'nodes': records}
