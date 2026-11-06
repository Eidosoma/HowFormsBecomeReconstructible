# HS001 plan: historical specificity, a reference and an asymptote

**Written 1 November 2026 by fork H1, before any HS001 tissue value** (the times are in the run root's progress.md). On the PI's "please start preparing for a study on this in parallel" (1 November 2026, about 13:30Z), relayed by the lead with the reviewer's comment on E014 and "our response"; forks A3 (AR003) and N4 (NL004) run beside it. The rules below for the reference's ratio and for the asymptote's fit are fixed from this file's first save, before any long-horizon value exists.

## The question

E014 (`experiments/E014_long_renewal/`, the manuscript's Figure 4) found a founder-specific signature after sixteen body-written replacements: at 128 bytes, own-record agreement 64.38%, foreign-record 63.00%, protected own copy 68.27%, own − foreign **+1.387 points [+0.848, +1.954]**. A reviewer asks for two things.
- **A reference:** "The 1.39-point own-history increment can't be read without the largest gap the record format allows. Add a protected-foreign arm and report normalised specificity." Our response: normalise by the protected gap, R_H = (own-renewed − foreign-renewed) / (own-protected − foreign-protected), and call it a reference, not the format's capacity. Report numerator, denominator and ratio together with joint whole-block uncertainty, and allow a ratio above one.
- **An asymptote:** "'Persists through sixteen rewrites' invites the reading that specificity is kept indefinitely. Figure 4D falls from about 2.1 to 1.4 points for the 2,048-byte record. A record chain that mixes loses initial-condition information geometrically; a plateau would mean several basins. Fit decay plus plateau over 128–256 rewrites and report whether the plateau's interval excludes zero."

**HS001 asks:** how much of the founder-specific information readable from a protected record survives body-written renewal, and does it decay to zero (a mixing chain) or level off above zero (several basins)?

## The machinery: E014's, imported read-only and unchanged

- **Imported, never edited:** `experiments/common.py` (rng, the E-series seeds), `E001_unprescribed_capture` (the tissue: formation, capture, step, pack/unpack, read_packets; the observer `analyze.score`/`own_scores`), `E006_compact_renewal.run` (initial packets, the generation), `E014_long_renewal.run` (simulate, statistics, CFG). PYTHONDONTWRITEBYTECODE=1 throughout; no E-series `main()`, worker or workflow is ever called, so nothing is written into the E-series tree. Everything HS001 writes goes to its run root and to `hs001/`.
- **Unchanged:** E001's heterogeneous formation (1,000 steps) and generic capture (1,000), the 16 × 16 toroidal tissue, E006's initial packets and generation (300 reading + 1,000 writing steps), records at factor 1 (2,048 bytes) and factor 4 (128 bytes), the recipient stream block + 1,000,000, the "terminal"-stream checkpoint reader, and E014's observer: qualified agreement Q = the share of all 256 cells with |v| > 0.2 and the own founder's sign (the prototype is an offline observer only).
- **New code (`hs001/`):**
  - a generation over a declared subset of arms, line for line E006's generation;
  - the protected-foreign probe;
  - the longer checkpoint schedule;
  - the endpoints, the ratio and the fit.
- **Why a subset of arms is exact:** E001's read and write noise has an arm axis of size 1, and every operation in `step` acts on one 16 × 16 sheet at a time. So the kept arms' arithmetic does not depend on the others. A code check before this plan (test block 950002, two generations, both budgets, no outcome read) found the kept arms' packets bit-identical to E006's ten-arm panel. Q3 repeats it over sixteen generations and against E014's published scores.

## Arms

| Arm | Initial record | Renewed? | Role |
|---|---|---|---|
| rewrite | the own founder's acquired record | yes (256 generations) | E014's own-record renewal |
| foreign | the next cyclic founder's acquired record (E014's) | yes | E014's matched foreign-record renewal |
| erased | none (zero field, E014's) | yes | renewal from no record: where the chain goes on its own |
| background | the shared formation background (E014's) | yes | renewal from the shared structure alone |
| copy | the own record's exact initial bytes at every boundary | no: a read | E014's protected own copy |
| copy_foreign (**new**) | the foreign record's exact initial bytes at every boundary | no: a read | the protected-foreign reference |
| copy_erased, copy_background (reported) | the erased and background records' exact initial bytes | no: reads | each renewed arm's protected start |

- Every arm is scored against the **own** founder's prototype, as in E014. Foreign founders share the own founder's background.
- **The reads are constant across horizons.** A protected record's bytes never change, and the checkpoint reader's births and noise are shared across horizons (E014's convention). So the copy probes are computed once a block and budget. Q5 checks that rereading them at two checkpoints gives the same scores bit for bit.
- E014's shuffled, held, read_off, write_off and challenged arms are not run: none bears on the reference or the asymptote.

## Checkpoints and horizon

- **256 complete read → erase → write replacements** at both budgets.
- **Fresh checkpoint readers** after rewrites **1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256** (log-spaced; E014's 1, 3, 8 and 16 are among them). They read the outgoing records and never feed back.
- Every generation's own lineage read (G1–G256) is also scored and reported, as E014's G stages.

## Endpoints (per block: the mean over 4 founders × 2 recipient lineages; percentage points)

- **D(n)** = Q(rewrite, n) − Q(foreign, n): E014's primary contrast at horizon n.
- **The reference** Δ_P = Q(copy) − Q(copy_foreign), constant in n.
- **R_H(n)** = D̄(n) / Δ̄_P, the ratio of block averages, with a joint whole-block bootstrap: each resample takes both means over the same blocks.
- **Floors and deficits** (reported): Q(rewrite) − Q(erased), Q(rewrite) − Q(background), Q(foreign) − Q(erased), and E014's protected-copy deficit Q(rewrite) − Q(copy).
- **Replicate concordance** (reported; the brief's discriminating diagnostic), at each checkpoint and arm:
  - the sign agreement between the two recipient lineages of the same founder's decoded records, less the mean sign agreement between lineages of different founders in the same block and arm;
  - also its correlation form.
  Basins predict a lasting excess; mixing predicts its decay to 0.

## The denominator rule (fixed now)

R_H at a budget is reported **as a ratio** only if the reference's 95% whole-block lower bound is at least **half** its point estimate there. Otherwise the numerator and denominator are reported with their intervals and the ratio is marked "not reported: the reference is not resolved". A ratio above 1 is reported as such. R_H is called a reference-normalised specificity, never the format's capacity.

## The asymptote: the fit rule (fixed now, before any long-horizon value)

- **Data:** at each budget, the 16 checkpoint means D̄(n) over the blocks. The same rule is applied to R_H(n) (each resample's curve divided by its own Δ̄_P).
- **Model M1, decay plus plateau:** D(n) = c + a ρ^(n−1), 0 < ρ < 1; the half-life h = ln 2 / (−ln ρ).
  - **Fitting:** profile least squares (equal weights over the 16 checkpoints). On a fixed grid of 400 half-lives log-spaced from 0.25 to 10⁵ rewrites, (c, a) are solved linearly. The grid minimum is refined by a bounded scalar search in log h between its neighbours.
  - The limit h → ∞ (D constant) is the grid's upper end. A fit at the grid's end is reported as "no decay resolved".
- **Model M0, pure decay to zero:** c = 0, fitted the same way.
- **Model M2, two timescales plus plateau:** D(n) = c + a₁ ρ₁^(n−1) + a₂ ρ₂^(n−1), h₁ < h₂. A 60 × 60 grid of half-life pairs with (c, a₁, a₂) linear, then refinement.
- **Uncertainty:** each model is refitted on 10,000 whole-block bootstrap resamples, with E014's generator `rng("E014", "bootstrap").integers(0, NB, (10000, NB))`. Percentile 95% intervals are taken for c, a, h (and a₁, a₂, h₁, h₂).
- **The plateau's reading:**
  - **Identified** only if M1's 95% upper bound for h is at most N/4 = 64 rewrites (at least four half-lives within the horizon).
  - **Above zero** if, in addition, M1's 95% interval for c excludes zero.
  - If h's upper bound exceeds 64 the reading is **"a plateau is not identified within 256 rewrites"**, whatever c's interval says.
  - M2's c is reported beside M1's. A plateau that M2 absorbs into a slow second timescale (M2's c interval including zero) is reported as such.
- **Model-free companions** (reported):
  - the late mean L = mean of D̄ over n ∈ {128, 192, 256};
  - the late slope D̄(256) − D̄(128);
  - the remaining decay a ρ^(N−1) at the horizon;
  - SSE(M0) − SSE(M1) and SSE(M1) − SSE(M2), with their bootstrap distributions.
- **Efficacy** (Q7): on synthetic curves with known c, a and ρ (including c = 0 and slow decays) and the noise of P49, the rule recovers the parameters, covers them at about the nominal rate, and flags slow decays as not identified.

## What the reviewer's points become

| Point | HS001's answer |
|---|---|
| "a ceiling": the protected gap | Δ_P per budget, measured, with R_H(n) and the numerator beside it; on E014's own cohort post hoc, and on a fresh cohort prospectively |
| "4D falls from about 2.1 to 1.4" | D(16) − D(1) at 2,048 bytes on a fresh cohort; the whole curve to 256 |
| "fit decay plus plateau … whether the plateau's interval excludes zero" | M1 by the rule above, with M0, M2, the identification rule and the model-free late mean |
| "several basins" | the replicate-concordance excess at long horizons, beside the fit |
| "would earn the word heredity" | the registration's "what each outcome would mean", which separates a plateau within this machinery from heredity's other conditions |

## The published cohort, post hoc (phase A; descriptive, never registered)

- For E014's 64 blocks (12000–12063): formation, capture and E006's initial packets (unchanged), then the terminal-stream reader on the copy and copy_foreign records at both budgets.
- **The bridge:** the copy probe must equal E014's published after-n copy scores exactly (`runs/confirmation_v2/observations.csv`, every founder and recipient, and the summary's block means).
- R_H at checkpoints 1, 3, 8 and 16 then uses E014's published rewrite and foreign block means and the new reference. The joint intervals use E014's own 10,000 index sets (`rng("E014", "bootstrap")`, 64 blocks).
- It is labelled post hoc on a published cohort. It sizes the reference's spread for the new cohort.
- **A reported continuation of E014's published lineages** (its 64 blocks through 256 rewrites with the four lineage arms) is scoped for phase B, run after the freeze. Its first 16 generations must equal E014's published scores at checkpoints 1, 3, 8 and 16 (a bridge over the whole cohort). It answers the reviewer on the very cohort of Figure 4. It is reported, not registered, since its first sixteen rewrites are published.

## Cohort size and identities

- **The development cohort: 128 fresh blocks** (951000–951127).
  - The rule: 128 if Q9's forecast fits the cap of 30 CPU-hours, else 64.
  - Reason: the plateau's sign is the key measurement and the fit's extrapolation widens c's interval, so the largest affordable cohort is used. At the measured cost 128 fits easily.
- **Identities** (assigned by the lead, about 13:40Z; to be re-scanned by fork H1 over the E-series tree and the lane before any run):

| Use | Blocks | Bookkeeping tag |
|---|---|---|
| Smoke (full length) | 950000–950001 | mse-hs001 |
| Tests | 950002–950003 | mse-hs001 |
| P49 (probe) | 950010–950017 (8 blocks; halves 950010–013 and 950014–017) | mse-p49 |
| Preflight | 950020–950021 | mse-hs001 |
| Debug | 950022–950023 | mse-hs001 |
| Spare | 950024–950031 | |
| Development | 951000–951127 (128 blocks) | mse-hs001 |
| Reserve (not drawn) | 951128–951191 | |
| E014's published cohort | 12000–12063 (the bridge, the post hoc reference; in phase B the reported continuation) | |

- The E-series seeds its founders by (E001's tag, block number), so 950000+ are fresh founders. E014's blocks reproduce E014's founders.
- 900014–900029 are E-series benchmarks and are never used.

## The price

- **Measured** (the code check, one core, load about 49):
  - a generation at one budget costs 0.38 CPU-seconds with the four lineage arms (0.87 with E014's ten);
  - formation and capture cost 0.20.
  - So a block (both budgets, 256 generations, 16 checkpoint reads, the probes) costs about **200 CPU-seconds**. To be replaced by the full-length smoke's timing.
- **The development:** 128 blocks ≈ 7.1 CPU-hours, plus the reported continuation of E014's 64 blocks ≈ 3.6, in all ≈ **11 CPU-hours** (≈ 15 at NL003's 1.38 load ratio), against the cap of 30. On 12 workers, about 1 h of wall.
- **Phase A:**

  | Item | CPU-hours |
  |---|---|
  | The bridge (E014 block 12000, 16 generations, both budgets, E014's own simulate and HS001's) | 0.02 |
  | The post hoc reference (64 blocks: formation, capture, reads) | 0.05 |
  | The smoke (950000–950001, full length) | 0.11 |
  | Tests (950002–950003) | 0.05 |
  | P49 (8 blocks, full length) | 0.45 |
  | The debug run (950022–950023) | 0.11 |
  | Q1–Q10, the fits' bootstraps, the reader | 0.4 |
  | In all | about 1.2, against the cap of about 8 |

## Statements (candidates; thresholds from P49 by the lane's rule)

The rule: each registered part sits at least 3√(1/4 + 1/16) = 1.68 SD_block inside its threshold on P49 and passes in both halves. SD_block = max(the SD over P49's 8 block values, the SD over its 64 lineage-level values / √8).

Candidates, set or dropped on P49:
- the reference resolved, Δ_P above a threshold at both budgets;
- R_H(16) at each budget within declared bounds;
- the 2,048-byte decline, D(16) − D(1) below zero;
- the long-horizon change, D(256) − D(16), at each budget;
- the late mean L at each budget;
- the replicate-concordance excess at 256.

What P49 cannot support with margin (likely the plateau's sign and c) becomes a **prespecified measurement** with a declared reading for each outcome (the fit rule above), not a statement.

## Decisions, with reasons

1. **Fresh cohort for the registered test; E014's cohort post hoc and as a reported continuation.** The reviewer's questions concern E014's figure, but E014's first sixteen rewrites are published. A fresh cohort makes every registered statement prospective. The continuation answers the reviewer on the very lineages of Figure 4.
2. **Four lineage arms.** rewrite and foreign are the contrast. erased and background give two neutral starts, showing whether every chain converges to one level (mixing) or stays apart. E014's other arms bear on neither question.
3. **The protected reads are computed once.** They are constant by construction under E014's shared checkpoint births; Q5 checks it.
4. **128 blocks** (the rule above).
5. **256 rewrites,** the brief's horizon. A longer horizon is cheap (1,024 rewrites on 128 blocks ≈ 28 CPU-hours), but it is not built. It is the lead's call if 256 leaves the plateau unidentified.
6. **The bootstrap uses E014's generator** (`rng("E014", "bootstrap")`), so the post hoc intervals on E014's cohort use E014's own index sets.
7. **No confirmation is declared.**

## What ran before this plan

- **Reading:** E014's protocol, report, README, summary and runner; E006's and E001's code; the reviewer analysis package; the manuscript's E014 passage.
- **The code check** (13:46Z, core 46, test block 950002, `runs/.../hs001/tools/timing_reduced.py`; no outcome read): formation, capture, two generations at both budgets with E006's ten-arm generation and with the subset generation over (rewrite, foreign, erased, background) and over (rewrite, foreign, erased). The kept arms' packets were bit-identical in all eight comparisons. The timings above.

## Added 1 November 2026, after P49: the information audit's founder-identification export

**The lead's scope addition** (sent at about 14:10Z): the PI pasted an information-audit handoff between 14:03Z and 14:10Z (the lane's note `INFORMATION_AUDIT_HANDOFF.md`, first commit a387f0aea7, pushed 14:10:38Z). Its "Instructions for the Forms lane" are addressed to this work. HS001 folds the handoff's schema into its outputs before the freeze, **without changing any endpoint, arm or simulation**.

- **What is exported:** `ROOT/export/<block>.npz` for every stage of HS001's own cohort, written by the worker beside the shards and raw files. `hs001/export.py` writes the stage's `EXPORT_MANIFEST.json` in the handoff's format.
  - **The candidate dictionary:** `evaluator/prototypes`, the block's four founders' late-formation prototypes, with `evaluator/prototype_halves`. These are evaluator resources; no reader or writer ever receives them. They are **one candidate set for the own, foreign and protected records**.
  - **The packets,** native uint8:
    - the lineage arms' incoming records at acquisition;
    - the protected records' exact bytes;
    - each lineage's outgoing record at the sixteen checkpoints.
  - **The recipients' fields,** native float64, no lossy conversion: the fresh checkpoint reader's full state (v, ema, ref) for every lineage at every checkpoint, and for every protected record. v is what E014's observer scores.
  - **The labels,** stored apart from every array a decoder would read:
    - per founder and arm, the founder whose acquired record the lineage or protected read started from: own f, foreign (f + 1) mod 4, and −1 for erased and background;
    - the formation flag per founder.
  - **IDs:** the independent block, the background ID (E001 draws the background per block), the recipient stream, and the founder, recipient and checkpoint indices.
- **Inclusion:** every block of the stage, all four founders (formation failures included and flagged), both recipient lineages, every arm and checkpoint. Nothing is excluded.
- **The target,** stated for an external task: which of the block's four founders' records a lineage or protected read started from (k = 4, uniform prior 1/4 within the block). Family, phase and fine-detail recovery are different tasks and are not declared.
- **Coordinate tolerance: none.** The native reader, the writer and E014's observer act cell by cell at the shared coordinates of the 16 × 16 torus. There is no translation, rotation, reflection or sign tolerance. A decoder that allows any must declare it as a different task.
- **The outcomes stay separate:** E014's qualified (Q), sign-only (S) and amplitude (|v| > 0.2) outcomes are written to the shards, never to the export. HS001's endpoints remain Q as before. S and A are reported only.
- **No decoder is fitted in HS001.** Identity decoding is a separate post hoc audit, frozen and reviewed on its own.
- **E014's own cohort:**
  - Its raw lineage fields are **not on this host.** Only E014's per-block JSON summaries, observations.csv and the reviewer package's count extracts are here.
  - The 128 lineage archives (`block_012000_factor_{1,4}.npz` … `block_012063_factor_{1,4}.npz`, 3,227,309,039 bytes) and the 64 founder/source archives stay on the producing host, at `/home/robert/Random-Replications/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/confirmation_v2/` (E014's reviewer handoff, `analysis/reviewer_specificity_v1/HANDOFF.md`).
  - Their sha256 hashes are recorded in E014's `runs/confirmation_v2/COMPLETE.json` (192 npz entries; the file's own sha256 80f52dfbeb0f851d…) and in `analysis/reviewer_specificity_v1/data_v2/SOURCE_INDEX.json`.
  - **No identity export of that cohort is made, and its lineages are not regenerated for identity decoding.** The bridge on block 12000 and the post hoc reference (P49p) stay as briefed.
  - The worker writes no export for the stage `e014`. The reported continuation of E014's lineages scoped above remains the lead's option, for the specificity endpoints only.
- **The extra disk:** about 8.0 MB a block (the recipients' fields 6.7 MB, the packets 1.3 MB), against 1.9 MB before. That is about 1.0 GB for the 128 development blocks and under 0.1 GB for every engineering stage together, against more than 200 TB free on the scratch file system. It does not enter git.
- **The design digest changes** (the schema is pinned in `design.IDENTITY_EXPORT`). P49 and the first debug run ran under the earlier digest f0222e5cf1de. The debug blocks are rerun under the new code (`debug_v2`), and every array they share with the first debug run must be bit-identical (the export adds outputs only). The thresholds set from P49 stand.

## The lead's review (1 November 2026, 14:38Z): phase B approved

- **The rules stay verbatim:** the ratio rule, the fit rule and the identification rule.
- **Wording only, ruling 6:** M1's a is free in sign, so the fit is "a decay or a rise to a plateau". The reader's reading label "decay to a plateau indistinguishable from zero" became "a plateau indistinguishable from zero".
- **The reported continuation of E014's 64 lineages is approved,** run after the freeze. It is reported, with no identity export. Its whole-cohort bridge, the first 16 generations against E014's published scores at checkpoints 1, 3, 8 and 16, is a stop condition.
- **The 1,024-rewrite horizon is declined for now.**
- **H1–H3 are context;** the prespecified measurements answer the reviewer.
- **The lead's check P49c** is 732ff65a92 (pushed 14:37:06Z).
