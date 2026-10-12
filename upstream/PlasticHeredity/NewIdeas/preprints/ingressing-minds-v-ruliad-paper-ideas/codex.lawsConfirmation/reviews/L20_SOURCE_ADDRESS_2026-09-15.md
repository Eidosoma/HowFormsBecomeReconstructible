# D126 — source feedback address and force audit

2026-09-15. COMPLETE; saved-data audit and independent raw reconstruction pass.
[Prospective contract](../protocols/L20_SOURCE_ADDRESS_V1.md).

## Result and adjudication

**ALIGNED_ADVANTAGE_QUALIFIED. L20 remains STRESS_TESTED / MIXED.**

Correctly addressed source feedback substantially improves the record a fresh
recipient can read. The ONE frozen aligned-minus-scrambled primary is
**+25.37231 [23.57178, 27.08766] preference points**. All eight paired
blocks and all 32 role/stratum-averaged lives favor aligned feedback.
Both directional intervals are positive: A +21.60645 [19.55160, 24.11713],
B +29.13818 [25.72418, 32.33643]. Each direction also has all eight blocks
and all 32 averaged lives positive.

The no-feedback baseline distinguishes useful feedback from harm caused by
scrambling. Both happen here; these are prespecified SECONDARY contrasts:

| Terminal preference contrast | Points, 95% whole-block interval | Positive / negative / tied blocks |
| --- | --- | --- |
| Aligned minus scrambled, PRIMARY | +25.37231 [23.57178, 27.08766] | 8 / 0 / 0 |
| Aligned minus no feedback | +9.33634 [8.32926, 10.38218] | 8 / 0 / 0 |
| Scrambled minus no feedback | -16.03597 [-18.16615, -13.92812] | 0 / 8 / 0 |
| Shuffle-adjusted specificity gain | +24.89624 [22.10490, 27.51358] | 8 / 0 / 0 |
| Sign-only aligned minus scrambled | +25.83415 [23.90940, 27.64079] | 8 / 0 / 0 |

Aligned-minus-no-feedback is positive in both directional intervals:
A +1.67236 [1.42405, 1.89209], B +17.00033 [14.90479, 19.25456].
All 32 averaged lives in both directions improve. Scrambled-minus-no-feedback
is negative in both directional intervals: A -19.93408 [-22.37549, -17.85889],
B -12.13786 [-16.31287, -7.99154]. All pooled averaged lives are negative,
but B has four positive and 28 negative lives; baseline harm is not uniform.

All THREE content routes and the readout instrument qualify. Pooled
intact-minus-own-recipient-shuffle preference is +43.79476 [41.91691, 45.61361]
for aligned, +18.89852 [17.10612, 20.21693] for scrambled and +34.53573
[32.55005, 36.51937] for no_feedback. Both directional content and intact-
minus-zero intervals are positive for every route. Scrambling harms content
without erasing all of it; some individual content-control contrasts are
negative, especially B. The losing-arm content rule is not decisive here:
even the scrambled arm qualifies.

| Qualified own-pattern agreement | Aligned source feedback | Scrambled source feedback | No source feedback |
| --- | --- | --- | --- |
| Pattern A, mean | 93.45% | 70.83% | 91.57% |
| Pattern B, mean | 87.59% | 54.74% | 69.29% |
| Pattern A, individual range | 87.50–96.88% | 49.61–86.72% | 85.94–95.31% |
| Pattern B, individual range | 69.92–95.31% | 42.97–67.58% | 57.42–87.50% |

Agreement is not the primary own-minus-other preference statistic, a pass
rate or an 80% certification. Ideal mean agreement is 95.24%/92.62% and
zero 45.35%/43.56% for A/B. Wide individual variation remains.

The pooled primary by original source stratum is +23.76099 [20.36133, 26.95328],
+26.14746 [22.68677, 29.29077] and +26.20850 [23.98071, 29.22974].
Every directional block/life primary contrast within each stratum is
positive: all 192 role-by-stratum-by-life comparisons favor aligned feedback.
This is descriptive consistency within eight independent blocks, not 192
independent replications or three new renewal generations. All three pooled
specificity intervals are positive; stratum 2 has one negative averaged life.

Only the declared pooled qualified primary is confirmatory. All other reader
and force intervals are prespecified secondary, pointwise/unadjusted. The
bootstrap resamples eight whole blocks 10,000 times; neither cells, paths,
source strata nor time steps inflate independent n. No threshold adjustment,
exclusions, adaptive extension or equivalence claim.

## What the force audit adds

The benefit is not explained by a larger scalar input or a larger average
realized next-step RMS increment. Spatial arrangement matters in this assay.

| Mean per-step diagnostic, model units | Aligned | Scrambled | No feedback |
| --- | --- | --- | --- |
| Applied theta std | 0.299700 | 0.299700 | 0 |
| Centered step-input RMS | 0.059940 | 0.059940 | 0 |
| Realized next-V increment RMS | 0.0575282933 | 0.0575387149 | 0 |
| Effective increment dot old V | 0.0480787032 | 0.0211670378 | 0 |
| Effective increment dot (old R minus old V) | -0.0112664131 | -0.0096981067 | 0 |
| Old R-minus-V RMS gap | 0.4390041998 | 0.5470748862 | 0.5068859927 |

These means include the initial zero-feedback step: the other 999 steps
have input std .3 and input RMS .06 in both nonzero arms. Every input trace
passes the fixed 1e-14 matching checks. Bootstrap differences around 1e-19
in input RMS are floating-point roundoff, with every block/life tied at the
declared 1e-12 descriptive tolerance, not a physical dose imbalance.

Aligned's average realized increment is slightly SMALLER: difference
-0.00001042160 [-0.00001064900, -0.00001013054], about 0.0181% below
scrambled, negative in all eight blocks/32 averaged lives. This is not exact
effective-force equivalence. The tiny but resolved difference does not
support an explanation in which aligned feedback wins by pushing harder.

The dot-old-V difference is +0.02691167 [0.02667953, 0.02713212], while
dot-reference-gap is -0.00156831 [-0.00169246, -0.00142885] and R-minus-V
RMS gap is -0.10807069 [-0.11082054, -0.10588809]. These are descriptive
state-dependent dot products/gaps, not normalized angles, energy, information
or a causal mediation decomposition. Force direction, spatial roughness and
development still differ. Final-update clip fraction is zero in all arms;
that does not rule out clipping at the earlier substep before R correction.

The zero-theta diagnostic uses the same old state and same noise, never
feeds forward and never advances the real RNG. The result therefore supports
useful spatially addressed feedback at matched additive input strength,
not complete force-matched stabilization or a uniquely isolated semantic
information mechanism. Scrambling changes local spatial organization too.

## Connection to the laws

D126 adds bounded E5 evidence for a useful spatial address in the source
theta-to-body-to-R feedback route. Correct feedback helps versus no feedback;
scrambled feedback actively harms the outgoing record on average. All routes
retain some readable content, so indispensable theta is not established.

This strengthens D125's source-maintenance interpretation without reversing
D124's negative added-final-theta-value result, D123's relative source-noise
buffering or D117's engineered three-boundary renewal. It does not establish
a necessary slower-and-cleaner cascade, autonomous address/ontology learning,
target-free acquisition, a learning-only disposition, biological canalization,
a natural genome or E6. The known pre-writing starts retain instructed
acquisition and earlier theta-supported development; there is no new serial
feedback-off or scrambled-feedback lineage. L20 remains STRESS_TESTED / MIXED.

## Prospective design and launch record

The following retains the prospective design and chronological preparation
record; later completion does not turn those earlier checkpoints into results.

User approved D125's next lead. Compare correctly addressed and spatially
scrambled source feedback at fixed input strength; retain no-feedback baseline.
All sources continue writing latent theta. Same R-final packet constructor
and matched fresh readers. One aligned-minus-scrambled primary.

The force audit uses same-old-state/same-noise zero-theta one-step diagnostics;
these never feed forward or alter the real RNG. Input strength matching is
not exact effective-force matching. Scrambling is target-blind and preserves
its own evolving arm's value multiset, not a supplied alternative message.

576 new source writers, 576,000 auxiliary diagnostic steps, 2,688 fresh
readers; three reused source strata, not new serial renewal boundaries.
Main identities 68000–68007, disposable 514226 (known source 514217).
All data external under /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation.
Six CPUs maximum; forecast >600s detached, no polling, user advances.
L20 remains STRESS_TESTED / MIXED. No adaptive retry or automatic successor.

Six new science files and this live review; earlier science/results/reviews
and original law/preprint/case files unchanged. The new runner validates
D125's hash-pinned flat transitive closure directly rather than repeatedly
re-entering all ancestral preparation validators. No outcomes dropped.

Pre-file development: one template selector failed before the new test file
was written; corrected without simulation or data impact. Tests, bridge,
freeze and disposable timing are required before main futures.

## Pre-freeze checks

444 tests pass in 346.56 s: 183 D126, 147 D125 and 114 D124, with no
failures/errors/skips. XML full disposable life 22.519 s; known six-writer/
six-reader bridge test 9.745 s (including setup). External report logs/d126_tests_attempt1.xml
and fixtures tmp/d126_tests_attempt1. Four ASTs, shell syntax, whitespace,
2,054 local Markdown links and all 300 prior repository-side input pins pass.
Existing bytecode unchanged: 124 files / 4,195,796 B / newest mtime
1788545213.016447. No code or protocol edit after the passing suite.
Retained known-history bridge COMPLETE 11:22:01.586697 UTC,6.8592299279s
after initial provenance preparation,631577B external. All six known source
writers/six readers and6000 force probes reproduce exactly,error0.
Freeze11:22:48.611332 UTC pins616 inputs with zero main futures; SHA256
4b5163dcda9bb5facfa7da4e593a9b6f41dc267a8dd3c5fd8843dcfc76e05e5f.
Disposable benchmark COMPLETE11:24:53.287512 UTC:92.9551426191s checked
block,1.8264561649s hash check. All72 source writers/336 readers/72000
force probes and156 aliases reproduce exactly; source/force/overall errors0.
Disposable outcomes are not qualification data. Forecast927.2940532826s
(~15.5min) mandates DETACHED main execution. Budget176633687B/168.45MiB;
raw block16427008B,benchmark11031614B,known bridge631577B.
Main prepared11:26:17.063020 UTC with620 inputs. Independent flat pre-launch
hash check confirms all620 and that execution had not started. Manifest SHA256
f2bb340fb419925d7d7723144b3dd6671a6fe0be5592afe8158f126244781257.
Launch ACKNOWLEDGED by detacher: PID2623186,closed stdin,new session,
six CPUs0–5 maximum,external log
[l20_source_address_v1_attempt1.log](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/l20_source_address_v1_attempt1.log).
Launcher reported user_polls=true,automatic_polling=false. At the launch
handoff no subsequent process/status/log/outcome check had been made;
acknowledgement was not treated as completion. No post-freeze science change.

Metadata vocabulary note: the legacy key source_pairs counts 192 matched
starting conditions (six per life), now each with THREE source branches.
It does not mean 192 independent samples or only two source branches.
Declared actual totals are 576 writers, 2,688 readers and eight inference blocks.

## Completed execution and audit

First post-launch status/outcome read was at the user's 2026-09-15 status
request, around 12:46 UTC. No automatic post-detachment polling occurred.

LAUNCH.json records 11:27:38.417666 UTC, PID2623186. Main COMPLETE at
**11:32:00.985174 UTC**, in **262.5667461669 s (~4 min 23 s)** after
execution start, with **89,118,157 B / 84.99 MiB** of main outputs.
Initial preparation/provenance is excluded from that elapsed counter.
The conservative frozen forecast was 927.29s; detachment was correctly
chosen from that forecast, not from hindsight. The 168.45MiB budget held.

All 576 source writer paths, 576,000 auxiliary force probes and 2,688 reader
paths were independently replayed during execution, with source/force/overall
maximum discrepancy zero in every block. All 1,248 aliases passed.
The separate completed saved-data audit now passes: all 620 inputs/19 outputs,
source addresses, metadata, observations, summary, verification counts,
manifest/output index and COMPLETE/STATUS agree. This saved audit does not
rerun dynamics; independent dynamics checks occurred during execution.

The separately prepared NumPy/stdlib-only raw reconstruction was executed
successfully, importing neither production nor checker. It rebuilds all
576 final-R primary packet bytes, source-start addresses, first-step matching,
target-blind source permutations, per-step input-strength traces, both terminal
observers, all 264 reader contrasts and 96 force contrasts (means, block/life
values, 10,000-draw intervals and sign counts), 1,248 aliases and all 620/19
hashes. Maximum reader-statistic roundoff5.5511151231e-17, force-statistic
roundoff2.9143354396e-16; packets/observations/aliases exact.

All data, outputs, fixtures and logs remain external under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation. At audit the workspace is
about17MiB, external free space about104GiB and root about5.5GiB free.
Only code/docs changed here. No main failure, retry, exclusion, deletion,
cleanup, commit, post-freeze science edit or automatically launched successor.

Closeout checks pass: all 307 frozen repository-side inputs (including prior
completed reviews and the six new science files), three original law/preprint/
case pins, four Python ASTs, shell syntax, whitespace and 2,061 local Markdown
links with zero broken targets. Existing bytecode remains exactly 124 files /
4,195,796 B / newest mtime 1788545213.016447. No frozen input was edited.

- [Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_source_address_v1_attempt1/summary.json):
  SHA256 8f9e29db7f23abf672b93fb95c94827dcc2d24b9d5a5283c283056c6ec2466f0.
- [Verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_source_address_v1_attempt1/verification.json):
  SHA256 6e54eef7363ab46901ed0cdd1508795cc9e2139e3e6b3153b4f0e35871e7eba7.
- [Manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_source_address_v1_attempt1/MANIFEST.json):
  SHA256 f2bb340fb419925d7d7723144b3dd6671a6fe0be5592afe8158f126244781257.
- [Completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_source_address_v1_attempt1/COMPLETE.json):
  SHA256 d150d898ca86a2eefd769c502446ea493ff8c17ad82b03eb9f211503d7671267.

## Next proposal only

A geometry-preserving misaddressing control: rigidly translate the entire
current feedback sheet on the periodic grid, keeping its internal spatial
organization instead of scattering its cells. With a new frozen comparison,
both roles and the same reader/force audit, ask whether the address matters
when spatial roughness/organization are preserved. Translation still changes
feedback relative to the body; it is not automatic force equivalence or
learned addressing. No translation/offset sweep or successor code, protocol,
identities or run has been created. A new run requires user approval.
