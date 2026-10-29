"""Two frozen fresh draws on two complete saved source cohorts."""
from pathlib import Path
from E077_fresh_reconstruction_tradeoff.plan import settings as prior

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
NAMES=dict(fixture='fixture_v1',benchmark='benchmark_v1',scientific='repeatability_v1')
ARMS=('native_sham','native_pulse','mixture_sham','mixture_pulse')
CONDITIONS=('I0','P0','I1','P1','OF','FF')
STARTS=dict(I0=0,P0=4,I1=9,P1=13,OF=18,FF=22)
SLOTS=tuple(f'{c}_{a}' for c in ('I0','P0') for a in ARMS)+('erased_h0',)+tuple(f'{c}_{a}' for c in ('I1','P1') for a in ARMS)+('erased_h1',)+tuple(f'{c}_{a}' for c in ('OF','FF') for a in ARMS)
REFERENCE=[0,1,2,3,0,1,2,3,8,9,10,11,12,9,10,11,12,17]+[18,19,20,21]*2


def cohort(task):
    if task==900080 or 41000<=task<41032:return 'E080'
    if task==900081 or 42000<=task<42032:return 'E081'
    raise ValueError(task)


def source_block(task):
    return 900041 if task in (900080,900081) else task


def settings(mode):
    return dict(**prior(mode)['reader'],mode=mode,
        blocks=list(range(41000,41032))+list(range(42000,42032)) if mode=='scientific' else [900080,900081],
        cohorts=['E080','E081'],reader_draws=[0,1],slots=list(SLOTS),conditions=list(CONDITIONS),arms=list(ARMS),
        primary=['E080_mixture_alignment','E081_mixture_alignment'],primary_confidence=.975,
        primary_family_size=2,bootstrap_samples=10000,centering='within_source_block_and_history',
        primary_weighting='equal_histories_within_each_block_separate_cohorts',
        reader_stream_tag='E083',cue_birth_correlation=1.,cue_noise_correlation=1.,
        reader_dtype='float64',normalization='natural',normalization_floor=0.,
        terminal_injury='scattered_24',gain_tolerance=4e-15,
        total_relative_tolerance=2e-14,total_absolute_tolerance=0.,
        prior_source_outcomes_known=True,new_source_records=False,source_generation_repeated=False,
        writer_dynamics_repeated=False,additional_rewrites=0,old_observations_pooled=False,
        old_labels_used_for_frozen_prediction=True,all_source_cases_retained=True,
        conditional_zero_denominator='null_interval_if_any_undefined_bootstrap_draw')
