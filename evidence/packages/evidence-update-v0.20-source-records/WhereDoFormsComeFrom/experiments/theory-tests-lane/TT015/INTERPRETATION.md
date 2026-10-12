# TT015 checked interpretation

TT015 is complete. Both original directional forecasts reproduce as
**POSITIVE_DEVELOPMENT_EVIDENCE** after full independent replay: repeated repair
improves uninterrupted success across generations 15–32 under matched cue noise,
and retains a positive advantage under independent ongoing cue noise. These are
two results on the same exposed 256 records in 16 blocks, with four blocks per
history. They are not a new confirmatory cohort.

The primary endpoint requires success at every one of the 18 actual
reconstructions. A lineage that fails and later recovers does not pass this
endpoint. All branches continue after failure and inherit their own body-written
successor. Reported intervals below are descriptive 95% stratified block
bootstrap intervals, using the source's 20,000 draws and fixed seed for each
study. Secondary intervals are not adjusted for multiple comparisons. The
original directional criteria are unchanged; no practical or equivalence margin
has been imposed after observing these results.

| Matched-noise policy | Uninterrupted success, generations 15–32 | Success at generation 32 |
| --- | ---: | ---: |
| No repair | 121/256 — 47.27% | 209/256 — 81.64% |
| Repair at generation 15 only | 136/256 — 53.13% | 216/256 — 84.38% |
| Repair before every reconstruction | 233/256 — 91.02% | 247/256 — 96.48% |
| Repeated shuffled-sign repair | 0/256 — 0% | 15/256 — 5.86% |

The serial primary, repeated repair minus no repair, is **+43.75 percentage
points [37.89, 49.61]**, positive in all 16 blocks. In paired uninterrupted
outcomes, 113 records succeed only with repeated repair, one only without repair,
120 under both policies and 22 under neither.

The one-time correction has a smaller secondary uninterrupted benefit of
**+5.86 points [1.95, 9.77]**. Repeated minus one-time repair is **+37.89 points
[32.42, 43.75]**. This supports persistence of some benefit after one correction,
and a much larger benefit from recurring corrective work in this apparatus.
The one-time terminal advantage is uncertain: **+2.73 points [-2.34, 8.20]**.
Terminal recovery is therefore not interchangeable with uninterrupted function.
The results do not establish passive or autonomous maintenance.

| Ongoing cue-noise correlation | No repair: uninterrupted | Repeated repair: uninterrupted | Repair advantage, percentage points |
| --- | ---: | ---: | ---: |
| 1, perfectly matched | 121/256 — 47.27% | 233/256 — 91.02% | +43.75 [37.89, 49.61] |
| .999, slight mismatch | 180/256 — 70.31% | 233/256 — 91.02% | +20.70 [15.63, 25.78] |
| 0, independent | 210/256 — 82.03% | 234/256 — 91.41% | +9.38 [6.25, 12.50] |

The independent-noise row is the cue-noise study's primary. Its repair advantage
is positive in 14 blocks, tied in one and negative in one; 25 records succeed
only with repair, one only without, 209 under both and 21 under neither. The
advantage shrinks mainly because the baseline improves: independent versus
matched noise raises baseline uninterrupted success by **34.77 points
[29.69, 39.84]**, while the corresponding repair change is **+0.39 points
[-0.78, 1.56]**. This is evidence of retained benefit under the tested mismatch,
without an equivalence or noninferiority conclusion. Identical observed
uninterrupted outcomes at correlations 1 and .999, including the zero-width
empirical contrast interval, do not guarantee population equivalence.

Terminal outcomes give a less favorable point comparison for repair across noise
regimes: repeated repair reaches 96.48%, 94.53% and 94.14% at correlations 1,
.999 and 0. Independent minus matched is **-2.34 points [-5.08, +0.39]**, which
remains uncertain. Within independent noise, terminal repair success is 94.14%
versus 90.23% without repair, a **+3.91-point [1.17, 7.03]** difference. The
primary conclusion uses the frozen uninterrupted endpoint, while retaining these
secondary results. All declared contrasts, endpoint summaries, opposite-task
outcomes, history summaries and resource accounts remain in the complete
[serial analysis](runs/audit_v1/serial_analysis.json) and
[cue-noise analysis](runs/audit_v1/noise_analysis.json).

Only ongoing cue-noise correlation changes. Teaching and birth/reset states
remain matched. Independently generated forcing reproduces every retained
generation's noise moments exactly. Measured correlations are 1,
0.9990000168 and 0.0000040946, with marginal variances close to 1. The
1,207,959,552 underlying noise draws per regime are not additional independent
scientific units; inference still uses 16 blocks.

Returning-edge fallback occurs on all 342,830 returning edge events under the
matched baseline, on 38 under matched repeated repair, and on none under either
mismatch regime. These diagnostics reproduce the mechanism change, but do not
identify the causal share of repair's benefit. Changing cue noise also changes
the ensuing body dynamics.

Repeated repair makes 4,608 intervention calls per policy versus 256 for one-time
repair and zero for baseline. All policies allocate 4,096-byte records and 36,864
reader updates per record across the horizon. Equal allocation does not mean
equal total computation or equal information content. Serial repeated and
shuffled repair each add 422,120 edge events, but their summed absolute added
weights differ (415,250.62 versus 385,916.62) as their histories diverge. The
shuffled comparison measures the longitudinal policy effect; it is not an
equal-total-resource comparison. Intervention and audit CPU measurements are
retained separately and are not biological cost estimates.

The detached full audit completed at **2026-10-11 16:02:10 UTC** in **1 hour
27 minutes 8 seconds**, below the 2.82-hour conservative forecast and six-hour
ceiling. It independently verifies 23,296 optimizer slots, 46,080 constructed
records and all 36,864 distinct nonlinear reconstruction contexts. The two
sources contain 46,080 contexts, of which 9,216 matched contexts are identical
overlap, not extra evidence. Every native array matches byte for byte; all 288
generation-level noise checks pass. Independent scoring covers 46,080 raw
endpoints, 92,160 task flags, six CSV tables and all declared summaries. Maximum
scalar-window error is 6.661e-16, safely below the nearest threshold distance
of 0.001066. The maximum scalar added-weight discrepancy, 7.105e-14, satisfies
the previously fixed floating-point bound.

The executable [closeout](closeout.py) passes. It verifies all 314 frozen inputs
in the live study and both job snapshots, all 26 committed full-audit outputs and
eight benchmark outputs, qualification/job chronology, enrollment and successor
continuity, all 1,728 native array receipts and their retained data, every
endpoint summary and contrast interval, paired counts and unchanged scientific
decisions. It generates no new trajectories. Qualified scoring evidence is
reused by hash from the benchmark, on identical inputs. Source scientific
functions are never executed by this audit; qualified independent implementations
are explicitly reused. See the machine-readable [closeout receipt](CLOSEOUT.json),
[completion](runs/audit_v1/COMPLETE.json) and [execution record](EXECUTION.md).

This strengthens the development case for a fixed conventional repair operating
through repeated native rewriting and under independent ongoing cue noise. The
lattice, input pins, reader and optimizer remain supplied. It does not establish
autonomy, transfer to another apparatus, general dispensability of historical
information or a prediction unique to RDT. Serial aggregate outcomes were known
before audit implementation, and the entire cohort was already exposed.
TT014 remains the separate prospective validation over one subsequent
reconstruction; it does not make this serial result prospective.

A next scientific validation would require fresh lineage identities and a
separately frozen serial protocol, with one primary endpoint, a meaningful
practical margin and a sample-size rationale. The independent-noise durability
contrast is a candidate primary; one-time repair and shuffled controls can
clarify the role of recurring work. No successor is launched. Pre-closeout
documents are preserved under `closeout_inputs/`; original scientific inputs,
source snapshots and run evidence remain unchanged.
