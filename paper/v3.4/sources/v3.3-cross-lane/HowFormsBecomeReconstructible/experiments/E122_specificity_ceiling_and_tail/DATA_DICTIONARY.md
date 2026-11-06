# E122 retained-field and derived-table interface

Each `block_B_factor_F.npz` has one independent background block, four own
founders, two recipients and the declared budget. Factors 1/4 encode 2,048/128
bytes. All floating arrays retain native float64; packets remain uint8, counts
uint16, masks bool and indices int16. No lossy precision conversion is made.
The adjoining JSON lists every array's actual shape, dtype, bytes and file hash.

- `prototype`, `prototype_halves`, `background`: original four-candidate
  dictionary and common background. Prototypes are external evaluator resources.
- `boundary_numbers`, `boundary_packets`, `boundary_sha256`: actual outgoing
  own/foreign records after 16–256 rewrites. Each next writer receives precisely
  the preceding packet. Axes: boundary, own founder, recipient, route, bytes.
- `protected_packets`: acquisition bytes for protected own/foreign, never
  rewritten. The original archive remains the source of earlier boundary fields.
- `checkpoint_packet`: all four incoming assessment routes at horizons
  1/3/8/16/32/64/128/256. Route order is own, foreign, protected own, protected
  foreign. These are the preceding writer outputs or acquisition bytes.
- `checkpoint_state`: fresh nonwriting recipient state, axes checkpoint,
  founder, recipient, route, component (`v,ema,ref`), row, column. This is the
  terminal reader instant; it produces no new outgoing record.
- `checkpoint_birth`, `checkpoint_mask`: shared birth and declared legacy
  challenge-mask coordinates. These four routes do not apply the challenged-arm
  intervention; a saved mask is not evidence of an applied injury.
- `checkpoint_writer_incoming/outgoing/read/written`: the actual supplying
  lifecycle at each checkpoint, only own/foreign routes. Read components are
  `v,ema,ref`; written components are `v,ema,ref,field`. Writing starts with a zero
  new field. There is no hidden protected or founder template in the writer.
- `checkpoint_joint`: counts, axes checkpoint, founder, recipient, route,
  candidate target (0–3), sign-match flag (0/1), amplitude-qualified flag (0/1).
  All four categories sum to 256; `[1,1]` is qualified agreement. Comparisons
  use `v>0`, prototype>0, and strict abs(v)>.2 in original coordinates.
- `checkpoint_pair_counts`: checkpoint, founder, recipient, comparison
  (renewed or protected own-versus-foreign), metric (qualified/sign/amplitude),
  direction (own-only/foreign-only). Counts are dependent cells, not replicates.
- `generation_read_joint`, `generation_written_joint`: the same all-target
  categories for actual supplying bodies at generations 17–256, with two routes.
  These are distinct from fresh-recipient checkpoint reconstruction.

The JSON metadata provides block, native own-target and historical donor mapping:
foreign routes inherit `(own_founder+1)%4`, own routes inherit own_founder.
That donor remains the historical label through descendants even though native
agreement always targets the own founder. Labels, conditions, block IDs and
row order must be kept outside E123 decoder features. Each held-out block has
its own four-candidate dictionary, identically available to all future observers.

`cases.csv` carries all cell-count numerators and the 256-cell denominator per
record; `block_outcomes.csv` aggregates eight founder/recipient cases with the
2,048-cell denominator. Whole-block averages, not cells or descendants, are
statistical units. `ratio_bootstrap.npz` keeps numerator, denominator and ratio
for every draw without filtering; `tail_fit_bootstrap.npz` keeps point then
2,000 fitted bootstrap results in columns C,A,tau,p,SSE,boundary flag. Final
scores, Fieller sets, predictions and model limitations are in `summary.json`.

Raw sources and original hashes are in `SOURCE_DATA.json`; run manifests pin
code and protocol copies. Retrieve each NPZ from its metadata path and verify
its SHA256 before decoding. A source file's missingness is an error, not grounds
to regenerate a replacement or silently omit the block. E014 exposures remain
known; an eventual E123 fitted-decoder analysis is post hoc and needs its own freeze.
