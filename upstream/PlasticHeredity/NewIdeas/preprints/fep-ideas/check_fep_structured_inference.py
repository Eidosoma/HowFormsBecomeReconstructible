#!/usr/bin/env python3
"""Qualification on separate small fixtures only; never runs a main fixture."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np
from fep_structured_inference import (
    Budget, Inference, ResourceStop, WORK_LEVELS, bits, chain_exact, decision,
    enumerate_exact, exact_elimination, full_q, model, objective,
)
from run_fep_structured_inference import (
    HERE, SOURCE_NAMES, execute_job, gate, identity, prepare, save, seal,
    supervise, validate_destination, verify_freeze,
)

COUNTS = Counter()
RESIDUALS = {}


def check(condition, label):
    COUNTS[label] += 1
    if not condition:
        raise AssertionError(label)


def close(a, b, label, tol=1e-10):
    residual = float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), residual)
    check(math.isfinite(residual) and residual <= tol, label)


def independent_bayes(f0, f1):
    lo, hi = 0., min(1., max(0., (.1-f0)/(f1-f0)))
    # Direct constrained derivative solve, independent of the sigmoid implementation.
    for _ in range(64):
        mid = (lo+hi)/2
        if mid == 0:
            return 0.
        derivative = math.log(mid)-math.log1p(-mid)-4*(.15-.5*(f1-f0))
        if derivative < 0:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def snapshot_checks(m, inf, snap, exact):
    q = full_q(inf)
    close(q.sum(), 1., 'joint Q normalization')
    kl = float(np.sum(q*(np.log(q)-np.log(exact['joint']))))
    tol = 1e-9*max(1., abs(snap['F']), abs(exact['log_z']), abs(kl))
    close(snap['F'], kl-exact['log_z'], 'direct joint VFE identity', tol)
    check(kl >= -tol, 'nonnegative exact KL')
    states = bits(m.n)
    q_flat = q.ravel()
    for e, (i, j) in enumerate(m.edges):
        covariance = snap['pairs'][e, 1, 1]-snap['nodes'][i, 1]*snap['nodes'][j, 1]
        for reverse in (False, True):
            src, dst = (j, i) if reverse else (i, j)
            t_src = m.h+(.1-m.h)*states[:, src]
            t_dst = m.h+(.1-m.h)*states[:, dst]
            f0 = float(q_flat @ t_dst)
            f1 = float(q_flat @ (t_src+t_dst-t_src*t_dst))
            entry = snap['decisions'][2*e+int(reverse)]['chosen']
            product = snap['product_decisions'][2*e+int(reverse)]['chosen']
            close(entry['f0'], f0, 'direct joint economy risk')
            close(entry['f1'], f1, 'direct joint precision risk')
            close(entry['r'], independent_bayes(f0, f1), 'same-Q independent Bayesian optimum')
            check(f0 <= .1+1e-10 and f1 > f0, 'economy feasible and precision increment positive')
            check(entry['risk'] <= .1+1e-10, 'Q-predicted policy feasible')
            close(product['f0'], entry['f0'], 'productization preserves economy risk')
            close(product['f1']-entry['f1'], (.1-m.h)**2*covariance,
                  'productization covariance identity')
            if inf.owner[i] != inf.owner[j]:
                close(product['f1'], entry['f1'], 'cross-block prediction unchanged')
            hi = min(1., max(0., (.1-f0)/(f1-f0)))
            for r in np.linspace(0., hi, 17):
                check(objective(float(r), f0, f1)['J'] >= entry['J']-1e-10,
                      'declared optimum beats feasible grid controls')
    close(snap['nodes'].sum(axis=1), 1., 'node normalization')
    close(snap['pairs'].sum(axis=(1, 2)), 1., 'pair normalization')
    for e, (i, j) in enumerate(m.edges):
        close(snap['pairs'][e].sum(axis=1), snap['nodes'][i], 'pair first marginal')
        close(snap['pairs'][e].sum(axis=0), snap['nodes'][j], 'pair second marginal')
    for b in inf.block:
        close(inf.odds_residual(b), 0., 'block conditional odds invariant')


def physical_checks(m, exact):
    logp = np.log(exact['joint'])
    for (i, j), psi in zip(m.edges, m.psi):
        axes = [i, j]+[v for v in range(m.n) if v not in (i, j)]
        p = logp.transpose(axes).reshape(2, 2, -1)
        physical = np.log(psi)
        log_odds = physical[0, 0]+physical[1, 1]-physical[0, 1]-physical[1, 0]
        close(p[0, 0]+p[1, 1]-p[0, 1]-p[1, 0], log_odds,
              'exact physical conditional odds')
    if m.record == 'success':
        for e, (i, j) in enumerate(m.edges):
            close(exact['pairs'][e], np.outer(exact['nodes'][i], exact['nodes'][j]),
                  'success-only posterior factorizes')
    if m.rows == 1 and m.cols == 2 and m.record == 'fail':
        h = m.h
        weights = np.array([[h*(2-h), .1+h-.1*h], [.1+h-.1*h, .19]])
        p = weights/weights.sum()
        close(exact['pairs'][0], p, 'original two-cause posterior')
        reference = decision(p, h)
        if h == 1e-6:
            close(reference['r'], .3690083861465186121, 'saved rare exact allowance')
        f0 = float(np.sum(p*np.array([[h, .1], [h, .1]])))
        f1 = float(np.sum(p*weights))
        close(reference['f0'], f0, 'original physical economy table')
        close(reference['f1'], f1, 'original physical precision table')


def fixture_checks(m):
    exact = enumerate_exact(m)
    eliminated = exact_elimination(m)
    close(eliminated['log_z'], exact['log_z'], 'elimination evidence')
    for key in ('nodes', 'pairs'):
        close(eliminated[key], exact[key], 'elimination '+key)
    check(eliminated['metadata']['compiled_success_edges'] == m.observations.count(0),
          'success factor compilation count')
    if m.rows == 1:
        chain = chain_exact(m)
        for key in ('log_z', 'nodes', 'pairs'):
            close(chain[key], exact[key], 'independent chain '+key)
    physical_checks(m, exact)
    trajectories = []
    for family in ('mf', 'block'):
        for order in ('forward', 'reverse'):
            inf = Inference(m, family, order)
            snapshot_checks(m, inf, inf.initial, exact)
            if len(inf.block) == 1:
                close(full_q(inf), exact['joint'], 'one-block exact initialization')
            before = inf.free_energy()
            event = inf.update()
            close(inf.free_energy()-before, event['delta_F'], 'local versus full coordinate F change')
            check(event['block'] == (0 if order == 'forward' else len(inf.block)-1),
                  'specified first update order')
            snapshots = []
            previous = inf.initial['F']
            for level in WORK_LEVELS:
                snap = inf.advance(level*len(m.edges))
                snapshot_checks(m, inf, snap, exact)
                check(snap['F'] <= previous+1e-9, 'checkpoint F nonincrease')
                check(snap['work'] <= snap['budget'] < snap['work']+inf.block[snap['next_block']]['cost'],
                      'checkpoint uses all whole updates within budget')
                previous = snap['F']
                snapshots.append(snap)
            trajectories.append({'family': family, 'order': order, 'initial': inf.initial,
                                 'snapshots': snapshots, 'sweeps': inf.sweeps,
                                 'offending_updates': inf.offending_updates})
    return {'model': m.description(), 'exact': {k: v for k, v in exact.items() if k != 'joint'},
            'elimination_metadata': eliminated['metadata'], 'trajectories': trajectories}


def mechanical_checks(output):
    probe = output/'FREEZE_PROBE.txt'
    probe.write_text('original\n')
    frozen = {'status': 'qualified_frozen', 'inputs': [identity(probe)]}
    check(verify_freeze(frozen) == frozen['inputs'], 'unchanged package accepted')
    for changed in (False, True):
        candidate = copy.deepcopy(frozen)
        if changed:
            probe.write_text('changed\n')
        else:
            candidate['status'] = 'unqualified'
        try:
            verify_freeze(candidate)
        except ValueError:
            check(True, 'changed or unqualified package rejected')
        else:
            check(False, 'changed or unqualified package rejected')
    probe.write_text('original\n')
    m = model(1, 2, 1e-6, 'fail')
    for family, initial, update in [('mf', 4, 6), ('block', 12, 12)]:
        a, b = Inference(m, family), Inference(m, family)
        check(a.initial_work == initial, 'hand-counted initialization')
        check(all(x['cost'] == update for x in a.block), 'hand-counted coordinate cost')
        for budget in (256, 1024, 4096):
            saved = a.advance(budget)
        plain = b.advance(4096)
        close(saved['nodes'], plain['nodes'], 'checkpoint resumption node equality', 0.)
        close(saved['pairs'], plain['pairs'], 'checkpoint resumption pair equality', 0.)
        check(saved['work'] == plain['work'] and saved['updates'] == plain['updates'] and
              saved['next_block'] == plain['next_block'], 'checkpoint schedule equality')
    for budget, reason in [(Budget(cpu=0.), 'cpu_limit'), (Budget(memory=1), 'memory_limit')]:
        try:
            budget.check()
        except ResourceStop as exc:
            check(str(exc) == reason, 'local resource status')
        else:
            check(False, 'local resource status')
    probes = {}
    probes['cpu'] = supervise([sys.executable, '-B', '-c', 'while True: pass'],
                               output/'probe_cpu', cpu=.1)
    probes['memory'] = supervise([sys.executable, '-B', '-c',
                                  'import time; x=bytearray(64*1024**2); time.sleep(2)'],
                                 output/'probe_memory', memory=32*1024**2)
    for key, record in probes.items():
        check(record['status'] == 'censored' and record['reason'] == key+'_limit',
              'supervisor '+key+' censor status')
    jobs = []
    for kind in ('exact', 'block'):
        job = {'rows': 2, 'cols': 3, 'h': .01, 'record': 'alternating',
               'main': False, 'kind': kind, 'order': 'forward'}
        result = execute_job(job, output/f'worker_{kind}')
        check(result['status'] == 'completed', 'supervised small '+kind+' job')
        jobs.append(result)
    # Constructed outcomes exercise the gate, never an evaluated main fixture.
    rows = []
    for f in range(8):
        for kind in ('mf', 'block'):
            for order in ('forward', 'reverse'):
                rows.append({'fixture': str(f), 'h': 1e-6 if f < 4 else .01,
                             'kind': kind, 'order': order, 'status': 'completed', 'query_count': 8,
                             'metrics': {'mean_action_error': .01 if kind == 'mf' else .005,
                                         'max_risk_excess': 0., 'nondegenerate_fraction': .5,
                                         'internal_risk_error': .001,
                                         'internal_product_error': .002}})
    check(gate(rows, 8)['passed'], 'constructed positive gate')
    check(not gate(rows[:-1], 8)['passed'], 'missing row rejects gate')
    for field, value, select in [
            ('mean_action_error', .011, 'block'), ('max_risk_excess', .001, 'block'),
            ('internal_product_error', .001, 'block'), ('nondegenerate_fraction', .1, 'mf')]:
        bad = copy.deepcopy(rows)
        for row in bad:
            if row['kind'] == select:
                row['metrics'][field] = value
        check(not gate(bad, 8)['passed'], 'constructed gate failure '+field)
    duplicate = copy.deepcopy(rows)
    duplicate[-1] = copy.deepcopy(duplicate[0])
    try:
        gate(duplicate, 8)
    except ValueError:
        check(True, 'duplicate gate records rejected')
    else:
        check(False, 'duplicate gate records rejected')
    return {'probes': probes, 'small_workers': jobs, 'constructed_gate': gate(rows, 8)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-digest', required=True)
    args = parser.parse_args()
    paths = [HERE/n for n in SOURCE_NAMES]+[
        HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(p) for p in paths]
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    if digest != args.source_digest:
        raise ValueError('pre-execution source digest mismatch')
    output = validate_destination(args.output)
    manifest = prepare(output, inputs, 'small_fixture_qualification_only')
    start = time.perf_counter()
    completed = []
    log = output/'RUN_LOG.txt'
    log.write_text('Qualification only. No main fixture evaluated. One numeric process at a time.\n')
    try:
        for shape in [(1, 2), (2, 2), (2, 3), (1, 6)]:
            for h in (1e-6, .01):
                for record in ('fail', 'success', 'alternating'):
                    fixture = f'{shape[0]}x{shape[1]}_h{h:g}_{record}'
                    result = fixture_checks(model(*shape, h, record))
                    save(output/(fixture+'.json'), result)
                    completed.append(fixture)
                    with log.open('a') as stream:
                        stream.write(f'{fixture}: passed; assertions={sum(COUNTS.values())}\n')
        mechanical = mechanical_checks(output)
        save(output/'MECHANICAL.json', mechanical)
        result = {'status': 'passed', 'fixture_count': len(completed),
                  'trajectory_count': 4*len(completed), 'checkpoint_count': 12*len(completed),
                  'assertion_count': sum(COUNTS.values()), 'assertions_by_label': dict(COUNTS),
                  'max_residuals': RESIDUALS, 'fixtures': completed, 'source_digest': digest,
                  'python': platform.python_version(), 'numpy': np.__version__,
                  'elapsed_seconds': time.perf_counter()-start, 'main_fixtures_evaluated': 0}
        save(output/'RESULTS.json', result)
        with log.open('a') as stream:
            stream.write(f"Passed {result['assertion_count']} checks in {result['elapsed_seconds']:.6f} s.\n")
        seal(output, manifest, 'passed')
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ('assertions_by_label', 'max_residuals', 'fixtures')}))
    except Exception:
        failure = traceback.format_exc()
        with log.open('a') as stream:
            stream.write(failure)
        save(output/'PARTIAL_RESULTS.json', {'completed': completed, 'counts': dict(COUNTS),
                                           'max_residuals': RESIDUALS, 'failure': failure})
        seal(output, manifest, 'failed')
        raise


if __name__ == '__main__':
    main()
