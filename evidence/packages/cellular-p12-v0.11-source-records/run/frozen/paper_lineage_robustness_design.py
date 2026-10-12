"""P12 registered randomized-spacing and single-component heterogeneity panel."""
import hashlib
import json
import numpy as np
import paper_editable_lineage_design as prior
from paper_editable_lineage_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-editable-lineage-20260915T125104Z-teji03a9'
STAGES=('baseline','timing','cells','combined','controls')
HISTORIES=('written','ordinary')
SCREEN_SEEDS=(101,102)
TEST_SEEDS=(201,202,203)
LEVELS=('mild','strong')
CONTROL_KINDS=('before_rna','before_cut','after_rna','after_cut','rewrite_sham','rewrite_none')
GRAPH=prior.GRAPH
FIXED=dict(experiment='P12_lineage_robustness',revision=REVISION,workers=2,
    worker_timeout_seconds=14400,total_budget_seconds=86400,verification_timeout_seconds=2700,
    maximum_cases=158,maximum_integrations=1746,screen_seeds=list(SCREEN_SEEDS),
    test_seeds=list(TEST_SEEDS),levels=list(LEVELS),gap_maxima=dict(mild=2000,strong=5000),
    protein_percent=dict(mild=10,strong=25),protein_index=7,clock=prior.FIXED['clock'],
    contact_per_pupil=20000,contact_window=80000,hold_horizons=[10000,10000],
    before_rounds=3,after_rounds=3,external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_LINEAGE_ROBUSTNESS_PROTOCOL.md',
    ROOT/'configs/paper_lineage_robustness_v1.json',
    ROOT/'configs/paper_lineage_robustness_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_lineage_robustness_design.py','run_paper_lineage_robustness.py',
        'analyze_paper_lineage_robustness.py','run_paper_lineage_robustness_detached.py',
        'test_paper_lineage_robustness.py')]

def case(stage,label='',level='',seed=0,history='ordinary',route='open',fine=False):
    parts=[stage]+[str(x) for x in (label,level,seed,history,route) if x!='']
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,label=label,
                level=level,seed=seed,history=history,route=route,fine=fine)

def stage_cases(stage):
    result=[]
    for fine in (False,True):
        if stage=='baseline':
            result += [case(stage,label=l,fine=fine) for l in ('M','E')]
        elif stage in ('timing','cells'):
            for level in LEVELS:
                for label in ('M','E'):
                    result += [case(stage,label,level,s,fine=fine) for s in SCREEN_SEEDS]
                    result += [case(stage,label,level,101,route=r,fine=fine) for r in ('rna','cut')]
        elif stage=='combined':
            result += [case(stage,seed=s,history=h,fine=fine) for h in HISTORIES for s in TEST_SEEDS]
        elif stage=='controls':
            result += [case(stage,seed=s,history=h,route=r,fine=fine)
                       for h in HISTORIES for s in TEST_SEEDS
                       for r in CONTROL_KINDS+(('founder_none',) if h=='written' else ())]
        else: raise ValueError('Unknown P12 stage')
    return result

def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]

def validate_config(config):
    if config!=FIXED: raise ValueError('Unregistered P12 configuration')
    return config

def word(seed,domain,index):
    text=f'P12_lineage_robustness_v1|{seed}|{domain}|{index}'
    return int(hashlib.sha256(text.encode('ascii')).hexdigest()[:16],16)

def draw_book():
    domains=[f'timing:r{n:02d}' for n in range(1,7)]+['protein:founder']+[f'protein:r{n:02d}' for n in range(1,7)]
    return {str(seed):{key:[f'{word(seed,key,i):016x}' for i in range(3)] for key in domains}
            for seed in (0,)+SCREEN_SEEDS+TEST_SEEDS}

def levels(c,selection):
    if c['stage']=='baseline': return None,None
    if c['stage']=='timing': return c['level'],None
    if c['stage']=='cells': return None,c['level']
    return selection['timing'],selection['cells']

def intervals(seed,number,level):
    cap=0 if level is None else FIXED['gap_maxima'][level]
    gaps=[100*(word(seed,f'timing:r{number:02d}',i)*(cap//100+1)//2**64) if cap else 0 for i in range(3)]
    result=[]; time=0
    for i,gap in enumerate(gaps):
        if gap: result.append((time,time+gap,[])); time+=gap
        result.append((time,time+20000,[i])); time+=20000
    result.append((time,80000,[]))
    return result

def recipient(stock,seed,role,level):
    state=np.repeat(stock,3,axis=1)
    cap=0 if level is None else FIXED['protein_percent'][level]
    delta=[word(seed,'protein:'+role,i)*(2*cap+1)//2**64-cap if cap else 0 for i in range(3)]
    state[7]*=1+np.array(delta)/100
    return state

def stem(c):
    if c['stage'] in ('combined','controls'): return f'p12:combined:{c["history"]}:{c["seed"]}'
    return f'p12:{c["stage"]}:{c["label"]}:{c["level"]}:{c["seed"]}'

def founder_ids(c): return [stem(c)+f':founder:{i:02d}' for i in range(3)]
def pupil_ids(c,n): return [stem(c)+f':pupil:{n:02d}:{i:02d}' for i in range(3)]

def archived_source(c):
    fine='__fine' if c['fine'] else ''
    if c['label']=='M':
        return 'age_M'+fine,'age_isolated_2',[f'p11:ordinary:founder:{i:02d}' for i in range(3)]
    return 'rewrite_E__ordinary__E_open'+fine,'writing_isolated_2',[
        f'p11:before:ordinary:pupil:03:{i:02d}' for i in range(3)]

def parent(c): return case('combined',seed=c['seed'],history=c['history'],fine=c['fine'])

def execution_manifest():
    result=prior.execution_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result

def input_paths():
    summary=json.loads((PREDECESSOR/'summary.json').read_text())
    if (not summary.get('all_execution_valid') or len(summary['cases'])!=74 or
        not all(v['quality_gate'] and v['eligible'] for v in summary['gates'].values())):
        raise ValueError('Unexpected P11 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[s+'_audit.json' for s in prior.STAGES]
    names += ['frozen/'+p.name for p in prior.LOCAL_FILES]
    names += ['inputs/'+name for name in prior.input_paths()]
    for row in summary['cases']:
        if row['id']!=row['result']['case']['id'] or not row['execution_pass']: raise ValueError('Invalid P11 case')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid inputs')
    return {'p11/'+name:PREDECESSOR/name for name in names}
