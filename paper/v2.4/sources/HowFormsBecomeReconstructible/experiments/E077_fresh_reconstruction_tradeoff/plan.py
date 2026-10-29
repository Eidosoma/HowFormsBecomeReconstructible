"""Untouched sources; one pruning/rewrite and two selected-value substitutions."""
from pathlib import Path
import numpy as np
from E068_fresh_recovery_confirmation.plan import settings as ancestry_settings
from E073_saved_cohort_reversal_replication.plan import settings as endpoint_settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLOCKS = tuple(range(41000, 41032))
TECH_BLOCK = 900041
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='confirmation_v1')
ARMS = ('native_sham', 'native_pulse', 'mixture_sham', 'mixture_pulse')
CONDITIONS = ('I0', 'P0', 'I1', 'P1', 'M1', 'J1')
STARTS = dict(I0=0, P0=4, I1=9, P1=13, M1=18, J1=22)
SLOTS = (tuple(f'{c}_{a}' for c in ('I0', 'P0') for a in ARMS) + ('erased_h0',)
         + tuple(f'{c}_{a}' for c in ('I1', 'P1') for a in ARMS) + ('erased_h1',)
         + tuple(f'{c}_{a}' for c in ('M1', 'J1') for a in ARMS))
REFERENCE = np.array([0,1,2,3,0,1,2,3,8,9,10,11,12,9,10,11,12,17] + [13,14,15,16]*2)
BASELINE = np.array(list(range(9))*2 + [4,5,6,7]*2)
PRIMARY = ('mixture_pruning_h0', 'mixture_pruning_h1',
           'mixture_magnitudes_h1', 'mixture_joint_h1')
PREDICTED = ('POSITIVE_EFFECT', 'NEGATIVE_EFFECT', 'NEGATIVE_EFFECT', 'POSITIVE_EFFECT')
CONFIDENCE = 1 - .05/4


def settings(mode):
    source = ancestry_settings(mode)
    previous = endpoint_settings(mode)
    return dict(mode=mode, blocks=list(BLOCKS) if mode=='scientific' else [TECH_BLOCK],
        recipients=previous['recipients'], config=previous['config'],
        cycle=previous['cycle'], reader=previous['reader'],
        source_config=source['source_config'], source_cycle=source['source_cycle'],
        body=source['body'], source_continuation=source['source_continuation'],
        source_recovery_cycle=source['cycle'],
        slots=list(SLOTS), arms=list(ARMS), conditions=list(CONDITIONS),
        primary=list(PRIMARY), predicted_directions=list(PREDICTED),
        primary_confidence=CONFIDENCE, primary_family_size=4, bootstrap_samples=10000,
        primary_arm_weighting='equal_within_block',
        prediction_criterion='all_four_adjusted_intervals_strictly_in_predicted_direction',
        source_family='E068', source_ancestry_tags=['E016','E022','E055','E058'],
        new_stream_tag='E077', source_recovery_stream_generation=0,
        endpoint_writer_stream_generation=1, source_boundary=1, additional_rewrites=1,
        fresh_sources=mode=='scientific', cohort_reused=False, source_generation_repeated=True,
        prior_E073_through_E076_results_known=True, old_observations_pooled=False,
        source_selection_by_outcome=False, prune_only_before_rewrite=True,
        selection='g1_incoming_zero_outgoing_nonzero_exact_fallback',
        selected_support_mismatch='stop_without_dropping_cases_preserve_available_endpoints',
        zero_convention='copysign_abs_magnitude_donor_signbit_sign_donor_including_zero',
        normalization='natural', normalization_floor=0., reader_dtype='float64',
        continuation_cue_noise_correlation=1., continuation_cue_birth_correlation=1.,
        exact_zero_fallback=True, terminal_injury='scattered_24',
        terminal_draws_shared_across_horizons=True, terminal_stream_independent_of_writer=True,
        gain_tolerance=4e-15)
