# D167 — saved stages of the two undisturbed copies, version 1

Specified 2026-09-22 before the new stage calculations. The user approved
D166's proposed passive-copy trace. This is post-test explanation, not a
prospective test or a new attempt to select a successful challenge.

## Fixed scope

Use every development founder 90000–90015 and pilot founder 100000–100063,
all four lives, both families and both writers. Ordinary means the source's
translated writer. Analyze U0 and U1, the two undisturbed diagnostic copies.
They start with identical records but have different diagnostic random streams.
The final diagnostic reader is not an actual three-replacement lineage outcome.

Read existing diagnostic NPZ/JSON archives only, plus pre-outcome endpoint
members for an exact bridge and earlier audit/provenance receipts. The archives
also contain C1; its arrays may be decompressed with the same NPZ member, but
are sliced out before analysis. Do not read actual lineage outcomes, forecast
values, model coefficients or errors. Never load development labels/futures.
No new simulation, model fit, prediction, founder or diagnostic cycle.

Pin the 160 raw diagnostic files to the D162 full-audit input/output manifest,
and the D166 evidence closure to its completed receipt and saved audit.
The old full physical replay is not repeated. Independently verify the saved
algebra, packet routing, writer-start continuity and endpoint extraction here.

## Complete saved-stage inventory

48 fields per diagnostic copy, in this order:

- Input packet and guide-routed input packet.
- V, ema and R at read steps 0, 1, 100, 101, 300 (15 fields).
- V, ema, R and theta at writer steps 0, 1, 300, 1000 (16 fields).
- tanh of final writer R, outgoing record, guide-routed outgoing record.
- V, ema and R at fresh diagnostic reader steps 0, 1, 100, 300 (12 fields).

V is the activity/body field, ema its running average, R the slower reference,
and theta the writer's feedback field. Only the final R snapshot enters the
instantaneous record constructor: center tanh(R), then scale to SD 0.3.
The outgoing record is not simply the saved theta. Read step 300 equals
writer step 0 for all three body fields; theta starts at zero. Within a family,
the two writer conditions have identical initial reads and writer steps 0/1.

For every field calculate five fixed measurements: best translation-invariant
own-family correlation, best alternative-family correlation, own-minus-other
best frozen-guide correlation, canonical own-minus-other target correlation
in that field's current coordinates, and field RMS. Constant fields have
zero correlations. Canonical correlation is not silently re-routed; only the
explicit packet-routing stages change coordinates. No label or 80% cutoff.
Guide/shape correlations describe a field, not necessarily a functional body.

Also retain qualified own-minus-other preference of fresh-reader V at each of
its four saved times, using the existing strict abs(V)>0.2 amplitude rule.
This is the inherited measurement, not a new survival threshold.

## Accounting and concentration

For every stage/measurement/group report each cohort's two copy means and
population SDs, U1-minus-U0 paired gap, each founder's four-life means/gap,
positive/negative/near-zero founder counts, min/max gap, and mean absolute gap.
Near-zero means abs(gap)<=1e-12, solely a numerical sign tolerance.
Report each single-founder score-only omission and its range. No case is
removed from the primary descriptive mean. Report the largest absolute
founder contribution as a fraction of the sum of absolute contributions,
not a potentially misleading fraction of a canceling net gap; ties use the
first declared founder. Null fraction when all gaps are zero.

Report pilot-minus-development changes in copy means and paired gap. For the
14-stage packet/reference path (input, routed, five read R checkpoints, four
write R checkpoints, tanh, outgoing, final routing), report all 13 successive
changes in copy gap for all five measurements/groups. This is a telescoping
description, not a causal decomposition: birth initializes a new field, tanh
is nonlinear, and the sparse saved checkpoints do not identify an exact onset.
Fresh-reader stages are reported separately, not treated as inherited R.

Keep all 960 field/group/measurement rows, 16 final-reader preference rows,
and 260 adjacent-reference transition rows, plus per-case arrays. Show complete
founder tables for outgoing-record own correlation/guide margin, read-end R
and writer-end R own correlation, and final diagnostic preference. All other
founder/stage entries remain in the external summary/arrays. No ranking used
for case selection, confidence intervals, significance tests, new predictions,
correlation with actual outcomes or changed D141/D162 conclusions.

## Qualification and execution

Production FFT correlations are checked independently by direct translated
template products. The checker separately extracts all fields, computes
preference, validates routing/projection/continuity and rebuilds summaries.
Bridge all six endpoint and four initial measurements to saved diagnostics,
the selected feature-archive members and D166 aggregate rows. Test constant
fields, translation/sign behavior, projection, copy reversal, founder order,
single-founder concentration, corruption, forbidden outcome access, and
write-once/external-output/detached guards. Qualify a full 16/64 synthetic panel
with the same field inventory and saved-output checks before real analysis.

Freeze protocol, implementation, independent checker, executor, tests, passing
qualification and consumed sources before analysis. Budget each real stage as
three full synthetic-panel durations plus four source-hash durations plus
120 seconds. If this exceeds 600 seconds, detach that stage with durable logs,
new session and null input. No automatic polling, retries or successor stage.

All outputs, fixtures, receipts and caches stay under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
128 MiB output allowance, 4 GiB free reserve; at most CPUs 0–5, one numerical
thread. Code and documentation only in this folder. Preserve failed attempts.

This may locate where a sample imbalance grows, not establish its cause,
prove diagnostic randomness responsible, or validate a challenge advantage.
D141/D162 and L20 STRESS_TESTED / MIXED are unchanged by this audit alone.
