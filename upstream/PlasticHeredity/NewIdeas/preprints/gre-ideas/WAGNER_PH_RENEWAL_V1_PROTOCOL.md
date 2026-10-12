# Wagner PH Renewal and Evolvability v1

## Question and claim boundary

The sealed Wagner–PH bridge showed two different mechanisms. Its fixed local
carrier retained history through generation 16, but disabling descendant
rewriting did not reduce the effect. Its evolved carriers did become
renewal-dependent, but the registered evolvability nomination failed narrowly
and remained at full ten-locus capacity.

This exploratory campaign asks whether a copy environment can make active
descendant rewriting necessary, whether selection then discovers that phenotype
reproducibly, whether the phenotype survives ordinary mutation, and whether an
unconstrained resource cost compresses it. A positive result is constructive
in-silico evidence. It is not evidence that the mechanism exists in nature, and
it does not revise any sealed parent verdict.

## Immutable provenance and prediction ledger

The parent is the sealed `runs/wagner-ph-bridge-v1` campaign. Its checksum seal,
evolution selection, and verdict are recorded before any new simulation runs.
The starting carrier is the parent's frozen `phase-coupling-1p00` diagnostic
selection. The new registration includes six directional predictions before
the frontier is observed: nominal copying should not require renewal; copy
damage should expose a renewal frontier; a carrier of at most seven loci may be
enough; renewal selection should beat all three controls; mutation should retain
the phenotype using cluster inference; and doubled unconstrained cost may
compress the median carrier to at most five loci.

## Stage 1 — renewal frontier

Four target-blind same-gene carriers (`k = 3, 5, 7, 10`) cross six ordered copy
environments:

| Environment | Dilution | Dropout | Sigma |
|---|---:|---:|---:|
| nominal | 0.95 | 0.02 | 0.05 |
| mild-dilution | 0.85 | 0.02 | 0.05 |
| moderate-dropout | 0.95 | 0.10 | 0.05 |
| mixed-moderate | 0.85 | 0.10 | 0.10 |
| heavy | 0.70 | 0.10 | 0.10 |
| severe | 0.70 | 0.20 | 0.15 |

Every cell has intact and renewal-off arms. Zero and perfect-latch controls are
also run. The fresh study uses 32 Wagner rulebooks, 16 futures per A/B history,
forced-break and release-only challenges, and checkpoints 0, 4, 8, 12, and 16.
A cell qualifies only when its generation-8 gain is at least 0.15 with a positive
simultaneous lower bound, its generation-12 and generation-16 lower bounds are
positive, and the generation-8 intact-minus-renewal-off contrast is at least
0.10 with a positive lower bound.

Selection is mechanical: choose the gentlest environment containing a qualified
cell, then its smallest qualified capacity. If none qualifies, choose the
strongest `mixed-moderate` cell and label every downstream result diagnostic;
that fallback cannot pass the primary campaign verdict. Evolution also receives
the next harsher registered environment as an out-of-distribution challenge.

## Stage 2 — six-arm paired evolution

Ten founder tasks are shared across six treatments. Each treatment has ten
populations of 32 genotypes, 32 evolutionary generations, four elites, and four
training futures per A/B history. Wagner weights and target-blind carrier
parameters coevolve. Treatment arms at the same population index receive the
same founder task and semantic environmental streams.

The treatments are:

- `renewal_standard_cost`: renewal objective and a carrier cost of at most 0.10;
- `renewal_high_cost`: the same objective with every carrier cost doubled;
- `renewal_k5_feasibility`: the standard objective with a hard `k <= 5` constraint;
- `memory_standard_cost`: generation-8 memory without a renewal term;
- `acute_standard_cost`: generation-0 performance;
- `neutral_drift`: no phenotype selection.

Renewal fitness is

`0.50 × selected-environment g8 gain + 0.25 × next-harsher g8 gain + 0.25 × (intact − renewal-off at g8) − carrier cost`.

The standard carrier cost is `0.05 × k/10 + 0.025 × coupling + 0.025 × write_rate`.
No carrier function receives A/B identity or a target label. Full ancestry,
parent IDs, genotypes, fitness components, and resumable generation checkpoints
are archived. The hard-k5 treatment is an engineering feasibility arm and can
never count as spontaneous compression.

## Stage 3 — untouched held-out and mutation audit

Every final population receives the same untouched 64-future-per-history panel
through generations 0, 4, 8, 12, and 16 under selected and next-harsher copying.
Founder and selected genotypes use identical streams. Both unconstrained renewal
treatments additionally receive founder-write-off, reader-off, renewal-off,
shuffle, generation-2 erase, sign reversal, generation-3 rescue, zero, and
perfect-latch controls.

For each of the three renewal treatments, six parents spanning final-population
fitness quantiles each produce four independently mutated offspring. Parent and
offspring use the same untouched assay streams. The analysis estimates one
within-population parent-to-offspring slope, then bootstraps populations; raw
Pearson correlation is not a gate. Offspring retention is the clustered fraction
that keeps at least 70% of its parent's nonnegative generation-8 gain and a
positive renewal contrast.

The primary standard-cost nomination requires all of the following:

- mean founder-to-selected generation-8 improvement at least 0.05 with lower bound above zero;
- paired advantage of at least 0.05 with positive lower bound over memory-only, acute, and neutral arms;
- positive generation-12 and generation-16 lower bounds;
- generation-8 renewal contrast at least 0.10 with positive lower bound;
- positive next-harsher generation-8 lower bound;
- causal write, read, renewal, shuffle, erase, reversal, and rescue controls;
- at least 80% of populations positive for both memory and renewal;
- positive clustered parent–offspring slope lower bound; and
- offspring-retention lower bound at least 0.70.

An unconstrained compact nomination additionally requires the doubled-cost arm
to pass its complete analogous gate and reach median `k <= 5`.

Generation 12 is an F12-like simulated checkpoint: it is the twelfth modeled
carrier transmission, not a claim of literal biological F12 equivalence.

## Runtime, integrity, and execution

The complete scientific campaign shares a cumulative 21,600-second hard wall
limit and a 20,400-second soft boundary across restarts, with at most four
workers. Reservations are 2,700 seconds for the frontier, 12,600 for evolution,
4,200 for held-out/mutation work, and 2,100 for analysis and safety margin. The
empirical preflight projection is 19,800 seconds; launch is refused if a frozen
projection exceeds the soft boundary. A restart cannot replenish consumed time.

Population evolution and held-out audits are individually resumable. All JSON
registrations and selections are written atomically. Completed stages and the
campaign receive SHA-256 manifests and independent verification. A partial or
time-exhausted run cannot pass. Replay supports local frontier futures,
`evolution:POPULATION_ID`, and `audit:POPULATION_ID`.

Runs longer than ten minutes must use the detached supervisor:

```bash
./scripts/run-wagner-ph-renewal-detached.sh \
  runs/wagner-ph-bridge-v1 runs/wagner-ph-renewal-v1 \
  4 /tmp/gre-sim-venv

./scripts/status-wagner-ph-renewal.sh \
  runs/wagner-ph-renewal-v1 /tmp/gre-sim-venv
```

The smoke campaign is a software and invariance test. Its signs, magnitudes, and
gates are not scientific evidence.

## Operational amendment after the first production attempt

The production attempt exhausted the original supervisor after 21,540 seconds.
The renewal frontier and all 60 evolution populations were sealed, while 38 of
60 held-out population files were complete. No campaign verdict or final-audit
analysis existed, and no scientific values from the partial audit were examined;
only runtime, stage status, timestamps, and treatment filenames were inspected.

The user then explicitly authorized resumption. Before any further simulations,
the implementation added an immutable `runtime-extension-registration.json`.
It permits at most 7,200 additional seconds, with a 6,600-second soft boundary,
and changes no seed, sample, treatment, endpoint, gate, selection, or analysis.
The original six-hour failure remains recorded. If completion succeeds, the
manifest must say that it completed under an authorized extension and did not
complete under the original six-hour boundary. The total cumulative authorized
wall time is at most 28,740 seconds for this run.

The extension uses a distinct persistent ledger and detached supervisor:

```bash
./scripts/resume-wagner-ph-renewal-extension-detached.sh \
  runs/wagner-ph-bridge-v1 runs/wagner-ph-renewal-v1 \
  4 /tmp/gre-sim-venv
```
