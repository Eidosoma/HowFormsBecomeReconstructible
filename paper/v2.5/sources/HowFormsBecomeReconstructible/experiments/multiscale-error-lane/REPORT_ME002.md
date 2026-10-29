# ME002: development result of the wide screen

**Completed 25 October 2026, 13:06Z. Development screen, not confirmation.**

- **Design:** frozen before any development outcome (commit 27c5b23bec, 11:52:43Z, digest `168df676…`; REGISTRATION_ME002.md).
- **Qualification:** passed on reserved engineering blocks (receipt 7fe007abf5, 12:12Z). The independent per-site model reproduced every replayed branch exactly (maximum difference 0.0).
- **The run:** 16 fresh development blocks (910100–910115), 54 panel-regimes, 864 tasks. It took 53.6 min of wall time and 12.4 CPU-hours on 16 cores.
- **Post-run check:** passes on development block 910100 (`results/me002/postcheck_receipt.json`): independent replay, legacy bit-exact, aliases, reanalysis, and the run's sources equal to the frozen ones.

Every number below comes from `results/me002/`: `TABLES.md`, the contrast CSVs, `summary.json` and `predictions_scored.json`. Contrasts are paired within case and summarised over the 16 block means with 95% t intervals. "Benefit" and "harm" mean the interval excludes zero. Successor values are fresh recipients reading the packet named, Q (the body's passive capture) or R (the record itself). There is no multiplicity allocation, because this is development.

## The arc

ME001 found that a setpoint helps where physics forgets, that every corrector has a scale, and that rewriting a record is safe only with provenance. ME002 asked whether these survive a wider world: injuries at random times, couplings and noise levels never tried, new pattern families, redundancy, equal correction effort and many generations. In plain words:

1. **Provenance-gated rewriting works at random times, once its latch is calibrated.** ME001's rule needed its injuries to arrive at update 1. With injuries at random times its latch was closed 82% of the time, so it acted on only 34–44% of injuries. Recalibrated against whole trajectories (v2), the same rule acts on 98–100% and matches the privileged oracle.
2. **The latch is a duration filter, and so it cannot tell a lasting change from lasting damage.** It adopts a pattern imposed for good and resists one imposed for 50 updates. But after a body injury that clipping makes partly permanent, the quiet, changed body looks like a lasting change, and the rule copies it into the record. Aborting a burst when the body moves mid-burst fixes the other vulnerable case.
3. **Which damage is worth repairing, and which trigger can see it, follows the body's own coupling.** In a weakly coupled body, fine record damage matters and only a site-level trigger sees it. In a strongly coupled body the coupling erases fine damage. The parameter-free theory predicted in advance how the harm of regional damage depends on coupling, where the continuum intuition registered beside it was wrong.
4. **A setpoint pays most where physics forgets but correction can still hold.** Arbitration pays most at low noise and turns harmful when the body is too noisy to be a faithful copy.
5. **Redundancy does what provenance cannot.** Two unprotected records that vote with the body nearly match a protected copy, and they repair injury to the body and a record together, which no one-record arm can.
6. **Protection need only cover what the body cannot regrow.** Sixteen protected values do what 256 do for coarse forms. Multi-scale forms need the full record, because clipping lets coarse damage reach fine content.
7. **Heredity.**
   - Capture loses information every generation, and copying the record does not.
   - Under a record injury in every life at native noise, every live strategy decays toward chance and only protected storage holds the lineage.
   - In-life repair keeps lineages well only at low noise.
8. **Voting's advantage in ME001 was dose.** At equal correction effort no majority vote beats its linear counterpart in sham.

## What we learned

### A. Time: random onset, sequences and lasting change

Primary regime F0 at σ = 0.3. The four regimes are F0 σ 0.3, F0 σ 0.1, F4 σ 0.3 and BL σ 0.3; successors from Q unless stated.

| Contrast | Coarse reference injury (regional / collective, RMS 2) | Collective body injury | Combined collective |
|---|---|---|---|
| v2 arbiter − hold | +0.082 / +0.119; across regimes +0.065 to +0.290 | −0.017 (−0.009 to −0.017) | −0.014 (−0.009 to −0.020) |
| ME001's arbiter − hold | +0.033 / +0.044; across regimes +0.021 to +0.122 | −0.001 | −0.007 |
| v2 arbiter − oracle | −0.001 / −0.001 (within 0.005 everywhere) | −0.017 | −0.014 |
| change-point − hold | +0.082 / +0.119 | −0.201 | −0.031 |

- **The latch mechanism, measured.** In sham, ME001's per-update threshold kept its latch closed for 82% of the window. It burst within 20 updates of a coarse reference injury in 34–44% of cases (PA1). The v2 latch was never closed in sham, false-alarmed in 3.1% of cases, and burst at once after every coarse reference injury.
- **The cost of the v2 latch.** After a collective body injury the v2 rule rewrote the record in 31% of cases, about 1,010 updates later, as its latch expired. Clipping had shifted the body's mean, which the native dynamics cannot restore (P1). So the body was quiet but changed, and the rule wrote it into the record. Successors pay −0.009 to −0.017 from Q and −0.025 to −0.062 from the record packet. Shorter latches rewrite sooner and cost more. ME001's rule avoided this only because its latch almost never reopened.
- **Duration filtering (PA2).**
  - A pattern imposed to the end of the window was adopted by the record for every latch length (R sign agreement with the imposed pattern 1.00).
  - A 50-update imposition was resisted (0.99 with the own target).
  - Without a latch, even 50 updates were adopted (0.99).
  - With W = 100, a 300-update imposition was adopted (−0.285 for successors scored against the old target), as the filter's length implies.
- **The vulnerable window (PA3).** A body injury 10 updates into a burst is copied into the record. Aborting the burst when surprise appears saves +0.074 for Q successors and +0.080 for R (+0.056 to +0.151 across regimes); it changes nothing when the injuries are 300 updates apart. A body injury closes the latch, so a reference injury 10 updates later is not acted on while it stays closed (PA4: 98–100% of cases).
- **Fixed schedules lose without onset knowledge.** A 20-update write at the window's start costs −0.035 to −0.072, and a periodic write every 450 updates −0.055 to −0.279.
- **Variants.**
  - Thresholds pooled over F0, F2 and F4 equal the regime's own for these families.
  - A site-level trigger equals the region trigger at g = 1.
  - Reciprocal writing harms at σ = 0.3 (−0.084 to −0.089 in sham) and helps at σ = 0.1 under coarse record injury (+0.039 to +0.047), as in ME001.
- **Copy beats capture again.** In sham, successors read 0.836 from the record and 0.756 from capture (ME001: 0.828 and 0.721).

### B. Coupling: the useful trigger follows the body's correction scale

Successors from Q, hold as the reference, couplings g = 0.25 / 1 / 2.5.

| | Fine record injury, σ 0.1 | Regional record injury, σ 0.3 | Setpoint value (hold − none, body sign), σ 0.1 |
|---|---|---|---|
| oracle − hold (F0) | +0.156 / +0.042 / −0.002 | −0.016 / +0.081 / +0.121 | 0.127 / 0.132 / 0.233 (F0); 0.126 / 0.131 / 0.235 (F4) |
| site trigger − hold | +0.156 / +0.042 / −0.002 | −0.016 / +0.081 / +0.121 | |
| region trigger − hold | 0.000 / +0.041 / −0.002 | −0.016 / +0.081 / +0.121 | |
| sheet trigger − hold | +0.006 / +0.042 / −0.002 | 0.000 / −0.001 / +0.010 | |

- **The mechanism.**
  - In a weakly coupled body (g = 0.25), fine record damage passes into the body. Repairing it is worth +0.156 at σ = 0.1, and only the site-level trigger sees it. P4's local rule, harmful at g = 1, is the right one there.
  - As coupling rises, the body's own line tension erases fine damage, and there is nothing left to repair at g = 2.5.
  - The harm of fine record damage to the held body falls monotonically with coupling in all four fine series.
- **Rewriting is only as good as the body.** At σ = 0.3 and g = 0.25 every rewrite harms, the oracle's included (−0.008 to −0.024): the weakly coupled noisy body is a worse copy than a damaged record. A trigger that cannot see the damage wins by abstaining.
- **Theory against intuition.**
  - The physics claim (PB10), that harm falls with coupling in both bands, FAILS: the regional harm peaks at g = 1 (F0 σ 0.3: 0.141, 0.221, 0.216).
  - The parameter-free theory had predicted exactly that non-monotone shape (PB10t, 6 of 8 series HOLD), because lattice-pinned walls at weak coupling resist coherent regional pulls.
  - The theory also predicted that a setpoint's value rises with coupling (PB12 HOLDS), though it overestimated how well a weakly coupled body holds the pattern alone (predicted gain 0.006, observed 0.127).
  - Its accuracy at the new couplings is 61% of cells within 0.05 (PB8 HOLDS).

### C. Breadth: the phase picture across noise and families

| Block-mean contrast (25 regimes) | σ 0.05 | 0.1 | 0.2 | 0.3 | 0.4 |
|---|---|---|---|---|---|
| Setpoint value, body (hold − none, sham), F0 | +0.080 | +0.133 | +0.318 | +0.407 | +0.269 |
| same, S4 (four walls) | +0.234 | +0.361 | +0.407 | +0.319 | +0.213 |
| Arbitration value (v2 − hold, collective record injury, successors), F0 | +0.289 | +0.286 | +0.252 | +0.115 | −0.015 |
| same, IS | +0.214 | +0.203 | +0.160 | +0.056 | −0.016 |
| Coarse immunity (sheet − site route, regional record injury, body), F4 | +0.204 | +0.162 | −0.002 | −0.182 | −0.145 |

- **A setpoint's value is non-monotone in noise.** It is small where physics holds, peaks where physics forgets but correction still holds, and falls when noise overwhelms both. More walls (S4) move the peak to lower noise.
- **Arbitration's value falls with noise** and is harmful at σ = 0.4 in every family. A record rewritten from a body that noisy is worse than a damaged one.
- **Coarse immunity against resolution.** A coarse route's blindness to regional record damage wins where physics holds (+0.15 to +0.20) and loses where it forgets.
- **The linear theory's domain (PB9 HOLDS).** Its hit fraction is 1.00, 0.91, 0.76, 0.41 and 0.28 at σ = 0.05 to 0.4, crossing 50% between 0.2 and 0.3, where native memory is lost.
- **Pooled thresholds transfer only to similar body plans (PC1 FAILS).** Sham false alarms on untouched families: S4 52% (twice the walls), IS 3.9%, BL 0.8%. Thresholds must scale with a body plan's wall density, as the calibration had warned.

### D. Storage and redundancy

| Successors from Q | One record injured (regional / collective) | Body and record injured (regional / collective) | Both records injured (collective) |
|---|---|---|---|
| two-record vote − hold | +0.153 / +0.191 (+0.107 to +0.307) | +0.098 / +0.111 (+0.067 to +0.174) | +0.124 (+0.073 to +0.232) |
| two-record vote − full protected backup | −0.005 / −0.005 | −0.057 / −0.066 | −0.072 |
| two-record vote − v2 arbiter | +0.072 / +0.076 | +0.098 / +0.101 | +0.009 |

- **Redundancy beats provenance (PD1 HOLDS).**
  - Under combined collective injury the vote rescues 85 cases and harms 28 (16 of 16 blocks); under combined regional injury, 120 and 2.
  - With one record injured, two unprotected records come within 0.005 of protected storage and beat rewriting from the body.
  - The vote never acts when the records agree, so body-only injury costs it exactly nothing.
- **Coarse protection** (PB11 FAILS as registered; the substance is mixed):
  - For aligned coarse forms (F0, F4), a 16-value region backup equals the 256-value backup within 0.002 under regional and collective damage. It is in fact slightly better (+0.0007 to +0.002), with intervals so tight that they read BENEFIT, not "no meaningful difference".
  - For the multi-scale families it is short by −0.005 to −0.042 (BL, IS).
  - Under fine damage every coarse backup is short by −0.018 to −0.074.
  - A 4-value backup equals the full one only for collective damage to F0.
- **Coarse packets.** As successors' packets, 4 protected values carry F0 (+0.004 versus the full record) and 16 carry F4 (+0.004). BL loses −0.103 and IS −0.069.

### E. Equal-dose voting

- **ME001's apparent advantage was dose (PE1 FAILS).** Gains scaled so that a vote delivers the same body correction as its linear counterpart (κ ≈ 0.39 for the sheet vote at σ = 0.3) erase it. The sheet-sensor vote is −0.085 below linear site correction in sham (all 128 cases worse) and within 0.006 of the linear sheet route.
- **At equal dose the site and region votes are worse than linear in sham** (−0.077 to −0.088 and −0.031 to −0.037).
- **One exception:** under regional record injury at σ = 0.1, the equal-dose site and region votes beat linear correction by +0.15 to +0.17.

### F. Heredity over eight generations

Body qualified agreement at the end of each life, F0 at σ = 0.3; mean over generations 1–8 in brackets.

| Lineage | no injuries, gen 1 → 8 | record injury every life | mixed injuries |
|---|---|---|---|
| none (Q) | 0.430 → 0.431 | — | — |
| hold, capture (Q) | 0.765 → 0.581 | 0.528 → 0.443 | 0.595 → 0.437 |
| hold, copy (R) | 0.840 → 0.836 | 0.542 → 0.448 | 0.625 → 0.457 |
| v2 arbiter, copy (R) | 0.830 → 0.820 | 0.628 → 0.452 (+0.030 over copy) | 0.658 → 0.464 |
| protected germline, 256 values | 0.840 → 0.836 | 0.645 → 0.628 | 0.719 → 0.671 |
| protected germline, 16 values | 0.845 → 0.839 | 0.645 → 0.629 | 0.721 → 0.672 |

- **Capture is a lossy channel (PF1 HOLDS, a replication).** It loses −0.184 over generations 1–8 even without injuries, and still decays at σ = 0.1 (0.958 → 0.909). Copying the record loses nothing without injuries.
- **Under a record injury in every life, every live strategy decays toward chance at σ = 0.3.** In-life repair helps a little on average (+0.017 to +0.030 over generations 1–8) but not in slope. PF2 FAILS as registered: the repaired lineage starts higher and falls further, because each repair rewrites the record from a noisy body. At σ = 0.1 repair keeps lineages far better (+0.353 over copying alone), because there the body is a faithful copy.
- **Protection is what holds a lineage.** The protected germline holds 0.63–0.67 at σ = 0.3 against 0.44–0.46 for copying alone.
- **Germline resolution (PF3 FAILS as registered).** A 16-value germline is as good as the full one for F0 and F4, and slightly better (+0.004 BENEFIT, a denoised record). It is worse for the multi-scale BL (−0.103): coarse forms need few protected values, multi-scale forms need all of them.

## The registered statements

| Id | Verdict | In one line |
|---|---|---|
| PB8 | HOLDS | Theory within 0.05 in 61% of cells at the new couplings (σ = 0.1) |
| PB9 | HOLDS | Theory hit rate 1.00 → 0.28 from σ 0.05 to 0.4, crossing 50% between 0.2 and 0.3 |
| PB10 | FAILS | Continuum intuition: harm falls with coupling. True for fine damage, false for regional |
| PB10t | HOLDS | Theory's non-monotone coupling dependence of regional harm (6 of 8 series) |
| PB12 | HOLDS | A setpoint's value rises with coupling (σ = 0.1), with the theory's low-coupling value too small |
| PB11 | FAILS | Coarse backup equals full: true within 0.002 for coarse forms (but read as benefit), false for multi-scale forms |
| PD1 | HOLDS | Two voting records repair combined injury (+0.111, +0.098) |
| PA1 | HOLDS | ME001's latch blocks it under random onset (34–44%); v2 acts (98–100%) |
| PA2 | HOLDS | The latch filters by duration; without it even 50 updates are adopted |
| PA3 | HOLDS | Aborting protects the record from a mid-burst body injury (+0.080) |
| PA4 | HOLDS | A body injury closes the latch for a following reference injury |
| PC1 | FAILS | Pooled thresholds false-alarm on S4 (52%); fine on BL and IS |
| PE1 | FAILS | At equal dose the sheet vote does not beat linear site correction (−0.085) |
| PF1 | HOLDS | Capture heredity decays (0.765 → 0.581), replicating the debug block |
| PF2 | FAILS | In-life repair does not slow the decline of copied records at σ = 0.3 (slope −0.082) |
| PF3 | FAILS | A coarse germline equals the full one for coarse forms (slightly better), worse for BL |

**Two rule-design lessons for the next registration:**
- An equivalence claim must test the ±0.02 interval directly. The reading hierarchy calls a precisely estimated +0.002 a BENEFIT (PB11, PF3).
- A slope metric penalises a lineage that starts higher (PF2); the mean over generations is the better primary.

## Harms, gaps and caveats

- **The v2 arbiter's harm.** It is −0.009 to −0.062 after collective body and combined injuries: it adopts permanent body changes after its latch expires. Duration alone cannot separate a legitimate lasting change from lasting damage. Biology appears to gate rewriting by phase or by an explicit signal rather than by duration alone (BODIES.md §6), which ME002 did not test.
- **Case-level harms** remain inside benefits. For example, the vote harms 28 of 128 cases under combined collective injury.
- **The event oracle** is privileged on timing but not a ceiling in sequences. The full protected backup is the ceiling.
- **Equal dose** only scaled votes down; three votes already delivering less than their linear comparator stayed native.
- **One apparatus:** a 16 × 16 sheet with supplied sensors, actions, records and redundancy. Development throughout; leads need fresh-block confirmation.

## What this says about where setpoints come from

Together with ME001, THEORY.md and BODIES.md, the screen supports a single picture:
- **When a setpoint pays.** It is an investment against forgetting. It pays where native physics loses the pattern faster than a lifetime but correction can still hold it, and its value grows with how cooperatively the tissue is coupled.
- **Where correction acts.** Correction is needed at the scales the body's own coupling cannot restore, and nowhere finer. That scale moves with coupling, and the useful trigger moves with it.
- **When rewriting the record is safe.** Only when evidence attributes the change to the record, and the body is a faithful enough copy. A latch makes that evidence a duration filter, which cannot tell lasting damage from lasting change.
- **Redundancy, and what to protect.** Redundancy (a second record voting with the body) removes the need to infer provenance, which is the coding-theory answer and the one bodies seem to use. Protection need only cover the scales the body cannot regrow.
- **Across generations.** Copying a protected record is what keeps a form; capture through the body is lossy every time.

## Next

- **OR001 (done, REPORT_OR001.md):** selection on heritable controller constants, from almost no setpoint, rediscovers these rules where they pay. It also finds a new strategy: when the record itself is unsafe, read it only to build each body and pass on the body.
- **Candidates for a frozen confirmation on fresh blocks:**
  - the v2 arbiter with abort;
  - the two-record vote;
  - the 16-value germline for coarse forms;
  - the site-level trigger at weak coupling.
- **A fix to test:** gate rewriting on recovery as well as quiet. For example, require that the body's pooled state has returned within its sham range, or that a second record agrees, before adopting a lasting change. Then test phase-gated rewriting (a plastic window after a declared cue), as BODIES.md suggests.
- **ME003 (from PROTOCOL):** conditional future usefulness with repeated futures. The scratch raw states hold the records to restore.

## Reproduction, checks and files

- **Freeze:** REGISTRATION_ME002.md and `me002/frozen/`. Run with `python -m me002.run --stage development` after the qualification receipt. Read with `python -m me002.analyze` and `python -m me002.tables`. Post-run check: `python me002/post/postcheck.py`.
- **Committed results:** `results/me002/`. Contrasts are split by panel and primary endpoint, plus `summary.json`, `predictions_scored.json`, `TABLES.md` and the post-run receipt.
- **Kept in scratch:** raw states (8.6 GB), the full contrast tables for every endpoint, and the full summary, all in `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/me002/development/`.
