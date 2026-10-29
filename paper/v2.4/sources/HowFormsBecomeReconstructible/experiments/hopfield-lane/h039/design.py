"""Fresh-network confirmation decisions, frozen before new outcomes."""
from __future__ import annotations

import numpy as np
from h035 import design as base

FIRST_BLOCK = 39039000
BOOTSTRAPS = 100000
ANALYSIS_SEED = 39039
ALPHA = .05
MINIMUM_EFFECT = .10
MINIMUM_JOINT_SUCCESS = .50
MINIMUM_POSITIVE_CONTROL = .75
CONTROLS = ('foreign_a', 'foreign_b', 'foreign_both', 'scrambled', 'erased',
            'read_off', 'write_off', 'damaged_copy', 'writer_scrambled')
PRIMARY = ('serial_benefit_at_gain8', *('own_minus_'+arm for arm in CONTROLS))
SECONDARY = ('serial_benefit_at_gain4', 'uninterrupted_benefit')
FAMILY = (*PRIMARY, *SECONDARY)
EXTRA = ('g16_4_4', 'g16_4_8', 'g16_8_4', 'g16_8_8',
         'path_gain4', 'path_gain8', 'g16_protected_gain8', 'renewal_minus_protected',
         'g0_renewal_gain8', 'terminal_minus_initial')
ENDPOINTS = (*FAMILY, *EXTRA)
CLASSIFICATION = 'FRESH_NETWORK_CONFIRMATION'


def endpoints(summary):
    outcomes = {(r['generation'], r['load'], r['arm'], r['reconstruction_gain'], r['assay_gain']): r
                for r in summary['outcome_rows']}
    paths = {(r['load'], r['arm'], r['reconstruction_gain']): r for r in summary['path_rows']}
    def rate(b, r, arm='renewal', g=16):
        return outcomes[(g, 'both', arm, b, r)]['joint']
    strong = rate(8, 8)
    values = {'serial_benefit_at_gain8': strong-rate(4, 8)}
    values.update({'own_minus_'+a: strong-rate(8, 8, a) for a in CONTROLS})
    values['serial_benefit_at_gain4'] = rate(8, 4)-rate(4, 4)
    path = [paths[('both', 'renewal', g)]['all_boundaries_success'] for g in (4, 8)]
    values['uninterrupted_benefit'] = path[1]-path[0]
    values.update({f'g16_{b}_{r}': rate(b, r) for b in (4, 8) for r in (4, 8)})
    values.update(path_gain4=path[0], path_gain8=path[1],
        g16_protected_gain8=rate(8, 8, 'protected_copy'),
        renewal_minus_protected=strong-rate(8, 8, 'protected_copy'),
        g0_renewal_gain8=rate(8, 8, g=0), terminal_minus_initial=strong-rate(8, 8, g=0))
    assert set(values) == set(ENDPOINTS)
    return values


def decisions(estimates, integrity_passed=True):
    controls = dict(integrity=bool(integrity_passed),
        initial_task=estimates['g0_renewal_gain8']['mean'] >= MINIMUM_POSITIVE_CONTROL,
        protected_copy=estimates['g16_protected_gain8']['mean'] >= MINIMUM_POSITIVE_CONTROL,
        useful_joint_success=estimates['g16_8_8']['mean'] >= MINIMUM_JOINT_SUCCESS)
    contrasts = {name: dict(mean_at_least_ten_points=estimates[name]['mean'] >= MINIMUM_EFFECT,
        adjusted_lower_positive=estimates[name]['adjusted_lower'] > 0) for name in FAMILY}
    passed = lambda name: all(contrasts[name].values())
    primary = all(controls.values()) and all(passed(k) for k in PRIMARY)
    original = primary and passed('serial_benefit_at_gain4')
    uninterrupted = primary and passed('uninterrupted_benefit') and estimates['path_gain8']['mean'] >= .5
    return dict(primary='SERIAL_GUIDANCE_CONFIRMED' if primary else 'SERIAL_GUIDANCE_NOT_CONFIRMED',
        original_reader='ORIGINAL_READER_BENEFIT_CONFIRMED' if original else 'ORIGINAL_READER_BENEFIT_NOT_CONFIRMED',
        uninterrupted='UNINTERRUPTED_INHERITANCE_CONFIRMED' if uninterrupted else 'UNINTERRUPTED_INHERITANCE_NOT_CONFIRMED',
        primary_qualified=primary, original_reader_qualified=original, uninterrupted_qualified=uninterrupted,
        controls=controls, contrast_gates=contrasts,
        uninterrupted_absolute_gate=estimates['path_gain8']['mean'] >= .5,
        secondary_claims_require_primary=True)


def settings(blocks):
    return dict(generations=base.GENERATIONS, checkpoints=base.CHECKPOINTS,
        reconstruction_gains=[4, 8], assay_gains=[4, 8], fresh_probes=8,
        audit_probe_excluded=True, loads=base.LOADS, arms=base.ARMS,
        input_root=35035, probe_root=38038, random_cohort='pilot',
        confirmation_blocks=list(range(FIRST_BLOCK, FIRST_BLOCK+blocks)),
        engineering_blocks=list(range(4)), family=FAMILY, endpoints=ENDPOINTS,
        alpha=ALPHA, bootstrap_draws=BOOTSTRAPS, analysis_seed=ANALYSIS_SEED,
        minimum_effect=MINIMUM_EFFECT, minimum_joint_success=MINIMUM_JOINT_SUCCESS,
        minimum_positive_control=MINIMUM_POSITIVE_CONTROL,
        classification=CLASSIFICATION, writer_changes=False, predictor_fits=0)
