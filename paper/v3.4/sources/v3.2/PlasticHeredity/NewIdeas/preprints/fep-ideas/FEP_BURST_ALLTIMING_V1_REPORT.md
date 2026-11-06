# Full-onset reliability learning: recovery improves, budget robustness is incomplete

Completed and independently verified 31 October 2026 under the
[prospective protocol](FEP_BURST_ALLTIMING_V1.md). This is a new study informed by the failed
[odd-onset candidate](FEP_BURST_LEARNING_V1_REPORT.md), whose evidence remains sealed.

**Restoring every onset to the loss improves recovery substantially, but the
new candidate passes the complete specification in only four of eight new
profiles.** All eight satisfy R<.1 and R<R_hybrid. Four exceed the stable-cost
budget, with the worst excess 10.621%. The overall preregistered result is
therefore failure, with a useful recovery improvement rather than a validated
general solution.

Recovery is 55.0–58.1% cheaper than the previous odd-onset reliability agent on
the same new profiles, including all purchased-feedback fees. This is a
comparison of the two frozen selection pipelines under different losses;
both selected component policies and their mixture weights changed. It is not
a retuning or retrospective validation of the old failed candidate.

## Design and selected policies

The model, costs, information access and ten-task horizon remain unchanged.
The agent jointly infers reversal onset, current sensor error and a fixed
persistence class in {0,.75}, using only purchased targets. Stationary error
marginal .05 is supplied. The orientation reversal prior remains probability
1/2, with all ten onsets equally likely conditional on reversal.

The loss now contains B+R over every onset, with a stable-cost penalty.
The same six mu values {0,1,2,4,8,16} and no-purchase floor form the candidate
pool. Selection minimizes mean training B+R at a=0 and .75, with S<=K at each,
where K=.0955500613134765625. All exact mixture vertices with support at most
three are enumerated. Fifteen are feasible; the selected mixture is:

| Component | Exact episode weight | Approximate weight |
| --- | --- | --- |
| full_mu01 | 23487492538/97007867009 | .242119462 |
| full_mu02 | 73520374471/97007867009 | .757880538 |

Training objective C=.1858516944. Training stable costs are exactly K and
.0915570960. Optimality is restricted to the declared finite pool. Selection
does not impose a separate recovery constraint at each training setting.
At a=0 the selected R=.0968023721 is **.0001277027 higher** than the hybrid's
.0966746694; at a=.75 it improves on the hybrid. This known-setting recovery
failure is retained alongside the new-profile results.

The best of all 1,024 fixed purchase schedules buys on tasks 2 through 10
(mask 1022), using the same reliability posterior and MAP unaided response.
Its S=.095, B=.0995, R=.1085 and B+R=.208 are unchanged across all physical
profiles: only task 1 is unbought, and its marginal error law is fixed.
This is the best schedule within the declared schedule/MAP response class.

The conservative rule, earlier independence-assuming reserve mixtures, hybrid,
always purchasing and both previous odd-onset selected mixtures remain frozen
controls. The reliability-freezing ablation retains orientation learning but
resets the conditional reliability state in real and imagined updates. It
uses the full candidate's selected weights, without its own retuning. An
independent normalized Bayesian Bellman audit checks the matched planner.

## New physical patterns and primary outcome

All candidates and controls were frozen before the new-profile evaluations.
Each profile sets the nine persistence values for transitions between tasks.
Every transition preserves P(error)=.05. Profiles are fixed independently of
orientation and action and are not revealed to the controller.

Four new constant persistences are .2,.4,.6,.8. Two profiles alternate 0 and
.9, starting respectively low or high. Two switch after task 5: four low then
five high transitions, or four high then five low transitions. These varying
profiles test the model's fixed-class assumption. Their component values were
already known; their temporal patterns are new. There is no withheld-onset
loss in this study. Odd/even summaries are descriptive only.

| Held-out profile | New S | New B | New R | Hybrid R | All three criteria |
| --- | --- | --- | --- | --- | --- |
| Constant .2 | .098684439 | .096455879 | .094619588 | .095362825 | Fail: stable budget |
| Constant .4 | .098482195 | .095199918 | .092866534 | .094418826 | Fail: stable budget |
| Constant .6 | .095471134 | .092106366 | .091513088 | .093842335 | Pass |
| Constant .8 | .089990000 | .087343482 | .090223160 | .093842148 | Pass |
| Alternating, starts low | .105698726 | .100318060 | .092281594 | .093152191 | Fail: stable budget |
| Alternating, starts high | .105492918 | .098474720 | .090839383 | .093550633 | Fail: stable budget |
| Persistence begins after task 5 | .093982824 | .091330876 | .091601530 | .095001817 | Pass |
| Persistence ends after task 5 | .092722843 | .092002252 | .095825029 | .096260203 | Pass |

Stable-budget excess is 3.280% and 3.069% for constants .2 and .4, and
10.621% and 10.406% for the alternating profiles. The constant-.6 pass has
only .000078927 cost per task to spare, or .082603% of K. Passing endpoint
training constraints did not protect the intermediate settings or the changing
patterns. These are exact finite-profile results, with no continuous-range
or arbitrary-profile guarantee.

The full-prior mean recovery improvement does not protect every onset.
Onsets 2 and 4 are worse than the hybrid in both full cost and recovery in
all eight profiles. Other onset harms depend on the profile and are retained
in the saved contrasts. Even-onset mean R remains .108533–.114293, above .1;
odd-onset mean R is .068626–.077764. Restoring losses greatly reduces the old
catastrophic timing weakness but does not make onset-level recovery uniform.

## Comparators and reliability-state intervention

Counts below are strict improvements over eight held-out profiles, not
probabilities. Every signed contrast and tie is retained in RESULTS.json.

| Comparator | New S lower | New B lower | New R lower | New B+R lower |
| --- | --- | --- | --- | --- |
| Previous joint reserve mixture | 5 | 5 | 4 | 5 |
| Previous fixed reserve mixture | 4 | 4 | 4 | 6 |
| Hybrid | 5 | 6 | 8 | 7 |
| Always purchasing | 6 | 7 | 8 | 8 |
| Conservative rule | 0 | 8 | 8 | 8 |
| Best fixed schedule | 3 | 7 | 8 | 8 |
| Frozen-reliability ablation | 7 | 4 | 0 | 2 |
| Previous odd-onset reliability agent | 0 | 4 | 8 | 8 |
| Previous odd-onset ablated agent | 4 | 6 | 8 | 8 |
| Matched Bayesian planner | 0 | 0 | 0 | 0 |

The matched Bayesian planner ties exactly. The conservative and fixed-schedule
controls meet K in all eight profiles, but fail both recovery comparisons
throughout. The previous odd-onset reliability agent also meets K throughout
while failing recovery. Improvements over it come with higher stable spending
in every new profile. The earlier joint reserve mixture meets all three
criteria in two profiles; the fixed reserve mixture does so in one.

The new ablation exceeds K in **all eight** profiles. The full reliability
agent lowers stable cost in seven; the exception is alternating-low. It lowers
B+R only for constant .8 and persistence ending after task 5, and its recovery
R is higher than the ablation's in all eight. Thus the predeclared mechanism
criterion requiring both lower R and lower B+R is not met anywhere.

For constant .8, full/ablated S=.089990/.107430, R=.090223/.085594 and
B+R=.177567/.182578. When persistence ends after task 5, full/ablated
S=.092723/.116569 and B+R=.187827/.188905. Reliability updating has useful
budget effects in these comparisons, but the two controllers are never both
budget-feasible on this holdout. The ablation is not separately optimized,
so it does not establish that every independence-assuming policy is inferior.

## Acquisition, interpretation and economic failure

The earlier timing loss left genuine changes largely unexamined. At constant
.4 and reversal onset 10, the old agent buys the remaining target with
probability .088102; the new agent buys it with probability .956410.
Corresponding recovery costs fall from .832404 to .108487. Across all eight
profiles, delay to first post-reversal purchase and missing-feedback probability
both improve relative to the old agent, as do confident-adoption delay and
full-prior orientation Brier loss. The restored loss changes actual evidence
acquisition and useful actions, not just a reporting score.

The remaining stable-cost failure is not uniformly over-purchasing. Compare
the new agent in alternating-low with the same frozen agent at independent
training noise:

| Stable-world quantity | Independent errors | Alternating-low |
| --- | --- | --- |
| Purchases per episode | 8.565792 | 8.440918 |
| Unaided errors per episode | .098921 | .212895 |
| Wrong-confidence task frequency | .000483 | .002475 |
| Orientation Brier loss | .029493 | .040625 |
| Total cost per task | .095550 | .105699 |

Purchases fall by .124874 while errors rise by .113974 per episode. The exact
identity `delta S=(delta errors+.1*delta purchases)/10` gives +.010148665:
saved fees do not compensate the new errors. Relative to the ablation in
this same profile, the full agent saves .690648 purchases but makes .075257
more errors, producing .000619187 higher S. Its wrong-confidence frequency
is still much lower: .2475% versus 2.3058%. Suppressing extreme confidence
therefore does not ensure economic robustness.

The opposite decomposition occurs when persistence ends after task 5.
Relative to the ablation, full reliability saves .187498 errors and .509675
purchases per stable episode, lowering S by .023846540. At constant .8 it
also saves both errors and fees. These improvements are real but conditional.

Wrong-confidence frequency, both stable and full-prior, is lower than the
ablation, hybrid and previous joint reserve mixture throughout all eight new
profiles. Brier improvements are less uniform. Confident orientation adoption
is slower than the ablation and hybrid throughout. Inverting an answer,
believing the orientation changed, purchasing evidence and recovering cheaply
remain distinct: sensor errors can compensate orientation changes. All
adoption/acquisition delays, pre/post-reversal purchases, actual errors,
repeat-message diagnostics and literal inversion metrics are retained.
Stable purchases are counted without assuming the agent knows they are
unnecessary. The observation subsets differ under the intervention; no claim
of an interpretation-only effect on identical observed histories is made.

## Verification, interpretation and next lead

Qualification passed **8,660 assertions** in **4.575 seconds**, including
twelve new exhaustive full/ablated Bellman comparisons through T=3, positive
loss on every onset, inherited filter/projection checks, all 273 short trees
and 6,306 variable-profile tree/world evaluations. Full-history enumeration
matches independent augmented-state flow, with constant-profile reduction,
fixed marginals and the nonconstant lag-correlation identity checked exactly.

The forecast was 326.117 seconds. Main calculation took **75.187 seconds**
and independent verification took **343.676 seconds**, on one CPU at nice 10,
library threads one, no bytecode. Qualification, main calculation and readback
together took about 423.4 seconds: longer than forecast but still below ten
minutes. The audit's full-onset schedule and expanded diagnostic workload
should be included when forecasting any later study.

Independent verification passed **1,522,511 assertions**, including all
354,288 Bellman states, 3,535 candidate graph decisions, all 1,024 fixed
schedules and 1,760 physical graph/world evaluations. It reconstructs Bayesian
posteriors and normalized Bellman expectations without importing the new
planner/evaluator, independently enumerates mixture vertices and verifies
variable-persistence dynamics by augmented-state forward flow. The old
odd-onset agents reproduce all sealed training-setting physical and belief
metrics exactly, with 1,208 additional reproduction checks in the main run.

Candidate selection was frozen at 11:02:45.034340 UTC, before evaluation began
at 11:02:45.158102 UTC. All 22 source/input identities, four snapshots, forty
frozen training files and forty-five manifested outputs verify. No calculation
or verification attempt failed, and no policy was tuned after results. The sealed attempt occupies
**71,924,868 bytes**. Manifest SHA-256:
`261b9437daa64d578e4537098f5fa964015405836697533ce060c2fc67438354`.
Report tables, seven document snapshots and completion provenance are stored
separately in `reporting-2026-10-31-correction-01/`. The original reporting
snapshot is retained; report QA corrected the last decimal of constant-.4 B
from .095199917 to .095199918, without changing exact data. All calculation and verification are
finished; nothing remains running.

During reporting, a text guard incorrectly flagged the word “spending”. Its
failed preflight and original reporter are preserved separately under
`reporting-preflight-failure-01/`. The guard was corrected before archiving;
the scientific calculation and independent verification remained unchanged.

Data belong only under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-alltiming-v1/`.
Source and research notes remain in this folder. All earlier sealed studies,
sister projects and manuscripts remain unchanged.

The FEP-related progress is concrete: a joint model of unreliable evidence can
support economical adaptation, and the action loss must include the changes
the system is expected to handle. This candidate demonstrates conditional
success, with unresolved budget fragility. Bayesian/VFE inference remains the
mechanism; constrained task cost remains the action objective. Matched
Bayesian agreement is an audited legitimate outcome.

**Proposed next lead:** check feasibility of all three constraints within the
existing policy pool across the now-exposed failure patterns before expanding
the model. Any selection using those outcomes would be development work,
requiring fresh prospective holdouts later. This study neither launches that
successor nor tunes its frozen candidate. Do not promote it as a generally
robust controller or integrate it into the larger model on this evidence.
