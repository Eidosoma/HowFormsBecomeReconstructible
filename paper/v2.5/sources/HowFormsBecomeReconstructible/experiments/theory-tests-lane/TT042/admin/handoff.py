"""Publish the launch and preserve previous administrative bindings."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
def replace_file(p,value):
 p=Path(p);tmp=p.with_name(p.name+'.tt042-pending');write(tmp,value);tmp.replace(p)
def main():
 startup=read(ROOT/'STARTUP_PERSISTENCE_CHECK.json');launch=read(ROOT/'QUEUE_LAUNCH.json');q=read(ROOT/'checks/preflight_v1/COMPLETE.json')
 assert startup['status']==q['status']=='PASS' and launch['status']=='DETACHED_STARTED'
 assert startup['phase_at_observation']=='QUALIFICATION_RUNNING'
 # The intake contains every old handoff binding before any of these edits.
 archived=read(ROOT/'intake_inputs/MANIFEST.json')
 for name,v in archived.items():assert sha(v['archive'])==v['sha256']
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl','TT041/README.md','TT041/CURRENT_EXECUTION.json'):
  p=LANE/name;assert sha(p)==archived[str(p)]['sha256'],p
 text='''# TT042 — exchange packets between saved body states

TT042 is launched as one detached two-CPU sequence. At the single startup
observation it was running full excluded qualification; production had not
started. The dynamic status is [QUEUE_STATUS.json](QUEUE_STATUS.json).
No scientific results have been inspected. There is no automatic polling.

The experiment restores TT040 at update 1000 and crosses two saved body states
(V, ema and R from preservation or late writing) with two saved packets
(preserved or late-written theta). All four combinations continue to 1900
with writing off and the original matched random forcing. This tests whether
later body effects depend on the packet, the other state fields, or their
interaction. It does not separate V, ema and R from one another.

All four exposed source blocks, three mixtures, both families, every injury
mask, own/foreign/neutral body sources, source positions and histories remain.
The focus is the half-mixed residual-family own-source target endpoint at 1900,
with intact and fully replaced panels alongside. Retain both conditional packet
effects, both conditional body effects, their interaction, the total contrast,
both ordered decompositions and all paired gains, harms and ties. The four
blocks are the population units. This is development, not fresh confirmation.

The unchanged combinations must reproduce TT040 exactly. Every continuation
also receives independent reference replay. The small excluded preflight
passed in 11.493 seconds: 88 full-from-start control arrays and 80 resumed
arrays matched, with arithmetic, mask weights, mutation, malformed-context and
RNG-offset checks passing. The full excluded phase repeats the entire design
on two excluded blocks and compares a fixed context against the serial
preflight exactly before production can start.

Recipient evidence is inherited from the actual TT040 reads, checked against
the packet bytes and matched environments. The packet remains fixed, so changing
only the saved body does not create a new packet or new recipient assay. This
study adds body continuations, not new receiving futures or capacity estimates.

The controller runs excluded qualification/benchmark once, freezes a measured
runtime and output forecast if qualified, admits resources again, then runs
the authorized production exchange once. It stops on failure and retains all
evidence. No retry, extension or successor is automatic. The controller does
not interpret production outcomes; review waits for the user's status request.
See [protocol](PROTOCOL.md), [execution](EXECUTION.md), [launch](QUEUE_LAUNCH.json)
and [startup check](STARTUP_PERSISTENCE_CHECK.json).
'''
 with (ROOT/'README.md').open('x') as f:f.write(text)
 execution=f'''# TT042 execution

Detached controller PID {launch['pid']} acknowledged at {launch['acknowledged_utc']}.
The one persistence check passed at {startup['recorded_utc']}, with both normal-
priority single-thread workers on CPUs 6 and 7. No subsequent polling is planned.
The phase at that observation was QUALIFICATION_RUNNING.

The excluded qualification/benchmark has a fixed 1800-second deadline.
After it passes, production forecast = 3 times its measured duration + 60
seconds, covering two block pairs with allowance. Require forecast below four
hours and projected total study output below 1 GiB. Production deadline is twice
the forecast, at least 600 seconds; the free-space reserve is 4 GiB. These limits
are not runtime estimates. The measured forecast will be retained in FREEZE.json.

Capacity admission occurs once before each phase and fails closed. The project
ceiling is 12 CPUs. Both phases run inside this detached session. Durable phase
and completion records are written without automatic result polling. No retries,
extensions or successor runs are authorized by this controller. Full production
results require later review, even if the controller reports completion.

All source states and diagonal outcomes were already exposed in TT040/TT041.
No new off-diagonal production outcomes existed at protocol/preflight freeze.
All previous handoff bindings are retained in intake_inputs/MANIFEST.json.
'''
 with (ROOT/'EXECUTION.md').open('x') as f:f.write(execution)
 old=read(PRIOR/'CURRENT_EXECUTION.json');old['successor_started']=True
 old['authorized_successor']=dict(study='TT042',status='DETACHED_SEQUENCE_STARTED',path='TT042/README.md',observed_utc=startup['recorded_utc'])
 replace_file(PRIOR/'CURRENT_EXECUTION.json',old)
 with (PRIOR/'README.md').open('a') as f:f.write('\n\nThe user authorized the proposed exchange test. [TT042](../TT042/README.md) now\nsupersedes the no-successor status above: its detached qualification and\nconditional production sequence is launched. TT041 scientific findings and\nfrozen artifacts are unchanged.\n')
 brief='''

[TT042 packet/body-state exchange](TT042/README.md) is launched as a detached
two-CPU sequence. The small excluded preflight passed exact full-from-start
controls, resumed reference replay and arithmetic checks. At the single startup
observation the full excluded qualification was running; production had not
started. Passing qualification and a bounded measured forecast trigger the
authorized four-block exchange once. It restores preservation/late V, ema and R
at 1000 and crosses them with preserved/late packets, then holds writing off
through 1900 under the original matched forcing. All cases, mixtures, controls
and paired harms remain. Recipient evidence is inherited from the same TT040
packets, with no new receiving assays. This is exposed development and changes
no previous scientific classification. There is no automatic result polling,
retry, extension or successor. Dynamic phase: TT042/QUEUE_STATUS.json.
'''
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
  with (LANE/name).open('a') as f:f.write(brief)
 intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=now()
 intake['body_packet_exchange_development']=dict(study='TT042',status_at_handoff='DETACHED_SEQUENCE_STARTED',
  observed_phase=startup['phase_at_observation'],observed_utc=startup['recorded_utc'],controller_pid=launch['pid'],
  dynamic_status='TT042/QUEUE_STATUS.json',current_execution='TT042/CURRENT_EXECUTION.json',protocol='TT042/PROTOCOL.md',
  preflight='TT042/checks/preflight_v1/COMPLETE.json',preflight_status='PASS',full_qualification_pending_at_handoff=True,
  source_blocks=BLOCKS,source_population_exposed=True,new_production_outcomes_inspected=False,production_started_at_observation=False,
  new_receiving_assays=0,recipient_evidence_inherited=True,confirmatory=False,all_cases_and_paired_harms_retained=True,
  automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
 intake['informative_packet_change_diagnosis']['successor_started']=True
 intake['informative_packet_change_diagnosis']['authorized_successor']='TT042 detached qualification and conditional production'
 replace_file(LANE/'prediction_intake_status.json',intake)
 event=dict(recorded_utc=now(),study='TT042',event='authorized_detached_exchange_sequence_launched',
  source_population_exposed=True,source_blocks=BLOCKS,full_qualification_pending_at_handoff=True,
  new_production_outcomes_inspected=False,new_receiving_assays=0,confirmatory=False,all_cases_retained=True,
  previous_classifications_unchanged=True,automatic_polling=False,automatic_successor=False)
 with (LANE/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(event,sort_keys=True)+'\n')
 files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl',
  'TT041/README.md','TT041/CURRENT_EXECUTION.json')]
 files += [ROOT/n for n in ('README.md','EXECUTION.md','QUEUE_PLAN.json','QUEUE_LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json',
  'checks/preflight_v1/COMPLETE.json','intake_inputs/MANIFEST.json','admin/handoff.py','admin/check_startup.py')]
 write(ROOT/'LAUNCH_HANDOFF.json',dict(status='PASS',recorded_utc=now(),files={str(p):sha(p) for p in files},
  phase_at_startup_observation=startup['phase_at_observation'],dynamic_status_not_hash_bound='TT042/QUEUE_STATUS.json',
  confirmatory=False,scientific_results_inspected=False,automatic_polling=False))
 print(json.dumps(dict(status='PASS',bound_files=len(files),dynamic_status='TT042/QUEUE_STATUS.json')))
if __name__=='__main__':main()
