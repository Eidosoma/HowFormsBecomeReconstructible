# E051 — cue pairing and the exact-zero repair fallback

Authorized on 8 October 2026: “let's insert a new experiment to test this.”
The E041 implementation review identifies matched rebuilding cue randomness as
a supporting condition for the exact-zero ordinary-coactivity fallback. The
reviewer's proposed sensitivity test is distinct from the E050 rollback study.

## Cohort and fixed comparison

Use 32 fresh blocks **34000–34031**, four founders and four recipients per block:
512 lineages per policy. Check IDs against every prior run manifest declaring
blocks. No prior scientific cases are reused or pooled. Excluded block 900041
provides compatibility checks, a fixture and a benchmark only. Freeze code and
this protocol before tests or new scientific trajectories; retain failures.

Cross seven cue-pairing conditions with five fixed writing policies, yielding
35 separate histories per lineage. Pairing conditions are `(reset rho, noise
rho)`: paired `(1,1)`, noise 0.999 `(1,.999)`, noise 0.99 `(1,.99)`, noise 0.9
`(1,.9)`, independent noise `(1,0)`, reset 0.99 `(.99,1)`, independent reset
`(0,1)`. Each condition changes rebuilding trials before capture only. Teaching,
damage, the final assay and holding-phase noise keep their original definitions.
There is no joint reset-plus-noise perturbation in this study.

Draw the first cue's Gaussian array from the unchanged E022 stream. For the
second use `rho*z + sqrt(1-rho*rho)*e`, with an independent E051 innovation
stream. At rho=1 explicitly copy the original array, preserving its bytes.
Keep both marginal distributions unchanged. Use common z and e across all
pairing conditions and policies, preserving paired counterfactual comparisons.
Initial-state correlation and update-noise correlation are separate parameters;
reset mismatch does not carry body state across generations.

The policies are exact-zero bridge rewriting, finite-tolerance bridge rewriting,
ordinary-coactivity rewriting, pure-contrast rewriting and exact-zero bridge
preservation. With `x=tanh(3*v)`, `d=(x_plus-x_minus)/2`, `q=d_i*d_j` and
ordinary coactivity `r=(x_i_plus*x_j_plus+x_i_minus*x_j_minus)/2`, the original
bridge selects r iff q==0. The tolerance bridge selects r iff `abs(q)<=1e-4`.
The fixed 1e-4 threshold is in dimensionless product units (equal endpoint
differences of magnitude .01 lie on its boundary); it is chosen before outcomes,
not optimized or selected from a sweep. Ordinary and pure-contrast controls use
r and q respectively. Preservation retains available incoming abs(w)>.5 and
otherwise applies the original bridge; other policies rewrite every available
edge. Unavailable edges are zero. No labels or damage history enter capture.

All histories receive 32 damaged rebuilding bodies. Keep teaching512/capture128,
reader2048 with1024 settling, holding128, observe32, dt.2, noise.02, birthSD.05,
gain2, 16x16 tissues, 4096-byte packets, 24 absent non-port cells per rebuilding
body and strict output margin>.25. Capture precedes holding. Each history passes
its own outgoing record forward. Source input ports alone are clamped in
rebuilding. The acquired consistent-teaching packet initializes every history.

## Outcomes and inference

At acquisition and after 8,16,24,32 rebuilds, assay own records with the unchanged
normalized reader under intact, scattered24 and square9 injury. Include one
shared erased-record assay at each horizon. All assay cue initial states/noise
remain paired. Retain all 32 rebuilding-body scores. The primary endpoint is
**h32 normalized scattered-terminal both-cue success**, matching E041's outcome.

There are two prespecified mild perturbations: noise rho=.999 and reset rho=.99.
For the original exact-zero rewriting policy, declare joint
PAIRING_ROBUSTNESS_ESTABLISHED only if the paired baseline and both perturbed
absolute success lower95% bounds exceed .75, and each perturbed-minus-paired
lower95% bound strictly exceeds -.05 (at most a five-point allowable loss).
These five requirements form one conjunction. Otherwise report
PAIRING_ROBUSTNESS_NOT_ESTABLISHED. A failed noninferiority requirement does not
prove fragility: separately label a contrast LOSS_EXCEEDS_FIVE_POINTS only when
its upper95% bound is below -.05; otherwise it may remain unresolved.

All other noise/reset levels, tolerance-minus-exact comparisons,
ordinary/contrast/preservation comparisons, shorter horizons, intact/square
outcomes and rebuilding-body outcomes are secondary, pointwise estimates.
Report the fixed tolerance's effect even if unfavorable. Do not choose another
tolerance, sample size or primary after outcomes. Use 10,000 shared whole-block
bootstrap resamples under `['E051','bootstrap','cue_pairing_robustness']`.
There is no separate familywise success claim for secondary alternatives.
Technical runs have null scientific decisions.

Measure at every boundary, separately on available and returning edges: exact
zero products, ordinary-coactivity selection, repaired nonzero/strong weights,
and initially zero connections made nonzero. Returning cells were absent in the
preceding body and are live now; generation1 has no returning cells. Also retain
returning-edge absolute weight/contrast sums and the number of returning cells
reachable from the input over exactly nonzero connections before/after capture.
Connectivity ignores edge sign and is descriptive, not a functional test.
Mechanism summaries average within-block rates over boundaries2–32, then use
whole-block intervals. Keep raw per-lineage counts, sums, end activities, packets
and scores so a change in fallback usage can be distinguished from task loss.

This focused sensitivity experiment does not repeat E041's entire 17-part
durability/context-control battery and cannot issue its full qualification.
No result establishes indefinite heredity, an autonomous origin of the writer,
robustness to combined perturbations, or performance with independent teaching
and terminal-assay cues. A positive tolerance result concerns a modified writer.

## Verification and execution

Independently replay teaching, every rebuilding and holding update, capture,
selection, connectivity/counts, assays, and inference using auditor primitives
without importing production dynamics. Record compact array commitments for
omitted intermediates. Retain body end activity, outgoing packets, masks, birth
arrays, noise moments, holding digests, mechanism counts/sums and mean ports.
Every original-policy trajectory in excluded fixture and benchmark must match
E041's paired exact rewriting, ordinary rewriting and bridge preservation byte
exactly, including all32 boundaries and selected normalized own-record assays.

Fixture: R2, teaching12/capture6/observe4, read24/settle12/hold8, all35 histories
and32 boundaries. Benchmark: R1, full teaching/capture/observe32, read128/settle64,
hold128, all35 histories and32 boundaries. Both are scientific exclusions.
Run meaningful synthetic checks for correlation construction, branch thresholds,
availability/preservation, capture timing, independent replay, evidence
corruption, endpoint axes and strict inference decisions. Inspect both figures.

Benchmark before the large run. Conservative full-workflow seconds:
`3*(benchmark_simulation_worker_s+benchmark_audit_worker_s)*16*4*ceil(32/workers)+120`.
The benchmark already includes32 generations and all35 histories; multiply
only for read length, recipients and block batches. Storage reserve:
`ceil(1.5*benchmark_run_bytes*4*32)+128MiB`. Check actual free capacity.
Use eight workers, one numerical thread each, within the shared12CPU ceiling.
If forecast>600s, launch detached with stdin/dev/null, local PID/log, frozen
inputs and durable status. Perform one bounded startup check; subsequently
await user-requested status. No automatic polling, restart or successor.
