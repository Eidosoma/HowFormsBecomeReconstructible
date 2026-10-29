# ME002 registration: a wide development screen of multi-scale error correction and setpoints

**Frozen 25 October 2026 at 11:52:43Z, before any development outcome. Development study, not confirmation.** The design is `me002/design.py`, digest `168df67657725e42127c40c106ff298408d071ae2e09307c4c552f71464d766e`. The source hashes, the public settings (thresholds, latch windows, equal-dose gains) and the registered statements are in `me002/frozen/`; the commit that adds this file is the freeze. Qualification on reserved engineering blocks follows the freeze, and the development run starts only if it passes. Nothing here authorises ME003.

## Why a wide screen

ME001 v2 recommended freezing `arbiter_region` unchanged as the single ME002 selector, with fixed-route, local-information, provenance-lesion and storage comparators, and five changes: damage at random onset, a packet that is the record itself, thresholds pooled across families, a sustained-change family and equal-dose sign decisions. The PI's word on 25 October 2026 was "lets go on your recommendations but at this early stage lets be wide rather than narrow in our explorations".

ME002 therefore keeps every recommendation, and ME001's selector with its rule unchanged, but it is not a single confirmatory test. On one fresh cohort it screens six questions about where multi-scale correction and setpoints come from and when they work. Each panel is a development read. A lead found here needs its own frozen confirmation on fresh blocks.

| Panel | Question | Regimes (family, σ, coupling g) | Conditions | Arms |
|---|---|---|---|---|
| **A. Time** | Does provenance-gated rewriting still work when injuries arrive at random times, in sequences, or as a lasting change that should be adopted? | F0 σ 0.3 and 0.1; F4 and BL at σ 0.3; g = 1 | 26 | 14 |
| **B. Coupling** | Does the useful trigger scale follow the scale the body cannot correct by itself? | F0, F4 × σ 0.3, 0.1 × g 0.25, 1, 2.5 | 10 | 9 |
| **C. Breadth** | Where across noise and pattern families does a setpoint pay, and do thresholds transfer to untouched families? | F0, F4, S4, BL, IS × σ 0.05, 0.1, 0.2, 0.3, 0.4 | 8 | 10 |
| **D. Storage** | How many protected values does a body need, and at what resolution? Can two unprotected records voting with the body do what provenance cannot? | F0, F4, BL, IS at σ 0.3; F0 at σ 0.1 | 12 | 6 |
| **E. Voting** | Does majority voting still win at equal correction dose? | F0, F4 × σ 0.3, 0.1 | 10 | 21 |
| **F. Heredity** | Over 8 generations, which policy and packet keeps a form, with and without injuries? | F0, F4, BL at σ 0.3; F0 at σ 0.1 | 3 environments | 10 |

## Design at a glance

| | |
|---|---|
| Cohort | 16 fresh development source blocks (910100–910115) × 4 messages × 2 parents = 128 acquired cases. The same cases run in every panel and regime. Primary regime: F0 at σ = 0.3, g = 1. |
| Pairing | Every stream is addressed by (tag `mse-me002`, block, message, parent, phase), never by arm, condition, regime or panel. All arms of a case share its acquired state, onset, injury fields and future draws; panels share them wherever they share a regime, and qualification checks that they agree bit for bit. |
| Acquisition | As ME001 v2: message-neutral birth, 120 settling updates, 1,000 imposed-body teaching updates of the family template at amplitude 1.2, a 200-update release on the hold route, then Q = 0. Per-block theta spread U(0.15, 0.30). |
| Successors | Four fresh, message-neutral recipients hold each outgoing packet for 1,000 updates on the native body route; their births and draws are shared by every packet of the case. |
| Engine | `mse/` and ME001's code unchanged; ME002's event loop (`me002/sim.py`) applies injuries, impositions and clamps between updates of the unchanged `mse.engine.step`. |
| Cost | About 12 CPU-hours (preflight timing to be recorded by Q9). |

### Target families

Every template is balanced (128 sites of each sign); kinds 2 and 3 are the reversals of 0 and 1; the foreign message is the orthogonal kind.

| Family | Messages | Band content (fine / regional / collective) | Boundary sites |
|---|---|---|---|
| F0 | aligned half-planes (ME001) | 0 / 0 / 1 | 64 |
| F2 | half-planes rolled (2, 2) (ME001; calibration only) | 0.50 / 0.25 / 0.25 | 64 |
| F4 | half-planes rolled (4, 4) (ME001) | 0 / 1 / 0 | 64 |
| S4 | stripes of width 4, four flat walls (new) | 0 / 1 / 0 | 128 |
| IS | half-planes with an off-grid 4 × 4 island of the opposite sign in each half (new) | 0.375 / 0.0625 / 0.5625 | 120 |
| BL | two smoothed random fields (periodic Gaussian, sd 2 sites) thresholded at the median, the second redrawn until the overlap is at most 0.05 (new; address index 4) | 0.49 / 0.24 / 0.26 | 86 |

## Panels in detail

**A. Time** (window 1,800 updates). Each case draws one onset τ uniformly from 100–500. Conditions:

- sham;
- one injury at τ: {body, reference, both} × {fine, regional, collective} × RMS {1, 2};
- two injuries: collective RMS 2 to the reference then the body 10 or 300 updates later, and the reverse;
- an imposition: the body is overwritten with the foreign template before every update for 50 or 300 updates, or until the window ends (the L15 full-field hold; a legitimate change to be adopted only if it lasts).

Arms: `inactive`; `hold_site`; `reciprocal`; `write20_t0` (ME001's fixed early write, now at the window's start, so it no longer knows the onset); `periodic20` (a 20-update write every 450 updates); `changepoint` (no latch); `arbiter_me001` (ME001's rule and calibration method, unchanged); `arbiter` (the same rule with the v2 latch threshold); `arbiter_W300` and `arbiter_W100` (shorter latches); `arbiter_abort` (a burst stops when surprise appears during it); `arbiter_pooled` (thresholds pooled over F0, F2 and F4); `arbiter_site` (site-pooled mismatch trigger, P4's local-information comparator); and the privileged `oracle`. Every arm passes two packets, Q (capture) and R (the record itself). Packet comparators: protected (pre-injury R, privileged), target, foreign target and zero. Fresh endpoints are scored against the own target (f) and the imposed one (g).

**B. Coupling** (window 1,000; injuries at the start as in ME001). Conditions: sham; reference × {fine, regional, collective} × RMS {1, 2}; body × {fine, regional, collective} × RMS 2. Arms: inactive, hold at site, region and sheet resolution, the arbiter with site, region or sheet mismatch triggers, the change-point and the oracle.

**C. Breadth** (window 1,000; start). Conditions: sham; reference and body damage in each band at RMS 2; combined collective RMS 2. Arms: inactive, the three hold routes, reciprocal, `write20_t0` (here at the injury, as in ME001), `arbiter_me001`, `arbiter`, `arbiter_pooled` and the oracle. Packet comparators: post-injury copy, protected, target, zero. S4, BL and IS are untouched by the pooled calibration.

**D. Storage** (window 1,000; start). Conditions:
- sham;
- reference damage in each band at RMS 1 and 2;
- body collective 2;
- combined regional and collective 2 (the body and the first record);
- regional and collective 2 to both records of a two-record arm, with independent fields; a one-record arm receives the first record's field alone, so for it these equal the one-record conditions.

Arms:
- hold;
- hold with a privileged protected backup of the pre-injury R at site (256 values), region (16) or sheet (4) resolution, restoring R's content at that resolution before every update (`clamp_*`);
- the arbiter;
- `dual_vote`: two unprotected working records, both injurable and not privileged. Before every update, in each 4 × 4 region where the records differ, both take the values of the record closer to the current body there (mean square over the region). Records that agree are never touched. The body reads the first record. This is the length-3 repetition code (two records and the body), added on the literature map's evidence that bodies cross-check references (BODIES.md §8.3).

The coarse backups are also read as packets.

**E. Voting** (window 1,000; start). Conditions: sham; body damage in each band at RMS 2; reference damage in each band at RMS 1 and 2. Arms: the three linear hold routes; the 3 × 3 sign factorial at native gain (ME001); and the same at equal dose, where a vote's gain is scaled so that its mean sham body L1 equals the linear hold route's at the coarser of its two levels, capped at the native gain.

**F. Heredity** (chains). The founder lives 2,500 updates from its released state; then 8 generations each begin with a message-neutral newborn that holds the incoming packet as its R and lives 2,500 updates. Each life has one injury at an onset drawn from 1,300–1,700 in two of three environments: none; reference (band drawn uniformly, RMS 2); and mixed (body 0.4, reference 0.4, both 0.2; band uniform; RMS 2). Onset, band and location are addressed per case and generation and shared by every arm and environment. Arms (packet passed on): inactive (Q), hold (Q), hold (R), reciprocal (Q), reciprocal (R), arbiter (Q), arbiter (R), arbiter with W = 300 (R), and two privileged germlines whose packet is the founder's record itself at region (16 values) or full resolution, unchanged by life. A newborn's arbiter latch starts closed for W updates (a developmental latch): without it a newborn would rewrite its inherited record from its own unformed body at update 1 (found in design review).

## Arms and rules

- **The arbiter family.** Default: read R and hold it. Mismatch is the mean square of R − V-tilde pooled at the trigger's resolution; surprise is the mean square of region-pooled V-tilde − ema. A latch of W updates closes after any surprise above its threshold. When mismatch exceeds its threshold with the latch open and no burst or refractory period running, the arm stops reading for 20 updates and rewrites R from the body at rate 0.1, then waits 200 updates (P4b's constants). With trigger region, W = 1,000 and no abort it is ME001's rule update for update (unit-tested).
- **Thresholds** are 99.5% quantiles over engineering sham trajectories of the read-and-hold route on calibration blocks 900930–900945. Mismatch: of per-trajectory maxima over the panel's window. Latch: ME001's rule uses all per-update surprise values over 1,000 updates (`arbiter_me001`); v2 uses per-trajectory maxima over the window. Engineering probe P5 (below) showed that ME001's per-update threshold keeps the latch closed most of the time at sham, which an injury at update 1 never met.
- **The event oracle** (privileged) bursts at each reference-only injury instant, and 20 updates after an imposition that lasts to the window's end. It is an instrument for timing, not a ceiling in sequences.
- **Clamps and germlines** are privileged protected storage, immune to injury by assumption.
- **The two-record vote** is not privileged: its second record (2,048 bytes, declared) is injured like the first, and the vote reads only the two records and the current body. It votes on the body at the moment of the vote, not on the lagging moving average. The lagging average would make the vote's provenance a timing artefact, since it still holds the pre-injury body for the first updates.
- **Equal-dose gains** and every threshold are public constants fixed before the freeze.

## Information boundary

The controller sees V-tilde, the moving average and R, and its own declared counters (latch, burst, refractory). Targets, condition labels, onsets, schedules, masks, pristine records and scores reach only the evaluator and the privileged arms (oracle, clamps, germlines). There is no selection or fitness in ME002.

## Endpoints

- **Body** at the window's end and at the sentinels 20 and 100 updates after the onset: sign, amplitude, qualified agreement, signed margin; in panel A also against the imposed pattern.
- **R and Q**: sign agreement and margin (and against the imposed pattern in A).
- **Successors** from each packet: sign, amplitude, qualified agreement, margin, averaged over the four recipients.
- **Dose**: body and reference L1, clamp L1, messages per update.
- **Telemetry**: bursts, first burst, updates from the first and from the last injury to the first burst after it, the fraction of updates latched, aborts.
- **Chains**: per generation, the body at the end of life, the packet passed on, R and Q, dose and telemetry.

Primary endpoints: body qualified agreement at the window's end (`v_qual`) and successor qualified agreement from Q (`fQ_qual`), plus from R (`fR_qual`) in A and D; in F, `v_qual` per generation and the packet's sign agreement.

## Analysis

As ME001 v2. Endpoints are paired within case, averaged over a block's 8 cases and summarised over the 16 block means with a 95% t interval; no multiplicity allocation (development). Readings: BENEFIT if the lower bound is above 0, HARM if the upper bound is below 0, NO MEANINGFUL DIFFERENCE if the interval lies within ±0.02, otherwise UNDECIDED. Case rescues and harms are case differences beyond ±0.02. The 89 registered contrasts are in `design.CONTRASTS` (families A1–A4, B1–B3, C1–C3, D1–D5, E1–E3, F1), computed in every regime and condition of their panel. Chain contrasts are read at generation 8 and as the mean over generations 1–8 in each environment.

## Track B2 and the registered statements

`me002/predict.py` applies ME001's parameter-free predictor (quiet settle + window covariance; no free parameters) to the new couplings (panel B) and to the new noise levels and families (panel C), on the calibration blocks' acquired states. Statement rules are in `frozen/predictions.json`:

Read plainly, the theory makes three new claims before the run:

- it expects to keep working at low noise and new couplings, and to fail as noise rises (PB8, PB9);
- it expects weakly coupled sites to hold the pattern as independent bistable cells, so that the setpoint's value rises with coupling (PB12);
- against the continuum intuition registered beside it (PB10), it expects the harm of regional reference damage to peak at g = 1 rather than fall with coupling (PB10t).

The other statements are mechanism, projection, coding, design and replication predictions, whose reasoning is in the claim and in the disclosure below.

| Id | Kind | Claim | Rule |
|---|---|---|---|
| PB8 | theory (QSL) | At sigma = 0.1 the QSL predictor gives the hold routes' body sign agreement within 0.05 at the new couplings g = 0.25 and 2.5 | a cell is a hit if \|observed - predicted\| <= 0.05; HOLDS if hits >= 50% of cells, else FAILS |
| PB9 | theory (QSL) | The QSL predictor degrades with noise: its hit fraction falls with sigma and crosses 50% between sigma = 0.1 and 0.3 | h(sigma) = fraction of cells with \|observed - predicted\| <= 0.05; HOLDS if h(0.1) >= 0.5, h(0.3) < 0.5 and h(next sigma) <= h(sigma) + 0.05 for each consecutive pair 0.05 -> 0.1 -> 0.2 -> 0.3 -> 0.4, else FAILS |
| PB10 | physics | Stronger coupling filters coarser reference errors: the harm of RMS-2 reference damage to the held body falls as g rises | a series is monotone if harm(1) <= harm(0.25) + 0.01 and harm(2.5) <= harm(1) + 0.01; HOLDS if >= 6 of 8 series are monotone, else FAILS |
| PB10t | theory (QSL) | The QSL predictor gives the direction in which the harm of fine and regional reference damage changes from g = 0.25 to g = 2.5 | a series agrees if sign(observed harm(0.25) - harm(2.5)) equals the predicted sign (observed differences within +-0.01 count as 0 and agree only with a predicted 0); HOLDS if >= 6 of 8 series agree, else FAILS |
| PB12 | theory (QSL) | A setpoint matters more in a more strongly coupled body: the held reference's gain over no correction rises with coupling | HOLDS if the observed block-mean contrast increases strictly from g = 0.25 to 1 to 2.5 in both families at sigma = 0.1, else FAILS; sigma = 0.3 is reported |
| PB11 | projection | A protected backup only needs the scales the body cannot regenerate: a region-resolution backup (16 values) equals the full backup under regional and collective reference damage, and a sheet-resolution backup (4 values) equals it under collective damage | HOLDS if every one of the 60 paired block contrasts reads NO MEANINGFUL DIFFERENCE (95% interval within +-0.02), else FAILS |
| PD1 | coding | Redundancy does what provenance cannot: two unprotected records that vote with the body repair an injury to the body and one record together, which no one-record arm fixes | HOLDS if the contrast is a BENEFIT under both conditions, else FAILS; dual_vote - clamp_site is reported |
| PA1 | mechanism | Under random onset ME001's unchanged arbiter rarely acts on a coarse reference injury, because spontaneous surprise keeps its latch closed (engineering probe P5); the trajectory-calibrated latch (v2) acts at once | HOLDS if, in every regime and both conditions, arbiter_me001's a_win20 rate <= 0.5 and arbiter's >= 0.9 (fraction of 128 cases), else FAILS |
| PA2 | mechanism | The latch is a duration filter: the v2 arbiter's record adopts a pattern imposed to the end of the window and keeps its own after a 50-update imposition; without a latch (change-point) even the short imposition is adopted | HOLDS if, in every sigma = 0.3 regime (block means), rg_sign >= 0.8 under impose-inf for arbiter, arbiter_W300 and arbiter_W100; r_sign >= 0.8 under impose-50 for arbiter and arbiter_W300; and changepoint's rg_sign >= 0.8 under impose-50; else FAILS |
| PA3 | mechanism | A body injury during a burst is copied into the record; aborting the burst on surprise protects the record | HOLDS if the contrast is a BENEFIT under ref-then-body-10 and NO MEANINGFUL DIFFERENCE under ref-then-body-300, else FAILS |
| PA4 | mechanism | A body injury closes the latch, so a reference injury 10 updates later is not acted on while the latch is closed | HOLDS if, in every regime, for both arms, >= 80% of cases have no burst within W - 50 updates of the reference injury (a_after2 = -1 or a_after2 >= W - 50), else FAILS |
| PC1 | design | Thresholds pooled over the calibration families (F0, F2, F4) transfer to untouched families without false alarms | HOLDS if the sham false-alarm rate (fraction of 128 cases with any burst) is <= 0.05 in each of the three regimes, else FAILS |
| PE1 | design | At equal correction dose the sheet-sensor majority vote still maintains the aligned target better than linear site correction | HOLDS if the contrast is a BENEFIT, else FAILS |
| PF1 | replication | Heredity through body capture decays across generations even without injuries (seen on debug block 900993: 0.75 -> 0.56) | HOLDS if the generation-8 block mean is below the generation-1 block mean by more than 0.05 with the paired 95% interval of (generation 8 - generation 1) below 0, else FAILS |
| PF2 | mechanism | Under a reference injury every generation, in-life provenance-gated repair slows the accumulation that pure copying suffers | d = (arbiter_R gen 8 - gen 1) - (hold_R gen 8 - gen 1), paired by block; HOLDS if the point estimate >= 0.05 and its 95% interval excludes 0, else FAILS |
| PF3 | projection | A protected coarse germline (16 values) keeps aligned coarse targets as well as the full germline, but not multi-scale ones | HOLDS if the contrast reads NO MEANINGFUL DIFFERENCE for F0 and F4 at sigma = 0.3 and HARM for BL at sigma = 0.3, else FAILS |

Headline theory numbers (sham, body sign agreement at t = 1000; F0 unless named):

| Regime | inactive | hold_site | hold_region | hold_sheet | setpoint value (hold_site − inactive) |
|---|---|---|---|---|---|
| F0_s0.1_g0.25 | 0.942 | 0.948 | 0.945 | 0.944 | +0.006 |
| F0_s0.1_g1 | 0.910 | 0.986 | 0.945 | 0.940 | +0.076 |
| F0_s0.1_g2.5 | 0.779 | 0.986 | 0.951 | 0.905 | +0.207 |
| F0_s0.3_g0.25 | 0.743 | 0.867 | 0.793 | 0.789 | +0.124 |
| F0_s0.3_g1 | 0.866 | 0.975 | 0.927 | 0.881 | +0.108 |
| F0_s0.3_g2.5 | 0.765 | 0.962 | 0.933 | 0.894 | +0.197 |
| F0_s0.05_g1 | 0.908 | 0.987 | 0.932 | 0.942 | +0.079 |
| F0_s0.2_g1 | 0.892 | 0.983 | 0.937 | 0.923 | +0.091 |
| F0_s0.4_g1 | 0.798 | 0.956 | 0.898 | 0.869 | +0.158 |
| S4_s0.1_g1 | 0.743 | 0.966 | 0.907 | 0.741 | +0.223 |
| BL_s0.1_g1 | 0.795 | 0.937 | 0.877 | 0.827 | +0.142 |
| IS_s0.1_g1 | 0.761 | 0.916 | 0.807 | 0.768 | +0.155 |

Predicted harm of RMS-2 reference damage to the held body (sham minus damaged sign agreement) at g = 0.25, 1, 2.5:

| Series | g = 0.25 | g = 1 | g = 2.5 |
|---|---|---|---|
| F0_s0.3_fine | 0.106 | 0.062 | 0.030 |
| F0_s0.3_regional | 0.148 | 0.270 | 0.235 |
| F0_s0.1_fine | 0.120 | 0.062 | 0.039 |
| F0_s0.1_regional | 0.181 | 0.278 | 0.257 |
| F4_s0.3_fine | 0.099 | 0.063 | 0.029 |
| F4_s0.3_regional | 0.140 | 0.260 | 0.231 |
| F4_s0.1_fine | 0.121 | 0.062 | 0.037 |
| F4_s0.1_regional | 0.185 | 0.266 | 0.250 |

## Qualification and stop rules

Fixed in `me002/checks.py` before their results, on the preflight engineering blocks 900950–900951 at the full shape (every panel, regime, arm, condition and case):

- **Q1** complete and finite.
- **Q2** serial equals parallel, one task per panel.
- **Q3** bit-exact against legacy `blueprint_step` for the identity routes and the fresh reader, at g = 1 and 2.5.
- **Q4** an independent per-site model built on the design fixtures, with its own event, clamp, vote and arbiter code, reproduces eight branches and a fresh reading within 1e-9.
- **Q5** exact aliases, including bit-for-bit agreement between panels wherever they run the same arm, regime and condition.
- **Q6** saved-output reanalysis, including re-reading saved packets.
- **Q7** the known-reference reader.
- **Q8** perturbation efficacy, including every imposition.
- **Q9** resources: at most 24 h of wall time on 16 workers, with RAM and disk headroom of 20% or more.
- **Q10** the reader completes on the preflight shards, scores every statement and keeps every git file at 256 KB or less.

A secondary-regime failure of Q7 alone gives PASS_WITH_FLAGS. Any other failure stops the campaign and is reported. A technical fix requires a new freeze with an explicit lineage, and the first attempt stays on record.

## What ran before the freeze (disclosed)

All of it used engineering identities. None used the reserved preflight blocks 900950–900951 or any development block.

- **Engineering probe P5** (blocks 900960–900967, tag `mse-me002-p5`, F0 at σ = 0.3 and 0.1, sham only). It measured the latch under ME001's thresholds:
  - closed for 62% of updates 100–500 and 96% thereafter at σ = 0.3;
  - closed for 66% and 94% at σ = 0.1;
  - 86% of cases crossed the per-update surprise threshold by update 500.

  It also read the sham per-trajectory maxima. P5 motivated the v2 latch and PA1. Script and output: `probes/p5_latch_occupancy.py`, `probes/results/p5_latch_v1.json` (rerun 11:36Z, identical).
- **Trial calibration** (10:47Z). Matching the dose of the region-sensor, sheet-actuator vote on F4 would have needed 17.6 times the native gain, because that vote barely acts on F4. Equal-dose gains were therefore capped at the native gain, before any panel E outcome existed.
- **Smoke run** (debug block 900993; one task per panel; trial calibration; 10:49–10:53Z). It found that coarse clamps were not exact no-ops (rounding), so the clamp was rewritten as R + (P(backup) − P(R)). Values read:
  - panel A sham hold: body 0.819, successors 0.742 from Q and 0.832 from R;
  - the reader: target packet 0.932 against zero 0.499;
  - the oracle bursting at its scheduled instants, imposition setting the body to the foreign template, and the clamp alias holding;
  - capture heredity (hold_Q) with no injuries: 0.831, 0.752, 0.688, 0.651, 0.628, 0.588, 0.580, 0.567, 0.561 over generations 0–8. **This is the basis of PF1, which is therefore registered as a replication, not a prediction.**
  - the germline packet's sign 1.0; a newborn arbiter latched for 0.41 of its life; equal-dose body L1 4,319 against hold's 4,295.
- **The theory's output** (first at 11:06Z; recomputed at 11:09Z and 11:33Z after the design changes) was read before PB10t's directions were taken from it and PB12 was added: the theory predicted a rising value of the setpoint with coupling and a non-monotone regional harm.
- **Debug run 1** (debug blocks 900993–900994, the full pipeline, 11:09–11:15Z, after calibration and predictions were written) and its checks. Q1–Q9 passed, with the independent replay exact (maximum difference 0.0). Q10 failed on the size of the git summary (658 KB), so the git copy was trimmed. The reader's dry run computed verdicts on the two debug blocks; they were not opened.
- **Literature map** (BODIES.md, 25 October). Its finding that bodies cross-check references led to the two-record vote (`dual_vote`), its two second-record conditions, contrast family D5 and PD1, added after debug run 1. The design digest changed, the calibration and predictions were recomputed under it, and debug run 2 (11:33Z) and its checks were run: PASS on all ten criteria (11:52Z); only the receipt was read.

No statement, rule, threshold, arm or margin was changed after reading any contrast or verdict. The changes listed above used plumbing values from engineering blocks, calibration values and the theory's output, never a development outcome.

## Execution

16 worker processes on the login node's least-busy cores, at nice 10, one numerical thread each, one worker pinned per core, all on CPU in float64, longest panels first. Each task (panel, regime, block) writes an immutable endpoint shard, a raw-state shard (final states and sentinels, no recipient states) and a hash-checked completion record to the scratch run root, outside git. An exclusive run lock, detached execution, and a coordinator that refuses development work unless the design digest, the sources and the calibration digest equal the frozen ones and the qualification receipt passes. No early stopping, no founder replacement, no tuning while reading.

## What each outcome would mean

- **A.** If the v2 arbiter keeps its benefit under random onset while ME001's rule loses it, the latch must be calibrated to whole trajectories, and ME001's selector carried an implicit onset. If the latch adopts lasting impositions and resists short ones, the latch window is a duration filter, the defend-or-adopt boundary of L15. If a mid-burst body injury is copied into the record unless the burst aborts, the rule has a vulnerable window. If the record packet beats capture under random onset too, copying the record should be the default packet.
- **B.** If the site trigger becomes useful at weak coupling and the sheet trigger at strong coupling, the useful trigger scale follows the body's own correction scale, a mechanism rather than a coincidence of one coupling. If the setpoint's value rises with coupling, cooperative tissues need setpoints more than independent bistable cells do.
- **C.** The phase picture: where in noise and pattern the setpoint and arbitration pay. If pooled thresholds false-alarm on untouched families, thresholds must be calibrated per body plan, or made relative.
- **D.** If 16 protected values do what 256 do under coarse damage, a body only needs to protect the scales it cannot regenerate; a coarse germline is enough for coarse forms.
- **E.** If voting's advantage survives equal dose, it is a decision effect, not a dose effect.
- **F.** If capture-based heredity decays while copying with in-life provenance-gated repair does not, a lineage needs both a copied record and a repair that knows the source; if a coarse germline suffices for coarse forms but not multi-scale ones, heredity must protect exactly the scales the body cannot regrow.
- **Nulls.** A NO MEANINGFUL DIFFERENCE reading bounds an effect within ±0.02. UNDECIDED is not absence.
