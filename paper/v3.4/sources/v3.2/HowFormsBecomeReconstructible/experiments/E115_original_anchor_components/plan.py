"""One size-matched component control anchored at the original diagonal states."""
from pathlib import Path
from E111_halfway_component_cross.plan import CONDITIONS as ORIGINAL_CONDITIONS, VARIANTS, METRICS
from E112_fresh_component_prediction.plan import BLOCKS, TECHNICAL, PRIMARY as PRIOR_PRIMARY
from E113_component_threshold_diagnosis.plan import COPY_NAMES, OUTPUT_METRICS
from E114_matched_component_amplitude.plan import NORM_KEYS, PRIMARY as MIDPOINT_PRIMARY

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
COMPONENTS=tuple(a+k for a in 'ON' for k in 'BMD')
CONDITIONS=tuple(c+l for c in COMPONENTS for l in 'ON')
PAIRS=tuple((c,a,l,a+'B'+l,a+k+l) for c,k in (('m','M'),('d','D')) for a in 'ON' for l in 'ON')
MIDPOINT_COPIES=('cases.csv','summary.json','comparisons.csv','events.csv','crossings.csv')
SCOPES=('all','eligible','affected','erased')
PRIMARY='anchored_shared_minus_cue_delta_both'
CONTINUOUS=tuple('anchored_shared_minus_cue_delta_'+q for q in METRICS if q!='both')
ANCHOR_KEYS=tuple(a+'_'+k for a in 'ON' for k in ('m_both_contrast_abs','d_both_contrast_abs','excess'))


def full_component(component):
    assert component in COMPONENTS
    a,k=component;b='N' if a=='O' else 'O'
    return a+a if k=='B' else b+a if k=='M' else a+b


def settings(mode):
    assert mode in ('benchmark','scientific')
    stop=2048 if mode=='scientific' else 512;R=4 if mode=='scientific' else 1
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),recipients=R,
        conditions=list(CONDITIONS),components=list(COMPONENTS),variants=list(VARIANTS),draws=[0,1],
        switch_step=stop//2,reader=dict(read_steps=stop,settling_steps=stop//2),
        config=dict(recipients=R,dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),
        primary=PRIMARY,primary_group='mixture/pooled/pooled/eligible',confidence=.95,bootstrap_samples=10000,
        contrast='gross anchored m sensitivity minus gross anchored d sensitivity of C-F success',
        positive_criterion='95% whole-source interval lower bound strictly above zero',
        norm='mean absolute component difference over free cells, pooled equally across C/F',
        free_cells='living cells excluding cue clamp; output ports included',target='min(original_m_size,original_d_size)',
        scales='E114 target/original component size; zero original norm gives zero scale',
        placement='from each original OO/NN diagonal state toward the opposite component; other component fixed',
        anchor_and_later_average='equal weight across O/N original anchors and O/N later noise',
        initial_arithmetic='anchor + scale*(original full-component target - anchor); exact endpoints at scale 0 or 1',
        pair_common_scales=True,variant_specific_norms_not_forced_equal=True,zero_targets_retained=True,
        attenuation_only=True,initial_clipping=False,initial_bounds=[-2.,2.],fixed_birth='O',paired_cue_noise=True,
        exact_archived_reuse='baseline or scale 0/1 only, by state-derived scale; partial scales get new readers',
        original_later_streams=['O','N'],absolute_noise_offsets=True,
        source_recipe='all completed E112 sources and unchanged safe four-cycle witnesses; E114 scales unchanged',
        source_selection=False,witness_reselection=False,new_source_blocks=0,new_injuries=False,new_streams=False,
        writer_dynamics_repeated=False,old_outcomes_known=True,anchored_outcomes_unseen_at_freeze=True,
        inference_scope='new controlled intervention on known sources, not fresh-source confirmation',
        prior_primaries_unchanged=True,scopes=list(SCOPES),max_workers=4,timing_margin=3,
        summary_allowance_seconds=180,resource_limit_seconds=43200,
        automatic_extension=False,automatic_restart=False,automatic_successor=False)


def identity(row):return tuple(int(row[k]) for k in ('task','arm','founder','recipient'))
def key(row):return identity(row)+(int(row['draw']),)


def summary_keys():
    return (list(NORM_KEYS)+[c+'_'+v+'_'+q for c in CONDITIONS for v in ('C','F','delta') for q in METRICS]+
        [c+'_'+q+'_'+term for c in ('m','d') for q in METRICS for term in OUTPUT_METRICS]+
        [PRIMARY,'full_size_excess','midpoint_excess','change_in_excess','anchor_minus_midpoint']+list(CONTINUOUS)+list(ANCHOR_KEYS))
