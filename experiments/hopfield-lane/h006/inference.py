"""Fixed current equivalence gates and conditional whole-network inference."""
from pathlib import Path
import numpy as np
from h006 import engine as e

PAIRS = ((0, 1), (0, 2), (2, 1))


def estimator(n, config, stage):
    index = e.e.m.rng(config['analysis_seed'], 'H006 whole-block bootstrap', stage).integers(
        0, max(n, 1), (config['bootstrap_draws'], n))

    def estimate(values, directional=None):
        result = dict(mean=None, low=None, high=None, equivalence_low=None,
                      equivalence_high=None, directional_lower=None)
        if n == 0:
            return result
        values = np.asarray(values)
        if values.shape != (n,):
            raise ValueError('One value per independent nonempty base network required')
        result['mean'] = float(values.mean())
        if n > 1:
            draws = values[index].mean(axis=1)
            quantiles = np.quantile(draws, [.025, .975, .05, .95])
            for name, value in zip(('low', 'high', 'equivalence_low', 'equivalence_high'), quantiles):
                result[name] = float(value)
            if directional is not None:
                result['directional_lower'] = float(np.quantile(draws, directional))
        return result
    return estimate


def current_decision(current, outputs, counts, config, stage):
    current = np.asarray(current).reshape(-1, 3)
    outputs = np.asarray(outputs).reshape(-1, 3, 4)
    estimate = estimator(len(current), config, stage)
    minimum_blocks = 6 if stage == 'selection' else 12
    gates = dict(at_least_64_matches=sum(counts) >= 64,
                 enough_nonempty_blocks=len(current) >= minimum_blocks)
    means = {v: estimate(current[:, i]) for i, v in enumerate(e.VARIANTS)}
    for v, stat in means.items():
        gates[v + '_current_success_at_least_95pct'] = stat['mean'] is not None and stat['mean'] >= .95
    differences = {}
    for a, b in PAIRS:
        name = e.VARIANTS[a] + '_minus_' + e.VARIANTS[b]
        differences[name] = dict(success=estimate(current[:, a] - current[:, b]))
        differences[name].update({f'output_{k}': estimate(outputs[:, a, k] - outputs[:, b, k])
                                  for k in range(4)})
        for observer, stat in differences[name].items():
            gates[name + '_' + observer + '_equivalent_within_1pp'] = (
                stat['equivalence_low'] is not None and
                stat['equivalence_low'] >= -.01 and stat['equivalence_high'] <= .01)
    return dict(passed=all(gates.values()), gates=gates, current_success=means,
                differences=differences, matches=int(sum(counts)), nonempty_blocks=len(current))


def mean_pairs(values, eligible):
    values = np.asarray(values)
    return values.reshape(*values.shape[:-2], 16)[..., eligible.ravel()].mean(axis=-1)


def present_summary(out, seeds, doses, stage, config):
    decisions = []
    for d, dose in enumerate(doses):
        counts, current, outputs, rows = [], [], [], []
        for seed in seeds:
            with np.load(Path(out) / f'{stage}_{seed}.npz') as raw:
                eligible = raw['eligible'][d]
                n = int(eligible.sum())
                counts.append(n)
                row = dict(seed=seed, matched=n, feasible=int(raw['feasible'].sum()), eligible=eligible.tolist())
                if n:
                    c = mean_pairs(raw['validation_success'][:, d].mean(axis=0), eligible)
                    s = raw['validation_signals'][:, d].mean(axis=0)[:, eligible].mean(axis=1)
                    current.append(c)
                    outputs.append(s)
                    row.update(current_success=c.tolist(), current_outputs=s.tolist(),
                               cue_link=mean_pairs(raw['cue_link'][d], eligible).tolist(),
                               record_norm=mean_pairs(raw['record_norm'][d], eligible).tolist(),
                               effective_total_norm=mean_pairs(raw['effective_total_norm'][d], eligible).tolist())
                rows.append(row)
        decision = current_decision(current, outputs, counts, config, stage)
        decision.update(dose=int(dose), blocks=rows)
        decisions.append(decision)
    return decisions


def select_dose(decisions):
    passing = [row['dose'] for row in decisions if row['passed']]
    return max(passing) if passing else None


def future_decision(future, current_passed, config, audit_passed):
    future = np.asarray(future).reshape(-1, 4, 3, len(e.ARMS))
    estimate = estimator(len(future), config, 'assay')
    own = e.ARMS.index('renewal')
    contrasts = {
        'unchanged_minus_output_flips': estimate(future[:, -1, 0, own] - future[:, -1, 1, own], .05/6),
        'hidden_flips_minus_output_flips': estimate(future[:, -1, 2, own] - future[:, -1, 1, own], .05/6)}
    for control in ('foreign', 'read_off', 'write_off', 'damaged_copy'):
        contrasts['unchanged_minus_' + control] = estimate(
            future[:, -1, 0, own] - future[:, -1, 0, e.ARMS.index(control)], .05/6)
    gates = dict(current_passed=bool(current_passed), integrity_passed=bool(audit_passed))
    for name, stat in contrasts.items():
        minimum = .10 if name.endswith('output_flips') else .15
        gates[name + '_minimum_effect'] = stat['mean'] is not None and stat['mean'] >= minimum
        gates[name + '_positive_adjusted_lower'] = stat['directional_lower'] is not None and stat['directional_lower'] > 0
    return dict(qualified=all(gates.values()) if config['mode'] == 'development' else None,
                gates=gates, primary_contrasts=contrasts, directional_family_size=6,
                terminal={v: {a: estimate(future[:, -1, i, j]) for j, a in enumerate(e.ARMS)}
                          for i, v in enumerate(e.VARIANTS)}), estimate
