# Adaptive calibration: useful learning, but no overall efficiency win

**Completed 22 September 2026.** [Frozen contract](FEP_ADAPTIVE_CALIBRATION_V1.md),
[checker](check_fep_adaptive_calibration.py),
[preceding fixed-budget study](FEP_FACTOR_REVISION_V1_REPORT.md).

The primary **functional gate passes**: an agent that chooses when to stop
calibration still makes useful, costed decisions under shared faults and in
the registered independent/shared average. Planning ahead starts learning
where a one-observation rule refuses to start.

The separate **efficiency gate fails**. The primary controller uses 22.17%
fewer calibration pairs in that average, but net task loss rises slightly,
from .071829050 to .071949614. Its calibration savings do not fully compensate
for the loss of useful evidence in the shared-fault case. Preserve this
failure; do not promote a comparator or change the stopping rule to rescue it.

## What changed

The previous study supplied 64 calibration pairs. This study lets the agent
buy one pair at a time or stop, with the same 64-pair cap, .001 price per pair,
100 later tasks, error/reference costs, priors, factor edit and five truth
fixtures. There is no free initial data, deployment feedback, drift or extra
sensor intervention. Known-positive paired calibration and transfer of its
stationary symmetric error law to deployment remain supplied assumptions.

The primary controller keeps the earlier evidence-selected deployment rule:
join the two error factors if the Bayes factor exceeds 9, then answer or ask
according to the selected model's posterior predictive. Its acquisition
planner retains uncertainty over both structures to predict the consequences
of stopping or continuing. This is a declared modular constraint: the planner
does not override the frozen deployment table after observing its expected
loss. A matched model-averaged deployment controller tests that restriction.

Free energy retains its inference role. Exact conjugate posteriors minimize
VFE within each model, and the structural posterior minimizes VFE over the
two models. The acquisition rule minimizes expected future task loss plus
actual calibration costs. It is ordinary Bayesian planning coupled to VFE
inference, with no intrinsic information bonus or new EFE identity. There is
no distinctive FEP advantage or discovery of a physical shared cause here.

## Primary result: fewer observations, a small quality tradeoff

Net loss is per deployment task, including `.001*E[N]/100` calibration cost.
Lower loss is better. Always asking a perfect reference costs .1 per task
without calibration. The fixed column is read from the sealed prior study.

| Truth | Mean pairs bought | Reaches 64 | Adaptive edit net loss | Fixed-64 edit net loss | Adaptive minus fixed |
|---|---:|---:|---:|---:|---:|
| Independent | 38.27588 | 1.10618% | .046888103 | .047163623 | −.000275520 |
| Shared | 61.34679 | 81.44150% | .097011124 | .096494477 | +.000516647 |
| Partial dependence | 48.52743 | 12.90322% | .083830227 | .084959996 | −.001129768 |
| Anticorrelated | 36.23641 | .81997% | .030907143 | .031213306 | −.000306163 |
| Marginal shift | 50.97407 | 12.23022% | .099588976 | .099698847 | −.000109871 |
| **Equal independent/shared average** | **49.81133** | — | **.071949614** | **.071829050** | **+.000120563** |

The same initial belief leads to buying calibration in every truth fixture;
the agent has not been told which fixture it faces. Later observations change
when it stops. There are no zero-calibration primary trajectories. It learns
to stop earlier on many independent-error histories, while shared errors
usually use the full budget. Median counts are 37 and 64 respectively.

Shared-fault net loss is about **2.99% below always asking**, so useful learning
survives acquisition choice and its costs. The primary average is also below
.1. Both registered positive-use checks pass. Relative to always buying 64,
however, the average saves 14.18867 pairs but increases loss by .000120563 per
task, about **.168%**. This is a small, exactly evaluated failure of the
stronger efficiency claim, not sampling noise.

Under shared errors, the edit's terminal join frequency falls from 98.87049%
in the fixed study to 95.13348% with stopping. Actual wrong-report probability
rises from .035525647 to .035849683, and reference use rises from .603288303 to
.605479726. These together worsen raw loss from .095854477 to .096397656;
the small reduction in calibration cost does not offset it. The lower join
frequency is a descriptive accompaniment, not an isolated causal attribution
of the whole loss increase.

## Strong controls and the retained negative case

All adaptive controls have the same sensing actions, cap and task. The
independent and always-joint controllers each use their own fixed model for
inference and acquisition; the first two retain the full structural posterior
for acquisition. Only deployment differs between edit and model average.

| Truth | Adaptive edit | Adaptive model average | Adaptive independent | Adaptive always-joint |
|---|---:|---:|---:|---:|
| Independent | .046888103 | .046899405 | .046759775 | .048003111 |
| Shared | .097011124 | .097015254 | .110153882 | .096496819 |
| Partial dependence | .083830227 | .083334784 | **.078586100** | .086894722 |
| Anticorrelated | .030907143 | .030907229 | .030935958 | .030817057 |
| Marginal shift | .099588976 | .099583168 | .099566000 | .099678532 |
| Equal independent/shared | .071949614 | .071957329 | .078456828 | .072249965 |

Keeping the independent model remains costly under shared faults despite
adaptive acquisition. Allowing dependence remains useful in this example.
The controllers acquire different data, so this comparison concerns the full
inference/acquisition/deployment systems, not a matched-history isolation of
the factor edit alone; the preceding study supplied that comparison.

The partial-dependence regression persists: edited loss .083830227 is still
worse than the parameter-only controller's .078586100, although both improve
over their own fixed-budget versions. Edited predictive log loss is better
(.835869507 versus .846587183), but it uses the reference more often
(.321893811 versus .186371006). Avoided wrong reports do not pay for all those
references. Model averaging reduces this penalty but does not remove it.

Model averaging saves some observations and slightly improves its own fixed
independent/shared average (.071968824 to .071957329). It nevertheless worsens
the shared-fault cost (.096794066 to .097015254). Always-joint shows a similar
small aggregate improvement with a shared-case loss. These secondary results
do not replace the primary edit controller's failed efficiency gate.

For context, primary future predictive log losses at stopping versus fixed 64
are .845947010 versus .840628994 (independent), .675448038 versus .664154781
(shared), and .835869507 versus .826954236 (partial). Stopping can save task
cost while leaving a less accurate predictive model; forecasting accuracy,
calibration expense and task utility remain distinct endpoints. All five
truths, all controls and full stopping-count distributions are in the record.

## Why looking ahead matters

With no data, the deployment policy asks the reference on every warning.
After any single calibration outcome it still asks on every warning. A
one-step rule therefore compares a task cost of 10 with 10+.001 and buys
nothing. Its actual loss stays .1 per task in every fixture. No initial
observations or forced minimum learning period were supplied to bypass this.

The full controller can value a sequence of observations that eventually
changes decisions. It chooses to begin calibration. This is instrumental
value of future contingent decisions, already present in the Bellman
continuation term; it requires no additional entropy reward.

Prior-predicted total episode costs, before any data:

| Controller | Stop immediately | Optimal stopping | Always buy 64 |
|---|---:|---:|---:|
| Edit | 10 | 7.408596979 | 7.429301965 |
| Model average | 10 | 7.406620522 | 7.425287077 |
| Independent | 10 | 7.367109598 | 7.387039975 |
| Always-joint | 10 | 7.623376214 | 7.637885828 |

The last two rows use different model priors from the first two, so their
predicted values are not direct performance rankings under a common belief.
For the shared full posterior, model averaging has no larger optimal value
than MAP deployment at every count state; this was checked exactly.

The primary controller is optimal within its declared policy family **under
its prior**, yet loses slightly against fixed calibration in the 50/50 test
average. There is no contradiction: that two-truth average is not its prior
over continuous error parameters and structures. Neither correct arithmetic
nor prior-optimal stopping guarantees improvement in every fixed environment.
The failed efficiency gate survives even though the prior predicts a gain.

Two boundary checks retain the meaning of cost and useful timing. With zero
future tasks, positive-cost calibration is skipped. A single calibration
pair costing 11 is rejected initially because it exceeds the entire avoidable
always-reference cost of 10. This is an analytic upper-bound check, not an
additional price sweep or a selected operating price.

## Computation, verification and evidence

The first execution completed without failure, correction, rerun or tuning.
One Python 3.10.12 process took **105.207866532 seconds wall** and
104.534291708 seconds CPU. It ran from
2026-09-22T11:01:12.087874+00:00 to 11:02:57.295722+00:00. No run exceeding
ten minutes or detached job was needed.

At the end of qualification, 3,364 checks had passed in .160 seconds,
including the initial integrity checks. Evidence weights and deployment
tables were matched against the frozen checker. A separate depth-three
ordered-history recursion matched the count-state planner. Direct stopped
path enumeration matched forward propagation, including an intentionally
outcome-dependent stopping rule. Structural/world VFE identities and
no-future-use behavior also passed. These small qualification cases were
not candidate scientific horizons.

The main calculation solved **814,385 count states** for four controllers.
An extra 50,116 likelihood states supply the one-step prediction from the
64-observation boundary; no controller buys a 65th observation. Scaled
integer likelihoods give integer Bellman comparisons, including ties.
There were no full-lattice stop/continue ties. Actual fixed-truth stopping
mass and task costs were then integrated exactly, after policies were fixed.
This correctly accounts for paths that stopped earlier; terminal histograms
were not assigned unconditional multinomial weights.

All 15,239,968 assertions pass, mostly repeated exact arithmetic, deployment
and path-accounting invariants. That count is not a number of independent
experiments. Decisions, costs, stopping probabilities and comparisons are
exact integers/rationals. The maximum recorded binary64 identity residual is
8.881784197001252e-16 against 1e-10. Predictive log losses are numerical
secondary summaries; this identity residual is not a global error bound on
every log-loss aggregate. The verification shares this research workflow and
uses the prior checker as a reference; it is not an independent replication.

Read-only closeout verified **7 input, 13 output and 23 preserved entries**.
The **88,681,020-byte** external record is:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-adaptive-calibration-v1/attempt-01/`

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Prospective contract | 11,546 | `46a41a9542a2b8fb8bf7e0514d04a31ff3cdc87a4370beb6327f1993e200de82` |
| Checker | 23,635 | `eb8ea12631035503de460f1c414b71e44f0d5106fdb9cc6ead86ea290015a46e` |
| PREPARATION.json | 8,660 | `8c54389741ce98e3b124a8d70833f86681642be2b4ab1b552b9e4090d9af4fa6` |
| QUALIFICATION.json | 736 | `2e5c6fb24e284fa74578ad2a17102c2996a2f084858c7793ecbf3ee6c12fd3cc` |
| BELLMAN.jsonl.gz | 15,894,403 | `97bd9ac3e39e631fb3cbda9d4c76e42d93938ca5f3ec3219e125610972b55022` |
| STOPPED.jsonl.gz | 72,250,621 | `305d19e0227d3e180a7740636ded904e8044351fb2a901acb43c595fe19b0f31` |
| RESULTS.json | 326,821 | `1f8e192e63a8b52fc585639f7239027caee141774fbb2c21fd1aceeb78859232` |
| RUN_LOG.txt | 856 | `7689883b612106d3199cdc102354b87fd76de5c910d9cf17e2f4d110aeceafac` |
| MANIFEST.json | 11,775 | `166d3532b5e77f0c618ad23092ceb0cef8d1886950a3e5a4f69c76a5168afb9f` |

The Bellman ledger records every count state's rounded stop/continue values,
exact choices, ties and terminal response codes. The frozen source reconstructs
the exact comparisons. The stopped ledger has 1,412,276 truth/controller/state
rows with exact probability numerators, response codes and predictive loss.
Aggregate results retain rational values and full stopping distributions.
Earlier source, reports, manuscript identities and external evidence remain
unchanged; only the six live notes were updated alongside these new files.

## Next proposed step

Inspect the **saved shared-fault stopping decisions responsible for the small
loss against fixed calibration**, before changing a rule. Distinguish the
consequences of ending observation from those of committing to one model;
model averaging's shared-case regression already rules out treating that
commitment as the sole explanation. Any quantitative attribution should be
declared separately and use the sealed histories, with no tuning of this run.
No successor calculation, manuscript integration or sister-project work is
launched here.
