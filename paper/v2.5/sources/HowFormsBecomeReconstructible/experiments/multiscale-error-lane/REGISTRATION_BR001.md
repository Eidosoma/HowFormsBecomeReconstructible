# BR001 registration: records in the tissue

**Frozen 25 October 2026 at 17:49:02Z, before any development outcome. Development study, not confirmation.** The design is `br001/design.py`, digest `03e4778294862d394030099540f957967801395826e6dfb6af539f7f2cf2b0fe`. Source hashes, the panel P write thresholds and the registered statements are in `br001/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows, and the development run starts only if it passes.

## Why

The biological review (REVIEW_BIOLOGY.md, 25 October) found the lane's least biological element: a full-resolution record kept apart from the body. In biology, chromatin, bioelectric and positional records mostly sit in the cells they shape, so a wound hits tissue and record together. Engineering probes P6 and P7 showed this changes the answers:
- **Redundancy needs independent copies.** A second record voting with the body helps only when the two are injured independently.
- **A tissue-held record needs repair at two scales.** A self-correcting record heals small wounds, a protected coarse code heals large ones, and only the two together heal every size.

BR001 makes the record live in the tissue and asks three questions on fresh blocks.

## The world

- **Body:** each site's state v follows the native physics and reads its own record r with the native gain. Two body variants are run:
  - **c**, the native body with the conserved mean (ME001, ME002), reproduced bit for bit when every new element is off;
  - **o**, an open body with no mean removal.

  Founders are acquired with the native physics, as in ME002, under tag `mse-br001`.
- **Record dynamics** (slow, bistable at ±1.2, quiet), each part optional by arm:
  - **self-correction:** r ← r + 0.05 [r (1 − (r/1.2)²) + k_r (N(r) − r)] + σ_r ξ, with k_r = 1 and σ_r = 0.02 unless stated;
  - **protected coarse code:** r ← r + k_c (B − P4(r)), where B is the taught record's 16 region means, immune to injury (privileged storage); k_c = 0.02 unless stated;
  - **writing from the body**, panel P only: r ← r + 0.05 · gate · (v − r).
- **Events:**
  - **lesion:** flips the sign of an s × s patch of body, record or both;
  - **wound:** flips the body's patch and sets damage tags there;
  - **scar:** holds the body's patch at the wrong sign and keeps its tags set;
  - **record lesion:** flips only the record's patch;
  - **imposition:** overwrites the whole body with the orthogonal message. It is either cued (an explicit instruction that opens a 500-update plastic window) or uncued, and lasts 300 updates or to the window's end;
  - **turnover:** a cell is replaced with probability p per update by a newborn cell (state 0.2·N(0, 1)) whose record entry starts at 0, unless the record is kept outside the cells.
- **Tags** decay with a time constant of 300 updates.

## Panels

| Panel | Question | Regimes (family, σ, body) | Conditions | Arms |
|---|---|---|---|---|
| **L** | Which record designs repair which lesion sizes? | F0 σ 0.1 and 0.3 (c and o); BL σ 0.1 and 0.3 (c); F4 σ 0.3 (c) | sham; {both, record, body} × size {2, 4, 6, 8}, at the start | static, self-correcting, coarse code, both (multi), protected; and multi with k_r 0.5 or 2, k_c 0.005 or 0.08, σ_r 0.05 |
| **P** | Which writing rule adopts a legitimate lasting change but not damage? | F0 σ 0.1 and 0.3 (c and o) | sham, wound, scar, record lesion (6 × 6), cued lasting imposition, uncued lasting imposition, 300-update imposition, at onsets drawn from 100–500 | a self-correcting record with writing gated: never, always (where region mismatch exceeds its threshold), duration latch (no region surprise in the last 500 updates), damage tags (no tag at the site), phase (inside the cued window) |
| **T** | Does turnover make a self-correcting record necessary? | F0 σ 0.05, 0.1 and 0.3 (c); F0 σ 0.1 (o); BL σ 0.1 (c) | turnover p = 0, 0.0003, 0.001, 0.003 per cell per update | inactive (body ignores its record), static, self-correcting, multi, a separate record untouched by turnover, protected |

Every arm runs every condition of its panel for 2,000 updates. Successors (4 recipients, 1,000 updates, the regime's body) read the final record as a static reference.

## Thresholds (public settings)

Panel P's write thresholds were calibrated on engineering blocks 900953–900958 (48 cases), using sham trajectories of the self-correcting record. For each, the per-trajectory maximum over the sheet of region mismatch (P4(r − V-tilde))² and of region surprise (P4(V-tilde − ema))² was taken; the threshold is its 99.5% quantile:

| Regime | mismatch | surprise |
|---|---|---|
| F0_s0.1_c | 0.6327 | 0.01836 |
| F0_s0.3_c | 2.3335 | 0.23864 |
| F0_s0.1_o | 1.0262 | 0.02447 |
| F0_s0.3_o | 2.8604 | 0.25424 |

## Endpoints, analysis and readings

**Endpoints:**
- body qualified agreement and sign agreement at the end;
- record sign agreement;
- record and body sign agreement inside the lesion patch (`les_r`, `les_v`);
- against the imposed pattern in P (`vg_qual`, `rg_sign`, and successors `gR_qual`);
- successors' qualified agreement from the final record (`fR_qual`);
- write L1 in P.

**Analysis:** as ME002. Units are the 16 development blocks (910300–910315), each with 8 cases; contrasts are paired within case, with 95% t intervals and readings at ±0.02. The 25 registered contrasts are in `design.CONTRASTS`.

## Registered statements

| Id | Kind | Claim | Rule |
|---|---|---|---|
| RL1 | replication (P7) | Local redundancy and a coarse code repair complementary lesion sizes: a self-correcting record heals small wounds, a 16-value code heals large ones, and together they heal every size | HOLDS if in both regimes (block means): self >= 0.9 at 2x2 and <= 0.6 at 8x8; code <= 0.1 at 2x2 and >= 0.6 at 8x8; multi >= 0.9 at every size; else FAILS |
| RL2 | design | Multi-scale self-repair keeps the body as well as a full protected copy of the record | HOLDS if the lower bound of every 95% interval (8 contrasts) is above -0.02, else FAILS |
| RL3 | projection | A coarse code cannot restore fine content: for the multi-scale family it adds less repair to large lesions than for half-planes | HOLDS if at each sigma (multi - self) for BL is below (multi - self) for F0 by more than 0.10 (block means), else FAILS |
| RL4 | physics | An open body heals large body wounds that a body with a conserved mean cannot fully heal | HOLDS if at each sigma the open body's les_v exceeds the conserved body's by at least 0.05 (block means), else FAILS |
| RP1 | mechanism | Explicit damage tags separate damage from change where a duration latch cannot: under a permanent scar the tag rule keeps the record while the duration rule adopts the scar; both adopt a cued lasting change | HOLDS if in every regime (block means): write_tags les_r >= 0.9 and write_duration les_r <= 0.5 under scar-6x6; write_tags and write_duration rg_sign >= 0.8 under impose-inf-cued; else FAILS |
| RP2 | mechanism | Every gate has a blind spot: tags adopt an untagged transient change, phase gating cannot adopt an uncued lasting change, and the duration latch rejects the transient but adopts every lasting change, scars included (RP1) | HOLDS if in every regime (block means): under impose-300, write_tags rg_sign exceeds write_duration rg_sign by at least 0.1; under impose-inf, write_phase rg_sign <= 0.6 and write_duration rg_sign >= 0.8; else FAILS |
| RP3 | mechanism | Writing without any gate copies damage into the record | HOLDS if write_always les_r <= 0.5 in every regime (block means), else FAILS |
| RT1 | mechanism | Turnover erases a static tissue-held record; a self-correcting record re-specifies new cells from their neighbours | HOLDS if in each regime static r_sign <= 0.6 and self r_sign >= 0.95 (block means), else FAILS |
| RT2 | mechanism | Under turnover the body keeps its pattern only with a self-correcting record | HOLDS if in each regime the self arm loses less than 0.05 and the static arm loses more than 0.10 (block means), else FAILS |
| RT3 | question | Turnover makes a record necessary even where noise does not: at sigma = 0.05 the record's value to the body grows with turnover | HOLDS if (self - inactive) at turnover-0.003 exceeds (self - inactive) at turnover-0 by at least 0.05 (block means), else FAILS |

## Information boundary

The body sees V-tilde and its record. The record's dynamics see local record values, the body (when writing), and three declared extras:
- the protected coarse code: 16 values of privileged storage;
- damage tags: an explicit, declared signal set by wounds, the biological analogue of damage signals (PROTOCOL §6: an explicit, budgeted cue);
- the instruction cue that opens the plastic window, declared with each cued imposition.

Targets, condition labels and scores reach only the evaluator.

## Qualification

Fixed in `br001/checks.py` before their results, on preflight blocks 900975–900976 at the full shape:
- **Q1** complete and finite;
- **Q2** serial equals parallel;
- **Q3** engine equivalence, bit for bit;
- **Q4** an independent per-site model of five branches, within 1e-9;
- **Q5** exact aliases, including across panels;
- **Q6** reanalysis, including re-reading the saved records;
- **Q7** the reader;
- **Q8** event efficacy;
- **Q9** resources;
- **Q10** the reader dry run, with every git file at 256 KB or less.

Any failure stops the campaign.

## What ran before the freeze (disclosed)

All of it used engineering identities.

- **Probe P6** (blocks 900980–900987). It showed that the two-record vote needs independent damage, and that a global trigger misses local lesions.
- **Probe P7** (blocks 900996–900999). A tissue-held record:
  - the self-correcting record healed 1.00 of 2 × 2 wounds and 0.45 of 8 × 8;
  - the coarse code healed 0.00 and 0.75;
  - both together healed 0.96–1.00 at every size.

  **RL1 is therefore a replication of P7.**
- **A trial calibration and a smoke run** (debug block 900977, one task per panel) checked plumbing only:
  - write activity per rule and condition;
  - turnover counts against their expectation;
  - the protected record staying unchanged;
  - the reader separating target from zero (0.879 against 0.414).

  After the smoke run, the uncued lasting imposition was added so that phase gating's blind spot could be seen.
- **A debug run of the whole pipeline** (debug blocks 900977–900978, 17:43Z) and its checks. Q1–Q9 passed, with the independent replay exact (0.0). Q10 failed on one contrast file at 262,350 bytes, so contrast files were split by endpoint, and the rerun passed. Its verdicts were not opened.

No statement, rule or threshold was changed after reading any contrast or verdict.

## What each outcome would mean

- **L.** If local redundancy and a coarse code repair complementary lesion sizes, multi-scale correction is a necessity once records live in the tissue: consensus for small damage, a protected coarse code for large damage. That is the lane's mathematics (THEORY.md §4) in a biological arrangement, with self-repair through neighbouring records as in intercalation and the community effect, and a coarse code as in Hox and positional memory.
- **P.** If damage tags keep the record under a scar where a duration latch adopts it, explicit provenance marks are what make rewriting safe, as hemimethylated DNA and synaptic tags do. If each gate has a blind spot, biology's combination of marks, cues and windows is the expected design.
- **T.** If turnover erases a static tissue-held record but not a self-correcting one, tissues that renew must keep their positional records in coupled, self-correcting form.
