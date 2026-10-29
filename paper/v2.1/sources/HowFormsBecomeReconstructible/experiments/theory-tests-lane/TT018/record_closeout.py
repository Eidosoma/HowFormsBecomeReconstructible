"""Publish a verified closeout into the existing local handoff documents."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

STUDY = Path(__file__).resolve().parent
LANE = STUDY.parent
RUN = STUDY / 'runs/validation_two_cpu_v1'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def save(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')

closeout = read(STUDY / 'CLOSEOUT.json')
complete = read(RUN / 'COMPLETE.json')
analysis = read(RUN / 'analysis.json')
assert closeout['status'] == 'PASS' and closeout['scientific_verdict'] == complete['scientific_verdict'] == analysis['primary']['verdict']
assert closeout['complete_sha256'] == sha(RUN / 'COMPLETE.json')
assert closeout['closeout_code_sha256'] == sha(STUDY / 'closeout.py')
assert sha(STUDY / 'CLOSEOUT.json') == sha(STUDY / 'closeout_checks/v1/COMPLETE.json')
assert not read(STUDY / 'COMPLETED_PROCESS_CHECK.json')['finished_controller']['scientific_process_active']
assert not (STUDY / 'CLOSEOUT_MANIFEST.json').exists()
now = datetime.now(timezone.utc).isoformat()

current_path = STUDY / 'CURRENT_EXECUTION.json'
current = read(current_path)
current.update(status='COMPLETE_CLOSEOUT_PASS', recorded_utc=now, completion_utc=complete['utc'],
    actual_wall_seconds=complete['seconds'], actual_wall_hours=complete['seconds']/3600,
    scientific_verdict=complete['scientific_verdict'], scientific_job_running=False,
    scientific_outcomes_inspected=True, full_closeout_performed=True,
    closeout='TT018/CLOSEOUT.json', closeout_sha256=sha(STUDY / 'CLOSEOUT.json'),
    closeout_seconds=closeout['seconds'], completed_batches=256, total_batches=256,
    original_absolute_deadline_met=True, current_workers=0,
    interpretation='TT018/INTERPRETATION.md', automatic_polling=False, automatic_successor=False)
current_path.write_text(json.dumps(current, indent=2, sort_keys=True, allow_nan=False) + '\n')

intake_path = LANE / 'prediction_intake_status.json'
intake = read(intake_path)
state = intake['restored_serial_futures_preparation']
state.update(status='COMPLETE_CLOSEOUT_PASS', scientific_job_running=False,
    scientific_outcomes_read=True, scientific_progress_polled=True, completion_utc=complete['utc'],
    completed_batches=256, total_batches=256, actual_wall_seconds=complete['seconds'],
    scientific_verdict=complete['scientific_verdict'], closeout='TT018/CLOSEOUT.json',
    closeout_sha256=sha(STUDY / 'CLOSEOUT.json'), closeout_seconds=closeout['seconds'],
    full_closeout_performed=True, interpretation='TT018/INTERPRETATION.md',
    original_absolute_deadline_met=True, validation_outputs_verified=6800,
    native_array_receipts_verified=62400, primary=analysis['primary'],
    endpoint_counts={endpoint:{policy:value['successes'] for policy,value in values.items() if 'successes' in value}
                     for endpoint,values in analysis['population'].items()},
    paired_primary=closeout['paired_outcomes']['terminal_record'],
    current_workers=0, successor_running=False, automatic_polling=False, automatic_successor=False,
    remaining=[], next_steps=['Completed study is ready for human review',
        'Any equal-budget scheduling or body-source experiment requires its own design and registration'])
intake_path.write_text(json.dumps(intake, indent=2, sort_keys=True, allow_nan=False) + '\n')

readme = '''# TT018 serial reliability from restored records

TT018 is **complete**, with its registered practical primary and retained-evidence
closeout both passing. Repeated repair yields **3,757/4,096 (91.72%)** fresh-recipient
successes, versus **3,585/4,096 (87.52%)** untreated. The gain is **4.20 percentage
points**, with a one-sided 95% lower bound of **2.61**, above the fixed two-point
margin. The two-sided interval is **2.29–6.11** points. Population inference uses
64 independent acquisition blocks; each fixed record has 64 future environments.
See the [interpretation](INTERPRETATION.md), [full report](runs/validation_two_cpu_v1/REPORT.md)
and [closeout](CLOSEOUT.json).

Uninterrupted performance across all eighteen bodies is **90.14%** with repeated
repair versus **77.91%** untreated. This is a separate endpoint. Terminal paired
outcomes retain 213 repeated-only successes and **41 untreated-only successes**.
Three records have a negative estimated repair effect. All nine initially failing
bodies remain enrolled, with each outgoing record assessed across 64 serial futures.
Individual probability estimates and pointwise/simultaneous uncertainty remain in
[record_probabilities.csv](runs/validation_two_cpu_v1/record_probabilities.csv).

The unchanged forecast candidate has lower mean Brier loss in this secondary
transport test. All models underpredict average untreated terminal success;
the candidate's two-sided improvement interval against the unsigned rival includes
zero. Repeated repair uses eighteen calls per chain, versus one for one-time
repair. No equal-budget efficiency or body-source causal claim follows.

The run finished on **13 October 2026 at 21:28:13 UTC**, after **16 hours 16 minutes
39 seconds** from the original start, including the operational pause. At the
user's request, a qualified extension moved the same cohort to two CPU cores,
preserving 513 checkpoint files and all 43 original runtime plus six registration/context
inputs. The original absolute 48-hour deadline remained fixed and was met.
The initial 43.47-hour and later 33.87-hour estimates were conservative forecasts;
they are not a controlled measurement of the realized speedup.

Full native replay ran during execution. Post-completion closeout verifies all
6,800 committed outputs, 62,400 native array receipts, actual successor chains,
registered random-input construction, retained repair construction, raw endpoint
scoring and exact regeneration of analysis/report files. The closeout verifier
was prepared after completed-result inspection and generates no new trajectories.
See [execution](EXECUTION.md), [current execution](CURRENT_EXECUTION.json),
[registration](REGISTRATION.json), [protocol](PROTOCOL.md) and
[execution amendment](EXECUTION_TWO_CPU_AMENDMENT.json).

Preparation history remains preserved: [source review](EVIDENCE_REVIEW.md),
[source bindings](SOURCE_REVIEW.json), [design checks](checks/design_v1/RESULTS.json),
[original draft](DRAFT_PROTOCOL.md), [prelaunch protocol](launch_inputs/TT018/PROTOCOL.md),
[registration-search correction](REGISTRATION_SEARCH_REVIEW.json),
[original qualification](runs/native_v3/qualification.json) and
[two-worker qualification](two_cpu_v1/checks/qualification_v2/COMPLETE.json).
The original launch and prior handoffs retain their historical status fields.
All TT018 test blocks are now exposed. No successor is running.
'''
(STUDY / 'README.md').write_text(readme)
execution_path = STUDY / 'EXECUTION.md'
execution = execution_path.read_text()
header = '# TT018 implementation and execution\n'
assert execution.startswith(header)
addition = f'''
TT018 **completed at 2026-10-13T21:28:13.045347+00:00**. The original-wall elapsed
time is **58,598.727 seconds (16 hours 16 minutes 39 seconds)**, including the
acquisition pause and two-CPU handover. All 256 serial batches, native replay,
analysis and report generation finished before the original 48-hour deadline.
The controller and numerical workers have finished; no successor is running.

The first completed-result inspection was requested by the user at 21:29:09 UTC,
after completion. The registered primary passes: repeated repair yields 3,757
fresh-recipient successes versus 3,585 untreated, out of 4,096 futures per policy.
The 4.20-point gain has a one-sided lower bound of 2.61, above the fixed two-point
margin. See [interpretation](INTERPRETATION.md) and [report](runs/validation_two_cpu_v1/REPORT.md).

Post-completion [closeout](CLOSEOUT.json) passes in **{closeout['seconds']:.2f} seconds**.
It verifies 43 runtime inputs in three copies, six registration/context inputs,
four controller inputs in three copies, all 6,800 validation outputs, 57 original
qualification outputs and 115 controller-qualification outputs. All 516 original
checkpoint commitments (including the archived mutable status) and 513 inherited
files verify. It checks 62,400 native array receipts and regenerates the complete
scoring, uncertainty, forecast, resource and report outputs from retained evidence.
It also reconstructs 77,824 injury/reset environments and checks all 389,120 source
keys and 77,824 saved repair constructions. No trajectories are generated or rerun.

The verifier was prepared after the completed-result inspection. Its corruption
fixtures reject changed packet bytes, added-edge counts and repair magnitudes.
All qualification and handover failures/recoveries remain preserved. The realized
16.28-hour runtime meets the ceiling; comparison with earlier conservative forecasts
does not isolate the causal speedup from using two CPUs. Earlier execution history
follows and does not indicate a still-running job.

'''
execution_path.write_text(header + addition + execution[len(header):])

path = LANE / 'README.md'
text = path.read_text()
paragraph = next(line for line in text.splitlines() if line.startswith('[TT018 is running on two CPU cores]'))
replacement = '''[TT018 is complete](TT018/INTERPRETATION.md) with its registered practical primary and closeout passing. Across 64 new starting records and 64 serial futures each, repeated repair raises fresh-recipient record success from **87.52% to 91.72%**. The gain is **4.20 points** (two-sided 95% interval 2.29–6.11); its one-sided lower bound of 2.61 exceeds the fixed two-point margin. Uninterrupted body performance is separately 90.14% versus 77.91%. The paired terminal comparison retains **41 untreated-only successes** as well as 213 repeated-only successes. Population inference uses 64 blocks; per-record probability estimates retain uncertainty. The unchanged forecast candidate improves the secondary probability score, with calibration, interval and computational limits retained. Completion took **16 hours 16 minutes 39 seconds**, including the requested two-CPU handover. Closeout verifies 6,800 outputs, 62,400 native array receipts and all inherited checkpoints. See [report](TT018/runs/validation_two_cpu_v1/REPORT.md), [closeout](TT018/CLOSEOUT.json) and [execution](TT018/EXECUTION.md). All TT018 blocks are now exposed; no successor is running.'''
text = text.replace(paragraph, replacement)
text = text.replace("The user's explicit TT018 request authorizes two single-thread workers under its", "TT018's completed run used two single-thread workers at the user's explicit request under its")
path.write_text(text)

appendix = f'''

## 13 October 2026 TT018 completed and closed out

TT018 finished at 21:28:13 UTC, before the user-requested completed-result
inspection at 21:29:09 UTC. Original-wall runtime is 58,598.727 seconds: 16 hours
16 minutes 39 seconds, including the acquisition pause and requested two-CPU
handover. The fixed original 48-hour deadline was met. All 256 continuation batches
and the final analysis finished. No successor is running.

The registered fresh-terminal-recipient primary passes. Untreated, one-time and
repeated repair yield 3,585, 3,688 and 3,757 successes out of 4,096 futures per policy.
Repeated-minus-untreated gain is 4.20 percentage points, with approximate two-sided
95% interval 2.29–6.11 and one-sided lower bound 2.61, above the fixed two-point
requirement. Inference uses 64 independent blocks, not 4,096 population units.
Paired outcomes include 213 repeated-only successes and 41 untreated-only successes;
51 records have a positive estimated difference, three negative and ten tied.

Uninterrupted eighteen-body performance is separately 3,191, 3,415 and 3,692
successes. All nine initially failing bodies remain represented. Their fixed
outgoing records now have 64 independent future chains per policy, with widely
different estimated terminal usefulness. Record 18000004 scores 62/64 untreated;
record 18000019 instead falls from 34/64 untreated to 14/64 with either repair
policy. All nine, including zero-success records, appear in the interpretation.
The registered pointwise and simultaneous intervals remain; 64/64 does not imply
certainty. One terminal read per descendant does not characterize that descendant's
own conditional repeated-read reliability.

The unchanged candidate improves the secondary Brier score to 0.054810 versus
0.065100 and 0.067711. All models underpredict average untreated terminal success.
Its two-sided improvement interval against the unsigned rival includes zero.
Repeated repair uses 73,728 calls versus 4,096 one-time calls; this does not establish
equal-budget scheduling efficiency. The body-source causal question remains separate.

Closeout passes in {closeout['seconds']:.2f} seconds. It verifies 43 frozen runtime inputs
in three copies, six context inputs, four controller inputs in three copies,
6,800 validation outputs, 57 native qualification outputs and 115 two-worker
qualification outputs. All 516 original checkpoint commitments and 513 inherited
files verify. It checks 62,400 native array receipts, reconstructs 77,824 injury/reset
environments, verifies 389,120 source keys and 77,824 retained repair constructions,
and exactly regenerates analysis/report files. No trajectories are rerun. The
closeout verifier was prepared after the completed-result inspection; its three
corruption fixtures pass. Original registration and the scheduling amendment
remain distinct and unchanged.

See [interpretation](TT018/INTERPRETATION.md), [report](TT018/runs/validation_two_cpu_v1/REPORT.md),
[closeout](TT018/CLOSEOUT.json), [execution](TT018/EXECUTION.md) and
[current status](TT018/CURRENT_EXECUTION.json). Prior handoffs are preserved in
TT018/closeout_inputs. All test blocks are now exposed. The present claims are
ready for human review; any new timing-policy or body-source test requires its
own design, qualification and registration. No automatic successor was launched.
'''
for name in ('DISCOVERY_LOG.md', 'THEORY_HANDOFF.md'):
    with (LANE / name).open('a') as handle:
        handle.write(appendix)

event = dict(event='TT018_COMPLETED_PROSPECTIVE_SERIAL_FUTURES_CLOSEOUT', study='TT018',
    recorded_utc=now, completion_utc=complete['utc'], scientific_verdict=complete['scientific_verdict'],
    complete_sha256=sha(RUN / 'COMPLETE.json'), closeout_sha256=sha(STUDY / 'CLOSEOUT.json'),
    interpretation_sha256=sha(STUDY / 'INTERPRETATION.md'), independent_blocks=64, futures_per_record=64,
    primary_gain=analysis['primary']['mean'], primary_lower_one_sided95=analysis['primary']['lower_one_sided95'],
    primary_margin=.02, primary_untreated_successes=3585, primary_repeated_successes=3757,
    paired_repeated_only=213, paired_untreated_only=41, validation_outputs=6800, native_array_receipts=62400,
    original_registered_cohort_preserved=True, same_scientific_inputs=True,
    scope='Prospective within supplied simulator; secondary forecasting, unequal repair budgets and conditional per-record uncertainty retained.',
    no_new_trajectories_at_closeout=True, automatic_polling=False, automatic_successor=False)
with (LANE / 'exposure_register.jsonl').open('a') as handle:
    handle.write(json.dumps(event, sort_keys=True, allow_nan=False) + '\n')

links = 0
for name in ('README.md', 'TT018/README.md', 'TT018/EXECUTION.md', 'TT018/INTERPRETATION.md'):
    path = LANE / name
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (path.parent / target.split('#', 1)[0]).exists(), (name, target)
        links += 1
files = ['README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md', 'prediction_intake_status.json',
    'exposure_register.jsonl', 'TT018/README.md', 'TT018/EXECUTION.md', 'TT018/INTERPRETATION.md',
    'TT018/CURRENT_EXECUTION.json', 'TT018/CLOSEOUT.json', 'TT018/closeout.py',
    'TT018/record_closeout.py', 'TT018/COMPLETION_INTAKE.json', 'TT018/CLOSEOUT_INPUTS.json',
    'TT018/COMPLETED_PROCESS_CHECK.json',
    'TT018/closeout_checks/v1/FIXTURE_CHECK.json', 'TT018/closeout_checks/v1/CPU_ADMISSION.json',
    'TT018/closeout_checks/v1/STARTED.json', 'TT018/closeout_checks/v1/COMPLETE.json']
frozen = STUDY / 'closeout_handoff_inputs'
frozen.mkdir()
commitments = {}
for rel in files:
    dest = frozen / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LANE / rel, dest)
    commitments[rel] = sha(LANE / rel)
    assert sha(dest) == commitments[rel]
save(STUDY / 'CLOSEOUT_MANIFEST.json', dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(),
    complete_sha256=sha(RUN / 'COMPLETE.json'), closeout_sha256=sha(STUDY / 'CLOSEOUT.json'),
    frozen_handoff='TT018/closeout_handoff_inputs', files_sha256=commitments,
    local_links_verified=links, scientific_run_outputs_unchanged=True,
    scientific_job_running=False, successor_running=False, automatic_polling=False, automatic_successor=False))
print(json.dumps(dict(status='PASS', scientific_verdict=complete['scientific_verdict'],
    handoff_files=len(commitments), local_links_verified=links, closeout_seconds=closeout['seconds'],
    interpretation='TT018/INTERPRETATION.md'), indent=2))
