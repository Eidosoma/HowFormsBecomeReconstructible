"""Record the authorized detached sequence without polling scientific outputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.tt044-pending')
    write(temporary, value); temporary.replace(path)


def main():
    pre = read(ROOT/'checks/preflight_v1/COMPLETE.json'); launch = read(ROOT/'QUEUE_LAUNCH.json')
    startup = read(ROOT/'STARTUP_PERSISTENCE_CHECK.json'); layout = read(ROOT/'LAYOUT.json')
    assert pre['status'] == startup['status'] == layout['status'] == 'PASS'
    assert startup['phase_at_observation'] == 'QUALIFICATION_RUNNING' and pre['inputs'] == inputs()
    verify(pre['outputs']); verify(read(PRIOR/'COMPLETION_HANDOFF.json')['files'])
    for path, record in read(ROOT/'intake_inputs/MANIFEST.json').items():
        assert sha(path) == sha(record['archive']) == record['sha256']
    readme = f'''# TT044 — receiving state and stochastic forcing

The user authorized this development test after reviewed TT043. The detached
two-CPU qualification and conditional production sequence is launched. At its
single startup observation, full excluded qualification was running and
production had not begun. Dynamic status is in
[CURRENT_EXECUTION.json](CURRENT_EXECUTION.json).

With memory feedback off, TT043 still found opposite packet effects in continuing
bodies and fresh recipients after 1000 updates: -1.953125 versus +1.5625 percentage
points in the half-mixed residual/own panel. TT044 crosses the two profiles'
starting states and realized forcing streams to diagnose this remaining gap.
Feedback remains off, memory updating remains native and writing remains off.

Each cell receives either the actual preserved packet or the actual late-written
packet. The four cells are CC (continuing state, continuing forcing), CF
(continuing state, fresh forcing), FC (fresh state, continuing forcing), and FF
(fresh state, fresh forcing). Starting V/ema/R are changed together. The forcing
intervention changes the realized stream, not its distribution or amplitude.
CC and FF must reproduce all six TT043 feedback-off states and observations,
including R. The two crossed cells are the new conditions.

Production uses all four original fresh indices d. CF uses forcing d; FC uses
starting state d; FF keeps the original matched state-d/forcing-d pair. CC has
one actual outcome and is retained once. Its repeated use in paired arithmetic
is a shared comparator, not four body observations or new receiving futures.
This is not a Cartesian product of fresh states and streams.

Retain all four exposed source blocks, three damage levels, two families, three
body sources, four masks, every task/history and all four role credits. Readouts
occur after 0, 1, 100, 500, 900 and 1000 updates. The main panel is
half-mixed/residual/own, all histories and masks, target credit at both 900 and
1000 updates. Report packet effects in each cell, state and forcing effects on
those packet effects, the three-way interaction, and both ordered decompositions
of the FF-minus-CC packet-effect gap. All 24 contrasts, continuous margins,
900-to-1000 changes, inherited original-packet controls and paired harms remain.
Do not assign a unique mediated fraction or substitute margins for success.

This is development informed by exposed outcomes. Four source blocks are the
population units; dependent positions, masks and paired indices are not extra
blocks. Reused starting conditions and forcing do not estimate state-local
capacity or add independent futures. Sparse snapshots do not establish
uninterrupted performance. No fresh confirmation or serial-writing successor
follows automatically. Earlier scientific classifications remain unchanged.

The excluded preflight passed in {pre['seconds']:.1f} seconds. Its eight physical
trajectories matched 192 independently replayed native arrays, 48 score
checkpoints, {pre['saved_anchor_arrays']} saved baseline arrays and
{pre['saved_anchor_score_arrays']} saved observation arrays. State/forcing pairing,
label/field rejection, a one-ULP packet mutation and wrong forcing selector/offset
checks passed. Arithmetic fixtures checked all 24 contrasts, both decomposition
orders, mask/index weights, actual CC denominators, paired harms and empty/unequal
block aggregation across all 1008 condition strata.

Full excluded qualification uses 656 distinct physical batch trajectories in two
blocks and must reproduce the fixed serial context byte for byte. Its forecast
is {pre['qualification_forecast_seconds']/60:.1f} minutes and its deadline is
{pre['qualification_deadline_seconds']/60:.1f} minutes. Production has 3976 distinct
physical batches in four blocks. Its runtime forecast and deadline will be
frozen from the measured qualification, with production conditional on checks,
storage and capacity. No partial significance or success result gates execution.

The initial conservative storage projection is
{layout['projected_study_bytes']/1024**3:.2f} GiB within an 8 GiB study cap, preserving
a 4 GiB free-space reserve. Two normal-priority workers use CPUs 6/7 and one
numerical thread each within the shared 12-CPU ceiling. One startup persistence
check passed. Long work is left unpolled until the user requests status, with no
automatic retry, extension or successor. All writes remain in this lane.

See [protocol](PROTOCOL.md), [preflight](checks/preflight_v1/COMPLETE.json),
[layout](LAYOUT.json), [execution](EXECUTION.md) and [queue status](QUEUE_STATUS.json).
'''
    with (ROOT/'README.md').open('x') as f: f.write(readme)
    execution = f'''# TT044 execution

Detached controller PID {launch['pid']}, acknowledged at
{launch['acknowledged_utc']}. The single startup persistence check passed at
{startup['recorded_utc']}; phase QUALIFICATION_RUNNING, production not started.
Both workers were alive at normal priority on CPUs 6 and 7.

Preflight: {pre['seconds']:.3f} seconds; timed eight-arm context:
{pre['timed_context_seconds']:.3f} seconds. Full excluded forecast:
{pre['qualification_forecast_seconds']} seconds; deadline:
{pre['qualification_deadline_seconds']} seconds. Each excluded block retains one
fresh index. Production retains four fresh indices per block; CC remains one.
The later production forecast explicitly uses the larger physical work count,
must be below four hours, and sets a fixed two-times deadline. These rules were
specified before crossed production outcomes.

The byte-only layout counted 656 excluded and 3976 production physical batches.
Its conservative projected total is {layout['projected_study_bytes']:,} bytes;
study cap {LIMIT:,} bytes, reserve {RESERVE:,} bytes. Capacity admission occurs
once per phase. The cap/reserve are checked between trajectories. Failed
verification or insufficient resources stops the sequence; there is no retry,
extension, waiting loop or successor.

Source blocks, outcomes and unchanged CC/FF baselines were already exposed;
new production crossed-condition outcomes did not exist at preflight/launch.
All previous handoff versions are retained in intake_inputs/MANIFEST.json.
Scientific code, protocol and input bindings remain unchanged after preflight.
The controller records completion or failure durably without result polling.
'''
    with (ROOT/'EXECUTION.md').open('x') as f: f.write(execution)
    old = read(PRIOR/'CURRENT_EXECUTION.json'); old['successor_started'] = True
    old['authorized_successor'] = dict(study='TT044', status='DETACHED_SEQUENCE_STARTED', path='TT044/README.md', observed_utc=startup['recorded_utc'])
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nThe user authorized the proposed receiving-state/forcing crossover.\n[TT044](../TT044/README.md) now supersedes the no-successor status above:\nexcluded qualification and conditional production are launched. TT043 findings\nand frozen artifacts are unchanged. No serial-writing confirmation is launched.\n')
    brief = f'''

[TT044 receiving state and forcing](TT044/README.md) is launched on two CPUs after
the excluded preflight passed. At its single startup check, full excluded
qualification was running; production had not begun. Qualification is forecast
at {pre['qualification_forecast_seconds']/60:.1f} minutes. The controller will freeze
a measured production forecast and proceed once if qualification and resources
pass. Long work remains unpolled until the user requests status.

At fixed feedback off, preserved/late packets are evaluated in CC/CF/FC/FF cells
crossing continuing/fresh initial states and realized forcing streams. Both
unchanged TT043 baselines replayed exactly in preflight, including R. The design
retains all four exposed blocks, all cases, four original fresh indices,
900/1000-update outcomes, continuous margins and paired harms. CC has one actual
observation, shared only as a comparator. Both ordered decompositions are kept;
no unique mediated fraction, new independent futures, capacity estimate or fresh
confirmation is claimed. All 24 contrast and weighting fixtures passed. Prior
scientific classifications are unchanged. No automatic retry, extension or
serial-writing successor follows.
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = now()
    intake['receiving_state_forcing_development'] = dict(study='TT044', status_at_handoff='DETACHED_SEQUENCE_STARTED',
        observed_phase=startup['phase_at_observation'], observed_utc=startup['recorded_utc'], controller_pid=launch['pid'],
        dynamic_status='TT044/QUEUE_STATUS.json', current_execution='TT044/CURRENT_EXECUTION.json', protocol='TT044/PROTOCOL.md',
        preflight_status='PASS', full_qualification_pending_at_handoff=True, source_blocks=BLOCKS,
        source_population_exposed=True, production_started_at_observation=False, new_production_outcomes_inspected=False,
        feedback_gain=0., new_receiving_conditions=True, new_independent_future_draws=0, confirmatory=False,
        all_cases_and_paired_harms_retained=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    intake['receiving_feedback_development']['successor_started'] = True
    intake['receiving_feedback_development']['authorized_successor'] = 'TT044 detached qualification and conditional production'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=now(), study='TT044', event='authorized_detached_state_forcing_crossover_launched',
                 source_population_exposed=True, full_qualification_pending_at_handoff=True,
                 new_production_outcomes_inspected=False, new_independent_future_draws=0, confirmatory=False,
                 all_cases_retained=True, previous_classifications_unchanged=True, automatic_polling=False, automatic_successor=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT043/CURRENT_EXECUTION.json', 'TT043/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'QUEUE_PLAN.json', 'QUEUE_LAUNCH.json',
        'STARTUP_PERSISTENCE_CHECK.json', 'checks/preflight_v1/COMPLETE.json', 'intake_inputs/MANIFEST.json',
        'LAYOUT.json', 'LAYOUT_INPUTS.json', 'admin/handoff.py', 'admin/check_startup.py')]
    write(ROOT/'LAUNCH_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
          phase_at_startup_observation=startup['phase_at_observation'], dynamic_status_not_hash_bound='TT044/QUEUE_STATUS.json',
          confirmatory=False, scientific_results_inspected=False, automatic_polling=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), scientific_results_inspected=False, automatic_polling=False)))


if __name__ == '__main__': main()
