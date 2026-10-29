# ME001 v2 registration: sensing and acting on errors across scales

**Frozen 24 October 2026 at 23:01:51Z, before any development outcome. Development study, not confirmation.** The design is `me001/design.py`, digest `84686773c639d257d711ea42b370c932cfe9d22f34e23564ba3d469554f410b2`. The source hashes, the arbiter thresholds and the track-B predictions are in `me001/frozen/`, and the commit that adds this file is the freeze. Qualification on engineering identities follows the freeze. The development run starts only if qualification passes. No ME002 run is authorised by this study.

## The question

The lane asks three things (PROTOCOL §1):

1. Which spatial discrepancies can the sheet's sensors detect, at site, region and whole-sheet resolution?
2. What do the resulting corrections do to the body and to its working reference?
3. When do those corrections help the present body and a fresh successor, rather than only reducing mismatch?

ME001 v2 runs the PROTOCOL's development design with the amendments below. Before the run it also registers testable predictions from a soft-mode theory of the sheet (track B).

## What changed from the draft, and why

The engineering probes (ENGINE.md, engineering identities only) motivated these changes.

| Proposed amendment (ENGINE.md) | In ME001 v2 |
|---|---|
| 1. Damage at two or more amplitudes | RMS 0.5 (the draft's, kept), 1 and 2: 27 damage conditions plus sham |
| 2. Release after teaching | 200 updates of the hold route before damage; outgoing capture Q zeroed after |
| 3. Realised mean shift of every injury | Recorded per case with realised RMS, band power, clipping, extrema and sign flips |
| 4. Boundary geometry beside the bands | Body sign agreement on target-boundary sites and interior sites |
| 5. Off-grid targets, content in finer bands | Three target families. **F0** is the aligned half-planes, 100% collective band. **F2** is rolled (2, 2), with boundaries inside 4×4 blocks; its content is 50% fine, 25% regional and 25% collective. **F4** is rolled (4, 4), with boundaries on block edges inside 8×8 quadrants; it is 100% regional, so the sheet sensor cannot see it. |
| 6. Separable sensing and actuation | The 3×3 sensing/actuation factorial uses a sign decision (local majority vote, threshold 0), where pairs are no longer aliases. Message-level noise is deferred. |
| 7. Body surprise among the sensor traces | Mismatch and surprise at site, region and sheet pooling, recorded at 11 instants and as window maxima, for the four traced arms |
| 8. Short early write windows | Write-then-read and wait-then-read with 20-update windows (rate 0.1) beside the draft's 500/500 schedules |
| 9. Qualified agreement and margins primary | Primary endpoints: body qualified agreement at t = 1000 and fresh-recipient qualified agreement. Recognition is secondary. |
| 10. Two noise levels | σ = 0.3 (native; no native memory) and σ = 0.1 (native physics carries part of the memory) |
| 11. Theta convention | Per-block spread U(0.15, 0.30), as in the L15/L17 lineage |
| 12. First decision after damage | Early endpoints at t = 20 and 100. The arbiter's decision in its first 20 updates is scored against the privileged oracle's. |
| 13. Latch window × rate × damage duration | **Deferred to ME002.** Every injury here is abrupt and transient, so a duration manipulation needs a sustained-change family with its own evaluation target. |
| 14. Conventional comparators | In ME001 v2: a change-point arm (the arbiter without its provenance latch), wait arms, protected copy and always-retain (the hold route). The equal-budget comparison belongs to ME002. |

Other differences, all recorded in ENGINE.md:

- Births are message-neutral.
- The theta field's uniform well asymmetry is omitted, because it is dynamically inert.
- No saved native life is available here. The bit-exact legacy replay stands in for it.

## Design at a glance

| | |
|---|---|
| Cohort | 16 development source blocks (910000–910015) × 4 messages × 2 parents = 128 acquired cases, run in all 6 regimes (3 families × 2 noise levels). Primary regime: F0 at σ = 0.3. |
| Pairing | Each stream is addressed by (block, message, parent, phase), never by arm, condition or regime. All arms and regimes of a case share theta, noise and injury fields. |
| Acquisition | Message-neutral birth (0.2 × centred N(0, 1)), then 120 settling updates, then 1,000 imposed-body teaching updates at amplitude 1.2 (L15), then a 200-update release |
| Damage | Sham, plus {body, reference, both} × {fine, regional, collective} × RMS {0.5, 1, 2}. Each case has one unit field per band and target, scaled by RMS. Damaged V and R are clipped to ±2. |
| Window | 1,000 updates per arm from the damaged state. Passive capture Q runs throughout. |
| Successor | Four fresh, message-neutral recipients hold each outgoing packet for 1,000 updates with the native body route. Their births and draws are shared by every packet of the case. |
| Branches | 977 arm-conditions per case, plus 34 packet readings and 202 foreign readings; about 5.7 million sheet updates per case and regime |

## Arms

The window has 41 dynamic arms. Unless stated otherwise each runs all 28 conditions; "single" means sham plus body or reference damage, 19 conditions. *Privileged* marks an arm that uses information the controller may not have.

| Panel | Arms |
|---|---|
| Routes | `inactive` (comparison off, R held); `body_r` (read R, hold it); `reference_r` (R updated from the body, comparison off); `reciprocal_r` (both, in native order). Each at r = site, region or sheet, with sensor and actuator matched. |
| Sign factorial (single) | `sign_s_a` for every sensor s and actuator a: body route, sign decision, threshold 0 |
| Placement (single) | Actuator grid shifted by (1, 1) with the sensor aligned, and the reverse, at region and sheet level |
| Timing | `write500_r` (500 reference-only updates, then 500 body updates with R held); `wait500_r` (500 with comparison off and R held, then the same 500); `write20_r` and `wait20_r` (the same with a 20-update window, writing at rate 0.1). Each at r = site or region. |
| Lesions (single) | `permute_r`: the sensed signal moved by a fixed derangement at its resolution. At sheet level the drawn derangement is the 180° rotation of quadrants, which reverses the left/right and top/bottom contrasts. `reverse_r`: the sign is reversed. |
| Capture | `snapshot`: the body route, with Q written from the window-start body instead of the living body |
| Arbitration | `arbiter_region`: P4b's provenance-gated rule with its constants unchanged. Default is read-and-hold; a burst is triggered by region-pooled mismatch above threshold with no region-pooled surprise in the last 1,000 updates. A burst means 20 updates with comparison off while R is rewritten from the body at rate 0.1, followed by a 200-update refractory period. `changepoint_region`: the same rule without the surprise latch. `oracle_location` (privileged): bursts at once exactly when only R was damaged. |

Packet-only comparators, read without a window:

- `copy_post`: the post-damage R.
- `protected` (privileged): the pre-damage R.
- `target` (privileged): the clean template.
- `zero`: a zero packet. This is also the Q-writing-off control.
- `off_reader`: recipients with comparison off.

Foreign readings use the orthogonal message of the same block and parent, for six arms: inactive, body_site, reciprocal_site, arbiter_region, copy_post and protected. Each is scored against the own target.

Fixed schedules and the snapshot start at the damage instant, so they use the damage time implicitly. The arbiter and change-point arms do not.

## Information boundary

The engine's policy hook gives a controller only V-tilde, the moving average and R. Targets, condition labels, masks, pristine records and scores reach only the evaluator and the privileged arms. The arbiter thresholds are fixed public settings for each family and noise level. They were calibrated on engineering sham trajectories (blocks 900900–900915; P4b's rule) before the freeze:

| Regime | Region-pooled mismatch (per-trajectory max, 99.5%) | Region-pooled surprise (all updates, 99.5%) |
|---|---|---|
| F0_s0.3 | 0.3086 | 0.02193 |
| F2_s0.3 | 0.2111 | 0.02211 |
| F4_s0.3 | 0.3760 | 0.02173 |
| F0_s0.1 | 0.0713 | 0.00177 |
| F2_s0.1 | 0.0527 | 0.00182 |
| F4_s0.1 | 0.0640 | 0.00176 |

## Endpoints

Every endpoint is computed on all 256 sites. The sign convention is x > 0, and amplitude eligibility is |V| > 0.2.

- **Body**, at t = 20, 100 and 1,000: sign, amplitude, qualified agreement, signed margin, mean, the four band errors, and sign agreement on boundary and interior sites.
- **R and Q**: sign agreement and margin.
- **Fresh recipients**, averaged over the four: sign, amplitude, qualified agreement, margin, tie-split recognition, band errors and the 2×2 sign × amplitude table. Foreign readings give sign, amplitude, qualified agreement and margin.
- **Dose**: body and reference L1 and L2 increments, changed sites, and messages per update.
- **Telemetry**: arbiter bursts and the time of the first burst.
- **Traces**: sensor features at the 11 recorded instants, and their window maxima.

## Analysis

- **Units.** Endpoints are paired within case, averaged over a block's 8 cases, and summarised over the 16 block means with a 95% t interval. Cases, messages, recipients and aliases are not independent units. No multiplicity allocation is made, because this is development.
- **Readings.** Positive means better for the first arm. **BENEFIT** if the lower bound is above 0. **HARM** if the upper bound is below 0. **NO MEANINGFUL DIFFERENCE** if the whole interval lies within ±0.02, about 5 of 256 sites. Otherwise **UNDECIDED**, including when a read is missing.
- **Case counts.** Rescues and harms are case differences above +0.02 or below −0.02.
- **Contrasts.** The 75 registered contrasts are listed in `design.CONTRASTS`, in 14 families:
  - routes versus inactive;
  - routes versus the post-damage copy;
  - reciprocal versus hold;
  - resolution;
  - arbitration;
  - timing;
  - sign versus linear;
  - sensing at a fixed actuator, and actuation at a fixed sensor;
  - placement;
  - lesions;
  - capture;
  - storage;
  - the reference-route alias.

  Each is computed for every regime and applicable condition, on both primary endpoints and seven secondary ones.
- **Detection.** Two AUCs per sensor feature, using its mean over t = 1–3 in the inactive arm (with the actuator off and the sensor logged), and over the cases:
  - **injury detection**: damaged cases against the same cases under sham;
  - **information-loss detection**: damaged cases whose damage cost the hold route's successors more than 0.02, against those it did not.
- **Arbiter.** Sham false alarms, bursts by condition, misses where the oracle helps, and agreement of its first decision with the oracle's.

## Track B: soft-mode predictions, frozen before the run

`me001/predict.py` computes a parameter-free quiet-settle + Lyapunov (QSL) predictor on the calibration blocks' acquired states:

- the noise-free 1,000-update relaxation from each damaged start, with R held;
- around the sham state, the stationary covariance of the linearised noisy update (discrete Lyapunov equation on the centred subspace);
- Gaussian probabilities of a sign match, and of qualified agreement, per site.

It covers the inactive route and the hold route at site, region and sheet level, in every regime and condition. The statements, with their arms, endpoints, instants, denominators and rules, are in `frozen/predictions.json`:

- **PB1a**: At sigma = 0.1 the QSL predictor gives the hold routes' body sign agreement within 0.05. Rule: a cell is a hit if |observed - predicted| <= 0.05; HOLDS if hits >= 50% of cells, else FAILS.
- **PB1b**: At sigma = 0.3 the QSL predictor gives the hold routes' body sign agreement within 0.05. Rule: as PB1a.
- **PB1c**: The local theory overpredicts native maintenance at sigma = 0.3 (escape lies outside it). Rule: HOLDS if predicted - observed > 0.20 in all three families, else FAILS.
- **PB2**: The QSL predictor orders the four hold routes correctly. Rule: HOLDS if the predicted difference has the observed sign in >= 80% of decided pairs, else FAILS.
- **PB3**: Projection immunity: a body route whose sensor cannot see a band ignores reference damage in that band (up to the clipping leak). Rule: HOLDS if every point estimate lies within +-0.01, else FAILS.
- **PB4**: Pooled sensors are blind to reference damage in the bands their projection removes; the site sensor sees all of it. Rule: HOLDS if in every regime AUC(region; reference-fine-0.5) <= 0.65, AUC(sheet; reference-fine-0.5) <= 0.65, AUC(sheet; reference-regional-0.5) <= 0.65 and AUC(site; every reference condition with RMS >= 1) >= 0.95.
- **PB5**: Under the hold route the body's errors concentrate on target-boundary sites (soft modes). Rule: HOLDS if |observed block mean - predicted| <= 0.15 in every regime, else FAILS.
- **PB6**: The mean of V is conserved apart from clipping, so no arm corrects the constant band. Rule: HOLDS if <= 0.01 in >= 99% of branch-cases of every arm and regime, else FAILS.
- **PB7**: The held body follows coarse reference errors more than fine ones. Rule: HOLDS if fine < regional < collective in all six regimes, else FAILS; magnitudes are compared with the theory's static transfer and reported, not scored.

Headline theory numbers (sham, t = 1000; full tables for every condition in the JSON):

| Regime | inactive sign (qualified) | body_site sign (qualified) | body_region sign (qualified) | body_sheet sign (qualified) | boundary share of body_site errors | body_site transfer fine / regional / collective | slow modes visible to region / sheet sensors | cases caught mid-flip (inactive, site, region, sheet) |
|---|---|---|---|---|---|---|---|
| F0_s0.3 | 0.852 (0.832) | 0.972 (0.952) | 0.925 (0.904) | 0.900 (0.880) | 0.858 | 0.025 / 0.064 / 0.068 | 0.157 / 0.030 | 6, 1, 0, 1 of 64 |
| F2_s0.3 | 0.855 (0.835) | 0.971 (0.951) | 0.910 (0.888) | 0.867 (0.846) | 0.874 | 0.039 / 0.141 / 0.190 | 0.208 / 0.049 | 2, 0, 2, 4 of 64 |
| F4_s0.3 | 0.853 (0.832) | 0.972 (0.952) | 0.912 (0.892) | 0.883 (0.861) | 0.871 | 0.091 / 0.286 / 0.464 | 0.154 / 0.051 | 4, 0, 2, 0 of 64 |
| F0_s0.1 | 0.895 (0.892) | 0.984 (0.981) | 0.952 (0.949) | 0.936 (0.933) | 0.971 | 0.049 / 0.132 / 0.137 | 0.155 / 0.029 | 7, 0, 0, 1 of 64 |
| F2_s0.1 | 0.892 (0.889) | 0.981 (0.977) | 0.926 (0.923) | 0.886 (0.883) | 0.971 | 0.028 / 0.088 / 0.109 | 0.209 / 0.049 | 4, 2, 4, 8 of 64 |
| F4_s0.1 | 0.896 (0.892) | 0.985 (0.982) | 0.922 (0.919) | 0.897 (0.894) | 0.972 | 0.041 / 0.108 / 0.155 | 0.153 / 0.051 | 4, 0, 4, 5 of 64 |

Read plainly: the local theory expects the held reference to keep 97% of signs at σ = 0.3 and 98% at σ = 0.1, coarser body routes to keep fewer, and the remaining errors to sit on boundary sites. It expects the slow modes to be almost invisible to pooled sensors, and a static reference error to pass into the body more when it is coarse. It also expects the inactive body to keep about 85–90% of signs, which the engineering probes already contradict at sigma = 0.3 (P1: 0.498). PB1c registers that failure in advance as the boundary of a theory that has no barrier escape.

## Qualification and stop rules

The criteria were fixed before their results, in `me001/checks.py`. They run on the preflight engineering blocks 900920–900921 in all six regimes, at the full shape: every arm, condition and case.

- **Q1** Complete and finite.
- **Q2** Serial run equals parallel run, bit for bit.
- **Q3** Bit-exact against legacy `blueprint_step`, for the identity routes and the fresh reader.
- **Q4** An independent per-site loop built on the design fixtures reproduces acquisition, twelve linear arms and a fresh reading, within 1e-9.
- **Q5** Exact aliases: reference_r equals inactive in V, Q and successors; the zero clamp equals inactive; snapshot V equals body_site V; the sham start equals the pre-damage state.
- **Q6** Saved-output reanalysis.
- **Q7** A known-reference reader:
  - in every regime, target-packet fresh sign minus zero-packet fresh sign is at least 0.15;
  - in the primary regime, target fresh sign is at least 0.75 and fresh qualified agreement at least 0.65.
- **Q8** Perturbations change the state:
  - every non-sham condition changes its damaged component in every case and leaves the other untouched;
  - in the primary regime, at RMS 2, some band lowers body_site's body or successor endpoint by at least 0.02, for body damage and for reference damage.
- **Q9** Resources: at most 48 h of wall time, with RAM and disk headroom of 20% or more.
- **Q10** The reader completes on the preflight shards, scores every statement and keeps every git file at 256 KB or less.

If only Q7 fails, and only in a secondary regime, the status is PASS_WITH_FLAGS, and that regime's successor endpoints are reported as reader-unqualified. Any other failure stops the campaign; the failure is kept and reported. A technical fix requires a new freeze with an explicit lineage, and the first attempt stays on record.

**What ran before the freeze (disclosed).** All of it used engineering identities, and none used the reserved preflight blocks 900920–900921 or the development blocks.

- **Smoke run** (block 900990, F0 σ = 0.3, placeholder thresholds). It found a shard-path bug: a reused loop variable. Its sham sanity values were read: hold-route body qualified agreement 0.841, fresh 0.722.
- **First theory pass** (22:40Z). It used the stationary Lyapunov covariance. Its own output showed some quiet states caught mid-flip (spectral radius above 1). That is a property of the theory, not an outcome. The registered method therefore uses the window covariance, recomputed at 22:47Z.
- **Debug run** of the whole pipeline on the unreserved blocks 900990–900991 (22:47–22:53Z), after the thresholds and predictions were written. It fixed the reader's git-summary size and its raw-file handling. It also printed verdicts on those two blocks: PB1b, PB5, PB6 and PB7 failed there. PB5 and PB7 were recomputed directly from the raw states and confirmed, so they are not computing bugs.

No statement, rule, threshold, arm or margin was changed after any of these outputs.

## Execution

- **Hardware and process limits.** The run uses 12 worker processes on the login node's least-busy cores, at nice 10, with one numerical thread each and one worker pinned per core, all on CPU in float64.
- **Tasks and storage.** Each task is one (regime, block) pair, 96 tasks in all. Raw arrays go to the scratch run root, outside git. Each task writes an immutable shard with a hash-checked completion record.
- **Process.** An exclusive run lock prevents two runs at once. The run is detached because it takes over 10 minutes.
- **Refusal rule.** The coordinator refuses development work unless the design digest and source hashes equal the frozen ones and the qualification receipt passes.
- **Stopping and retries.** There is no early stopping, no founder replacement and no tuning while reading. Retries keep the first attempt's manifests.

## What each outcome would mean

PROTOCOL §10 applies unchanged. In addition:

- **Region-triggered arbiter matches the oracle on fresh development blocks and all three families, with no sham harm.** This would support freezing it as the ME002 selector, against the change-point, hold and protected-copy comparators.
- **The change-point arm does as well as the arbiter.** The provenance latch adds nothing here.
- **F4 defeats the sheet routes while region routes keep it.** A sensor's scale bounds the corrections it can drive.
- **QSL fails at σ = 0.3 but holds at σ = 0.1.** The soft-mode picture is a low-noise theory, and the setpoint's work at the lane's noise level is partly nonlinear: holding against escape.
