"""Archive current lane administration and publish the one acknowledged launch."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c

def main():
    frozen = c.read_json(ROOT/'FREEZE.json'); launch = c.read_json(ROOT/'LAUNCH.json')
    qualification = c.read_json(Path(c.read_json(ROOT/'QUALIFICATION.json')['path']))
    benchmark = c.read_json(ROOT/'runs/benchmark_v1/COMPLETE.json')
    assert launch['status'] == 'DETACHED_STARTED' and qualification['status'] == 'PASS' and benchmark['status'] == 'COMPLETE'
    assert launch['freeze_sha256'] == c.sha(ROOT/'FREEZE.json')
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    previous = c.LANE/'TT024'
    old_receipt = c.read_json(previous/'DIAGNOSTIC_HANDOFF.json')
    c.verify(old_receipt['files'])
    archive = ROOT/'launch_handoff_inputs'; archive.mkdir(exist_ok=False)
    files = []
    paths = [c.LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md',
        'prediction_intake_status.json', 'exposure_register.jsonl', 'TT024/README.md',
        'TT024/CURRENT_EXECUTION.json', 'TT024/DIAGNOSTIC_HANDOFF.json')]
    paths += [ROOT/'README.md', ROOT/'EXECUTION.md']
    for path in paths:
        target = archive/path.relative_to(c.LANE); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert c.sha(path) == c.sha(target)
        files.append(dict(original=str(path), snapshot=str(target), sha256=c.sha(path)))
    c.write_json(archive/'MANIFEST.json', dict(status='PASS', files=files))
    recorded = c.now(); acknowledgment = datetime.fromisoformat(launch['acknowledged_utc'])
    status = dict(study='TT025', status='STARTED_DETACHED_UNPOLLED', recorded_utc=recorded,
        acknowledged_utc=launch['acknowledged_utc'], startup_acknowledged=True, pid=launch['pid'],
        job='TT025/runs/paired_v1', log='TT025/paired_v1.log', current_execution='TT025/CURRENT_EXECUTION.json',
        protocol='TT025/PROTOCOL.md', freeze='TT025/FREEZE.json', freeze_sha256=c.sha(ROOT/'FREEZE.json'),
        launch='TT025/LAUNCH.json', launch_sha256=c.sha(ROOT/'LAUNCH.json'),
        qualification='TT025/checks/qualification_v1/COMPLETE.json', qualification_checks=len(qualification['checks']),
        qualification_seconds=qualification['seconds'], qualification_status='PASS',
        qualification_serial_parallel_array_files=qualification['serial_parallel_array_files'],
        benchmark='TT025/runs/benchmark_v1/COMPLETE.json', benchmark_status='COMPLETE', benchmark_seconds=benchmark['seconds'],
        benchmark_sha256=c.sha(ROOT/'runs/benchmark_v1/COMPLETE.json'), benchmark_verification=benchmark['verification'],
        workers=2, numerical_threads=1, cpus=frozen['cpus'], blocks=frozen['blocks'], families=frozen['families'], arms=frozen['arms'],
        historical_futures=4, new_recipient_draws=4, generations=8, population_blocks=4, records_per_family=64,
        packet_bytes=2048, primary=frozen['primary'], planned_verification=frozen['planned_verification'],
        forecast_seconds=frozen['forecast_seconds'], deadline_seconds=frozen['deadline_seconds'],
        forecast_completion_from_ack_utc=(acknowledgment+timedelta(seconds=frozen['forecast_seconds'])).isoformat(),
        deadline_from_ack_utc=(acknowledgment+timedelta(seconds=frozen['deadline_seconds'])).isoformat(),
        estimated_output_bytes=frozen['estimated_output_bytes'], run_byte_limit=frozen['run_byte_limit'],
        free_reserve_bytes=frozen['free_reserve_bytes'], resource_admission='TT025/PRELAUNCH_RESOURCE_CHECK.json',
        frozen_inputs=len(frozen['inputs']), frozen_evidence=len(frozen['evidence']),
        scientific_classification='EXPOSED_CASE_PAIRED_RECEIVING_DEVELOPMENT',
        starting_cases_and_histories_exposed=True, new_production_receiving_outcomes_inspected=False,
        fresh_population_confirmation=False, significance_verdict=False, task_labels_enter_physics=False,
        administrative_archive='TT025/launch_handoff_inputs/MANIFEST.json',
        automatic_polling=False, automatic_retry=False, automatic_sample_extension=False, automatic_successor=False,
        post_startup_progress_polled=False, next_check_trigger='USER_STATUS_REQUEST')
    c.write_json(ROOT/'CURRENT_EXECUTION.json', status)
    qtext = f'\nThe production run was acknowledged at **{launch["acknowledged_utc"]}**, PID **{launch["pid"]}**, on CPUs {frozen["cpus"]}. The full-update benchmark passed in **{benchmark["seconds"]:.3f} seconds**. The conservative production forecast is **{frozen["forecast_seconds"]/3600:.2f} hours**, with a fixed deadline of **{frozen["deadline_seconds"]/3600:.2f} hours**. The job is detached and unpolled. No production scientific outcome has been inspected.\n'
    for name in ('README.md', 'EXECUTION.md'):
        with (ROOT/name).open('a') as stream: stream.write(qtext)
    old_status = c.read_json(previous/'CURRENT_EXECUTION.json')
    old_status.update(recorded_utc=recorded, authorized_successor=dict(study='TT025', status=status['status'],
        current_execution=status['current_execution'], paired_receiving_proposal='TT024/PAIRED_RECEIVING_PROPOSAL.md',
        automatic_polling=False, new_production_receiving_outcomes_inspected=False))
    (previous/'CURRENT_EXECUTION.json').write_bytes(c.serialized(old_status))
    with (previous/'README.md').open('a') as stream:
        stream.write('\nThe subsequently authorized [TT025 paired receiving experiment](../TT025/README.md) is implemented, qualified, frozen and launched. It uses all retained cases and four new paired recipient draws; production outcomes remain uninspected.\n')
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, paired_receiving_development=status, serial_fill_subtraction_development=old_status)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    public = f'\n\n[TT025 paired receiving development](TT025/README.md) is now implemented, qualified, frozen and launched under the user\'s authorization. It tests each actual saved incoming/outgoing record pair in the same new receiving conditions, retaining all TT024 cases, both families and four policies. Four new draws yield 3,200 native batches (51,200 individual evaluations), each independently replayed, and 65,536 paired cycle/draw contrasts. The primary descriptive endpoint is informative corrected writing\'s final-minus-initial credit. The four historical blocks remain exposed development cases; conditional futures are not fresh population confirmation.\n\nAll 23 qualification checks pass, including exact native equivalence and serial/two-worker equality. The full-update excluded benchmark passes in {benchmark["seconds"]:.3f} seconds. Production runs on two single-thread workers with a conservative {frozen["forecast_seconds"]/3600:.2f}-hour forecast. Its one startup acknowledgment passed; the job is detached and unpolled, and no production outcomes have been interpreted. See [protocol](TT025/PROTOCOL.md), [freeze](TT025/FREEZE.json), [execution](TT025/EXECUTION.md) and [current status](TT025/CURRENT_EXECUTION.json). No automatic retry, sample extension or successor is configured.\n'
    for name in ('README.md', 'THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream: stream.write(public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-16: TT025 paired receiving experiment launched\n'+public)
    event = dict(event='TT025_PAIRED_RECEIVING_DEVELOPMENT_LAUNCHED', recorded_utc=recorded, status=status)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream: stream.write(json.dumps(event, sort_keys=True, allow_nan=False)+'\n')
    for name in ('README.md', 'EXECUTION.md'):
        path = ROOT/name
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()): assert (path.parent/link).exists(), (name, link)
    assert c.read_json(c.LANE/'prediction_intake_status.json')['paired_receiving_development'] == status
    mutable = paths+[ROOT/'CURRENT_EXECUTION.json', ROOT/'LAUNCH.json', ROOT/'FREEZE.json', Path(__file__).resolve(), archive/'MANIFEST.json']
    result = dict(status='PASS_LAUNCH_HANDOFF', recorded_utc=recorded, code_sha256=c.sha(__file__),
        files={str(p): c.sha(p) for p in sorted(set(mutable))}, archive='TT025/launch_handoff_inputs/MANIFEST.json',
        administrative_snapshots_verified=len(files), scientific_progress_polled=False,
        production_outcomes_inspected=False, current_status_consistent=True, local_document_links_pass=True)
    c.verify(frozen['inputs']); c.verify(frozen['evidence']); c.verify(result['files'])
    c.write_json(ROOT/'LAUNCH_HANDOFF.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, sort_keys=True))

if __name__ == '__main__': main()
