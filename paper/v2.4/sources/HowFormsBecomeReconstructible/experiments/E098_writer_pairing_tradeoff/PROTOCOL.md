# E098 — writer cue pairing and the pruning penalty

23 October 2026. Authorized after E097. Test a causal dependency proposed from
known outcomes; the scientific sources will be new. No outcome-based selection.

## Fixed apparatus and planned sample

Candidate sample: **32 new independent blocks, 980000–980031**, four founders,
four recipients, native/mixture × sham/pulse, two terminal draws. Use the E077
recovery/writer stream recipe, for which the original fresh-source tradeoff was
confirmed. Do not split the sample into two underpowered recipe subgroups.
After the excluded benchmark, freeze this unchanged sample in SAMPLE_FREEZE.json
if it fits the resource bound. Otherwise report the constraint without generating
scientific sources. The sample is not selected from technical outcomes.

Source acquisition, 32 ancestry rewrites, pulse/sham and three continuation
rewrites follow unchanged E065/E068 equations and streams with new source IDs.
One E077 recovery produces the selected restored fallback edges. Preserve the
intact I0 record; construct P0 by deleting exactly those originally selected
weights. Preserve the erased control. No old scientific packet or score enters.

Cross intact/pruned input with writer cue-noise correlation rho=1 or rho=0 in
one subsequent rewrite. Initial activity stays shared across cues. The first
cue keeps the unchanged E077 Gaussian stream. At rho=1, copy it to the second
cue exactly; at rho=0, the second cue uses an independent E098 innovation stream.
Share both streams across all input policies. Marginal amplitude remains .02;
birth SD .05, dt .2, beta 3, float64, natural normalization and no denominator
floor remain. Injury removes 24 non-port cells, shared across the four conditions.

Read 2048 updates with 1024 settling, retain the final 32 observations, capture
from the final read state, then hold 128 updates with the unchanged paired noise.
Capture uses cue contrast unless its product is exactly zero, then ordinary
coactivity. Noise affects only the writer read phase. Terminal assays keep paired
cue birth/noise, independent of the writer, with the unchanged 2048/1024/32 schedule.
Both fresh terminal draws are matched across all records and both endpoints.

Terminal packet order is I0/P0/erased (nine slots), paired-writer outputs
(nine slots), independent-noise-writer outputs (nine slots). Immediate outcomes
are read once per draw, not repeated as independent samples under future writer
conditions. One writer realization supplies both terminal draws. Total source
contexts 2,048; terminal context/draw rows 4,096; terminal cue observations
55,296; manipulated-writer cue observations 18,432, apart from source ancestry.

## One prediction and inference

For pooled mixtures define D(rho)=success(P1,rho)−success(I1,rho). The frozen
directional conjunction requires both **D(0)−D(1)>0** and
**success(P1,0)−success(P1,1)>0**, each with a strictly positive 97.5% paired
whole-block bootstrap lower bound. Use 10,000 shared block resamples over the
32 source blocks, with equal within-block arm/founder/recipient/draw weighting.
Two adjusted intervals give the approximate nominal 95% family target. Rows,
reader draws and edges are not independent histories.

Report each primary contrast as positive, negative or unresolved. Separately
retain the paired baseline pruning contrast and its descriptive 95% interval.
Claim attenuation of a demonstrated penalty only if the primary conjunction
passes and that baseline interval is negative. If the conjunction passes but
baseline cost is unresolved, report the gain/interaction without claiming a
demonstrated penalty was attenuated. Do not call worsening intact performance
alone a rescue: actual pruned improvement is part of the primary conjunction.

Three percentage points is a declared practical reference, not a different
primary threshold. Report whether each adjusted interval lies above, below or
across .03. With no prior estimate of the writer-noise interaction's variance,
do not claim assured power for that effect. Use the fixed 32-block sample and
its uncertainty, with no extension or changed threshold after outcomes.

Native results, sham/pulse subdivisions, each draw, writer-end and writer-window
scores, margins, signed/aligned transfer and remaining contrasts are secondary,
pointwise descriptive 95% intervals. Keep every individual gain, harm and zero,
both four-by-four I0/P0 versus I1/P1 tables, conditional denominators, and exact
same-context event recurrence across terminal draws. Do not select only sources
that initially succeed. Erased controls are measured, not assigned zero scores.

## Mechanism evidence and limitations

For every available originally selected edge retain availability, restored
nonzero counts, exact-fallback and contrast counts, cue-independent m_i*m_j and
cue-dependent d_i*d_j terms, magnitude sums and sign changes. Save uninjured,
writer and terminal effective weights, denominators, normalized couplings and
selected coupling shares. Empty denominators get an explicit zero-available
flag; natural zero coupling remains zero. The shares include all receivers and
are structural diagnostics, not fractions of functional mediation.

Verify ordinary coactivity equals m_i*m_j+d_i*d_j numerically. Noise changes
activity beyond fallback selection. Even a positive interaction and changed
branch use establish a writer-pairing dependency, not exclusive fallback
mediation or a general repair rule. Earlier E051 pairing outcomes and E097
subgroups motivate the test but are not pooled into the new evidence.

## Checks, timing and retention

Independently replay every source, manipulated writer and terminal update, with
state hashes, saved final fields, source packets and noise commitments. Construct
pruning independently. Independently score the final writer state and window,
all terminal outputs, branch diagnostics and full event tables. Verify the
rho=1 branch byte-for-byte against the frozen E077 implementation on archived
excluded benchmark inputs and fresh fixtures. Check zero-noise equivalence,
equal marginal-noise construction, shared birth/injury, strict threshold, all
binary combinations, absence of outcome filtering and exact CSV roundtrips.

Excluded fixture IDs 9000982/9000983; benchmark IDs 9000980/9000981, one recipient
and shortened configured read schedules. The benchmark covers complete source
generation, both writers, both terminal draws, audit and summaries. Archive
projection to old block 900041 is disabled for new excluded IDs only; equations
and requested schedules remain unchanged. The archived 900041 equivalence test
is separate and excluded from science.

Forecast acquisition separately, read/update durations and recipient scaling
for source stages, and four recipients × four read length for the post-source
pipeline (a conservative overcount for unchanged holding). Use the slower
benchmark block, threefold timing allowance, 180 seconds for summaries and a
1.5 storage reserve. Up to four one-thread workers, at most twelve CPUs across
jobs. Require the conservative scientific forecast at selected capacity to fit
twelve hours; routine resource review may be documented before scientific
generation if needed, without altering the sample based on outcomes.

All work stays inside experiments. Refuse existing run paths, retain failures
and frozen inputs. Jobs forecast above ten minutes detach with /dev/null input,
unique log/PID/status and one bounded startup check; no automatic status polling,
restart, sample extension or successor. Manuscript integration remains separate.
