# D138 — retained hand-off persistence

Status: COMPLETE, independently reconstructed and hash-audited. No new dynamics.
See [protocol](../protocols/L20_HANDOFF_PERSISTENCE_AUDIT_V1.md).

We are following D137's small unresolved effect through retained states:
does the corrected reference begin with better shape, and what happens to
that difference during writing, packet construction/routing and reading?
Separate template fidelity from state convergence and actual reader scores.
All four arms, both roles, three source stages and eight blocks remain.

No dynamics or new reader trials. This is post-hoc localization, not a new
confirmation, serial rescue or causal loss allocation. The known D137 primary
and L20's overall MIXED verdict are unchanged. All artifacts external, one
numeric worker, at most CPUs0–5; detach forecasts above600s and wait for user
advancement without polling. No automatic successor.

## Qualification and execution

Initial88 tests passed in30.55s; added eight targeted control-corruption
checks before freeze. Final454 tests passed in69.41s:96 new D138 plus358
D136 regressions, no failures or skips. Report
`logs/d138_final_20260916_b.xml`, with separate external b fixtures; passing
initial a artifacts retained. Full disposable audit0.964s gives150.848s
forecast, below600s, permitting one foreground audit worker.

995 source/science files verified; final XML gives996 audit inputs. Runner
seals INPUTS before main extraction, then reconstructs all saved arrays and
summary independently before COMPLETE. Original three LAWS/v2.3/L20 case
hashes unchanged; earlier science and completed reviews unedited. No
parameter changes or new main outcomes were used to choose this design.

INPUTS sealed at17:33:16.023503 UTC; COMPLETE at17:33:43.885552 UTC on
2026-09-16. Actual27.862081s,41,097,484 bytes including COMPLETE (39.19MiB),
below the128MiB budget. One foreground numeric worker, affinity0–5. A separate
read-only saved audit then passed all996 input/four output hashes and full
reconstruction. No active job, failed main attempt, retry or successor.

## Finding: an initial shape gain, followed by a smaller advantage

Here “fit” means normalized correlation with the assigned ideal pattern,
maximized over all256 translations. It is not a success percentage, reader
preference or measurement of all information in a state. The table averages
all three source stages, eight blocks and four lives equally for each role.
Each role contributes96 paired cases, but the independent block count is
eight, not96. These are three separate conditional hand-off experiments,
not a lineage receiving repeated corrections.

| Pattern | Checkpoint | Original-reference arm | Matched-history arm | Corrected minus original |
| --- | --- | ---: | ---: | ---: |
| A | R at write0 | 0.903193 | 0.937620 | +0.034426 |
| A | R at write300 | 0.931695 | 0.939944 | +0.008249 |
| A | R at write1000 | 0.940650 | 0.941914 | +0.001264 |
| A | Raw or routed output record | 0.941840 | 0.942666 | +0.000827 |
| A | Fresh-reader V at300 | 0.868206 | 0.867588 | -0.000618 |
| B | R at write0 | 0.712874 | 0.748306 | +0.035432 |
| B | R at write300 | 0.726731 | 0.739142 | +0.012411 |
| B | R at write1000 | 0.721977 | 0.727409 | +0.005432 |
| B | Raw or routed output record | 0.721370 | 0.726314 | +0.004944 |
| B | Fresh-reader V at300 | 0.631524 | 0.632176 | +0.000652 |

The initial correction is not negligible in this diagnostic: A improves in
all96 cases, B in92 with four losses. Its advantage is already smaller at
write300, then smaller again at1000. But the two patterns differ importantly.

For A, the original reference mostly catches up. Original R improves
by0.037457 during writing, while corrected R improves by0.004294. Both
improve in all eight block means. The corrected-minus-original gap decreases
in all eight block means and all96 individual cases; this is not evidence
that corrected A itself generally deteriorates.

For B, corrected R itself loses fidelity:0.748306→0.727409, a change
of-0.020897. Seven block means decline and one improves;66 individual cases
decline and30 improve. Original R improves by0.009103 on average (five
positive/three negative blocks;64 positive/32 negative cases). The advantage
decreases in all eight block means and93 of96 cases; three increase.
The remaining B advantage is positive in70 of96 raw packets, not uniformly.

This narrows the description to an initially improved reference whose
advantage diminishes during writing. It does not identify a causal fraction
lost to each equation or prove that all useful information has vanished.

## State convergence, strength controls and routing

The two R states also become more alike, without becoming identical. A's
raw RMS distance decreases0.11110→0.05138 and standardized RMS
0.26951→0.06154 between write0 and1000. B decreases0.11137→0.06743 and
0.29340→0.08756, respectively. The reference-shape finding therefore does
not rest only on raw amplitude convergence. Nevertheless, convergence and
loss of target fidelity are different measurements.

All four arms and five fixed paired comparisons remain in the saved audit.
The following shape contrasts at write1000 show that the larger initial
pattern advantage also diminishes without restoring R's original strength.
H is birth-subtracted history; “dose” is R's pattern at H's mean/std.

| Contrast | A fit difference | B fit difference |
| --- | ---: | ---: |
| Matched H minus original R | +0.001264 | +0.005432 |
| Natural H minus dose | +0.001243 | +0.005399 |
| Natural H minus original R | +0.001291 | +0.005172 |
| Dose minus original R | +0.000048 | -0.000226 |
| Matched H minus natural H | -0.000027 | +0.000260 |

The guide's roll preserves best translated fit for the focused packets,
as required. Raw-to-routed pair distances can increase because each packet
receives its own selected roll; that is not itself information damage.
For A, reference and matched guide calls choose A in all96 cases; all96
also fit ideal A better. For B, both guides choose B in all96, while the
ideal best fit favours B in89 reference and90 corrected cases. Corrected
shape still need not be the requested ideal family, even when the learned
guide gives the intended label. All other arm/control routes remain saved.

## Functional result remains unresolved

Reconstructed body observers agree exactly with D137. Its frozen primary
remains matched-history minus original-reference
+0.095622[-0.044759,+0.238037] preference points. A's secondary is+0.122070
[+0.032552,+0.215658]; B's is+0.069173[-0.231934,+0.402934]. All four content
routes and readout qualify. These thresholded body preferences are not the
static correlations above: no correlation gain is promoted to a functional
rescue, no new confidence interval or success threshold is introduced, and
no negative cases are excluded. D137 remains
`REFERENCE_HANDOFF_EFFECT_UNRESOLVED`; L20 remains `STRESS_TESTED / MIXED`.

## Bounded next lead: record-stage by correction interaction

The retained slower theta state has a larger endpoint correction advantage
than the instant-R record actually transmitted in D137:

| Pattern / candidate | Original arm fit | Corrected arm fit | Correction advantage |
| --- | ---: | ---: | ---: |
| A, final theta | 0.937875 | 0.941998 | +0.004123 |
| A, current instant-R record | 0.941840 | 0.942666 | +0.000827 |
| B, final theta | 0.726678 | 0.735512 | +0.008834 |
| B, current instant-R record | 0.721370 | 0.726314 | +0.004944 |

Theta was not transmitted in D137. These are static candidate measurements,
not a tested reader benefit. Also retain the relevant negative finding:
[D124](L20_THETA_STAGE_2026-09-14.md) favoured instant R over theta by0.254313
preference points, with theta-minus-instant95% interval[-0.343831,-0.144450].
That used earlier source writers without the present aligned-renewal
hand-off comparison. It is evidence against simply assuming theta is better,
not a reason to omit that result when proposing another test.

Proposed next, subject to approval and a new frozen protocol: reuse saved
endpoints for a matched fresh-reader record-stage × hand-off experiment.
Compare final theta versus the current instant-R record, under original and
matched-corrected hand-offs, holding the2048-byte format, frozen public guide
and paired fresh reader starts fixed. Retain both roles, all source stages
and content/disabled controls. The primary question should be the interaction:

`(corrected - original when theta is sent) - (corrected - original when instant R is sent)`.

This asks whether theta preserves a functional benefit of the correction,
not whether another selected endpoint can make theta look universally better.
Reuse writers; no parameter search or new guide fit. Even a positive result
would be a conditional descendant effect, not a repaired serial lineage or
learned ontology. No successor code, run identity or job has been created.

## Coverage and reproducibility

The saved extraction contains23,040 focused field instances and8,448 packet
fields, with1,536 overlaps:29,952 unique fields /31,488 feature evaluations.
All4,325,376 packet-template correlations,3,840 selectors,768 record/erased
writer-birth reconstructions and1,632 reader aliases are retained/verified.
Observers for all4,224 reader paths are checked at four checkpoints.
All720 focused groups,264 packet groups,132 terminal control readouts,
132 family groups,900 paired checkpoints,210 paired segments and192 full
matched/reference paths are reconstructed. All paired lives/block means,
constant flags and control exceptions are preserved.

Independent maximum absolute errors: features2.88658e-15,
correlations1.66533e-15, distances0, first projection2.77556e-16,
hand-off5.55112e-17, route invariance2.44249e-15, selectors1.11022e-15,
source body observers0. This checks the stored static analysis; ancestor
dynamic replay remains certified by its unchanged pinned artifacts.

All data are under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_handoff_persistence_audit_v1_attempt1`.
Only code/docs were added here. Frozen science and completed ancestor reviews
were not edited. The new live result and six tracking documents are outside
the audit-input freeze.

| Artifact | SHA-256 |
| --- | --- |
| COMPLETE.json | `258cda0deed8b7a9f917b40c0be27f88630aed878d338c0b9c55fa17f2bd303e` |
| INPUTS.json | `7428aa6003263c21fb51d7b29962749e1b66089f4bde6a09e81fe115b948ccf1` |
| summary.json | `9b9d5dd717bde25f37566a8556ff7930a2ee3647039ddc615e686abcac897437` |
| verification.json | `17161d4124cbcfb32e40fa9e4ccd2c01d343bf3b777d142fcc07f332211dc66a` |
| features.npz | `dd184a1a59d98a8e15b5806131fcede04bbc9086f0d9815e9c38aaea334975aa` |
