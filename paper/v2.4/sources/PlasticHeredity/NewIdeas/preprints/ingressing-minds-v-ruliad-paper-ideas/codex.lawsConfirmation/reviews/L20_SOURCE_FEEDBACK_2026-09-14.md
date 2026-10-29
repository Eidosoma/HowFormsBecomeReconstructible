# D125 — theta feedback and source record maintenance

Opened and run 2026-09-14; completed-result audit 2026-09-15.
**COMPLETE — FEEDBACK_ADVANTAGE_QUALIFIED.**
[Prospective contract](../protocols/L20_SOURCE_FEEDBACK_V1.md).
L20 remains **STRESS_TESTED / MIXED**.

## Result in plain terms

Letting the developing record feed back into the source helps preserve a
pattern that a fresh recipient can later read. Feedback improved terminal
own-versus-other-pattern preference by **8.61 [7.67, 9.88] points**.
All eight paired blocks and all 32 role/stratum-averaged lives favored it.
Both source arms still produced readable content, so this shows a benefit,
not indispensability.

The effect was much larger for pattern B. Its mean qualified target agreement
was 87.19% with source feedback versus 69.60% without; pattern A was 93.29%
versus 91.57%. Agreement is not the same measure as the primary preference
contrast, and these are averages, not a pass rate or an 80% certification.

Together with [D124](L20_THETA_STAGE_2026-09-14.md), this supports a distinction:
theta helps while the source develops, even though the actual theta endpoint
did not beat an instantaneous R-derived final copy in that separate assay.
This is evidence for the usefulness of the theta-to-body-to-R feedback route,
not yet a uniquely identified slower-and-cleaner copying mechanism.

## Frozen design and inference

User approved D124's source-maintenance lead. Take all 192 known D117
pre-writing V/EMA/R starts at time 300, checkpoint 4, across eight blocks,
four paired lives, both roles and three original-generation strata. These
starts already experienced inherited theta during reading. Erase theta to
zero; run two NEW 1,000-step source writers per start with paired new noise.

Only theta applied to the body differs: current latent theta for feedback,
zero for no_feedback. Both arms keep writing latent theta and retain R
feedback .2, rho .002, lambda .001, noise .3, norm .3 and duration. The first
source update is exactly shared because initial theta is zero. At the end,
BOTH arms transmit only project(tanh(R_final), .3), not latent theta.

Each packet is a 2,048-byte 16-by-16 little-endian float64 sheet, not the
DoorKey 64-byte germ. Fresh matched recipients reset V/EMA/R, receive only
the declared packet and public configuration/identities, and read for 300
steps with writing and R feedback off. Source no_feedback is an ENABLED
recipient condition; only the separately named *_off arms disable reading.

Both source routes have their own shuffle, sham and disabled-reader controls;
ideal and zero calibrate the readout. There are 384 new source writer paths,
1,920 new recipient paths and 864 exact handling/read-off aliases. The three
source strata are reused histories, not three new serial renewal boundaries.
Native rulebook parameters do not give eight distinct effective physics
families; the independent uncertainty units are eight random-stream blocks.

ONE primary is feedback-minus-no_feedback terminal qualified preference:
correct-sign AND strict abs(V) > .2, divided by all 256 cells, own minus
alternative pattern. Average three strata and both roles within each life,
then four lives within each block. Use the frozen 10,000 whole-block
percentile bootstrap. No 80% threshold, exclusions or outcome-driven extension.
All other intervals below are prespecified secondary, pointwise/unadjusted.

## Main result and controls

| Contrast | Preference points, 95% block interval | Positive / negative / tied blocks |
| --- | --- | --- |
| Feedback minus no feedback, pooled PRIMARY | +8.61206 [7.66998, 9.88363] | 8 / 0 / 0 |
| Same comparison, pattern A | +1.52588 [1.22477, 1.81071] | 8 / 0 / 0 |
| Same comparison, pattern B | +15.69824 [13.97705, 18.12337] | 8 / 0 / 0 |
| Shuffle-adjusted specificity gain, pooled | +8.35164 [6.69759, 9.98332] | 8 / 0 / 0 |
| Sign-only feedback comparison, pooled | +8.82975 [7.79205, 10.31494] | 8 / 0 / 0 |

The primary has 32 positive / zero negative / zero tied averaged lives.
A alone has 31 positive and one tied; B has 32 positive. Both directional
primary intervals are positive. That does NOT mean every role/stratum/path
benefits: A has negative individual comparisons in each source stratum,
including two negative blocks in stratum 2; one B life is negative in stratum 3.

Both content flags and the readout instrument qualify. Intact-minus-own-
shuffle preference is +42.61678 [41.06237, 44.01449] points with feedback,
and +34.26514 [32.27097, 36.11247] without it. Both directions of both
content contrasts, and both intact-minus-zero and ideal-minus-zero directions,
have positive block intervals and all eight blocks/32 averaged lives positive.

The prospective ablation rule did not require the losing arm to retain
qualified content, because losing content could itself be the effect.
Here it DOES qualify anyway; the positive label does not depend on that
difference from D124's both-useful-records gate.

Shuffle-adjusted specificity is also positive in both directions:
A +1.55436 [0.97239, 2.22585], B +15.14893 [12.03206, 18.26172] points.
It has all 32 pooled averaged lives positive, but A has three negative lives.
These recipient-side shuffles test the outgoing packet's spatial content;
they do NOT isolate content-specific feedback at the source.

The pooled feedback advantage by original source stratum is +10.93750
[9.16138, 12.63428], +7.06177 [5.21240, 9.08203] and +7.83691
[6.98837, 8.94165] points. All three pooled intervals and both directional
intervals in each stratum are positive. Each stratum has some negative or
tied pooled lives; these are not additional independent replicates or a
demonstrated serial trend. All three pooled specificity intervals are positive,
but stratum 2 includes a negative block.

| Qualified target agreement | Feedback, mean (individual range) | No feedback, mean (individual range) |
| --- | --- | --- |
| Pattern A | 93.29% (87.89–96.09%) | 91.57% (85.94–95.31%) |
| Pattern B | 87.19% (67.97–94.14%) | 69.60% (54.69–89.45%) |

Ideal agreement is 95.16% / 92.24% and zero 41.83% / 42.74% for A / B.
There is substantial individual variation, especially B; no uniform high-
fidelity, equivalence or categorical 80% claim follows.

## Verification and provenance

Before main futures, 435 tests passed in 192.16 s: 147 D125, 114 D124 and
174 D123, no failures/errors/skips. Disposable full-life replay took 8.968 s;
the known six-writer/six-reader bridge test 4.218 s. Reports and fixtures
are external under logs/d125_tests_attempt1.xml and tmp/d125_tests_attempt1.
Four ASTs, shell syntax, Markdown links and original law/preprint/case pins
passed. No science or protocol edits after the passing suite.

The retained known bridge completed 2026-09-14 23:34:00.203536 UTC,
54.4844025886 s / 457,722 B after initial provenance preparation. All six
old source writer and six terminal reader paths reproduced exactly under
original and independently restated equations; both maximum errors were zero.
The freeze at 23:37:08.454247 UTC pinned 576 inputs with zero main futures;
SHA256 b9bda955e12b25f0962499e5170520580f2157bdeb1ef943cc5b072ecb3ecebe.
The six mutable trackers and this live review were explicitly excluded.

Main in-run independent replay covered all 384 source writer paths and 1,920
reader paths, with source/overall maximum state discrepancy zero in every
block. All 864 exact aliases passed. The separate completed saved-data audit
passes: 580 inputs / 19 outputs, metadata, source addresses, observations,
summary, verification counts, manifest/hash index and COMPLETE/STATUS agree.
This saved audit does NOT rerun dynamics; those were checked independently
during execution.

A separate NumPy/stdlib-only reconstruction, importing neither production nor
checker modules, independently verifies all 580 input and 19 output hashes,
384 primary packet constructions/bytes from source-final R, original D117
start addresses, zero initial theta, matching first source updates, both
terminal observers, all 168 contrast means, bootstrap intervals, block/life
values and sign counts, and all 864 aliases. Maximum statistic roundoff
1.1102230246e-16; packets, observations and aliases are exact.

No failed main run, retry, exclusion, deletion, cleanup, commit or post-freeze
science change. Earlier completed reviews/science/results and original
law/preprint/case files remain unchanged.

## Execution and retained artifacts

Disposable benchmark completed 2026-09-14 23:42:32.422334 UTC:
35.4306977075 s per checked block, 104.0170124890 s provenance check.
All 48 source writers / 240 readers / 108 aliases reproduced exactly.
Disposable outcomes were not used for qualification. Forecast
671.4796066377 s (~11.2 min) exceeded 600 s, so the main run was detached.
Budget 107,621,101 B (~102.64 MiB); benchmark 6,680,307 B; raw block 8,366,080 B.

Main preparation at 23:45:22.310294 UTC pinned 580 inputs; a separate flat
pre-launch hash check passed. Launcher acknowledged PID 2469819 with closed
stdin, a new session, six CPUs 0–5 maximum and an external log.
LAUNCH.json records 23:49:21.509742 UTC. No subsequent process/status/log/
outcome polling occurred until the user's 2026-09-15 status request.

Main COMPLETE: **2026-09-14 23:52:56.832663 UTC**, **215.3221850032 s**
after execution start (initial preparation/provenance excluded), with
**53,920,518 B / 51.42 MiB** of main outputs, below the frozen budget.
All data, fixtures, outputs and logs remain under
/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation; only code/docs here.
At audit time the workspace is about 17 MiB, external free space about
104 GiB and root free space about 5.8 GiB.

- [Summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_source_feedback_v1_attempt1/summary.json):
  SHA256 5d42e89cda7b689b8993cc31541718acac9c2ea8724b35ce5e0fbf73970d99c7.
- [Verification](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_source_feedback_v1_attempt1/verification.json):
  SHA256 4c2bf6f79c92d19c3d1da2fb010b570a912a8058ef43a02bc90794775709a26c.
- [Manifest](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_source_feedback_v1_attempt1/MANIFEST.json):
  SHA256 7da570e5e988d8c0d08ed56e2b867e93001da883506d956262ca08871425e3ab.
- [Completion](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/runs/l20_source_feedback_v1_attempt1/COMPLETE.json):
  SHA256 68dc22a5299fdfc421f5ac032e87bc5bff80e432180817d2789512cf22db9b49.
- [Detached log](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/logs/l20_source_feedback_v1_attempt1.log).

## Law verdict and next proposal only

D125 adds bounded fresh-reader E5 evidence for source-maintenance feedback.
It does not reverse D124's negative added-final-theta-value result, D123's
relative history/noise benefit or D117's engineered three-boundary renewal.
L20 stays STRESS_TESTED / MIXED, not a confirmed universal law.

Removing source theta feedback also removes a restoring force. Even with
readable, shuffle-specific outgoing packets, this does not distinguish
content-specific source feedback from generic reinforcement/stabilization.
There is no force-matched or wrong-content source arm. Earlier instructed
acquisition and theta-supported ancestry remain; no new feedback-off lineage,
autonomous ontology, learning-only disposition, necessary lambda << rho,
uniquely stationary noise filtering, natural genome, biological canalization
or E6 claim follows.

Next proposal, requiring approval and a new frozen protocol: matched-strength
wrong-content SOURCE feedback, retaining both target roles and the fixed
reader assay, with an explicit check of applied-force differences. Ask
whether the right feedback content matters beyond added stabilization.
Norm matching alone must not be called exact force matching. No new threshold,
rate/norm sweep, successor code/protocol/identities or run launched.
