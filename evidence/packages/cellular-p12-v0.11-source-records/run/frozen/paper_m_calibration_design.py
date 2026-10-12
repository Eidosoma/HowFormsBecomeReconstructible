"""Registered P7: two historical anchors and ordinary-M capacity calibration."""
from paper_rewrite_design import (ROOT, SOURCE, REVISION, digest, write_json, source_check,
    LOCAL_FILES as P6_FILES, execution_manifest as p6_manifest)

PREDECESSOR = ROOT/'runs/paper-rewrite-20260912T121215Z-971x3guc'
P3_SOURCE = ROOT/'runs/paper-sheet-20260909T210234Z-6u875ntn'
LAYOUTS = dict(three_to_three=([2,3],3,3), three_to_one=([2,2],3,1), six_to_three=([3,3],6,3))
KD = dict(low=8.801117367933935e-16, high=1.25e-14)
CONDITIONS = ('M_open','E_sham','M_rna','M_cut')
P3_CASE = dict(id='bank__depol__edge',kind='bank',history='depol',location='edge',blocked=False,fine=False)
P6_CASE = dict(id='assay__M',kind='assay',label='M',fine=False)
FIXED = dict(revision=REVISION,workers=2,worker_timeout_seconds=7200,total_budget_seconds=28800,
    layouts=list(LAYOUTS),algorithms=['depol','hypol'],kd_anchors=KD,conditions=list(CONDITIONS),
    contact_power=60,contact_horizon=20000,hold_horizons=[10000,10000],late_fraction=.95,
    replay_cases=2,coarse_cases=48,fine_cases=48,planned_cases=98,planned_integrations=295,
    serial_relay=False,midway_rewriting=False,stress_panel=False,automatic_follow_on=False)
LOCAL_FILES = P6_FILES + [ROOT/'PAPER_M_CALIBRATION_PROTOCOL.md',ROOT/'configs/paper_m_calibration_v1.json'] + [
    ROOT/'scripts'/n for n in ('paper_m_calibration_design.py','run_paper_m_calibration.py',
        'analyze_paper_m_calibration.py','run_paper_m_calibration_detached.py','test_paper_m_calibration.py')]


def fixed_cases():
    cases=[dict(id='replay__p3_M_acquisition',kind='replay',source='p3',fine=False),
           dict(id='replay__p6_M_failure',kind='replay',source='p6',fine=False)]
    cases += [dict(id=f'capacity__{layout}__{mode}__{anchor}__{condition}'+('__fine' if fine else ''),
        kind='capacity',layout=layout,algorithm=mode,anchor=anchor,condition=condition,fine=fine)
        for fine in (False,True) for layout in LAYOUTS for mode in ('depol','hypol')
        for anchor in KD for condition in CONDITIONS]
    return cases


def validate_config(config):
    if config != FIXED: raise ValueError('Not the registered 98-case P7 design')
    return config


def execution_manifest():
    result=p6_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    p3=['summary.json','independent_audit.json','gate.json','bank_gate.json',
        'reference/result.json','reference/preparation.npz','inputs/pilot/result.json','inputs/pilot/endpoints.npz']
    p3 += ['bank__depol__edge/'+n for n in ('result.json','preparation.npz','acquisition.npz',
                                         'acquired_isolated_1.npz','acquired_isolated_2.npz')]
    p6=['summary.json','independent_audit.json','gate.json',
        'inputs/p5/inputs/p4_inputs/reference/preparation.npz']
    p6 += ['assay__M/'+n for n in ('result.json','onward_contact.npz','onward_isolated_1.npz','onward_isolated_2.npz')]
    return {**{'p3/'+n:P3_SOURCE/n for n in p3},**{'p6/'+n:PREDECESSOR/n for n in p6}}
