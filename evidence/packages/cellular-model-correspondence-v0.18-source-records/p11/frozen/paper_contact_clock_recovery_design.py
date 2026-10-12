"""P10R: full same-design rerun with bounded numerical clocks; P10 stays failed."""
import paper_contact_schedule_design as p10
from paper_contact_schedule_design import (ROOT,SOURCE,REVISION,PREDECESSOR,LINEAGE,GRAPH,FOUNDERS,SCHEDULES,
    PRIORITY,digest,write_json,source_check,make_case,continuation_cases,segments,replay_source)

FAILED_ATTEMPT=ROOT/'runs/paper-contact-schedule-20260913T212804Z-22if1sgx'
PROBES=(('rewritten_restored_E','simultaneous','open'),('ordinary_M','simultaneous','open'),
    ('rewritten_restored_E','sequential','cut'),('ordinary_M','sequential','cut'),
    ('rewritten_restored_E','overlap_50','open'),('ordinary_M','overlap_50','open'))
CLOCK=dict(method='native_explicit_euler_bounded_clock_v1',sample_interval=100,
    coarse_max_step=100,fine_max_step=50,initial_and_final_samples=True,integer_tick_clock=True)
FIXED=dict(p10.FIXED,experiment='P10R_clock_recovery',clock=CLOCK,verification_timeout_seconds=1800,
    failed_attempt=FAILED_ATTEMPT.name,clock_probe_cases=12,minimum_cases=22,screened_cases=72,maximum_cases=96,
    minimum_integrations=54,screen_prefix_integrations=390,maximum_integrations=1230,
    diagnostic_sources=[make_case('screen',h,s,r)['id'] for h,s,r in PROBES],
    failed_screen_endpoints_used_for_selection=False,all_new_phases_use_bounded_clock=True)
LOCAL_FILES=p10.LOCAL_FILES+[ROOT/'PAPER_CONTACT_CLOCK_RECOVERY_PROTOCOL.md',ROOT/'configs/paper_contact_clock_recovery_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_contact_clock_recovery_design.py','paper_bounded_clock.py',
        'run_paper_contact_clock_recovery.py','analyze_paper_contact_clock_recovery.py',
        'run_paper_contact_clock_recovery_detached.py','test_paper_contact_clock_recovery.py')]


def probe_cases():
    cases=[]
    for fine in (False,True):
        for h,s,r in PROBES:
            case=make_case('clock_probe',h,s,r,fine); case['source']=make_case('screen',h,s,r)['id']
            cases.append(case)
    return cases


def fixed_cases():
    old=p10.fixed_cases()
    return old[:2]+probe_cases()+old[2:]


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered conditional 22-96 case P10R recovery')
    return config


def execution_manifest():
    result=p10.execution_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result


def input_paths():
    result=p10.input_paths()
    result.update({'failed_attempt/'+n:FAILED_ATTEMPT/n for n in
                   ('summary.json','gate.json','calibration_audit.json','screen_audit.json')})
    result.update({'failed_attempt/inputs/'+n:FAILED_ATTEMPT/'inputs'/n for n in p10.input_paths()})
    result.update({'failed_attempt/frozen/'+p.name:FAILED_ATTEMPT/'frozen'/p.name for p in p10.LOCAL_FILES})
    for c in p10.fixed_cases():
        names=['contact','isolated_1','isolated_2'] if c['kind']=='replay' else [
            f'r01_segment_{i:02d}' for i in range(1,len(segments(c['schedule']))+1)]+['r01_isolated_1','r01_isolated_2']
        for name in ['result.json']+[n+'.npz' for n in names]:
            result['failed_attempt/'+c['id']+'/'+name]=FAILED_ATTEMPT/c['id']/name
    return result
