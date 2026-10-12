# Discovery Log — Clean-Room Plastic Heredity in Cellular Automata

Date: 2026-08-20

Status: golden-trace reconciliation complete

Current run: [`results/golden-reconciliation/`](results/golden-reconciliation/)

## Executive verdict

The code-free golden traces were sufficient to turn the earlier structural
replication into an **exact quantitative reconstruction of the retained raw ECA
atlas**. Across all 88 canonical rules and 180,224 futures, strict frequency,
break-by-8 frequency, median first-generation time, mean survival, and every
form-library ID match the retained CSV exactly. Every numerical error is zero
and every rank correlation is 1.0.

This exactness is scoped. The phase experiment used an undisclosed fresh random
stream and therefore agrees strongly rather than cell-for-cell. Particle-domain
launch rows remain undisclosed, and Life remains numerically nonidentical even
after applying the supplied pooling convention. Those limitations do not weaken
the exact raw-atlas result; they define the remaining clean-room boundary.

## Golden-trace reconciliation, 2026-08-20

### Hard replay prerequisite

An integer replay independent of the NumPy campaign engine reproduced:

- all 16 authoritative launch rows and populations;
- all **907/907** post-sweep rows and activity increments;
- all **15/15** terminal final4 spectra; and
- every disclosed copy mask and offspring row.

The vendored trace is accompanied by the upstream evidence hashes in
[`MANIFEST.json`](results/golden-reconciliation/MANIFEST.json). The exact engine
pins NumPy 2.5.2 and PCG64.

### What fixed the raw atlas

The high-impact conventions were not cosmetic:

1. the same heterogeneous 16-row launch library is shared across rules, with no
   burn-in or noiseless preparation;
2. composition zero is the first completed generation;
3. noise is applied after the rule, and activity counts the realized post-noise
   row difference;
4. failure to reach activity 256 by sweep 128 is death even when the terminal
   row is not monochrome;
5. the terminal row is observed before copying error, but the whole generation
   batch consumes an unconditional copy draw;
6. each rule/seed has one PCG64 stream whose per-sweep arrays shrink as futures
   finish, and strict-positive futures stop entering later generations;
7. the retained `break_by_8` name covers generations 0–7, hence seven observable
   fidelity boundaries; its strict comparison anchor is the break-causing
   daughter; and
8. ECA forms use each broken future's last completed composition, with the
   break-causing daughter satisfying the later-generation requirement. Form IDs
   are assigned in first-discovery order.

Items 7–8 were inferred from the retained outputs after the trace pack fixed the
physical trajectory. They are now regression-pinned: changing either loses
exact equality.

### Raw ECA atlas: exact

| Quantity | Exact matches | Error / agreement |
|---|---:|---:|
| Strict frequency | 88/88 | MAE 0; Spearman 1.0 |
| Break-by-8 | 88/88 | MAE 0; Spearman 1.0 |
| Median first-generation sweeps | 88/88 | MAE 0; Spearman 1.0 |
| Mean survival | 88/88 | MAE 0; Spearman 1.0 |
| Form libraries | 88/88 | 217/217 global forms |

The retained scientific fingerprint is recovered: the five strict champions
are rules 35 (`0.43457`), 43 (`0.34863`), 11 (`0.33984`), 57 (`0.29297`), and
184 (`0.16797`); rule 110 and all raw class-4 representatives have strict rate
zero; the undisputed class-3 core has minimum break rate `0.94238`, above the
clean class-1/2 median `0.27124`.

The clean-room re-adjudication gets the same class separation, rule-110,
heavy-tail, and smoothness directions. Its descriptor-vs-Hamming metric
calculation still differs from the retained summary despite identical atlas
rows, locating that residual specifically in the downstream null/metric
calculation rather than the simulator or atlas.

### Five-point phase: strong, not bit-exact

All 440 cells ran. Exact-cell counts are 190/440 for strict, 100/440 for break,
and 405/440 for the median clock. Agreement is nevertheless very strong:

| Endpoint | Spearman | MAE |
|---|---:|---:|
| Strict | 0.96362 | 0.00207 |
| Break-by-8 | 0.99877 | 0.00478 |
| Median sweeps | 0.99905 | 0.0773 |

All registered phase conclusions match: every noise cell excludes the class-3
core from the capability band, no class-1 rule awakens, 58 rules are capable
somewhere, every capable profile is unimodal within tolerance, and raw rule 110
has zero strict events at all five points. The remaining cell differences are
consistent with the retained phase using a fresh stream whose seed tag was not
included in the code-free pack.

### Particle, Life, and evolution

- **Particle:** the corrected batch lifecycle gives rule 110 strict
  `37/2048 = 0.01807`, nearly the retained `38/2048 = 0.01855`; the redemption
  gate passes and the chaotic-control gate fails in both. The clean-room
  champion-stability gate passes while the retained one fails. Numeric equality
  is not claimed because the four domain-dictionary launch rows were not given.
- **Life:** the disclosed hierarchical round-5 pooling is implemented exactly
  as prose: normalize each completed generation, average through the
  break-causing generation within each future, then average futures equally.
  Fidelity, persistence, and distinct-form gates all pass. Supports are glider
  `159`, blinker `667`, and toad `2715`, versus retained `2715`, `667`, and
  `671`; only blinker is exact, so execution/RNG details beyond pooling remain.
- **Evolution:** on the exact atlas, selection again finds the class-2 boundary
  and repertoire stickiness again fails, matching both retained gate outcomes.
  GPS remains out of scope because no independent fresh-stream truth table was
  available.

### Verification and artifacts

All **30 tests pass**. The reference cascade completed every stage with no
software errors. Key artifacts are:

- [`REPORT.md`](results/golden-reconciliation/REPORT.md)
- [`RESULTS.json`](results/golden-reconciliation/RESULTS.json)
- [`eca_rules.csv`](results/golden-reconciliation/atlas/eca_rules.csv)
- [`reference_comparison.json`](results/golden-reconciliation/atlas/reference_comparison.json)
- [`phase.csv`](results/golden-reconciliation/phase/phase.csv)
- [`particle_gates.json`](results/golden-reconciliation/particle/particle_gates.json)
- [`observer.json`](results/golden-reconciliation/life/observer.json)

## Superseded first-round record

The remainder of this document preserves the 2026-08-19 pre-trace run as an
audit trail. Its “partial replication” verdict describes the underspecified
first implementation, not the reconciled result above.

## Clean-room boundary

The implementation was written from the Plastic Heredity preprint, sibling
prose contracts, and retained result JSON/CSV files. No sibling `src/`,
`tests/`, or executable script was opened or reused. The implementation and
the unresolved semantic choices are recorded in
[`CLEANROOM_PROTOCOL.md`](CLEANROOM_PROTOCOL.md). All 14 independent unit
tests pass.

## What the strict endpoint means

A lineage first has to stop resembling its old anchor at cosine similarity
`<= 0.9`. Strict plastic heredity is counted only if, later within the
32-boundary horizon, it produces eight consecutively inherited daughters, all
28 daughter pairs are mutually coherent above `0.9`, and every daughter remains
at most `0.85` similar to the old anchor. Thus ordinary persistence and mere
change do not count: the lineage must change and then inherit the changed form.

## Run scale

- Raw atlas: 88 ECA orbits × 16 seeds × 128 futures = **180,224 lineages**.
- Noise phase: 88 orbits × 5 noise levels × 2,048 futures = **901,120
  lineages**.
- Particle observer: 25 registered rules × 2,048 futures = **51,200
  lineages**.
- Life: four named-object cells × 256 futures plus three random-control cells ×
  2,048 futures = **7,168 lineages**.
- Evolution: 32 repeats of four arms, 24 individuals, and 40 generations.
- Total simulated lineage futures: **1,139,712**.
- Sixteen workers were used for the ECA experiments. Measured stage time was
  267.70 s atlas, 1,243.02 s phase, 108.64 s particle, 139.32 s Life, and
  6.59 s evolution: about **29 min 25 s** of stage wall time.

## Gate-level scorecard

| Claim or diagnostic | Clean room | Retained result | Adjudication |
|---|---:|---:|---|
| Raw class-3 break separation | pass | pass | reproduced |
| Raw class-4/rule-110 strict frequency negligible | pass | pass | reproduced |
| Raw strict events have a heavy tail | pass | pass | reproduced |
| Neighboring ECA rules have smoother repertoires than random pairs | pass | pass | reproduced |
| Exact raw rule ordering and rates | no | reference table | not reproduced |
| Descriptor metric beats Hamming distance | pass | fail | opposite outcomes |
| Noise ridge/unimodality | pass | pass | reproduced |
| Class-2-only phase regime is robust across noise | fail | pass | not reproduced |
| No class-1 awakening | fail: six awaken | pass: none awaken | not reproduced |
| Particle observer redeems rule 110 | pass | pass | reproduced, weaker rate |
| Particle observer keeps all chaotic controls out | fail | fail | same negative result |
| Particle observer preserves all raw champions | pass | fail | different outcome |
| Named Life objects have high absolute fidelity | pass | pass | reproduced |
| Named Life objects out-persist random controls | pass | pass | reproduced |
| Glider, blinker, and toad have distinct form supports | fail | pass | not reproduced |
| Evolutionary selection finds the boundary robustly | fail | pass | not reproduced |
| Evolved walks are repertoire-sticky | pass | fail | opposite outcomes |
| Goal-directed planning search (GPS) | omitted | pass | not tested clean-room |

## 1. Raw-texture ECA atlas

### Structural outcomes

The clean-room atlas recovered all 88 reflection/conjugation orbits. The
break-by-8 medians were `0.2246`, `0.8916`, `1.0000`, and `0.9995` for Wolfram
classes 1–4. The minimum undisputed class-3 break rate was `0.9839`, above the
clean class-1/2 median of `0.8481`; the registered separation gate passes.

Raw class-4 strict heredity remained negligible:

| Rule | Clean-room strict | Retained strict |
|---:|---:|---:|
| 41 | 0 | 0 |
| 54 | 0.000488 | 0 |
| 106 | 0 | 0 |
| 110 | 0 | 0 |

Rule 110 ranked `79.5` of 88 in the clean-room strict ordering and did not enter
the top decile, matching the retained negative result.

The other landscape-level diagnostics were close:

| Diagnostic | Clean room | Retained result |
|---|---:|---:|
| Heavy-tail share | 0.6714 | 0.6455 |
| Neighbor/random repertoire smoothness ratio | 2.8656 | 3.1534 |
| Number of registered forms | 188 | 217 |
| Descriptor-distance Spearman | 0.1237 | 0.1350 |
| Hamming-distance Spearman | 0.0822 | 0.1534 |

Heavy-tail and smoothness gates pass in both runs. The metric diagnostic flips:
descriptor distance beats Hamming in the clean room, whereas the retained run
found the reverse. This is a mismatch, even though the clean-room gate itself
is positive.

### Numerical mismatch

Across all 88 rules, break-by-8 has Spearman `0.7113` and mean absolute error
`0.2545` against the retained table. Strict heredity has Spearman `0.5483` and
mean absolute error `0.1441`. This is meaningful rank agreement at the broad
class level, but not a numerical reconstruction.

The top five lists show the problem directly:

| Rank | Clean-room rule | Clean-room strict | Retained rule | Retained strict |
|---:|---:|---:|---:|---:|
| 1 | 28 | 0.9097 | 35 | 0.4346 |
| 2 | 14 | 0.8555 | 43 | 0.3486 |
| 3 | 156 | 0.8511 | 11 | 0.3398 |
| 4 | 13 | 0.8140 | 57 | 0.2930 |
| 5 | 172 | 0.7935 | 184 | 0.1680 |

In the retained table, clean-room leaders 28, 14, 156, 13, and 172 score only
`0.00684`, `0.0327`, `0.00293`, `0.000488`, and `0`, respectively. Conversely,
all five retained champions remain nonzero in the clean room, but at altered
rates: rule 35 `0.3013`, 43 `0.5215`, 11 `0.6611`, 57 `0.7246`, and 184
`0.4585`.

The retained directional checks—class separation, negligible raw class 4,
negligible raw rule 110, and at least three nonzero class-2 champions—all pass.
The exact atlas fingerprint does not.

Raw files:
[`atlas_summary.json`](results/reference-suite/atlas/atlas_summary.json),
[`eca_rules.csv`](results/reference-suite/atlas/eca_rules.csv), and
[`reference_comparison.json`](results/reference-suite/atlas/reference_comparison.json).

## 2. Five-point noise phase

The grid used process-noise values `0.0025`, `0.005`, `0.01`, `0.02`, and
`0.04`, with copy error `1.5 × eta`. Rule profiles are almost always unimodal:
`0.9855` of ever-capable rules in the clean room versus `1.0` retained. The
ridge-law gate therefore reproduces. The number of rules ever entering the
registered capability band is 69 versus 58 retained.

The regime composition does not reproduce:

| eta | Clean band size | Clean class-2 share | Clean core-3 intruders | Retained band size | Retained class-2 share | Retained core-3 intruders |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0025 | 35 | 91.4% | 2 | 36 | 97.2% | 0 |
| 0.005 | 42 | 95.2% | 2 | 34 | 100% | 0 |
| 0.01 | 41 | 95.1% | 2 | 36 | 100% | 0 |
| 0.02 | 44 | 84.1% | 1 | 35 | 100% | 0 |
| 0.04 | 36 | 88.9% | 0 | 25 | 100% | 0 |

Only the highest-noise clean-room cell passes the class-purity criterion, so
the registered regime-robustness gate fails. Six nominal class-1 rules awaken
somewhere on the grid—8, 32, 40, 136, 160, and 168—whereas the retained run has
none. Rule 110 remains effectively absent in raw texture: one event in 2,048
at `eta=0.0025` and zero at the other four cells; the retained run has zero at
all five.

Result files:
[`phase_summary.json`](results/reference-suite/phase/phase_summary.json) and
[`phase.csv`](results/reference-suite/phase/phase.csv).

## 3. Particle/figure-ground observer

The observer learned a rule-specific noiseless 3×3 spacetime-domain dictionary
and measured 4-mer composition only on cells outside that dictionary. Its
learned coverage is strikingly close to the retained observer:

| Wolfram class | Clean coverage | Retained coverage |
|---:|---:|---:|
| 1 | 1.0000 | 1.0000 |
| 2 | 0.9113 | 0.9173 |
| 3 | 0.8679 | 0.8656 |
| 4 | 0.9061 | 0.9064 |

The central observer-dependence result reproduces. Raw rule 110 has zero
strict events, while the particle observer gives 15/2,048 = `0.00732`, inside
the registered redemption band. The retained observer gives 38/2,048 =
`0.01855`. The clean-room Rule-110 break rate is `0.4385` versus `0.1084`
retained, and its mean above-threshold inheritance is `0.9104` versus `0.9766`;
the rescue is therefore real but quantitatively weaker.

Class-4 rates are all positive in both runs:

| Rule | Clean strict | Retained strict |
|---:|---:|---:|
| 41 | 0.01563 | 0.10303 |
| 54 | 0.04346 | 0.05420 |
| 106 | 0.00732 | 0.04248 |
| 110 | 0.00732 | 0.01855 |

The class-3 control still fails in both runs. Its maximum strict rate is
`0.02295` clean-room versus `0.06836` retained: less contamination, but still
above the registered exclusion threshold. The five raw champions all clear
the clean-room particle threshold (strict rates 11 `0.0151`, 35 `0.0244`, 43
`0.1084`, 57 `0.0127`, 184 `0.0200`), so champion stability passes here. It
fails in the retained run because rule 57 falls to `0.00342`.

Result file:
[`particle_gates.json`](results/reference-suite/particle/particle_gates.json).

## 4. Conway Life named objects

The registered 16×16 Life observer uses a generation-averaged live 2×2 census.
Absolute fidelity and persistence reproduce closely:

| Object | Clean mean H | Retained mean H | Clean survival-8 | Retained survival-8 | Clean random control | Retained random control |
|---|---:|---:|---:|---:|---:|---:|
| Blinker | 0.96969 | 0.96681 | 0.5586 | 0.5078 | 0.0688 | 0.0601 |
| Glider | 0.97062 | 0.97015 | 0.5742 | 0.5664 | 0.0869 | 0.0596 |
| Toad | 0.97035 | 0.97027 | 0.6211 | 0.5703 | 0.0464 | 0.0337 |

The named structures persist roughly 6.6–13.4 times as often as their
density-matched random controls in the clean room. The descriptive block has
mean fidelity `0.9691` and survival-8 `0.3906`, versus `0.9583` and `0.3398`
retained.

Break rates are glider `0.1563`, blinker `0.4102`, toad `0.2695`, and block
`0.2266`; retained values are `0.1445`, `0.3086`, `0.1758`, and `0.2148`.
Strict rates are small—glider `0`, blinker `0.0156`, toad `0.00391`, and block
`0.0117`—because persistence without a qualifying break is deliberately not a
strict plastic-heredity event.

Form distinctness does not reproduce. Clean-room form supports are blinker
`2715`, glider `2719`, and toad `2719`, so glider and toad merge. The retained
supports `667`, `2715`, and `671` are all distinct. Between-object cosine
similarities are nevertheless nearly identical across runs (`0.990`–`0.997`
clean-room and `0.990`–`0.998` retained), locating the mismatch in the discrete
support classification rather than overall fidelity or persistence.

Result file: [`observer.json`](results/reference-suite/life/observer.json).

## 5. Evolution on the ECA rule hypercube

Selection raises mean final fitness, but not enough to clear the clean-room
control gate:

| Arm | Clean mean | Clean 95% interval | Retained mean | Retained 95% interval |
|---|---:|---:|---:|---:|
| Selection | 0.2642 | 0.1485–0.4379 | 0.1066 | 0.0492–0.2160 |
| Drift | 0.1600 | 0.0720–0.2742 | 0.0367 | 0.00858–0.0689 |
| Random walk | 0.1777 | 0.0943–0.3180 | 0.0302 | 0.00633–0.0725 |
| Fitness shuffled | 0.1472 | 0.0485–0.2745 | 0.0252 | 0.00510–0.0640 |

The clean-room selection lower bound (`0.1485`) does not exceed the drift and
random-walk means, so `gate_selection_finds_boundary` fails; the retained gate
passes. This follows naturally from the inflated and redistributed raw atlas:
the controls encounter many high-scoring rules without selection.

Selection visits the class-3 core `0.0852` of the time versus `0.1007` for a
random walk, a modest avoidance. The retained comparison is `0.0620` versus
`0.1018`, a stronger effect.

Repertoire stickiness reverses. Clean-room evolved one-bit transitions have
mean Jaccard `0.1447` versus random-pair `0.0547` (nonempty reanalysis ratio
`2.655`), so the sticky-walk gate passes. The retained run reports `0.0201`
versus `0.0511`, so it fails.

The goal-directed planning-search (GPS) result was deliberately omitted. A
clean-room GPS adjudication needs an independent fresh-stream truth table; using
the same atlas for planning and truth would be circular. The retained GPS gate
passes, but this reconstruction makes no claim about it.

Result file:
[`evolution_summary.json`](results/reference-suite/evolution/evolution_summary.json).

## Scientific interpretation

### What is independently supported

1. A strict change-then-inheritance event can be realized in noisy cellular
   automata without importing the sibling implementation.
2. Raw-texture plastic heredity is strongly structured by dynamical regime and
   is concentrated in a heavy tail of mostly class-2 rules.
3. Rule 110 demonstrates observer dependence: it is null in raw texture and
   positive under a rule-conditioned figure/ground observer.
4. Named Life structures retain high fidelity and multi-generation persistence
   far beyond density-matched random initial conditions.
5. Local rule-space geometry is nonrandom: neighboring rules share repertoire
   structure more than unrelated pairs.

### What is not independently pinned down

1. The exact ECA champion identities, ranking, or strict-event probabilities.
2. A class-2-only capability band across the full noise grid.
3. The absence of class-1 awakenings.
4. A unique discrete form identity for each named Life object.
5. Robust evolutionary localization of the boundary landscape.
6. Goal-directed planning performance.

The large raw-atlas discrepancies cannot be attributed to seed noise at 2,048
futures per rule. The most consequential unresolved axes are the launch-anchor
timing, seed-row ensemble, process-noise ordering, terminal/death bookkeeping,
and post-break pooling convention. Form pooling directly affects repertoire
and Life-form results; the first four axes can also alter strict lineage rates.

The clean-room result therefore strengthens the paper's broad claim that
heredity is observer-relative and localized near dynamical organization, while
also showing that the retained prose/data do not specify a unique executable
experiment closely enough to recover the exact numerical atlas.

<!-- causal-heredity-round-1:start -->
## Causal heredity round 1

Completed `1787313673.1448975` under design `51710c4b87bdf0f154c67741daff6b15c7ff5d97fc2a68af62fe79da354f3e8b`.

- `causal_transmission`: `False`
- `structure_matters`: `False`
- `dose_response`: `False`
- `pedigree_persistence`: `False`
- `observer_robustness`: `False`
- `environmental_memory`: `False`
- `rule_specificity`: `True`

See `results/causal-heredity-round-1/REPORT.md` and `LAY_SUMMARY.md` for the full evidence boundary.
<!-- causal-heredity-round-1:end -->

<!-- life-carrier-round-2:start -->
## Life carrier round 2

Completed under design `9565528d988ec8b79c797103da560f239b7f681cb2768d70d5baed9b04705582`.

- Rule-125398 audit: `SATURATION_LEAD_NOT_REPLICATED`
- Sealed holdout candidates: `[]`
- Overall verdict: `NO_CAUSAL_CARRIER_FOUND`

See `results/life-carrier-round-2/REPORT.md` and `LAY_SUMMARY.md`.
<!-- life-carrier-round-2:end -->

<!-- ca-carrier-round-3:start -->
## CA carrier round 3

State `complete` under design `041fd850aa50248722cd190c03d59409560b8d91939d0729b48ee7fa2cce61f3`.
Narrow rule-31649 verdict: `DURABLE_LOCAL_PLASTIC_HEREDITY`.
Broad holdouts adjudicated: `8`.

See `results/ca-carrier-round-3/REPORT.md` for the continuous-form evidence ladder.
<!-- ca-carrier-round-3:end -->

<!-- ca-lineage-field-round-4:start -->
## CA lineage-field round 4

Overall verdict: `NO_RENEWED_LINEAGE_CARRIER`.
Selected timing profile: `reference`; elapsed `0.07` wall hours.
See `results/ca-lineage-field-round-4/REPORT.md` and `LAY_SUMMARY.md`.
<!-- ca-lineage-field-round-4:end -->

<!-- ca-motif-lineage-stage-1:start -->
## CA motif-lineage Stage 1

Upper-bound verdict: `ROBUST_LOCAL_MOTIF_CONTROLLABILITY`.
Profile: `reference`; elapsed `0.040` wall hours.
See `results/ca-motif-lineage-stage-1/REPORT.md` and `LAY_SUMMARY.md`.
<!-- ca-motif-lineage-stage-1:end -->

<!-- ca-motif-lineage-stage-2:start -->
## CA motif-lineage Stage 2

Frozen-reader verdict: `DENSITY_ROBUST_GENERAL_MOTIF_CHANNEL`.
Profile: `reference`; elapsed `0.211` wall hours.
See `results/ca-motif-lineage-stage-2/REPORT.md` and `LAY_SUMMARY.md`.
<!-- ca-motif-lineage-stage-2:end -->

<!-- ca-motif-lineage-stage-3:start -->
## CA motif-lineage Stage 3

Renewed-lineage verdict: `NO_RENEWED_CA_PLASTIC_HEREDITY`.
Profile: `reference`; elapsed `0.357` wall hours.
See `results/ca-motif-lineage-stage-3/REPORT.md` and `LAY_SUMMARY.md`.
<!-- ca-motif-lineage-stage-3:end -->

<!-- ca-motif-lineage-stage-3r:start -->
## CA motif-lineage Stage 3R

State: `awaiting_human_review`; verdict: `AWAITING_HUMAN_REVIEW`.
Elapsed `0.000` wall hours.
See `results/ca-motif-lineage-stage-3r/REPORT.md` and `LAY_SUMMARY.md`.
<!-- ca-motif-lineage-stage-3r:end -->

<!-- STAGE4_COMPRESSION_START -->
## CA Stage 4 — compressed texture heredity

State: `complete`; verdict: `ROBUST_COMPACT_RENEWED_CA_PLASTIC_HEREDITY`.
Elapsed `2.071` wall hours.
See `results/ca-motif-lineage-stage-4/REPORT.md` and `LAY_SUMMARY.md`.
<!-- STAGE4_COMPRESSION_END -->

<!-- CA_MOTIF_STAGE6_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6 — bounded minimality programme

Implemented on 2026-08-24 after the sealed Stage-5R verdict
`ROBUST_REGENERATIVE_LOCAL_64BIT_CA_PLASTIC_HEREDITY`. Stage 6 does not treat
that success as the end point: the Stage-5R one-site seed still filled the
entire 16x16 torus, and its local writer circuit still aggregated the entire
lattice. The new question is whether the history-specific recovery survives
when both operations have genuinely finite causal reach.

The clean-room implementation adds five separately invoked gates:

1. `locality`: 20 finite-hop/finite-writer-window mechanisms, strict causal
   qualification to generation 32, and endurance to generation 64;
2. `scale`: fixed and diameter-scaled communication on 16, 32, and 64 cells,
   exact light-cone checks, distance-band phenotypes, and an 18-neighbour rule
   panel without refitting;
3. `compression`: 64-, 36-, 24-, 16-, 8-, and 4-bit carriers, full ordinary
   and damaged causal ladders, corruption/drift curves, information lower
   bounds, and a cost/effect Pareto frontier;
4. `ecology`: paired carrier-wave collisions plus descent and de-novo sparse
   writer evolution, with proxy winners counted only after disjoint full-CA
   validation; and
5. `audit`: a separately authorized, model-sealed test on all 62 remaining
   untouched founder pairs.

Every visible daughter is bitwise reset before each generation. Only the
quantized boundary payload crosses that reset. Germination uses synchronous
nearest-neighbour copying, reading is local to the occupied light cone, and
rewriting is an explicitly audited directed shift-and-accumulate rectangle.
Inherited bits, temporary field/writer storage, routing work, and shared
parameters remain separate accounting categories.

The complete five-round smoke execution passed its engineering checks,
including 64x64 lattices, all checkpoint/resume paths, round decisions, final
authorization, and pre-audit model sealing. Smoke effects are not scientific
results: its two-pair gates are explicitly marked non-adjudicative. The
reference Round 6A is the only round authorized to launch initially; later
rounds wait for human review and no successor launches automatically.

Protocol: `CA_MOTIF_LINEAGE_STAGE6_PROTOCOL.md`. Implementation:
`plastic_ca/motif_minimality.py`. Tests: `tests/test_motif_minimality.py`.
<!-- CA_MOTIF_STAGE6_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6AR_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6A and Stage 6A-R correction

Reference Stage 6A completed on 2026-08-24. Its historical global and exact
controls reproduced strong generation-8 lineage crossover (0.949 and 0.959),
but no bounded candidate passed; the selected diagnostic reached crossover
zero at generations 16, 32, and 64. This initially appeared to limit the
positive Stage-5R result to organism-wide coordination.

Forensic inspection then located a specific v1 normalization defect. The
directed rectangle reducer already returned a spatial mean, but the writer
divided it by the rectangle area again. At full 16x16 span this attenuated the
empirical history term by exactly **1/256**. The first rewritten compact-anchor
payload consequently had zero lineage-centroid distance even though its
absolute bias remained nonzero. Independently randomizing the next seed origin
also allowed a bounded writer to sample outside the parent's causal region.
The negative Stage 6A record remains immutable, but it is not a clean rejection
of bounded locality.

Stage 6A-R implements a separately hashed correction and five manually gated
phases: arithmetic/equivalence audit, a 60-cell hop/window/origin bridge
matrix, local causal screening, strict qualification, and generation-64
endurance. It adds co-located and adjacent-budding origin policies, preserves
independent relocation as a non-promotable control, uses candidate-order-
independent paired random streams, and records entry/exit carrier centroids,
writer moments, causal overlap, decoder ties, and spatial phenotype effects.

The complete smoke workflow passed its engineering gates. In that two-pair
diagnostic, the corrected full bridge retained 0.75 of the historical compact
anchor while the frozen legacy calculation again produced exactly zero. Smoke
effects are not scientific evidence. The official reference correction audit
then passed under frozen design
`7be77a6e42c2a2eafdb3ec99cd106313164acebd5773d8b6b4952855a6e67225`:
the maximum writer-moment error was `6.94e-18`, full-span quantized payloads
matched Stage 5R exactly, the historical attenuation reproduced as
`0.00390625`, and the original zero-centroid collapse reproduced. Origin
geometry, label-independent random streams, tie-aware scoring, frozen Stage 6A
hashes, and reserve isolation all passed. This is an implementation audit, not
yet a biological positive result. The reference bridge is queued but remains
blocked pending explicit review; all 62 final-audit trajectories are unloaded.

Protocol: `CA_MOTIF_LINEAGE_STAGE6AR_PROTOCOL.md`. Implementation:
`plastic_ca/motif_minimality_repair.py`. Tests:
`tests/test_motif_minimality_repair.py`.
<!-- CA_MOTIF_STAGE6AR_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6BR_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6B-R — renewal, coverage, and scale

Implemented on 2026-08-25 as a new clean-room campaign. The frozen Stage-6A-R
result remains negative: the corrected whole-lattice anchor worked, but none of
the registered radius-at-most-five objects survived generation eight. The
posthoc traces nevertheless exposed a narrower lead. Several local carriers
affected generations one through four, founder clamping restored the effect,
and carrier magnitude remained nonzero while family identity rotated toward
chance. Stage 6B-R asks whether renewal geometry—not the existence of a local
signal—is the missing ingredient.

The registered search crosses five writer windows, three shared label-blind
writer fits, and four slow-latch turnover rates. Six diverse candidates are
then compared with raw and Hamming(8,4) transmission, including a paired 1%
carrier-corruption condition. Survivors cross radii five through eight and
one-, two-, and four-seed constellations. Multi-seed designs distinguish full
payload replication from a fixed-total-bit partition; zero-valued encoded
channels remain physical channels. Scale tests use nearest-seed distance,
verify exact absence of carrier support outside the union of local light cones,
and separately report inherited bits, temporary field/writer values, routing
work, seed density, and shared parameters.

All visible daughters are reset to the same matched board before every
generation. Random streams are semantic and independent of candidate labels,
ordering, worker count, and resume boundaries. Development uses disjoint
already-exposed cohorts. The 62 protected pairs remain unloaded unless at most
two finite candidates pass strict generation-16 causality and generation-64
endurance; only then is `FINAL_AUDIT_DESIGN.json` sealed and the automatically
authorized reserve opened without retuning.

The final end-to-end engineering smoke run completed all five corrected phases,
230 checkpoints, and 16x16/32x32/64x64 scale cases in 6 minutes 10 seconds. Its
protected reserve remained closed. Fifteen focused Stage-6B-R tests exercise
the positive sealing branch as well as the ordinary negative branch, and the
full 199-test repository suite passes. Smoke effects are not scientific
results. The reference output and its immutable design digest are recorded only
by the detached registered run.

Protocol: `CA_MOTIF_LINEAGE_STAGE6BR_PROTOCOL.md`. Implementation:
`plastic_ca/motif_renewal_repair.py`. Tests:
`tests/test_motif_renewal_repair.py`.
<!-- CA_MOTIF_STAGE6BR_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6C_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6C — synergistic and acquired heredity

Stage 6B-R finished with `TRANSIENT_LOCAL_PH_ONLY`. Its strongest distributed
carrier retained 0.9888 of intact recovery after a communication cut because
each separated component still held complete replicated payloads. Stage 6C
preserves that result and tests the missing causal property rather than
loosening its gate.

The new carrier represents every four-bit Walsh channel as two- or four-of-four
XOR shares. Any strict subset is independent of the payload; the reader sees a
decoded field only where all independently propagated share waves meet. The
registered controls include the frozen replicated winner, the strong
fixed-total partitioned leads, and the whole-lattice anchor. Carrier values,
occupancy, temporary fields, routing work, and shared writer parameters are
accounted separately.

A second test clamps only a density-balanced 4x4 patch in the visible parent at
generation four, releases it before the writer window, resets every daughter,
and measures paired recovery of that acquired motif. Timed cuts distinguish
germination from rewriting; scale tests predict fixed-time failure and
diameter-time rescue; endurance runs to generation 64. Only a candidate passing
the complete ladder can seal a design and open the 62 untouched pairs.

The implementation is in `plastic_ca/motif_synergistic_heredity.py`; its frozen
protocol is `CA_MOTIF_LINEAGE_STAGE6C_PROTOCOL.md`. An end-to-end engineering
smoke run exercised all five phases and the positive sealing branch. Smoke
effects are non-adjudicative. The reference output is written only by the
registered detached run, with at most four workers and eight wall hours.
<!-- CA_MOTIF_STAGE6C_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6C_RESULT_START -->
## CA motif-lineage Stage 6C

Verdict: `DURABLE_PARTITIONED_BUT_LEAKY_MEMORY`. Elapsed `2.475` wall hours.
See `results/ca-motif-lineage-stage-6c/REPORT.md` and `LAY_SUMMARY.md`.
<!-- CA_MOTIF_STAGE6C_RESULT_END -->

<!-- CA_MOTIF_STAGE6CR_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6C-R — acquired texture repair

Stage 6C provided a clean mechanistic separation. Its four-of-four XOR carrier
was causal and non-leaky: all shares together decoded the inherited identity,
strict subsets were near chance, communication cuts erased recovery, correct
rescue restored it, and opposite rescue reversed it. It nevertheless failed to
acquire an arbitrary environmental texture. The held-out acquisition effect
was only `0.005615234375`, and active rewriting was `-0.0211181640625` better
than passive decay.

Frozen forensics rejected one initial suspicion: the selected co-located
origin policy had exactly zero parent-to-daughter displacement. The actionable
breaks were instead timing and representation. The visible clamp occupied
sweeps 41--48, while the writer observed sweeps 49--64, and the 16-channel
carrier represented motif statistics rather than an oriented 4x4 bitmap.

Stage 6C-R therefore adds a separate slow texture latch without changing Stage
6C. A label-blind local writer observes only the actual visible cells during
the exposure, stores 4, 8, or 16 Walsh texture coefficients as four XOR shares,
and lets a daughter reconstruct the texture only where the four local waves
meet. The daughter then rewrites the latch from its own expressed patch.
Complement-paired stimuli and reversed assignments make the acquired history
independent of the pre-existing donor identity. The full causal panel includes
sham exposure, zero, shuffle, missing share, read and acquisition-write blocks,
transport loss, passive decay, ablation, same rescue, opposite rescue,
translation, and statistical-scaffold removal.

The five-phase engineering smoke completed 88 trajectory checkpoints,
including generation 64, 16x16/32x32/64x64 lattices, both locality scalings,
and the positive final-path rehearsal, in 526 seconds with no errors. It did
not load the protected reserve. Smoke promotion is deliberately forced and is
not scientific evidence. The reference design uses all 24 registered
candidates on disjoint exposed cohorts, at most two promotions, four workers,
an eight-hour hard stop, and a conditionally opened 62-pair final audit.

Protocol: `CA_MOTIF_ACQUISITION_REPAIR_PROTOCOL.md`. Implementation:
`plastic_ca/motif_acquisition_repair.py`. Tests:
`tests/test_motif_acquisition_repair.py`.
<!-- CA_MOTIF_STAGE6CR_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6CR_RESULT_START -->
## CA motif-lineage Stage 6C-R reference result

The reference campaign completed in 2,634 seconds with verdict
`NO_ACQUIRED_TEXTURE_WRITE`; none of the 24 candidates passed the frozen
screen, so qualification, endurance, and adjudication were skipped and the 62
protected pairs remained untouched.

This was not a featureless null. The full-rank, strong-read, `rho=0.75`
candidate produced a generation-8 acquisition effect of `0.4231770833`
(`97.5% CI 0.384765625--0.4599609375`) and perfect joint decoding, but 81.46%
of that signal remained when rewriting was stopped. Its terminal effect was
only `0.0423177083`. It was therefore a strong passive inherited imprint, not
a demonstrated actively renewed memory.

The more informative near-winner was
`texture-r16-s60-d48-rho50`. It produced acquisition `0.2444661458`
(`0.2115885417--0.2789713542`), missing the registered 0.25 cutoff by only
`0.0055338542`. It already had active-rewrite advantage `0.248046875`,
no-rewrite retention `-0.0146471`, joint decoding `0.98828125`, proper-subset
upper interval `0.59635417`, positive effects for every template pair, full
survival, and preserved statistical scaffold. This isolates the next problem
as strength and causal separation, not absence of an acquisition/renewal
channel.
<!-- CA_MOTIF_STAGE6CR_RESULT_END -->

<!-- CA_MOTIF_STAGE6D_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6D — consumptive renewal

Stage 6D is a separate clean-room follow-up that makes passive carrier copying
impossible. Each daughter may read its four-share texture carrier early in a
generation, but all share values and occupancy bits are then physically
zeroed. The CA evolves for four or eight unguided sweeps, after which a
label-blind writer observes eight visible patches and creates entirely fresh
shares. The writer interface receives neither environment bits nor labels,
lineage identity, targets, or the incoming payload.

The frozen search contains 24 full-rank candidates crossing read strength,
read duration, washout, and writer gain. The Stage 6C-R `rho=0.50` near-winner
is rerun only as a non-promotable calibration anchor. New interventions scrub
the carrier-free phenotype before writing, rescue it with the same form,
replace it with the opposite form, or reverse writer observations between the
paired histories. Together with carrier ablation/rescue/reversal, these tests
whether heredity actually traverses the daughter form rather than echoing an
old hidden state.

Nine focused tests pass. The complete engineering smoke exercised all five
phases, 92 trajectory checkpoints, generation 64, six scale combinations,
every intervention, winner freezing, and substitute audit execution in
808.73 seconds with four workers and no errors. It left the real 62-pair
reserve untouched. Smoke gates are forced software checks and provide no
scientific evidence.

Protocol: `CA_MOTIF_CONSUMPTIVE_RENEWAL_PROTOCOL.md`. Implementation:
`plastic_ca/motif_consumptive_renewal.py`. Tests:
`tests/test_motif_consumptive_renewal.py`.
<!-- CA_MOTIF_STAGE6D_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6E_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6E — phenotype bridge and somatic consolidation

Stage 6D finished with `NO_RENEWABLE_TEXTURE`, but its generation-resolved
failure was sharply localized. The strongest generation-five configuration
read the inherited texture at `0.8248697917`, retained `0.1731770833` after
the registered washout, and still showed `0.1116536458` during writing. Yet
the replacement carrier decoded at `0.4967447917`, indistinguishable from
chance. Acquisition and carrier-to-form expression worked; visible decay and
coarse writer quantization broke the first form-to-carrier handoff.

Stage 6E first maps carrier-free delays 1/2/3/5/9, writer traces 1/2/4/8, and
legacy, calibrated, automatic-gain, eight-bit, and float32 writer ceilings.
Two frontends are validated in an actual next daughter and sealed before the
mechanism search. The 26 promotable mechanisms comprise timing-only controls,
four strengths of label-blind visible hysteresis, and local-latch or diffusing
somatic fields crossed with retention, bias, and strict/broad claim tier.

The claim distinction is physical. Strict candidates destroy incoming carrier
values, occupancy, and every somatic value before a visible-only writer runs.
Broad candidates may use a zero-at-birth, non-inherited field to support the
visible phenotype during writing, but the writer never receives that field and
it is destroyed before exit. Both tiers face stopped writing, missing shares,
read/write blocks, ablation, shuffle, same/opposite rescue, phenotype and
somatic intervention, writer reversal, translation, generation-64 endurance,
three sizes, and six rule transfers. Only frozen developmental winners may
open the 62-pair reserve, with separate 98.75% final intervals for the two
claims.

Seven focused tests and the complete 234-test repository suite pass. The
six-phase, four-worker engineering smoke completed in 1,240.36 seconds with
`SMOKE_PATH_VALIDATED`, exercised both final branches using exposed substitute
pairs, produced no errors, and kept the protected reserve untouched. These
forced smoke gates are software evidence only.

The registered reference campaign was launched detached with four workers and
an eight-hour persisted clock under design
`d33b9649b9e00a2cc68fa41160e371b2600c18455b7c1c08f4169810531016a6`.
Its pollable output is `results/ca-motif-phenotype-bridge-stage-6e`; the
protected reserve was still `untouched` at launch.

Protocol: `CA_MOTIF_PHENOTYPE_BRIDGE_PROTOCOL.md`. Implementation:
`plastic_ca/motif_phenotype_bridge.py`. Tests:
`tests/test_motif_phenotype_bridge.py`.
<!-- CA_MOTIF_STAGE6E_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6ER_STAGE6F_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6E-R/6F — acquisition repair and write-back ladder

The original Stage 6E scientific verdict is invalid. Inspection of all 32
saved bridge checkpoints showed that generation four never wrote a founder
carrier: `fresh_carrier_written` was false in 32/32 traces, and every
generation-five intact patch sequence exactly equalled its sham sequence. The
simulator calculated `writer_connected` from an incoming texture reader at the
acquisition boundary and then suppressed the write when that reader was, as
designed, absent. Frozen Stage 6D has an explicit acquisition branch before
the reader-valid gate; Stage 6E had accidentally dropped it.

Stage 6E version 2 restores that branch, records whether reader connection is
required, and retains the v1 semantic namespace so the repaired replay changes
only founder acquisition. A regression test now requires a valid carrier at
generation four and five, preserves the disabled-acquisition zero control,
and proves that corrected intact/sham traces diverge. The old result directory
is immutable and is referenced by hash as `INVALID_ACQUISITION_GATE`.

The adaptive Stage 6F campaign first performs the complete corrected Stage 6E
replay. If its screen succeeds, the newly discovered ladder remains unopened.
If it fails, pair-blocked diagnostic ceilings map local patches, bounded
radii, temporal windows, and a non-promotable full-board view after carrier
destruction. Up to 132 offline proposals cover four visible temporal features
and three zero-born multi-channel fields; at most four strict, four
visible-bias, and four field-readable candidates are frozen. Field-readable
results are eligible only for the broader somatically mediated claim.

Promoted writers receive no carrier values, environment bits, templates, or
history labels. They face trace write/read blocks, ablation, shuffle,
same/opposite rescue, temporal reversal, visible scrub, carrier interventions,
generation-64 endurance, three sizes, and six rule transfers. The existing 64
exposed pairs support development, while the 62-pair reserve remains sealed
until a frozen strict or somatic winner passes every preceding gate. The run
is capped at four workers and eight persisted wall hours, with new discovery
ending after 5.5 hours.

The full adaptive engineering smoke completed in 1,134.75 seconds. It replayed
the repaired Stage 6E route and, under forced smoke gates, also exercised the
otherwise conditional Stage 6F route: all 128 observability configurations,
132 bounded proposals, eight sealed smoke writers, 24 screen checkpoints,
eight qualification checkpoints, 26 endurance checkpoints, and four
substitute final-audit checkpoints. The real reserve remained untouched. A
single-pair smoke-only cross-validation warning exposed by this run was
replaced with an explicitly labelled leave-one-sample-out software fallback;
reference inference continues to require leave-one-pair-out folds. The full
repository suite then passed 241 tests. These smoke outcomes validate the
implementation, not either scientific claim.

Protocol: `CA_MOTIF_WRITEBACK_LADDER_PROTOCOL.md`. Implementation:
`plastic_ca/motif_writeback_ladder.py`. Tests:
`tests/test_motif_writeback_ladder.py`.
<!-- CA_MOTIF_STAGE6ER_STAGE6F_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6G_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6G — local transduction and hereditary closure

The repaired reference campaign completed in 5,245.67 seconds. Stage 6E-R
showed a valid one-generation bridge, and Stage 6F found a sharply localized
post-erasure signal: a pair-blocked observer decoded the first carrier-free
4 by 4 patch at 0.849121 accuracy against 0.5 sham. Yet none of twelve live
writers passed screening; the best read effect was 0.047363. The negative is
therefore specifically `OBSERVABLE_NOT_WRITABLE`, not absence of historical
information.

Stage 6G tests the resulting code-alignment hypothesis. The diagnostic learned
an arbitrary cross-bit map, whereas the failed writer directly projected the
visible patch into the Walsh carrier basis. Exactly 144 offline translators
cross two reader endpoints, patch/radius-2 views, one/two-sweep windows,
visible-bit/Walsh targets, three ridge penalties, and full/rank-8/sparse-q8
compression. Four diverse fitted maps are frozen using only the eight bridge
pairs. They join four label-free phase-locked writers and four translated
somatic variants, for twelve candidates fixed before the disjoint screen.

Preflight decomposition supports the lead. Direct identity writing preserved
only 0.229980 of target bits. The best frozen translator achieved 0.849121
pair-held-out visible accuracy and 0.837402 carrier-roundtrip accuracy. A true
payload survived the registered quantizer exactly and survived four-share
Hamming copying and recovery at 0.988281. Thus both the information source and
downstream physical carrier work in isolation; the live closed loop remains
the decisive test.

The claim boundary is explicit. Hand-specified writers can support
label-free-local closure. Translators trained with exposed environmental labels
can support only rulebook-assisted closure, even though their frozen runtime
interface sees visible cells alone. Per-daughter calibration or target exposure
is a non-promotable diagnostic. Translator ablation, input-weight shuffle,
output-bit permutation, history shuffle, spatial displacement, phenotype
interventions, carrier controls, generation-64 endurance, scale, and rule
transfer precede any protected audit. The four-worker clock remains capped at
eight hours, with the 62-pair reserve sealed until every exposed gate passes.

The final corrected smoke (`ca-motif-local-transduction-stage-6g-smoke-v2`)
completed in 745.37 seconds with `SMOKE_PATH_VALIDATED`. It completed 24/24
screen, 12/12 qualification, 52/52 endurance, and 8/8 substitute final-audit
trajectories. The status stream correctly advanced through each phase, all
eight phase completion sentinels and the root sentinel were written, and the
manifest hashes matched the frozen implementation and protocol. The protected
62-pair reference reserve was never opened (`smoke-exposed-only`). The full
repository suite passed 248 tests. Candidate promotion in this smoke was
forced solely to exercise every conditional route and therefore carries no
scientific evidential weight.

Protocol: `CA_MOTIF_LOCAL_TRANSDUCTION_PROTOCOL.md`. Implementation:
`plastic_ca/motif_local_transduction.py`. Tests:
`tests/test_motif_local_transduction.py`.
<!-- CA_MOTIF_STAGE6G_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6H_IMPLEMENTATION_START -->
## CA motif-lineage Stage 6H — generational dialect repair

The Stage 6G reference campaign completed 448/448 exposed screen trajectories
in 2,017.70 seconds and returned `DECODABLE_NOT_TRANSDUCIBLE`. It never opened
qualification, endurance, or the protected reserve. This negative was more
specific than the preceding write failure. The best frozen visible translator
wrote a first daughter carrier with mean balanced accuracy 0.916016, while the
same measure declined to 0.658203, 0.603516, and 0.513672 over generations
6--8. Visible read effect simultaneously declined from 0.792480 to 0.104980.
The first local conversion therefore worked, but its self-produced daughters
moved away from the translator's training distribution.

Stage 6H registers a direct test of that generational-dialect hypothesis. It
uses the already exposed 16 Stage 6G screen pairs for training, divides the
previously unused 32 qualification pairs into 16 validation and 16
qualification pairs, retains the unused eight-pair endurance cohort, and keeps
all 62 final pairs unloaded until a fully frozen candidate passes every prior
gate. All 448 parent checkpoints and the parent design, result, manifest,
candidate seals, and reserve state are hashed before development.

The diagnostic decomposition compares the unchanged translator, target
forcing at every daughter, target rescue for generation 5 only, and zero
process/copy noise. It retains local eight-sweep writer traces and constructs
a train-generation by test-generation matrix for generations 5--12. Three
deterministic rollout-aggregation rounds then learn from states induced by the
previous frozen writer. Pooled ridge, random-feature, square-equivariant, and
observation-gated mixture maps provide complementary repair families. Three
somatic maps are fit on the exact EMA, reservoir, or eligibility channel they
observe at runtime, correcting Stage 6G's visible-training/somatic-runtime
channel mismatch.

Exactly 16 promotable candidates are sealed before validation: four
label-free full-form temporal summaries, two label-free compressed writers,
five assisted visible maps, three assisted channel-matched somatic maps, and
two assisted compressed maps. The four independently gated claim groups are
label-free/full, assisted/full, label-free/compressed, and
assisted/compressed. Compression uses registered Walsh ranks 8 and 4 and is
scored only in that subspace. It can establish a narrow causal heredity result
without being misreported as recovery of all 16 coefficients.

Promotable runtime paths receive no target, environment label, pair identity,
history identity, incoming payload, protected-data statistic, generation
index, or online update. Target ceilings are non-promotable. Learned maps face
ablation, input shuffle, output permutation, history shuffle, and spatial
shift; trace mechanisms face write/read blocks, ablation, shuffle,
same/opposite rescue, temporal perturbation, active-rewrite removal,
generation-64 endurance, three lattice sizes, and rule transfer. The campaign
is capped at four workers and eight persisted wall hours.

Nine Stage 6H-focused tests pass, alongside the 15 directly affected Stage
6E/6G regression tests. A real 12-generation retained-trace probe also
confirmed the expected sample shapes and no target exposure on a promoted
path.

The complete four-worker engineering smoke finished in 1,826.78 seconds with
`SMOKE_PATH_VALIDATED`. It completed 72/72 validation, 16/16 qualification,
104/104 endurance, and 16/16 substitute-audit trajectories. Forced selection
carried one member of each claim group through generation 64, all six scale
cases, all six rule transfers, and the complete final intervention panel. The
scientific 62-pair reserve was not loaded (`smoke-exposed-only`), all phase and
root sentinels were written, and the manifest's implementation, simulator,
and protocol hashes matched the files on disk. These forced gates establish
software integrity only; none of the four smoke “confirmations” is scientific
evidence.

The reference campaign was then launched in the workspace's persistent
detached execution session with four workers and an eight-hour clock under
design `49eb93b82b95e36030e6e5178b2c53e57699e77da336c51272658f699cf09d61`.
Its pollable output is
`results/ca-motif-generational-transduction-stage-6h`; at launch the protected
reserve was `untouched`. The full repository suite passes 257 tests.

Protocol: `CA_MOTIF_GENERATIONAL_TRANSDUCTION_PROTOCOL.md`. Implementation:
`plastic_ca/motif_generational_transduction.py`. Extended simulator:
`plastic_ca/motif_phenotype_bridge.py`. Tests:
`tests/test_motif_generational_transduction.py`.
<!-- CA_MOTIF_STAGE6H_IMPLEMENTATION_END -->

<!-- CA_MOTIF_STAGE6I_SMOKE -->
## CA motif-lineage Stage 6I — dynamic form and slow-field heredity

The registered campaign completed with verdict `SMOKE_PATH_VALIDATED`. Static form and phase-tolerant dynamic form were judged independently for visible-only, zero-born transient-field, and encoded inherited-field mechanisms. Confirmed claim groups: []. The protected reserve ended in state `smoke-exposed-only`.

Pollable artifacts: `results/ca-motif-trajectory-stabilization-stage-6i-smoke`. Protocol: `CA_MOTIF_TRAJECTORY_STABILIZATION_PROTOCOL.md`. Implementation: `plastic_ca/motif_trajectory_stabilization.py`.

The smoke completed 80/80 screen, 24/24 qualification, 156/156 endurance,
and 24/24 substitute-audit checkpoints in 2,503.11 seconds. Six distinct
finalists exercised the visible-only, zero-born transient-field, and encoded
inherited-field branches for both static and dynamic claims. The actual
62-pair reserve was never loaded. The full repository suite passes 267 tests.

The scientific reference was launched in the persistent execution session
with four workers and the registered eight-hour clock under design
`480ee3f9097800293694c43f8cd761d8a00344f9e55e3016a243555ae0649ecd`.
Its pollable output is
`results/ca-motif-trajectory-stabilization-stage-6i`; at launch the protected
reserve was `untouched`.

<!-- CA_MOTIF_STAGE6I_RESULT -->
## CA motif-lineage Stage 6I — dynamic form and slow-field heredity

The registered campaign completed with verdict `NO_TRAJECTORY_OR_FIELD_HEREDITY`. Static form and phase-tolerant dynamic form were judged independently for visible-only, zero-born transient-field, and encoded inherited-field mechanisms. Confirmed claim groups: []. The protected reserve ended in state `untouched`.

Pollable artifacts: `results/ca-motif-trajectory-stabilization-stage-6i`. Protocol: `CA_MOTIF_TRAJECTORY_STABILIZATION_PROTOCOL.md`. Implementation: `plastic_ca/motif_trajectory_stabilization.py`.

<!-- CA_MOTIF_STAGE6J_RESULT -->
## CA motif-lineage Stage 6J — adaptive handoff and directed trajectories

The registered campaign completed with verdict `SMOKE_PATH_VALIDATED`. Label-free and rulebook-assisted local adaptation, and static and dynamic form, were adjudicated separately. Confirmed claim groups: ['label-free-dynamic', 'rulebook-assisted-static']. The protected reserve ended in state `smoke-exposed-only`.

Pollable artifacts: `results/ca-motif-adaptive-handoff-stage-6j-smoke-v2`. Protocol: `CA_MOTIF_ADAPTIVE_HANDOFF_PROTOCOL.md`. Implementation: `plastic_ca/motif_adaptive_handoff.py`.

<!-- CA_MOTIF_STAGE6K_RESULT -->
## CA motif-lineage Stage 6K — learned writer closure and moving forms

The registered campaign completed with verdict `SMOKE_PATH_VALIDATED`. Ideal-field controls were non-promotable; learned writers had no runtime target, parent field, pair identity, or generation-index access. Joint heldout candidates: ['stage6k-equivariant-ridge-r4-w8-d40-sr0', 'stage6k-equivariant-ridge-r4-w8-d40-sr1', 'stage6k-rff-r2-w8-d40-sr0', 'stage6k-rff-r2-w8-d40-sr1']. The independent direction-aware mover bank and narrow causal lineage were adjudicated separately. The 62-pair reserve remained untouched.

Pollable artifacts: `results/ca-motif-writer-closure-stage-6k-smoke-r2`. Protocol: `CA_MOTIF_WRITER_CLOSURE_PROTOCOL.md`. Implementation: `plastic_ca/motif_writer_closure.py`.

## Stage 6L: inverse-carrier distillation and dialect closure

Stage 6L design `e26248687287ec374e9340daad959dad4126e47660fec08434dbddcaa50aee7d` completed with verdict **DYNAMIC_CA_CARRIER_CLOSURE_ONLY**. The campaign calibrated the inherited-field decoder, trained stable q4 carrier targets, performed out-of-fold closed-loop dataset aggregation, tested newly recombined narrow pairs, and ran a separate four-generation moving-object track. The protected 62-pair reserve remained untouched.

Artifacts: `/home/robert/Random-Replications/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.reconstructionsAndStressTesting/results/ca-motif-inverse-distillation-stage-6l`. Protocol: `CA_MOTIF_INVERSE_DISTILLATION_PROTOCOL.md`. Implementation: `plastic_ca/motif_inverse_distillation.py`.

## Stage 6M: latent memory and abstract carrier regeneration

Stage 6M design `122efc3c897dac27c5c4200cc96f9cbd255ff779a11c77609dd40ad4f44d7a14` completed with verdict **LATENT_AND_ABSTRACT_REGENERATION_NOT_CAUSAL**. The campaign localized history signal in retained visible traces, fitted compact encoder/decoder writers, tested closed-loop renewal on donor-disjoint procedural pairs, and independently replaced the motion snapshot with a phase/translation-neutral discrete code. The protected 62-pair reserve remained untouched.

Artifacts: `/home/robert/Random-Replications/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.reconstructionsAndStressTesting/results/ca-motif-latent-regeneration-stage-6m`. Protocol: `CA_MOTIF_LATENT_REGENERATION_PROTOCOL.md`. Implementation: `plastic_ca/motif_latent_regeneration.py`.

## Stage 6N: causal controllability and attractor renewal

Stage 6N design `4d6de28b28aa275677c84f10d48eb3ccd9abe4a699372a94a471fdc52305fd48` completed with verdict **NO_CAUSAL_COMPACT_OR_ABSTRACT_CARRIER**. The campaign calibrated object-centred mover metrics, tested direct compact-field controllability, tested a zero-born local attractor writer through closed-loop renewal, and separately tested binary-medoid shape plus polarity carriers. The protected 62-pair reserve remained untouched.

## Stage 6O: counterfactual carrier audit and closure

Stage 6O design `c0c8822730c7f050a168560f1a370bd351e8b58c45b4cce9480a0c6e993e9ff4` completed with verdict **MOTION_COMMAND_CONTROL_ONLY**. It prospectively separated instruction obedience from signed original direction, scored mover form modulo D4 symmetry, and independently repeated the Stage 6N compact ranks 4 and 16 without lowering their threshold. Stage 6N remained immutable and the protected 62-pair reserve remained untouched.

## Stage 6P: polarity closure and causal compact bases

Stage 6P design `c1e4e99e5bfc034c04630b5bf29caa793848c4856b28ca4f659d2fbd377102fe` completed with verdict **NO_POLARITY_OR_COMPACT_CLOSURE**. It prospectively separated an absolute opposite seed from repeated toggling, used frozen parental rescue codes, mapped eight-orientation transitions, and compared PCA with paired-contrast, hybrid, and supervised compact bases. Stage 6O remained immutable and the protected 62-pair reserve remained untouched.

## Stage 6Q: torus-equivariant motion closure

Stage 6Q design `b84aa9546bbbd25537dae1af395a09dd3d174350bd40d3aeaddcd18d6fc08fad` completed with verdict **OBSERVER_SEAM_ARTIFACT_CONFIRMED_NO_TORUS_CARRIER_CLOSURE**. It prospectively audited the seam-blind observer, paired center/translation/seam copy noise, and tested fresh daughter-written motion carriers. Stage 6P remained immutable and the protected 62-pair reserve remained untouched.
