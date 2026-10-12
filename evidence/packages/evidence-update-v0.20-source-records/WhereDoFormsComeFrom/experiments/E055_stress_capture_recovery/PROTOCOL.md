# E055 — stress, recovery and capture

Design selected 11 October 2026 after the audited E053/E054 results and before
any E055 intervention outcomes. The user authorized implementation and execution.
This is a mechanistic follow-up on all existing E051 blocks 34000–34031,
not a fresh confirmation. Keep all four founders and four recipient slots:
512 lineages per history, including initially unsuccessful cases. Acquired
records are duplicated over recipient slots; these are not extra acquisitions.

## Histories and numerical conditions

Three sources: acquired records, then h32 full-rewrite records under shared
or independent rebuilding cue noise (E051 condition indices 0 and 20).
The primary history is independent-noise h32 rewriting, chosen from E053/E054.
The other two histories are secondary; no preservation-policy panel is added.

Use float64, zero normalization floor and no record noise or quantization.
E053 did not establish combined-stress noninferiority; E055 isolates the new
pulse/capture mechanism in the common numerical apparatus rather than treating
those stresses as already qualified. Current-body intrinsic cue noise is
independent in **all** histories; the birth state is shared across cues.
This common new writer environment separates source history from current noise.
Terminal cue noise/birth remains shared, as in E054. Distinguish these three
pairings from the additional pulse, which is identical across cue episodes.

## Pulse and capture

Read each incoming record in a body with 24 scattered absent non-port cells,
using the normalized reader, dt=.2, Gaussian noise SD=.02, birth SD=.05 and
gain 2. Hold the effective incoming weights fixed. Read for 2048 steps, with
amplification disabled for the first 1024. Sham and pulse copies share every
reset, injury and ordinary noise draw and are identical before the pulse.

Select 64 living non-port cells uniformly without replacement, independently
of record values, task rule and performance. Give each a fixed independently
drawn sign ±1. The same field is used for both cues, all three histories and
the two opposite-rule founders in each pair. During the next 32 steps, add
dt × 1.0 × this field to the pulse body's ordinary clipped update, then clip
again to [-2,2]. The sham gets no extra forcing. Record requested/delivered
squared increments and clipping counts. The dose uses the model's order-one
activity scale; it is not fitted to scientific or technical success rates.

Capture at pulse end (step 2080), then allow 512 unforced steps and capture
again (step 2592). Amplification stays on after step 1024. All bodies run to
2592. Save endpoint fields and the last 32 port observations at the before,
early and late boundaries. Shortened excluded technical runs use the fixed
settings in plan.py; they validate delivery/replay, not scientific effect size.

Capture uses the original exact-fallback full writer: with x=tanh(3v),
d=(x+−x−)/2, write d_i d_j, except use mean ordinary paired coactivity where
that product is exactly zero. Mask edges incident on currently absent cells.
Each outgoing branch is a single new write from its endpoint field, without
access to incoming values, targets, scores or a future state. Early capture
is stored in a buffer and does not change the trajectory used for late capture.
There is no additional holding phase or second rewrite: this tests one
capture-and-fresh-read boundary, not the complete serial E041 renewal cycle.

## Seven outgoing arms and common recipients

Sham early, pulse early, sham late, pulse late, protected sham, protected pulse,
and erased. Both protected arms transmit identical incoming values with the
same current physical edge erasures. Erased transmits all zeros. Only the
packet crosses into a fresh recipient; no old activity, pulse label, capture
time, history-specific reader parameter or task target is passed.

Use the common E054-style terminal reader: 2048 steps, first 1024 without
amplification, 32 final observations, strict output margin .25. Test intact,
scattered24 and square9 injury, always protecting ports. Injury and fresh
randomness are matched across histories/arms. No extra pulse is delivered.
The protected pulse/sham fields, traces and scores must agree exactly.

## Outcomes and fixed inference

Retain both-cue success, per-cue margins, raw and task-aligned signed transfer
for the current body and fresh recipient separately. Save source/effective
and outgoing packets, pulse field, masks, resets, boundary fields, port windows,
every-step SHA256 state hashes, exposure and writer components/fallback masks.
Record normalized couplings, denominators, sign-disagreement numerators and
common-support denominators against the matching sham, new/lost support and
ordered-forest graph parity/reachability. Cross-support cycle counts are
descriptive, not a basis-independent measure of frustration.

For the primary independent-noise history and scattered terminal injury, define
E_early = Q(pulse early)−Q(sham early), E_late analogously, and
I = E_late−E_early. Bootstrap 10000 paired whole-block samples, preserving all
within-block pairing. Four requirements jointly establish **transfer protection**:

1. E_early upper 95% bound < −.05: an early transferred loss exceeding five points.
2. I lower 95% bound > .05: a pulse-specific benefit of delaying capture.
3. E_late lower 95% bound > −.05: late loss bounded within five points of sham.
4. Q(pulse late) lower 95% bound > .75: adequate absolute late function.

This is one conjunction; failure of any requirement means protection was not
established. Report all components, not only the label. The conjunction is an
intersection-union test; individual intervals are pointwise, not simultaneous
claims about every arm/history. A failed bound does not establish equivalence,
absence of effect or loss greater than five points.

Stronger **joint body-and-transfer recovery** additionally requires current-body
early pulse−sham upper bound < −.05, late pulse−sham lower bound > −.05 and late
pulse success lower bound > .75. Thus a positive interaction alone, or recovery
in the old body alone, cannot establish this stronger result. All remaining
histories, injuries, history interactions and mechanism diagnostics are secondary
pointwise 95% summaries. No successful-case filtering or outcome-driven expansion.

## Verification and execution

Replay source extraction, all stochastic fields, every body/recipient update,
capture, packet boundaries, diagnostics, scores, block contrasts and intervals
with independent equations. Verify zero-pulse equivalence, no capture feedback,
matched shams, exact protected equality, injury masks, rule-blind pulse delivery,
and no target access inside dynamics/writing. Technical runs emit no scientific
classifications. Freeze source receipts/design/code before retained fixtures;
benchmark full simulation plus audit on excluded block 900041 before science.

Scientific execution uses eight single-thread workers, detached if forecast
exceeds ten minutes, within the shared twelve-CPU ceiling. Keep immutable run
directories, failures and frozen hashes. No automatic restart or successor;
subsequent status checks follow user requests. Pulse trains, serial persistence,
stressed numerical readers and spatial historical specificity remain separate.
