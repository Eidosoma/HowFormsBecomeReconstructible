# Adaptive calibration v1: deciding when evidence is worth buying

**Prospective contract, 22 September 2026.** The user's “lets go” approves
the next acquisition test. Freeze this file and `check_fep_adaptive_calibration.py`
before qualification or outcomes. Preserve all attempts and either scientific
verdict. Source/notes remain local; generated records use only the mounted
`/mnt/bioIce1/fep-ideas/` namespace. No tuning or automatic successor.

## Question and inherited resources

Can the factor-revision agent decide how much paired calibration to buy,
instead of receiving a fixed block? Does looking far enough ahead matter
when the first observation alone cannot change a useful action?

Keep the [factor-revision contract](FEP_FACTOR_REVISION_V1.md) unchanged:
binary hidden task input W, fair independent task worlds, symmetric errors
Y_i=W XOR E_i, stationary IID error pairs, known-positive paired calibration,
the single factor-join primitive, and the two conjugate model families.
M0 has independent Beta(1,1) error rates; M1 has a four-cell Dirichlet(1/2)
factor. Structural priors remain .9/.1. No truth parameters enter planning.
Paired calibration identifies dependence, not a unique physical cause.

Wrong reports cost 1; a perfect reference costs .1. Task response ties ask
the reference. Keep H=100 deployment tasks and calibration price k=.001 per
pair. Deployment still uses a fixed learned response table conditioned on
each task's warning pair, with no learning from deployment feedback.
Calibration time has no additional loss or effect on the subsequent H tasks.
All persistence, symmetry, supervised-calibration and reference assumptions
remain supplied; no previous continuation-risk guarantee applies.

The new action is to **stop calibration and deploy**, or buy one more paired
calibration observation, up to the same hard cap B=64. There are no initial
free observations. Payment is per actual observation, including observations
that do not change a decision. The agent may stop at every count history.
This is a finite optimal-stopping problem, not a price or budget search.

## Preserve the deployment rule; separate structural uncertainty

The primary controller retains the earlier MAP edit rule at deployment:
select M1 iff its evidence exceeds nine times M0's evidence, then use the
selected model's posterior predictive to choose answers/references. Its
acquisition planner retains the full .9/.1 model posterior to predict what
future calibration would do to that same deployment rule. Candidate capacity
must therefore be available during lookahead, not invented after stopping.

This is intentionally a modular, constrained controller. The acquisition
planner is not allowed to replace the frozen MAP deployment table after
seeing its expected loss. A model-averaged deployment controller supplies
the unconstrained Bayesian benchmark in the same response-table family.
Holding MAP deployment fixed isolates the acquisition change; its possible
inconsistency with the richer acquisition belief must remain visible.

Compare these four deployment/planning pairs:

| Name | Deployment predictive | Calibration predictive / expected loss |
|---|---|---|
| adaptive_edit (primary) | Evidence-selected M0 or M1 | Full structural posterior mixture |
| adaptive_average | Full structural posterior mixture | Same full mixture |
| adaptive_independent | M0 | M0 |
| adaptive_joint | M1 | M1 |

All retain their exact conjugate parameter posteriors. The latter two hold
structure fixed but learn parameters and plan acquisition. The primary and
model-average controllers share beliefs, costs, access and stopping choices;
they differ in deployment commitment. Thus model averaging is not a new
observation advantage.

## VFE inference and instrumental planning

As before, minimized variational free energy within a model is negative log
evidence. Across structures, the exact posterior minimizes

```
F(q_M) = sum_m q_m [log(q_m/prior_m) - log e_m(D)].
```

Its minimum is `-log sum_m prior_m e_m(D)` and its gap is posterior KL.
Use evidence ratios for both structural updating and coherent predictions
of subsequent observations. No hand-added information reward is used.

Let d_j(c) be controller j's declared terminal response table at count state
c, n=sum(c). Let p_j(e|c) be its planning predictive and
R_j(c,d) the one-task expected loss under that predictive. Define total
remaining episode loss, excluding already paid calibration:

```
S_j(c) = H R_j(c,d_j(c))
V_j(c) = S_j(c)                                      if n=B
V_j(c) = min[S_j(c), k + sum_e p_j(e|c) V_j(c+e)]     otherwise.
```

Exact ties stop. There is no extra VOI bonus: the continuation term already
includes useful future decisions. This is Bayesian task planning coupled to
VFE inference, not a new EFE or distinctive FEP advantage. Do not claim that
optimality under these priors guarantees lower loss at each fixed truth.

Include a **myopic edit** control replacing child V by child S. Starting
without data, one calibration observation leaves the MAP deployment table
asking for a reference on every warning. The first-step instrumental benefit
is therefore zero, although a longer sequence may enable a useful answer.
Verify this analytically and numerically; do not rescue the myopic controller
with free seed data or a minimum forced calibration count.

## Exact computation, without enumerating 4^64 ordered paths

Use sufficient count states c=(c00,c01,c10,c11). The 814,385 states through
n=64 are a dynamic-programming lattice, not independent sampled runs.
An additional layer of 50,116 n=65 evidence weights supplies predictive
outcomes for the n=64 terminal calculation; it authorizes no 65th calibration.

For exact arithmetic choose a common likelihood denominator
`D = 4^(B+1) * ((B+2)!)^2`. For every state through n=65,
`w0(c)=D*e0(c)` and `w1(c)=D*e1(c)` are integers. They satisfy
`sum_e w_m(c+e)=w_m(c)`. Use `w=9*w0+w1` for full-mixture controllers;
M0/M1 controllers use w0/w1. Posterior branch probabilities are child/parent
weights, so the arbitrary common scale cancels.

For error pair e and response table d, let ell_e be the sum over the two
world values of 10 times the wrong-report indicator plus the reference
indicator. One-task expected loss is `sum_e p(e|c)*ell_e/20`.
With H=100 and k=1/1000, the scaled Bellman values `A=1000*w*V` obey

```
stop_A = 5000 * sum_e w(c+e)*ell_e
continue_A = w(c) + sum_e A(c+e)
A(c) = min(stop_A, continue_A).
```

All planning decisions and ties can therefore be made with integers. Keep
only adjacent value layers in memory, plus compact policies for evaluation.
Log rounded stop/continue values and exact choice/tie flags for every state;
the frozen source and counts reconstruct the integer calculation.

Evaluate stopped trajectories by propagating probability mass along each
controller's actual continue branches. **Do not weight stopping counts by an
unconditional multinomial law**: some permutations have already stopped.
For each fixed truth, propagate integers with denominator 100^64, then
aggregate stopping mass, observation count and terminal physical losses.
Return exact rational costs and probabilities. Future predictive log loss
is a secondary binary64 quantity, with identity tolerance 1e-10.

## Frozen truth panel, controls and verdicts

Reuse all five old truth laws, in the same cell order:

| Truth | Q |
|---|---|
| independent | (.72,.18,.08,.02) |
| shared | (.80,.10,0,.10) |
| partial | (.76,.14,.04,.06) |
| anticorrelated | (.70,.20,.10,0) |
| marginal_shift | (.56,.14,.24,.06) |

The primary evaluator aggregate is again equal independent/shared weight,
not the learner's prior. Preserve the partial-dependence regression as a
visible control. Compare all four adaptive controllers, the myopic edit,
always asking, fixed follow-A, and known-Q oracle. Reuse the hash-verified
N=64 fixed-budget results for all four corresponding deployment rules;
do not rerun or refit that experiment.

Report per truth/controller: expected calibration count, full stopping-count
distribution, cap-hit probability, probability of zero calibration, terminal
MAP-join frequency for the edit controller, wrong-report/reference
probabilities, raw/net loss per deployment task, and future predictive log
loss. Net loss is `raw + k*E[N]/H`; stopped histories and cumulative costs
must agree. Separately report prior-predicted root cost; no fixed-truth
performance is used to choose an action, a prior or a stopping threshold.

The **primary functional gate** requires adaptive_edit net loss below .1
under shared truth and in the equal independent/shared aggregate, with
positive expected calibration use. This asks whether learning is useful at
all, before comparative advantage. The separately labeled **efficiency gate**
requires that aggregate loss not exceed fixed-64 editing and that aggregate
expected calibration count be below 64. Report every comparison against
model averaging, always-joint and the parameter-only controller regardless
of either gate. Do not replace a failed primary controller by a favorable
comparator after results.

Mechanism checks include myopic refusal at the initial state, the actual
lookahead initial choice (do not force it to continue), and the no-task-use
boundary. With H=0, positive-cost calibration is skipped. A calibration pair
costing 11 cannot improve over the initial always-reference loss of 10 even
if it eliminates all future error; certify initial rejection analytically,
without an additional high-price sweep or invented utility conversion.

## Qualification, resource limit and records

Before the main lattice, check evidence weights/predictives against the frozen
checker, model/world VFE identities, exact index/child mappings, terminal
response tables, and a depth-three recursive ordered-history planner against
the count-lattice planner. Independently enumerate all depth-three stopped
ordered paths and compare their exact masses/costs with forward propagation.
Check optional-stopping accounting on a deliberately outcome-dependent test
rule as well as the optimized rule. This small fixture tests the evaluation
mechanism; it is not an extra scientific horizon from which to select results.

On the full lattice verify likelihood normalization, finite-cost bounds,
Bellman choices, exact tie behavior, and model-average value no greater than
MAP value under their common posterior. In physical evaluation verify exact
total stopping mass, count/cost identity and the known-Q task lower bound.
The checks are implementation/equivalence checks, not independent experiments.

Use one process, within the four-CPU ceiling; standard-library exact arithmetic
and compressed ledgers keep the test lean. The bounded 814,385-state run is
forecast below ten minutes from the earlier 54,616-state calculation. Runs
forecast to exceed ten minutes must be detached with durable logs and no
automatic progress polling. Preserve failures and source snapshots; never
overwrite an attempt. Do not increase B, H, search prices or add fixtures
after outcomes. Frozen earlier source/reports/manuscripts remain unchanged.

Record preparation and identities, qualification, Bellman decisions, terminal
stopping ledgers, aggregate results, runtime logs and final manifest on the
external mount. Report and update the six live project notes, then stop.
This test does not add sensor interventions, calibration drift, task feedback,
an LLM proposer, deployment-time learning or manuscript integration.
