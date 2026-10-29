"""Publish the reviewed feedback intervention and preserve prior handoff bindings."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.completion-pending')
    write(temporary, value); temporary.replace(path)


def main():
    run = ROOT/'runs/feedback_v1'; complete = read(run/'COMPLETE.json'); qualification = read(ROOT/'runs/qualification_v1/COMPLETE.json')
    close = read(ROOT/'CLOSEOUT.json'); finding = read(ROOT/'FINDINGS.json'); frozen = read(ROOT/'FREEZE.json')
    assert complete['status'] == 'COMPLETE' and close['status'] == 'PASS' and qualification['serial_parallel_bitwise_equal']
    assert close['complete_sha256'] == sha(run/'COMPLETE.json') and close['findings_sha256'] == sha(ROOT/'FINDINGS.json')
    assert close['review_code_sha256'] == sha(ROOT/'admin/review.py') and read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    verify(frozen['inputs'])
    half = finding['panels']['mix050']['profiles']
    expected = {'continuing': [[-1.5625, -1.171875, .390625], [-1.953125, -4.6875, -2.734375]],
                'fresh': [[-1.7578125, .68359375, 2.44140625], [1.5625, -.390625, -1.953125]]}
    for profile, values in expected.items():
        for ti, row in zip((4, 5), values):
            assert [half[profile]['contrasts'][name]['by_time_pp'][ti] for name in
                    ('packet_feedback_off', 'packet_feedback_on', 'interaction')] == row
    fresh = half['fresh']['contrasts']
    assert fresh['feedback_with_T0']['by_time_pp'][-1] == 3.125 and fresh['feedback_with_T1']['by_time_pp'][-1] == 1.171875
    assert fresh['packet_feedback_off']['case_harm_tie_gain_by_time'][-1] == [17, 211, 28]
    assert fresh['packet_feedback_on']['case_harm_tie_gain_by_time'][-1] == [21, 219, 16]
    assert fresh['interaction']['case_harm_tie_gain_by_time'][-1] == [35, 204, 17]
    assert [b[-1] for b in fresh['interaction']['block_effects_by_time_pp']] == [-1.171875, -1.953125, -1.171875, -3.515625]
    near([fresh[n]['continuous_margin_by_time'][-1] for n in ('packet_feedback_off', 'packet_feedback_on', 'interaction')],
         [.007092087203321505, .007909782372974355, .0008176951696528483])
    prior = ROOT/'LAUNCH_HANDOFF.json'; previous = read(prior); verify(previous['files'])
    archive = ROOT/'completion_handoff_inputs'; archive.mkdir(exist_ok=False); archived = {}
    paths = set(previous['files']) | {str(prior), str(ROOT/'CURRENT_EXECUTION.json'), str(ROOT/'QUEUE_STATUS.json')}
    for name in sorted(paths):
        source = Path(name); target = archive/source.relative_to(LANE); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); assert sha(source) == sha(target)
        archived[name] = dict(archive=str(target), sha256=sha(target))
    write(archive/'MANIFEST.json', archived)
    text = '''# TT043 — packet usefulness with and without memory feedback

TT043 is complete and reviewed. It tests the effect of memory feedback on the
usefulness of the same actual preserved and late-written packets, with writing
off. Full excluded qualification took **19 minutes**; production took
**59 minutes 44 seconds on two CPUs**. Every physical continuation passed an
independent equation replay, and independent closeout reproduced all reductions.

The main finding is a timing-dependent interaction between the packet and the
receiving system's memory feedback. In the half-mixed residual/own panel, the
late-minus-preserved target-success effect is:

| Receiving profile | Updates | Feedback off (pp) | Feedback on (pp) | On-minus-off change in packet effect (pp) |
|---|---:|---:|---:|---:|
| Continuing body | 900 | -1.5625 | -1.1719 | +0.3906 |
| Continuing body | 1000 | -1.9531 | -4.6875 | -2.7344 |
| Fresh recipient | 900 | -1.7578 | +0.6836 | +2.4414 |
| Fresh recipient | 1000 | +1.5625 | -0.3906 | -1.9531 |

At 1000 updates in fresh recipients, feedback changes the late packet's relative
success advantage from +1.5625 to -0.390625 percentage points. This does not mean
feedback lowers either packet's absolute mean score: it improves the preserved
packet by +3.125 points and the late packet by +1.171875. The preserved comparator
benefits more. All four block interaction effects are negative at this horizon:
[-1.171875, -1.953125, -1.171875, -3.515625] points.

Paired variation remains. Without feedback, the late packet produces 17 harmed
injury cases, 211 ties and 28 gains; with feedback, 21 harms, 219 ties and 16
gains. The change in the packet effect itself is negative in 35 cases, zero in
204 and positive in 17. Each of these 256 cases averages its four original
receiving draws. They are dependent injury cases from 64 source positions in
four exposed blocks, not 256 independent replications. Source-position averages
and individual-draw counts remain separately available.

At 900 updates, the same fresh-recipient interaction is positive (+2.44140625
points). Its four block values are [+3.125, -1.171875, +2.734375, +5.078125].
Both horizons were specified before production. The sign change prevents a
general claim that feedback suppresses, enhances or stabilizes rewriting.
The fresh feedback-off packet effect itself changes from -1.7578125 at 900
to +1.5625 at 1000, so the earlier positive endpoint is not uninterrupted
advantage. The continuing 900-update point reproduces TT042 at absolute update
1900; its 1000-update point is absolute update 2000.

Continuous margins qualify the success-score result. At 1000 in fresh
recipients, late-minus-preserved mean target-versus-best-other margin is positive
with feedback off (+0.00709209) and on (+0.00790978). Its small positive
interaction (+0.00081770) differs from the negative success-credit interaction.
An average margin and tied-winner success credit measure different outcomes;
neither substitutes for the other or establishes general information capacity.

Other damage levels are retained. With intact packets, the mean late-packet
effect stays negative in both profiles and feedback settings at both terminal
horizons. With full replacement it stays positive. At 1000, full-replacement
continuing-body effects are +15.2344 points with feedback off and +6.6406 with it
on; fresh-recipient effects are +13.1836 and +13.7695. Feedback is therefore not
uniformly helpful or harmful across damage and receiving conditions. Individual
harms, ties and gains remain even where a mean feedback effect is zero.

Within each profile/draw, feedback gain is the only changed physical parameter:
c_m is 0 or 0.2, while memory updating rho stays 0.002. Initial V/ema/R, the
supplied finite float64 packet and forcing are paired. The profiles themselves
have different initial states and forcing, so their direct difference does not
isolate feedback. With feedback off, fresh R tracks V without feeding back;
V/ema/theta and readouts reproduce the original R-clamped assay, but R does not.
The two original clamped native assays were also replayed in qualification.

The feedback intervention affects packet usefulness in these simulated receiving
conditions. It does not by itself explain the whole TT042 body/recipient gap:
at 1000 updates with feedback off in both profiles, the continuing packet effect
is still negative (-1.953125) while the fresh effect is positive (+1.5625).
The useful next diagnosis is to cross saved receiving initial states with the
two forcing streams at fixed feedback and matched horizons. That would separate
the remaining state and forcing differences, retaining preserved/late packets,
all conditions and paired harms. It is proposed, not launched; no serial-writing
confirmation follows automatically.

All four exposed source blocks, three mixtures, two families, three body sources,
all histories/tasks, four masks, geometry strata and four role credits remain.
All seven contrasts, both ordered decompositions, six checkpoints, 900-to-1000
changes, paired signs, continuous margins and original-packet controls are saved.
The single continuing-body observation is not counted as four receiving draws.
The four original fresh draws and forcing were reused: new intervention
conditions are not new independent futures, capacity estimates or a fresh
population confirmation. Sparse checkpoints do not establish uninterrupted
performance. Earlier scientific classifications remain unchanged.

Production independently replayed all 2704 physical batches: 64,896 native
arrays matched exactly, 16,224 score checkpoints passed, and 34,560 saved anchor
arrays plus 20,736 saved anchor-score arrays matched. Closeout verified 8,168
retained output files, 4,008 consumed source files and eight additional source
tables; independently reproduced all 4,032 condition/block reductions and every
global summary; and checked 92,160 case/arm/draw endpoint vectors plus 2,211,840
continuous-margin entries. Physical dynamics were not rerun at closeout because
each continuation had already undergone full independent replay in production.
Qualification's serial/parallel equality passed; production did not repeat that
separate comparison. All processes have exited. No job or successor is active.

See [frozen report](runs/feedback_v1/REPORT.md), [findings](FINDINGS.json),
[closeout](CLOSEOUT.json), [protocol](PROTOCOL.md) and [execution](EXECUTION.md).
'''
    (ROOT/'README.md').write_text(text)
    execution = f'''# TT043 execution

Full excluded qualification completed at {qualification['completed_utc']} in
{qualification['seconds']:.3f} seconds. Its forecast was 1575 seconds and deadline
3150 seconds. All 656 physical batches passed independent replay and exact
serial/parallel comparison of the fixed preflight context.

Production froze at {frozen['frozen_utc']} and started at
{complete['started_utc']}. It completed at {complete['completed_utc']} in
{complete['seconds']:.3f} seconds (59 minutes 44 seconds). The measured forecast
was {frozen['forecast_seconds']} seconds and fixed deadline
{frozen['deadline_seconds']} seconds. Two normal-priority workers used CPUs 6/7
with one numerical thread each. The complete detached sequence took
{read(ROOT/'QUEUE_COMPLETE.json')['seconds']:.3f} seconds, about 79 minutes.

Production retained {complete['retained_bytes']:,} output bytes. Total study size
at closeout was {close['study_bytes_at_review']:,} bytes, below the 6 GiB cap;
free space exceeded the 4 GiB reserve. There were no phase failures, retries,
extensions or scientific changes after qualification. The 1-MiB per physical
batch and phase-level storage allowances remained conservative.

One startup persistence check was performed. Further checks were only at the
user's explicit status requests. The final status turn first inspected new
production results after completion. Independent closeout passed in
{close['seconds']:.3f} seconds. The host check confirmed the controller, two
qualification workers and four production workers from successive block pairs
have exited. No automatic polling or successor is active.

Frozen protocol, source data, qualification and production artifacts are
unchanged. Earlier handoff versions are retained in
completion_handoff_inputs/MANIFEST.json. The revised interpretation is in
README.md; numerical review scope and bindings are in CLOSEOUT.json.
'''
    (ROOT/'EXECUTION.md').write_text(execution)
    stamp = now()
    proposal = 'Cross receiving initial state and forcing stream at fixed feedback and matched 900/1000 horizons; retain preserved/late packets, all conditions and harms. Proposed, not launched.'
    state = dict(study='TT043', status='COMPLETE_REVIEWED', phase='COMPLETE_REVIEWED', observed_utc=stamp,
                 completed_utc=complete['completed_utc'], actual_seconds=complete['seconds'], qualification_seconds=qualification['seconds'],
                 forecast_seconds=frozen['forecast_seconds'], deadline_seconds=frozen['deadline_seconds'],
                 production_started=True, production_completed=True, production_results_inspected=True,
                 no_active_jobs=True, successor_started=False, qualification_status='PASS', confirmatory=False,
                 classification=finding['classification'], source_population_exposed=True, independent_population_blocks=4,
                 all_cases_and_paired_harms_retained=True, new_independent_future_draws=0, new_receiving_conditions=True,
                 verification=complete['verification'], closeout='TT043/CLOSEOUT.json', findings='TT043/FINDINGS.json',
                 current_execution='TT043/CURRENT_EXECUTION.json', automatic_polling=False, automatic_retry=False,
                 automatic_extension=False, automatic_successor=False, proposal=proposal)
    replace_file(ROOT/'CURRENT_EXECUTION.json', state); replace_file(ROOT/'QUEUE_STATUS.json', state)
    old = read(PRIOR/'CURRENT_EXECUTION.json')
    old['authorized_successor'] = dict(study='TT043', status='COMPLETE_REVIEWED', path='TT043/README.md', observed_utc=stamp)
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nTT043 is now complete and reviewed: [receiving feedback](../TT043/README.md).\nIts packet-by-feedback interaction changes with horizon in the primary panel.\nIt does not fully explain the body/recipient gap. TT042 frozen findings remain\nunchanged. No successor to TT043 is active.\n')
    brief = '''

TT043 is complete and reviewed: [receiving feedback](TT043/README.md). Full
qualification took 19 minutes and production 59 minutes 44 seconds on two CPUs.
Every physical continuation passed independent replay; closeout reproduced all
4,032 condition/block reductions and retained paired harms and continuous margins.

In half-mixed residual/own fresh recipients, the late-minus-preserved success
effect at 1000 updates changes from +1.5625 points without feedback to -0.390625
with feedback: interaction -1.953125, negative in all four exposed blocks.
Feedback improves both absolute scores, helping preservation more (+3.125
versus +1.171875 points). At 900 the interaction instead is +2.44140625 points.
Late-packet mean continuous margins remain positive in both settings at 1000,
with a small positive margin interaction. Timing, metric and paired harms cannot
be collapsed into one generic benefit label. The matching continuing-body
interaction is +0.390625 at 900 and -2.734375 at 1000.

Even at 1000 with feedback off in both profiles, continuing and fresh packet
effects retain opposite signs. A state-by-forcing crossover at fixed feedback
and matched horizons is the proposed next diagnosis; no successor is launched.
These are four exposed blocks and reused receiving draws, not new independent
futures or fresh confirmation. Prior classifications are unchanged. All processes
have exited. See [findings](TT043/FINDINGS.json) and [review scope](TT043/CLOSEOUT.json).
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = stamp
    intake['receiving_feedback_development'] = state | dict(report='TT043/README.md', protocol='TT043/PROTOCOL.md',
        predecessor='TT042', full_qualification_pending_at_handoff=False, scientific_results_inspected=True)
    intake['body_packet_exchange_development']['authorized_successor'] = 'TT043 complete and reviewed'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=stamp, study='TT043', event='completed_receiving_feedback_review', source_population_exposed=True,
                 new_production_outcomes_inspected=True, confirmatory=False, new_independent_future_draws=0,
                 all_cases_retained=True, previous_classifications_unchanged=True, successor_started=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT042/CURRENT_EXECUTION.json', 'TT042/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'CURRENT_EXECUTION.json', 'QUEUE_STATUS.json', 'FINDINGS.json',
        'CLOSEOUT.json', 'REVIEW_EXTRA_INPUTS.json', 'RESULT_INSPECTION.json', 'COMPLETION_PROCESS_CHECK.json',
        'COMPLETION_REVIEW_RESOURCE.json', 'admin/review.py', 'admin/complete_handoff.py', 'completion_handoff_inputs/MANIFEST.json')]
    space()
    write(ROOT/'COMPLETION_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
          complete_sha256=sha(run/'COMPLETE.json'), closeout_sha256=sha(ROOT/'CLOSEOUT.json'),
          previous_handoff_versions_preserved=True, scientific_results_inspected=True, successor_started=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), no_active_jobs=True, successor_started=False)))


if __name__ == '__main__': main()
