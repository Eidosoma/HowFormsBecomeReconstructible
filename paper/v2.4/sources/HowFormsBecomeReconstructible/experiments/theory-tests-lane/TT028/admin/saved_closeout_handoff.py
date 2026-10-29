"""Record the preserved report failure and the authorized saved-only closeout."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c


def main():
    archive = c.read_json(ROOT/'closeout_handoff_inputs/MANIFEST.json')
    for row in archive['files']:
        assert c.sha(row['snapshot']) == c.sha(row['original']) == row['sha256']
    plan = c.read_json(ROOT/'SAVED_CLOSEOUT_PLAN.json')
    launch = c.read_json(ROOT/'SAVED_CLOSEOUT_LAUNCH.json')
    proof = c.read_json(ROOT/'SAVED_CLOSEOUT_PERSISTENCE_CHECK.json')
    diagnosis = c.read_json(ROOT/'checks/report_order_diagnosis_v1/COMPLETE.json')
    assert launch['status'] == 'DETACHED_STARTED'
    assert proof['status'] == 'PASS' and proof['main']['pid'] == launch['pid']
    assert len(proof['workers']) == 2 and proof['checked_after_host_launcher_returned']
    assert launch['plan_sha256'] == proof['plan_sha256'] == c.sha(ROOT/'SAVED_CLOSEOUT_PLAN.json')
    assert diagnosis['original_report_recovered_by_registered_claim_order_only']
    c.verify(plan['code_and_evidence'])
    recorded = c.now()
    current = c.read_json(ROOT/'CURRENT_EXECUTION.json')
    current.update(status='ACQUISITION_FINISHED_REPORT_ORDER_FAILURE_SAVED_CLOSEOUT_RUNNING_UNPOLLED',
        administrative_updated_utc=recorded, acquisition_finished_blocks=64,
        original_execution_status='FAILED', original_failure='TT028/runs/confirmation_v1/FAILED.json',
        original_failure_utc=diagnosis['failure_utc'], original_failure_preserved=True,
        acquisition_saved_checks_passed=64, retained_acquisition_verification=diagnosis['acquisition_counts'],
        reporting_failure_diagnosis='Three claim rows changed traversal order after sorted JSON serialization; every report line and value is identical.',
        report_order_diagnosis='TT028/checks/report_order_diagnosis_v1/COMPLETE.json',
        acquisition_forecast_retired=True,
        active_operation=dict(role='SAVED_EVIDENCE_CLOSEOUT', job='TT028/checks/closeout_v1',
            log='TT028/saved_closeout_v1.log', pid=launch['pid'], workers=2, numerical_threads=1,
            cpus=launch['cpus'], acknowledged_utc=launch['acknowledged_utc'],
            forecast_seconds=launch['forecast_seconds'], forecast_completion_utc=launch['forecast_completion_utc'],
            deadline_seconds=launch['deadline_seconds'], deadline_utc=launch['deadline_utc'],
            plan='TT028/SAVED_CLOSEOUT_PLAN.json', launch='TT028/SAVED_CLOSEOUT_LAUNCH.json',
            startup_persistence='TT028/SAVED_CLOSEOUT_PERSISTENCE_CHECK.json',
            startup_verified_after_launcher_returned=True, live_workers_verified=2,
            new_dynamics=0, new_receiving_assays=0),
        latest_execution_observation='SAVED_CLOSEOUT_COORDINATOR_AND_TWO_WORKERS_PERSIST_AFTER_HOST_LAUNCH',
        latest_execution_observation_utc=proof['recorded_utc'],
        new_production_outcomes_inspected=False, scientific_result_interpretation_pending=True,
        administrative_archive='TT028/closeout_handoff_inputs/MANIFEST.json',
        automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    (ROOT/'CURRENT_EXECUTION.json').write_bytes(c.serialized(current))
    previous = c.read_json(c.LANE/'TT027/CURRENT_EXECUTION.json')
    previous['administrative_updated_utc'] = recorded
    previous['authorized_successor'].update(status=current['status'],
        new_production_outcomes_inspected=False, automatic_polling=False)
    (c.LANE/'TT027/CURRENT_EXECUTION.json').write_bytes(c.serialized(previous))
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, packet_damage_body_source_development=previous,
        conditional_correction_confirmation=current)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    note = ('TT028 acquired all **64 fresh blocks**, **110,592 intervention repairs** and '
        '**688,128 receiving evaluations**. All block saved checks passed. The execution stopped '
        'at the final report roundtrip assertion on **18 October at 06:29:41 UTC**: JSON sorting '
        'alphabetized three claim keys while the report retained registered order. Diagnosis verifies '
        'the same report lines and values; restoring the declared claim order reproduces the original '
        'report exactly. The failed run, report, data and frozen scientific code remain unchanged. '
        'No scientific effects have been displayed or interpreted.\n\n'
        'A separate saved-data closeout is now detached on **two single-thread workers**, both verified '
        'after the host launcher returned. It rechecks every saved block, all conditional observations, '
        'global aggregation, the original report and file hashes. It generates no new trajectories or '
        'receiving assays and changes no scientific inference. '
        f'Conservative finish estimate: **{launch["forecast_completion_utc"]}**. '
        'It remains unpolled until the user asks. '
        'See [current execution](TT028/CURRENT_EXECUTION.json), '
        '[diagnosis](TT028/checks/report_order_diagnosis_v1/COMPLETE.json) and '
        '[saved-closeout plan](TT028/SAVED_CLOSEOUT_PLAN.json).\n')
    for name in ('README.md', 'THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream:
            stream.write('\n\n'+note)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-18: TT028 report-order failure and saved-data closeout\n\n'+note)
    text = (ROOT/'README.md').read_text()
    heading, body = text.split('\n', 1)
    (ROOT/'README.md').write_text(heading+'\n\n**Current status, 18 October:**\n\n'+
        note.replace('(TT028/', '(')+'\n**Original 17 October launch record (superseded by the status above):**\n'+body)
    with (c.LANE/'TT027/README.md').open('a') as stream:
        stream.write('\nTT028 has now finished acquisition of all 64 new blocks. A report claim-order '
            'assertion stopped its final completion receipt; the values are unchanged and a separate '
            'saved-data closeout is running. See [TT028 current status](../TT028/CURRENT_EXECUTION.json).\n')
    event = dict(event='TT028_REPORT_ORDER_FAILURE_DIAGNOSED_SAVED_CLOSEOUT_STARTED',
        study='TT028', recorded_utc=recorded, original_run_status='FAILED', original_failure_preserved=True,
        acquired_blocks=64, diagnosis_sha256=c.sha(ROOT/'checks/report_order_diagnosis_v1/COMPLETE.json'),
        plan_sha256=c.sha(ROOT/'SAVED_CLOSEOUT_PLAN.json'),
        no_scientific_effects_displayed_or_interpreted=True, new_dynamics=0, new_receiving_assays=0,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:
        stream.write(json.dumps(event, sort_keys=True)+'\n')
    assert c.read_json(c.LANE/'prediction_intake_status.json')['conditional_correction_confirmation'] == current
    frozen = c.read_json(ROOT/'FREEZE.json')
    c.verify(frozen['inputs']); c.verify(frozen['evidence']); c.verify(plan['code_and_evidence'])
    files = {Path(row['original']) for row in archive['files']}
    files |= {ROOT/name for name in ('SAVED_CLOSEOUT_PLAN.json', 'SAVED_CLOSEOUT_LAUNCH.json',
        'SAVED_CLOSEOUT_RESOURCE_CHECK.json', 'SAVED_CLOSEOUT_PERSISTENCE_CHECK.json',
        'saved_closeout.py', 'admin/launch_saved_closeout.py', 'admin/saved_closeout_handoff.py',
        'closeout_handoff_inputs/MANIFEST.json', 'checks/report_order_diagnosis_v1/COMPLETE.json',
        'checks/saved_closeout_preparation_v1/COMPLETE.json')}
    receipt = dict(status='PASS_SAVED_CLOSEOUT_LAUNCH_HANDOFF', recorded_utc=c.now(),
        files={str(p):c.sha(p) for p in sorted(files)}, prior_bound_files_archived=True,
        original_failure_preserved=True, scientific_inputs_unchanged=True,
        current_status_consistent=True, new_dynamics=0, no_scientific_effects_interpreted=True,
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    c.verify(receipt['files'])
    c.write_json(ROOT/'SAVED_CLOSEOUT_HANDOFF.json', receipt)
    print({k:v for k,v in receipt.items() if k != 'files'}, flush=True)


if __name__ == '__main__':
    main()
