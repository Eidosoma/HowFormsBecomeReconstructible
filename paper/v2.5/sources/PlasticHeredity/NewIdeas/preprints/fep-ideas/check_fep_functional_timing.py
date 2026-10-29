#!/usr/bin/env python3
"""Exact finite timing/model-adequacy audit; writes only to the external record."""
import argparse
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
TAU, HAZARD = F(1, 10), F(1, 4)
TOL, PAD = D('1e-60'), D('1e-50')
EDGES = ((0, 1), (1, 2))
QUERIES = ((0, 1), (1, 0), (1, 2), (2, 1))
STATES = tuple(product((0, 1), repeat=3))
PRIORS = ((F(1, 2), F(1, 2)),) * 3
CHECKS = 0


def check(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(label)


def dec(x):
    if isinstance(x, D):
        return x
    x = F(x)
    return D(x.numerator) / D(x.denominator)


def close(a, b, label):
    check(abs(dec(a)-dec(b)) < TOL, label)


def kl(p, q):
    return sum((dec(a)*(dec(a)/dec(b)).ln()
                for a, b in zip(p, q) if a), D(0))


def bern(p, bit):
    return p if bit else 1-p


def rates(h, z, pair):
    i, j = pair
    ti, tj = h+(TAU-h)*z[i], h+(TAU-h)*z[j]
    return tj, ti+tj-ti*tj


def factors(h):
    table = tuple(tuple((h+(TAU-h)*i)+(h+(TAU-h)*j)
                        -(h+(TAU-h)*i)*(h+(TAU-h)*j)
                        for j in (0, 1)) for i in (0, 1))
    return (table, table)


def pair_tables(priors, edges, fs, pair, h):
    """Agent operation: local factors only; no reference or world argument."""
    i, j = pair
    boundary = next(k for k in range(3) if k not in pair)
    rows = []
    for bit in (0, 1):
        weights = []
        for zi, zj in product((0, 1), repeat=2):
            z = [0, 0, 0]
            z[i], z[j], z[boundary] = zi, zj, bit
            weight = priors[i][zi]*priors[j][zj]
            for (a, b), table in zip(edges, fs):
                if a in pair or b in pair:
                    weight *= table[z[a]][z[b]]
            weights.append((tuple(z), weight))
        total = sum(w for _, w in weights)
        check(total > 0, 'positive local normalizer')
        eta = [(z, w/total) for z, w in weights]
        a = sum(p*rates(h, z, pair)[0] for z, p in eta)
        g = sum(p*(rates(h, z, pair)[1]-rates(h, z, pair)[0]) for z, p in eta)
        rows.append(dict(boundary=boundary, bit=bit, eta=eta, A=a, G=g))
    return rows


def action(lines):
    if not lines or any(a < 0 or a > TAU or g <= 0 for a, g in lines):
        raise ValueError('No valid economy fallback or positive-slope certificate')
    ceiling = min(F(1), min((TAU-a)/g for a, g in lines))
    guard = max(g for _, g in lines)
    root = 1/(1+(2*dec(guard)-D('.6')).exp())
    # A rational ceiling below 1/2 is strictly below this model's root.
    if ceiling <= F(1, 2) and guard < F(3, 10):
        chosen = ceiling
    else:
        chosen = min(ceiling, max(F(0), F(str(root-PAD))))
    check(0 <= chosen <= ceiling <= 1, 'action range')
    check(dec(chosen) <= root, 'objective guard')
    check(all(a+g*chosen <= TAU for a, g in lines), 'certified safe choice')
    m = kl((F(1), F(0)), (F(1, 2), F(1, 2))) \
        - kl((1-chosen, chosen), (F(1, 2), F(1, 2))) \
        + D('.6')*dec(chosen)-2*dec(guard*chosen)
    gain_u = chosen*(F(3, 20)-guard/2)
    return dict(ceiling=ceiling, guard=guard, r=chosen,
                guaranteed_J_gain=m, guaranteed_U_gain=gain_u,
                sufficient_cost_ceiling=min(m, 4*dec(gain_u)))


def construct(h, pair):
    tables = pair_tables(PRIORS, EDGES, factors(h), pair, h)
    decision = action([(row['A'], row['G']) for row in tables])
    check(decision['r'] > 0, 'positive nominal candidate')
    check(decision['sufficient_cost_ceiling'] > 0, 'nonempty symbolic cost range')
    return dict(h=h, pair=pair, Q=[F(1, 8)]*8, local=tables,
                local_weight_evaluations=8, decision=decision)


def replay_schedule(h, pair, schedule):
    """Replay the declared compute/commit events before any exact reference."""
    events = {'stop': ('commit',), 'timely': ('compute', 'commit'),
              'late': ('commit', 'compute'), 'blocked': ('compute', 'commit')}[schedule]
    available, completed, committed = None, None, None
    trace = []
    for event in events:
        if event == 'compute':
            completed = construct(h, pair)
            if schedule != 'blocked':
                available = completed
        else:
            committed = available['decision']['r'] if available else F(0)
        trace.append(dict(event=event, available=available is not None, committed=committed))
    check(committed is not None, 'action committed once')
    return dict(r=committed, completed=completed, trace=trace,
                cost_coefficient=int(completed is not None))


def exact_reference(priors, edges, fs):
    """Independent full enumeration; never called by construct/pair_tables."""
    weights = {}
    for z in STATES:
        w = F(1)
        for k in range(3):
            w *= priors[k][z[k]]
        for e in range(len(edges)):
            first, second = edges[e]
            w *= fs[e][z[first]][z[second]]
        weights[z] = w
    evidence = sum(weights.values())
    pi = {z: w/evidence for z, w in weights.items()}
    check(sum(pi.values()) == 1, 'reference normalized')
    return pi, evidence, weights


def verify_conditionals(tables, pi, pair):
    for row in tables:
        boundary, bit = row['boundary'], row['bit']
        mass = sum(p for z, p in pi.items() if z[boundary] == bit)
        check(sum(p for _, p in row['eta']) == 1, 'conditional normalization')
        for z, p in row['eta']:
            check(p == pi[z]/mass, 'conditional versus independent enumeration')


def qualify():
    start = CHECKS
    uniform = pair_tables(PRIORS, (), (), (0, 1), F(1, 100))
    check(all(p == F(1, 4) for row in uniform for _, p in row['eta']), 'uniform conditional')
    check(action([(TAU, F(1, 20))])['r'] == 0, 'economy-only ceiling')
    free = action([(F(1, 100), F(1, 50))])
    check(F(1, 2) < free['r'] < free['ceiling'], 'free optimum branch')
    rejected = 0
    for invalid in ([], [(F(11, 100), F(1, 20))], [(F(1, 20), F(0))]):
        try:
            action(invalid)
        except ValueError:
            rejected += 1
    check(rejected == 3, 'invalid certificates rejected')
    priors = ((F(3, 5), F(2, 5)), (F(9, 20), F(11, 20)), (F(7, 10), F(3, 10)))
    edges = ((0, 1), (2, 1))
    fs = (((F('.02'), F('.1')), (F('.08'), F('.19'))),
          ((F('.03'), F('.09')), (F('.07'), F('.16'))))
    pi, _, _ = exact_reference(priors, edges, fs)
    for pair in ((0, 1), (1, 0), (2, 1), (1, 2)):
        verify_conditionals(pair_tables(priors, edges, fs, pair, F('.01')), pi, pair)
    return dict(assertions=CHECKS-start, rejected=3, status='PASS')


def full_law(pi, pair, h, r, shifted):
    result = {}
    for z, pz in pi.items():
        f0, f1 = rates(h, z, pair)
        if shifted:
            f1 = 1-(1-f1)*(1-HAZARD)
        for a, task, continuation in product((0, 1), repeat=3):
            accuracy = F(3, 4) if a == 0 else F(9, 10)
            failure = f0 if a == 0 else f1
            result[(z, a, task, continuation)] = pz*bern(r, a)*bern(accuracy, task)*bern(1-failure, continuation)
    check(len(result) == 64 and sum(result.values()) == 1, 'full physical law normalized')
    return result


def evaluate(record):
    agent, schedules = record['agent'], record['schedules']
    h, pair = agent['h'], agent['pair']
    pi, evidence, weights = exact_reference(PRIORS, EDGES, factors(h))
    verify_conditionals(agent['local'], pi, pair)
    a = sum(p*rates(h, z, pair)[0] for z, p in pi.items())
    g = sum(p*(rates(h, z, pair)[1]-rates(h, z, pair)[0]) for z, p in pi.items())
    t = agent['decision']['r']
    lines = [(x['A'], x['G']) for x in agent['local']]
    points = {F(0), F(1, 4), F(1, 2), F(3, 4), F(1), t}
    if lines[0][1] != lines[1][1]:
        crossing = (lines[1][0]-lines[0][0])/(lines[0][1]-lines[1][1])
        if 0 <= crossing <= 1:
            points.add(crossing)
    for r in points:
        lo, hi = min(x+y*r for x, y in lines), max(x+y*r for x, y in lines)
        check(lo <= a+g*r <= hi, 'risk envelope covers nominal law')
    reference = full_law(pi, pair, h, F(1, 2), False)
    tilted = {s: dec(p)*(4*dec(s[2]+F(1, 2)*s[3])).exp() for s, p in reference.items()}
    normalizer = sum(tilted.values())
    preferred = {s: p/normalizer for s, p in tilted.items()}
    close(sum(preferred.values()), 1, 'preferred law normalized')
    discrepancy = D(0)
    for z, p in pi.items():
        failure = rates(h, z, pair)[1]
        shifted_failure = 1-(1-failure)*(1-HAZARD)
        discrepancy += dec(p)*kl((1-shifted_failure, shifted_failure), (1-failure, failure))
    # Compute VFE directly from Q and unnormalized nominal joint, then by KL.
    vfe = sum((dec(F(1,8))*(dec(F(1,8))/dec(weights[z])).ln() for z in STATES), D(0))
    close(vfe, kl([F(1,8)]*8, [pi[z] for z in STATES])-dec(evidence).ln(), 'VFE identity')
    delta_critical = (TAU-(a+g*t))/(t*(1-a-g))
    check(delta_critical >= 0, 'nominal shift threshold nonnegative')
    cells, laws = [], {}
    for shifted in (False, True):
        world = 'shifted' if shifted else 'nominal'
        for schedule in ('stop', 'timely', 'late', 'blocked'):
            r = schedules[schedule]['r']
            law = full_law(pi, pair, h, r, shifted)
            laws[(world, schedule)] = law
            risk = sum(p for (_, _, _, v), p in law.items() if v == 0)
            accuracy = sum(p for (_, _, task, _), p in law.items() if task == 1)
            utility = sum(p*(task+F(1,2)*v) for (_, _, task, v), p in law.items())
            actual_g = g + (HAZARD*(1-a-g) if shifted else 0)
            check(risk == a+actual_g*r, 'actual risk formula')
            check(accuracy == F(3,4)+F(3,20)*r, 'task accuracy formula')
            check(utility == F(5,4)+F(3,20)*r-risk/2, 'raw utility formula')
            j = kl((1-r, r), (F(1,2), F(1,2)))-4*dec(utility)
            divergence = kl(list(law.values()), [preferred[s] for s in law])
            physical_discrepancy = dec(r)*discrepancy if shifted else D(0)
            close(divergence, j+normalizer.ln()+physical_discrepancy, 'fixed-preference FEP identity')
            predicted_risk = a+g*r
            reported_upper = max(x+y*r for x, y in lines)
            check(predicted_risk <= reported_upper <= TAU, 'nominal certificate at executed action')
            if shifted and schedule == 'timely':
                check((risk > TAU) == (HAZARD > delta_critical), 'exact shift threshold classification')
                check(risk > predicted_risk, 'positive hidden-hazard effect')
            cells.append(dict(world=world, schedule=schedule, r=r,
                              compute_cost_coefficient=schedules[schedule]['cost_coefficient'],
                              risk=risk, correctness=accuracy, utility=utility, J=j,
                              continuation=1-risk, model_predicted_risk=predicted_risk,
                              certificate_upper=reported_upper, risk_violation=risk>TAU,
                              certificate_exceeded=risk>reported_upper,
                              full_FEP_divergence=divergence,
                              model_discrepancy=physical_discrepancy, VFE=vfe))
        for schedule in ('late', 'blocked'):
            check(laws[(world, schedule)] == laws[(world, 'stop')], 'committed-action distribution unchanged')
    by = {(c['world'],c['schedule']): c for c in cells}
    for schedule in ('stop','timely','late','blocked'):
        check(by[('nominal',schedule)]['r'] == by[('shifted',schedule)]['r'], 'world absent from actor input')
    baseline, timely = by[('nominal','stop')], by[('nominal','timely')]
    gain_j = baseline['J']-timely['J']
    gain_u = timely['utility']-baseline['utility']
    check(gain_j+TOL >= agent['decision']['guaranteed_J_gain'] > 0, 'guaranteed objective gain')
    check(gain_u >= agent['decision']['guaranteed_U_gain'] > 0, 'guaranteed functional gain')
    check(timely['correctness'] > baseline['correctness'], 'strict correctness gain')
    check(timely['risk'] <= TAU, 'primary absolute continuation requirement')
    # Independent expression for the matched Bayesian robust utility/reference rule.
    reference_weight = (4*(D('.15')-dec(max(y for _,y in lines))/2)).exp()
    bayes_free = reference_weight/(1+reference_weight)
    bayes_cap = min(F(1), min((TAU-x)/y for x,y in lines))
    bayes_r = min(bayes_cap, max(F(0), F(str(bayes_free-PAD))))
    close(bayes_r, t, 'matched decision rule equality')
    functional_pass = (timely['risk'] <= TAU
                       and timely['correctness'] > baseline['correctness']
                       and gain_u > 0
                       and agent['decision']['sufficient_cost_ceiling'] > 0)
    return dict(h=h, pair=pair, evidence=evidence, pi=[(z,pi[z]) for z in STATES],
                A=a,G=g,VFE=vfe,preference_normalizer=normalizer,
                preference=[(s,p) for s,p in preferred.items()],
                delta_critical=delta_critical, actual_J_gain=gain_j, actual_U_gain=gain_u,
                nominal_functional_pass=functional_pass, cells=cells)


def encode(x):
    if isinstance(x, (F,D)):
        return str(x)
    raise TypeError(type(x).__name__)


def write(path, obj):
    path.write_text(json.dumps(obj, default=encode, indent=2, allow_nan=False)+'\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    mount = Path('/mnt/bioIce1')
    base = mount/'fep-ideas/formal-checks/fep-functional-timing-v1'
    output = args.output.resolve()
    if not mount.is_mount() or output.parent != base.resolve():
        raise SystemExit('Require the mounted external FEP study directory')
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing attempt')
    base.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    (output/'inputs').mkdir()
    source_root = Path(__file__).resolve().parent
    source_names = ('FEP_FUNCTIONAL_TIMING_V1.md', Path(__file__).name,
                    'FEP_COMPUTATION_VALUE_V1.md', 'FEP_PAIR_CONDITIONAL_RISK_V1.md')
    manifest = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                    python=platform.python_version(), pid=os.getpid(), processes=1, inputs=[])
    for name in source_names:
        source = source_root/name
        shutil.copyfile(source, output/'inputs'/name)
        manifest['inputs'].append(identity(source))
    write(output/'MANIFEST.json', manifest)
    wall, cpu = perf_counter(), process_time()
    with (output/'RUN_LOG.txt').open('x') as log:
        try:
            qualification = qualify()
            log.write(json.dumps(qualification)+'\n')
            records = []
            for h in (F('1e-6'),F('.01')):
                for pair in QUERIES:
                    schedules = {s: replay_schedule(h, pair, s)
                                 for s in ('stop','timely','late','blocked')}
                    agent = schedules['timely']['completed']
                    for schedule in ('late','blocked'):
                        check(schedules[schedule]['completed'] == agent, 'identical completed calculations')
                        check(schedules[schedule]['r'] == schedules['stop']['r'] == 0, 'commitment locks fallback')
                    check(schedules['stop']['cost_coefficient']==0, 'stop has no calculation charge')
                    check(all(schedules[s]['cost_coefficient']==1 for s in ('timely','late','blocked')), 'compute charged in all timings')
                    # Save one shared representation of the equal outputs, plus event traces.
                    for replay in schedules.values():
                        replay.pop('completed')
                    records.append(dict(agent=agent, schedules=schedules))
            write(output/'AGENT_RECORDS.json', records)
            agent_digest = identity(output/'AGENT_RECORDS.json')['sha256']
            log.write('All eight agent records sealed before exact main references: '+agent_digest+'\n')
            log.flush()
            results = []
            for record in records:
                result = evaluate(record)
                results.append(result)
                agent = record['agent']
                log.write(f"Completed h={agent['h']} query={agent['pair']}\n")
                log.flush()
            check(identity(output/'AGENT_RECORDS.json')['sha256'] == agent_digest, 'agent record unchanged')
            cells = [c for result in results for c in result['cells']]
            check(len(results)==8 and len(cells)==64, 'all registered cells retained')
            summary = dict(status='PASS', problems=8, policy_cells=64, assertions=CHECKS,
                           nominal_timely_functional_passes=sum(r['nominal_functional_pass'] for r in results),
                           shifted_timely_risk_violations=sum(c['risk_violation'] for c in cells if c['world']=='shifted' and c['schedule']=='timely'),
                           shifted_timely_certificate_exceedances=sum(c['certificate_exceeded'] for c in cells if c['world']=='shifted' and c['schedule']=='timely'),
                           fallback_risk_violations=sum(c['risk_violation'] for c in cells if c['schedule']!='timely'),
                           timing_and_fixed_preference_checks='PASS', selected_operating_cost=None)
            write(output/'RESULTS.json', dict(qualification=qualification, results=results, summary=summary))
            log.write(json.dumps(summary)+'\n')
            manifest.update(status='complete', summary=summary)
        except BaseException:
            manifest.update(status='failed', assertions=CHECKS)
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
    print(json.dumps(dict(output=str(output), status=manifest['status'], summary=manifest.get('summary'),
                          wall_seconds=manifest['wall_seconds']), indent=2))


if __name__ == '__main__':
    main()
