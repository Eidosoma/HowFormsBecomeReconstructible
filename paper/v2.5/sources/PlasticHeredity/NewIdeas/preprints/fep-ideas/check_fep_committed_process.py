#!/usr/bin/env python3
"""Finite committed FEP process; generated files only on the external FEP mount."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass, FrozenInstanceError, is_dataclass
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

getcontext().prec = 80
BITS = (0, 1)
HIDDEN = tuple(product(BITS, repeat=2))
STATES = tuple(product(BITS, repeat=9))
SCHEDULES = ('timely', 'late', 'blocked', 'frozen')
A, BN, BH, TAU, S = F(2, 25), F(3, 50), F(11, 40), F(1, 10), F(4, 55)
TOL, RESIDUAL = D('1e-65'), D(0)
COUNTS = Counter()
PRESERVED = {
    'FEP_ACTION_SELECTION_AUDIT_V1.md': 'dc13f56393252d07a868e265c31bf623e07bc12afc47162b9553d00293e08c3f',
    'FEP_ACTION_SELECTION_AUDIT_V1_CHECKS.md': '7042d3b766967e2112ec4efaf197de433e7039d849260138678c9dcd3efe7d8c',
    'FEP_ACTIVE_SENSOR_CHOICE_V1.md': '3f04062b757d78ddafb25ec213e3a8275e767cc1267e2e1020de4f7fa82e6fb4',
    'FEP_ACTIVE_SENSOR_CHOICE_V1_CHECKS.md': '8812f5607b4ad097c6ab3a8ac54186dd2a6306033159a340dcd0b4701d7f5302',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md': '402480808b61ad9718d38fa0f6f494f2c01819b807491cb386fdde89eb5b76f0',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md': 'fdabe647e938aa4c6b3e828447b4c0162e3ee32644581505776d819889c11d9c',
}


def dec(x):
    return D(x.numerator)/D(x.denominator) if isinstance(x, F) else D(x)


def check(group, label, condition):
    if not condition:
        raise AssertionError(f'{group}: {label}')
    COUNTS[group] += 1


def close(group, label, x, y):
    global RESIDUAL
    error = abs(dec(x)-dec(y))
    RESIDUAL = max(RESIDUAL, error)
    check(group, label, error <= TOL)


def bern(p, bit):
    return p if bit else 1-p


def kl(q, p):
    return sum((dec(a)*(dec(a)/dec(b)).ln() for a, b in zip(q, p) if a), D(0))


def k(r):
    return kl((r, 1-r), (F(1, 2), F(1, 2)))


def logit(r):
    return (dec(r)/(1-dec(r))).ln()


def calibration(th, x):
    return bern(F(9, 10) if th else F(4, 5), x)


def warning(th, w, b, y, drift=False):
    good = th != b
    alarm = (F(9, 10) if good else (F(3, 5) if drift else F(4, 5))) if w else (F(1, 10) if good else F(1, 5))
    return bern(alarm, y)


def risk(w, r):
    return A+(BH if w else BN)*r


def encode(obj):
    if is_dataclass(obj):
        return encode(asdict(obj))
    if isinstance(obj, (D, F)):
        return str(obj)
    if isinstance(obj, dict):
        return {str(key): encode(value) for key, value in obj.items()}
    if isinstance(obj, (tuple, list)):
        return [encode(value) for value in obj]
    return obj


def digest(obj):
    return sha256(json.dumps(encode(obj), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Response:
    quality: F
    r: tuple
    utility: F
    loss: D


@dataclass(frozen=True)
class Rule:
    lambda_a: F
    channel: int
    response: tuple
    utility: F
    loss: D


@dataclass(frozen=True)
class Library:
    responses: tuple
    prior: Rule
    after: tuple
    gain: D
    utility_gain: F


def prepare():
    """No realized observation, hidden world or physical drift is an input."""
    responses = []
    for t in (F(1, 3), F(2, 3), F(8, 17), F(9, 17), F(1, 2)):
        beta = F(4, 5)+t/10
        c0 = (beta*F(3, 25)+(1-beta)*F(1, 80))/2
        c1 = ((1-beta)*F(3, 25)+beta*F(1, 80))/2
        c = c0-c1/4
        def derivative(e):
            return logit(dec(S)+e)/2-logit(dec(S)-e/4)/8-4*dec(c)
        lo, hi = D(0), 4*dec(S)
        check('preparation', 'interior root exists', derivative(lo) < 0)
        for _ in range(320):
            mid = (lo+hi)/2
            if derivative(mid) > 0:
                hi = mid
            else:
                lo = mid
        e = F((lo+hi)/2)
        r0, r1 = S+e, S-e/4
        multiplier = -(logit(r0)/2-4*dec(c0))/dec(F(1, 5))
        close('preparation', 'root stationarity', derivative(dec(e)), 0)
        close('preparation', '2D KKT stationarity', logit(r1)/2-4*dec(c1)+multiplier*dec(F(4, 5)), 0)
        check('preparation', 'complete robust feasibility', multiplier > 0 and 0 < r1 < r0 < 1
              and F(9, 10)*r0+r1/10 < F(1, 3) and F(4, 5)*r0+r1/5 < F(1, 3)
              and r0/5+F(4, 5)*r1 == S and r0/10+F(9, 10)*r1 < S)
        utility = F(5, 4)-A/2+F(53, 800)*S+c*e
        responses.append(Response(t, (r0, r1), utility, (k(r0)+k(r1))/2-4*dec(utility)))
    indexed = {r.quality: r for r in responses}
    def choose(lmb):
        b = int(indexed[1-lmb].loss < indexed[lmb].loss)
        r = indexed[1-lmb if b else lmb]
        return Rule(lmb, b, r.r, r.utility, r.loss)
    prior = choose(F(1, 2))
    after = (choose(F(1, 3)), choose(F(9, 17)))
    gain = prior.loss-dec(F(3, 20))*after[0].loss-dec(F(17, 20))*after[1].loss
    gu = F(3, 20)*after[0].utility+F(17, 20)*after[1].utility-prior.utility
    check('preparation', 'conditional choices', prior.channel == 0 and tuple(r.channel for r in after) == (1, 0))
    check('preparation', 'useful acquisition interval', 0 < gain < 4*dec(gu))
    return Library(tuple(responses), prior, after, gain, gu)


@dataclass(frozen=True)
class Plan:
    library: Library
    expected: str
    price: D
    override: str
    expected_gain: D
    purchase: int


def make_plan(library, expected, price, override='optimized'):
    if expected not in SCHEDULES or price < 0 or override not in ('optimized', 'buy', 'skip'):
        raise ValueError('Invalid declared preparation')
    gain = library.gain if expected == 'timely' else D(0)
    m = int(price < gain) if override == 'optimized' else int(override == 'buy')
    return Plan(library, expected, price, override, gain, m)


def plan_record(plan):
    return dict(expected=plan.expected, price=plan.price, override=plan.override,
                expected_gain=plan.expected_gain, purchase=plan.purchase,
                library_sha256=digest(plan.library))


class Process:
    def __init__(self, plan):
        self._plan = plan
        self._rule = None
        self.m = self.x = self.y = self.r = None
        self.q = (F(1, 4),)*4
        self.available_x = None
        self.at_response = None
        self.events = [dict(event='prepared', plan_sha256=digest(plan_record(plan)), belief=self.q)]

    @property
    def plan(self):
        return self._plan

    @property
    def rule(self):
        return self._rule

    def choose_purchase(self):
        if self.m is not None:
            raise ValueError('Purchase may be selected only once')
        self.m = self.plan.purchase
        self.events.append(dict(event='purchase_selected', purchase=self.m))

    def _update(self, likelihood):
        raw = tuple(p*l for p, l in zip(self.q, likelihood))
        evidence = sum(raw)
        posterior = tuple(p/evidence for p in raw)
        decrease = kl(self.q, posterior)
        self.q = posterior
        return evidence, decrease

    def deliver_calibration(self, x):
        if self.m != 1 or self.x is not None or x not in BITS:
            raise ValueError('Single binary calibration requires purchase')
        evidence, decrease = self._update(tuple(calibration(th, x) for th, w in HIDDEN))
        self.x = x
        self.events.append(dict(event='calibration_delivered', bit=x, after_response=self.r is not None,
                                evidence=evidence, vfe_decrease=decrease, belief=self.q))

    def commit_channel(self):
        if self.m is None or self.rule is not None:
            raise ValueError('Channel commitment requires purchase selection and occurs once')
        use = self.x is not None and self.plan.expected != 'frozen'
        self._rule = self.plan.library.after[self.x] if use else self.plan.library.prior
        self.available_x = self.x
        self.events.append(dict(event='channel_committed', available_x=self.x, used_calibration=use,
                                channel=self.rule.channel, response=self.rule.response, belief=self.q))

    def deliver_warning(self, y):
        if self.rule is None or self.y is not None or y not in BITS:
            raise ValueError('Single binary main warning requires committed channel')
        evidence, decrease = self._update(tuple(warning(th, w, self.rule.channel, y) for th, w in HIDDEN))
        self.y = y
        self.events.append(dict(event='warning_delivered', bit=y, evidence=evidence,
                                vfe_decrease=decrease, belief=self.q))

    def commit_response(self):
        if self.y is None or self.r is not None:
            raise ValueError('Single response commitment requires main warning')
        self.r = self.rule.response[self.y]
        self.at_response = dict(channel=self.rule.channel, response=self.rule.response,
                                r=self.r, belief=self.q)
        self.events.append(dict(event='response_committed', **self.at_response))

    def record(self):
        if self.r is None:
            raise ValueError('Cannot seal an incomplete process')
        return dict(purchase=self.m, available_x=self.available_x, observed_x=self.x,
                    channel=self.rule.channel, response=self.rule.response, r=self.r,
                    belief_at_response=self.at_response['belief'], final_belief=self.q,
                    events=self.events)


def replay(plan, actual, x, y):
    if actual not in SCHEDULES:
        raise ValueError('Unknown physical delivery schedule')
    process = Process(plan)
    process.choose_purchase()
    if process.m and actual in ('timely', 'frozen'):
        process.deliver_calibration(x)
    process.commit_channel()
    process.deliver_warning(y)
    process.commit_response()
    locked = digest(process.at_response)
    if process.m and actual == 'late':
        process.deliver_calibration(x)
    check('process', 'committed action remains fixed', digest(process.at_response) == locked
          and process.r == process.at_response['r'] and process.rule.response == process.at_response['response'])
    record = process.record()
    check('process', 'both qualities remain supported', all(p > 0 for p in record['final_belief']))
    return dict(x=x, y=y, **record)


def qualify(library):
    before, start = sum(COUNTS.values()), perf_counter()
    rejected = []
    def reject(label, fn):
        try:
            fn()
        except (ValueError, AttributeError, FrozenInstanceError) as exc:
            rejected.append(dict(label=label, exception=type(exc).__name__, message=str(exc)))
            check('qualification', label, True)
        else:
            raise AssertionError('Invalid event was accepted: '+label)
    plan = make_plan(library, 'timely', D('0.0001'))
    p = Process(plan)
    reject('calibration before purchase', lambda: p.deliver_calibration(0))
    reject('channel before purchase', p.commit_channel)
    reject('warning before channel', lambda: p.deliver_warning(0))
    reject('response before warning', p.commit_response)
    p.choose_purchase()
    reject('repeated purchase', p.choose_purchase)
    reject('invalid calibration bit', lambda: p.deliver_calibration(2))
    p.deliver_calibration(0)
    reject('repeated calibration', lambda: p.deliver_calibration(1))
    p.commit_channel()
    reject('repeated channel commitment', p.commit_channel)
    reject('replace frozen plan', lambda: setattr(p, 'plan', plan))
    reject('mutate frozen response table', lambda: setattr(p.rule, 'response', (F(0), F(0))))
    p.deliver_warning(0)
    reject('repeated warning', lambda: p.deliver_warning(1))
    p.commit_response()
    reject('repeated response', p.commit_response)
    check('qualification', 'below acquisition boundary', make_plan(library, 'timely', library.gain/2).purchase == 1)
    check('qualification', 'at acquisition boundary', make_plan(library, 'timely', library.gain).purchase == 0)
    check('qualification', 'above acquisition boundary', make_plan(library, 'timely', 2*library.gain).purchase == 0)
    cases = {name: {(x, y): replay(make_plan(library, name, D('0.0001'), 'buy'), name, x, y)
                    for x, y in product(BITS, repeat=2)} for name in SCHEDULES}
    for x, y in product(BITS, repeat=2):
        late, frozen = cases['late'][x, y], cases['frozen'][x, y]
        check('qualification', 'late and frozen infer same joint posterior', late['final_belief'] == frozen['final_belief'])
        check('qualification', 'late and frozen preserve prior action', late['r'] == frozen['r'] == library.prior.response[y])
        check('qualification', 'timely uses correct conditional channel', cases['timely'][x, y]['channel'] == 1-x)
        check('qualification', 'late improves belief without changing action', late['final_belief'] != late['belief_at_response'])
    return dict(status='PASS', assertions=sum(COUNTS.values())-before,
                rejected=rejected, seconds=perf_counter()-start)


def preparations(library):
    cases = []
    def add(name, expected, actual, price, override='optimized'):
        plan = make_plan(library, expected, price, override)
        traces = [replay(plan, actual, x, y) for x, y in product(BITS, repeat=2)]
        for y in BITS:
            left, right = [r for r in traces if r['y'] == y]
            if not plan.purchase or actual == 'blocked':
                check('access', 'inaccessible X changes no event or decision', left['events'] == right['events'])
            if actual == 'late':
                check('access', 'late X cannot alter response', left['r'] == right['r'] == library.prior.response[y])
        cases.append(dict(case_id=name, plan=plan_record(plan), actual=actual, traces=traces))
    for label, price in (('free', D(0)), ('witness', D('0.0001')), ('costly', D(3).ln())):
        for schedule in SCHEDULES:
            add(f'optimized-{schedule}-{label}', schedule, schedule, price)
    for schedule in SCHEDULES:
        add(f'forced-{schedule}', schedule, schedule, D('0.0001'), 'buy')
    add('forced-skip', 'timely', 'timely', D('0.0001'), 'skip')
    for schedule in ('late', 'blocked'):
        add(f'unexpected-{schedule}', 'timely', schedule, D('0.0001'))
    check('record', 'registered scope', len(cases) == 19 and sum(len(c['traces']) for c in cases) == 76)
    return cases


def preferred(price):
    raw = []
    for th, w, x, m, b, y, a, t, v in STATES:
        base = F(1, 32)*calibration(th, x)*warning(th, w, b, y)
        base *= bern(F(3, 4)+F(3, 20)*a, t)*bern(1-risk(w, a), v)
        raw.append(dec(base)*(4*dec(F(t)+F(v, 2))-price*m).exp())
    z = sum(raw, D(0))
    preferred_law = tuple(p/z for p in raw)
    close('normalization', 'preferred law', sum(preferred_law), 1)
    return z, preferred_law


def evaluate(case, drift, reference, actual=None):
    traces = {(r['x'], r['y']): r for r in case['traces']}
    m, price = case['plan']['purchase'], case['plan']['price']
    z, target = reference
    mass, utility, correct, failure = F(0), F(0), F(0), F(0)
    direct, response_kl, discrepancy = D(0), D(0), D(0)
    for state, pref in zip(STATES, target):
        th, w, x, mm, b, y, a, t, v = state
        trace = traces[x, y]
        if mm != m or b != trace['channel']:
            continue
        prob = F(1, 4) if actual is None else F((th, w) == actual)
        prob *= calibration(th, x)*warning(th, w, b, y, drift)*bern(trace['r'], a)
        prob *= bern(F(3, 4)+F(3, 20)*a, t)*bern(1-risk(w, a), v)
        if not prob:
            continue
        mass += prob
        utility += prob*(F(t)+F(v, 2))
        correct += prob*t
        failure += prob*(1-v)
        direct += dec(prob)*(dec(prob)/pref).ln()
    reduced_u, reduced_t, reduced_r = F(0), F(0), F(0)
    for th, w, x, y in product(BITS, repeat=4):
        trace = traces[x, y]
        b, r = trace['channel'], trace['r']
        weight = F(1, 4) if actual is None else F((th, w) == actual)
        weight *= calibration(th, x)*warning(th, w, b, y, drift)
        rr, tt = risk(w, r), F(3, 4)+F(3, 20)*r
        reduced_t += weight*tt
        reduced_r += weight*rr
        reduced_u += weight*(tt+(1-rr)/2)
        response_kl += dec(weight)*k(r)
        discrepancy += dec(weight)*(dec(warning(th, w, b, y, drift))/dec(warning(th, w, b, y))).ln()
    check('full joint', 'exact normalization and physical outcomes', mass == 1 and utility == reduced_u and correct == reduced_t and failure == reduced_r)
    reduced_j = 2*D(2).ln()+response_kl-4*dec(utility)+price*m+discrepancy
    close('full joint', 'complete KL and fixed-world offset', direct, reduced_j+z.ln()+(D(4).ln() if actual is not None else 0))
    return dict(actual=actual, utility=utility, correctness=correct, risk=failure,
                net_utility=dec(utility)-price*m/4, response_KL=response_kl,
                warning_KL=discrepancy, reduced_J=reduced_j, full_KL=direct)


def diagnostics(case, drift):
    histories, per_signal = {}, []
    for th, w in HIDDEN:
        groups = {}
        for trace in case['traces']:
            x, y, b, r = trace['x'], trace['y'], trace['channel'], trace['r']
            weight = calibration(th, x)*warning(th, w, b, y, drift)
            key = trace['available_x']
            numerator, mass = groups.get(key, (F(0), F(0)))
            groups[key] = numerator+weight*risk(w, r), mass+weight
            if not any(row['theta'] == th and row['world'] == w and row['history_x'] == key and row['y'] == y for row in per_signal):
                per_signal.append(dict(theta=th, world=w, history_x=key, y=y, risk=risk(w, r)))
        for hx, (num, mass) in groups.items():
            histories[th, w, hx] = num/mass
    primary = [dict(theta=th, world=w, history_x=hx, risk=value) for (th, w, hx), value in histories.items()]
    predictive = []
    for trace in case['traces']:
        hx, y = trace['available_x'], trace['y']
        if any(row['history_x'] == hx and row['y'] == y for row in predictive):
            continue
        q = [F(1, 4)*(calibration(th, hx) if hx is not None else 1)*warning(th, w, trace['channel'], y, drift) for th, w in HIDDEN]
        q = [p/sum(q) for p in q]
        agent = sum(p*risk(w, trace['r']) for p, (th, w) in zip(trace['belief_at_response'], HIDDEN))
        true = sum(p*risk(w, trace['r']) for p, (th, w) in zip(q, HIDDEN))
        if not drift:
            check('belief calibration', 'nominal posterior prediction', agent == true)
        predictive.append(dict(history_x=hx, y=y, agent_risk=agent, actual_risk=true))
    return dict(primary=primary, primary_safe=all(r['risk'] <= TAU for r in primary),
                primary_failures=sum(r['risk'] > TAU for r in primary), primary_cases=len(primary),
                primary_max=max(r['risk'] for r in primary), per_signal=per_signal,
                signal_failures=sum(r['risk'] > TAU for r in per_signal), signal_cases=len(per_signal),
                signal_max=max(r['risk'] for r in per_signal), predictive=predictive,
                predictive_agent_failures=sum(r['agent_risk'] > TAU for r in predictive),
                predictive_actual_failures=sum(r['actual_risk'] > TAU for r in predictive))


def write(path, data):
    with path.open('w') as handle:
        json.dump(encode(data), handle, indent=2, sort_keys=True)
        handle.write('\n')


def identity(path):
    content = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(content), sha256=sha256(content).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    mount = Path('/mnt/bioIce1')
    base = mount/'fep-ideas/formal-checks/fep-committed-process-v1'
    output = args.output.resolve()
    if not mount.is_mount() or output.parent != base.resolve() or not output.name.startswith('attempt-'):
        raise SystemExit('Require a fresh attempt under the mounted external FEP study directory')
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing attempt')
    base.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    (output/'inputs').mkdir()
    source = Path(__file__).resolve().parent
    names = ('FEP_COMMITTED_PROCESS_V1.md', Path(__file__).name, 'audit_fep_committed_process.py',
             'FEP_ACTION_SELECTION_AUDIT_V1.md', 'FEP_ACTION_SELECTION_AUDIT_V1_CHECKS.md',
             'FEP_ACTIVE_SENSOR_CHOICE_V1.md', 'FEP_ACTIVE_SENSOR_CHOICE_V1_CHECKS.md')
    manifest = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                    python=platform.python_version(), processes=1, pid=os.getpid(), inputs=[], preserved=[])
    write(output/'MANIFEST.json', manifest)
    wall, cpu = perf_counter(), process_time()
    with (output/'RUN_LOG.txt').open('x') as log:
        try:
            for name in names:
                shutil.copyfile(source/name, output/'inputs'/name)
                manifest['inputs'].append(identity(source/name))
            for name, expected in PRESERVED.items():
                entry = identity(source/name)
                check('integrity', 'preserved '+name, entry['sha256'] == expected)
                manifest['preserved'].append(entry)
            write(output/'MANIFEST.json', manifest)
            log.write('Seven source files frozen; six prior identities checked.\n')
            log.flush()
            library = prepare()
            qualification = qualify(library)
            write(output/'QUALIFICATION.json', qualification)
            log.write('Qualification: '+json.dumps(encode(qualification))+'\n')
            log.flush()
            before = digest(library)
            cases = preparations(library)
            check('record', 'immutable library after all traces', digest(library) == before)
            write(output/'AGENT_RECORDS.json', dict(library=library, library_sha256=before, cases=cases))
            sealed = identity(output/'AGENT_RECORDS.json')['sha256']
            log.write('All 19 preparations and 76 traces sealed before main physical evaluation: '+sealed+'\n')
            log.flush()
            references = {price: preferred(price) for price in (D(0), D('0.0001'), D(3).ln())}
            for price, (z, law) in references.items():
                close('normalization', 'symbolic cost normalizer', z, references[D(0)][0]*(1+(-price).exp())/2)
            results = []
            for case in cases:
                for drift in (False, True):
                    ref = references[case['plan']['price']]
                    result = dict(case_id=case['case_id'], drift=drift,
                                  mixture=evaluate(case, drift, ref),
                                  worlds=[evaluate(case, drift, ref, actual) for actual in HIDDEN],
                                  diagnostics=diagnostics(case, drift))
                    results.append(result)
                log.write('Evaluated '+case['case_id']+' under both physical laws.\n')
                log.flush()
            nominal = {r['case_id']: r for r in results if not r['drift']}
            baseline = nominal['forced-skip']['mixture']
            acquired = nominal['forced-timely']['mixture']
            close('function', 'retained learning utility', acquired['utility']-baseline['utility'], library.utility_gain)
            close('function', 'retained learning score', baseline['reduced_J']-acquired['reduced_J'], library.gain-D('0.0001'))
            check('function', 'timely correctness and continuation improve', acquired['correctness'] > baseline['correctness'] and acquired['risk'] < baseline['risk'])
            for case in cases:
                result = nominal[case['case_id']]
                check('primary safety', 'nominal per-world history requirement', result['diagnostics']['primary_safe'])
                usable = bool(case['plan']['purchase'] and case['actual'] == 'timely')
                expected_gain = library.utility_gain if usable else F(0)
                close('function', 'physical timing and cost identity', result['mixture']['net_utility']-baseline['net_utility'], dec(expected_gain)-case['plan']['price']*case['plan']['purchase']/4)
            for entry in manifest['inputs']+manifest['preserved']:
                check('integrity', 'source unchanged '+entry['path'], identity(Path(entry['path'])) == entry)
            check('integrity', 'agent record unchanged', identity(output/'AGENT_RECORDS.json')['sha256'] == sealed)
            summary = dict(status='PASS', preparations=len(cases), traces=sum(len(c['traces']) for c in cases),
                           mixture_evaluations=len(results), fixed_world_evaluations=4*len(results),
                           full_joint_comparisons=5*len(results), assertions=sum(COUNTS.values()),
                           groups=dict(COUNTS), max_decimal_residual=RESIDUAL,
                           nominal_primary_safe=sum(r['diagnostics']['primary_safe'] for r in results if not r['drift']),
                           drift_primary_unsafe=sum(not r['diagnostics']['primary_safe'] for r in results if r['drift']),
                           gain=library.gain, utility_gain=library.utility_gain, selected_operating_price=None)
            write(output/'RESULTS.json', dict(summary=summary, normalizers={str(p): z for p, (z, _) in references.items()}, evaluations=results))
            manifest.update(status='complete', summary=summary)
        except BaseException:
            manifest.update(status='failed', assertions=sum(COUNTS.values()), groups=dict(COUNTS))
            log.write(traceback.format_exc())
            raise
        finally:
            manifest.update(finished_utc=datetime.now(timezone.utc).isoformat(),
                            wall_seconds=perf_counter()-wall, cpu_seconds=process_time()-cpu)
            log.write('Final: '+json.dumps(encode(manifest))+'\n')
            log.flush()
            manifest['outputs'] = [identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
            write(output/'MANIFEST.json', manifest)
    print(json.dumps(encode(dict(output=str(output), status=manifest['status'], summary=manifest['summary'],
                                wall_seconds=manifest['wall_seconds'])), indent=2))


if __name__ == '__main__':
    main()
