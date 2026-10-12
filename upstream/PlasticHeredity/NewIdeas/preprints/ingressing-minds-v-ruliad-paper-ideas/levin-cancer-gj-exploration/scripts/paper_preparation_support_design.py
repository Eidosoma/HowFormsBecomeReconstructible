"""P19: equal extra preparation with distinct coupling conditions."""
import json
import paper_preparation_turnover_design as prior
from paper_preparation_turnover_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-preparation-turnover-20260921T140509Z-dfvaunkc'
STAGES=('baseline','renewal','onward')
FOUNDERS=('written','ordinary','stock_E')
EXTRAS=(200,900)
MODES=('open','rna','isolated')
READOUTS=('open','rna','cut')
ANCHORS=(100,300,1000)
STORE=ROOT.__class__('/mnt/workspaces/levin-cancer-gj-exploration')
FIXED=dict(experiment='P19_preparation_support',revision=REVISION,workers=2,
    worker_timeout_seconds=21600,total_budget_seconds=108000,verification_timeout_seconds=7200,
    maximum_cases=192,maximum_integrations=870,founders=list(FOUNDERS),extra_intervals=list(EXTRAS),
    preparation_modes=list(MODES),readouts=list(READOUTS),reference_first_intervals=list(ANCHORS),
    first_interval=100,later_interval=300,source_logical_time=1180000,
    source_stage='P17_open_prefix',source_phase='replacement_01',shape=[1,3],readout_shape=[2,3],
    incoming_draw_namespace='P16_turnover_limit_v1',incoming_seed=501,protein_percent=25,
    isolation_horizons=[10000,10000],readout_horizon=20000,no_turnover_horizon=120000,
    power=60,mirna_kd=1.25e-14,clock=prior.FIXED['clock'],
    later_transport='open_for_every_preparation_mode',whole_trio_isolation_during_extra=True,
    archive_mode='hardlink_immutable_v1',predecessor_reaudit='original_once_plus_archive_integrity',
    external_store=str(STORE),minimum_free_gib=5,large_artifact_bytes=262144,
    external_schedule=True,automatic_follow_on=False,outcome_dependent_selection=False)
LOCAL_FILES=prior.LOCAL_FILES+[
    ROOT/'PAPER_PREPARATION_SUPPORT_PROTOCOL.md',ROOT/'configs/paper_preparation_support_v1.json',
    ROOT/'configs/paper_preparation_support_draws_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_preparation_support_design.py','run_paper_preparation_support.py',
    'analyze_paper_preparation_support.py','run_paper_preparation_support_detached.py','test_paper_preparation_support.py')]+[
    ROOT/'storage/relocate_artifacts.py',ROOT/'storage/artifact_storage_v2.py']

def case(stage='renewal',founder='written',extra=200,mode='open',arm='',first=100,readout='',fine=False):
    later=300
    if stage=='baseline':
        if arm=='capacity': founder,extra,mode,first,later='stock_E',0,'none',0,0
        elif arm=='no_turn': extra,mode,first,later=0,'none',20000,20000
        elif arm in ('reference','wipe_reference'):
            extra,mode=0,'none'
            if arm=='wipe_reference': founder='stock_E'
        elif arm=='wipe': founder,first='stock_E',100
    else: arm,first='prepared',100
    parts=[stage,founder,arm,str(first),str(later),str(extra),mode]+([readout] if readout else [])
    return dict(id='__'.join(parts)+('__fine' if fine else ''),stage=stage,founder=founder,
        extra=extra,mode=mode,arm=arm,first=first,later=later,route='open',readout=readout,fine=fine)

def stage_cases(stage):
    if stage=='baseline':
        return ([case(stage,arm='capacity',readout=k,fine=f) for f in (False,True) for k in READOUTS]+
            [case(stage,h,arm='no_turn',fine=f) for f in (False,True) for h in FOUNDERS]+
            [case(stage,h,arm='reference',first=t,fine=f) for f in (False,True) for h in FOUNDERS for t in ANCHORS]+
            [case(stage,arm='wipe_reference',first=t,fine=f) for f in (False,True) for t in ANCHORS]+
            [case(stage,extra=t,mode=m,arm='wipe',fine=f) for f in (False,True) for t in EXTRAS for m in MODES])
    if stage=='renewal':
        return [case(stage,h,t,m,fine=f) for f in (False,True) for h in FOUNDERS for t in EXTRAS for m in MODES]
    if stage=='onward':
        return [case(stage,h,t,m,readout=k,fine=f) for f in (False,True) for h in FOUNDERS for t in EXTRAS for m in MODES for k in READOUTS]
    raise ValueError('Unregistered P19 stage')

def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]
def parent(c): return case('renewal',c['founder'],c['extra'],c['mode'],fine=c['fine'])
def prefix_source(c): return 'prefix__%s__100__open'%c['founder']+('__fine' if c['fine'] else '')
def stem(c): return 'p19:%s:%s:%s:%s'%(c['founder'],c['arm'],c['extra'],c['mode'])
def stock_ids(c): return [stem(c)+':stock_E:%02d'%i for i in range(3)]
def new_id(c,cycle,pos): return stem(c)+':replacement:%d:%d'%(cycle,pos)
def pupils(c): return [stem(c)+':pupil:%02d'%i for i in range(3)]
def draw_book(): return prior.draw_book()
def incoming(M,cycle,pos): return prior.incoming(M,cycle,pos)
def duration(c): return 100+c['extra']+1500

def replay_case(c):
    if c['stage']!='baseline' or c['arm']=='wipe': return None
    if c['arm']=='reference': return prior.case('renewal',c['founder'],c['first'],300,'open',fine=c['fine'])
    return prior.case('baseline',c['founder'],c['first'],c['later'],'open',
        arm='wipe' if c['arm']=='wipe_reference' else c['arm'],readout=c['readout'],fine=c['fine'])
def replay_source(c):
    x=replay_case(c); return x['id'] if x else None

def validate_config(value):
    if value!=FIXED: raise ValueError('Unregistered P19 configuration')
    return value

def execution_manifest():
    result=prior.execution_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result

def input_paths():
    s=json.loads((PREDECESSOR/'summary.json').read_text()); a=json.loads((PREDECESSOR/'independent_audit.json').read_text())
    if (not s.get('all_execution_valid') or len(s['cases'])!=282 or not a['quality_gate'] or
        a['independent_check_count']!=104607 or a['integration_calls']!=1296): raise ValueError('Unexpected P18 predecessor')
    names=['summary.json','independent_audit.json','predecessor_audit.json']+[x+'_audit.json' for x in prior.STAGES]
    names+=['frozen/'+p.name for p in prior.LOCAL_FILES]; names+=['inputs/'+p for p in prior.input_paths()]
    for row in s['cases']:
        if not row['execution_pass'] or row['id']!=row['result']['case']['id']: raise ValueError('Invalid P18 input')
        names.append(row['id']+'/result.json'); names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names): raise ValueError('Invalid input paths')
    return {'p18/'+n:PREDECESSOR/n for n in names}
