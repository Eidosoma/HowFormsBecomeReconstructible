# ME001 v2: development result

**Completed 24 October 2026, 23:59Z. Development study, not confirmation.**

- **Design:** frozen before any development outcome (commit 4f6b39bb9a, digest `84686773c639…`).
- **Qualification:** passed on reserved engineering blocks (receipt 3f178282e6).
- **The run:** 16 development source blocks (910000–910015), 6 regimes, 96 tasks. It took 43.7 min of wall time and 8.6 CPU-hours on 12 cores.
- **Post-run checks:** the independent checks on development block 910000 pass, and the run's sources equal the frozen ones.

Every number below comes from `results/me001_v2/`: `TABLES.md`, the contrast CSVs, `summary.json` and `predictions_scored.json`. The units are source blocks, and intervals are 95% t intervals over 16 blocks. "Benefit" or "harm" means the interval excludes zero. No multiplicity allocation was made, because this is development.

## The arc

The question was where multi-scale error correction and setpoints come from, and when they work. The answers below come from the model and are not claims about biology.

- **When a setpoint helps.** A setpoint is a slow record that a fast, noisy body is pulled toward. It helps only where native physics forgets, and where physics already holds, a damaged setpoint does harm.
- **Every corrector has a scale, and the scale cuts both ways.**
  - **Coarse sensing:** a coarse sensor cannot see or fix errors finer than itself, but for the same reason it ignores reference damage finer than itself.
  - **Nonlinear decisions:** with a nonlinear (majority-vote) decision, the sensor's scale alone sets the outcome.
- **When rewriting is safe.** Rewriting the setpoint from the body is safe only with provenance, meaning evidence of which source moved, at the scale the body cannot correct itself. Gating on provenance matched or beat a privileged oracle in all six regimes. Without it, the same rule copied damage from the body into the record.
- **What theory and storage add.**
  - **A local soft-mode theory**, frozen before the run, predicts the low-noise regime quantitatively and fails at the lane's native noise level. There, the setpoint's work is partly nonlinear: holding the pattern against noise-driven escape.
  - **Storage:** a protected copy still beats every live mechanism. In this apparatus, copying the reference beats capturing the body.

## What we learned

### 1. A setpoint is needed exactly where physics forgets

- **At σ = 0.3**, the native body keeps only 0.434 of sites qualified by t = 1000. With the held reference it keeps 0.826, and the successors read 0.721 against 0.437 (body_site − inactive: +0.392 for the body, +0.284 for successors, 16 of 16 blocks).
- **At σ = 0.1**, physics keeps 0.822 by itself, and the reference adds only +0.108 for successors. With reference damage at RMS 2, reading the reference **harms** successors relative to ignoring it: −0.140 for regional and −0.208 for collective damage. It still helps after collective body damage (+0.318).

The value of reading a setpoint therefore changes sign with noise. That is the phase picture from P2, now measured on fresh blocks.

### 2. Every corrector has a scale, and the scale cuts both ways

- **Resolution costs robustness.** With an intact reference and the aligned family F0, finer body routes maintain better: site 0.826, region 0.767, sheet 0.751. Region minus site is −0.058 and sheet minus site is −0.075, both harms in 16 of 16 blocks.
- **Coarseness buys immunity.** A route whose sensor cannot see a band ignores reference damage in that band, up to the small leak that clipping causes. Prediction PB3 holds: the largest change over 36 block-mean contrasts is 0.0007. Under regional reference damage at RMS 2, the sheet route beats the site route (+0.038 for the body, +0.044 for successors, 16 of 16 blocks). At σ = 0.1 the margin is +0.12 to +0.16 for the body.
- **A target finer than the sensor is invisible.** F4 is entirely regional-band. Under the sheet route it fares the same as no correction at all: 0.437 against the inactive arm's 0.441, a difference of −0.004 with 8 of 16 blocks positive. The region route keeps it at 0.773.
- **Misalignment degrades coarse routes.** F2's boundaries fall inside the pooling blocks. The sheet route drops to 0.563 and the region route to 0.683, while the site route holds at 0.832.
- **Grid alignment matters.** Shifting the sensor grid or the actuator grid by one site harms the body in every condition shown. The cost in sham is −0.044 to −0.073, and shifting the sensor costs more than shifting the actuator.
- **Placement and sign carry the information.** The fixed derangement costs −0.33 to −0.73 for the body in sham; the sign reversal costs −0.73 to −0.78. At sheet level the drawn derangement is a 180° rotation of the quadrants, which acts as a reversal for half-plane targets (−0.733 for both).

### 3. With a majority vote, the sensor's scale decides

The 3×3 factorial used a sign decision (threshold 0), which removes the linear aliases. Values are body qualified agreement at t = 1000, sham, F0 at σ = 0.3.

| Sensor \ actuator | site | region | sheet |
|---|---|---|---|
| site | 0.863 | 0.784 | 0.765 |
| region | 0.877 | 0.877 | 0.865 |
| sheet | 0.884 | 0.884 | 0.884 |

- **Coarse sensors make the actuator irrelevant.** After a coarse sign decision the signal is already constant at that scale, so finer actuators reproduce it exactly, for balanced targets. The region-sensor and sheet-sensor arms have identical trajectories across actuators.
- **Coarse voting beats linear site correction on the aligned target.** The sheet vote reaches 0.884, against 0.826 for linear site correction. It is also immune to regional reference damage: 0.762, against 0.596 for the site-sensor vote.
- **But a coarse vote is blind to what it cannot see.** On F4 it reaches only 0.435.
- **Caveat: dose.** The sign arms deliver about 1.5 times the body correction (body L1 9,912 against 6,608). An equal-dose comparison is needed before calling voting better.

### 4. Provenance makes rewriting safe

- **The arbiter.** `arbiter_region` is P4b's rule with its constants unchanged. It reads and holds R. It rewrites R from the body for 20 updates when region-pooled mismatch appears with no region-pooled body surprise.
- **Primary-regime successors** (F0, σ = 0.3):

| Condition | Arbiter minus hold | Blocks | Case rescues / harms (of 128) |
|---|---|---|---|
| Regional reference damage, RMS 2 | **+0.070** | 16/16 | 103 / 4 |
| Collective reference damage, RMS 2 | **+0.108** | 14/16 | 88 / 36 |
| Collective reference damage, RMS 1 | **+0.032** | 10/16 | 67 / 53 |
| Sham, body damage, combined damage | 0.000 or −0.001 | — | — |

  Across all 28 conditions in all six regimes, the arbiter matched the privileged location oracle or beat it. It beat it under weak fine reference damage (RMS 0.5–1), by up to +0.075 for successors and +0.12 for the body. There the oracle knows only that R was damaged, and its rewrite costs, because the body already filters fine damage. The arbiter's pooled sensor abstains. The one exception is −0.004 for the body under fine damage at RMS 2, at σ = 0.1. Knowing which source was damaged is not enough; the useful trigger also knows the damage's scale. This is P4b's lesson, now on fresh blocks.
- **Across regimes**, regional and collective reference damage at RMS 2 give a benefit in all six:
  - +0.069 to +0.108 at σ = 0.3;
  - +0.224 to +0.293 at σ = 0.1, where the arbiter also gains +0.04 under fine damage.
- **Telemetry.**
  - **Sham false alarms:** 1 of 128 cases.
  - **Coarse reference damage:** it bursts at update 1 in 99.2% of cases, and misses 1 of 104 and 1 of 89 cases where the oracle helps.
  - **Fine reference damage:** it never bursts, because its pooled sensor is blind by projection. There the oracle's rewrite would gain nothing (arbiter − oracle +0.008, not meaningful).
- **First-decision sentinel** (amendment 12). There is no early harm: at t = 20 and t = 100 the arbiter equals hold in sham and under body or combined damage. Under regional reference damage it is already ahead at t = 20 (+0.013) and at t = 100 (+0.072).
- **Without provenance.** `changepoint_region` is the same rule with the surprise latch removed. It rewrites from damaged bodies: −0.206 under collective body damage and −0.191 under regional body damage. It also raises a sham false alarm in 5.5% of cases. The surprise gate is what makes the rule safe.
- **What disagreement cannot settle.** When body and reference are both damaged, the arbiter and the oracle both do nothing. No live arm rescues those cases; only protected storage does. This is PROTOCOL §6's limit, now observed rather than assumed.

### 5. Copying beats capture, and protected storage beats everything

- **Copy versus capture.** The post-damage R, copied directly as the packet, gives successors 0.828 in sham. A packet captured from the held body (the L17 boundary) gives 0.721. The body is a noisy copy of R, so capture loses 0.107 in sham, and 0.046–0.128 across the conditions shown (harm in 16 of 16 blocks in each).
- **Arbiter versus copy.** The arbiter beats the copy only under collective reference damage at RMS 2 (+0.061). Under regional damage at RMS 2 the difference is +0.021 and undecided.
- **Protected storage.** The privileged pre-damage R beats the post-damage copy by +0.13 to +0.26 under reference damage.
- **Snapshot.** The snapshot arm writes Q from the window-start body. It gains +0.072 to +0.195 under reference damage and loses −0.15 to −0.17 under body damage. Its timing coincides with the damage onset, so part of its gain is privileged timing.

### 6. Present and successor effects separate

- **Waiting.** Waiting 500 updates before reading leaves no trace in the body at t = 1000 (0.000). It still costs successors −0.070, because Q captured an unmaintained body.
- **Reciprocal writing** costs −0.115 for the body and −0.049 for successors in sham at σ = 0.3. At σ = 0.1 under reference damage it helps a little (+0.03 to +0.04), because there the body is the better source.
- **Writing windows.**
  - The short early write (20 updates at rate 0.1) helps only when R is the damaged source: +0.070 and +0.109 under coarse reference damage. It costs −0.075 in sham and −0.21 under collective body damage.
  - The draft's 500-update write harms in every condition (−0.015 to −0.128), because it writes from a decaying body.

### 7. Detecting an injury is not detecting lost information

Detection was measured with the actuator off and the sensor logged, over updates 1–3:

- **Site-level mismatch** detects every reference injury at RMS 1 or more (AUC 1.00).
- **Pooled mismatch** is blind to reference damage in the bands its projection removes (primary regime: AUC 0.48–0.49 at RMS 0.5; PB4 holds in all six regimes). At RMS 2 it reads fine damage *backwards* (AUC 0.05 for region pooling, 0.00 for sheet pooling): clipping shrinks R's coarse content, so pooled mismatch falls.
- **Body surprise** detects body damage (AUC 1.00 at RMS 2), including damage with no lasting consequence. Only 61 of 1,152 body-damaged cases cost successors more than 0.02.
- **Information-loss detection** is only moderate: AUC 0.70–0.79 for body damage, 0.56–0.80 for combined damage and 0.40–0.75 for reference damage.

### 8. The soft-mode theory works at low noise and fails at the lane's noise level

Track B's predictor, quiet-settle + window covariance, was frozen before the run and has no free parameters.

| Statement | Verdict | What it says |
|---|---|---|
| PB1a | **HOLDS** | At σ = 0.1, 241 of 252 hold-route cells are within 0.05 (median error 0.016) |
| PB1b | **FAILS** | At σ = 0.3, 24 of 252 cells are within 0.05 (median error 0.091) |
| PB1c | **HOLDS** | The pre-registered failure: theory overpredicts the unaided body at σ = 0.3 by 0.35 in each family |
| PB2 | **HOLDS** | The predicted ordering of the four hold routes matches 868 of 933 decided pairs (93%) |
| PB3 | **HOLDS** | Projection immunity (largest change 0.0007) |
| PB4 | **HOLDS** | Pooled sensors are blind to bands their projection removes; the site sensor sees everything |
| PB5 | **FAILS** | Boundary share of errors at σ = 0.3: 0.55 observed, 0.86–0.87 predicted. At σ = 0.1: 0.96–0.97 observed, 0.97 predicted. |
| PB6 | **FAILS** | At σ = 0.3, clipping moves the mean of V by more than 0.01 in about 5% of hold-route cases, and in up to 48% of cases under the reversed site arm. Every arm meets the bound at σ = 0.1. |
| PB7 | **FAILS** | The ordering of transfer to the body (fine < regional < collective) holds in 5 of 6 regimes; F0 at σ = 0.1 inverts regional and collective (0.224 against 0.212). For F0 at σ = 0.3 the observed transfer is 2 to 4 times the static linear value; for F4 it is below it. |

What this means: at σ = 0.1 the setpoint steers soft boundary modes and the linear theory describes it. At σ = 0.3, nearly half of the errors are in the bulk, away from boundaries. There the reference is holding the pattern against noise-driven escape, which a local theory cannot see. Three of the four failures are at σ = 0.3. PB7 fails on a single inversion at σ = 0.1.

## Harms, gaps and caveats

- **Case-level harms.** The arbiter's benefit under collective reference damage includes 36 harmed cases of 128 at RMS 2, and 53 at RMS 1.
- **Onset alignment.** All damage is abrupt, single-onset, and lands right after release. Fixed schedules and the snapshot know the onset implicitly.
- **Family-specific thresholds.** The arbiter's thresholds are public settings calibrated on sham trajectories for each family and noise level. Whether one pooled threshold works across families is open.
- **One apparatus.** One sheet size, one coupling, three target families; aliases are counted once.
- **Recognition saturates** (0.992 for the hold route, 1.000 for copies), so it was rightly secondary. Successor differences are carried by sign (fresh sign 0.792 against amplitude 0.874 for hold in sham), not amplitude.
- **Specificity.** Own-history specificity is large. Successors scored against their own target read 0.721 for hold and 0.828 for copies. Matched foreign packets read 0.435–0.449, a baseline near chance.
- **Deferred.** Message-level noise (amendment 6) and damage duration (amendment 13) were deferred.

## Advancement recommendation

**Freeze `arbiter_region` unchanged as the single ME002 selector**, on fresh blocks. It is the only arm that:

- matches or beats the privileged location oracle;
- helps under coarse reference damage in every regime;
- does no measurable harm in sham, body damage or combined damage, including at the first decision.

Comparators:

- **Strong fixed routes:** hold (`body_site`), the best fixed route without reference damage; and `write20_site`, the best fixed route with it.
- **Local-information comparator:** P4's site-triggered rule. It was harmful in engineering and is untested here.
- **Provenance lesion:** `changepoint_region`.
- **Packets:** the post-damage copy, protected storage (privileged) and the snapshot.
- **Equal-budget accounting**, reported per case:

| Arm | Reference L1 | Messages per update (nominal) | Retained state |
|---|---|---|---|
| Arbiter | 54.6 | 512 | 3 counters per case |
| Change-point | 169 | 512 | 3 counters per case |
| Fixed early write | 255 | 256 | none |
| Hold | 0 | 256 | none |
| Snapshot | — | — | adds 2,048 bytes |
| Protected copy | — | — | adds 2,048 bytes |

ME002 needs five changes that this study exposed:

1. Damage at random onset times, so fixed schedules lose their implicit onset knowledge.
2. A variant whose packet is the final R as well as Q, because copying beat capture.
3. One threshold pooled across families, beside the family-specific ones.
4. A sustained-change family, for amendment 13.
5. Equal-dose sign decisions.

Registered conclusions where there is no policy:

- **Combined damage:** no permitted signal identifies the trustworthy source.
- **Fine reference damage at σ = 0.3:** there is nothing to fix. The body filters it, and rewriting does not help.

ME002 is not launched; it needs its own freeze and the PI's word.

## Manuscript handoff

For §7.3 / SI P.1, without changing any existing verdict. In a supplied reference sheet:

- **When a setpoint helps.** A setpoint helps where native dynamics forget (σ = 0.3) and hurts when it is corrupt where native dynamics hold (σ = 0.1).
- **Scale.** A corrector's scale bounds both what it can repair and what damage it can ignore. Majority voting makes the sensing scale decisive.
- **Provenance.** Rewriting a setpoint from the body helps only when local body surprise attributes the change to the record. Disagreement alone cannot do it.
- **Storage.** A protected copy remains strongest, and a direct copy of the record beats capture from the body.
- **Theory.** A parameter-free soft-mode theory, frozen in advance, predicts the low-noise regime, 241 of 252 cells within 0.05. Its failure at native noise locates the regime where the setpoint does nonlinear work.

All of this concerns a supplied model with supplied sensors, actions and references. It identifies no biological comparator.

## Reproduction, checks and files

- **Freeze:** `REGISTRATION.md` and `me001/frozen/` (design and source hashes, thresholds, predictions, qualification receipt).
- **Run:** `python -m me001.run --stage development` after the qualification receipt. Read it with `python -m me001.analyze` and `python -m me001.tables`.
- **Independent checks:**
  - Qualification Q1–Q10 on engineering blocks: legacy bit-exact 26/26; independent replay 4e-15; aliases 31/31; serial = parallel; reanalysis exact.
  - The post-run receipt `results/me001_v2/postcheck_receipt.json`, on development block 910000: legacy bit-exact, independent replay, aliases, reanalysis, sources equal frozen.
- **Committed tables:** `results/me001_v2/`, containing:
  - the contrasts for each regime and primary endpoint;
  - `blocks_F0_s0.3.csv` (per-block values);
  - `summary.json`, `predictions_scored.json`, `TABLES.md` and the post-run receipt.
- **Kept in scratch:** the raw states (14.35 GiB), the per-case tables and the full summary, all in `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/me001_v2/development/`. The packets saved there are the records ME003 would restore.
