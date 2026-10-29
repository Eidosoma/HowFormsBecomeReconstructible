#!/usr/bin/env python3
"""One local conditional risk correction, with a certified remainder."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import json
import math
import os
from pathlib import Path
import platform
import statistics as stats
import time
import traceback

import check_fep_signed_risk_bound as signed

prior = signed.prior
ZERO, ONE, HALF, TAU = signed.ZERO, signed.ONE, signed.HALF, signed.TAU
PAD, NUMTOL, TOL, TIE = signed.PAD, signed.NUMTOL, signed.TOL, signed.TIE
COUNTS, RESIDUALS = signed.COUNTS, signed.RESIDUALS
check, close, dec_close, le = signed.check, signed.close, signed.dec_close, signed.le
read, write, identity, states = prior.read, prior.write, prior.identity, prior.states
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-signed-risk-bound-v1/attempt-01'
DEST = BASE/'fep-local-risk-correction-v1/attempt-01'
SPEC = HERE/'FEP_LOCAL_RISK_CORRECTION_V1.md'
METHODS = ('signed', 'correction', 'combined')


def compile_operators(m):
    """Known model only; cache three local functions for each undirected edge."""
    start = time.process_time()
    direction = signed.decreasing_model(m)
    operators = []
    for i, j in m['edges']:
        variables = sorted(set(m['neighbors'][i]+m['neighbors'][j]))
        assignments = list(states(len(variables)))
        lookup = {bits: k for k, bits in enumerate(assignments)}
        values = [[], [], []]
        for bits in assignments:
            x = dict(zip(variables, bits))
            ti, tj = [m['h']+(TAU-m['h'])*x[k] for k in (i, j)]
            mi, mj = [m['h']+(TAU-m['h'])*m['conditionals'][k][tuple(x[n] for n in m['neighbors'][k])]
                      for k in (i, j)]
            values[0].append((ti+mi)/2)
            values[1].append((tj+mj)/2)
            values[2].append((tj+mi*(1-tj)+ti+mj*(1-ti))/2)
        increments = []
        for table in values:
            result = {}
            for axis, node in enumerate(variables):
                differences = [table[lookup[bits[:axis]+(1,)+bits[axis+1:]]]-table[k]
                               for k, bits in enumerate(assignments) if bits[axis] == 0]
                result[node] = dict(plus=max(ZERO, max(differences))+PAD,
                                    minus=max(ZERO, -min(differences))+PAD)
            increments.append(result)
        operators.append(dict(variables=variables, assignments=assignments, lookup=lookup,
                              values=values, increments=increments))
    m['operators'] = operators
    return dict(cpu=time.process_time()-start, direction=direction,
                max_variables=max(len(op['variables']) for op in operators),
                assignments=sum(len(op['assignments']) for op in operators),
                function_values=3*sum(len(op['assignments']) for op in operators),
                edges=[dict(variables=op['variables'], assignments=len(op['assignments']),
                            increments=op['increments']) for op in operators])


def action_bounds(m, op, q, local):
    weights = q.marginal(op['variables'])
    ranges = [(m['h'], TAU), (m['h'], TAU), (m['h']*(2-m['h']), TAU*(2-TAU))]
    results = []
    for values, inc, (low, high) in zip(op['values'], op['increments'], ranges):
        mean = sum(weights[bits]*value for bits, value in zip(op['assignments'], values))
        ep = sum(w['plus']*local['v_plus'][i]+w['minus']*local['v_minus'][i] for i, w in inc.items())
        em = sum(w['plus']*local['v_minus'][i]+w['minus']*local['v_plus'][i] for i, w in inc.items())
        lower, upper = max(low, mean-em-PAD), min(high, mean+ep+PAD)
        check(lower <= upper+NUMTOL, 'nonempty corrected action interval')
        results.append(dict(mean=mean, error_plus=ep, error_minus=em, lower=lower, upper=upper))
    return results


def bounds_at(m, row, local, r):
    lo, hi = signed.envelope(m, row['a'], row['g'], row['source'], row['target'],
                             local['v_plus'], local['v_minus'], r)
    corr = row['correction_line']
    lc = (1-r)*corr['l0']+r*corr['l1']
    uc = (1-r)*corr['u0']+r*corr['u1']
    return dict(signed=(lo, hi), correction=(lc, uc), combined=(max(lo, lc), min(hi, uc)))


def classification(lower, upper):
    return 'safe' if upper <= TAU else 'unsafe' if lower > TAU else 'unresolved'


def construct(m, q):
    """Model and Q only; the old outcomes and exact references are not inputs."""
    check(m.get('antitone_verified', False), 'decreasing model checked before correction')
    local = signed.signed_bound(m, q)
    signed_query_cpu, correction_cpu = 0., 0.
    queries = []
    for e, ((i, j), op) in enumerate(zip(m['edges'], m['operators'])):
        start = time.process_time()
        pair = q.marginal([i, j])
        edge_rows = []
        for source, target in ((i, j), (j, i)):
            pp = pair if source == i else {(y, x): w for (x, y), w in pair.items()}
            a, g = prior.pair_risks(pp, m['h'])
            original = min(prior.free(g), (TAU-a)/g)
            old_policy = signed.policy(m, a, g, source, target, local['v_plus'], local['v_minus'])
            edge_rows.append(dict(edge=e, source=source, target=target, a=a, g=g, original=original,
                                  policies={'signed': old_policy}))
        signed_query_cpu += time.process_time()-start
        start = time.process_time()
        endpoint_bounds = action_bounds(m, op, q, local)
        for row in edge_rows:
            b0, b1 = endpoint_bounds[0 if row['target'] == i else 1], endpoint_bounds[2]
            row['action_bounds'] = [b0, b1]
            row['correction_line'] = dict(l0=b0['lower'], l1=max(b0['lower'], b1['lower']),
                                           u0=b0['upper'], u1=max(b0['upper'], b1['upper']))
            line = row['correction_line']
            cap = prior.safe_cap(line['u0'], line['u1'])
            rc = min(row['original'], cap)
            rb = max(row['policies']['signed']['r'], rc)
            check(ZERO <= rc <= row['original']+NUMTOL, 'correction respects original allowance')
            check(row['policies']['signed']['r'] <= rb <= row['original']+NUMTOL,
                  'combined certified allowance ordering')
            original_bounds = bounds_at(m, row, local, row['original'])
            for name, rr in (('correction', rc), ('combined', rb)):
                lo, hi = original_bounds[name]
                _, certupper = bounds_at(m, row, local, rr)[name]
                check(certupper <= TAU+NUMTOL, name+' policy upper certifies')
                row['policies'][name] = dict(r=rr, lower=lo, upper=hi, certified_upper=certupper,
                                           classification=classification(lo, hi))
            row['risk_correction'] = ((1-row['original'])*(b0['mean']-row['a'])
                                      +row['original']*(b1['mean']-row['a']-row['g']))
            queries.append(row)
        correction_cpu += time.process_time()-start
    return dict(local=local, queries=queries, signed_query_cpu=signed_query_cpu,
                correction_cpu=correction_cpu,
                cpu=local['conditional_cpu']+local['propagation_cpu']+signed_query_cpu+correction_cpu,
                corrected_marginal_assignments=sum(len(op['assignments']) for op in m['operators']),
                corrected_expectation_terms=3*sum(len(op['assignments']) for op in m['operators']))


def assess(m, cert, pairs, saved=None, old_queries=None, main=False, grid=None):
    records = []
    for k, row in enumerate(cert['queries']):
        true_pair = pairs[row['edge']]
        if row['source'] != m['edges'][row['edge']][0]:
            true_pair = {(y, x): w for (x, y), w in true_pair.items()}
        a, g = prior.pair_risks(true_pair, m['h'])
        exact = min(prior.free(g), (TAU-a)/g)
        if main:
            check((TAU-a)/g < prior.free(g), 'exact main decision remains binding')
        actual, _ = prior.score(row['original'], a, g)
        _, optimal_j = prior.score(exact, a, g)
        if saved is not None:
            close(row['original'], saved[k]['chosen']['r'], 'saved original allowance')
            close(actual, saved[k]['actual']['risk'], 'saved original risk')
            close(exact, saved[k]['exact']['r'], 'saved exact allowance')
        if old_queries is not None:
            before = old_queries[k]
            check(all(row[key] == before[key] for key in ('edge', 'source', 'target')), 'old query correspondence')
            for field in ('a', 'g', 'original'):
                dec_close(row[field], before[field], 'reproduced original '+field)
            for field in ('r', 'lower', 'upper', 'certified_upper'):
                dec_close(row['policies']['signed'][field], before['policies']['signed'][field],
                          'reproduced signed '+field)
        points = (grid if grid is not None else [ZERO, ONE])+[row['original']]
        points += [p['r'] for p in row['policies'].values()]
        for rr in points:
            env = bounds_at(m, row, cert['local'], rr)
            risk = a+rr*g
            check(env['combined'][0] >= env['signed'][0]-NUMTOL, 'combined lower nesting')
            check(env['combined'][1] <= env['signed'][1]+NUMTOL, 'combined upper nesting')
            for name, (lo, hi) in env.items():
                check(lo <= hi+NUMTOL, name+' interval nonempty')
                le(lo, risk, name+' lower risk coverage')
                le(risk, hi, name+' upper risk coverage')
        result = {**row, 'exact_r': exact, 'original_actual_risk': actual, 'policies': {}}
        for name in METHODS:
            p = row['policies'][name]
            risk, j = prior.score(p['r'], a, g)
            le(risk, TAU, name+' actual feasibility')
            le(risk, p['certified_upper'], name+' certified risk coverage')
            le(optimal_j, j, name+' feasible regret nonnegative')
            if p['classification'] == 'safe':
                le(actual, TAU, name+' safe classification verified')
            if p['classification'] == 'unsafe':
                le(TAU, actual, name+' unsafe classification verified')
            if main:
                le(p['r'], exact, name+' certified allowance no larger than exact')
            if old_queries is not None and name == 'signed':
                close(risk, old_queries[k]['policies']['signed']['actual_risk'], 'reproduced signed actual risk')
                close(j-optimal_j, old_queries[k]['policies']['signed']['objective_regret'], 'reproduced signed regret')
            result['policies'][name] = {**p, 'actual_risk': risk, 'objective_regret': j-optimal_j}
        if main:
            le(result['policies']['combined']['objective_regret'], result['policies']['signed']['objective_regret'],
               'combined regret improves in binding regime')
        records.append(result)
    return records


def physical(bits, source, target, h, action):
    ti, tj = [h+(TAU-h)*bits[k] for k in (source, target)]
    return tj if action == 0 else ti+tj-ti*tj


def direct_update(m, bits, source, target, action):
    value = ZERO
    for site in (source, target):
        probability = m['conditionals'][site][tuple(bits[k] for k in m['neighbors'][site])]
        for bit, weight in ((0, 1-probability), (1, probability)):
            new = list(bits)
            new[site] = bit
            value += weight*physical(new, source, target, m['h'], action)/2
    return value


def verify_small_operator(m, q, weights, cert):
    full_q = q.marginal(list(range(m['n'])))
    negative_exercised = False
    for row in cert['queries']:
        op = m['operators'][row['edge']]
        index0 = 0 if row['target'] == m['edges'][row['edge']][0] else 1
        for action, index in ((0, index0), (1, 2)):
            full_values = {}
            for bits in weights:
                direct = direct_update(m, bits, row['source'], row['target'], action)
                full_values[bits] = direct
                compiled = op['values'][index][op['lookup'][tuple(bits[k] for k in op['variables'])]]
                dec_close(direct, compiled, 'direct local operator formula')
            true_before = sum(w*physical(bits, row['source'], row['target'], m['h'], action)
                              for bits, w in weights.items())
            true_after = sum(w*full_values[bits] for bits, w in weights.items())
            dec_close(true_before, true_after, 'operator preserves posterior expectation')
            q_after = sum(w*full_values[bits] for bits, w in full_q.items())
            q_before = sum(w*physical(bits, row['source'], row['target'], m['h'], action)
                           for bits, w in full_q.items())
            drift = sum(w*(full_values[bits]-physical(bits, row['source'], row['target'], m['h'], action))
                        for bits, w in full_q.items())
            dec_close(q_after, row['action_bounds'][action]['mean'], 'local expectation matches full enumeration')
            dec_close(true_before-q_before, drift+(true_after-q_after), 'signed correction remainder identity')
            for node in op['variables']:
                differences = [full_values[bits[:node]+(1,)+bits[node+1:]]-value
                               for bits, value in full_values.items() if bits[node] == 0]
                wp, wm = max(ZERO, max(differences))+PAD, max(ZERO, -min(differences))+PAD
                dec_close(wp, op['increments'][index][node]['plus'], 'enumerated positive increment')
                dec_close(wm, op['increments'][index][node]['minus'], 'enumerated negative increment')
                negative_exercised |= wm > NUMTOL
    return negative_exercised


def qualify():
    results = []
    negative_exercised = False
    grid = [ZERO, D('.25'), HALF, D('.75'), ONE]
    for h in (D('1e-6'), D('.01')):
        for observation in (0, 1):
            m = prior.model_from_saved(dict(h=h, prior=[[HALF, HALF]]*2,
                                            edges=[(0, 1)], observations=[observation]))
            prep = compile_operators(m)
            weights, pairs, _ = prior.enumerate_reference(m)
            signed.direct_conditionals(m, weights)
            for kind in ('prior', 'asymmetric', 'exact'):
                if kind == 'exact':
                    q = prior.Belief([[0, 1]], [list(weights.values())])
                else:
                    means = [HALF, HALF] if kind == 'prior' else [D('.3'), D('.7')]
                    q = prior.Belief([[0], [1]], [[1-p, p] for p in means])
                cert = construct(m, q)
                signed.direct_signed_residuals(m, q, {'primary': cert['local']})
                negative_exercised |= verify_small_operator(m, q, weights, cert)
                rows = assess(m, cert, pairs, grid=grid)
                results.append(dict(h=h, observation=observation, kind=kind, alpha=m['alpha'],
                                    operator=prep, local=cert['local'], queries=rows))
    edges = [(i, j) for i in range(4) for j in range(i+1, 4)]
    m = prior.compile_model([[HALF, HALF]]*4, edges,
                            [[[D('.0001'), ONE], [ONE, D('.0001')]]]*6, D('.01'))
    prep = compile_operators(m)
    weights, pairs, _ = prior.enumerate_reference(m)
    signed.direct_conditionals(m, weights)
    q = prior.Belief([[i] for i in range(4)], [[HALF, HALF]]*4)
    cert = construct(m, q)
    negative_exercised |= verify_small_operator(m, q, weights, cert)
    rows = assess(m, cert, pairs, grid=grid)
    check(m['alpha'] > 1, 'noncontractive correction control exercised')
    check(negative_exercised, 'negative transformed increment exercised')
    results.append(dict(kind='noncontractive_K4', alpha=m['alpha'], operator=prep,
                        local=cert['local'], queries=rows))
    m = prior.compile_model([[HALF, HALF]]*2, [(0, 1)], [[[2, 1], [1, 2]]], D('.01'))
    rejected, reason = False, ''
    try:
        compile_operators(m)
    except ValueError as error:
        rejected, reason = True, str(error)
    check(rejected, 'unsupported increasing model rejected before correction')
    results.append(dict(kind='unsupported_increasing_factor', rejected=rejected, reason=reason))
    return results


def summarize(records):
    result = dict(queries=len(records), original_mean_r=stats.fmean(float(r['original']) for r in records),
                  exact_mean_r=stats.fmean(float(r['exact_r']) for r in records),
                  mean_risk_correction=stats.fmean(float(r['risk_correction']) for r in records),
                  min_risk_correction=min(float(r['risk_correction']) for r in records),
                  max_risk_correction=max(float(r['risk_correction']) for r in records))
    for name in METHODS:
        pp = [r['policies'][name] for r in records]
        gains = [float(p['r']-r['policies']['signed']['r']) for p, r in zip(pp, records)]
        safe = [float(TAU-p['upper']) for p in pp if p['classification'] == 'safe']
        unsafe = [float(p['lower']-TAU) for p in pp if p['classification'] == 'unsafe']
        result[name] = dict(mean_r=stats.fmean(float(p['r']) for p in pp),
                            zero_allowances=sum(p['r'] == 0 for p in pp),
                            full_original_allowance=sum(p['r'] == r['original'] for p, r in zip(pp, records)),
                            max_actual_risk=max(p['actual_risk'] for p in pp),
                            mean_regret=stats.fmean(p['objective_regret'] for p in pp),
                            mean_original_width=stats.fmean(float(p['upper']-p['lower']) for p in pp),
                            classifications=dict(Counter(p['classification'] for p in pp)),
                            improved_vs_signed=sum(x > TIE for x in gains),
                            tied_vs_signed=sum(abs(x) <= TIE for x in gains),
                            worse_vs_signed=sum(x < -TIE for x in gains),
                            min_safe_margin=min(safe) if safe else None,
                            min_unsafe_margin=min(unsafe) if unsafe else None)
    changes = [float(r['policies']['signed']['upper']-r['policies']['correction']['upper']) for r in records]
    result['correction_original_upper_comparison'] = dict(improved=sum(x > TIE for x in changes),
                                                         tied=sum(abs(x) <= TIE for x in changes),
                                                         worse=sum(x < -TIE for x in changes))
    return result


def aggregate(rows, old_summary):
    output = {}
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [row for row in rows if row['kind'] == kind and row['level'] == level]
            item = {key: stats.fmean(row[key] for row in rr) for key in
                    ('original_mean_r', 'exact_mean_r', 'mean_risk_correction', 'q_reconstruction_cpu',
                     'signed_bound_cpu', 'signed_query_cpu', 'correction_cpu', 'certificate_cpu')}
            item['queries'] = sum(row['queries'] for row in rr)
            item['min_risk_correction'] = min(row['min_risk_correction'] for row in rr)
            item['max_risk_correction'] = max(row['max_risk_correction'] for row in rr)
            for name in METHODS:
                ps = [row[name] for row in rr]
                classes = Counter()
                for p in ps:
                    classes.update(p['classifications'])
                item[name] = {key: stats.fmean(p[key] for p in ps)
                              for key in ('mean_r', 'mean_regret', 'mean_original_width')}
                item[name].update({key: sum(p[key] for p in ps) for key in
                                   ('zero_allowances', 'full_original_allowance', 'improved_vs_signed',
                                    'tied_vs_signed', 'worse_vs_signed')})
                item[name]['max_actual_risk'] = max(p['max_actual_risk'] for p in ps)
                item[name]['classifications'] = dict(classes)
                for key in ('min_safe_margin', 'min_unsafe_margin'):
                    values = [p[key] for p in ps if p[key] is not None]
                    item[name][key] = min(values) if values else None
            item['correction_original_upper_comparison'] = {
                key: sum(row['correction_original_upper_comparison'][key] for row in rr)
                for key in ('improved', 'tied', 'worse')}
            item['prior_kl_baselines'] = old_summary[kind+'_'+str(level)]['prior_kl_baselines']
            output[kind+'_'+str(level)] = item
    return output


def run(output, log):
    qualification = qualify()
    log.write('Thirteen accepted controls and increasing-model rejection passed.\n')
    log.flush()
    signed.verify_manifest(MAIN/'MANIFEST.json')
    signed.verify_manifest(OLD/'MANIFEST.json')
    core, old = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json')
    check(not core['gate']['passed'], 'failed original mechanism gate preserved')
    old_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in old['rows']}
    old_queries = {}
    with (OLD/'QUERIES.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            key = (row['fixture'], row['kind'], row['order'], row['level'])
            old_queries.setdefault(key, []).append(row)
    models, model_rows, rows = {}, {}, []
    querycount = 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture, kind, order = [case[key] for key in ('fixture', 'kind', 'order')]
            job = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')
            if fixture not in models:
                m = prior.model_from_saved(job['model'])
                prep = compile_operators(m)
                check(prep['max_variables'] <= 8, 'grid correction support at most eight causes')
                models[fixture] = m
                model_rows[fixture] = dict(alpha=m['alpha'], conditional_prepare_cpu=m['prepare_cpu'],
                                           operator=prep, total_prepare_cpu=m['prepare_cpu']+prep['cpu'])
                dec_close(m['alpha'], old['models'][fixture]['alpha'], 'previous model influence norm')
            m = models[fixture]
            for level, snap in zip((256, 1024, 4096), job['snapshots']):
                key = (fixture, kind, order, level)
                start = time.process_time()
                q = prior.Belief(snap['groups'], [[D(str(x)).exp() for x in block]
                                                 for block in snap['block_log_probabilities']])
                reconstruction = time.process_time()-start
                cert = construct(m, q)
                # Exact-reference access only after model/Q-only certificate construction.
                ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                ev = read(MAIN/f'{fixture}_{kind}_{order}_evaluation.json')[(256, 1024, 4096).index(level)]
                true_pairs = [{s: D(str(p[s[0]][s[1]])) for s in states(2)} for p in ref['pairs']]
                for field in ('b_plus', 'b_minus', 'v_plus', 'v_minus', 'mu', 'cap_plus', 'cap_minus'):
                    for value, before in zip(cert['local'][field], old_rows[key]['primary'][field]):
                        dec_close(value, before, 'reproduced signed '+field)
                records = assess(m, cert, true_pairs, saved=ev['queries'], old_queries=old_queries[key], main=True)
                for row in records:
                    stream.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **row),
                                            default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summarize(records)
                close(summary['signed']['mean_r'], old_rows[key]['signed']['mean_r'], 'previous signed mean')
                check(summary['signed']['classifications'] == old_rows[key]['signed']['classifications'],
                      'previous original classifications')
                rows.append(dict(fixture=fixture, kind=kind, order=order, level=level, local=cert['local'],
                                 q_reconstruction_cpu=reconstruction,
                                 signed_bound_cpu=cert['local']['conditional_cpu']+cert['local']['propagation_cpu'],
                                 signed_query_cpu=cert['signed_query_cpu'], correction_cpu=cert['correction_cpu'],
                                 certificate_cpu=cert['cpu'], corrected_marginal_assignments=cert['corrected_marginal_assignments'],
                                 corrected_expectation_terms=cert['corrected_expectation_terms'],
                                 main_cost=case['cost'], **summary))
                querycount += len(records)
            log.write(f'Completed {fixture} {kind} {order}; all three budgets retained.\n')
            log.flush()
    check(len(rows) == 96 and querycount == 13056, 'all saved checkpoints and queries retained')
    return dict(qualification=qualification, models=model_rows, rows=rows,
                summary=aggregate(rows, old['summary']), checkpoints=len(rows), original_queries=querycount,
                new_certified_policies=2*querycount, reproduced_signed_policies=querycount)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted correction output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen correction checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen correction specification')
    check(identity(signed.__file__)['sha256'] == 'a6029890e806a64c8bf61ec1932c86a54400bede75e5d1b38e78935f5c9c1bc4',
          'unchanged signed helper')
    check(identity(prior.__file__)['sha256'] == 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6',
          'unchanged local helper')
    check(identity(OLD/'MANIFEST.json')['sha256'] == '35c60597f04e69b2482625779dcffd92d2b64a86b31423aa917af6213ef3cfb0',
          'pinned preceding record')
    paths = [SPEC, Path(__file__), Path(signed.__file__), Path(prior.__file__),
             HERE/'FEP_SIGNED_RISK_BOUND_V1.md', HERE/'FEP_SIGNED_RISK_BOUND_V1_REPORT.md',
             OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl',
             MAIN/'MANIFEST.json', MAIN/'CORE.json', MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
             HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(path) for path in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    for path, name in ((SPEC, 'SPECIFICATION.md'), (Path(__file__), 'CHECKER_SOURCE.py'),
                       (Path(signed.__file__), 'REUSED_SIGNED_HELPER.py'), (Path(prior.__file__), 'REUSED_LOCAL_HELPER.py')):
        (DEST/name).write_bytes(path.read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='local conditional risk correction on saved beliefs; original allowances retained',
                    python=platform.python_version(), decimal_precision=60, propagation_steps=32, cpu_processes=1,
                    update_operator='equal mixture of one single-site conditional update at either query endpoint')
    write(DEST/'MANIFEST.json', manifest)
    start, cpu = time.perf_counter(), time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result = run(DEST, log)
            result.update(status='passed', assertions=sum(COUNTS.values()), assertions_by_label=dict(COUNTS),
                          max_residuals=RESIDUALS, elapsed_seconds=time.perf_counter()-start,
                          cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json', result)
            manifest['status'] = 'passed'
            log.write(f"Passed {result['assertions']} checks and {result['new_certified_policies']} new certified policies.\n")
            print(json.dumps({key: result[key] for key in ('status', 'assertions', 'elapsed_seconds', 'cpu_seconds',
                              'checkpoints', 'original_queries', 'new_certified_policies', 'summary')},
                             default=prior.encode, indent=2))
        except Exception:
            manifest['status'] = 'failed'
            log.write(traceback.format_exc())
            raise
        finally:
            log.flush()
            manifest['outputs'] = [identity(path) for path in sorted(DEST.iterdir()) if path.name != 'MANIFEST.json']
            write(DEST/'MANIFEST.json', manifest)


if __name__ == '__main__':
    main()
