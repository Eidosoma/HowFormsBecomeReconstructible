# Hidden preferences: what does preserving useful information justify?

**Completed 19 September 2026.** The
[prospective specification](FEP_HIDDEN_PREFERENCES_V1.md) and
[checker](check_fep_hidden_preferences.py) passed their first scientific
execution: 14 fixed-policy distributions, 126 preference scores and 126
relabeling checks in 2.929488602 seconds on one process. All prospective
predictions below were confirmed. Two earlier launch requests had been
rejected before process creation by an approval-service authentication error;
that operational interruption is resolved and recorded in Section 6.

The central conclusion is that **the task does not uniquely determine
preferences over hidden states**. In this model, preferring a reader output
that literally matches the target adds a different objective from preserving
the ability to interpret that output correctly. That extra preference can
favor costly maintenance over the useful calibration policy. The original
FEP calculation remains valid under its original preferred joint.

## 1. A preference choice, with the physical problem unchanged

The [representation contract](FEP_REPRESENTATION_CONTRACT_V1.md) showed how to
preserve an objective when removing state variables. Here nothing is removed.
The state, physical dynamics, observation access, policy timing, task, costs
and beta=8 remain those of the original
[continuation model](FEP_TRANSFER_CONTINUATION_V1_REPORT.md). Observation
ambiguity remains zero. Only the preferred distribution within hidden-state
fibers changes.

Let B=(X2,D,a0,a1,m,b) collect the hidden target, final report and every
cost-bearing action. Hold its entire preferred joint C_B fixed. For any
positive conditional r(s|B), fixed across policies,

```text
C_r(s)=C_B(B(s))*r(s|B(s))
J_r(pi)=KL(Q_pi,B || C_B)
        + E_Qpi,B KL(Q_pi,S(.|B) || r(.|B)).
```

The second term can vary between policies. Specifying the same preferred
target/report/cost joint therefore does not specify the full FEP objective.
This is a direct conditional-KL decomposition, not a claim that one preference
is automatically the correct one.

Starting from the original counting-weight preference C0, an explicit change is

```text
C_lambda,f(s)=C0(s)*exp(lambda*f(s))/M_lambda,f(B(s))
M_lambda,f(B)=E_C0(.|B) exp(lambda*f(S)).
```

Normalizing within each B fiber preserves C_B exactly. If f is already just
a function of B, this change cancels completely. An additional value for task
success itself cannot be introduced this way while retaining that same joint.

## 2. Three properties with different meanings

The comparison uses three binary properties:

| Preference favors | Definition | Consequence under the supplied physical model |
|---|---|---|
| Correct stored content | R2=X2 | No permitted action changes R2. Its probability is constant across policies. |
| Literal reader agreement | Y2=X2 | Maintenance can increase it, even when a learned inversion already makes reading useful. |
| Correctness with the true decoder | Y2 xor ((1-m)*F2)=X2 | Equals correct stored content on every possible trajectory; the true F2 is an oracle input, not agent knowledge. |

Each property holds on half of every preferred B fiber. This counting statement
uses the original full preferred alphabet, including states that the predictive
model cannot produce. Thus M_lambda=(1+exp(lambda))/2 for all three, and

```text
J_lambda,f(pi)=J0(pi)-lambda*E_Qpi f+log M_lambda.
```

In the supplied dynamics, Y2=R2 xor ((1-m)*F2). Correctness with the true decoder
therefore equals stored-content correctness pointwise. Both have expectation
(1+p)/2 for every allowed policy. Their score shifts are constant, so they
preserve every original deterministic-policy ranking, not merely the seven
policies chosen for verification. These preferences do not give an agent a
missing content-repair action or reveal its hidden decoder.

The two preferred joints differ on some predictively impossible states but
produce identical scores here. Even policy-score agreement need not identify
a unique preferred joint.

Literal agreement is different. Because full trajectory entropy is constant
across these deterministic policies, its score is equivalent, up to constants,
to maximizing

```text
original expected utility + (lambda/beta)*Pr(Y2=X2).
```

It introduces an additional objective for the unprocessed output. It can
reward alignment even on branches where the report comes from an independent
reference or where a free inversion suffices. The actual task scores the final
report and all costs, not literal agreement as an additional benefit.

## 3. Verified preference witnesses

Compare the saved two-calibration policy with unconditional maintenance.
Their original utilities were reconstructed from the sealed review. The
literal-agreement expectations and changed-score gaps below match the
prospective analytic predictions. Lower risk is preferred; Delta means
maintenance minus the saved policy.

| Fixture | Saved-policy utility | Maintenance utility | Literal agreement: saved / maintenance | Original Delta J | Verified Delta J at lambda=2 |
|---|---:|---:|---:|---:|---:|
| Main | 0.638 | 0.600 | 1/2 / 3/4 | +0.304 | -0.196 |
| Transfer isolated | 0.86875 | 0.850 | 9/16 / 1 | +0.150 | -0.725 |

The verified changes follow directly:

```text
main:              Delta J = 0.304 - lambda/4
transfer isolated: Delta J = 0.150 - 7*lambda/16.
```

The crossings are lambda=152/125 and lambda=12/35 respectively. At lambda=2,
literal-agreement preference favors maintenance in these two comparisons,
losing original utility 0.038 and 0.01875. Content and oracle-decoding
preferences retain the positive original gaps for every lambda.

The checker assessed all seven fixed review policies and confirmed all 18
minimum sets: three preference families at three strengths in two fixtures.
At lambda=0, all families select the saved policy. Content and oracle-decoding
preferences retain it at every tested strength. Literal preference ties the
saved policy with maintenance at its analytic crossing and selects maintenance
at lambda=2. Both members of each tie are retained even though their task
utilities differ. These are complete minima within the seven declared policies,
not newly established global optima over all possible policies.

## 4. A coding convention must not masquerade as useful information

Relabel the final reader bit Y2'=1-Y2, carrying the observation interpretation,
reports and preferred distribution through that bijection. Task performance
and every KL score remain unchanged by a change of summation index.
The original literal-agreement preference now favors Y2'!=X2.

Reimposing Y2'=X2 would instead favor the opposite physical readout. The
derived maintenance-minus-saved gaps at lambda=2 then become +0.804 and +1.025.
Both gaps were verified, along with all 126 scores under the consistently
carried preference. This does not claim a failure of KL
invariance: the latter comparison deliberately changes the preference.

A physical requirement for a particular output code could justify valuing
literal agreement. Our task provides a freely usable decoder and charges
only the declared resources, so that requirement is not present here.

## 5. Scientific judgment

Under the current success-minus-cost endpoint, hidden properties have justified
instrumental value when they improve an action's expected task performance.
The original model already demonstrates that useful calibration can have
that value. It does not supply an additional intrinsic value for matching a
particular code or for knowing a decoder that the agent cannot access.

For this project:

- Keep the original preferred joint explicit in historical FEP comparisons.
  Its counting measure is a declared modeling convention, not a uniquely
  neutral law derived from the task.
- Report content fidelity, raw reader agreement and accessible decoding
  separately. Use external task performance and full costs to establish
  whether a change actually preserves useful information.
- Introduce a further hidden-state preference only with a separately justified
  valued endpoint: for example a specified future workload, a decoder
  restriction, or a measured cost of maintaining the capacity to decode.
  Include that endpoint prospectively instead of treating it as a free bonus.

This does not show that hidden-state preferences can never be justified.
It shows what the present task fails to determine. Nor does it settle model
adequacy: the preceding review's undetectable late reset remains a distinct
failure mode. A preferred hidden property cannot create evidence that the
controller never receives.

The comparison is complete. The next proposed local step is an analytic
definition of usable information through performance on a specified future
task, using only the decoder and evidence the agent can access and charging
their costs. Determine whether that adds a justified endpoint or clarifies
the existing task value before proposing another FEP objective. No successor
calculation is launched here. Manuscript integration remains with the other agent.

## 6. Execution and integrity record

The specification preceded implementation. Python syntax and imports passed;
these checks did not execute the numerical verification. The drive was verified
as `/mnt/bioIce1` on `/dev/sdc1`, with about 92 GB free, but exposed read-only
inside the sandbox. The single-process run was forecast below thirty seconds.
Seven direct input identities were recorded before numerical verification.

Executed command:

```bash
python -B check_fep_hidden_preferences.py --output /mnt/bioIce1/fep-ideas/formal-checks/fep-hidden-preferences-v1/attempt-01
```

Automatic approval rejected the command before process creation. Its reason
was: the access token could not be refreshed after logout or an account change,
and a fresh sign-in was required. No code/data risk was specified. At the
**2026-09-19T12:16:05.931520+00:00** read-only checkpoint, the proposed output
directory did not exist. At that point there was no scientific execution or
result. The user was asked
to sign in again and confirm the retry, then explicitly selected **"Retry after
sign-in"**. The unchanged command was attempted again and rejected before
process creation with the same token-refresh error, now during a remote review
task. At **2026-09-19T12:21:45.204259+00:00**, the output directory still did not
exist. These errors identified an approval-service token failure; they did not
establish that the user's chat session was logged out. No workaround or
local-data fallback was attempted.

After the user reported signing in again, the unchanged command started at
**2026-09-19T12:40:25.990883+00:00** and completed successfully. The existing
process was checked after the conversational interruption; no duplicate job
was launched. This was the first actual scientific execution. All **14
distributions**, **126 preference scores**, **126 relabeling checks**,
**3,240 numeric comparisons** and **44,190 structural checks** passed.
Maximum residual was **9.05941988094e-14**, below the frozen **1e-12** tolerance.
Runtime was **2.929488602 seconds** on one Python 3.10.12 process. No input
changed between the rejected launches and this execution.

The **84,361-byte** external record contains:

- [Scores, fixed-set minima, preferred marginals and identity residuals](/mnt/bioIce1/fep-ideas/formal-checks/fep-hidden-preferences-v1/attempt-01/RESULTS.json)
- [Execution log](/mnt/bioIce1/fep-ideas/formal-checks/fep-hidden-preferences-v1/attempt-01/RUN_LOG.txt)
- [Seven frozen inputs and two output identities](/mnt/bioIce1/fep-ideas/formal-checks/fep-hidden-preferences-v1/attempt-01/MANIFEST.json)

All seven input and two output hashes and byte counts were verified afterward.
The result file is 81,617 bytes, SHA-256
`30151a21eeb00d05734d96eb01adb65045f3b7645bb4ddbc00e0fb883615f26f`.
The log is 394 bytes, SHA-256
`2ea69f647f10603f07931de90fcfc4faa195b054cce4d335a6fe229ddca7cc3d`.

The principal frozen input identities are:

| File | Bytes | SHA-256 |
|---|---:|---|
| FEP_HIDDEN_PREFERENCES_V1.md | 9302 | `203da61d1d0e02de34753a73822b348c140b607cd2d92f232320a23d83039480` |
| check_fep_hidden_preferences.py | 13146 | `0804fe654c524d504286691cce3d84e0b85cc6023b9293b210234c368271c8bc` |
| FEP_REPRESENTATION_CONTRACT_V1.md | 13031 | `c6931015b2820ec6db935449ccc35b626e4d9edaad2c47279cee82b98a887287` |

Preserve these inputs and the complete external record. The checker verified
the source review's sealed inputs and outputs before evaluating its fixed
policies; the original utility and state-risk values were also reconstructed.
No refitting, global policy optimization, new temporal mechanism, scientific
failure or retuning occurred. Earlier sources, outputs and manuscripts remain
unchanged. This report uses local derivations and exact arithmetic verification,
with no fresh literature or sister-project search and no claim of literature
novelty. The approval rejections were operational failures before execution,
not failed scientific attempts.
