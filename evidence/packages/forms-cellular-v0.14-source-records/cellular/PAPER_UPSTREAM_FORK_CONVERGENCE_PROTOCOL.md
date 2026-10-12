# P29: regenerate the upstream fork and test downstream convergence

Registered October 4, 2026, following the user's authorization to continue
the P28 repair. Registration and software verification precede scientific
integration. All executed P27/P28 artifacts and acceptance rules stay frozen.

## Question and source trace

P28 converged at fixed archived sources, but its immediate-five and
start-ten/duration-100 schedules remained source sensitive under both
histories. Final retention agreed. The all-before checkpoint used downstream
is P17's `replacement_01` endpoint at logical time 1180100. P19 carries that
endpoint into the initial sample of `preparation_extra`; P20 takes its before
state and reanchors it to 1180300 without integration. P21/P27 apply one
native algebraic binding refresh, without changing primary concentrations.
No part of P19's 200-unit preparation is used in that all-before state.

P17 constructs its first replacement from the matching P15 founder's final
isolated trio at 1180000 and P11 M stock, with the unchanged legacy event-zero
ZEB-protein perturbation. Coarse/fine initial primary-state differences have
maximum normalized size about 0.00000334; archived fork differences are
larger. This source inspection suggests testing the short P17 integration
before rebuilding the much longer ancestral history. It is not a simulation
result or proof that ancestral uncertainty is negligible.

## Fixed design

Keep both written and ordinary histories and both matched archived input
bundles (P15 founder plus P11 stock). Retain their complete arrays and original
cell identities. Regenerate the 100-unit P17 first replacement at solver
divisors 1, 2, 4, 8, 16, giving 20 prefix cases. Use native equations and
legacy event-zero draw, shape 1 by 3, open communication, power 60 and RNA
transport coefficient 1.25e-14. The founder-to-prefix state construction must
be independently reconstructed from raw founder and stock files.

Reanchor each selected actual prefix endpoint from 1180100 to 1180300 without
integration, preserving the inherited counterfactual assembly convention.
Apply one native noniterative binding refresh to all columns. Save both raw
and refreshed states; no primary-variable editing, averaging, relaxation or
outcome-dependent preparation is permitted.

For the downstream challenge, preserve all 26 P28 phases, its segmentation,
five replacements, both isolated holds, incoming sequence 17021 and native
E/M/X classifier. Four schedules: baseline, immediate-five, immediate-25 and
start-ten/duration-100. Preserve P27 counterfactual cell IDs and the original
five incoming protein draws. These numerical comparisons are not independent
biological replicates. No onward-transmission assay is included.

There are 16 downstream replay cases using each source bundle's original
prefix divisor (1 for coarse, 2 for fine) and downstream divisor 16. All
numerical arrays and reconstructed outcomes must exactly match P28.

There are 80 refined downstream cases: for every history, input bundle and
schedule, use the fixed `(prefix divisor, downstream divisor)` combinations
`(4,16), (8,16), (16,4), (16,8), (16,16)`. This measures each refinement axis
at the finest setting of the other. It is not a full factorial over both
numerical ladders, and does not estimate every possible interaction.

Total **116 cases / 2,516 integrations**: 20 prefix integrations plus
96 downstream cases with 26 phases each. Every registered case runs unless
a technical audit, execution, resource or watchdog requirement fails.
Unfavorable convergence does not select a new case or trigger an automatic retry.

At divisor q, set native `time_step=0.0001/q`, concentration adaptive limit
`0.001/q`, voltage adaptive limit `0.0001/q`, and phase maximum step
`min(100,horizon/100)/q`. Keep sampling `min(100,horizon/20)` independent of q.
Use the original explicit Euler update, native adaptive proposal and integer
tick clipping. Prefix samples are 0,5,...,100. Downstream common diagnostics
remain at 0,15,...,300. Numerical settings are independent of archived source
precision and, downstream, of prefix refinement.

## Stages and technical gates

1. `prefix_replay`: four original-settings prefix cases. Replay all 33 P17
   raw arrays and reconstructed outcomes exactly. Cumulative 4 cases / 4 integrations.
2. `prefix_refine`: remaining 16 prefix combinations. Cumulative 20 / 20.
3. `replay`: 16 downstream P28 replays from the newly rebuilt original-setting
   prefixes. Cumulative 36 / 436.
4. `refinement`: 80 downstream refined cases. Cumulative 116 / 2,516.

Independently audit native numerical controls, clocks, observations, bath,
geometry, gates, routing, cell identities, exact survivors, incoming draws,
source provenance and registered file inventory. Verify all 48 baseline/
immediate-25 control anchors against P28 at matching source precision for
retention, sampled behavior, first-cell stability and complete replacement.
Require all 48 pairs sharing an initial downstream communication schedule
to have exactly matching raw arrays until their routes diverge.

Verify complete source/input manifests and pinned P28 terminal evidence,
including its unresolved source gate. P28 is a valid diagnostic predecessor,
not a qualified repair. Retain the original P27 failure. No historical full
mathematical audit is rerun.

## Predeclared convergence and interpretation

Report all 16 adjacent prefix comparisons. For each of four fixed-source
prefix groups, require the fixed finest pair 8/16 to have the same phase
inventory, reconstructed outcomes, phase-end labels and every sampled cell
label. Maximum normalized error across primary rows 0–7 and 16, every saved
sample and cell, is `abs(x-y)/max(1,abs(x),abs(y))`, maximized over the data.
Require error at most 0.01 and no larger than the 4/8 error plus 1e-12.

For each of 16 history/source/schedule groups, separately require upstream
8/16 agreement at downstream divisor 16 and downstream 8/16 agreement at
prefix divisor 16. Each axis uses its own 4/8 comparison for contraction.
Require matching phase inventory, complete reconstructed outcomes, every
phase-end cell label, and complete common-grid first-challenge diagnostic,
including loss and return brackets, with the same error and contraction rules.
This gives 16 finest upstream and 16 finest downstream comparisons, in
addition to the four prefix comparisons. Do not choose an earlier passing
pair, extend the ladder, change sampling or relax thresholds after results.

Separately compare coarse/fine input bundles at prefix divisor 16 (two pairs)
and after the full challenge with both divisors 16 (eight pairs). Require
matching inventories, outcomes, endpoint labels and diagnostics, and normalized
error at most 0.01. Prefix diagnostics mean all sampled cell labels. Bundle
comparisons do not isolate founder versus stock sensitivity individually.

A technically valid negative convergence result is saved and interpreted.
Support for a separately reviewed refined full-panel experiment requires
all technical checks, all 36 finest numerical comparisons, and all ten input
bundle comparisons to pass. Even a favorable result is finite-ladder evidence
for this targeted checkpoint and sequence, not exact-solution convergence of
the entire historical lineage, a timing threshold or onward transmission.
No larger panel is launched automatically, and P27 is never relabeled a pass.

## Software and resources

New execution source is confined to `p29_upstream_fork_convergence/` and
this protocol: **274 execution sources / 33,880 registered input paths**.
Previous scientific code, parameters, draws, outputs and
legacy inventory remain unchanged. Freeze all execution sources before the
detached supervisor repeats all **34 software tests**. The suite exercises
the complete synthetic panel, both replay stages and deliberate state,
clock, routing, identity, timing, provenance and convergence failures.
Synthetic trajectories test software; they are not scientific results.

All large outputs, fixtures, caches and logs remain beneath
`/mnt/workspaces/levin-cancer-gj-exploration/p29-upstream-fork-convergence`.
Use two workers, one numerical-library thread each, exclusive experiment
lock and at least five GiB on the actual output filesystem. Watchdogs:
software two hours, case six hours, runner forty hours, final audit six hours,
overall forty-eight hours. Long work is detached with durable logs,
heartbeat, completion status and no automatic retry.
