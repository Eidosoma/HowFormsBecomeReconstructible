# TT043 — packet usefulness with and without memory feedback

TT043 is complete and reviewed. It tests the effect of memory feedback on the
usefulness of the same actual preserved and late-written packets, with writing
off. Full excluded qualification took **19 minutes**; production took
**59 minutes 44 seconds on two CPUs**. Every physical continuation passed an
independent equation replay, and independent closeout reproduced all reductions.

The main finding is a timing-dependent interaction between the packet and the
receiving system's memory feedback. In the half-mixed residual/own panel, the
late-minus-preserved target-success effect is:

| Receiving profile | Updates | Feedback off (pp) | Feedback on (pp) | On-minus-off change in packet effect (pp) |
|---|---:|---:|---:|---:|
| Continuing body | 900 | -1.5625 | -1.1719 | +0.3906 |
| Continuing body | 1000 | -1.9531 | -4.6875 | -2.7344 |
| Fresh recipient | 900 | -1.7578 | +0.6836 | +2.4414 |
| Fresh recipient | 1000 | +1.5625 | -0.3906 | -1.9531 |

At 1000 updates in fresh recipients, feedback changes the late packet's relative
success advantage from +1.5625 to -0.390625 percentage points. This does not mean
feedback lowers either packet's absolute mean score: it improves the preserved
packet by +3.125 points and the late packet by +1.171875. The preserved comparator
benefits more. All four block interaction effects are negative at this horizon:
[-1.171875, -1.953125, -1.171875, -3.515625] points.

Paired variation remains. Without feedback, the late packet produces 17 harmed
injury cases, 211 ties and 28 gains; with feedback, 21 harms, 219 ties and 16
gains. The change in the packet effect itself is negative in 35 cases, zero in
204 and positive in 17. Each of these 256 cases averages its four original
receiving draws. They are dependent injury cases from 64 source positions in
four exposed blocks, not 256 independent replications. Source-position averages
and individual-draw counts remain separately available.

At 900 updates, the same fresh-recipient interaction is positive (+2.44140625
points). Its four block values are [+3.125, -1.171875, +2.734375, +5.078125].
Both horizons were specified before production. The sign change prevents a
general claim that feedback suppresses, enhances or stabilizes rewriting.
The fresh feedback-off packet effect itself changes from -1.7578125 at 900
to +1.5625 at 1000, so the earlier positive endpoint is not uninterrupted
advantage. The continuing 900-update point reproduces TT042 at absolute update
1900; its 1000-update point is absolute update 2000.

Continuous margins qualify the success-score result. At 1000 in fresh
recipients, late-minus-preserved mean target-versus-best-other margin is positive
with feedback off (+0.00709209) and on (+0.00790978). Its small positive
interaction (+0.00081770) differs from the negative success-credit interaction.
An average margin and tied-winner success credit measure different outcomes;
neither substitutes for the other or establishes general information capacity.

Other damage levels are retained. With intact packets, the mean late-packet
effect stays negative in both profiles and feedback settings at both terminal
horizons. With full replacement it stays positive. At 1000, full-replacement
continuing-body effects are +15.2344 points with feedback off and +6.6406 with it
on; fresh-recipient effects are +13.1836 and +13.7695. Feedback is therefore not
uniformly helpful or harmful across damage and receiving conditions. Individual
harms, ties and gains remain even where a mean feedback effect is zero.

Within each profile/draw, feedback gain is the only changed physical parameter:
c_m is 0 or 0.2, while memory updating rho stays 0.002. Initial V/ema/R, the
supplied finite float64 packet and forcing are paired. The profiles themselves
have different initial states and forcing, so their direct difference does not
isolate feedback. With feedback off, fresh R tracks V without feeding back;
V/ema/theta and readouts reproduce the original R-clamped assay, but R does not.
The two original clamped native assays were also replayed in qualification.

The feedback intervention affects packet usefulness in these simulated receiving
conditions. It does not by itself explain the whole TT042 body/recipient gap:
at 1000 updates with feedback off in both profiles, the continuing packet effect
is still negative (-1.953125) while the fresh effect is positive (+1.5625).
The useful next diagnosis is to cross saved receiving initial states with the
two forcing streams at fixed feedback and matched horizons. That would separate
the remaining state and forcing differences, retaining preserved/late packets,
all conditions and paired harms. It is proposed, not launched; no serial-writing
confirmation follows automatically.

All four exposed source blocks, three mixtures, two families, three body sources,
all histories/tasks, four masks, geometry strata and four role credits remain.
All seven contrasts, both ordered decompositions, six checkpoints, 900-to-1000
changes, paired signs, continuous margins and original-packet controls are saved.
The single continuing-body observation is not counted as four receiving draws.
The four original fresh draws and forcing were reused: new intervention
conditions are not new independent futures, capacity estimates or a fresh
population confirmation. Sparse checkpoints do not establish uninterrupted
performance. Earlier scientific classifications remain unchanged.

Production independently replayed all 2704 physical batches: 64,896 native
arrays matched exactly, 16,224 score checkpoints passed, and 34,560 saved anchor
arrays plus 20,736 saved anchor-score arrays matched. Closeout verified 8,168
retained output files, 4,008 consumed source files and eight additional source
tables; independently reproduced all 4,032 condition/block reductions and every
global summary; and checked 92,160 case/arm/draw endpoint vectors plus 2,211,840
continuous-margin entries. Physical dynamics were not rerun at closeout because
each continuation had already undergone full independent replay in production.
Qualification's serial/parallel equality passed; production did not repeat that
separate comparison. All processes have exited. No job or successor is active.

See [frozen report](runs/feedback_v1/REPORT.md), [findings](FINDINGS.json),
[closeout](CLOSEOUT.json), [protocol](PROTOCOL.md) and [execution](EXECUTION.md).


The user authorized the proposed receiving-state/forcing crossover.
[TT044](../TT044/README.md) now supersedes the no-successor status above:
excluded qualification and conditional production are launched. TT043 findings
and frozen artifacts are unchanged. No serial-writing confirmation is launched.


TT044 is now complete and reviewed: [receiving state and forcing](../TT044/README.md).
The relative packet effect depends on starting state, realized forcing and
observation horizon; a larger relative advantage can accompany lower absolute
success. TT043 frozen findings remain unchanged. No TT044 successor is active.
