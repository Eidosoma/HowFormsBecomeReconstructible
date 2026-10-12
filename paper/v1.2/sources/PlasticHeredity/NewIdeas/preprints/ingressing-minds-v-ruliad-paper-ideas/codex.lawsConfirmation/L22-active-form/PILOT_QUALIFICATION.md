# D184 pilot implementation qualification

12 October 2026. **All 188 scoped tests passed in 31.46 seconds.** The complete
disposable benchmark is qualified for launch; this is not a 64-record pilot
result or evidence that body-supplied correction works.

The suite contains 56 new tests and 132 D183/source-recovery/feedback/readout
regressions. A complete miniature execution exercised all 36 repair paths,
51 named assay conditions, packet-only transfer, selective controls, exact
aliases, independent replay, scalar scoring, saved-array checks and all 20
descriptive contrasts. The miniature uses tissue 603184 with one replicate
per message, two readers, three settling sweeps, six imprinting sweeps and four
repair/readout sweeps. It is a software fixture, not a scientific performance
measurement. The full benchmark retains the protocol's full-length settings.

Zero-reset native writing matches frozen D183. The separate ema=V comparison
matches the original source recovery API. The averaging sidecar leaves its
sampled body's dynamics unchanged; an independent online-mean calculation
checks the production cumulative sum. Tampering tests cover state, RNG,
packets, probabilities, message labels, control-plan labels and contrast
directions. Tests also reject missing runtime dependencies, changed readout
settings, failed XML receipts, excess threads/CPU affinity, low disk reserve
and attempted artifact overwrite or escape from the data directory.

## Retained qualification history

- Attempt 1: 98 passed, one failed. The miniature execution found a local
  dictionary variable overwritten by a scalar in the contrast checker.
- Attempt 2: 185 passed, one failed. The execution completed, but a test
  incorrectly required each disabled-reader message stratum to score 25
  percent. The correct requirement is 25 percent over balanced messages,
  with identical uninformed trajectories across intended-message labels.
- Attempt 3: 187 passed in 30.73 seconds. Neither correction changed physical
  equations, endpoints or scientific settings.
- Attempt 4: 188 passed in 31.46 seconds, after binding all five test sources,
  Python/NumPy versions and a conservative uncompressed storage bound.

All receipts and fixtures are retained separately under the external pilot
root. No full-length benchmark or four-block outcome informed these fixes.

## Freeze and prelaunch checks

Freeze completed at **13:27:30 UTC**, before full-length acquisition. It binds
252 input hashes, including D183's original inputs and saved outputs, every
one of the 46 imported repository modules, all five test files, the protocol,
the new independent checker and the final XML receipt. This includes the
helper absent from D183's construction freeze; no old freeze was changed.
All hashes and runtime-module coverage were reverified before launch.

Freeze SHA-256:
a99f02583a871d65b4c6c3a9f44c982b8f6e5b5b1659417d3e125bb24159e32f.
Final XML SHA-256:
3912b82f73c63a8a873a0dc91c237d29d118f261402d302dda1b55e1d650f4ed.

Prelaunch retention was 132,944,326 bytes, about 126.79 MiB, including all
qualification attempts and the freeze. The benchmark's uncompressed storage
allowance is 135,102,464 bytes, with no alias/compression discount. Retention
plus that allowance and 64 MiB headroom fit below 1 GiB; the separate 4 GiB
free-volume reserve passed. The benchmark uses one CPU and numerical thread.

Its 646.59-second allowance requires detachment. The launcher acknowledges
startup only and never polls, retries or starts a successor. See
[benchmark status](PILOT_STATUS.md) for the acknowledged launch and next gate.
Use manifest-to-COMPLETE wall time for the complete cost, not just the inner
block timer; input/output hashing and final serialization must not disappear
from the estimate. Report peak process memory and uncompressed saved size too.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-pilot-v1`.
Freeze: `runs/FREEZE_l22_active_form_pilot_v1_benchmark_attempt1.json`.
Test receipts: `logs/qualification_v1_attempt1.xml` through `attempt4.xml`.

The original benchmark executor remains unable to acquire the four-block
panel. After [benchmark completion and saved review](BENCHMARK_RESULTS.md),
a [separate panel executor](PANEL_QUALIFICATION.md) passed 227 tests; its
[status page](PANEL_STATUS.md) owns the new freeze and execution gate.
Fresh confirmation and repeated renewal remain later, conditional stages.
