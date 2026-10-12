"""Prespecified feasibility gates; no long-term durability inference."""
from pathlib import Path
import numpy as np
from h007 import engine as e


def estimator(n, config):
    index = e.e.m.rng(config['analysis_seed'], 'H007 whole-block bootstrap').integers(
        0, max(n, 1), (config['bootstrap_draws'], n))

    def estimate(values, directional=False):
        result = dict(mean=None, low=None, high=None, equivalence_low=None,
                      equivalence_high=None, directional_lower=None)
        if not n:
            return result
        values = np.asarray(values)
        if values.shape != (n,):
            raise ValueError('Exactly one observation per nonempty base network required')
        result['mean'] = float(values.mean())
        if n > 1:
            means = values[index].mean(axis=1)
            for name, q in [('low', .025), ('high', .975), ('equivalence_low', .0125), ('equivalence_high', .9875)]:
                result[name] = float(np.quantile(means, q))
            if directional:
                result['directional_lower'] = float(np.quantile(means, .05/(4*3)))
        return result
    return estimate


def mean_pairs(values, eligible):
    values = np.asarray(values)
    return values.reshape(*values.shape[:-2], 16)[..., eligible.ravel()].mean(axis=-1)


def current_decision(current, signals, counts, config):
    current = np.asarray(current).reshape(-1, 2)
    signals = np.asarray(signals).reshape(-1, 2, 4)
    estimate = estimator(len(current), config)
    gates = dict(at_least_64_matches=sum(counts) >= 64, at_least_16_networks=len(current) >= 16)
    means = {v: estimate(current[:, i]) for i, v in enumerate(e.VARIANTS)}
    for name, stat in means.items():
        gates[name+'_success_at_least_95pct'] = stat['mean'] is not None and stat['mean'] >= .95
    differences = dict(success=estimate(current[:, 1]-current[:, 0]))
    differences.update({f'output_{k}': estimate(signals[:, 1, k]-signals[:, 0, k]) for k in range(4)})
    for name, stat in differences.items():
        gates[name+'_equivalent_within_1pp'] = (stat['equivalence_low'] is not None and
             stat['equivalence_low'] >= -.01 and stat['equivalence_high'] <= .01)
    return dict(passed=all(gates.values()), gates=gates, current_success=means, differences=differences,
                matches=int(sum(counts)), nonempty_blocks=len(current))


def present_summary(out, config):
    decisions = []
    for d, dose in enumerate(e.DOSES):
        current, signals, counts, rows = [], [], [], []
        for seed in config['seeds']:
            with np.load(Path(out)/f'present_{seed}.npz') as raw:
                eligible = raw['eligible'][d]
                n = int(eligible.sum())
                counts.append(n)
                row = dict(seed=seed, matched=n, feasible=int(raw['feasible'].sum()), eligible=eligible.tolist())
                if n:
                    c = mean_pairs(raw['validation_success'][:, d].mean(axis=0), eligible)
                    s = raw['validation_signals'][:, d].mean(axis=0)[:, eligible].mean(axis=1)
                    current.append(c)
                    signals.append(s)
                    row.update(current_success=c.tolist(), current_outputs=s.tolist(),
                               record_norm=mean_pairs(raw['record_norm'][d], eligible).tolist(),
                               effective_total_norm=mean_pairs(raw['effective_total_norm'][d], eligible).tolist())
                rows.append(row)
        decision = current_decision(current, signals, counts, config)
        decision.update(dose=int(dose), blocks=rows)
        decisions.append(decision)
    return decisions


def transmission_decision(joint, current_passed, config, audit_passed):
    joint = np.asarray(joint).reshape(-1, len(e.ARMS))
    estimate = estimator(len(joint), config)
    own = joint[:, e.ARMS.index('renewal')]
    stats = dict(joint_functional_retention=estimate(own, True))
    for control in ('read_off', 'write_off'):
        stats['renewal_minus_'+control] = estimate(own-joint[:, e.ARMS.index(control)], True)
    gates = dict(current_passed=bool(current_passed), integrity_passed=bool(audit_passed))
    for name, stat in stats.items():
        minimum, lower = (.80, .70) if name == 'joint_functional_retention' else (.50, 0.)
        gates[name+'_minimum_mean'] = stat['mean'] is not None and stat['mean'] >= minimum
        gates[name+'_lower_bound'] = stat['directional_lower'] is not None and (
            stat['directional_lower'] >= lower if name == 'joint_functional_retention' else stat['directional_lower'] > lower)
    return dict(passed=all(gates.values()), gates=gates, statistics=stats), estimate
