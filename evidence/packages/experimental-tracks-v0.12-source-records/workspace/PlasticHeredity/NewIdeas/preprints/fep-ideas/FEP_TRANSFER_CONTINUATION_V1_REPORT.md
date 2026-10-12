# Transfer checking becomes useful when it can change a later FEP action

**Subsequent scientific review:** the
[19 September assumption review](FEP_TRANSFER_CONTINUATION_REVIEW_2026-09-19.md)
preserves this calculation and qualifies its generalization. Matching past
calibration need not imply the assumed future dynamics; some failures remain
invisible under the chosen checks. Marginalizing hidden state also changes
the FEP ranking unless the removed conditional term is retained. Frozen inputs
and results below are unchanged.

**Completed 19 September 2026.** The
[prospectively specified three-record model](FEP_TRANSFER_CONTINUATION_V1.md)
passes its main prediction: paid recalibration improves net utility from
**0.625 to 0.638** when its evidence can guide a later choice. State-preference
FEP, the three declared information extensions and matched Bayesian planning
all select the same unique policy in this main case.

The [checker](check_fep_transfer_continuation.py) passed on its first execution:
twelve fixed fixtures, 23,520 terminal choices and 60 complete optimum sets.
The calculation took **17.471792667 seconds on one process**. There was no
retuning or rerun. This is an exact finite-model result, not sampled biological
evidence or an advantage unique to FEP.

## 1. A check now has a later decision in which to matter

Records 0 and 1 contain independent calibration targets; record 2 contains
the sole rewarded target. Both calibration opportunities are optional and
paid. Relative to the preceding model, record 1 is now a diagnostic opportunity,
with no task reward; the final task is on record 2. Comparisons below use
controls inside this new endpoint rather than comparing different total rewards.

The reader can consistently copy or invert content. Its unknown episode-wide
class either preserves orientation across all three records, with prior
probability 0.75, or redraws orientation independently. Content has a separate
unknown intact/erased class, with intact probability 0.5. Independently grounded
references have reliability 0.9. These classes, priors and reference properties
are supplied; the agent infers the realized mechanisms within that family.

The winning policy buys both calibration read/reference pairs, costing 0.025
each. It compares the orientation suggested by each pair:

| Calibration suggestions | Frequency | Final action | Conditional accuracy |
|---|---:|---|---:|
| Agree | 0.62 | Copy or invert the final read using their shared suggestion | 23/31, about 0.741935 |
| Disagree | 0.38 | Pay 0.30 for the final independent reference and report it | 0.900000 |

Total accuracy is 0.802. Subtract 0.050 for calibration and 0.114 for final
reference access, giving **0.638**. No maintenance is selected in this case.
The best policy with at most one calibration earns **0.625**, whether that
single calibration uses the old or the more recent record. Using neither
earns **0.600** through maintenance or direct reference use.

Thus the gain is not explained by comparing against a controller forced to
use stale calibration. The fresh single-calibration alternative is included.

## 2. The benefit depends on changing the later resource choice

After the first anchor, the best final value before further calibration costs
is 0.650. Seeing the second anchor before choosing the final action raises
expected final value to 0.688. Its gross value is **0.038**. Paying 0.025
therefore leaves the observed **0.013** gain.

In the timing control, the agent must choose maintenance and final reference
access before seeing the second calibration. Its eventual report is still
allowed to use that calibration. All four committed action pairs and all
their history-dependent reporting maps were considered.

The best such policy with both calibrations earns only **0.600**. Two
equal-quality orientation suggestions do not improve average report accuracy
alone: agreement strengthens the estimate, while disagreement creates a tie.
Allowing the constrained planner to skip the second purchase recovers 0.625.
The extra evidence pays here because it tells the agent **when to buy a
different information source for the final answer**.

At a second-anchor price of 0.038, buying and skipping tie. Each of the four
first-anchor histories can make that choice independently, yielding sixteen
complete Bayesian/state policies, all at utility 0.625. At price 0.055,
Bayesian/state FEP declines the second anchor and retains 0.625.

## 3. A control isolates uncertainty about transfer

The main case updates beliefs about content, orientation and transfer together.
It should not be described as a pure test of learning transfer. Indeed, even
when persistence is known, noisy calibration and uncertain content can still
make a second check useful.

The separate **transfer-isolated** fixture sets content to known intact and
both calibration references to perfect. Their comparisons then reveal the
two past orientations exactly. Uncertainty remains about whether that mapping
will persist to the final record.

- The comparisons agree with probability 7/8. The posterior probability of
  the stable class becomes 6/7, and using the inferred interpretation gives
  final accuracy 13/14.
- They disagree with probability 1/8. This identifies the reset class, so
  even the correctly known recent orientation cannot predict the next one.
  The agent maintains the final reader instead.

State-preference FEP and Bayesian planning obtain accuracy 15/16 and net
utility **0.86875**, versus **0.85000** with at most one calibration or
unconditional maintenance. Maintenance occurs only in 1/8 of episodes.
This establishes a value for transfer-sensitive action within the supplied
family, with the strong reference assumptions made explicit.

The task-information extension chooses unconditional maintenance instead,
scoring 0.85. Its extra preference for task certainty favors perfect reporting
despite the lower costed utility. The full and mechanism extensions match the
Bayesian/state policy in this control.

## 4. What is specifically being checked about FEP

Exact posterior inference satisfies the variational identity

```text
F(q;o)=KL(q || P(W|o))-log P(o).
```

The checker verifies it at both calibration stages for exact and perturbed
posteriors. The same inference is available to every planner. No iterative
variational approximation or model-family discovery is tested.

With the declared full trajectory state, all physical randomness is retained
in W and policy-dependent actions/readouts are deterministic extensions.
Therefore H(S)=H(W) for every policy. State-preference FEP reduces to

```text
J_state=log Z_C-beta*U-H(W).
```

Its complete optimum sets equal Bayesian planning throughout all twelve
fixtures. The exact outcome-risk plus conditional-KL decomposition also holds;
the conditional term was retained. Useful information acquisition arises from
its consequences for future preferred outcomes even without an added explicit
information bonus.

The three extensions instead subtract information about the full trajectory,
the final target, or the future mechanism from preferred cross-entropy.
Agreement in the main case does not make these different scores equivalent.

| Fixture | Bayesian / state | Full extension | Task extension | Mechanism extension |
|---|---:|---:|---:|---:|
| Continuation | 0.638000 | 0.638000 | 0.638000 | 0.638000 |
| Reset | 0.600000 | 0.550000 | 0.600000 | 0.600000 |
| Stable | 0.684000 | 0.684000 | 0.684000 | 0.684000 |
| Transfer isolated | 0.868750 | 0.868750 | 0.850000 | 0.868750 |
| Erased content | 0.600000 | 0.550000 | 0.600000 | 0.600000 |
| Chance calibration | 0.600000 | 0.550000 | 0.600000 | 0.600000 |
| Cheap final reference | 0.890000 | 0.840000 | 0.890000 | 0.890000 |
| Cheap maintenance | 0.725000 | 0.657500 | 0.725000 | 0.725000 |
| Costly recheck | 0.625000 | 0.608000 | 0.600000 | 0.608000 |
| Recheck price boundary | 0.625000 | 0.625000 | 0.625000 | 0.625000 |
| Weak preferences | 0.638000 | 0.550000 | 0.600000 | 0.638000 |
| No future reward | 0.000000 | -0.050000 | 0.000000 | 0.000000 |

These are optimum-set utilities rounded to six decimals. All members of each
set have the same utility within 1e-12. Bayesian/state tie between maintenance
and reference in the reset and chance-calibration cases; the recheck boundary
has sixteen policies. With no future reward, Bayesian/state/task/mechanism
have four equivalent report maps after skipping all paid actions. The full
extension buys both calibrations and has 4^16 equivalent report-map choices,
all at -0.05. Other optimum sets are unique.

The costly-recheck result is a useful discrimination: the full and mechanism
extensions buy a check whose information bonus outweighs its excess task cost,
earning 0.608 instead of 0.625. Under cheap maintenance, the full extension
buys both calibrations, maintains after agreement and buys a reference after
disagreement. That more elaborate policy earns 0.6575 versus 0.725 from simply
maintaining. Objective improvement and costed usefulness remain separate.

## 5. Scope and next scientific question

The positive result requires a supplied episode-wide transition class. It
does not estimate an arbitrary changing transfer rate. With unknown population
content and transfer probabilities, the calibration law still identifies their
product, not each separately. Independent reference quality, the ability to
invert a read, protected history and effective maintenance remain resources.

The state/Bayesian equivalence also relies on retaining pre-maintenance states
and buffered physical signals. It is a theorem for this declared representation,
not a claim that every FEP state description yields the same policy. The
information extensions are explicitly named EFE-inspired scores, not all
published definitions of expected free energy.

The next proposed local step is a focused scientific review of the shared-class
and retained-state assumptions: which part of the useful checking result is
robust, and which part follows from those choices? Use these sealed results
before deciding whether another model is warranted. No successor is launched,
and manuscript integration remains with the other agent.

## 6. Execution and integrity record

The specification preceded implementation and execution. Syntax, the mounted
external drive, the reused helper and three predecessor manifests were checked
before the run. It started at **2026-09-19T11:19:01.208933+00:00**, using Python
3.10.12 and one process. The complete verification comprises:

- 12 fixtures, 23,520 terminal choices and 117,600 local objective scores;
- 1,260 second-access scores and 180 initial-access scores;
- 60 complete global optimum sets and 180 direct whole-trajectory audits;
- 360 explicit policy checks attaining the extreme utilities of tie products;
- 36,458 numeric comparisons and 6,751 structural checks.

All passed on the first execution. Maximum residual was
**5.15143483426e-14**, below the frozen 1e-12 tolerance. The huge contingent
policy sets are represented exactly through sums/products of branch optima;
they are not sampled or materialized individually. All three input and two
output hashes were verified after execution. The external record occupies
**9,645,910 bytes**:

- [Results, controls and complete branch optima](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01/RUN_LOG.txt)
- [Frozen inputs and output hashes](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-v1/attempt-01/MANIFEST.json)

Preserve the specification, checker, helper and outputs. No failed execution,
retuning, prior-study rerun, manuscript edit or fresh literature/sister search
occurred. The result supports a conditional FEP account of useful checking and
action, with matched Bayesian performance and explicit limits.
