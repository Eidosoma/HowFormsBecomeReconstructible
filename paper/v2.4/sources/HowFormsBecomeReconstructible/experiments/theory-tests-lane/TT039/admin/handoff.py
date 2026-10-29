"""Publish preflight and the observed detached qualification startup."""
from pathlib import Path
import os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

prior=read(ROOT/'intake_inputs/MANIFEST.json')['files']
targets=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT038/README.md','TT038/CURRENT_EXECUTION.json')]
for p in targets:
    entry=prior[str(p)];assert sha(p)==entry['sha256']==sha(entry['snapshot'])
startup=read(ROOT/'QUEUE_STARTUP_CHECK.json');launch=read(ROOT/'QUEUE_LAUNCH.json');plan=read(ROOT/'QUEUE_PLAN.json')
qp=ROOT/'checks/preflight_v1/COMPLETE.json';q=read(qp)
assert startup['status']==q['status']=='PASS' and inputs()==plan['inputs'];verify(plan['evidence'])
reservation=read(ROOT/'RESERVATION_REVIEW.json');rng=read(ROOT/'RANDOMNESS.json')
assert reservation['status']=='PASS_NO_IDENTITY_COLLISION' and reservation['reservation_sha256']==sha(ROOT/'RESERVATION.json')
assert rng['status']=='PASS' and not rng['production_random_samples_generated'];stamp=now()
message=f"""
[TT039 fresh confirmation of late writing](TT039/README.md) is **implemented,
preflight checked and queued for full qualification**, following the user's
acceptance of the TT038 successor proposal. This is a new confirmation cohort:
64 reserved identities, 39010000–39010063. New parents, captured packets,
developed bodies, corruptions and recipient conditions are generated after the
measured freeze. Existing production records and outcomes are not reused.

Source capture/development retain the audited 1000-update recipe. Experimental
bodies run to 1900 under preservation, early 1–100, late 901–1000 and full
1–1000 writing. All arms have writing off after 1000. The fixed primary contrast
is late minus preservation, residual family, own source, all masks equally
weighted, original-target fractional credit. Two co-primary outcomes are body
credit at 1900 and outgoing-record credit in new 1000-update recipients. Four
receiving conditions per corruption give 512 new matched environments across
the 64 blocks. Both families, all masks, body sources, histories and credits,
all six arm contrasts and all paired harms remain retained.

Joint confirmation requires both one-sided paired-block Student-t lower bounds
to exceed zero, alpha .025 each / Bonferroni family alpha .05. Coverage is
approximate, with a zero-variance bounded fallback and bounded sensitivity.
Other schedules, timepoints and secondary panels cannot rescue a failed primary
decision. All source blocks remain enrolled; there is no interim scientific
inspection, optional stopping or cohort extension. The 64-block size is fixed
without a power guarantee or practical-effect threshold.

The bounded local identity and RNG checks found no reuse within their declared
scope. They provide neither independent custody nor a global non-use proof.
{len(q['checks'])} preflight groups passed in {q['seconds']:.2f} seconds, including
analytic gains/harms and joint-decision fixtures and one excluded synthetic
1900-update body plus 1000-update recipient with independent physical replay.
Full qualification remains a separate required stage. It checks both excluded
blocks, all schedules/masks/sources, fresh source generation, exact prior source
and schedule bridges, serial/two-worker equality, raw physical replays and saved
analysis/report roundtrips. No new confirmation outcomes have been generated.

The host-detached controller (PID {launch['pid']}) acknowledged at
{launch['acknowledged_utc']}; its single startup observation found
**{startup['phase_at_single_startup_check']}** at {startup['recorded_utc']}.
It may wait cumulatively two hours for capacity, run full qualification once
(1800-second limit), benchmark once (600-second limit), freeze measured inputs
and resources, and launch production only after all preceding checks pass.
Production uses two CPUs, 6/7, one numerical thread each; forecast must be below
24 hours, output below 32 GiB, reserve at least 8 GiB, and hard deadline twice
forecast capped at 48 hours. The controller checks production persistence once
and exits. No automatic scientific polling, retry, extension or successor.

TT039 tests joint average benefit of this fixed schedule in the stated source
population. It does not establish individual benefit, optimal timing, continuous
performance, indefinite stability, independent teaching cues, damage-level
robustness or serial heredity. TT028 primary/joint and TT036 confirmation remain
unchanged. See [protocol](TT039/PROTOCOL.md), [preflight](TT039/checks/preflight_v1/COMPLETE.json),
[queue plan](TT039/QUEUE_PLAN.json) and [current execution](TT039/CURRENT_EXECUTION.json).
"""
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
with (ROOT/'README.md').open('x') as f:
    f.write('# TT039 — fresh confirmation of late writing\n\n'+message.replace('(TT039/','(')+
        '\nCompletion-bound predecessor documents are preserved in [the intake archive](intake_inputs/MANIFEST.json).\n')
with (PRIOR/'README.md').open('a') as f:
    f.write('\nAuthorized successor TT039 has passed preflight and is queued for detached full qualification, benchmark and conditional production. It tests late writing versus preservation on 64 new source blocks, with body at 1900 and fresh-recipient packet credit as co-primary outcomes, retaining all four schedules and paired harms. See [TT039 execution](../TT039/CURRENT_EXECUTION.json). Prior completion-bound documents are preserved in [the TT039 intake archive](../TT039/intake_inputs/MANIFEST.json).\n')
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt039.pending');write(temp,value);os.replace(temp,path)
successor=dict(study='TT039',status_at_handoff='PREFLIGHT_PASSED_QUALIFICATION_QUEUED',observed_phase=startup['phase_at_single_startup_check'],
    observed_utc=startup['recorded_utc'],current_execution='TT039/CURRENT_EXECUTION.json',queue_plan='TT039/QUEUE_PLAN.json',
    queue_pid=launch['pid'],new_source_blocks=64,new_independent_receiving_draws=512,body_endpoint=END,recipient_endpoint=1000)
old=read(PRIOR/'CURRENT_EXECUTION.json');old.update(successor_started=True,authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',old)
intake=read(LANE/'prediction_intake_status.json');intake['postwriting_body_followup'].update(authorized_successor=successor,successor_started=True)
intake['fresh_late_writing_confirmation']=dict(successor,preflight='TT039/checks/preflight_v1/COMPLETE.json',preflight_status='PASS',
    qualification='TT039/checks/'+plan['qualification']+'/COMPLETE.json',full_qualification_pending_at_handoff=True,
    queue_startup='TT039/QUEUE_STARTUP_CHECK.json',queue_startup_status='PASS',administrative_archive='TT039/intake_inputs/MANIFEST.json',
    source_population_exposed=False,primary='late minus preservation; body at 1900 and fresh recipient co-primary',
    new_production_outcomes_inspected=False,automatic_polling=False,automatic_retry=False,automatic_successor=False)
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT039',event='fresh_late_confirmation_preflight_passed_qualification_queued',recorded_utc=stamp,
        queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),preflight_sha256=sha(qp),reservation_sha256=sha(ROOT/'RESERVATION.json'),
        observed_phase=startup['phase_at_single_startup_check'],source_population_exposed=False,new_production_outcomes_generated=False,
        new_production_outcomes_inspected=False,planned_new_source_blocks=64,planned_new_independent_receiving_draws=512,
        body_checkpoints=SNAPSHOTS,automatic_polling=False),sort_keys=True)+'\n')
bound=targets+[ROOT/n for n in ('README.md','QUEUE_PLAN.json','QUEUE_LAUNCH.json','QUEUE_STARTUP_CHECK.json',
    'checks/preflight_v1/COMPLETE.json','checks/queue_controller_v1/COMPLETE.json','RESERVATION_REVIEW.json',
    'admin/controller.py','admin/check_queue.py','admin/check_startup.py','admin/preflight.py','admin/handoff.py')]
write(ROOT/'QUEUE_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,observed_phase=startup['phase_at_single_startup_check'],
    archived_predecessor_files=len(prior),current_state_is_asynchronous=True,full_qualification_pending_at_handoff=True,
    new_production_outcomes_inspected=False,files={str(p):sha(p) for p in bound}))
verify(read(ROOT/'QUEUE_HANDOFF.json')['files']);verify(plan['inputs'])
print(dict(status='PASS',handoff_files=len(bound),archived_predecessor_files=len(prior),automatic_result_polling=False))
