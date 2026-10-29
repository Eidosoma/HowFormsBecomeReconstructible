"""Record TT021's checked scientific interpretation without changing run evidence."""
import common as c


def main():
    directory = c.ROOT/'runs/confirmation_continuation_v1'
    receipt = c.read_json(c.ROOT/'CLOSEOUT.json')
    complete = c.read_json(directory/'COMPLETE.json')
    summary = c.read_json(directory/'SUMMARY.json')
    assert receipt['status'] == 'PASS' and complete['status'] == 'COMPLETE'
    assert receipt['completion_sha256'] == c.sha(directory/'COMPLETE.json')
    assert receipt['primary'] == complete['primary'] == summary['primary']
    assert receipt['report_exact'] and receipt['summary_exact']
    paths = [c.ROOT/'CURRENT_EXECUTION.json', c.LANE/'prediction_intake_status.json',
             c.ROOT/'EXECUTION.md', c.LANE/'DISCOVERY_LOG.md', c.LANE/'THEORY_HANDOFF.md',
             c.LANE/'README.md', c.ROOT/'README.md', c.LANE/'exposure_register.jsonl']
    archive = c.ROOT/'closeout_handoff_inputs/v1'
    archive.mkdir(parents=True, exist_ok=False)
    hashes = {str(p.relative_to(c.LANE)): c.sha(p) for p in paths}
    for p in paths:
        dest = archive/p.relative_to(c.LANE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(p.read_bytes())
    now = c.now()
    c.write_json(archive/'MANIFEST.json', dict(archived_utc=now, files=hashes))
    for p in paths: assert c.sha(p) == hashes[str(p.relative_to(c.LANE))]
    names = {
        'primary_capture_gain': 'Early capture versus ordinary repair',
        'memory_refresh': 'Updating memory versus a held snapshot',
        'matched_writer': 'Captured fixed-reading writer versus matched averaging',
        'body_source': 'Own surviving body versus partner body',
        'informative_record_harm': 'Harm from capture to informative records',
    }
    table = ['| Registered comparison | Gain (percentage points) | One-sided 99% lower bound | Required margin | Result |',
             '| --- | ---: | ---: | ---: | --- |']
    for key in summary['formal_claims']:
        row = summary['contrasts'][key]
        table.append(f"| {names[key]} | {100*row['mean']:.3f} | {100*row['interval']['lower_one_sided']:.3f} | {100*row['margin']:.1f} | {row['classification']} |")
    primary = summary['contrasts']['primary_capture_gain']
    interpretation = '''# TT021: early capture confirmed in fresh receiving bodies

The registered primary passes on all 64 new blocks and all 1,024 enrolled
records. Under common incoming records, ordinary repair gives 50.000% mean
recognition and early capture gives 75.659%: a gain of 25.659 percentage points.
The registered one-sided 99% lower bound is 22.157 points, above the fixed
five-point margin. The separate pointwise two-sided 95% interval is
22.727–28.591 points. These are mean recognition scores across four receiving
draws per record, with fractional tie credit; the population sample size is 64
paired tissue blocks.

Early capture initializes memory from the current injured body, including its
fresh fill, before repair proceeds. It does not receive an intact parental
memory. The held-snapshot comparator protects that same initial captured state.

'''+ '\n'.join(table) + '''

The five directional tests use alpha .01 each and Bonferroni's .05 family
budget. Student-t coverage and the resulting family control are approximate.
The conservative bounded lower sensitivity is −12.276 points for the primary,
so it does not also pass that more conservative calculation. The body-source
claim passes its bounded sensitivity, at +13.480 points. All registered
classifications retain their original rules; no secondary result rescues the
primary and no result is selected for omission.

The body-source comparison is informative: keeping the incoming common record
fixed, own-body capture gives 75.659% intended recognition, while partner-body
capture gives 24.243%. With the partner body, recognition of the partner message
is 75.659%. This supports message-specific information from the surviving body
being written into the outgoing record in this apparatus. The fresh recipient
receives only its 256 float64 values, 2,048 bytes, rather than the surviving body
or its memory. Own-body scrambling and history erasure give 51.978% and 40.967%
intended recognition respectively; those additional contrasts are descriptive.

The writer comparison holds the reading stream fixed: captured writing reaches
68.604%, versus 62.695% for its matched average. Its +5.908-point gain clears the
two-point margin. The benefit is concentrated in message 3 (+22.949 points);
message-specific differences for messages 0–2 are +0.977, 0.000 and −0.293
points. The live arm's 75.659% uses a changing body stream, so comparing that
number with fixed-stream averaging does not isolate a writer-only effect.

Refreshing the captured memory adds only 0.513 points over the protected held
snapshot (75.146%). The registered two-point refresh claim is not confirmed.
This leaves the held snapshot as a strong comparator; the test does not establish
that ongoing memory refresh is required for the primary gain.

For damaged informative records, ordinary repair reaches 90.015% and capture
89.917%. The ordinary-minus-capture harm estimate is +0.098 points, with
pointwise 95% interval −1.557 to +1.752. The predicted harm above two points is
not confirmed. This is not evidence of equivalence or absence of harm to
individual records: capture improves 82 records, worsens 139 and ties 803.
For the primary common-record comparison, capture improves 290 records,
worsens 20 and ties 714. Each change compares four-draw record averages, not a
precise estimate of an individual's future capacity.

All 51,968 native checkpoint arrays agree exactly with the independent physical
reference during acquisition. The largest averaging discrepancy is 7.11e−15,
below the unchanged 2e−12 tolerance. Final saved-evidence closeout passes:
303 runtime inputs (301 original scientific/runtime inputs plus the continuation
adapter and amendment), 6,698 carried files and 219 continuation outputs,
65,024 array identities, 29,696 record rows and 1,856 packet routes. The frozen
scorer reproduces every saved block; the summary and report reproduce exactly.
A separate moment/quantile calculation from the checked record rows reproduces
all five registered decisions. The closeout script was written after outcome
inspection and generates no new dynamics.

The original run stopped at its free-space safeguard after 62 verified blocks,
before the final two began. Its failure and all existing outputs are preserved.
An explicit execution amendment, registered without inspecting interim scientific
summaries, retained the original cohort and scientific rules and completed only
those two unstarted identities. The original run lasted 3 hours 11 minutes
22 seconds before the halt. The continuation finished at 13:39:39 UTC on
15 October 2026 in 5 minutes 31 seconds. The amendment was made after 62 blocks
were generated and must be disclosed with these results.

This is prospective evidence for one subsequent reconstruction in the supplied
simulator and its original pairing regime. It does not establish serial
durability, autonomous repair, independently perturbed cue/message robustness,
biological transfer or a unique theoretical law. A capture-specific serial
comparison retaining the strong held-snapshot and matched-average controls is
a candidate next experiment; it is not launched or registered here. All TT021
blocks are now exposed and cannot serve as a new confirmation cohort.

See [frozen report](runs/confirmation_continuation_v1/REPORT.md),
[full summary](runs/confirmation_continuation_v1/SUMMARY.json),
[closeout](CLOSEOUT.json), [original protocol](PROTOCOL.md),
[execution amendment](CONTINUATION_AMENDMENT.md) and [execution record](EXECUTION.md).
'''
    with (c.ROOT/'INTERPRETATION.md').open('x') as f: f.write(interpretation)
    current = c.read_json(c.ROOT/'CURRENT_EXECUTION.json')
    current.update(status='COMPLETE_CONFIRMATION_AND_CLOSEOUT_PASS', recorded_utc=now,
        last_checked_utc=now, last_poll_user_requested=True, last_user_requested_check='TT021/CLOSEOUT.json',
        post_startup_progress_polled=True, completed_verified_blocks=64, total_blocks=64,
        completion_count_observed_utc=now, pending_block_ids=[], active_worker_count=0,
        active_workers_observed=False, job_completed=True, completed_utc=complete['completed_utc'],
        continuation_runtime_seconds=complete['seconds'],
        original_runtime_to_storage_halt_seconds=receipt['original_runtime_to_storage_halt_seconds'],
        closeout='TT021/CLOSEOUT.json', closeout_status='PASS', closeout_sha256=c.sha(c.ROOT/'CLOSEOUT.json'),
        completion_sha256=c.sha(directory/'COMPLETE.json'),
        report='TT021/runs/confirmation_continuation_v1/REPORT.md', interpretation='TT021/INTERPRETATION.md',
        primary_classification=summary['primary'], primary_gain=primary['mean'],
        primary_lower_one_sided=primary['interval']['lower_one_sided'],
        formal_claim_results={k: summary['contrasts'][k]['classification'] for k in summary['formal_claims']},
        scientific_outcomes_inspected=True, all_blocks_now_exposed=True,
        verification=receipt['verification'], saved_verification=receipt['saved_verification'],
        verified_inputs=receipt['verified_inputs'], verified_original_inputs=receipt['verified_original_inputs'],
        verified_carried_outputs=receipt['verified_carried_outputs'],
        verified_continuation_outputs=receipt['verified_continuation_outputs'],
        administrative_archive='TT021/closeout_handoff_inputs/v1/MANIFEST.json',
        automatic_polling=False, automatic_retry=False, automatic_successor=False, successor_launched=False)
    current.pop('pending_ids_basis', None)
    (c.ROOT/'CURRENT_EXECUTION.json').write_bytes(c.serialized(current))
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    item = intake['early_capture_confirmation']
    for key in ('status', 'last_user_requested_check', 'post_startup_progress_polled',
                'completed_verified_blocks', 'pending_block_ids', 'job_completed', 'completed_utc',
                'continuation_runtime_seconds', 'original_runtime_to_storage_halt_seconds', 'closeout',
                'closeout_status', 'closeout_sha256', 'completion_sha256', 'report', 'interpretation',
                'primary_classification', 'primary_gain', 'primary_lower_one_sided', 'formal_claim_results',
                'scientific_outcomes_inspected', 'all_blocks_now_exposed', 'verified_inputs',
                'verified_carried_outputs', 'verified_continuation_outputs', 'successor_launched'):
        item[key] = current[key]
    item.update(updated_utc=now, active_workers=0)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    handoff = '''

## 15 October 2026 TT021 complete: primary and closeout pass

All 64 new blocks and 1,024 records are retained. Common-record recognition is
75.659% with capture versus 50.000% with ordinary repair: +25.659 percentage
points, one-sided 99% lower bound +22.157, above the registered five-point margin.
The matched-writer (+5.908 points) and body-source (+51.416 points) claims also
pass. Refreshing memory (+0.513 points) and informative-record harm (+0.098
points) do not meet their two-point gates. The five directional claims share
the prespecified .05 family budget; Student-t coverage is approximate.

The primary comparison retains 290 improved, 20 worsened and 714 tied records.
Informative-record capture improves 82, worsens 139 and ties 803; the unconfirmed
population harm claim does not imply individual safety or equivalence. Only
the 2,048-byte outgoing record crosses into a fresh recipient. This establishes
one receiving-horizon result within the supplied simulator and pairing regime.

The original storage failure at 62 blocks is preserved. The registered execution
amendment retained all 62, with no interim scientific summary inspection, and
completed only the two unstarted identities. The continuation finished at
13:39:39 UTC in 331.23 seconds. This execution amendment after 62 generated
blocks accompanies the result. All 51,968 native checkpoint arrays matched
independent physics during acquisition. Final closeout verifies 303 runtime
inputs, 6,698 carried files, 219 continuation outputs and 65,024 array receipts;
all scores, five decisions, summary and report reproduce. The saved-only
closeout verifier was written after outcome inspection and ran no dynamics.

All TT021 blocks are now exposed. No successor is launched; no automatic polling,
retry or successor is configured. See [interpretation](TT021/INTERPRETATION.md),
[report](TT021/runs/confirmation_continuation_v1/REPORT.md),
[closeout](TT021/CLOSEOUT.json) and [execution](TT021/EXECUTION.md).
'''
    for p in (c.LANE/'THEORY_HANDOFF.md', c.LANE/'DISCOVERY_LOG.md'):
        with p.open('a') as f: f.write(handoff)
    with (c.ROOT/'EXECUTION.md').open('a') as f:
        f.write(handoff.replace('(TT021/', '('))
        f.write(f'\nUser-requested completion review recorded at {now}. Saved-evidence closeout took {receipt["seconds"]:.2f} seconds.\n')
    readme = '''[TT021 is complete](TT021/INTERPRETATION.md), with the registered primary and\nfinal closeout passing across all 64 new blocks and 1,024 records. Early capture\nraises common-record recognition from **50.00% to 75.66%**. The **25.66-point**\ngain has a one-sided 99% lower bound of **22.16 points**, above the five-point\nmargin. Matched-writer and body-source claims also pass; the memory-refresh and\ninformative-record-harm claims are not confirmed. The primary retains 20\nrecords that worsen with capture.\n\nThe original storage halt at 62 blocks and the [execution amendment](TT021/CONTINUATION_AMENDMENT.md)\nare preserved. Only the two unstarted blocks were continued; they finished at\n**13:39 UTC on 15 October 2026**. Final closeout verifies 303 inputs, 6,698 carried\nfiles and 219 continuation outputs. This supports one fresh receiving horizon\nwithin the simulator; all blocks are now exposed. See [report](TT021/runs/confirmation_continuation_v1/REPORT.md),\n[closeout](TT021/CLOSEOUT.json) and [execution](TT021/EXECUTION.md). No successor is launched.\n'''
    p = c.LANE/'README.md'
    old = p.read_text(); marker = '[TT021](TT021/README.md) is completing a registered fresh confirmation'
    assert old.count(marker) == 1
    p.write_text(old[:old.index(marker)]+readme)
    (c.ROOT/'README.md').write_text('# TT021: fresh early-capture confirmation\n\n'+readme.replace('(TT021/', '('))
    event = dict(event='TT021_COMPLETED_FRESH_CONFIRMATION_AND_SAVED_CLOSEOUT', study='TT021',
        recorded_utc=now, completed_utc=complete['completed_utc'], primary=summary['primary'],
        primary_gain=primary['mean'], primary_lower_one_sided=primary['interval']['lower_one_sided'],
        claims=current['formal_claim_results'], population_units=64, records=1024,
        all_test_blocks_now_exposed=True, original_failure_preserved=True,
        execution_amendment_after_62_generated=True, scientific_rules_unchanged=True,
        completion_sha256=current['completion_sha256'], closeout_sha256=current['closeout_sha256'],
        registration_sha256=receipt['registration_sha256'],
        continuation_registration_sha256=receipt['continuation_registration_sha256'],
        closeout_verifier_written_after_outcome_inspection=True, closeout_new_trajectories=0,
        continuation_runtime_seconds=complete['seconds'], automatic_polling=False,
        automatic_retry=False, automatic_successor=False, successor_launched=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as f:
        f.write(c.json.dumps(event, sort_keys=True)+'\n')
    outputs = paths+[c.ROOT/'INTERPRETATION.md']
    c.write_json(c.ROOT/'CLOSEOUT_HANDOFF.json', dict(status='PASS', recorded_utc=now,
        closeout_sha256=c.sha(c.ROOT/'CLOSEOUT.json'), recorder_sha256=c.sha(__file__),
        outputs={str(p): c.sha(p) for p in outputs}, scientific_evidence_modified=False,
        successor_launched=False))
    print(c.json.dumps(dict(status='COMPLETE_HANDOFF_RECORDED', primary=summary['primary'],
        original_inputs=receipt['verified_original_inputs'], all_runtime_inputs=receipt['verified_inputs'],
        carried_files=receipt['verified_carried_outputs'], continuation_outputs=receipt['verified_continuation_outputs'],
        interpretation='TT021/INTERPRETATION.md', successor_launched=False), sort_keys=True))


if __name__ == '__main__':
    main()
