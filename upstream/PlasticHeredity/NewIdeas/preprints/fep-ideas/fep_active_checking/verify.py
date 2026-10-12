"""One exact study, with a durable run log and source/output identities."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import fsum
from pathlib import Path
from time import perf_counter
import argparse
import io
import json
import os
import platform
import traceback
import unittest

from .exact import (ALPHAS, CLOSED, EXTENDED, MODEL_TRUTHS, TARGETS, TRUTHS,
                    Engine, bayesian_reference, evaluate, information_reference,
                    physical_paths, serialize_policy, world_information_reference)

ROOT = Path(__file__).resolve().parents[1]
MOUNT = Path('/mnt/bioIce1')
DATA_ROOT = MOUNT/'fep-ideas'
DEFAULT_OUTPUT = DATA_ROOT/'formal-checks/fep-active-checking-v5'
INPUTS = ('FEP_ACTIVE_CHECKING_V5.md', 'fep_active_checking/__init__.py',
          'fep_active_checking/exact.py', 'fep_active_checking/verify.py',
          'tests/test_fep_active_checking.py', 'fep_model_learning/__init__.py',
          'fep_model_learning/exact.py', 'fep_model_checking/__init__.py', 'fep_model_checking/exact.py')
LENGTHS, COSTS, AUDIT_COSTS, BETAS = (2, 3, 4), (.05, .2), (.02, .1, .3), (1, 4, 16)
PRIORS = {'closed': CLOSED, 'expanded': EXTENDED}
TOL = 1e-10


def checked_destination(requested):
    if not os.path.ismount(MOUNT):
        raise RuntimeError('Data drive is not mounted; no workspace fallback')
    path = Path(requested).resolve()
    if DATA_ROOT.resolve() != DATA_ROOT or path == DATA_ROOT or not path.is_relative_to(DATA_ROOT):
        raise ValueError('Output must stay inside /mnt/bioIce1/fep-ideas')
    if path.exists():
        raise FileExistsError('Preserve existing attempts; choose a fresh output directory')
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    if parent.stat().st_dev != MOUNT.stat().st_dev:
        raise ValueError('Output is not on the specified data filesystem')
    return path


def hashes():
    return {name: sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS}


def qualify():
    stream = io.StringIO()
    start = perf_counter()
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_fep_active_checking.py')
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {'passed': result.wasSuccessful(), 'tests': result.testsRun,
            'elapsed_seconds': perf_counter()-start, 'log': stream.getvalue()}


def block(prior_name, horizon):
    """Reuse one small trajectory model across the predeclared prices."""
    start = perf_counter()
    prior = PRIORS[prior_name]
    engine = Engine(prior, horizon)
    physical = {t.name: physical_paths(t, horizon) for t in TRUTHS}
    oracle_engines = {t.name: Engine((1,), horizon, models=(t,)) for t in TRUTHS}
    baselines = {name: engine.baseline(name) for name in ('no_measurements', 'one_audit_memory', 'audit_memory')}
    rows, policies, maxima = [], [], {}

    def check(name, a, b):
        residual = abs(a-b)
        maxima[name] = max(maxima.get(name, 0), residual)
        if residual > TOL:
            raise AssertionError(f'{prior_name}/{horizon}/{name}: {a} != {b}')

    for cost, audit_cost in product(COSTS, AUDIT_COSTS):
        reference = bayesian_reference(prior, horizon, cost, audit_cost)
        fixed, fixed_node = engine.best_fixed(cost, audit_cost)
        oracle_values = {name: e.solve(1, cost, audit_cost, 'none').utility for name, e in oracle_engines.items()}
        weighted_oracle = fsum(p*oracle_values[t.name] for p, t in zip(prior, MODEL_TRUTHS))
        check('fixed_schedule_bound', max(0, fixed['utility']-reference), 0)
        check('extra_label_oracle_bound', max(0, reference-weighted_oracle), 0)
        control_nodes = baselines | {'best_fixed_schedule': fixed_node}
        controls = {name: {'prior_score': evaluate(engine.prior_paths(), node, cost, audit_cost, engine),
                           'truth_scores': {t.name: evaluate(physical[t.name], node, cost, audit_cost, engine) for t in TRUTHS}}
                    for name, node in control_nodes.items()}
        for beta in BETAS:
            controllers = {}
            setting_id = f'{prior_name}-h{horizon}-c{cost}-d{audit_cost}-b{beta}'
            for target in TARGETS:
                solution = engine.solve(beta, cost, audit_cost, target)
                scored = evaluate(engine.prior_paths(), solution.node, cost, audit_cost, engine)
                info = information_reference(engine, solution.node)
                check('physical_utility', scored['utility'], solution.utility)
                check('conditional_information', solution.information, info[target])
                check('bayesian_task_bound', max(0, solution.utility-reference), 0)
                if target == 'none':
                    check('independent_bayesian_reference', solution.utility, reference)
                    check('no_bayesian_terminal_audit', scored['audits_by_round'][-1], 0)
                if target == 'family' and prior_name == 'closed':
                    check('closed_family_information', solution.information, 0)
                    check('closed_family_bayesian_equivalence', solution.utility, reference)
                # Joint world enumeration once per target/block checks the coordinate reduction.
                if (cost, audit_cost, beta) == (.05, .1, 4):
                    world = world_information_reference(engine, solution.node)
                    for key in world:
                        check('world_information_'+key, world[key], info[key])
                truth_scores = {}
                for t in TRUTHS:
                    result = evaluate(physical[t.name], solution.node, cost, audit_cost, engine)
                    check('truth_oracle_bound', max(0, result['utility']-oracle_values[t.name]), 0)
                    check('family_ratio_ceiling', max(0, result['maximum_family_ratio']-2**(horizon-1)), 0)
                    if t in MODEL_TRUTHS[:3]:
                        for alpha in ALPHAS:
                            check('individual_null_alarm_bound', max(0, result['alarm_probability'][str(alpha)]-alpha), 0)
                    truth_scores[t.name] = result
                check('conditional_true_class_average', scored['utility'],
                      fsum(p*truth_scores[t.name]['utility'] for p, t in zip(prior, MODEL_TRUTHS)))
                controllers[target] = {'prior_score': scored, 'information': info,
                                       'prior_task_regret': max(0, reference-scored['utility']),
                                       'truth_scores': truth_scores}
                policies.append({'setting': setting_id, 'target': target, 'policy': serialize_policy(solution.node)})
            rows.append({'setting': setting_id, 'prior': prior_name, 'horizon': horizon, 'cost': cost,
                         'audit_cost': audit_cost, 'beta': beta, 'controllers': controllers,
                         'independent_bayesian_utility': reference, 'fixed_schedules': fixed,
                         'controls': controls, 'extra_truth_label_oracle_utility': oracle_values})
    return {'prior': prior_name, 'horizon': horizon, 'seconds': perf_counter()-start,
            'rows': rows, 'policies': policies, 'max_abs_errors': maxima}


def report(data):
    rows = data['rows']
    example = next(r for r in rows if r['setting'] == 'expanded-h4-c0.05-d0.1-b4')
    lines = ['# FEP active checking v5: exact record', '',
             'Evidence acquisition is chosen and paid throughout the episode. Route probes precede a report; audits reveal success only after that report. All actual successes and both observation costs enter the task score.', '',
             'The declared EFE extension prefers actual task success even when it is not observed. It uses expected preference cost minus information gain; the previous observed-feedback risk identity is not assumed.', '',
             '## Four-round worked case', '',
             'Expanded prior (0.3,0.3,0.3,0.1), probe cost 0.05, audit cost 0.1, beta=4. Scores are prior-weighted exact expectations, not sampled results.', '',
             '| Objective | Total utility | Correct reports | Probes | Audits | Final-round audits |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for target, row in example['controllers'].items():
        s = row['prior_score']
        lines.append(f"| {target} | {s['utility']:.6f} | {s['expected_correct']:.6f} | {s['expected_probes']:.6f} | {s['expected_audits']:.6f} | {s['audits_by_round'][-1]:.6f} |")
    lines += ['', '| Control | Total utility |', '| --- | ---: |']
    for name, control in example['controls'].items():
        lines.append(f"| {name} | {control['prior_score']['utility']:.6f} |")
    lines += ['', 'Bayesian planning includes the future value of purchased evidence. Its last audit probability is zero throughout the grid. FEP objectives can buy information after the final answer; that information has no remaining task use. With paid optional feedback, task-state EFE need not share the Bayesian policy ordering established under compulsory free feedback in earlier models.', '',
              'The family-target objective explicitly values distinguishing P from the original family when P has positive prior weight. With the closed prior, that target is constant and its task value equals Bayesian utility. The added alternative and its prior remain supplied.', '',
              '## Adaptive adequacy readout', '',
              'History likelihoods include the selected probes and audits. The P likelihood divided by the largest individual S/V/C likelihood is checked under each null. A last-round alarm is recorded separately from an alarm that preceded a later report. With at most four rounds the statistic cannot exceed eight; a 0.05 alarm is impossible even with full observation. Useful evidence can be acquired before that standard of rejection is reachable.', '',
              'The unannounced route break shares its history and final pre-report observation distribution with a stable route. A post-report audit cannot undo its last error. Alarm statistics test the specified P alternative and do not cover arbitrary failures.', '',
              '## Verification and resources', '',
              f"Passed {data['qualification']['tests']} qualification tests, {len(rows)} settings and {len(rows)*len(TARGETS)} objective solutions. There are {len(rows)*len(TARGETS)*len(TRUTHS)} conditional physical-mechanism evaluations, 36 independent Bayesian reference problems and 4,032 unique fixed-schedule scores.",
              f"Maximum identity residual: {max(data['max_abs_errors'].values()):.6g}. Calculation plus qualification elapsed time: {data['elapsed_seconds']:.3f} seconds; worker limit: {data['workers']}.", '',
              'Checks cover hidden-feedback masking, paid acquisition, independent physical utility, complete joint world information, Bayesian reference values, v3 reduction under compulsory free audits, per-null adaptive alarm calibration, finite information bounds and simple memory controls. Costs, all truth panels, policy trees and negative findings are retained.', '',
              'This is one exact finite-model study, not biological evidence, arbitrary model discovery, a general FEP verdict or a new sampled campaign.', '',
              '## Record and reproduction', '',
              f"Output: `{data['output_directory']}`. RUN.json records the specification/source hashes before calculation. RUN_LOG.txt and QUALIFICATION.txt record execution and tests. RESULTS.json and POLICIES.json retain outcomes and choices. MANIFEST.json seals the completed record.", '',
              '```bash',
              'python -B -m fep_active_checking.verify --workers 4 --output /mnt/bioIce1/fep-ideas/formal-checks/fep-active-checking-v5-recheck',
              '```', '',
              'Use a fresh directory on the mounted drive. Existing attempts are never overwritten, including failed attempts. No further study is launched by this record.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=4)
    args = parser.parse_args()
    destination = checked_destination(args.output)
    inputs = hashes()
    destination.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    receipt = {'kind': 'exact finite-model calculation, no sampled cohort',
               'created_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
               'workers': args.workers, 'source_directory': str(ROOT), 'output_directory': str(destination),
               'inputs': inputs, 'grid': {'priors': PRIORS, 'horizons': LENGTHS, 'costs': COSTS,
                                        'audit_costs': AUDIT_COSTS, 'betas': BETAS},
               'preflight': 'Largest-horizon engine check: 1.096 seconds including all five objectives, independent reference and fixed schedules. Conservative foreground budget: four minutes.'}
    (destination/'RUN.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')

    def log(message):
        with (destination/'RUN_LOG.txt').open('a') as f:
            f.write(datetime.now(timezone.utc).isoformat()+' '+message+'\n')
        print(message, flush=True)

    try:
        log('START: fixed specification and source hashes recorded; no free audit history; all costs counted.')
        qualification = qualify()
        (destination/'QUALIFICATION.txt').write_text(qualification['log'])
        if not qualification['passed']:
            raise AssertionError('Qualification failed; see QUALIFICATION.txt')
        log(f"QUALIFIED: {qualification['tests']} tests in {qualification['elapsed_seconds']:.3f} seconds.")
        blocks = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(block, name, h): (name, h) for name, h in product(PRIORS, LENGTHS)}
            for future in as_completed(futures):
                result = future.result()
                blocks.append(result)
                log(f"BLOCK: {result['prior']} H={result['horizon']}, 18 settings, {result['seconds']:.3f} seconds.")
        rows = sorted((r for b in blocks for r in b['rows']), key=lambda r: r['setting'])
        policies = sorted((p for b in blocks for p in b['policies']), key=lambda p: (p['setting'], p['target']))
        maxima = {name: max(b['max_abs_errors'].get(name, 0) for b in blocks)
                  for name in {n for b in blocks for n in b['max_abs_errors']}}
        if hashes() != inputs:
            raise RuntimeError('Source changed during calculation; do not seal this attempt')
        data = receipt | {'qualification': qualification, 'rows': rows, 'max_abs_errors': maxima,
                          'elapsed_seconds': perf_counter()-started,
                          'block_times': [{k: b[k] for k in ('prior', 'horizon', 'seconds')} for b in blocks]}
        (destination/'RESULTS.json').write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n')
        (destination/'POLICIES.json').write_text(json.dumps(policies, indent=2, sort_keys=True, allow_nan=False)+'\n')
        (destination/'RESULTS.md').write_text(report(data))
        log(f"COMPLETE: {len(rows)} settings; maximum residual {max(maxima.values()):.6g}; {data['elapsed_seconds']:.3f} seconds.")
        outputs = ('RUN.json', 'RUN_LOG.txt', 'QUALIFICATION.txt', 'RESULTS.json', 'POLICIES.json', 'RESULTS.md')
        manifest = {'kind': receipt['kind'], 'created_utc': receipt['created_utc'], 'inputs': inputs,
                    'outputs': {name: sha256((destination/name).read_bytes()).hexdigest() for name in outputs}}
        (destination/'MANIFEST.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
        print(json.dumps({'passed': True, 'output': str(destination), 'tests': qualification['tests'],
                          'settings': len(rows), 'seconds': data['elapsed_seconds']}, sort_keys=True))
    except BaseException:
        log('FAILED: preserving this attempt and its diagnostics; no completion manifest written.')
        (destination/'FAILURE.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
