"""Publish reviewed TT042 findings while preserving prior handoff versions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.completion-pending')
    write(temporary, value); temporary.replace(path)


def main():
    run = ROOT/'runs/exchange_v1'; complete = read(run/'COMPLETE.json')
    close = read(ROOT/'CLOSEOUT.json'); finding = read(ROOT/'FINDINGS.json')
    assert complete['status'] == 'COMPLETE' and close['status'] == 'PASS'
    assert close['complete_sha256'] == sha(run/'COMPLETE.json') and close['findings_sha256'] == sha(ROOT/'FINDINGS.json')
    assert close['review_code_sha256'] == sha(ROOT/'admin/review.py')
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    verify(read(ROOT/'FREEZE.json')['inputs'])
    half = finding['panels']['mix050']['contrasts']; full = finding['panels']['mix100']['contrasts']
    for name in ('packet_in_B0', 'packet_in_B1'):
        assert half[name]['body_by_time_pp'][-1] == -1.171875 and half[name]['recipient_effect_pp'] == 1.5625
        assert half[name]['body_case_harm_tie_gain'] == [6, 247, 3]
        assert half[name]['recipient_case_harm_tie_gain'] == [17, 211, 28]
    for name in ('body_with_T0', 'body_with_T1'):
        assert half[name]['body_case_harm_tie_gain'] == [0, 256, 0]
    assert full['body_with_T0']['body_case_harm_tie_gain'] == [1, 254, 1]
    for damage, body, recipient in [('mix000', -3.90625, -1.66015625), ('mix050', -1.171875, 1.5625), ('mix100', 6.640625, 13.18359375)]:
        c = finding['panels'][damage]['contrasts']; assert c['packet_in_B0']['body_by_time_pp'][-1] == c['packet_in_B1']['body_by_time_pp'][-1] == body
        assert c['packet_in_B0']['recipient_effect_pp'] == recipient
        assert np.all(np.array(finding['panels'][damage]['saved_state_diagnostic']['nonidentical_body_fields']) == 256)
    summary = arrays(run/'SUMMARY.npz')
    for condition in ('mix000|residual|all|all_masks|foreign', 'mix100|common|all|all_masks|own'):
        assert 100*summary['equal_body_effects'][INDEX[condition], 6, 4, 0] == -0.78125
    prior = ROOT/'corrections/storage_layout_v2/HANDOFF.json'; previous = read(prior); verify(previous['files'])
    archive = ROOT/'completion_handoff_inputs'; archive.mkdir(exist_ok=False)
    paths = set(previous['files']) | {str(prior), str(ROOT/'CURRENT_EXECUTION.json'), str(ROOT/'QUEUE_STATUS.json'),
                                    str(PRIOR/'CURRENT_EXECUTION.json'), str(PRIOR/'README.md')}
    archived = {}
    for name in sorted(paths):
        source = Path(name); target = archive/source.relative_to(LANE); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); assert sha(source) == sha(target)
        archived[name] = dict(archive=str(target), sha256=sha(target))
    write(archive/'MANIFEST.json', archived)
    text = '''# TT042 — exchanging packets between saved body states

TT042 is complete and reviewed. It crossed the preserved and late-written
packets with the preserved and late-writing body states at update 1000, then
continued each combination to 1900 with writing off and the original matched
forcing. All four exposed TT040 blocks and every predeclared case remain.
Production took **26 minutes 37 seconds on two CPUs**, within its fixed deadline.

The principal result concerns target-credit performance in the residual-family,
own-body-source panels, averaged over masks within source positions:

| Incoming packet condition | Late packet effect on final body score, starting from either body (pp) | Inherited fresh-recipient effect (pp) |
|---|---:|---:|
| Intact | -3.9063 | -1.6602 |
| Half mixed | -1.1719 | +1.5625 |
| Fully replaced | +6.6406 | +13.1836 |

The half-mixed final body scores are 76.9531% with the preserved packet and
75.7813% with the late-written packet, whichever saved body state supplies V,
ema and R. Holding the packet fixed, all **256 injury cases** have equal final
target-credit scores under the two body states. With either starting body,
switching to the late packet produces **6 harmed cases, 247 ties and 3 gains**.
After averaging injury masks within source positions, those counts become
6 harms, 56 ties and 2 gains among 64 dependent source positions.

The corresponding fresh-recipient evidence remains the actual TT040 assays:
17 harmed packets, 211 ties and 28 gains after averaging four receiving draws
per packet; source-position averages give 10 harms, 39 ties and 15 gains.
TT042 performed no new receiving assays. The +1.5625-point effect is inherited
evidence, not another replication or a new state-specific capacity estimate.
The packet intervention therefore preserves the earlier distinction between
continuing-body performance and usefulness in fresh recipients.

This is endpoint score equality, not erasure of body state. A post-result
exploratory check of the saved fields finds that V, ema and R remain bytewise
different in every same-packet body pair in these three panels, at every saved
checkpoint. In the half-mixed panel, maximum V differences at 1900 are about
0.1007 with the preserved packet and 0.0869 with the late packet. Coarse success
scores can agree while physical states differ. All saved field differences
are retained in FINDINGS.json, with no extra dynamics generated for this check.

Body-state effects also matter earlier: at 1001 in the half-mixed panel,
substituting the late-writing body changes the target score by -2.7344 points
with the preserved packet and -1.5625 with the late packet. Do not infer
uninterrupted equivalence from the equal final scores or sparse checkpoints.

The intact panel likewise has no final target-score differences between the
two bodies at a fixed packet. Complete replacement retains an exception:
with the preserved packet, one case is harmed and one improves, despite a zero
mean body-state effect. Its four block effects are [-1.5625, +1.5625, 0, 0]
points. Its two conditional packet effects have the same mean but different
paired harm/gain counts. Other predeclared panels also retain interactions:
intact/residual/foreign and fully-replaced/common/own each have a -0.78125-point
mean endpoint interaction. No universal packet-only mechanism or unique
percentage mediation follows. Both ordered decompositions are retained.

All histories, tasks, common/residual families, own/foreign/neutral sources,
mask/geometry panels, four credits, seven contrasts, original-packet controls,
per-draw observations and paired harms remain. The four source blocks are the
independent population units; 64 positions and 256 injury cases are dependent
within them. These are exposed development results under fixed reused forcing,
not a fresh confirmation, serial-inheritance demonstration or general law.

The useful next development question is why the same packet change has opposite
mean effects in the continuing body and the fresh-recipient assay. A controlled
comparison should match the supplied packet, initial receiving state, duration
and forcing, then vary one defined difference between the two reading regimes,
such as memory feedback. Retain incoming/preserved packets, all damage levels,
all cases and paired harms. This is a proposal, not a launched successor; it
does not yet justify another serial-writing confirmation.

Every one of 848 physical continuations was independently replayed during
production: 16,960 saved native arrays matched exactly, with 11,520 saved
diagonal-state and 11,520 saved diagonal-score comparisons to TT040. Closeout
rehash checks covered 2,599 retained output files and 3,164 consumed source files.
Independent integer arithmetic reproduced all 4,032 condition/block reductions,
18,432 case-arm body endpoint arrays, inherited recipient rows, every global
summary array and the frozen report. Qualification's serial/parallel comparison
passed; production did not repeat that separate comparison.

The prior storage-admission failure remains preserved. Production reused the
passed qualification after a documented layout-based output estimate and the
verified TT030/TT036 archive. Scientific code, protocol, 1 GiB study cap and
4 GiB reserve were unchanged. All production processes have exited; no retry,
extension, successor or automatic polling is active. TT028, TT036, TT039, TT040
and TT041 scientific classifications remain unchanged.

See [frozen report](runs/exchange_v1/REPORT.md), [findings](FINDINGS.json),
[review scope](CLOSEOUT.json), [protocol](PROTOCOL.md), and [execution](EXECUTION.md).
'''
    (ROOT/'README.md').write_text(text)
    execution = f'''# TT042 execution

Production completed at {complete['completed_utc']} in {complete['seconds']:.3f}
seconds (26 minutes 37 seconds). Forecast: 1179 seconds. Fixed deadline: 2358
seconds. Two normal-priority workers used CPUs 6 and 7, with one numerical
thread each. The recorded host check confirms the controller and all four
worker processes from the two sequential block pairs have exited.

The first controller stopped at storage admission after passing full excluded
qualification in 372.979 seconds. Preserve QUEUE_FAILED.json and the original
status review. No production run or freeze existed at that stop. The later
recorded storage correction reused the qualification, counted the actual 848
distinct starting states and conservatively budgeted their fixed numeric file
layouts, metadata, reports and administration. No scientific input or resource
limit changed. The prior qualification and all failed-admission evidence remain.

The first production run began on 24 October at 22:00:58 UTC after its freeze.
It retained {complete['retained_bytes']:,} output bytes. Total study size at
completion review was {close['study_bytes_at_review']:,} bytes, below the 1 GiB
cap; free space exceeded the 4 GiB reserve. The recorded storage forecast for
additional output was 790,430,220 bytes. One startup persistence check passed;
no further polling occurred until the user's status request on 25 October.

The source population and TT040 outcomes were already exposed. New exchange
outcomes were first inspected in that post-completion status turn. Closeout
passed in {close['seconds']:.3f} seconds. Every physical continuation had already
undergone independent reference replay during production; closeout verifies
custody and reductions without rerunning dynamics. A separately labelled
exploratory saved-field comparison qualifies the equal-score interpretation.

Previous handoff versions are in completion_handoff_inputs/MANIFEST.json.
Production manifests, freeze, qualification, source artifacts and original
failed queue remain unchanged. No automatic successor is authorized or active.
'''
    (ROOT/'EXECUTION.md').write_text(execution)
    stamp = now()
    proposal = 'Match packet, initial receiver, duration and forcing; vary one reading-regime difference, such as memory feedback; retain preservation, all cases and harms. Proposed, not launched.'
    state = dict(study='TT042', status='COMPLETE_REVIEWED', phase='COMPLETE_REVIEWED', observed_utc=stamp,
                 completed_utc=complete['completed_utc'], actual_seconds=complete['seconds'], forecast_seconds=1179,
                 deadline_seconds=2358, production_started=True, production_completed=True, production_results_inspected=True,
                 no_active_jobs=True, successor_started=False, qualification_status='PASS', qualification_reused=True,
                 confirmatory=False, classification=finding['classification'], source_population_exposed=True,
                 independent_population_blocks=4, all_cases_and_paired_harms_retained=True,
                 new_receiving_assays=0, new_independent_future_draws=0, recipient_evidence_inherited=True,
                 verification=complete['verification'], closeout='TT042/CLOSEOUT.json', findings='TT042/FINDINGS.json',
                 current_execution='TT042/CURRENT_EXECUTION.json', previous_failure='TT042/QUEUE_FAILED.json',
                 automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False,
                 proposal=proposal)
    replace_file(ROOT/'CURRENT_EXECUTION.json', state); replace_file(ROOT/'QUEUE_STATUS.json', state)
    old = read(PRIOR/'CURRENT_EXECUTION.json')
    old['authorized_successor'] = dict(study='TT042', status='COMPLETE_REVIEWED', path='TT042/README.md', observed_utc=stamp)
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nTT042 is now complete and reviewed. Its crossed-state intervention tests the\nproposed body/packet distinction; see [TT042](../TT042/README.md). TT041 results\nand frozen artifacts are unchanged. No successor to TT042 is active.\n')
    brief = '''

TT042 is complete and reviewed: [body/packet exchange](TT042/README.md).
Production took 26 minutes 37 seconds on two CPUs; every physical continuation
passed independent replay. Closeout independently reproduced all 4,032
condition/block reductions and retained all paired harms.

In the half-mixed residual/own panel, the final target score follows the packet:
late versus preserved gives -1.171875 points from either saved body state. At a
fixed packet, all 256 injury cases have equal final target scores across body
states, although V/ema/R remain physically different. Switching packets retains
6 harmed cases, 247 ties and 3 gains. The inherited fresh-recipient effect is
+1.5625 points (17 harmed packets, 211 ties, 28 gains); no new receiving assays.
Complete replacement retains opposing individual body-state effects despite
their zero mean, and other panels retain mean interactions. Four exposed blocks
support a bounded developmental intervention, not fresh confirmation or a
universal packet-only mechanism. A controlled reading-regime comparison is the
proposed next diagnosis; no successor or serial-writing confirmation is launched.

The original storage failure, passed qualification and administrative correction
remain preserved. The verified archive moved 20.5 GB of completed TT030/TT036
data to /mnt/datasets with original paths retained. All processes have exited.
See [findings](TT042/FINDINGS.json) and [closeout](TT042/CLOSEOUT.json).
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = stamp
    intake['body_packet_exchange_development'] = state | dict(report='TT042/README.md', protocol='TT042/PROTOCOL.md',
        predecessor='TT041', full_qualification_pending_at_handoff=False, scientific_results_inspected=True)
    intake['informative_packet_change_diagnosis']['authorized_successor'] = 'TT042 complete and reviewed'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=stamp, study='TT042', event='completed_exchange_review', source_population_exposed=True,
                 new_exchange_outcomes_inspected=True, confirmatory=False, new_receiving_assays=0,
                 all_cases_retained=True, exploratory_saved_field_diagnostic=True,
                 previous_classifications_unchanged=True, successor_started=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT041/CURRENT_EXECUTION.json', 'TT041/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'CURRENT_EXECUTION.json', 'QUEUE_STATUS.json',
                              'FINDINGS.json', 'CLOSEOUT.json', 'RESULT_INSPECTION.json', 'COMPLETION_PROCESS_CHECK.json',
                              'COMPLETION_REVIEW_RESOURCE.json', 'admin/review.py', 'admin/complete_handoff.py',
                              'completion_handoff_inputs/MANIFEST.json')]
    space()
    write(ROOT/'COMPLETION_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
          complete_sha256=sha(run/'COMPLETE.json'), closeout_sha256=sha(ROOT/'CLOSEOUT.json'),
          previous_handoff_versions_preserved=True, scientific_results_inspected=True, successor_started=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), no_active_jobs=True, successor_started=False)))


if __name__ == '__main__': main()
