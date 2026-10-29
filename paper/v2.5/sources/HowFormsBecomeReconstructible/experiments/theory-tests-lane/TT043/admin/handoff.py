"""Record the authorized detached sequence without polling its outcomes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.tt043-pending')
    write(temporary, value); temporary.replace(path)


def main():
    pre = read(ROOT/'checks/preflight_v1/COMPLETE.json'); launch = read(ROOT/'QUEUE_LAUNCH.json')
    startup = read(ROOT/'STARTUP_PERSISTENCE_CHECK.json'); layout = read(ROOT/'LAYOUT.json')
    assert pre['status'] == startup['status'] == layout['status'] == 'PASS'
    assert startup['phase_at_observation'] == 'QUALIFICATION_RUNNING' and pre['inputs'] == inputs()
    verify(pre['outputs']); verify(read(PRIOR/'COMPLETION_HANDOFF.json')['files'])
    for path, record in read(ROOT/'intake_inputs/MANIFEST.json').items():
        assert sha(path) == sha(record['archive']) == record['sha256']
    readme = '''# TT043 — packet usefulness with and without memory feedback

The user authorized this development test after reviewed TT042. The detached
two-CPU qualification and conditional production sequence is launched. At its
single startup observation, full excluded qualification was running; production
had not begun. Dynamic status is in [CURRENT_EXECUTION.json](CURRENT_EXECUTION.json).

TT042 found that changing the supplied packet could have opposite mean effects
in a continuing body and a fresh recipient. Equal final success scores also
concealed differences in physical body states. TT043 tests one defined receiving
mechanism: the feedback gain from the slow R memory field into V.

The four arms cross the actually preserved incoming packet and actually
late-written packet with feedback gain 0 or native gain 0.2. Memory updating
rho remains 0.002 in every arm; writing stays off and theta stays byte-identical.
Within each receiving profile/draw, all four arms share exactly the same initial
body and stochastic forcing. Observers receive labels only after physical
continuation. No new teaching, repair, normalization or feedback-triggered policy.

The continuing profile starts from the preserved body at update 1000 and resumes
its original forcing. The fresh profile uses all four original TT040 receiving
births and draws. Both are observed after 0, 1, 100, 500, 900 and 1000 updates.
The two profiles differ in starting state and forcing; the controlled feedback
contrast is within each profile. Retaining both final horizons makes the original
900-versus-1000 duration difference visible without silently collapsing it.

With feedback off, R still tracks V but cannot feed back into it. The expressed
fresh-receiver fields V/ema/theta reproduce the original assay, whose R was
clamped at zero. This is not full R-state identity. The excluded preflight
independently reproduced both original clamped native assays and checked every
saved expressed field against the new nonfeeding-memory trajectories.

All four exposed TT040 blocks, three packet mixtures, two families, three body
sources, four masks, every task/history and all four role credits remain. Keep
the preserved packet comparator, inherited original-packet readout, individual
paired harms and gains, and block-level results. Primary contrasts in the
half-mixed residual/own panel are the late-minus-preserved effect with feedback
off, the same effect with feedback on, and their interaction, separately for
each profile at 900 and 1000 updates. Continuous score margins are retained as
secondary descriptive outcomes alongside success credit.

These are new intervention conditions on exposed source blocks and reused
randomness. They do not add independent receiving futures, state-local capacity
estimates or a fresh population confirmation. Four population blocks, not their
dependent masks, tasks or receiving draws, are the independent units. The single
continuing-body observation is not repeated four times as receiving evidence.
No new serial-writing confirmation follows automatically.

The small excluded preflight passed in 34 seconds. Its eight physical
trajectories matched 192 independent native arrays, 48 scalar-score checkpoints,
60 saved anchor arrays and 48 saved anchor-score arrays. Invalid context/fields,
a one-ULP packet mutation and a wrong RNG offset were rejected. Fixtures checked
mask and draw weights, retained harms, empty/unequal blocks and all 1008 strata.

Full excluded qualification uses 656 distinct physical batch trajectories across
two excluded blocks, and must reproduce the fixed serial context bitwise. Its
forecast is 26 minutes 15 seconds; its deadline is 52 minutes 30 seconds.
Production has 2704 distinct physical batches across the four exposed blocks.
Its runtime forecast and fixed deadline will be frozen from the measured full
qualification. Production proceeds once only if all checks and limits pass.

The initial storage projection covers approximately 5.35 GiB within a 6 GiB
study cap, preserving a 4 GiB free-space reserve. These are conservative storage
allowances, not expected physical allocation. All writes remain in this lane.
Two normal-priority workers use CPUs 6/7 and one numerical thread each within
the shared 12-CPU ceiling. One startup persistence check passed. The job is left
unpolled until the user requests status, with no automatic retry, extension or
successor. Previous studies' scientific classifications remain unchanged.

See [protocol](PROTOCOL.md), [preflight](checks/preflight_v1/COMPLETE.json),
[layout](LAYOUT.json), [execution](EXECUTION.md) and [queue status](QUEUE_STATUS.json).
'''
    with (ROOT/'README.md').open('x') as f: f.write(readme)
    execution = f'''# TT043 execution

The detached controller PID is {launch['pid']}, acknowledged at
{launch['acknowledged_utc']}. The single startup check passed at
{startup['recorded_utc']}; phase QUALIFICATION_RUNNING, production not started.
Both workers were alive at normal priority on CPUs 6 and 7.

Preflight completed in {pre['seconds']:.3f} seconds; its timed eight-trajectory
context took {pre['timed_context_seconds']:.3f} seconds. Full excluded forecast
{pre['qualification_forecast_seconds']} seconds, deadline
{pre['qualification_deadline_seconds']} seconds. Both excluded blocks retain
their one existing fresh draw. Production retains all four fresh draws per
exposed block; its larger work count is explicitly included in the later
measured forecast. That forecast must be under four hours, with a two-times
deadline. All estimates and bounds are fixed by PROTOCOL.md and QUEUE_PLAN.json.

The byte-only layout counted 656 excluded and 2704 production physical batches
before new outcomes. Its projected total is {layout['projected_study_bytes']:,}
bytes; cap {LIMIT:,} bytes, free-space reserve {RESERVE:,} bytes. Each phase has
one capacity admission. Between trajectories the cap and reserve are checked.
Insufficient resources or failed verification stop the sequence; no retry,
extension, waiting loop or successor is authorized by the controller.

No new production feedback-intervention outcomes existed at preflight/launch.
Source outcomes and the four production blocks were already exposed. All prior
handoff versions are retained in intake_inputs/MANIFEST.json. The physical
code, protocol and input bindings are unchanged after preflight. The detached
controller records completion or failure durably, without result polling.
'''
    with (ROOT/'EXECUTION.md').open('x') as f: f.write(execution)
    old = read(PRIOR/'CURRENT_EXECUTION.json'); old['successor_started'] = True
    old['authorized_successor'] = dict(study='TT043', status='DETACHED_SEQUENCE_STARTED', path='TT043/README.md', observed_utc=startup['recorded_utc'])
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nThe user authorized the proposed receiving-regime diagnosis. [TT043](../TT043/README.md)\nnow supersedes the no-successor status above: excluded qualification and\nconditional production are launched. TT042 findings and frozen artifacts are\nunchanged. No serial-writing confirmation is launched.\n')
    brief = '''

[TT043 receiving feedback](TT043/README.md) is launched on two CPUs after the
small excluded preflight passed. At its single startup check, full excluded
qualification was running and production had not started. The controller will
freeze a measured production forecast and proceed once only if qualification
and resources pass. Full qualification is forecast at 26 minutes 15 seconds.

The test crosses preserved/late packets with feedback gain 0/0.2, holding memory
updating fixed. Each profile pairs identical initial bodies and forcing across
all four arms; continuing and fresh receiving profiles remain separate. All four
exposed blocks, packet conditions, source cases, four original fresh draws,
900/1000-update endpoints, continuous margins and paired harms remain. Original
continuing and fresh-readout anchors replayed exactly in preflight; an independent
equation replay, invalid-input tests and weighting fixtures passed. Feedback-off
fresh R is a nonfeeding tracker, so only its expressed fields match the original
R-clamped assay. No new independent futures, capacity estimate or confirmation
is claimed. Prior scientific classifications are unchanged. The detached job is
unpolled until the user asks; no automatic retry, extension or successor.
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = now()
    intake['receiving_feedback_development'] = dict(study='TT043', status_at_handoff='DETACHED_SEQUENCE_STARTED',
        observed_phase=startup['phase_at_observation'], observed_utc=startup['recorded_utc'], controller_pid=launch['pid'],
        dynamic_status='TT043/QUEUE_STATUS.json', current_execution='TT043/CURRENT_EXECUTION.json', protocol='TT043/PROTOCOL.md',
        preflight_status='PASS', full_qualification_pending_at_handoff=True, source_blocks=BLOCKS,
        source_population_exposed=True, production_started_at_observation=False, new_production_outcomes_inspected=False,
        new_receiving_conditions=True, new_independent_future_draws=0, confirmatory=False,
        all_cases_and_paired_harms_retained=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    intake['body_packet_exchange_development']['successor_started'] = True
    intake['body_packet_exchange_development']['authorized_successor'] = 'TT043 detached qualification and conditional production'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=now(), study='TT043', event='authorized_detached_receiving_feedback_sequence_launched',
                 source_population_exposed=True, full_qualification_pending_at_handoff=True,
                 new_production_outcomes_inspected=False, new_independent_future_draws=0, confirmatory=False,
                 all_cases_retained=True, previous_classifications_unchanged=True, automatic_polling=False, automatic_successor=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT042/CURRENT_EXECUTION.json', 'TT042/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'QUEUE_PLAN.json', 'QUEUE_LAUNCH.json',
        'STARTUP_PERSISTENCE_CHECK.json', 'checks/preflight_v1/COMPLETE.json', 'intake_inputs/MANIFEST.json',
        'LAYOUT.json', 'LAYOUT_INPUTS.json', 'admin/handoff.py', 'admin/check_startup.py')]
    write(ROOT/'LAUNCH_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
          phase_at_startup_observation=startup['phase_at_observation'], dynamic_status_not_hash_bound='TT043/QUEUE_STATUS.json',
          confirmatory=False, scientific_results_inspected=False, automatic_polling=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), scientific_results_inspected=False, automatic_polling=False)))


if __name__ == '__main__': main()
