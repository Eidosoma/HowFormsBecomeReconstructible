"""Run the predeclared v4 exact checks; store generated records on bioIce1 only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
from itertools import product
import json
from math import fsum, log
import os
from pathlib import Path
import platform
from time import perf_counter
import unittest

from .exact import (
    CLOSED, EXTENDED, INDEX, MODEL_TRUTHS, MODELS, NULLS, POLICIES, STATES,
    TARGETS, TRUTHS, Choice, History, bayesian_reference, choose, class_joint,
    class_posterior, copy_last, crossing_length, gate, histories, history_probability,
    monitor, normalize, physical_history_joint, physical_score, posterior_evidence,
    prediction, score, terminal_distribution,
)

ROOT = Path(__file__).resolve().parents[1]
MOUNT = Path('/mnt/bioIce1')
DATA_ROOT = MOUNT/'fep-ideas'
DEFAULT_OUTPUT = DATA_ROOT/'formal-checks/fep-model-checking-v4'
LENGTHS = (1, 3, 5, 7)
ALPHAS = (.05, .125, .25)
COSTS = (.05, .1, .25)
BETAS = (1.0, 4.0, 16.0)
INPUTS = ('FEP_MODEL_CHECKING_V4.md', 'fep_model_checking/__init__.py',
          'fep_model_checking/exact.py', 'fep_model_checking/verify.py',
          'tests/test_fep_model_checking.py',
          'fep_model_learning/__init__.py', 'fep_model_learning/exact.py')
TOL = 1e-10


def checked_destination(requested):
    if not os.path.ismount(MOUNT):
        raise RuntimeError('Required /mnt/bioIce1 drive is not mounted; no workspace fallback')
    if DATA_ROOT.resolve() != DATA_ROOT:
        raise ValueError('The FEP data namespace must not redirect through a symlink')
    destination = Path(requested).resolve()
    if destination == DATA_ROOT or not destination.is_relative_to(DATA_ROOT):
        raise ValueError('New data must be inside the FEP namespace on /mnt/bioIce1')
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite existing record: {destination}')
    parent = destination.parent
    while not parent.exists():
        parent = parent.parent
    if parent.stat().st_dev != MOUNT.stat().st_dev:
        raise ValueError('Output parent is not on the specified data filesystem')
    return destination


def hashes():
    return {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS}


def qualify():
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_fep_model_checking.py')
    stream = io.StringIO()
    start = perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError(stream.getvalue())
    return {'passed': True, 'tests': result.testsRun, 'elapsed_seconds': perf_counter()-start,
            'log': stream.getvalue()}


def exact_checks():
    errors = {}

    def check(name, x, y):
        residual = abs(x-y)
        errors[name] = max(errors.get(name, 0.0), residual)
        if residual > TOL:
            raise AssertionError(f'{name}: {x} != {y}')

    evidence_rows = []
    for n in LENGTHS:
        for truth in TRUTHS:
            joint = physical_history_joint(truth, n)
            check('history_normalization', fsum(fsum(d.values()) for d in joint.values()), 1)
            for h in histories(n):
                mass = fsum(joint.get(h, {}).values())
                check('history_probability', history_probability(truth, h), mass)
                if mass:
                    expected = terminal_distribution(truth, h)
                    for ra in product((0, 1), repeat=2):
                        check('conditional_terminal_physics', expected.get(ra, 0), joint[h].get(ra, 0)/mass)
            for alpha in ALPHAS:
                alarm = fsum(fsum(d.values())*monitor(h, alpha)['alarm'] for h, d in joint.items())
                k = crossing_length(alpha)
                expected = 0.0 if n < k else (1-truth.rho)**k
                check('monitor_power_formula', alarm, expected)
                if truth in NULLS:
                    check('null_false_alarm_bound', max(alarm-alpha, 0), 0)
        for h in histories(n):
            values = {}
            for name, prior in (('closed', CLOSED), ('extended', EXTENDED)):
                values[name] = posterior_evidence(prior, h)
                q = prediction(prior, h)
                physical = [0.0]*16
                for m, truth in enumerate(MODEL_TRUTHS):
                    for (r, a), p in physical_history_joint(truth, n).get(h, {}).items():
                        physical[INDEX[m, r, a]] += prior[m]*p
                actual = normalize(physical)
                check('posterior_normalization', fsum(q), 1)
                for a, b in zip(q, actual):
                    check('prediction_vs_physical_mixture', a, b)
                check('vfe_evidence_identity', values[name]['exact_vfe'], -log(values[name]['evidence']))
                for p in POLICIES:
                    s = score(q, p, 4, .1)
                    check('direct_efe_identity', s['efe']['all'], s['efe_direct_all'])
                reference = bayesian_reference(q, .1)
                for target in ('task', 'none'):
                    selected = choose(q, 4, .1, target)
                    utility = fsum(score(q, p, 4, .1)['utility'] for p in selected.policies)/len(selected.policies)
                    check('task_efe_bayesian_equivalence', utility, reference)
            evidence_rows.append({'n': n, 'history': h.label, 'last_sensor': h.last_sensor,
                                  'beliefs': values, 'monitor_at_each_alpha': {
                                      str(a): monitor(h, a) for a in ALPHAS}})
    return {'max_abs_errors': errors, 'distinct_histories': len(evidence_rows),
            'physical_truth_length_panels': len(TRUTHS)*len(LENGTHS), 'history_evidence': evidence_rows}


def plans(h, beta, cost):
    return {f'{name}_{target}': choose(prediction(prior, h), beta, cost, target)
            for name, prior in (('closed', CLOSED), ('extended', EXTENDED)) for target in TARGETS}


def setting(n, alpha, cost, beta):
    decisions = {h: plans(h, beta, cost) for h in histories(n)}
    results = []
    for truth in TRUTHS:
        physical = physical_history_joint(truth, n)
        totals = {}
        alarm_mass = 0.0
        oracle_total = 0.0
        for h, state_weights in physical.items():
            mass = fsum(state_weights.values())
            state_distribution = {s: p/mass for s, p in state_weights.items()}
            selected = dict(decisions[h])
            selected.update({f'gated_{target}': gate(selected[f'closed_{target}'], h, alpha) for target in TARGETS})
            selected['copy_last'] = copy_last(h)
            alarm_mass += mass*monitor(h, alpha)['alarm']
            oracle_total += mass*max(physical_score(state_distribution, Choice((p,)), cost)['utility'] for p in POLICIES)
            for name, choice in selected.items():
                result = physical_score(state_distribution, choice, cost)
                aggregate = totals.setdefault(name, {k: 0.0 for k in result})
                for metric, value in result.items():
                    aggregate[metric] += mass*value
        for name, values in totals.items():
            if values['utility'] > oracle_total+TOL:
                raise AssertionError('Controller exceeded its truth-informed upper bound')
            values['regret_to_truth_informed_oracle'] = max(0.0, oracle_total-values['utility'])
            values['gain_over_copy_last'] = values['utility']-totals['copy_last']['utility']
            if name.startswith('gated_'):
                target = name.removeprefix('gated_')
                values['gain_over_closed_same_objective'] = values['utility']-totals[f'closed_{target}']['utility']
        results.append({'truth': truth.name, 'sensor_flip_rate': truth.rho,
                        'alarm_probability': alarm_mass, 'controllers': totals,
                        'extra_truth_label_oracle_utility': oracle_total})
    return {'n': n, 'alpha': alpha, 'cost': cost, 'beta': beta, 'truth_panels': results}


def grid_checks():
    rows = [setting(n, a, c, b) for n, a, c, b in product(LENGTHS, ALPHAS, COSTS, BETAS)]
    gated_summary = {}
    for target in TARGETS:
        gains = [p['controllers'][f'gated_{target}']['gain_over_closed_same_objective']
                 for r in rows for p in r['truth_panels']]
        gated_summary[target] = {'truth_settings_improved': sum(g > TOL for g in gains),
                                 'truth_settings_harmed': sum(g < -TOL for g in gains),
                                 'truth_settings_unchanged': sum(abs(g) <= TOL for g in gains),
                                 'largest_gain': max(gains), 'largest_loss': min(gains)}
    return {'settings': len(rows), 'truth_settings': len(rows)*len(TRUTHS),
            'controller_truth_scores': len(rows)*len(TRUTHS)*13,
            'gating_summary': gated_summary, 'rows': rows}


def policy_record():
    rows = []
    for n, cost, beta in product(LENGTHS, COSTS, BETAS):
        rows.append({'n': n, 'cost': cost, 'beta': beta, 'history_policies': {
            h.label: {name: c.serialized() for name, c in plans(h, beta, cost).items()}
            for h in histories(n)}})
    return {'conditioning': 'Policies condition only on the recorded history and supplied prior, never the truth panel.',
            'ties': 'Skip a tied probe; average equally over tied report maps conditional on each draw.',
            'gates': 'Apply monitor at the requested alpha; on any past crossing use copy_last without probing.',
            'rows': rows}


def report(data):
    grid = data['verification']
    example = next(r for r in grid['rows'] if (r['n'], r['alpha'], r['cost'], r['beta']) == (5, .05, .1, 4))
    lines = ['# FEP model checking v4: exact calculation record', '',
             'A concentrated posterior over a supplied family can coexist with a calibrated signal that the family misses an observed regularity. The check helps only for failures it can see, and its fallback must be compared with a cheap memory rule.', '',
             'This record fixes the acquisition history and scores one subsequent decision. It is not an optimized sensing campaign or a model-discovery result. The two common audit probes cost 2*c; total-cost-adjusted scores are retained in JSON.', '',
             '## Worked endpoint comparison', '',
             'Five observed sensor transitions, alpha=0.05, beta=4, terminal probe cost 0.1. Utility is expected terminal accuracy minus terminal probe cost. Subtract 0.2 from every entry to include the common audit probes.', '',
             '| Physical truth | Alarm probability | Closed full EFE | Gated full EFE | Closed Bayesian | Gated Bayesian | Extended Bayesian | Copy last |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for p in example['truth_panels']:
        c = p['controllers']
        lines.append(f"| {p['truth']} | {p['alarm_probability']:.6f} | {c['closed_all']['utility']:.6f} | {c['gated_all']['utility']:.6f} | {c['closed_none']['utility']:.6f} | {c['gated_none']['utility']:.6f} | {c['extended_none']['utility']:.6f} | {c['copy_last']['utility']:.6f} |")
    lines += ['', 'The monitor alarms after five initial zero sensor changes at alpha=0.05. Its false-alarm rate is exactly 1/32 under each original class, below 0.05. It detects a permanently fixed sensor with probability one once five transitions are observed. At flip rates 0.1, 0.25 and 0.75, its probability of any alarm is respectively 0.9^5, 0.75^5 and 0.25^5. An early change kills this no-reset monitor; later changes do not erase an alarm already raised.', '',
              'A first transition b=0,v=1 makes the original family certain of its volatile class. After five zero sensor changes that posterior is still certain, while the adequacy monitor has value 32 and alarms. The closed-family evidence and exact VFE are identical for an equally long history with the same first transition but a later change, although that history need not alarm. Absolute evidence and relative posterior certainty do not themselves specify the discrepancy being tested.', '',
              'The added persistent-sensor model can affect Bayesian decisions before the threshold is crossed. This comparison receives the same observations but a supplied additional likelihood and prior. Its benefit is not evidence of autonomous model discovery or an advantage unique to FEP.', '',
              'The copy-last control already performs perfectly for an unchanging sensor. Detection can improve a controller that relied on the wrong family without beating that simpler rule. Conversely, copying alone forgoes useful diagnostic probes when the route is stable and the sensor changes unpredictably. Report-map ties are averaged exactly, so an arbitrary bit-label choice cannot create apparent out-of-family accuracy.', '',
              'The unannounced future route break has exactly the same visible diagnostic-history distribution as the stable-route null. No detector using only that history can distinguish the two. Alarm rates are therefore identical, despite different later task outcomes. No general protection from unforeseeable changes is established.', '',
              '## FEP interpretation', '',
              'Four declared EFE targets are compared with identical beliefs, resources and terminal actions. Full-state EFE can pay to identify a transient route even when that information cannot improve the report. Model-target EFE can also value discrimination without a later use. Task-state EFE and the epistemic ablation agree with Bayesian task utility within each supplied family; the ordinary final feedback makes their task-information term policy-independent.', '',
              'The monitor is a likelihood-ratio check against one supplied persistence alternative, followed by a supplied action rule. The same wrapper is available to FEP and Bayesian controllers. Its statistical calibration holds under each specified null, not arbitrary worlds, model changes or detector resets.', '',
              '## Qualification and scope', '',
              f"Passed {data['qualification']['tests']} qualification tests, {grid['settings']} grid settings, {grid['truth_settings']} truth/settings panels and {grid['controller_truth_scores']} aggregate controller scores. Independent transition enumeration covers {data['exact_checks']['distinct_histories']} distinct histories across the four audit lengths.",
              f"Maximum identity residual: {max(data['exact_checks']['max_abs_errors'].values()):.6g}. Qualification and exact calculation time: {data['elapsed_seconds']:.3f} seconds on one Python process.", '',
              'Checks cover physical-history likelihoods, class-posterior calibration, terminal mapping predictions, VFE/evidence and EFE identities, individual-null false alarms, sequential stopping, power, known blind spots, report timing, label symmetry, the no-warning control and the v3 reduction. There are no sampled cohorts, significance estimates, biological claims or literature novelty claims.', '',
              '## Storage and reproduction', '',
              f"Output directory: `{data['output_directory']}`. RESULTS.json retains every aggregate panel, history evidence and monitor trace. POLICIES.json retains the exact conditional report-map mixtures. QUALIFICATION.txt and MANIFEST.json record tests and source/output identities.", '',
              'From fep-ideas, use a fresh output directory:', '', '```bash',
              'python -B -m fep_model_checking.verify --output /mnt/bioIce1/fep-ideas/formal-checks/fep-model-checking-v4-recheck',
              '```', '',
              'The drive must be mounted; existing records cannot be overwritten. Prior v1–v3 and IM records remain separate. No further experiment is launched by this record.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--benchmark', action='store_true', help='One largest-history setting in memory; no data files')
    args = parser.parse_args()
    if args.benchmark:
        start = perf_counter()
        row = setting(7, .05, .1, 4)
        elapsed = perf_counter()-start
        print(json.dumps({'kind': 'timing and qualification-scale check, no files written',
                          'seconds_for_largest_history_setting': elapsed,
                          'truth_panels': len(row['truth_panels']),
                          'conservative_full_forecast_seconds': elapsed*108*3+30}))
        return
    destination = checked_destination(args.output)
    inputs = hashes()
    started = perf_counter()
    data = {'kind': 'exact finite-model verification, not a sampled scientific cohort',
            'created_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
            'source_directory': str(ROOT), 'output_directory': str(destination),
            'grid': {'history_lengths': LENGTHS, 'alphas': ALPHAS, 'costs': COSTS, 'betas': BETAS,
                     'closed_prior': CLOSED, 'extended_prior': EXTENDED},
            'qualification': qualify(), 'exact_checks': exact_checks(), 'verification': grid_checks()}
    policies = policy_record()
    data['elapsed_seconds'] = perf_counter()-started
    if inputs != hashes():
        raise RuntimeError('Source changed during verification; no record written')
    outputs = {'RESULTS.json': json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n',
               'POLICIES.json': json.dumps(policies, indent=2, sort_keys=True, allow_nan=False)+'\n',
               'RESULTS.md': report(data), 'QUALIFICATION.txt': data['qualification']['log']}
    manifest = {'kind': data['kind'], 'created_utc': data['created_utc'],
                'source_directory': str(ROOT), 'output_directory': str(destination), 'inputs': inputs,
                'outputs': {name: sha256(value.encode()).hexdigest() for name, value in outputs.items()}}
    checked_destination(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in outputs.items():
        with (destination/name).open('x', encoding='utf-8') as f:
            f.write(content)
    with (destination/'MANIFEST.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'passed': True, 'output': str(destination), 'tests': data['qualification']['tests'],
                      'settings': data['verification']['settings'], 'elapsed_seconds': data['elapsed_seconds'],
                      'max_residual': max(data['exact_checks']['max_abs_errors'].values())}, sort_keys=True))


if __name__ == '__main__':
    main()
