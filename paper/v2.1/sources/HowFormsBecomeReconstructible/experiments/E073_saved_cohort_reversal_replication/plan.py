"""One pruning step followed by one unchanged ordinary rewrite."""
from pathlib import Path
import numpy as np
from E067_ordinary_mixture_rebuilding.plan import settings as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='replication_v1')
ARMS = ('native_sham', 'native_pulse', 'mixture_sham', 'mixture_pulse')
POLICIES = ('intact', 'pruned')
INITIAL = tuple(f'{p}_{a}' for p in POLICIES for a in ARMS) + ('erased',)
SLOTS = tuple(f'h{h}_{s}' for h in (0, 1) for s in INITIAL)
REFERENCE = np.array([0, 1, 2, 3, 0, 1, 2, 3, 8, 9, 10, 11, 12, 9, 10, 11, 12, 17])
BASELINE = np.array(list(range(9)) * 2)
PRIMARY = ('mixture_gain_h0', 'mixture_gain_h1')
CONFIDENCE = 1 - .05 / len(PRIMARY)


def index(h, policy, arm):
    return 9*h + (8 if arm == 'erased' else 4*POLICIES.index(policy) + ARMS.index(arm))


def settings(mode):
    cfg = prior(mode)
    cycle = dict(cfg['cycle'], generations=1)
    if mode == 'benchmark':
        cycle.update(read_steps=512, settling_steps=256)
    return dict(mode=mode, blocks=list(range(40000, 40032)) if mode == 'scientific' else cfg['blocks'], recipients=cfg['recipients'],
        config=cfg['config'], cycle=cycle, reader=cfg['reader'],
        source_experiment='E068', source_boundary=1, additional_rewrites=1,
        slots=list(SLOTS), arms=list(ARMS), policies=list(POLICIES), horizons=[0, 1],
        primary=list(PRIMARY), primary_confidence=CONFIDENCE, primary_family_size=2,
        bootstrap_samples=10000, primary_arm_weighting='equal_within_block',
        persistence_criterion='both_primary_gain_lower_bounds_strictly_positive',
        cohort_reused=True, prior_E067_E070_E071_outcomes_known=True,
        E068_prior_outcomes_known=True, E072_prior_outcomes_known=True,
        independent_source_cohort_from_E072=True,
        reversal_replication_criterion='h0_lower_bound_positive_and_h1_upper_bound_negative',
        old_observations_pooled=False, source_generation_repeated=False,
        prune_only_before_rewrite=True, pruning_during_or_after_rewrite=False,
        normalization='natural', normalization_floor=0., reader_dtype='float64',
        continuation_cue_noise_correlation=1., continuation_cue_birth_correlation=1.,
        exact_zero_fallback=True, terminal_injury='scattered_24',
        terminal_draws_shared_across_horizons=True, terminal_stream_independent_of_writer=True,
        gain_tolerance=4e-15)
