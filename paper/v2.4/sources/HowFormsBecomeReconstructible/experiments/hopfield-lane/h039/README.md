# H039 — Fresh-network confirmation of serial guidance

**Completed at 22:12:06 UTC on 17 October 2026**, with all **88 fresh networks**
retained and all three frozen verdicts passing. Independent closeout passed
at **10:16:22 UTC on 18 October**, following the user-requested status check.
Main run `runs/h039_confirmation_v1` took **3h48m00s**, including **2h54m52s**
of shared CPU-capacity waiting. Controller **895323** has exited.

At generation 16, both-rule success in fresh recipients is:

| Guidance during reconstruction | Final assay gain | Joint success |
| --- | ---: | ---: |
| Original (4) | 4 | 19.5135% |
| Original (4) | 8 | 29.3857% |
| Stronger (8) | 4 | 49.6094% |
| Stronger (8) | 8 | 74.2543% |

All three decisions retain their own endpoints:

| Verdict | Improvement | Marginal 95% interval | Family-adjusted directional lower |
| --- | ---: | ---: | ---: |
| **SERIAL_GUIDANCE_CONFIRMED** | 44.8686 points | [39.5064, 50.0710] | 37.5888 points |
| **ORIGINAL_READER_BENEFIT_CONFIRMED** | 30.0959 points | [26.5803, 33.4872] | 25.3196 points |
| **UNINTERRUPTED_INHERITANCE_CONFIRMED** | 72.8693 points | [67.8977, 77.6989] | 66.0511 points |

The primary compares reconstruction gains 8 versus 4 at the same final assay
gain 8. The original-reader comparison uses the same final gain 4. Stronger
reconstruction helps on **82/88 networks** in the primary contrast and harms
six; the original-reader contrast has **81 positive, one tied and six negative**
network effects. No network was excluded. Strong guidance yields successful
bodies at every one of sixteen replacements in **518/704 related paths
(73.5795%)**, versus **5/704 (0.7102%)** under ordinary guidance; **87 networks
improve and one ties**. The 88 networks remain the inferential units.

Protected copying still reaches **99.4851%** under the same terminal gain-8
assay. Strong renewal is **25.2308 points lower**, marginal 95% interval
[-30.1669, -20.5611]. Its own joint success falls from **99.3786%** at generation
zero to **74.2543%** at generation sixteen. This confirms mitigation of serial
loss under supplied machinery, with continuing attrition and a copying deficit.

Content remains necessary and specific. The three selective donor arms give
**74.2543% donor-joint success**, while original-joint success is **1.1186%,
0.7813%, and 0%** for foreign A, B and both. Erased acquisition, scrambled
records, read-off, write-off and damaged copying give zero terminal joint
success; scrambled writing gives **0.2841%**. All nine declared control contrasts
and all positive controls pass. Single-rule terminal trained success at gain
8/8 is **99.7159% for A** and **100% for B**. Zero observed failures do not
establish zero population risk.

All **15 fixtures and 67,584 retained numerical/boundary checks** pass, including
**61,952 confirmation checks**. Independent matching-bit closeout reproduced
all **254,496 CSV rows**, source/input seals, fresh-base provenance, network
weights, paired effects, and the complete 100,000-draw bootstrap and decisions.
It took **104.077 seconds**, generating no new trajectories or predictor fits.
The PNG figure was inspected; PNG/PDF and all raw evidence are retained.

Engineering smoke `runs/h039_smoke_v1` completed at **18:23:52 UTC**, in
**8m55s**, including **7m of CPU-capacity waiting**. All **15 controls and 704
numerical/boundary checks** passed. Its regenerated baseline and factorial
match all **25 archived source/raw arrays** exactly. Full block generation,
compression/I/O, replay and summaries took **98.836 seconds**. Independent
closeout completed at **18:24:03 UTC**, in **5.603 seconds**, reproducing all
**2,892 CSV rows**, seals, source equality and aggregates. The seven new
confirmation fixtures include a separate network-count bootstrap check;
the engineering block itself receives no population inference or verdict.
The figure was inspected; PNG/PDF are retained.

Stage controller **894061** and engineering controller **892986** also exited.
The 88-network cohort, model and decision rules are unchanged. No later
experiment has launched.

The [protocol](PROTOCOL.md) tests H038's development lead on **88 fresh base
networks**, IDs **39039000–39039087**, under the unchanged input law. The
historical internal RNG stream name is `pilot`; these new, unused IDs form
the confirmation cohort, with no development observations pooled into it.
Fresh input generation began only after the worker-count decision was sealed.

The four settings remain reconstruction/assay gains **4/4, 4/8, 8/4 and 8/8**.
Keep sixteen replacements, three loads, four histories, two descendants,
eight primary readout probes and all eleven arms. No dynamics or writer
change. The separately retained baseline audit probe is excluded from primary
averages. The source implementations must match the sealed H038 snapshot.

Three explicit verdicts:

- **Serial guidance:** at generation 16, 8/8 renewal must exceed 4/8 renewal
  by at least ten percentage points, with a positive adjusted lower bound.
  It must also pass all nine non-protected content/control comparisons,
  useful joint success and initial/protected-copy positive controls.
- **Original final reader:** 8/4 minus 4/4 must exceed the same effect and
  directional-bound thresholds; eligible only after the primary qualifies.
- **Uninterrupted inheritance:** the difference in paths successful at every
  replacement must pass those thresholds, with at least half of strong-guidance
  paths successful throughout; eligible only after the primary qualifies.

The twelve directional comparisons share a Bonferroni family at .05, using
100,000 joint whole-network bootstrap draws. Histories, descendants and probes
remain related observations within each network. Report all failed gates,
protected-copy deficits, attrition, single-load outcomes and the complete
factorial regardless of verdict. No numerical gate failed. Percentile inference
is approximate. The attained marginal interval half-width exceeded the planned
five points for two endpoints: **5.2823 points** for the primary and **5.1758**
for own-minus-foreign-A. Precision is not a decision gate; the sample was not
resized after outcomes.

The [sample-size calculation](SAMPLE_SIZE.json) uses only H038's eight
development summaries. It targets marginal five-point 95% interval half-widths
for 22 declared endpoints using sample SD inflated by 50%, a minimum of 64,
and rounding up to eight. The primary serial effect requires 86 networks;
rounding gives **88**. This is an approximate precision plan, not a guarantee
or a power calculation. There is no interim resizing, outcome-based exclusion
or replacement seed.

Engineering uses only exposed blocks 0–3. The smoke passed the eight
unchanged dynamics controls plus seven confirmation-decision controls, every
independent numerical replay, and exact source/raw equality with H038. The
[independent verifier](closeout.py) reconstructs every saved table with a
matching-bit observer and checks inference with network-frequency weighting.
The stage controller ran it on engineering before launching confirmation.

The main run measured **384.923 seconds serial versus 114.149 seconds with
four workers**, including baseline generation, compression/I/O, full independent
replay and summaries: **3.3721x speedup**. All **100 source/intervention arrays**,
audits and summaries agree exactly. Four workers were selected at **18:34:07
UTC**, before fresh inputs, under the frozen below-90%-of-serial rule. Numerical
threads were one per worker, with shared admission under twelve CPUs. The
confirmation stage took **2,624.332 seconds (43m44s)** excluding admission.

Engineering source/configuration freeze:
`339debf3bd478631abcfe91a62f318fa700b81703ed9087c066788a452c36ab2`.
Stage-controller freeze:
`e784451d1c3da9bc4111e83d640fb596b0e676e859d49d7ea7100021e3106fe2`.
Main source/configuration freeze:
`521521bd72ab892d30623ece2280162a8cf5b4fbeb0e7c6cabd2f6bcf3fee539`.
Final run manifest SHA-256:
`7071229cd64afb37b2bf90e80303428c34416a5024839a10d9147d74a84a6623`.

[Report](../runs/h039_confirmation_v1/REPORT.md) ·
[Inference](../runs/h039_confirmation_v1/inference.json) ·
[Figure](../runs/h039_confirmation_v1/overview.png) ·
[Main completion](../runs/h039_confirmation_v1/COMPLETE.json) ·
[Independent full verification](../.cache/h039_closeout_v1.json) ·
[Main launch](../runs/h039_confirmation_v1_launch.json) ·
[Engineering completion](../runs/h039_smoke_v1/COMPLETE.json) ·
[Independent engineering verification](../.cache/h039_smoke_closeout_v1.json) ·
[Stage-controller status](../runs/h039_pipeline_v1/STATUS.json) ·
[Stage-controller launch](../runs/h039_pipeline_v1_launch.json) ·
[Frozen scientific settings](../runs/h039_confirmation_v1/config.json).

The main run and independent closeout are complete; do not repeat the campaign.
The verifier refuses an occupied output destination. H031's separate causal
result and forecasting failure, H033's two negative verdicts, H034's diagnosis
and H035–H038's results remain unchanged. This confirms the declared inheritance
intervention under this model; it does not establish evolved reconstruction
machinery, universal robustness or an RDT forecasting advantage. No private
AI-lane material, manuscript edit or public release is included.
