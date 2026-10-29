#!/usr/bin/env python3
"""Independent integer Bellman and observable-history verification."""
from datetime import datetime, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    start = time.monotonic()
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
    for path, expected in manifest['outputs'].items():
        check('output_hash', digest(a/path) == expected)
    for path, expected in freeze['inputs'].items():
        check('input_hash', digest(path) == expected)
    for name, expected in freeze['snapshots'].items():
        check('snapshot_hash', digest(a/'inputs'/name) == expected)
    T = result['T']
    check('fixed_model', T == 100 and Q(result['rho']) == Q(1, 2) and Q(result['c']) == Q(1, 10))
    check('fixed_arms', set(result['policies']) == {'ordinary', 'recovery', 'erased'})
    L = math.lcm(*range(1, T+1))
    H = [0]
    for t in range(1, T+1):
        H.append(H[-1]+L//(T-t+1))

    def best(scores):
        value = min(scores.values())
        return next(x for x in ('B', 'F', 'R') if scores[x] == value)

    # U = 10*T*LCM(1..T)*(2*T-k)*V, using rho=1/2 and integer lambda.
    all_scores, roots = {}, {}
    for name, lam, erased in [('ordinary', 0, False), ('recovery', 1, False), ('erased', 1, True)]:
        values = {(T+1, k): 0 for k in range(T+1)}
        scores_at = {}
        for t in range(T, 0, -1):
            for k in ([0] if erased else range(t)):
                h = H[t]-H[k]
                immediate = {'F': 10*L*(t-k)+20*T*lam*h,
                             'R': 10*L*(2*T-t),
                             'B': L*(2*T-k)+2*T*lam*h}
                future = values[t+1, k]
                scores = {'F': immediate['F']+future, 'R': immediate['R']+future,
                          'B': immediate['B']+(future if erased else values[t+1, t])}
                values[t, k] = min(scores.values())
                scores_at[t, k] = scores
        roots[name] = Q(values[1, 0], 10*T*L*2*T)
        all_scores[name] = scores_at
        check('independent_bellman_root', roots[name] == Q(result['policies'][name]['root_value']))

    old_path = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-checking-tradeoff-v1/attempt-01/RESULTS.json')
    check('baseline_frozen', str(old_path) in freeze['inputs'])
    old = json.loads(old_path.read_text())
    summaries = {}
    for name, record in result['policies'].items():
        lam = 0 if name == 'ordinary' else 1
        erased = name == 'erased'
        worlds = record['worlds']
        check('all_worlds', [w['onset'] for w in worlds] == [None, *range(1, T+1)])
        costs, recoveries, weighted_values = [], [], []
        changed_errors, changed_purchases, missing, unverified = 0, 0, 0, 0
        history_actions = {}
        for index, world in enumerate(worlds):
            onset, actions = world['onset'], world['actions']
            check('action_support', len(actions) == T and set(actions) <= set('FBR'))
            k, detected, history = 0, False, []
            errors, purchases, post_ticks, first = 0, 0, 0, None
            unverified_times = []
            for t, action in enumerate(actions, 1):
                check('saved_action_optimality', action == ('R' if detected else best(all_scores[name][t, k])))
                key = (t, tuple(history))
                check('identical_paid_history', history_actions.setdefault(key, action) == action)
                if action == 'R' and not detected:
                    unverified_times.append(t)
                # Physical onset is used only for evaluation and purchased feedback.
                changed = onset is not None and t >= onset
                error = int(action != 'B' and (action == 'R') != changed)
                buy = int(action == 'B')
                errors += error
                purchases += buy
                if changed:
                    post_ticks += 10*error+buy
                if buy:
                    if changed and first is None:
                        first = t
                    if not erased:
                        history.append((t, int(changed)))
                        if changed:
                            detected = True
                        else:
                            k = t
            cost = Q(10*errors+purchases, 10)
            recovery = None if onset is None else Q(post_ticks, 10*(T-onset+1))
            weighted = cost/T+(2*lam*recovery if onset is not None else 0)
            check('physical_cost', cost == Q(world['cost']))
            check('counts', (errors, purchases) == (world['errors'], world['purchases']))
            check('recovery_cost', (recovery is None and world['recovery'] is None) or
                  (recovery is not None and recovery == Q(world['recovery'])))
            check('weighted_world_cost', weighted == Q(world['weighted_cost']))
            check('first_purchase', first == world['first_post_purchase'])
            check('unverified_inversion_times', unverified_times == world['unverified_inversions'])
            costs.append(cost)
            weighted_values.append(weighted)
            unverified += len(unverified_times)
            if onset is not None:
                recoveries.append(recovery)
                changed_errors += errors
                changed_purchases += purchases
                missing += first is None
            if name == 'ordinary':
                previous = old['policies']['full']['worlds'][index]
                check('old_actions_identical', previous['actions'] == actions)
                check('old_costs_identical', Q(previous['cost']) == cost)
                check('old_onsets_identical', previous['onset'] == onset)
            if erased:
                check('erased_state', k == 0 and not detected and not history)
        stable = costs[0]/T
        changed = sum(costs[1:])/(T*T)
        B, R = (stable+changed)/2, sum(recoveries)/T
        actual = {'stable': stable, 'changed_full': changed, 'B': B, 'R': R,
                  'J': B+lam*R, 'lambda': lam,
                  'stable_errors': worlds[0]['errors'], 'stable_purchases': worlds[0]['purchases'],
                  'mean_changed_errors': Q(changed_errors, T),
                  'mean_changed_purchases': Q(changed_purchases, T),
                  'missing_post_purchase_worlds': missing, 'unverified_inversions': unverified}
        for field, value in actual.items():
            check('summary_'+field, value == Q(record['summary'][field]))
        check('belief_world_identity', actual['J'] == (weighted_values[0]+sum(weighted_values[1:])/T)/2)
        check('world_bellman_identity', actual['J'] == roots[name])
        for onset in (13, 38, 63, 88):
            check('onset_summary', Q(record['summary']['onsets'][str(onset)]) == recoveries[onset-1])
        summaries[name] = actual

    sources = {name: item['summary'] for name, item in old['policies'].items()}
    sources['frontier_18'] = old['frontier']['rows'][18]
    check('reference_names', set(result['references']) == set(sources))
    for name, s in sources.items():
        expected = {'stable': Q(s['stable']), 'B': Q(s['prior_full']), 'R': Q(s['recovery']),
                    'J1': Q(s['prior_full'])+Q(s['recovery'])}
        for field, value in expected.items():
            check('saved_reference', value == Q(result['references'][name][field]))
    hybrid = result['references']['hybrid_ct4_gap1']
    r = summaries['recovery']
    gate = {'below_always': r['R'] < Q(1, 10), 'below_hybrid': r['R'] < Q(hybrid['R']),
            'stable_not_higher': r['stable'] <= Q(hybrid['stable'])}
    gate['joint'] = all(gate.values())
    check('feasibility_gate', gate == result['gate'])
    check('ordinary_cost_optimal', summaries['ordinary']['B'] <= r['B'])
    check('recovery_monotonicity', r['R'] <= summaries['ordinary']['R'])
    check('weighted_optimality', r['J'] <= summaries['ordinary']['B']+summaries['ordinary']['R'])
    check('retention_value', r['J'] <= summaries['erased']['J'])

    counter = load('QUALIFICATION.json')['terminal_counterexample']
    direct = {'F': Q(0), 'R': Q(0), 'B': Q(0)}
    mean_weight = Q(0)
    for onset in [None, *range(1, 41)]:
        probability = Q(1, 2) if onset is None else Q(1, 80)
        weight = Q(1, 40)+(Q(2, 41-onset) if onset is not None else 0)
        mean_weight += probability*weight
        direct['F'] += probability*weight*int(onset is not None)
        direct['R'] += probability*weight*int(onset is None)
        direct['B'] += probability*weight/10
    for action, value in direct.items():
        check('counterexample_latent_sum', value == Q(counter['correct'][action]))
    naive = {'F': mean_weight/2, 'R': mean_weight/2, 'B': mean_weight/10}
    for action, value in naive.items():
        check('counterexample_product', value == Q(counter['product_shortcut'][action]))
    check('counterexample_wrong_choice', best(direct) == 'R' and best(naive) == 'B')
    started = load('STARTED.json')
    check('resources', 1 <= len(started['affinity']) <= 4 and started['nice'] >= 10)
    check('detachment', load('BENCHMARK.json')['forecast_seconds'] <= 600 or started['detached'])
    record = {'passed': True, 'completed': datetime.now(timezone.utc).isoformat(),
              'seconds': time.monotonic()-start, 'checks': checks, 'total_checks': sum(checks.values()),
              'simulated_policy_episodes_rerun': 0, 'gate': gate,
              'manifest_sha256': digest(a/'MANIFEST.json'), 'source_sha256': digest(__file__)}
    with (a/'READBACK.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
