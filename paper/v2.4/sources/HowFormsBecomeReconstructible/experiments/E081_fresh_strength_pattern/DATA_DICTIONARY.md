# E081 data dictionary

Scientific blocks 42000–42031; technical block 900041 excluded. Four founders
(rules +/−/+/−), four recipients scientifically, cue order +/−, four arms native
sham/pulse and mixture sham/pulse. A packet encodes 512 float64 undirected weights
in 4,096 uint8 bytes. All arrays finite; equality checks include signed-zero bytes.

Reader slots: I0 0–3, P0 4–7, erased h0 8; I1 9–12, P1 13–16, erased h1 17;
OF 18–21, FF 22–25. OF ordinary pattern and FF filtered pattern both have filtered
selected total and ordinary selected signs. Outside bytes are P1. They are
post-rewrite interventions, not two independent source histories.

`acquisition_*`, `source_boundary_*`, `body_*`, `outgoing_*`, and
`source_continuation_*` retain full fresh-source evidence. `ancestry_*` contains
the earlier/final source packets; `source_interventions_*` builds native/mixture/
erased branches; `source_*` records first recovery, including incoming/outgoing
packets, ordinary/contrast/fallback arrays and reader/holding states and hashes.
`interventions_*` retains I0/P0/erased packets and original four-arm eligible mask.
`rewrite_*` retains the nine-slot ordinary writer output and complete writer data.

`components_*` stores eight OF/FF packets and repeated eligible masks; four-arm
`ordinary_packets` and `filtered_packets` share P1 outside bytes and ordinary
selected signs. `ordinary_total` and `filtered_total` have shape (4,4,R);
`scales` and `target_totals` have shape (8,4,R). OF scale T_F/T_O; FF scale one;
empty totals scale one. Records above native range are retained, never clipped.

`records_*` stores all 26 packets, raw denominators and signed normalized directed
couplings. `assay_*` stores common injury, effective weights/coupling/denominators,
paired births, final states/windows, every-step hashes and clipping counts.
`cases_*` fields have shape (26,4,R), except cue margins (26,4,R,2). Both-cue
success requires both margins >.25. Signed transfer and rule-aligned transfer,
minimum margin, wrong-sign/weak/zero partitions and opposite-rule success remain.

Additional fields: selected mass before/after injury, maximum absolute weight,
counts above one, selected nonzero count, normalized selected-coupling share,
isolation and denominator mean. Coupling share includes clamped ports; it is
not realized influence. Pattern effects preserve support/signs but may change
local denominators and surviving selected totals.

Reference diagnostics compare P0 to I0, P1 to I1, FF to OF; I0/I1/OF and erased
slots reference themselves. Temporal reference for later intact/pruned branches
is the corresponding initial branch; OF/FF reference P0 as ancestry context.
`transition_*` describes the nine writer branches: original eligible, surviving,
rewritten, fallback-written and contrast-written positions. It is not an extra
terminal observation.

`individual_effects.csv` preserves all six conditions, both cue margins, transfer,
identifiers, pattern gain, both pruning effects and temporal changes.
`individual_summary.json` includes gains/losses for every contrast, the new
immediate/later 3×3 pruning table, harms at either endpoint and immediate
beneficiaries harmed later. All counts and serialized rows are independently checked.

`summary.json` contains one primary mixture FF−OF direction and prediction flag,
all block means/intervals and secondary comparisons. Primary/secondary intervals
are both 95% but only the declared single primary determines confirmation.
Technical/failure scientific flags are null. `pattern.png/svg` shows both new
endpoints, OF/FF native-scale success, the primary contrast and individual harms.
On component failure, `available_*` retains the 18 available endpoint slots,
with a failure receipt and no substituted or dropped source cases.
