"""Publish verified paired receiving results, preserving prior administration."""
from datetime import datetime
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c


def main():
    archive = c.read_json(ROOT/'closeout_handoff_inputs/MANIFEST.json')
    assert len(archive['files']) == 12
    for row in archive['files']:
        assert c.sha(row['snapshot']) == c.sha(row['original']) == row['sha256']
    frozen = c.read_json(ROOT/'FREEZE.json')
    complete = c.read_json(ROOT/'runs/paired_v1/COMPLETE.json')
    closeout = c.read_json(ROOT/'CLOSEOUT.json')
    inspection = c.read_json(ROOT/'RESULT_INSPECTION.json')
    summary = c.read_json(ROOT/'runs/paired_v1/SUMMARY.json')
    findings = c.read_json(ROOT/'FINDINGS.json')
    assert complete['status'] == 'COMPLETE' and closeout['status'] == 'PASS'
    assert closeout['run_completion_sha256'] == c.sha(ROOT/'runs/paired_v1/COMPLETE.json')
    assert closeout['summary_sha256'] == findings['source_summary_sha256'] == c.sha(ROOT/'runs/paired_v1/SUMMARY.json')
    assert inspection['closeout_sha256'] == findings['closeout_sha256'] == c.sha(ROOT/'CLOSEOUT.json')
    assert closeout['code_sha256'] == c.sha(ROOT/'closeout.py')
    assert datetime.fromisoformat(closeout['completed_utc']) < datetime.fromisoformat(inspection['recorded_utc'])
    assert findings['primary_effect'] == summary['primary_effect']
    c.verify(closeout['outputs'])

    # Check the human report's complete numerical tables against saved results.
    prose = (ROOT/'INTERPRETATION.md').read_text()
    changes = lambda v: ' / '.join(str(v[k]) for k in ('improved', 'worsened', 'tied'))
    number = lambda v: f'{100*v:.3f}'.replace('-', '−')
    labels = dict(full_on='Full capture, writing', subtract_on='Corrected capture, writing',
                  zero_on='Zero initial memory, writing', zero_off='Packet preservation')
    for family, label in (('residual', 'Informative'), ('common', 'Common')):
        for arm, data in summary['families'][family]['arms'].items():
            v = data['final_minus_initial']
            expected = f'| {label} | {labels[arm]} | {number(v["incoming"])}% | {number(v["outgoing"])}% | {number(v["effect"])} pp | {changes(v["draw_changes"])} | {changes(v["record_changes"])} |'
            assert expected in prose, expected
    primary_arm = summary['families']['residual']['arms']['subtract_on']
    for g, data in primary_arm['cycles'].items():
        v = data['overall']
        expected = f'| {g} | {number(v["incoming"])}% | {number(v["outgoing"])}% | {number(v["effect"])} pp | {changes(v["draw_changes"])} |'
        assert expected in prose, expected

    recorded = c.now()
    current = c.read_json(ROOT/'CURRENT_EXECUTION.json')
    assert current['status'] == 'STARTED_DETACHED_UNPOLLED'
    for name in ('forecast_completion_from_ack_utc', 'deadline_from_ack_utc'):
        current['historical_'+name] = current.pop(name)
    primary = primary_arm['final_minus_initial']
    current.update(status='COMPLETE_VERIFIED_PAIRED_RECEIVING_DEVELOPMENT', recorded_utc=recorded,
        administrative_updated_utc=recorded, completed_utc=complete['completed_utc'], seconds=complete['seconds'],
        completion='TT025/runs/paired_v1/COMPLETE.json', completion_sha256=c.sha(ROOT/'runs/paired_v1/COMPLETE.json'),
        closeout='TT025/CLOSEOUT.json', closeout_status='PASS', closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'),
        closeout_verifier='TT025/closeout.py', closeout_seconds=closeout['seconds'],
        closeout_written_after_acquisition=True, closeout_written_before_effect_inspection=True,
        closeout_new_dynamics=0, report='TT025/runs/paired_v1/REPORT.md', summary='TT025/runs/paired_v1/SUMMARY.json',
        conditional_pairs='TT025/runs/paired_v1/CONDITIONAL.json', interpretation='TT025/INTERPRETATION.md',
        findings='TT025/FINDINGS.json', proposed_followup='TT025/NEXT_STEP.md',
        proposed_followup_status='DRAFT_ONE_EPISODE_WRITING_WINDOW_INTERVENTION_NOT_IMPLEMENTED',
        new_production_receiving_outcomes_inspected=True, all_new_scientific_outcomes_now_exposed=True,
        outcome_inspection='TT025/RESULT_INSPECTION.json', effect_inspection_utc=inspection['recorded_utc'],
        status_check='TT025/STATUS_CHECK.json', post_startup_progress_polled=True,
        poll_trigger='USER_CONTINUE_REQUEST', latest_scientific_execution_observation='COMPLETE_AND_SAVED_CLOSEOUT_PASS',
        latest_scientific_execution_observation_utc=closeout['completed_utc'], next_check_trigger=None,
        completed_blocks=4, primary_descriptive_effect=summary['primary_effect'],
        primary_interpretation='INFORMATIVE_FINAL_RECORD_USEFULNESS_LOWER_THAN_PRESERVED_INITIAL_IN_ALL_FOUR_BLOCKS',
        primary_block_effects=primary['blocks'], primary_record_changes=primary['record_changes'],
        primary_draw_changes=primary['draw_changes'], verification=complete['verification'],
        saved_verification=complete['saved_verification'], summary_verification=complete['summary_verification'],
        original_run_files=closeout['original_run_files'], original_run_unchanged=True,
        retained_bytes_before_completion_receipt=complete['retained_bytes'], peak_worker_rss_bytes=complete['peak_worker_rss_bytes'],
        summary_byte_identical=True, conditional_byte_identical=True, report_byte_identical=True,
        successor_launched=False, historical_launch_administrative_archive=current['administrative_archive'],
        administrative_archive='TT025/closeout_handoff_inputs/MANIFEST.json',
        final_recognition={f:{a:v['final_minus_initial']['outgoing'] for a,v in data['arms'].items()} for f,data in summary['families'].items()})
    (ROOT/'CURRENT_EXECUTION.json').write_bytes(c.serialized(current))

    completion_text = ('TT025 is **complete and verified**. Production ended at **2026-10-16 18:43:05 UTC**, '
        'in **2 hours 3 minutes 36 seconds** on two CPUs. All 51,200 receiving evaluations passed independent replay. '
        'The user-authorized saved closeout passed in **52.504 seconds** before effect inspection; '
        'all 65,536 paired comparisons and the original run verify. See [interpretation](INTERPRETATION.md), '
        '[full report](runs/paired_v1/REPORT.md), [closeout](CLOSEOUT.json) and [next proposal](NEXT_STEP.md).')
    for name in ('README.md', 'EXECUTION.md'):
        path = ROOT/name
        old = path.read_text()
        updated, count = re.subn(r'The production run was acknowledged at \*\*.*?No production scientific outcome has been inspected\.', completion_text, old)
        assert count == 1
        if name == 'README.md':
            updated += ('\nCorrected informative writing reduces recognition from **88.770% to 73.730%**, '
                'a **15.039-point** loss, negative in all four blocks. Its first complete rewrite already loses '
                '**3.223 points**. Forty-two starting-record means worsen, four improve and eighteen tie. '
                'The correction still improves on full capture, but preservation remains ahead; common corrected '
                'writing has a smaller **1.270-point** loss. All policies, cases and paired harms remain. '
                'The proposed duration intervention is a draft; no successor is running.\n')
        else:
            updated = updated.replace('The exact input/evidence hashes and fixed budget will be in [freeze](FREEZE.json).',
                                      'The exact input/evidence hashes and fixed budget are in [freeze](FREEZE.json).')
            updated += ('\nThere was no automatic production polling. The user\'s subsequent “lets go” authorized '
                'the first completion check. Closeout code was written after acquisition and before effects '
                'were inspected; it integrated no trajectories. The 445 frozen inputs, 2,415 evidence files '
                'and 6,441 original run files remain unchanged. All summaries, conditional pairs and the report '
                'reproduce exactly. No automatic retry, extension or successor occurred.\n')
        path.write_text(updated)

    previous_path = c.LANE/'TT024/CURRENT_EXECUTION.json'
    previous = c.read_json(previous_path)
    previous.update(recorded_utc=recorded, authorized_successor=dict(study='TT025', status=current['status'],
        current_execution='TT025/CURRENT_EXECUTION.json', completed_utc=complete['completed_utc'],
        closeout='TT025/CLOSEOUT.json', closeout_status='PASS', new_production_receiving_outcomes_inspected=True,
        interpretation='TT025/INTERPRETATION.md', automatic_polling=False, successor_launched=False))
    previous_path.write_bytes(c.serialized(previous))
    old_readme = c.LANE/'TT024/README.md'
    with old_readme.open('a') as stream:
        stream.write('\nThe [TT025 paired receiving diagnosis](../TT025/INTERPRETATION.md) is now complete and verified. '
            'Corrected informative final records lose 15.039 points relative to their preserved starting packets, '
            'with losses in all four blocks and in every pooled cycle. The first complete rewrite already loses '
            '3.223 points. All gains and harms remain; a shorter-writing intervention is proposed separately.\n')
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, paired_receiving_development=current, serial_fill_subtraction_development=previous)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))

    public = '''[TT025 is complete and verified](TT025/INTERPRETATION.md). In matched fresh recipients,
corrected informative records fall from **88.770% initially to 73.730% after
eight rewrites**, a **15.039-point loss**, negative in every source block.
Every pooled corrected informative cycle has a negative change; the first
complete rewrite already loses **3.223 points**. Final versus initial paired
draws include **41 gains, 195 harms and 788 ties**; starting-record means include
**4 gains, 42 harms and 18 ties**. Preservation is byte-exact and has zero paired
change. All cases and all four policies remain.

Correction still outperforms full capture by **26.172 informative points** and
**20.410 common points**, positive in all blocks. Common corrected writing's
loss versus initial is **1.270 points**, with positive, zero and negative
cycle means. Corrected versus zero-memory final effects are small and have
mixed block signs. Individual improvements and task-relative injury strata
remain visible; they do not qualify an autonomous selection rule.

Production completed in **2 hours 3 minutes 36 seconds** on two CPUs. All
51,200 evaluations passed independent replay. Saved closeout passed before
effect inspection, reproducing every summary and all 65,536 paired rows while
preserving the original run. Four exposed source blocks and four new draws
per historical packet support a development diagnosis, not fresh-population
confirmation or a precise capacity estimate for each packet.

The reviewer-prioritized diagnosis is now available. The [next draft](TT025/NEXT_STEP.md)
varies writing duration within one episode while keeping body repair at 1,000
updates, retaining preservation and the full-budget controls. No shorter budget
is established as beneficial and no successor is launched. This completed
status supersedes the earlier pending TT025 language. See the
[report](TT025/runs/paired_v1/REPORT.md), [closeout](TT025/CLOSEOUT.json) and
[current execution](TT025/CURRENT_EXECUTION.json).
'''
    for name in ('README.md', 'THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream:
            stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-17: TT025 verified paired receiving diagnosis\n\n'+public+
            '\nCloseout verified 445 frozen inputs, 2,415 evidence files, 6,441 original run files, '
            '51,200 array identities, 8,192 telescoping chains and 16,384 zero preservation rows '
            'in 52.504 seconds. Twelve current administrative documents were archived after '
            'verifying the launch/reviewer bindings and before updating this handoff. '
            'The duration proposal was written after effects were inspected; it is not a preregistration.\n')
    event = dict(event='TT025_PAIRED_RECEIVING_COMPLETED_AND_SAVED_CLOSEOUT_PASSED', study='TT025',
        recorded_utc=recorded, completed_utc=complete['completed_utc'], status=current['status'],
        completion_sha256=current['completion_sha256'], closeout_sha256=current['closeout_sha256'],
        freeze_sha256=current['freeze_sha256'], primary_descriptive_effect=current['primary_descriptive_effect'],
        primary_record_changes=primary['record_changes'], primary_draw_changes=primary['draw_changes'],
        all_new_scientific_outcomes_now_exposed=True, original_run_unchanged=True,
        fresh_population_confirmation=False, significance_verdict=False, population_blocks=4,
        records_per_family=64, historical_futures=4, recipient_draws_per_packet=4, cycles=8,
        closeout_new_dynamics=0, closeout_written_after_acquisition=True,
        closeout_written_before_effect_inspection=True, trigger='USER_CONTINUE_REQUEST',
        administrative_archive=current['administrative_archive'], automatic_polling=False,
        automatic_retry=False, automatic_successor=False, successor_launched=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:
        stream.write(json.dumps(event, sort_keys=True, allow_nan=False)+'\n')

    for name in ('README.md', 'EXECUTION.md', 'INTERPRETATION.md', 'NEXT_STEP.md', 'REVIEWER_ALIGNMENT.md'):
        path = ROOT/name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            assert (path.parent/target).exists(), (name, target)
    assert c.read_json(c.LANE/'prediction_intake_status.json')['paired_receiving_development'] == current
    assert c.read_json(c.LANE/'prediction_intake_status.json')['serial_fill_subtraction_development'] == previous
    files = {Path(row['original']) for row in archive['files']}
    files |= {ROOT/name for name in ('INTERPRETATION.md', 'NEXT_STEP.md', 'FINDINGS.json', 'CLOSEOUT.json',
        'closeout.py', 'RESULT_INSPECTION.json', 'STATUS_CHECK.json', 'closeout_handoff_inputs/MANIFEST.json')}
    files.add(Path(__file__).resolve())
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    c.verify(c.read_json(ROOT/'checks/closeout_v1/ORIGINAL_FILES.json'))
    receipt = dict(status='PASS_COMPLETION_HANDOFF', recorded_utc=c.now(),
        files={str(p):c.sha(p) for p in sorted(files)}, code=str(Path(__file__).resolve()), code_sha256=c.sha(__file__),
        archive=current['administrative_archive'], administrative_snapshots_verified=12,
        frozen_inputs_verified=len(frozen['inputs']), frozen_evidence_verified=len(frozen['evidence']),
        original_run_files_verified=closeout['original_run_files'], current_status_consistent=True,
        local_document_links_pass=True, human_report_tables_match_saved_summary=True,
        new_dynamics=0, successor_launched=False)
    c.verify(receipt['files'])
    c.write_json(ROOT/'COMPLETION_HANDOFF.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    main()
