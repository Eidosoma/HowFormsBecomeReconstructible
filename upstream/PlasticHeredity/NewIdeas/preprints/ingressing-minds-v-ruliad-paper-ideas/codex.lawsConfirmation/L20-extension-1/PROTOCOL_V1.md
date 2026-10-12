# D141 / L20-extension-1: fixed-budget challenge prediction, v1

Declared 2026-09-17 before extension development diagnostics or held-out
outcomes. This document is a prospective specification, not a result.
Freeze its hash with code, tests and sources before the development run.
Later corrections require an explicit version and reason, preserving originals.

## Question and scope

Under a fixed observation budget, does the response to one controlled record
perturbation predict retained acquired organization after three replacements
better than two undisturbed observations? Compare forecasts, not treatment
effects on the actual lineage: diagnostic copies never enter that lineage.

Reuse D135/D140's tissue, supplied target families A/B, fixed D131 learned
guide (SHA256 59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c),
2048-byte little-endian float64 record, reader, and translated/aligned writers.
This extension does not use the separate 64-byte DoorKey germ.
Both writers start with the same ordinary/translated F0 record, at exactly
the interface used in D135 and D140. The guide is public host machinery,
not transmitted or fitted anew. These are two supplied families, not learned
functional ontologies or a test of biology itself.

## Cohorts and retention

Development: all four lives, both families and both writers in D135 blocks
75000–75007 (underlying founder/host IDs 73000–73007) and completed D140 blocks
78000–78007. Thus 16 unique blocks, 64 lives, 256 cases. D132/D135/D136 share
founders and must not be counted as independent development cohorts.
Already-observed terminal outcomes may be used to fit development predictors.
New diagnostic probes of these founders are explicitly development work.
Disposable qualification uses D140 benchmark founder 514240, never a test case.

Held out: reserve IDs 90000–90015, all four lives per block, both families,
both writer modes: 16 new blocks / 256 forecast cases. Use a new, separate
founder/lineage namespace `l20-extension1-heldout-v1`. Do not pool these with
D140's registered replication. No selection on appearance, fidelity, guide
confidence, diagnostic response or future survival. A numerical/implementation
failure stops qualification and is reported; it does not silently remove or
replace a case. No fresh guide fitting or founder tuning.

## Diagnostic budget and perturbation

Both observers receive the same starting measurements, true family and writer
condition, plus exactly two complete read–rewrite–fresh-read cycles:

| Observer | Copy 1 | Copy 2 |
| --- | --- | --- |
| Passive | Intact U0 | Intact U1 |
| Challenge | The same intact U0 | Partially shuffled C1 |

The shared U0 reduces computational cost, not the information budget. U1 and
C1 use identical birth, read, write, final-read and writer-shift noise streams;
U0 uses an independent trial stream. All diagnostics are independent of the
actual lineage's noise. Pair streams across family/writer conditions within a
life. RNG inputs/host IDs/seeds are never predictor features.

Before the first guide routing, select 64 unique sites from the 256-site record
using the first 64 entries of a fixed seeded uniform permutation. Apply a
second independent uniform permutation only among those selected sites.
Selection and permutation streams are separate and shared across the four
family/writer cases within a life. No resampling, targeted weak-site choice,
reprojection, normalization or perturbation search. Uniform permutations may
have fixed points; record the actual changed-site count, not a claim that 64
values necessarily changed. Unselected entries, the complete value multiset,
mean and magnitude remain unchanged, to floating-point summation precision.
Call this a **25%-site shuffle**, not an established small functional dose.

Each diagnostic uses the frozen guide to route the incoming record, a new
300-step reader, a 1000-step writer starting from the reader's V/EMA/R with
latent theta erased, then a freshly born independent 300-step final reader
of the newly written and guide-routed record. The writer has no incoming
record, target, guide, previous theta or hidden-parent access. Only the ordinary
record is passed to each fresh reader. Diagnostic states/records are discarded
with respect to the actual lineage. Retain them externally for auditing only.

## Frozen feature interface

Four continuous starting features:

1. Maximum normalized own-template correlation over all 256 translations.
2. Own maximum minus alternative-family maximum template correlation.
3. Frozen guide's own-family maximum correlation minus its alternative maximum.
4. Canonical own-minus-alternative template correlation after ordinary guide routing.

For each allowed diagnostic copy, six continuous features: the same four
features of its outgoing rewritten record; final fresh-reader qualified
own-minus-alternative preference; final fresh-reader V root-mean-square strength.
Each full predictor therefore has 16 continuous features, in initial/U0/second
copy order. Family × writer supplies four categorical intercepts. The secondary
starting-only predictor has the first four continuous features and the same
intercepts. Raw pixels, intermediate body states, parent history, block/life ID,
RNG identity, future state, U1 for challenge, and C1 for passive are forbidden.
No challenge-minus-U1 feature: it would leak a third diagnostic copy.
Record RMS/mean, guide choice and changed-site count are saved as apparatus
measurements, not additional features. Record RMS is fixed by the .3 norm and
is not treated as independent predictive information.

Template correlations use mean-centered fields and population standard
deviation, with zero correlation for a zero-variance record. The terminal
qualified preference is (qualified own matches minus qualified alternative
matches)/256 with the existing strict |V| > .2 gate and V > 0 signs. It is not
conditioned on the active cells alone. Forecast outcome lies in [-1,1].

## Same simple predictor for both observers

Fit ridge linear regression with four unpenalized family × writer intercepts.
Center features and outcome within each group using training rows only; scale
centered features by their pooled training population SD (SD <= 1e-12 becomes
1). Solve mean squared residual + alpha * squared coefficient norm. Shared
candidate grid: [.001, .01, .1, 1, 10, 100]. Choose alpha separately for each
observer by leave-one-development-founder-block-out mean squared error;
all 16 related cases leave the fit together. Refit preprocessing in every fold.
Tie within 1e-12: prefer the larger alpha. Clip every prediction to [-1,1].
No extra nonlinear terms, architecture search, missing-value imputation or
test normalization. The starting-only secondary uses the identical procedure.
Refit selected models on all 16 development blocks, then save and hash their
coefficients, means, scales, feature names, alpha, CV records and source hashes.
Development CV scores are selection-affected exploratory diagnostics, not the
primary evidence and not grounds to change the registered challenge.

## Prospective seal and primary score

Before held-out founder generation, seal the final predictors and scoring
rules. Qualify the separate held-out executor using disposable founders, pin
its code/tests and the development seal before any test outcomes. Save **all
256 forecasts**, case identities and feature hashes in a write-once artifact,
and seal its hash before running **any** actual held-out terminal lineage.
The development executable has no held-out execution or automatic successor.

Actual lineages retain the original unperturbed F0, perform three ordinary
read/rewrite generations G1–G3 with hard-reset readers, then a fresh G4 read
for the primary outcome, exactly the D135/D140 horizon. This wording retains
the terminal read interface rather than silently dropping it from the count.

Per case, loss difference = (passive prediction - outcome)^2 minus
(challenge prediction - outcome)^2. Average equally over four lives, two
families and two writers within each block, then equally over the 16 blocks.
Positive means challenge has lower prediction error. Report both MSEs, their
absolute difference, relative reduction (undefined if passive MSE is zero),
and the 16 paired block differences. Use 10,000 percentile bootstrap resamples
of the 16 whole blocks, seed 14120260917, central 95% interval.
Interval entirely above zero: CHALLENGE_PREDICTIVE_GAIN; entirely below zero:
CHALLENGE_PREDICTIVE_HARM; otherwise PREDICTIVE_DIFFERENCE_UNRESOLVED.
No arbitrary percentage-success threshold or post-hoc power claim.

MAE, calibration intercept/slope, starting-only baseline, and per-family/writer
MSE comparisons are descriptive secondary analyses with no alternative success
gate. An inconclusive interval is not equivalence. If both probes are worse
than the starting-only baseline, report that even if challenge beats passive.
Sixteen blocks gives limited precision; report the interval, not an assurance
of adequate power. No subgroup rescue of a failed pooled primary comparison.

## Controls and interpretation

On held-out founders retain the complete D140 control panel: protected copying,
aligned read-disabled, write-disabled, wrong-content, lesion and rescue;
terminal aligned pre/post-selector shuffles, ideal and zero. None enters
predictor fitting or the primary prediction contest. Use the same block
bootstrap seed/draw count as the primary, but resample each control's paired
contrast, not prediction errors. The apparatus checks are fixed now:

- Readout: distinct targets; each family's ideal-minus-zero and copy-minus-zero
  terminal lower 95% bound above zero.
- Aligned content: each family's aligned-minus-zero lower bound above zero;
  aligned versus each pre/post-shuffle control has pooled lower bound above
  zero and positive means in both families.
- Continuity: aligned versus read-off and write-off has pooled lower bound
  above zero and positive means in both families, at G2, G3 and G4.
- Interventions: terminal aligned-minus-wrong, aligned-minus-lesion and
  rescue-minus-lesion each has pooled lower bound above zero and positive
  means in both families. Rescue is externally supplied, not autonomous repair.

These replicate D140's qualification logic with 16 blocks. They do not add
family-specific gates to the pooled primary forecast contest. Qualify and hash
their executor on disposable data before any held-out outcomes. Any failure is
reported alongside the primary score and limits interpretation; no exclusions,
favorable control selection or changes after development forecast results.

A positive result supports only incremental predictive value of this challenge,
feature interface and simple model under this budget, on this fixed tissue,
guide and two-family distribution. It does not establish a universal superiority
of active observation, a new biological law, autonomous ontology or subjective
experience. A null/negative is retained without looking for another shuffle dose
on the same held-out cohort. The current L20 law verdict is not upgraded by
development scores or by implementation completion.

## Storage, provenance and stopping

Code/docs only in this subfolder; all fixtures, logs, arrays, forecasts and
outputs under `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1`.
Pin completed D140's closure and COMPLETE hash
`353e4c16236aae3ec6254e24d401ea7710f9578c75e69145bff28bfe6b97a415`.
Retain its numerical environment, moving only TMPDIR/XDG_CACHE_HOME into this
extension's external subtree; record both the original and current environments.
Independent checker restates masks, feature calculations, routing, reset/noise
provenance, reader/writer dynamics and ridge fitting. Full disposable replay
and production worker replays precede acceptance; saved audits regenerate
features/predictions from retained states without new simulations.

Maximum six workers/CPUs, numerical threads one, 512 MiB development allowance
and 4 GiB free-space reserve. Forecast stages over 600 seconds run detached,
no automatic polling, retries or successor jobs. Development stage stops after
fitting/sealing and saved audit. Held-out generation is a separate later stage.
