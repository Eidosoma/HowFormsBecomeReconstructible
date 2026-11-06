"""One startup check and lane handoff without inspecting production outcomes."""
from pathlib import Path
import sys,os,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

def replace_file(p,value):
 p=Path(p);tmp=p.with_name(p.name+'.handoff-pending');write(tmp,value);tmp.replace(p)

def main():
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 launch=read(ROOT/'QUEUE_LAUNCH.json');pre=read(ROOT/'checks/preflight_v2/COMPLETE.json')
 assert launch['status']=='DETACHED_STARTED' and pre['status']=='PASS' and pre['inputs']==inputs()
 age=(datetime.now(timezone.utc)-datetime.fromisoformat(launch['acknowledged_utc'])).total_seconds()
 if age<15:time.sleep(15-age)
 pid=launch['pid'];proc=Path('/proc')/str(pid)
 assert proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[0] not in ('Z','X')
 assert os.getpgid(pid)==pid and os.sched_getaffinity(pid)=={6,7} and not (ROOT/'QUEUE_FAILED.json').exists()
 current=read(ROOT/'QUEUE_STATUS.json');assert current['phase'] in ('QUALIFICATION_RUNNING','QUALIFIED','PRODUCTION_RUNNING')
 value=dict(status='PASS',recorded_utc=now(),controller_pid=pid,phase_at_observation=current['phase'],
  single_startup_check=True,scientific_results_inspected=False,automatic_polling=False)
 write(ROOT/'STARTUP_PERSISTENCE_CHECK.json',value)
 # Retain any live documents replaced by this handoff, outside frozen intake.
 old=ROOT/'launch_handoff_inputs';old.mkdir(exist_ok=False);archived={}
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl'):
  p=LANE/name;target=old/name;shutil.copyfile(p,target);assert sha(p)==sha(target)
  archived[str(p)]=dict(archive=str(target),sha256=sha(target))
 write(old/'MANIFEST.json',archived)
 report=f'''# TT048 — mixed unmarked corruption and abstaining repair

TT048 is launched as a bounded one-read development study on two single-thread
CPUs. The single startup check passed at {value['recorded_utc']}, observed phase
**{current['phase']}**. Excluded preflight passed in {pre['seconds']:.1f} seconds.
Full qualification is forecast at {pre['qualification_forecast_seconds']/60:.1f}
minutes. It must pass exact serial/parallel replay and resource admission before
the controller freezes and starts production. No production effects have been read.

This follows the user's review of [TT014's frozen repair](../TT014/PROTOCOL.md).
That rule fills exact zeros while preserving every nonzero weight. TT048 tests
whether ordinary graph and optimizer repairs help when nonzero values can also
be misleading. Eight existing TT014 blocks retain all 128 records, including
initial failures, with two blocks from each writing history. These are exposed
source records; four new matched recipient futures per record do not make the
source population prospectively fresh.

Eight input panels retain original records, added missing edges, sign errors,
mixed unmarked weak replacements/sign errors/magnitude changes, an actual
opposite-acquired-history transplant, balanced aligned and wrong-task controls,
and erasure. The synthetic balanced pair has identical support/magnitudes and
zero pinned graph inconsistency. Control labels are isolated from repair.

Six arms compare preservation, unchanged TT014 completion, a maximum spanning
forest, the fixed multi-start optimizer, and selective versions of both new
repairs. Their abstention action returns the current input unchanged. All cases
remain in unconditional intended- and opposite-task outcomes and paired harm
tables. Coverage, edit/no-change decisions and performance among eligible cases
are reported separately. Physical edit budgets and computational work remain visible.

Structural eligibility is an uncalibrated fixed rule, not confidence that the
record has the right historical identity. Every algorithm result retains
**history UNVERIFIED**. An internally consistent wrong record can pass structural
checks; preflight verifies that failure mode rather than declaring consistency
to be correctness. Identical packet bytes with different hidden historical labels
must yield identical record-only repair actions. A trusted external anchor would
be a separate information resource, absent from this study.

Preflight independently checks graph/optimizer construction, corruption, packet
edits, abstention, all paired counts and Monte Carlo errors. Both native reader
implementations agree byte for byte on the excluded assays, and scalar raw-window
scores agree. Original zero-fill results reproduce TT014 exactly. The initial
preflight failed a numerical test fixture: rounded weights gave a disagreement
fraction .049999999999999996 rather than exactly .05. The fixed rule correctly
accepted it, but the fixture's equality assertion failed. Dyadic weights now test
the exact boundary. The initial failure, code and diagnostic correction remain
under [corrections](corrections/threshold_fixture_v1/CORRECTION.json); no scientific
rule changed and no receiving assay had begun before that correction.

Production uses 24,576 packet/future contexts, with both cues in each, and full
independent native replay. The study cap is 1 GiB with a 4 GiB free reserve;
runtime forecast must remain below six hours. Long work stays detached after
one startup check, with no automatic polling, retry, extension or serial successor.
The archive continues independently, and TT047's interrupted experiment is not
restarted by TT048. See [protocol](PROTOCOL.md), [current state](CURRENT_EXECUTION.json)
and [source bindings](SOURCE_MANIFEST.json).
'''
 (ROOT/'README.md').write_text(report)
 brief=f'''

[TT048 mixed unmarked corruption](TT048/README.md) is launched following the
reviewer-directed extension of TT014. Excluded preflight passed; the single
startup observation at {value['recorded_utc']} found phase {current['phase']}.
Full qualification and measured resource/runtime admission precede production.

Eight exposed TT014 blocks (all 128 records, balanced across four histories)
receive eight fixed input conditions, including unmarked mixed corruption,
an actual opposite-history transplant and exactly balanced wrong-task controls.
Preservation and TT014 zero-fill are compared with a spanning-forest repair,
the fixed multi-start optimizer and abstaining versions of both. Four new
receiving futures are paired across every arm and regime. All paired harms,
opposite-task successes, margins, coverage and selected/unconditional outcomes
remain. No new-source confirmation or serial claim is made.

Abstention preserves the original input bytes. Structural eligibility is not
historical correctness: every output has history UNVERIFIED, and coherent wrong
controls can pass the structural gate. Preflight checks this limit, exact
native replay and original TT014 completion. A rounded numerical boundary
fixture was corrected before any receiving assay; its failure and old code
are preserved. The scientific 5% rule is unchanged.

Two single-thread workers, a 1 GiB cap and a 4 GiB reserve bound this one-read
pilot. No automatic polling, retry, extension or serial successor follows.
TT047 recovery remains separate, as does the requested dataset archive.
'''
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
  with (LANE/name).open('a') as f:f.write(brief)
 intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=now()
 intake['unmarked_corruption_repair_development']=dict(study='TT048',status='LAUNCHED',protocol='TT048/PROTOCOL.md',
  current_execution='TT048/CURRENT_EXECUTION.json',report='TT048/README.md',phase_at_startup=current['phase'],blocks=BLOCKS,
  source_population_exposed=True,new_recipient_futures=4,graph_comparator=True,explicit_abstention=True,
  coherent_wrong_controls=True,history_always_unverified=True,scientific_results_inspected=False,automatic_polling=False,automatic_successor=False)
 replace_file(LANE/'prediction_intake_status.json',intake)
 with (LANE/'exposure_register.jsonl').open('a') as f:
  f.write(json.dumps(dict(recorded_utc=now(),study='TT048',event='launched_fixed_one_read_development',blocks=BLOCKS,
   source_population_exposed=True,selection='two fixed ordered blocks per history',production_results_inspected=False,
   graph_comparator=True,explicit_abstention=True,automatic_successor=False),sort_keys=True)+'\n')
 files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl')]
 files += [ROOT/n for n in ('README.md','PROTOCOL.md','SOURCE_MANIFEST.json','SEEDS.json','PLANNING_EXPOSURE.json','QUEUE_PLAN.json',
  'QUEUE_LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json','checks/preflight_v2/COMPLETE.json','PREFLIGHT_FAILED.json',
  'PREFLIGHT_RESOURCE.json','PREFLIGHT_V2_RESOURCE.json','preflight_v1.log','preflight_v2.log','admin/handoff.py',
  'launch_handoff_inputs/MANIFEST.json','corrections/threshold_fixture_v1/CORRECTION.json')]
 write(ROOT/'LAUNCH_HANDOFF.json',dict(status='PASS',recorded_utc=now(),files={str(p):sha(p) for p in files},
  previous_documents_preserved=True,scientific_results_inspected=False,automatic_polling=False))
 verify(read(ROOT/'LAUNCH_HANDOFF.json')['files']);verify(pre['inputs'])
 print(json.dumps(dict(status='PASS',phase_at_startup=current['phase'],bound_files=len(files),scientific_results_inspected=False)))

if __name__=='__main__':main()
