"""P16 registered turnover-rate screen and deterministic bounded follow-ups."""
import hashlib
import json
import paper_tissue_dependence_design as prior
from paper_tissue_dependence_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-tissue-dependence-20260919T132624Z-323q0waq'
STAGES=('baseline','screen','rna_controls','onward')
FOUNDERS=('written','ordinary','stock_E')
SCHEMES=('single','pair_center','pair_edge','wipe')
TAUS=(1,10,100,20000)
READOUTS=('open','rna','cut')
FIXED=dict(experiment='P16_turnover_limit',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=86400,verification_timeout_seconds=5400,
    maximum_cases=234,maximum_integrations=1056,founders=list(FOUNDERS),schemes=list(SCHEMES),
    intervals=list(TAUS),readouts=list(READOUTS),cycles=2,source_logical_time=1180000,
    source_route='actual__patch__open',source_phase='isolated_2',shape=[1,3],readout_shape=[2,3],
    incoming_draw_namespace='P16_turnover_limit_v1',incoming_seed=501,protein_percent=25,
    isolation_horizons=[10000,10000],readout_horizon=20000,no_turnover_horizon=120000,
    internal_power=60,readout_power=60,mirna_kd=1.25e-14,
    selection='fastest_shared_retention_both_resolutions_else_20000',
    clock=dict(method='native_explicit_euler_bounded_clock_v1',sample='min(100,H/20)',
               maximum_step='min(100,H/100)',fine_maximum_step_factor=.5),
    external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_TURNOVER_LIMIT_PROTOCOL.md',ROOT/'configs/paper_turnover_limit_v1.json',
    ROOT/'configs/paper_turnover_limit_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_turnover_limit_design.py','run_paper_turnover_limit.py',
    'analyze_paper_turnover_limit.py','run_paper_turnover_limit_detached.py','test_paper_turnover_limit.py')]

def case(stage='screen',founder='written',scheme='single',tau=1,route='open',readout='',fine=False):
    if stage=='baseline':
        scheme,tau,route=('capacity',0,'open') if readout else ('no_turn',20000,'open')
        if readout: founder='stock_E'
    parts=[stage,founder,scheme,str(tau),route]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
                scheme=scheme,tau=tau,route=route,readout=readout,fine=fine)
def stage_cases(stage,selection=None):
    if stage=='baseline':
        return [case(stage,readout=k,fine=f) for f in (False,True) for k in READOUTS]+[
            case(stage,h,fine=f) for f in (False,True) for h in FOUNDERS]
    if stage=='screen':
        return [case(stage,h,s,t,fine=f) for f in (False,True) for h in FOUNDERS for s in SCHEMES for t in TAUS]
    if stage not in STAGES or selection is None: raise ValueError('Missing registered P16 selection/stage')
    if set(selection)!=set(SCHEMES[:-1]) or any(x['tau'] not in TAUS or x['reason'] not in
            ('fastest_shared_retention','no_shared_retention') for x in selection.values()):
        raise ValueError('Invalid P16 selection')
    return [case(stage,h,s,selection[s]['tau'],r,k,f) for f in (False,True) for h in FOUNDERS
            for s in SCHEMES[:-1] for r in (('rna',) if stage=='rna_controls' else ('open','rna'))
            for k in (('',) if stage=='rna_controls' else READOUTS)]
def fixed_cases(selection=None):
    stages=STAGES if selection is not None else STAGES[:2]
    return [c for stage in stages for c in stage_cases(stage,selection)]
def select(by):
    result={}
    for s in SCHEMES[:-1]:
        qualifying=[t for t in TAUS if all(by.get(case('screen',h,s,t,fine=f)['id'],{}).get('retained_E') is True
            and by.get(case('screen',h,s,t,fine=f)['id'],{}).get('available') is True
            for h in FOUNDERS[:2] for f in (False,True))]
        result[s]=dict(tau=min(qualifying) if qualifying else 20000,
            reason='fastest_shared_retention' if qualifying else 'no_shared_retention')
    return result
def parent(c):
    return case('screen' if c['route']=='open' else 'rna_controls',c['founder'],c['scheme'],c['tau'],c['route'],fine=c['fine'])
def source(c): return 'onward__'+c['founder']+'__actual__patch__open'+('__fine' if c['fine'] else '')
def stem(c): return 'p16:%s:%s:%s:%s'%(c['founder'],c['scheme'],c['tau'],c['route'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def benchmark_ids(): return ['p16:readout:stock_E:%02d'%i for i in range(3)]
def schedule(scheme,tau):
    groups={'single':((0,),(1,),(2,)),'pair_center':((0,2),(1,)),
            'pair_edge':((0,1),(2,)),'wipe':((0,1,2),)}[scheme]
    return [dict(cycle=cycle,positions=list(g),horizon=len(g)*tau) for cycle in range(2) for g in groups]
def random_word(i):
    return int.from_bytes(hashlib.sha256(('P16_turnover_limit_v1|501|turnover|%d'%i).encode('ascii')).digest()[:8],'big')
def draw_book(): return {'501':{'turnover':['%016x'%random_word(i) for i in range(6)]}}
def incoming(M,cycle,pos):
    value=M.copy(); value[7,0]=M[7,0]*(1+(random_word(3*cycle+pos)*51//(1<<64)-25)/100)
    return value
def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P16 configuration')
    return value
def execution_manifest():
    result=prior.execution_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result
def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text()); a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=102 or not a['quality_gate'] or
        a['independent_check_count']!=24043 or a['integration_calls']!=354): raise ValueError('Unexpected P15 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]
    names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P15 input')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p15/'+n:PREDECESSOR/n for n in names}
