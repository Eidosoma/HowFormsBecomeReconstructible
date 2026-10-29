# Autonomous reversal confidence interval correction

**17 October 2026.** The completed simulation is preserved. This correction
replaces **105 pooled cost interval records across 21 panels** in the reporting
analysis. Mean costs, saved actions, observations, purchases, per-condition
intervals and the two declared reversal/core verdicts are unchanged.

The authoritative pooled intervals are now in
[CORRECTED_RESULTS.json](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/CORRECTED_RESULTS.json).
Keep the original `attempt-01/RESULTS.json` and `READBACK.json` as historical
records; their pooled cost intervals must not be used for inference.

## Defect and scope

The frozen runner represents cost rates with axes
`base, block, condition, arm, segment`, of size `27,32,25,2,2`.
Its pooled selection `rates[:, :, selected, :, segment]` combines separated
NumPy advanced indices. For four reversal conditions this returns axes
`condition, base, block, arm`, with shape `4,27,32,2`.
Taking `mean(axis=2)` therefore averages blocks and leaves a `4,27,2` array.
The interval helper then treats four conditions as strata and 27 physical
bases as independent Monte Carlo repetitions.

The specification instead requires conditions to be averaged within each
independent block, producing `27,32,2`: 27 fixed base strata, each with 32
independent blocks. Balanced means survive the erroneous transpose and average,
but variances and confidence intervals do not. The defect affects both arms,
their paired contrast and their contrasts against always purchasing in each
pooled full-episode/post-change cost panel. It does not enter a policy decision,
physical generator, feedback mask or stored trajectory.

The automatic saved-data checker used the same erroneous advanced-index
expression for these panels. Its independently implemented variance formula
therefore did not detect the wrong observational units. The repeated reporting
fixture also repeated identical block values and lacked an explicit shape
contract. The reported 390,195 automatic assertions passed, but were insufficient
to validate these pooled intervals. This defect was found while checking the
cost-component decomposition for the reviewer-requested final report.

## Repair and verification

The separate [reporting analysis](analyze_fep_autonomous_reversal_report.py)
selects the segment first and uses `np.take(..., axis=2)` for conditions.
It asserts the selected and averaged shapes before any interval calculation.
The estimator and 1.96 multiplier remain exactly those in the specification.

Verification uses explicit Python loops over each base, block, condition and
arm, followed by a separate two-pass stratified variance calculation. A
nonconstant synthetic fixture with unequal axis lengths detects both the
original shape and variance failure. Additional checks cover permutation of
blocks within strata, an analytic variance example, error/purchase cost and
variance closure, unchanged condition-level intervals, preserved diagnostic
intervals, and reconstruction of saved belief/action relationships.

The correction and descriptive report analysis passed **75,873 assertions in
4.92 seconds**. The serialized pooled intervals were checked again against the
explicit scalar per-block construction. All 70 frozen inputs, three snapshots
and 232 original outputs retain their hashes. No scientific policy was rerun,
no data were discarded, and the frozen specification/runner/readback remain
unchanged. New analysis outputs use the separate `reporting-2026-10-17/` folder.

## Numerical impact

| Reversal recovery measure | Mean | Original invalid 95% interval | Corrected 95% interval |
|---|---:|---|---|
| Previous controller cost | .155140659 | [.134525197, .175756121] | [.151061487, .159219830] |
| Structured controller cost | .122635122 | [.112687052, .132583191] | [.119954823, .125315420] |
| Structured minus previous | −.032505537 | [−.045368308, −.019642766] | [−.035901791, −.029109283] |

The structured controller still improves on its predecessor and still costs
more than always purchasing (.1) during recovery. Both the primary reversal
and secondary core two-part success criteria remain **FAIL**: paired improvement
passes; the absolute cost criterion fails.

Ancillary interval interpretations can change. For example, B-partial full
episode cost has unchanged mean difference +.000352431, but its interval changes
from [+.000029736, +.000675125] to [−.000030757, +.000735619]. It no longer
supports a directional harm claim at this nominal interval level. Stable's
small cost increase remains supported: +.000603009 [.000223142, .000982877].
Every affected interval, including unfavorable and inconclusive comparisons,
is retained in the [complete correction table](/mnt/bioIce1/fep-ideas/formal-checks/fep-autonomous-reversal-v1/reporting-2026-10-17/INTERVAL_CORRECTION.json).

Main manifest SHA-256:
`92ae729ed63faa44a5296e7525357feb9ccbf83936334d04bcb03058e45324f5`.
Original automatic readback SHA-256:
`97160a67363acf2026184a0f1fc0992cf355644e6f321eac887fd8dfba99831e`.
Corrected results SHA-256:
`dc6d44925a905c43dc6e3212378fc9b489aa6abe11e507294103bb0ae9b07202`.
Analysis readback SHA-256:
`bb4aa132f9c2370416fc6a63dcfd786739e89ad34c21b53dc8a7bf91a04bdd9a`.
