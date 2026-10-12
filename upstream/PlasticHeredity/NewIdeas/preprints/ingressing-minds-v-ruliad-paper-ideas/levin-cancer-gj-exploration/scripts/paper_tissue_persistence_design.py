"""P14: bounded 2D persistence/relapse bridge, not an exact paper replication."""
import hashlib
import json
import numpy as np
import paper_lineage_return_design as prior
from paper_lineage_return_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-lineage-return-20260917T124731Z-ywa3ycu1'
STAGES=('panel',)
HISTORIES=('written','ordinary','fresh_M')
ARMS=('sham','internal','boundary','both','rna','cut')
PATCH=(83,84,85)
COMPETITORS=(28,29,30,41,42,43,54,55,56)
BACKGROUND_E=tuple(i for i in range(169) if i not in PATCH+COMPETITORS)
FIXED=dict(experiment='P14_tissue_persistence',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=129600,verification_timeout_seconds=3000,
    maximum_cases=36,maximum_integrations=288,source_seed=301,challenge_seed=401,
    histories=list(HISTORIES),arms=list(ARMS),shape=[13,13],patch=list(PATCH),
    competitor_patch=list(COMPETITORS),protein_index=7,protein_percent=25,
    intervention_horizon=20000,withdrawal_horizons=[10000,10000],
    replacement_horizons=[20000,20000,20000],isolation_horizons=[10000,10000],
    basal_internal=60,basal_boundary=1,helper_power=60,mirna_kd=1.25e-14,
    clock=prior.FIXED['clock'],external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_TISSUE_PERSISTENCE_PROTOCOL.md',ROOT/'configs/paper_tissue_persistence_v1.json',
    ROOT/'configs/paper_tissue_persistence_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_tissue_persistence_design.py','run_paper_tissue_persistence.py',
    'analyze_paper_tissue_persistence.py','run_paper_tissue_persistence_detached.py','test_paper_tissue_persistence.py')]

def case(history='written',arm='both',fine=False):
    return dict(id='__'.join(('panel',history,arm))+('__fine' if fine else ''),
                stage='panel',history=history,arm=arm,fine=fine)
def stage_cases(stage):
    if stage!='panel': raise ValueError('Unknown P14 stage')
    return [case(h,a,f) for f in (False,True) for h in HISTORIES for a in ARMS]
def fixed_cases(): return stage_cases('panel')
def validate_config(config):
    if config!=FIXED: raise ValueError('Unregistered P14 configuration')
    return config
def word(i):
    return int(hashlib.sha256(f'P14_tissue_persistence_v1|401|turnover|{i}'.encode('ascii')).hexdigest()[:16],16)
def draw_book(): return {'401':{'turnover':[f'{word(i):016x}' for i in range(3)]}}
def incoming(M,i):
    value=M.copy(); value[7]*=1+(word(i)*51//2**64-25)/100
    return value
def stem(c): return 'p14:'+c['history']
def fresh_ids(c): return [stem(c)+f':ordinary_M:{i:02d}' for i in range(3)]
def new_id(c,i): return stem(c)+f':replacement:{i:02d}'
def source(c):
    if c['history']=='fresh_M': return None,None,fresh_ids(c)
    name=f'returns__{c["history"]}__301__open'+('__fine' if c['fine'] else '')
    return name,'r09_isolated_2',[f'p13:{c["history"]}:301:pupil:09:{i:02d}' for i in range(3)]
def logical_base(c): return 0 if c['history']=='fresh_M' else 1020000
def tissue_ids(c,carrier_ids):
    ids=[stem(c)+f':background:{i:03d}' for i in range(169)]
    for p,name in zip(PATCH,carrier_ids): ids[p]=name
    return ids
def treatment(c):
    arm=c['arm']
    return dict(internal=1 if arm in ('internal','both','rna','cut') else 60,
                boundary=60 if arm in ('boundary','both','rna','cut') else 1,
                kd=0 if arm=='rna' else 1.25e-14,cut=arm=='cut')
def execution_manifest():
    result=prior.execution_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result
def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text())
    a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=102 or not a['quality_gate'] or
        a['independent_check_count']!=63744 or any(x['control_qualified_successes']!=3 for x in a['trial_counts'])):
        raise ValueError('Unexpected P13 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]
    names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P13 input')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p13/'+n:PREDECESSOR/n for n in names}
