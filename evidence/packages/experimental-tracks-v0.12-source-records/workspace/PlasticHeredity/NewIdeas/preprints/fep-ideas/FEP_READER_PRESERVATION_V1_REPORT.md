# Reader preservation with no information gain: exact result

**Completed 18 September 2026.** The
[analytic specification](FEP_READER_PRESERVATION_V1.md) preceded implementation
and execution of the [finite checker](check_fep_reader_preservation.py).
All eleven fixed settings passed on the first execution. This is mathematical
verification of a supplied finite model, not sampled biological evidence.
Manuscript integration remains with the other agent, as requested by the user.

**Subsequent review qualification:** the
[scientific review](FEP_READER_PRESERVATION_REVIEW_2026-09-18.md) confirms the
calculation and narrows its interpretation to supplied readout reliability.
The known message cancels from the success equation; the necessity of a
retained record or learned decoder was not tested. The original report below
and all frozen calculation inputs and outputs are preserved.

## What happened, in simple terms

The saved message never changes, and the agent already knows what it says.
But the only route for expressing it can fail. Paying for maintenance makes
that route more reliable without teaching the agent anything.

At low cost, the stated FEP state-preference objective chooses maintenance,
just like the Bayesian planner. This establishes a narrow positive result:
preservation need not be driven by acquiring information.

At a higher cost that is still worth paying for the task, the state-preference
objective skips maintenance. Its score includes the uncertainty of future
success, and making the reader reliable reduces that uncertainty. This term
partly offsets the improved success rate. The agent can therefore obtain a
better internal score while choosing a worse task outcome.

The result connects directly to the pivot, but the maintenance action's
effectiveness is supplied. We have not shown that a system invents, learns
or sustains its own maintenance mechanism.

## Model and principal results

There is one known, unchanged record bit and one readout channel. Maintenance
`a` costs `c*a`; the channel then flips with probability `1-rho_a`.
The controller can prepare either the original bit or its inverse (`b`), but
both reports cross the same channel. Neither the flip nor the actual report
is observed by the controller. The four deterministic policies are all pairs
`(a,b)`. Every objective has identical knowledge, access and available actions.
The full episode's information gain is exactly zero for every policy.

The independently fixed task score is expected successful use minus maintenance
cost, `U=E[v*g-c*a]`. The principal setting has `v=1`, reliability `rho_0=0.5`
without maintenance, `rho_1=1` with maintenance, and preference scale `beta=4`.

| Maintenance price | Bayesian planner and latent extension | State risk and exact decomposition | Outcome risk with conditional KL omitted |
|---|---|---|---|
| 0.10 | Maintain; utility **0.90** | Maintain; utility **0.90** | Skip; utility **0.50** |
| 0.40 | Maintain; utility **0.60** | Skip; utility **0.50** | Skip; utility **0.50** |
| 0.60 | Skip; utility **0.50** | Skip; utility **0.50** | Skip; utility **0.50** |

At price 0.40, the state score for maintenance minus skipping is
**+0.293147180560**, so skipping strictly minimizes that score. The latent
extension's difference is **-0.400000000000**, and Bayesian utility improves
by **0.10**. All optimal policies for each objective have the displayed utility;
the disagreement is not produced by tie-breaking.

An interior case removes the fair/perfect reliability endpoints. With
`rho_0=0.75`, `rho_1=0.95`, `beta=4` and price `0.15`, Bayesian planning and the
latent extension preserve the reader and obtain **0.80**. State risk skips
and obtains **0.75**. Its maintenance threshold is approximately **0.109045**,
below the task threshold of **0.20**.

## Why this differs from the preceding bridge

Use the same audited state-risk expression and its exact outcome decomposition,
but now on the declared future state `S=(g,a,b)` and outcome `O=(a,b)`.
Conditioning on the known record makes S a one-to-one relabeling of the
physical fault and two actions. Every policy has deterministic O; there is
no feedback and no information gain. With the specification's fixed preferred
joint and normalization constant K:

```text
J_state = J_exact = K-beta*U-h(rho_a)
J_latent = K-beta*U
J_drop = log(1+exp(-beta*c)) + log(2) + beta*c*a.
```

The [two-report bridge](FEP_TWO_REPORT_FORMULATION_BRIDGE_V1_REPORT.md) had
constant state entropy across policies. Its state-risk/Bayesian agreement
therefore does not transfer automatically. Reader preservation changes the
entropy of future success. Writing `delta=rho_1-rho_0` and
`L=h(rho_0)-h(rho_1)`, the thresholds are:

- Bayesian planning and the latent extension preserve when `c < v*delta`.
- State risk and the exact decomposition preserve when
  `c < v*delta-L/beta`.
- Outcome risk after omitting the conditional KL skips at every positive cost.

The exact decomposition still holds. Its largest checked residual was
**8.882e-16**. The new state-risk disagreement is present before any term is
dropped; it comes from the declared soft preference distribution and its
entropy term. It is not an implementation failure or a general disproof of FEP.

The extension that previously overbought information matches task utility here
because there is no information to buy. Neither objective is given a universal
success verdict across different physical and observation contracts.

## Controls, boundaries and ties

When there is no reader damage, maintenance is ineffective, or no rewarded
task remains, every objective skips the positive-cost action. The outcome-only
score still ignores report quality; skipping alone does not establish correct
task preferences.

With the original reliability pair and price 0.40, increasing beta to 16 makes
state risk choose useful maintenance, giving utility 0.60. At beta 1 and zero
price, it instead rejects even free perfect preservation: its threshold is
negative. Both facts follow from the analytic formula and were specified
before execution. They illustrate dependence on the finite preference scale,
not a scale selected after observing results.

At the state threshold `0.5-log(2)/4`, the three state-optimal policies have
utilities spanning **0.50 to 0.673286795140**. The representative is chosen
lexicographically; all policies and their utility range remain in the data.
At the task threshold 0.50, the three Bayesian/extension optima all have utility
0.50. In the free-maintenance fixture, the outcome-only score ties all four
policies, spanning utility **0 to 1**. No favorable tie is promoted to a result.

The model preserves an already known record's physical expression. It does
not model forgetting, acquisition of a decoder, changing goals, collective
organization, or autonomous learning of maintenance efficacy. The required
single output path is a real restriction: an intact alternative route could
remove the need for this maintenance. No conditional policy can inspect the
hidden fault. Only deterministic policies are compared; an additional rule
for randomized policy selection is not silently included.

## Verification and evidence

The checker enumerated **44 policy distributions** in eleven settings,
yielding **220 objective scores**. All **55 optimum sets**, **44 content-bit
symmetry comparisons**, **838 numeric comparisons** and **254 structural
checks** passed. It also checks the state score after a one-to-one change to
fault coordinates, transforming the preferred joint consistently.

Maximum numeric residual was **3.5527136788005009e-15**, below the fixed
`1e-12` tolerance. Calculation time was **0.003857389 seconds** on one Python
3.10.12 process. There were no random draws, exclusions, failed executions,
retuned fixtures or reruns. The source syntax check preceded execution.
The under-ten-second forecast justified foreground execution; one process
stayed below the user's four-CPU ceiling.

The external mount was verified before writing. The complete record is
**44,602 bytes**, stored only under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/`:

- [Results and all policy scores](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/RUN_LOG.txt)
- [Input/output manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/MANIFEST.json)

The manifest freezes the specification and checker and identifies both output
files. All four hashes were checked after execution. Preserve those inputs
and the complete record. The report and status notes are outside the frozen
calculation inputs. All earlier inputs, results and manuscript files were left
untouched by this task; no sister project or new literature was searched.

Reproduction uses a **new**, unused directory under the mounted namespace:

```bash
python -B check_fep_reader_preservation.py \
  --output /mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/reproduction-01
```

The authorized calculation is complete. Before extending the model, the useful
next step is scientific review of the state, observation and policy assumptions
and of how narrowly this result supports the original pivot. No further run
or manuscript integration was launched.
