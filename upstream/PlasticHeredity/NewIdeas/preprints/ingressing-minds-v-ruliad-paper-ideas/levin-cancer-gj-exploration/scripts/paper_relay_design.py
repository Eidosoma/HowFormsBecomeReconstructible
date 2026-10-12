"""Fixed P5 repeated 2D handovers from actual P4 recipients."""
from paper_topology_design import (ROOT,SOURCE,REVISION,digest,write_json,source_check,
    LOCAL_FILES as P4_FILES,execution_manifest as p4_manifest,input_paths as p4_inputs)

PREDECESSOR=ROOT/'runs/paper-topology-20260910T135736Z-_g47fgl8'
ANCESTRIES=('ordinary_E','ordinary_M','restored_E','failed_M')
ROUTES=('open','rna_blocked','border_cut')
FIXED=dict(revision=REVISION,workers=2,worker_timeout_seconds=7200,total_budget_seconds=28800,
    total_rounds=12,historical_rounds=1,new_rounds=11,carriers=3,recipients=3,
    contact_shape=[2,3],hold_shape=[1,3],contact_horizon=20000,hold_horizons=[10000,10000],
    contact_algorithm='hypol',hold_algorithm='depol',power=1,kd=1.25e-14,late_fraction=.95,
    ancestries=list(ANCESTRIES),routes=list(ROUTES),gate_cases=4,main_lineages=4,
    coarse_controls=8,fine_cases=12,planned_cases=28,planned_integrations=804,
    planned_continuation_rounds=264,midway_rewriting=False,stress_panel=False)
LOCAL_FILES=P4_FILES+[ROOT/'PAPER_RELAY_PROTOCOL.md',ROOT/'configs/paper_relay_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_relay_design.py','run_paper_relay.py',
        'analyze_paper_relay.py','run_paper_relay_detached.py','test_paper_relay.py')]


def fixed_cases():
    cases=[dict(id='replay__'+h,kind='replay',ancestry=h,source='capacity__'+h,
                route='open',fine=False) for h in ANCESTRIES]
    cases += [dict(id=f'relay__{h}__{route}'+('__fine' if fine else ''),
                   kind='relay',ancestry=h,source='capacity__'+h,route=route,fine=fine)
              for fine in (False,True) for h in ANCESTRIES for route in ROUTES]
    return cases


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered 28-case P5 design')
    return config


def execution_manifest():
    result=p4_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    paths={'p4/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json')}
    paths.update({'p4_inputs/'+name:PREDECESSOR/'inputs'/name for name in p4_inputs()})
    for h in ANCESTRIES:
        for name in ('result.json','onward_contact.npz','onward_isolated_1.npz','onward_isolated_2.npz'):
            folder='capacity__'+h; paths[folder+'/'+name]=PREDECESSOR/folder/name
    return paths

