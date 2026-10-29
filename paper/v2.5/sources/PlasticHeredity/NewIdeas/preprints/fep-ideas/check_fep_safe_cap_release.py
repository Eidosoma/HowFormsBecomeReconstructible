#!/usr/bin/env python3
"""Certify upward decisions beyond an old approximate-action cap."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import json
import os
from pathlib import Path
import platform
import statistics as stats
import time
import traceback

import check_fep_decision_regret as old

prior = old.prior
ZERO, ONE, TAU, PAD = old.ZERO, old.ONE, old.TAU, old.PAD
GUARD, NUMTOL, TOL, TIE = old.GUARD, old.NUMTOL, old.TOL, old.TIE
check, close, read, write, identity = old.check, old.close, old.read, old.write, old.identity
require, le, dec_close = old.require, old.le, old.dec_close
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-decision-regret-v1/attempt-01'
DEST = BASE/'fep-safe-cap-release-v1/attempt-01'
SPEC = HERE/'FEP_SAFE_CAP_RELEASE_V1.md'
METHODS = ('physical', 'interval')


def safe_ceiling(env, selected):
    require(all(b >= ZERO for a, b in env['upper']), 'negative upper slope unsupported')
    caps = []
    for a, b in env['upper']:
        if a > TAU:
            caps.append(None)
        elif a+b <= TAU:
            caps.append(ONE)
        else:
            require(b > ZERO, 'invalid binding upper slope')
            caps.append(old.clip((TAU-a-PAD)/b, ZERO, ONE))
    require(any(c is not None for c in caps), 'no certified safe action')
    ceiling = max(selected, max(c for c in caps if c is not None))
    check(old.interval(env, ceiling)[1] <= TAU+NUMTOL, 'safe ceiling certified')
    witness = min(range(len(env['upper'])), key=lambda i: old.affine(env['upper'][i], ceiling))
    return dict(value=ceiling, line_caps=caps, witness=witness)


def guaranteed_gain(start, finish, guard, cache):
    check(finish >= start, 'improvement guarantee is for upward move')
    if start == finish:
        return ZERO
    raw = old.psi(start, guard, cache)-old.psi(finish, guard, cache)
    check(raw >= -NUMTOL, 'analytic improvement lower bound nonnegative')
    return max(ZERO, raw-2*GUARD)


def policy(selected, ceiling, guard, cache):
    free_guard = max(ZERO, cache.stationary(guard)-PAD)
    chosen = max(selected, min(ceiling, free_guard))
    if chosen == selected:
        limit = 'hold_objective' if free_guard <= selected else 'hold_safety'
    else:
        limit = 'risk' if ceiling <= free_guard else 'objective'
    return dict(r=chosen, slope_guard=guard, free_guard=free_guard, limit=limit,
                guaranteed_gain=guaranteed_gain(selected, chosen, guard, cache))


def global_bounds(r, env, glo, ghi, cap, minimum, cache):
    require(r <= cap+NUMTOL, 'choice lies in relaxed global comparator')
    upper = cache.k(r)-5-D('.6')*r+2*old.interval(env, r)[1]+GUARD
    level = upper-minimum['value']
    check(level >= -NUMTOL, 'nonnegative direct level bound')
    left = old.clip(cache.stationary(ghi), ZERO, r)
    right = old.clip(cache.stationary(glo), r, cap)
    slope = max(ZERO, old.psi(r, ghi, cache)-old.psi(left, ghi, cache),
                old.psi(r, glo, cache)-old.psi(right, glo, cache))+2*GUARD
    level = max(ZERO, level)
    return dict(level_bound=level, slope_bound=slope, direct_bound=min(level, slope),
                selected_objective_upper=upper, slope_left_argmin=left, slope_right_argmin=right)


def derive(h, selected, original_cap, env):
    """Pure policy and certificate calculation, with no reference-data access."""
    start = time.process_time()
    old.validate_inputs(h, selected, original_cap, dict(signed=env, combined=env))
    ceiling = safe_ceiling(env, selected)
    l0, u0 = old.interval(env, ZERO)
    l1, u1 = old.interval(env, ONE)
    glo = max(h*(1-TAU), l1-u0-PAD)
    ghi = min(TAU*(1-h), u1-l0+PAD)
    require(glo <= ghi+NUMTOL, 'empty physical risk-slope interval')
    cache = old.ScalarCache()
    policies = {name: policy(selected, ceiling['value'], guard, cache)
                for name, guard in (('physical', TAU*(1-h)), ('interval', ghi))}
    check(selected <= policies['physical']['r'] <= policies['interval']['r'] <= ceiling['value'],
          'baseline physical interval action ordering')
    for name, item in policies.items():
        item['certified_risk_upper'] = old.interval(env, item['r'])[1]
        check(item['certified_risk_upper'] <= TAU+NUMTOL, name+' certified risk limit')
        if item['r'] > selected:
            check(item['r'] <= cache.stationary(item['slope_guard']), name+' move below guarded optimum')
    comparison_gain = guaranteed_gain(policies['physical']['r'], policies['interval']['r'], ghi, cache)
    policy_cpu = time.process_time()-start
    policy_entropy, policy_stationary = cache.entropy_calls, cache.stationary_calls
    start = time.process_time()
    relaxed = old.relaxed_cap(env['lower'], ONE)
    minimum = old.minimize_lower(env['lower'], relaxed, cache)
    baseline = global_bounds(selected, env, glo, ghi, relaxed, minimum, cache)
    baseline['bound'] = baseline['direct_bound']
    baseline['r'] = selected
    for name, item in policies.items():
        bounds = global_bounds(item['r'], env, glo, ghi, relaxed, minimum, cache)
        propagated = baseline['bound']-item['guaranteed_gain']+PAD
        check(propagated >= -NUMTOL, name+' nonnegative propagated regret bound')
        bounds['propagated_bound'] = max(ZERO, propagated)
        bounds['bound'] = min(bounds['direct_bound'], bounds['propagated_bound'], baseline['bound'])
        check(bounds['bound'] <= baseline['bound'], name+' retained global bound nonincreasing')
        item['regret'] = bounds
    return dict(safe_ceiling=ceiling, slope_lower=glo, slope_upper=ghi,
                relaxed_cap=relaxed, lower_optimum=minimum, baseline=baseline, policies=policies,
                primary_over_control_guarantee=comparison_gain, policy_cpu=policy_cpu,
                regret_cpu=time.process_time()-start,
                policy_entropy_calls=policy_entropy, policy_stationary_calls=policy_stationary,
                total_entropy_calls=cache.entropy_calls, total_stationary_calls=cache.stationary_calls)


def construct(view):
    values, envelopes = old.compile_envelopes(view)
    env = envelopes['combined']
    return env, derive(values['h'], values['selected'], values['original_cap'], env)


def reproduce_baseline(cert, saved):
    before = saved['certificates']['combined']
    for key in ('slope_lower', 'slope_upper'):
        dec_close(cert[key], before[key], 'unchanged '+key)
    dec_close(cert['relaxed_cap'], before['global']['relaxed_cap'], 'unchanged relaxed global ceiling')
    for key in ('r', 'value'):
        dec_close(cert['lower_optimum'][key], before['global']['lower_optimum'][key], 'unchanged lower minimum '+key)
    for key in ('level_bound', 'slope_bound', 'bound', 'slope_left_argmin', 'slope_right_argmin'):
        dec_close(cert['baseline'][key], before['global'][key], 'reproduced old global '+key)
    dec_close(cert['baseline']['selected_objective_upper'], before['selected_objective_upper'],
              'reproduced old objective upper')


def evaluate(cert, env, original_cap, a, g, saved=None):
    """Exact model risks enter only after policies and certificates are fixed."""
    optimum = min(prior.free(g), (TAU-a)/g)
    capped = min(optimum, original_cap)
    _, best_j = prior.score(optimum, a, g)
    _, capped_j = prior.score(capped, a, g)
    old_r = cert['baseline']['r']
    old_risk, old_j = prior.score(old_r, a, g)
    le(old_risk, TAU, 'baseline true risk limit')
    baseline_regret = old_j-best_j
    result = dict(exact_r=optimum, old_risk=old_risk, old_global_regret=baseline_regret,
                  old_capped_regret=old_j-capped_j, old_cap_loss=capped_j-best_j, policies={})
    le(cert['slope_lower'], g, 'true risk slope lower coverage')
    le(g, cert['slope_upper'], 'true risk slope upper coverage')
    le(optimum, cert['relaxed_cap'], 'true optimum in relaxed domain')
    le(cert['lower_optimum']['value'], best_j, 'lower objective minimum valid')
    le(baseline_regret, cert['baseline']['bound'], 'baseline global bound coverage')
    for name, item in cert['policies'].items():
        r = item['r']
        risk, score = prior.score(r, a, g)
        gain, regret = old_j-score, score-best_j
        le(risk, TAU, name+' true risk limit')
        le(score, old_j, name+' true objective nonworsening')
        le(item['guaranteed_gain'], gain, name+' guaranteed improvement coverage')
        le(0, regret, name+' true global regret nonnegative')
        for field in ('level_bound', 'slope_bound', 'direct_bound', 'propagated_bound', 'bound'):
            le(regret, item['regret'][field], name+' '+field+' covers true regret')
        result['policies'][name] = dict(risk=risk, objective=score, gain=gain, global_regret=regret)
    control, primary = [result['policies'][name] for name in METHODS]
    gain = control['objective']-primary['objective']
    le(0, gain, 'interval rule no worse than physical control')
    le(cert['primary_over_control_guarantee'], gain, 'primary over control guarantee coverage')
    result['primary_over_control_gain'] = gain
    for r in (ZERO, ONE, old_r, optimum, cert['safe_ceiling']['value'],
              *(p['r'] for p in cert['policies'].values())):
        lo, hi = old.interval(env, r)
        le(lo, a+r*g, 'inherited risk lower coverage')
        le(a+r*g, hi, 'inherited risk upper coverage')
    if saved is not None:
        before = saved['evaluation']
        for key, previous in (('exact_r', 'exact_r'), ('old_risk', 'actual_risk'),
                              ('old_global_regret', 'global_regret'), ('old_capped_regret', 'capped_regret'),
                              ('old_cap_loss', 'cap_loss')):
            close(result[key], before[previous], 'reproduced evaluation '+key)
    return result


def scalar_case(name, a, g, s, cap, uppers=None):
    h = D('.01')
    env = dict(lower=[(h, h*(1-h))], upper=[(TAU, TAU*(1-TAU))])
    if uppers is None:
        env['lower'].append((a, g))
        env['upper'].append((a, g))
    else:
        env['upper'].extend(tuple(map(D, line)) for line in uppers)
    certificate = derive(h, s, cap, env)
    assessment = evaluate(certificate, env, cap, a, g)
    return dict(name=name, h=h, true_a=a, true_g=g, original_cap=cap, selected=s,
                envelope=env, certificate=certificate, evaluation=assessment)


def qualify():
    rows = []
    cases = [
        ('risk_binding', '.08', '.08', '0', '.2', None),
        ('risk_bound_reached', '.08', '.08', '.25', '.4', None),
        ('free_limited', '.01', '.02', '.2', '.3', None),
        ('loose_slope', '.04', '.04', '.2', '.3', [('.04', '.04')]),
        ('envelope_switch', '.085', '.04', '.1', '.15', [('.085', '.08'), ('.09', '.045')]),
        ('flat_safe_bound', '.01', '.02', '.2', '.3', [('.09', '0')]),
        ('no_certified_increase', '.08', '.04', '.1', '.2', [('.09', '.1')]),
        ('exact_optimum', '.01', '.02', None, '.8', None),
        ('above_free', '.01', '.02', '.8', '.9', None),
        ('economy_only', '.1', '.04', '0', '.2', None),
        ('endpoint_choice', '.01', '.02', '1', '1', None),
    ]
    for name, a, g, s, cap, uppers in cases:
        a, g, cap = D(a), D(g), D(cap)
        s = prior.free(g) if s is None else D(s)
        row = scalar_case(name, a, g, s, cap, uppers)
        cert = row['certificate']
        p, c = cert['policies']['interval'], cert['policies']['physical']
        if name in ('risk_bound_reached', 'no_certified_increase', 'exact_optimum',
                    'above_free', 'economy_only', 'endpoint_choice'):
            check(p['r'] == c['r'] == s, name+' retains current choice')
        else:
            check(p['r'] > s and row['evaluation']['policies']['interval']['gain'] > TIE,
                  name+' strict improvement')
        if name == 'risk_binding':
            dec_close(p['r'], D('.25'), 'risk-binding expected choice')
            check(p['r'] > cap, 'risk-binding crosses old cap')
        if name == 'free_limited':
            dec_close(p['r'], prior.free(g), 'exact free optimum reached')
            check(p['r'] > c['r'], 'slope information improves free-limited control')
            _, safety_j = prior.score(cert['safe_ceiling']['value'], a, g)
            _, old_j = prior.score(s, a, g)
            check(safety_j > old_j+TIE, 'safety-only increase can worsen objective')
            row['safety_only_counterexample'] = dict(r=cert['safe_ceiling']['value'],
                                                    objective_increase=safety_j-old_j)
        if name in ('loose_slope', 'flat_safe_bound'):
            check(p['r'] > c['r'], name+' distinguishes slope guards')
        if name == 'envelope_switch':
            dec_close(cert['safe_ceiling']['value'], D('.01')/D('.045'), 'union uses larger safe ceiling')
            check(cert['safe_ceiling']['witness'] == 2, 'second upper line witnesses safety')
        rows.append(row)
    for name in ('uncertified_current', 'negative_upper', 'unexpected_truth_field'):
        reason = ''
        try:
            if name == 'unexpected_truth_field':
                view = {key: '0' for key in old.FIELDS}
                view.update(h='.01', a='.04', g='.04', l0='.04', l1='.08', u0='.04', u1='.08',
                            selected='.2', original_cap='.3', exact_a='.04')
                construct(view)
            else:
                exact = (D('.01'), D('.02')) if name == 'negative_upper' else (D('.08'), D('.08'))
                env = dict(lower=[(D('.01'), D('.0099')), exact],
                           upper=[(TAU, D('.09')), exact])
                if name == 'negative_upper':
                    env['upper'].append((D('.12'), D('-.01')))
                derive(D('.01'), D('.4') if name == 'uncertified_current' else D('.1'), D('.4'), env)
        except ValueError as error:
            reason = str(error)
        expected = dict(uncertified_current='current choice is not certified feasible',
                        negative_upper='negative upper slope unsupported',
                        unexpected_truth_field='unexpected or missing agent-view field')
        check(reason == expected[name], name+' rejected for declared reason')
        rows.append(dict(name=name, rejected=True, reason=reason))
    return rows


def summarize(records):
    result = dict(queries=len(records),
                  old_mean_r=stats.fmean(float(q['agent_view']['selected']) for q in records),
                  original_mean_r=stats.fmean(float(q['agent_view']['original_cap']) for q in records),
                  exact_mean_r=stats.fmean(float(q['evaluation']['exact_r']) for q in records),
                  old_mean_regret=stats.fmean(q['evaluation']['old_global_regret'] for q in records),
                  old_mean_cap_loss=stats.fmean(q['evaluation']['old_cap_loss'] for q in records),
                  old_mean_bound=stats.fmean(float(q['certificate']['baseline']['bound']) for q in records),
                  primary_over_control_mean_gain=stats.fmean(q['evaluation']['primary_over_control_gain'] for q in records),
                  primary_over_control_mean_guarantee=stats.fmean(float(q['certificate']['primary_over_control_guarantee']) for q in records),
                  policy_disagreements=sum(float(q['certificate']['policies']['interval']['r']-
                                                  q['certificate']['policies']['physical']['r']) > TIE for q in records))
    for key in ('policy_cpu', 'regret_cpu', 'policy_entropy_calls', 'policy_stationary_calls',
                'total_entropy_calls', 'total_stationary_calls'):
        result[key] = sum(q['certificate'][key] for q in records)
    for name in METHODS:
        pp = [q['certificate']['policies'][name] for q in records]
        ee = [q['evaluation']['policies'][name] for q in records]
        result[name] = dict(mean_r=stats.fmean(float(p['r']) for p in pp),
                            mean_risk=stats.fmean(e['risk'] for e in ee), max_risk=max(e['risk'] for e in ee),
                            mean_regret=stats.fmean(e['global_regret'] for e in ee),
                            mean_gain=stats.fmean(e['gain'] for e in ee),
                            mean_guaranteed_gain=stats.fmean(float(p['guaranteed_gain']) for p in pp),
                            max_regret=max(e['global_regret'] for e in ee),
                            changed=sum(float(p['r'])-float(q['agent_view']['selected']) > TIE for p, q in zip(pp, records)),
                            crossed_old_cap=sum(float(p['r'])-float(q['agent_view']['original_cap']) > TIE for p, q in zip(pp, records)),
                            guaranteed_improvements=sum(float(p['guaranteed_gain']) > TIE for p in pp),
                            actual_improvements=sum(e['gain'] > TIE for e in ee),
                            actual_worsenings=sum(e['gain'] < -TIE for e in ee),
                            limits=dict(Counter(p['limit'] for p in pp)))
        for field in ('level_bound', 'slope_bound', 'direct_bound', 'propagated_bound', 'bound'):
            result[name]['mean_'+field] = stats.fmean(float(p['regret'][field]) for p in pp)
        result[name]['max_bound'] = max(float(p['regret']['bound']) for p in pp)
        result[name]['mean_bound_slack'] = stats.fmean(float(p['regret']['bound'])-e['global_regret'] for p, e in zip(pp, ee))
    return result


def aggregate(rows):
    result = {}
    count_fields = ('queries', 'policy_disagreements', 'policy_entropy_calls', 'policy_stationary_calls',
                    'total_entropy_calls', 'total_stationary_calls')
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [r for r in rows if r['kind'] == kind and r['level'] == level]
            item = {}
            for field in ('old_mean_r', 'original_mean_r', 'exact_mean_r', 'old_mean_regret',
                          'old_mean_cap_loss', 'old_mean_bound', 'primary_over_control_mean_gain',
                          'primary_over_control_mean_guarantee', 'policy_cpu', 'regret_cpu'):
                item[field] = stats.fmean(r[field] for r in rr)
            for field in count_fields:
                item[field] = sum(r[field] for r in rr)
            for name in METHODS:
                pp = [r[name] for r in rr]
                item[name] = {}
                for field in pp[0]:
                    if field == 'limits':
                        total = Counter()
                        for p in pp:
                            total.update(p[field])
                        item[name][field] = dict(total)
                    else:
                        reducer = stats.fmean if field.startswith('mean_') else max if field.startswith('max_') else sum
                        item[name][field] = reducer(p[field] for p in pp)
            result[kind+'_'+str(level)] = item
    return result


def run(output, log):
    qualification = qualify()
    log.write('Eleven accepted scalar cases and three rejection controls passed.\n')
    log.flush()
    old.verify_manifest(MAIN/'MANIFEST.json')
    old.verify_manifest(OLD/'MANIFEST.json')
    core, previous = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json')
    check(not core['gate']['passed'], 'failed original mechanism gate preserved')
    previous_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in previous['rows']}
    saved_queries = {}
    with (OLD/'QUERIES.jsonl').open() as stream:
        for line in stream:
            q = json.loads(line)
            saved_queries.setdefault((q['fixture'], q['kind'], q['order'], q['level']), []).append(q)
    rows, count = [], 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture, kind, order = [case[k] for k in ('fixture', 'kind', 'order')]
            for level in (256, 1024, 4096):
                key = (fixture, kind, order, level)
                prepared = []
                for q in saved_queries[key]:
                    # A separate strict projection is all the constructor receives.
                    view = dict(q['agent_view'])
                    env, cert = construct(view)
                    reproduce_baseline(cert, q)
                    prepared.append((q, view, env, cert))
                # Every new choice for this belief exists before exact-reference scoring.
                ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                edges = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')['model']['edges']
                records = []
                for q, view, env, cert in prepared:
                    pair = ref['pairs'][q['edge']]
                    pair = {bits: D(str(pair[bits[0]][bits[1]])) for bits in prior.states(2)}
                    if q['source'] != edges[q['edge']][0]:
                        pair = {(y, x): value for (x, y), value in pair.items()}
                    a, g = prior.pair_risks(pair, D(view['h']))
                    evaluation = evaluate(cert, env, D(view['original_cap']), a, g, saved=q)
                    record = dict(edge=q['edge'], source=q['source'], target=q['target'],
                                  agent_view=view, certificate=cert, evaluation=evaluation)
                    records.append(record)
                    stream.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **record),
                                            default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summarize(records)
                before = previous_rows[key]
                close(summary['old_mean_regret'], before['actual_global_regret'], 'old case regret reproduced')
                close(summary['old_mean_bound'], before['combined']['global']['mean_bound'], 'old case bound reproduced')
                rows.append(dict(fixture=fixture, kind=kind, order=order, level=level,
                                 preceding_certificate_cpu=before['preceding_certificate_cpu'],
                                 preceding_q_reconstruction_cpu=before['preceding_q_reconstruction_cpu'],
                                 preceding_regret_cpu=before['regret_cpu'], main_cost=before['main_cost'], **summary))
                count += len(records)
            log.write(f'Completed {fixture} {kind} {order}; all three budgets retained.\n')
            log.flush()
    check(len(rows) == 96 and count == 13056, 'all saved checkpoints and queries retained')
    return dict(qualification=qualification, rows=rows, summary=aggregate(rows),
                inherited_model_preparation=previous['inherited_model_preparation'],
                checkpoints=len(rows), original_queries=count, new_policies=2*count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted cap-release output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen cap-release checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen cap-release specification')
    check(identity(old.__file__)['sha256'] == '961ebf6505e74b562c1baf6fd9da0d9ea2cadbb3af7fd391945511b14b1d1d70',
          'unchanged regret helper')
    check(identity(prior.__file__)['sha256'] == 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6',
          'unchanged numerical helper')
    check(identity(OLD/'MANIFEST.json')['sha256'] == '03f7bb49003c16d5df36a6167ac95d30ddb0f1fb75e4c381dc6cd20f5b7385d3',
          'pinned regret record')
    paths = [SPEC, Path(__file__), Path(old.__file__), Path(prior.__file__), HERE/'FEP_DECISION_REGRET_V1.md',
             HERE/'FEP_DECISION_REGRET_V1_REPORT.md', OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl',
             MAIN/'MANIFEST.json', MAIN/'CORE.json', MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
             HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    for path, name in ((SPEC, 'SPECIFICATION.md'), (Path(__file__), 'CHECKER_SOURCE.py'),
                       (Path(old.__file__), 'REUSED_REGRET_HELPER.py'), (Path(prior.__file__), 'REUSED_NUMERICAL_HELPER.py')):
        (DEST/name).write_bytes(path.read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='certified release of old action cap on fixed saved beliefs; no inference updates',
                    cpu_processes=1, python=platform.python_version(), decimal_precision=60,
                    primary_rule='combined risk-slope guard', control='physical risk-slope guard',
                    selected_stopping_tolerance=None)
    write(DEST/'MANIFEST.json', manifest)
    start, cpu = time.perf_counter(), time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result = run(DEST, log)
            result.update(status='passed', assertions=sum(prior.COUNTS.values()),
                          assertions_by_label=dict(prior.COUNTS), max_residuals=prior.RESIDUALS,
                          elapsed_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json', result)
            manifest['status'] = 'passed'
            log.write(f"Passed {result['assertions']} checks and {result['new_policies']} new policy evaluations.\n")
            print(json.dumps({key: result[key] for key in ('status', 'assertions', 'elapsed_seconds', 'cpu_seconds',
                              'checkpoints', 'original_queries', 'new_policies', 'summary')}, default=prior.encode, indent=2))
        except Exception:
            manifest['status'] = 'failed'
            log.write(traceback.format_exc())
            raise
        finally:
            log.flush()
            manifest['outputs'] = [identity(p) for p in sorted(DEST.iterdir()) if p.name != 'MANIFEST.json']
            write(DEST/'MANIFEST.json', manifest)


if __name__ == '__main__':
    main()
