# Observable-history feasibility reference for the FEP track

Prospective specification, 1 November 2026. The user's next “lets go” approves
the capability check proposed after the targeted reliability study. Preserve
all previous results. This is one bounded study, not another model expansion.

## Question and fixed task

Can any policy using the existing purchased-feedback interface meet the
original stable-budget and recovery requirements on all eighteen exposed
burst profiles? The ten development profiles and eight former transfer
profiles in `fep-burst-targeted-v1/attempt-01/MODEL.json` are now development
conditions. No fresh validation or continuous-profile guarantee is claimed.

Keep T=10, reversal prior rho=1/2, conditional onset uniform over tasks 1–10,
error marginal .05, accurate current-target purchase cost .1, unaided error
cost 1 and K=19568652557/204800000000. For each profile, error persistence a[t]
gives P(z[t+1]=1|z[t])=.05*(1-a[t])+a[t]*z[t], with initial Bernoulli(.05).
The orientation is initially normal and reverses at the sampled onset, or
never reverses. Profiles, orientation, errors and unpurchased targets/losses
are hidden. A purchase reveals discrepancy d=orientation XOR error. Unaided
following F or reversing R supplies no observation, denoted N. Actions do not
change the latent dynamics. The raw symmetric message supplies no additional
state information in this abstract interface; private randomness is allowed.

S is mean stable cost per task. R is the mean of post-reversal cost per
remaining task, averaging the ten onsets uniformly. B is full-episode cost
per task under the unchanged reversal prior; retain B, J=B+R, error counts,
purchase counts/fees and onset-specific costs. Primary requirements remain
S<=K, R<.1 and R<R_hybrid in every profile. Always purchasing and the frozen
hybrid retain all costs. No hidden evidence or free feedback is introduced.

## Complete policy class and pricing calculation

A deterministic policy chooses B,F,R at every history over {N,0,1}. Its
previous F/R choices can be reconstructed from that history and its own
policy. Every randomized finite policy is a distribution over deterministic
contingent policies after sampling its private randomness at episode start.
Thus linear expected-cost bounds for all deterministic policies also bound
all randomized policies with this interface.

The full tree has (3^10-1)/2=29,524 decision histories, indexed breadth first:
children of i are 3*i+1 (N), 3*i+2 (0), 3*i+3 (1). Minimize arbitrary
nonnegative rational scalar loss C=sum_k(u[k]*S[k]+v[k]*R[k]) exactly.
For stable physical world k use loss weight u[k]/T; for reversal tau use
v[k]/(T*(T-tau+1)), active only from tau onward. Observations and transitions
before tau still matter. These are loss weights, not calibrated beliefs.

Let L clear the loss-weight denominators; let D clear all transition
denominators (D=400 suffices for the declared full roster). Initial weighted
error masses are (19*c,c), c=L*weight. Propagate integer masses through the
full history tree. At task t lift immediate cost by D^(T-t); measure cost in
tenths. F/R add ten times the respective wrong mass; B adds the active total
mass. F/R share the N continuation; B sums its two observed continuations.
Minimize in B,F,R tie order. Divide the root integer by 200*L*D^(T-1).
Backward induction proves this scalar minimum over the complete policy class.
Save every value/action and a reachable policy graph. No belief or confidence
semantics are assigned to these loss-weighted masses.

## Restricted master and global certificate

Seed with all 34 frozen graphs from the targeted study, including both full
and ablated families and all simple/fixed controls. Keep named duplicates.
Order all non-floor names lexicographically, with `full_floor` last. Solve
the exact mixture program with hard S<=K and common margin delta:
S+delta<=K, R+delta<=.1, R+delta<=R_hybrid. Eliminate the floor weight and
shift delta by +1, using the frozen exact Bland simplex and 2,000-pivot limit.
The floor has S=.05<K and R=.95 everywhere. If the original inequalities
are feasible, a sufficiently small floor perturbation makes stable cost
strict while preserving both strict recovery inequalities. Hence the
original requirements are feasible iff some common margin is positive.

For master dual weights h,s,a,b on hard budget, margin budget, always and
hybrid recovery, respectively, set u=h+s, v=a+b and W=sum(s+a+b)>=1.
If V is the complete-tree minimum of C, a global upper bound is
U=(sum_k((h+s)*K+a*.1+b*R_hybrid)-V)/W. For every feasible policy,
C+W*delta is at most that weighted limit, while C>=V. This bounds policies
outside the current master, including arbitrary private randomization.

Save exact primal/dual witnesses, physical costs, pricing tables and bounds
at every iteration. A positive restricted-master margin proves FEASIBLE
with an explicit implementable mixture; U<=0 proves INFEASIBLE within the
declared interface/domain. Otherwise add the pricing graph and repeat.
The pricing reduced cost is y_normalization+V-C_floor. Nonnegative reduced
cost certifies master optimality; a negative duplicate is an integrity error.
Retain the best bound; the initial trivial upper bound is .1 since R>=0.
Stop on a decisive sign or after 16 pricing calls. At the cap report the
exact remaining interval as INCONCLUSIVE, not an impossibility result.
Do not tune the cap, profiles, criteria or seed pool after seeing outcomes.

## Qualification and independent verification

Freeze new protocol/source snapshots, imported local helpers and predecessor
input identities before qualification. Independently check physical cost
evaluation, stationary error marginals and full-tree Bellman optima against
every contingent tree through T=3, using diverse stable/recovery weights,
multiple profiles and zero/tied loss cases. Check exact LP certificates on
positive/zero/negative fixtures and reject corrupted witnesses. Reproduce
source graph identities; truncate graphs only for short qualification and
timing, without changing full-horizon candidates.

The independent verifier must not import the new planner. It propagates
one unweighted physical world at a time over the full tree, accumulates
integer immediate costs, then independently checks every backward minimum,
chosen action, root scale and extracted graph. Audit each candidate's costs
with the frozen independent rational backward evaluator. Reconstruct every
master matrix, certify primal/dual equality and verify the global-bound
algebra, graph additions, all mixtures, fees, gates and final sign. Hash
checks cover inputs, snapshots and outputs. A failure remains a failed attempt.

## FEP interpretation and bounded execution

This is an information-limited reference for FEP design: it distinguishes
limitations of our supplied models/policy pools from limitations of the
observation and cost setup. It is not a new FEP posterior or canonical EFE
controller. The action target is constrained task cost. Ordinary Bayesian
decision theory can implement the same finite history policies; uniqueness
to FEP is neither required nor claimed. Existing false-confidence and
reliability-freezing results remain separate. A policy without an imposed
belief model has no defined orientation confidence or reliability state;
do not invent either metric or an ablation for this reference.

Benchmark T=7 pricing with positive u=v=1 on all eighteen profile prefixes,
its independent full-tree audit, physical cost plus independent cost audit
for the extracted graph, and the 34-seed short-horizon master. Forecast:
`180 + 2*16*27*(11/8)*(pricing_seconds+audit_seconds+cost_seconds)
 + 4*16*master_seconds`. The factors conservatively allow history growth,
more onset worlds, increasing master size and verification. Save short-run
timings only as benchmark evidence; they are not full-horizon results.

Use the 7,200-second forecast ceiling. Default one CPU at nice 10, at most
four, library threads one and python -B. Forecasts over 600 seconds detach
with durable logs, exactly one startup check and no automatic polling.
All generated data use `/mnt/bioIce1/fep-ideas/formal-checks/fep-history-feasibility-v1/`.
Source and research notes stay here. Close the report and six live notes,
or a detached checkpoint. Preserve all predecessors and failed attempts.
No later successor, model integration, manuscript or sister write is queued.
