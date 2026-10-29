# TT044 — receiving state and stochastic forcing

TT044 is complete and reviewed. Full excluded qualification took **10 minutes
58 seconds**; production took **70 minutes 32 seconds on two CPUs**. The whole
detached sequence took about **82 minutes** and finished on 27 October 2026 at
17:23:49 UTC. Independent physical replay and the separate saved-data review
passed. All processes have exited; no successor is running.

The result is a timing-dependent interaction between the supplied packet,
starting state and realized forcing. The same late-written packet can help or
hurt relative to preservation depending on the receiving conditions and readout
time. This diagnoses the remaining TT043 body/recipient gap within these exposed
conditions; it does not identify a generally beneficial starting state or noise
stream.

Feedback is off throughout (c_m=0); memory updating stays native (rho=0.002),
writing is off, and the supplied packet is held byte for byte. C/F mean
continuing/fresh. The first letter selects initial V/ema/R together; the second
selects the realized forcing stream. CC and FF are unchanged TT043 feedback-off
baselines; CF and FC are crossed conditions. The forcing law and amplitude are
unchanged. The continuing stream resumes after exactly 1000 Gaussian fields.

In the main half-mixed residual/own panel, all histories and masks, the
late-minus-preserved target-success effect is:

| State / forcing cell | 900 updates (percentage points) | 1000 updates (percentage points) |
|---|---:|---:|
| CC | -1.5625 | -1.9531 |
| CF | -1.3672 | +0.7812 |
| FC | +1.1719 | -0.7812 |
| FF | -1.7578 | +1.5625 |

At 1000 updates, switching only the forcing changes the packet effect from
-1.953125 to +0.78125 points in the continuing state, and from -0.78125 to
+1.5625 in fresh states. Switching only the state changes -1.953125 to -0.78125
under continuing forcing and +0.78125 to +1.5625 under fresh forcing. Thus the
mean sign at this horizon follows the forcing choice in this panel. It does
not do so uniformly across individual blocks or injuries.

At 900 updates, switching only the state under continuing forcing instead
changes the mean effect from -1.5625 to +1.171875 points. Switching only the
forcing in the continuing state leaves it negative (-1.3671875). With both
changes it is -1.7578125. Both horizons were predeclared. A single terminal
sign cannot establish a persistent advantage or explain the result generally
as either a starting-state effect or a forcing effect.

The 1000-update FF-minus-CC packet-effect gap is +3.515625 points. Both ordered
decompositions hold exactly: changing state first then forcing gives
1.171875 + 2.34375; changing forcing first then state gives 2.734375 + 0.78125.
These are conditional contrasts, not unique causal shares. Their three-way
interaction is -0.390625 points, but its block values are
[-6.25, -4.6875, +3.125, +6.25]. The small mean conceals substantial opposing
block effects. At 900 the interaction is -3.125, negative in all four blocks:
[-3.125, -3.125, -5.078125, -1.171875]. Four blocks provide limited population
information; no significance or confirmation gate was used.

Relative advantage must remain separate from absolute performance. At 1000,
switching the forcing in the continuing state lowers preserved-packet success
from 83.984375% to 72.65625% (-11.328125 points), and late-packet success from
82.03125% to 73.4375% (-8.59375 points). The late packet becomes relatively
better because preservation loses more. In fresh states, the same forcing
switch lowers preserved success by 6.640625 points and late-packet success by
4.296875. These are realized-stream effects, not evidence that fresh noise
improves overall performance or that changing the noise distribution helps.

Paired harms remain. The 1000-update packet contrasts across 256 injury cases
have the following harm/tie/gain counts; CF/FC/FF cases average their four
original paired indices, while CC retains its single actual condition:

| Cell | Harm | Tie | Gain |
|---|---:|---:|---:|
| CC | 9 | 243 | 4 |
| CF | 26 | 206 | 24 |
| FC | 8 | 242 | 6 |
| FF | 17 | 211 | 28 |

For CF, a positive mean coexists with more harmed cases than improved cases;
the sizes of changes differ. These cases come from 64 source positions in four
exposed blocks and are dependent. Position-averaged counts and paired-index
counts remain separate. The CC-only contrast has 64 paired-index observations;
other contrasts have 256, with CC reused only as a shared comparator.

Continuous margins give a different perspective. At 1000 the late-packet
target-versus-best-other margin effects in CC/CF/FC/FF order are
[+0.00236511, -0.00008677, +0.00673244, +0.00709209]. Their signs do not all
match the success effects. Margins and tied-winner success credit measure
different outcomes; neither substitutes for the other or estimates capacity.

Other damage levels are retained. With full replacement, all four cells have
positive mean packet effects at both terminal horizons, also positive in each
block: at 1000, +15.234375, +14.84375, +15.625 and +13.18359375 points in
CC/CF/FC/FF order. With intact packets, all eight cell/horizon mean effects are
negative except CF at 900, whose mean is zero and still contains harms and
gains. The diagnosis is conditional on damage as well as timing and receiving
conditions. All families, sources, tasks, histories, masks, four role credits,
six checkpoints, inherited original-packet controls and 24 contrasts are saved.

These are four exposed source blocks with reused starting states and forcing,
not new independent futures or fresh confirmation. The fresh index d pairs
state d and stream d; this is not a Cartesian product. State replacement
bundles V/ema/R. Sparse checkpoints do not establish uninterrupted performance.
Prior scientific classifications remain unchanged.

The proposed next step is a frozen fresh-forcing replication: restore these
same states and packets, use genuinely new paired forcing seeds, retain both
900/1000 horizons and all cases, and estimate whether the packet/state contrast
persists across futures. This would assess repeatability conditional on the
exposed records; new source records would still be needed for a fresh population
confirmation. No follow-up or serial-writing confirmation has been launched.

Production independently replayed all 3976 physical batches: 95,424 native
arrays matched exactly, 23,856 score checkpoints passed, and 69,120 saved
baseline arrays plus 69,120 saved observation arrays matched. Closeout verified
11,984 output files and 4,072 consumed source files; independently reproduced
all 4,032 condition/block reductions and every global summary; and checked
119,808 case/packet/index endpoint vectors and 2,875,392 margin entries.
CC denominators, all paired harms, and both TT043 baseline endpoints and margins
were checked. Physical dynamics were already independently replayed during
production and were not rerun at closeout. Qualification's separate serial/
parallel comparison passed; production did not repeat that comparison.

See [frozen report](runs/crossover_v1/REPORT.md), [findings](FINDINGS.json),
[closeout](CLOSEOUT.json), [protocol](PROTOCOL.md) and [execution](EXECUTION.md).


The user authorized the proposed fresh-forcing follow-up.
[TT045](../TT045/README.md) now supersedes the no-successor status above:
excluded qualification and conditional production are launched. TT044 findings
and frozen artifacts are unchanged. No serial-writing confirmation is launched.


TT045 is now complete and reviewed: [new paired futures](../TT045/README.md).
Full-replacement packet benefits persist in both states and at both horizons;
half-mixed effects remain small and time dependent. These are conditional
estimates on the same exposed source records. TT044 findings remain unchanged.
