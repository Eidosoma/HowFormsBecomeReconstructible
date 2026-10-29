#!/usr/bin/env python3
"""Independent integer optimality and saved-trace verifier; no planner import."""
from __future__ import annotations

import bisect
from datetime import datetime, timezone
from fractions import Fraction as Q
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    begin = time.monotonic()
    a = Path(sys.argv[1])
    checks = {}

    def check(label, condition):
        checks[label] = checks.get(label, 0)+1
        if not condition:
            raise AssertionError(label)

    def load(name):
        return json.loads((a/name).read_text())

    manifest, freeze, result = load('MANIFEST.json'), load('FREEZE.json'), load('RESULTS.json')
    check('completed', manifest['status'] == 'COMPLETE')
    for name, expected in manifest['outputs'].items():
        check('output_hash', digest(a/name) == expected)
    for name, expected in freeze['inputs'].items():
        check('frozen_input', digest(name) == expected)
    for name, expected in freeze['snapshots'].items():
        check('source_snapshot', digest(a/'inputs'/name) == expected)
    T = result['T']
    check('fixed_parameters', T == 100 and Q(result['rho']) == Q(1, 2)
          and Q(result['c']) == Q(1, 10))

    # U = 10*(2*T-k)*V. Cancellation makes every Bellman value an integer.
    tables, score_tables = {}, {}
    for cap in (False, True):
        values = {(T+1, k, d): 0 for k in range(T+1) for d in (0, 1)}
        scores_at = {}
        for t in range(T, 0, -1):
            for k in range(t):
                continuation = values[t+1, k, 1 if cap else 0]
                purchase = (2*T-k)+values[t+1, t, 0]
                if cap:
                    purchase += (t-k)*((T-t)//2)
                scores = {'F': 10*(t-k)+continuation,
                          'R': 10*(2*T-t)+continuation, 'B': purchase}
                for d in (0, 1):
                    available = {'B': purchase} if cap and d else scores
                    values[t, k, d] = min(available.values())
                    scores_at[t, k, d] = available
        tables[cap], score_tables[cap] = values, scores_at
        name = 'full_gap1' if cap else 'full'
        check('independent_full_optimum', Q(values[1, 0, 0], 20*T) == Q(result['bellman_total'][name]))

    @lru_cache(None)
    def truncated(t, k, h):
        if h == 0:
            return 0
        follow = 10*(t-k)+truncated(t+1, k, h-1)
        invert = 10*(2*T-t)+truncated(t+1, k, h-1)
        buy = (2*T-k)+truncated(t+1, t, h-1)
        return min(follow, invert, buy)

    def select(scores):
        minimum = min(scores.values())
        return next(x for x in ('B', 'F', 'R') if scores.get(x) == minimum)

    summaries = {}
    for name, data in result['policies'].items():
        worlds = data['worlds']
        check('complete_world_set', [w['onset'] for w in worlds] == [None, *range(1, T+1)])
        full_costs, post_costs, mean_buys, mean_errors = [], [], 0, 0
        missing = 0
        erase_actions = set()
        for w in worlds:
            tau, actions = w['onset'], w['actions']
            check('action_length', len(actions) == T and set(actions) <= set('FBR'))
            k, gap, learned = 0, 0, False
            error_count, purchase_count, post_ticks, first, extra = 0, 0, 0, None, 0
            for t, action in enumerate(actions, 1):
                cap = name in ('full_gap1', 'hybrid_ct4_gap1')
                if cap:
                    check('paid_gap', not gap or action == 'B')
                if name == 'always':
                    expected = 'B'
                elif name == 'erase':
                    expected = select({'F': 10*t, 'R': 10*(2*T-t), 'B': 2*T})
                elif name == 'hybrid_ct4_gap1' and gap:
                    expected = 'B'
                elif learned:
                    remaining = T-t+1
                    if name == 'full_gap1':
                        scores = {'F': 10+remaining//2, 'R': remaining//2,
                                  'B': 1+(remaining-1)//2}
                        if gap:
                            scores = {'B': scores['B']}
                        expected = select(scores)
                    else:
                        expected = 'R'
                elif name in ('full', 'full_gap1'):
                    expected = select(score_tables[name == 'full_gap1'][t, k, gap])
                else:
                    h = min(4, T-t+1)
                    expected = select({'F': 10*(t-k)+truncated(t+1, k, h-1),
                                       'R': 10*(2*T-t)+truncated(t+1, k, h-1),
                                       'B': 2*T-k+truncated(t+1, t, h-1)})
                check('saved_action_optimality', expected == action)
                # Only this accounting section has access to the physical onset.
                changed = tau is not None and t >= tau
                error = int(action != 'B' and (action == 'R') != changed)
                purchase = int(action == 'B')
                error_count += error
                purchase_count += purchase
                if changed:
                    post_ticks += 10*error+purchase
                if purchase:
                    extra += int(learned)
                    if changed and first is None:
                        first = t
                    if name != 'erase':
                        if changed:
                            learned = True
                        else:
                            k = t
                gap = 0 if purchase else 1
            cost = Q(10*error_count+purchase_count, 10)
            check('world_cost', cost == Q(w['cost']))
            check('world_counts', (error_count, purchase_count) == (w['errors'], w['purchases']))
            check('world_first_purchase', first == w['first_post_purchase'])
            check('world_post_detection_purchases', extra == w['purchases_after_retained_detection'])
            full_costs.append(cost)
            if tau is not None:
                recovery = Q(post_ticks, 10*(T-tau+1))
                check('world_recovery', recovery == Q(w['recovery']))
                post_costs.append(recovery)
                mean_buys += purchase_count
                mean_errors += error_count
                missing += first is None
            else:
                check('stable_has_no_recovery', w['recovery'] is None)
            if name == 'erase':
                erase_actions.add(actions)
        actual = {'stable': full_costs[0]/T,
                  'changed_full': sum(full_costs[1:])/(T*T),
                  'recovery': sum(post_costs)/T,
                  'prior_full': (full_costs[0]/T+sum(full_costs[1:])/(T*T))/2,
                  'mean_purchases_stable': worlds[0]['purchases'],
                  'mean_purchases_changed': Q(mean_buys, T),
                  'mean_errors_changed': Q(mean_errors, T),
                  'missing_post_purchase_worlds': missing}
        for field, value in actual.items():
            check('summary_'+field, value == Q(data['summary'][field]))
        for onset in (13, 38, 63, 88):
            check('onset_summary', post_costs[onset-1] == Q(data['summary']['onsets'][str(onset)]))
        if name == 'erase':
            check('erased_memory', len(erase_actions) == 1)
        summaries[name] = actual

    # Independent backward integer recursion for each remaining purchase budget.
    scale = 10*T*math.lcm(*range(1, T+1))
    edge = {}
    for k in range(T):
        for j in range(k+1, T+1):
            edge[k, j] = sum((10*(j-u)+1)*(scale//(10*T*(T-u+1)))
                             for u in range(k+1, j+1))
    suffix = {k: (T-k)*(scale//T) for k in range(T+1)}
    optima = [suffix[0]]
    for m in range(1, T+1):
        suffix = {k: min(edge[k, j]+suffix[j] for j in range(k+1, T-m+2))
                  for k in range(T-m+1)}
        optima.append(suffix[0])
    rows = result['frontier']['rows']
    check('all_budgets', [r['m'] for r in rows] == list(range(T+1)))
    feasible = []
    nondominated = []
    for row in rows:
        m, schedule = row['m'], row['schedule']
        check('schedule_support', len(schedule) == m and schedule == sorted(set(schedule))
              and all(1 <= x <= T for x in schedule))
        post, changed_total, errors, purchases = Q(0), Q(0), 0, 0
        for u in range(1, T+1):
            i = bisect.bisect_left(schedule, u)
            if i < m:
                delay = schedule[i]-u
                ticks = 10*delay+1
                count = i+1
            else:
                delay, count = T-u+1, m
                ticks = 10*delay
            post += Q(ticks, 10*(T-u+1))
            changed_total += Q(10*delay+count, 10)
            errors += delay
            purchases += count
        stable, rec, changed = Q(m, 10*T), post/T, changed_total/(T*T)
        metrics = {'stable': stable, 'recovery': rec, 'changed_full': changed,
                   'prior_full': (stable+changed)/2,
                   'mean_errors_changed': Q(errors, T),
                   'mean_purchases_changed': Q(purchases, T)}
        for field, value in metrics.items():
            check('frontier_'+field, value == Q(row[field]))
        check('independent_frontier_optimum', rec == Q(optima[m], scale))
        if stable < summaries['hybrid_ct4_gap1']['stable'] and rec < min(
                Q(1, 10), summaries['hybrid_ct4_gap1']['recovery']):
            feasible.append(m)
        if not nondominated or rec < Q(rows[nondominated[-1]]['recovery']):
            nondominated.append(m)
    check('feasibility_all', result['feasibility']['feasible_m'] == feasible)
    check('feasibility_exists', result['feasibility']['exists'] == bool(feasible))
    check('feasibility_minimum', result['feasibility']['smallest_m'] == (min(feasible) if feasible else None))
    check('nondominated', result['frontier']['nondominated_m'] == nondominated)
    hull = result['frontier']['convex_envelope_m']
    check('hull_coverage', hull[0] == 0 and hull[-1] == nondominated[-1] and hull == sorted(set(hull)))
    slopes = []
    for left, right in zip(hull, hull[1:]):
        x0, y0 = Q(rows[left]['stable']), Q(rows[left]['recovery'])
        x1, y1 = Q(rows[right]['stable']), Q(rows[right]['recovery'])
        slope = (y1-y0)/(x1-x0)
        slopes.append(slope)
        for row in rows[left:right+1]:
            check('hull_lower_bound', Q(row['recovery']) >= y0+slope*(Q(row['stable'])-x0))
    check('hull_convex', all(b > a for a, b in zip(slopes, slopes[1:])))
    for name in ('ct4', 'always', 'erase', 'full_gap1'):
        check('full_dominance', summaries['full']['prior_full'] <= summaries[name]['prior_full'])
    check('constrained_dominance', summaries['full_gap1']['prior_full'] <= summaries['hybrid_ct4_gap1']['prior_full'])
    for name, cap in [('full', False), ('full_gap1', True)]:
        check('optimal_policy_evaluation', summaries[name]['prior_full']*T == Q(tables[cap][1, 0, 0], 20*T))
    started = load('STARTED.json')
    check('cpu_limit', 1 <= len(started['affinity']) <= 4 and started['nice'] >= 10)
    check('detach_rule', load('BENCHMARK.json')['forecast_seconds'] <= 600 or started['detached'])
    record = {'passed': True, 'completed': datetime.now(timezone.utc).isoformat(),
              'seconds': time.monotonic()-begin, 'checks': checks,
              'total_checks': sum(checks.values()), 'simulated_policy_episodes_rerun': 0,
              'manifest_sha256': digest(a/'MANIFEST.json'),
              'source_sha256': digest(__file__), 'feasibility': result['feasibility']}
    with (a/'READBACK.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
