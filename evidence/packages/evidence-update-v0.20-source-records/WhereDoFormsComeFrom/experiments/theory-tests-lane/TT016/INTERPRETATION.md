# TT016: prospective serial durability passes the practical primary

The registered fresh-cohort validation is **PRACTICAL_SUPERIORITY_PASS**.
Under independent ongoing cue noise, repeated repair achieves uninterrupted
success in 920/1,024 records (89.84%), compared with 794/1,024 (77.54%) without
repair. The gain is **12.30 percentage points**, with a two-sided 95% stratified
block interval of **9.71 to 14.90 points**. Its one-sided 95% lower bound is
**10.14 points**, above the practical margin of **5 points** frozen before
generation. The result supports repeated repair through successive rebuilding
within this apparatus.

All 64 new independent blocks, identities 16000000–16000063, contribute to the
primary. There are 16 blocks per history and 16 records per block. Every outgoing
generation-14 record was enrolled before continuation, including initial failures;
all eight policies continued through generations 15–32 after failures. Each branch
inherited its own actual body-written successor. Uninterrupted success requires
the intended task at all 18 rebuilds, with the unchanged strict margin > .25.
Later recovery cannot undo an earlier failure on this endpoint.

The independent units for inference are the 64 blocks. The primary uses the
registered stratified Welch–Satterthwaite calculation, with SE .0129507 and
58.1144 degrees of freedom; its Student-t coverage is approximate. The descriptive
stratified bootstrap interval is 9.96 to 14.75 points. There are 52 positive block
contrasts, 12 ties and no negative blocks. Paired record counts are 127 succeeding
only with repeated repair, one only without repair, 793 under both and 103 under
neither. No sample resizing, substitution, optional stopping or retuning occurred.

| Ongoing cue noise | Repair policy | Uninterrupted success | Terminal success |
| --- | --- | ---: | ---: |
| Matched | None | 458/1,024 — 44.73% | 823/1,024 — 80.37% |
| Matched | Once, at generation 15 | 557/1,024 — 54.39% | 868/1,024 — 84.77% |
| Matched | Every rebuild | 916/1,024 — 89.45% | 945/1,024 — 92.29% |
| Matched | Shuffled signs every rebuild | 0/1,024 — 0% | 70/1,024 — 6.84% |
| Independent | None | 794/1,024 — 77.54% | 880/1,024 — 85.94% |
| Independent | Once, at generation 15 | 856/1,024 — 83.59% | 912/1,024 — 89.06% |
| Independent | Every rebuild | 920/1,024 — 89.84% | 934/1,024 — 91.21% |
| Independent | Shuffled signs every rebuild | 0/1,024 — 0% | 87/1,024 — 8.50% |

All secondary intervals below are descriptive stratified block bootstrap 95%
intervals, without multiplicity adjustment. They do not replace the primary.
Under independent noise, a single repair improves uninterrupted success by
6.05 points [4.10, 8.11], and repeated repair adds another 6.25 [4.49, 8.11].
The single intervention also improves terminal success by 3.13 points [1.66, 4.59],
supporting consequences that persist to generation 32. Recurring intervention
supplies further benefit. These comparisons do not identify a passive maintenance
mechanism. Under matched
noise the repeated-minus-baseline gain is much larger: 44.73 points [40.82, 48.44].
The zero uninterrupted successes under shuffled signs show the importance of
the constructed sign arrangement relative to that control, but shuffled repair
can itself be damaging. The primary comparison with no repair establishes the
positive repair benefit directly.

Changing to independent noise raises baseline uninterrupted success by
32.81 points [29.20, 36.33]. Repeated-repair uninterrupted success changes by
only +0.39 points [-0.29, 1.07]. This interval does not establish equivalence.
Retain the less favorable terminal comparison as well: repeated-repair terminal
success falls from 92.29% with matched noise to 91.21% with independent noise,
a change of **-1.07 points [-1.86, -0.39]**. This unadjusted secondary interval
excludes zero. It does not negate the primary benefit over baseline, but it
precludes a broad conclusion that cue-noise pairing is harmless. Within the
independent regime, repeated repair still improves terminal success over baseline
by 5.27 points [3.71, 6.84].

The four history-specific independent-noise uninterrupted gains are 13.28,
10.55, 10.16 and 15.23 points for exact, single, spaced and clustered histories,
respectively. These are descriptive strata of the same cohort. Of the 1,024
generation-14 records, 180 initially fail and 844 initially pass. Repeated repair
versus baseline achieves uninterrupted success in 79 versus 57 of the 180 initial
failures, and 841 versus 737 of the 844 initial successes. The registered target
is the complete population and equal mixture of histories; favorable subgroups
are not additional replications or alternative primary targets.

Only ongoing cue-noise correlation changes. Teaching and birth/reset randomness
remain matched. Native forcing checks give correlation 1 in the matched regime
and .0000136169 in the independent regime. All independent-noise arms have zero
fallback writes. Matched baseline uses fallback on all 1,375,170 returning-edge
events; matched repeated repair does so on 187. These counts describe the writer
behavior and do not isolate a causal mediation mechanism.

Repeated repair requires 18,432 optimizer calls per noise regime, versus 1,024
for one-time repair and none for baseline. Allocated record bytes and reader
updates are fixed at 4,096 and 36,864 per record, respectively, but total computation
differs. Shuffled repair matches support, magnitudes and the sign multiset of its
own current input. Diverging histories produce different cumulative added weights;
this is not an exactly resource-matched comparison across entire trajectories.

The job completed at **2026-10-12T05:45:43.395128+00:00**, taking 46,736.585 seconds
(12 hours 58 minutes 57 seconds), against the conservative 18.91-hour forecast.
The first completion/result inspection in this lane was user-requested at
2026-10-12T11:08:13.632081+00:00. Full independent replay passes for all 64 teachings,
14,336 preliminary contexts, 147,456 continuation contexts, 75,776 optimizer checks,
17,472 native array comparisons and 1,152 generation-level forcing checks.
All native states and noise moments match byte for byte. Independent scoring
passes for 147,456 endpoints and 294,912 task flags. The largest scalar window
error is 6.66134e-16, versus a nearest threshold distance of 3.47366e-5; the maximum
resource summation discrepancy, 7.10543e-14, is within the fixed bound.

The executable closeout passes on its first execution. It verifies all 61 frozen
inputs in three retained copies, all 2,381 committed validation outputs and 13
benchmark outputs, registration/qualification chronology, enrollment seals and
every actual successor link. It checks fixed repair schedules and all 17,472
native array receipts, reconstructs endpoint summaries and all declared contrast
intervals, and reproduces the unchanged primary verdict. This post-completion
check uses saved evidence and generates no new trajectories. See the
[closeout receipt](CLOSEOUT.json). Pre-closeout documents and hashes are preserved
under `closeout_inputs/`.

Registration and qualification preceded generation of the new cohort. Prior
TT014/TT015 outcomes informed the design and remain exposed development evidence;
their lineages were excluded here. The namespace search checks accessible identity
collisions and does not establish independent custody or technical blinding.
This prospective result uses the same supplied simulator, lattice, pins, reader
and fixed repair solver. The repair reads the current record, which retains
learned history. These findings do not establish autonomous maintenance, transfer
to another apparatus, external replication, or a prediction unique to RDT.
All 64 TT016 blocks are now exposed. No successor experiment has been launched.

See the unchanged [protocol](PROTOCOL.md), [registration](REGISTRATION.json),
[saved analysis](runs/validation_v1/analysis.json),
[native audit](runs/validation_v1/NATIVE_AUDIT.json),
[scoring audit](runs/validation_v1/SCORING_AUDIT.json),
[completion receipt](runs/validation_v1/COMPLETE.json) and [execution](EXECUTION.md).
