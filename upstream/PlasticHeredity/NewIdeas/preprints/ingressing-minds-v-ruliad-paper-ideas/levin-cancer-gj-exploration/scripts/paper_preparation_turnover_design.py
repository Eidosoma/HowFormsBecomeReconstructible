"""P18 fixed factorial of initial preparation and subsequent turnover."""
import json
import paper_renewal_maturation_design as prior
from paper_renewal_maturation_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-renewal-maturation-20260920T160219Z-zayh7z05'
STAGES=('baseline','renewal','onward')
FOUNDERS=('written','ordinary','stock_E')
TIMES=(100,300,1000)
ROUTES=('open','rna')
READOUTS=('open','rna','cut')
ONWARD=((100,100),(100,300),(300,300),(1000,100))
FIXED=dict(experiment='P18_preparation_turnover',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=108000,verification_timeout_seconds=7200,
    maximum_cases=282,maximum_integrations=1296,founders=list(FOUNDERS),first_intervals=list(TIMES),
    later_intervals=list(TIMES),routes=list(ROUTES),readouts=list(READOUTS),
    onward_schedules=[list(x) for x in ONWARD],cycles=2,source_logical_time=1180000,
    source_stage='P17_prefix',source_phase='replacement_01',shape=[1,3],readout_shape=[2,3],
    incoming_draw_namespace='P16_turnover_limit_v1',incoming_seed=501,protein_percent=25,
    isolation_horizons=[10000,10000],readout_horizon=20000,no_turnover_horizon=120000,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],
    archive_mode='hardlink_immutable_v1',predecessor_reaudit='original_once_plus_archive_integrity',
    external_schedule=True,automatic_follow_on=False,outcome_dependent_selection=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_PREPARATION_TURNOVER_PROTOCOL.md',ROOT/'configs/paper_preparation_turnover_v1.json',
    ROOT/'configs/paper_preparation_turnover_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_preparation_turnover_design.py','run_paper_preparation_turnover.py',
    'analyze_paper_preparation_turnover.py','run_paper_preparation_turnover_detached.py','test_paper_preparation_turnover.py')]

def case(stage='renewal',founder='written',first=100,later=100,route='open',arm='',readout='',fine=False):
    if stage=='baseline':
        route='open'
        if arm=='capacity': founder,first,later='stock_E',0,0
        elif arm=='no_turn': first=later=20000
        elif arm=='wipe': founder='stock_E'
    else: arm='renew'
    parts=[stage,founder,str(first),str(later),route]+[x for x in (arm,readout) if x]
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
                first=first,later=later,route=route,arm=arm,readout=readout,fine=fine)

def stage_cases(stage):
    if stage=='baseline':
        return ([case(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
            [case(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
            [case(stage,first=u,later=v,arm='wipe',fine=f) for f in (False,True) for u in TIMES for v in TIMES])
    if stage=='renewal':
        return [case(stage,h,u,v,r,fine=f) for f in (False,True) for h in FOUNDERS for u in TIMES for v in TIMES for r in ROUTES]
    if stage=='onward':
        return [case(stage,h,u,v,r,readout=k,fine=f) for f in (False,True) for h in FOUNDERS for u,v in ONWARD for r in ROUTES for k in READOUTS]
    raise ValueError('Unregistered P18 stage')

def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case('renewal',c['founder'],c['first'],c['later'],c['route'],fine=c['fine'])
def prefix_source(c): return 'prefix__%s__%d__%s'%(c['founder'],c['first'],c['route'])+('__fine' if c['fine'] else '')
def stem(c): return 'p18:%s:%s:%s:%s'%(c['founder'],c['first'],c['later'],c['route'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def benchmark_ids(): return ['p18:readout:stock_E:%02d'%i for i in range(3)]
def draw_book(): return prior.draw_book()
def incoming(M,cycle,pos): return prior.incoming(M,cycle,pos)
def duration(c): return c['first']+5*c['later']

def replay_source(c):
    suffix='__fine' if c['fine'] else ''
    if c['stage']=='baseline':
        if c['arm']=='capacity': return 'baseline__stock_E__0__open__capacity__'+c['readout']+suffix
        if c['arm']=='no_turn': return 'baseline__%s__20000__open__no_turn'%c['founder']+suffix
        if c['first']==c['later']: return 'baseline__stock_E__%d__open__wipe'%c['first']+suffix
    elif c['first']==c['later']:
        if c['stage']=='renewal': return 'forks__%s__%d__%s__renew'%(c['founder'],c['first'],c['route'])+suffix
        return 'onward__%s__%d__%s__renew__%s'%(c['founder'],c['first'],c['route'],c['readout'])+suffix
    return None

def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P18 configuration')
    return value

def execution_manifest():
    result=prior.execution_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result

def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text()); a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=312 or not a['quality_gate'] or
        a['independent_check_count']!=75638 or a['integration_calls']!=1020): raise ValueError('Unexpected P17 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]; names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P17 input')
        names.append(row['id']+'/result.json'); names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p17/'+n:PREDECESSOR/n for n in names}
