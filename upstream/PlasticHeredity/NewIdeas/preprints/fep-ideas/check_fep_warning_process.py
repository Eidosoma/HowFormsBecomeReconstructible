#!/usr/bin/env python3
"""Bounded warning-process audit; all generated records go to the FEP mount."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass, FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback

import check_fep_functional_timing as retained

getcontext().prec = 80
TAU, DELTA, ETA = F(1, 10), F(1, 4), F(1, 2)
TOL = D('1e-65')
INFORMATIVE, UNINFORMATIVE, DEGRADED = (F('.1'), F('.9')), (F('.5'), F('.5')), (F('.1'), F('.8'))
SCHEDULES = ('stop', 'timely', 'late', 'blocked')
COUNTS = Counter()
MAX_RESIDUAL = D(0)
FULL_STATES = tuple((w, z, y, m, a, t, v)
                    for w, z, y, m, a, t, v in product(
                        (0, 1), retained.STATES, (0, 1), (0, 1), (0, 1), (0, 1), (0, 1)))


def check(group, label, condition):
    if not condition:
        raise AssertionError(f'{group}: {label}')
    COUNTS[group] += 1


def dec(x):
    if isinstance(x, D):
        return x
    x = F(x)
    return D(x.numerator)/D(x.denominator)


def close(group, label, a, b):
    global MAX_RESIDUAL
    residual = abs(dec(a)-dec(b))
    MAX_RESIDUAL = max(MAX_RESIDUAL, residual)
    check(group, label, residual < TOL)


def bern(p, bit):
    return p if bit else 1-p


def likelihood(sensor, w, y):
    return bern(sensor[w], y)


def qprob(sensor, y):
    return sum(bern(ETA, w)*likelihood(sensor, w, y) for w in (0, 1))


def posterior(sensor, y):
    return ETA*likelihood(sensor, 1, y)/qprob(sensor, y)


def mean_action(sensor, w, rs):
    return sum(likelihood(sensor, w, y)*rs[y] for y in (0, 1))


def kl(p, q):
    return sum((dec(a)*(dec(a)/dec(b)).ln() for a, b in zip(p, q) if a), D(0))


def action_kl(r):
    return kl((1-r, r), (F('.5'), F('.5')))


def encode(x):
    if isinstance(x, (F, D)):
        return str(x)
    if isinstance(x, tuple):
        return [encode(v) for v in x]
    if isinstance(x, list):
        return [encode(v) for v in x]
    if isinstance(x, dict):
        return {k: encode(v) for k, v in x.items()}
    return x


def packed(x):
    return json.dumps(encode(x), sort_keys=True, separators=(',', ':')).encode()


def digest(x):
    return sha256(packed(x)).hexdigest()


def step(lines, sensor):
    if not lines or not (0 < sensor[0] <= sensor[1] < 1):
        raise ValueError('Require valid local lines and overlapping supplied sensor')
    if any(not (0 < a < TAU and 0 < g <= TAU*(1-a)) for a, g in lines):
        raise ValueError('Invalid inherited risk lines')
    rows = tuple((a, g, g+DELTA*(1-a-g)) for a, g in lines)
    cn = min(F(1), min((TAU-a)/g for a, g, h in rows))
    s = min(F(1), min((TAU-a)/h for a, g, h in rows))
    alpha, beta = sensor
    if alpha == beta:
        return rows, cn, s, F(0), (s, s), F(0), D(0), D(0)
    c, d = (1-beta)/beta, (beta-alpha)/beta
    e0 = min(1-s, s/c, (cn-s)/d)/2
    lo, hi = s-c*e0, s+e0
    bcurv = max(1/(lo*(1-lo)), 1/(hi*(1-hi)))*(qprob(sensor, 0)+qprob(sensor, 1)*c*c)
    ghi = max(g for a, g, h in rows)
    d0 = dec((1-ETA)*d)*(dec(F('.6')-2*ghi)-(dec(s)/dec(1-s)).ln())
    epsilon = min(e0, F(d0/dec(bcurv)))
    rs = (s+epsilon, s-c*epsilon)
    gain_u = (1-ETA)*(F('.15')-ghi/2)*d*epsilon
    margin_j = d0*dec(epsilon)/2
    return rows, cn, s, epsilon, rs, gain_u, margin_j, min(4*dec(gain_u), margin_j)


@dataclass(frozen=True)
class Plan:
    h: F
    pair: tuple
    sensor: tuple
    rows: tuple
    nominal_cap: F
    fallback: F
    epsilon: F
    response: tuple
    raw_gain_lower: F
    fep_gain_lower: D
    incremental_cost_ceiling: D


def make_plan(h, pair, sensor):
    """No actual world/sensor or evaluator input is accepted."""
    local = retained.pair_tables(retained.PRIORS, retained.EDGES,
                                 retained.factors(h), pair, h)
    return Plan(h, pair, sensor, *step(tuple((r['A'], r['G']) for r in local), sensor))


class Process:
    """The observable process; timing is a causal event order, not CPU time."""
    def __init__(self, plan):
        self._plan = plan
        self.mode = None
        self.seen = None
        self.action = None
        self.belief = ETA
        self.vfe_drop = D(0)
        self.trace = [dict(event='prepared', plan_sha256=digest(asdict(plan)),
                           response=plan.response, fallback=plan.fallback, world_belief=ETA)]

    @property
    def plan(self):
        return self._plan

    def choose(self, mode):
        if self.mode is not None or mode not in (0, 1):
            raise ValueError('Purchase mode must be chosen exactly once before evidence')
        self.mode = mode
        self.trace.append(dict(event='purchase_selected', mode=mode))

    def deliver(self, bit):
        if self.mode != 1 or self.seen is not None or bit not in (0, 1):
            raise ValueError('One binary delivery requires a prior purchase')
        self.seen = bit
        self.belief = posterior(self.plan.sensor, bit)
        self.vfe_drop = kl((1-ETA, ETA), (1-self.belief, self.belief))
        self.trace.append(dict(event='warning_delivered', bit=bit,
                               after_commitment=self.action is not None,
                               world_belief=self.belief, model_vfe_drop=self.vfe_drop))

    def commit(self, use_warning):
        if self.mode is None or self.action is not None:
            raise ValueError('One commitment requires a selected purchase mode')
        if use_warning and (self.mode != 1 or self.seen is None):
            raise ValueError('A contingent commitment requires delivered evidence')
        self.action = self.plan.response[self.seen] if use_warning else self.plan.fallback
        self.trace.append(dict(event='action_committed', r=self.action,
                               used_warning=use_warning, world_belief=self.belief))

    def record(self):
        if self.action is None:
            raise ValueError('Cannot seal an uncommitted process')
        return dict(r=self.action, mode=self.mode, observed=self.seen,
                    final_world_belief=self.belief, model_vfe_drop=self.vfe_drop,
                    trace=self.trace)


def replay(plan, schedule, bit):
    process = Process(plan)
    process.choose(int(schedule != 'stop'))
    if schedule == 'stop':
        process.commit(False)
    elif schedule == 'timely':
        process.deliver(bit)
        process.commit(True)
    elif schedule == 'late':
        process.commit(False)
        process.deliver(bit)
    elif schedule == 'blocked':
        process.deliver(bit)
        process.commit(False)
    else:
        raise ValueError('Unknown schedule')
    return process.record()


def evaluate_reference(h, pair):
    """Evaluator-only global posterior; independent of the pair operation."""
    weights = {}
    for z in retained.STATES:
        ts = [h+(TAU-h)*bit for bit in z]
        weights[z] = (ts[0]+ts[1]-ts[0]*ts[1])*(ts[1]+ts[2]-ts[1]*ts[2])/8
    evidence = sum(weights.values())
    pi = {z: p/evidence for z, p in weights.items()}
    i, j = pair
    a = sum(p*(h+(TAU-h)*z[j]) for z, p in pi.items())
    g = sum(p*(h+(TAU-h)*z[i])*(1-h-(TAU-h)*z[j]) for z, p in pi.items())
    return pi, a, g, g+DELTA*(1-a-g)


def full_law(pi, h, pair, sensor, purchase, rs, fixed_world=None):
    law = []
    for w, z, y, m, a, t, v in FULL_STATES:
        pw = bern(ETA, w) if fixed_world is None else F(w == fixed_world)
        f0, f1 = retained.rates(h, z, pair)
        fail = f0 if a == 0 else 1-(1-f1)*(1-DELTA*w)
        prob = (pw*pi[z]*likelihood(sensor, w, y)*bern(purchase, m)*bern(rs[y], a)
                *bern(F('.75')+F('.15')*a, t)*bern(1-fail, v))
        law.append(prob)
    return law


def preference(pi, h, pair, sensor, price=D(0)):
    reference = full_law(pi, h, pair, sensor, F('.5'), (F('.5'), F('.5')))
    weights = [dec(p)*(4*dec(F(s[5])+F(s[6], 2))-price*s[3]).exp()
               for s, p in zip(FULL_STATES, reference)]
    norm = sum(weights, D(0))
    return [w/norm for w in weights], norm


def utility(a, slope, r):
    return F('1.25')+F('.15')*r-(a+slope*r)/2


def outcome(law):
    return dict(risk=sum(p for s, p in zip(FULL_STATES, law) if s[6] == 0),
                correctness=sum(p for s, p in zip(FULL_STATES, law) if s[5]),
                precision=sum(p for s, p in zip(FULL_STATES, law) if s[4]),
                raw_utility=sum(p*(F(s[5])+F(s[6], 2)) for s, p in zip(FULL_STATES, law)))


def qualify():
    start_count = sum(COUNTS.values())
    plan = make_plan(F('.05'), (0, 1), INFORMATIVE)
    cases = {name: [replay(plan, name, bit) for bit in (0, 1)] for name in SCHEDULES}
    for bit in (0, 1):
        check('qualification', 'timely selects frozen entry', cases['timely'][bit]['r'] == plan.response[bit])
        for name in ('stop', 'late', 'blocked'):
            check('qualification', 'constant fallback', cases[name][bit]['r'] == plan.fallback)
        check('qualification', 'same delivered-bit belief', all(cases[name][bit]['final_world_belief'] == posterior(INFORMATIVE, bit) for name in ('timely', 'late', 'blocked')))
    errors = []
    def reject(label, operation):
        try:
            operation()
        except (ValueError, AttributeError, FrozenInstanceError) as exc:
            errors.append(dict(control=label, exception=type(exc).__name__, message=str(exc)))
            check('qualification', label, True)
        else:
            raise AssertionError('Failed to reject: '+label)
    p = Process(plan)
    reject('delivery without purchase', lambda: p.deliver(0))
    p.choose(1)
    reject('contingent commitment without evidence', lambda: p.commit(True))
    p.deliver(0)
    reject('second delivery', lambda: p.deliver(1))
    p.commit(True)
    reject('second commitment', lambda: p.commit(False))
    reject('replace frozen process plan', lambda: setattr(p, 'plan', plan))
    reject('mutate frozen response table', lambda: setattr(plan, 'response', (F(0), F(0))))
    uniform = make_plan(F('.05'), (0, 1), UNINFORMATIVE)
    check('qualification', 'uninformative policy constant', uniform.response == (uniform.fallback,)*2 and uniform.epsilon == 0)
    check('qualification', 'uninformative posterior unchanged', all(posterior(UNINFORMATIVE, y) == ETA for y in (0, 1)))
    pi, a, g, h = evaluate_reference(plan.h, plan.pair)
    pref0, z0 = preference(pi, plan.h, plan.pair, INFORMATIVE)
    price = D(3).ln()
    prefk, zk = preference(pi, plan.h, plan.pair, INFORMATIVE, price)
    close('qualification', 'nonzero price normalization', zk, z0*(1+(-price).exp())/2)
    for mode in (0, 1):
        rs = plan.response if mode else (plan.fallback,)*2
        law = full_law(pi, plan.h, plan.pair, INFORMATIVE, F(mode), rs)
        close('qualification', 'nonzero price coefficient', kl(law, prefk)-kl(law, pref0), price*mode+(zk/z0).ln())
    check('qualification', 'complete state space', len(FULL_STATES) == 512)
    return dict(assertions=sum(COUNTS.values())-start_count, rejected_controls=errors)


def evaluate_policy(plan, branches, pi, a, g, h, pref, norm, actual_sensor):
    rs = tuple(branch['r'] for branch in branches)
    mode = branches[0]['mode']
    check('process', 'same mode before either warning', mode == branches[1]['mode'])
    law = full_law(pi, plan.h, plan.pair, actual_sensor, F(mode), rs)
    check('full joint', 'mixture normalized', sum(law) == 1)
    check('full joint', 'mixture support', sum(p > 0 for p in law) == 256)
    mixture = outcome(law)
    mixture['full_kl_kappa0'] = kl(law, pref)
    mixture['cost_coefficient'] = mode
    mixture['mean_model_vfe_drop'] = sum((dec(qprob(actual_sensor, y))*branches[y]['model_vfe_drop'] for y in (0, 1)), D(0))
    worlds = []
    sensor_kls = []
    for w in (0, 1):
        slope = (g, h)[w]
        r_actual = mean_action(actual_sensor, w, rs)
        r_model = mean_action(plan.sensor, w, rs)
        fixed = full_law(pi, plan.h, plan.pair, actual_sensor, F(mode), rs, w)
        check('full joint', 'fixed world normalized', sum(fixed) == 1)
        check('full joint', 'fixed world support', sum(p > 0 for p in fixed) == 128)
        metrics = outcome(fixed)
        check('physical identities', 'risk from full law', metrics['risk'] == a+slope*r_actual)
        check('physical identities', 'correctness from full law', metrics['correctness'] == F('.75')+F('.15')*r_actual)
        check('physical identities', 'utility from full law', metrics['raw_utility'] == utility(a, slope, r_actual))
        check('physical identities', 'precision from full law', metrics['precision'] == r_actual)
        discrepancy = kl((1-actual_sensor[w], actual_sensor[w]), (1-plan.sensor[w], plan.sensor[w]))
        sensor_kls.append(discrepancy)
        action_cost = sum((dec(likelihood(actual_sensor, w, y))*action_kl(rs[y]) for y in (0, 1)), D(0))
        metrics['j_actual'] = action_cost-4*dec(metrics['raw_utility'])
        metrics['full_kl_kappa0'] = kl(fixed, pref)
        close('full preference identities', 'fixed-world mismatch term', metrics['full_kl_kappa0'],
              -dec(bern(ETA, w)).ln()+D(2).ln()+metrics['j_actual']+norm.ln()+discrepancy)
        model_upper = max(row[0]+row[w+1]*r_model for row in plan.rows)
        per_signal = [dict(y=y, risk=a+slope*rs[y], risk_violation=a+slope*rs[y] > TAU,
                           probability=likelihood(actual_sensor, w, y)) for y in (0, 1)]
        worlds.append(dict(world=('nominal', 'hazard')[w], actual_mean_precision=r_actual,
                           model_mean_precision=r_model, sensor_discrepancy=discrepancy,
                           reported_model_upper=model_upper,
                           certificate_exceeded=metrics['risk'] > model_upper,
                           risk_violation=metrics['risk'] > TAU,
                           per_signal=per_signal,
                           raw_gain_over_economy=metrics['raw_utility']-utility(a, slope, F(0)),
                           **metrics))
    for key in ('risk', 'correctness', 'precision', 'raw_utility'):
        check('physical identities', 'mixture '+key, mixture[key] == sum(bern(ETA, w)*worlds[w][key] for w in (0, 1)))
    action_cost = sum((dec(qprob(actual_sensor, y))*action_kl(rs[y]) for y in (0, 1)), D(0))
    mixture['j_actual'] = action_cost-4*dec(mixture['raw_utility'])
    mixture['sensor_discrepancy'] = sum((dec(bern(ETA, w))*sensor_kls[w] for w in (0, 1)), D(0))
    close('full preference identities', 'mixture mismatch term', mixture['full_kl_kappa0'],
          D(2).ln()+mixture['j_actual']+norm.ln()+mixture['sensor_discrepancy'])
    diagnostics = []
    for y in (0, 1):
        py_model, py_actual = posterior(plan.sensor, y), posterior(actual_sensor, y)
        risk_model = a+(g+py_model*(h-g))*rs[y]
        risk_actual = a+(g+py_actual*(h-g))*rs[y]
        upper = max(ab+(gb+py_model*(hb-gb))*rs[y] for ab, gb, hb in plan.rows)
        check('risk diagnostics', 'model posterior interval', risk_model <= upper)
        diagnostics.append(dict(y=y, actual_probability=qprob(actual_sensor, y),
                                model_conditional_pH=py_model, actual_conditional_pH=py_actual,
                                model_conditional_risk=risk_model, actual_conditional_risk=risk_actual,
                                model_conditional_upper=upper,
                                posterior_predictive_violation=risk_actual > TAU,
                                actual_conditional_bound_exceeded=risk_actual > upper,
                                observed_by_end=branches[y]['observed'] is not None,
                                belief_at_commit=next(e['world_belief'] for e in branches[y]['trace'] if e['event'] == 'action_committed'),
                                belief_at_end=branches[y]['final_world_belief']))
    return dict(actions=rs, mixture=mixture, worlds=worlds, posterior_diagnostics=diagnostics,
                per_world_average_safe=all(not row['risk_violation'] for row in worlds),
                posterior_predictive_safe=all(not row['posterior_predictive_violation'] for row in diagnostics),
                per_world_per_signal_safe=all(not row['risk_violation'] for w in worlds for row in w['per_signal']))


def evaluate_case(record):
    plan = record['plan']
    pi, a, g, h = evaluate_reference(plan.h, plan.pair)
    pref, norm = preference(pi, plan.h, plan.pair, plan.sensor)
    close('full joint', 'preferred joint normalized', sum(pref, D(0)), 1)
    regimes = [('calibrated', plan.sensor)]
    if plan.sensor == INFORMATIVE:
        regimes.append(('degraded', DEGRADED))
    evaluations = []
    for label, actual in regimes:
        policies = {name: evaluate_policy(plan, record['schedules'][name], pi, a, g, h, pref, norm, actual) for name in SCHEDULES}
        baseline = policies['stop']
        for name, policy in policies.items():
            policy['comparison_to_stop'] = dict(
                raw_gain=policy['mixture']['raw_utility']-baseline['mixture']['raw_utility'],
                correctness_gain=policy['mixture']['correctness']-baseline['mixture']['correctness'],
                full_kl_gain_kappa0=baseline['mixture']['full_kl_kappa0']-policy['mixture']['full_kl_kappa0'],
                incremental_cost_coefficient=policy['mixture']['cost_coefficient'])
            if name in ('late', 'blocked') or plan.sensor == UNINFORMATIVE:
                check('controls', 'raw law unchanged', all(policy['mixture'][key] == baseline['mixture'][key] for key in ('risk', 'precision', 'correctness', 'raw_utility')))
                close('controls', 'constant policy same intercept', policy['mixture']['full_kl_kappa0'], baseline['mixture']['full_kl_kappa0'])
                check('controls', 'world outcomes unchanged', all(policy['worlds'][w][key] == baseline['worlds'][w][key] for w in (0, 1) for key in ('risk', 'precision', 'correctness', 'raw_utility')))
        timely = policies['timely']
        change = timely['comparison_to_stop']
        functional = None
        if plan.sensor == INFORMATIVE and label == 'calibrated':
            functional = (timely['per_world_average_safe'] and change['raw_gain'] > 0
                          and change['correctness_gain'] > 0 and change['full_kl_gain_kappa0'] > 0
                          and plan.incremental_cost_ceiling > 0)
            check('calibrated mechanism', 'registered functional criterion', functional)
            check('calibrated mechanism', 'raw gain covers certificate', change['raw_gain'] >= plan.raw_gain_lower > 0)
            check('calibrated mechanism', 'full score covers certificate', change['full_kl_gain_kappa0']+TOL >= plan.fep_gain_lower > 0)
            check('calibrated mechanism', 'hazard outcome law unchanged', all(timely['worlds'][1][key] == baseline['worlds'][1][key] for key in ('risk', 'precision', 'correctness', 'raw_utility')))
        if label == 'degraded':
            expected = plan.fallback+(1-actual[1]/plan.sensor[1])*plan.epsilon
            check('degradation mechanism', 'fixed-rule sensitivity identity', timely['worlds'][1]['actual_mean_precision'] == expected)
            check('degradation mechanism', 'no nominal law change', timely['worlds'][0]['actual_mean_precision'] == mean_action(plan.sensor, 0, plan.response))
        evaluations.append(dict(sensor_condition=label, actual_sensor=actual,
                                calibrated_functional_pass=functional, policies=policies))
    ell_n = F('.15')-max(row[1] for row in plan.rows)/2
    ell_h = F('.15')-max(row[2] for row in plan.rows)/2
    total_cost = (4*min(ell_n*mean_action(plan.sensor, 0, plan.response), ell_h*plan.fallback)
                  if ell_h > 0 else None)
    return dict(agent_id=record['agent_id'], h=plan.h, pair=plan.pair, panel=record['panel'],
                reference=dict(pi=[(z, p) for z, p in pi.items()], A=a, G=g, H=h, Z0=norm),
                total_cost_ceiling_above_economy=total_cost, evaluations=evaluations)


def write(path, value):
    with path.open('w') as handle:
        json.dump(encode(value), handle, indent=2, sort_keys=True)
        handle.write('\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    mount = Path('/mnt/bioIce1')
    base = mount/'fep-ideas/formal-checks/fep-warning-process-v1'
    output = args.output.resolve()
    if not mount.is_mount() or output.parent != base.resolve() or not output.name.startswith('attempt-'):
        raise SystemExit('Require a new attempt on the mounted external FEP study directory')
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing attempt')
    base.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    (output/'inputs').mkdir()
    source_root = Path(__file__).resolve().parent
    source_names = ('FEP_WARNING_PROCESS_V1.md', Path(__file__).name,
                    'FEP_WARNING_EVIDENCE_V1.md', 'FEP_WARNING_EVIDENCE_V1_CHECKS.md',
                    'FEP_FUNCTIONAL_TIMING_V1.md', 'check_fep_functional_timing.py')
    manifest = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                    python=platform.python_version(), processes=1, pid=os.getpid(), inputs=[])
    write(output/'MANIFEST.json', manifest)
    wall, cpu = perf_counter(), process_time()
    with (output/'RUN_LOG.txt').open('x') as log:
        try:
            for name in source_names:
                source = source_root/name
                shutil.copyfile(source, output/'inputs'/name)
                manifest['inputs'].append(identity(source))
            write(output/'MANIFEST.json', manifest)
            log.write('Six source files copied and frozen before qualification.\n')
            log.flush()
            qualification = qualify()
            write(output/'QUALIFICATION.json', qualification)
            log.write(json.dumps(qualification)+'\n')
            log.flush()
            records = []
            for h in (F('1e-6'), F('.01')):
                for pair in retained.QUERIES:
                    for panel, sensor in (('informative', INFORMATIVE), ('uninformative', UNINFORMATIVE)):
                        plan = make_plan(h, pair, sensor)
                        before = digest(asdict(plan))
                        schedules = {name: [replay(plan, name, y) for y in (0, 1)] for name in SCHEDULES}
                        check('process', 'plan immutable across all traces', before == digest(asdict(plan)))
                        for y in (0, 1):
                            check('process', 'one common table before each signal', all(schedules[name][y]['trace'][0]['plan_sha256'] == before for name in SCHEDULES))
                            check('process', 'same posterior across delivery schedules', all(schedules[name][y]['final_world_belief'] == posterior(sensor, y) for name in ('timely', 'late', 'blocked')))
                            check('process', 'no-purchase retains prior', schedules['stop'][y]['final_world_belief'] == ETA)
                        for w in (0, 1):
                            check('agent certificate', 'model per-world safety', all(row[0]+row[w+1]*mean_action(sensor, w, plan.response) <= TAU for row in plan.rows))
                        records.append(dict(agent_id=len(records), panel=panel, plan=plan, schedules=schedules))
            serialized = [dict(agent_id=r['agent_id'], panel=r['panel'],
                               plan=asdict(r['plan']), schedules=r['schedules'],
                               Q_z='uniform product, unchanged', local_weight_evaluations=8) for r in records]
            write(output/'AGENT_RECORDS.json', serialized)
            sealed = identity(output/'AGENT_RECORDS.json')['sha256']
            log.write('All 16 agent preparations and 128 traces sealed before exact main references: '+sealed+'\n')
            log.flush()
            results = []
            for record in records:
                results.append(evaluate_case(record))
                log.write(f"Evaluated agent {record['agent_id']} ({record['panel']}).\n")
                log.flush()
            check('record integrity', 'agent seal unchanged', identity(output/'AGENT_RECORDS.json')['sha256'] == sealed)
            for entry in manifest['inputs']:
                check('record integrity', 'source unchanged', identity(Path(entry['path']))['sha256'] == entry['sha256'])
            calibrated = [r['evaluations'][0] for r in results if r['panel'] == 'informative']
            degraded = [r['evaluations'][1] for r in results if r['panel'] == 'informative']
            policies = [p for r in results for e in r['evaluations'] for p in e['policies'].values()]
            worlds = [w for p in policies for w in p['worlds']]
            check('record integrity', 'complete registered scope', len(records) == 16 and len(policies) == 96 and len(worlds) == 192)
            summary = dict(status='PASS', base_problems=8, agent_preparations=16, branch_traces=128,
                           mixture_policy_evaluations=96, world_policy_evaluations=192,
                           calibrated_functional_passes=sum(e['calibrated_functional_pass'] for e in calibrated),
                           calibrated_timely_posterior_predictive_failures=sum(not e['policies']['timely']['posterior_predictive_safe'] for e in calibrated),
                           calibrated_timely_per_world_per_signal_failures=sum(not e['policies']['timely']['per_world_per_signal_safe'] for e in calibrated),
                           degraded_timely_primary_failures=sum(not e['policies']['timely']['per_world_average_safe'] for e in degraded),
                           degraded_timely_posterior_predictive_failures=sum(not e['policies']['timely']['posterior_predictive_safe'] for e in degraded),
                           degraded_timely_certificate_exceedances=sum(e['policies']['timely']['worlds'][1]['certificate_exceeded'] for e in degraded),
                           fallback_primary_failures=sum(w['risk_violation'] for r in results for e in r['evaluations'] for name, p in e['policies'].items() if name != 'timely' for w in p['worlds']),
                           assertions=sum(COUNTS.values()), assertion_groups=dict(COUNTS),
                           retained_helper_assertions=retained.CHECKS,
                           max_decimal_residual=MAX_RESIDUAL, selected_operating_price=None)
            write(output/'RESULTS.json', dict(summary=summary, cases=results))
            log.write(json.dumps(encode(summary))+'\n')
            manifest.update(status='complete', summary=summary)
        except BaseException:
            manifest.update(status='failed', assertions=sum(COUNTS.values()), assertion_groups=dict(COUNTS))
            log.write(traceback.format_exc())
            raise
        finally:
            manifest.update(wall_seconds=perf_counter()-wall, cpu_seconds=process_time()-cpu,
                            finished_utc=datetime.now(timezone.utc).isoformat())
            log.write(f"Status: {manifest['status']}; wall {manifest['wall_seconds']:.6f}s; CPU {manifest['cpu_seconds']:.6f}s\n")
            log.flush()
            manifest['outputs'] = [identity(p) for p in sorted(output.rglob('*'))
                                   if p.is_file() and p.name != 'MANIFEST.json']
            write(output/'MANIFEST.json', manifest)
    print(json.dumps(encode(dict(output=str(output), status=manifest['status'], summary=manifest.get('summary'),
                                wall_seconds=manifest['wall_seconds'])), indent=2))


if __name__ == '__main__':
    main()
