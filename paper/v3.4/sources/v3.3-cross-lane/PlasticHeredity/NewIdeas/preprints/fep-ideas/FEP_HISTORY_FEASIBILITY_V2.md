# Observable-history feasibility v2 — bounded continuation

Prospective specification, 2 November 2026. The user's next “lets go” approves
continuing the exact search recommended in the [v1 report](FEP_HISTORY_FEASIBILITY_V1_REPORT.md).
V1 remains sealed at its declared sixteen pricing calls. This is a separate,
bounded computation using its fifty verified policies and exact interval.

## Unchanged scientific problem

Inherit the [v1 task, proofs and scope](FEP_HISTORY_FEASIBILITY_V1.md) unchanged:
T=10, reversal prior rho=1/2, conditional onset uniform over tasks 1–10,
sensor error marginal .05 and the same eighteen exposed persistence profiles.
An accurate target costs .1; an unaided mistake costs 1. A purchase reveals
orientation XOR error; F/R supply no target or realized-loss observation.
No profile, orientation, error state or other hidden information is supplied.
All feedback fees remain in stable, recovery and full-prior costs.

Keep K=19568652557/204800000000 and require S<=K, R<.1, R<R_hybrid in every
profile. The additional common-margin stable inequality and floor equivalence
proof stay unchanged. The hybrid is unchanged despite exceeding K in sixteen
profiles. All conditions are development conditions; no new validation,
arbitrary-profile guarantee, individual-onset guarantee or unique FEP claim
is introduced. This is a capability reference for FEP design, with constrained
task-cost actions and no imposed posterior or reliability state. The completed
false-confidence and reliability-freezing studies remain separate.

## Continuation and stopping rule

Start with all fifty v1 graphs, costs and their exact final variable order,
with full_floor last. Reconstruct costs from the sealed seed costs and sixteen
added-policy records; do not estimate them anew or change any graph. Reproduce
the exact final master and its optimum before starting new pricing. Retain
the v1 global upper bound and its independently verified pricing certificate.
The inherited interval is approximately [-.001548058421, +.001893063326].

Reuse the frozen v1 integer complete-history pricing routine, B,F,R ties,
exact Bland simplex (2,000 pivots), cost evaluator and independent audit
helpers without modification. Use 29,524 histories per full pricing call.
Each new master adds the preceding pricing graph to the same optimization
problem. Preserve the old variable order; append new policies immediately
before the floor. Continue policy names history_17 through at most history_48.
New iteration 0 corresponds to cumulative master 16.

Allow **at most 32 additional pricing calls**, at most 33 master certificates
and at most 82 policies in the final pool. The first master is the exact
reproduction saved during qualification, not another recomputation. Carry
forward the best upper bound and require lower bounds to be nondecreasing.
Stop early at a positive feasible-mixture margin or a nonpositive global
upper bound. A negative reduced-cost duplicate is an integrity failure.
At the cap, a remaining interval across zero is INCONCLUSIVE. Do not change
the cap, profiles, losses or criteria after seeing new outcomes. Do not claim
global optimality unless the exact bounds meet.

Save each new master, pricing value/action table, graph, physical costs and
bound. Keep S, R, full-prior B, J=B+R, errors, purchases and per-onset costs.
Compare the selected mixture with v1's selected history mixture, the targeted
full and separately optimized ablated mixtures, hybrid, always purchasing,
conservative controller and the frozen best fixed schedule. Retain adverse
timings and fee/error decompositions when interpreting the result. No belief
confidence or reliability-freezing score is invented for history policies.

## Qualification and independent verification

Freeze the new protocol and driver/auditor snapshots, imported local helpers
and predecessor records before qualification. Check the predecessor's complete
manifest, readback identity and source/snapshot hashes. The unchanged pricing,
physical and simplex algorithms inherit their successful v1 exhaustive short
qualification; do not repeat it merely to increase test counts.

Qualification focuses on the new continuation path: reconstruct all fifty
policy costs and the exact variable order, independently reconstruct the final
v1 matrix, solve it again and reproduce the entire saved master, validate its
primal/dual witness, and reject an altered witness. Independently replay the
best inherited global-bound pricing table and recompute its bound. Check the
initial interval, inherited qualification identity and next-name uniqueness.
These are exposed v1 outcomes, not new policy searches.

The new auditor imports the frozen independent v1 audit helpers, never the
new driver or planner. It checks immutable inheritance, reconstructs the
initial costs/order/matrix independently, audits every new pricing node and
graph, independently recomputes every new policy's physical costs, verifies
every master and global bound, and checks mixtures, fees, gates, final sign
and monotonic interval. Previously audited cost records are reused under
their manifest identities; report inherited and newly recomputed evidence
separately. Verify all new input, snapshot and output identities. Preserve
any failed attempt; do not amend frozen scientific files in place.

## Benchmark and resources

Benchmark T=7 pricing with u=v=1 on all eighteen profile prefixes, the
independent complete-tree audit, extracted-policy physical costs plus their
independent audit, and the fifty-seed short-horizon master. Freeze the forecast:
`360 + 2*32*27*(11/8)*(pricing_seconds+audit_seconds+cost_seconds)
 + 4*32*master_seconds`.
The larger fixed allowance covers inheritance checks, reporting costs and
certificate overhead. This is a conservative timing forecast, not a stopping
decision based on scientific outcomes. Keep the 7,200-second forecast ceiling.

Use one CPU at nice 10 by default, at most four; library threads one and
python -B. Forecasts over 600 seconds run detached with durable logs, exactly
one startup check and no automatic polling. All generated files use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-history-feasibility-v2/`.
Source and research notes stay in this folder. Close the report and six live
notes or an explicit detached checkpoint. Preserve v1 and all predecessors.
No further continuation, model integration, manuscript or sister write is
authorized by this bounded study.
