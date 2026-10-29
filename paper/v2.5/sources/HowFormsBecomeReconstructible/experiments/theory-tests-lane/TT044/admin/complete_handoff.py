"""Save the reviewed crossover interpretation and preserve earlier handoffs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.completion-pending')
    write(temporary, value); temporary.replace(path)


def main():
    run = ROOT/'runs/crossover_v1'; complete = read(run/'COMPLETE.json'); qualification = read(ROOT/'runs/qualification_v1/COMPLETE.json')
    close = read(ROOT/'CLOSEOUT.json'); finding = read(ROOT/'FINDINGS.json'); frozen = read(ROOT/'FREEZE.json')
    assert complete['status'] == 'COMPLETE' and close['status'] == 'PASS' and qualification['serial_parallel_bitwise_equal']
    assert close['complete_sha256'] == sha(run/'COMPLETE.json') and close['findings_sha256'] == sha(ROOT/'FINDINGS.json')
    assert close['review_code_sha256'] == sha(ROOT/'admin/review.py') and read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    verify(frozen['inputs'])
    half = finding['panels']['mix050']['contrasts']
    expected = dict(CC=[-1.5625, -1.953125], CF=[-1.3671875, .78125], FC=[1.171875, -.78125], FF=[-1.7578125, 1.5625])
    for cell, values in expected.items(): assert half['packet_'+cell]['by_time_pp'][-2:] == values
    assert half['state_forcing_packet']['by_time_pp'][-2:] == [-3.125, -.390625]
    assert half['forcing_in_C_T0']['by_time_pp'][-1] == -11.328125
    assert half['forcing_in_C_T1']['by_time_pp'][-1] == -8.59375
    assert half['forcing_in_F_T0']['by_time_pp'][-1] == -6.640625
    assert half['forcing_in_F_T1']['by_time_pp'][-1] == -4.296875
    assert half['packet_gap_FF_minus_CC']['by_time_pp'][-1] == 3.515625
    assert [b[-1] for b in half['state_forcing_packet']['block_effects_by_time_pp']] == [-6.25, -4.6875, 3.125, 6.25]
    near([half['packet_'+c]['continuous_margin_by_time'][-1] for c in CELLS],
         [.0023651119595712276, -.00008677157597465146, .006732444935115661, .007092087203321505])
    for cell, counts in dict(CC=[9, 243, 4], CF=[26, 206, 24], FC=[8, 242, 6], FF=[17, 211, 28]).items():
        assert half['packet_'+cell]['case_harm_tie_gain_by_time'][-1] == counts
    prior = ROOT/'LAUNCH_HANDOFF.json'; previous = read(prior); verify(previous['files'])
    archive = ROOT/'completion_handoff_inputs'; archive.mkdir(exist_ok=False); archived = {}
    paths = set(previous['files']) | {str(prior), str(ROOT/'CURRENT_EXECUTION.json'), str(ROOT/'QUEUE_STATUS.json')}
    for name in sorted(paths):
        source = Path(name); target = archive/source.relative_to(LANE); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); assert sha(source) == sha(target)
        archived[name] = dict(archive=str(target), sha256=sha(target))
    write(archive/'MANIFEST.json', archived)
    table = '\n'.join(f"| {c} | {expected[c][0]:+.4f} | {expected[c][1]:+.4f} |" for c in CELLS)
    harms = '\n'.join(f"| {c} | "+' | '.join(map(str, half['packet_'+c]['case_harm_tie_gain_by_time'][-1]))+' |' for c in CELLS)
    text = f'''# TT044 — receiving state and stochastic forcing

TT044 is complete and reviewed. Full excluded qualification took **10 minutes
58 seconds**; production took **70 minutes 32 seconds on two CPUs**. The whole
detached sequence took about **82 minutes** and finished on 27 October 2026 at
17:23:49 UTC. Independent physical replay and the separate saved-data review
passed. All processes have exited; no successor is running.

The result is a timing-dependent interaction between the supplied packet,
starting state and realized forcing. The same late-written packet can help or
hurt relative to preservation depending on the receiving conditions and readout
time. This diagnoses the remaining TT043 body/recipient gap within these exposed
conditions; it does not identify a generally beneficial starting state or noise
stream.

Feedback is off throughout (c_m=0); memory updating stays native (rho=0.002),
writing is off, and the supplied packet is held byte for byte. C/F mean
continuing/fresh. The first letter selects initial V/ema/R together; the second
selects the realized forcing stream. CC and FF are unchanged TT043 feedback-off
baselines; CF and FC are crossed conditions. The forcing law and amplitude are
unchanged. The continuing stream resumes after exactly 1000 Gaussian fields.

In the main half-mixed residual/own panel, all histories and masks, the
late-minus-preserved target-success effect is:

| State / forcing cell | 900 updates (percentage points) | 1000 updates (percentage points) |
|---|---:|---:|
{table}

At 1000 updates, switching only the forcing changes the packet effect from
-1.953125 to +0.78125 points in the continuing state, and from -0.78125 to
+1.5625 in fresh states. Switching only the state changes -1.953125 to -0.78125
under continuing forcing and +0.78125 to +1.5625 under fresh forcing. Thus the
mean sign at this horizon follows the forcing choice in this panel. It does
not do so uniformly across individual blocks or injuries.

At 900 updates, switching only the state under continuing forcing instead
changes the mean effect from -1.5625 to +1.171875 points. Switching only the
forcing in the continuing state leaves it negative (-1.3671875). With both
changes it is -1.7578125. Both horizons were predeclared. A single terminal
sign cannot establish a persistent advantage or explain the result generally
as either a starting-state effect or a forcing effect.

The 1000-update FF-minus-CC packet-effect gap is +3.515625 points. Both ordered
decompositions hold exactly: changing state first then forcing gives
1.171875 + 2.34375; changing forcing first then state gives 2.734375 + 0.78125.
These are conditional contrasts, not unique causal shares. Their three-way
interaction is -0.390625 points, but its block values are
[-6.25, -4.6875, +3.125, +6.25]. The small mean conceals substantial opposing
block effects. At 900 the interaction is -3.125, negative in all four blocks:
[-3.125, -3.125, -5.078125, -1.171875]. Four blocks provide limited population
information; no significance or confirmation gate was used.

Relative advantage must remain separate from absolute performance. At 1000,
switching the forcing in the continuing state lowers preserved-packet success
from 83.984375% to 72.65625% (-11.328125 points), and late-packet success from
82.03125% to 73.4375% (-8.59375 points). The late packet becomes relatively
better because preservation loses more. In fresh states, the same forcing
switch lowers preserved success by 6.640625 points and late-packet success by
4.296875. These are realized-stream effects, not evidence that fresh noise
improves overall performance or that changing the noise distribution helps.

Paired harms remain. The 1000-update packet contrasts across 256 injury cases
have the following harm/tie/gain counts; CF/FC/FF cases average their four
original paired indices, while CC retains its single actual condition:

| Cell | Harm | Tie | Gain |
|---|---:|---:|---:|
{harms}

For CF, a positive mean coexists with more harmed cases than improved cases;
the sizes of changes differ. These cases come from 64 source positions in four
exposed blocks and are dependent. Position-averaged counts and paired-index
counts remain separate. The CC-only contrast has 64 paired-index observations;
other contrasts have 256, with CC reused only as a shared comparator.

Continuous margins give a different perspective. At 1000 the late-packet
target-versus-best-other margin effects in CC/CF/FC/FF order are
[+0.00236511, -0.00008677, +0.00673244, +0.00709209]. Their signs do not all
match the success effects. Margins and tied-winner success credit measure
different outcomes; neither substitutes for the other or estimates capacity.

Other damage levels are retained. With full replacement, all four cells have
positive mean packet effects at both terminal horizons, also positive in each
block: at 1000, +15.234375, +14.84375, +15.625 and +13.18359375 points in
CC/CF/FC/FF order. With intact packets, all eight cell/horizon mean effects are
negative except CF at 900, whose mean is zero and still contains harms and
gains. The diagnosis is conditional on damage as well as timing and receiving
conditions. All families, sources, tasks, histories, masks, four role credits,
six checkpoints, inherited original-packet controls and 24 contrasts are saved.

These are four exposed source blocks with reused starting states and forcing,
not new independent futures or fresh confirmation. The fresh index d pairs
state d and stream d; this is not a Cartesian product. State replacement
bundles V/ema/R. Sparse checkpoints do not establish uninterrupted performance.
Prior scientific classifications remain unchanged.

The proposed next step is a frozen fresh-forcing replication: restore these
same states and packets, use genuinely new paired forcing seeds, retain both
900/1000 horizons and all cases, and estimate whether the packet/state contrast
persists across futures. This would assess repeatability conditional on the
exposed records; new source records would still be needed for a fresh population
confirmation. No follow-up or serial-writing confirmation has been launched.

Production independently replayed all 3976 physical batches: 95,424 native
arrays matched exactly, 23,856 score checkpoints passed, and 69,120 saved
baseline arrays plus 69,120 saved observation arrays matched. Closeout verified
11,984 output files and 4,072 consumed source files; independently reproduced
all 4,032 condition/block reductions and every global summary; and checked
119,808 case/packet/index endpoint vectors and 2,875,392 margin entries.
CC denominators, all paired harms, and both TT043 baseline endpoints and margins
were checked. Physical dynamics were already independently replayed during
production and were not rerun at closeout. Qualification's separate serial/
parallel comparison passed; production did not repeat that comparison.

See [frozen report](runs/crossover_v1/REPORT.md), [findings](FINDINGS.json),
[closeout](CLOSEOUT.json), [protocol](PROTOCOL.md) and [execution](EXECUTION.md).
'''
    (ROOT/'README.md').write_text(text)
    execution = f'''# TT044 execution

Qualification completed at {qualification['completed_utc']} in
{qualification['seconds']:.3f} seconds, against forecast 824 seconds and deadline
1648 seconds. All 656 physical batches passed independent replay and the fixed
preflight context matched the parallel execution byte for byte.

Production froze at {frozen['frozen_utc']}, started at {complete['started_utc']},
and completed at {complete['completed_utc']} in {complete['seconds']:.3f} seconds
(70 minutes 32 seconds). The measured forecast was {frozen['forecast_seconds']}
seconds; the fixed deadline was {frozen['deadline_seconds']} seconds. The whole
detached sequence took {read(ROOT/'QUEUE_COMPLETE.json')['seconds']:.3f} seconds.
Two normal-priority workers used CPUs 6/7 with one numerical thread each.

Production retained {complete['retained_bytes']:,} output bytes. Total study size
at closeout was {close['study_bytes_at_review']:,} bytes, below the 8 GiB cap;
free space exceeded the 4 GiB reserve. No phase failed, and there were no
retries, extensions or scientific changes after qualification.

One startup persistence check was performed; later checks were user requested.
The 28 October status turn first inspected production results after completion.
Independent saved-data review passed in {close['seconds']:.3f} seconds. The host
check confirmed the controller, two qualification workers and four production
workers have exited. No successor or automatic polling is active.

Frozen artifacts remain unchanged. Earlier handoff versions are retained in
completion_handoff_inputs/MANIFEST.json. README.md contains the interpretation;
CLOSEOUT.json records the independent review scope and evidence bindings.
'''
    (ROOT/'EXECUTION.md').write_text(execution)
    stamp = now()
    proposal = 'Frozen fresh-forcing replication of the same states and packets with new paired seeds, both 900/1000 horizons, all cases and harms; conditional on exposed records. Proposed, not launched.'
    state = dict(study='TT044', status='COMPLETE_REVIEWED', phase='COMPLETE_REVIEWED', observed_utc=stamp,
        completed_utc=complete['completed_utc'], actual_seconds=complete['seconds'], qualification_seconds=qualification['seconds'],
        forecast_seconds=frozen['forecast_seconds'], deadline_seconds=frozen['deadline_seconds'],
        production_started=True, production_completed=True, production_results_inspected=True,
        no_active_jobs=True, successor_started=False, qualification_status='PASS', confirmatory=False,
        classification=finding['classification'], source_population_exposed=True, independent_population_blocks=4,
        all_cases_and_paired_harms_retained=True, new_independent_future_draws=0, new_receiving_conditions=True,
        verification=complete['verification'], closeout='TT044/CLOSEOUT.json', findings='TT044/FINDINGS.json',
        current_execution='TT044/CURRENT_EXECUTION.json', automatic_polling=False, automatic_retry=False,
        automatic_extension=False, automatic_successor=False, proposal=proposal)
    replace_file(ROOT/'CURRENT_EXECUTION.json', state); replace_file(ROOT/'QUEUE_STATUS.json', state)
    old = read(PRIOR/'CURRENT_EXECUTION.json')
    old['authorized_successor'] = dict(study='TT044', status='COMPLETE_REVIEWED', path='TT044/README.md', observed_utc=stamp)
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nTT044 is now complete and reviewed: [receiving state and forcing](../TT044/README.md).\nThe relative packet effect depends on starting state, realized forcing and\nobservation horizon; a larger relative advantage can accompany lower absolute\nsuccess. TT043 frozen findings remain unchanged. No TT044 successor is active.\n')
    brief = '''

TT044 is complete and reviewed: [receiving state and forcing](TT044/README.md).
Qualification took 10 minutes 58 seconds and production 70 minutes 32 seconds
on two CPUs. Physical replay and independent closeout passed for all four blocks,
all 4,032 condition/block reductions, paired harms and continuous margins.

In half-mixed residual/own cases with feedback off, late-minus-preserved mean
success effects at 1000 updates are CC -1.953125, CF +0.78125, FC -0.78125,
FF +1.5625 percentage points. Changing only realized forcing reverses the mean
sign at either state. At 900, effects are -1.5625, -1.3671875, +1.171875 and
-1.7578125: changing only state under continuing forcing instead reverses the
sign. Both horizons were frozen. At 1000 the forcing switch lowers both packets'
absolute success, but lowers preservation more; relative advantage is distinct
from absolute improvement. Paired harms remain and margin signs differ.

The 1000-update packet gap is +3.515625 points, with two ordered decompositions:
1.171875 + 2.34375 and 2.734375 + 0.78125. The three-way mean interaction is
-0.390625, with block values [-6.25, -4.6875, +3.125, +6.25]; at 900 it is
-3.125 and negative in all four blocks. No unique mediated fraction or general
noise benefit follows. Full-replacement packet effects remain positive in every
cell/block at both horizons; intact effects are negative except one zero mean.

These are exposed records and reused forcing. A frozen fresh-forcing replication
with new paired seeds, both horizons and all cases is proposed to assess
repeatability conditional on these records. Fresh population confirmation still
requires new source records. No successor is launched. All processes have exited;
prior classifications are unchanged. See [findings](TT044/FINDINGS.json) and
[review scope](TT044/CLOSEOUT.json).
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = stamp
    intake['receiving_state_forcing_development'] = state | dict(report='TT044/README.md', protocol='TT044/PROTOCOL.md',
        predecessor='TT043', full_qualification_pending_at_handoff=False, scientific_results_inspected=True)
    intake['receiving_feedback_development']['authorized_successor'] = 'TT044 complete and reviewed'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=stamp, study='TT044', event='completed_state_forcing_crossover_review', source_population_exposed=True,
        new_production_outcomes_inspected=True, confirmatory=False, new_independent_future_draws=0,
        all_cases_retained=True, previous_classifications_unchanged=True, successor_started=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT043/CURRENT_EXECUTION.json', 'TT043/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'CURRENT_EXECUTION.json', 'QUEUE_STATUS.json', 'FINDINGS.json',
        'CLOSEOUT.json', 'REVIEW_EXTRA_INPUTS.json', 'RESULT_INSPECTION.json', 'COMPLETION_PROCESS_CHECK.json',
        'COMPLETION_REVIEW_RESOURCE.json', 'admin/review.py', 'admin/complete_handoff.py', 'completion_handoff_inputs/MANIFEST.json')]
    space()
    write(ROOT/'COMPLETION_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
        complete_sha256=sha(run/'COMPLETE.json'), closeout_sha256=sha(ROOT/'CLOSEOUT.json'),
        previous_handoff_versions_preserved=True, scientific_results_inspected=True, successor_started=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), no_active_jobs=True, successor_started=False)))


if __name__ == '__main__': main()
