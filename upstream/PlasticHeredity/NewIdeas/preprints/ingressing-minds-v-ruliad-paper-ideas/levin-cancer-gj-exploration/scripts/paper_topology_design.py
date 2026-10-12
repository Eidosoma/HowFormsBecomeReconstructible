"""Registered P4 paired topology/connection interventions."""
from paper_sheet_design import (ROOT,SOURCE,REVISION,digest,write_json,source_check,
    LOCAL_FILES as P3_FILES,execution_manifest as p3_manifest)

PREDECESSOR=ROOT/'runs/paper-sheet-20260909T210234Z-6u875ntn'
STRATEGIES={'neither':('depol',60),'voltage':('hypol',60),'expression':('depol',1),'both':('hypol',1)}
FIXED=dict(revision=REVISION,workers=2,worker_timeout_seconds=7200,total_budget_seconds=57600,
    field_shape=[13,13],histories=['depol','nbrDepol','hypol'],destinations=['edge','centre'],
    patch_sides=[2,3],voltage_modes=['depol','hypol'],internal_powers=[1,60],boundary_powers=[1,60],
    helper_power=60,kd=1.25e-14,contact_horizon=20000,hold_horizons=[10000,10000],late_fraction=.95,
    gate_cases=6,main_cases=96,planned_cases=146,planned_integrations=858,serial_relay_rounds=0)
LOCAL_FILES=P3_FILES+[ROOT/'PAPER_TOPOLOGY_PROTOCOL.md',ROOT/'configs/paper_topology_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_topology_design.py','run_paper_topology.py',
        'analyze_paper_topology.py','run_paper_topology_detached.py','test_paper_topology.py')]


def fixed_cases():
    cases=[]
    def add(kind,hist,loc,n,algo,inner,border,helper=60,fine=False,source=None,ident=None):
        name=f'{kind}__{hist}__{loc}__s{n}__{algo}__i{inner}__b{border}'+('__fine' if fine else '')
        cases.append(dict(id=ident or name,kind=kind,history=hist,location=loc,side=n,algorithm=algo,
            internal=inner,boundary=border,helper=helper,fine=fine,bank=f'bank__{hist}__edge',source=source))
    for strategy,(algo,power) in STRATEGIES.items():
        add('replay','depol','edge',3,algo,power,power,power,
            source=f'main__depol__edge__s3__{strategy}',ident='replay__'+strategy)
    cases += [dict(id='assay__'+label,kind='assay',label=label,source='assay__'+label,fine=False) for label in 'EM']
    for h in FIXED['histories']:
        for l in FIXED['destinations']:
            for n in (2,3):
                for v in ('depol','hypol'):
                    for i in (1,60):
                        for b in (1,60): add('main',h,l,n,v,i,b)
    for h in FIXED['histories']:
        for l in FIXED['destinations']:
            for v in ('depol','hypol'): add('helper',h,l,3,v,1,1,1)
    for kind in ('blocked','cut'):
        for h in FIXED['histories']:
            for l in FIXED['destinations']: add(kind,h,l,3,'depol',60,60)
    for l in FIXED['destinations']:
        for v in ('depol','hypol'):
            for i in (1,60):
                for b in (1,60): add('main','depol',l,3,v,i,b,fine=True)
    cases += [dict(id='capacity__'+label,kind='capacity',label=label,source=source,fine=False) for label,source in (
        ('ordinary_E','reference'),('ordinary_M','reference'),
        ('restored_E','main__depol__edge__s3__both'),('failed_M','main__depol__edge__s3__expression'))]
    return cases


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered 146-case P4 design')
    return config


def execution_manifest():
    result=p3_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result


def input_paths():
    paths={n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json','bank_gate.json')}
    def include(folder,names):
        for n in names: paths[folder+'/'+n]=PREDECESSOR/folder/n
    include('reference',['result.json','preparation.npz'])
    for h in FIXED['histories']:
        include(f'bank__{h}__edge',['result.json','preparation.npz','acquisition.npz',
                                  'acquired_isolated_1.npz','acquired_isolated_2.npz'])
    for strategy in STRATEGIES:
        include(f'main__depol__edge__s3__{strategy}',['result.json','restoration.npz','isolated_1.npz',
            'isolated_2.npz','onward_contact.npz','onward_isolated_1.npz','onward_isolated_2.npz'])
    for label in 'EM':
        include('assay__'+label,['result.json','onward_contact.npz','onward_isolated_1.npz','onward_isolated_2.npz'])
    return paths


def block(row,col,side,cols=13):
    return [(row+r)*cols+col+c for r in range(side) for c in range(side)]
