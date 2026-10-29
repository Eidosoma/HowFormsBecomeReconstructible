#!/usr/bin/env python3
"""Direct mixed-action remainder on immutable pair tables and saved beliefs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
from itertools import groupby
import json
import os
from pathlib import Path
import platform
import statistics as stats
import time
import traceback

import check_fep_pair_conditional_risk as pair

correction, signed, prior, regret, release = pair.correction, pair.signed, pair.prior, pair.regret, pair.release
ZERO, ONE, HALF, TAU, PAD = pair.ZERO, pair.ONE, pair.HALF, pair.TAU, pair.PAD
NUMTOL, TOL, TIE = pair.NUMTOL, pair.TOL, pair.TIE
check, close, dec_close, le = pair.check, pair.close, pair.dec_close, pair.le
read, write, identity, states = pair.read, pair.write, pair.identity, pair.states
require = release.require
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-pair-conditional-risk-v1/attempt-01'
LOCAL = BASE/'fep-local-risk-correction-v1/attempt-01'
DEST = BASE/'fep-mixed-action-risk-v1/attempt-01'
SPEC = HERE/'FEP_MIXED_ACTION_RISK_V1.md'
METHODS = ('chord', 'physical', 'interval')
GRID = {'zero': ZERO, 'quarter': D('.25'), 'half': HALF, 'three_quarters': D('.75'), 'one': ONE}


def affine(line, r):
    return line[0]+line[1]*r


def hull(lines):
    """Upper envelope of lines on [0,1], with an endpoint dominance check."""
    parallel = {}
    for a, b in lines:
        parallel[b] = max(a, parallel.get(b, a))
    active, starts = [], []
    for b, a in sorted(parallel.items()):
        while active:
            crossing = (active[-1][0]-a)/(b-active[-1][1])
            if starts[-1] is None or crossing > starts[-1]:
                break
            active.pop()
            starts.pop()
        starts.append(crossing if active else None)
        active.append((a, b))
    result = []
    for i, line in enumerate(active):
        left = ZERO if starts[i] is None else max(ZERO, starts[i])
        right = min(ONE, starts[i+1]) if i+1 < len(starts) else ONE
        if left < right:
            result.append(dict(left=left, right=right, line=line))
    check(result[0]['left'] == ZERO and result[-1]['right'] == ONE, 'hull covers full domain')
    for i, segment in enumerate(result):
        if i:
            check(result[i-1]['right'] == segment['left'], 'hull has no gaps')
            check(result[i-1]['line'][1] < segment['line'][1], 'hull slopes increase')
        for r in (segment['left'], segment['right']):
            # Affine dominance at both cell endpoints proves it throughout that cell.
            dec_close(affine(segment['line'], r), max(affine(line, r) for line in lines),
                      'hull endpoint equals direct maximum')
    return result


def active_line(segments, r):
    return next(s['line'] for s in segments if s['left'] <= r <= s['right'])


def compile_tables(source):
    """Project only known-model local function tables, no posterior reference."""
    start = time.process_time()
    queries = []
    for saved in source:
        op = {k: saved[k] for k in ('edge', 'pair', 'boundary', 'assignments', 'values')}
        assignments = [tuple(x) for x in op['assignments']]
        lookup = {x: i for i, x in enumerate(assignments)}
        values = [list(map(D, row)) for row in op['values']]
        check(len(assignments) == 2**len(op['boundary']), 'complete pair boundary table')
        for orientation in (0, 1):
            source_node, target = op['pair'][orientation], op['pair'][1-orientation]
            h0, h1 = values[1-orientation], values[2]
            check(all(a <= b+NUMTOL for a, b in zip(h0, h1)), 'pure transformed risk ordering')
            parts, breaks = [], {ZERO, ONE}
            for axis, node in enumerate(op['boundary']):
                lines = [(ZERO, ZERO)]
                for index, bits in enumerate(assignments):
                    if bits[axis] == 0:
                        other = lookup[bits[:axis]+(1,)+bits[axis+1:]]
                        d0, d1 = h0[other]-h0[index], h1[other]-h1[index]
                        lines.append((d0, d1-d0))
                positive, negative = hull(lines), hull([(-a, -b) for a, b in lines])
                for segment in positive+negative:
                    breaks.update((segment['left'], segment['right']))
                parts.append(dict(node=node, lines=lines, positive=positive, negative=negative))
            queries.append(dict(edge=op['edge'], source=source_node, target=target, parts=parts,
                                breaks=sorted(breaks)))
    return dict(cpu=time.process_time()-start, queries=queries,
                raw_lines=sum(len(p['lines']) for q in queries for p in q['parts']),
                hull_pieces=sum(len(p[s]) for q in queries for p in q['parts'] for s in ('positive', 'negative')),
                cells=sum(len(q['breaks'])-1 for q in queries),
                max_cells=max(len(q['breaks'])-1 for q in queries))


def project(saved):
    return dict(risk_view=dict(saved['available']['risk_view']), pair_line=dict(saved['pair_line']),
                means=[b['mean'] for b in saved['pair_action_bounds']],
                selected=saved['certificate']['policies']['interval']['r'],
                previous_bound=saved['certificate']['policies']['interval']['regret']['bound'])


def available_inputs(view):
    require(set(view) == {'risk_view', 'pair_line', 'means', 'selected', 'previous_bound'},
            'unexpected mixed agent fields')
    values, envs = regret.compile_envelopes(view['risk_view'])
    require(set(view['pair_line']) == {'l0', 'l1', 'u0', 'u1'}, 'unexpected pair endpoint fields')
    line = {k: D(v) for k, v in view['pair_line'].items()}
    env = envs['combined']
    env['lower'].append((line['l0'], line['l1']-line['l0']))
    env['upper'].append((line['u0'], line['u1']-line['u0']))
    require(len(view['means']) == 2, 'two pure transformed means required')
    means = list(map(D, view['means']))
    require(values['h']-NUMTOL <= means[0] <= TAU+NUMTOL and
            means[0] <= means[1]+NUMTOL <= TAU*(2-TAU)+2*NUMTOL, 'invalid transformed mean range')
    selected, bound = D(view['selected']), D(view['previous_bound'])
    require(ZERO <= selected <= ONE and bound >= ZERO, 'invalid inherited choice or bound')
    regret.validate_inputs(values['h'], selected, ONE, dict(signed=env, combined=env))
    return values, env, means, selected, bound


def weighted_cells(op, means, local):
    cells = []
    for left, right in zip(op['breaks'], op['breaks'][1:]):
        middle = (left+right)/2
        plus, minus = [ZERO, ZERO], [ZERO, ZERO]
        for part in op['parts']:
            vp, vm = local['v_plus'][part['node']], local['v_minus'][part['node']]
            pp, nn = active_line(part['positive'], middle), active_line(part['negative'], middle)
            for axis in (0, 1):
                padding = PAD if axis == 0 else ZERO
                plus[axis] += (pp[axis]+padding)*vp+(nn[axis]+padding)*vm
                minus[axis] += (pp[axis]+padding)*vm+(nn[axis]+padding)*vp
        mean = (means[0], means[1]-means[0])
        lower = (mean[0]-minus[0]-PAD, mean[1]-minus[1])
        upper = (mean[0]+plus[0]+PAD, mean[1]+plus[1])
        cells.append(dict(left=left, right=right, lower=lower, upper=upper, error_plus=plus, error_minus=minus))
    return cells


def mixed_at(cells, r):
    cell = next(c for c in cells if c['left'] <= r <= c['right'])
    return {k: affine(cell[k], r) for k in ('lower', 'upper', 'error_plus', 'error_minus')}


def direct_errors(op, local, r):
    plus, minus = ZERO, ZERO
    for part in op['parts']:
        changes = [affine(line, r) for line in part['lines']]
        wp, wm = max(changes)+PAD, -min(changes)+PAD
        vp, vm = local['v_plus'][part['node']], local['v_minus'][part['node']]
        plus += wp*vp+wm*vm
        minus += wp*vm+wm*vp
    return plus, minus


def chord_cell(cells):
    start, end = mixed_at(cells, ZERO), mixed_at(cells, ONE)
    return [dict(left=ZERO, right=ONE, **{k: (start[k], end[k]-start[k]) for k in start})]


def safe_intervals(cells):
    intervals = []
    for index, cell in enumerate(cells):
        left, right, (a, b) = cell['left'], cell['right'], cell['upper']
        target = TAU-PAD
        if b > 0:
            right = min(right, (target-a)/b)
        elif b < 0:
            left = max(left, (target-a)/b)
        elif a > target:
            continue
        if left <= right:
            check(ZERO <= left <= right <= ONE, 'raw safe cell within domain')
            check(max(a+b*left, a+b*right) <= TAU+NUMTOL, 'raw safe cell endpoints certified')
            intervals.append(dict(left=left, right=right, cell=index))
    return intervals


def choose(selected, old_ceiling, intervals, guard, cache):
    free_guard = max(ZERO, cache.stationary(guard)-PAD)
    candidates = [(selected, 'baseline')]
    if selected < free_guard:
        candidates.append((max(selected, min(old_ceiling, free_guard)), 'previous'))
        for item in intervals:
            left, right = max(selected, item['left']), min(free_guard, item['right'])
            if left <= right:
                candidates.append((right, 'raw_cell_'+str(item['cell'])))
    chosen, witness = max(candidates, key=lambda x: x[0])
    if chosen == selected:
        limit = 'hold_objective' if free_guard <= selected else 'hold_safety'
    else:
        limit = 'objective' if chosen == free_guard else 'risk'
    return dict(r=chosen, free_guard=free_guard, slope_guard=guard, witness=witness, limit=limit,
                guaranteed_gain=release.guaranteed_gain(selected, chosen, guard, cache))


def policies(h, selected, previous_bound, env, cells, chord, intervals, chord_intervals):
    start = time.process_time()
    ceiling = release.safe_ceiling(env, selected)
    l0, u0 = regret.interval(env, ZERO)
    l1, u1 = regret.interval(env, ONE)
    glo, ghi = max(h*(1-TAU), l1-u0-PAD), min(TAU*(1-h), u1-l0+PAD)
    require(glo <= ghi+NUMTOL, 'empty inherited slope interval')
    cache = regret.ScalarCache()
    result = {}
    for name in METHODS:
        source = chord if name == 'chord' else cells
        safe = chord_intervals if name == 'chord' else intervals
        guard = TAU*(1-h) if name == 'physical' else ghi
        item = choose(selected, ceiling['value'], safe, guard, cache)
        raw = mixed_at(source, item['r'])
        item['certified_risk_upper'] = min(regret.interval(env, item['r'])[1], raw['upper'])
        check(item['certified_risk_upper'] <= TAU+NUMTOL, name+' chosen action certified safe')
        propagated = previous_bound-item['guaranteed_gain']+PAD
        check(propagated >= -NUMTOL, name+' propagated regret nonnegative')
        item['propagated_bound'] = max(ZERO, propagated)
        item['bound'] = min(previous_bound, item['propagated_bound'])
        result[name] = item
    check(selected <= result['physical']['r'] <= result['interval']['r'], 'physical interval action ordering')
    check(selected <= result['chord']['r'] <= result['interval']['r']+NUMTOL, 'direct interval contains chord choices')
    advantage = {name: release.guaranteed_gain(result[name]['r'], max(result[name]['r'], result['interval']['r']), ghi, cache)
                 for name in ('physical', 'chord')}
    return dict(old_ceiling=ceiling, raw_intervals=intervals, chord_intervals=chord_intervals,
                slope_lower=glo, slope_upper=ghi, policies=result, advantage_guarantees=advantage,
                cpu=time.process_time()-start, entropy_calls=cache.entropy_calls, stationary_calls=cache.stationary_calls)


def construct(prepared, views, local):
    """Only known local tables and explicitly projected available inputs."""
    start = time.process_time()
    require(set(local) == {'v_plus', 'v_minus'}, 'unexpected mismatch-vector fields')
    require(len(local['v_plus']) == len(local['v_minus']) and
            all(ZERO <= v <= ONE for values in local.values() for v in values), 'invalid mismatch vectors')
    require(len(views) == len(prepared['queries']), 'missing mixed-action query inputs')
    queries, remainder_cpu, policy_cpu, diagnostic_cpu = [], 0., 0., 0.
    for op, view in zip(prepared['queries'], views):
        values, env, means, selected, previous_bound = available_inputs(view)
        began = time.process_time()
        cells = weighted_cells(op, means, local)
        chord = chord_cell(cells)
        safe, chord_safe = safe_intervals(cells), safe_intervals(chord)
        remainder_cpu += time.process_time()-began
        cert = policies(values['h'], selected, previous_bound, env, cells, chord, safe, chord_safe)
        policy_cpu += cert['cpu']
        began = time.process_time()
        points = dict(GRID, original=values['original_cap'], baseline=selected,
                      **{'chosen_'+name: p['r'] for name, p in cert['policies'].items()})
        comparisons = {}
        for label, r in points.items():
            direct, interpolated = mixed_at(cells, r), mixed_at(chord, r)
            plus, minus = direct_errors(op, local, r)
            dec_close(direct['error_plus'], plus, 'mixed cell agrees with direct positive maximum')
            dec_close(direct['error_minus'], minus, 'mixed cell agrees with direct negative maximum')
            check(plus <= interpolated['error_plus']+NUMTOL and minus <= interpolated['error_minus']+NUMTOL,
                  'direct remainder no larger than endpoint chord')
            old_lo, old_hi = regret.interval(env, r)
            new_lo, new_hi = max(old_lo, direct['lower']), min(old_hi, direct['upper'])
            chord_lo, chord_hi = max(old_lo, interpolated['lower']), min(old_hi, interpolated['upper'])
            check(new_lo >= chord_lo-NUMTOL and new_hi <= chord_hi+NUMTOL, 'direct envelope nests chord envelope')
            check(new_lo <= new_hi+NUMTOL, 'mixed interval consistent')
            comparisons[label] = dict(r=r, raw=direct, chord_raw=interpolated, old_lower=old_lo, old_upper=old_hi,
                                      chord_lower=chord_lo, chord_upper=chord_hi, lower=new_lo, upper=new_hi,
                                      cancellation_plus=interpolated['error_plus']-plus,
                                      cancellation_minus=interpolated['error_minus']-minus)
        original = comparisons['original']
        classes = {name: correction.classification(original[lo], original[hi]) for name, lo, hi in
                   (('old', 'old_lower', 'old_upper'), ('chord', 'chord_lower', 'chord_upper'), ('combined', 'lower', 'upper'))}
        if classes['old'] != 'unresolved':
            check(classes['old'] == classes['combined'], 'previous classification retained')
        diagnostic_cpu += time.process_time()-began
        queries.append(dict(edge=op['edge'], source=op['source'], target=op['target'], available=view,
                            cells=cells, certificate=cert, comparisons=comparisons, classifications=classes))
    return dict(queries=queries, remainder_cpu=remainder_cpu, policy_cpu=policy_cpu,
                diagnostic_cpu=diagnostic_cpu, construct_cpu=time.process_time()-start,
                cells=sum(len(q['cells']) for q in queries))


def assess(queries, true_pairs, edges, h, previous=None):
    records = []
    for index, row in enumerate(queries):
        pp = true_pairs[row['edge']]
        if row['source'] != edges[row['edge']][0]:
            pp = {(y, x): w for (x, y), w in pp.items()}
        a, g = prior.pair_risks(pp, h)
        optimum = min(prior.free(g), (TAU-a)/g)
        _, best_j = prior.score(optimum, a, g)
        selected, previous_bound = D(row['available']['selected']), D(row['available']['previous_bound'])
        baseline_risk, baseline_j = prior.score(selected, a, g)
        baseline_regret = baseline_j-best_j
        original_risk = a+D(row['available']['risk_view']['original_cap'])*g
        cert = row['certificate']
        le(baseline_risk, TAU, 'baseline true safety')
        le(baseline_regret, previous_bound, 'baseline global regret bound valid')
        le(cert['slope_lower'], g, 'inherited true slope lower coverage')
        le(g, cert['slope_upper'], 'inherited true slope upper coverage')
        for comp in row['comparisons'].values():
            risk = a+comp['r']*g
            for name in ('raw', 'chord_raw'):
                le(comp[name]['lower'], risk, name+' risk lower coverage')
                le(risk, comp[name]['upper'], name+' risk upper coverage')
            le(comp['lower'], risk, 'combined risk lower coverage')
            le(risk, comp['upper'], 'combined risk upper coverage')
        for name, classification in row['classifications'].items():
            if classification == 'safe':
                le(original_risk, TAU, name+' original classification safe')
            elif classification == 'unsafe':
                le(TAU, original_risk, name+' original classification unsafe')
        evaluation = dict(exact_r=optimum, baseline_risk=baseline_risk, baseline_regret=baseline_regret,
                          original_risk=original_risk, policies={})
        for name, policy in cert['policies'].items():
            risk, objective = prior.score(policy['r'], a, g)
            gain, actual_regret = baseline_j-objective, objective-best_j
            le(risk, TAU, name+' actual safety')
            le(risk, policy['certified_risk_upper'], name+' certified upper covers actual risk')
            le(0, gain, name+' objective nonworsening')
            le(policy['guaranteed_gain'], gain, name+' gain guarantee valid')
            le(0, actual_regret, name+' actual regret nonnegative')
            le(actual_regret, policy['bound'], name+' propagated global regret valid')
            evaluation['policies'][name] = dict(risk=risk, objective=objective, gain=gain, regret=actual_regret)
        for name in ('physical', 'chord'):
            gain = evaluation['policies'][name]['objective']-evaluation['policies']['interval']['objective']
            le(cert['advantage_guarantees'][name], gain, 'primary advantage over '+name)
            evaluation['advantage_over_'+name] = gain
        if previous is not None:
            old = previous[index]
            check(all(row[k] == old[k] for k in ('edge', 'source', 'target')), 'preceding query identity')
            close(baseline_risk, old['evaluation']['policies']['interval']['risk'], 'preceding risk reproduced')
            close(baseline_regret, old['evaluation']['policies']['interval']['regret'], 'preceding regret reproduced')
            close(optimum, old['evaluation']['exact_r'], 'exact comparator reproduced')
            check(row['classifications']['old'] == old['classifications']['combined'], 'preceding classification reproduced')
        records.append(dict(**row, evaluation=evaluation))
    return records


def qualify_algorithms():
    cases = {
        'constant': [(1, 0)],
        'parallel': [(1, 0), (0, 0), (1, 0)],
        'interior_kink': [(0, 1), ('.4', '-1')],
        'three_active': [('0', '0'), ('-.2', '1'), ('-.9', '2')],
        'endpoint_zero': [('0', '-1'), ('0', '1')],
        'endpoint_one': [('0', '1'), ('-1', '2')],
        'outside': [('0', '0'), ('-2', '1')],
    }
    output = []
    for name, raw in cases.items():
        lines = [tuple(map(D, line)) for line in raw]
        segments = hull(lines)
        points = {ZERO, ONE}
        for a, b in lines:
            for aa, bb in lines:
                if b != bb:
                    crossing = (aa-a)/(b-bb)
                    if ZERO <= crossing <= ONE:
                        points.add(crossing)
        ordered = sorted(points)
        points.update((l+r)/2 for l, r in zip(ordered, ordered[1:]))
        for r in points:
            dec_close(affine(active_line(segments, r), r), max(affine(line, r) for line in lines),
                      'independent hull crossing and midpoint control')
        output.append(dict(name=name, lines=lines, hull=segments, points=sorted(points)))
    lines = [(ZERO, ZERO), (D('.04'), D('-.08'))]
    op = dict(parts=[dict(node=0, lines=lines, positive=hull(lines), negative=hull([(-a, -b) for a, b in lines]))],
              breaks=[ZERO, HALF, ONE])
    local = dict(v_plus=[D('.25')], v_minus=[ZERO])
    cells = weighted_cells(op, [D('.04'), D('.10')], local)
    chord = chord_cell(cells)
    for r in GRID.values():
        value = (1-r)*D('.05')+r*D('.09')
        interval = mixed_at(cells, r)
        le(interval['lower'], value, 'opposing-change lower coverage')
        le(value, interval['upper'], 'opposing-change upper coverage')
    check(mixed_at(cells, HALF)['error_plus'] < mixed_at(chord, HALF)['error_plus']-D('1e-12'),
          'opposing changes strictly cancel positive error')
    check(mixed_at(cells, HALF)['error_minus'] < mixed_at(chord, HALF)['error_minus']-D('1e-12'),
          'opposing changes strictly cancel negative error')
    output.append(dict(name='opposing_changes', cells=cells, chord=chord))
    h, selected = D('.01'), D('.05')
    env = dict(lower=[(h, h*(1-h))], upper=[(TAU, D('.09')), (D('.095'), D('.1'))])
    cases = {'reachable_gap': [('.13', '-.2'), ('.01', '.2')],
             'unreachable_gap': [('.24', '-.2'), ('-.08', '.2')],
             'flat_safe': [('.09', '0')], 'flat_unsafe': [('.11', '0')],
             'increasing': [('.08', '.08')]}
    for name, raw in cases.items():
        hh = hull([tuple(map(D, line)) for line in raw])
        cells = [dict(left=s['left'], right=s['right'], upper=s['line'], lower=(h, h*(1-h)),
                      error_plus=(ZERO, ZERO), error_minus=(ZERO, ZERO)) for s in hh]
        chord = chord_cell(cells)
        cert = policies(h, selected, ONE, env, cells, chord, safe_intervals(cells), safe_intervals(chord))
        _, baseline_j = prior.score(selected, D('.01'), D('.02'))
        for method, policy in cert['policies'].items():
            risk, objective = prior.score(policy['r'], D('.01'), D('.02'))
            le(risk, TAU, 'scalar '+name+' true safety')
            le(policy['guaranteed_gain'], baseline_j-objective, 'scalar '+name+' gain coverage')
        if name == 'reachable_gap':
            dec_close(cert['policies']['interval']['r'], D('.45'), 'reachable safe island selected')
        if name in ('unreachable_gap', 'flat_unsafe'):
            dec_close(cert['policies']['interval']['r'], selected, 'unreachable safe point cannot fill gap')
        if name == 'increasing':
            dec_close(cert['policies']['interval']['r'], D('.25'), 'increasing raw boundary solved')
        if name == 'flat_safe':
            check(cert['policies']['interval']['limit'] == 'objective', 'flat raw bound reaches objective guard')
        output.append(dict(name=name, cells=cells, certificate=cert))
    reason = ''
    try:
        available_inputs({'exact_r': '.2'})
    except ValueError as error:
        reason = str(error)
    check(reason == 'unexpected mixed agent fields', 'unexpected reference field rejected')
    output.append(dict(name='unexpected_reference_field', rejected=True, reason=reason))
    return output


def qualify_models():
    output = []

    def one_model(m, label, choices):
        correction.compile_operators(m)
        known = pair.compile_pairs(m)
        prepared = compile_tables(known['edges'])
        weights, true_pairs, _ = prior.enumerate_reference(m)
        for kind in choices:
            if kind == 'exact':
                q = prior.Belief([list(range(m['n']))], [list(weights.values())])
            elif kind == 'paired_chain':
                q = prior.Belief([[0, 1], [2]], [[D('.1'), D('.3'), D('.2'), D('.4')], [D('.6'), D('.4')]])
            else:
                means = [HALF]*m['n'] if kind == 'prior' else [D('.3'), D('.7'), D('.4')][:m['n']]
                q = prior.Belief([[i] for i in range(m['n'])], [[1-p, p] for p in means])
            baseline = correction.construct(m, q)
            local = {k: baseline['local'][k] for k in ('v_plus', 'v_minus')}
            views = []
            for row in baseline['queries']:
                view = regret.whitelist(m['h'], baseline['local'], row)
                _, released = release.construct(view)
                views.append(dict(risk_view=view, selected=released['policies']['interval']['r'],
                                  previous_bound=released['policies']['interval']['regret']['bound']))
            preceding = pair.construct(m, q, local, views)
            new = construct(prepared, [project(x) for x in preceding['queries']], local)
            # Full-state flip verification uses the independently enumerated state domain.
            for op, row in zip(prepared['queries'], new['queries']):
                table = m['pair_operators'][op['edge']]
                target_index = 0 if row['target'] == m['edges'][op['edge']][0] else 1
                for r in GRID.values():
                    transformed = {bits: (1-r)*table['values'][target_index][table['lookup'][tuple(bits[n] for n in table['variables'])]]
                                          +r*table['values'][2][table['lookup'][tuple(bits[n] for n in table['variables'])]] for bits in weights}
                    for node in range(m['n']):
                        diffs = [transformed[bits[:node]+(1,)+bits[node+1:]]-value for bits, value in transformed.items() if bits[node] == 0]
                        wp, wm = max(ZERO, max(diffs)), max(ZERO, -min(diffs))
                        part = next((p for p in op['parts'] if p['node'] == node), None)
                        if part is None:
                            check(wp == wm == ZERO, 'mixed off-boundary influence exactly zero')
                        else:
                            dec_close(wp, affine(active_line(part['positive'], r), r), 'mixed full-state positive flip')
                            dec_close(wm, affine(active_line(part['negative'], r), r), 'mixed full-state negative flip')
                    fullq = q.marginal(list(range(m['n'])))
                    true_mean = sum(weights[bits]*value for bits, value in transformed.items())
                    q_mean = sum(fullq[bits]*value for bits, value in transformed.items())
                    ep, em = direct_errors(op, local, r)
                    le(true_mean-q_mean, ep, 'enumerated direct positive remainder coverage')
                    le(q_mean-true_mean, em, 'enumerated direct negative remainder coverage')
                    if not op['parts']:
                        check(ep == em == ZERO, 'empty-boundary mixed remainder zero')
            records = assess(new['queries'], true_pairs, m['edges'], m['h'])
            output.append(dict(model=label, kind=kind, h=m['h'], alpha=m['alpha'], queries=records))

    for h in (D('1e-6'), D('.01')):
        for observation in (0, 1):
            m = prior.model_from_saved(dict(h=h, prior=[[HALF, HALF]]*2, edges=[(0, 1)], observations=[observation]))
            one_model(m, 'two_node_'+str(observation), ('prior', 'asymmetric', 'exact'))
    edges = [(i, j) for i in range(4) for j in range(i+1, 4)]
    m = prior.compile_model([[HALF, HALF]]*4, edges, [[[D('.0001'), ONE], [ONE, D('.0001')]]]*6, D('.01'))
    one_model(m, 'noncontractive_K4', ('prior',))
    check(m['alpha'] > ONE, 'noncontractive mixed control exercised')
    m = prior.compile_model([[.6, .4], [.45, .55], [.7, .3]], [(0, 1), (2, 1)],
                            [[[.02, .1], [.08, .19]], [[.03, .09], [.07, .16]]], D('.01'))
    one_model(m, 'oriented_chain', ('asymmetric', 'paired_chain', 'exact'))
    reason = ''
    try:
        pair.compile_pairs(prior.compile_model([[HALF, HALF]]*2, [(0, 1)], [[[2, 1], [1, 2]]], D('.01')))
    except ValueError as error:
        reason = str(error)
    check(reason == 'increasing posterior conditional: signed antitone method unsupported', 'increasing model rejected')
    output.append(dict(model='unsupported_increasing_factor', rejected=True, reason=reason))
    check(len(output) == 17, 'sixteen model controls and rejection retained')
    return output


def summarize(records):
    result = dict(queries=len(records), old_mean_r=stats.fmean(float(q['available']['selected']) for q in records),
                  old_mean_regret=stats.fmean(q['evaluation']['baseline_regret'] for q in records),
                  old_mean_bound=stats.fmean(float(q['available']['previous_bound']) for q in records),
                  exact_mean_r=stats.fmean(float(q['evaluation']['exact_r']) for q in records),
                  classifications={name: dict(Counter(q['classifications'][name] for q in records)) for name in ('old', 'chord', 'combined')})
    for name in METHODS:
        pp = [q['certificate']['policies'][name] for q in records]
        ee = [q['evaluation']['policies'][name] for q in records]
        result[name] = dict(mean_r=stats.fmean(float(p['r']) for p in pp),
                            mean_risk=stats.fmean(e['risk'] for e in ee), max_risk=max(e['risk'] for e in ee),
                            mean_regret=stats.fmean(e['regret'] for e in ee), max_regret=max(e['regret'] for e in ee),
                            mean_gain=stats.fmean(e['gain'] for e in ee),
                            mean_guaranteed_gain=stats.fmean(float(p['guaranteed_gain']) for p in pp),
                            mean_bound=stats.fmean(float(p['bound']) for p in pp), max_bound=max(float(p['bound']) for p in pp),
                            changed=sum(float(p['r'])-float(q['available']['selected']) > TIE for p, q in zip(pp, records)),
                            improved=sum(e['gain'] > TIE for e in ee), worsened=sum(e['gain'] < -TIE for e in ee),
                            limits=dict(Counter(p['limit'] for p in pp)))
    for name in ('physical', 'chord'):
        result['advantage_over_'+name] = dict(mean_gain=stats.fmean(q['evaluation']['advantage_over_'+name] for q in records),
                                             changed=sum(float(q['certificate']['policies']['interval']['r'])-float(q['certificate']['policies'][name]['r']) > TIE for q in records))
    result['cancellation'] = {}
    for point in ('baseline', 'half', 'chosen_interval'):
        pp = [q['comparisons'][point] for q in records]
        item = {}
        for side in ('plus', 'minus'):
            vv = [float(p['cancellation_'+side]) for p in pp]
            item[side] = dict(mean=stats.fmean(vv), improved=sum(v > TIE for v in vv), worsened=sum(v < -TIE for v in vv))
        result['cancellation'][point] = item
    return result


def aggregate(rows):
    def combine(items, path=()):
        if isinstance(items[0], dict):
            if path[-1:] == ('limits',) or path[:1] == ('classifications',) and len(path) == 2:
                total = Counter()
                for item in items:
                    total.update(item)
                return dict(total)
            return {k: combine([x[k] for x in items], path+(k,)) for k in items[0]}
        key = path[-1]
        reducer = stats.fmean if key == 'mean' or key.startswith(('mean_', 'old_mean_', 'exact_mean_')) or key.endswith('_cpu') else max if key.startswith('max_') else sum
        return reducer(items)
    result = {}
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [r for r in rows if r['kind'] == kind and r['level'] == level]
            fields = [k for k in rr[0] if k not in ('fixture', 'kind', 'order', 'level', 'preceding_cost', 'main_cost')]
            result[kind+'_'+str(level)] = {k: combine([r[k] for r in rr], (k,)) for k in fields}
    return result


def run(output, log):
    algorithms, qualification = qualify_algorithms(), qualify_models()
    log.write('All fixed hull, cancellation, scalar safe-set and model controls passed.\n')
    log.flush()
    for path in (MAIN/'MANIFEST.json', OLD/'MANIFEST.json', LOCAL/'MANIFEST.json'):
        signed.verify_manifest(path)
    core, previous, local_record = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json'), read(LOCAL/'RESULTS.json')
    check(not core['gate']['passed'], 'failed mechanism gate preserved')
    case_key = lambda x: tuple(x[k] for k in ('fixture', 'kind', 'order', 'level'))
    previous_rows, local_rows = [{case_key(r): r for r in source['rows']} for source in (previous, local_record)]
    models, rows, seen = {}, [], set()
    with (OLD/'QUERIES.jsonl').open() as source, (output/'QUERIES.jsonl').open('w') as destination:
        for key, group in groupby((json.loads(line) for line in source), case_key):
            saved = list(group)
            fixture, kind, order, level = key
            check(key not in seen, 'unique belief checkpoint')
            seen.add(key)
            if fixture not in models:
                model = previous['models'][fixture]
                prepared = compile_tables(model['operator']['edges'])
                models[fixture] = dict(operator=prepared, preceding_prepare_cpu=model['incremental_pipeline_prepare_cpu'])
            prepared = models[fixture]['operator']
            began = time.process_time()
            local = {k: list(map(D, local_rows[key]['local'][k])) for k in ('v_plus', 'v_minus')}
            views = [project(q) for q in saved]
            input_cpu = time.process_time()-began
            new = construct(prepared, views, local)
            # Evaluation-only exact references are read after all checkpoint policies exist.
            ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
            true_pairs = [{bits: D(str(p[bits[0]][bits[1]])) for bits in states(2)} for p in ref['pairs']]
            edges = [op['pair'] for op in previous['models'][fixture]['operator']['edges']]
            records = assess(new['queries'], true_pairs, edges, D(views[0]['risk_view']['h']), previous=saved)
            for row in records:
                destination.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **row),
                                             default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
            summary = summarize(records)
            before = previous_rows[key]
            for old_field, previous_field in (('old_mean_r', 'mean_r'), ('old_mean_regret', 'mean_regret'), ('old_mean_bound', 'mean_bound')):
                close(summary[old_field], before['interval'][previous_field], 'preceding summary reproduced '+old_field)
            preceding_cost = {k: before[k] for k in ('q_reconstruction_cpu', 'construct_cpu', 'preceding_risk_certificate_cpu', 'preceding_policy_cpu', 'preceding_regret_cpu')}
            rows.append(dict(fixture=fixture, kind=kind, order=order, level=level, input_cpu=input_cpu,
                             **{k: new[k] for k in ('remainder_cpu', 'policy_cpu', 'diagnostic_cpu', 'construct_cpu', 'cells')},
                             preceding_cost=preceding_cost, main_cost=before['main_cost'], **summary))
            log.write(f'Completed {fixture} {kind} {order} budget {level}.\n')
            log.flush()
    count = sum(r['queries'] for r in rows)
    check(len(rows) == 96 and count == 13056, 'all saved checkpoints and directed queries retained')
    return dict(algorithm_qualification=algorithms, model_qualification=qualification, models=models, rows=rows,
                summary=aggregate(rows), checkpoints=len(rows), original_queries=count, policy_evaluations=3*count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted mixed output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen mixed checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen mixed specification')
    helpers = [(Path(pair.__file__), '5bb2219db4c27f25c75691f2cde2150b6def3e2726c56da86ce14ac365ce61cf', 'REUSED_PAIR_HELPER.py'),
               (Path(release.__file__), '5888e2db569798d840f1a8e67236e8762bdf718e52f6c28f6a170d19c6744f9d', 'REUSED_CAP_RELEASE_HELPER.py'),
               (Path(regret.__file__), '961ebf6505e74b562c1baf6fd9da0d9ea2cadbb3af7fd391945511b14b1d1d70', 'REUSED_REGRET_HELPER.py'),
               (Path(correction.__file__), '2dc09583c43bdc236506d262de84cbc36b859656cff2449bba3392e6ea09368f', 'REUSED_CORRECTION_HELPER.py'),
               (Path(signed.__file__), 'a6029890e806a64c8bf61ec1932c86a54400bede75e5d1b38e78935f5c9c1bc4', 'REUSED_SIGNED_HELPER.py'),
               (Path(prior.__file__), 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6', 'REUSED_NUMERICAL_HELPER.py')]
    for path, sha, _ in helpers:
        check(identity(path)['sha256'] == sha, 'unchanged '+path.name)
    check(identity(OLD/'MANIFEST.json')['sha256'] == '7865f7d385099ce54cfef7e8758028012b701944ac1bf2f106c82bf6da83bc8d', 'pinned pair record')
    check(identity(LOCAL/'MANIFEST.json')['sha256'] == 'dddd352612b2c8c1f0d2d19c8625e2ad0e725ffe60f81838e2cb4e2977c739bf', 'pinned mismatch record')
    paths = [SPEC, Path(__file__)]+[p for p, _, _ in helpers]+[
        HERE/'FEP_PAIR_CONDITIONAL_RISK_V1.md', HERE/'FEP_PAIR_CONDITIONAL_RISK_V1_REPORT.md',
        OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl', LOCAL/'MANIFEST.json', LOCAL/'RESULTS.json',
        MAIN/'MANIFEST.json', MAIN/'CORE.json', MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
        HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
        HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    for path, name in [(SPEC, 'SPECIFICATION.md'), (Path(__file__), 'CHECKER_SOURCE.py')]+[(p, name) for p, _, name in helpers]:
        (DEST/name).write_bytes(path.read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='direct mixed-action remainder on fixed Q; no inference update', cpu_processes=1,
                    python=platform.python_version(), decimal_precision=60, selected_stopping_tolerance=None)
    write(DEST/'MANIFEST.json', manifest)
    start, cpu = time.perf_counter(), time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result = run(DEST, log)
            result.update(status='passed', assertions=sum(prior.COUNTS.values()), assertions_by_label=dict(prior.COUNTS),
                          max_residuals=prior.RESIDUALS, elapsed_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json', result)
            manifest['status'] = 'passed'
            log.write(f"Passed {result['assertions']} assertions and {result['policy_evaluations']} policy evaluations.\n")
            print(json.dumps({k: result[k] for k in ('status', 'assertions', 'elapsed_seconds', 'cpu_seconds', 'checkpoints', 'original_queries', 'policy_evaluations')}, indent=2))
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
