"""Record the authorized detached development sequence without polling outcomes."""
from pathlib import Path
import os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

preflight=read(ROOT/'checks/preflight_v1/COMPLETE.json')
assert preflight['status']=='PASS' and preflight['inputs']==inputs()
launch=read(ROOT/'QUEUE_LAUNCH.json');startup=read(ROOT/'QUEUE_STARTUP_CHECK.json')
assert launch['status']=='QUEUED' and startup['status']=='PASS'
assert startup['pid']==launch['pid'] and not startup['science_results_inspected']
assert not (ROOT/'QUEUE_FAILED.json').exists()
archive=read(ROOT/'intake_inputs/MANIFEST.json')
for path,entry in archive['files'].items():assert sha(entry['snapshot'])==entry['sha256']
stamp=now();observed=startup['latest_queue_state'];phase=observed['phase']
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt040-handoff.pending');write(temp,value);os.replace(temp,path)

message=f"""
[TT040 writing timing with informative and damaged packets](TT040/README.md)
is **implemented, preflight checked and queued for detached qualification**
following the user's acceptance of the next development experiment.
The fixed cohort is four exposed TT039 blocks: 39010000, 39010016, 39010032 and
39010048, selected by identity rather than outcome. Source states are restored
from TT039; new body and recipient outcomes will be generated after the measured
production freeze. This is development evidence, not another confirmation.

Compare intact packets, equal-amplitude original/noise mixtures, and complete
replacement, using the same noise across mixture weights. Half mixing is not
a claim that half the information was erased. Preserve no writing, early
1-100, late 901-1000 and full 1-1000, followed by holding all packets through
body update 1900. All masks, both families, own/foreign/neutral sources,
histories and paired harms remain. Four new 1000-update receiving conditions
per block compare actual incoming and outgoing records with matched birth and
forcing. The damage levels share those conditions: 16 new receiving environments
in total, not 48. Intact preservation equals the original packet byte for byte.

The primary descriptive contrast is late minus preservation for half-mixed
residual packets with own source and all masks. Body and recipient scores stay
separate; intact and fully replaced panels cannot be pooled to hide a loss.
All four block values, six arm contrasts, four recognition credits and gains,
harms and ties remain. There is no significance gate, absence-of-harm claim,
outcome-based case selection or automatic cohort extension.

All **{len(preflight['checks'])} preflight groups passed** in
{preflight['seconds']:.2f} seconds, including independent mixture reconstruction,
damage-join and invalid-input rejection, and three full-duration excluded late
writers with paired fresh readers and independent physical replay. The detached
controller acknowledged at {launch['acknowledged_utc']} (PID {launch['pid']});
the single startup observation found **{phase}** at {startup['recorded_utc']}.

Full qualification (3600-second limit) precedes one excluded benchmark
(1800-second limit). Only passing checks and a measured forecast below 12 hours,
production output below 4 GiB and a 4 GiB free reserve permit the fixed four-block
run. The controller can wait cumulatively two hours for capacity. It uses two
normal-priority single-thread workers on CPUs 6/7 within the shared 12-CPU ceiling,
checks production startup once, then exits. No scientific polling, automatic
retry, extension or successor. No new production outcomes have been inspected.
TT028 primary/joint and TT036/TT039 confirmations are unchanged.

See [protocol](TT040/PROTOCOL.md), [preflight](TT040/checks/preflight_v1/COMPLETE.json),
[queue plan](TT040/QUEUE_PLAN.json) and [current state](TT040/CURRENT_EXECUTION.json).
"""
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
(ROOT/'README.md').write_text('# TT040 — writing timing across packet damage\n\n'+message.replace('(TT040/','(')+
    '\nPrior handoff-bound documents are preserved in [the intake archive](intake_inputs/MANIFEST.json).\n')
successor=dict(study='TT040',status_at_handoff='PREFLIGHT_PASSED_QUALIFICATION_QUEUED',
    current_execution='TT040/CURRENT_EXECUTION.json',queue_plan='TT040/QUEUE_PLAN.json',queue_pid=launch['pid'],
    observed_phase=phase,observed_utc=startup['recorded_utc'],reused_source_blocks=BLOCKS,
    source_population_exposed=True,confirmatory=False,damage_levels=DAMAGE,
    body_endpoint=1900,recipient_endpoint=1000,new_independent_receiving_draws=16,
    qualification='TT040/checks/qualification_v1/COMPLETE.json')
with (PRIOR/'README.md').open('a') as f:
    f.write('\nAuthorized successor TT040 is preflight checked and queued for detached qualification: four exposed source blocks, three packet mixtures, all four writing schedules, matched fresh recipients and retained harms. TT039 confirmation is unchanged. See [TT040 current state](../TT040/CURRENT_EXECUTION.json). Prior handoff-bound documents are preserved in the TT040 intake archive.\n')
predecessor=read(PRIOR/'CURRENT_EXECUTION.json')
predecessor.update(authorized_successor=successor,successor_started=True,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',predecessor)
intake=read(LANE/'prediction_intake_status.json')
intake['fresh_late_writing_confirmation']['authorized_successor']=successor
intake['fresh_late_writing_confirmation']['successor_started']=True
intake['packet_integrity_timing_development']=dict(successor,preflight='TT040/checks/preflight_v1/COMPLETE.json',
    preflight_status='PASS',full_qualification_pending_at_handoff=True,new_production_outcomes_inspected=False,
    administrative_archive='TT040/intake_inputs/MANIFEST.json',all_cases_and_paired_harms_retained=True,
    automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT040',event='packet_integrity_timing_development_implemented_and_queued',recorded_utc=stamp,
        protocol_sha256=sha(ROOT/'PROTOCOL.md'),preflight_sha256=sha(ROOT/'checks/preflight_v1/COMPLETE.json'),
        queue_plan_sha256=sha(ROOT/'QUEUE_PLAN.json'),source_population_exposed=True,source_population_reused=True,
        reused_source_blocks=BLOCKS,block_selection='every sixteenth TT039 identity, not outcomes',
        new_production_outcomes_inspected=False,confirmatory=False,automatic_successor=False),sort_keys=True)+'\n')
paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT039/README.md','TT039/CURRENT_EXECUTION.json')]+[ROOT/n for n in (
    'README.md','QUEUE_PLAN.json','QUEUE_LAUNCH.json','QUEUE_STARTUP_CHECK.json','checks/preflight_v1/COMPLETE.json',
    'checks/queue_controller_v1/COMPLETE.json','admin/controller.py','admin/check_queue.py','admin/check_startup.py',
    'admin/preflight_v1.py','admin/handoff.py')]
write(ROOT/'QUEUE_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,observed_phase=phase,
    files={str(p):sha(p) for p in paths},current_state_is_asynchronous=True,
    full_qualification_pending_at_handoff=True,new_production_outcomes_inspected=False))
verify(read(ROOT/'QUEUE_HANDOFF.json')['files']);assert inputs()==preflight['inputs']
print(dict(status='QUEUED_HANDOFF_PASS',bound_files=len(paths),observed_phase=phase,
    production_results_inspected=False,automatic_result_polling=False))
