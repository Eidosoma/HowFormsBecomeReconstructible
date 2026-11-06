# Comparator and interface table

This is success forecasting with a supplied task orientation. It is not
label-blind historical-identity decoding. Common setup includes the lattice,
input/output patches, task repertoire, future injury/noise and writer contract.
The current body and packet are sampled after the g14 read/capture. Family
names, IDs and target labels do not become numerical features.

| Model/input set | Permitted information | Feature count | Extra native probes | Linear diagnostic work per packet | Role |
|---|---|---:|---:|---:|---|
| Class/history | Current four-way expression class, known history, injury/noise condition | 11 | 0 | 0 | Simple baseline |
| Boundary | B11: aligned means/minimum/pass, three history indicators, unsigned/signed transfer; condition | 16 | 0 | 64 unsigned + 64 signed | Same-fold conventional baseline |
| Full cheap | B11 + declared body/packet summaries, class/products and fixed condition interactions | 70 | 0 | Same 128 iterations plus scans/traversal | Fixed principal comparator |
| No history | Full cheap minus history indicators | 67 | 0 | Same as full cheap | Feature ablation |
| No body/expression | Remove body and current-expression/class features and their interactions | 37 | 0 | Same 128 iterations | Feature ablation |
| No signed record diagnostics | Remove signed transfer and declared signed packet/body-conflict features | 60 | 0 | 64 unsigned sufficient when extracted alone | Task-aligned body information remains; not a wholly label-free/unsigned observer |
| No packet summaries | Remove packet-statistic groups/interactions; transfers remain | 47 | 0 | Same 128 iterations | Does not remove all structural information |
| Plus parent | Full cheap + 12 g13 boundary summaries | 82 | 0 new probes | +128 ancestor iterations | Separate ancestor forecast analysis |
| Plus grandparent | Above + 12 g12 summaries | 94 | 0 new probes | +128 further ancestor iterations | Separate ancestor forecast analysis |
| Original frozen TT008 | Its original B11 and coefficients | 11 | 0 | 64 unsigned + 64 signed | Different training cohort; transfer reference, not a same-training feature ablation |
| Existing direct8/direct64/successor32 probes | Their frozen declared boundary/condition inputs plus measured probe summaries | See receiving protocol | 8 / 64 / 64 | Boundary extraction plus probe work | Keep original protocols; any augmented version needs its own freeze |

Current-boundary acquisition, saved full body fields and prior ancestor
generation are shared resources, not costless abilities. Parent/grandparent
features require retained earlier fields; the zero-probe principal comparator
does not. The full dataset export computes all families together, so its timing
is shared extraction, not a separately measured optimum for each ablation.
Training and calibration costs are reported separately from native reads.

## Machine interface

- `FEATURE_SCHEMA.json` contains ordered names, feature groups and each model's
  columns. `features.packet_body` takes the full 2×16×16 float64 packet (or its
  4,096-byte native encoding), 2×16×16 body endpoint, 16×16 Boolean injury mask,
  2×2 port-window means, history and explicitly supplied task rule.
- `features.context` adds known injury count and matched/independent future
  condition. Current enrollment is after g14 and continuation uses exact writes.
  Body-derived quantities are observations at that boundary, not future probes.
- A prediction row has exactly `key` and `features`. `key` is opaque join
  metadata, never part of fitting. `features` is a finite numerical dictionary
  using only names in the frozen schema. Unrecognized/future fields are rejected.
  Missing ancestor fields are acceptable when only current-boundary models
  are requested; they are required for an ancestor model.
- The model artifact stores columns, training-only scaling, coefficients,
  selected ridge and calibration parameters. Prediction does no fitting and
  reads no outcomes. Preserve MODEL_FREEZE.json, which binds the model hash.

Example after the documented solver correction:

```bash
bash run_python.sh TT051/predict.py \
  --artifact TT051/development_v2/MODELS.json \
  --freeze TT051/development_v2/MODEL_FREEZE.json \
  --features /absolute/path/to/permitted_feature_rows.json \
  --models class_history,boundary,cheap_all \
  --output /absolute/path/in/theory-tests-lane/sealed_predictions.json
```

The receiving study must verify source identities and feature construction,
bind the complete cohort and record predictions before target outcomes. This
CLI rejects future columns but cannot certify a producer that has covertly
encoded a target inside a permitted numeric field. Source manifests, extraction
code and grouped leakage checks supply the complementary boundary assurance.

The typed raw interface differs from TT008's older aliased column names only
in storage labels; its first eleven numerical values reproduce B11 exactly
on all 32 selected development packets. No large source arrays are copied.
DATA.npz and IDENTITIES.json support the compact fit reproduction, while
SOURCE_MANIFEST.json gives native packet/body/ancestor paths and hashes.

