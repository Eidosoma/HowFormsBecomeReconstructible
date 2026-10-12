# D185 where the body distinction weakens

12 October 2026. The saved trajectories support an early capture problem,
but do not yet establish its remedy. The surviving bodies initially express
their own histories clearly. Much of that target-aligned difference fades
before the slow reference and writer have substantially changed the shared
record. Later, large physical differences between bodies persist without
recovering the two missing identities in fresh readers.

This is a retrospective diagnosis of the [D184 pilot](PANEL_RESULTS.md), not
a new positive repair result. The [analysis contract](TRACE_V1.md) was fixed
after the terminal outcomes were known and before extracting these trajectory
metrics. All original conditions and outcomes remain unchanged.

## The distinction is present at the start

All 64 initial own bodies have the correct nearest original template. Their
average own-minus-partner template projection is +0.551679. Both histories
receive byte-identical within-pair records, and R and ema start at zero.
Thus the starting record cannot specify which member of its pair is intended,
while the surviving body does express that distinction.

In the native equations, R updates by `R += 0.002 * (V - R)`. The writer
mixes `0.001 * tanh(R)` into the record, followed by normalization. At the
first step with R starting at zero, the writer therefore receives a very
small-amplitude body-derived proposal. All 100 enabled-writer first-step
identities were checked against saved states without advancing the equations.
The tracked ema is not an input to the rung A activity drift in this setup;
it must not be described as a second causal writer bottleneck.

## Target alignment fades before substantial record change

These are equal-block averages for the own-body, live-feedback, common-record
condition. Projection gaps are signed geometric scores in each field's units,
not comparable fractions of information across the three columns.

| Saved repair step | Body V projection gap | Reference R projection gap | Record theta projection gap | Record correlation with own parent |
| --- | ---: | ---: | ---: | ---: |
| 0 | +0.551679 | 0 | 0 | 0.795862 |
| 1 | +0.465743 | +0.000931 | +0.000000816 | 0.795863 |
| 50 | +0.027457 | +0.014024 | +0.000470 | 0.796546 |
| 250 | −0.000929 | +0.007850 | +0.002553 | 0.798562 |
| 500 | −0.010732 | +0.002002 | +0.003342 | 0.790927 |
| 1000 | −0.009807 | −0.004407 | +0.002262 | 0.740144 |

By step 50, the pooled body projection gap is about **95 percent smaller**
than at birth. This is a decrease of this signed projection, not a measurement
that 95 percent of all information has been destroyed. At step 50 the body
already favors the wrong partner in the pooled message-0 and message-3 strata.
By step 250 the reference and its tanh proposal also favor those same wrong
directions; the terminal fresh-reader failures are not first appearing only
at the final readout.

The decrease is not solely a cancellation artifact. In every block, the
own-versus-partner body intervention loses most of its initial target-aligned
projection by step 50. However, two blocks remain positively aligned and two
reverse sign, so it would also be wrong to call the late effect uniformly zero.

| Block | Body source contrast at step 0 | At step 50 | At step 1000 |
| --- | ---: | ---: | ---: |
| 30056 | +1.101891 | +0.120750 | +0.147016 |
| 30057 | +1.103051 | +0.193661 | +0.200123 |
| 30058 | +1.103774 | −0.036358 | −0.165770 |
| 30059 | +1.104715 | −0.058398 | −0.259827 |

Here a source contrast projects `V_own - V_partner` on the intended-minus-
partner template. Its pooled normalized directional alignment falls from
0.814910 at birth to 0.065200 at step 50 and −0.024201 at step 1000. In
contrast, the RMS physical difference between those bodies remains substantial:
1.104831, 0.734468 and 0.800337 at those times. Bodies remain different; their
differences no longer consistently point toward the intended histories.

## The later record differences do not recover identity

At step 50, the own-versus-partner outgoing-record difference has RMS
0.001017. By step 1000 it has grown to 0.137824, yet its intended-direction
projection is only +0.004523 pooled and reverses sign in two blocks. A larger
record difference is not necessarily a more informative corrective difference.

Fresh bodies start with identical paired birth noise. Their own-versus-partner
record source contrast has RMS zero at birth, 0.027565 after one read step and
0.265240 at the terminal read. Nevertheless, both record sources give the same
terminal intended-message recognition pattern: **0, 100, 100, 0 percent**.
The continuous readout changes, but the two missing messages stay missing.

Neither the native nor conventional averaging record changes that template
recognition pattern at any saved record checkpoint. Those intermediate record
template scores are only offline geometry; no fresh readers were run from
intermediate packets. They do not prove what an early-stopped lineage would do.

## What the comparisons rule out and leave open

Holding the reader on its initial record gives almost the same early collapse:
the body gap at step 50 is +0.026697, versus +0.027457 with live feedback.
The live-minus-fixed body RMS difference is only 0.001233 then. Updating the
record's feedback is therefore not necessary for the observed early loss in
these existing interventions. This does not remove the influence of the
shared incoming record itself or isolate every component of body dynamics.

Conventional averaging captures more early directional signal in its record:
at step 50, its projection gap is +0.009186 versus +0.000470 for the native
writer. It still fails to recover the missing identities. Faster or stronger
capture alone is therefore a hypothesis, not an established sufficient fix.

When the incoming record retains individual information, the body gap stays
positive: +0.198079 at step 50 and +0.335482 at step 1000. Its record gap grows
from +0.070076 to +0.127162, and actual fresh recognition improves from
83.984375 to 87.890625 percent. Averaging matches that final recognition.
The model can reinforce surviving content more readily than restore the
deliberately removed distinction under these tested settings.

## Recommended next bounded intervention

Test **early body-derived reference capture**, not a search over writer
strengths or a new pass threshold. A candidate is to initialize the existing
working reference from the current surviving body once, then leave the
ordinary reference and writer equations unchanged. Compare with the original
zero reference and retain partner-body, scrambled-body, disabled-channel and
averaging controls. No original parent reference or parent record may be used
as a hidden backup. Any full-field working memory must be disclosed, and only
the ordinary record may enter a fresh reader.

This would test whether promptly capturing information already present in
the allowed body helps. It changes both reference-mediated body maintenance
and writing, so a positive result would require a further channel-specific
test before attributing the rescue to one of those routes. The complete
protocol, matched resources and frozen cases must precede outcomes. No such
simulation, rate selection, new cohort or serial-renewal run has launched.

## Verification and resources

Twenty synthetic qualification tests passed in 0.77 seconds. The analysis
freeze at **15:56:50.026019 UTC** binds 1,077 inputs, including all 420 original
frozen inputs and all 649 panel outputs. The diagnostic completed at
**15:58:18.763528 UTC** in **74.244 seconds**, using one numerical thread on
CPU 6 at nice 10, with no dynamics or fits. Peak RSS was 1,136,304,128 bytes
(about 1.06 GiB); this is transient memory, not retained disk data.

All 135,936 field rows were checked against a separate scalar implementation;
maximum difference was 7.55e-15. All 204 terminal named reads match the original
per-record recognition, partner recognition, preference and projection scores.
Intact and supplied-positive controls remain 100 percent; disabled reading
remains 25 percent pooled. All four block files were reopened and compared
exactly before complete-panel aggregation.

A fresh-process readback passed at 16:01:11.401026 UTC in 3.14 seconds. It
reverified all 1,077 input hashes, all five outputs and 6,444 derived arrays,
then independently recomputed all 523,575 pooled and stratified summary
entries. Maximum aggregation discrepancy was 7.77e-16. This additional checker
was written after extraction and supplies validation, not prospective evidence.

All 1,611 metric keys per block, every time, field, message, replicate and
control remain in the external derived arrays. The JSON summary contains
pooled, block, message and block-by-message values for each key. Reader metrics
are averaged over their four draws only after per-draw scalar verification.
The complete stage occupied 23,180,830 bytes (22.11 MiB) before its final
receipt, within a separate 128 MiB cap. No source data were copied or deleted.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-trace-v1`.
Evidence: `FREEZE.json`, `MANIFEST.json`, `COMPLETE.json`, `SAVED_CHECK.json`,
`outputs/SUMMARY.json`, and `outputs/tissue_<index>.npz`.

- Freeze SHA-256: `e3e8ac3e52912e877d49f236d3146f34fe469a2e4fcc9ae0f031faedec6c27ac`.
- Completion SHA-256: `a271d40fd46e0184842a69ab5c9eb7f3957105ecadca0a439290343a1a007f53`.
- Summary SHA-256: `300b87cfdf23f8cd517b058f91a7c8539292fb2066243f3eaca4a956badeb35b`.

Sparse checkpoints cannot locate the exact transition, recover unsaved write
proposals, prove absence of decodable information in other features, or turn
this development diagnosis into a prospective prediction. L20/L22 verdicts
remain STRESS_TESTED / MIXED; repeated renewal remains conditional.
