#!/usr/bin/env python3
"""Select full-onset policies, freeze them, then test new burst patterns."""
from fractions import Fraction as F
from pathlib import Path
import argparse
import math
import os
import platform
import subprocess
import sys
import time

import check_fep_noise_interval as io
import check_fep_burst_confidence as physical
import check_fep_burst_learning as previous
import fep_burst_alltiming_core as core

ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
STORE = BASE / 'fep-burst-alltiming-v1'
BASELINE = BASE / 'fep-noise-sequence-v1/attempt-01'
LEARNING = BASE / 'fep-burst-learning-v1/attempt-01'
SOURCES = ('FEP_BURST_ALLTIMING_V1.md', 'fep_burst_alltiming_core.py',
           'check_fep_burst_alltiming.py', 'readback_fep_burst_alltiming.py')
REFERENCES = ('FEP_BURST_LEARNING_V1.md', 'FEP_BURST_LEARNING_V1_REPORT.md',
              'fep_burst_learning_core.py', 'check_fep_burst_learning.py',
              'readback_fep_burst_learning.py', 'check_fep_burst_confidence.py',
              'readback_fep_burst_confidence.py', 'check_fep_noise_interval.py', 'check_fep_noise_switch.py')
save, read, sha, utc, log, check_freeze = io.save, io.read, io.sha, io.utc, io.log, io.check_freeze


def select_schedules(model, logger=None):
    records, best, selected_graph = [], None, None
    for mask in range(1 << model.T):
        graph = core.previous.graph_for_schedule(model, mask)
        cost = core.training(graph, model.T)
        row = dict(mask=mask, training=cost)
        records.append(row)
        if max(cost['S']) <= core.K and (best is None or (cost['C'], mask) < (best['training']['C'], best['mask'])):
            best, selected_graph = row, graph
        if logger and mask % 128 == 127:
            logger('SCHEDULES ' + str(mask + 1))
    assert best is not None
    return dict(selected=best, records=records), selected_graph


def train(a):
    model, candidates, costs = core.Model(10), {}, {}
    (a / 'candidates').mkdir()
    (a / 'bellman').mkdir()
    for frozen in (False, True):
        prefix = 'ablated' if frozen else 'full'
        for mu in core.MUS:
            name = f'{prefix}_mu{mu:02d}'
            start = time.monotonic()
            oracle = core.Oracle(model, mu, frozen)
            root, graph = oracle.root(), oracle.graph()
            cost = core.training(graph, 10)
            subjective = (cost['settings']['0']['C'] + mu * cost['settings']['0']['stable']) if frozen else cost['C'] + mu * sum(cost['S']) / 2
            assert root == subjective, name
            item = dict(graph=graph, belief='explicit', mu=mu, frozen=frozen, training=cost,
                        subjective_root=root, utility_denominator=oracle.den, bellman_states=len(oracle.cache))
            save(a / 'candidates' / f'{name}.json', item)
            previous.dump_bellman(a / 'bellman' / f'{name}.jsonl.gz', oracle)
            candidates[name] = item
            if not frozen:
                costs[name] = cost
            log(a, f'ORACLE_COMPLETE {name} states={len(oracle.cache)} seconds={time.monotonic()-start:.3f}')
    floor = core.previous.floor_graph(model)
    floor_cost = core.training(floor, 10)
    for prefix in ('full', 'ablated'):
        name = prefix + '_floor'
        item = dict(graph=floor, belief='explicit', mu=None, frozen=prefix == 'ablated', training=floor_cost)
        candidates[name] = item
        save(a / 'candidates' / f'{name}.json', item)
    costs['full_floor'] = floor_cost
    selection = core.select_pool(costs)
    save(a / 'SELECTION.json', selection)
    log(a, 'POOL_SELECTED')
    schedules, schedule = select_schedules(model, lambda msg: log(a, msg))
    save(a / 'SCHEDULES.json', schedules)
    graphs = dict(read(BASELINE / 'GRAPHS.json')['graphs'])
    mixtures = read(BASELINE / 'MIXTURES.json')
    for component in selection['selected']['components']:
        for name in (component['policy'], component['policy'].replace('full_', 'ablated_', 1)):
            graphs[name] = {k: candidates[name][k] for k in ('graph', 'belief')}
    oldgraphs = read(LEARNING / 'EVAL_GRAPHS.json')['graphs']
    oldmix = read(LEARNING / 'EVAL_MIXTURES.json')
    for name in ('reliability', 'frozen_reliability'):
        mixtures['previous_' + name] = [dict(policy='previous_' + c['policy'], weight=c['weight']) for c in oldmix[name]]
        for c in oldmix[name]:
            graphs['previous_' + c['policy']] = oldgraphs[c['policy']]
    graphs['conservative'], graphs['always'] = oldgraphs['conservative'], oldgraphs['always']
    graphs['fixed_schedule'] = dict(graph=schedule, belief='explicit')
    mixtures['reliability'] = selection['selected']['components']
    mixtures['frozen_reliability'] = [dict(policy=c['policy'].replace('full_', 'ablated_', 1), weight=c['weight']) for c in mixtures['reliability']]
    mixtures['matched_bayesian'] = mixtures['reliability']
    save(a / 'EVAL_GRAPHS.json', dict(T=10, rho='1/2', budget=core.K, graphs=graphs))
    save(a / 'EVAL_MIXTURES.json', mixtures)
    save(a / 'MODEL.json', dict(T=10, rho='1/2', p='1/20', alphas=core.TRAIN, prior=model.prior,
        states=model.states, D=model.D, loss_onsets=list(range(1, 11)), profiles=core.PROFILES,
        heldout_profiles=core.HELDOUT, mus=core.MUS, objective='mean full-prior B+R'))
    check_freeze(a)
    files = [p for p in sorted(a.rglob('*')) if p.is_file() and p.name != 'RUN_LOG.txt']
    save(a / 'CANDIDATE_FREEZE.json', dict(created=utc(), selected=selection['selected'], fixed_schedule=schedules['selected']['mask'],
        training_files={str(p.relative_to(a)): sha(p) for p in files},
        evaluation_graphs_sha256=sha(a / 'EVAL_GRAPHS.json'), evaluation_mixtures_sha256=sha(a / 'EVAL_MIXTURES.json'),
        heldout_profiles=core.HELDOUT, note='All deployment onsets carry training loss. No new-profile policy costs computed before this freeze.'))
    log(a, 'CANDIDATES_FROZEN')
    model.step.cache_clear()


def test(a):
    freeze = read(a / 'CANDIDATE_FREEZE.json')
    for name, digest in freeze['training_files'].items():
        assert sha(a / name) == digest, name
    save(a / 'TEST_STARTED.json', dict(utc=utc(), candidate_freeze_sha256=sha(a / 'CANDIDATE_FREEZE.json')))
    graphs, mixtures = read(a / 'EVAL_GRAPHS.json')['graphs'], read(a / 'EVAL_MIXTURES.json')
    traces = {name: [physical.trace(p['graph'], physical.info(p['graph'], p['belief']), 10, tau)
        for tau in [None, *range(1, 11)]] for name, p in graphs.items()}
    cases = {}
    controls = ('joint_mixture', 'fixed_pool', 'hybrid', 'always', 'conservative', 'fixed_schedule',
                'frozen_reliability', 'matched_bayesian', 'previous_reliability', 'previous_frozen_reliability')
    for label, profile in core.PROFILES.items():
        ps = {n: core.record(p['graph'], p['belief'], profile, traces[n]) for n, p in graphs.items()}
        for name, components in mixtures.items():
            ps[name] = core.mix(ps, components)
        gates = {n: physical.gates(p['summary'], ps['hybrid']['summary']) for n, p in ps.items()}
        comparisons, target = {}, ps['reliability']
        for name in controls:
            reference = ps[name]
            comparisons[name] = dict(summary={k: None if reference['summary'][k] is None else v - reference['summary'][k]
                for k, v in target['summary'].items()}, worlds=[dict(onset=u['onset'], full=(u['cost'] - v['cost']) / 10,
                recovery=None if u['recovery'] is None else u['recovery'] - v['recovery'])
                for u, v in zip(target['worlds'], reference['worlds'])])
        assert all(v is None or v == 0 for v in comparisons['matched_bayesian']['summary'].values())
        cases[label] = dict(profile=profile, held_out_pattern=label in core.HELDOUT, policies=ps, gates=gates, comparisons=comparisons)
        log(a, 'TEST_PROFILE_COMPLETE ' + label)
    result = dict(T=10, rho=F(1, 2), budget=core.K, profiles=core.PROFILES, heldout_profiles=core.HELDOUT, cases=cases,
        primary_pass=all(all(cases[n]['gates']['reliability'][k] for k in ('stable', 'always_recovery', 'hybrid_recovery')) for n in core.HELDOUT),
        mechanism={n: dict(lower_R=cases[n]['comparisons']['frozen_reliability']['summary']['R'] < 0,
            lower_J=cases[n]['comparisons']['frozen_reliability']['summary']['J'] < 0,
            full_stable=cases[n]['gates']['reliability']['stable'], ablated_stable=cases[n]['gates']['frozen_reliability']['stable']) for n in core.HELDOUT})
    save(a / 'RESULTS.json', result)
    # Reproduce the sealed odd-onset agents at the two known physical settings.
    predecessor = read(LEARNING / 'RESULTS.json')
    checks = 0
    for label, alpha in [('training_00', '0'), ('training_75', '3/4')]:
        for name in ('reliability', 'frozen_reliability'):
            old = predecessor['cases'][alpha]['policies'][name]
            new = cases[label]['policies']['previous_' + name]
            for u, v in zip(new['worlds'], old['worlds']):
                for key, value in v.items():
                    assert u[key] is None if value is None else u[key] == F(value), (label, name, key)
                    checks += 1
            for key, value in old['summary'].items():
                assert new['summary'][key] is None if value is None else new['summary'][key] == F(value), (label, name, key)
                checks += 1
    save(a / 'REPRODUCTION.json', dict(passed=True, checks=checks))
    for name, digest in freeze['training_files'].items():
        assert sha(a / name) == digest, name


def qualify():
    import readback_fep_burst_alltiming as audit
    inherited, _ = previous.qualify()
    checks, trees, worlds, fixtures = inherited['checks'], 0, 0, []
    for T in (1, 2, 3):
        m = core.Model(T)
        for frozen in (False, True):
            for mu in (0, 4):
                oracle = core.Oracle(m, mu, frozen)
                optimum = None
                for tree in io.trees(T):
                    cost = core.training(io.graph_from_tree(tree), T)
                    value = cost['settings']['0']['C'] + mu * cost['settings']['0']['stable'] if frozen else cost['C'] + mu * sum(cost['S']) / 2
                    optimum = value if optimum is None else min(optimum, value)
                assert oracle.root() == optimum
                assert all(v > 0 for row in oracle.coeff.values() for v in row)
                checks += 2
                fixtures.append(dict(T=T, mu=mu, frozen=frozen, root=oracle.root(), graph=oracle.graph()))
        profiles = sorted({(F(0),) * (T-1), (F(3,4),) * (T-1),
                           tuple([F(1,4), F(3,4)][:T-1]), tuple([F(3,4), F(1,4)][:T-1]),
                           tuple([F(1), F(0)][:T-1]), tuple([F(0), F(1)][:T-1])})
        for profile in profiles:
            masses, den = core.markov(T, profile)
            for i in range(T):
                for j in range(i+1, T):
                    joint = F(sum(p for bits, p in enumerate(masses) if bits >> i & 1 and bits >> j & 1), den)
                    assert joint == F(1,400) + F(19,400) * math.prod(profile[i:j])
                    checks += 1
        for tree in io.trees(T):
            trees += 1
            graph = physical.history.graph_from_tree(tree, T, F(1,2), 'nominal_5_percent')
            qs, independent = physical.info(graph, 'nominal_5_percent'), audit.flow.beliefs(graph, 'nominal_5_percent')
            for tau in [None, *range(1,T+1)]:
                traces = physical.trace(graph, qs, T, tau)
                for profile in profiles:
                    actual = core.evaluate(graph, qs, T, tau, profile, traces)
                    assert actual == audit.forward(graph, independent, T, tau, profile)
                    checks += 1
                    worlds += 1
                    if not profile or len(set(profile)) == 1:
                        constant = physical.evaluate(graph, qs, T, tau, profile[0] if profile else F(0), traces)
                        assert all(actual[k] == v for k, v in constant.items())
                        checks += 1
        select_schedules(m)
    return dict(passed=True, checks=checks, inherited_filter_checks=inherited['checks'],
                new_exhaustive_oracles=12, short_trees=trees, variable_profile_worlds=worlds), fixtures


def run(a, detached):
    check_freeze(a)
    forecast = read(a / 'BENCHMARK.json')['forecast_seconds']
    assert forecast <= 7200 and (forecast <= 600 or detached)
    save(a / 'STARTED.json', dict(utc=utc(), pid=os.getpid(), sid=os.getsid(0), nice=os.getpriority(os.PRIO_PROCESS, 0),
                               affinity=sorted(os.sched_getaffinity(0)), detached=detached))
    start = time.monotonic()
    log(a, 'TRAINING_START')
    train(a)
    log(a, 'TEST_START')
    test(a)
    check_freeze(a)
    log(a, 'MAIN_COMPLETE')
    save(a / 'MANIFEST.json', dict(status='COMPLETE', finished=utc(), wall_seconds=time.monotonic()-start,
        outputs={str(p.relative_to(a)): sha(p) for p in sorted(a.rglob('*')) if p.is_file()}))
    with (a / 'READBACK_STDOUT.log').open('x') as out:
        subprocess.run([sys.executable, '-B', str(ROOT / 'readback_fep_burst_alltiming.py'), str(a)], stdout=out, stderr=subprocess.STDOUT, check=True)
    print('READBACK_COMPLETE ' + str(a), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='attempt-01')
    parser.add_argument('--main-only', action='store_true')
    parser.add_argument('--detached', action='store_true')
    args = parser.parse_args()
    assert args.attempt.startswith('attempt-') and '/' not in args.attempt and Path('/mnt/bioIce1').is_mount()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        os.nice(10 - os.getpriority(os.PRIO_PROCESS, 0))
    a = STORE / args.attempt
    if args.main_only:
        assert a.is_dir() and not (a / 'STARTED.json').exists()
    else:
        a.mkdir(parents=True, exist_ok=False)
    try:
        if not args.main_only:
            (a / 'inputs').mkdir()
            for n in SOURCES:
                (a / 'inputs' / n).write_bytes((ROOT / n).read_bytes())
            paths = [ROOT / n for n in SOURCES + REFERENCES]
            for directory, files in [(BASELINE, ('GRAPHS.json', 'MIXTURES.json', 'MANIFEST.json', 'READBACK.json')),
                                     (LEARNING, ('EVAL_GRAPHS.json', 'EVAL_MIXTURES.json', 'RESULTS.json', 'MANIFEST.json', 'READBACK.json'))]:
                audit, manifest = read(directory / 'READBACK.json'), read(directory / 'MANIFEST.json')
                assert audit['passed'] and audit['manifest_sha256'] == sha(directory / 'MANIFEST.json')
                for n in files:
                    if n in manifest['outputs']:
                        assert sha(directory / n) == manifest['outputs'][n], n
                paths.extend(directory / n for n in files)
            save(a / 'FREEZE.json', dict(created=utc(), inputs={str(p): sha(p) for p in paths},
                snapshots={n: sha(a / 'inputs' / n) for n in SOURCES}, python=platform.python_version(),
                profiles=core.PROFILES, heldout_profiles=core.HELDOUT, mus=core.MUS, budget=core.K))
            log(a, 'QUALIFICATION_START')
            start = time.monotonic()
            q, fixtures = qualify()
            q['seconds'] = time.monotonic() - start
            save(a / 'QUALIFICATION.json', q)
            save(a / 'FIXTURES.json', fixtures)
            log(a, 'QUALIFICATION_PASS')
            start = time.monotonic()
            model = core.Model(7)
            for frozen in (False, True):
                oracle = core.Oracle(model, 4, frozen)
                oracle.root()
                oracle.graph()
            oracle_seconds = time.monotonic() - start
            model.step.cache_clear()
            start = time.monotonic()
            model = core.Model(5)
            select_schedules(model)
            schedule_seconds = time.monotonic() - start
            model.step.cache_clear()
            forecast = 240 + 4*6*3**3*(11/8)*oracle_seconds + 4*(1024/32)*(11/6)*schedule_seconds
            save(a / 'BENCHMARK.json', dict(oracle_T=7, oracle_mu=4, oracle_seconds=oracle_seconds, schedule_T=5,
                schedule_count=32, schedule_seconds=schedule_seconds, forecast_seconds=forecast, timing_only=True))
            log(a, 'BENCHMARK_COMPLETE')
            if forecast > 7200:
                log(a, 'FEASIBILITY_CEILING_EXCEEDED')
                return
            if forecast > 600:
                print('DETACHED_MAIN_REQUIRED', flush=True)
                return
        run(a, args.detached)
    except Exception as error:
        name = 'READBACK_FAILURE.json' if (a / 'MANIFEST.json').exists() else 'FAILURE.json'
        if not (a / name).exists():
            save(a / name, dict(utc=utc(), error=repr(error)))
        raise


if __name__ == '__main__':
    main()
