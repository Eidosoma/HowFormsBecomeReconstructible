"""Qualify and record the fixed model-learning calculation on the external drive."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
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
    INDEX, KERNELS, MODELS, Policy, best_fixed_schedule, entropy, evaluate,
    initial_belief, model_marginal, node_summary, normalize, path_observation,
    posterior_from_transition, round_branches, solve, trajectories,
    trajectory_bayesian_reference, transition, update, vfe,
)

MOUNT = Path('/mnt/bioIce1')
DATA_ROOT = MOUNT/'fep-ideas'
DEFAULT_OUTPUT = DATA_ROOT/'formal-checks/fep-model-learning-v3'
ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('FEP_MODEL_LEARNING_V3.md', 'fep_model_learning/__init__.py',
          'fep_model_learning/exact.py', 'fep_model_learning/verify.py',
          'tests/test_fep_model_learning.py',
          'fep_persistence/__init__.py', 'fep_persistence/exact.py')
PRIORS = ((1/3,)*3, (.8, .1, .1), (.1, .45, .45))
HORIZONS = (1, 2, 3)
COSTS = (0.0, .05, .1, .12, .125, .15, .25)
BETAS = (1.0, 4.0, 16.0)
TARGETS = ('all', 'model', 'task', 'none')
TOL = 1e-10


def checked_destination(requested: Path) -> Path:
    if not os.path.ismount(MOUNT):
        raise RuntimeError(f'Required data drive is not mounted: {MOUNT}; no local fallback')
    namespace = DATA_ROOT.resolve()
    if namespace != DATA_ROOT:
        raise ValueError('FEP data namespace must not redirect through a symlink')
    destination = requested.resolve()
    if destination == namespace or not destination.is_relative_to(namespace):
        raise ValueError(f'New data must be in a subdirectory of {DATA_ROOT}')
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite an existing record: {destination}')
    existing_parent = destination.parent
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if existing_parent.stat().st_dev != MOUNT.stat().st_dev:
        raise ValueError('Output parent is not on the specified data filesystem')
    return destination


def source_hashes():
    return {name: sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS}


def qualification_checks() -> dict:
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_fep_model_learning.py')
    stream = io.StringIO()
    started = perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError(stream.getvalue())
    return {'tests': result.testsRun, 'passed': True,
            'elapsed_seconds': perf_counter()-started, 'log': stream.getvalue()}


def physical_filter_residual(prior, horizon, node) -> float:
    """Compare every reached compact posterior with independently grouped paths."""
    worst = 0.0

    def visit(paths, q, current, stage):
        nonlocal worst
        direct = [0.0]*12
        for (m, xs, rs, aas), p in paths.items():
            direct[INDEX[m, rs[stage], aas[stage]]] += p
        worst = max(worst, *(abs(a-b) for a, b in zip(q, direct)))
        compact = round_branches(q, current.policy)
        groups = {}
        for state, p in paths.items():
            obs = path_observation(state, current.policy, stage)
            groups.setdefault(obs, {})[state] = p
        if groups.keys() != compact.keys():
            raise AssertionError('Physical and inferred observable supports disagree')
        for obs, paths_after in groups.items():
            probability = fsum(paths_after.values())
            expected_p, post = compact[obs]
            posterior_paths = {s: p/probability for s, p in paths_after.items()}
            direct_post = [0.0]*12
            for (m, xs, rs, aas), p in posterior_paths.items():
                direct_post[INDEX[m, rs[stage], aas[stage]]] += p
            worst = max(worst, abs(probability-expected_p),
                        *(abs(a-b) for a, b in zip(post, direct_post)))
            if stage+1 < horizon:
                visit(posterior_paths, transition(post), current.children[obs], stage+1)

    visit(trajectories(prior, horizon), initial_belief(prior), node, 0)
    return worst


def grid_checks() -> dict:
    maxima = {key: 0.0 for key in (
        'trajectory_mass', 'utility_vs_physical', 'information_chain', 'efe_direct',
        'risk_plus_ambiguity', 'task_information', 'bayesian_reference',
        'task_efe_utility', 'conditional_class_average', 'filter_vs_physical',
        'bayesian_upper_bound_violation', 'oracle_upper_bound_violation',
        'fixed_schedule_upper_bound_violation')}

    def check(key, a, b):
        residual = abs(a-b)
        maxima[key] = max(maxima[key], residual)
        if residual > TOL:
            raise AssertionError(f'{key}: {a} != {b}')

    def bound(key, value, ceiling):
        check(key, max(value-ceiling, 0.0), 0.0)

    @lru_cache(None)
    def reference(prior, horizon, cost):
        return trajectory_bayesian_reference(prior, horizon, cost)

    @lru_cache(None)
    def fixed(prior, horizon, cost):
        label, solution, rows = best_fixed_schedule(prior, horizon, cost)
        return {'best_schedule': label, 'best_utility': solution.utility, 'all_schedules': rows}

    @lru_cache(None)
    def oracle(horizon, cost):
        return tuple(solve(tuple(int(i == m) for i in range(3)), horizon, 1, cost, 'none').utility
                     for m in range(3))

    rows = []
    for prior, horizon, cost, beta in product(PRIORS, HORIZONS, COSTS, BETAS):
        bayes = reference(prior, horizon, cost)
        fixed_scores = fixed(prior, horizon, cost)
        oracle_by_class = oracle(horizon, cost)
        oracle_score = fsum(p*u for p, u in zip(prior, oracle_by_class))
        bound('oracle_upper_bound_violation', bayes, oracle_score)
        bound('fixed_schedule_upper_bound_violation', fixed_scores['best_utility'], bayes)
        controllers = {}
        for target in TARGETS:
            solution = solve(prior, horizon, beta, cost, target)
            scored = evaluate(prior, horizon, solution.node, beta, cost)
            check('trajectory_mass', scored['trajectory_mass'], 1)
            check('utility_vs_physical', solution.utility, scored['utility'])
            check('information_chain', solution.information,
                  0 if target == 'none' else scored['information'][target])
            check('efe_direct', scored['efe']['all'], scored['efe_direct_all'])
            check('risk_plus_ambiguity', scored['efe']['all'], scored['risk_plus_ambiguity_all'])
            check('task_information', scored['information']['task'], horizon*log(2))
            check('filter_vs_physical', physical_filter_residual(prior, horizon, solution.node), 0)
            bound('bayesian_upper_bound_violation', scored['utility'], bayes)
            by_class = {}
            for m, name in enumerate(MODELS):
                result = evaluate(tuple(int(i == m) for i in range(3)), horizon, solution.node, beta, cost)
                by_class[name] = {k: result[k] for k in ('utility', 'expected_probes', 'accuracy_by_round', 'probes_by_round')}
            check('conditional_class_average', scored['utility'],
                  fsum(prior[m]*by_class[name]['utility'] for m, name in enumerate(MODELS)))
            scored['true_class_outcomes_fixed_policy'] = by_class
            scored['bayesian_task_regret'] = max(0.0, bayes-scored['utility'])
            controllers[target] = scored
        check('bayesian_reference', controllers['none']['utility'], bayes)
        check('task_efe_utility', controllers['task']['utility'], bayes)
        rows.append({'prior': prior, 'horizon': horizon, 'cost': cost, 'beta': beta,
                     'controllers': controllers, 'bayesian_path_reference': bayes,
                     'fixed_probe_schedules': fixed_scores,
                     'extra_class_label_oracle': {'utility': oracle_score,
                        'utility_by_true_class': dict(zip(MODELS, oracle_by_class))}})
    summaries = {target: {
        'settings_below_bayesian_task_utility': sum(r['controllers'][target]['bayesian_task_regret'] > TOL for r in rows),
        'max_task_regret': max(r['controllers'][target]['bayesian_task_regret'] for r in rows),
        'settings_matching_bayesian_task_utility': sum(r['controllers'][target]['bayesian_task_regret'] <= TOL for r in rows),
    } for target in TARGETS}
    return {'settings': len(rows), 'planner_solutions': len(rows)*len(TARGETS),
            'unique_independent_bayesian_reference_problems': reference.cache_info().currsize,
            'unique_fixed_schedule_scores': sum(2**h for p, h, c in product(PRIORS, HORIZONS, COSTS)),
            'conditional_true_class_evaluations': len(rows)*len(TARGETS)*3,
            'max_abs_errors': maxima, 'objective_summary': summaries, 'rows': rows}


def worked_examples() -> dict:
    prior = PRIORS[0]
    examples = []
    for horizon, cost in ((3, .1), (3, .12), (3, .15), (2, .1)):
        controllers, trees = {}, {}
        for target in TARGETS:
            solution = solve(prior, horizon, 4, cost, target)
            controllers[target] = evaluate(prior, horizon, solution.node, 4, cost)
            trees[target] = node_summary(solution.node, initial_belief(prior), horizon)
        label, best, fixed_rows = best_fixed_schedule(prior, horizon, cost)
        examples.append({'prior': prior, 'horizon': horizon, 'cost': cost, 'beta': 4,
                         'controllers': controllers, 'policy_trees': trees,
                         'best_fixed_schedule': label, 'best_fixed_utility': best.utility,
                         'all_fixed_schedules': fixed_rows})
    if abs(examples[0]['controllers']['none']['utility']-47/30) > TOL:
        raise AssertionError('Predeclared 47/30 prediction failed')
    if abs(examples[1]['controllers']['none']['utility']-(1.5+1/3-(8/3)*.12)) > TOL:
        raise AssertionError('Predeclared cost .12 prediction failed')

    posteriors = []
    for b, v in product((0, 1), repeat=2):
        joint = tuple(prior[m]*fsum(p for bb, vv, p in KERNELS[m] if (bb, vv) == (b, v)) for m in range(3))
        posterior = posterior_from_transition(prior, b, v)
        posteriors.append({'sensor_change': b, 'route_change': v, 'probability': fsum(joint),
                           'class_posterior': posterior, 'exact_vfe': vfe(posterior, joint),
                           'negative_log_evidence': -log(fsum(joint))})
    probe = Policy(True, 0, 0)
    first = update(initial_belief(prior), probe, (0, 1))
    second = update(transition(first), probe, (1, 1))  # b=0,v=1: only volatile remains
    prediction = transition(second)
    final = {}
    for target in TARGETS:
        solution = solve(prior, 1, 4, .1, target, belief=prediction)
        final[target] = {'probe': solution.node.policy.probe, 'utility': solution.utility,
                         'information_about_selected_target': solution.information}
    return {'cases': examples, 'adjacent_transition_posteriors': posteriors,
            'known_volatile_final_decision': {'class_posterior': model_marginal(prediction),
                'beta': 4, 'cost': .1, 'controllers': final}}


def report(data) -> str:
    grid = data['verification']
    lines = ['# FEP model learning v3: exact calculation record', '',
             'Learning a supplied persistence model can improve later probe decisions. Which information the EFE objective values determines whether it also pays for information with no remaining task use.', '',
             'This is a finite mathematical model with exact enumeration, not a sampled scientific cohort or biological evidence. Model classes, likelihoods, protected posterior memory, feedback and preferences are supplied.', '',
             '## Worked cases', '',
             'Uniform prior over stable, independently changing and shared-change mechanisms; beta=4. Utility is the expected number of correct reports minus all probe costs. Probe decisions can depend on observed history.', '',
             '| Rounds | Cost | Full-state EFE | Model-target EFE | Bayesian / task EFE | Best fixed schedule |',
             '| ---: | ---: | ---: | ---: | ---: | --- |']
    for row in data['examples']['cases']:
        c = row['controllers']
        lines.append(f"| {row['horizon']} | {row['cost']:.2f} | {c['all']['utility']:.6f} | {c['model']['utility']:.6f} | {c['none']['utility']:.6f} | {row['best_fixed_schedule']} / {row['best_fixed_utility']:.6f} |")
    lines += ['', 'With three rounds and cost 0.1, the Bayesian planner buys two probes, then continues only if the route has not changed. Its utility is 47/30. The same first two probes can reveal that a stable route is ruled out; then spending on a third probe cannot improve the last answer. The best fixed schedule obtains 23/15 and never probing obtains 1.5.', '',
              'Model-target EFE matches this useful contingent policy at beta=4, cost=0.1. Full-state EFE probes all three rounds and earns less task utility because it values transient route information too. After a transition that identifies the volatile class exactly, model-target EFE and Bayes skip the final probe; full-state EFE buys it when beta*cost < log(2).', '',
              'Model-target EFE is not generally task-optimal. With only two rounds at cost 0.1 it pays to discriminate classes even though the resulting class evidence arrives after the final decision. Task-state EFE and the epistemic ablation match the Bayesian task optimum throughout this grid. The latter already includes useful future learning; it is not a greedy controller.', '',
              '## Grid verification', '',
              f"Passed {data['qualification']['tests']} qualification tests and {grid['settings']} exact settings, with {grid['planner_solutions']} planner solutions, {grid['unique_independent_bayesian_reference_problems']} independent full-path Bayesian reference problems, {grid['unique_fixed_schedule_scores']} unique fixed-schedule scores and {grid['conditional_true_class_evaluations']} conditional true-class policy evaluations.", '',
              '| Objective | Settings matching Bayesian task utility | Settings below it | Maximum task regret |',
              '| --- | ---: | ---: | ---: |']
    for target, values in grid['objective_summary'].items():
        lines.append(f"| {target} | {values['settings_matching_bayesian_task_utility']} | {values['settings_below_bayesian_task_utility']} | {values['max_task_regret']:.6f} |")
    lines += ['', 'Grid frequencies are descriptions of the predeclared parameter grid, not estimates of how common a phenomenon is in nature. The class-informed oracle has an extra label and is only an upper bound. Conditional true-class scores use the fixed mixture policy without supplying that label.', '',
              f"Maximum identity residual: {max(grid['max_abs_errors'].values()):.6g}. Total qualification and calculation time: {data['elapsed_seconds']:.3f} seconds, one Python process, no numerical libraries or worker threads.", '',
              'Every reached compact posterior was checked against grouped physical trajectories. Conditional information agrees with whole-trajectory mutual information; full-state EFE also agrees with the direct biased-joint and risk calculations. Tests verify the analytic class posteriors, value-of-information boundary, no early feedback access, passive/single-probe nonidentifiability, zero-support rejection, and reduction to the frozen v2 model when class is known.', '',
              '## Limits and next scientific question', '',
              'This learns a discrete persistent model index within a supplied closed family. It does not discover arbitrary causal structures, learn arbitrary transition rates, change preferences, repair a diagnostic route, or demonstrate heredity. The true mechanism is assumed to remain in the family and fixed across the episode. A useful next design question concerns failure of those assumptions and whether calibrated model checks detect it before misleading action. No successor campaign is launched by this record.', '',
              '## Storage and reproduction', '',
              f"Data directory: `{data['output_directory']}`. The actual mount uses a capital I in bioIce1. Source code and small research notes remain in fep-ideas; earlier sealed records are preserved.", '',
              'From the fep-ideas source directory:', '', '```bash',
              'python -B -m fep_model_learning.verify --output /mnt/bioIce1/fep-ideas/formal-checks/fep-model-learning-v3-recheck',
              '```', '',
              'The command includes qualification tests, requires the data mount, and refuses an existing output directory. MANIFEST.json contains source and output hashes. No raw calculation data are written to the workspace disk.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    destination = checked_destination(args.output)
    inputs = source_hashes()
    started = perf_counter()
    data = {'kind': 'exact finite-model verification, not a sampled scientific cohort',
            'created_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
            'output_directory': str(destination), 'source_directory': str(ROOT),
            'grid': {'priors': PRIORS, 'horizons': HORIZONS, 'costs': COSTS, 'betas': BETAS},
            'qualification': qualification_checks(), 'verification': grid_checks(),
            'examples': worked_examples()}
    data['elapsed_seconds'] = perf_counter()-started
    if inputs != source_hashes():
        raise RuntimeError('Source changed during verification; no record written')
    outputs = {'RESULTS.json': json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n',
               'RESULTS.md': report(data), 'QUALIFICATION.txt': data['qualification']['log']}
    manifest = {'kind': data['kind'], 'created_utc': data['created_utc'],
                'source_directory': str(ROOT), 'output_directory': str(destination),
                'inputs': inputs,
                'outputs': {name: sha256(value.encode('utf-8')).hexdigest() for name, value in outputs.items()}}
    # Recheck the mount immediately before the first data write.
    checked_destination(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in outputs.items():
        with (destination/name).open('x', encoding='utf-8') as f:
            f.write(content)
    with (destination/'MANIFEST.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'output': str(destination), 'passed': True,
                      'tests': data['qualification']['tests'], 'settings': data['verification']['settings'],
                      'elapsed_seconds': data['elapsed_seconds'],
                      'max_residual': max(data['verification']['max_abs_errors'].values())}, sort_keys=True))


if __name__ == '__main__':
    main()
