# Calibration can guide later maintenance when the mechanism persists

**Completed 18 September 2026.** The [prospective specification](FEP_CALIBRATION_TRANSFER_V1.md)
preceded the [checker](check_fep_calibration_transfer.py) and its first,
successful execution. This is an exact finite-model result, not empirical
evidence. Manuscript integration remains with the other agent.

**Subsequent scientific review:** the [calibration-transfer review](FEP_CALIBRATION_TRANSFER_REVIEW_2026-09-18.md)
retains this calculation but tests the frozen policy under changed physical
laws. Mistaken transfer and consistent reader faults can remove its benefit;
native and reversed readers can produce identical visible data but different
task performance. The original independent-error entropy term also needs
rederivation for persistent faults. Frozen inputs and results are unchanged.

## What worked

Diagnosis on one record can improve maintenance decisions for a different
record. In the main example, Bayesian planning, state-preference FEP and all
three declared information-target extensions select the same contingent policy:

1. Pay for two reads of the calibration record.
2. If they agree, leave the later reader alone.
3. If they disagree, maintain it before reading the later record.
4. Report the later reader's output.

The policy earns **0.65125**, compared with **0.625** for the best policy without
calibration. These are expected correct-report rewards minus all access and
maintenance costs. Every main optimum is unique. The gain is shared with
ordinary Bayesian planning; it is not an advantage unique to FEP.

The two targets are independent, so the first record cannot supply the second
answer. What transfers is information about the reader's mechanism. Maintenance
changes the later reading channel without changing the saved content.

## Where the gain comes from

The model independently allows intact or randomly replaced content and intact
or random reading. All four mechanisms have prior probability 1/4. In the
main case, that mechanism persists across the two records; individual targets,
replacement bits and reading errors do not persist.

Two calibration reads agree with probability 3/4. Agreement raises the
probability of an intact reader to 2/3; disagreement identifies the random
reader within this supplied family. The probability of intact content remains
1/2 in both cases. Thus this policy **does not learn content validity**. It
uses reader evidence while averaging over the supplied content prior.

Each calibration read costs 0.0025. Maintenance costs 0.125 and is selected
on 25% of histories. Final accuracy is 0.6875, giving

```text
Net score = 0.6875 - 2*0.0025 - 0.25*0.125 = 0.65125.
```

Without calibration, never maintaining and always maintaining tie at 0.625:
their accuracies are 0.625 and 0.75 respectively, but the latter pays 0.125.
The improvement comes from selecting maintenance by evidence, not from
claiming higher raw accuracy than every comparator.

Independent references are available on both records, with 0.75 accuracy.
Their access costs are 0.10 for calibration and 0.25 for the final task in
this example. All controllers may answer directly from the final reference.
The optimal policy declines both references at these prices. No restriction
forces it to preserve the reader.

## FEP dependence and controls

The actual final reader output is part of the physical state. Maintaining a
random reader removes its read-error entropy. The declared state-risk
objective therefore contains an entropy term in addition to task value:

```text
J_state = constant - beta*U + log(2)*P(maintain and reader initially random).
```

This is the representation-dependent effect already exposed by the preceding
maintenance models. The direct conditional-KL decomposition remains exact.
The full-state, task-target and future-regime scores are separately declared
EFE-inspired extensions, not interchangeable formulations of all FEP.

For the main strategy, calibration improves the Bayesian score when its total
price is below **0.03125**. At beta=8, the state objective's threshold is
**0.009589150608**. The chosen price 0.005 is below both. The beta=8 example,
beta=4 control and price boundaries were specified before calculation; no
parameter was retuned after results.

The table gives net task utility of each objective's optima. All policies
tied within a displayed cell have that same utility. “Task” targets X1;
“regime” targets the future mechanism H1.

| Condition | Bayesian | State risk | Full-state extension | Task extension | Regime extension |
|---|---:|---:|---:|---:|---:|
| Persistent, beta=8 | 0.65125 | 0.65125 | 0.65125 | 0.65125 | 0.65125 |
| Mechanism reset | 0.62500 | 0.62500 | 0.62000 | 0.62500 | 0.62500 |
| Persistent, beta=4 | 0.65125 | 0.62500 | 0.48875 | 0.65125 | 0.65125 |
| Calibration price 0.02 | 0.63625 | 0.62500 | 0.63625 | 0.63625 | 0.63625 |
| Final reference price 0.01 | 0.74000 | 0.74000 | 0.73500 | 0.74000 | 0.73500 |
| Maintenance disabled | 0.62500 | 0.62500 | 0.62000 | 0.62000 | 0.62000 |
| Content erased | 0.50000 | 0.50000 | 0.49500 | 0.50000 | 0.49500 |

The controls explain the scope of the positive result:

- **Reset:** the controller is told that the later mechanism is independent.
  Bayesian, state, task and future-regime objectives skip calibration. The
  full-state extension still buys two reads of the old record, paying 0.005
  for information with no future task use. Equal net scores for the other
  objectives do not imply identical maintenance choices; the prior task tie
  remains in the data.
- **Weaker preferences or higher calibration price:** state risk can reject
  useful calibration because it also penalizes the entropy reduction from
  subsequent maintenance. At beta=4 the full-state extension instead buys
  both calibration signals and sometimes the final reference, substantially
  reducing utility through information costs.
- **Cheap direct reference:** Bayesian/state/task objectives skip calibration
  and maintenance, answer from the final reference, and earn 0.74. The full
  and regime extensions spend an additional 0.005 on calibration without
  improving final accuracy.
- **Disabled maintenance:** Bayesian/state skip calibration. The information
  extensions pay for it despite no gain in net task value. All local optima
  reject the ineffective maintenance action itself.
- **Content erasure:** reader maintenance cannot create information about X1.
  Without the final reference, all terminal report maps remain at chance.
  The independent reference can supply new target information, but at its
  declared price it only ties the net score of guessing. This is external
  information, not reconstruction of the lost record.

Both boundary fixtures preserve the full ties. At the Bayesian calibration
threshold, three policies attain utility 0.625: two prior-only maintenance
choices and the contingent calibration strategy. At the state threshold,
state risk ties a prior-only policy with the calibration policy even though
their task utilities differ: **0.625 to 0.646660849392**. The displayed
representative uses the specified policy order, not the best external utility.

## What remains supplied

The model supplies the candidate failure family, prior, independent read
errors, transfer law, reference calibration and maintenance efficacy. The
agent infers which mechanism it faces; it does not learn whether these
assumptions hold. The reset control uses a correctly informed controller,
so it does not test an agent incorrectly expecting persistence.

This establishes one mechanism for useful FEP-guided reader maintenance:
paid evidence has future value when it predicts a later, effective action.
It does not establish autonomous grounding, sustained biological maintenance,
discovery of the repair mechanism, or a general FEP guarantee.

The next proposed step is a focused scientific review of the two assumptions
carrying the gain: independent errors across repeated reads and correctly
specified transfer between records. Establish what survives persistent or
systematic reader faults and mistaken persistence before extending the model.
No successor is implemented or run here.

## Verification and record

Exact dynamic programming evaluated **6,840 terminal choices**, **34,200
local objective scores** and **225 initial-bundle scores** across nine fixed
fixtures. It retains **45 complete global optimum sets** as products of local
tie sets. This avoids enumerating trillions of contingent policies; it is not
a sampled policy search. Every objective and initial bundle also received a
direct whole-trajectory check: **225 trajectory audits** verified the dynamic
scores, state entropy, mutual information, utility and conditional-KL identity.

All **6,900 numeric comparisons** and **1,546 structural checks** passed on the
first execution. Maximum residual was **1.7763568394002505e-15**, below the
fixed 1e-12 tolerance. Calculation took **4.246122804 seconds** on one Python
3.10.12 process. No failed run, retuning or numerical rerun occurred.

The external mount and source syntax were checked before execution. The
manifest records the new specification/checker and the reused, unchanged
helper from the preceding reader-evidence study. All five input/output hashes
were verified afterward. The **2,141,638-byte** record is:

- [Scores, posterior branches, complete optima and trajectory audits](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01/RUN_LOG.txt)
- [Input/output manifest](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-v1/attempt-01/MANIFEST.json)

Preserve the frozen inputs and outputs. Reports and status notes are outside
the frozen calculation inputs. Earlier records and manuscripts were not
changed; no sister-project or fresh literature search was needed. Reproduction
must use a new directory on the verified external mount.
