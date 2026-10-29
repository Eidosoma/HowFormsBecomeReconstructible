# E077 data dictionary

Slots 0–3 I0, 4–7 P0, 8 erased h0, 9–12 I1, 13–16 P1, 17 erased h1,
18–21 M1, 22–25 J1. Each four-slot group orders native sham, native pulse,
mixture sham, mixture pulse. Founder axis has four rules +/−/+/−; recipient
axis has R=4 scientifically. Each record encodes 512 float64 undirected weights
as 4,096 bytes. Cue axis orders +1, −1. Whole source blocks are independent units.

`acquisition_*`, `source_boundary_*_g1..g32`, `body_*`, `outgoing_*` and
`source_continuation_*_g1..g3` retain regenerated source history and state hashes.
`ancestry_*` holds its initial/final packet pair. `source_interventions_*` holds
native/mixture/erased inputs to the first recovery writer. `source_*` holds that
writer's complete boundary: incoming/outgoing, ordinary/contrast/fallback,
injury masks, states, denominators and state hashes. E077 source generation is
new; previous scientific arrays are not inputs.

`interventions_*` retains I0/P0/erased packets and the original four-arm eligible
mask. `rewrite_*` is the complete nine-slot I1/P1/erased writer, with no repeated
pruning. `components_*` contains the eight M1/J1 packets and original eligible
mask. `records_*` contains all 26 packets, raw denominators and normalized
directed couplings. `assay_*` retains matched terminal injury, effective weights,
denominators/couplings, birth, final state, final port window, all state hashes
and clipping counts.

`cases_*` has shape (26,4,R) except two-cue `margin`, shape (26,4,R,2).
`both` requires both margins > .25. `transfer` is the signed cue response;
`aligned_transfer` multiplies it by the founder rule. `minimum_margin` is the
worse cue margin. The mutually exclusive outcome partition is success,
correct signs below threshold, zero without wrong sign, any wrong sign.
Opposite-rule success is also retained, as a subset of wrong-sign outcomes.

Reference-relative fields (`gained_success`, `lost_success`, sign/support changes,
coupling distances) compare P0 with I0, P1 with I1, M1/J1 with P1; each other
slot references itself. Temporal fields compare I1 with I0, P1/M1/J1 with P0,
and erased h1 with erased h0. They are different comparisons. `selected_present`
counts originally selected nonzero positions; coupling shares divide their
absolute directed coupling by all absolute directed coupling and include clamped
ports. `postinjury_` fields use each reader's effective record. Zero denominators
give zero drive; a zero total share uses zero with eligibility/isolation flags.

`transition_*` is the nine-slot writer's counts of available/rewritten selected
positions and exact fallback versus contrast use. Counts are not independent
edge replicates. `individual_effects.csv` retains all six outcomes, two cue
margins and transfers per native/mixture case, with identifiers and four signed
binary contrasts. `individual_summary.json` retains gains/losses, the 3×3
immediate/later effect table (harm/unchanged/benefit axes), number harmed at either
endpoint and continuous changes. Both files are independently checked against
raw cases and summary means before completion.

`summary.json` stores every block mean, effect, interval and four-direction
conjunction. Technical/failed-control scientific flags are null. On selected
support mismatch, `component_failure_*` records the affected positions and
`available_assay_*` / `available_cases_*` retain the first 18 endpoint slots;
the block/run fails rather than silently dropping source cases.
