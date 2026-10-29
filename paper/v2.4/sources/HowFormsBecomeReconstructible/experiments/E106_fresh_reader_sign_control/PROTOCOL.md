# E106 — fresh readers for the matched-weight sign comparison

24 October 2026. Authorized after E105. E105's eligible-mixture C−F success
advantage was 1.531 points [0.250, 3.111], six discordances in four source
blocks. None repeated in both stored draws. These outcomes inform this question,
but do not select its records, witnesses, reader seeds or analysis.

## Fixed records, injuries and fresh nuisances

Use all 32 archived E105 blocks 980000–980031 and its exact D/W/C/F packets,
common magnitudes, eligibility, physical connectivity and two injury masks.
No witness search, weight adjustment, source selection or new writer. D/W keep
original cycle magnitudes; C/F use the same arithmetic mean. D/C keep signs;
W/F flip them. C/F preserve every cell's positive/negative incident-weight
multisets, counts, normalization and absolute normalized coupling under the
stored injuries. Recheck these constraints independently before new readers.

For each source and each of its two stored injuries, run one fresh birth/noise
realization. Its semantic PCG64 stream is `rng('E106', task, 'terminal', draw)`
with draw 0/1 paired to the corresponding original injury. The original E102
stream was `rng('E077', task, 'E102_terminal_DRAW', 0)`. Generate full arrays
of shape `(2,R,16,16)` before paired-founder expansion and case indexing.
Birth/noise remain shared across variants and cue episodes within each draw.
This changes birth and noise jointly; it does not test independent cue noise.
No seed search, extra repetitions, adaptive extension or old/new pooling.

Keep E105 reader equations and settings: float64, dt .2, noise .02, birth SD
.05, 2,048 steps with 1,024 settling and 32 final observations, strict success
margin >.25, natural strength normalization, zero drive at zero denominator.
Use all four founders, four recipients and four native/mixture × sham/pulse
arms. This is reader robustness on known sources and fixed injuries, not
untouched-source confirmation, injury robustness or unique loop mediation.

## Avoid redundant dynamics without reusing old outcomes

Read D afresh for every context/draw. Read W/C/F additionally for every context
with a nonempty archived witness, including draws where injury erases it. For
an empty witness all four packets are byte-identical; derive W/C/F outcomes
from that row's **new D read**. Never substitute an E105 success or continuous
score for a new-reader outcome. This retains new absolute rates everywhere.

All 2,048 contexts / 4,096 rows remain: 4,096 new D reads plus 3×808 additional
variant reads = **6,520 variant/draw reads**, compared with 16,384 if every
identical packet were re-read. Each read evaluates both cues. Independently
replay every new step, noise hash, end state and score. Retain original full
birth/masks, selected batch indices, state/noise hashes and late-window data.
Verify masks equal the archive and the new birth/noise stream differs from the
old one. Recheck erased-cycle aliases empirically, including signed zeros.

Retain E105's complete cases and summary byte-for-byte as `previous_*`, plus
its byte-identical `original_*` tables containing both earlier immediate and
reconstruction endpoints and every individual harm. New inference uses only
new D/W/C/F outcomes. Old outcomes enter explicitly labelled descriptive
old/new transition tables and differences, never case selection or pooling.

## One frozen primary and complete secondary reporting

Predict that fresh-reader pooled-mixture **C−F success among preinjury eligible
contexts** remains positive. Use 10,000 shared bootstrap resamples of all 32
source blocks, conditional ratios of source sums/counts, keeping zero-eligible
blocks. A positive lower bound of the prespecified 95% interval passes; a
negative upper bound is negative; otherwise unresolved, not equivalent.
No practical-effect gate or success-contingent increase in runtime.

Retain all/eligible/affected, native/mixture, sham/pulse and pooled/per-draw
results; absolute D/W/C/F success, margins, signed/aligned transfer; D−W,
C−F, C−D, F−W and `(C−F)−(D−W)`; all 16 joint outcomes, individual
gains/harms/zeros and within-repeat recurrence. Report the baseline C−D cost.
Also retain old/new contrast transition counts and identities under each
same injury, including E105 losses that recur, disappear or reverse, and new
losses/gains elsewhere. Report the new-minus-old matched-arrangement contrast
as secondary. Only the fresh pooled-mixture eligible success contrast is primary.
All secondary intervals are pointwise. Empty groups and bootstrap resamples
are explicit. Preserve every source sum and denominator.

## Checks, timing and stopping

Pin E105's completed archive, closeout and packet-preflight hashes. Validate
new batching against the unmodified full reader on excluded inputs with the
declared streams injected only in the fixture. Replaying the original streams
must reproduce archived E105 scores and overlapping states exactly. Test fresh
streams, empty witnesses, erased witnesses, all-case D coverage, identity
derivation from new D, threshold equality and old/new transitions.

Benchmark complete 512/256-step readers on excluded blocks 9000980/9000981,
R=1. Preflight all scientific packets and exact work counts without new reader
outcomes. Forecast using the slower measured time per evaluated variant-step,
including independent replay, static work scaled for four recipients, 120
seconds for summaries and a threefold timing margin. Use at most four one-thread
workers under the shared twelve-CPU ceiling; reserve storage before launch.
Detach when the conservative forecast exceeds 600 seconds, perform one bounded
startup check, then await user-requested status. Preserve all failures. No
automatic restart, extension, successor or untouched-source experiment.
