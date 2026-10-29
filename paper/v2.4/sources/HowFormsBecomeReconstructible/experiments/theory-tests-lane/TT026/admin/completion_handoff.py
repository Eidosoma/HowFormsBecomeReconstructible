"""Record checked window results without changing the frozen acquisition."""
from datetime import datetime
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c
import design


def main():
    archive = c.read_json(ROOT/'closeout_handoff_inputs/MANIFEST.json')
    assert len(archive['files']) == 11
    for row in archive['files']:
        assert c.sha(row['snapshot']) == c.sha(row['original']) == row['sha256']
    frozen = c.read_json(ROOT/'FREEZE.json')
    complete = c.read_json(ROOT/'runs/window_v1/COMPLETE.json')
    closeout = c.read_json(ROOT/'CLOSEOUT.json')
    inspection = c.read_json(ROOT/'RESULT_INSPECTION.json')
    summary = c.read_json(ROOT/'runs/window_v1/SUMMARY.json')
    assert complete['status'] == 'COMPLETE' and closeout['status'] == 'PASS'
    assert closeout['run_completion_sha256'] == c.sha(ROOT/'runs/window_v1/COMPLETE.json')
    assert closeout['summary_sha256'] == c.sha(ROOT/'runs/window_v1/SUMMARY.json')
    assert inspection['closeout_sha256'] == c.sha(ROOT/'CLOSEOUT.json')
    assert closeout['code_sha256'] == c.sha(ROOT/'closeout.py')
    assert datetime.fromisoformat(closeout['completed_utc']) < datetime.fromisoformat(inspection['recorded_utc'])
    c.verify(closeout['outputs'])
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])

    # Compact exact results retain every arm, endpoint, block and prespecified
    # stratum. Individual record means remain in the immutable original summary.
    compact = lambda v: {k:x for k,x in v.items() if k != 'record_means'}
    families = {f:{a:{e:{g:(compact(values) if g == 'overall' else
        {name:compact(v) for name,v in values.items()}) for g,values in groups.items()}
        for e,groups in endpoints.items()} for a,endpoints in data['arms'].items()}
        for f,data in summary['families'].items()}
    informative = summary['families']['residual']['arms']
    common = summary['families']['common']['arms']
    assert list(summary['primary_curve'].values()) == [0., 0., -0.001953125, -0.005859375, -0.041015625]
    assert all(v['receiving']['overall']['effect'] <= 0 for f in summary['families'].values() for v in f['arms'].values())
    assert all(x < 0 for x in informative['corrected_1000']['receiving']['overall']['blocks'].values())
    for f in (informative, common):
        assert f['corrected_0001']['receiving']['overall']['pair_changes'] == dict(improved=0,worsened=0,tied=1024)
    for a in design.CORRECTED[:-1]:
        assert all(x > 0 for x in informative[a]['receiving_vs_full']['overall']['blocks'].values())

    recorded = c.now()
    findings = dict(study='TT026', recorded_utc=recorded,
        classification=summary['classification'], source_summary='TT026/runs/window_v1/SUMMARY.json',
        source_summary_sha256=closeout['summary_sha256'], closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'),
        primary=summary['primary'], primary_curve=summary['primary_curve'], families=families,
        all_arms_and_strata_retained=True, all_family_arm_pooled_receiving_effects_nonpositive=True,
        one_update_observed_credit_ties_in_every_pair_both_families=True,
        zero_effect_is_not_equivalence=True, lower_harm_is_not_benefit_over_preservation=True,
        independent_population_blocks=4, records_per_family=64, historical_futures=4,
        receiving_draws_per_packet=4, receiving_rows_per_arm_family=1024, body_rows_per_arm_family=256,
        new_population_confirmation=False, serial_endpoint=False, selected_winner=False,
        significance_verdict=False, successor_launched=False)
    c.write_json(ROOT/'FINDINGS.json', findings)

    number = lambda x: f'{100*x:.3f}'.replace('-', '−')
    changes = lambda v: ' / '.join(str(v[k]) for k in ('improved','worsened','tied'))
    labels = {'corrected_0000':'Corrected, preserve', 'corrected_0001':'Corrected, 1 update',
        'corrected_0010':'Corrected, 10 updates', 'corrected_0100':'Corrected, 100 updates',
        'corrected_1000':'Corrected, 1,000 updates', 'full_1000':'Full capture, 1,000 updates',
        'zero_1000':'Zero initial memory, 1,000 updates'}
    tables = []
    for family, title in (('residual','Informative'),('common','Common')):
        lines = [f'## {title} records', '',
            '| Variant | Incoming | Outgoing | Paired change | Draw gains / harms / ties | Record-mean gains / harms / ties |',
            '| --- | ---: | ---: | ---: | --- | --- |']
        for arm in design.ARMS:
            v = summary['families'][family]['arms'][arm]['receiving']['overall']
            lines.append(f'| {labels[arm]} | {number(v["incoming"])}% | {number(v["outgoing"])}% | {number(v["effect"])} pp | {changes(v["pair_changes"])} | {changes(v["record_changes"])} |')
        lines += ['', '| Variant | Change versus full corrected writing | Draw gains / harms / ties | Repaired body | Body change versus full corrected | Body gains / harms / ties |',
            '| --- | ---: | --- | ---: | ---: | --- |']
        for arm in design.ARMS:
            a = summary['families'][family]['arms'][arm]
            r = a['receiving_vs_full']['overall']; b = a['repaired_body_vs_full']['overall']
            lines.append(f'| {labels[arm]} | {number(r["effect"])} pp | {changes(r["pair_changes"])} | {number(b["outgoing"])}% | {number(b["effect"])} pp | {changes(b["pair_changes"])} |')
        tables.append('\n'.join(lines))

    interpretation = '''# TT026: shorter writing reduces measured damage

TT026 is complete and verified. In the informative family, the complete
corrected-writing curve is 88.477%, 88.477%, 88.281%, 87.891% and 84.375%
outgoing recognition for 0, 1, 10, 100 and 1,000 writing updates. The incoming
record scores 88.477% in these matched fresh recipients. The 1,000-update loss
is 4.102 percentage points and is negative in every block. Every shorter
budget has a positive mean contrast against full corrected writing in every
block, but none has a positive overall contrast against preservation.

One update has identical recognition credit to its incoming packet in every
tested comparison in both families. This is an observed score tie, not a
demonstration of packet identity, general harmlessness or equivalence. Only
zero writing has the specified byte-exact preservation identity. The other
corrected informative budgets have increasingly negative pooled effects;
individual cases and subgroups do not follow a universal monotone rule.

All seven variants repair their own body and memory for 1,000 updates; only
the writing gate varies among corrected variants. The comparison therefore
tests actual writing duration during complete repair. It does not shorten
the body-repair episode or splice another variant's later state into a body.

Each family/variant has 1,024 paired receiving observations, from 64 starting
record positions, four retained historical futures and four new receiving
draws per packet. Those observations share four exposed source blocks. Each
record mean averages 16 observations. Body outcomes have 256 historical cases
per family/variant, counted once each. Percentages are mean native recognition
credit, including the protocol's fractional treatment of ties. All cases,
controls and prespecified strata remain; no winning budget is selected.

'''+ '\n\n'.join(tables) + '''

## Paired effects and heterogeneity

Full corrected informative writing helps 32 receiving comparisons and harms
74; six starting-record means improve and nineteen worsen. Its block effects
are −5.078, −2.344, −8.594 and −0.391 points. The 100-update variant has mixed
effects versus its input: −2.734, 0.000, −0.781 and +1.172 points by block.
It improves on full corrected writing by 3.516 points overall, while 25 paired
receiving comparisons still worsen relative to that full-writing comparator.
This is a mean improvement with retained individual harms.

The corrected 1,000-update informative loss is larger among historically
failing developed bodies: −22.000 points across 100 receiving comparisons,
versus −2.165 across 924 comparisons from passing bodies. At 100 updates the
same contrasts are −12.000 and +0.649 points. Historical body status is a
separate, pre-repair observation; these are conditional descriptive strata,
not independent cohorts or reliable estimates for each particular record.

Task-relative injury strata also differ. Full corrected informative writing
has a +2.734-point effect when the positive half survives, −4.297 when the
negative half survives and −7.422 when both polarities remain. At 100 updates
the corresponding effects are −2.734, 0.000 and +0.195 points. Individual gains
and this reversal remain visible alongside the overall negative curve. The
injury strata use supplied task information and do not qualify an autonomous
policy for deciding when to write.

For common records, corrected writing has small pooled losses beyond one
update and mixed block effects. The 10- and 1,000-update pooled scores match
although their individual gains and harms differ. Full capture has a negative
overall common effect but a +22.727-point effect among historically failing
bodies and a −14.944-point effect among passing bodies. Corrected writing's
overall advantage over full capture must not erase those counterexamples.
All message, injury and body-status summaries for every arm and endpoint are
in the [saved summary](runs/window_v1/SUMMARY.json) and [findings](FINDINGS.json).

## Body performance and scientific scope

Informative repaired-body credit is 80.078% under zero writing, 80.469% under
100 updates and 76.562% under full corrected writing. The 100-update body
contrast versus full writing is +3.906 points, with 16 paired gains and six
harms; its block signs are mixed. Common repaired-body credit instead falls
from 67.188% under full corrected writing to 66.406% under zero writing.
Recipient usefulness and body performance cannot be collapsed into one label.
Developed-to-repaired changes compare stages and are not policy effects.

The demonstrated result is reduced measured damage from shorter writing in
the informative condition. No tested writing arm improves overall receiving
usefulness over its preserved input in either family. Existing favorable
subgroups and body outcomes do not establish a general reason to overwrite.
These first episodes do not establish serial durability. New recipient draws
do not make these previously exposed blocks a fresh population confirmation,
and four draws per historical packet give coarse conditional estimates.

The full-budget bodies and packets reproduce retained TT024 controls exactly.
TT025's first-rewrite estimate used a different receiving namespace, so its
−3.223-point informative result and TT026's −4.102-point result are separate
conditional assay estimates of retained packets. They are not contradictory
new body experiments, and their repeated source cases should not be pooled
as new population replication. TT018 and TT021 address other frozen
comparisons; this development diagnosis does not overturn their bounded results.

## Execution and custody

Production ended at 2026-10-17 12:13:12 UTC after 2,687.890 seconds
(44 minutes 48 seconds) on two single-thread workers. The original 2.37-hour
forecast was a conservative benchmark-based admission estimate. It was not
an elapsed-time observation. No automatic production polling occurred; the
user's status request triggered the first later check.

All 224 repair batches and 896 reader batches passed independent physical
replay, covering 3,584 individual repairs and 14,336 individual receiving
evaluations. All 17,920 native arrays agree exactly, along with 1,152 retained
control arrays. [Saved closeout](CLOSEOUT.json), written after acquisition and
before effect inspection, passed in 39.438 seconds with no new dynamics. It
verified 22,400 saved arrays, 14,336 paired rows, 3,584 separate body rows and
3,584 four-draw conditional pairs. Summaries, conditional estimates and the
report reproduce byte-for-byte. All 549 frozen inputs, 629 evidence files and
2,513 original run files remain unchanged.

See the [protocol](PROTOCOL.md), [full report](runs/window_v1/REPORT.md),
[current status](CURRENT_EXECUTION.json) and [next-step draft](NEXT_STEP.md).
No successor is launched.
'''
    with (ROOT/'INTERPRETATION.md').open('x') as stream:
        stream.write(interpretation)

    next_step = '''# Next question: when does an incoming record need rewriting?

This is a post-result development proposal, written after TT026 inspection.
It is not a frozen protocol or an initiated experiment.

TT025 establishes accumulated harm from the retained corrected rewrites.
TT026 shows that early stopping reduces first-episode damage but provides no
overall fresh-recipient advantage over preserving the incoming record. Those
records were not experimentally corrupted in TT026; the injury intervention
damaged the body. Preservation is therefore a substantive scientific control.

The next useful causal question is whether writing can restore a record whose
usefulness has been degraded while the surviving body retains relevant
information. Develop a bounded one-episode packet-damage challenge before
another serial confirmation. Retain every exposed starting case, including
the unmodified-packet control. Specify a small corruption grid and its
numerical channel before new outcomes, pair each actual damaged packet across
arms and compare each outgoing packet directly with that same damaged input
in matched fresh recipients. Report recovery relative to both damaged-input
preservation and the original unmodified input; neither substitutes for the
other. Enrollment must not depend on a pilot reader's success or failure.

Hold the damaged packet fixed while comparing its own surviving body with a
matched foreign-message body and an appropriate no-body-information control.
Keep resource use and initialization explicit, including supplied masks,
task-aligned information and any memory state carried by a body. This can test
whether corrective information comes from the relevant body history, rather
than attributing a generic packet transformation to reciprocal repair.

Keep the writing-duration grid and preservation visible, along with full-
capture and zero-memory controls; do not choose one step as a proven optimum
from TT026's observed score tie. A reduced panel would need an explicit
pre-acquisition rationale. Body repair must continue for the same duration
across writing conditions. Separate body and receiving endpoints and retain
all paired harms, messages and historical passing/failing cases.

Before execution, freeze corruption, body matching, budgets, random addresses,
contrasts and stopping rules; qualify the zero-damage and preservation
identities and independently replay the actual intervention. Benchmark
excluded cases, then set a bounded development schedule. Do not make a fresh
population or serial-durability claim from this exposed-case challenge.
An operational rule would need subsequent frozen testing on genuinely new
records; later serial tests would require actual continued trajectories.

The reviewer-prioritized incoming/outgoing diagnosis is complete and retained
in TT025 and TT026. The current negative aggregate results are useful even if
this proposed damage challenge is never run. No new simulation, automatic
retry, sample extension or successor was started for this draft.
'''
    with (ROOT/'NEXT_STEP.md').open('x') as stream:
        stream.write(next_step)

    current = c.read_json(ROOT/'CURRENT_EXECUTION.json')
    assert current['status'] == 'STARTED_DETACHED_UNPOLLED'
    for name in ('forecast_completion_from_ack_utc','deadline_from_ack_utc'):
        current['historical_'+name] = current.pop(name)
    current.update(status='COMPLETE_VERIFIED_WRITING_WINDOW_DEVELOPMENT', recorded_utc=recorded,
        administrative_updated_utc=recorded, completed_utc=complete['completed_utc'], seconds=complete['seconds'],
        completion='TT026/runs/window_v1/COMPLETE.json', completion_sha256=c.sha(ROOT/'runs/window_v1/COMPLETE.json'),
        closeout='TT026/CLOSEOUT.json', closeout_status='PASS', closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'),
        closeout_verifier='TT026/closeout.py', closeout_seconds=closeout['seconds'],
        closeout_written_after_acquisition=True, closeout_written_before_effect_inspection=True,
        closeout_new_dynamics=0, report='TT026/runs/window_v1/REPORT.md', summary='TT026/runs/window_v1/SUMMARY.json',
        conditional_pairs='TT026/runs/window_v1/CONDITIONAL.json', interpretation='TT026/INTERPRETATION.md',
        findings='TT026/FINDINGS.json', proposed_followup='TT026/NEXT_STEP.md',
        proposed_followup_status='POST_RESULT_DRAFT_PACKET_DAMAGE_BODY_SOURCE_CHALLENGE_NOT_IMPLEMENTED',
        new_production_outcomes_inspected=True, all_new_scientific_outcomes_now_exposed=True,
        outcome_inspection='TT026/RESULT_INSPECTION.json', effect_inspection_utc=inspection['recorded_utc'],
        status_check='TT026/STATUS_CHECK.json', post_startup_progress_polled=True, poll_trigger='USER_STATUS_REQUEST',
        latest_scientific_execution_observation='COMPLETE_AND_SAVED_CLOSEOUT_PASS',
        latest_scientific_execution_observation_utc=closeout['completed_utc'], next_check_trigger=None,
        completed_blocks=4, primary_descriptive_curve=summary['primary_curve'],
        primary_interpretation='SHORTER_INFORMATIVE_WRITING_REDUCES_MEAN_HARM_WITHOUT_IMPROVING_ON_PRESERVATION',
        verification=complete['verification'], saved_verification=complete['saved_verification'],
        summary_verification=complete['summary_verification'], original_run_files=closeout['original_run_files'],
        original_run_unchanged=True, retained_bytes_before_completion_receipt=complete['retained_bytes'],
        peak_worker_rss_bytes=complete['peak_worker_rss_bytes'], summary_byte_identical=True,
        conditional_byte_identical=True, report_byte_identical=True, successor_launched=False,
        historical_launch_administrative_archive=current['administrative_archive'],
        administrative_archive='TT026/closeout_handoff_inputs/MANIFEST.json',
        final_recognition={f:{a:v['receiving']['overall']['outgoing'] for a,v in d['arms'].items()} for f,d in summary['families'].items()})
    (ROOT/'CURRENT_EXECUTION.json').write_bytes(c.serialized(current))

    notice = ('TT026 is **complete and verified**. Production ended at **2026-10-17 12:13:12 UTC** '
        'after **44 minutes 48 seconds** on two CPUs. All 224 repair batches and 896 reader batches passed '
        'independent replay. Saved closeout passed before effect inspection, reproducing all summaries '
        'and verifying 14,336 paired receiving rows and 3,584 separate body rows. '
        'See [interpretation](INTERPRETATION.md), [full report](runs/window_v1/REPORT.md), '
        '[closeout](CLOSEOUT.json), [freeze](FREEZE.json) and [current status](CURRENT_EXECUTION.json).')
    for name in ('README.md','EXECUTION.md'):
        p = ROOT/name
        text, count = re.subn(r'Production was acknowledged at \*\*.*?\[current status\]\(CURRENT_EXECUTION.json\)\.', notice, p.read_text())
        assert count == 1
        text = text.replace('Every production repair will be computed', 'Every production repair was computed')
        text = text.replace('Qualification and a full-duration excluded benchmark precede production freeze.',
                            'Qualification and a full-duration excluded benchmark preceded production freeze.')
        text = text.replace('A long run will\nuse two single-thread workers, one startup acknowledgment, and no polling\nuntil the user asks.',
                            'The run used two single-thread workers, one startup acknowledgment and no\nautomatic polling. The user requested the later status check.')
        if name == 'README.md':
            text += ('\nThe informative corrected-writing curve is **88.477%, 88.477%, 88.281%, '
                '87.891% and 84.375%** for 0, 1, 10, 100 and 1,000 updates. Shorter writing '
                'reduces measured damage, but no tested arm improves on preservation overall. '
                'Full corrected writing has 32 paired gains and 74 harms; its mean loss is negative '
                'in all four blocks. Body performance and all controls remain separate. '
                'A [post-result next-step draft](NEXT_STEP.md) asks when a damaged incoming record '
                'can benefit from relevant body information. No successor is launched.\n')
        else:
            text += ('\nThe 2.37-hour forecast and 7.28-hour deadline are historical admission bounds. '
                'The actual production duration was 2,687.890 seconds. All 30 qualification checks '
                'passed before freeze. The saved closeout was written after acquisition and before '
                'effect inspection; it passed in 39.438 seconds without new dynamics. All 549 frozen '
                'inputs, 629 evidence files and 2,513 original run files remain unchanged. '
                'No automatic polling, retry, extension or successor occurred.\n')
        p.write_text(text)

    previous_path = c.LANE/'TT025/CURRENT_EXECUTION.json'
    previous = c.read_json(previous_path)
    previous.update(recorded_utc=recorded, administrative_updated_utc=recorded,
        proposed_followup_status='IMPLEMENTED_AND_COMPLETED_AS_TT026', successor_launched=True,
        authorized_successor=dict(study='TT026', status=current['status'],
            current_execution='TT026/CURRENT_EXECUTION.json', completed_utc=complete['completed_utc'],
            closeout='TT026/CLOSEOUT.json', closeout_status='PASS', new_production_outcomes_inspected=True,
            interpretation='TT026/INTERPRETATION.md', automatic_polling=False, successor_launched=False))
    previous_path.write_bytes(c.serialized(previous))
    with (c.LANE/'TT025/README.md').open('a') as stream:
        stream.write('\nThe authorized [TT026 writing-window experiment](../TT026/INTERPRETATION.md) '
            'is now complete and verified. Shortening informative corrected writing reduces '
            'first-episode damage, but none of the tested writing arms improves overall receiving '
            'usefulness over preservation. All cases, controls and paired harms remain. '
            'This completion supersedes the pending TT026 status above; its successor is not launched.\n')
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, writing_window_development=current, paired_receiving_development=previous)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))

    public = '''[TT026 is complete and verified](TT026/INTERPRETATION.md). Corrected informative
writing yields **88.477%, 88.477%, 88.281%, 87.891% and 84.375%** fresh-recipient
credit for 0, 1, 10, 100 and 1,000 writing updates while body repair continues
for all 1,000 updates. The full-writing **4.102-point loss** is negative in
every block. Shorter writing reduces measured damage; none of the tested
writing arms improves on preservation overall in either family. One update
ties its incoming record's recognition credit in all observed comparisons;
that does not establish general equivalence or byte identity.

Full corrected informative writing has **32 paired gains, 74 harms and 918
ties**, with **6 improved, 19 worsened and 39 tied starting-record means**.
All seven arms, both families, all cases and every prespecified stratum remain.
The 100-update body has higher mean credit than the full-writing body, with
paired harms and mixed block signs; body and receiving endpoints remain separate.
The four previously exposed blocks and four new draws per historical packet
support a development diagnosis, without a fresh-population or serial claim.

Production ended at **12:13:12 UTC on 17 October 2026**, after **44 minutes
48 seconds** on two CPUs. All 224 repair and 896 receiving batches passed
independent replay. Saved closeout passed before effect inspection, verifying
22,400 saved arrays and reproducing all 14,336 paired receiving rows and 3,584
separate body rows. Frozen inputs and original runs remain unchanged. This
completes the writing-window diagnosis; no successor is running. The
[next-step draft](TT026/NEXT_STEP.md) proposes testing whether an experimentally
damaged incoming record benefits from relevant surviving-body information,
retaining matched preservation before considering another serial confirmation.
It was written after these results, and is not a frozen or initiated study.
See [report](TT026/runs/window_v1/REPORT.md), [closeout](TT026/CLOSEOUT.json) and
[current execution](TT026/CURRENT_EXECUTION.json). This entry supersedes the
earlier pending TT026 language.
'''
    for name in ('README.md','THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream: stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-17: TT026 verified writing-window development\n\n'+public+
            '\nThe first user-requested check followed completion. Closeout was written '
            'after acquisition and before effect inspection; no trajectories were integrated '
            'for closeout. Eleven current administrative documents were archived after '
            'verifying the launch binding and before this update. All 549 frozen inputs, '
            '629 evidence files and 2,513 original run files still verify.\n')
    event = dict(event='TT026_WRITING_WINDOW_COMPLETED_AND_SAVED_CLOSEOUT_PASSED', study='TT026',
        recorded_utc=recorded, completed_utc=complete['completed_utc'], status=current['status'],
        completion_sha256=current['completion_sha256'], closeout_sha256=current['closeout_sha256'],
        freeze_sha256=current['freeze_sha256'], primary_descriptive_curve=summary['primary_curve'],
        all_new_scientific_outcomes_now_exposed=True, original_run_unchanged=True,
        fresh_population_confirmation=False, significance_verdict=False, serial_endpoint=False,
        selected_winner=False, population_blocks=4, records_per_family=64, historical_futures=4,
        receiving_draws_per_packet=4, closeout_new_dynamics=0, closeout_written_after_acquisition=True,
        closeout_written_before_effect_inspection=True, trigger='USER_STATUS_REQUEST',
        administrative_archive=current['administrative_archive'], automatic_polling=False,
        automatic_retry=False, automatic_successor=False, successor_launched=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:
        stream.write(json.dumps(event, sort_keys=True, allow_nan=False)+'\n')

    for name in ('README.md','EXECUTION.md','INTERPRETATION.md','NEXT_STEP.md'):
        path = ROOT/name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            assert (path.parent/target).exists(), (name,target)
    assert c.read_json(c.LANE/'prediction_intake_status.json')['writing_window_development'] == current
    assert c.read_json(c.LANE/'prediction_intake_status.json')['paired_receiving_development'] == previous
    # Tables are rendered from the verified saved summary; check the persisted
    # document still contains the exact complete tables, not a selected subset.
    assert all(t in (ROOT/'INTERPRETATION.md').read_text() for t in tables)
    files = {Path(row['original']) for row in archive['files']}
    files |= {ROOT/n for n in ('INTERPRETATION.md','NEXT_STEP.md','FINDINGS.json','CLOSEOUT.json',
        'closeout.py','RESULT_INSPECTION.json','STATUS_CHECK.json','closeout_handoff_inputs/MANIFEST.json')}
    files.add(Path(__file__).resolve())
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    c.verify(c.read_json(ROOT/'checks/closeout_v1/ORIGINAL_FILES.json'))
    receipt = dict(status='PASS_COMPLETION_HANDOFF', recorded_utc=c.now(),
        files={str(p):c.sha(p) for p in sorted(files)}, code=str(Path(__file__).resolve()),
        code_sha256=c.sha(__file__), archive=current['administrative_archive'], administrative_snapshots_verified=11,
        frozen_inputs_verified=len(frozen['inputs']), frozen_evidence_verified=len(frozen['evidence']),
        original_run_files_verified=closeout['original_run_files'], current_status_consistent=True,
        local_document_links_pass=True, human_report_tables_match_saved_summary=True,
        new_dynamics=0, successor_launched=False)
    c.verify(receipt['files'])
    c.write_json(ROOT/'COMPLETION_HANDOFF.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'files'}, sort_keys=True))


if __name__ == '__main__':
    main()
