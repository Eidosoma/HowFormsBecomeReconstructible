"""Registered P9: three continuously updated teachers, three fresh pupils."""
from paper_calibrated_rewrite_design import (ROOT,SOURCE,REVISION,digest,write_json,source_check,
    LOCAL_FILES as P8_FILES,execution_manifest as p8_manifest,input_paths as p8_inputs)

PREDECESSOR=ROOT/'runs/paper-calibrated-rewrite-20260912T212822Z-kg2pgq0w'
FOUNDERS=('rewritten_ordinary_E','rewritten_restored_E','ordinary_M')
CONDITIONS=('sequential','simultaneous_20','simultaneous_60','sequential_rna','sequential_cut')
FIXED=dict(revision=REVISION,workers=2,worker_timeout_seconds=14400,total_budget_seconds=43200,
    founders=list(FOUNDERS),conditions=list(CONDITIONS),sham_founder='ordinary_E_sham',
    algorithm='depol',power=60,kd=1.25e-14,teachers=3,pupils=3,maximum_rounds=6,
    contact_horizon=20000,round_horizon=80000,hold_horizons=[10000,10000],late_fraction=.95,
    stop_rule='first_incomplete_three_M_round',replay_cases=2,coarse_cases=16,fine_cases=16,
    planned_cases=34,minimum_integrations=188,maximum_integrations=1098,
    live_teacher_reuse=True,waiting_cells_evolve=True,external_handover_schedule=True,
    automatic_follow_on=False)
LOCAL_FILES=P8_FILES+[ROOT/'PAPER_STAGED_RELAY_PROTOCOL.md',ROOT/'configs/paper_staged_relay_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_staged_relay_design.py','run_paper_staged_relay.py',
        'analyze_paper_staged_relay.py','run_paper_staged_relay_detached.py','test_paper_staged_relay.py')]


def replay_source(layout):
    return dict(id=f'capacity__{layout}__depol__high__M_open',kind='capacity',layout=layout,
                algorithm='depol',anchor='high',condition='M_open',fine=False)


def fixed_cases():
    cases=[dict(id='replay__'+l,kind='replay',layout=l,source=replay_source(l)['id'],fine=False)
           for l in ('three_to_one','three_to_three')]
    for fine in (False,True):
        for founder,condition in [(h,c) for h in FOUNDERS for c in CONDITIONS]+[('ordinary_E_sham','sequential')]:
            cases.append(dict(id=f'relay__{founder}__{condition}'+('__fine' if fine else ''),
                              kind='relay',founder=founder,condition=condition,fine=fine))
    return cases


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered 34-case P9 design')
    return config


def execution_manifest():
    result=p8_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result


def input_paths():
    result={'p8/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json','age_gate.json')}
    result.update({'p8/inputs/'+n:PREDECESSOR/'inputs'/n for n in p8_inputs()})
    for history in ('ordinary_E','restored_E'):
        name='rewrite__'+history+'__M_open'
        names=['result.json']+[stage+'_'+phase+'.npz' for stage in ('writing','probe')
                              for phase in ('contact','isolated_1','isolated_2')]
        result.update({'p8/'+name+'/'+n:PREDECESSOR/name/n for n in names})
    return result
