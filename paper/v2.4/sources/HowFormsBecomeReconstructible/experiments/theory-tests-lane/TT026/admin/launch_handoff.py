"""Archive current administration and publish only the startup acknowledgment."""
from datetime import datetime,timedelta
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import common as c

def main():
    frozen=c.read_json(ROOT/'FREEZE.json');launch=c.read_json(ROOT/'LAUNCH.json')
    q=c.read_json(Path(c.read_json(ROOT/'QUALIFICATION.json')['path']))
    b=c.read_json(ROOT/'runs/benchmark_v1/COMPLETE.json')
    assert launch['status']=='DETACHED_STARTED' and q['status']=='PASS' and b['status']=='COMPLETE'
    assert launch['freeze_sha256']==c.sha(ROOT/'FREEZE.json')
    c.verify(frozen['inputs']);c.verify(frozen['evidence'])
    previous=c.LANE/'TT025';old_receipt=c.read_json(previous/'COMPLETION_HANDOFF.json');c.verify(old_receipt['files'])
    paths=[c.LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
        'exposure_register.jsonl','TT025/README.md','TT025/CURRENT_EXECUTION.json','TT025/COMPLETION_HANDOFF.json')]
    paths += [ROOT/'README.md',ROOT/'EXECUTION.md']
    archive=ROOT/'launch_handoff_inputs';archive.mkdir(exist_ok=False);snapshots=[]
    for p in paths:
        target=archive/p.relative_to(c.LANE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target);assert c.sha(p)==c.sha(target)
        snapshots.append(dict(original=str(p),snapshot=str(target),sha256=c.sha(p)))
    c.write_json(archive/'MANIFEST.json',dict(status='PASS',files=snapshots))
    recorded=c.now();ack=datetime.fromisoformat(launch['acknowledged_utc'])
    status=dict(study='TT026',status='STARTED_DETACHED_UNPOLLED',recorded_utc=recorded,
        acknowledged_utc=launch['acknowledged_utc'],startup_acknowledged=True,pid=launch['pid'],
        job='TT026/runs/window_v1',log='TT026/window_v1.log',current_execution='TT026/CURRENT_EXECUTION.json',
        protocol='TT026/PROTOCOL.md',freeze='TT026/FREEZE.json',freeze_sha256=c.sha(ROOT/'FREEZE.json'),
        launch='TT026/LAUNCH.json',launch_sha256=c.sha(ROOT/'LAUNCH.json'),
        qualification=str(Path(c.read_json(ROOT/'QUALIFICATION.json')['path']).relative_to(c.LANE)),
        qualification_checks=len(q['checks']),qualification_seconds=q['seconds'],qualification_status='PASS',
        qualification_serial_parallel_array_files=q['serial_parallel_array_files'],
        benchmark='TT026/runs/benchmark_v1/COMPLETE.json',benchmark_status='COMPLETE',benchmark_seconds=b['seconds'],
        benchmark_sha256=c.sha(ROOT/'runs/benchmark_v1/COMPLETE.json'),benchmark_verification=b['verification'],
        workers=2,numerical_threads=1,cpus=frozen['cpus'],blocks=frozen['blocks'],families=frozen['families'],arms=frozen['arms'],
        writing_budgets=frozen['writing_budgets'],repair_updates=1000,historical_futures=4,new_recipient_draws=4,
        population_blocks=4,records_per_family=64,packet_bytes=2048,primary=frozen['primary'],
        planned_verification=frozen['planned_verification'],forecast_seconds=frozen['forecast_seconds'],
        deadline_seconds=frozen['deadline_seconds'],
        forecast_completion_from_ack_utc=(ack+timedelta(seconds=frozen['forecast_seconds'])).isoformat(),
        deadline_from_ack_utc=(ack+timedelta(seconds=frozen['deadline_seconds'])).isoformat(),
        estimated_output_bytes=frozen['estimated_output_bytes'],run_byte_limit=frozen['run_byte_limit'],
        free_reserve_bytes=frozen['free_reserve_bytes'],resource_admission='TT026/PRELAUNCH_RESOURCE_CHECK.json',
        frozen_inputs=len(frozen['inputs']),frozen_evidence=len(frozen['evidence']),
        scientific_classification='EXPOSED_CASE_WRITING_WINDOW_DEVELOPMENT',starting_cases_and_histories_exposed=True,
        historical_repair_noise_intentionally_reused=True,new_production_outcomes_inspected=False,
        fresh_population_confirmation=False,significance_verdict=False,serial_endpoint=False,selected_winner=False,
        task_labels_enter_receiving_physics=False,administrative_archive='TT026/launch_handoff_inputs/MANIFEST.json',
        automatic_polling=False,automatic_retry=False,automatic_sample_extension=False,automatic_successor=False,
        post_startup_progress_polled=False,next_check_trigger='USER_STATUS_REQUEST')
    c.write_json(ROOT/'CURRENT_EXECUTION.json',status)
    notice=(f'\nProduction was acknowledged at **{launch["acknowledged_utc"]}**, PID **{launch["pid"]}**, '
        f'on CPUs {frozen["cpus"]}. All **{len(q["checks"])} qualification checks** pass, including exact '
        f'serial/two-worker equality for {q["serial_parallel_array_files"]} array files. The excluded '
        f'full-duration benchmark passes in **{b["seconds"]:.3f} seconds**. The conservative production '
        f'forecast is **{frozen["forecast_seconds"]/3600:.2f} hours**, with a fixed '
        f'**{frozen["deadline_seconds"]/3600:.2f}-hour** deadline. The run is detached and unpolled; '
        'no production outcomes have been inspected. See [freeze](FREEZE.json) and '
        '[current status](CURRENT_EXECUTION.json).\n')
    for name in ('README.md','EXECUTION.md'):
        path=ROOT/name;text=path.read_text()
        text=text.replace('Production is not yet frozen or launched.','Production was subsequently frozen and launched as recorded below.')
        path.write_text(text+notice)
    previous_status=c.read_json(previous/'CURRENT_EXECUTION.json')
    previous_status.update(recorded_utc=recorded,authorized_successor=dict(study='TT026',status=status['status'],
        current_execution=status['current_execution'],proposal='TT025/NEXT_STEP.md',automatic_polling=False,
        new_production_outcomes_inspected=False))
    (previous/'CURRENT_EXECUTION.json').write_bytes(c.serialized(previous_status))
    with (previous/'README.md').open('a') as stream:
        stream.write('\nThe user subsequently authorized the proposed [TT026 writing-window experiment](../TT026/README.md). '
            'It is now implemented, qualified, frozen and launched. Its first startup acknowledgment passed; '
            'production remains unpolled and its outcomes uninspected. TT025\'s original results are unchanged.\n')
    intake=c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded,writing_window_development=status,paired_receiving_development=previous_status)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    public=f'''[TT026 writing-window development](TT026/README.md) is implemented, qualified,
frozen and launched under the user's authorization. It restores all first-episode
injured bodies and incoming records from the four exposed blocks, retaining both
families and all cases. Corrected writing runs for 0, 1, 10, 100 or 1,000 updates;
body and memory repair continue for 1,000 updates in every case. Full-capture
and zero-memory full-writing controls remain, with exact preservation and
paired harms. Each variant evolves its own later state.

All {len(q['checks'])} qualification checks pass. The excluded full-duration benchmark
passes in {b['seconds']:.3f} seconds. Production has 224 repair batches and 896
receiving batches, all independently replayed: 3,584 individual repairs and
14,336 receiving evaluations. Four new receiving draws are paired across
versions; historical repair noise is intentionally retained. Body endpoints
remain separate from receiving outcomes.

The complete duration curve is descriptive development, with no selected
winning budget, fresh-population confirmation or serial-durability claim.
The conservative forecast is {frozen['forecast_seconds']/3600:.2f} hours on two single-thread
workers. Its startup acknowledgment passed; the run is detached and unpolled.
No production outcome is inspected. See [protocol](TT026/PROTOCOL.md),
[freeze](TT026/FREEZE.json), [execution](TT026/EXECUTION.md) and
[current status](TT026/CURRENT_EXECUTION.json). No automatic retry, extension
or successor is configured.
'''
    for name in ('README.md','THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream:stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-17: TT026 writing-window experiment launched\n\n'+public)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(event='TT026_WRITING_WINDOW_DEVELOPMENT_LAUNCHED',recorded_utc=recorded,status=status),sort_keys=True,allow_nan=False)+'\n')
    for name in ('README.md','EXECUTION.md'):
        path=ROOT/name
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):assert (path.parent/link).exists(),(name,link)
    assert c.read_json(c.LANE/'prediction_intake_status.json')['writing_window_development']==status
    assert c.read_json(c.LANE/'prediction_intake_status.json')['paired_receiving_development']==previous_status
    paths += [ROOT/'CURRENT_EXECUTION.json',ROOT/'LAUNCH.json',ROOT/'FREEZE.json',Path(__file__).resolve(),archive/'MANIFEST.json']
    receipt=dict(status='PASS_LAUNCH_HANDOFF',recorded_utc=c.now(),code_sha256=c.sha(__file__),
        files={str(p):c.sha(p) for p in sorted(set(paths))},archive='TT026/launch_handoff_inputs/MANIFEST.json',
        administrative_snapshots_verified=len(snapshots),scientific_progress_polled=False,
        production_outcomes_inspected=False,current_status_consistent=True,local_document_links_pass=True)
    c.verify(frozen['inputs']);c.verify(frozen['evidence']);c.verify(receipt['files'])
    c.write_json(ROOT/'LAUNCH_HANDOFF.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'},sort_keys=True))

if __name__=='__main__':main()
