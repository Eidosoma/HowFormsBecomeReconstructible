# H4b v1 — Longer unseen histories and the cost boundaries of inheritance

Specified 2026-09-08 before native H4b integration. User authorized the proposed
combined benefit/cost follow-up. H5 self-managed renewal remains separate.

## What is new, and what is unchanged

H4 finished all 76 cases with 112,544 independent checks. Before assigned
contact costs, rewritable inheritance scored 1.00, .90, .80 and .50 across
constant, slow, rapid and misleading worlds respectively, averaged over the two
schedules and two founder polarities. It did not uniformly beat cue-only or
no-information controls. Under the prespecified normalized parent-cost penalty
.10, its mean advantage over cue-only in the slow world disappeared.

Those findings motivated this NEW test, so H4 is exploratory evidence for it.
H4b doubles the trajectory from six to twelve epochs, replaces two scripted
schedules with four new random streams, and separates speed, availability and
cue reliability contrasts. It does not fit parameters, select descendants,
discover new attractors, measure ATP, impose growth/survival fitness, or start H5.

Native code, H4 relay/cue dynamics, source histories, integration settings,
contact geometries and assessment conventions are unchanged. The new runner
uses the immutable H4 trajectory function. Only schedule generation, duration,
analysis and bounded orchestration change.

## Fixed design

Four policies as in H4: rewritable (parent and cue routes on), fixed (parent
only), reactive (cue only), neither (both routes off). Fixed is not a state
clamp. Reactive is not devoid of all intracellular memory: it cannot receive
ancestral state through the modeled junctions.

Profiles specify probabilities per epoch after the initial bootstrap:

| Profile | World flips E↔M | Cue available | Available cue incorrect |
| --- | ---: | ---: | ---: |
| slow_reliable | .15 | .60 | 0 |
| fast_reliable | .75 | .60 | 0 |
| slow_sparse | .15 | .25 | 0 |
| slow_noisy | .15 | .60 | .25 |

This is a one-factor-at-a-time contrast against slow_reliable, not a full
three-way factorial or a universal phase diagram. In particular, it does not
estimate scarcity-by-noise interactions.

PCG64 seeds: 20260908101, 20260908102, 20260908103, 20260908104. Each generates
an 11×3 array of independent uniform draws, columns world-flip, cue-availability,
cue-error. Reuse the same draws across all profiles, policies, E/M polarities
and selected fine checks. A threshold crossing on column 1 flips the previous
hidden world state; column 2 controls cue presence; column 3 flips a present
cue relative to truth. The comparisons therefore have paired stochastic
opportunities while still allowing the new profiles to change those constraints.

Epoch 1 has the founder's hidden label and a present truthful cue. It is a
declared initially aligned bootstrap; it is not a test of acquiring a useful
state from an arbitrary unaligned origin. All later events follow the draws
without forced flips, balanced cue counts, minimum errors, or resampling.
Realized event counts may differ substantially from their probabilities and
are retained as generated. These seeds are disjoint from the two H4 seeds.
No schedule is changed after its draw or outcome is inspected.

128 main baseline cases = 4 profiles × 4 seeds × 2 founder polarities × 4 policies.
8 fine cases = all policies/polarities in slow_noisy at seed 20260908104.
8 registered historical controls = first two epochs of all policies/polarities
from H4's misleading, seed 2026090811, baseline-numerics cases.
Total: 144 cases, 28,016 native integrations, 3,296 fresh lineage recipients.
The fixed generated schedules supply 8,720 fresh cue-cell instances.

Four random streams are a bounded replication improvement, not a large
population sample. E/M polarities and numerical refinements are paired checks,
not independent environmental replicates. Prefix controls do not count as new
held-out tests.

## Physical assay and information boundary

Exactly the H4 assay is used: two actual parents, sequential 1,000-unit
contacts to two fresh recipients, the first recipient's matched wait, isolated
10,000+10,000 holds, and nonforwarded local shadow/challenge branches.
Each current recipient then receives a 100-unit opportunity to meet five
fresh visible-cue cells, followed by isolated 10,000+10,000 holds.
With no cue it spends the 100 units alone. Disabled routes zero all GJ transport.
Every cue cell is removed; both actual post-hold recipients are forwarded.
There are 17 integrations and 42,100 nominal forward units per epoch.
Native solver overshoot is retained, not clipped.

Fresh targets are EM in odd epochs, ME in even epochs, independent of truth.
Contacts, cell opportunities and clocks are paired across policies. Sources
remain the old pre-H4 protein-route M pair and pooled rewritten E incumbents
from distinct protein/RNA routes, not successful H4 descendants. Fine main
cases use the identical baseline source history and refine only new dynamics.

The low-level trajectory function receives visible cues but no desired-state
sequence, probabilities, error labels, cost or reward. No cue reliability is
inferred and then used to grant an extra intervention. The anchor label in old
relay diagnostics refers to the founder, NOT H4b environmental success.
All unsuccessful/mixed descendants continue without rescue or source resets.

## Analysis fixed before execution

Primary state-match and cost scores use epochs 2–12. Also report all-twelve
scores/costs and late-epoch (7–12) performance. Source acquisition and externally
prepared reference-bank costs are not included; all-twelve costs still do not
constitute a complete lifecycle/energy budget.

Report inherited/pre-cue and final/post-hold match fractions, both-correct
frequency, actual cue/error/world-switch counts, conditional subsets, and
checkpoint correction at 22,000/22,100/32,100/42,100 nominal units. Checkpoint
correction is not exact continuous latency. Empty event subsets return null,
not zero. Preserve per-seed/polarity results before aggregation.

Carry forward the whole utility formula:
U = mean match − c_parent × mean(active parent-edge time / 4,000)
               − c_cue × mean(active cue-edge time / 1,000).

Report every point in the 8×8 cost grid, each coefficient from
{0, .025, .05, .075, .10, .15, .20, .30}. Also report the linear utility
coefficients so any assumed nonnegative cost can be evaluated without rerunning
cells. No favorable cost is selected as the sole result. These coefficients
are dimensionless declared contact-burden assumptions, NOT measured molecular
flux, energy, ATP, metabolic scarcity, survival or fitness.

Paired contrasts include rewritable−reactive, rewritable−fixed and the 2×2
interaction. The parent-cost break-even against reactive equals their raw
match difference because their cue burdens are identical and normalized parent
burdens differ by one. Against fixed, cue-cost break-even is their raw match
difference divided by scored cue availability. If availability is zero, report
no differential cue use rather than divide by zero. Negative break-even values
mean no positive cost can rescue that advantage, not a beneficial negative budget.
Cost-independent inequalities and all grid winners/ties/losers are retained.

### A simple binary reference

Additionally compute, without native integration, a prespecified perfect-copy
reference using only visible history. Start with two founder labels. An enabled
parent route copies the previous pair; otherwise start from the scheduled EM/ME
fresh pair. An enabled visible cue immediately sets both labels to that cue;
otherwise preserve the pre-cue labels. Retain those labels through the two holds.

Compare its four checkpoint labels and task scores to the actual native cells
at every epoch. This is a deliberately simple “remember the last hint”
explanation, not a fitted surrogate, optimal decision-maker, new native replicate
or equal-physical-cost comparator. Agreement would show that this task's coarse
observations need no richer explanation; it would not prove identical mechanisms
or absence of richer hidden concentration dynamics. Disagreement is an informative
result, not a failed data-quality gate.

## Provenance, controls and stopping rules

Read-only recompute H4's full independent audit and require exact agreement
with its stored report and all 112,544 checks. Snapshot H4 run/job artifacts
before and after that audit; never resave into the historical run. Freeze 114
source/control files: the existing 72-input bank, H4 summary/audit, eight old
branch records, and 32 historical two-epoch endpoint sets. Verify source states
independently. Preserve the pinned native revision
b2cb370aaecbc8299f259bc4251d5396c81f19a6 and all executed files.

Freeze this protocol, all 144 cases and all execution dependencies BEFORE any
registered native control is run. Execute the eight two-epoch historical controls
first; independently reconstruct their state/identity/transport continuity and
require all 32 historical endpoint sets to match bitwise. The rest of the fixed
panel runs only if this reproduction gate passes. These are registered controls,
not a hidden pilot, and no retuning follows either success or failure.

The final audit independently reconstructs all 144 cases, both sources, every
phase and every forwarded/removed ID. It reuses the same explicitly named
mixed-fresh check replacement as H4 and drops no other relay checks.
Require checkpoint-label and task-score agreement in all eight fine comparisons;
report continuous normalized differences too. Failure blocks strong interpretation,
not permission to tune toward a favored result.

A scientific loss/tie for inheritance, or disagreement with the binary reference,
does not stop the panel. Historical-control, execution, provenance or numerical
failures are kept explicit; no automatic retries or extra cases. Final review,
not this launcher, decides any H5 design.

## Resource limits and validation

Two single-threaded workers, 3,600-second individual case cap, 86,400-second
panel cap including preflight/control gate. Supervisor runner/audit watchdogs:
86,700/1,800 seconds; total 90,000 seconds. At least 5 GiB free before launch,
controls, and each subsequent worker; never delete previous results.
Use durable detached supervision, five-second heartbeat, status, logs and exit
codes. Rough estimate under H4's observed load: 18–22 hours after actual launch;
the 24-hour panel cap is not a completion guarantee.

Before launch, use software-only synthetic fixtures for schedules, negative
benefits, zero-cue subsets, exact cost boundaries, binary-reference mismatch,
complete lineage/audit reconstruction, numerical gates and detached orchestration.
No new native biological pilot integrations precede the fixed panel.

