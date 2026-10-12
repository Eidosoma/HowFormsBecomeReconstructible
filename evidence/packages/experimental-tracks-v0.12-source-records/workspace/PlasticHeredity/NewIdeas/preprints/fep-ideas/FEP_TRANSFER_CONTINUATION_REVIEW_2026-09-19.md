# Scientific review: transfer assumptions and the state used by FEP

**Completed 19 September 2026.** The
[three-record calculation](FEP_TRANSFER_CONTINUATION_V1_REPORT.md) remains
correct. Its useful-checking result depends on the supplied temporal model,
and its state-risk/Bayesian equivalence depends on the retained state. The
review verifies counterexamples to extending either claim without qualification.

The [prospective review checks](FEP_TRANSFER_CONTINUATION_REVIEW_CHECKS_2026-09-19.md)
and [checker](check_fep_transfer_continuation_review.py) evaluate the saved
policies and fixed controls. No controller was refit, no new optimum was
searched, and the original optimization was not rerun. All forty-two
distributions passed on the first execution in 2.174277625 seconds.

## 1. What remains supported

Within the original supplied model, checking twice improves net utility from
0.625 to 0.638 because its evidence changes a later reference-purchase decision.
The action-timing control establishes that consequence. With known intact
content and perfect calibration references, inference about the shared transfer
class supports contingent maintenance at utility 0.86875 versus 0.85.

All five objectives selected the same policy in the main fixture. Bayesian,
state, full and mechanism objectives shared the isolated-fixture policy;
its task-information extension instead chose unconditional maintenance.
The original utility, entropy and all five scores of the saved Bayesian
representatives were reconstructed from their sealed records before making
counterfactual comparisons.

The positive examples establish useful action within a specified model family.
They do not establish that past agreement identifies the future transition
law among alternative temporal models.

## 2. The same calibration evidence can imply a different future

The original model draws one stable-versus-reset class for an entire episode.
With probability 0.75, every orientation is the same; otherwise they are
independent fair draws. The review retains the complete calibration law,
including its hidden initial mechanism, and changes only the final orientation.

In **stepwise dynamics**, the final transition copies the previous orientation
with probability 0.75 and otherwise redraws it, independently of the initial
mechanism selection. Adjacent orientations match with probability 7/8 in
both the original and stepwise laws. But orientations separated by two steps
match with probability 7/8 in the original law and 25/32 under stepwise change.
The dependence across transitions differs even though adjacent reliability
and all calibration evidence agree.

In **late reset**, the final orientation is simply redrawn independently.
Again, everything available from the calibration records has the same law.
The controller retains its original policy and beliefs in both counterfactuals.

| Physical truth | Main frozen policy | Main recent-anchor control | Isolated frozen policy | Isolated maintenance control |
|---|---:|---:|---:|---:|
| Original episode class | 0.638000 | 0.625000 | 0.868750 | 0.850000 |
| Independent transition changes | 0.619250 | 0.625000 | 0.821875 | 0.850000 |
| Final orientation reset | 0.488000 | 0.475000 | 0.493750 | 0.850000 |

In the main stepwise case, the frozen checking policy loses to a single
recent calibration. After late reset, it falls below the 0.50 net score of
blind guessing; uncalibrated maintenance or direct reference use earns 0.60.
These are comparisons with feasible fixed controls, not new globally optimal
solutions for the changed laws.

The isolated control is informative about scope. With a shared episode class,
conflicting past orientations identify the reset class and justify maintenance.
Under stepwise transitions, knowing that an earlier transition changed does
not make the next transition less reliable. The original contingent-maintenance
rule then loses to unconditional maintenance. The task extension's original
maintenance policy happens to retain 0.85 in these counterfactuals. This does
not establish that it is generally more robust.

## 3. Selective checking leaves an observational blind spot

The complete calibration distribution is identical across all three laws.
More strongly, **the main frozen policy has the same complete visible
trajectory law under the original dynamics and late reset**, although utility
falls from 0.638 to 0.488. No true target or success feedback is delivered to
the controller.

The agent buys a final reference only after its calibration suggestions
disagree. Those are precisely the histories where its original model already
predicts no useful orientation. A late reset therefore leaves its checked
branches looking unchanged, while damaging the unchecked agreement branches.
Under this feedback contract, even repeated observations from that fixed
policy cannot distinguish those two laws.

In the isolated fixture, the frozen policy never buys the final reference.
All three laws consequently have identical visible trajectories, despite the
large utility differences. Learning within the original class does not certify
the class itself.

A fixed diagnostic witness adds final reference access on every history while
preserving the original maintenance and reporting decisions. It makes the
laws distinguishable. The exact total-variation distances from the original
law are:

| Fixture and policy | Stepwise alternative | Late-reset alternative |
|---|---:|---:|
| Main frozen | 0.0150 | 0 |
| Main with every branch audited | 0.0300 | 0.1200 |
| Isolated frozen | 0 | 0 |
| Isolated with every branch audited | 0.0375 | 0.3000 |

This is a witness of available evidence, not a free or decisive diagnostic.
The extra expected cost is 0.186 in the main case and 0.30 in the isolated
case. For example, under the original main truth it reduces utility from
0.638 to 0.452 without changing the reports. No audit policy was optimized.
These figures make the cost of exposing a trusted branch explicit.

## 4. Removing hidden state can reverse the FEP ranking

The second review changes no physical law, observation or task. It changes
which state the state-risk objective scores.

The original full state S retains every physical variable, including hidden
mechanisms and unobserved buffered signals. For any fixed deterministic policy
its entropy is constant, so its risk ranks policies as Bayesian utility:

```text
J_full = KL(Q_S || C_S) = log Z_C - beta*U - H(S).
```

Now project to **T=(X2,O)**, retaining the entire visible trajectory O and the
hidden target X2 required to express success. X2 remains hidden from the
controller. All actions, costs, observations and reports remain represented.
O is still a deterministic function of the new state, so ambiguity is zero.
The predictive distribution is the exact marginal of the same physical model.
This is an objective audit, not a separately implemented controller.

Use the exact marginal preference C_T obtained from C_S, including its hidden
state multiplicities. Do not silently replace it by a uniform preference on
the smaller alphabet. The checker verifies that the preferred joint marginal
of target, report and every cost-bearing action is preserved.

Nevertheless the two risks satisfy

```text
J_full = J_projected
         + E_QT KL(Q(S|T) || C(S|T)).
```

That final conditional term varies across policies. Omitting it can change
the action ranking even though the preferred marginal of task outcomes and
costs is unchanged:

| Original fixture | Full-risk difference, frozen minus recent anchor | Projected-risk difference |
|---|---:|---:|
| Main | -0.104000 | +0.094964 |
| Transfer isolated | -0.150000 | +0.317993 |

Lower risk is preferred. Thus full risk favors the useful two-check policy,
whereas projected risk favors the single recent anchor in both comparisons.
These are ranking reversals between two fixed policies, not claims about a
globally optimal projected controller.

The removed conditional terms differ by -0.198964 and -0.467993 respectively.
Restoring them exactly recovers the original scores. The projected identity
also makes the policy dependence explicit:

```text
J_projected = log Z_C - 17*ln2 - beta*U
              + E(number of observed bits)*ln2 - H(O) + I(X2;O).
```

The equality with Bayesian planning therefore does not follow merely from
using the same task preferences and observations. It also depends on which
latent distinctions the state-risk objective retains. This is a noninvertible
projection, not a renaming of variables: bijective relabeling preserves KL.
The review establishes neither representation as uniquely correct, and does
not refute the original full-state calculation or all FEP formulations.

## 5. Scientific judgment and next step

The useful-checking mechanism remains a valid conditional result. The review
identifies two distinct qualifications:

- Matching past calibration and adjacent reliability does not establish the
  temporal dependence needed to justify a future action. A policy's selected
  checks can leave its damaging model error unobservable.
- State-preference FEP needs an explicit representation contract. Marginalizing
  hidden variables while preserving observable task preferences can still
  alter the policy score through a discarded conditional KL.

The main dynamics failure applies to the policy shared by all five original
objectives. It is a model-assumption failure, not a uniquely FEP failure.
The representation result is directly about the specified FEP state-risk
comparison. The previously demonstrated Bayesian equivalence remains correct
for the declared full state, with the full preferred joint retained.

The next proposed local deliverable is a short **FEP representation contract**:
state which physical variables are retained or marginalized, specify the
induced preferences, and derive which conditional terms must be retained to
preserve policy-score differences. A policy-independent removed term is
sufficient for unchanged ranking; it is not necessary for every particular
finite policy set to retain its ordering. Resolve that contract before adding
more temporal mechanisms or a larger campaign. No successor is launched here.
Manuscript integration remains with the other agent.

## 6. Integrity record

The check specification preceded implementation and execution. The source
manifest, selected policies, syntax and mounted output drive were checked
before numerical work. The run started at
**2026-09-19T11:40:27.573923+00:00**, using Python 3.10.12 and one process.
All **42 distributions**, **784 numeric comparisons** and **298 structural
checks** passed on the first execution. Maximum residual was
**4.97379915032e-14**, below the frozen 1e-12 tolerance; runtime was
**2.174277625 seconds**.

All seven input and two output hashes were verified afterward. The complete
**277,926-byte** external record is:

- [Fixed-policy risks, utilities and observable laws](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-review-2026-09-19/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-review-2026-09-19/attempt-01/RUN_LOG.txt)
- [Frozen inputs and output hashes](/mnt/bioIce1/fep-ideas/formal-checks/fep-transfer-continuation-review-2026-09-19/attempt-01/MANIFEST.json)

Preserve the check specification, checker and outputs. The original report
links this qualification; its frozen specification, implementation and data
are unchanged. No failed execution, refitting, new controller optimization,
original-study rerun, manuscript edit or fresh literature/sister search occurred.
