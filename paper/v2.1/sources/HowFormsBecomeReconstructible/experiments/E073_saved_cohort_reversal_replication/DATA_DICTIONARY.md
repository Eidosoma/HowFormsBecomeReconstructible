# E073 retained evidence

Scientific blocks 40000–40031, four founder slots, R=4 recipients; technical
block 900041 is excluded, with R=2 fixture and R=1 benchmark. Arrays are finite
and loaded without pickle. Blocks are the independent units.

## Slots and source

Nine initial slots: intact native sham/pulse and mixture sham/pulse (0–3),
their once-pruned counterparts (4–7), and the saved erased-start rewrite (8).
Terminal slots 0–8 are h0; 9–17 are their complete ordinary-rewrite outputs
at h1. E073 h0/h1 correspond to source g1/g2. No second pruning step.

Same-horizon intact reference indices are
`[0,1,2,3,0,1,2,3,8,9,10,11,12,9,10,11,12,17]`.
Own-policy temporal references are `[0,1,2,3,4,5,6,7,8]` repeated twice.

- `source_BLOCK.npz`: source `incoming`/`outgoing` uint8 packets
  `(5,4,R,4096)`, decoding to little-endian float64 `(5,4,R,2,16,16)`;
  writer `ordinary`, `contrast`, `fallback` with decoded shape; injury
  `masks` `(4,R,16,16)`. No predecessor reader scores are loaded.
- `interventions_BLOCK.npz`: initial `packets` `(9,4,R,4096)`, `eligible`
  bool `(4,4,R,2,16,16)`. Selected values become positive zero; all outside
  bytes and the erased source packet remain exact.
- `rewrite_BLOCK.npz`: complete E067-equation rewrite evidence, including
  incoming/outgoing packets, fresh masks/birth, effective weights,
  denominator and four directed normalized couplings, final developed state,
  final port trace/means, every-step SHA256 state hashes, captured ordinary/
  contrast/fallback fields and post-capture holding state/hashes. State shape
  `(9,4,R,2,16,16)` includes the cue axis. Hash arrays are `(steps,32)` uint8.
  The captured packet is inherited; holding activity is not.
- `records_BLOCK.npz`: 18 terminal packets and their uninjured natural
  denominator `(18,4,R,16,16)` and coupling `(18,4,R,4,16,16)`.
- `assay_BLOCK.npz`: terminal masks/birth `(4,R,16,16)`, effective weights,
  natural denominators/couplings, end state `(18,4,R,2,16,16)`, `late_ports`
  `(observe_steps,18,4,R,2,2)`, `mean_ports` `(18,4,R,2,2)`, every-step
  hashes and boundary counts `(18,4,R)`. Directed order: right,left,down,up.

Writer and terminal streams are distinct. All policies/horizons within a
terminal assay share injury, birth and cue noise; opposite-rule founders
0/1 and 2/3 share nuisance draws. Terminal results never affect rewriting.

## Cases and transition diagnostics

`cases_BLOCK.npz` has shape `(18,4,R)` per scalar metric; `margin` adds two
cues. Functional fields: `both`, minimum margin, signed/aligned transfer,
correct-sign below threshold, zero without wrong sign, any wrong sign and
opposite-rule success. `gained_success`/`lost_success` compare same-horizon
intact records; `temporal_gained_success`/`temporal_lost_success` compare each
policy to its own h0 under the same reader draws.

`eligible_edges`, `no_eligible_edges`, `selected_present` and
`selected_present_fraction` refer to the original selection, even after it
has been pruned or rewritten. Presence fraction divides by original eligible
count. Support gain/loss and shared-edge sign changes compare to same-horizon
intact records. Edge counts are undirected; weight mass is absolute.

For prefixes `''` and `'postinjury_'`, `selected_coupling_share` is the selected
absolute normalized coupling divided by current total coupling. Signed/
unsigned `coupling_l1` compares same-horizon intact coupling, and
`temporal_coupling_l1` compares the own-policy initial coupling; sums divide by
256 cells. Denominator means and isolation include all cells, including
injured cells and clamped ports. These structural measures are not realized
causal influence. Empty ratios are zero and absence flags remain explicit.
`boundary_fraction` counts clipping at ±2 on live nonport cells over both
cues and all terminal steps.

`transition_BLOCK.npz` has `(9,4,R)` scalar fields: original eligible count,
available selected count after writer injury, no-available flag, selected
nonzero output count, its fraction of physically available selected edges,
and nonzero selected outputs written through fallback versus contrast.
Fallback plus contrast counts must equal rewritten selected count. These
raw transition counts are independently replayed; the summary reports the
before/after presence and coupling measures. Reappearance alone is descriptive.

## Inference and receipts

`summary.json` retains block means, means, percentile intervals and confidence
for all scalar case metrics and prespecified score contrasts. Only
`effect/both/pooled/mixture_gain_h0` and `mixture_gain_h1` use 97.5%; other
intervals use pointwise 95%. `native/` is the inherited naming convention for
directly observed summaries, including mixture records. `persistence_supported`
requires both primary intervals strictly positive, with all controls passed.
Scientific classifications are null on technical or failed-control results.

`reversal_replicated` requires the immediate mixture gain interval strictly
positive and the post-rewrite interval strictly negative. It is null for
technical/failed-control runs. E072's original status labels and
`persistence_supported` rule are retained. Sources are all E068 g1 blocks,
with prior exposure declared and no predecessor scores pooled.

Worker receipts retain source/intervention/writer/reader controls and separate
production/audit timings. `CHECKS.json`, `COMPLETE.json` and
`INDEPENDENT_AUDIT.json` retain verification counts, original hashes and the
scientific verdict. All model/analysis dependencies are frozen before retained
technical runs. Qualification and the runtime/storage forecast precede
scientific launch. Scientific closeout follows replay and figure inspection.
