"""Publish an authorized launch without polling production outcomes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import *
from datetime import timedelta


def replace_json(path,value):Path(path).write_bytes(serialized(value))
def append(path,text):
    with Path(path).open('a') as f:f.write('\n\n'+text.strip()+'\n')


def main():
    frozen=read_json(ROOT/'FREEZE.json');launch=read_json(ROOT/'LAUNCH.json');persistence=read_json(ROOT/'STARTUP_PERSISTENCE_CHECK.json')
    q=read_json(ROOT/'checks/qualification_v2/COMPLETE.json');benchmark=read_json(ROOT/'runs/benchmark_v2/COMPLETE.json')
    run=read_json(ROOT/'runs/reset_v1/RUNNING.json')
    assert launch['status']=='DETACHED_STARTED' and persistence['status']=='PASS' and persistence['live_workers']==2
    assert q['status']=='PASS' and benchmark['status']=='COMPLETE'
    assert frozen['inputs']==q['inputs']==benchmark['inputs']==runtime_hashes()
    verify(frozen['inputs']);verify(frozen['evidence'])
    archive=read_json(ROOT/'intake_inputs/MANIFEST.json')
    for path,row in archive['files'].items():assert sha(path)==row['sha256']
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl','TT031/README.md','TT031/CURRENT_EXECUTION.json'):
        assert sha(LANE/name)==sha(ROOT/'intake_inputs'/name),name
    expected_finish=(datetime.fromisoformat(run['started_utc'])+timedelta(seconds=frozen['forecast_seconds'])).isoformat()
    status=dict(study='TT032',status='DETACHED_RUNNING_FROZEN_RESET_INTERVENTION',recorded_utc=now(),
        authorization='User lets go after the TT031 reset-ablation proposal',run='TT032/runs/reset_v1',
        pid=launch['pid'],workers=2,numerical_threads=1,cpus=frozen['cpus'],started_utc=run['started_utc'],
        conservative_finish_utc=expected_finish,forecast_seconds=frozen['forecast_seconds'],deadline_seconds=frozen['deadline_seconds'],
        estimated_output_bytes=frozen['estimated_output_bytes'],freeze='TT032/FREEZE.json',freeze_sha256=sha(ROOT/'FREEZE.json'),
        qualification_checks=q['checks_passed'],benchmark_seconds=benchmark['seconds'],
        worker_nice=0,scheduling_amendment='TT032/SCHEDULING_AMENDMENT.json',
        original_benchmark_timeout_preserved=True,saved_benchmark_closeout='PASS',scheduling_scientific_equivalence='PASS',
        source_blocks=64,source_records_per_family=1024,source_population_exposed=True,
        damage='mix100',families=['common','residual'],body_sources=['own','foreign','neutral'],
        masks=4,resets=['corrected','uniform','reversed'],mean_offset_matched=True,writing_budgets=[0,1000],
        body_updates=1000,new_receiving_draws=4,record_bytes=2048,
        planned_logical_verification=frozen['planned_logical_verification'],physical_batch_upper_bounds=frozen['physical_batch_upper_bounds'],
        exact_duplicate_reuse_declared=True,all_cases_and_paired_harms_retained=True,
        production_effects_inspected=False,post_startup_progress_polled=False,startup_persistence_verified=True,
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False,
        fresh_population_confirmation=False,serial_endpoint=False,fitted_policy=False,
        TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED')
    replace_json(ROOT/'CURRENT_EXECUTION.json',status)
    (ROOT/'README.md').write_text(f'''# TT032: spatial reset intervention

**Frozen and running under the user's authorization.** The test changes only
the initial memory offset while holding the voltage state, incoming packet,
physical mask, saved jitter and repair forcing fixed. The corrected spatial
offset, uniform offset and reversed offset all have the same spatial mean.

TT031 found that fully replaced neutral packets followed a predefined
mask/reset pattern in all 4,096 saved receiving observations. TT032 now
intervenes on that spatial reset structure and measures what relevant
surviving-body information adds under each reset.

The new intervention focuses on completely replaced packets. It retains all
64 exposed TT028 blocks, both record families, both corruption realizations,
all four masks, own/foreign/neutral sources, and matched preservation and
1,000-write budgets. Every body evolves for 1,000 updates. Four new matched
recipients evaluate each packet, including replaced incoming and unmodified
original references. Other damage levels remain in the completed evidence;
they are not newly simulated here.

Exact duplicate full states or packets may reuse computation only after
byte-identity checks under the same physical context and randomness. Every
labelled case is retained with an explicit alias. Foreign permutations are
simulated directly. Body and recipient outcomes, target/donor/template
credits, all paired harms and history/message groups remain separate.
The two mixed masks are averaged within each record for geometry contrasts.
Uniform-neutral template credit averaged across all four masks is a balanced
scoring identity, not a new empirical null-test result.

All **{q['checks_passed']} qualification checks** passed, including independent
physical replay, initializer mutations, alias accounting, serial/two-worker
equality, and all report branches. The full-duration excluded benchmark
passed in **{benchmark['seconds']:.2f} seconds**. No benchmark effects were
displayed or used to select the design.

The initial benchmark timed out during its final saved-data recheck under
low-priority scheduling. Its acquired outputs subsequently passed saved-only
verification; the original failure remains. The declared revision uses
normal worker priority, repeats the same excluded cases and all qualification
checks, and verifies every scientific output against the original. Shared
host load also varies; the runtime forecast includes conservative headroom.

Production started at **{run['started_utc']}** on two single-thread CPUs
{frozen['cpus']}. The conservative forecast is **{frozen['forecast_seconds']/3600:.2f}
hours**, finishing around **{expected_finish}**. The hard deadline is
{frozen['deadline_seconds']/3600:.2f} hours; the storage forecast is
{frozen['estimated_output_bytes']/1024**3:.2f} GiB. Both workers were verified
after the host launcher returned. The run is left unpolled until the user
asks; no production effects have been inspected.

This is mechanism development on exposed cases. Four receiving futures are
coarse individual-output estimates. **TT028 primary and joint claims remain
NOT_CONFIRMED.** No fresh-population, serial or autonomous-policy claim is
made, and no automatic retry, extension or successor is configured.

See [protocol](PROTOCOL.md), [freeze](FREEZE.json), [admission](ADMISSION.json),
[benchmark receipt](runs/benchmark_v2/COMPLETE.json), [scheduling amendment](SCHEDULING_AMENDMENT.json),
[equivalence check](checks/scheduling_equivalence_v1/COMPLETE.json), [startup check](STARTUP_PERSISTENCE_CHECK.json)
and [current execution](CURRENT_EXECUTION.json).
''')
    previous=read_json(LANE/'TT031/CURRENT_EXECUTION.json')
    previous.update(updated_utc=now(),successor_started=True,authorized_successor='TT032',
        successor_status=status['status'],successor_current_execution='TT032/CURRENT_EXECUTION.json')
    replace_json(LANE/'TT031/CURRENT_EXECUTION.json',previous)
    append(LANE/'TT031/README.md','The subsequently authorized [TT032 reset intervention](../TT032/README.md) is frozen and running. It compares corrected, uniform and reversed offsets with matched means, all body sources and preservation. TT031 frozen science, saved results and original report failure remain unchanged; the prior handoff is archived in TT032/intake_inputs.')
    text=f'''[TT032 spatial reset intervention](TT032/README.md) is **frozen and running** under the user's authorization. It tests the TT031 neutral-template finding by replacing the spatial memory offset with a uniform, mean-matched offset or reversing it, while keeping voltage, packet, mask, jitter and repair forcing fixed. The new intervention focuses on complete packet replacement, retaining all 64 exposed source blocks, both families, both corruptions, all four masks, own/foreign/neutral sources and matched 0/1,000 writing budgets. Every body evolves for 1,000 updates; four new paired recipients evaluate each packet with incoming and original references.

All cases, paired harms, body endpoints and target/donor/template credits remain. Exact duplicate full states and packets reuse computation only after byte checks, with explicit aliases. Four-mask and mixed-geometry means stay within starting records. Uniform-neutral average template credit is structurally 25% once mask independence is verified. This is exposed-case mechanism development; TT028 primary and joint remain NOT_CONFIRMED.

All {q['checks_passed']} qualification checks passed. The full-duration excluded benchmark took {benchmark['seconds']:.2f} seconds. Production began at {run['started_utc']} on two single-thread CPUs; both workers were verified after host launch. Conservative forecast: **{frozen['forecast_seconds']/3600:.2f} hours**, finishing around **{expected_finish}**. The run remains unpolled until the user asks. No production effects have been inspected and no automatic retry, extension or successor is configured. See [current execution](TT032/CURRENT_EXECUTION.json), [protocol](TT032/PROTOCOL.md) and [freeze](TT032/FREEZE.json).'''
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):append(LANE/name,text)
    intake=read_json(LANE/'prediction_intake_status.json');assert 'spatial_reset_intervention' not in intake
    intake['spatial_reset_intervention']=status;replace_json(LANE/'prediction_intake_status.json',intake)
    with (LANE/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(study='TT032',event='frozen_reset_intervention_launched',
        recorded_utc=now(),source_population_exposed=True,production_effects_inspected=False,freeze_sha256=sha(ROOT/'FREEZE.json'),
        fresh_population_confirmation=False,mean_offset_matched=True,automatic_polling=False,automatic_successor=False),sort_keys=True)+'\n')
    paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl',
        'TT031/README.md','TT031/CURRENT_EXECUTION.json')]
    paths += [ROOT/n for n in ('README.md','CURRENT_EXECUTION.json','PROTOCOL.md','FREEZE.json','ADMISSION.json','LAUNCH.json',
        'STARTUP_PERSISTENCE_CHECK.json','intake_inputs/MANIFEST.json','checks/qualification_v2/COMPLETE.json',
        'runs/benchmark_v2/COMPLETE.json','SCHEDULING_AMENDMENT.json','checks/benchmark_saved_closeout_v1/COMPLETE.json',
        'checks/scheduling_equivalence_v1/COMPLETE.json','admin/launch_handoff.py')]
    value=dict(study='TT032',status='PASS_LAUNCH_HANDOFF',recorded_utc=now(),files={str(p):sha(p) for p in paths},
        frozen_inputs_unchanged=True,prior_bound_documents_archived=True,production_effects_inspected=False,
        two_workers_verified=True,post_startup_progress_polled=False,automatic_polling=False,automatic_successor=False)
    write_json(ROOT/'LAUNCH_HANDOFF.json',value)
    print(dict(status=value['status'],files=len(paths),conservative_finish_utc=expected_finish,forecast_seconds=frozen['forecast_seconds']),flush=True)


if __name__=='__main__':main()
