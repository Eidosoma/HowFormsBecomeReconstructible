"""Count-matched selected-sign arrangement under two frozen injury masks."""
from pathlib import Path
from E101_cross_noise_components.plan import (settings as previous, OLD098, OLD099,
    OLD100, CONTRASTS100, STARTS as OLD101, CONTRASTS as CONTRASTS101)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARENT = ROOT/'E101_cross_noise_components'
BLOCKS = tuple(range(980000,980032))
TECHNICAL = (9000980,9000981)
METRICS = ('both','minimum_margin','transfer','aligned_transfer')
STARTS = dict(B=0,M=4,D=8,S=12)
CONTRASTS = {
    'arrangement_advantage': {'D':1,'S':-1},
    'selected_transfer': {'D':1,'B':-1},
    'donor_sign': {'D':1,'M':-1},
    'shuffle_sign': {'S':1,'M':-1},
    'shuffled_transfer': {'S':1,'B':-1},
    'magnitude_only': {'M':1,'B':-1},
}
INTERACTIONS = ()
PRIMARY = ('arrangement_advantage_both','selected_transfer_both')


def settings(mode):
    cfg=previous(mode)
    for key in ('magnitude_only_signs','old_E098_E099_E100_endpoints_retained'):
        cfg.pop(key,None)
    cfg.update(slots=18,variants=list(STARTS),primary=list(PRIMARY),
        new_terminal_stream_phase='E102_terminal_DRAW',
        intervention='selected_sign_permutation_within_two_draw_survival_strata',
        prediction='donor_sign_arrangement_beats_count_matched_shuffle_and_selected_transfer_repeats',
        permutation_stream='E102/task/selected_sign_permutation/arm/founder/recipient/stratum',
        permutation_count_per_record=1,permutation_shared_across_reader_draws=True,
        permutation_pool='selected_nonzero_edges_in_C_order_within_survival_signature_0_to_3',
        permutation_conditioning='fixed_injury_masks_only_no_birth_noise_states_scores_or_outcomes',
        sign_counts='exact_within_survival_strata_hence_global_and_each_injury',
        homogeneous_empty_singleton_or_identity_permutations='retain_without_resampling',
        local_incident_sign_counts_and_signed_weight_sums='not_preserved_report_separately',
        old_E098_E099_E100_E101_endpoints_retained=True)
    return cfg


def identity(row):
    return tuple(row[k] for k in ('task','arm','founder','recipient'))


def expected_identities(cfg):
    return {(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4)
            for r in range(cfg['recipients']) for d in cfg['draws']}


def references():
    baseline=list(range(4))*4+[16,17]
    donor=list(range(8,12))*4+[16,17]
    return baseline,donor
