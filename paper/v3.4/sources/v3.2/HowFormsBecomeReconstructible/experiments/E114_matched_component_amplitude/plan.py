"""One frozen matched-amplitude contrast on the complete known E112 cohort."""
from pathlib import Path
from E111_halfway_component_cross.plan import CONDITIONS, COMPONENTS, VARIANTS, METRICS
from E112_fresh_component_prediction.plan import BLOCKS, TECHNICAL, PRIMARY as PRIOR_PRIMARY
from E113_component_threshold_diagnosis.plan import COPY_NAMES, PAIRS, OUTPUT_METRICS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PRIMARY='matched_shared_minus_cue_delta_both'
SCOPES=('all','eligible','affected','erased')
NORM_KEYS=('free_cells','original_m_size','original_d_size','target_size','m_scale','d_scale',
           'zero_target','m_C_size','m_F_size','d_C_size','d_F_size','maximum_size_error','maximum_component_leak')


def settings(mode):
    assert mode in ('benchmark','scientific')
    stop=2048 if mode=='scientific' else 512;R=4 if mode=='scientific' else 1
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),recipients=R,
        conditions=list(CONDITIONS),components=list(COMPONENTS),variants=list(VARIANTS),draws=[0,1],
        switch_step=stop//2,reader=dict(read_steps=stop,settling_steps=stop//2),
        config=dict(recipients=R,dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),
        primary=PRIMARY,primary_group='mixture/pooled/pooled/eligible',confidence=.95,bootstrap_samples=10000,
        contrast='gross matched m sensitivity minus gross matched d sensitivity of C-F success',
        positive_criterion='95% whole-source interval lower bound strictly above zero',
        norm='mean absolute component difference over free cells, pooled equally across C/F',
        free_cells='living cells excluding cue clamp; output ports included',target='min(original_m_size,original_d_size)',
        scales='target/original_component_size; zero original norm gives zero scale',
        placement='symmetric about each original O/N component midpoint',
        pair_common_scales=True,variant_specific_norms_not_forced_equal=True,zero_targets_retained=True,
        attenuation_only=True,initial_clipping=False,initial_bounds=[-2.,2.],
        full_scale_diagonal_states_reused_exactly=True,fixed_birth='O',paired_cue_noise=True,
        original_later_streams=['O','N'],absolute_noise_offsets=True,
        source_recipe='all completed E112 sources, first safe four-cycle witness unchanged',
        source_selection=False,witness_reselection=False,new_source_blocks=0,new_injuries=False,new_streams=False,
        writer_dynamics_repeated=False,old_outcomes_known=True,matched_outcomes_unseen_at_freeze=True,
        inference_scope='new controlled intervention on known sources, not fresh-source confirmation',
        prior_primary_unchanged=True,scopes=list(SCOPES),max_workers=4,timing_margin=3,
        summary_allowance_seconds=180,resource_limit_seconds=43200,
        automatic_extension=False,automatic_restart=False,automatic_successor=False)


def identity(row):return tuple(int(row[k]) for k in ('task','arm','founder','recipient'))
def key(row):return identity(row)+(int(row['draw']),)


def summary_keys():
    return (list(NORM_KEYS)+[c+'_'+v+'_'+q for c in CONDITIONS for v in ('C','F','delta') for q in METRICS]+
            [c+'_'+q+'_'+term for c in ('m','d') for q in METRICS for term in OUTPUT_METRICS]+
            [PRIMARY,'full_size_excess','change_in_excess'])
