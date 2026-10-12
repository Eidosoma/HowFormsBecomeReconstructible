# Bounded source-reproduction pilot

Date: 2026-09-05. Written before the pilot simulations.

The user authorized the proposed short investigation: small isolation and
neighbour-switching comparisons, saved-output mapping, and a larger timing
check. This is not a complete reproduction of the paper or a PH experiment.

## Source and execution limits

- Unmodified BITSEY revision `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.
- Existing Python environment in `requirements-smoke.txt`.
- At most two simultaneous simulation processes, one numerical-library thread
  each; 900 seconds per case and a one-hour launch budget for the whole pilot.
- Every run gets a unique ignored directory. Store stdout, configuration,
  source/reference/harness hashes, timing, numerical checks, and results.
- No broad parameter sweeps and no upstream edits. Configuration changes used
  for numerical sensitivity are named explicitly, not silently substituted.

## A. Isolation: reproduce threshold brackets and a matched comparison

Use a 25-cell line with six M-like cells at one end and E-like neighbours,
Snail 72, miRNA valence -1, and medium-size miRNA. Follow the upstream
`find_min_Kd_tumorFix` preparation: create the configuration, equilibrate for
500 with miRNA transfer off, then run `sim_is_fixed` for 20000. Initial ionic
conditions and gates are those of the source helper.

The saved `results_miRNA/tumor_isolate_1D_V1M` reports approximate thresholds:
no isolation `7.18e-15`; voltage isolation `1.51e-13`; connexin underexpression
`9.41e-15`; both `2.96e-13`. The saved gap-junction dumps show underexpression
0.5. These are historical source-run targets, not the paper's 3D table values.

Rather than rerun four full binary searches immediately, check these brackets:

| Strategy | Lower Kd: expect not normalized | Upper Kd: expect normalized |
| --- | ---: | ---: |
| None | 6.25e-15 | 1.25e-14 |
| Underexpression 0.5 | 8e-15 | 1.25e-14 |
| Voltage gating | 1e-13 | 2e-13 |
| Both, underexpression 0.5 | 2e-13 | 4e-13 |

Also run voltage isolation at `1.25e-14`, expecting no normalization. Together
with the no-isolation upper case this is a same-Kd comparison. Voltage-only
at `2e-13` versus both at `2e-13` tests added protection at the same Kd.

Success means the registered binary outcomes match and the sampled trajectories
are finite and nonnegative. Report independently counted E/M/X labels as well
as the upstream normalization criterion. A bracket match is not a precise
threshold replication; a mismatch remains visible and requires diagnosis.

## B. Neighbour-state switching: repeat a small native threshold experiment

Run the upstream `surround_flip_sims` experiment at Snail 72. It tests a central
cell with 2, 3, 4, or 5 oppositely initialized neighbours, in both directions.
It uses a 500-unit disconnected preparation and a 1000-unit connected horizon,
with the source's binary search and its concentration-distance success test.

Reference: `results_miRNA/surround_flip_72`. Expected threshold values:

| Neighbours | E centre toward M | M centre toward E |
| --- | ---: | ---: |
| 2 | 1.129e-15 | 1.005e-15 |
| 3 | 7.124e-16 | 6.442e-16 |
| 4 | 5.212e-16 | 4.740e-16 |
| 5 | 4.108e-16 | 3.748e-16 |

Report relative error for all eight, with a provisional source-reproduction
gate of <=2% per threshold and no missing/failed searches. This tolerance
is chosen before execution and is not biological validation. The native binary
search bracket is about 0.1%; the wider reproduction gate allows for the
rounded reference and environment/version differences without calling them
exactly identical. Do not use this gate to hide larger discrepancies.

## C. Numerical sensitivity

Repeat voltage-only and both at `Kd=2e-13`, halving the minimum explicit step
from 1e-4 to 5e-5, the adaptive concentration-increment bound from 1e-3 to
5e-4, and the adaptive voltage-increment bound from 1e-4 to 5e-5. Both retain
their original 20000-unit connected horizon.

Also repeat the both-at-2e-13 case with the baseline integrator settings and
a 40000-unit connected horizon. Compare classifications and concentration
differences; do not infer solver convergence from these few checks.

If a baseline case fails to run, keep its sensitivity comparison inconclusive
rather than replacing it with a conveniently successful condition.

## D. Larger-network timing

Use a 1x25x25 grid (625 cells) containing a 1x6x6 corner of M-like cells.
Run no-isolation at `Kd=1.25e-14` with the same 500/20000 horizons. The saved
`tumor_isolate_2D_V1M` reports a no-isolation threshold near `1.89e-15`, so
normalization is the qualitative expectation. The matching 25-cell run gives
a small-vs-large timing comparison, not a linear-scaling law.

Record wall time and CPU time. A 900-second timeout is a lower-bound timing
observation, not a scientific refutation. If needed, a separately labelled
81-cell follow-up may be used to obtain an intermediate timing point; do not
claim it reproduces the 625-cell result.

## Instrumentation and decision

The pilot harness may wrap `sim.sim` to inspect and save its returned snapshots.
It must forward the arguments and return values unchanged, without altering
the equations, gates, stopping conditions, or numerical settings except for
the explicitly listed sensitivity configurations. This checks saved snapshots,
not every internal integrator step.

Load the upstream module using its existing empty CLI range `[0,0)` so that
its unguarded `main()` performs no experiment during import. Then call the
original functions. Record this import adapter and keep it outside upstream.

Decide at closeout whether the observed agreement, interpretability, and runtime
justify a full source reproduction. Keep historical-output reproduction,
paper-figure reproduction, independent implementation, and PH extensions
separate. Do not report hypothetical therapeutic implications as new findings.
