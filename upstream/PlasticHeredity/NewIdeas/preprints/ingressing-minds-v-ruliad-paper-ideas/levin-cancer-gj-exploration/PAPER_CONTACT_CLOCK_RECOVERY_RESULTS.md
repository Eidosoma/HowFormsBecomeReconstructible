# P10R results: clock-validated renewal under sequential and overlapping contact

Completed **2026-09-15 03:34:04 UTC**, about 16h13m after detached launch.
Run: `runs/paper-contact-clock-recovery-20260914T113138Z-rvzg2jra`.
Job: `runs/jobs/paper-contact-clock-recovery-20260914T112127Z-8om__suw`.
Protocol: [PAPER_CONTACT_CLOCK_RECOVERY_PROTOCOL.md](PAPER_CONTACT_CLOCK_RECOVERY_PROTOCOL.md).

## Result in plain terms

The state passes from three carriers to three fresh cells, and those new cells
replace the carriers entirely. This works through six complete handovers for
both the rewritten-restored-E-founded M lineage and ordinary M, under both
sequential and 50%-overlapping contact. Both numerical resolutions agree.

Blocking miRNA transport or cutting teacher-pupil communication in the first
continuation round leaves all pupils E: no M transmission at that handover.
The screen's simultaneous-contact condition also fails to establish M in pupils.
All six other screened schedules qualify in both histories; only sequential
and 50% overlap were selected by the preregistered rule for full continuations.

| Founder | Sequential | 50% overlap | RNA-blocked continuation | Cut continuation |
| --- | --- | --- | --- | --- |
| Rewritten-restored-E lineage, currently M | 6 complete handovers | 6 complete handovers | Fails at round 2 | Fails at round 2 |
| Ordinary M | 6 complete handovers | 6 complete handovers | Fails at round 2 | Fails at round 2 |

Round 1 is the newly simulated open screen; rounds 2-6 continue its actual
pupils. Controls branch after that shared first round. Prefixes and finer
numerics are not independent biological replicates.

## Verification and failed-attempt handling

All **96 cases**, **754 integration calls**, **47,340 independent checks**, and
**47 coarse/fine comparisons** pass. Of the calls, six are unchanged-native
historical replays and 748 use native equations with bounded clocks. The 860-test
software suite passed in 607.530 seconds before the scientific runner began.
The runner itself used 57,711.9 seconds, with a final independent audit afterward.

Twelve clock diagnostic cases, eight graph calibrations, fifty timing screens
and twenty-four continuations completed. The complete screen has 21,098 checks,
none failed. The seven provenance/integrity flags all pass. A fresh full read-only
audit on September 15 exactly matched the saved final audit (28.05 seconds).
It confirms four history/schedule pairs with control-qualified renewal at both
resolutions. There were 106 newly simulated screen/continuation rounds including
controls and finer cases, not 106 independent lineages.

The old [P10 attempt](PAPER_CONTACT_SCHEDULE_FAILURE.md) remains failed and untouched.
Its six failed checks and ten large overshoots remain in the archived history.
P10R does not reclassify that attempt as a success.

## Meaning and limits

On one common graph, identical cells can have different transmission outcomes
when contact timing changes. Sequential and overlapping handovers can preserve
a state through repeated complete carrier replacement in this finite model.
Open-contact duration does not guarantee equal molecular flux. The seven fixed
schedules are not random timing-noise replicates.

Ordinary M works too; no acquired-history advantage or unique PH mechanism is
demonstrated. Scheduling and fresh cells are externally supplied, and cell division,
autonomous reproduction, fitness and wet-lab behavior are not simulated.

The new clock adapter explicitly changes integration and observation, while
preserving the native biological equations. Finer agreement is a numerical
cross-check, not proof of convergence. The P9 founder and older reference stock
were still inherited historical preparations, not rebuilt under bounded clocks.
P11 addresses that remaining end-to-end preparation gap while testing another
rewrite followed by renewed inheritance.

