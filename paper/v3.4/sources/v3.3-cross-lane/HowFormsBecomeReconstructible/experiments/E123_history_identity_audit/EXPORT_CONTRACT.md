# E123 retained-field export contract

2 November 2026. This fixes the first inventory/interface deliverable, **not a
decoder, analysis freeze or new simulation**. E014 is an already inspected
cohort. All later estimates from it are post hoc. E122 continues under its own
freeze; this export does not inspect its running outputs.

## Sources and inclusion

Verify all 192 E014 `confirmation_v2` archives: source blocks 12000–12063,
their factor-1 and factor-4 lineages, all founders and both recipients. Compare
archive hashes against both the original completion receipt and E122's verified
registry; verify the 12 original input snapshots. Inventory every native array,
including controls outside the proposed recognition task. Preserve failures and
record missing files explicitly. Do not generate replacement fields.

For the small interface export choose **block 12000**, the first eligible block,
before decoding. Use both budgets and checkpoints 1, 3, 8 and 16. This is a
development fixture, not a population sample. The complete inventory and native
checkpoint count table cover all 64 blocks. Large archives remain in their
original storage; record logical paths, resolved physical paths, sizes, SHA256,
array schemas and C-order content hashes. No float32 conversion is permitted.

The initial recognition interface includes own renewal, foreign renewal and
protected own. The other seven original arms remain inventoried but require
separate history/null target definitions before decoder inclusion. Protected
foreign fresh readers are **not present in E014**; use E122's actual retained
reads after completion. Permuting an own protected reader into a foreign reader
would change the recipient's matched birth/noise and is not a valid substitute.

## Resources and boundaries

| Resource | Exact interface and status |
| --- | --- |
| A | Shared formation background, public 16×16 coordinates, codec factor and fixed dynamics/configuration. The background is common context for the observer; the native ordinary recipient receives a decoded packet, not an extra background field. |
| D | All four float64 founder prototypes, 8,192 bytes per block. Same dictionary for every observer. Evaluator resource; never a native writer input. |
| R | Actual uint8 incoming packet, 2,048 or 128 bytes. Decoding repeats its float64 coarse cells without rescaling. |
| B | Three float64 fields `v,ema,ref` at a named instant: 6,144 bytes. The learned reference belongs to B, not A. |
| O | Actual outgoing packet after writing. Available at the supplying lifecycle only. |
| Z | No separate acquired controller or anchor state in these selected routes. |
| Other retained context | Birth activity and generated challenge mask. The challenge is not applied to these routes. Inventory/export separately; exclude from this initial observer whitelist. |

Checkpoint rows contain the packet supplied to the independent fresh reader and
its final B after 300 reading steps. That reader does not write: **O is absent**.
Lifecycle rows contain actual R before generation g, B after its 300-step read,
the B and field after 1,000 writing steps, and actual O. The new writing field
starts at zero. These rows are exported for own/foreign only. Do not describe a
post-write field as an additional independent body component: it creates O.
Lifecycle native readout is not an independent fresh-successor outcome.

Initial activity and dynamic noise are matched across treatment arms; independent
streams occur across generations. Checkpoint probes reuse the same terminal
draws across horizons. Protected bytes and protected checkpoint bodies therefore
repeat exactly; they do not create more independent examples. The RNG coordinates
and source/recipient indices are provenance, not permitted decoder inputs.
The coordinate frame is fixed; no phase, translation or sign-gauge optimization
is performed by the export. Additional tolerances require a later declared assay.

## Target and labels

The proposed task has four block-local candidate founders and balanced prior
`[1/4,1/4,1/4,1/4]`. Its target is the **acquisition donor**, including after
renewal. Own/protected-own donor = founder slot f; foreign donor = `(f+1)%4`.
Native reconstruction always compares with own slot f. Keep both labels in a
separate metadata table and never join either into a feature bundle.

The background and complete dictionary are identical across all four targets
within a block/condition. An observer given only that setup has no case-specific
input. This is a design property, not a fitted decoding result. Bytes, four-way
recognition and native cell agreement measure different things.

The whitelist returns A and D plus R, B, R+B, or O as requested. The post-write
B view is explicitly distinct from the primary end-of-reading B. Seeds,
filenames, array row numbers, arm names, source IDs, native outcomes and labels
are not returned to observers. Metadata is for grouping and scoring only.

## Tables and checks

`native_checkpoint_counts.csv.gz` contains every eligible block, both budgets,
all four checkpoints, four own slots, two recipients and three selected routes:
12,288 rows. Each row keeps the four sign/amplitude joint counts against each
candidate, plus native qualified/sign/amplitude numerators and denominator 256.
Sign means `v>0` matches `prototype>0`; amplitude means strict `abs(v)>.2`.
Cell counts are dependent measurements, not independent samples.

`PREDICTION_SCHEMA.json` follows the theory lane's common reporting format. It
defines an empty future table: there are no predictions or probabilities in
this deliverable. Group by source block and keep all descendants, dictionaries,
budgets, conditions and horizons together. Exact features, folds, tuning,
calibration, smoothing, ties, primary comparison and measured-cost budget still
need their separate post hoc analysis freeze before fitting.

Checks cover original file/code hashes, all array schemas/content hashes,
donor initialization, byte-continuous lineages, actual written outputs,
checkpoint packet boundaries, shared dictionaries, protected duplicates, label
balance, native count reconciliation against original observations, and a
metadata-free feature whitelist. Synthetic fixtures test zero/threshold
conventions. Interface payloads are checked against their raw-array slices.
No dynamics are rerun; no classifier is trained or scored.

Run from `experiments` with `bash run_python.sh E123_history_identity_audit/export.py`:
`benchmark --name benchmark_v1` checks one source and forecasts the full scan;
`inventory --name inventory_v1` writes the complete manifest, counts and fixture;
`check --name inventory_v1` independently verifies the resulting interface.
Each command creates a new result/receipt and refuses replacement.

Read-only reporting reference:
[theory common format](../theory-lane/rdt_information_source_reporting_v0_1/reviews_2026_11_02/COMMON_REPORTING_FORMAT.txt).
The manuscript hold remains in effect.
