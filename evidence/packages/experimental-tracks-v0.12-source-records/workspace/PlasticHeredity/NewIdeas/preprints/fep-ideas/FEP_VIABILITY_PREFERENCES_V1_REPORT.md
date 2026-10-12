# Energy-grounded preferences: a constructive result and its limits

**Completed 19 September 2026.** The
[specification](FEP_VIABILITY_PREFERENCES_V1.md) preceded implementation and
the first exact execution of [the checker](check_fep_viability_preferences.py).
All eight declared cases passed. This is verification of a finite theoretical
model, not evidence from an organism or a learned physical system.

**The construction can express a real constraint on continued operation and
preserve FEP scores when hidden energy details are removed. Its decisions agree
with Bayesian planning given the same constraint and costs. Physical mechanics
do not determine the tolerated risk, reference policy or preference strength.**

## 1. What was tested

A system has two energy units and two reading tasks. Economy mode consumes
one unit and reads the first target with accuracy 0.75; precision consumes
two and has accuracy 0.90. An independent recharge arrives with probability
0.90. A perfect second reader requires one remaining energy unit. The second
task is worth 0.5 and the first is worth 1. There is no separate invented
energy penalty: resource consumption changes whether the future task is possible.

In the main physical setting, economy always permits the second task and
earns expected task utility 1.25. Precision permits it with probability 0.90
and earns 1.35. Which mode is appropriate depends on whether continued
operation is mandatory, just valuable through the future task, or assigned
an additional failure cost.

The preferred joint is constructed from the complete physical trajectory law
mu under a fixed reference controller, multiplied by exp(beta*u) and a
continuation weight: one for successful continuation and epsilon for failure.
It is normalized once, across both modes. The physical law is held fixed
when each action is evaluated. Beta=4 and an equal reference over the two
modes are declared conventions, not inferred physiological facts.

## 2. Complete deterministic results

The table reports minima over both specified deterministic protocols. The
matched Bayesian planner uses the same hard requirement or finite failure
penalty and the same reference cost. Both modes are retained at a tie.

| Declared case | Deterministic FEP optimum | Matched Bayesian optimum | What it establishes |
| --- | --- | --- | --- |
| Hard continuation, epsilon=0 | Economy | Economy | Precision's 10% failure probability violates the hard requirement. |
| Task value only, epsilon=1 | Precision | Precision | Future loss is already counted in utility; the better immediate reading outweighs it here. |
| Failure price 1, epsilon=exp(-4) | Both | Both | Exactly balanced tradeoff; no tie is discarded. |
| Failure price 2, epsilon=exp(-8) | Economy | Economy | The additional failure cost changes the objective and decision. |
| Hard continuation, certain recharge | Precision | Precision | Both modes can continue with certainty; greater accuracy wins. |
| Hard continuation, no recharge | Economy | Economy | Precision cannot perform the future task. |
| Task value only, precision reference probability 1/4 | Economy | Economy with the same reference cost | The reference convention alone changes the decision; raw task value still favors precision. |
| Hard continuation, independent 10% outage | No finite feasible policy | No policy meeting the same hard constraint | A valid preferred density need not have a causally feasible policy satisfying its support. |

For epsilon>0, direct trajectory enumeration confirms

```text
J(a) = log Z - log rho_a - beta*U_a - (1-v_a)*log epsilon.
```

Thus the extra terms are precisely a failure price
`-log(epsilon)/beta` and a reference cost `-log(rho_a)/beta`.
Neither term is established as a metabolic cost by this calculation. With a
uniform reference, the deterministic optimum condition is

```text
precision wins iff gamma-alpha > (w + failure_price)*(v_0-v_1).
```

This equivalence is algebraic across the declared model domain. The finite
cases check its implementation and boundaries; a larger parameter grid would
not establish a new FEP advantage.

Hard preferences were handled without probability floors. Any positive mass
on failure gives infinite risk. The unavoidable-outage control has continuation
probabilities 0.90 and 0.81, so both modes fail the requirement. All five checked
mixtures in that control are infeasible too. The preferred joint remains
normalizable because some surviving trajectories exist. This is a feasibility
failure of the imposed requirement, not a numerical failure or a general
refutation of FEP.

## 3. A positive result for state representation

The full state includes recharge and outage details. The reduced state retains
the chosen mode, both targets and both reported signals. It therefore retains
the whole observable history, realized utility, continuation event and all
task/cost coordinates, while keeping the targets hidden from the controller.

Under this one common preference construction, the predictive and preferred
conditionals on the removed details are equal. Their conditional KL is zero.
Full and reduced FEP risks agree in all 45 checked policy distributions,
including the same infinite-support failures. The marginal preferred task
joint is also preserved.

This provides a constructive case where the
[representation contract](FEP_REPRESENTATION_CONTRACT_V1.md) is satisfied
exactly. The relevant condition is that both policy/reference and
preference/reference likelihood ratios depend only on retained variables;
the retained state must also preserve observations. The previous ranking
reversals remain valid for their different preferred joints. This result
does not make arbitrary state reductions invariant or identify a unique
preferred law from physics alone.

## 4. Two misleading shortcuts exposed

**Selecting an action from the preferred surviving trajectories can hide its
actual failure risk.** In the main hard case, precision has approximately
0.518219 of the preferred action marginal, compared with 0.481781 for economy.
Choosing the more probable action in that marginal selects precision, despite
its infinite full trajectory risk under the hard requirement. Conditioning
on survival has filtered out unlucky recharges; executing precision cannot
perform that filtering on the world.

That action-only shortcut drops task outcomes, observations and the conditional
divergence. It is not an equivalent reduced FEP model. The need to retain
physical dynamics when using outcome-conditioned control models has an
established precedent in
[Levine's control-as-inference analysis, sections 2.3–3.2](https://arxiv.org/html/1805.00909v3).
Our result is a concrete application, not a claim of priority for the general
conditioning-versus-control distinction.

**Random-policy risk contains a separate entropy/reference term.** Randomizing
precision with probability r gives

```text
J(r) = log Z + KL(Bern(r)||Bern(rho))
       - beta*U_r - (1-v_r)*log epsilon.
```

The analytic optimum is certified by
`J(r)-J(r_star)=KL(Bern(r)||Bern(r_star))` on the finite feasible domain.
For task value alone with a uniform reference, r_star is approximately
0.598688; ordinary unregularized expected utility selects precision with
probability one. This difference is explained by the declared KL penalty,
equivalently an entropy bonus under the uniform reference. It does not show
a task-value advantage. The checker treats stochastic and deterministic policy
classes separately and verifies the global optimum identity, not just a grid
minimum.

## 5. Grounding achieved, and what remains supplied

The energy mechanics determine when the system can perform another task.
They give a physically interpretable continuation event and a common causal
reference law with which to construct the preferred joint. This construction
also fixes the hidden conditional needed for the tested state reduction.

The mechanics do not decide that continuation must be certain, how much risk
is acceptable, or how much another report is worth. An equal reference over
two named protocols remains a convention. The parameter values, correct model,
available modes, known decoder and perfect future reader are supplied.
Nothing here demonstrates autonomous discovery of preferences, learning the
energy law, or building the information-using apparatus.

The next focused question is **whether finite accessible evidence can justify
the continuation guarantee when the recharge/outage model is uncertain**.
This connects the two remaining leads: preferences now have an explicit
physical event, but the evidence supporting the model of that event may be
incomplete. A prospective analytic audit should specify candidate laws,
observable evidence, causal actions and hard versus probabilistic guarantees,
with matched Bayesian access. It should first identify indistinguishable or
unlearnable cases. No successor run, risk-tolerance tuning or repair variant
is launched by this result.

## 6. Execution and integrity

The first scientific execution started at
**2026-09-19T16:03:00.711003+00:00**, with Python 3.10.12 and one process.
It passed in **0.008771352 seconds**:

- Eight declared fixtures and all eight complete deterministic optimum sets.
- 256 physical reference/preference cells across fixtures.
- 45 checked policy distributions, including 13 expected infinite scores.
- 1,495 numeric comparisons and 1,112 structural checks.
- Maximum finite residual **5.68434188608e-14**, below the frozen 1e-12 tolerance.

The global random-policy results also have the algebraic KL-gap certificate.
The numeric checkpoints are not a substitute for that proof. No scientific
failure, source change, outcome-based retuning or duplicate run occurred.
Syntax, prospective links, protected source identities and the unused attempt
path were checked before execution. The external mount was verified; the
authorized external-write invocation completed successfully.

The **101,632-byte** record contains:

- [Results and physical reference/preference cells](/mnt/bioIce1/fep-ideas/formal-checks/fep-viability-preferences-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-viability-preferences-v1/attempt-01/RUN_LOG.txt)
- [Input/output manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-viability-preferences-v1/attempt-01/MANIFEST.json)

Both input and both output identities were checked after execution. The
specification hash is
`ceb6f5e6844b66668b06e2b233177a6ad53dc1ed316f1339f757d13fbf847490`;
the checker hash is
`9ff550ec14fbeafd4ae5dd50500d050a0f536beb78bbaf4e3e36476956cf2c3a`.
Preserve these frozen inputs and the output record. Earlier source/data records,
both manuscripts and sister-project folders were not edited.
