# E048 — fixed half rollback after first rebuilding failure

User-authorized follow-up to E047 on 7 October 2026. Freeze inputs before tests
or new receiving trajectories. E047 full rollback rescued 55 cases and lost 36,
raising recovery from 174/301 to 193/301; its +6.31-point interval [0.68,12.50]
failed the required lower bound above five points. This test asks whether a
gentler change improves recovery while reducing those losses. It is a post hoc
intervention on existing cases, not fresh or serial policy qualification.

Use the same 32 E041 blocks 32000–32031, four founders and four descendants per
block. Derive first full-bridge-rewrite body failure independently from original
E041 scores; audit reconstructs scores from ports. Keep every onset at g1–g31:
301 eligible of 307 ever-failed lineages among 512. Six g32 onsets lack follow-up,
205 never fail. Cross-check E046 and E047. No later success, intervention outcome,
edit count or next injury selects cases. Keep zero-edit and empty-block cases.

The target is unchanged: currently physically available connections whose
incoming absolute value is >0.5 and outgoing absolute value is <=0.5. Incoming
g1 is consistent acquisition; later incoming is the previous outgoing packet.
Compare exactly three variants on all eligible cases:

1. Original outgoing packet, copied byte for byte.
2. Half rollback at every target: `new + 0.5 * (old - new)` in float64.
3. Full rollback at every target: copy the exact old value, rather than evaluate
   the interpolation at one and incur endpoint rounding.

Half is a fixed signed-value interpolation, not random selection of half the
edges or half an absolute-weight gain. An opposing sign can pass through zero;
finite precision may leave a tiny eligible change unchanged at half dose.
Report actual changed coordinates. Outside the target preserve exact outgoing
values, including current injury erasures and old-weak/zero new repairs. Do not
try other fractions, tune thresholds or substitute a better-performing dose.

Read the same next rebuilding body g+1, with the original next injury, full-size
birth/noise streams, normalized local-strength reader and two cues. Scientific
reading is 2,048 steps with 1,024 settling steps: multiply E041's saved base
settling count by four exactly once. Recompute local denominators after injury.
No new capture, holding write or later-generation propagation. E041 original
ports, margins and outcomes must match; E047 original/full packets, all returned
reader arrays and scores must reproduce byte exactly. Scientific controls must
retain 174 and 193 recoveries and the original full-rollback 55 rescues/36 losses.

Primary outcome is both cues correct in the next body, each signed output
margin strictly >0.25. Whole-block inference pools eligible-case numerators
and denominators across all 32 blocks, including empty blocks. Draw 10,000
whole-block samples using ('E048', 'bootstrap', 'partial_rollback'); report
two-sided percentile 95% intervals. Omit only bootstrap samples with zero total
denominator, reporting valid count; absent estimates are null. Original E047
intervals are not replaced by these new bootstrap draws.

Joint benefit requires **all three** frozen criteria:

1. Half minus original success: lower confidence bound >+0.05.
2. Half minus full success: lower confidence bound >0.
3. Reduction in original-success losses (full losses minus half losses): lower
   confidence bound >0, using **all 301 eligible cases** as denominator.

A loss means the unchanged next body succeeds under both cues and the altered
next body fails. This identifies a fixed outcome component for analysis; it
does not remove cases or choose edits. Report counts and rates separately from
overall success and rescues. Requiring criterion 3 prevents a net improvement
with more new failures from qualifying as the intended gentler intervention.
Status is HALF_ROLLBACK_JOINT_BENEFIT_ESTABLISHED only if all pass; otherwise
HALF_ROLLBACK_JOINT_BENEFIT_NOT_ESTABLISHED. Technical runs have null decisions.
Negative contrasts remain reportable. No global multiplicity guarantee is
claimed for secondary intervals.

Secondary reporting: all three pairwise success/individual-cue accuracy/margin
contrasts; paired rescues, losses, retained successes/failures; success by rule;
eligible and actual edited coordinates; sign changes, total absolute-weight
gain and L1 change; edits surviving next injury. Do not condition the primary
cohort on next-body success or surviving edits. Signed interpolation does not
isolate sign from magnitude; a positive result would concern this fixed dose,
selected existing cases and one response, not sustained recovery or deployment.

Retain incoming/outgoing/variant packets, addresses, availability/target/change
masks, edit counts, next-injury masks, effective packets, denominators, births,
end states, late-port traces, scores and worker receipts. Intermediate voltage
states and full noise draws are reproducible but not retained. The independent
auditor imports no production model/runner: reconstruct all edits coordinate by
coordinate, replay noise incrementally, compare all returned array bytes, verify
old controls, every numerical summary, transition count and primary requirement.
Source data and prior frozen inputs remain read-only. Figures require audit PASS.

Twelve checks use synthetic or excluded E041 fixture cases only: first/last and
missing onsets; strict cue scoring; target thresholds, torus injury and repair
preservation; signed interpolation/rounding; no-edit and exact endpoints; full
source noise streams; g1 acquisition and single timing conversion; mixed-generation
baseline replay; corruption detection; next-injury erasure/denominators; empty
cohorts/pooled ratios; loss accounting and three strict primary thresholds.
Fixture 900041 has R2, read24/settle12. Mixed-generation technical addresses are
(0,0,1), (1,1,2), (2,0,3), (3,1,5); they are not a scientific cohort. End-to-end
fixture and benchmark must also reproduce the saved E047 original/full controls.

Benchmark excluded E041 900041 R1, read128/settle64, against corresponding E047
benchmark. This R1 source has no E046 chronology; derive its onsets independently.
Forecast seconds = 3*(benchmark simulation-worker + independent audit-worker
seconds)*16 read factor*4 maximum case-count factor*ceil(32/workers)+120.
Storage reserve = ceil(1.5*benchmark run bytes*4*32)+128 MiB. Up to eight workers,
one numerical thread each, within the common 12-CPU limit. Forecasts >600 seconds
run detached with stdin /dev/null, unique log/PID and durable status. One bounded
startup check then await user polls; no automatic polling, restart or successor.
Preserve failures and version any amended inputs before further trajectories.
