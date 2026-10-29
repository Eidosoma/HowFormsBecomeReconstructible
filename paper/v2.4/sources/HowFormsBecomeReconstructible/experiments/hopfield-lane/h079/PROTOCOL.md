# H079 — fresh replication of query-onset feedback timing

Authorized after H078's completed status on 23 October 2026. Replicate the
unchanged H078 comparison on **192 fresh independent networks**, with four
separate engineering networks. Root seed **79079**; fixture, engineering and
replication namespaces and named response/birth/order streams remain distinct.
Freeze this protocol and all executable dependencies before opening new
numerical outcomes. No tuning, optional stopping, replacement seeds, exclusions,
inherited transition, predictor search or automatic successor is included.

## Unchanged experiment

Import H078's production dynamics directly. Preserve its 128 binary neurons
(32 context, 48 query, 48 response), four context codes, two opposite query
codes and eight independently sampled balanced response patterns. Teach all
eight associations using the same projection rule, SVD tolerance and zero
diagonal. Evaluate taught associations only. All record sizes, ordinary
linear/quadratic LS and nearest-history readers, and their explicit 80-value
cue-history buffers remain unchanged. Acquisition/computation are not matched.

Each network supplies four births shared across eight queries and all arms.
Prepare with four context-clamped sweeps, followed by zero or four unclamped
gap sweeps under full J; gap four remains primary. Every schedule/horizon
branches from the exact same prepared state, cues, record and update orders.
The response is never clamped or reset, and the reader receives no target.

Only response-to-response couplings change during the eight-sweep query
window: on=[1,1,1,1,1,1,1,1], delayed=[0,1,1,1,1,1,1,1],
off=[0,0,0,0,0,0,0,0]. All other connections remain. Zero, one and eight active
free-neuron sweeps retain the complete schedule/clamp clock, holding state
after the allowed updates. Zero updates and feedback off remain distinct.
Preserve own, swapped-context, absent-context, foreign-record and erased
conditions, intended/donor scores, query/bit/exact outcomes, all paired harms,
context retention, flips, nominal target stability and actual endpoint flags
under both scheduled and restored matrices. Switch work, clamp work and neural
energy reductions remain separately balanced.

## Fixed sample size and precision

The independent observation is a network's complete-task fraction in [0,1],
averaged over its four related births. A task requires all eight queries, each
with at least 44/48 correct response bits. Main totals are **768 tasks and
6,144 queries**; these are not the inferential sample size.

Use a conservative bounded-independent-observation interval for the primary
delayed/own/gap-four/eight-sweep mean. For n networks, its unclipped half-width
is `sqrt(log(2/0.05)/(2*n))`. A target of at most 0.10 requires
`ceil(log(40)/(2*0.10^2)) = 185` networks. Fix **192**, rounding upward to a
multiple of four; the half-width is approximately **0.09801**. Clip limits to
[0,1]. This bound uses independence and the known range, without a pilot
variance assumption or treating related tasks as independent. It remains
nondegenerate for all-zero/all-one samples.

This application follows [Hoeffding (1963), Theorem 2](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf).
The probability statement concerns new networks drawn from the declared
sampling model, using separate pseudorandom streams; it is not uncertainty
over arbitrary architectures, task distributions or undisclosed tuning.

## Separate verdicts

Keep H078's seven point-estimate capability gates unchanged, separately for
each schedule: complete tasks >=0.75; eight-minus-one >=0.10; eight-minus-zero
>=0.25; own-minus-each of four context/source controls >=0.50. All seven must
pass for `ITERATIVE_READER_CAPABILITY_SCREEN_PASSED`; otherwise retain
`ITERATIVE_READER_CAPABILITY_SCREEN_FAILED`. A passing point screen is not a
population lower-bound guarantee. Separately report whether the primary
absolute 95% lower bound reaches 0.75.

Prospectively define one family of three paired **complete-task** contrasts
at own/gap four: delayed-eight minus on-eight, off-eight, and delayed-one.
Each network contributes a paired difference in [-1,1]. For each difference,
use the one-sided lower bound
`mean - 2*sqrt(log(3/0.05)/(2*n))`, clipped below at -1. Each tail is allocated
0.05/3; the union bound gives simultaneous coverage of at least 95% for this
three-contrast family. At n=192 the subtracted radius is approximately 0.20652.
No sign-symmetry, normality or independent-query assumption is needed.

Declare `TIMING_AND_ITERATION_BENEFIT_REPLICATED` only when **all three lower
bounds exceed zero**. Otherwise declare
`NO_QUALIFIED_TIMING_AND_ITERATION_REPLICATION`. This joint timing/iteration
decision and the unchanged capability decision are reported even if they
disagree. The absolute interval and this family have separate 95% coverage
statements; no joint 95% coverage across both is claimed.

Retain all 1,784 H078-style descriptive two-sided network bootstrap intervals,
using 20,000 draws at seed **7907901**, alongside these bounds. They do not
replace the prospective decision or acquire a multiplicity guarantee. Retain
all stronger ordinary comparators and their gaps; no qualified superiority,
efficiency, copying, inheritance or RDT-forecast claim is defined here. Do not
pool H078's exposed eight networks into this replication or rescue a failed
primary using zero gap, individual queries, donor results or secondary arms.

## Verification, execution and preservation

Use H078's independent rational/extended-precision replay unchanged apart from
the new tape namespace. Keep weights 4e-14, projection identities 2e-13,
fields/energy/work balance 2e-11 and table sums 2e-9. Discrete states/flips/flags
must agree exactly. A reference field within 5e-14 of a +/-1e-12 update threshold
fails execution without excluding a network. Require full erasure, common
prequery states, serialized reloads and all controls to pass their audits.

Run the existing 17 H078 fixtures plus checks for unchanged dynamics/audit
code, new fixture streams, network-level bounds, negative/null effects,
nondegenerate extreme-sample uncertainty, duplicate-network rejection, paired-
count corruption, no engineering verdict and a complete H079 report. Perform
an additional full audit of a new fixture network before engineering.

Benchmark the same four new engineering networks serially and with four
workers. Require exact arrays/audits/tables; select four if speedup >=1.15,
otherwise one, before main. Forecast main as 1.25 times the selected four-
network batch duration times 48, plus 120 seconds for reporting. Each worker
uses one numerical thread; admission respects the shared twelve-slot ceiling.
Runs forecast above ten minutes or sustained capacity waits remain detached,
with unique logs/PID, durable progress and automatic report/integrity closeout.
Shorter forecasts use the authorized watcher loop. No intermediate outcome
controls continuation or sample size.

Bind H078's completed manifest, selected context artifacts and the completed
interpretation/review sources; import no numerical network. Keep H078's passing
development screen and H076/H077's failures intact. Preserve H031's causal
result separately from its forecasting failure and both H033 verdicts, with
H071's failed screens unchanged. Richer inherited tasks remain a separate
priority. All writes stay in this lane; no private quotation or public
manuscript edit is authorized by this protocol.
