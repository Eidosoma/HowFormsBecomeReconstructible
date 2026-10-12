# D171 — qualified and benchmarked; real development fitting unstarted

2026-09-23. [Frozen execution protocol](EXECUTION_PROTOCOL_V1.md),
[unchanged scientific proposal](PROPOSAL_V1.md), [current status](README.md).

The saved-data comparison is implemented and ready for the next user-driven
stage. **No new real-data fits, real-data forecasts, tissue simulations,
diagnostic cycles, founders or lineage outcomes were produced.** This is an
apparatus/implementation result, not evidence that settings improve prediction.
Existing array schemas and reference metadata were inspected; the benchmark
itself used synthetic data only.

## What was qualified

Ninety synthetic tests passed in 7.52 seconds. They cover all shift geometries
and aligned unused-shift invariance; strict per-observer feature boundaries;
case/life/founder order; labels, IDs and third-copy rejection; whole-founder
exclusion; train-only scaling; constants and collinearity; raw-reading tying
with unequal scales; zero-settings nesting; clipping; independent SVD fits;
future-mean scoring identities; reference/model/report corruption; saved
roundtrips; write-once and external-only output; resource guards; detached
startup acknowledgement; and no automatic polling, retry or successor.

The first qualification attempt retained 83 passes and one failure. An
artificial 1e7 feature created million-unit un-clipped extrapolations whose
floating-point re-expression discrepancy (~9.3e−10) exceeded the fixed
2e−10 absolute audit tolerance. The clipping test now uses a still-extrapolating
1e3 feature, and a separate test confirms that the extreme case fails closed.
The scientific model and tolerance were not relaxed. Both attempt reports
and all fixtures are retained and included in the storage account.

Before freeze, input verification was narrowed from repeatedly hashing the
entire ~8.3 GB historical D160 input closure to checking all consumed files,
the full D170 evidence set, and immutable predecessor manifest/completion/
independent-audit anchors. The larger historical closure passed the first
qualification check; unconsumed archived fit/trajectory files need not be
reread at every new stage. No consumed reference or outcome was omitted.

The frozen implementation binds 367 input files, the passing test XML and
41 qualification-artifact paths. Freeze completed at 16:59:30 UTC. Old frozen
scientific modules and the D170 design receipt's documents were not edited.

## Complete synthetic benchmark

All sixteen synthetic founders and all life/group cases were retained.
Fixture construction made 336 synthetic reference fits; the tested workflow
then made 336 augmented fits and 5,376 out-of-fold forecasts. It checked the
saved references, independently solved every augmented fit in group SVD
coordinates, verified nesting and raw ties, built every report, wrote and
reopened outputs, and rechecked frozen input hashes. A subsequent read-only
recheck of those saved synthetic files passed too.

Largest SVD forecast discrepancy: 4.00e−15; projected stationarity residual:
5.34e−16; raw-reading tie residual: 1.39e−17. The report check covered 42
absolute score records, 93 fixed paired contrasts, twelve changes in
challenge/passive gaps and sixteen explicitly selection-affected cheap-
baseline comparisons. No confidence intervals or deployment selection.

Measured elapsed time was **5.5584 seconds**, including 0.4843 seconds for
the final frozen-input hash pass. Saved benchmark fixtures and outputs:
6,625,895 bytes (6.319 MiB). The new output panel alone:
3,621,764 bytes (3.454 MiB). Qualification artifacts from both attempts:
3,973,404 bytes. Including receipts and logs, the retained D171 artifacts
totaled 10,788,140 bytes (about 10.3 MiB) before this documentation handoff.
All numerical artifacts are on `/mnt/bioIce1`; only code/docs were added here.

The protocol's conservative next-stage time budget is **132.09 seconds**,
not a promise of exact elapsed time. Its aggregate storage reservation is
50,779,626 bytes (48.427 MiB), comfortably below the 128 MiB allowance, with
the separate 4 GiB external reserve. This reservation includes the preserved
qualification artifacts, twice the full benchmark size and 32 MiB headroom
for the real run, logs, inventories and receipts. The old 63 GB simulation
budget does not apply to this saved-data fit.

## Handoff

Next, after user advancement: run the frozen comparison on the sixteen
already-studied development founders. Read the old references in place;
produce only the 336 new fits and 5,376 forecasts. Check all groups, alphas
and cheap baselines; keep residual-minus/passive at .01 focal. Then perform
a separate saved audit and report the actual development findings plainly.

Entry from the workspace root:
`bash L20-extension-1/scripts/run_settings_prediction.sh execute --development-fit-approved`.
Its current measured budget is below the ten-minute detachment threshold.
If a later budget exceeds 600 seconds, use the qualified detached launcher,
not a progress-polling loop. One worker, one numerical thread, maximum six
CPUs. No job is currently active and no successor has been scheduled.

Even favorable development findings would need a newly approved, untouched
prospective cohort. The old pilot is not a fresh test. D141/D162 remain
unresolved; L20 stays STRESS_TESTED / MIXED. Knowing diagnostic apparatus
settings is not autonomous address learning or complete shape preservation.

## External provenance

All paths below are relative to
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.

- Passing qualification: `logs/d171_qualification_v2.xml`, SHA-256
  `645fdb39d3330501e697d12c572cb6189e835ecd9602ad826af4e4ed13a1411a`.
- Freeze: `tmp/l20_extension1_settings_prediction_dev_v1_attempt1_freeze.json`,
  SHA-256 `dea3c08f0de000ff827bd1d2dcc46dffab74952420a12beccb98c6bb712fed4a`.
- Benchmark: `tmp/l20_extension1_settings_prediction_dev_v1_attempt1_benchmark.json`,
  SHA-256 `05f5295c91c16c157661a8bf8d6acae938fe790c7dee73d6aa2ff96bce568f9f`.
- Synthetic files: `tmp/l20_extension1_settings_prediction_dev_v1_attempt1_benchmark/`.
- Failed first qualification: `logs/d171_qualification_v1.xml`; preserved,
  not represented as a passing freeze proof.
- Actual run/output namespace `l20_extension1_settings_prediction_dev_v1_attempt1`
  remains absent from both `runs/` and `outputs/` at this handoff.
