# Hidden-state preferences with a fixed usable-information task

**Prospective specification, 19 September 2026.** The user's "lets go on all
of this" authorizes the next analytic preference comparison and its bounded
verification. The [representation contract](FEP_REPRESENTATION_CONTRACT_V1.md)
has already separated an equivalent state reduction from an objective change.
Here the state itself stays fixed. This specification precedes the checker
and its first execution; preserve it after execution.

## 1. Question and fixed resources

Does preserving the preferred joint distribution of the task and its costs
determine what a state-preference FEP objective should value about hidden
content and its reader? Distinguish three proposed properties: intact content,
literal reader agreement, and correctness after decoding with the true hidden
orientation. The last is an oracle diagnostic, not new controller access.

Use only the original episode law of the `continuation` and `transfer_isolated`
fixtures in the [sealed review](FEP_TRANSFER_CONTINUATION_REVIEW_2026-09-19.md).
Retain its full S, observations, timing, actions, parameters, beta=8, task
utility and seven saved/fixed policies. No changed temporal mechanism, policy
refitting, new global optimization or added information bonus is permitted.
State observation ambiguity remains zero, so the scored objective is
J(pi)=KL(Q_pi,S || C_S). This is the selected state-preference objective,
not a statement about every FEP formulation.

Let B=(X2,D,a0,a1,m,b) contain the target, final report and all cost-bearing
actions. The original preferred law is C0(s)=exp(beta*u(s))/Z_C on the entire
declared alphabet, including predictively unreachable states. Each B fiber
contains 2^16 states, and C_B(B)=2^16*exp(beta*u(B))/Z_C. Keep this full joint
marginal fixed, not merely its expected reward or individual marginals.

## 2. What the task leaves undetermined

Every positive, policy-independent conditional r(s|B) defines a preferred
joint with that same task/cost marginal:

```text
C_r(s)=C_B(B(s))*r(s|B(s))
J_r(pi)=KL(Q_pi,B || C_B)
        + E_Qpi,B KL(Q_pi,S(.|B) || r(.|B)).
```

Thus the task marginal alone does not select the preferred conditional.
For a fixed statistic f(s), consider the normalized conditional tilt

```text
C_lambda,f(s) = C0(s)*exp(lambda*f(s))/M_lambda,f(B(s))
M_lambda,f(B) = E_C0(.|B) exp(lambda*f(S))
J_lambda,f(pi) = J0(pi)-lambda*E_Qpi f(S)
                + E_Qpi,B log M_lambda,f(B).
```

The normalizer is mandatory to preserve C_B. If f is solely a function of B,
the tilt cancels exactly: it cannot add a new task preference while preserving
that same preferred joint. No conditional is fitted separately to a policy.

## 3. Three explicit preferred conditionals

For lambda>=0 define the following indicators on the same full alphabet:

| Name | f(s) | Meaning |
|---|---|---|
| `content` | 1{R2=X2} | The retained content is correct. |
| `literal` | 1{Y2=X2} | The unprocessed reader output matches the target. |
| `oracle_decoded` | 1{Y2 xor ((1-m)*F2)=X2} | Reading succeeds if the true orientation is supplied to a decoder. |

In each B fiber every indicator equals one on exactly half the states.
Consequently all three have the same B-independent normalizer:

```text
M_lambda=(1+exp(lambda))/2
J_lambda,f(pi)=J0(pi)-lambda*E_Qpi f+log M_lambda.
```

Verify preference normalization and every preferred B cell independently of
the predictive support. A compressed enumeration is exact: retain R2,Y2,F2
as three free bits in each B fiber and multiply each preferred mass by 2^13
for the remaining bits. This covers all 144 B cells and all 2^16 states per
fiber without materializing the whole alphabet.

On every physically possible trajectory,
Y2=R2 xor ((1-m)*F2), hence `oracle_decoded` equals `content` pointwise.
The content law is unaffected by any allowed policy, so both expectations
equal (1+p)/2. Their score shifts are policy-independent for every admissible
deterministic policy. They cannot select a better preservation action in this
model; no action changes the stored R2. These two preferred joints differ off
physical support but give identical scores here. This is an analytic result,
not an inference from checking only seven policies.

Literal agreement can be changed by maintenance. It is not the same as
information usable by a calibrated decoder: the task permits free inversion,
and the saved two-calibration policy uses that option.

## 4. Prospective numerical witnesses

Evaluate the seven review policies under each original fixture: `frozen`,
`old_anchor`, `recent_anchor`, `maintain`, `reference`, `blind`, `frozen_audit`.
Compare each reconstructed utility and original state risk with the saved
review values before evaluating changed preferences.

The literal-agreement predictions needed for the main contrast are:

| Fixture | Frozen utility | Maintenance utility | Frozen literal agreement | Maintenance literal agreement |
|---|---:|---:|---:|---:|
| Main | 0.638 | 0.600 | 0.5 | 0.75 |
| Transfer isolated | 0.86875 | 0.850 | 9/16 | 1 |

The frozen-audit policy has the same reader agreement as frozen. The other
four unmaintained controls have agreement 1/2. In the isolated fixture, frozen
maintains on 1/8 of histories; symmetry gives agreement 1/2 on the remainder.

Write Delta as unconditional maintenance minus frozen. Since H(S)=H(W) is
policy-independent for these deterministic policies,

```text
Delta J_literal = beta*(U_frozen-U_maintain)
                  -lambda*(A_maintain-A_frozen)
main:             0.304 - 0.25*lambda
transfer isolated:0.150 - (7/16)*lambda.
```

Use lambda=0, lambda=2, and the analytic crossing for each fixture:
lambda*=152/125=1.216 in main; lambda*=12/35 in isolated. These are derived
crossings, not fitted thresholds. At lambda=2 the gaps must be -0.196 and
-0.725 respectively, although maintenance has lower original task utility.
For `content` and `oracle_decoded`, both gaps stay +0.304 and +0.150.

For the seven fixed policies, predict these complete minimum sets:

- At lambda=0, every preference family selects `frozen`.
- For `content` and `oracle_decoded`, every tested lambda selects `frozen`.
- For `literal`, lambda* ties `frozen` and `maintain`; lambda=2 selects `maintain`.

These are minima over the seven declared policies, not new global optima.
There are 14 physical policy distributions and 126 preference score cells
(two fixtures, seven policies, three families, three lambda values).

## 5. Coding control

Use the same trajectories with the reader bit relabeled Y2'=1-Y2 and the
observation/report interpretation carried along. Target, report and utility
are unchanged. Pushing the preferred joint through that bijection must
preserve each score exactly. The literal preference then rewards Y2'!=X2.

Reimposing Y2'=X2 instead of carrying the old preference is an explicit
preference change. At lambda=2 its maintenance-minus-frozen gaps must become
+0.804 and +1.025. This control distinguishes a coding convention from a
property of accessible information. It is not a failure of KL invariance or
a second physical experiment.

## 6. Interpretation and stopping rule

If the identities hold, the task marginal underdetermines hidden preferences.
Content validity is policy-invariant here; literal agreement adds an incentive
that can conflict with calibrated use of information. Oracle decodability
does not establish that a real agent knows the decoder. None is automatically
an additional intrinsic value implied by final success minus costs.

Use the original declared full objective for historical comparisons. Treat
content and reader diagnostics separately from extra reward unless a further
valued endpoint, future workload, decoding restriction or resource cost is
explicitly justified. A different endpoint is a different study, not a silent
repair of these results. Do not conclude that no hidden-state preference could
ever be justified, that counting measure is uniquely neutral, or that this
comparison establishes a new general theorem specific to FEP.

## 7. Lean verification and evidence record

Use one small standard-library checker and unchanged trajectory functions from
the review. Verify the source manifest and saved policy identities. Check
direct KL values against the tilt identity, normalization and every preferred
B cell, physical pointwise decoding, constant entropy, the analytic gaps,
all minimum sets including ties, and the relabeling control. Tolerance 1e-12.
No parameter search or new controller optimization follows the results.

Forecast under thirty seconds on one process, within the four-CPU ceiling.
If that forecast changes above ten minutes, detach with durable logs and no
automatic polling. Verify the output mount before writing. Freeze this
specification, checker, representation contract, imported sources and source
manifest/results before checking. Retain logs and every failure, and verify
hashes afterward. New data use only:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-hidden-preferences-v1/attempt-01/`.

The report and project notes stay in `fep-ideas/`. Earlier frozen studies and
manuscripts remain unchanged; sister projects remain read-only. No fresh
literature or sister search is required for these local derivations.
