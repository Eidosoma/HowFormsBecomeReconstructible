# E068 retained evidence

Scientific blocks 40000–40031 are newly generated. Each history has four
founders and four recipients: 512 cases per sham/pulse history and 32 independent
blocks. Technical block 900041 is excluded and uses fewer recipients.

- `acquisition_BLOCK.npz`: full consistent/inconsistent-teacher acquisition;
  only the prespecified consistent-teacher record starts the source history.
- `source_boundary_BLOCK_gG.npz`, G=1…32: E065 source-generation arrays for
  each ordinary renewal, including packets, injury, read/hold endpoints and
  per-step hashes. Every boundary is independently regenerated.
- `body_BLOCK.npz`, `outgoing_BLOCK.npz`: current-body sham/pulse states,
  masks/sites, retained windows/hashes and early captured packets. The unused
  zero-duration recovery capture is retained as in the verified E065 generator.
- `source_continuation_BLOCK_gG.npz`, G=1…3: source-native continuations from
  the early capture, independently replayed under the original E058 streams.
- `source_BLOCK.npz`: earlier/final packets `(2,4,R,4096)` uint8; first axis
  sham/pulse. Scientific files are generated here, not copied from E065/E067.
- `interventions_BLOCK.npz`: native sham/pulse, mixture sham/pulse and erased
  initial packets `(5,4,R,4096)`, plus the common-support mask.
- `boundary_BLOCK_gG.npz`, G=1,2,3: recovery incoming/outgoing and cumulative
  copy packets, injury, effective weights/couplings, birth/read/hold endpoints,
  output windows, ordinary/contrast products, exact-zero fallback mask,
  clipping counts and every-step state hashes. Capture precedes holding.
- `records_BLOCK.npz`: 23 terminal packets and preinjury denominators/couplings.
  Order: five initial; five h1 rewrites; four h1 cumulative copies; five h3
  rewrites; four h3 copies. Protected copies alias h0; erased copies alias h0
  erased. Erased rewrites remain physical slots 9 and 18.
- `assay_BLOCK.npz`: common terminal injury/birth, effective postinjury weights,
  denominators/couplings, endpoints/output windows and every-step hashes.
- `cases_BLOCK.npz`: success, cue margins, signed/aligned transfer, wrong-sign
  and weak-correct outcomes, support/sign/magnitude/coupling diagnostics and
  paired gains/losses. Definitions and shapes match
  [E067](../E067_ordinary_mixture_rebuilding/DATA_DICTIONARY.md).
- `progress_BLOCK.json`, `worker_BLOCK.json`: durable stage and final replay
  receipts, including separately timed source, recovery, terminal and audit
  phases. Progress is not a scientific result.
- `summary.json`, `REPORT.md`, `rebuilding.png/.svg`: block-clustered estimates,
  fixed primary verdict, trajectories and descriptive failure composition.

`SOURCE_DATA.json` records unused scientific IDs and excluded projections.
Frozen manifests hash the complete local import closure. `COMPLETE.json`
hashes original outputs; `INDEPENDENT_AUDIT.json` links equation/state replay
and independent inference. Artifact/figure closeout is a separate final check.
Shared noise and alias reads are not independent replicates; all resampling
uses whole source blocks.
