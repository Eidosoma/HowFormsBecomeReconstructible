# Generalization attribution v1: beliefs and stopping behind known losses

**Post-result specification, 23 September 2026.** The user's next “lets go”
authorizes the attribution recommended after the
[generalization test](FEP_GENERALIZATION_V1_REPORT.md). Freeze this document
and checker before qualification. The cases and performance failures are
already known; this is explanation, not fresh validation, a new controller
or a revised success criterion.

## Fixed scope and context

Analyze exactly the three positive-headroom failures and the two tied worst
total-cost cases, using the preceding population's names and laws:

- `a15_b15_pos05`;
- `a15_b45_neg05` and `a45_b15_neg05`;
- `a15_b35_pos05` and `a35_b15_pos05`.

Keep both sensor orders and both original controllers. Preserve the complete
125-world panel, its equal weights, ten separate known controls, two verdicts,
costs and regret decomposition as context. Do not create a new aggregate from
the five selected cases or reinterpret them as a validation set. No new
generalization population is evaluated.

Use the original calibration stopping laws and deployment tables, before
deployment feedback. Keep cap 64, horizon 100, pair price .001, reference
price .1, wrong-report cost 1, stationary IID errors, fair targets and XOR
warnings. The independent Beta(1,1) and joint Dirichlet(.5,.5,.5,.5) models
and .9/.1 structural prior are unchanged. VFE supplies exact evidence and
posterior inference; there is no new EFE or information bonus.

Read sealed posterior/stopping, bounded forecast and Bellman-table ledgers
in place. Reconstruct current posterior quantities by their closed conjugate
formulas and verify saved choices. Do not import or call an optimizer, revise
priors, select a price/confidence threshold or provide evaluator Q to an agent.

## A. Same-history decision attribution

Cross the two saved stopping schedules s with the two saved deployment
rules d (MAP and model average), without reoptimizing acquisition. Record
all four complete costs L(s,d), charging the original calibration at that
schedule. Verify both diagonal costs against the sealed generalization
result. Report the two substitution orders for their difference:

```
L(E,E)-L(A,A) = [L(E,E)-L(E,A)] + [L(E,A)-L(A,A)]
              = [L(E,E)-L(A,E)] + [L(A,E)-L(A,A)].
```

These are matched counterfactuals, not selected replacement agents. A same-
history comparison isolates the deployment-rule change; it does not by itself
isolate every effect of structural uncertainty.

For each diagonal controller, use one declared-order parameter substitution.
Let Q0 be the product of Q's true sensor marginals, and Q1=Q. At history c,
retain its saved MAP model j(c) or its exact posterior joint-model weight p(c):

```
Q_star_MAP(c) = Q_j(c)
Q_star_average(c) = (1-p(c))*Q0 + p(c)*Q1.
```

Apply the existing report/reference decision rule to that vector, with the
existing reference-at-tie convention. This supplies exact within-model
parameters to the evaluator while holding the history's structural choice
or weight fixed. The real agent never receives those parameters. Define

```
parameter contribution = R_Q(saved action) - R_Q(parameter-substituted action)
structure/weight remainder = R_Q(parameter-substituted action) - B(Q)
```

The first term is signed and can be negative; the second is nonnegative
because B(Q) is the unrestricted known-Q decision floor. They sum exactly
to the original decision regret, including within each warning class.
Calibration adds back to the full gap. Retain positive and negative parameter
contributions separately rather than clipping a compensating effect.

The remainder describes an independence approximation or retained structural
weight at true within-model parameters. It is **not** a lower bound on all
actions representable by an independent model, proof of irreducible model-class
failure, or a unique causal attribution. Biased estimates can compensate for
an inadequate factorization. The order is declared bookkeeping, not an
empirical discovery; do not sum it with the separate stopping comparison as
if those were disjoint causes.

Partition each diagonal's original regret and these signed terms jointly
by MAP-selected structure, exact stopping count and agreement/disagreement.
For averaging, the MAP label is a diagnostic, not its deployment operation.
Retain both structure categories and all counts, including empty cells.
Record exact stopped model-selection probabilities and full-cost components.

## B. Complete the same calibration stream to 64

For each physical Q and unchanged deployment rule d, compute

```
C_Q,d(c) = R_Q(d(c))                         at n=64
C_Q,d(c) = sum_e Q_e C_Q,d(c+e)              otherwise
b_Q,d(c) = R_Q(d(c))-C_Q,d(c)-(64-n)/100000.
```

Use the full frozen response-table lattice, with no minimizing step.
Positive b means completing this fixed continuation has lower conditional
expected full cost. It does not mean every realized future history helps.
For all four schedule/deployment combinations, report fixed-64 and stopped
costs, signed completion benefit, positive/negative gain contributions and
probabilities, and the fraction of early-stop probability with positive b.
Verify exactly that stopped-law averaging of C recovers the same fixed-64
root, and average b equals stopped full cost minus fixed-64 full cost.
Every cap benefit is exactly zero. Keep possible harm from extra calibration.

The acquisition belief is the original full structural posterior. Read its
already-sealed risk and completion-benefit bounds at each actual diagonal
stop, rather than recomputing or optimizing that prior calculation. Bounds
are exact adjacent multiples of 2^-40, with zero width when representable.
Verify complete ledger alignment and nonpositive completion upper bounds.
Report physical-Q-weighted mean forecast intervals and physical completion
values, keeping interval signs and widths. Positive physical b with a
nonpositive subjective bound is a fixed-environment forecast disagreement,
not an invalid posterior or a VFE minimization failure. No off-diagonal
subjective forecast is invented where the saved ledger contains none.

## Examples, arithmetic and qualification

For each of five cases and two diagonal controllers, retain one highest-
contribution history/warning for excess checking, one for unsafe reporting,
and one history for positive net completion gain. Select by the exact
probability-weighted contribution; break ties by lexicographic counts then
warning index. Keep absent examples explicit. These at most 30 examples
illustrate the already-known losses and do not define a selected performance
population. Include counts, probability, selected model, posterior model
weight, actions, predicted and physical report risks, the parameter-substituted
action and saved forecast bounds where applicable.

Use exact integers/rationals for physical weights, action choices, regret,
gain signs and all identities. With Q denominator 800, stopped mass is
K_s(c)*product(q_e**c_e)*800**(64-n), with denominator 800**64. Never replace
first-stop K by unrestricted multinomial counts. Physical loss numerators
use denominator 8000; net completion gain can use denominator
200000*800**(64-n). Quantization affects only inherited forecast summaries,
never actions or physical comparisons. Floating values are display/timing only.

Qualify conjugate evidence, model odds and saved current actions against the
frozen factor checker. Qualify physical costs and parameter-substitution
telescoping by independent fair-target/error enumeration, including ties and
zero-probability warnings. Through cap three, compare the backward completion
recursion with direct enumeration of every future error sequence, and use
two outcome-dependent stopping schedules to verify every crossed global
coupling and signed-gain identity. Exercise archived result-schema bridges
before main execution so missing-field errors are caught during preparation.

Benchmark the full five-case workload over the top two lattice layers,
including stopped-history accounting and example selection. Forecast 120
seconds plus four times the full-lattice extrapolation. Use one process within
the four-CPU ceiling. Forecasts over ten minutes run detached with durable
logs and no automatic polling; write a pending checkpoint and inspect completion
on a later user-requested continuation. Preserve every failed attempt and
separately freeze any correction. No outcomes are tuning inputs.

## Records and completion

Generated records belong only under the verified mount at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-generalization-attribution-v1/`.
Source and research notes remain in `fep-ideas`. Save source/provenance,
qualification and benchmark, all five cases and crossings, joint attribution
bins, bounded forecasts, examples and absences, timing, logs and manifest.
Reference the intact full-panel result instead of duplicating its large
ledgers. Preserve both generalization attempts and every preceding freeze.

Complete a report and six live-note updates, or a qualified detached checkpoint.
Keep earlier successes and failures unchanged. No automatic successor,
controller promotion, tuned remedy, feedback extension, manuscript integration
or sister-project write is authorized.
