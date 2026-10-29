# E065 retained evidence

Scientific blocks are 39000–39031, with F=4 founders and R=4 recipient slots.
Opposite-rule founders form two paired families; inference resamples the 32
blocks. Technical block 900041 is excluded from science.

- `acquisition_BLOCK.npz`: unchanged E016 teaching arrays. Only the consistent
  record, `acquired[1]`, initializes the source chain. Diagnostic teaching regimes
  retained in this file do not become additional scientific source histories.
- `source_boundary_BLOCK_g1.npz` through `g32`: one retained shared-noise branch,
  with packets shaped `(1,F,R,4096)`. Contains incoming/effective/outgoing packets,
  injury, birth, denominator, read endpoint, late ports, ordinary and contrast
  products, exact-zero fallback, holding endpoint and every-step hashes.
- `body_BLOCK.npz`: one h32 history, two original arms (sham/pulse), two snapshots
  (before/early). Current-body cue noise is independent. Pulse field, selected
  sites, requested/delivered squared increments, clipping counts, effective
  weights/coupling, ports and every-step hashes are retained. The legacy API's
  zero-recovery duplicate endpoint is checked and removed; it is not a third
  observation.
- `outgoing_BLOCK.npz`: generation-zero sham/pulse packets and their writer
  ordinary, contrast and fallback arrays. Packet shape `(2,F,R,4096)`.
- `continuation_BLOCK_g1.npz` through `g3`: the two source arms, same fields as
  source boundaries and packet shape `(2,F,R,4096)`. New E058 stream draws; no
  further pulse or external earlier reference enters these rewrites.
- `source_BLOCK.npz`: `initial` (early capture) and `final` (third continuation),
  both `(2,F,R,4096)`. These are the source records for the intervention.
- `interventions_BLOCK.npz`: 13 packet slots: FF sham/pulse, FO sham/pulse,
  OF sham/pulse, OO sham/pulse, earlier-C sham/pulse, earlier-S sham/pulse,
  erased. Also stores no-change alias packets, common/C/S/later-only masks,
  preinjury denominators/couplings and signed graph/anchor diagnostics.
- `assay_BLOCK.npz`: fresh E065 reader injury, birth, effective weights,
  denominators/couplings, endpoint, late port means, every-step state hashes
  and postinjury signed graph/anchor diagnostics. The paired cue axis follows
  founder and recipient axes in activity arrays. Birth/noise are common across
  record slots and shared across the two cue episodes.
- `cases_BLOCK.npz`: 13-slot raw success/margin/transfer and record diagnostics.
  Four source edge-count metrics have two original-arm slots instead. Group
  influence is per 256 grid cells; its sum is the nonisolated fraction, not one.
- `worker_BLOCK.json`: all controls, exact replay receipts, observed phase
  timings and cue count. `progress_BLOCK.json` records the last verified source
  stage during execution; its final state is retained with the run.
- `summary.json`: all block estimates, intervals, three primary classifications
  and their conjunction. Original histories and secondary effects remain visible.

Packets are little-endian float64 bytes on a reciprocal 16×16 horizontal/vertical
grid. C/S membership is fixed before fresh reader injury. Initial-only edges
cannot return in the six interventions; later-only raw values remain final.
Signs change only in OF/OO. Magnitude substitutions change local normalization.
Signed graph basis counts and forest parities retain E062's interpretation limits.

`COMPLETE.json` hashes original outputs. `INDEPENDENT_AUDIT.json` links the
complete receipt to independent source/reader checks and inference. Closeout
verifies those bytes and frozen inputs after inspecting the final figure.
