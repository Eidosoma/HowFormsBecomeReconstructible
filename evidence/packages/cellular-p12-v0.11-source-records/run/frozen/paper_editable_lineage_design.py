"""P11: fresh bounded-clock writing, three M handovers, E rewriting, three E handovers."""
import json
import paper_contact_clock_recovery_design as prior
from paper_contact_clock_recovery_design import ROOT,SOURCE,REVISION,digest,write_json,source_check

PREDECESSOR=ROOT/'runs/paper-contact-clock-recovery-20260914T113138Z-rvzg2jra'
GRAPH=prior.GRAPH
HISTORIES=('written','ordinary')
STAGES=('stocks','calibration','before','rewrite','after')
FIXED=dict(experiment='P11_editable_lineage',revision=REVISION,workers=2,
    worker_timeout_seconds=14400,total_budget_seconds=64800,verification_timeout_seconds=1800,
    algorithm='depol',power=60,kd=1.25e-14,graph=[list(e) for e in GRAPH],
    preparation_horizon=1000,writing_shape=[3,3],cue_cells=6,carrier_cells=3,
    writing_horizon=20000,hold_horizons=[10000,10000],late_fraction=.95,
    schedule='sequential',contact_window=80000,round_horizon=100000,
    before_rounds=3,after_rounds=3,clock=prior.CLOCK,
    stage_case_totals=[2,22,34,54,74],maximum_cases=74,maximum_integrations=722,
    all_new_integrations_bounded=True,historical_endpoint_used_as_founder=False,
    independent_random_replicates=False,external_schedule=True,automatic_follow_on=False)
LOCAL_FILES=prior.LOCAL_FILES+[ROOT/'PAPER_EDITABLE_LINEAGE_PROTOCOL.md',ROOT/'configs/paper_editable_lineage_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_editable_lineage_design.py','run_paper_editable_lineage.py',
        'analyze_paper_editable_lineage.py','run_paper_editable_lineage_detached.py','test_paper_editable_lineage.py')]


def case(kind,condition='',history='',fine=False,route=''):
    fields=[kind]+([history] if history else [])+([condition] if condition else [])+([route] if route else [])
    return dict(id='__'.join(fields)+('__fine' if fine else ''),kind=kind,condition=condition,
                history=history,fine=fine,route=route)


def stage_cases(stage):
    result=[]
    for f in (False,True):
        if stage=='stocks': result.append(case('stock',fine=f))
        elif stage=='calibration':
            result += [case('write_M',c,fine=f) for c in ('M_open','E_sham','M_rna','M_cut','no_cue')]
            result.append(case('age_M',fine=f))
            result += [case('calibration_E',c,fine=f) for c in ('E_open','E_rna','E_cut','M_sham')]
        elif stage=='before':
            result += [case('before',history=h,fine=f,route=r) for h in HISTORIES for r in ('open','rna','cut')]
        elif stage=='rewrite':
            result += [case('rewrite_E',c,h,f) for h in HISTORIES for c in ('E_open','M_sham','E_rna','E_cut','no_cue')]
        elif stage=='after':
            result += [case('after',w,h,f,r) for h in HISTORIES for w,r in
                       (('E_open','open'),('E_open','rna'),('E_open','cut'),('M_sham','open'),('no_cue','open'))]
        else: raise ValueError('Unknown P11 stage')
    return result


def fixed_cases(): return [c for stage in STAGES for c in stage_cases(stage)]


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered conditional 2-74 case P11 design')
    return config


def execution_manifest():
    result=prior.execution_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    summary=json.loads((PREDECESSOR/'summary.json').read_text())
    if not summary.get('all_execution_valid') or len(summary['cases'])!=96 or summary['selected']!=['sequential','overlap_50']:
        raise ValueError('Unexpected P10R predecessor')
    names=['summary.json','independent_audit.json','gate.json','calibration_audit.json',
           'screen_audit.json','clock_probe_audit.json','failed_attempt_audit.json']
    names += ['frozen/'+p.name for p in prior.LOCAL_FILES]
    names += ['inputs/'+n for n in prior.input_paths()]
    for row in summary['cases']:
        if row['id']!=row['result']['case']['id'] or not row['execution_pass']:
            raise ValueError('Invalid predecessor case')
        names.append(row['id']+'/result.json')
        names += [row['id']+'/'+p['phase']+'.npz' for p in row['result']['phases']]
    if len(names)!=len(set(names)) or any('..' in n.split('/') for n in names):
        raise ValueError('Invalid archived input names')
    return {'p10r/'+n:PREDECESSOR/n for n in names}


def source_case(c):
    f=c['fine']; kind=c['kind']
    if kind=='before':
        return case('write_M','M_open',fine=f)['id'] if c['history']=='written' else case('age_M',fine=f)['id']
    if kind=='rewrite_E': return case('before',history=c['history'],fine=f,route='open')['id']
    if kind=='after': return case('rewrite_E',c['condition'],c['history'],f)['id']
    return case('stock',fine=f)['id']


def source_phase(c):
    if c['kind']=='before': return 'writing_isolated_2' if c['history']=='written' else 'age_isolated_2'
    if c['kind']=='rewrite_E': return 'r03_isolated_2'
    if c['kind']=='after': return 'writing_isolated_2'
    return 'preparation'


def founder_ids(history):
    return [f'p11:{history}:founder:{i:02d}' for i in range(3)]


def pupil_ids(c,n):
    tag='calibration' if c['kind']=='calibration_E' else c['kind']+':'+c['history']
    return [f'p11:{tag}:pupil:{n:02d}:{i:02d}' for i in range(3)]


def target_ids(c):
    if c['kind']=='rewrite_E':
        return pupil_ids(case('before',history=c['history']),3)
    return founder_ids('ordinary' if c['kind']=='age_M' else 'written')

