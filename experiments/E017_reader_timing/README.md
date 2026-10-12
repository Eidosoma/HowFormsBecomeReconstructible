# E017 — reader timing

Status: **complete; independent audit and closeout passed**. The prespecified
timing benefit was supported, and staged reading passed all 24 original
reliability/control gates for both consistent learned and engineered records.
All 32 fresh blocks (15000–15031), 128 founders and 129024 scored condition/cue
trials were retained. No job remains running; no renewal study was started.

The comparison used baseline reading (512 updates), unchanged extended reading
(2048), and staged reading (2048, positive linear self-amplification removed for
the first 256). Records, initial states, noise and damage were matched across
timing conditions. The baseline is the exact prefix of the extended trajectory.

For consistent learned records, success under **both opposing cues** was:

| Reader | Intact | Scattered cell loss | Square lesion | Original gates passed |
| --- | --- | --- | --- | --- |
| Baseline | 33.2% | 17.2% | 35.5% | 18/24 |
| Extended | 35.0% | 21.7% | 37.9% | 18/24 |
| Staged | 100% observed | 78.1% | 99.8% | 24/24 |

The single primary comparison, staged minus extended intact both-cue success,
was **+65.04 percentage points [95% whole-block bootstrap: 60.55, 69.53]**.
Extended minus baseline was +1.76 [0.78, 2.93] points, a small secondary benefit.
Delayed amplification therefore helped beyond simply allowing more time.

The original absolute reliability gates concern individual-cue, rule-specific
accuracy, not the both-cue endpoint in the table. Staged individual-cue accuracy
pooled across rules was 100% intact, 89.06% [86.52, 91.50] under scattered loss,
and 99.90% [99.71, 100] under square lesions. All six rule-by-damage absolute
gates and all 18 control-advantage gates passed. The engineered control also
passed all 24 gates, with both-cue success of 100%, 90.23% and 100%, respectively.
Input-isolated responses were exactly identical across cues; both input-isolated
and communication-off controls had zero both-cue successes throughout.

All intervals except the single primary comparison are pointwise secondary
descriptions. Observed 100% success and a degenerate bootstrap interval do not
establish population certainty. Staging supplies an external clock and changes
both early states and total amplification exposure; the result does not uniquely
identify premature commitment as the mechanism. It qualifies this elementary,
explicitly instructed routing task for a future renewal test. Preservation
through body-written replacement, active repair, autonomous goals and
independently active patterns remain untested here.

Simulation/reporting took 730.40 seconds, independent replay 630.29 seconds,
and the detached workflow 1362.17 seconds (22.70 minutes), within the 38.23-minute
forecast. At most 12 CPUs were used, with one numerical thread per worker.
The audit exactly reconstructed teaching, records, masks, reader trajectories,
checkpoints, scores, intervals and gates. Closeout verified frozen inputs and
original outputs, fixture receipts, job references, figure provenance and
unchanged E014–E016 frozen inputs. No retuning or case exclusions occurred.

The readable figure was generated and visually inspected on the completion poll.
Its separate presentation script, unchanged since the benchmark, fixes a
title/legend overlap; frozen plotting code and original outputs are retained.
All writes remained inside the experiment tree.

[Scientific report](runs/timing_v1/REPORT.md),
[readable figure](figures/timing_v1_readable/reader_timing.png),
[independent audit](runs/timing_v1/INDEPENDENT_AUDIT.json),
[closeout](analysis/closeout_v1.json), [frozen protocol](PROTOCOL.md),
[final status](jobs/timing_v1/status.json), [workflow log](jobs/timing_v1/workflow.log).
