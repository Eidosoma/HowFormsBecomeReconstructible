"""Record the authorized fresh-future sequence without polling outcomes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(path, value):
    path = Path(path); temporary = path.with_name(path.name+'.tt045-pending')
    write(temporary, value); temporary.replace(path)


def main():
    pre = read(ROOT/'checks/preflight_v1/COMPLETE.json'); launch = read(ROOT/'QUEUE_LAUNCH.json')
    startup = read(ROOT/'STARTUP_PERSISTENCE_CHECK.json'); layout = read(ROOT/'LAYOUT.json')
    assert pre['status'] == startup['status'] == layout['status'] == 'PASS'
    assert startup['phase_at_observation'] == 'QUALIFICATION_RUNNING' and pre['inputs'] == inputs()
    verify(pre['outputs']); verify(read(PRIOR/'COMPLETION_HANDOFF.json')['files'])
    for path, record in read(ROOT/'intake_inputs/MANIFEST.json').items():
        assert sha(path) == sha(record['archive']) == record['sha256']
    readme = f'''# TT045 — new stochastic futures of fixed states and packets

The user authorized this follow-up after reviewed TT044 and reiterated the
request to continue. The detached two-CPU qualification and conditional
production sequence is launched. At its single startup check, full excluded
qualification was running and production had not started. Dynamic status is in
[CURRENT_EXECUTION.json](CURRENT_EXECUTION.json).

TT044 found that the relative usefulness of actual preserved and late-written
packets depends on starting state, realized forcing and observation time. Its
noise-induced relative advantage at 1000 updates accompanied lower absolute
success for both packets. TT045 tests whether packet/state effects persist when
averaging genuinely new forcing futures, retaining both 900 and 1000 horizons.

For every original record/context, restore its one saved continuing state and
all four saved fresh states. Every state receives every one of 16 new future
streams, paired across both packets, all states and all injury conditions within
the block. The new future index is separate from the old birth index. The
Gaussian law, amplitude and native message coupling are unchanged. No state
is regenerated, and no seed is selected by its outcome. All 64 production
block/future addresses were fixed and checked against the prior addresses before
new dynamics. Four excluded seed banks are separate from production.

Feedback stays off, memory updating stays native, writing stays off, and the
finite float64 packet is held byte for byte. Observations occur after 0, 1, 100,
500, 900 and 1000 updates. Retain all four exposed blocks, damage levels,
families, sources, masks, histories, tasks and role credits. The main panel is
half-mixed/residual/own, all histories and masks, target at both terminal
horizons. Retain packet effects in C and F, their interaction, absolute scores,
state effects, all seven contrasts, both ordered decompositions, continuous
margins, paired harms and joint signs across the two terminal times. TT044
endpoints and the inherited original-packet comparator remain separate
historical data with their original case table.

C uses one actual fixed starting state per new future. F averages four actual
fixed starting states, each exposed to every new future. Fixed-state means,
paired packet effects and Monte Carlo standard errors are also retained before
this averaging. Sixteen futures give coarse individual estimates. The Monte
Carlo standard error treats each block/future as the simulation replicate,
averaging its dependent conditions first. Across block seed banks, variances
use squared weights. This measures simulation uncertainty conditional on these
records, not population uncertainty. Zero sampled variance is not certainty.

The source blocks are exposed. The four saved fresh states form an empirical
mixture, not a newly enrolled recipient population. New forcing futures do not
create additional population blocks. No fresh population confirmation, general
capacity, further-writing heredity or uninterrupted-performance claim follows.
Prior classifications remain unchanged. No successor runs automatically.

The excluded preflight passed in {pre['seconds']:.1f} seconds. Four original
baseline trajectories reproduced all {pre['saved_anchor_arrays']} saved physical
arrays and {pre['saved_anchor_score_arrays']} observation arrays. Eight new
trajectories passed pairing and restoration checks. All twelve passed independent
equation replay (288 native arrays and 72 score checkpoints). Invalid fields,
labels, a one-ULP packet mutation and wrong seed/stream/offset were rejected.
Fixtures checked all 1008 strata, weighting, actual continuing denominators,
fixed-state estimates, paired Monte Carlo error, block variance propagation,
paired harms and timing signs. Packed storage expanded byte for byte to all
24 raw arrays; the largest measured package was {pre['largest_new_package_bytes']:,}
bytes, below the {BATCH_BYTES:,}-byte bound.

Qualification uses 656 distinct physical batches across two excluded blocks,
with two new futures and one saved fresh state in each. It must reproduce the
serial preflight context exactly. Its conservative forecast is
{pre['qualification_forecast_seconds']/60:.1f} minutes, with a
{pre['qualification_deadline_seconds']/60:.1f}-minute deadline. Production uses
21,632 distinct physical batches. Its forecast and deadline are set from the
complete two-CPU qualification; production starts once only if the forecast
is below 12 hours and verification, CPU admission and storage checks pass.
Failure of a bound stops the sequence without retry or extension.

The preflight was slower than TT044's. A one-time host diagnostic found other
project work active; no job was stopped or modified. Qualification provides the
measured basis for the production decision rather than assuming yesterday's
throughput. No production future outcomes have been inspected.

The initial conservative storage projection is
{layout['projected_study_bytes']/1024**3:.2f} GiB, within an 18 GiB study cap and
with a 4 GiB free-space reserve. Each held packet is stored once per trajectory,
alongside every V/ema/R checkpoint and all observations. Every package is
expanded and verified exactly; no scientific precision is reduced. Fixed
package/count bounds and the reserve are checked during execution, and actual
study size is checked at block/phase boundaries.

Two normal-priority workers use CPUs 6/7 and one numerical thread each within
the shared 12-CPU ceiling. One startup check passed. Long work is left unpolled
until the user requests status; no automatic retry, extension or successor.
All writes remain in this lane.

See [protocol](PROTOCOL.md), [preflight](checks/preflight_v1/COMPLETE.json),
[layout](LAYOUT.json), [seeds](SEEDS.json), [execution](EXECUTION.md) and
[queue status](QUEUE_STATUS.json).
'''
    with (ROOT/'README.md').open('x') as f: f.write(readme)
    execution = f'''# TT045 execution

Detached controller PID {launch['pid']}, acknowledged at
{launch['acknowledged_utc']}. The single persistence check passed at
{startup['recorded_utc']}; phase QUALIFICATION_RUNNING. Both workers were alive
at normal priority on CPUs 6/7. Production had not started at that observation.

Preflight took {pre['seconds']:.3f} seconds; its eight-new-trajectory timed
context took {pre['timed_context_seconds']:.3f} seconds. Full excluded forecast
{pre['qualification_forecast_seconds']} seconds, deadline
{pre['qualification_deadline_seconds']} seconds. Four old baseline trajectories
were checked separately and are excluded from the forecast multiplier.

The byte-only layout counted 656 excluded and 21,632 production batches.
Production retains all four fixed fresh states and crosses every fixed state
with all 16 new futures; qualification has one fixed fresh state and two new
futures. The larger work count is explicit in the production forecast formula.
The forecast must be below {MAX_FORECAST} seconds, with deadline twice forecast.
This conditional sequence is authorized by the user; no further approval is
needed if the frozen checks pass. It does not extend or retry failed work.

Initial projected study bytes: {layout['projected_study_bytes']:,}; cap:
{LIMIT:,}; free reserve: {RESERVE:,}; per physical package bound: {BATCH_BYTES:,}.
The phase reductions/receipt allowance is 1 GiB. Each package stores one held
theta and all six V/ema/R states; expansion reproduces 24 raw arrays exactly.
No prior study is removed or modified scientifically.

All scientific code, protocol and input bindings remain unchanged after
preflight. Prior handoff versions are preserved in intake_inputs/MANIFEST.json.
The controller records durable completion/failure, with no polling loop.
'''
    with (ROOT/'EXECUTION.md').open('x') as f: f.write(execution)
    old = read(PRIOR/'CURRENT_EXECUTION.json'); old['successor_started'] = True
    old['authorized_successor'] = dict(study='TT045', status='DETACHED_SEQUENCE_STARTED', path='TT045/README.md', observed_utc=startup['recorded_utc'])
    replace_file(PRIOR/'CURRENT_EXECUTION.json', old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nThe user authorized the proposed fresh-forcing follow-up.\n[TT045](../TT045/README.md) now supersedes the no-successor status above:\nexcluded qualification and conditional production are launched. TT044 findings\nand frozen artifacts are unchanged. No serial-writing confirmation is launched.\n')
    brief = f'''

[TT045 new stochastic futures](TT045/README.md) is launched on two CPUs after
the excluded preflight passed. At its single startup check, full qualification
was running and production had not started. Qualification is forecast at
{pre['qualification_forecast_seconds']/60:.1f} minutes. A measured production
forecast below 12 hours, complete verification and resource admission are
required before the one authorized production run starts. No automatic retry,
extension, polling or successor is enabled.

Restore the same exposed packets and one continuing/four fresh states for 16
new paired forcing futures per fixed state. Separate new future index from old
birth index; cross every state with every future. Retain all cases, both 900/1000
horizons, absolute performance, packet advantage, continuous margins, paired
harms and timing signs. All seeds are fixed and distinct from the retained old
addresses. Monte Carlo SE quantifies simulation error conditional on the records;
four population blocks remain. Individual estimates from 16 futures are coarse.
Earlier classifications are unchanged; no population confirmation is claimed.

The preflight independently replayed twelve trajectories, including four old
baselines, and checked lossless packet-once storage, new-stream pairing, exact
weights, Monte Carlo variance, actual continuing denominators and harms.
Production has 21,632 physical batches. The conservative storage projection is
{layout['projected_study_bytes']/1024**3:.2f} GiB within an 18 GiB cap, preserving
4 GiB free. The busy host's throughput will be measured by full qualification.
'''
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f: f.write(brief)
    intake = read(LANE/'prediction_intake_status.json'); intake['updated_utc'] = now()
    intake['fresh_forcing_development'] = dict(study='TT045', status_at_handoff='DETACHED_SEQUENCE_STARTED',
        observed_phase=startup['phase_at_observation'], observed_utc=startup['recorded_utc'], controller_pid=launch['pid'],
        dynamic_status='TT045/QUEUE_STATUS.json', current_execution='TT045/CURRENT_EXECUTION.json', protocol='TT045/PROTOCOL.md',
        preflight_status='PASS', full_qualification_pending_at_handoff=True, source_blocks=BLOCKS,
        source_population_exposed=True, production_started_at_observation=False, new_production_outcomes_inspected=False,
        new_futures_per_fixed_state=16, independent_production_block_future_banks=64,
        fixed_starting_states=dict(continuing=1, fresh=4), population_confirmation=False, confirmatory=False,
        all_cases_and_paired_harms_retained=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    intake['receiving_state_forcing_development']['successor_started'] = True
    intake['receiving_state_forcing_development']['authorized_successor'] = 'TT045 detached qualification and conditional fresh-future production'
    replace_file(LANE/'prediction_intake_status.json', intake)
    event = dict(recorded_utc=now(), study='TT045', event='authorized_detached_fresh_future_sequence_launched',
        source_population_exposed=True, full_qualification_pending_at_handoff=True,
        new_production_outcomes_inspected=False, new_futures_per_fixed_state=16, confirmatory=False,
        all_cases_retained=True, previous_classifications_unchanged=True, automatic_polling=False, automatic_successor=False)
    with (LANE/'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE/n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
                             'exposure_register.jsonl', 'TT044/CURRENT_EXECUTION.json', 'TT044/README.md')]
    files += [ROOT/n for n in ('README.md', 'EXECUTION.md', 'QUEUE_PLAN.json', 'QUEUE_LAUNCH.json',
        'STARTUP_PERSISTENCE_CHECK.json', 'checks/preflight_v1/COMPLETE.json', 'intake_inputs/MANIFEST.json',
        'LAYOUT.json', 'LAYOUT_INPUTS.json', 'SEEDS.json', 'admin/handoff.py', 'admin/check_startup.py', 'admin/CPU_DIAGNOSIS.json')]
    write(ROOT/'LAUNCH_HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
        phase_at_startup_observation=startup['phase_at_observation'], dynamic_status_not_hash_bound='TT045/QUEUE_STATUS.json',
        confirmatory=False, scientific_results_inspected=False, automatic_polling=False))
    print(json.dumps(dict(status='PASS', bound_files=len(files), scientific_results_inspected=False, automatic_polling=False)))


if __name__ == '__main__': main()
