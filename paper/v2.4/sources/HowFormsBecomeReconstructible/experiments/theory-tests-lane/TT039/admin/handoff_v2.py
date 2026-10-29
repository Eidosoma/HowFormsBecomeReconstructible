"""Publish the recorded validator correction and separate qualification restart."""
from pathlib import Path
import os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

verify(read(ROOT/'QUEUE_HANDOFF.json')['files'])
plan=read(ROOT/'QUEUE_V2_PLAN.json');startup=read(ROOT/'QUEUE_V2_STARTUP_CHECK.json');launch=read(ROOT/'QUEUE_V2_LAUNCH.json')
preflight=read(ROOT/'checks/preflight_v2/COMPLETE.json');correction=read(ROOT/'corrections/metadata_timer_v1/CORRECTION.json')
assert startup['status']==preflight['status']=='PASS' and inputs()==plan['inputs'];verify(plan['evidence'])
assert correction['new_qualify_sha256']==sha(ROOT/'qualify.py');stamp=now()
message=f"""
[TT039 fresh late-writing confirmation](TT039/README.md): **the qualification
validator was corrected and a separate version-2 sequence is queued**.
Qualification v1 stopped at 2026-10-22T22:33:16 UTC because it required native
capture wall-clock durations to match between serial and two-worker runs.
Only that duration field differed in the common and residual capture metadata.
The diagnosis rehashed the three completed excluded block outputs and found
all **5,391 saved array pairs exactly identical**, with all other metadata
matching across 143 JSON pairs. No benchmark or confirmation case had started.

The correction permits only the named capture duration field to vary in those
two files, requires finite nonnegative durations, and retains exact comparison
of every other field and array. Tests reject altered RNG/hash metadata, invalid
timers and differences outside the two declared files. Only qualify.py changed
among 340 frozen input files; the numerical pipeline, protocol, source identities,
randomness and statistical rule are unchanged. All failed receipts, raw outputs
and prior handoff files are preserved. This is an explicit recorded correction,
not an automatic retry or a change following confirmation outcomes.

All **{len(preflight['checks'])} preflight groups passed** in {preflight['seconds']:.2f}
seconds. The detached version-2 controller (PID {launch['pid']}) acknowledged at
{launch['acknowledged_utc']}; its single startup check observed
**{startup['phase_at_single_startup_check']}** at {startup['recorded_utc']}.
It will repeat full qualification in qualification_v2, then benchmark once and
launch the same 64-block fresh confirmation only if validation and resource
limits pass. Two CPUs (6/7), one numerical thread each, remain assigned; there
is no automatic scientific polling, further retry, extension or successor.

The co-primary contrast remains late writing minus preservation: body credit at
1900 and packet credit in fresh 1000-update recipients. All four schedules,
cases, histories, masks and paired harms remain included. Joint confirmation
still requires both prespecified lower bounds to exceed zero; secondary panels
cannot rescue a failure. No fresh confirmation outcomes have been generated or
inspected. Historical root QUEUE_FAILED.json and qualification_v1/FAILED.json
remain failure evidence; current progress is in QUEUE_V2_STATUS.json and
CURRENT_EXECUTION.json.

See [diagnosis](TT039/corrections/metadata_timer_v1/DIAGNOSIS.json),
[correction](TT039/corrections/metadata_timer_v1/CORRECTION.json),
[protocol](TT039/PROTOCOL.md) and [current execution](TT039/CURRENT_EXECUTION.json).
"""
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
(ROOT/'README.md').write_text('# TT039 — fresh confirmation of late writing\n\n'+message.replace('(TT039/','(')+
    '\nThe original handoff is preserved in [the correction archive](corrections/metadata_timer_v1/PRIOR_FILES.json).\n')
with (PRIOR/'README.md').open('a') as f:
    f.write('\nTT039 qualification v1 stopped on a wall-clock metadata comparison bug before confirmation. Every saved array matched across serial and parallel runs. The narrow correction passed nine preflight groups, and a separate qualification_v2 is queued with unchanged scientific protocol. See [TT039 current execution](../TT039/CURRENT_EXECUTION.json).\n')
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt039-v2.pending');write(temp,value);os.replace(temp,path)
successor=dict(study='TT039',status_at_handoff='CORRECTED_PREFLIGHT_PASSED_QUALIFICATION_V2_QUEUED',
    observed_phase=startup['phase_at_single_startup_check'],observed_utc=startup['recorded_utc'],
    current_execution='TT039/CURRENT_EXECUTION.json',queue_plan='TT039/QUEUE_V2_PLAN.json',queue_pid=launch['pid'],
    qualification='TT039/checks/qualification_v2/COMPLETE.json',correction='TT039/corrections/metadata_timer_v1/CORRECTION.json',
    new_source_blocks=64,new_independent_receiving_draws=512,body_endpoint=END,recipient_endpoint=1000)
old=read(PRIOR/'CURRENT_EXECUTION.json');old.update(authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',old)
intake=read(LANE/'prediction_intake_status.json');intake['postwriting_body_followup']['authorized_successor']=successor
intake['fresh_late_writing_confirmation'].update(successor,preflight='TT039/checks/preflight_v2/COMPLETE.json',preflight_status='PASS',
    queue_startup='TT039/QUEUE_V2_STARTUP_CHECK.json',full_qualification_pending_at_handoff=True,
    failed_attempt='TT039/checks/qualification_v1/FAILED.json',failed_attempt_preserved=True,scientific_protocol_changed=False)
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT039',event='recorded_validator_correction_and_separate_qualification_v2_queued',recorded_utc=stamp,
        queue_plan_sha256=sha(ROOT/'QUEUE_V2_PLAN.json'),correction_sha256=sha(ROOT/'corrections/metadata_timer_v1/CORRECTION.json'),
        failed_attempt_preserved=True,numerical_pipeline_changed=False,protocol_changed=False,
        new_production_outcomes_generated=False,new_production_outcomes_inspected=False,automatic_retry=False,automatic_polling=False),sort_keys=True)+'\n')
bound=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT038/README.md','TT038/CURRENT_EXECUTION.json')]+[ROOT/n for n in (
    'README.md','QUEUE_V2_PLAN.json','QUEUE_V2_LAUNCH.json','QUEUE_V2_STARTUP_CHECK.json',
    'checks/preflight_v2/COMPLETE.json','checks/queue_controller_v2/COMPLETE.json',
    'corrections/metadata_timer_v1/DIAGNOSIS.json','corrections/metadata_timer_v1/CORRECTION.json',
    'corrections/metadata_timer_v1/PRIOR_FILES.json','corrections/metadata_timer_v1/PROCESS_CHECK.json','qualify.py',
    'admin/controller_v2.py','admin/check_queue_v2.py','admin/check_startup_v2.py','admin/preflight_v2.py','admin/handoff_v2.py')]
write(ROOT/'QUEUE_V2_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,observed_phase=startup['phase_at_single_startup_check'],
    failed_attempt_preserved=True,full_qualification_pending_at_handoff=True,current_state_is_asynchronous=True,
    new_production_outcomes_inspected=False,files={str(p):sha(p) for p in bound}))
verify(read(ROOT/'QUEUE_V2_HANDOFF.json')['files']);verify(plan['inputs'])
print(dict(status='PASS',handoff_files=len(bound),failed_attempt_preserved=True,automatic_result_polling=False))
