"""Close TT028 with its registered nonconfirmation and both secondary results."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c
import design


def cell(findings, family, damage, body='own', arm='corrected_1000', endpoint='receiving'):
    return findings['panel'][family][damage][body][arm][endpoint]['overall']


def counts(value, key='pair_changes'):
    return ' / '.join(str(value[key][k]) for k in ('improved', 'worsened', 'tied'))


def narrative(findings, closeout):
    claims = findings['registered_inference']['claims']
    lines = [
        '**Completed and verified, 18 October 2026. Primary practical-correction claim: NOT_CONFIRMED.**',
        '',
        'The fresh 64-block study found a positive average change after half mixing, but its registered '
        'lower confidence bound did not exceed the required two-percentage-point margin. The joint '
        'message-specific partial-correction claim therefore remains unconfirmed. The two separate '
        'claims about body specificity and correction after complete packet replacement passed. '
        'Neither secondary result rescues the primary.',
        '',
        '| Registered claim | Mean change | One-sided lower bound | Required margin | Verdict |',
        '| --- | ---: | ---: | ---: | --- |',
    ]
    labels = dict(partial_correction='Half-mixed informative packet: outgoing minus preserved incoming',
        partial_body_specificity='Same condition: own-body minus foreign-body target credit',
        full_replacement_correction='Noise-replaced informative packet: outgoing minus incoming')
    for name in design.claims():
        v = claims[name]
        lines.append(f'| {labels[name]} | {100*v["interval"]["mean"]:+.3f} pp | '
            f'{100*v["interval"]["lower_one_sided"]:+.3f} pp | {100*v["margin"]:.1f} pp | {v["classification"]} |')
    primary = claims['partial_correction']['interval']
    lines += ['',
        'Inference uses all 64 equally weighted source blocks, with approximate paired-block Student-t '
        'coverage and Bonferroni alpha .05/3 for each registered test. The primary pointwise two-sided '
        f'95% interval is [{100*primary["pointwise_two_sided_95"][0]:.3f}, '
        f'{100*primary["pointwise_two_sided_95"][1]:.3f}] percentage points. '
        'NOT_CONFIRMED does not establish absence or equivalence. The frozen bounded Hoeffding '
        'sensitivity lower limits are -33.017, +0.131 and +16.836 points in the table order; only the '
        'complete-replacement claim clears its practical margin under that more conservative sensitivity.',
        '',
        'Mean receiving credit retains the prescribed fractional tie handling. Each cell has 1,024 '
        'starting record positions, two corruption draws and eight paired receiving futures per output '
        '(16,384 paired observations). These are repeated observations of 64 population blocks. '
        'All records, including failing histories and harmful rewrites, remain included.',
        '',
        '| Family | Incoming packet | Incoming credit | Own corrected outgoing | Change | Paired gains / harms / ties | Blocks improved / worsened / tied |',
        '| --- | --- | ---: | ---: | ---: | --- | --- |',
    ]
    damage_labels = dict(mix000='Unmodified', mix050='Equal-weight mixing with noise', mix100='Replaced with noise')
    for family in design.FAMILIES:
        for damage in design.DAMAGE:
            v = cell(findings, family, damage)
            lines.append(f'| {family} | {damage_labels[damage]} | {100*v["incoming"]:.3f}% | '
                f'{100*v["outgoing"]:.3f}% | {v["effect_pp"]:+.3f} pp | {counts(v)} | {counts(v,"block_changes")} |')
    lines += ['',
        'For informative half-mixed packets, 336 of the 1,024 record-position means improve, '
        '203 worsen and 485 tie. The repaired output remains 5.640 points below the unmodified '
        'original reference. Complete replacement improves 882 record means, worsens 90 and ties 52; '
        'its 77.606% output remains 11.633 points below the original 89.240% reference. Positive '
        'population averages do not imply every rewrite helps or that original performance is restored.',
        '',
        'Body source matters. Under informative half mixing, own-body target credit is 83.600%, '
        'foreign-body target credit 47.699% and neutral-body target credit 53.937%. Foreign-body '
        'donor-message credit is 45.569%. Under complete replacement, own target credit and foreign '
        'donor credit both equal 77.606%; foreign target credit is 10.565%, and neutral target credit '
        'is 25.000%. The own/foreign donor equality follows the matched message permutation and is '
        'not an independent replication. Neutral output at 25% still has 3,051 paired gains and '
        '3,051 harms against its noisy input; equality of averages is not packetwise preservation.',
        '',
        'The writer controls remain important. For informative half mixing, the original full-capture '
        'writer changes credit by -18.652 points and the zero-initial-memory writer by -0.964 points. '
        'Corrected full writing changes unmodified informative credit by -4.120 points, with 1,252 '
        'paired harms and 577 gains. This study supports conditional body-supplied reconstruction '
        'within the supplied apparatus; it does not establish that writing generally improves a record.',
        '',
        'Body outcomes are separate. In the informative half-mixed condition, full corrected writing '
        'changes the rebuilding body from 77.490% to 76.611% (-0.879 points; 154 gains, 172 harms, '
        '1,722 ties across 2,048 body observations). Complete replacement changes body credit from '
        '46.729% to 73.633% (+26.904 points). Receiving draws are not counted again as body replicates.',
        '',
        'The declared 100-update writing sensitivity yields 83.228% informative half-mixed receiving '
        'credit (+2.380 points versus preservation), with 759 gains and 369 harms. Its body credit '
        'is 79.541% (+2.051 points versus preservation). Relative to full writing, 100 updates give '
        '-0.372 points of receiving credit and +2.930 points of body credit. All bodies still evolve '
        'for 1,000 steps; only writing is gated. This descriptive arm is not a newly confirmed policy '
        'or a replacement primary endpoint.',
        '',
        'The preregistered descriptive strata suggest a useful diagnosis. Under informative half '
        'mixing, pooled receiving change is -16.339 points for the 127 starting bodies that did not '
        'uniquely pass before injury, and +5.456 points for the 897 that did. Equal-block within-stratum '
        'means are -18.322 and +5.399 points respectively; the first stratum occurs in 53 blocks. '
        'Injury geometries retaining both message polarities show -2.490 pooled points, versus '
        '+7.715 and +8.276 points for the two single-polarity groups. These are descriptive overlaps, '
        'not causal explanations, enrollment filters or validated scheduling rules.',
        '',
        'The next proposed work is a saved-data diagnosis of the 100-versus-1,000-update contrast: '
        'retain every case and cross-classify gains, harms, body changes, pre-injury history and injury '
        'geometry. The aim is to explain where additional writing helps and where it damages useful '
        'records before designing another fresh or serial confirmation. This cohort is now exposed; '
        'it must not be relabeled as prospectively fresh. No successor, sample extension or new '
        'simulation has been launched.',
        '',
        'Individual record estimates still use only eight futures per fixed output, with the saved '
        'pointwise Hoeffding and Clopper-Pearson intervals. They do not precisely characterize each '
        'record’s latent capacity or future descendants. One fixed developed/injured body and repair '
        'forcing are restored across corruption draws. Injury mask, resting value, cue structure '
        'and numerical channel are supplied apparatus. Serial durability, autonomous intervention '
        'selection and biological transfer remain untested here.',
        '',
        f'Final saved closeout passed at **{closeout["completed_utc"]}**, taking '
        f'**{closeout["seconds"]:.3f} seconds** on two CPUs. It verified 864,192 saved arrays, '
        '884,736 paired rows, 110,592 body rows and 110,592 conditional output comparisons. '
        'The original 109,340 run files, all frozen inputs and the numerical summaries are unchanged. '
        'The original run retains FAILED.json because sorted JSON keys changed the display order of '
        'three claim rows. Restoring their registered order reproduces the original report exactly; '
        'the separate closeout passed without new dynamics or assays. First scientific effect '
        'inspection occurred only after that pass.',
        '',
        'Evidence: [full retained report](runs/confirmation_v1/REPORT.md), '
        '[all extracted contrasts and strata](FINDINGS.json), [saved closeout](CLOSEOUT.json), '
        '[first inspection record](RESULT_INSPECTION.json), [protocol](PROTOCOL.md), '
        '[freeze](FREEZE.json) and [current status](CURRENT_EXECUTION.json).',
        '',
    ]
    return '\n'.join(lines)


def main():
    old_receipt = ROOT/'SAVED_CLOSEOUT_HANDOFF.json'
    old = c.read_json(old_receipt)
    c.verify(old['files'])
    findings = c.read_json(ROOT/'FINDINGS.json')
    closeout = c.read_json(ROOT/'CLOSEOUT.json')
    inspected = c.read_json(ROOT/'RESULT_INSPECTION.json')
    assert closeout['status'] == 'PASS' and closeout['new_dynamics'] == closeout['new_receiving_assays'] == 0
    assert closeout == c.read_json(ROOT/'checks/closeout_v1/COMPLETE.json')
    assert findings['closeout_sha256'] == inspected['closeout_sha256'] == c.sha(ROOT/'CLOSEOUT.json')
    assert findings['summary_sha256'] == closeout['summary_sha256'] == c.sha(ROOT/'runs/confirmation_v1/SUMMARY.json')
    assert findings['registered_inference']['primary_classification'] == 'NOT_CONFIRMED'
    assert findings['registered_inference']['joint_classification'] == 'NOT_CONFIRMED'
    assert {k for k,v in findings['registered_inference']['claims'].items() if v['classification'] == 'PRACTICAL_SUPERIORITY_PASS'} == {
        'partial_body_specificity', 'full_replacement_correction'}
    c.verify(closeout['outputs'])
    frozen = c.read_json(ROOT/'FREEZE.json')
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])

    archive = ROOT/'completion_handoff_inputs'
    archive.mkdir(exist_ok=False)
    paths = {Path(p) for p in old['files']} | {old_receipt, ROOT/'CLOSEOUT.json', ROOT/'RESULT_INSPECTION.json', ROOT/'FINDINGS.json'}
    rows = []
    for source in sorted(paths):
        destination = archive/source.relative_to(c.LANE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(source.read_bytes())
        assert c.sha(source) == c.sha(destination)
        rows.append(dict(original=str(source), snapshot=str(destination), sha256=c.sha(source)))
    c.write_json(archive/'MANIFEST.json', dict(status='PASS', recorded_utc=c.now(), files=rows,
        prior_bound_files_preserved_before_edits=True))

    recorded = c.now()
    current = c.read_json(ROOT/'CURRENT_EXECUTION.json')
    current.update(status='COMPLETE_SAVED_CLOSEOUT_PASS_PRIMARY_NOT_CONFIRMED', administrative_updated_utc=recorded,
        completed_utc=closeout['completed_utc'], closeout='TT028/CLOSEOUT.json', closeout_status='PASS',
        closeout_seconds=closeout['seconds'], closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'),
        result_inspection='TT028/RESULT_INSPECTION.json', first_result_inspection_utc=inspected['recorded_utc'],
        findings='TT028/FINDINGS.json', interpretation='TT028/README.md',
        registered_inference=findings['registered_inference'], no_active_jobs=True,
        new_production_outcomes_inspected=True, scientific_result_interpretation_pending=False,
        original_execution_status='FAILED', original_report_order_failure_preserved=True,
        no_numeric_or_inference_change=True, all_cases_and_paired_harms_retained=True,
        saved_verification=closeout['saved_verification'], conditional_pairs=closeout['conditional_pairs'],
        latest_execution_observation='SAVED_CLOSEOUT_PASS_ALL_64_BLOCKS_AND_REGISTERED_RESULTS_INTERPRETED',
        latest_execution_observation_utc=recorded, administrative_archive='TT028/completion_handoff_inputs/MANIFEST.json',
        next_proposal=dict(status='PROPOSED_NOT_STARTED', kind='EXPOSED_SAVED_DATA_HARM_DIAGNOSIS',
            focus='100 versus 1000 writing updates; paired recipient harms, body outcomes, prior history and injury geometry',
            new_simulations=False, fresh_confirmation=False, successor_started=False),
        automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    current['active_operation'].update(status='COMPLETE', active=False, completed_utc=closeout['completed_utc'],
        seconds=closeout['seconds'], forecast_retired=True, closeout='TT028/CLOSEOUT.json')
    (ROOT/'CURRENT_EXECUTION.json').write_bytes(c.serialized(current))
    previous = c.read_json(c.LANE/'TT027/CURRENT_EXECUTION.json')
    previous.update(administrative_updated_utc=recorded)
    previous['authorized_successor'].update(status=current['status'], new_production_outcomes_inspected=True,
        closeout='TT028/CLOSEOUT.json', primary_classification='NOT_CONFIRMED',
        joint_classification='NOT_CONFIRMED', automatic_successor=False)
    (c.LANE/'TT027/CURRENT_EXECUTION.json').write_bytes(c.serialized(previous))
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, packet_damage_body_source_development=previous,
        conditional_correction_confirmation=current)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))

    old_readme = (ROOT/'README.md').read_text()
    heading, history = old_readme.split('\n', 1)
    (ROOT/'README.md').write_text(heading+'\n\n'+narrative(findings, closeout)+
        '\n## Historical execution notes (superseded by the completed result above)\n'+history)
    public = ('[TT028](TT028/README.md) is **complete with saved closeout PASS**. '
        'The original report-order assertion failure is preserved, with no numerical or inference changes. '
        'All 64 fresh blocks and 688,128 receiving evaluations are retained. **Primary and joint claims: '
        'NOT_CONFIRMED.** Informative half-mixed packets improve from 80.847% to 83.600% '
        '(+2.753 points), but the registered lower bound is +1.425 points, below the required +2.0. '
        'The own-versus-foreign body contrast passes (+35.901 points; lower +34.034; margin +5), '
        'as does complete-replacement correction (25.000% to 77.606%; +52.606 points; lower +50.231; '
        'margin +5). These secondary findings do not rescue the primary.\n\n'
        'Full corrected writing harms unmodified informative packets (-4.120 points). The primary '
        'condition contains 1,501 paired gains, 1,050 harms and 13,833 ties; repaired body credit '
        'changes by -0.879 points. All preservation, writer and body-source controls remain in '
        '[the retained report](TT028/runs/confirmation_v1/REPORT.md) and '
        '[extracted findings](TT028/FINDINGS.json). The next proposal is a saved-data diagnosis '
        'of additional writing from 100 to 1,000 updates and its paired harms, using all exposed '
        'cases. No successor, sample extension or simulation has been launched. '
        'See [current status](TT028/CURRENT_EXECUTION.json).\n')
    for name in ('README.md', 'THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream:
            stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-18: TT028 complete; primary unconfirmed, two secondary claims pass\n\n'+public)
    with (c.LANE/'TT027/README.md').open('a') as stream:
        stream.write('\nTT028 is now complete and verified. Its primary practical partial-correction '
            'claim was not confirmed; body specificity and correction after complete replacement passed '
            'their separate margins. See the [full fresh confirmation result](../TT028/README.md).\n')
    event = dict(event='TT028_VERIFIED_RESULTS_INSPECTED_AND_RECORDED', study='TT028', recorded_utc=recorded,
        first_effect_inspection_utc=inspected['recorded_utc'], closeout_completed_utc=closeout['completed_utc'],
        fresh_source_blocks=list(c.BLOCKS), now_exposed=True, primary_classification='NOT_CONFIRMED',
        joint_classification='NOT_CONFIRMED', confirmed_secondary_claims=['partial_body_specificity','full_replacement_correction'],
        closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'), findings_sha256=c.sha(ROOT/'FINDINGS.json'),
        original_report_order_failure_preserved=True, all_cases_and_paired_harms_retained=True,
        no_new_dynamics=True, no_sample_extension=True, automatic_successor=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:
        stream.write(json.dumps(event, sort_keys=True)+'\n')

    assert c.read_json(c.LANE/'prediction_intake_status.json')['conditional_correction_confirmation'] == current
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT/'README.md').read_text()):
        assert (ROOT/target).exists(), target
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    assert c.sha(ROOT/'runs/confirmation_v1/FAILED.json') == closeout['original_failure_sha256']
    assert c.sha(ROOT/'runs/confirmation_v1/SUMMARY.json') == closeout['summary_sha256']
    assert c.sha(ROOT/'runs/confirmation_v1/REPORT.md') == closeout['report_sha256']
    files = paths | {ROOT/'admin/completion_handoff.py', archive/'MANIFEST.json'}
    receipt = dict(status='PASS_COMPLETION_HANDOFF', study='TT028', recorded_utc=c.now(),
        files={str(p):c.sha(p) for p in sorted(files)}, prior_bound_files_archived=True,
        original_failure_preserved=True, scientific_inputs_unchanged=True, no_new_dynamics=True,
        complete_saved_verification_pass=True, first_effect_inspection_after_closeout=True,
        primary_classification='NOT_CONFIRMED', joint_classification='NOT_CONFIRMED',
        secondary_results_do_not_rescue_primary=True, all_cases_and_paired_harms_retained=True,
        current_status_consistent=True, document_links_pass=True, no_active_jobs=True,
        successor_started=False, automatic_polling=False, automatic_retry=False, automatic_extension=False)
    c.verify(receipt['files'])
    c.write_json(ROOT/'COMPLETION_HANDOFF.json', receipt)
    print({k:v for k,v in receipt.items() if k != 'files'}, flush=True)


if __name__ == '__main__':
    main()
