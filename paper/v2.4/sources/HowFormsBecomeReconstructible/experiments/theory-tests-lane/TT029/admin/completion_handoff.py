"""Publish the completed descriptive diagnosis into the lane's existing records."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common as c


def percent(value): return f'{100*value:+.3f}'


def document(findings, complete):
    panel = findings['panel']; focus = panel['residual|mix050']
    draw = focus['receiving_draw']['all']; body = focus['fixed_output_pair']['all']; records = focus['record_position']['all']
    transition = draw['preservation_transition']
    new_harms = transition['tied|worsened']+transition['improved|worsened']
    removed = transition['worsened|tied']+transition['worsened|improved']
    lines = ['# TT029: diagnosis of writing after update 100', '',
        '**Complete; all checks passed.** This reanalysis identifies a sharp pattern by injury '
        'geometry and pre-injury body history. It does not provide a new confirmatory result or '
        'a validated repair policy. TT028\'s original primary and joint claims remain NOT_CONFIRMED.', '',
        'For partly corrupted informative records, extending writing from 100 to 1,000 updates '
        f'changes recipient credit by **{percent(draw["recipient_effects"]["extra_writing"]["pooled_effect"])} '
        f'percentage points** and body credit by **{percent(body["body_effects"]["extra_writing"]["pooled_effect"])} '
        'points**. All bodies still run for the same 1,000 physical steps. Shared saved V, ema, R '
        'and theta states at updates 0, 1 and 100 are byte-identical, repair forcing is paired, and '
        'the short arm\'s packet is held exactly after its writing gate.', '',
        '| Informative incoming record | Extra recipient credit, 1,000 minus 100 writes | Extra body credit |',
        '| --- | ---: | ---: |']
    for damage,label in (('mix000','Unmodified'),('mix050','Equal-weight mixing with noise'),('mix100','Replaced with noise')):
        v = panel['residual|'+damage]
        lines.append(f'| {label} | {percent(v["receiving_draw"]["all"]["recipient_effects"]["extra_writing"]["pooled_effect"])} pp | '
            f'{percent(v["fixed_output_pair"]["all"]["body_effects"]["extra_writing"]["pooled_effect"])} pp |')
    lines += ['',
        f'In the partly corrupted informative condition, additional writing introduces **{new_harms} '
        f'new harms against preservation** and removes **{removed} earlier harms** across 16,384 '
        'matched receiving observations. Another 273 observations are harmed under both budgets. '
        'This accounts exactly for the rise from 369 harms at 100 writes to 1,050 at 1,000 writes. '
        'The additional writing also creates 858 new gains against preservation and removes 116 '
        'earlier gains. Directly comparing the two outputs gives 954 gains, 893 harms and 14,537 '
        'ties. These are repeated receiving observations, not independent populations.', '',
        'After averaging both corruptions and all 16 receiving observations per starting record '
        'position, 255 of 1,024 means improve, 210 worsen and 559 tie. At the eight-draw fixed-output '
        'level, 74 of 2,048 pairs show both recipient and body deterioration, 23 show recipient '
        'improvement with body deterioration, and 15 show recipient deterioration with body '
        'improvement. The body/record endpoints therefore must remain distinct. The full joint '
        'tables are retained at both fixed-output and record levels.', '',
        'The table below describes the partly corrupted informative condition. Injury labels '
        'refer to the **target code on the retained half of the tissue**, not the observed sign '
        'of its voltages. They require the known task code and injury mask; they are not an '
        'autonomous warning signal. Means here are pooled over starting record positions; all '
        'three geometry groups occur in every source block.', '',
        '| Retained target-code geometry | Starting records | Extra recipient credit | Extra body credit |',
        '| --- | ---: | ---: | ---: |']
    for name,label in (('positive_half_retained','Positive half'),('negative_half_retained','Negative half'),('both_polarities_retained','Both polarities')):
        v = focus['record_position']['injury:'+name]
        lines.append(f'| {label} | {v["n"]} | {percent(v["recipient_effects"]["extra_writing"]["pooled_effect"])} pp | '
            f'{percent(v["body_effects"]["extra_writing"]["pooled_effect"])} pp |')
    lines += ['',
        'Pre-injury history also matters descriptively. The 127 bodies that did not uniquely pass '
        'before injury show -10.581 pooled points of extra recipient change; the 897 that did pass '
        'show +1.923 points. Equal means over nonempty blocks are -12.390 and +1.897 points '
        'respectively, across 53 and 64 contributing blocks. Neither history nor geometry is '
        'treated as a fitted predictor.', '',
        'Their cross-tabulation is the strongest lead. Among bodies that passed before injury, '
        'retaining the positive target half gives +9.634 recipient points and +7.205 body points '
        '(229 records), whereas retaining both polarities gives -1.897 recipient points and '
        '-6.027 body points (448 records). Thus removing previously failing bodies would not '
        'remove the observed harm. Conversely, previously failing bodies retaining the positive '
        'half show +5.093 recipient points in 27 records; prior failure is not a universal rule '
        'for suppressing extra writing. Previously failing bodies retaining both polarities '
        'show -19.336 recipient points in 64 records. These exposed, overlapping subgroup '
        'comparisons motivate an intervention; they do not establish the mechanism or a safe '
        'selection policy.', '',
        'The common family is retained as a comparator: extra recipient/body changes are '
        '-0.287/-1.465 points for unmodified records, +0.299/-0.537 points under half mixing, '
        'and +21.692/+10.352 points after full replacement. Extra writing can remain useful '
        'when the record is wholly replaced, while adding little net recipient benefit under '
        'partial corruption and reducing body performance.', '',
        'The next proposed experiment holds each developed body, incoming packet, jitter and '
        'repair forcing fixed, varies the four possible half-body injury masks, and compares '
        'preservation, 100 writes and 1,000 writes. Keep the actual injury mask as an exact '
        'replay control and assess outgoing packets in matched fresh recipients. Retain both '
        'families, all corruption strengths and every case. This would directly test whether '
        'the geometry pattern persists within the same body and packet. It should first be '
        'designed and benchmarked as an exposed-cohort mechanism experiment, with no serial '
        'or new population-confirmation claim. It has not been started.', '',
        'All 64 TT028 blocks remain included. The diagnosis retains 98,304 paired receiving '
        'comparisons, 12,288 fixed-output/corruption pairs and 6,144 record-position comparisons '
        'across six family/corruption cells. The original 884,736 receiving rows, 110,592 body '
        'rows and all 54 preservation/writer/body-source control cells were checked. The analysis '
        'verified 768 short/full trajectory pairs, 9,216 shared checkpoint arrays and 1,536 '
        'post-gate packet holds. No new dynamics or receiving assays were generated.', '',
        f'All 22 qualification checks passed. The full single-thread analysis took '
        f'**{complete["seconds"]:.3f} seconds**. Saved table review verifies the transition and '
        'joint-table margins, all group counts and pooled/equal-block weights. All consumed '
        'source files and frozen code are unchanged. Eight futures per fixed output still '
        'give coarse conditional estimates; the saved pointwise Hoeffding intervals remain '
        'visible. Repeated unmodified body states and receiving futures are not new population '
        'replicates. No threshold search, significance test, policy fit, sample extension or '
        'successor run was performed.', '',
        'Evidence: [full diagnostic report](runs/diagnosis_v1/REPORT.md), '
        '[all contrasts and cross-tabulations](FINDINGS.json), '
        '[original control table](runs/diagnosis_v1/CONTROL_TABLE.json), '
        '[analysis plan](PROTOCOL.md), [frozen inputs](FREEZE.json), '
        '[completed run](runs/diagnosis_v1/COMPLETE.json), [saved review](CLOSEOUT.json), '
        '[first inspection](RESULT_INSPECTION.json), [next proposal](NEXT_STEP.json) and '
        '[current execution](CURRENT_EXECUTION.json).', '',
    ]
    return '\n'.join(lines)


def main():
    archive = c.read_json(ROOT/'intake_inputs/MANIFEST.json')
    for row in archive['files']:
        assert c.sha(row['snapshot']) == c.sha(row['original']) == row['sha256']
    frozen = c.read_json(ROOT/'FREEZE.json'); close = c.read_json(ROOT/'CLOSEOUT.json')
    complete = c.read_json(ROOT/'runs/diagnosis_v1/COMPLETE.json'); findings = c.read_json(ROOT/'FINDINGS.json')
    inspected = c.read_json(ROOT/'RESULT_INSPECTION.json')
    assert close['status']=='PASS' and complete['status']=='COMPLETE'
    assert findings['closeout_sha256'] == inspected['closeout_sha256'] == c.sha(ROOT/'CLOSEOUT.json')
    assert complete['verification'] == frozen['planned_verification']
    c.verify(frozen['inputs']); c.verify(frozen['evidence']); c.verify(complete['outputs'])
    recorded = c.now()
    next_step = dict(status='PROPOSED_NOT_STARTED', recorded_utc=recorded,
        question='Does changing injury geometry within the same developed body and incoming packet reproduce the writing-benefit and harm pattern?',
        classification='EXPOSED_COHORT_CAUSAL_MECHANISM_DEVELOPMENT',
        held_fixed=['developed body','incoming packet and corruption realization','injury jitter','repair forcing'],
        intervention='all four half-body injury masks: both axes and both sides',
        writers=['preservation','corrected 100 updates','corrected 1000 updates'],
        controls=['exact replay of actual injury','both record families','all three corruption strengths','all source cases'],
        endpoints=['outgoing packet in matched fresh recipients','rebuilding body at the same physical duration'],
        prerequisites=['freeze the complete design','qualify actual-mask replay','benchmark and budget before a large run'],
        no_policy_selection=True, fresh_population_confirmation=False, serial_endpoint=False,
        no_job_started=True, automatic_successor=False)
    c.write_json(ROOT/'NEXT_STEP.json', next_step)
    current = dict(study='TT029', status='COMPLETE_SAVED_DIAGNOSIS_PASS', recorded_utc=recorded,
        authorization='User lets go after the TT028 saved-data harm-diagnosis proposal',
        classification='EXPOSED_SAVED_DATA_DIAGNOSIS', source='TT028/runs/confirmation_v1',
        job='TT029/runs/diagnosis_v1', completed_utc=complete['completed_utc'], seconds=complete['seconds'],
        closeout='TT029/CLOSEOUT.json', closeout_status='PASS',
        freeze='TT029/FREEZE.json', freeze_sha256=c.sha(ROOT/'FREEZE.json'),
        source_manifest='TT029/SOURCE_MANIFEST.json', findings='TT029/FINDINGS.json',
        report='TT029/runs/diagnosis_v1/REPORT.md', interpretation='TT029/README.md',
        result_inspection='TT029/RESULT_INSPECTION.json', first_result_inspection_utc=inspected['recorded_utc'],
        qualification_checks=22, population_blocks=64, population_reused_and_exposed=True,
        verification=complete['verification'], retained_bytes=complete['retained_bytes'],
        original_control_cells=54, no_active_jobs=True, new_dynamics=0, new_receiving_assays=0,
        original_primary_classification='NOT_CONFIRMED', original_joint_classification='NOT_CONFIRMED',
        no_new_significance_tests=True, no_fitted_policy=True, all_cases_and_paired_harms_retained=True,
        administrative_archive='TT029/intake_inputs/MANIFEST.json', next_proposal='TT029/NEXT_STEP.json',
        automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    c.write_json(ROOT/'CURRENT_EXECUTION.json', current)
    with (ROOT/'README.md').open('x') as stream: stream.write(document(findings,complete))
    prior = c.read_json(c.UPSTREAM/'CURRENT_EXECUTION.json')
    prior.update(administrative_updated_utc=recorded,
        authorized_successor=dict(study='TT029', status=current['status'], current_execution='TT029/CURRENT_EXECUTION.json',
            report='TT029/README.md', source_population_reused_and_exposed=True, new_dynamics=0,
            source_primary_classification_unchanged=True, automatic_successor=False))
    prior['next_proposal']['status']='COMPLETED_AS_TT029'
    (c.UPSTREAM/'CURRENT_EXECUTION.json').write_bytes(c.serialized(prior))
    intake = c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded, conditional_correction_confirmation=prior, additional_writing_diagnosis=current)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    public = ('[TT029 saved-data diagnosis](TT029/README.md) is **complete and verified**. '
        'All 64 exposed TT028 blocks, both families, all corruption conditions and all original controls '
        'remain. No new dynamics or assays were generated. Extending corrected writing from 100 to '
        '1,000 updates in partly corrupted informative records adds **+0.372 recipient points** and '
        '**-2.930 body points**. It introduces **777 new receiving harms against preservation**, '
        'removes **96 earlier harms**, and leaves 273 harms under both budgets. Direct short/full '
        'comparison gives 954 gains, 893 harms and 14,537 ties.\n\n'
        'The injury geometry is a useful descriptive lead: positive-target-half retention gives '
        '**+9.155 recipient / +9.375 body points**; negative-half retention gives **+0.488 / -9.375**; '
        'both-polarity retention gives **-4.077 / -5.859**. These labels use the known task code and '
        'injury mask. Harm also remains among previously passing bodies, so filtering earlier failures '
        'would not establish a reliable writing policy. Full record replacement still benefits from '
        'extra writing (+26.031 recipient / +11.328 body points). All results are descriptive; '
        '**TT028\'s primary and joint claims remain NOT_CONFIRMED**.\n\n'
        'The [next proposal](TT029/NEXT_STEP.json) varies half-body injury masks while holding the '
        'developed body, incoming packet, jitter and forcing fixed, with preservation and both writing '
        'budgets. It requires design, qualification and benchmarking and has not been started. '
        'No job is currently running in this lane. See [current status](TT029/CURRENT_EXECUTION.json).\n')
    for name in ('README.md','THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream: stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-18: TT029 saved diagnosis isolates additional-writing harms and geometry leads\n\n'+public)
    with (c.UPSTREAM/'README.md').open('a') as stream:
        stream.write('\nThe authorized [TT029 saved-data diagnosis](../TT029/README.md) is now complete. '
            'Its geometry and history cross-tabulations are descriptive reuses of this exposed cohort; '
            'TT028\'s registered conclusions remain unchanged.\n')
    event = dict(event='TT029_EXPOSED_SAVED_DIAGNOSIS_COMPLETE', study='TT029', recorded_utc=recorded,
        source_blocks=list(c.BLOCKS), source_study='TT028', fresh_population_cases=0,
        first_diagnostic_effect_inspection_utc=inspected['recorded_utc'],
        freeze_sha256=c.sha(ROOT/'FREEZE.json'), closeout_sha256=c.sha(ROOT/'CLOSEOUT.json'),
        all_cases_and_paired_harms_retained=True, source_primary_unchanged='NOT_CONFIRMED',
        new_dynamics=0, new_receiving_assays=0, no_fitted_policy=True, automatic_successor=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream: stream.write(json.dumps(event,sort_keys=True)+'\n')
    assert c.read_json(c.LANE/'prediction_intake_status.json')['additional_writing_diagnosis'] == current
    assert c.read_json(c.UPSTREAM/'CURRENT_EXECUTION.json')['status'] == 'COMPLETE_SAVED_CLOSEOUT_PASS_PRIMARY_NOT_CONFIRMED'
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT/'README.md').read_text()): assert (ROOT/target).exists(), target
    c.verify(frozen['inputs']); c.verify(frozen['evidence'])
    files = {Path(row['original']) for row in archive['files']}
    files |= {ROOT/name for name in ('CURRENT_EXECUTION.json','README.md','NEXT_STEP.json','FINDINGS.json',
        'CLOSEOUT.json','RESULT_INSPECTION.json','review.py','inspect_results.py','admin/completion_handoff.py',
        'FREEZE.json','SOURCE_MANIFEST.json','intake_inputs/MANIFEST.json','runs/diagnosis_v1/COMPLETE.json')}
    receipt = dict(status='PASS_COMPLETION_HANDOFF', study='TT029', recorded_utc=c.now(),
        files={str(p):c.sha(p) for p in sorted(files)}, prior_bound_files_archived=True,
        scientific_inputs_and_source_data_unchanged=True, all_cases_and_paired_harms_retained=True,
        source_confirmatory_classifications_unchanged=True, no_active_jobs=True,
        no_new_dynamics=True, no_new_significance_tests=True, no_fitted_policy=True,
        current_status_consistent=True, document_links_pass=True, successor_started=False)
    c.verify(receipt['files']); c.write_json(ROOT/'COMPLETION_HANDOFF.json',receipt)
    print({k:v for k,v in receipt.items() if k!='files'},flush=True)


if __name__ == '__main__': main()
