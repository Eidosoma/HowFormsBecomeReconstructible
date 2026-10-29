# E083 retained evidence

`SOURCE_DATA.json` pins input archives and predecessor receipts. `source_TASK.npz`
contains unchanged 26-slot packets, four eligible-edge masks and original score
arrays (`old_` prefix). Task 900080/900081 uses excluded source block 900041;
scientific task IDs equal source IDs. Slots and shapes are in plan.py.

`records_TASK.npz` contains unchanged packets and uninjured denominators/couplings.
`assay_TASK_rDRAW.npz` holds injury masks, birth, effective weights, denominators,
directed normalized couplings, terminal state, final port observations, every-step
SHA-256 state hashes and boundary counts. There are exactly two draws, 0 and 1.
`cases_TASK_rDRAW.npz` retains all functional scores and weight/coupling diagnostics.
The threshold is strictly greater than .25 on both cues. Minimum margin is the
minimum across cues and the two required output signs. Transfer is signed relative
to cues; aligned transfer additionally applies the founder rule.

Selected coupling share uses all 256 receivers (including clamped input ports),
matching the historical E081 diagnostic. It is the summed absolute selected
normalized coupling divided by summed absolute normalized coupling. It differs
from E082's receiver-restricted diagnostic. Coupling L1 is divided by 256; its
reference is I0 for P0, I1 for P1, OF for FF. Pre/postinjury means and fractions
include all cells. Zero denominators yield zero coupling. OF/FF selected mass
matches before injury; injury can change the two surviving totals differently.

`individual_draws.csv` has one row per source case and fresh draw: old labels,
all six old/new endpoint scores, both cue margins, transfers, selected normalized
coupling shares, pattern effects and both pruning effects. E080 old endpoint
provenance is E077; its OF/FF labels are from E080. `individual_two_draw_means.csv`
keeps one row per original case with means over exactly two draws and gain/harm
recurrence counts. An unchanged old effect has an empty old-sign recurrence field;
its transitions remain fully counted. Every row is checked against raw arrays.

`summary.json` contains two primary mixture alignment tests (dimensionless binary
effect products, not percentage points), block scores and 97.5% intervals; complete
secondary block means and pointwise 95% intervals; fixed original group counts;
old group/new effect tables (columns harm, unchanged, gain); recurrence on 0/1/2
draws; and original/fresh pruning tables (rows immediate harm/unchanged/gain,
columns later harm/unchanged/gain). Native and mixture, sham/pulse/pooled and each
draw/two-draw mean are explicit keys. Group-conditional estimates retain block
numerators and denominators. If any bootstrap sample has no group members, its
interval is null and the undefined sample count is retained. Missing groups have
null estimates. Technical runs have null scientific verdicts.

`worker_TASK.json`, `CHECKS.json`, `INDEPENDENT_AUDIT.json`, `COMPLETE.json` and
job status/launch receipts supply independent replay, inference/count checks,
runtime and artifact hashes. `repeatability.png`/PDF show mean functional effects,
old-label/new-effect alignment, conditional recurrence and both pruning endpoints.
Technical figures are labeled as excluded from scientific inference.
