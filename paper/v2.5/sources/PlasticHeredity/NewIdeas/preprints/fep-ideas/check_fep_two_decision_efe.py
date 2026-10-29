#!/usr/bin/env python3
"""Exact two-task conditional EFE with physical-world enumeration and external records."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
from functools import lru_cache
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback
from typing import NamedTuple

getcontext().prec = 80
BITS = (0, 1)
LATENTS = tuple(product(BITS, repeat=2))
PRIOR = (F(1, 4),)*4
VERTICES = ((F(0), F(0)), (F(2, 11), F(0)),
            (F(4, 55), F(4, 55)), (F(0), F(8, 99)))
CONSTRAINTS = ((F(-1), F(0), F(0)), (F(0), F(-1), F(0)),
               (F(1), F(0), F(1)), (F(0), F(1), F(1)),
               (F(9, 10), F(1, 10), F(1, 3)), (F(4, 5), F(1, 5), F(1, 3)),
               (F(1, 10), F(9, 10), F(4, 55)), (F(1, 5), F(4, 5), F(4, 55)),
               (F(2, 5), F(3, 5), F(4, 55)))
MOUNT = Path('/mnt/bioIce1')
OUTPUT_ROOT = MOUNT/'fep-ideas/formal-checks/fep-two-decision-efe-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-terminal-action-audit-v1/attempt-01'
TOL, MAX_ERROR = D('1e-60'), D(0)
COUNTS = Counter()
PRESERVED = {
    'FEP_TERMINAL_ACTION_AUDIT_V1.md': 'be1adb0c9206c1b804ba932ae01f08a3d10b2e173fd13aaba56987b7d1e4b069',
    'FEP_TERMINAL_ACTION_AUDIT_V1_REPORT.md': '10df3990f3761a0f902e5cf4d78894ae24ffa845e2abd506a990176d86fcd327',
    'check_fep_terminal_action_audit.py': '64750a4e7c5d500ff54339bc75e95ae3429f00f5871f91e9b61b00cadca289d8',
    'FEP_SENSOR_CHANGE_V1.md': '68b25252b633200741f5d8d3cc1f48c3d63e40e3c2e9d775b9b1673f50e059fb',
    'FEP_SENSOR_CHANGE_V1_REPORT.md': 'ebb84a4d955c8c5e9b334d7e3c9719cc7e6f49b04716125fdb486e6c28144a0c',
    'check_fep_sensor_change.py': '2ae348a8b7872e9c63040575c69ad8a5441286752bcbb348e7f4ce2f15280e22',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md': '402480808b61ad9718d38fa0f6f494f2c01819b807491cb386fdde89eb5b76f0',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md': 'fdabe647e938aa4c6b3e828447b4c0162e3ee32644581505776d819889c11d9c',
}


def dec(x):
    return D(x.numerator)/D(x.denominator) if isinstance(x, F) else D(x)


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, a, b):
    global MAX_ERROR
    error = abs(dec(a)-dec(b))
    MAX_ERROR = max(MAX_ERROR, error)
    check(group, label, error <= TOL)


def bern(p, x):
    return p if x else 1-p


@lru_cache(None)
def entropy(q):
    return -sum((dec(p)*dec(p).ln() for p in q if p), D(0))


@lru_cache(None)
def update(q, likelihood):
    mass = sum(p*l for p, l in zip(q, likelihood))
    posterior = tuple(p*l/mass for p, l in zip(q, likelihood))
    information = sum((dec(p)*(dec(p)/dec(prior)).ln() for p, prior in zip(posterior, q)), D(0))
    return mass, posterior, information


def sensor(l, w, b, y):
    theta, changed = l
    good = theta != b
    alarm = F(9 if good else (6 if changed else 8), 10) if w else F(1 if good else 2, 10)
    return bern(alarm, y)


def failure(w, a):
    return F(2, 25)+(F(11, 40) if w else F(3, 50))*a


@lru_cache(None)
def cal_law(x):
    return tuple(bern(F(9 if th else (6 if dd else 8), 10), x) for th, dd in LATENTS)


@lru_cache(None)
def warning_law(b, y):
    return tuple(sum(sensor(l, w, b, y) for w in BITS)/2 for l in LATENTS)


@lru_cache(None)
def feedback_law(b, y, a, v):
    return tuple(sum(sensor(l, w, b, y)*bern(1-failure(w, a), v) for w in BITS)
                 /sum(sensor(l, w, b, y) for w in BITS) for l in LATENTS)


class Value(NamedTuple):
    U: F
    Ic: D
    Iy: D
    Ifb: D


ZERO = Value(F(0), D(0), D(0), D(0))


def add(a, b):
    return Value(*(x+y for x, y in zip(a, b)))


def mean(rows):
    return Value(sum(p*v.U for p, v in rows),
                 *(sum((dec(p)*v[j] for p, v in rows), D(0)) for j in (1, 2, 3)))


def information(v):
    return v.Ic+v.Iy+v.Ifb


def value_record(v):
    return dict(U=v.U, information=information(v), calibration_information=v.Ic,
                warning_information=v.Iy, feedback_information=v.Ifb)


class Planner:
    def __init__(self, kind, slot, buy):
        self.kind, self.slot, self.buy = kind, slot, buy
        self.nodes = {}

    def score(self, v):
        return -4*dec(v.U)-(information(v) if self.kind == 'EFE' else 0)

    @lru_cache(None)
    def solve(self, t, q, live, received):
        key = (t, q, live, received)
        check('beliefs', 'positive supported posterior', sum(q) == 1 and all(x > 0 for x in q))
        if t == self.slot and self.buy and not received:
            rows = []
            for x in BITS:
                px, qx, ix = update(q, cal_law(x))
                rows.append((px, add(self.solve(t, qx, live, True), Value(F(0), ix, D(0), D(0)))))
            result, node = mean(rows), dict(event='calibration')
        elif t == 3:
            result, node = ZERO, dict(event='terminal')
        elif not live:
            result, node = self.solve(t+1, q, False, received), dict(event='inactive')
        else:
            candidates = []
            for b in BITS:
                responses = {}
                warnings = {}
                for y in BITS:
                    py, qy, iy = update(q, warning_law(b, y))
                    warnings[y] = (py, iy)
                    for a in BITS:
                        rows = []
                        for v in BITS:
                            pv, qv, iv = update(qy, feedback_law(b, y, a, v))
                            later = self.solve(t+1, qv, bool(v), received)
                            local = Value(F(3, 4)+F(3, 20)*a+F(v, 2), D(0), D(0), iv)
                            rows.append((pv, add(local, later)))
                        responses[y, a] = mean(rows)
                per_channel = []
                for index, r in enumerate(VERTICES):
                    rows = [(warnings[y][0]*bern(r[y], a), responses[y, a]) for y, a in product(BITS, repeat=2)]
                    value = add(mean(rows), Value(F(0), D(0),
                                sum((dec(p)*ig for p, ig in warnings.values()), D(0)), D(0)))
                    candidate = dict(channel=b, vertex=index, value=value, score=self.score(value))
                    candidates.append(candidate)
                    per_channel.append(candidate)
                intercept = per_channel[0]['score']
                coefficients = [dec(warnings[y][0])*(self.score(responses[y, 1])-self.score(responses[y, 0])) for y in BITS]
                for c in per_channel:
                    r = VERTICES[c['vertex']]
                    close('Bellman', 'affine response score', c['score'], intercept+sum(dec(r[y])*coefficients[y] for y in BITS))
            selected = candidates[0]
            for candidate in candidates[1:]:
                if candidate['score'] < selected['score']-TOL:
                    selected = candidate
            check('Bellman', 'all vertex/channel choices compared', len(candidates) == 8
                  and all(selected['score'] <= c['score']+TOL for c in candidates))
            result = selected['value']
            node = dict(event='decision', channel=selected['channel'], vertex=selected['vertex'],
                        candidates=[dict(channel=c['channel'], vertex=c['vertex'], score=c['score'],
                                         **value_record(c['value'])) for c in candidates])
        self.nodes[key] = dict(t=t, belief=q, live=live, received=received,
                               **node, **value_record(result), score=self.score(result))
        return result

    def choice(self, t, q):
        received = bool(self.buy and self.slot <= t)
        self.solve(t, q, True, received)
        node = self.nodes[t, q, True, received]
        assert node['event'] == 'decision'
        return node['channel'], node['vertex']


def qualify():
    vertices = set()
    for (a, b, c), (d, e, f) in combinations(CONSTRAINTS, 2):
        determinant = a*e-b*d
        if determinant:
            point = ((c*e-b*f)/determinant, (a*f-c*d)/determinant)
            if all(u*point[0]+v*point[1] <= w for u, v, w in CONSTRAINTS):
                vertices.add(point)
    check('qualification', 'complete polygon vertices', vertices == set(VERTICES))
    for l, w, b, r in product(LATENTS, BITS, BITS, VERTICES):
        risk = sum(sensor(l, w, b, y)*(F(2, 25)+(F(11, 40) if w else F(3, 50))*r[y]) for y in BITS)
        check('qualification', 'primary risk at all vertices', risk <= F(1, 10))
    for b, y, a in product(BITS, repeat=3):
        for index, l in enumerate(LATENTS):
            check('qualification', 'collapsed warning', warning_law(b, y)[index] == sum(sensor(l, w, b, y) for w in BITS)/2)
            for v in BITS:
                direct = sum(sensor(l, w, b, y)*bern(1-failure(w, a), v)/2 for w in BITS)
                check('qualification', 'collapsed feedback retains world dependence',
                      warning_law(b, y)[index]*feedback_law(b, y, a, v)[index] == direct)
            check('qualification', 'feedback normalized', sum(feedback_law(b, y, a, v)[index] for v in BITS) == 1)
    for likelihood in [cal_law(x) for x in BITS]+[warning_law(b, y) for b, y in product(BITS, repeat=2)]:
        mass, posterior, _ = update(PRIOR, likelihood)
        for candidate in (PRIOR, posterior):
            direct = sum((dec(p)*(dec(p)/dec(prior*l)).ln() for p, prior, l in zip(candidate, PRIOR, likelihood)), D(0))
            posterior_kl = sum((dec(p)*(dec(p)/dec(post)).ln() for p, post in zip(candidate, posterior)), D(0))
            close('qualification', 'VFE identity', direct, posterior_kl-dec(mass).ln())
    for x in BITS:
        mass, posterior, ig = update(PRIOR, (F(1, 2),)*4)
        check('qualification', 'uninformative calibration', mass == F(1, 2) and posterior == PRIOR and ig == 0)
    for q in (PRIOR, update(PRIOR, cal_law(0))[1], update(PRIOR, cal_law(1))[1]):
        for b, y, v in product(BITS, repeat=3):
            qy = update(q, warning_law(b, y))[1]
            check('qualification', 'fallback feedback carries no sensor information', update(qy, feedback_law(b, y, 0, v))[1] == qy)
    def event_check(q, likelihoods, preferences):
        desired_mass, direct, ce, ig, physical_mass = D(0), D(0), D(0), D(0), F(0)
        for outcome, likelihood in likelihoods.items():
            mass = sum(p*l for p, l in zip(q, likelihood))
            posterior = tuple(p*l/mass for p, l in zip(q, likelihood)) if mass else q
            desired_mass += sum((preferences[outcome]*dec(p) for p in posterior), D(0))
            physical_mass += mass
            if mass:
                ce -= dec(mass)*preferences[outcome].ln()
                for prior, like, post in zip(q, likelihood, posterior):
                    weight = dec(prior*like)
                    direct += weight*(dec(prior)/(dec(post)*preferences[outcome])).ln()
                    ig += weight*(dec(post)/dec(prior)).ln()
        check('qualification', 'conditional physical observation normalization', physical_mass == 1)
        close('qualification', 'desired posterior-factor joint normalized', desired_mass, 1)
        close('qualification', 'conditional EFE derived from normalized joint', direct, ce-ig)
    null_likelihood = (F(0),)*4
    uniform = {o: D(1)/3 for o in (0, 1, None)}
    event_check(PRIOR, {0: cal_law(0), 1: cal_law(1), None: null_likelihood}, uniform)
    event_check(PRIOR, {0: null_likelihood, 1: null_likelihood, None: (F(1),)*4}, uniform)
    weights = {(t, v): D(4*t+2*v).exp() for t, v in product(BITS, repeat=2)}
    weights[None] = D(1)
    pref = {o: weight/sum(weights.values()) for o, weight in weights.items()}
    for b, y, a in product(BITS, repeat=3):
        qy = update(PRIOR, warning_law(b, y))[1]
        likelihoods = {(t, v): tuple(bern(F(3, 4)+F(3, 20)*a, t)*p for p in feedback_law(b, y, a, v))
                       for t, v in product(BITS, repeat=2)}
        likelihoods[None] = null_likelihood
        event_check(qy, likelihoods, pref)
    event_check(PRIOR, {o: (F(1),)*4 if o is None else null_likelihood for o in pref}, pref)
    return dict(vertices=VERTICES, assertions=COUNTS['qualification'])


def enumerate_law(planner, slot, buy):
    joint = defaultdict(lambda: [F(0)]*4)
    replayed = {}
    leaves = 0
    def visit(index, t, q, live, received, probability, history):
        nonlocal leaves
        l = LATENTS[index]
        if t == slot and not received:
            if buy:
                for x in BITS:
                    qx = update(q, cal_law(x))[1]
                    visit(index, t, qx, live, True, probability*cal_law(x)[index], history+(('E', slot, x),))
            else:
                visit(index, t, q, live, True, probability, history+(('E', slot, None),))
            return
        if t == 3:
            leaves += 1
            joint[history][index] += probability
            if history in replayed:
                assert replayed[history] == q
            replayed[history] = q
            return
        if not live:
            visit(index, t+1, q, False, received, probability,
                  history+(('Y', t, None, None), ('F', t, None, None)))
            return
        b, vertex = planner.choice(t, q)
        r = VERTICES[vertex]
        for w, y, a, correct, v in product(BITS, repeat=5):
            pa = bern(r[y], a)
            if not pa:
                continue
            qy = update(q, warning_law(b, y))[1]
            qv = update(qy, feedback_law(b, y, a, v))[1]
            weight = (probability*F(1, 2)*sensor(l, w, b, y)*pa
                      *bern(F(3, 4)+F(3, 20)*a, correct)*bern(1-failure(w, a), v))
            visit(index, t+1, qv, bool(v), received, weight,
                  history+(('C', t, b, vertex), ('Y', t, b, y), ('a', t, a), ('F', t, correct, v)))
    for index in range(4):
        visit(index, 1, PRIOR, True, False, F(1, 4), (('M', buy),))
    return joint, replayed, leaves


def analyze_law(label, joint, replayed, leaves, planner, buy, expected=None):
    mass = sum(sum(row) for row in joint.values())
    check('physical', label+' normalized', mass == 1)
    prefixes = defaultdict(lambda: [F(0)]*4)
    metrics = {key: F(0) for key in ('T1', 'V1', 'T2', 'V2', 'reach2')}
    utility = F(0)
    info = D(0)
    for history, row in joint.items():
        weight = sum(row)
        posterior = tuple(p/weight for p in row)
        check('posterior', label+' direct posterior', posterior == replayed[history])
        check('physical', label+' complete slots', Counter(e[0] for e in history)['E'] == 1
              and Counter(e[0] for e in history)['Y'] == 2 and Counter(e[0] for e in history)['F'] == 2)
        info += sum((dec(p)*(dec(post)/D('.25')).ln() for p, post in zip(row, posterior)), D(0))
        for event in history:
            if event[0] == 'F' and event[2] is not None:
                t, correct, v = event[1:]
                metrics[f'T{t}'] += weight*correct
                metrics[f'V{t}'] += weight*v
                if t == 2:
                    metrics['reach2'] += weight
                utility += weight*(correct+F(v, 2))
        for end in range(len(history)+1):
            bucket = prefixes[history[:end]]
            for index, p in enumerate(row):
                bucket[index] += p
    increments = Counter({'E': D(0), 'Y': D(0), 'F': D(0), 'a': D(0), 'C': D(0), 'M': D(0)})
    for prefix, row in prefixes.items():
        if not prefix:
            continue
        prior_row = prefixes[prefix[:-1]]
        weight, prior_weight = sum(row), sum(prior_row)
        posterior = tuple(p/weight for p in row)
        prior = tuple(p/prior_weight for p in prior_row)
        event = prefix[-1][0]
        increment = sum((dec(p)*(dec(post)/dec(pre)).ln() for p, post, pre in zip(row, posterior, prior)), D(0))
        increments[event] += increment
        if event in ('a', 'C', 'M'):
            check('access', label+' control adds no hidden information', posterior == prior)
    close('information', label+' causal chain', info, sum(increments.values()))
    close('information', label+' entropy identity', info, entropy(PRIOR)-sum(
          (dec(sum(row))*entropy(tuple(p/sum(row) for p in row)) for row in joint.values()), D(0)))
    for event in ('a', 'C', 'M'):
        close('information', label+' zero control information', increments[event], 0)
    value = Value(utility, increments['E'], increments['Y'], increments['F'])
    if expected is not None:
        check('dynamic readback', label+' exact task value', utility == expected.U)
        for index in (1, 2, 3):
            close('dynamic readback', label+' information component', value[index], expected[index])
    pref_weights = {(t, v): D(4*t+2*v).exp() for t, v in product(BITS, repeat=2)}
    pref_weights[None] = D(1)
    zf = sum(pref_weights.values())
    close('preference', label+' feedback normalizer', zf, 1+(1+D(4).exp())*(1+D(2).exp()))
    pref_feedback = {key: value/zf for key, value in pref_weights.items()}
    close('preference', label+' feedback normalization', sum(pref_feedback.values()), 1)
    direct_ce = D(0)
    for history, row in joint.items():
        log_cost = D(2).ln()
        for event in history:
            if event[0] in ('E', 'Y'):
                log_cost += D(3).ln()
            elif event[0] == 'F':
                key = None if event[2] is None else (event[2], event[3])
                log_cost -= pref_feedback[key].ln()
        direct_ce += dec(sum(row))*log_cost
    constant0 = D(2).ln()+3*D(3).ln()+2*zf.ln()
    close('preference', label+' direct observation preference', direct_ce, constant0-4*dec(utility))
    costs = []
    for price in (D(0), D('.0001'), D(3).ln()):
        constant = (1+(-price).exp()).ln()+3*D(3).ln()+2*zf.ln()
        ce = direct_ce-D(2).ln()+(1+(-price).exp()).ln()+price*buy
        efe = ce-info
        close('preference', label+' conditional EFE', efe, constant+price*buy-4*dec(utility)-info)
        costs.append(dict(price=price, preference_surprisal=ce, EFE=efe,
                          net_utility=dec(utility)-price*buy/4))
    used = Counter((event[1], event[2], event[3]) for history in joint for event in history if event[0] == 'C')
    return dict(label=label, kind=planner.kind, buy=buy, **value_record(value), metrics=metrics,
                physical_leaves=leaves, observed_histories=len(joint), prefix_count=len(prefixes),
                control_information={key: increments[key] for key in ('a', 'C', 'M')},
                programs=[dict(task=t, channel=b, vertex=v) for t, b, v in sorted(used)],
                scores=costs, reduced_EFE=-4*dec(utility)-info, reduced_task=-4*dec(utility))


def project_tasks(joint):
    result = defaultdict(lambda: [F(0)]*4)
    for history, row in joint.items():
        h = tuple(e for e in history if e[0] not in ('E', 'M'))
        for index, p in enumerate(row):
            result[h][index] += p
    return dict(result)


def encode(value):
    if isinstance(value, (F, D)):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(v) for v in value]
    return value


def write(path, value):
    path.write_text(json.dumps(encode(value), sort_keys=True, indent=2)+'\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def run(output):
    start, cpu = perf_counter(), process_time()
    started = datetime.now(timezone.utc).isoformat()
    source = Path(__file__).resolve().parent
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
        raise RuntimeError('Mounted external FEP namespace required')
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    def log(message):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(str(message)+'\n')
        print(message, flush=True)
    inputs, preserved = [], []
    try:
        log('Started '+started+'; one process; no prior checker imports')
        for name, expected in PRESERVED.items():
            entry = identity(source/name)
            check('integrity', name, entry['sha256'] == expected)
            preserved.append(entry)
        previous = identity(PREVIOUS/'MANIFEST.json')
        check('integrity', 'previous manifest', previous['sha256'] == '6cb7d16f7fed6976280214c735268d9d5ffcec01bad98643f90d68b1d7dcfdec')
        preserved.append(previous)
        old_manifest = json.loads((PREVIOUS/'MANIFEST.json').read_text())
        for group in ('inputs', 'outputs', 'preserved'):
            for entry in old_manifest[group]:
                check('integrity', 'previous record '+entry['path'], identity(Path(entry['path'])) == entry)
        originals = [source/'FEP_TWO_DECISION_EFE_V1.md', Path(__file__).resolve(),
                     source/'FEP_TERMINAL_ACTION_AUDIT_V1.md', source/'FEP_TERMINAL_ACTION_AUDIT_V1_REPORT.md',
                     source/'FEP_SENSOR_CHANGE_V1.md', PREVIOUS/'MANIFEST.json']
        for path in originals:
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path, output/'inputs'/path.name)
            check('integrity', 'copied '+path.name, identity(output/'inputs'/path.name)['sha256'] == entry['sha256'])
        write(output/'PREPARATION.json', dict(inputs=inputs, preserved=preserved, prior=PRIOR,
              target='Theta,D; transient worlds marginalized; executed controls conditioned on',
              timings=dict(early=1, between=2, late=3), vertices=VERTICES, tolerance=TOL,
              scope='two skip, six purchased, two locked late laws', primary_sources=[
              'https://arxiv.org/html/2004.08128v5#S3', 'https://arxiv.org/html/2001.07203v2#S7']))
        log('Source and scope snapshots sealed before qualification')
        qualification = qualify()
        write(output/'QUALIFICATION.json', qualification)
        log(f'Qualification passed: {qualification["assertions"]} assertions')
        planners, values = {}, {}
        for kind in ('EFE', 'task'):
            jobs = [('skip', 1, 0), ('early', 1, 1), ('between', 2, 1), ('late', 3, 1)]
            for timing, slot, buy in jobs:
                planner = Planner(kind, slot, buy)
                label = f'{kind}_{timing}'
                value = planner.solve(1, PRIOR, True, False)
                planners[label], values[label] = planner, value
                log(f'Planned {label}: {len(planner.nodes)} contexts; U={dec(value.U):.15f}; I={information(value):.15f}')
        write(output/'POLICIES.json', {label: list(planner.nodes.values()) for label, planner in planners.items()})
        planned_counts = {label: len(planner.nodes) for label, planner in planners.items()}
        results, joints = {}, {}
        for label, planner in planners.items():
            joint, replayed, leaves = enumerate_law(planner, planner.slot, planner.buy)
            result = analyze_law(label, joint, replayed, leaves, planner, planner.buy, values[label])
            results[label], joints[label] = result, joint
            write(output/(label+'_JOINT.json'), dict(latent_order=LATENTS, rows=[dict(history=h, joint_mass=row) for h, row in joint.items()]))
            log(f'Read back {label}: {len(joint)} histories, {leaves} physical leaves')
        for kind in ('EFE', 'task'):
            planner = planners[kind+'_skip']
            label = kind+'_locked_late'
            joint, replayed, leaves = enumerate_law(planner, 3, 1)
            result = analyze_law(label, joint, replayed, leaves, planner, 1)
            results[label], joints[label] = result, joint
            write(output/(label+'_JOINT.json'), dict(latent_order=LATENTS, rows=[dict(history=h, joint_mass=row) for h, row in joint.items()]))
            check('late control', kind+' exact marginalized task law', project_tasks(joint) == project_tasks(joints[kind+'_skip']))
            check('late control', kind+' task value unchanged', result['U'] == results[kind+'_skip']['U'])
            check('late control', kind+' positive late calibration information', result['calibration_information'] > 0)
            log(f'Read back {label}: no task-law change; late information={result["calibration_information"]:.15f}')
        comparisons = {}
        for kind in ('EFE', 'task'):
            baseline = results[kind+'_skip']
            for timing in ('early', 'between', 'late'):
                result = results[kind+'_'+timing]
                gain = result['U']-baseline['U']
                delta_info = result['information']-baseline['information']
                boundary = 4*dec(gain)+(delta_info if kind == 'EFE' else 0)
                planned_gain = planners[kind+'_skip'].score(values[kind+'_skip'])-planners[kind+'_'+timing].score(values[kind+'_'+timing])
                close('function', kind+'/'+timing+' purchase boundary', boundary, planned_gain)
                decisions = [dict(price=price, buys=price < boundary,
                                 chosen_net_gain=dec(gain)-price/4 if price < boundary else D(0))
                             for price in (D(0), D('.0001'), D(3).ln())]
                comparisons[kind+'_'+timing] = dict(raw_utility_gain=gain, information_change=delta_info,
                    purchase_threshold=boundary, functional_price_boundary=4*dec(gain),
                    positive_functional_interval=gain > 0, decisions=decisions)
                if kind == 'task':
                    check('function', timing+' nonnegative task information value', gain >= 0)
                    check('function', timing+' task benchmark dominates', result['U'] >= results['EFE_'+timing]['U'])
        check('late control', 'task optimized late receipt has no task value', results['task_late']['U'] == results['task_skip']['U'])
        check('late control', 'task optimized late law unchanged', project_tasks(joints['task_late']) == project_tasks(joints['task_skip']))
        check('late control', 'EFE optimal late score includes locked option',
              comparisons['EFE_late']['purchase_threshold']+TOL >= results['EFE_locked_late']['calibration_information'])
        check('function', 'task skip benchmark dominates', results['task_skip']['U'] >= results['EFE_skip']['U'])
        check('scope', 'all executed contexts were planned before enumeration',
              planned_counts == {label: len(planner.nodes) for label, planner in planners.items()})
        check('scope', 'ten executed laws', len(results) == 10)
        for entry in inputs+preserved:
            check('integrity', 'final '+entry['path'], identity(Path(entry['path'])) == entry)
        summary = dict(assertions=sum(COUNTS.values()), groups=dict(COUNTS), max_decimal_residual=MAX_ERROR,
              executed_laws=len(results), planned_contexts=sum(len(p.nodes) for p in planners.values()),
              decision_contexts=sum(n['event'] == 'decision' for p in planners.values() for n in p.nodes.values()),
              observed_histories=sum(r['observed_histories'] for r in results.values()),
              physical_leaves=sum(r['physical_leaves'] for r in results.values()), selected_operating_price=None)
        write(output/'RESULTS.json', dict(summary=summary, laws=results, comparisons=comparisons))
        finished = datetime.now(timezone.utc).isoformat()
        wall, cpu_seconds = perf_counter()-start, process_time()-cpu
        log(f'PASS: {summary["assertions"]} assertions, max residual {MAX_ERROR}; {wall:.6f} seconds wall')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'MANIFEST.json', dict(status='complete', started_utc=started, finished_utc=finished,
              wall_seconds=wall, cpu_seconds=cpu_seconds, python=platform.python_version(), processes=1,
              inputs=inputs, outputs=outputs, preserved=preserved, summary=summary))
    except Exception:
        log(traceback.format_exc())
        write(output/'FAILURE.json', dict(status='failed', assertions=sum(COUNTS.values()), groups=dict(COUNTS),
              inputs=inputs, preserved=preserved, wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
