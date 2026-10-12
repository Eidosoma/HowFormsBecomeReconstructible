"""P17 actual first-replacement fork: isolated retention versus continued renewal."""
import json
import paper_turnover_limit_design as prior
from paper_turnover_limit_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-turnover-limit-20260919T213853Z-vji7f9zl'
STAGES=('baseline','prefix','forks','onward')
FOUNDERS=('written','ordinary','stock_E')
TAUS=(100,300,1000,3000,10000,20000)
ROUTES=('open','rna')
READOUTS=('open','rna','cut')
FIXED=dict(experiment='P17_renewal_maturation',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=86400,verification_timeout_seconds=7200,
    maximum_cases=312,maximum_integrations=1020,founders=list(FOUNDERS),intervals=list(TAUS),
    routes=list(ROUTES),readouts=list(READOUTS),arms=['isolate','renew'],cycles=2,
    source_logical_time=1180000,source_route='actual__patch__open',source_phase='isolated_2',
    shape=[1,3],readout_shape=[2,3],incoming_draw_namespace='P16_turnover_limit_v1',incoming_seed=501,
    protein_percent=25,isolation_horizons=[10000,10000],readout_horizon=20000,no_turnover_horizon=120000,
    power=60,mirna_kd=1.25e-14,selection='fastest_shared_renewal_and_preceding_grid_else_endpoints',
    clock=prior.FIXED['clock'],external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_RENEWAL_MATURATION_PROTOCOL.md',ROOT/'configs/paper_renewal_maturation_v1.json',
    ROOT/'configs/paper_renewal_maturation_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_renewal_maturation_design.py','run_paper_renewal_maturation.py',
    'analyze_paper_renewal_maturation.py','run_paper_renewal_maturation_detached.py','test_paper_renewal_maturation.py')]

def case(stage='prefix',founder='written',tau=100,route='open',arm='',readout='',fine=False):
    if stage=='baseline':
        route='open'
        if arm=='capacity': founder,tau='stock_E',0
        elif arm=='no_turn': tau=20000
        elif arm=='wipe': founder='stock_E'
    if stage=='prefix': arm=''
    if stage=='onward': arm='renew'
    parts=[stage,founder,str(tau),route]+[x for x in (arm,readout) if x]
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
                tau=tau,route=route,arm=arm,readout=readout,fine=fine)
def stage_cases(stage,selection=None):
    if stage=='baseline':
        return ([case(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
            [case(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
            [case(stage,tau=t,arm='wipe',fine=f) for f in (False,True) for t in TAUS])
    if stage in ('prefix','forks'):
        return [case(stage,h,t,r,arm,fine=f) for f in (False,True) for h in FOUNDERS for t in TAUS
                for r in ROUTES for arm in (('',) if stage=='prefix' else ('isolate','renew'))]
    if stage!='onward' or selection is None or selection.get('reason') not in (
            'shared_boundary','left_censored','no_shared_renewal'):
        raise ValueError('Missing registered P17 selection/stage')
    taus=selection['taus']
    if len(taus)!=2 or taus!=sorted(set(taus)) or any(t not in TAUS for t in taus):
        raise ValueError('Invalid P17 selection')
    return [case(stage,h,t,r,'renew',k,f) for f in (False,True) for h in FOUNDERS for t in taus for r in ROUTES for k in READOUTS]
def fixed_cases(selection=None):
    return [c for stage in (STAGES if selection is not None else STAGES[:3]) for c in stage_cases(stage,selection)]
def select(by):
    good=[t for t in TAUS if all(by.get(case('forks',h,t,'open','renew',fine=f)['id'],{}).get('retained_E') is True
        and by.get(case('forks',h,t,'open','renew',fine=f)['id'],{}).get('available') is True
        for h in FOUNDERS[:2] for f in (False,True))]
    if not good: return dict(taus=[100,20000],reason='no_shared_renewal')
    at=TAUS.index(min(good))
    return dict(taus=list(TAUS[at-1:at+1]) if at else [100,300],reason='shared_boundary' if at else 'left_censored')
def prefix(c): return case('prefix',c['founder'],c['tau'],c['route'],fine=c['fine'])
def parent(c): return case('forks',c['founder'],c['tau'],c['route'],'renew',fine=c['fine'])
def source(c): return 'onward__'+c['founder']+'__actual__patch__open'+('__fine' if c['fine'] else '')
def stem(c): return 'p17:%s:%s:%s'%(c['founder'],c['tau'],c['route'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def benchmark_ids(): return ['p17:readout:stock_E:%02d'%i for i in range(3)]
def draw_book(): return prior.draw_book()
def incoming(M,cycle,pos): return prior.incoming(M,cycle,pos)
def replay_source(c):
    if c['stage']=='baseline':
        if c['arm']=='capacity': return 'baseline__stock_E__capacity__0__open__'+c['readout']+('__fine' if c['fine'] else '')
        if c['arm']=='no_turn': return 'baseline__'+c['founder']+'__no_turn__20000__open'+('__fine' if c['fine'] else '')
        if c['tau'] in (100,20000): return 'screen__stock_E__wipe__%d__open'%c['tau']+('__fine' if c['fine'] else '')
    if c['stage']=='prefix' or (c['stage']=='forks' and c['arm']=='renew'):
        if c['route']=='open' and c['tau'] in (100,20000): stage='screen'
        elif c['route']=='rna' and c['tau']==20000: stage='rna_controls'
        else: return None
        return '%s__%s__single__%d__%s'%(stage,c['founder'],c['tau'],c['route'])+('__fine' if c['fine'] else '')
    return None
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P17 configuration')
    return value
def execution_manifest():
    result=prior.execution_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result
def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text()); a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=234 or not a['quality_gate'] or
        a['independent_check_count']!=70715 or a['integration_calls']!=1056): raise ValueError('Unexpected P16 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]; names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P16 input')
        names.append(row['id']+'/result.json'); names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p16/'+n:PREDECESSOR/n for n in names}
