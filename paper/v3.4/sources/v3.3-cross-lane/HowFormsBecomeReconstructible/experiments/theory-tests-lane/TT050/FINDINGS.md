# TT050: connectivity preservation gives a causal lead, not a duration verdict

Completed 1 November 2026 at 16:37 UTC; saved-data review passed. All eight
prespecified exposed E077 source blocks and all 512 records remain. The
development phase took 2 h 49 min 38 s on two workers, including independent
native replay and scoring audits. Qualification ran separately beforehand.

Preventing re-isolation before fresh injury retained part of pruning's
immediate benefit and improved next-generation usefulness relative to full
pruning and matched placements that leave cells isolated. This supports a
connectivity/placement mechanism worth following in the shared duration study.
It does not establish unique mediation by isolation, removal of the later
cost, or a one-generation delay rather than lasting harm.

## Principal mixture panel

There are 256 mixture records, each assessed under two receiving draws. Counts
below are successes out of **512 paired receiving contexts per arm/horizon**,
not 512 independent source records. The inference units are eight source blocks.

- **I:** preserve the incoming record unchanged.
- **P:** delete the entire selected exact-fallback edge set.
- **C:** retain a minimum set of selected edges that restores I's connected
  components, at their original positions and values; delete the remainder.
- **L_native:** retain the same number of selected edges elsewhere, leaving
  cells isolated, with those positions' original weights.
- **L:** use the same positions as L_native but transplant C's retained weights,
  matching its full signed-weight multiset, absolute mass and edge count.

| Arm | Immediate success | After one rewrite |
|---|---:|---:|
| I | 255/512 — 49.80% | 318/512 — 62.11% |
| P | 309/512 — 60.35% | 313/512 — 61.13% |
| C | 283/512 — 55.27% | 329/512 — 64.26% |
| L_native | 295/512 — 57.62% | 315/512 — 61.52% |
| L | 291/512 — 56.84% | 297/512 — 58.01% |

| Paired comparison | Immediate effect, percentage points | After one rewrite, percentage points |
|---|---:|---:|
| P − I | +10.55 [7.81, 13.67] | −0.98 [−3.91, 2.73] |
| C − I | +5.47 [3.13, 7.62] | +2.15 [−0.59, 4.88] |
| C − P | −5.08 [−8.20, −2.34] | +3.13 [0.78, 5.86] |
| C − L_native | −2.34 [−5.08, 0.20] | +2.73 [0.19, 5.47] |
| C − L | −1.56 [−4.30, 0.59] | +6.25 [2.73, 9.97] |

Brackets are the frozen **pointwise 95% whole-block percentile intervals** from
10,000 draws. These are approximate development intervals across many retained
comparisons, not a familywise confirmation. The also-prespecified bounded
Hoeffding intervals are much wider and all these comparisons include zero;
for example C−L at h1 is [−89.78, 100] points. Both interval types remain in
the complete output. Zero empirical variance never establishes equivalence.

C preserves a smaller immediate improvement than P and performs better after
one rewrite. But this panel does not establish P's later penalty in the first
place, nor establish C's equivalence/noninferiority to I after writing. Thus
“the later cost is removed while the benefit is retained” is too strong.
This uses the first eight exposed source blocks and newly paired terminal
draws, not the full original E077 cohort or its original assessment outcomes.
I/P writer packets nevertheless reproduce the retained E077 writer exactly.

Paired harms remain. At h0, C versus I rescues 39 contexts and harms 11.
At h1, C versus P rescues 30 and harms 14; C versus L rescues 44 and harms 12;
C versus I rescues 30 and harms 19. These are paired context counts, not
independent samples or a claim that every record benefits. The h1 mean-margin
changes support the same ordering: C−P +0.0865 [0.0299, 0.1454] and C−L +0.1144
[0.0554, 0.1804]. Opposite-task success changes are unresolved in both contrasts.
All margins, opposite outcomes and record-level gain/harm counts are retained.

## Did the manipulation change the proposed mechanism?

Yes, within its stated limits. All 512 count/weight placement comparisons were
feasible; none was dropped or replaced by a favorable case.

| Mixture mean per record | P | C | L |
|---|---:|---:|---:|
| Newly isolated before fresh writer injury, relative to I | 21.91 | 0.00 | 15.22 |
| Newly isolated surviving cells after writer injury | 20.00 | 2.06 | 13.90 |
| Available selected edges using exact fallback | 59.94 | 7.48 | 41.96 |
| Selected share of normalized absolute coupling after injury | 0.0000 | 0.1068 | 0.0565 |

All newly isolated surviving cells have zero cue contrast in this matched-noise
regime. C restores the initial components exactly, but fresh injury can sever
its sparse reconnections: it does **not** eliminate realized re-isolation in
every writer. Selected fallback use is much reduced, not abolished. Both output
patches remain input-reachable in the saved summaries; reachability of other
live cells changes. After writing the displayed arms have the same aggregate
support/isolation summaries, while their weights and receiving usefulness differ.

The C/L weight multiset match does not match local normalized influence,
graph location, all paths or injury vulnerability. The table demonstrates that
normalized coupling differs substantially. The intervention therefore supports
a causal role for connectivity/placement under these controls; it cannot
allocate a unique fraction of the effect to isolated-cell counts alone.

## Signs, magnitude, capture route and history

The C−L h1 contrast remains positive in point estimates under every declared
sign/magnitude setting: +6.25 points with native values, +5.47 with donor signs
reversed, +5.08 with quarter magnitudes, and +5.47 with both changes. For C alone,
sign reversal changes h1 success by +0.20 [−0.98, 1.37] points and quartering
magnitudes by +0.39 [−0.59, 1.76]. These do not establish sign/magnitude equivalence.
L is more sensitive in some comparisons: quartering native-sign magnitudes
improves h1 success by +1.56 [0.59, 2.73] points. Explicit placement interactions
and both sign settings are in `closeout_review_v1/PLACEMENT_INTERACTIONS.json`.

Same-body capture controls have an important degeneracy. For P, ordinary
selected-edge capture and both sign/magnitude substitutions are **byte identical
to the hybrid outgoing packet in all 512 records**. Their zero effects provide
no independent evidence about capture choice. For C, ordinary capture and its
magnitude substitution change every record; the sign substitution changes
439/512. Selected support never disagrees. On mixture records, ordinary capture
loses 2.34 [0.98, 3.91] points relative to the hybrid, with 12 harms and no rescues;
the magnitude substitution has the same net loss. Sign substitution leaves
the binary outcomes unchanged despite altered packets. Continuous effects and
bounded uncertainty remain available; this does not prove sign irrelevance.
These results do not support assuming harmful fallback specifically because
its signs are task-irrelevant.

Native and mixture sources differ. Native P−I changes immediate success by
only +0.20 points, then costs 10.16 [6.05, 14.45] points after writing. Native
C−P gains 11.13 [7.22, 15.43] at h1, while C has no observed immediate success
gain over I. Pooling native cases with mixture cases would therefore obscure
which population supplies the immediate benefit versus the later penalty.

The declared sham/pulse strata are exported separately. Mixture P−I at h1 is
+0.78 [−3.52, 5.08] for sham and −2.73 [−6.64, 1.17] for pulse; both are unresolved.
Mixture C−L is +3.91 [0.78, 7.42] for sham and +8.59 [1.95, 16.02] for pulse.
All four source/history strata, all arms and all harms are retained in
`closeout_review_v1/STRATA.json`. Writing-body endpoints are separate in
`WRITING_BODY_BLOCKS.csv`; they are not substituted for fresh-recipient outcomes.

## Scope, verification and handoff

Acquisition, writing and terminal readout all use the matched cue apparatus,
float64 packets, exact-zero fallback and natural absolute-weight normalization.
Terminal injury/reset/noise are matched across treatments **and both horizons**;
writer injury is separate. These results do not test an independent-noise,
tolerant-writer regime, another substrate, or additional generations.

The run independently replayed the native dynamics and graph/normalization
instrumentation, and matched I/P writers to E077 in every source block. Closeout
verified 144 frozen inputs, 290 distinct files, all 28,672 exported case rows
and 504 paired-metric/interval calculations. No frozen file was changed.
The closeout added the already-declared source/history strata and explicit
factorial interactions without new dynamics. Original automated outputs remain
unchanged; review receipts and supplements are separate.

The next scientific interpretation should join this diagnosis with E119's
four-rewrite trajectories through the declared shared streams. TT050 supplies
no evidence yet that arms converge at rewrite 2, stay separated or alternate.
Do not launch another unchanged serial confirmation on the basis of this
one-rewrite result. No successor or manuscript change was started. The queued
TT021 information-source audit remains unstarted.

Reproducible sources: [protocol](PROTOCOL.md),
[complete original results](runs/development_v1/analysis/RESULTS.json),
[case predictions/outcomes](runs/development_v1/analysis/CASES.csv),
[run scoring audit](runs/development_v1/analysis/AUDIT.json),
[closeout review](closeout_review_v1/REVIEW.json),
[saved-data review script](review_closeout.py), and
[Forms stream/instrumentation contract](FORMS_INTEGRATION.md).

To repeat only the saved-data review into a new directory from theory-tests-lane:

```bash
bash run_python.sh -c 'import sys; from pathlib import Path; sys.path.insert(0,"TT050"); import review_closeout as r; r.OUT=Path("TT050/closeout_reproduction_v1"); r.main()'
```

The new directory must not already exist. This checks hashes, tables and
declared summaries, and does not rerun the native trajectories.
