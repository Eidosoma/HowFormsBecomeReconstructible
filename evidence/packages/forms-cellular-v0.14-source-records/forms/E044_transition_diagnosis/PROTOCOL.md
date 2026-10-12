# E044 — histories of timing rescues, losses and persistent failures

Authorized by “lets go” on 6 October 2026 after E043's verified negative timing
result. This exploratory diagnosis reuses all **32 blocks 32000–32031 / 512 E041
lineages**. E043 already established 17 scattered rescues and 14 losses at h32,
and eight rescues and fourteen losses at h24. Those known results motivate this
analysis; they are not newly predicted or independently replicated here.

Freeze twelve inputs before new joined measurements. No new trajectories,
record changes, intervention outcomes or parent manuscript edits are generated.
No scientific pass/fail gate is introduced. E041's qualification and E043's
failed timing criterion remain unchanged.

## Fixed population and measurements

Use **full bridge rewriting only**, the normalized reader and own-record arm,
at **h24 and h32**, under **all three injuries**. Include all original, extra-time
and delayed-extra-time outcomes. Other readers and controls remain in the
completed E043 experiment; this analysis addresses its declared focal method.
Join by exact block, founder, descendant and horizon, never by rank or outcome.

For each horizon/injury, define four mutually exclusive groups by original versus
delayed success: persistent failure (fail/fail), rescued (fail/succeed), lost
(succeed/fail), stable success (succeed/succeed). All cases remain represented.
Retain 113 per-lineage features and group codes:

- Cohort membership; all ten original E032 output features for each of the three
  schedules, including both-cue success, full reversal, locked-output failure,
  other failure, cue accuracy, worst margin, two cue amplitudes and two absolute
  cue-independent biases. The strict margin remains 0.25. The four labels are
  mutually exclusive, not proposed causal mechanisms.
- All seventeen outgoing-packet features from E042 at the target generation,
  including strong (>0.5) counts, sign changes, physical strong loss, weak-to-strong
  promotion, strong weakening and strong sign flips. Sign changes relative to
  acquisition are descriptive and need not mean incorrect information.
- All seventeen E042 repair counts at that generation and three declared pooled
  conditional ratios: returning edges restored nonzero, available weak nonzero
  edges promoted strong, and recently returning weak edges promoted strong.
- E042's four graph measurements under the exact saved injury mask; all ten
  current rebuilding-body output features. These measurements were independently
  audited in E042 and are reused, not recomputed from dynamics here. Unsigned
  graph connectivity does not establish sufficient functional information.
- Twelve history summaries: fraction of bodies failing strictly before h;
  previous/current body success; failure, new-failure and recovery counts in the
  last eight bodies g(h−7)…g(h); net strong-count change from packet h−8 to h;
  weak-promotion, strong-weakening, physical-strong-loss and strong-sign-flip
  counts across those eight writes; and strong count in the incoming packet h−1.
  First transitions in the eight-body window compare g(h−7) with g(h−8).
  Check the strong-edge accounting identity. Body challenges differ across time;
  this is not irreversible survival or evidence that a later packet is better.
- Original and delayed intact/square success, plus next-body success and an
  observation flag. Next body means g25 for h24. There is no saved g33: **h32
  next-body success is null in summaries**, never zero success.
- All sixteen original-to-delayed transitions between the four output classes.

Repeat packet/body/history measurements across terminal injuries solely to allow
conditioning on each injury's outcome group; these repetitions are not new data.
Summarize every feature for the full cohort and each group, for every horizon and
injury, plus the three repair ratios: **3,480 fixed summaries**. Cohort fractions
use all cases as denominator; other means use group membership, repair ratios use
eligible-edge totals, and next-body success uses the observed-follow-up flag.
Every estimate retains block numerators/denominators. Empty conditional groups
have null estimates and intervals, rather than invented zeros.

## Inference and verification

Use 10,000 whole-block resamples from `E044/bootstrap/transition_diagnosis`.
Conditional estimates are ratios of pooled block totals; keep empty blocks in
resampling, omit undefined bootstrap ratios and report the valid-draw count.
All intervals are exploratory and pointwise. Groups are outcome-conditioned on
an existing cohort and may be small. Associations cannot identify the direction
of causation between unsuccessful reading, weight changes and later failure.
They must not become post hoc eligibility rules presented as fresh confirmation.

Pin E042/E043 source completion, audits, summaries and closeouts, plus upstream
E041 completion/audit/summary/closeout. Verify full consumed source outputs and
frozen inputs at both ends. Independently reread source arrays, classify outputs
with the separate E032 auditor, join each scalar lineage, and compute history
windows with explicit generation loops. Verify new arrays, independently rebuild
all summary definitions/totals/intervals, and exactly reproduce E043's eighteen
normalized own-record success means and all twenty-four four-group counts.
Upstream packet/body/graph equations and source dynamics remain covered by E042
and E041 audits; they are not rerun or claimed as newly validated mechanisms.

Eight synthetic checks cover exclusive classes/strict cutoffs, all outcome groups,
reader/horizon/founder/injury/arm indexing and corrupted scores, historical windows,
class transitions and missing follow-up, empty-block ratios, null h32 summaries,
and source-row or strong-accounting mismatches. No scientific case is a fixture.

## Execution

Before scientific measurement, run a complete excluded benchmark using E042's
benchmark records and E043's fixture records: both derive from E041 fixture block
900041 with two recipients. Verify all joins and summaries, and inspect its
figure. Forecast seconds as
`1.8*(benchmark extraction+independent worker seconds)*32*2/workers+180`.
The factor2 scales R2 to R4; the 180-second allowance covers source verification,
3,480 scientific summaries and independent intervals, report and figures. This
bounded saved-array analysis is expected to finish below ten minutes.

Forecast retained storage as `ceil(1.5*benchmark_run_bytes*64)+128MiB`. Use at most
eight CPUs/workers, one numerical thread per process, and keep all writes inside
experiments. A forecast over 600s requires detached execution, stdin `/dev/null`,
local PID/log, frozen inputs, durable status and one bounded startup check, then
user-requested status only. Otherwise complete the analysis in this turn.
Preserve failures and frozen inputs. No automatic restart, intervention sweep or
scientific successor.
