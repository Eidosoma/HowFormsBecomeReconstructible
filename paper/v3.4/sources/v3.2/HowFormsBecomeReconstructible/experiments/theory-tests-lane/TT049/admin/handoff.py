"""One startup check, preserved handoff, no production result inspection."""
from pathlib import Path
import os,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from study import *

def main():
 assert len(list(Path('/proc').glob('[0-9]*')))>16
 launch=read(ROOT/'QUEUE_LAUNCH.json');pre=read(ROOT/'checks/preflight_v1/COMPLETE.json')
 assert launch['status']=='DETACHED_STARTED' and pre['status']=='PASS' and pre['inputs']==inputs()
 age=(datetime.now(timezone.utc)-datetime.fromisoformat(launch['acknowledged_utc'])).total_seconds()
 if age<15:time.sleep(15-age)
 pid=launch['pid'];proc=Path('/proc')/str(pid)
 assert proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[0] not in ('Z','X')
 assert os.getpgid(pid)==pid and os.sched_getaffinity(pid)=={6,7} and not (ROOT/'QUEUE_FAILED.json').exists()
 current=read(ROOT/'QUEUE_STATUS.json');assert current['phase'] in ('QUALIFICATION_RUNNING','QUALIFIED','PRODUCTION_RUNNING')
 stamp=now();write(ROOT/'STARTUP_PERSISTENCE_CHECK.json',dict(status='PASS',recorded_utc=stamp,controller_pid=pid,
  phase_at_observation=current['phase'],single_startup_check=True,scientific_results_inspected=False,automatic_polling=False))
 prior=ROOT/'launch_handoff_inputs';prior.mkdir(exist_ok=False);copies={}
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl'):
  source=LANE/name;target=prior/name;shutil.copyfile(source,target);assert sha(source)==sha(target)
  copies[str(source)]=dict(copy=str(target),sha256=sha(target))
 write(prior/'MANIFEST.json',copies)
 (ROOT/'README.md').write_text(f'''# TT049 — fresh one-read graph screen test

TT049 is launched on two normal-priority, single-thread CPUs. The single startup
check passed at {stamp}, observing **{current['phase']}**. Excluded preflight
passed in {pre['seconds']:.1f} seconds. Full qualification must pass before any
new production source is generated. No production effects have been inspected.

The fixed cohort is 32 new source blocks, eight per writing history, containing
all 512 generation-14 records. Sources are newly taught and rebuilt through
14 generations under a new namespace, with full independent native replay.
Initial failures remain enrolled. The repair itself is a one-read intervention;
this is not serial continuation of repaired records.

Three paired arms preserve the input, always apply the maximum-weight graph
repair, or apply it only when the two output patches have opposite nonzero
majority signs. The screen receives only packet-derived information. The fixed
opposite-output task family is supplied; the historical orientation is not.
Every historical status remains UNVERIFIED.

Four new matched receiving futures per record retain all eight TT048 input
regimes, including original records, missing edges, sign flips, mixed unmarked
damage, actual opposite-history donors, balanced aligned/wrong controls and
erasure. There are 49,152 receiving packet/future contexts, each with both cues.
All native readers are independently replayed byte for byte. The majority
policy's physical outcome must equal its selected preservation/graph outcome.

The main panel is mixed unmarked damage. Report intended and opposite success,
continuous margins, edit frequency, all rescues and paired harms. Preserve all
history/pass-fail strata and distinguish source-block uncertainty from four-future
Monte Carlo errors. Pointwise intervals have a bounded fallback when sample
variance is zero. There is no composite positive verdict or equivalence claim.

Full qualification runs two excluded known-source blocks concurrently with all
four receiving futures and all regimes. Its measured complete wave, including
source generation, determines production admission: 1.5 times sixteen waves
plus 120 seconds, capped at an eight-hour forecast. Production deadline is twice
forecast; qualification has a one-hour deadline. The study cap is 2 GiB, each
block is capped at 32 MiB, and the free-space reserve is 4 GiB.

Preflight reproduced native teaching and exact/tolerance/post-pulse writing,
and all 1,024 TT048 graph/screen bridge cases. Full qualification additionally
reconstructs the complete known lineages and compares the one-future preflight
with the corresponding future in the four-future read.

After this startup check the detached job stays unpolled until the user asks.
There is no automatic retry, extension or serial successor. The requested archive
and TT047 recovery remain separate work. See [protocol](PROTOCOL.md),
[current execution](CURRENT_EXECUTION.json), [bound sources](SOURCE_MANIFEST.json)
and the [exposed diagnosis](../TT048/diagnostics_v1/REPORT.md).
''')
 note=f'''

[TT049 fresh-source graph screening](TT049/README.md) launched following the
user's authorization of the next one-read test. Preflight passed; the single
startup observation at {stamp} found {current['phase']}. Two single-thread
workers first qualify full native source generation and four-future receiving
assays on excluded known sources. Measured full-wave runtime controls production
admission. No fresh production effects have been inspected.

The frozen cohort is 32 new source blocks, 512 records, four histories and four
new paired futures. Preservation, unconditional forest repair and the fixed
opposite-majority screen share all eight corruption/control regimes. Both wrong
histories remain explicit. Intended/opposite success, margins, edits, rescues,
paired harms and initial failures are retained. All history remains UNVERIFIED.
An eight-hour forecast ceiling, two-GiB study cap and four-GiB free reserve bound
the run. No automatic polling, retry, extension or serial successor follows.
'''
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
  with (LANE/name).open('a') as f:f.write(note)
 intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=stamp
 intake['fresh_graph_screen_test']=dict(study='TT049',status='LAUNCHED',protocol='TT049/PROTOCOL.md',
  report='TT049/README.md',current_execution='TT049/CURRENT_EXECUTION.json',phase_at_startup=current['phase'],
  new_source_blocks=32,records=512,futures=4,source_namespace=SOURCE_NS,source_population_exposed=False,
  all_initial_failures_retained=True,historical_status='UNVERIFIED',scientific_results_inspected=False,automatic_polling=False,automatic_successor=False)
 replace(LANE/'prediction_intake_status.json',intake)
 with (LANE/'exposure_register.jsonl').open('a') as f:
  f.write(json.dumps(dict(recorded_utc=stamp,study='TT049',event='launched_prospective_graph_screen_test',
   production_blocks=BLOCKS,source_namespace=SOURCE_NS,source_population_exposed=False,production_results_inspected=False,
   TT048_development_results_exposed=True,automatic_successor=False),sort_keys=True)+'\n')
 files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl')]
 files += [ROOT/n for n in ('README.md','PROTOCOL.md','SOURCE_MANIFEST.json','SEEDS.json','PLANNING_EXPOSURE.json',
  'QUEUE_PLAN.json','QUEUE_LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json','checks/preflight_v1/COMPLETE.json',
  'PREFLIGHT_RESOURCE.json','preflight_v1.log','admin/handoff.py','launch_handoff_inputs/MANIFEST.json')]
 write(ROOT/'LAUNCH_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,files={str(p):sha(p) for p in files},
  previous_handoff_preserved=True,scientific_results_inspected=False,automatic_polling=False))
 verify(read(ROOT/'LAUNCH_HANDOFF.json')['files']);verify(pre['inputs'])
 print(json.dumps(dict(status='PASS',phase_at_startup=current['phase'],bound_files=len(files),scientific_results_inspected=False)))

if __name__=='__main__':main()
