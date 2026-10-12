# Commitment-window protocol (v1; fixed before new integrations)

## Question and scope

At which of a fixed set of stopping points does a short-contact train leave
receivers able to retain the target regulatory state without cues and pass it
through two complete fresh-pair replacements? This maps sampled commitment
points, not an exact separatrix, universal threshold, monotone dose-response law,
new attractor, or wet-lab discovery.

The completed history crossover distinguishes a transient M-labelled state after
five contacts from a durable E return at that same point. Ten contacts succeed
in both directions. The earlier E observation after gap four is not necessarily
the same as the endpoint of contact four. This panel removes cues at CONTACT
endpoints, before any subsequent gap.

Native BITSEY equations, parameters, classification and onward relay are
unchanged. No PH force, reference overwrite, extra cue, adaptive rescue, or
outcome-dependent checkpoint selection is introduced.

## Fixed panel and historical inputs

Exactly 30 new branches: E→M→E and M→E→M, stopping after N = 2, 3, 4, 6 or 8
contacts, each with baseline active history, baseline all-transport-blocked
history, and fine active history. Counts are fixed before inspecting the new
hold/relay outcomes. No additional counts are launched within this protocol.

Reuse full canonical `final` 17×6 checkpoints from the completed spacing run
`runs/pulse-spacing-20260906T130210Z-8pyjjxct`, specifically
`<direction>_train_g0010_<pulse|blocked>[_fine]/exposure/carrier_i_pulse_NN.npz`.
The source is always the exact earlier round-three descendant pair (nominal
89000), not descendants produced by the crossover's onward relays.

Each prefix has N contacts of nominal length 10 and N−1 all-transport-off gaps
of length 10. The same five cue cells per receiver evolve throughout the prefix,
without refresh or clamping. A blocked history has all gap-junction transport
off throughout, but intracellular regulation and elapsed time continue. Thus
controls are age matched at each N, not untreated newborn cells.

Five-contact baseline R1C1 active outcomes from
`runs/history-crossover-20260906T144633Z-gkc7ryjt` and ten-contact baseline/fine
active and baseline blocked outcomes from the spacing run are historical
benchmarks, not new replicates. The five-contact crossover baseline endpoints
must remain bitwise identical to the spacing run's contact-five endpoints.
Its fine probe is not a fully fine prefix and is not used as that benchmark.
Existing ten-contact outcomes do not substitute for unmeasured early stops.
Both historical panels are independently re-audited before launch.

Fine new branches use the spacing run's already fine active prefix, then fine
new holds and onward relay (half numerical step and adaptive increment limits).
This refines acquisition from nominal 89000 onwards as well as new continuation;
the older incoming lineage/reference bank is not refined. Blocked histories
are baseline only. These are deterministic counterfactual checkpoint forks,
not independent biological replicates or statistical confidence intervals.

## Removal, retention, renewal and identity

At each checkpoint remove all ten cue cells. Copy only the two receivers'
complete 17-variable columns into separate, standard-environment isolated cells,
then integrate 10000 + 10000 nominal units with no intervening edit. No contact,
extra gap, or pre-hold refresh integration is added. Native algebraic derived
refresh remains allowed and must preserve all eight primary variables.

Forward the actual held receiver pair, even if negative or mixed. Use the
unchanged two-donor/two-fresh-recipient relay in rounds 4 and 5: two sequential
1000-unit writes, two 10000-unit recipient holds, and separate 5000-unit shadow
and 20%-opposite-regulator challenges. Only unchallenged actual recipients
continue; challenge/shadow forks are never forwarded. All onward contacts are
active, including after a blocked acquisition history. Every fresh recipient
starts opposite the requested target state.

IDs exclude the older 18-instance lineage ledger plus two qualified historical
receiver IDs and ten cue IDs (30 excluded instances per branch). Four fresh
recipient IDs per branch are disjoint. Checkpoint states at different stop
counts are placements/forks of the same history, not additional independent
cells. Cues and prepared target references must not replace receivers.

Nominal removal age is 20N−10. Round 4 starts at 109000 + (20N−10) and ends
22000 later; round 5 follows for another 22000. These are scheduled durations,
not reconstructed exact native endpoint timestamps: native integration can
overshoot and the live canonical endpoint is not necessarily the last sample.

## Fixed outcomes and analysis

Keep the six existing writing outcomes: contact_acquired, postcue_state_written,
new_state_transmitted, durable_rewrite, prompt_rewrite, delayed_rewrite.
Here contact_acquired means both receivers have the target label at REMOVAL,
before any new integration; it is not evidence that this continuation wrote
anything. Postcue writing requires both target endpoints and ≥0.95 target
occupancy in the last quarter of both cue-free holds. Durable rewrite also
requires successful target acquisition, retention and local recovery in BOTH
fresh replacement rounds. Preserve the earlier strict retained_switch endpoint.

Report removal labels, held labels, both onward-pair labels, all six outcomes,
all numerical disagreements, and comparisons against the matched blocked
history. A target label that reverts is not commitment. A non-target label that
later settles to and transmits the target can meet delayed_rewrite; do not
silently require a target removal label for durable success.

Report the earliest successful SAMPLED stop and any preceding sampled failure,
without assuming monotonicity or asserting what happens at untested counts
(especially 1, 7 and 9) or between saved endpoints. Detect and report any
success-to-failure reversal among sampled points. Similar final labels do not
establish full-state equilibrium. Old-state recipients retaining their initial
label do not alone prove old-state information was transmitted.

Independent analysis reconstructs source selection, primary state continuity,
all hold trajectories, identity exclusions, relay recovery, outcome logic and
nominal clocks from saved arrays. It compares baseline/fine checkpoint states,
post-hold receiver pairs and both outgoing fresh pairs. No mechanistic claim
about a particular molecule, delivery equality, or evolving learning rule is
inferred from this stopping-point assay.

## Execution and stopping rule

Pin upstream commit `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.
Freeze this protocol, config, runner, auditor and all executing helpers before
new integration. Copy/hash all source inputs; verify both historical audits,
frozen files, original and copied inputs, and unchanged native source.

Two single-threaded workers maximum, 900 seconds per branch, 3600 seconds total
including preflight; no automatic retries, extensions or parameter tuning.
Expected new work is 30 × (4 hold + 22 relay/challenge) = 780 integrations,
120 fresh recipients and 60 complete pair replacements. Historical priming
and benchmarks are reused and excluded from new costs. No new cue cells are
prepared or integrated after checkpoint selection.

Run software tests before launch. A failed execution/audit remains visible;
a scientifically negative branch is still a valid execution. Stop after this
panel, its audit and documentation. Any finer threshold search is a separately
authorized future experiment.
