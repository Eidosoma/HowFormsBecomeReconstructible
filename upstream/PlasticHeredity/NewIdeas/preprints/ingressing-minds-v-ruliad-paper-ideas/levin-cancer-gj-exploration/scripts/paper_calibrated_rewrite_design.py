"""Registered P8: calibrated six-cell cue, four E backgrounds, one fresh probe."""
from paper_m_calibration_design import (ROOT,SOURCE,REVISION,digest,write_json,source_check,
    LOCAL_FILES as P7_FILES,execution_manifest as p7_manifest,input_paths as p7_inputs)

PREDECESSOR=ROOT/'runs/paper-m-calibration-20260912T181247Z-hj82p5cg'
LINEAGE_SOURCE=ROOT/'runs/paper-relay-20260911T150113Z-b8woml1d'
BACKGROUNDS=('fresh_E','aged_E','ordinary_E','restored_E')
CONDITIONS=('M_open','E_sham','M_write_rna','M_write_cut','no_cue','M_probe_rna','M_probe_cut')
LAYOUTS=('six_to_three','three_to_one','three_to_three')
FIXED=dict(revision=REVISION,workers=2,worker_timeout_seconds=7200,total_budget_seconds=28800,
    backgrounds=list(BACKGROUNDS),conditions=list(CONDITIONS),algorithm='depol',power=60,kd=1.25e-14,
    writing_shape=[3,3],cue_cells=6,targets=3,probe_shape=[2,2],probe_recipients=1,
    contact_horizon=20000,hold_horizons=[10000,10000],age_horizons=[20000,10000,10000],late_fraction=.95,
    historical_lineage_round=6,replay_cases=3,age_cases=2,coarse_rewrite_cases=28,fine_rewrite_cases=28,
    fine_comparisons=29,planned_cases=61,planned_integrations=351,
    serial_relay=False,stress_panel=False,automatic_follow_on=False)
LOCAL_FILES=P7_FILES+[ROOT/'PAPER_CALIBRATED_REWRITE_PROTOCOL.md',ROOT/'configs/paper_calibrated_rewrite_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_calibrated_rewrite_design.py','run_paper_calibrated_rewrite.py',
        'analyze_paper_calibrated_rewrite.py','run_paper_calibrated_rewrite_detached.py','test_paper_calibrated_rewrite.py')]


def replay_source(layout):
    return dict(id=f'capacity__{layout}__depol__high__M_open',kind='capacity',layout=layout,
                algorithm='depol',anchor='high',condition='M_open',fine=False)


def fixed_cases():
    cases=[dict(id='replay__'+l,kind='replay',layout=l,source=replay_source(l)['id'],fine=False) for l in LAYOUTS]
    cases += [dict(id='age__E'+('__fine' if f else ''),kind='age',fine=f) for f in (False,True)]
    cases += [dict(id=f'rewrite__{h}__{c}'+('__fine' if f else ''),kind='rewrite',background=h,condition=c,fine=f)
              for f in (False,True) for h in BACKGROUNDS for c in CONDITIONS]
    return cases


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered 61-case P8 design')
    return config


def execution_manifest():
    result=p7_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result


def input_paths():
    result={'p7/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json')}
    result.update({'p7/inputs/'+n:PREDECESSOR/'inputs'/n for n in p7_inputs()})
    for layout in LAYOUTS:
        case=replay_source(layout)['id']
        result.update({'p7/'+case+'/'+n:PREDECESSOR/case/n for n in ('result.json','contact.npz','isolated_1.npz','isolated_2.npz')})
    result.update({'p5/'+n:LINEAGE_SOURCE/n for n in ('summary.json','independent_audit.json','gate.json',
        'inputs/p4_inputs/reference/preparation.npz')})
    for h in ('ordinary_E','restored_E'):
        name='relay__'+h+'__open'
        result.update({'p5/'+name+'/'+n:LINEAGE_SOURCE/name/n for n in ('result.json','r05_isolated_2.npz',
            'r06_contact.npz','r06_isolated_1.npz','r06_isolated_2.npz')})
    return result
