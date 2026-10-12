"""P15 fixed counterfactuals of background support and actual-cell onward readout."""
import json
import paper_tissue_persistence_design as prior
from paper_tissue_persistence_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-tissue-persistence-20260918T153202Z-e2vsqxgl'
STAGES=('readout','turnover','onward')
HISTORIES=('written','ordinary')
CARRIERS=('actual','stock_E')
ROUTES=('tissue','patch','patch_rna')
READOUTS=('open','rna','cut')
PATCH=(83,84,85)
FIXED=dict(experiment='P15_tissue_dependence',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=86400,verification_timeout_seconds=3600,
    maximum_cases=102,maximum_integrations=354,source_seed=301,
    source_arm='sham',source_phase='withdrawal_2',source_logical_time=1060000,
    histories=list(HISTORIES),carriers=list(CARRIERS),routes=list(ROUTES),readouts=list(READOUTS),
    shape=[13,13],patch=list(PATCH),incoming_draw_namespace='P14_tissue_persistence_v1',
    incoming_seed=401,protein_percent=25,replacement_horizons=[20000]*3,
    isolation_horizons=[10000,10000],readout_horizon=20000,readout_shape=[2,3],
    internal_power=60,boundary_power=1,helper_power=60,readout_power=60,mirna_kd=1.25e-14,
    clock=prior.FIXED['clock'],external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_TISSUE_DEPENDENCE_PROTOCOL.md',ROOT/'configs/paper_tissue_dependence_v1.json',
    ROOT/'configs/paper_tissue_dependence_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_tissue_dependence_design.py','run_paper_tissue_dependence.py',
    'analyze_paper_tissue_dependence.py','run_paper_tissue_dependence_detached.py','test_paper_tissue_dependence.py')]

def case(stage='turnover',history='written',carrier='actual',route='patch',readout='',fine=False):
    if stage=='readout': history,carrier,route='stock','stock_E',''
    parts=[stage]+[s for s in (history,carrier,route,readout) if s]
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,history=history,
                carrier=carrier,route=route,readout=readout,fine=fine)
def stage_cases(stage):
    if stage not in STAGES: raise ValueError('Unknown P15 stage')
    if stage=='readout': return [case(stage,readout=k,fine=f) for f in (False,True) for k in READOUTS]
    return [case(stage,h,s,r,k,f) for f in (False,True) for h in HISTORIES for s in CARRIERS
            for r in ROUTES for k in (READOUTS if stage=='onward' else ('',))]
def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case('turnover',c['history'],c['carrier'],c['route'],fine=c['fine'])
def source(c): return 'panel__'+c['history']+'__sham'+('__fine' if c['fine'] else '')
def stem(c): return 'p15:'+c['history']+':'+c['carrier']+':'+c['route']
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,i): return stem(c)+':replacement:%02d'%i
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def benchmark_ids(): return ['p15:readout:stock_E:%02d'%i for i in range(3)]
def draw_book(): return prior.draw_book()
def incoming(M,i): return prior.incoming(M,i)
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P15 configuration')
    return value
def execution_manifest():
    result=prior.execution_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result
def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text())
    a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=36 or not a['quality_gate'] or
        a['independent_check_count']!=18273 or a['integration_calls']!=288):
        raise ValueError('Unexpected P14 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json','panel_audit.json']
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]
    names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P14 input')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p14/'+n:PREDECESSOR/n for n in names}
