"""Fresh finite histories; five fixed formulations and one pruning rewrite."""
from pathlib import Path
from E098_writer_pairing_tradeoff.plan import settings as legacy_settings
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BLOCKS=tuple(range(1180000,1180032))
TECHNICAL=(9000980,9000981)
REGIMES=('T0F0Q0','T1F0Q0','T0F1Q0','T0F0Q1','T1F1Q1')
ENDPOINTS=('I0','P0','I1','P1')
EPS=ENDPOINTS+('I1_common','P1_common')
METRICS=('both','minimum_margin','transfer','aligned_transfer')

def parameters(reg):
    return dict(tolerance=int(reg[1])*1e-4,floor=int(reg[3])*1e-4,grid=int(reg[5])*2**-16)

def settings(mode):
    assert mode in ('fixture','probe','benchmark','scientific')
    old=legacy_settings('scientific' if mode=='scientific' else 'benchmark')
    s=old['source'];R=1 if mode=='fixture' else 4
    c=dict(old['config'],recipients=R);acq=dict(s['source_config'],recipients=R)
    short=128;steps=2048 if mode=='scientific' else short
    body=dict(s['body'],recipients=R)
    if mode!='fixture':
        body.update(body_pre_steps=steps,body_settling_steps=steps//2,
                    pulse_steps=32 if mode=='scientific' else 8,
                    observe_steps=32 if mode=='scientific' else 8)
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),
        regimes=list(REGIMES),recipients=R,config=c,source_config=acq,body=body,
        ancestry_generations=1 if mode=='probe' else 32,continuation_generations=3,
        source_steps=dict(read_steps=steps,settling_steps=steps//2),
        steps=dict(read_steps=512 if mode=='fixture' else steps,
                   settling_steps=256 if mode=='fixture' else steps//2),
        source_tags=['E016','E022','E055','E058','E077'],draws=[0,1],
        primary_regime='T1F1Q1',primary_population='mixture/pooled/pooled',
        absolute_floor=.5,retention_allowance=.05,primary_requires_all_ten=True,
        bootstrap_samples=10000,bootstrap_seed=['E118','finite_formation'],confidence=.95,
        own_pre_channel_repair_tags=True,common_coordinate_comparison=False,
        finite_acquisition_from_first_commit=True,acquisition_weight_feedback=False,
        acquisition_fixed_unit_scaffold=True,holding_steps_omitted=128,
        all_sources_retained=True,new_source_blocks=32 if mode=='scientific' else 0,
        source_selection=False,no_outcome_selection=True,old_scientific_cases_pooled=False,
        chunk_records=128,max_workers=4,shared_cpu_ceiling=12,timing_margin=3,
        summary_allowance_seconds=240,conservative_resource_limit_seconds=172800,
        automatic_restart=False,automatic_extension=False,automatic_successor=False)

def key(row):
    return tuple(int(row[k]) for k in ('task','arm','founder','recipient','draw'))
