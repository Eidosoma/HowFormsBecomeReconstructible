"""P13: second content change in actual P12 descendants, three new handovers."""
import hashlib
import json
import numpy as np
import paper_lineage_robustness_design as prior
from paper_lineage_robustness_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-lineage-robustness-20260916T094348Z-quf8m72y'
STAGES=('benchmarks','returns','writing_controls','relay_controls')
HISTORIES=('written','ordinary')
SEEDS=(301,302,303)
WRITING_CONTROLS=('rna','cut','sham','none')
FIXED=dict(experiment='P13_lineage_return',revision=REVISION,workers=2,
    worker_timeout_seconds=14400,total_budget_seconds=86400,verification_timeout_seconds=2700,
    maximum_cases=102,maximum_integrations=1008,challenge_seeds=list(SEEDS),source_seeds=[201,202,203],
    timing_level='strong',protein_level='strong',gap_maximum=5000,protein_percent=25,protein_index=7,
    contact_per_pupil=20000,contact_window=80000,writing_horizon=20000,hold_horizons=[10000,10000],
    round_numbers=[7,8,9],clock=prior.FIXED['clock'],external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_LINEAGE_RETURN_PROTOCOL.md',ROOT/'configs/paper_lineage_return_v1.json',
    ROOT/'configs/paper_lineage_return_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_lineage_return_design.py','run_paper_lineage_return.py',
        'analyze_paper_lineage_return.py','run_paper_lineage_return_detached.py','test_paper_lineage_return.py')]

def case(stage,history='written',seed=301,route='open',fine=False):
    return dict(id='__'.join((stage,history,str(seed),route))+('__fine' if fine else ''),
                stage=stage,history=history,seed=seed,route=route,fine=fine)

def stage_cases(stage):
    result=[]
    for fine in (False,True):
        if stage=='benchmarks':
            result += [case(stage,'benchmark',seed,fine=fine) for seed in SEEDS]
        elif stage=='returns':
            result += [case(stage,h,s,fine=fine) for h in HISTORIES for s in SEEDS]
        elif stage=='writing_controls':
            result += [case(stage,h,s,r,fine) for h in HISTORIES for s in SEEDS for r in WRITING_CONTROLS]
        elif stage=='relay_controls':
            result += [case(stage,h,s,r,fine) for h in ('benchmark',)+HISTORIES for s in SEEDS for r in ('rna','cut')]
        else: raise ValueError('Unknown P13 stage')
    return result

def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def validate_config(config):
    if config!=FIXED: raise ValueError('Unregistered P13 configuration')
    return config

def word(seed,domain,index):
    return int(hashlib.sha256(f'P13_lineage_return_v1|{seed}|{domain}|{index}'.encode('ascii')).hexdigest()[:16],16)

def draw_book():
    domains=[f'timing:r{n:02d}' for n in (7,8,9)]+['protein:benchmark']+[f'protein:r{n:02d}' for n in (7,8,9)]
    return {str(s):{key:[f'{word(s,key,i):016x}' for i in range(3)] for key in domains} for s in SEEDS}

def intervals(seed,number):
    result=[]; time=0
    for i in range(3):
        gap=100*(word(seed,f'timing:r{number:02d}',i)*51//2**64)
        if gap: result.append((time,time+gap,[])); time+=gap
        result.append((time,time+20000,[i])); time+=20000
    result.append((time,80000,[]))
    return result

def recipient(stock,seed,role):
    state=np.repeat(stock,3,axis=1)
    delta=[word(seed,'protein:'+role,i)*51//2**64-25 for i in range(3)]
    state[7]*=1+np.array(delta)/100
    return state

def stem(c): return f'p13:{c["history"]}:{c["seed"]}'
def founder_ids(c): return [stem(c)+f':founder:{i:02d}' for i in range(3)]
def pupil_ids(c,n): return [stem(c)+f':pupil:{n:02d}:{i:02d}' for i in range(3)]
def cue_ids(c): return [stem(c)+f':writing:cue:{i:02d}' for i in range(6)]
def source(c):
    p=prior.case('combined',seed=c['seed']-100,history=c['history'],fine=c['fine'])
    return p['id'],'r06_isolated_2',prior.pupil_ids(p,6)
def parent(c):
    return case('benchmarks' if c['history']=='benchmark' else 'returns',c['history'],c['seed'],fine=c['fine'])
def logical_base(c): return 0 if c['history']=='benchmark' else 680000

def execution_manifest():
    result=prior.execution_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result

def input_paths():
    summary=json.loads((PREDECESSOR/'summary.json').read_text())
    audit=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not summary.get('all_execution_valid') or len(summary['cases'])!=158 or
        summary['selection']!={'timing':'strong','cells':'strong'} or not audit['quality_gate'] or
        any(r['control_qualified_successes']!=3 for r in audit['trial_counts'])):
        raise ValueError('Unexpected P12 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[s+'_audit.json' for s in prior.STAGES]
    names += ['frozen/'+p.name for p in prior.LOCAL_FILES]
    names += ['inputs/'+name for name in prior.input_paths()]
    for row in summary['cases']:
        if row['id']!=row['result']['case']['id'] or not row['execution_pass']: raise ValueError('Invalid P12 input')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p12/'+name:PREDECESSOR/name for name in names}

