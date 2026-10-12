# Hopfield reconstruction lane

This lane tests whether selected mechanisms in *How Forms Become
Reconstructible* survive translation into small Hopfield networks. The initial
decision is to keep `hopfield-lane`, using both binary and graded-response
Hopfield dynamics. The latter is needed for a minimal model of transmission
readiness beneath identical coarse labels. Neither implementation claims to
replace the cellular simulator's molecular model.

The first experiment is [H001](PROTOCOL.md), an exploratory feasibility suite.
[Results](runs/pilot_v1/REPORT.md), [numerical summary](runs/pilot_v1/summary.json),
[figure](runs/pilot_v1/overview.png), and [integrity audit](runs/pilot_v1/AUDIT.json)
are retained with raw arrays and frozen sources. Results belong to this lane;
the main manuscript has not been edited. See [the discovery log](DISCOVERY_LOG.md)
for the bounded interpretation and next experiments.

The approved [research ladder](RESEARCH_LADDER.md) starts with selected private
replications, then tests complete rewriting, reciprocal repair and continuation
in the forms models. It ends with fresh confirmation of a limited forms
contribution; discovery of inherited competence is a later milestone.

[H002](h002/PROTOCOL.md) completed on 24 fresh base networks through 16
replacements, comparing complete versus retained rewriting and eight versus
four cue sites. In the four-site primary panel, capture passed its development
gates for both writers (52.86% and 53.39% terminal completion). Taught function
failed for both: own records gave 29.43% and 29.95% completion, close to the
foreign-record controls. Protected copying remained stronger. All 3,224
retained-data checks passed; runtime was 11 minutes 28 seconds.
See the [report](runs/h002_development_v1/REPORT.md),
[summary](runs/h002_development_v1/summary.json),
[figure](runs/h002_development_v1/overview.png) and [H002 usage](h002/README.md).
These are prospective development results, with separate task verdicts;
publication confirmation remains a later step.

[H003](h003/PROTOCOL.md) followed the functional failure with a fixed cue-coupling
intervention. On 24 fresh networks, gain 4 throughout the lineage raised G16
function from 31.51% to 89.58%; gain applied only to the final read reached
45.31%. Extra settling time left baseline outcomes unchanged. All prespecified
development gates and 970 integrity checks passed. Foreign records primarily
directed their donor's opposing rule, and protected copying still performed
better. See the [report](runs/h003_development_v1/REPORT.md),
[summary](runs/h003_development_v1/summary.json),
[figure](runs/h003_development_v1/overview.png) and
[preceding diagnosis](runs/h003_diagnosis_v1/REPORT.md).
The intervention adds supplied reader coupling; the writer remains body-only.

[H004](h004/PROTOCOL.md) confirmed the selected result on 72 fresh networks,
seeds 14000–14071, through the same 16 replacements and complete control set.
Sustained gain 4 achieved **92.53%** terminal function, versus **30.90%** at
baseline and **43.14%** with gain applied only to the final read. Every primary
gate, all 17 adjusted directional contrasts, and the subsequent timing claim
passed. Protected copying remained stronger at **98.87%**. All 3,334 retained
checks and four scientific fixtures passed; runtime was 24 minutes 39 seconds.
The finished artifacts' checksums were verified and the figure inspected.
This is confirmation within the specified supplied model, not an architecture
comparison or a useful-repair result. See the
[report](runs/h004_confirmation_v1/REPORT.md),
[summary](runs/h004_confirmation_v1/summary.json),
[figure](runs/h004_confirmation_v1/overview.png) and [H004 details](h004/README.md).

[H005](h005/PROTOCOL.md) completed the matched-expression continuation study.
Of 384 paired H003 development checkpoints, 106 matched across all 24 networks.
With identical future apparatus and eight new branches through 16 more
replacements, terminal success was **83.46% versus 87.49%**. The gain-4-history
advantage was **4.03 percentage points** [95% interval 1.97, 6.18], below the
frozen ten-point minimum: **H005 does not qualify**. Current validation passed
the declared five-point equivalence bounds, with success **96.53% versus
98.11%**; this is approximate observer equivalence. All other gates, nine
fixtures and **9,429 audit checks** passed. Runtime was 17 minutes 19 seconds.
At closeout, 41 of the 106 matched pairs had identical complete packets; both
groups retained nearly maximal cue association. These descriptive findings
motivate direct packet interventions, without changing the cohort or verdict.
See the [report](runs/h005_development_v1/REPORT.md),
[summary](runs/h005_development_v1/summary.json),
[figure](runs/h005_development_v1/overview.png) and [H005 details](h005/README.md).

[H006](h006/PROTOCOL.md) completed direct, strength-preserving record
interventions. Four balanced sign flips were the only dose passing selection;
195 matched packets across 16 separate development networks then passed the
one-point current-equivalence bounds. After 16 further replacements, renewal
success was **89.59% unchanged, 89.65% with cue-to-output flips and 89.46% with
cue-to-hidden flips**. Both planned durability contrasts failed:
**H006 does not qualify**. Ten scientific fixtures and **7,159 audit checks**
passed; runtime was 17 minutes 21 seconds. A post-result inspection found
99.56% and 99.42% exact agreement with the unchanged branch's packet after
just one replacement/write, averaging networks equally. The intervention
differences usually vanished immediately; this diagnostic leaves the frozen
verdict unchanged. See [H006 details](h006/README.md), the
[report](runs/h006_development_v1/REPORT.md),
[figure](runs/h006_development_v1/overview.png) and
[closeout diagnostic](h006/CLOSEOUT_DIAGNOSTICS.json).

[H007](h007/PROTOCOL.md) passed its development feasibility screen on all four
hidden-pattern swap sizes. The frozen rule nominates the largest, **eight
hidden-neuron pairs**, with **244 matched packets across all 24 networks**.
Current success was **97.67% unchanged versus 97.87% swapped**, passing all
one-point equivalence bounds. After **one damaged replacement**, both distinct
intended records were retained exactly with functional rebuilt bodies and
fresh readers in **94.15%** of paired trials, averaging networks equally
[95% interval 93.04, 95.16; adjusted lower 92.65]. Read/write blocks reduced
this joint event to zero. Ten fixtures and **7,011 audit checks** passed;
runtime was 11 minutes 22 seconds. Checksums verified and the figure was
inspected. This establishes one-replacement feasibility within the development
cohort; differing long-term durability remains untested. See
[H007 details](h007/README.md), the [report](runs/h007_development_v1/REPORT.md)
and [figure](runs/h007_development_v1/overview.png).

[H008](h008/PROTOCOL.md) completed with **PRESENT_GATE_FAILED** after 49 seconds.
Fresh validation of H007's fixed 244 pairs gave current success **97.02%
unchanged versus 97.67% swapped**. The adjusted success-difference interval
was **[0.28, 1.04] points**, and two output intervals were **[0.47, 1.62]**;
these exceed the required ±1-point equivalence bounds. As frozen, the study
generated **no sixteen-replacement futures**, with no rematching or fallback
dose. All 15 fixtures and **896 audit checks** passed; checksums verified and
the figure was inspected. This is a failure to establish current equivalence
on fresh probes; long-term durability remains untested. See
[H008 details](h008/README.md), the [report](runs/h008_development_v1/REPORT.md)
and [figure](runs/h008_development_v1/overview.png).

H001 completed on 12 independent blocks. After 16 replacements, capture
completion was **59.9%** and taught-function success **43.2%**. Both exceeded
copying with accumulated damage and trailed protected copying. Surviving
arrangement mattered, but the stronger useful reciprocal-repair effect was
unresolved. The continuous screen produced preparation-dependent transmission
and editable relays, while the tested pause rescue failed. Six invariant tests
and 2334 retained-evidence checks passed. These are exploratory results.

## Source review and scope

The authoritative forms text found here is [MANUSCRIPT.md](../../MANUSCRIPT.md),
working v0.17, dated 10 October 2026. Its assembled source is
[PRE_PRINT_PAPER_DRAFT_V0.17.md](../../PRE_PRINT_PAPER_DRAFT_V0.17.md).
[Plastic Heredity v5.0](../../../PlasticHeredity/PRE_PRINT_PAPER_DRAFT_V5.0.md)
retains the v4 results and changes discussion/citation placement. Its core
cutoff is 24 August, with an identified 7 September reproduction update.
[SOURCE_REVIEW.json](SOURCE_REVIEW.json) records file hashes and public sources.
The sibling reference available in this checkout is `../theory-lane`; there is
no `../theory-main` directory.

Plastic Heredity distinguishes an episode of broken and restored resemblance
from acquisition and renewal of a carrier. Forms distinguishes acquisition,
present expression and capacity to support a successor. H001 centers the
latter distinction. It does not equate the number of break-and-renewal events
with better inheritance, or repeat a fixed-attractor recall demonstration as
the proposed contribution.

| Existing forms experiment | Translation in H001 | Material difference |
|---|---|---|
| E001/E004/E014: unprescribed development, capture and replacement | Four uninstructed founders per random network; activity writes a record; compare own and foreign records through fresh bodies | Dense binary neurons and a symmetric weight record; no physical tissue geometry or compact 16-value carrier |
| E041: taught two-rule function through damaged reconstruction | Input/output teaching once, then input-only reads and complete coactivity rewriting after each edge injury | Different reader, writer, connectivity, damage and horizon; no cue-difference writer or reader normalization |
| D073/D074: reciprocal repair and surviving arrangement | Matched damaged record; kept/shuffled survivor values; fixed/live reader feedback; assay the resulting record in a fresh body | Coordinate organization in a dense graph; not a replication of a spatial voltage field |
| BITSEY P11: editing actual descendants and complete membership replacement | Three continuous units, finite induction/revision cues, tracked surviving members and serial newcomers | Three state variables; no ionic species, RNA transport, cell mechanics or biological time calibration |
| BITSEY P20/P26: preparation and communication timing | Equal positive sign labels with different amplitudes; isolated preparation and scheduled contact pauses | A bounded state-space analogy; each parameter panel is deterministic and related |

The functional sheet already uses reciprocal neighbor couplings and local
coactivity. Calling another implementation a neural network alone would add
little. H001 changes the dynamics and observation boundary while retaining
the causal questions. Effect sizes across these apparatuses are not pooled.

## Why retain Hopfield, and which alternatives matter?

The classical model provides associative completion and a checkable energy
function for asynchronous symmetric dynamics. H001 uses that as an instrument,
then adds explicit acquired records and replacement boundaries. Recall itself
is established prior art. [Hopfield, 1982](https://authors.library.caltech.edu/records/w41x7-8bn13)

Graded-response Hopfield dynamics retain continuous internal states and
associative behavior. H001 uses `du/dt = -u + W tanh(2u) + I`, with symmetric
couplings, for the three-unit model. Under fixed couplings and zero external
input the implementation checks energy descent. Weight writing, cue changes
and replacement are interventions; no global descent claim spans those
operations. [Hopfield, 1984](https://doi.org/10.1073/pnas.81.10.3088)

There is a direct reason to retain amplitude: with fixed apparatus and no
hidden variables, identical complete binary states have identical future
distributions. Three identical binary signs cannot themselves represent
different readiness. Continuous states allow the same coarse sign labels to
hide different distances from a transition boundary. This is a model-design
argument, not a claim that amplitude alone explains the molecular results.

| Candidate | Assessment for this lane |
|---|---|
| Binary Hopfield with a writable record | Useful first benchmark for acquisition, content/address interventions and complete rewriting. Exact energy checks make implementation failures easier to detect. |
| Graded-response Hopfield | Best current addition for the readiness question: retains amplitude, time and symmetric interaction with little extra apparatus. Remains in the same model family. |
| Modern Hopfield / attention memory | Attractive for larger associative capacity, but its stored patterns or learned prototypes must be counted at the transmission boundary. High recall capacity does not answer whether a body renews its record. No need for that extra machinery in H001. |
| Neural cellular automaton | A plausible later choice if growth, locality and changing spatial anatomy become the main target. It adds learned update rules and training history that need separate accounting. |
| General asymmetric recurrent network / regulatory model | Consider if directed transport, oscillation or richer cellular state is essential to a failed translation. Fixed symmetric gradient dynamics cannot reproduce every such mechanism. No comparative performance claim has been tested here. |

The modern associative alternative is described by
[Ramsauer et al.](https://arxiv.org/abs/2008.02217); the growth, persistence and
regeneration alternative by [Mordvintsev et al.](https://distill.pub/2020/growing-ca/).
The choice above is an inference from the task requirements and model
structure, not a completed architecture competition. A rename to a broader
recurrent-network lane would be justified if future experiments require
asymmetry or learned local update dynamics.

## Information boundary and publication policy

Private neural work was reviewed as background. It contributes no quoted text,
reported result, imported implementation, dataset, trained state or citation to
the forms-facing artifacts here. The private reading inventory is git-ignored
under `private/`; it must be excluded from a release bundle. These new
experiments are not described as source-isolated: the existing forms model code
and related research protocols were read before implementation.

H001's equations, scripts, seed tapes and observations are self-contained. The
writer in the serial assay receives only current activity, and a fresh assay
receives only the resulting record plus the shared apparatus. The repair assay
explicitly retains an old-record component, whereas the graded relay transmits
the complete state of surviving members. These are three different boundaries.

The 64-neuron record contains 2016 unique float64 edge values, occupying 16128
bytes as a packed symmetric payload; raw arrays here use a full 32768-byte
matrix. Shared base weights, input conventions and update schedules are extra
apparatus. Dense redundancy is supplied and has not been optimized. The
three-unit model transmits live state through turnover, not this weight packet.

## Reproduction

From this directory:

```bash
bash run_python.sh tests.py
bash run_python.sh run.py --output runs/NEW_RUN --blocks 12 --generations 16 --seed-start 11000
bash run_python.sh audit.py runs/NEW_RUN
```

An existing output directory is rejected. The commands above repeat the pilot
cohort; a fresh directory is not fresh evidence. To reproduce frozen code after
later development, use `runs/pilot_v1/source/run.py` from that snapshot and an
output directory within its own source tree. To run with another Python
environment, set `FORMS_PYTHON` to its executable. Only NumPy and Matplotlib are
required beyond the standard library; the exact executed versions are recorded
in the run and [requirements.txt](requirements.txt).

Execution follows [RUN_POLICY.md](../RUN_POLICY.md): one numerical thread here,
all artifacts local, no overwrites, and detached execution for forecasts over
ten minutes. The one-block two-generation benchmark is disposable development,
not evidence for a population effect. All scientific comparisons and failures
in the pilot remain visible in its report.
