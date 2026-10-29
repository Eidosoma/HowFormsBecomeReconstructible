#!/usr/bin/env python3
"""Signed local certificates on immutable saved beliefs; no inference rerun."""
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

import check_fep_local_risk_bound as prior

ZERO, ONE, HALF = D(0), D(1), D('.5')
TAU, PAD, NUMTOL, TOL, TIE = D('.1'), D('1e-30'), D('1e-25'), 1e-10, 1e-12
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-local-risk-bound-v1/attempt-01'
DEST = BASE/'fep-signed-risk-bound-v1/attempt-01'
SPEC = HERE/'FEP_SIGNED_RISK_BOUND_V1.md'
METHODS = ('symmetric', 'direction_only', 'signed')
COUNTS, RESIDUALS = prior.COUNTS, prior.RESIDUALS
read, write, identity = prior.read, prior.write, prior.identity
check, close, states = prior.check, prior.close, prior.states


def dec_close(a, b, label):
    residual = abs(D(a)-D(b))
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), float(residual))
    check(residual <= NUMTOL, label)


def le(a, b, label, tolerance=TOL):
    excess = float(a)-float(b)
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), max(0., excess))
    check(math.isfinite(excess) and excess <= tolerance, label)


def decreasing_model(m):
    """Validate the signed recursion's local direction assumption."""
    start = time.process_time()
    check(all(x > 0 for row in m['prior'] for x in row), 'positive model unaries')
    check(all(x > 0 for p in m['factors'] for row in p for x in row), 'positive model factors')
    largest_increase = ZERO
    comparisons = 0
    for table in m['conditionals']:
        for bits, value in table.items():
            for axis, bit in enumerate(bits):
                if bit:
                    continue
                change = table[bits[:axis]+(1,)+bits[axis+1:]]-value
                comparisons += 1
                largest_increase = max(largest_increase, change)
                if change > NUMTOL:
                    raise ValueError('increasing posterior conditional: signed antitone method unsupported')
    m['antitone_verified'] = True
    return dict(comparisons=comparisons, largest_increase=largest_increase,
                cpu=time.process_time()-start)


def propagate(m, bp, bm, cp, cm):
    vp, vm = cp.copy(), cm.copy()
    for _ in range(32):
        np = [min(cp[i], bp[i]+sum(c*vm[j] for j, c in row.items())+PAD)
              for i, row in enumerate(m['C'])]
        nm = [min(cm[i], bm[i]+sum(c*vp[j] for j, c in row.items())+PAD)
              for i, row in enumerate(m['C'])]
        check(all(x <= y+NUMTOL for x, y in zip(np, vp)), 'decreasing upward bound')
        check(all(x <= y+NUMTOL for x, y in zip(nm, vm)), 'decreasing downward bound')
        vp, vm = np, nm
    return vp, vm


def signed_bound(m, q):
    start = time.process_time()
    bp, bm, mu, counts = [], [], [], []
    for i in range(m['n']):
        partners = [j for j in q.groups[q.owner[i]] if j != i]
        variables = sorted(set(partners+m['neighbors'][i]))
        local, full = q.marginal(variables), q.marginal([i]+partners)
        conditional = {s: full[(1,)+s]/(full[(0,)+s]+full[(1,)+s])
                       for s in states(len(partners))}
        plus, minus = ZERO, ZERO
        for bits, weight in local.items():
            x = dict(zip(variables, bits))
            p = m['conditionals'][i][tuple(x[j] for j in m['neighbors'][i])]
            qi = conditional[tuple(x[j] for j in partners)]
            plus += weight*max(ZERO, p-qi)
            minus += weight*max(ZERO, qi-p)
        bp.append(min(ONE, plus+PAD))
        bm.append(min(ONE, minus+PAD))
        mu.append(q.marginal([i])[(1,)])
        counts.append(len(local))
    cp = [min(ONE, 1-p+PAD) for p in mu]
    cm = [min(ONE, p+PAD) for p in mu]
    conditional_cpu = time.process_time()-start
    start = time.process_time()
    vp, vm = propagate(m, bp, bm, cp, cm)
    return dict(b_plus=bp, b_minus=bm, mu=mu, cap_plus=cp, cap_minus=cm,
                v_plus=vp, v_minus=vm, local_assignments=sum(counts),
                max_local_variables=int(math.log2(max(counts))),
                propagation_steps=32, propagation_multiply_adds=64*sum(map(len, m['C'])),
                conditional_cpu=conditional_cpu, propagation_cpu=time.process_time()-start)


def envelope(m, a, g, source, target, vp, vm, r, signed=True):
    h, delta = m['h'], TAU-m['h']
    wi, wj = r*delta*(1-h), delta*(1-r*h)
    lower = max(h+r*h*(1-h), a+r*g-wi*vm[source]-wj*vm[target]-(PAD if signed else ZERO))
    upper = min(TAU+r*TAU*(1-TAU), a+r*g+wi*vp[source]+wj*vp[target]+PAD)
    return lower, upper


def policy(m, a, g, source, target, vp, vm, signed=True):
    h, delta = m['h'], TAU-m['h']
    A = a+delta*vp[target]
    G = g+delta*((1-h)*vp[source]-h*vp[target])
    check(G >= h*(D('.8')+h)-NUMTOL, 'positive signed certificate slope')
    original = min(prior.free(g), (TAU-a)/g)
    r = min(prior.free(g), max(ZERO, min(ONE, (TAU-A-2*PAD)/G)))
    lower, upper = envelope(m, a, g, source, target, vp, vm, original, signed)
    _, certupper = envelope(m, a, g, source, target, vp, vm, r, signed)
    check(certupper <= TAU+NUMTOL, 'policy envelope certifies')
    return dict(r=r, lower=lower, upper=upper, certified_upper=certupper,
                classification='safe' if upper <= TAU else 'unsafe' if lower > TAU else 'unresolved')


def construct(m, q):
    """Known local model and Q only. References and saved labels are excluded."""
    check(m.get('antitone_verified', False), 'model direction verified before construction')
    primary = signed_bound(m, q)
    start = time.process_time()
    queries = []
    for e, (i, j) in enumerate(m['edges']):
        pair = q.marginal([i, j])
        for source, target in ((i, j), (j, i)):
            oriented = pair if source == i else {(y, x): w for (x, y), w in pair.items()}
            a, g = prior.pair_risks(oriented, m['h'])
            original = min(prior.free(g), (TAU-a)/g)
            item = policy(m, a, g, source, target, primary['v_plus'], primary['v_minus'])
            queries.append(dict(edge=e, source=source, target=target, a=a, g=g,
                                original=original, policies={'signed': item}))
    primary['query_cpu'] = time.process_time()-start
    primary['cpu'] = sum(primary[k] for k in ('conditional_cpu', 'propagation_cpu', 'query_cpu'))

    start = time.process_time()
    dp, dm = propagate(m, primary['b_plus'], primary['b_minus'], [ONE]*m['n'], [ONE]*m['n'])
    absolute = prior.conditional_bound(m, q)
    for i in range(m['n']):
        # Two individually padded signed residuals sum to b_abs+PAD except at clipping.
        dec_close(min(ONE, primary['b_plus'][i]+primary['b_minus'][i]-PAD), absolute['b'][i],
                  'signed residuals reconstruct absolute discrepancy')
        for key, direction in (('v_plus', dp), ('v_minus', dm)):
            check(primary[key][i] <= direction[i]+NUMTOL, 'marginal caps strengthen direction control')
            check(direction[i] <= absolute['v'][i]+NUMTOL, 'signed vector dominated by symmetric')
    for row in queries:
        args = [m, row['a'], row['g'], row['source'], row['target']]
        row['policies']['direction_only'] = policy(*args, dp, dm)
        row['policies']['symmetric'] = policy(*args, absolute['v'], absolute['v'], signed=False)
        pp = row['policies']
        for left, right in (('symmetric', 'direction_only'), ('direction_only', 'signed')):
            check(pp[left]['r'] <= pp[right]['r']+NUMTOL, 'certified allowance ordering')
            check(pp[left]['lower'] <= pp[right]['lower']+NUMTOL, 'original lower interval nesting')
            check(pp[right]['upper'] <= pp[left]['upper']+NUMTOL, 'original upper interval nesting')
        check(pp['signed']['r'] <= row['original']+NUMTOL, 'certificate no larger than original')
    return dict(primary=primary, direction_only=dict(v_plus=dp, v_minus=dm),
                symmetric=absolute, queries=queries, controls_cpu=time.process_time()-start)


def assess(m, cert, true_pairs, saved=None, previous=None, main=False, grid=None):
    records = []
    directions = {name: (cert[name]['v_plus'], cert[name]['v_minus'])
                  for name in ('direction_only',)}
    directions['signed'] = (cert['primary']['v_plus'], cert['primary']['v_minus'])
    directions['symmetric'] = (cert['symmetric']['v'], cert['symmetric']['v'])
    for k, row in enumerate(cert['queries']):
        pair = true_pairs[row['edge']]
        if row['source'] != m['edges'][row['edge']][0]:
            pair = {(y, x): w for (x, y), w in pair.items()}
        a, g = prior.pair_risks(pair, m['h'])
        exact = min(prior.free(g), (TAU-a)/g)
        if main:
            check((TAU-a)/g < prior.free(g), 'exact primary branch remains binding')
        _, optimal_j = prior.score(exact, a, g)
        actual, _ = prior.score(row['original'], a, g)
        result = {**row, 'exact_r': exact, 'original_actual_risk': actual, 'policies': {}}
        if saved is not None:
            close(row['original'], saved[k]['chosen']['r'], 'saved original decision')
            close(actual, saved[k]['actual']['risk'], 'saved original risk')
            close(exact, saved[k]['exact']['r'], 'saved exact decision')
        if previous is not None:
            old = previous[k]
            check(all(row[key] == old[key] for key in ('edge', 'source', 'target')), 'old query correspondence')
            for key in ('a', 'g', 'original'):
                dec_close(row[key], old[key], 'old query '+key)
            for key in ('r', 'lower', 'upper', 'certified_upper'):
                dec_close(row['policies']['symmetric'][key], old[key], 'reproduced symmetric '+key)
        for name in METHODS:
            policy_row = row['policies'][name]
            vp, vm = directions[name]
            points = (grid if grid is not None else [ZERO, ONE])+[row['original']]
            for r in points:
                low, high = envelope(m, row['a'], row['g'], row['source'], row['target'],
                                     vp, vm, r, signed=name != 'symmetric')
                risk = a+r*g
                le(low, risk, name+' lower risk coverage')
                le(risk, high, name+' upper risk coverage')
            delta = TAU-m['h']
            le(a-row['a'], delta*vp[row['target']], name+' upward marginal coverage')
            le(row['a']-a, delta*vm[row['target']], name+' downward marginal coverage')
            r = policy_row['r']
            risk, objective = prior.score(r, a, g)
            le(risk, TAU, name+' actual feasibility')
            le(risk, policy_row['certified_upper'], name+' certified risk coverage')
            le(optimal_j, objective, name+' nonnegative feasible regret')
            if main:
                le(r, exact, name+' certified action no larger than binding exact')
            if previous is not None and name == 'symmetric':
                close(risk, previous[k]['certificates']['local']['actual_risk'], 'reproduced symmetric risk')
                close(objective-optimal_j, previous[k]['certificates']['local']['objective_regret'],
                      'reproduced symmetric regret')
            result['policies'][name] = {**policy_row, 'actual_risk': risk,
                                        'objective_regret': objective-optimal_j}
        if main:
            for left, right in (('symmetric', 'direction_only'), ('direction_only', 'signed')):
                le(result['policies'][right]['objective_regret'], result['policies'][left]['objective_regret'],
                   'binding-regime objective improves with certified allowance')
        records.append(result)
    return records


def direct_conditionals(m, weights):
    for i in range(m['n']):
        for bits in weights:
            matches = [(s, w) for s, w in weights.items()
                       if all(s[j] == bits[j] for j in range(m['n']) if j != i)]
            value = sum(w for s, w in matches if s[i])/sum(w for _, w in matches)
            local = m['conditionals'][i][tuple(bits[j] for j in m['neighbors'][i])]
            dec_close(value, local, 'enumerated posterior conditional')


def direct_signed_residuals(m, q, cert):
    full = q.marginal(list(range(m['n'])))
    for i in range(m['n']):
        bp, bm, mu = ZERO, ZERO, ZERO
        for bits, weight in full.items():
            matches = [(t, w) for t, w in full.items()
                       if all(t[j] == bits[j] for j in range(m['n']) if j != i)]
            qi = sum(w for t, w in matches if t[i])/sum(w for _, w in matches)
            p = m['conditionals'][i][tuple(bits[j] for j in m['neighbors'][i])]
            bp += weight*max(ZERO, p-qi)
            bm += weight*max(ZERO, qi-p)
            mu += weight*bits[i]
        dec_close(min(ONE, bp+PAD), cert['primary']['b_plus'][i], 'enumerated upward local discrepancy')
        dec_close(min(ONE, bm+PAD), cert['primary']['b_minus'][i], 'enumerated downward local discrepancy')
        dec_close(mu, cert['primary']['mu'][i], 'enumerated Q marginal cap input')


def qualify():
    out = []
    grid = [ZERO, D('.25'), HALF, D('.75'), ONE]
    for h in (D('1e-6'), D('.01')):
        for observation in (0, 1):
            m = prior.model_from_saved(dict(h=h, prior=[[HALF, HALF]]*2,
                                            edges=[(0, 1)], observations=[observation]))
            direction = decreasing_model(m)
            weights, pairs, _ = prior.enumerate_reference(m)
            direct_conditionals(m, weights)
            if observation:
                a, b, c = h*(2-h), TAU+h-TAU*h, TAU*(2-TAU)
                dec_close(a*c-b*b, -(TAU-h)**2, 'failure determinant identity')
            for kind in ('prior', 'asymmetric', 'exact'):
                if kind == 'exact':
                    q = prior.Belief([[0, 1]], [list(weights.values())])
                else:
                    means = [HALF, HALF] if kind == 'prior' else [D('.3'), D('.7')]
                    q = prior.Belief([[0], [1]], [[1-p, p] for p in means])
                cert = construct(m, q)
                direct_signed_residuals(m, q, cert)
                rows = assess(m, cert, pairs, grid=grid)
                if kind == 'exact':
                    check(max(cert['primary']['b_plus']+cert['primary']['b_minus']) < NUMTOL,
                          'exact Q signed discrepancy vanishes')
                out.append(dict(kind=kind, h=h, observation=observation, direction=direction,
                                alpha=m['alpha'], primary=cert['primary'], queries=rows))
    edges = [(i, j) for i in range(4) for j in range(i+1, 4)]
    m = prior.compile_model([[HALF, HALF]]*4, edges,
                            [[[D('.0001'), ONE], [ONE, D('.0001')]]]*6, D('.01'))
    direction = decreasing_model(m)
    weights, pairs, _ = prior.enumerate_reference(m)
    direct_conditionals(m, weights)
    q = prior.Belief([[i] for i in range(4)], [[HALF, HALF]]*4)
    cert = construct(m, q)
    direct_signed_residuals(m, q, cert)
    rows = assess(m, cert, pairs, grid=grid)
    check(m['alpha'] > 1, 'noncontractive signed control exercised')
    check(all(v == 1 for v in cert['symmetric']['v']), 'noncontractive symmetric control reproduced')
    check(all(abs(v-HALF) <= NUMTOL for v in cert['primary']['v_plus']+cert['primary']['v_minus']),
          'noncontractive signed bound retains marginal caps')
    out.append(dict(kind='noncontractive_K4', direction=direction, alpha=m['alpha'],
                    primary=cert['primary'], queries=rows))
    m = prior.compile_model([[HALF, HALF]]*2, [(0, 1)], [[[2, 1], [1, 2]]], D('.01'))
    rejected = False
    try:
        decreasing_model(m)
    except ValueError as error:
        rejected = True
        reason = str(error)
    check(rejected, 'increasing-factor control rejected before certification')
    out.append(dict(kind='unsupported_increasing_factor', rejected=rejected, reason=reason))
    return out


def summarize(records):
    result = dict(queries=len(records), original_mean_r=stats.fmean(float(r['original']) for r in records),
                  exact_mean_r=stats.fmean(float(r['exact_r']) for r in records))
    for name in METHODS:
        pp = [r['policies'][name] for r in records]
        gains = [float(p['r']-r['policies']['symmetric']['r']) for p, r in zip(pp, records)]
        result[name] = dict(mean_r=stats.fmean(float(p['r']) for p in pp),
                            zero_allowances=sum(p['r'] == 0 for p in pp),
                            max_actual_risk=max(p['actual_risk'] for p in pp),
                            mean_regret=stats.fmean(p['objective_regret'] for p in pp),
                            classifications=dict(Counter(p['classification'] for p in pp)),
                            improved_vs_symmetric=sum(x > TIE for x in gains),
                            tied_vs_symmetric=sum(abs(x) <= TIE for x in gains),
                            worse_vs_symmetric=sum(x < -TIE for x in gains),
                            max_gain_vs_symmetric=max(gains))
    gains = [float(r['policies']['signed']['r']-r['policies']['direction_only']['r']) for r in records]
    result['marginal_cap_increment'] = dict(mean=stats.fmean(gains), maximum=max(gains),
                                          improved=sum(x > TIE for x in gains),
                                          tied=sum(abs(x) <= TIE for x in gains))
    return result


def verify_manifest(path):
    manifest = read(path)
    check(manifest['status'] in ('passed', 'completed'), 'prior record complete')
    for entry in manifest['inputs']+manifest['outputs']:
        check(identity(entry['path']) == entry, 'immutable dependency identity')


def run(output, log):
    qualification = qualify()
    log.write('Thirteen accepted mathematical cases and increasing-factor rejection passed.\n')
    log.flush()
    verify_manifest(MAIN/'MANIFEST.json')
    verify_manifest(OLD/'MANIFEST.json')
    core, old = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json')
    check(not core['gate']['passed'], 'failed original mechanism gate retained')
    old_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in old['rows']}
    old_queries = {}
    with (OLD/'QUERIES.jsonl').open() as stream:
        for line in stream:
            r = json.loads(line)
            key = (r['fixture'], r['kind'], r['order'], r['level'])
            old_queries.setdefault(key, []).append(r)
    models, model_rows, rows = {}, {}, []
    querycount = 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture, kind, order = [case[k] for k in ('fixture', 'kind', 'order')]
            job = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')
            if fixture not in models:
                m = prior.model_from_saved(job['model'])
                direction = decreasing_model(m)
                models[fixture] = m
                model_rows[fixture] = dict(alpha=m['alpha'], iteration_tail=m['alpha']**32,
                                           C=m['C'], direction=direction,
                                           conditional_assignments=m['conditional_assignments'],
                                           prepare_cpu=m['prepare_cpu']+direction['cpu'])
                dec_close(m['alpha'], old['models'][fixture]['alpha'], 'previous influence row norm')
                for i, row in enumerate(m['C']):
                    for j, value in row.items():
                        dec_close(value, old['models'][fixture]['C'][i][str(j)], 'previous model influence')
            m = models[fixture]
            for level, snap in zip((256, 1024, 4096), job['snapshots']):
                key = (fixture, kind, order, level)
                start = time.process_time()
                q = prior.Belief(snap['groups'], [[D(str(x)).exp() for x in block]
                                                 for block in snap['block_log_probabilities']])
                reconstruction = time.process_time()-start
                cert = construct(m, q)
                # No exact-reference argument or file access occurs in construction.
                ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                ev = read(MAIN/f'{fixture}_{kind}_{order}_evaluation.json')[(256, 1024, 4096).index(level)]
                true_pairs = [{s: D(str(p[s[0]][s[1]])) for s in states(2)} for p in ref['pairs']]
                for field in ('b', 'v'):
                    for value, before in zip(cert['symmetric'][field], old_rows[key][field]):
                        dec_close(value, before, 'reproduced symmetric '+field)
                records = assess(m, cert, true_pairs, saved=ev['queries'], previous=old_queries[key], main=True)
                for r in records:
                    stream.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **r),
                                            default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summarize(records)
                close(summary['symmetric']['mean_r'], old_rows[key]['local']['mean_r'], 'previous mean allowance')
                check(summary['symmetric']['zero_allowances'] == old_rows[key]['local']['zero_allowances'],
                      'previous zero allowances')
                rows.append(dict(fixture=fixture, kind=kind, order=order, level=level,
                                 primary=cert['primary'], direction_only_vectors=cert['direction_only'],
                                 q_reconstruction_cpu=reconstruction, controls_cpu=cert['controls_cpu'],
                                 main_cost=case['cost'], **summary))
                querycount += len(records)
            log.write(f'Completed {fixture} {kind} {order}; all three saved budgets retained.\n')
            log.flush()
    check(len(rows) == 96 and querycount == 13056, 'all saved checkpoints and queries retained')
    summary = {}
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [r for r in rows if r['kind'] == kind and r['level'] == level]
            item = {key: stats.fmean(r[key] for r in rr)
                    for key in ('original_mean_r', 'exact_mean_r', 'q_reconstruction_cpu', 'controls_cpu')}
            item['primary_cpu'] = stats.fmean(r['primary']['cpu'] for r in rr)
            item['queries'] = sum(r['queries'] for r in rr)
            for name in METHODS:
                pp = [r[name] for r in rr]
                classes = Counter()
                for p in pp:
                    classes.update(p['classifications'])
                item[name] = {key: stats.fmean(p[key] for p in pp) for key in ('mean_r', 'mean_regret')}
                item[name].update({key: sum(p[key] for p in pp) for key in
                                   ('zero_allowances', 'improved_vs_symmetric', 'tied_vs_symmetric', 'worse_vs_symmetric')})
                item[name].update({key: max(p[key] for p in pp) for key in ('max_actual_risk', 'max_gain_vs_symmetric')})
                item[name]['classifications'] = dict(classes)
            item['marginal_cap_increment'] = dict(mean=stats.fmean(r['marginal_cap_increment']['mean'] for r in rr),
                                                 maximum=max(r['marginal_cap_increment']['maximum'] for r in rr),
                                                 improved=sum(r['marginal_cap_increment']['improved'] for r in rr),
                                                 tied=sum(r['marginal_cap_increment']['tied'] for r in rr))
            # Immutable baselines are reused, not fitted or recomputed.
            item['prior_kl_baselines'] = {name: old['summary'][kind+'_'+str(level)][name]
                                          for name in ('pinsker', 'binary')}
            summary[kind+'_'+str(level)] = item
    return dict(qualification=qualification, models=model_rows, rows=rows, summary=summary,
                checkpoints=len(rows), original_queries=querycount,
                new_certified_policies=2*querycount, reproduced_symmetric_policies=querycount)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen signed checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen signed specification')
    check(identity(prior.__file__)['sha256'] == 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6',
          'pinned unchanged helper')
    check(identity(OLD/'MANIFEST.json')['sha256'] == '0974424e5331b5394a421f9a9c14f955754456843cb936dacdb589bf6fb358e9',
          'pinned symmetric record')
    paths = [SPEC, Path(__file__), Path(prior.__file__), HERE/'FEP_LOCAL_RISK_BOUND_V1.md',
             HERE/'FEP_LOCAL_RISK_BOUND_V1_REPORT.md', OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl',
             MAIN/'MANIFEST.json', MAIN/'CORE.json', MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
             HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(path) for path in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    (DEST/'SPECIFICATION.md').write_bytes(SPEC.read_bytes())
    (DEST/'CHECKER_SOURCE.py').write_bytes(Path(__file__).read_bytes())
    (DEST/'REUSED_HELPER.py').write_bytes(Path(prior.__file__).read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='signed local certificate audit; immutable saved beliefs; no inference',
                    python=platform.python_version(), decimal_precision=60, propagation_steps=32,
                    cpu_processes=1, reused_kl_results=True)
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
