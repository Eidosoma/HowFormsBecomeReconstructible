# P1 — Paper-native population competition, removal and onward memory

Registered 2026-09-09, before any new native P1 integration. The user asked
to extend the PH work closer to the original Grodstein–Mathews–Levin paper.
This is a bounded source-faithful bridge, not full publication replication.
H4b is complete (144 cases, 423,639 checks); it found conditional task benefit
and complete agreement with the simple binary reference at measured label
checkpoints. P1 introduces no more artificial target-state schedules.

## Scientific question and relationship to the paper

The original source models an EMT regulatory circuit, voltage-dependent
gap junctions, state-dependent potassium-channel control and state-dependent
junction overexpression. Do its population-induced E-to-M changes survive
removal of the original M population? Do they need a remaining connected
neighbourhood? Can two fixed, originally E neighbours carry the effect into
a new E neighbourhood after a donor-free retention interval?

Use the unmodified BITSEY revision
`b2cb370aaecbc8299f259bc4251d5396c81f19a6`. Restore its 25-cell nearest-neighbour
line and the three `algorithm_on` modes, rather than the PH star relay or
external cue task. The choices are source `depol` (state-dependent voltage
mismatch), `nbrDepol` (also permits directional neighbour voltage control),
and `hypol` (no extra state-dependent potassium gate). The last name is
retained as a source identifier: the code itself warns that its default
absolute voltage is not a literal physiological hyperpolarization. Measure
actual voltages; do not silently change channels to match the prose.

This uses the 1D source experiment related to Table 3, not Table 1's 15,625-cell
3D field. `PAPER_OUTPUT_MAP.md` records unresolved paper/source labels and
geometry. In particular, native `tumor_has_grown` means M-labelled cell count
increased, whereas the paper describes conversion of all surrounding cells.
Report BOTH partial expansion and complete conversion, never conflate them.
The model does not simulate proliferation, migration, malignancy or survival.

## Fixed panel, selected before results

42 cases: six historical benchmark endpoints; 24 ordinary cases (two starting
M sizes, three algorithms, four powers); six miRNA-blocked controls; six
finer-numerics cases. These deterministic cases are not 42 biological replicates.

- Original field: 25 cells; first 6 or 11 start M, the others E.
- Base miRNA diffusion: `8.801117367933935e-16`, exactly the third value in
  the source's `np.geomspace(1e-16,6e-13,9)` (archive case 22).
- Junction-overexpression powers: 1, 8, 60, 100; `GJ_OiET=.5`, tumorness=1.
- Native source preparation: algorithm enabled at power 1, native default
  E/M initialization, 1,000 units with miRNA transport off. Small-ion GJs
  remain present, exactly as in `disconnected_sim`; this is NOT total isolation.
- Competition: copy the LAST RETURNED preparation snapshot, set the assigned
  power/diffusion and integrate 20,000 units, matching `power_search` semantics.
  Preserve both that snapshot and the live final state, including their difference.
- Post-competition forks carry the LIVE final state with no primary-variable
  editing, regulator pulses, resetting, relabelling or source selection.
- Blocked cases use power 60, each size/mode, with miRNA diffusion zero
  throughout competition and onward contact. All other native communication
  and voltage rules remain, making this specifically a miRNA-route control.
- Fine cases: size 11, powers 8 and 60, all algorithms. Halve minimum step
  and concentration/voltage increment bounds, including preparation. They are
  whole-protocol sensitivity checks, not additional environmental replicates.

Six benchmark cases are size 11, power 1 or 100, each algorithm. The pinned
archive `results_miRNA/metas_algos_1D_V1M_0_81.gz` case 22 explicitly records
11 final M cells at power 1 and 25 at power 100, for all three algorithms.
Require these counts and initial 11 M/14 E labels, with provenance/numerical
checks, before running any new removal/onward experiments. This reproduces
six source endpoints, NOT an exact threshold sweep or table-number agreement.

## Three forks from the same competition endpoint

1. CONTINUOUS: retain all 25 cells and their native communication, 20,000 units.
2. SOURCE REMOVED, NEIGHBOURHOOD INTACT: remove ALL original M cell identities;
   retain every originally E cell, regardless of its current label. Keep their
   native internal connections; integrate 10,000 + 10,000 units.
3. SOURCE REMOVED, CELLS ISOLATED: retain the identical originally E cells,
   but zero EVERY junction transport coefficient, including the separate free
   miRNA coefficient. Disable the `nbrDepol` gate's neighbour-reading flag:
   zero junction diffusion alone does not remove that non-junctional route.
   Preserve its cell-autonomous voltage rule. Integrate 10,000 + 10,000 units.

The isolated cells can be evaluated in one vectorized array, but cannot read
one another through either route. Structural line-edge records remain; they
are inert, not evidence of active contact. Native gates are algebraic in cell
state; no hidden gate memory is copied. Rebuilding keeps the same fixed native
external bath. Changes in material concentration are never reset between holds.

## One preassigned onward handover

Take the first TWO originally E neighbours (original positions size and size+1)
from the isolated second hold. Always take those same identities, even if
unchanged, mixed, unsuccessful or opposite to expectation. Do not pick winners.
Put them at the start of a new 16-cell native line, followed by 14 fresh E
reference cells prepared from the corresponding source preparation snapshot.
They are externally supplied cells, not biological offspring. The original M
population and the other exposed neighbours cannot enter this new line.

Use the case's original voltage/overexpression mode and miRNA setting for
20,000 units. Then remove the two carriers and isolate all 14 recipients
(all junction transport and neighbour-voltage reading off), for 10,000 +
10,000 units. Score every recipient, not only converted ones. This is one
assisted onward-transfer challenge, not autonomous renewable heredity or a
claim that the two-cell bottleneck is sufficient in this geometry.

There are 10 integrations per non-benchmark case and 2 per benchmark: 372
native integrations total. The continuous and excision forks are diagnostics,
not mutually consecutive stages. Only the isolated fork feeds onward transfer.

## Endpoints and interpretation, fixed before execution

Save full returned concentration arrays, times, live final states, cell IDs,
topology, native bath and membrane/junction parameters for every phase.
Record actual voltage, the native GJ voltage gate and expression multiplier
at phase start/end (diagnostic evaluations must not mutate cell state).
Independently reconstruct E/M/X from `Zeb_mRNA_total - miR200_total`, cutoffs
strictly above +2 or below -2. X is not silently assigned to E or M.

Report initial/final whole-field M counts, original-neighbour conversion,
native count expansion, complete neighbourhood conversion, retention in both
holds and the fraction of late returned samples that remain M (>=.95 for a
strict stable-M label). Compare exactly the same cell IDs across forks.
Report isolated retained M, connected-neighbourhood retained M and continuous
contact M separately. Onward success additionally requires originally E
carriers retained M and originally E new recipients remain M in BOTH final
isolated holds with the late-sample criterion. Also report graded counts and
partial outcomes. Record continuous marker changes, not only binary labels.

Compare native and independent E/M/X rules, provenance, inputs and snapshots.
Six whole-protocol fine cases must agree in endpoint labels and scientific
counts; report continuous differences. Quality failure limits interpretation;
negative biological-model outcomes, absence of memory and failed onward
transfer are valid results. Do not retune, retry or extend horizons after seeing
an outcome. No automatic H5, large 3D sweep, threshold search or new state model.

## Bounds and immutable provenance

Freeze configuration, protocol, all execution dependencies, tests, raw source
archive and local paper before the first benchmark integration. Hash the pinned
native Python files and require an unmodified upstream checkout. H4/H4b files
and old run artifacts remain unchanged; P1 takes no successful H4b descendants.
Only new run directories may receive P1 arrays, analysis and logs.

Run detached with two single-threaded workers; 3,600 s per-case and 21,600 s
(six hours) total runner budget. Supervisor limits: runner 21,900 s, audit
900 s, overall 23,400 s. Require 5 GiB free; never delete old results. The
rough planning estimate is 2–5 hours, not a guarantee. If the source benchmark
gate fails, stop before extension cases and report the discrepancy unchanged.
Software-only fixtures and native setup/serialization tests precede execution;
there is no unregistered native biological pilot and no outcome-driven selection.
