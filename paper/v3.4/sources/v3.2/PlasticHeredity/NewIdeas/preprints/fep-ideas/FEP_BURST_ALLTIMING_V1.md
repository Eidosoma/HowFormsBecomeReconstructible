# Reliability learning with every deployment onset in the objective

Prospective specification, 31 October 2026. The user's latest “lets go”
authorises the next lead proposed after FEP 1 and FEP 2: keep all reversal
timings in the planning loss, then test unfamiliar burst patterns. This is a
new study informed by the previous negative result. It does not replace,
repair in place or retrospectively validate the failed odd-onset candidate.

## Question and isolated design change

Can the same small reliability-learning model preserve stable costs and
recover economically when its planning objective includes every deployment
onset? Does reliability-state updating improve actions against its matched
ablation, and does any advantage survive new error-persistence patterns?

Keep the FEP 2 generative model, observation interface, posterior updates,
action tie order, candidate penalties and mixture-selection class unchanged.
Change the training loss from B_odd+R_odd to the original full-prior B+R.
The old odd-onset policy remains a frozen comparison. This contrasts the
complete selection pipelines under two losses; changes in actions and
mixture weights are allowed consequences of the loss change.

The horizon is ten tasks, reversal probability 1/2 and reversal onset uniform
over all ten tasks. A purchased accurate target costs .1; an unaided error
costs 1. Unpurchased targets/losses are hidden. Stable budget
K=19568652557/204800000000. Purchased discrepancy is orientation XOR error.
The controller never receives true orientation, true error or persistence for
free. Its internal persistence class is a in {0,3/4}, with equal prior weights,
and its current error bit has stationary prior probability p=1/20.

The posterior represents reversal onset, current error and persistence
jointly. The base error marginal is supplied, not learned. Transitions occur
even on unbought tasks. Bayesian/VFE inference is the FEP-related mechanism;
the action target remains constrained task cost, not a new canonical EFE.

## Training and frozen candidate selection

Use physical persistence a=0 and a=3/4 for training. Both were already studied;
neither is a holdout. For every policy evaluate the stable world and all ten
onsets, including every purchase fee. Let C be the mean of B+R over these two
settings, enforcing S<=K separately at both. No onset is absent from the loss.

Keep mu={0,1,2,4,8,16}. Each exact full-horizon planner minimizes
`C + mu*mean(S)` under the same supplied generative model. The per-task
utility multiplier for static onset tau and task t is:

```text
1/T
+ 1[0 < tau <= t] / (rho * (T-tau+1))
+ mu * 1[tau=infinity] / ((1-rho)*T).
```

All onsets receive the first term. The second produces R under the original
uniform-onset prior. Utility multipliers never change the Bayesian posterior.
An onset represented as zero in code denotes infinity, not a task-zero reversal.
Ties remain B,F,R. Keep the 250,000-state ceiling for each Bellman cache.

Add the always-follow/no-purchase floor to the six planning candidates. Select
the exact minimum-C episode mixture from this seven-policy pool subject to the
two stable constraints. Enumerate all vertices with support at most three;
tie order is C, component count, sorted component names, exact weights. Save
every candidate, training metric, feasible vertex and compressed Bellman table.
Do not claim global optimality beyond this declared pool.

## Controls and reliability intervention

Retain the earlier independence-assuming reserve mixtures, five graphs, hybrid
and always-purchase control. Preserve both failed FEP 2 selected mixtures,
with their original component weights, as `previous_reliability` and
`previous_frozen_reliability`. Evaluate these graphs without refitting.

Retain the conservative rule: buy on tasks 2,4,6,8,10; otherwise follow the
current direction, initially F; change direction after two successive
purchased discrepancies supporting its opposite. Supporting the current
direction resets the counter. No posterior is invented for this rule.

Select the best fixed schedule from all 1,024 schedules using the new full
training objective and both stable constraints. Retain the same joint filter
and posterior-MAP unaided response, with F on ties and smallest schedule mask
breaking selection ties. “Best” refers only to this schedule/MAP class. The
previously selected schedule is not relabelled as newly optimal.

For each mu construct the paired reliability-freezing planner. After observed
or imagined purchases preserve the updated onset marginal but reset the
conditional persistence/error state to uniform class weights and Bernoulli(.05),
removing learned dependence. Keep orientation learning and observation access.
Use the full agent's selected component weights, without ablation retuning.
This is an intervention on reliability updating and its planned information
use, not an independently optimized ablated policy class or identical-observation
comparison. Physical streams match in distribution, but purchased subsets can
differ. Report both agents' stable constraints explicitly.

Audit ordinary Bayesian planning with exactly the same model, objective,
observations and costs using an independent normalized Bellman calculation.
Require matching values/actions and exact ties. Agreement is legitimate.

## Held-out burst patterns and freeze order

Freeze all selected graphs, mixture weights, schedules and training evidence
before computing the eight new physical profiles below. Each profile specifies
the nine transition persistences a_t for z_t -> z_(t+1). Begin z_1~Bernoulli(.05)
and use P(z_next=1|z)=.05*(1-a_t)+a_t*z. Every transition preserves the same
stationary marginal, so P(z_t=1)=.05 at every task even as persistence changes.
Profiles are fixed externally, independent of orientation and actions, and
are not revealed to the controller.

| Profile | Transition persistences, t=1,...,9 |
| --- | --- |
| constant_20 | .2 repeated nine times |
| constant_40 | .4 repeated nine times |
| constant_60 | .6 repeated nine times |
| constant_80 | .8 repeated nine times |
| alternating_low | 0,.9,0,.9,0,.9,0,.9,0 |
| alternating_high | .9,0,.9,0,.9,0,.9,0,.9 |
| onset_after_5 | 0,0,0,0,.9,.9,.9,.9,.9 |
| offset_after_5 | .9,.9,.9,.9,0,0,0,0,0 |

The four constants are new durations relative to FEP 1/FEP 2. The four varying
profiles are new temporal patterns; their component values are not themselves
claimed to be previously unseen. Constant means need not describe a varying
profile's run-length law. The model still assumes a fixed class within an
episode: the varying profiles deliberately test that assumption. The original
orientation prior and all ten onsets stay in both training and evaluation.
Odd/even onset summaries are descriptive diagnostics, not a timing holdout.

Also score the frozen policies at both training settings as labelled
diagnostics. No held-out score may select penalties, weights, thresholds or
schedules. Keep failed gates and every onset. No interval or arbitrary-profile
guarantee follows from these ten exact settings; the old independence-based
interpolation proof does not cover this study.

## Outcomes and qualification

Each of the eight held-out profiles must satisfy S<=K, R<.1 and R<R_hybrid.
Report the three gates separately and their joint result. Keep B, B+R, full
fees and onset-specific costs visible. Compare every simple/previous control
on those quantities, retaining all signs and ties. For the reliability
intervention report lower R and lower B+R per profile, together with both
stable budgets. A mixed or negative outcome remains such.

Retain FEP 1/FEP 2 wrong-confidence frequency, orientation Brier, repeated
wrong-message updates, stable/pre/post-reversal purchase counts, acquisition
delay and missing feedback, confident-adoption delay/missing adoption and
literal first-inversion delay. Distinguish purchase, interpretation and
economic failures. Stable purchases are not automatically unnecessary. Do not
equate confidence, latent orientation or first inversion with useful recovery.

Freeze specification, code, verifier and imported dependencies before
qualification. Recheck exact full/ablated Bellman roots against all contingent
trees through T=3 under the new loss; require positive loss weight for every
onset. Check coefficient identities, stationary propagation and posterior
projection. Cross-check variable-persistence path enumeration against an
independent augmented-state flow on every short tree and onset; confirm
constant-profile reduction and fixed marginals. Preserve failed attempts.

Independently verify all saved Bellman states/actions, all schedules, exact
finite-pool selection, inherited graph identities, freeze chronology and all
physical/diagnostic outcomes. The independent auditor imports no new planner
or evaluator. Reuse verified frozen IO/filter helpers without editing them.

Benchmark a full and an ablated T=7,mu=4 planner and all T=5 fixed schedules.
Forecast the workflow as
`240 + 4*6*3^3*(11/8)*oracle_seconds + 4*(1024/32)*(11/6)*schedule_seconds`.
The higher fixed allowance covers additional profiles and prior-policy
diagnostics. Retain the two-hour forecast ceiling. At most four CPUs; default
one CPU at nice 10, library threads one, no bytecode. Forecasts over 600 seconds
run detached, with durable logs, one startup check and no automatic polling.

All generated data, snapshots and logs belong under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-alltiming-v1/`. Source and small
research notes stay in this folder. Close the report and six live notes, or
record an explicit detached checkpoint. No further study, policy retuning on
these tests, larger-model integration, manuscript or sister-project write is
authorised by this successor.
