"""Frozen two-sided durability contrast and eight directional route controls."""
from pathlib import Path
import numpy as np
from h008 import engine as e
from h007.inference import mean_pairs


def estimator(n, config):
    index = e.model.m.rng(config['analysis_seed'], 'H008 whole-block bootstrap').integers(
        0, max(n, 1), (config['bootstrap_draws'], n))

    def estimate(values, adjusted=False):
        result = dict(mean=None, low=None, high=None, equivalence_low=None,
                      equivalence_high=None, primary_low=None, primary_high=None, directional_lower=None)
        if not n:
            return result
        values = np.asarray(values)
        if values.shape != (n,):
            raise ValueError('Exactly one value per nonempty base network required')
        result['mean'] = float(values.mean())
        if n > 1:
            draws = values[index].mean(axis=1)
            for name, q in [('low', .025), ('high', .975), ('equivalence_low', .0125), ('equivalence_high', .9875)]:
                result[name] = float(np.quantile(draws, q))
            if adjusted:
                result.update(primary_low=float(np.quantile(draws, .05/18)),
                              primary_high=float(np.quantile(draws, 1-.05/18)),
                              directional_lower=float(np.quantile(draws, .05/9)))
        return result
    return estimate


def current_decision(current, outputs, counts, config):
    current = np.asarray(current).reshape(-1, 2)
    outputs = np.asarray(outputs).reshape(-1, 2, 4)
    estimate = estimator(len(current), config)
    gates = dict(at_least_64_matches=sum(counts) >= 64, at_least_16_networks=len(current) >= 16)
    means = {v: estimate(current[:, i]) for i, v in enumerate(e.VARIANTS)}
    for name, stat in means.items():
        gates[name+'_success_at_least_95pct'] = stat['mean'] is not None and stat['mean'] >= .95
    differences = dict(success=estimate(current[:, 1]-current[:, 0]))
    differences.update({f'output_{k}': estimate(outputs[:, 1, k]-outputs[:, 0, k]) for k in range(4)})
    for name, stat in differences.items():
        gates[name+'_equivalent_within_1pp'] = (stat['equivalence_low'] is not None and
             stat['equivalence_low'] >= -.01 and stat['equivalence_high'] <= .01)
    return dict(passed=all(gates.values()), gates=gates, current_success=means, differences=differences,
                matches=int(sum(counts)), nonempty_blocks=len(current))


def present_summary(out, config):
    current, outputs, counts, rows = [], [], [], []
    for seed in config['seeds']:
        with np.load(Path(out)/f'present_{seed}.npz') as raw:
            eligible = raw['eligible']
            n = int(eligible.sum())
            counts.append(n)
            row = dict(seed=seed, matched=n, eligible=eligible.tolist())
            if n:
                c = mean_pairs(raw['validation_success'].mean(axis=0), eligible)
                s = raw['validation_signals'].mean(axis=0)[:, eligible].mean(axis=1)
                current.append(c)
                outputs.append(s)
                row.update(current_success=c.tolist(), current_outputs=s.tolist(),
                           record_norm=mean_pairs(raw['record_norm'], eligible).tolist(),
                           effective_total_norm=mean_pairs(raw['effective_total_norm'], eligible).tolist())
            rows.append(row)
    decision = current_decision(current, outputs, counts, config)
    decision.update(dose=e.DOSE, blocks=rows)
    return decision


def future_decision(future, current_passed, config, audit_passed):
    future = np.asarray(future).reshape(-1, len(e.CHECKPOINTS), 2, len(e.ARMS))
    estimate = estimator(len(future), config)
    terminal = future[:, -1]
    own = e.ARMS.index('renewal')
    primary = estimate(terminal[:, 1, own]-terminal[:, 0, own], True)
    gates = dict(current_passed=bool(current_passed), integrity_passed=bool(audit_passed))
    gates['absolute_terminal_difference_at_least_10pp'] = primary['mean'] is not None and abs(primary['mean']) >= .10
    gates['adjusted_primary_interval_excludes_zero'] = (primary['primary_low'] is not None and
         (primary['primary_low'] > 0 or primary['primary_high'] < 0))
    contrasts = {}
    for v, variant in enumerate(e.VARIANTS):
        for control in ('foreign', 'read_off', 'write_off', 'damaged_copy'):
            name = variant+'_renewal_minus_'+control
            stat = estimate(terminal[:, v, own]-terminal[:, v, e.ARMS.index(control)], True)
            contrasts[name] = stat
            gates[name+'_at_least_15pp'] = stat['mean'] is not None and stat['mean'] >= .15
            gates[name+'_positive_adjusted_lower'] = stat['directional_lower'] is not None and stat['directional_lower'] > 0
    return dict(qualified=all(gates.values()) if config['mode'] == 'development' else None, gates=gates,
                primary_contrast=primary, primary_definition='hidden_swap minus unchanged renewal at generation 16',
                primary_direction=('hidden_swap_higher' if primary['mean'] > 0 else 'unchanged_higher' if primary['mean'] < 0 else 'equal') if primary['mean'] is not None else None,
                route_contrasts=contrasts, family_size=9,
                terminal={v: {a: estimate(terminal[:, i, j]) for j, a in enumerate(e.ARMS)}
                          for i, v in enumerate(e.VARIANTS)}), estimate
