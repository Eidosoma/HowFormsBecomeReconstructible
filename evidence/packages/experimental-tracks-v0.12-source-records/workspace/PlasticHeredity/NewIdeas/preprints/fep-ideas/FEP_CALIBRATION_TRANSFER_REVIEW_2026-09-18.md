# Scientific review: calibration, persistent faults and mistaken transfer

**Completed 18 September 2026.** The user approved review of the
[calibration-transfer study](FEP_CALIBRATION_TRANSFER_V1_REPORT.md), focusing
on independent read errors and correctly specified transfer. Its calculation
stands. The positive maintenance result is conditional on those assumptions;
it does not establish reliable diagnosis of arbitrary reader faults.

The review combines analytic arguments with a
[prospectively specified arithmetic check](FEP_CALIBRATION_TRANSFER_REVIEW_CHECKS_2026-09-18.md).
The [checker](check_fep_calibration_transfer_review.py) reads the existing
unique policy from the sealed result. It changes physical truth and evaluates
fixed controls without refitting, optimizing another controller or rerunning
the original study. Manuscript integration remains with the other agent.

## 1. What the original result establishes

In its main model, all five objectives select the same policy: read the first
record twice, maintain the later reader only after disagreement, and copy the
final read. With the declared independent noise and persistent mechanism,
its net utility is **0.65125**, against **0.625** without calibration.

The two records hold independent targets. The first supplies information about
the reader mechanism, not the second answer. Content validity remains at its
supplied prior. This is a valid example of useful, costed maintenance selected
by state-preference FEP and conventional Bayesian planning alike.

The original reset control correctly told its controllers that the mechanism
would reset. It therefore did not establish that the persistent policy is
robust to an incorrect transfer belief. Likewise, its random-reader class
generated new independent errors on each read. Agreement was evidence for
an intact reader only within that restricted candidate family.

## 2. Mistaken transfer: less value, without different visible data

Hold the original policy fixed. Let tau be the probability that the entire
mechanism is copied from the calibration record to the next record; otherwise
draw it independently from the original prior. Tau is a transition-mixture
weight, not the probability that two independent draws happen to match.

Direct calculation gives

```text
U_frozen(tau) = 0.620 + tau/32
U_no_calibration_copy = U_always_maintain = 0.625.
```

Thus the fixed calibration policy remains useful for tau greater than 0.16.
Its benefit declines continuously; it does not require perfect persistence.
The four fixed checks give:

| Transfer weight tau | Frozen policy utility | Gain over either prior-only control |
|---|---:|---:|
| 0 | 0.620000 | -0.005000 |
| 0.16 | 0.625000 | 0 |
| 0.5 | 0.635625 | 0.010625 |
| 1 | 0.651250 | 0.026250 |

More seriously, **the complete visible trajectory under this policy has the
same distribution at every tau**. Calibration histories 00 and 11 each have
probability 3/8; 01 and 10 each have probability 1/8. The final read is fair
conditional on any of them. Maintenance and reporting are known functions of
those observed bits. Neither the target nor success feedback is supplied.

Consequently these observations cannot update prior odds over tau. Correct
observable predictions do not establish that the inferred mechanism still
predicts task correctness. This is an identifiability limit for the selected
observation policy, not an assertion that every possible intervention is
uninformative.

## 3. Consistent faults defeat the disagreement rule

First preserve each individual read's marginal law but change its dependence
across time. In the random-reader class, draw one fair flip F and reuse it:
`Y=R XOR F` for both calibration reads and the final unmaintained read. The
intact class still reads natively. Content and reader priors remain unchanged.

The two calibration reads now always agree. The frozen policy never maintains
and obtains **0.620**, versus **0.625** for copying without calibration.
Both the calibration and final single-read laws match the original laws
under the copy control. The failure comes from the dependence between errors,
not worse marginal reader performance.

A stronger counterexample is a systematic reversal of every unmaintained
read. With the same 1/2 prior probability of intact content, copying the
reversed output has accuracy 1/4. The calibration policy again sees agreement,
declines maintenance and earns **0.245** after its 0.005 access cost.

| True reader law | Frozen policy | Copy, no calibration | Invert, no calibration | Blind guess |
|---|---:|---:|---:|---:|
| Shared fair flip in the original random-reader class | 0.620 | 0.625 | 0.375 | 0.500 |
| Native reading in every reader | 0.745 | 0.750 | 0.250 | 0.500 |
| Permanent reversal in every reader | 0.245 | 0.250 | 0.750 | 0.500 |

The native and reversal truths have **identical visible laws under the frozen
policy**, despite their 0.50 difference in task utility. Both calibration reads
agree and the later read is fair. Even an exact observation-likelihood
calculation cannot distinguish these truths through that interface.

The inversion control demonstrates remaining information, not successful
learning by the original agent. Knowing the orientation would allow utility
0.75 without maintenance. In both native and reversal cases the read retains
one bit about R1, and `I(X1;Y1)=log(2)-h(1/4)=0.130812035941` nats. The channel
has not lost its information; the agent applies the wrong interpretation.
The permanent-reversal case changes the true mechanism beyond the original
family and is not a matched comparison against a better-informed learned agent.

More repeated agreement is not a solution by itself. Analytically, if one
mechanism persists across n calibration records, the original family gives
the event of agreement within every pair probability
`1/2 + (1/2)*2^(-n)`. A stable mapping gives it probability 1. The Bayes factor
for stability over that original mixture approaches only 2, while the
original family's posterior probability of its native intact-reader class
approaches 1. It can explain all agreement through that class without testing
orientation. This many-record argument is analytic, not a new sampled run.

## 4. What an independent reference changes

The existing action space already permits a paid reference Z1 linked to X1.
Keeping the frozen maintenance rule and additionally buying that reference
makes the final read/reference relationship observable. For the IID-transfer
family:

```text
P(Y1=Z1 | calibration agreement) = 9/16 + tau/48
P(Y1=Z1 | calibration disagreement) = 5/8.
```

The laws are now distinguishable in principle. Their observable total-variation
distance for tau=0 versus tau=1 is only **1/64** for this query policy. One
noisy query cannot certify persistence. For native versus permanently reversed
reading, final read/reference agreement is **5/8 versus 3/8**; the corresponding
observable-law distance is **1/4**.

The reference is not free. The fixed queried policy reports Z1 and scores
**0.46375** in the four IID-transfer cases, after calibration, maintenance and
reference costs. It is a witness that the laws can be tested through a
declared resource, not an optimized or cost-effective diagnostic strategy.
The reference's own calibration and independence remain supplied assumptions.

## 5. FEP interpretation and the entropy qualification

All five objectives originally selected the same policy, so the failures above
are shared. They do not rank FEP against Bayesian planning. They separate
having accurate beliefs within a candidate family from establishing that the
family and its target relationships are adequate. An information reward or
an internally exact posterior cannot recover a distinction absent from its
observations or model.

The state-risk calculation also needs to respect the changed physical law.
In the original model, maintenance removes a fresh random read error, yielding
the entropy term `log(2)*P(m=1,T1=0)`. Under the shared flip, F is already fixed
by the hidden pair (R0,Y01) in the declared full trajectory state. Conditional
on that state and R1, the final unmaintained read is deterministic.

Using the same state alphabet and preferred joint, maintenance then changes
the readout mapping without removing a new entropy contribution. State
entropy is constant across the seven checked policies in the shared-flip,
native and reversal truths, and their true-law state-risk differences equal
`-beta*Delta_U`. The original IID entropy penalty cannot simply be carried
over to these correlated mechanisms.

These true-law scores are review calculations, not scores available to the
misspecified controller. The result depends on retaining the full trajectory
state, including its unobserved record and buffered readouts. No universal
representation-invariance or newly optimized FEP controller is claimed.

## Verdict and next step

Retain the original positive result with its explicit model conditions. It
shows that paid diagnosis can guide later maintenance, not that agreement
certifies a trustworthy reader or that successful prediction establishes
correct interpretation. The content/reader distinction remains essential.

The next proposed step is an analytic design that admits stable reversal and
uncertain transfer, then asks when a paid independent reference justifies
changing interpretation, maintaining the reader, or using the reference
directly. Match access and costs across Bayesian and explicitly named FEP
objectives. A model supporting only independent noise cannot adjudicate those
alternatives. No such successor has been implemented or run in this review.

## Verification and preservation

All **49 distributions** from seven physical laws and seven fixed policies
passed: **386 numeric comparisons** and **55 structural checks**. Maximum
residual was **1.0019762797242038e-14**, below the fixed 1e-12 tolerance.
Calculation took **0.420610994 seconds** on one Python 3.10.12 process. The
original common policy, planned utility, physical entropy and state score
were recovered from the sealed record and independently checked in its
original physical law.

The mount and syntax were checked before execution. All seven recorded inputs
and both outputs were hash-verified afterward. No failed run, retuning,
original-study rerun or new optimum search occurred. The **72,580-byte** record
is on the external mount:

- [Fixed-policy results and observable laws](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-review-2026-09-18/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-review-2026-09-18/attempt-01/RUN_LOG.txt)
- [Frozen inputs and output hashes](/mnt/bioIce1/fep-ideas/formal-checks/fep-calibration-transfer-review-2026-09-18/attempt-01/MANIFEST.json)

Preserve the check specification, checker and outputs. This review and status
notes are outside the frozen arithmetic inputs. Earlier frozen studies and
manuscripts remain unchanged; the preceding research report links to this
qualification. No fresh literature or sister-project search was needed for
these derivations.
