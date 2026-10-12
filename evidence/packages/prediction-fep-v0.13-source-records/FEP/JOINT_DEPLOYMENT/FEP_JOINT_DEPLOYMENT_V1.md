# Joint deployment v1: does structural competition earn its place?

**Post-result specification, 23 September 2026.** The user's next “lets go”
authorizes the bounded comparison recommended after
[generalization attribution](FEP_GENERALIZATION_ATTRIBUTION_V1_REPORT.md).
Freeze this contract and checker before qualification or calculating new
ablation outcomes. The population and original failures are known; this is
a mechanism comparison, not fresh validation or a prospectively unseen test.

## Fixed intervention and FEP question

At exactly the original saved calibration histories, deploy the existing
joint component instead of selecting a model or averaging their predictions.
For error counts c=(c00,c01,c10,c11), its posterior prediction is

```
Q_joint(e | c) = (c_e + 1/2) / (n + 2).
```

This conditions deployment on the supplied joint model with its unchanged
Dirichlet(.5,.5,.5,.5) prior. It deliberately removes structural competition
at deployment; it does not preserve the mixture's deployed model weights.
The calibration policies still use their original full structural posterior,
with .9/.1 independent/joint weights and independent Beta(1,1) components.
No optimizer is rerun. Thus this is a matched deployment ablation, not a
new jointly optimized acquisition/deployment agent or new representation.

Keep both original first-stop laws: MAP schedule E is primary, averaged
schedule A a required sensitivity/control. On each schedule compare all
three response rules: original MAP, original averaging, and learned joint.
Never promote whichever schedule performs better after reading outcomes.

The joint component receives only the counts already seen by the baseline.
It receives neither true Q nor free labels. All three rules retain the same
report/reference decision rule, including reference at a cost tie. Keep
known-input paired calibration, stationary IID errors, fair binary targets,
XOR warning transfer, calibration cap 64, 100 deployment tasks, pair price
.001, reference price .1 and wrong-report cost 1. No deployment feedback,
confidence threshold, prior, observation interface or price is tuned.

VFE supplies exact posterior inference and model evidence; the ablation asks
whether using evidence to retain structural competition improves paid task
decisions at this budget. Conditional joint inference remains valid within
that component, while full-posterior averaging is optimal for the original
mixture's immediate task risk. Verify that latter pointwise inequality at
every saved history. It is not a guarantee under every fixed physical law
or the equally weighted evaluation population. No new EFE, information bonus,
prior-wide oracle or advantage unique to FEP is introduced.

## Population, comparisons and fixed criteria

Reuse the exact 125-world generalization population and weights 1/125:
a,b in {.05,.15,.25,.35,.45}, with the five declared dependence settings
t in {−1,−.5,0,.5,1}. The original population file is an immutable input.
Keep both sensor orders and all 36 zero-headroom environments. Do not select
the five known failures as a new aggregate. All ten earlier controls remain
separate with zero contribution to the 125-world mean; report their ablation
costs too. Reproduce original diagonal results for all 135 laws and the
preceding attribution's four crossed costs for all five focus worlds.

On the primary E schedule, evaluate separately:

1. Joint mean full cost is strictly below matched MAP mean cost.
2. Joint mean full cost is strictly below matched averaged mean cost.
3. Joint mean full cost is strictly below always referencing (.1).
4. Joint full cost is strictly below .1 in every world with B(Q)<.1.

Apply the same comparisons to schedule A as required secondary results.
Ties fail strict improvement criteria. These are criteria for this ablation;
they do not replace any original experiment's gates or authorize promotion.
Keep mean improvement and coverage distinct. Report all four verdicts even
if the first fails. Uniform improvement against either matched comparator
is descriptive: report improved/tied/worse counts and every case's signed
contrast, with no additional selected success gate.

For all six schedule/deployment combinations, save per-world raw/full cost,
expected calibration and reference/error counts, stopping probabilities,
response-table probabilities and the original known-Q gap decomposition:
calibration, excess checking, unsafe reporting, wrong direction. B(Q) sees
the same warning and pays for references; it does not get free true targets.
Include achieved advantage, available headroom and their ratio only where
headroom is positive. Panel and slice capture use ratios of means. Keep all
undefined ratios, negative advantages, zero-headroom harms and tied worst cases.

Report the five equally weighted dependence-slice means without choosing a
slice-specific remedy. For each schedule and original deployment comparator,
save joint-minus-comparator full cost and component contrasts, the probability
of a changed response table, and the probability/gross signed contribution
of histories where joint deployment's conditional physical task cost is
lower, equal or higher. These are expected costs conditional on calibration,
not fractions of individual realized tasks won. Calibration cancels exactly
within each matched comparison. Preserve compensation rather than clipping
unfavorable contributions. Do not claim a unique causal decomposition.

## Exact implementation and qualification

Use the pinned saved first-stop ledger. Append the learned joint response
code computed from counts; verify the original MAP/average codes against
the frozen factor checker. The integer joint prediction is (2*c_e+1), with
the same rule for each warning. Persist these joint codes with their counts.
Check complement symmetry, reachable rows, multiplicities, all original
codes, and the full-mixture posterior inequality for joint versus averaging.

For every Q with integer cells q summing to 800, accumulate exact stop mass

```
K_s(c) * product_e q_e**c_e * 800**(64-n), denominator 800**64.
```

Accumulate response-table masses for all three deployments, stopped count
mass, and matched original/joint response-code pair masses. Use the inherited
exact physical task accounting. Verify normalization, matched calibration,
all warning/regret partitions, contrast identities and gross signed sums.
Use integers/rationals for signs and scientific comparisons; floats are
only for displays and timing. No sampling or standard errors are needed.

Before main execution qualify joint predictive probabilities against exact
Dirichlet evidence ratios and the frozen factor checker through n=6, including
threshold ties. Check posterior decision optimality by direct target/error
enumeration of all response tables. Qualify physical regret units under all
135 laws and synthetic zero-probability, reversed-risk and tie controls.
For two outcome-dependent schedules through cap three, compare all six
weighted response laws and paired-code laws against direct enumeration of
all ordered error streams. Complete the ten known diagonal bridges before
execution, including their archived field schema.

Benchmark all 135 laws on the first 2,048 saved rows with all six comparisons
and pair bookkeeping. Forecast 120 seconds plus four times the full-row
extrapolation. Use one process within the four-CPU ceiling. If forecast
exceeds 600 seconds, launch detached with durable logs and no automatic
polling; write a pending checkpoint and inspect completion only on a later
user-requested continuation. Preserve failed attempts and freeze any source
correction separately. Never tune from the outcome of this comparison.

## Record and completion

Source and research notes stay in `fep-ideas`. Generated records use only the
verified external mount under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-joint-deployment-v1/`.
Save source/input snapshots and hashes, population, joint response ledger,
qualification/benchmark, all world/slice/panel contrasts, criteria, timing,
logs and manifest. Read large earlier ledgers in place; preserve every older
freeze, both generalization attempts and the attribution record.

Complete a report and six live-note updates, or a qualified detached launch
checkpoint. No automatic successor, schedule optimization, weight tuning,
new feedback, manuscript integration or sister-project writing is authorized.
