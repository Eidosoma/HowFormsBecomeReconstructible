# Hybrid preservation and rewriting composition test

The user authorized this first P04 development probe after the P03 injury-transfer
result. The earlier prediction of a positive rewrite benefit under new injuries
failed in its selected development panel. That result is preserved. This new
experiment tests the missing combination of preservation and rewriting, with a
frozen ordinary additive forecast and a sign-permutation control.

## Cohort and records

Retain all 64 exposed generation-14 failures, in eight blocks and four writer
histories. No enrollment depends on later success, signed diagnostics, or the
new interventions. Let I be the actual incoming record, O the actual outgoing
original-writer record, and A the edge-availability mask at the original injury.
All weights have the same two reciprocal edge planes and 4,096-byte encoding.

Use six records, fixed across all new injury and read draws:

| Record | Originally available edges | Originally unavailable edges |
|---|---|---|
| Incoming I | I | I |
| Erasure-only D | I | Zero |
| Outgoing O | O | Zero |
| Hybrid H | O | I |
| Scrambled hybrid S | O | Magnitudes from I with permuted signs |
| Erased | Zero | Zero |

Construct H by selecting O where A is true and I elsewhere. The outgoing
record already has zero values where A is false. D removes only the original
injury's incident edges from I; it does not copy other zeros from O.

For S, uniformly permute the signs among nonzero incoming edges where A is
false, keeping each edge's exact original magnitude and location. Use one fixed
permutation per case, seeded by namespace, block, `backup_signs`, history index,
founder, recipient. Keep zeros and all available-edge O values unchanged. Do not
redraw identity permutations or select for disruption. Record the number of
backed-up nonzero edges and the number of signs changed. This is a conditional
test of the declared permutations, not a precise average over all scrambles.
H and S have identical absolute weights, hence identical masked unsigned
operators and unsigned-access diagnostics. A success difference establishes
sensitivity to this sign placement, not a new theory of historical information.

The hybrid assumes that the incoming record remains accessible while the body
writes. That old-record access and protection are supplied resources. Equal
output packet length does not establish equal total costs or autonomous repair.

## Frozen predictions and endpoints

The previous fresh-injury equal-block rates were I=0.28418039209054835,
O=0.22284437567640691 and D=0.08453606939935063. The ordinary additive prediction
for H is p_O+p_I-p_D = **0.4224886983676046**, or **42.25 percent**. Freeze the
corresponding eight block forecasts from the prior analysis, without fitting,
clipping or selecting a model. All eight fall within [0,1]. Also freeze each
block's prior I and O rates as simple carry-forward forecast rivals. This is a
conventional additive baseline, not a uniquely RDT prediction.

The primary forecast outcome is H success under fresh injuries. Report the
equal-block observed rate, signed error from 42.25 percent, every block residual,
mean absolute block error and root-mean-square block error. Evaluate all three
frozen block forecasts with Brier loss on new H read outcomes, weighting cases
equally within blocks and the eight blocks equally. Report paired Brier
differences. Accuracy is continuous: no post-outcome accuracy threshold or
acceptance claim based merely on an interval containing zero.

The primary intervention comparisons are H minus I and H minus O under fresh
injury. The proposed preservation-plus-rewriting benefit requires both point
estimates to be positive in this development panel; report uncertainty for each.
The predeclared secondary content contrast is H minus S, with H predicted to
do better. Other fixed contrasts are O minus I, O minus D, D minus I and S minus
O. Negative or mixed effects narrow the corresponding claim independently.

Measure the contemporaneous four-way interaction

    J = p_H - p_O - p_I + p_D.

J=0 is the additive null. Distinguish J from error against the prior forecast:
forecast error = J + change in (p_O+p_I-p_D) between the old and new draws.
Report both terms and their exact decomposition. This separates non-additivity
from the new controls' sampling variation. A nonzero interaction does not by
itself support a distinct RDT mechanism. An adequate additive forecast favors
the simpler account.

## Injury, reader and sampling

Use the original fixed injury as an exact-control regime and fresh uniformly
sampled 24-cell non-port injuries as the primary regime. For each block and draw
0–15, sample from all 244 non-port cells without replacement using the key
namespace, block, `injury`, draw, founder//2, recipient. Histories sharing a
native context share masks. Do not select masks for overlap or connectivity.
Prior missing weights remain missing unless H explicitly restores an incoming
value. Each fresh mask is paired with one fresh reset/noise stream.

The read RNG key is namespace, block, `read`, draw; this is separate from masks
and backup-sign permutations. Retain the native matched-cue and founder-pair
noise contract. Draw the complete two-founder-pair by four-recipient panel at
each update; share draws across records, histories and injury regimes.

Use the unchanged nonlinear reader: dt 0.2, noise 0.02, birth SD 0.05, clipping
at plus/minus 2, input clamping, and injured cells zeroed each update. Read for
2,048 updates, with 1,024 settling and 1,024 amplification updates. No writing
occurs during a read. Both cues must give all four task-aligned output means
strictly above 0.25, averaging the last 32 observations. There are 12,288
packet/read trajectories: 64 cases x 2 regimes x 6 records x 16 paired draws.

Compute unchanged 64-step signed and unsigned diagnostics under each actual
mask before native outcomes. These are retained descriptors and implementation
controls; no new model or record-selection policy is fitted. Under the original
mask, I and D must read identically; O, H and S must read identically. Erased
outputs must be cue-identical and never pass. Under every mask, H and S must
have exactly equal unsigned diagnostics.

Eight blocks remain the inference units. Report all block effects and a
descriptive 20,000-resample whole-block bootstrap with seed 2026101002.
Per-case Wilson intervals from 16 draws describe Monte Carlo uncertainty only.
Use the same bootstrap block indices for paired errors and contrasts. These
are exposed source states and an outcome-informed design; new random draws
do not make it independent or confirmatory evidence.

## Verification and bounded execution

Hash-bind the prior completion marker, analysis, frozen preparation and all
consumed arrays. Preserve enrollment, six packet byte arrays, masks, backup
permutation statistics, diagnostics, native resets, endpoint bodies, last-32
windows, scores and all forecast inputs. Independently regenerate masks and
sign permutations, reconstruct H and S, and check the old forecast arithmetic.

Before launch, test the native reader against the separate flattened-grid
implementation, order invariance, support/magnitude preservation, original-mask
identities, strict scoring, forecast isolation and the full analysis/report
interface with nontrivial synthetic outcomes. Benchmark the largest block using
six duplicated known incoming records and two original-stream duplicates at
2,048 updates. Require byte-exact replay. Forecast runtime as 1.5 times measured
seconds times the scientific, known-replay and independent-audit cell-update
ratio, plus 180 seconds. The ceiling is 3,600 single-thread forecast seconds;
an overrun of that forecast gate stops launch without shrinking the experiment.

The worker replays every original native case before fresh reads. Independently
rescore every raw observation window and table. Audit the first enrolled case
of every block at draw 4 using the separate native reader for all six records
and both injury regimes; check its diagnostics with dense operators. Preserve
failures and completed snapshots. Freeze source and inputs before launch and
execute the frozen copy.

Use one persistent detached host process and one numerical thread, with at least
1 GiB free disk and all writes/caches inside the theory lane. Durable status,
PID, log and completion/failure records accompany automatic analysis,
verification, report and figures. Do not poll the long run automatically. No
successor, publication or external message is launched.
