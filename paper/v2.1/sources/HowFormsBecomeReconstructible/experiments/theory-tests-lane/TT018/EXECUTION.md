# TT018 implementation and execution

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

Post-completion [closeout](CLOSEOUT.json) passes in **459.85 seconds**.
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


Following the user's request to use two CPUs, the same registered study now runs
under detached controller **4112897**, with two single-thread numerical workers
pinned to distinct physical cores, CPUs **1 and 2**. Current job and output are
`jobs/validation_two_cpu_v1` and `runs/validation_two_cpu_v1`. The observed startup
workers were 4112918 and 4112921; the controller creates a new two-worker pool
when it changes from acquisition to continuation. See [current execution](CURRENT_EXECUTION.json)
and the separate [execution amendment](EXECUTION_TWO_CPU_AMENDMENT.json).

The original process was paused at 05:41:10 UTC after 25 complete acquisitions
and ten complete generations of block 18000025. All **513 inherited files**
were verified and copied without alteration. The incomplete acquisition resumes
from its saved prefix with independent replay; no record is dropped, replaced
or selected by outcome. The original 43 runtime inputs and six registration/context
inputs remain unchanged. All seeds, policies, models, endpoints and inference
remain those of the original registration.

The final [two-worker qualification](two_cpu_v1/checks/qualification_v2/COMPLETE.json)
passes in **429.238 seconds**, with **1,603 byte-exact array comparisons**, preserved
prefix checks, full eighteen-generation chains, terminal assays, and shared CPU
inventory visibility. The earlier numerical qualification passed but is superseded
because its standard multiprocessing launch hid the workers from the shared CPU
inventory; its files and [review](two_cpu_v1/QUALIFICATION_V1_REVIEW.json) remain.
The qualified wrapper makes both numerical workers visible without changing
scientific functions. The latest measured speedup is **1.286 times**, giving a
conservative full-work forecast of **121,929.037 seconds (33.87 hours)**. An earlier
two-worker timing gave 28.52 hours; shared-host timing variation precludes treating
either forecast as a precise completion time. The original absolute deadline,
**15 October 2026 at 05:11:34 UTC**, is retained.

The new controller launched at 06:01:42 UTC and wrote its manifest about 2.69
seconds later. The launcher's two-second startup window was too short, so the
handover receipt was initially absent and the original worker stayed paused.
An [administrative recovery](jobs/validation_two_cpu_v1/STARTUP_RECOVERY.json)
verified the same live controller, both single-thread workers on separate cores,
all inherited evidence, original inputs, qualification and exact process identities.
It completed the [startup check](jobs/validation_two_cpu_v1/STARTUP_CHECK.json)
without restarting the new job. Only then was the paused original PID retired,
at 06:07:36 UTC. The [migration receipt](two_cpu_v1/MIGRATION_COMPLETE.json)
preserves the original output directory and points to the current one.

No scientific outcomes or interim aggregates were inspected during this change.
Checkpoint progress was read only to perform the requested handover. Leave the
long job unpolled until the user asks; no automatic retry or successor is configured.
At closeout, verify both the original registration and this execution amendment,
including all inherited checkpoint hashes. The original launch history follows.

The registered validation started at **2026-10-13T05:11:34.750913+00:00**,
with original detached PID **4093327**, one worker and one numerical thread. The single
startup check passed. Launch admission found three other numerical slots within
the shared ceiling of twelve. Leave the job unpolled until the user requests
status. No automatic retry, replacement cohort or successor is configured.

The original measured full-work forecast was **156,486.633 seconds (43.47 hours)**, including
full independent replay, a 50% timing reserve and a 900-second analysis allowance.
The fixed complete-work ceiling remains 48 hours. Available storage passed the
complete evidence forecast, frozen input copies and separate 1 GiB reserve.
The worker enforces the runtime and storage limits and preserves technical failures.

All 43 runtime inputs and six registration/context inputs match the live and frozen
job copies. Registration preceded the job and first acquisition. The startup
metadata verification checks the saved process/session identity, CPU admission,
software thread settings, input commitments, qualification and test-start binding.
It reads no scientific progress or outcome. See [launch status](LAUNCH_STATUS.json)
and [startup check](jobs/validation_v1/STARTUP_CHECK.json).

Registration SHA-256:
`fa58e9891390ed6bf18310ab1392e55077301d12028328d403d3842f37c89000`.
Qualification completion SHA-256:
`5a4c1f8e03212338d35eb9a731d80fabc4f26dffdb8aefaa96f9bb8047767e26`.

The design uses 64 preassigned records from 64 fresh blocks, 64 independent
future environments each and three policies. All records and forecasts are
sealed before continuation. The additional terminal recipient receives the
actual last outgoing record, without extra repair or writing. This terminal
record endpoint is separate from uninterrupted and last-body performance.
The two-point practical-primary margin, models, streams and sampling were fixed
before TT017 outcome review and remain unchanged.

TT017 completed and passed its prepared closeout before registration. Its
[interpretation](../TT017/INTERPRETATION.md), closeout and completion receipts
are copied into registration_context and bound by the new registration.
TT017's direction did not select or alter TT018's scientific design.

The first native qualification, native_v1, completed its numerical fixtures but
failed final bookkeeping when a one-future test panel overwrote a two-future
variable. That attempt and [failure review](NATIVE_V1_REVIEW.json) remain preserved.
Correcting the fixture variable produced native_v2, which passed in 150.901
seconds with a 41.82-hour forecast. It supplied the original prelaunch evidence.

The first registration attempt then failed before reservation or acquisition.
An unbounded substring search reported five identity-digit fragments in decimal
values as collisions. All five matches and original code are preserved in
[registration_attempts/search_v1](registration_attempts/search_v1/FAILED.json).
The corrected numeric matcher requires complete digit sequences, retains
conservative namespace matching and does not omit any source file. Its 454
positive/negative checks and five source checks pass. This changes register.py
only; the other 42 runtime inputs remain byte-identical to native_v2.

Complete requalification **native_v3** passed in **170.625 seconds**, with all
43 inputs and 57 committed outputs verified. The Python, NumPy and SciPy versions
match qualification. The final protocol appends the disclosed administrative
correction to the unchanged original scientific text; the original is retained
under launch_inputs. The second reservation search checks 20,010 files, finds
no matching identities and passes. Its bounded accessible search does not
establish independent custody or programme-wide exposure completeness.

The final [launch review](LAUNCH_REVIEW_v2.json) binds native_v3, the corrected
matcher, preserved registration failure, unchanged scientific design, TT017
closeout and storage admission. The earlier LAUNCH_REVIEW.json and prelaunch
receipts remain historical evidence. The final launch command was:

```sh
bash run_python.sh TT018/run.py --mode validation --name validation_v1 --qualification native_v3 --host-launch
```

On a later user-requested status check, inspect `runs/validation_two_cpu_v1` for
the durable status and completion or failure receipts. The original run's
`MIGRATED` status is historical. A completed run requires a retained-evidence closeout and
an interpretation preserving a negative or inconclusive primary, unfavorable
secondary findings, calibration limits and computational costs. Do not change
this running study or launch an automatic successor.
