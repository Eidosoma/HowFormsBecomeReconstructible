# Forecast validation v1: prior consistency and fixed environments

**Prospective analysis specification, 22 September 2026.** The user's next
“lets go” approves the proposed validation of task-risk and learning-value
forecasts. Freeze this contract and its checker before qualification/main
calculation. The earlier shared-fault attribution is known and motivates
the question; the nine panel outcomes below have not been calculated for
this study. This is a new finite-model evaluation, not an independent
empirical replication or validation outside the supplied model class.

Keep the frozen adaptive-edit and adaptive-average policies from
[adaptive calibration](FEP_ADAPTIVE_CALIBRATION_V1_REPORT.md). Do not optimize
or change priors, costs, observation access, response rules or cap. Preserve
the known [stopping attribution](FEP_STOPPING_ATTRIBUTION_V1_REPORT.md), all
earlier studies and manuscripts. No repair is selected by this calculation.

## Question and unchanged FEP mechanism

Does correct inference under a generative model give reliable forecasts of
task risk and useful further learning across different fixed environments?
Separate two statements: consistency averaged under the learner's own prior,
and performance under a different declared population of environments.

VFE still supplies exact parameter inference and structural model evidence.
The supplied models are independent Bernoulli errors with Beta(1,1) priors,
and a joint four-cell error law with Dirichlet(.5,.5,.5,.5). Structural prior
weights are .9/.1. The primary deployment module selects a joint factor iff
the Bayes factor exceeds 9; the strong comparison averages both models.
Both acquisition policies use the full structural posterior. Their saved
policies minimize future task loss and calibration cost, with no extra
information bonus. This is Bayesian planning coupled to VFE, not a new EFE.

Retain fresh fair binary targets, XOR sensor errors, IID/stationary error
pairs, known-positive paired calibration, symmetric transfer to deployment,
100 future tasks, wrong-report cost 1, perfect-reference cost .1, calibration
pair cost .001 and cap 64. No deployment feedback or additional action.
Dependence does not identify a physical common cause. All edit, transfer
and access assumptions remain supplied.

## Two declared evaluation populations

**Own-prior control.** Sample the structure and stationary parameters from
the original prior once per episode, then generate all calibration and task
outcomes from those parameters. Integrate this distribution exactly using
conjugate evidence; do not sample it. Verify that saved stopping-path
integration reproduces the already sealed root value and fixed-64 value.
Posterior risk calibration under this population is a conditional-expectation
identity, including after outcome-dependent stopping and forecast binning.
Treat it as a mathematical/integrity control, not evidence that the prior
describes another environment population. It does not require the posterior
mean to equal each individual latent parameter's risk.

**New finite panel.** Use all nine combinations of sensor A error
`a in {.05,.15,.25}`, sensor B error `b=2a`, and dependence interpolation
`rho in {0,.5,1}`. Define

```
q11 = (1-rho)*a*b + rho*a
Q = (1-a-b+q11, b-q11, a-q11, q11).
```

Rho interpolates from independence to fully nested A errors; it is not
Pearson correlation or an identified physical common-cause parameter.
All nine cases receive equal weight in the primary aggregate. Their integer
probabilities, in 00/01/10/11 order with common denominator 400, are:

| A error | B error | rho=0 | rho=.5 | rho=1 |
|---|---|---|---|---|
| .05 | .10 | (342,38,18,2) | (351,29,9,11) | (360,20,0,20) |
| .15 | .30 | (238,102,42,18) | (259,81,21,39) | (280,60,0,60) |
| .25 | .50 | (150,150,50,50) | (175,125,25,75) | (200,100,0,100) |

These nine laws differ from all five earlier truth fixtures. The old shared
case is excluded from the panel and its aggregate. Reproduce its known
diagonal totals only as a labeled integrity replay, with no new scientific
claim. Do not choose cases, weights or subgroups after reading results.
The high-error independent/partial cases can make always asking optimal
even with known parameters; retain them as a limitation/control, not a
surprising newly discovered failure to beat an unattainable optimum.

## Fixed-policy estimands

At a count history c, let K_s(c) count ordered calibration sequences that
first reach c without an earlier stop under saved schedule s. Propagate
integer sequence counts along each continued branch. At a stopped c their
probability is `K_s(c)*prod_e Q_e**c_e`, or `K_s(c)*m(c)` under the prior,
where m is mixed evidence of an ordered sequence. Never substitute the full
multinomial multiplicity for these stopping-conditioned path counts.

For each controller separately, d(c) is its unchanged response table.
Let r(c) be posterior-predicted raw loss under the full acquisition belief,
and R_Q(c) the actual raw task loss under Q. Complete the remaining stream
to 64 using the same deployment rule:

```
C_Q(c) = R_Q(c) at 64; otherwise sum_e Q_e*C_Q(c+e)
b_Q(c) = R_Q(c)-C_Q(c)-(64-n)/100000.
```

Use the analogous full-posterior expectation C_prior(c) and b_prior(c).
Every reachable saved stop must have `b_prior<=0`; cap benefits are zero.
Positive b_Q means completion improves conditional expected net task value,
not that every realized completion helps. Its stopped-law average must equal
`Delta_Q = adaptive net loss - fixed64 net loss` exactly.

For each environment/controller retain mean n, early/cap probabilities,
raw/net adaptive and fixed losses, known-Q best response raw loss, signed
completion gain, positive/negative gain contributions and probabilities,
and the fraction of early-stop probability with b_Q>0. Report predicted
versus actual mean task risk and mean completion benefit. No controller
gets evaluator Q or changes policy in response to these diagnostics.

Report risk calibration in the fixed intervals `[0,.025)`, `[.025,.05)`,
`[.05,.075)`, `[.075,.1)`, `[.1,.125)`, `[.125,1]`, assigned by exact r(c).
Retain empty bins. Give bin probability, actual risk and bounded predicted
risk. Also retain every stopping-count stratum, including zero mass.
These summaries are diagnostic; do not select a threshold or repair from
a favorable bin. No ranking of illustrative histories is required.

## Declared outcomes and numeric contract

Primary results concern the frozen edit controller on the equal nine-case
panel. Report all three questions separately:

1. Does chosen learning pay overall? Mean adaptive net loss < .1.
2. Does stopping improve mean cost against completing calibration?
   Mean Delta_Q <= 0.
3. Does stopping avoid loss in every panel environment? Max Delta_Q <= 0.

Apply the same descriptive questions to the averaged controller, without
promoting it after results. Report every environment, including failures.
These are new panel assessments, not replacements for the earlier registered
functional/efficiency gates. Forecast bias is reported with its sign and
magnitude, not a result-chosen tolerance declaring the model calibrated.

Use exact integer/rational path weights, physical costs, completion gains,
bin assignments, gate comparisons and sign tests. Prior-weighted summaries
are exact because evidence denominators cancel. Averaging subjective values
under a different Q otherwise introduces heterogeneous denominators. Bound
each such value by floor quantization at step `2^-40` and its next grid
point, using exact integer division; use zero width when exactly divisible.
Weight these bounds with exact history probabilities. Mean interval widths
must be <=2^-40, including within nonempty bins. Quantization never affects
actions, positive-benefit classification or success criteria. Display-only
floating checks use tolerance 1e-10.

Qualify against direct ordered histories through cap 3 using an explicitly
outcome-dependent toy stopping schedule, independent evidence calculations
from the frozen factor checker, and brute-force future completions. Verify
exact stop normalization, n accounting, loss units, bins and quantization
containment, and both prior and fixed-Q coupling identities. The toy is a
numerical qualification, not another optimized agent. Verify complete saved
ledger indexing and frozen source identities. Do not import an optimizer.

## Records and limits

Use one process, at most four CPUs. Forecast below ten minutes from the
earlier 814,385-state calculation; record a qualification-based estimate
and detach if it forecasts above ten minutes. Longer jobs retain durable
logs and no automatic progress polling.

Source and research notes stay in this folder; all generated records use
the mounted `/mnt/bioIce1/fep-ideas/formal-checks/fep-forecast-validation-v1/`.
Freeze source/contract and inputs before qualification. Save preparation,
qualification, one compact stopped-forecast ledger, all environment/bin/count
summaries, prior control, labeled old-case replay, runtime and manifest.
Read old large ledgers in place with hashes rather than copying them again.
The compact ledger records exact path multiplicities and bounded forecasts;
fixed-Q recursions are reproducible from the frozen code and saved policies.
Do not write repeated full history ledgers for every Q. Keep failed attempts.

After the bounded calculation, report either result and update the six live
notes. Do not launch a remedy, tune priors/thresholds or expand the panel.
Sister projects and manuscript integration remain outside this task.
