# E035 — can the writer preserve cue responsiveness?

**Complete and independently verified; the predefined improvement and absolute
reliability criteria were not met.** Finished on 28 September 2026 at
**03:32:31 UTC**, in 2h24m36s, about 13m11s later than forecast. Independent
replay checked all 258,048 terminal scores and 2,048 reused source-body scores,
every source/terminal update, construction, statistic and decision. The subsequent
[E036 fresh serial comparison](../E036_serial_cue_capture_v2/README.md) is complete:
the cue-contrast policy collapsed under repeated rebuilding, despite this
earlier one-boundary benefit.

Cue-contrast capture with full rewriting raises scattered-damage both-cue
success from **356/512 (69.53%) to 386/512 (75.39%)** under the common normalized
reader. Its gain is **5.86 percentage points [2.93, 8.98]**. The lower bound is
below the required five-point improvement, so the frozen primary fails.
Absolute reliability also fails: success has interval **[71.48%, 79.30%]**,
whose lower bound is below 75%. Passing all 24 older context gates does not
replace either criterion.

| Construction, normalized scattered test | Both cues correct | Success % [95% interval] |
| --- | --- | --- |
| Current capture / preserve strong | 356/512 | 69.53 [65.43, 73.63] |
| Current capture / rewrite all | 343/512 | 66.99 [62.50, 71.29] |
| Cue contrast / preserve strong | 351/512 | 68.55 [63.48, 73.44] |
| Cue contrast / rewrite all | 386/512 | 75.39 [71.48, 79.30] |
| Matched strength / preserve strong | 363/512 | 70.90 [66.60, 75.00] |
| Matched strength / rewrite all | 365/512 | 71.29 [66.80, 75.59] |

The controls identify a useful conditional lead. Removing strong preservation
with the current capture hurts success by **2.54 points [0.78, 4.30]**. With
cue-contrast capture, removing preservation instead helps by **6.84 points
[3.91, 9.96]**. Their interaction is **9.38 points [5.86, 13.28]**. The effect
of copying therefore depends on what the writer captures in this intervention.

Within full rewriting, changing only to cue-derived signs while holding every
weight magnitude, support and receiving denominator fixed improves success by
**4.30 points [2.15, 6.45]** over standard full rewriting. This supports a
contribution from signs, beyond changes in strength, under that policy.
Cue-contrast full rewriting adds **4.10 points [1.56, 6.64]** over the matched
construction. With strong preservation, matched signs give **1.37 points
[-0.20, 2.93]**, so that comparison does not resolve a benefit. All these
secondary intervals are pointwise, not fresh confirmatory evidence.

The same cue-contrast/full-rewriting candidate reaches **87.30% intact** and
**85.35% square-injury** success, versus 77.54% and 78.32% for the current policy.
This experiment writes six records from the same 512 delayed-renewal E034
bodies. The writer uses activity from the two cues, without desired output
labels or terminal outcomes. It does not change the source body or create a
new serial history. The current-policy reference reproduces E034 exactly.

The separately frozen E036 comparison tested cue-sensitive writing and the
current writer, with copying and settling controlled, on 512 fresh lineages
through sixteen damaged renewals. It finished on 29 September at 09:04:54 UTC
and passed independent replay. Cue-contrast full rewriting gave zero scattered
success at h8/h16, versus 81.64%/56.64% for delayed standard preservation.
The one-boundary benefit did not translate into a durable serial policy.
Longer settling with the standard writer remains a positive secondary lead.

All eight technical checks passed before launch. The excluded fixture and
benchmark independently replayed 4,032 / 2,016 terminal and 32 / 16 reused body
scores. All 25 scientific inputs were frozen before validation. The full run
used eight workers with one numerical thread each. Simulation took 4,379.57
seconds and independent replay 4,293.11 seconds.

Artifact closeout passed at **17:14:31 UTC on 28 September**: 33 fixture,
33 benchmark and 188 scientific original outputs, all 25 frozen inputs,
source provenance, operational receipts and figure hashes verified. The
scientific figure was visually inspected. Retained scientific data total
24,314,467 bytes; 636,059,648 bytes were free at closeout. No new trajectories
ran during closeout.

- [Frozen protocol](PROTOCOL.md)
- [Scientific report](runs/capture_v1/REPORT.md)
- [All statistics](runs/capture_v1/summary.json)
- [Scientific figure](figures/capture_v1/capture.png)
- [Independent replay](runs/capture_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Source provenance](SOURCE_DATA.json)
- [Technical validation](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Prelaunch verification](analysis/prelaunch_scientific_v1.json)
- [Verified launch and estimate](analysis/scientific_launch_verification_v1.json)
- [Durable job status](jobs/capture_v1/status.json)
