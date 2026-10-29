"""Publish the qualified design and observed queue startup into the lane handoff."""
from pathlib import Path
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

prior=read(ROOT/'intake_inputs/MANIFEST.json')['files']
targets=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT035/README.md','TT035/CURRENT_EXECUTION.json')]
for path in targets:
    archived=prior[str(path)];assert sha(path)==archived['sha256']==sha(archived['snapshot'])
startup=read(ROOT/'QUEUE_STARTUP_CHECK.json');launch=read(ROOT/'QUEUE_LAUNCH.json');plan=read(ROOT/'QUEUE_PLAN.json')
qp=ROOT/'checks'/plan['qualification']/'COMPLETE.json';q=read(qp)
assert q['status']=='PASS' and startup['status']=='PASS' and inputs()==plan['inputs'];verify(plan['evidence']);stamp=now()
message=f"""
[TT036 fresh-cohort stopped-writing confirmation](TT036/README.md) is **implemented,
qualified and queued**, authorized after TT035. It reserves 64 new source blocks,
36000000–36000063. Parents, records, bodies, corruption and matched recipients
are newly generated. All three budgets (0, 100 and 1,000 writes) share the
1,000-update body endpoint. Four fresh recipient conditions per corruption
compare incoming and outgoing packets under matched birth and forcing noise.

The fixed co-primary comparison is 100 minus 1,000 writes, residual family,
own body, all masks, original target credit: terminal body and recipient
endpoints separately. Joint confirmation requires both one-sided paired-block
lower bounds above zero at alpha .025 each. Coverage is approximate; effect
sizes, pointwise intervals and conservative bounded sensitivity are retained.
Preservation, both families, every source/mask/history/message and all paired
harms remain visible. No optimal stopping time, uninterrupted body performance
or serial-heredity claim is tested. TT028 primary/joint remain NOT_CONFIRMED.

{len(q['checks'])} qualification groups passed in {q['seconds']:.2f} seconds,
including a {q['bridge_arrays']}-array bridge to the exposed TT028 source recipe,
full independent physical replays, exact serial/two-worker agreement, gate and
randomness checks, joint arithmetic and the registered inference path. The
bounded local identity search and RNG manifest passed; these do not establish
independent custody or blinding. Excluded outcomes are not confirmation data.

The detached controller (PID {launch['pid']}) acknowledged at
{launch['acknowledged_utc']}. Its single startup check observed
**{startup['phase_at_single_startup_check']}** at {startup['recorded_utc']}.
It may wait at most two hours for capacity, benchmark once, freeze a forecast
below 24 hours and launch on CPUs 6 and 7 with one numeric thread each. The
hard deadline is at most 48 hours, with a 32 GiB output cap. After one assay
startup check the controller exits. No automatic scientific polling, retry,
extension or successor. Production outcomes have not been inspected.

See [protocol](TT036/PROTOCOL.md), [qualification](TT036/checks/{plan['qualification']}/COMPLETE.json),
[queue plan](TT036/QUEUE_PLAN.json) and [current execution](TT036/CURRENT_EXECUTION.json).
"""
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
(ROOT/'README.md').write_text('# TT036 — fresh-cohort stopped writing\n\n'+message.replace('(TT036/','(')+
    '\nCompletion-bound predecessor documents are preserved in [the intake archive](intake_inputs/MANIFEST.json).\n')
with (PRIOR/'README.md').open('a') as f:f.write('\nAuthorized successor TT036 is qualified and queued for a fixed, fresh-cohort comparison of stopping at 100 versus 1,000 writes, with separate body and newly acquired recipient endpoints, preservation and all paired harms. See [TT036 execution](../TT036/CURRENT_EXECUTION.json). Prior completion-bound documents are preserved in [the TT036 intake archive](../TT036/intake_inputs/MANIFEST.json).\n')
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt036.pending');write(temp,value);os.replace(temp,path)
successor=dict(study='TT036',status_at_handoff='QUALIFIED_QUEUED',observed_phase=startup['phase_at_single_startup_check'],
    observed_utc=startup['recorded_utc'],current_execution='TT036/CURRENT_EXECUTION.json',queue_plan='TT036/QUEUE_PLAN.json',
    queue_pid=launch['pid'],new_source_blocks=64,new_independent_receiving_draws=True,body_endpoint=1000)
old=read(PRIOR/'CURRENT_EXECUTION.json');old.update(successor_started=True,authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',old)
intake=read(LANE/'prediction_intake_status.json')
intake['stopped_writing_body_endpoint'].update(authorized_successor=successor,successor_started=True)
intake['fresh_stopped_writing_confirmation']=dict(successor,qualification=f'TT036/checks/{plan["qualification"]}/COMPLETE.json',
    qualification_status='PASS',bridge_arrays=q['bridge_arrays'],queue_startup='TT036/QUEUE_STARTUP_CHECK.json',
    queue_startup_status='PASS',administrative_archive='TT036/intake_inputs/MANIFEST.json',source_population_exposed=False,
    joint_decision_pending=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT036',event='qualified_fresh_stopping_confirmation_queued',recorded_utc=stamp,
        queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),qualification_sha256=sha(qp),
        observed_phase=startup['phase_at_single_startup_check'],new_production_outcomes_inspected=False,
        fresh_reserved_blocks=list(BLOCKS),excluded_identities=list(EXCLUDED),exposed_bridge_identity=28000000,
        primary_fixed_before_production=True,automatic_polling=False),sort_keys=True)+'\n')
bound=targets+[ROOT/n for n in ('README.md','QUEUE_PLAN.json','QUEUE_LAUNCH.json','QUEUE_STARTUP_CHECK.json',
    f'checks/{plan["qualification"]}/COMPLETE.json','checks/queue_controller_v1/COMPLETE.json',
    'admin/controller.py','admin/check_queue.py','admin/check_startup.py','admin/handoff.py',
    'admin/qualify_counter_correction.py','admin/check_input_counter.py','checks/qualification_v2/CORRECTION.json','RESERVATION_REVIEW.json')]
write(ROOT/'QUEUE_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,observed_phase=startup['phase_at_single_startup_check'],
    archived_predecessor_files=len(prior),current_state_is_asynchronous=True,new_production_outcomes_inspected=False,
    files={str(p):sha(p) for p in bound}))
verify(read(ROOT/'QUEUE_HANDOFF.json')['files']);verify(plan['inputs'])
print(dict(status='PASS',handoff_files=len(bound),archived_predecessor_files=len(prior),automatic_result_polling=False))
