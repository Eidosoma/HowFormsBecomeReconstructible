"""Fresh cohort, unchanged apparatus and a three-contrast confirmation family."""
from pathlib import Path
from E057_fresh_capture_confirmation.plan import settings as prior

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BLOCKS=tuple(range(39000,39032))
TECH_BLOCK=900041
NAMES=dict(fixture='fixture_v1',benchmark='benchmark_v1',scientific='confirmation_v1')
CONDITIONS=('FF','FO','OF','OO','earlier_changed','earlier_unchanged')
SLOTS=tuple(f'{c}_{a}' for c in CONDITIONS for a in ('sham','pulse'))+('erased',)
PRIMARY=('earlier_sign_benefit','sign_magnitude_interaction','joint_magnitude_excess_loss')
CONFIDENCE=1-.05/3
SOURCE_METRICS=('common_edges','changed_edges','unchanged_edges','later_only_edges')
GRAPH_FIELDS=('edges','components','cycle_rank','negative_basis_cycles','input_reachable',
              'positive_port_reachable','negative_port_reachable')


def settings(mode):
    p=prior(mode);body=p['body'].copy();body['recovery_steps']=0
    continuation={**p['cycle'],'generations':3}
    return dict(mode=mode,blocks=list(BLOCKS) if mode=='scientific' else [TECH_BLOCK],
        config=p['config'],source_cycle=p['cycle'],body=body,continuation=continuation,
        reader=p['reader'],recipients=p['config']['recipients'],slots=list(SLOTS),
        primary=list(PRIMARY),primary_confidence=CONFIDENCE,primary_family_size=3,
        bootstrap_samples=10000,fresh_sources=mode=='scientific',old_observations_pooled=False,
        history='paired_rewrite',capture='early',source_horizons=[0,3],
        source_noise_correlation=1.,body_noise_correlation=0.,continuation_noise_correlation=1.,
        reader_noise_correlation=1.,birth_correlation=1.,normalization_floor=0.,dtype='float64')
