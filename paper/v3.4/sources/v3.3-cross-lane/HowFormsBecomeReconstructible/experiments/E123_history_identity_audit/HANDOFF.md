# E123 first deliverable: verified retained-data interface

**2 November 2026: complete and checked.** No decoder fitting, new trajectories
or manuscript changes. E122's running files were not opened or amended.

The [source manifest](analysis/inventory_v1/SOURCE_MANIFEST.json) covers all
**64 E014 blocks, 192 archives and 3,136 native arrays**, including all failed
formations. The 12 original code/protocol snapshots also match their recorded
hashes. Compressed source archives total 3,287,271,417 bytes; their arrays total
4,527,919,104 bytes. Those archives remain in place. Logical and resolved
physical paths, archive hashes and individual C-order array hashes are retained.
No required source archive is missing and no precision conversion was made.

The full inventory took **98.30 seconds** on one numerical thread. Independent
interface/count checks took **41.92 seconds**. The four small development
payloads total 3,523,582 bytes; the raw archive was not copied into this study.
The earlier one-block cost benchmark took 1.56 seconds.

## Portable outputs

| Output | Content |
| --- | --- |
| [SOURCE_MANIFEST.json](analysis/inventory_v1/SOURCE_MANIFEST.json) | All eligible sources, arrays, original runtime/code hashes, input whitelist, target and inclusion status. |
| [Native checkpoint counts](analysis/inventory_v1/native_checkpoint_counts.csv.gz) | 12,288 case rows covering both budgets, four checkpoints, all founders/recipients and own, foreign, protected-own routes. Every sign/amplitude joint category against every candidate, plus native count numerators and denominator. |
| [Interface check](analysis/inventory_v1/INTERFACE_CHECK.json) | Passing receipt: raw slice identity, all native qualified counts reconciled against original observations, within-stratum label balance, protected duplicates, strict threshold/zero handling and feature-boundary checks. |
| [Missingness](analysis/inventory_v1/MISSINGNESS.json) | Protected-foreign fresh readers absent from E014; full noise trajectories not saved; checkpoint outgoing records intentionally nonexistent. |
| [Development payloads](analysis/inventory_v1/development/) | Predetermined block 12000 only: 192 fresh-reader cases and 128 supplying-lifecycle cases across both budgets. Development fixture, never a cohort estimate. Metadata/labels are separate JSON files. |
| [Future prediction schema](PREDICTION_SCHEMA.json) | Shared-format table with all four raw/scored probabilities, source grouping, separate donor/native labels, model hashes, native counts and probability-rule ID. The exported CSV has a header only. |
| [Resource origins](RESOURCE_ORIGINS.json) | Original array locations, timing, exact derived configuration constant, and which fields enter observers. |
| [Exporter](export.py), [interface](interface.py), [checks](checks.py) | Reproducible retained-data inventory and tests; no dynamics or classifier implementation. Exact versions are also saved under the inventory's `inputs/`. |

Inspect native arrays with `numpy.load(path, allow_pickle=False)` using the
manifest's archive path. Verify its SHA256 first. To check an array's content
hash, hash `numpy.ascontiguousarray(array).tobytes()` and compare its separately
recorded shape/dtype. Relative paths resolve under the `experiments` root; the
physical paths document this host's current location. Metadata and row indices
locate cases; they are never observer features.

The interface's `A_factor` is an exact int64 serialization of the public
configuration integer 1 or 4. It is a **derived constant**, not a retained
historical array; `RESOURCE_ORIGINS.json` makes that distinction explicit. The
fixture's per-array dtype entries describe its serialized arrays. All actual
body/dictionary/background values are unchanged float64 slices, packets remain
uint8, and saved masks remain bool. Codec expansion is deterministic and does
not increase the amount of inherited data.

## What the interface can and cannot establish

The historical label is the founder that supplied the acquisition packet. A
foreign packet's donor is `(own_slot+1)%4`; the native reconstruction target
remains `own_slot`. Both are balanced and recorded separately. Candidates are
four observed founder prototypes from the same background, supplied identically
to every observer. The dictionary is an evaluator resource and does not enter
the native writer.

These selected checkpoint and lifecycle bodies are freshly regenerated from
incoming records. A future joint observer's improvement could show that the
body's processing makes a history easier for that observer to recognize. It
would not, by itself, show that a separately surviving body added historical
content absent from the incoming record. Acquisition-time bodies are also
inventoried but constitute a different boundary and would need their own task.

Protected fields repeat across horizons because terminal assessment draws are
reused. They remain dependent measurements within the original 64 source blocks.
The duplicate checks in the interface receipt concern the single development
block; full input-duplicate, target-shuffled and candidate-permutation decoder
checks still belong to the later analysis freeze. A passing export does not
qualify an unimplemented decoder.

## E122 integration and next work

After E122 completes and its outputs pass verification, ingest its actual
protected-foreign and 32/64/128/256 fields. Verify the overlapping E014
own/foreign/protected-own checkpoint arrays and **count each case once**; E122
continues the same blocks, not an additional independent cohort. Retain the
original native qualified/sign/amplitude outcomes and E122's frozen primary
specificity analysis unchanged.

Then finalize the bounded post hoc decoder plan: a named boundary and primary
paired comparison, inspectable template observer plus a stronger regularized
comparator, grouped outer/inner folds, probability calibration/floor/ties,
leakage controls, resource budget and block-level uncertainty. Preserve the
common theory reporting format and review the information interpretation before
fitting. Seal held-out probability tables before scoring. No identity accuracy,
log loss, historical-information estimate or component credit is measured yet.

The manuscript hold remains in effect.
