#!/usr/bin/env python3
"""Full conditional pair averaging with a signed risk remainder."""
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

import check_fep_local_risk_correction as correction
import check_fep_safe_cap_release as release

signed, prior, regret = correction.signed, correction.prior, release.old
ZERO, ONE, HALF, TAU = signed.ZERO, signed.ONE, signed.HALF, signed.TAU
PAD, NUMTOL, TOL, TIE = signed.PAD, signed.NUMTOL, signed.TOL, signed.TIE
check, close, dec_close, le = signed.check, signed.close, signed.dec_close, signed.le
read, write, identity, states = prior.read, prior.write, prior.identity, prior.states
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-safe-cap-release-v1/attempt-01'
LOCAL = BASE/'fep-local-risk-correction-v1/attempt-01'
DEST = BASE/'fep-pair-conditional-risk-v1/attempt-01'
SPEC = HERE/'FEP_PAIR_CONDITIONAL_RISK_V1.md'
METHODS = ('physical', 'interval')


def compile_pairs(m):
    """Known local factors only; each incident factor occurs exactly once."""
    start = time.process_time()
    direction = signed.decreasing_model(m)
    operators, saved = [], []
    pair_bits = list(states(2))
    for edge, (i, j) in enumerate(m['edges']):
        boundary = sorted((set(m['neighbors'][i]) | set(m['neighbors'][j]))-{i, j})
        incident = [e for e, (u, v) in enumerate(m['edges']) if i in (u, v) or j in (u, v)]
        assignments = list(states(len(boundary)))
        lookup = {bits: k for k, bits in enumerate(assignments)}
        tables, values = [], [[], [], []]
        for bits in assignments:
            assignment = dict(zip(boundary, bits))
            weights = []
            for xi, xj in pair_bits:
                assignment[i], assignment[j] = xi, xj
                weight = m['prior'][i][xi]*m['prior'][j][xj]
                for e in incident:
                    u, v = m['edges'][e]
                    weight *= m['factors'][e][assignment[u]][assignment[v]]
                check(weight > ZERO, 'positive local pair weight')
                weights.append(weight)
            total = sum(weights)
            probabilities = [w/total for w in weights]
            dec_close(sum(probabilities), ONE, 'local pair conditional normalizes')
            tables.append(probabilities)
            local_values = [ZERO, ZERO, ZERO]
            for (xi, xj), probability in zip(pair_bits, probabilities):
                ti, tj = [m['h']+(TAU-m['h'])*x for x in (xi, xj)]
                for k, value in enumerate((ti, tj, ti+tj-ti*tj)):
                    local_values[k] += probability*value
            for k, value in enumerate(local_values):
                values[k].append(value)
        increments = []
        for table in values:
            inc = {}
            for axis, node in enumerate(boundary):
                differences = [table[lookup[bits[:axis]+(1,)+bits[axis+1:]]]-table[k]
                               for k, bits in enumerate(assignments) if bits[axis] == 0]
                inc[node] = dict(plus=max(ZERO, max(differences))+PAD,
                                 minus=max(ZERO, -min(differences))+PAD)
            increments.append(inc)
        op = dict(variables=boundary, assignments=assignments, lookup=lookup,
                  conditionals=tables, values=values, increments=increments)
        operators.append(op)
        saved.append(dict(edge=edge, pair=[i, j], boundary=boundary, assignments=assignments,
                          conditionals=tables, values=values, increments=increments))
    m['pair_operators'] = operators
    return dict(cpu=time.process_time()-start, direction=direction,
                max_boundary=max(len(op['variables']) for op in operators),
                boundary_assignments=sum(len(op['assignments']) for op in operators),
                conditional_pair_weights=4*sum(len(op['assignments']) for op in operators),
                expectation_terms=3*sum(len(op['assignments']) for op in operators), edges=saved)


def project(saved):
    """Only quantities already available to the preceding agent."""
    return dict(risk_view=dict(saved['agent_view']),
                selected=saved['certificate']['policies']['interval']['r'],
                previous_bound=saved['certificate']['policies']['interval']['regret']['bound'])


def available_inputs(view, h):
    release.require(set(view) == {'risk_view', 'selected', 'previous_bound'}, 'unexpected agent fields')
    values, envelopes = regret.compile_envelopes(view['risk_view'])
    dec_close(values['h'], h, 'agent and model physical baseline agree')
    selected, bound = D(view['selected']), D(view['previous_bound'])
    release.require(ZERO <= selected <= ONE and bound >= ZERO, 'invalid inherited choice or bound')
    release.require(regret.interval(envelopes['combined'], selected)[1] <= TAU+NUMTOL,
                    'inherited choice must already be certified safe')
    return values, envelopes['combined'], selected, bound


def pair_line(bounds, target_index):
    b0, b1 = bounds[target_index], bounds[2]
    return dict(l0=b0['lower'], l1=max(b0['lower'], b1['lower']),
                u0=b0['upper'], u1=max(b0['upper'], b1['upper']))


def interval_line(line, r):
    return (line['l0']+r*(line['l1']-line['l0']), line['u0']+r*(line['u1']-line['u0']))


def construct(m, q, local, views):
    """Known model, Q, available mismatch vectors and certificates only."""
    start = time.process_time()
    release.require(set(local) == {'v_plus', 'v_minus'}, 'unexpected mismatch-vector fields')
    for key in local:
        release.require(len(local[key]) == m['n'] and all(ZERO <= x <= ONE for x in local[key]),
                        'invalid mismatch-vector domain')
    release.require(len(views) == 2*len(m['edges']), 'missing available query inputs')
    check(m.get('antitone_verified', False), 'known model direction checked')
    expectation_cpu, policy_regret_cpu, queries = 0., 0., []
    for edge, ((i, j), op) in enumerate(zip(m['edges'], m['pair_operators'])):
        began = time.process_time()
        bounds = correction.action_bounds(m, op, q, local)
        pair_q = q.marginal([i, j])
        expectation_cpu += time.process_time()-began
        for orientation, (source, target) in enumerate(((i, j), (j, i))):
            view = views[2*edge+orientation]
            values, before, selected, previous_bound = available_inputs(view, m['h'])
            oriented = pair_q if source == i else {(y, x): w for (x, y), w in pair_q.items()}
            a, g = prior.pair_risks(oriented, m['h'])
            dec_close(a, values['a'], 'unchanged Q risk intercept')
            dec_close(g, values['g'], 'unchanged Q risk slope')
            target_index = 1 if target == j else 0
            line = pair_line(bounds, target_index)
            envelope = dict(lower=before['lower']+[(line['l0'], line['l1']-line['l0'])],
                            upper=before['upper']+[(line['u0'], line['u1']-line['u0'])])
            began = time.process_time()
            certificate = release.derive(m['h'], selected, ONE, envelope)
            for name, policy in certificate['policies'].items():
                final = policy['regret']
                inherited = previous_bound-policy['guaranteed_gain']+PAD
                check(inherited >= -NUMTOL, name+' inherited propagated bound nonnegative')
                final['helper_bound'] = final['bound']
                final['inherited_propagated_bound'] = max(ZERO, inherited)
                final['bound'] = min(final['bound'], previous_bound, final['inherited_propagated_bound'])
                check(final['bound'] <= previous_bound, name+' previous regret guarantee preserved')
            policy_regret_cpu += time.process_time()-began
            comparisons = {}
            for label, r in (('zero', ZERO), ('one', ONE), ('original', values['original_cap']), ('baseline', selected)):
                old_lo, old_hi = regret.interval(before, r)
                pair_lo, pair_hi = interval_line(line, r)
                new_lo, new_hi = regret.interval(envelope, r)
                check(new_lo >= old_lo-NUMTOL and new_hi <= old_hi+NUMTOL, 'new interval nests previous interval')
                comparisons[label] = dict(old_lower=old_lo, old_upper=old_hi, pair_lower=pair_lo,
                                          pair_upper=pair_hi, combined_lower=new_lo, combined_upper=new_hi)
            at_original = comparisons['original']
            classifications = {name: correction.classification(at_original[prefix+'lower'], at_original[prefix+'upper'])
                               for name, prefix in (('old', 'old_'), ('pair', 'pair_'), ('combined', 'combined_'))}
            drift = ((1-selected)*bounds[target_index]['mean']+selected*bounds[2]['mean'])-(a+selected*g)
            queries.append(dict(edge=edge, source=source, target=target, available=view,
                                pair_action_bounds=[bounds[target_index], bounds[2]], pair_line=line,
                                risk_correction=drift, comparisons=comparisons,
                                classifications=classifications, certificate=certificate))
    return dict(queries=queries, expectation_cpu=expectation_cpu, policy_regret_cpu=policy_regret_cpu,
                construct_cpu=time.process_time()-start,
                boundary_assignments=sum(len(op['assignments']) for op in m['pair_operators']),
                expectation_terms=3*sum(len(op['assignments']) for op in m['pair_operators']))


def assess(m, queries, true_pairs, previous=None, grid=None):
    records = []
    for index, row in enumerate(queries):
        pair = true_pairs[row['edge']]
        if row['source'] != m['edges'][row['edge']][0]:
            pair = {(y, x): w for (x, y), w in pair.items()}
        a, g = prior.pair_risks(pair, m['h'])
        view, cert = row['available'], row['certificate']
        values, before, selected, old_bound = available_inputs(view, m['h'])
        line = row['pair_line']
        envelope = dict(lower=before['lower']+[(line['l0'], line['l1']-line['l0'])],
                        upper=before['upper']+[(line['u0'], line['u1']-line['u0'])])
        optimum = min(prior.free(g), (TAU-a)/g)
        _, best_j = prior.score(optimum, a, g)
        baseline_risk, baseline_j = prior.score(selected, a, g)
        original_risk, _ = prior.score(values['original_cap'], a, g)
        evaluation = dict(exact_r=optimum, baseline_risk=baseline_risk,
                          baseline_regret=baseline_j-best_j, original_risk=original_risk, policies={})
        le(baseline_risk, TAU, 'baseline actual safety')
        le(evaluation['baseline_regret'], old_bound, 'inherited baseline regret bound valid')
        le(evaluation['baseline_regret'], cert['baseline']['bound'], 'refined baseline regret bound valid')
        le(cert['slope_lower'], g, 'true slope lower coverage')
        le(g, cert['slope_upper'], 'true slope upper coverage')
        le(optimum, cert['relaxed_cap'], 'relaxed global domain contains true optimum')
        le(cert['lower_optimum']['value'], best_j, 'global lower objective valid')
        points = (grid if grid is not None else [ZERO, ONE])+[values['original_cap'], selected, optimum]
        points += [p['r'] for p in cert['policies'].values()]
        for r in points:
            risk = a+r*g
            lo, hi = interval_line(line, r)
            le(lo, risk, 'pair-only risk lower coverage')
            le(risk, hi, 'pair-only risk upper coverage')
            old_lo, old_hi = regret.interval(before, r)
            new_lo, new_hi = regret.interval(envelope, r)
            check(new_lo >= old_lo-NUMTOL and new_hi <= old_hi+NUMTOL, 'evaluated interval nesting')
            le(new_lo, risk, 'combined risk lower coverage')
            le(risk, new_hi, 'combined risk upper coverage')
        for name, classification in row['classifications'].items():
            if classification == 'safe':
                le(original_risk, TAU, name+' original safe classification valid')
            if classification == 'unsafe':
                le(TAU, original_risk, name+' original unsafe classification valid')
        for name, p in cert['policies'].items():
            risk, objective = prior.score(p['r'], a, g)
            gain, actual_regret = baseline_j-objective, objective-best_j
            le(risk, TAU, name+' actual safety')
            le(risk, p['certified_risk_upper'], name+' certified upper covers risk')
            le(objective, baseline_j, name+' objective nonworsening')
            le(p['guaranteed_gain'], gain, name+' improvement guarantee valid')
            le(0, actual_regret, name+' actual regret nonnegative')
            for field in ('level_bound', 'slope_bound', 'direct_bound', 'propagated_bound', 'helper_bound',
                          'inherited_propagated_bound', 'bound'):
                le(actual_regret, p['regret'][field], name+' '+field+' covers regret')
            evaluation['policies'][name] = dict(risk=risk, objective=objective, gain=gain, regret=actual_regret)
        primary, control = [evaluation['policies'][n] for n in ('interval', 'physical')]
        advantage = control['objective']-primary['objective']
        le(0, advantage, 'interval rule no worse than physical control')
        le(cert['primary_over_control_guarantee'], advantage, 'primary versus control guarantee valid')
        evaluation['primary_over_control_gain'] = advantage
        if previous is not None:
            old_row = previous[index]
            check(all(row[k] == old_row[k] for k in ('edge', 'source', 'target')), 'previous query correspondence')
            old_ev = old_row['evaluation']['policies']['interval']
            close(baseline_risk, old_ev['risk'], 'reproduced previous risk')
            close(evaluation['baseline_regret'], old_ev['global_regret'], 'reproduced previous regret')
            close(optimum, old_row['evaluation']['exact_r'], 'reproduced exact optimum')
        records.append(dict(**row, evaluation=evaluation))
    return records


def verify_small(m, q, weights, queries):
    full_q = q.marginal(list(range(m['n'])))
    negative = False
    for edge, ((i, j), op) in enumerate(zip(m['edges'], m['pair_operators'])):
        for k, bits in enumerate(op['assignments']):
            matching = {s: w for s, w in weights.items() if tuple(s[n] for n in op['variables']) == bits}
            denominator = sum(matching.values())
            for pair_index, pair_bits in enumerate(states(2)):
                conditional = sum(w for s, w in matching.items() if (s[i], s[j]) == pair_bits)/denominator
                dec_close(conditional, op['conditionals'][k][pair_index], 'pair conditional from independent full joint')
        bounds = [queries[2*edge+1]['pair_action_bounds'][0], queries[2*edge]['pair_action_bounds'][0],
                  queries[2*edge]['pair_action_bounds'][1]]
        for function_index, table in enumerate(op['values']):
            transformed = {bits: table[op['lookup'][tuple(bits[n] for n in op['variables'])]] for bits in weights}
            physical = {}
            for bits in weights:
                ti, tj = [m['h']+(TAU-m['h'])*bits[n] for n in (i, j)]
                physical[bits] = (ti, tj, ti+tj-ti*tj)[function_index]
                k = op['lookup'][tuple(bits[n] for n in op['variables'])]
                repeated = ZERO
                for (xi, xj), probability in zip(states(2), op['conditionals'][k]):
                    updated = list(bits)
                    updated[i], updated[j] = xi, xj
                    repeated += probability*transformed[tuple(updated)]
                dec_close(repeated, transformed[bits], 'pair projection idempotent')
            true_before = sum(w*physical[bits] for bits, w in weights.items())
            true_after = sum(w*transformed[bits] for bits, w in weights.items())
            q_before = sum(w*physical[bits] for bits, w in full_q.items())
            q_after = sum(w*transformed[bits] for bits, w in full_q.items())
            drift = sum(w*(transformed[bits]-physical[bits]) for bits, w in full_q.items())
            dec_close(true_before, true_after, 'pair projection preserves posterior expectation')
            dec_close(q_after, bounds[function_index]['mean'], 'boundary expectation matches full Q expectation')
            dec_close(true_before-q_before, drift+(true_after-q_after), 'pair correction remainder identity')
            le(true_after-q_after, bounds[function_index]['error_plus'], 'direct upward remainder coverage')
            le(q_after-true_after, bounds[function_index]['error_minus'], 'direct downward remainder coverage')
            for node in range(m['n']):
                differences = [transformed[bits[:node]+(1,)+bits[node+1:]]-value
                               for bits, value in transformed.items() if bits[node] == 0]
                plus, minus = max(ZERO, max(differences)), max(ZERO, -min(differences))
                if node in op['variables']:
                    inc = op['increments'][function_index][node]
                    dec_close(plus+PAD, inc['plus'], 'full-state positive boundary increment')
                    dec_close(minus+PAD, inc['minus'], 'full-state negative boundary increment')
                    negative |= minus > NUMTOL
                else:
                    check(plus == minus == ZERO, 'eliminated and off-boundary increments exactly zero')
            if not op['variables']:
                check(bounds[function_index]['error_plus'] == bounds[function_index]['error_minus'] == ZERO,
                      'empty boundary has zero mismatch remainder')
                dec_close(q_after, true_before, 'empty boundary gives exact risk expectation')
    return negative


def qualify():
    output, negative = [], False

    def one_model(m, label, choices):
        nonlocal negative
        correction.compile_operators(m)
        prepared = compile_pairs(m)
        weights, pairs, _ = prior.enumerate_reference(m)
        signed.direct_conditionals(m, weights)
        for kind in choices:
            if kind == 'exact':
                q = prior.Belief([list(range(m['n']))], [list(weights.values())])
            elif kind == 'paired_chain':
                q = prior.Belief([[0, 1], [2]], [[D('.1'), D('.3'), D('.2'), D('.4')], [D('.6'), D('.4')]])
            else:
                means = [HALF]*m['n'] if kind == 'prior' else [D('.3'), D('.7'), D('.4')][:m['n']]
                q = prior.Belief([[i] for i in range(m['n'])], [[1-p, p] for p in means])
            baseline = correction.construct(m, q)
            signed.direct_signed_residuals(m, q, {'primary': baseline['local']})
            views = []
            for row in baseline['queries']:
                risk_view = regret.whitelist(m['h'], baseline['local'], row)
                _, released = release.construct(risk_view)
                views.append(dict(risk_view=risk_view, selected=released['policies']['interval']['r'],
                                  previous_bound=released['policies']['interval']['regret']['bound']))
            local = {key: baseline['local'][key] for key in ('v_plus', 'v_minus')}
            new = construct(m, q, local, views)
            negative |= verify_small(m, q, weights, new['queries'])
            records = assess(m, new['queries'], pairs, grid=[ZERO, D('.25'), HALF, D('.75'), ONE])
            output.append(dict(model=label, h=m['h'], kind=kind, alpha=m['alpha'], operator=prepared, queries=records))

    for h in (D('1e-6'), D('.01')):
        for observation in (0, 1):
            m = prior.model_from_saved(dict(h=h, prior=[[HALF, HALF]]*2, edges=[(0, 1)], observations=[observation]))
            one_model(m, 'two_node_'+str(observation), ('prior', 'asymmetric', 'exact'))
    edges = [(i, j) for i in range(4) for j in range(i+1, 4)]
    m = prior.compile_model([[HALF, HALF]]*4, edges, [[[D('.0001'), ONE], [ONE, D('.0001')]]]*6, D('.01'))
    one_model(m, 'noncontractive_K4', ('prior',))
    check(m['alpha'] > ONE, 'noncontractive pair control exercised')
    m = prior.compile_model([[.6, .4], [.45, .55], [.7, .3]], [(0, 1), (2, 1)],
                            [[[.02, .1], [.08, .19]], [[.03, .09], [.07, .16]]], D('.01'))
    one_model(m, 'oriented_chain', ('asymmetric', 'paired_chain', 'exact'))
    check(negative, 'negative boundary influence exercised')
    m = prior.compile_model([[HALF, HALF]]*2, [(0, 1)], [[[2, 1], [1, 2]]], D('.01'))
    reason = ''
    try:
        compile_pairs(m)
    except ValueError as error:
        reason = str(error)
    check(reason == 'increasing posterior conditional: signed antitone method unsupported',
          'increasing model rejected for signed-bound assumption')
    output.append(dict(model='unsupported_increasing_factor', rejected=True, reason=reason))
    check(len(output) == 17, 'all fixed mathematical controls retained')
    return output


def summarize(records):
    result = dict(queries=len(records),
                  old_mean_r=stats.fmean(float(q['available']['selected']) for q in records),
                  exact_mean_r=stats.fmean(float(q['evaluation']['exact_r']) for q in records),
                  old_mean_regret=stats.fmean(q['evaluation']['baseline_regret'] for q in records),
                  old_mean_bound=stats.fmean(float(q['available']['previous_bound']) for q in records),
                  refined_baseline_mean_bound=stats.fmean(float(q['certificate']['baseline']['bound']) for q in records),
                  mean_risk_correction=stats.fmean(float(q['risk_correction']) for q in records),
                  policy_disagreements=sum(float(q['certificate']['policies']['interval']['r']-
                                                 q['certificate']['policies']['physical']['r']) > TIE for q in records),
                  classifications={name: dict(Counter(q['classifications'][name] for q in records))
                                   for name in ('old', 'pair', 'combined')}, standalone={})
    for point in ('zero', 'one', 'original', 'baseline'):
        cc = [q['comparisons'][point] for q in records]
        result['standalone'][point] = {}
        for side in ('lower', 'upper'):
            change = [(float(c['pair_'+side])-float(c['old_'+side]))*(1 if side == 'lower' else -1) for c in cc]
            result['standalone'][point][side] = dict(improved=sum(v > TIE for v in change),
                                                     worsened=sum(v < -TIE for v in change),
                                                     tied=sum(abs(v) <= TIE for v in change), mean_improvement=stats.fmean(change))
    for name in METHODS:
        pp = [q['certificate']['policies'][name] for q in records]
        ee = [q['evaluation']['policies'][name] for q in records]
        result[name] = dict(mean_r=stats.fmean(float(p['r']) for p in pp),
                            mean_risk=stats.fmean(e['risk'] for e in ee), max_risk=max(e['risk'] for e in ee),
                            mean_regret=stats.fmean(e['regret'] for e in ee), max_regret=max(e['regret'] for e in ee),
                            mean_gain=stats.fmean(e['gain'] for e in ee),
                            mean_guaranteed_gain=stats.fmean(float(p['guaranteed_gain']) for p in pp),
                            changed=sum(float(p['r'])-float(q['available']['selected']) > TIE for p, q in zip(pp, records)),
                            improved=sum(e['gain'] > TIE for e in ee), worsened=sum(e['gain'] < -TIE for e in ee),
                            limits=dict(Counter(p['limit'] for p in pp)))
        for field in ('level_bound', 'slope_bound', 'direct_bound', 'propagated_bound', 'helper_bound',
                      'inherited_propagated_bound', 'bound'):
            result[name]['mean_'+field] = stats.fmean(float(p['regret'][field]) for p in pp)
        result[name]['max_bound'] = max(float(p['regret']['bound']) for p in pp)
        result[name]['mean_bound_slack'] = stats.fmean(float(p['regret']['bound'])-e['regret'] for p, e in zip(pp, ee))
    return result


def aggregate(rows):
    result = {}
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [r for r in rows if r['kind'] == kind and r['level'] == level]
            item = {key: stats.fmean(r[key] for r in rr) for key in
                    ('old_mean_r', 'exact_mean_r', 'old_mean_regret', 'old_mean_bound', 'refined_baseline_mean_bound',
                     'mean_risk_correction', 'q_reconstruction_cpu', 'expectation_cpu', 'policy_regret_cpu', 'construct_cpu')}
            item.update({key: sum(r[key] for r in rr) for key in ('queries', 'policy_disagreements', 'boundary_assignments', 'expectation_terms')})
            item['classifications'] = {}
            for name in ('old', 'pair', 'combined'):
                total = Counter()
                for row in rr:
                    total.update(row['classifications'][name])
                item['classifications'][name] = dict(total)
            item['standalone'] = {}
            for point in ('zero', 'one', 'original', 'baseline'):
                item['standalone'][point] = {}
                for side in ('lower', 'upper'):
                    cc = [r['standalone'][point][side] for r in rr]
                    item['standalone'][point][side] = {field: (stats.fmean if field == 'mean_improvement' else sum)(c[field] for c in cc)
                                                     for field in cc[0]}
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
    log.write('Sixteen accepted small-model cases and the increasing-model rejection passed.\n')
    log.flush()
    for path in (MAIN/'MANIFEST.json', OLD/'MANIFEST.json', LOCAL/'MANIFEST.json'):
        signed.verify_manifest(path)
    core, previous, local_record = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json'), read(LOCAL/'RESULTS.json')
    check(not core['gate']['passed'], 'failed original mechanism gate preserved')
    local_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in local_record['rows']}
    previous_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in previous['rows']}
    previous_queries = {}
    with (OLD/'QUERIES.jsonl').open() as stream:
        for line in stream:
            q = json.loads(line)
            previous_queries.setdefault((q['fixture'], q['kind'], q['order'], q['level']), []).append(q)
    models, model_rows, rows, count = {}, {}, [], 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture, kind, order = [case[k] for k in ('fixture', 'kind', 'order')]
            job = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')
            if fixture not in models:
                m = prior.model_from_saved(job['model'])
                prepared = compile_pairs(m)
                check(prepared['max_boundary'] <= 6, 'grid boundary at most six causes')
                models[fixture] = m
                model_rows[fixture] = dict(model_reconstruction_cpu=m['prepare_cpu'], operator=prepared,
                                           inherited_prepare_cpu=local_record['models'][fixture]['total_prepare_cpu'],
                                           incremental_pipeline_prepare_cpu=local_record['models'][fixture]['total_prepare_cpu']+prepared['cpu'])
            m = models[fixture]
            for level, snapshot in zip((256, 1024, 4096), job['snapshots']):
                key = (fixture, kind, order, level)
                began = time.process_time()
                q = prior.Belief(snapshot['groups'], [[D(str(x)).exp() for x in block]
                                                    for block in snapshot['block_log_probabilities']])
                q_cpu = time.process_time()-began
                local = {k: [D(x) for x in local_rows[key]['local'][k]] for k in ('v_plus', 'v_minus')}
                views = [project(saved) for saved in previous_queries[key]]
                certificate = construct(m, q, local, views)
                # All new policies and certificates exist before exact-reference access.
                ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                pairs = [{bits: D(str(p[bits[0]][bits[1]])) for bits in states(2)} for p in ref['pairs']]
                records = assess(m, certificate['queries'], pairs, previous=previous_queries[key])
                for row in records:
                    stream.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **row),
                                            default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summarize(records)
                before = previous_rows[key]
                close(summary['old_mean_r'], before['interval']['mean_r'], 'previous mean action reproduced')
                close(summary['old_mean_regret'], before['interval']['mean_regret'], 'previous mean regret reproduced')
                close(summary['old_mean_bound'], before['interval']['mean_bound'], 'previous mean bound reproduced')
                check(summary['classifications']['old'] == local_rows[key]['combined']['classifications'], 'previous classifications reproduced')
                rows.append(dict(fixture=fixture, kind=kind, order=order, level=level, q_reconstruction_cpu=q_cpu,
                                 **{k: certificate[k] for k in ('expectation_cpu', 'policy_regret_cpu', 'construct_cpu', 'boundary_assignments', 'expectation_terms')},
                                 preceding_risk_certificate_cpu=before['preceding_certificate_cpu'],
                                 preceding_policy_cpu=before['policy_cpu'], preceding_regret_cpu=before['regret_cpu'],
                                 main_cost=before['main_cost'], **summary))
                count += len(records)
            log.write(f'Completed {fixture} {kind} {order}; all budgets retained.\n')
            log.flush()
    check(len(rows) == 96 and count == 13056, 'all saved checkpoints and queries retained')
    return dict(qualification=qualification, models=model_rows, rows=rows, summary=aggregate(rows),
                checkpoints=len(rows), original_queries=count, new_policy_evaluations=2*count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted pair output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen pair checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen pair specification')
    helpers = [(Path(release.__file__), '5888e2db569798d840f1a8e67236e8762bdf718e52f6c28f6a170d19c6744f9d', 'REUSED_CAP_RELEASE_HELPER.py'),
               (Path(regret.__file__), '961ebf6505e74b562c1baf6fd9da0d9ea2cadbb3af7fd391945511b14b1d1d70', 'REUSED_REGRET_HELPER.py'),
               (Path(correction.__file__), '2dc09583c43bdc236506d262de84cbc36b859656cff2449bba3392e6ea09368f', 'REUSED_CORRECTION_HELPER.py'),
               (Path(signed.__file__), 'a6029890e806a64c8bf61ec1932c86a54400bede75e5d1b38e78935f5c9c1bc4', 'REUSED_SIGNED_HELPER.py'),
               (Path(prior.__file__), 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6', 'REUSED_NUMERICAL_HELPER.py')]
    for path, sha, _ in helpers:
        check(identity(path)['sha256'] == sha, 'unchanged '+path.name)
    check(identity(OLD/'MANIFEST.json')['sha256'] == '59b2277408c405e14a56b54f9f7fcf88357d4e34e37e7829c479f13c996dfcd5', 'pinned cap-release record')
    check(identity(LOCAL/'MANIFEST.json')['sha256'] == 'dddd352612b2c8c1f0d2d19c8625e2ad0e725ffe60f81838e2cb4e2977c739bf', 'pinned signed-vector record')
    paths = [SPEC, Path(__file__)]+[p for p, _, _ in helpers]+[
        HERE/'FEP_SAFE_CAP_RELEASE_V1.md', HERE/'FEP_SAFE_CAP_RELEASE_V1_REPORT.md',
        HERE/'FEP_LOCAL_RISK_CORRECTION_V1.md', HERE/'FEP_LOCAL_RISK_CORRECTION_V1_REPORT.md',
        OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl', LOCAL/'MANIFEST.json', LOCAL/'RESULTS.json',
        MAIN/'MANIFEST.json', MAIN/'CORE.json', MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
        HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    copies = [(SPEC, 'SPECIFICATION.md'), (Path(__file__), 'CHECKER_SOURCE.py')]+[(p, name) for p, _, name in helpers]
    for path, name in copies:
        (DEST/name).write_bytes(path.read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='full local pair averaging on fixed beliefs; saved signed mismatch bounds; no inference updates',
                    cpu_processes=1, python=platform.python_version(), decimal_precision=60,
                    selected_stopping_tolerance=None, pair_operator='exact conditional expectation given pair boundary')
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
            log.write(f"Passed {result['assertions']} checks and {result['new_policy_evaluations']} policy evaluations.\n")
            print(json.dumps({k: result[k] for k in ('status', 'assertions', 'elapsed_seconds', 'cpu_seconds',
                             'checkpoints', 'original_queries', 'new_policy_evaluations', 'summary')}, default=prior.encode, indent=2))
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
