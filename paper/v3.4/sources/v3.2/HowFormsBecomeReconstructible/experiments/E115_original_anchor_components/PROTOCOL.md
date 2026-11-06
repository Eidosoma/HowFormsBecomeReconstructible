# E115 — equal component changes from original halfway states

Authorised 29 October 2026 following E114 closeout. This is a controlled
continuation on all known E112 sources, not fresh-source confirmation.
E112 and E114's eligible-mixture primary intervals both include zero. E114
equalised component changes by moving their levels around midpoints; E115
tests the same doses starting at the original diagonal states instead.

## Fixed intervention

Use all 32 E112 sources 1120000–1120031, all four arms, four founders,
four recipients, both injury/reader draws, existing safe four-cycle witnesses,
and both C/F records. Retain all 4,096 context/draw rows, including the 554
eligible rows, erased controls and ineligible rows. No witness reselection,
new injury, source, noise, writer update, horizon extension or threshold sweep.

At the saved halfway step define m=(x+ + x−)/2, d=(x+ − x−)/2.
Keep E114's exact norm: mean absolute O/N component difference over living
cells excluding cue-clamped P0, pooled equally across C/F; include output
ports. Target t=min(Lm,Ld), alpha_c=t/Lc, or zero for Lc=0. Scales are
common across each C/F pair. Individual C/F norms need not match.

For each original anchor a=O,N, baseline B is the exact saved OO or NN
halfway state. M changes m toward its opposite-history value by alpha_m,
holding d at the anchor; D changes d by alpha_d, holding m at the anchor.
Implement in state coordinates as x_anchor+alpha*(x_full_target−x_anchor).
At alpha=0 return the exact anchor bytes; at alpha=1 return the exact E111
full-target bytes, including signed zeros. These endpoint branches prevent
roundoff from invalidating exact archived reuse. Independently assemble the
states with scalar arithmetic and check intended size, component isolation,
clamped/dead cells and [-2,2] bounds. Do not clip injected states. Maximum
allowed size/isolation roundoff is 4e-15 in native activity units.

Continue each state under each original later stream at its absolute offsets
1024–2047, using the unchanged compensated reader, paired cue noise, time
step, noise amplitude, clamps and terminal 32-step port average. Benchmark
uses only excluded sources 9000980/9000981, one recipient, offsets 256–511.

Twelve conditions: anchor O/N × B/M/D × later O/N. Eight comparisons per
eligible row: B→M and B→D at both anchors and both later streams. Compare
the same C/F records in each. At zero target, perturbations equal their own
anchor; different anchors need not equal one another.

## Exact reuse and workload

Reuse a saved original continuation only when alpha is exactly zero or one,
or for B. Select reuse solely from frozen input scales and verify its exact
initial state, original stream/offset metadata, weights, masks, final ports
and scalar scores. Original condition mapping: B→aa, M→opposite(a)a,
D→a opposite(a); append the later-stream letter. Preserve all original
tables and all E114 comparisons/crossings byte-for-byte.

Only partial-scale states get new updates, independently replayed at every
step. Batching subsets does not change scientific eligibility. Save subset
indices and genuine subset trajectory hashes; never fabricate full-batch
trajectory hashes by combining rows. Assembled full condition states/ports
carry explicit per-case reuse codes and point to the pinned source archives.
Known E114 input scales imply 4,432 new variant continuations (4,538,368
updates), 8,864 exact reused variant outcomes and 4,432 paired comparisons.
All d scales are one in this cohort: gross d effects must match E112's
original gross d effects. Any disagreement fails validation.

## Inference fixed before new scientific outcomes

For each component average |(C_after−F_after)−(C_before−F_before)| across
two anchors and two later streams. The **sole primary** is eligible pooled
mixture gross m sensitivity minus gross d sensitivity of both-cue success.
Preserve all 32 independent source blocks, including zero-eligible blocks.
Use 10,000 whole-source bootstrap resamples (fixed E115 semantic seed),
ratio-of-sums estimates and percentile 95% intervals. POSITIVE requires
lower bound >0, NEGATIVE upper bound <0; otherwise UNRESOLVED. Only
POSITIVE meets the stated greater-shared-sensitivity criterion. A bound
equal to zero is unresolved, not equivalence.

Paired secondary contrasts: anchored minus E114 midpoint m−d excess,
anchored minus E112 original full-size excess, the m−d contrasts for
minimum margin, transfer and aligned transfer, and each anchor's binary
component sensitivity/excess. Also report native, sham/pulse, each draw,
affected/erased/all scopes, absolute C/F performance, signed changes,
total absolute movement, cancellation, all gains, losses and bottleneck
crossings. Secondary intervals are pointwise, not simultaneous. Ineligible
absolute outcomes remain null; their contrasts are zero. Empty denominators
remain null. Do not select rows by effect or drop harms.

Copy E112 and E114 original primaries and source sums unchanged. E115
does not update either earlier interval. Results concern these directions,
these doses and these two original anchors under the existing apparatus;
they cannot establish a component's universal importance or biological
generality. This uses known sources and is not an untouched-record test.

## Bounded execution

Freeze after analytic tests, excluded benchmark and figure inspection, before
new scientific continuations. Price the complete closed scale inventory and
all independent replay from the measured benchmark; allow 3× timing margin,
180 seconds summary allowance, and full uncompressed output growth. At most
four workers and 12 total logical CPUs across active work, one numerical
thread per worker. Respect RUN_POLICY.md: forecast >600 seconds runs detached
with frozen job, unique log/PID, stdin /dev/null and durable status. One
bounded startup check; thereafter user-driven status only. Preserve technical
failures. No automatic extension, retry or successor.
