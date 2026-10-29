#!/usr/bin/env python3
"""Independent normalized Bayes Bellman and integer forward verification."""
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import sys
import time

sys.set_int_max_str_digits(0)


def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())


def main():
    start, a = time.monotonic(), Path(sys.argv[1])
    counts, totals = {}, dict(graphs=0, nodes=0, worlds=0, certificates=0, diagnostic_worlds=0)

    def check(name, ok):
        counts[name] = counts.get(name, 0)+1
        if not ok: raise AssertionError(name)

    def equal(saved, actual, label):
        if isinstance(actual, dict):
            check(label+'_keys', set(saved) == set(actual))
            for k, v in actual.items(): equal(saved[k], v, label)
        elif isinstance(actual, (tuple, list)):
            check(label+'_length', len(saved) == len(actual))
            for x, y in zip(saved, actual): equal(x, y, label)
        else:
            check(label, saved is None if actual is None else Q(saved) == actual)

    manifest, freeze = load(a/'MANIFEST.json'), load(a/'FREEZE.json')
    check('complete', manifest['status'] == 'COMPLETE')
    for p, h in manifest['outputs'].items(): check('output_hash', digest(a/p) == h)
    for p, h in freeze['inputs'].items(): check('input_hash', digest(p) == h)
    for p, h in freeze['snapshots'].items(): check('snapshot_hash', digest(a/'inputs'/p) == h)
    refs = {}
    for path in freeze['inputs']:
        if path.endswith('/RESULTS.json'):
            folder = Path(path).parent
            key = 'mismatch' if 'noise-mismatch' in path else 'stable' if 'stable-constraint' in path else 'deterministic'
            refs[key] = load(path)
            seal, readback = load(folder/'MANIFEST.json'), load(folder/'READBACK.json')
            check('inherited_readback', readback['passed'] and readback['manifest_sha256'] == digest(folder/'MANIFEST.json'))
            check('inherited_result_hash', seal['outputs']['RESULTS.json'] == digest(path))

    def verify(case, primary):
        T, rho, noise = case['T'], Q(case['rho']), case['noises']
        M, K, price = len(noise), Q(case['budget']), Q(1, 10)
        block = [T*(rho.denominator-rho.numerator)]+[rho.numerator]*T
        g = math.gcd(*block)
        prior = tuple(w//g for w in block)*M
        hypotheses = [(e, j) for e in range(M) for j in range(T+1)]
        check('physical_parameters', Q(case['c']) == price and noise == [4, 5, 6])
        if primary:
            check('main_parameters', T == 10 and rho == Q(1, 2) and K == Q(19568652557, 204800000000))

        @lru_cache(None)
        def update(t, weights, d):
            raw = [w*(100-noise[e] if d == int(0 < j <= t) else noise[e])
                   for w, (e, j) in zip(weights, hypotheses)]
            factor = math.gcd(*raw)
            return Q(sum(raw), 100*sum(weights)), tuple(w//factor for w in raw)

        def summarize(worlds):
            rates = {}
            for e in range(M):
                rows = worlds[e*(T+1):(e+1)*(T+1)]
                s = rows[0]['cost']/T
                b = (1-rho)*s+rho*sum(w['cost'] for w in rows[1:])/(T*T)
                r = sum(w['recovery'] for w in rows[1:])/T
                rates[str(e)] = dict(stable=s, B=b, R=r, J=b+r,
                    stable_errors=rows[0]['errors'], stable_purchases=rows[0]['purchases'],
                    mean_changed_errors=sum(w['errors'] for w in rows[1:])/T,
                    mean_changed_purchases=sum(w['purchases'] for w in rows[1:])/T,
                    mean_post_errors=sum(w['post_errors'] for w in rows[1:])/T,
                    mean_post_purchases=sum(w['post_purchases'] for w in rows[1:])/T,
                    capped_first_delay=sum(w['delay'] for w in rows[1:])/T,
                    no_post_purchase_probability=sum(w['missing'] for w in rows[1:])/T)
            return dict(rates=rates, C=sum(s['J'] for s in rates.values())/M, S_last=rates[str(M-1)]['stable'])

        def gate(summary):
            rates = {}
            for e, rate in enumerate(('0.04', '0.05', '0.06')):
                s = summary['rates'][str(e)]
                h = refs['mismatch']['conditions'][rate]['policies']['hybrid']['summary']
                row = dict(below_always=s['R'] < price, below_hybrid=s['R'] < Q(h['R']), stable_not_higher=s['stable'] <= K)
                row['joint'] = all(row.values())
                row['matched_stable_not_higher'] = s['stable'] <= Q(h['stable'])
                rates[rate] = row
            return dict(rates=rates, joint=all(r['joint'] for r in rates.values()))

        def merge(policies, components):
            weights = [(c['policy'], Q(c['weight'])) for c in components]
            check('mixture_probability', sum(w for _, w in weights) == 1 and all(w >= 0 for _, w in weights))
            worlds = []
            for i in range(M*(T+1)):
                example = policies[weights[0][0]]['worlds'][i]
                row = {k: example[k] for k in ('noise_index', 'onset')}
                for k in example:
                    if k in row: continue
                    row[k] = None if example[k] is None else sum(w*policies[n]['worlds'][i][k] for n, w in weights)
                worlds.append(row)
            return dict(worlds=worlds, summary=summarize(worlds))

        rebuilt = {}
        for name, problem in case['problems'].items():
            erased = problem['erased']
            check('arm', erased == (name == 'erased') and Q(problem['budget']) == K)
            policies = {}
            for pid, policy in problem['policies'].items():
                graph = policy['graph']
                mu = None if policy['mu'] is None else Q(policy['mu'])
                totals['graphs'] += 1; totals['nodes'] += len(graph)

                @lru_cache(None)
                def value(t, w):
                    return Q(0) if t > T else min(scores(t, w).values())

                def scores(t, w):
                    out = dict(F=Q(0), R=Q(0), B=Q(0))
                    for mass, (e, j) in zip(w, hypotheses):
                        z = 0 < j <= t
                        utility = Q(1, T)+(1/(rho*(T-j+1)) if z else 0)
                        if e == M-1 and j == 0: utility += M*mu/((1-rho)*T)
                        factor = Q(mass, sum(w))*utility
                        risk = Q(100-noise[e] if z else noise[e], 100)
                        out['F'] += factor*risk
                        out['R'] += factor*(1-risk)
                        out['B'] += factor*price
                    later = value(t+1, w)
                    out['F'] += later; out['R'] += later
                    if erased: out['B'] += later
                    else:
                        for d in (0, 1):
                            probability, posterior = update(t, w, d)
                            out['B'] += probability*value(t+1, posterior)
                    return out

                check('initial_beliefs', graph[0]['t'] == 1 and tuple(graph[0]['weights']) == prior)
                reachable = {0}
                for i in sorted(range(len(graph)), key=lambda j: graph[j]['t']):
                    node = graph[i]
                    t, w, action = node['t'], tuple(node['weights']), node['action']
                    check('reachable', i in reachable)
                    check('action_interface', set(node) == {'t', 'weights', 'action', 'children'})
                    check('canonical_joint_support', len(w) == M*(T+1) and min(w) > 0 and math.gcd(*w) == 1)
                    if erased: check('erased_belief', w == prior)
                    if mu is None: check('floor_action', action == 'F')
                    else:
                        values = scores(t, w)
                        check('optimal_action', action == min(('B', 'F', 'R'), key=lambda x: values[x]))
                    expected = ({str(d): w if erased else update(t, w, d)[1] for d in (0, 1)}
                                if action == 'B' else {'N': w})
                    check('observation_interface', set(expected) == set(node['children']))
                    for label, next_w in expected.items():
                        child = node['children'][label]
                        if t == T: check('terminal', child is None)
                        else:
                            check('joint_bayes_edge', child is not None and graph[child]['t'] == t+1
                                  and tuple(graph[child]['weights']) == next_w)
                            reachable.add(child)
                if mu is not None: check('normalized_root', Q(policy['root']) == value(1, prior))
                value.cache_clear()

                want_diag = pid in problem['diagnostics']
                worlds, diagnostic_worlds = [], []
                den = 100**T
                for e in range(M):
                    for tau in [None, *range(1, T+1)]:
                        active = {(0, True): 1}
                        err = buy_sum = posterr = postbuy = delay = missing = terminal_mass = 0
                        prob_true, brier = Q(0), Q(0)
                        for t in range(1, T+1):
                            following = defaultdict(int)
                            for (i, unseen), mass in active.items():
                                node = graph[i]
                                check('forward_time', node['t'] == t)
                                post = tau is not None and t >= tau
                                buy = node['action'] == 'B'
                                risk = 100-noise[e] if post else noise[e]
                                factor = 100**(T-t)
                                error_num = 0 if buy else risk if node['action'] == 'F' else 100-risk
                                err += mass*error_num*factor
                                buy_sum += mass*int(buy)*100*factor
                                if post:
                                    posterr += mass*error_num*factor
                                    postbuy += mass*int(buy)*100*factor
                                    delay += mass*int(unseen and not buy)*100*factor
                                still_unseen = unseen and not (post and buy)
                                branches = [('0', 100-risk), ('1', risk)] if buy else [('N', 100)]
                                for label, n in branches:
                                    moved = mass*n
                                    child = node['children'][label]
                                    if t < T: following[child, still_unseen] += moved
                                    else:
                                        check('forward_terminal', child is None)
                                        terminal_mass += moved
                                        missing += moved*int(still_unseen)
                                        if want_diag:
                                            w = tuple(node['weights'])
                                            if buy and not erased: w = update(t, w, int(label))[1]
                                            q = [Q(sum(w[j*(T+1):(j+1)*(T+1)]), sum(w)) for j in range(M)]
                                            prob_true += Q(moved, den)*q[e]
                                            brier += Q(moved, den)*sum((p-int(j == e))**2 for j, p in enumerate(q))
                            active = following
                        check('unit_world_mass', terminal_mass == den)
                        er, bu, pe, pb, de, mi = [Q(x, den) for x in (err, buy_sum, posterr, postbuy, delay, missing)]
                        row = dict(noise_index=e, onset=tau, cost=er+price*bu, errors=er, purchases=bu,
                            post_cost=pe+price*pb, post_errors=pe, post_purchases=pb, delay=de, missing=mi,
                            recovery=None if tau is None else (pe+price*pb)/(T-tau+1))
                        worlds.append(row); totals['worlds'] += 1
                        if want_diag:
                            diagnostic_worlds.append(dict(noise_index=e, onset=tau, true_probability=prob_true, brier=brier))
                            totals['diagnostic_worlds'] += 1
                summary = summarize(worlds)
                equal(policy['worlds'], worlds, 'physical_world')
                equal(policy['summary'], summary, 'physical_summary')
                if mu is not None: check('objective_identity', Q(policy['root']) == summary['C']+mu*summary['S_last'])
                policies[pid] = dict(worlds=worlds, summary=summary)
                if want_diag:
                    per_noise = {}
                    for e in range(M):
                        group = diagnostic_worlds[e*(T+1):(e+1)*(T+1)]
                        per_noise[str(e)] = {k:(1-rho)*group[0][k]+rho*sum(w[k] for w in group[1:])/T for k in ('true_probability', 'brier')}
                    average = {k:sum(v[k] for v in per_noise.values())/M for k in ('true_probability', 'brier')}
                    check('proper_posterior_identity', average['brier'] == 1-average['true_probability'])
                    initial = 1-Q(1, M)
                    check('bayes_brier_nonincrease', average['brier'] <= initial)
                    if erased: check('erased_noise_unlearned', all(v['true_probability'] == Q(1, M) and v['brier'] == initial for v in per_noise.values()))
                    equal(problem['diagnostics'][pid], dict(worlds=diagnostic_worlds, rates=per_noise, average=average,
                          prior_brier=initial, brier_gain=initial-average['brier']), 'noise_diagnostics')

            solution = merge(policies, problem['solution']['components'])
            equal(problem['solution']['worlds'], solution['worlds'], 'solution_worlds')
            equal(problem['solution']['summary'], solution['summary'], 'solution_summary')
            cert, s = problem['certificate'], solution['summary']
            mu = Q(cert['mu']); oracle = problem['policies'][cert['oracle']]
            bound = Q(oracle['root'])-mu*K
            check('certificate_multiplier', mu >= 0 and mu == Q(oracle['mu']))
            check('relaxed_budget', s['S_last'] <= K)
            check('complementarity', mu*(s['S_last']-K) == 0)
            check('exact_dual_gap', s['C'] == bound == Q(cert['lower_bound']) and Q(cert['duality_gap']) == 0)
            totals['certificates'] += 1
            feasible = [n for n, p in policies.items() if all(v['stable'] <= K for v in p['summary']['rates'].values())]
            best = min(feasible, key=lambda n:(policies[n]['summary']['C'], n))
            check('best_saved_deterministic', best == problem['best_saved_feasible_deterministic'])
            check('full_stable_optimum', problem['full_stable_optimum'] == all(v['stable'] <= K for v in s['rates'].values()))
            check('oracle_limit', problem['oracle_calls'] == len(policies)-1 <= 128)
            for step in problem['trace']:
                p = problem['policies'][step['oracle']]
                if 'low' in step:
                    low, high = policies[step['low']]['summary'], policies[step['high']]['summary']
                    slope = (low['C']-high['C'])/(high['S_last']-low['S_last'])
                    chord = low['C']+slope*low['S_last']
                    check('search_bracket', low['S_last'] <= K < high['S_last'])
                    check('search_slope', Q(p['mu']) == slope and Q(step['chord']) == chord)
                    check('search_lower_bound', Q(p['root']) <= chord)
                    if step['decision'] == 'dual_certificate': check('support_equality', Q(p['root']) == chord)
                    elif step['decision'] == 'exact_budget': check('search_exact_budget', Q(p['summary']['S_last']) == K)
                    else: check('search_replacement', step['decision'] == ('replace_low' if Q(p['summary']['S_last']) < K else 'replace_high'))
                else: check('unconstrained_feasible', step['decision'] == 'unconstrained_feasible' and Q(p['mu']) == 0 and Q(p['summary']['S_last']) <= K)
            if primary:
                check('scientific_gates', problem['gate'] == gate(s))
                check('deterministic_gates', problem['deterministic_gate'] == gate(policies[best]['summary']))
            rebuilt[name] = dict(policies=policies, solution=solution)

        if primary:
            controls, frozen = case['controls'], {}
            for name, saved in controls['frozen'].items():
                worlds = []
                for e, rate in enumerate(('0.04', '0.05', '0.06')):
                    for row in refs['mismatch']['conditions'][rate]['policies'][name]['worlds']:
                        v = {k: None if row[k] is None else Q(row[k]) for k in
                             ('cost','errors','purchases','post_cost','post_errors','post_purchases','delay','missing','recovery')}
                        worlds.append(dict(noise_index=e, onset=row['onset'], **v))
                p = frozen[name] = dict(worlds=worlds, summary=summarize(worlds))
                equal(saved, p, 'frozen_control')
            pool = controls['fixed_pool']
            lower, upper = Q(0), Q(1)
            for e in range(M):
                l = frozen['low_component']['summary']['rates'][str(e)]['stable']
                h = frozen['anchor']['summary']['rates'][str(e)]['stable']
                if h > l: upper = min(upper, (K-l)/(h-l))
                elif h < l: lower = max(lower, (K-l)/(h-l))
                else: check('pool_constant_constraint', l <= K)
            check('pool_feasible_interval', 0 <= lower <= upper <= 1 and [Q(x) for x in pool['feasible_interval']] == [lower, upper])
            p = upper if frozen['anchor']['summary']['C'] < frozen['low_component']['summary']['C'] else lower
            check('pool_optimal_weight', Q(pool['probability_high']) == p)
            check('pool_components', [(c['policy'], Q(c['weight'])) for c in pool['components']] == [('low_component', 1-p), ('anchor', p)])
            result = merge(frozen, pool['components'])
            equal(pool['worlds'], result['worlds'], 'pool_worlds')
            equal(pool['summary'], result['summary'], 'pool_summary')
            check('pool_gates', pool['gate'] == gate(result['summary']))
            delta = rebuilt['retained']['policies']['oracle000']['summary']['C']-frozen['recovery']['summary']['C']
            check('matched_objective_control', delta == Q(controls['unconstrained_C_delta']) and delta <= 0)
            inherited = refs['stable']['conditions']['1']['problems']['erased_recovery_bound']
            ic = inherited['certificate']
            bound = Q(inherited['policies'][ic['oracle']]['root'])-Q(ic['mu'])*K
            check('inherited_erased_scope', inherited['erased'] and inherited['alpha'] == 0 and Q(inherited['budget']) == K)
            check('inherited_erased_bound', bound == Q(ic['lower_bound']) == Q(case['inherited_erased_R_lower_bound'])
                  == Q(inherited['solution']['summary']['R']) and bound > price and Q(ic['duality_gap']) == 0)

    verify(load(a/'RESULTS.json'), True)
    for case in load(a/'SHORT_FIXTURES.json'): verify(case, False)
    resources, bench = load(a/'STARTED.json'), load(a/'BENCHMARK.json')
    check('resources', len(resources['affinity']) == 1 and resources['nice'] >= 10
          and all(v == '1' for v in resources['library_threads'].values()))
    check('detachment', bench['forecast_seconds'] <= 600 or resources['detached'])
    check('ceiling', bench['forecast_seconds'] <= 7200)
    result = dict(passed=True, completed=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-start,
        checks=counts, total_checks=sum(counts.values()), totals=totals, manifest_sha256=digest(a/'MANIFEST.json'),
        source_sha256=digest(__file__), method='Independent normalized joint Bayes Bellman; integer forward world occupancy; exact primal/dual and control verification.')
    with (a/'READBACK.json').open('x') as out:
        json.dump(result, out, indent=2, sort_keys=True); out.write('\n')
    print(json.dumps(dict(passed=True, checks=result['total_checks'], seconds=result['seconds'], totals=totals)), flush=True)


if __name__ == '__main__': main()
