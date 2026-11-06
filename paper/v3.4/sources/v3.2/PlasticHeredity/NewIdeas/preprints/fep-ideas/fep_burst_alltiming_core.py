"""Full-onset loss and exact changing-persistence evaluation; v1 stays frozen."""
from fractions import Fraction as F
import math

import fep_burst_learning_core as previous
import check_fep_burst_confidence as physical
from check_fep_burst_learning import summary

Model, K, MUS = previous.Model, previous.K, previous.MUS
TRAIN = (F(0), F(3, 4))
PROFILES = {
    'training_00': (F(0),) * 9,
    'training_75': (F(3, 4),) * 9,
    'constant_20': (F(1, 5),) * 9,
    'constant_40': (F(2, 5),) * 9,
    'constant_60': (F(3, 5),) * 9,
    'constant_80': (F(4, 5),) * 9,
    'alternating_low': tuple(F(9, 10) if j % 2 else F(0) for j in range(9)),
    'alternating_high': tuple(F(0) if j % 2 else F(9, 10) for j in range(9)),
    'onset_after_5': (F(0),) * 4 + (F(9, 10),) * 5,
    'offset_after_5': (F(9, 10),) * 4 + (F(0),) * 5,
}
HELDOUT = tuple(PROFILES)[2:]


class Oracle(previous.Oracle):
    def __init__(self, m, mu, frozen=False):
        self.m, self.mu, self.frozen = m, F(mu), frozen
        self.cache = {}
        utility = {t: [F(1, m.T)
            + (1 / (m.rho * (m.T - tau + 1)) if 0 < tau <= t else 0)
            + (self.mu / ((1 - m.rho) * m.T) if tau == 0 else 0)
            for _, tau, _ in m.states] for t in range(1, m.T + 1)}
        assert all(v > 0 for row in utility.values() for v in row)
        self.den = math.lcm(*(v.denominator for row in utility.values() for v in row))
        self.coeff = {t: tuple(int(v * self.den) for v in row) for t, row in utility.items()}


def training(graph, T):
    settings = {}
    for alpha in TRAIN:
        ws = [previous.physical(graph, T, tau, alpha) for tau in [None, *range(1, T + 1)]]
        stable = ws[0]['cost'] / T
        full = stable / 2 + sum(w['cost'] for w in ws[1:]) / (2 * T * T)
        recovery = sum(w['recovery'] for w in ws[1:]) / T
        settings[str(alpha)] = dict(worlds=ws, stable=stable, B=full, R=recovery, C=full + recovery)
    return dict(settings=settings, C=sum(v['C'] for v in settings.values()) / 2,
                S=[settings[str(a)]['stable'] for a in TRAIN])


def select_pool(records, budget=K):
    result = previous.select_pool(records, budget)
    result['objective'] = 'mean training full-prior B+R'
    return result


def markov(T, profile):
    assert len(profile) == T - 1 and all(0 <= a <= 1 for a in profile)
    transitions = []
    den = 20
    for a in profile:
        n, d = a.numerator, a.denominator
        den *= 20 * d
        transitions.append(((19 * d + n, d - n), (19 * (d - n), d + 19 * n)))
    masses = []
    for bits in range(1 << T):
        z = bits & 1
        mass = 1 if z else 19
        for t, transition in enumerate(transitions, 1):
            nextz = (bits >> t) & 1
            mass *= transition[z][nextz]
            z = nextz
        masses.append(mass)
    assert sum(masses) == den
    assert all(20 * sum(p for bits, p in enumerate(masses) if bits >> t & 1) == den for t in range(T))
    return masses, den


def evaluate(graph, beliefs, T, tau, profile, traces=None):
    masses, den = markov(T, profile)
    traces = physical.trace(graph, beliefs, T, tau) if traces is None else traces
    totals = [0] * len(physical.RAW)
    visits, repeats = [0] * len(graph), [0] * len(graph)
    delay = missing = pre = 0
    for mass, (row, seen, repeated) in zip(masses, traces):
        if not mass:
            continue
        for j, value in enumerate(row):
            totals[j] += mass * value
        for i in seen:
            visits[i] += mass
        for i in repeated:
            repeats[i] += mass
        inversions = [graph[i]['t'] for i in seen if graph[i]['action'] == 'R']
        after = [] if tau is None else [t for t in inversions if t >= tau]
        pre += mass * sum(tau is None or t < tau for t in inversions)
        missing += mass * int(not after)
        delay += mass * (0 if tau is None else after[0] - tau if after else T - tau + 1)
    out = dict(onset=tau, **{k: F(v, den) for k, v in zip(physical.RAW, totals)})
    if beliefs[0] is None:
        out.update({k: None for k in physical.BELIEF})
    else:
        brier = confidence = gain = F(0)
        for i, n in enumerate(graph):
            truth = int(tau is not None and n['t'] >= tau)
            q = beliefs[i]['q']
            brier += visits[i] * (q - truth) ** 2
            confidence += visits[i] * max(q, 1 - q)
            gain += repeats[i] * (beliefs[i]['post'][1 - truth] - q) * (1 - 2 * truth)
        out.update(brier=brier / den, confidence=confidence / den, repeat_gain=gain / den)
    out.update(cost=out['errors'] + out['purchases'] / 10,
               post_cost=out['post_errors'] + out['post_purchases'] / 10,
               inverse_delay=F(delay, den), inverse_missing=F(missing, den), pre_inverse=F(pre, den))
    out['recovery'] = None if tau is None else out['post_cost'] / (T - tau + 1)
    return out


def record(graph, belief, profile, traces=None):
    qs = physical.info(graph, belief)
    worlds = [evaluate(graph, qs, 10, tau, profile, None if traces is None else traces[j])
              for j, tau in enumerate([None, *range(1, 11)])]
    return dict(worlds=worlds, summary=summary(worlds))


def mix(policies, components):
    assert sum(F(c['weight']) for c in components) == 1
    worlds = []
    for j, tau in enumerate([None, *range(1, 11)]):
        row = dict(onset=tau)
        for k in policies[components[0]['policy']]['worlds'][j]:
            if k == 'onset':
                continue
            values = [(F(c['weight']), policies[c['policy']]['worlds'][j][k]) for c in components]
            row[k] = None if any(v is None for _, v in values) else sum(w * v for w, v in values)
        worlds.append(row)
    return dict(components=components, worlds=worlds, summary=summary(worlds))
