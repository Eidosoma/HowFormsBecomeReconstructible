# Preserving a reader without acquiring information

**18 September 2026.** Analytic specification written before its finite
verification. The user's "lets go" authorizes this bounded follow-up to the
[two-report bridge](FEP_TWO_REPORT_FORMULATION_BRIDGE_V1_REPORT.md). Manuscript
integration belongs to another agent and is not part of this task. Preserve
this specification and its checker once the run manifest records their hashes.

## 1. Question and scope

Can a specified active-inference objective pay to preserve the usefulness of
an existing record when the maintenance action supplies **no information**?
When does it agree with a Bayesian task planner, and which assumption explains
any disagreement?

Use a physical readout failure, rather than simulate forgetting while secretly
retaining an intact history in the planner. The record and the controller's
knowledge of its content stay intact. Every report must pass through one
fallible reader; knowing the right answer cannot bypass that channel.
Maintenance changes its reliability, without supplying any observations.

This is an objective comparison on a supplied mechanism. It is not a new
generic repair apparatus, an L20 reconstruction study, or evidence that an
agent discovers how to maintain its own machinery. The physical efficacy of
maintenance and the single-channel restriction are explicit assumptions.

## 2. Physical model, access and policies

Condition on a previously acquired, known bit `m`, stored without alteration.
Both `m=0` and `m=1` must give identical scores. A complete episode is:

1. Choose `a` in `{0,1}`: skip or maintain, at price `c*a`.
2. The reader experiences an unobserved flip `F`. Its probability of staying
   aligned is `P(F=0 | a)=rho_a`, where `1/2 <= rho_0 <= rho_1 <= 1`.
3. Choose a report preparation `b` in `{0,1}`: send the stored bit unchanged
   or inverted. There are no intervening observations, so `b` can depend only
   on the known content, chosen action and fixed model, never on `F`.
4. The physical report is `d = m XOR b XOR F`. External success is
   `g = 1[d=m] = 1[F=b]`. No report, fault or success feedback reaches the
   controller before the episode ends.

All outputs, including an attempted direct answer from memory, cross the same
reader. There is no second output path, inspection of `F`, free audit, repeated
attempt or surviving side channel. At each known `m`, the four deterministic
policies are exactly `(a,b)`. Evaluating every pair therefore covers every
admissible deterministic continuation. We do not optimize distributions over
policies or count randomness in the controller's own choices as new evidence.

The external endpoint is `U = E[v*g-c*a]`, with task value `v >= 0`.
The negative control `v=0` represents no remaining rewarded use of the record.
Costs use the same task-value units. For a policy `(a,b)`, write

```text
p_ab = rho_a if b=0, otherwise 1-rho_a
U_ab = v*p_ab-c*a.
```

For positive `v`, each objective that retains success preferences prefers
`b=0` at a given `a` when `rho_a>1/2`; both preparations tie at `rho_a=1/2`.
At `v=0` they tie. The outcome-only score ignores success, so both preparations
tie regardless of reliability. Always-maintain and never-maintain baselines
use `b=0`; both baselines are included among the enumerated policies.

## 3. Fixed preferred joint and compared objectives

Use the common eight-state alphabet `S=(g,a,b)`. Given known `m`, this is a
one-to-one relabeling of the complete future uncertain state `(F,a,b)`.
No changing physical state has been hidden solely to force constant entropy.
The only available outcome is the pair of known actions `O=(a,b)`, with
deterministic likelihood `L(O|S)`. For each fixed policy, `H(O)=0`, ambiguity
is zero, and `I_Q(S;O)=0`. Maintenance provides no epistemic gain, including
over the full episode under this observation contract.

For fixed `beta>0`, define normalized preferences on the full common alphabet:

```text
C_G(g) = exp(beta*v*g) / (1+exp(beta*v))
C_A(a) = exp(-beta*c*a) / (1+exp(-beta*c))
C_B(b) = 1/2
C_S(g,a,b) = C_G(g)*C_A(a)*C_B(b)
P_C(S,O) = C_S(S)*L(O|S)
C_O(a,b) = C_A(a)*C_B(b).

K = log(1+exp(beta*v)) + log(1+exp(-beta*c)) + log(2).
```

The success preference concerns latent physical success, not an observed
reward signal. Its normalization, action cost and neutral preparation prior
are shared across policies. They are not refitted to favor the useful action.

Minimize the following five scores, using the same physical predictions:

```text
J_Bayes  = -U
J_state  = KL(Q(S) || C_S)                # state risk; zero ambiguity
D        = E_Q(O) KL(Q(S|O) || P_C(S|O))
J_exact  = KL(Q(O) || C_O) + D = J_state
J_drop   = KL(Q(O) || C_O)                # conditional KL omitted
J_latent = E_Q[-log C_S(S)] - I_Q(S;O)    # declared extension
```

The state/outcome decomposition follows the already reviewed formulation in
[the local audit](FEP_FORMULATION_AUDIT_2026-09-18.md), which records the
primary sources. This application and the derivation below are ours.
`J_latent` retains the previously declared extension's identity; it is not
silently substituted for the state-preference objective. These are finite
future-state functionals, not an implementation of a published temporal agent.
There is no belief-updating or variational-inference optimization in this task.

## 4. Derivation before numerical verification

Let `h(p)=-p*log(p)-(1-p)*log(1-p)`, with `0*log(0)=0`. Direct evaluation gives

```text
H_Q(S) = h(p_ab) = h(rho_a)
J_state = J_exact = K-beta*U_ab-h(rho_a)
J_latent = K-beta*U_ab
J_drop = log(1+exp(-beta*c)) + log(2) + beta*c*a
D = KL(Bernoulli(p_ab) || C_G).
```

Thus the latent extension ranks policies exactly by task utility here because
its information term is zero. State risk has an additional entropy term.
The bridge's exact state-risk/Bayesian agreement required fixed state entropy;
that premise no longer holds when maintenance changes failure probability.
The decomposition itself remains exact.

For unchanged preparation `b=0`, set `delta=rho_1-rho_0` and
`L=h(rho_0)-h(rho_1) >= 0`. Maintenance minus skipping gives

| Quantity | Difference |
|---|---|
| External utility | `v*delta-c` |
| Bayesian score | `c-v*delta` |
| State risk and exact decomposition | `beta*(c-v*delta)+L` |
| Latent extension | `beta*(c-v*delta)` |
| Outcome-only score | `beta*c` |
| Conditional KL | `-beta*v*delta+L` |

Consequently, including all report preparations and all ties:

- Bayesian utility and the latent extension maintain when `c < v*delta`.
- State risk and its exact decomposition maintain when
  `c < v*delta-L/beta`.
- The outcome-only score skips for every `c>0`; both actions tie at `c=0`.
- At each threshold, both maintenance choices tie; retain all optimal report
  preparations using the rules in section 2. Use lexicographic `(a,b)` only
  to name a representative, and report the full utility range among ties.

For a strict reliability improvement above chance, `L>0`. The interval
`v*delta-L/beta < c < v*delta`, intersected with nonnegative prices, therefore
gives a strict disagreement: preservation benefits the task, but state risk
rejects it. This does not depend on a favorable tie rule. At fixed positive
`v` and away from the task threshold, state risk approaches the task decision
as `beta` increases without bound.

In the main case `beta=4`, `v=1`, `rho_0=1/2`, `rho_1=1`, the task threshold is
`1/2`, while the state threshold is `1/2-log(2)/4`, approximately `0.326713`.
At price `0.1`, state risk and Bayesian planning both preserve the reader;
utility is `0.9` versus `0.5` for skipping. At price `0.4`, Bayesian planning
and the latent extension preserve it with utility `0.6`, while state risk and
the outcome-only score skip with utility `0.5`.

This is a consequence of a stated finite, soft preference distribution and
changing forecast entropy. State risk compares distributions, not just their
expected success. Calling the extra entropy term an approximation error would
be incorrect. It is already present in the full declared state objective.

## 5. Bounded arithmetic fixtures and falsifying checks

Fix the following eleven settings before implementation and execution. These
illustrate the derived regimes; they are not sampled observations or a search
for a favorable effect. All costs are nonnegative.

| Fixture | beta | v | rho_0 | rho_1 | c |
|---|---:|---:|---:|---:|---:|
| Useful cheap preservation | 4 | 1 | 0.5 | 1 | 0.1 |
| Useful preservation rejected by state risk | 4 | 1 | 0.5 | 1 | 0.4 |
| Excessive cost | 4 | 1 | 0.5 | 1 | 0.6 |
| State threshold | 4 | 1 | 0.5 | 1 | `0.5-log(2)/4` |
| Task threshold | 4 | 1 | 0.5 | 1 | 0.5 |
| No reader damage | 4 | 1 | 1 | 1 | 0.1 |
| Ineffective maintenance | 4 | 1 | 0.5 | 0.5 | 0.1 |
| No remaining task value | 4 | 0 | 0.5 | 1 | 0.1 |
| Interior reliability disagreement | 4 | 1 | 0.75 | 0.95 | 0.15 |
| Stronger success preference | 16 | 1 | 0.5 | 1 | 0.4 |
| Weak preference, free maintenance | 1 | 1 | 0.5 | 1 | 0 |

Enumerate every policy in every fixture. Calculate the distributions and
scores directly from the physical flip/report process, independently of the
closed forms used for comparison. Check normalization, absence of a bypass,
content-bit symmetry, zero information gain, entropy, utility, preference
cross entropy, the conditional KL identity, all five score differences and
the complete optimum sets. Verify the state KL under the one-to-one change
from success to fault coordinates with the preferred joint transformed too.
This does not claim invariance to adding hidden states or changing preferences.

Treat any analytic mismatch as a failed check, retain the failed inputs and
log, and explain any correction before a fresh attempt. Do not change fixtures
after seeing their calculated outcomes. Use absolute tolerance `1e-12`.
The expected workload is 44 policy distributions and 220 objective scores,
plus content-symmetry checks, on one standard-library Python process. Forecast
runtime is under ten seconds and data below 100 KB; no detached job is needed.

Write the source and research notes only in `fep-ideas/`. Verify that the
external drive is mounted, then write results, logs and source/output hashes
under `/mnt/bioIce1/fep-ideas/formal-checks/fep-reader-preservation-v1/attempt-01/`.
Never overwrite an attempt or fall back to workspace data storage. Preserve
the earlier studies and all manuscript versions. No successor campaign is
automatically authorized by this finite check.

## 6. What a completed check would establish

A positive low-cost case would establish that this specified state-preference
objective can select physical preservation with zero information acquisition.
A verified disagreement would establish the boundary of that result and
identify the variable-entropy term that breaks the bridge's earlier utility
equivalence. Neither result would show a unique advantage over Bayesian
planning, autonomous discovery of maintenance, or biological self-preservation.
The primary endpoint stays fixed even when the internal score prefers another
policy. The original pivot's broader ambition remains open.
