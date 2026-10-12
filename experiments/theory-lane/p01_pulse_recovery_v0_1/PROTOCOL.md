# Pulse recovery from completed native histories

Development analysis, 9 October 2026. The user accepted analysis of the completed
pulse experiment as the immediate next step. No new native trajectories are
required. All terminal outcomes, earlier diagnostics and the full E051 cohort
are already exposed. Definitions below are fixed before extracting these new
recovery measurements; this does not make the analysis confirmatory.

Use blocks 34000–34007, every founder and recipient, and every saved generation
3–32. Join the original/tolerance/sign-restored pilot with the subsequent
original/magnitude-restored/single-pulse pilot. Original histories must match
byte for byte at each boundary. O, T, S, M and P retain their frozen definitions.
P writes T at generation 3 and O thereafter. Its generation-3 outgoing packet
and generation-4 pre-write body must equal T's. All bodies coincide before the
generation-3 write. Verify actual outgoing packets against independent writer
calculations on each branch's own body, including the specified zero-sign
completion for M. Do not mistake a hypothetical O-to-T comparison on P's later
body for an actual second tolerance event.

Normalize each saved outgoing reciprocal weight network by the sum of absolute
incident weights at each receiving cell, with zero rows mapped to zero. This is
the native reader's linear input operator, not the full nonlinear noisy reader.
Use the existing diagnostic implementation and fixed 64 linear updates with
input clamped to +1. Report the minimum correctly signed output-port response
as signed transfer and the minimum unsigned response as access. These are
surrogates, never reconstruction probabilities. Outgoing packets already encode
the current body's missing edges. Add no next-generation mask: using that future
mask would change the meaning of an observable at the current boundary.

For every lineage and generation record:

- Native pre-write minimum output margin and strict both-cue pass/fail.
- Actual outgoing signed transfer and unsigned access.
- Mean row L1 distance from the same-generation O branch; also the absolute
  signed-transfer difference from O. Average rows over live non-input cells.
- Mean row L1 distance of the actual writer from counterfactual O evaluated on
  the same body. This local action differs from accumulated distance from the
  O history. Save counterfactual O signed transfer as well.
- The hypothetical fraction of available nonzero-contrast edges selected by
  tolerance: 0 < abs(q) <= 1e-4. Retain the sign-flip fraction and compare both
  with the existing saved diagnostics.
- Mean absolute end-body cue difference, output-margin difference from O,
  and the native generation-32 scattered terminal outcome as a separate label.

The principal recovery contrasts are P's change in distance from O between
generation 3 and generation 4 (first O rewrite), and between generation 3 and
generation 6 (three O rewrites). Retain the signed-transfer gap alongside distance
so functional recovery is not equated with packet restoration. Summarize changes
within each block, then average the eight blocks; report all block values and
directions without confirmatory p-values. Show all generations, including late
divergence or reversals. No favorable stopping generation will replace these
declared comparisons.

Report paired P-minus-T and P-minus-O body success, margins and diagnostics over
time, with S and M as secondary context. Count P/O body discordances and
ever-failure over generations 4–32 separately from terminal reconstruction.
For any lineage failing in P but succeeding in O at generation 4, report the
first later P body pass, or right-censor at generation 32; varying damage makes
this descriptive, not a controlled recovery-time assay. Report early measurements
for all terminal P-versus-O outcome strata, preserving the four known harmed
lineages, without treating outcome-defined groups as prospective predictors.

No terminal prediction model, threshold search, horizon search, feature sweep
or new cohort is fitted here. In particular, these diagnostics must not silently
revive the previously failed passive P01 feature set. They describe response to
an actual controlled pulse and help specify a subsequent timing intervention.
A timing comparison should hold pulse count, last pulse generation and final
recovery interval fixed while varying spacing. It remains unrun after this
analysis; prospective prediction requires a separately frozen test.

Bind all consumed files to the completed-run hashes and their array commitments.
Use one numerical thread. Benchmark extraction on one declared boundary before
the full calculation; detach and leave unpolled if the conservative forecast
exceeds 600 seconds. Keep source, configuration, tests, raw feature rows, block
summaries, verification, plot and conclusions in this new versioned directory.
Never overwrite earlier runs or a failed extraction.
