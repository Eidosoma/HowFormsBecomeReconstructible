# D170 — what is already controlled, and the smallest prediction lead

2026-09-23. Design review following the user's approval after
[D169](../address-swap/RESULTS.md). No new prediction fit or simulation.
[Proposed next stage](PROPOSAL_V1.md), [evidence checker](check_design.py).

## Decision in simple terms

Do not rerun the tissue just to make the challenged and passive copies use
the same feedback location: they already do. Instead, first ask whether the
observer can interpret its readings better if it is told which diagnostic
feedback settings produced them. Give that information to both competitors
and retain cheaper observers with the same information.

An analogy is knowing the conditions under which a measuring instrument was
used. A low reading could reflect weak reconstruction or an unfavorable
diagnostic feedback location. The saved settings might help separate them.
This is a hypothesis about measurement interpretation, not an established
prediction improvement or a claim that a better outcome has been found.

We can test this first using existing development data: no new tissue cycles,
future lineages or large storage allocation. Only if a separately qualified
development comparison is informative should we design any fresh test.

## The existing pairing is stronger than a casual description suggests

[D141's original protocol](../PROTOCOL_V1.md) already specifies matched U1/C1
streams. [D162](../confirmation/PILOT64_PROTOCOL_V1.md) preserves this for
its original shuffle and all three later fixed edits. Its primary challenge
is residual-minus, not D141's 25%-site shuffle. The two are not interchangeable.

| Physical diagnostic | Input treatment | Stream family | Assigned writer shift | Observer access |
| --- | --- | --- | --- | --- |
| U0 | Intact | trial0 | a0 | Shared first reading for every two-copy observer |
| U1 | Intact | trial1 | a1 | Passive observer's second reading only |
| C1 | Original 25%-site shuffle before incoming routing | trial1 | The same a1 | Original-shuffle observer's second reading only |
| Attenuation | Fixed edit after original routing | trial1 | The same a1 | Attenuation observer's second reading only |
| Residual-plus | Fixed edit after original routing | trial1 | The same a1 | Plus observer's second reading only |
| Residual-minus | Fixed edit after original routing | trial1 | The same a1 | Minus observer's second reading only |

Each second-copy alternative shares initial birth, initial read noise, writer
noise, final birth and final read noise with U1. Different inputs can and
should produce different trajectories and routing decisions; matched noise
does not mean identical states. The post-routing edits are not routed again
on entry; their newly written output is routed normally. The original
shuffle's entry-routing response remains part of that different diagnostic.

The assignment is also shared across public family/writer groups within a
life. Those group rows are not independent address draws. Ordinary writers
apply the assigned displacement; aligned writers ignore it. U0 and U1 use
different trial streams, but this same U0/U1 schedule is available to both
competing two-copy observers. Actual lineages use separate namespaces/phases.

Source-level evidence:

- [Pilot diagnostics](../src/l20_extension1/pilot_diagnostics.py): `cycle` and
  `simulate_life` assign trial0 only to U0 and trial1 to U1/C1.
- [Pilot fixed edits](../src/l20_extension1/pilot_probe.py): `random` uses the
  same diagnostic namespace and `trial1` for every edit, including its shift.
- [Independent diagnostic checker](../src/l20_extension1/pilot_diagnostic_audit.py)
  and [edit checker](../src/l20_extension1/pilot_probe_audit.py) reconstruct
  these assignments and check saved births/noise metadata.
- [Actual pilot lineages](../src/l20_extension1/pilot_system.py) and
  [additional futures](../src/l20_extension1/pilot_repeated.py) use future
  namespaces, not diagnostic trials. The earlier full audit verifies resets
  and isolation; D170 does not repeat that physics audit.

The new bounded saved-metadata check retains all 16 development and 64 pilot
founders, four lives and four groups. Across 1,280 cases it verifies 5,120
U1-to-second-alternative comparisons, each with an identical shift and five
matching stream fingerprints: 25,600 fingerprint comparisons. Every U0/U1
phase fingerprint differs. One pilot life happens to have equal U0/U1
physical shifts; none in development does. That coincidence remains included
and does not make the random streams identical. These are apparatus checks,
not new independent founder replications or prediction evidence.

## Equal reading weights already remove one route for copy imbalance

The [D160 constraint](../difference-ablation/PROTOCOL_V1.md), retained in
D162's primary pair, equates corresponding **raw** slopes for U0 and the
second reading. A predictor therefore uses their sum/mean, not their raw
half-difference. This is not equality of standardized coefficients, and it
does not make the two observers' separately trained models identical.

For any scalar D169 response let Yca denote background c and shift donor a.
The original passive mean is (Y00+Y11)/2; after swapping it is (Y01+Y10)/2.
Their difference is exactly −I/2, where
I=(Y11−Y10)−(Y01−Y00). It is not the much larger address contrast A that
changes the U1-minus-U0 gap. Large opposite within-copy effects can cancel.

For the already reported B-ordinary outgoing-own feature, this passive-mean
change is +0.001520132 in development and +0.000965328 in the pilot. These
are simple identities from D169's fixed cell means, not new forecasts,
outcome comparisons or uncertainty tests. D169 did not swap challenged
copies, and these numbers cover only one endpoint feature. Other features,
case-specific effects, learned coefficients and clipping can matter: we
have not established that the forecast itself is unchanged or improved.

This is why the large copy-gap reversal alone is insufficient grounds for
an expensive “balanced” rerun of the prediction study.

## What the observer is not told

[The current feature assembly](../src/l20_extension1/pilot_models.py) accepts
only `start`, `endpoint` and `targeted`. A primary two-copy row contains seven
starting and six features from each permitted reading: 19 continuous inputs
plus public family/writer group. Numeric IDs, RNG identities, raw shifts and
diagnostic feedback compatibility are not inputs. The challenge observer
does not receive U1, or U1-minus-challenge; that would be a third reading.

Both shifts are nevertheless saved in the raw diagnostic arrays and writer
metadata before actual outcomes. The existing
[D168 geometry definition](../src/l20_extension1/passive_feedback.py) maps
a shift and the already public target family to ideal-template compatibility
q. For aligned writing the effective displacement is zero, so effective q=1.

The proposed new pair (q0,q1) is computed from the two **diagnostic** settings,
never the actual future's shifts or the copy's resulting hidden state.
Both passive and challenged observers receive exactly the same pair. It adds
known apparatus information, not a third reconstruction or future knowledge.
It explicitly changes the old feature contract: equal diagnostic-cycle cost
does not mean an identical historical information interface.

q is a deliberately limited summary. Equal q can conceal different physical
shifts; its relevance can depend on the evolving body and perturbation.
No monotonicity or complete removal of address effects is assumed. A null
result would test this specific simple correction, not show that all feedback
information is useless or that all perturbations lack predictive value.

## Why not change the physical schedule first?

| Option | What it would answer or change | Decision now |
| --- | --- | --- |
| Expose existing settings equally | Can the fixed observers interpret their existing readings better? No new cycles. | Recommended development check |
| Give U0/U1 the same shift | Changes independent diagnostic address sampling; matched passive/challenge second copies already exist. | Not required to repair fairness; defer |
| Force balanced or favorable q categories | Changes the diagnostic distribution, with family-dependent shift multiplicities and an externally supplied geometry rule. | Separate experimental question; defer |
| Cross every body with both shifts | Supplies more reconstruction outputs than the two-copy budget; D169 supplies passive counterfactuals, not corresponding challenge arms. | Do not silently treat as free observations |
| Align every diagnostic writer | Changes the reconstruction process used as an assay; ordinary actual futures would still face translated feedback. | Not a neutral nuisance correction; defer |

None of these alternatives is ruled out forever. They simply do not follow
as necessary fixes from D169. Retain its original causal finding and both
unresolved prospective verdicts without rewriting their protocols.

## Proposed next coding stage and interpretation

[The bounded proposal](PROPOSAL_V1.md) adds two setting features to the existing
seven selected observer types, retains the three alpha values and whole-
founder-out fitting on 90000–90015, and reuses existing no-setting references.
It keeps residual-minus as the focal challenge rather than switching to a
pilot-favorable direction. Original shuffle, attenuation and plus remain
visible; no new perturbation or fitted winner is chosen in this design.

First distinguish three outcomes:

1. Settings improve passive and challenged forecasts similarly: useful
   calibration of the diagnostic method, not extra challenge information.
2. The challenge gains against settings-aware passive observation but loses
   to a cheap baseline: a narrow comparison, not broadly useful superiority.
3. A challenge advantage survives strong baselines in development: a lead
   for a separately frozen fresh test, not confirmation on these studied data.

Poorer or mixed results are retained. No automatic q interaction search,
shift selection, dose tuning, founder exclusions or sample-size escalation.
The former 64-founder pilot has already informed this design and cannot
become untouched evidence for it. L20 remains STRESS_TESTED / MIXED;
D141 and D162 remain unresolved. This does not test autonomous addressing,
learned ontology, complete shape preservation or biological heredity.

## Evidence, cost and boundaries of this design review

The [read-only checker](check_design.py) rehashes 340 consumed, previously
pinned files: the diagnostic/targeted blocks, selected code, prior completion/
audit/manifest records and D169's summary. It does not claim to redo every
old closure or any physics replay. It checks only the `shift` arrays from
diagnostic NPZ files and saved metadata; no actual outcome arrays, fitted
prediction coefficients or future-lineage states are loaded.

Synthetic checks cover eight feature-boundary assertions, all 255 legal
shifts for both template families (510 closed-form/array comparisons), and
30 factorial mean identities. No actual or synthetic model is fitted.
The proposed 336 fits and 5,376 predictions are counts, not completed work.

The design receipt binds this review, proposal and checker at:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/logs/d170_prediction_design_review_v1.json`.
It records measured check time and source hashes. Only code/docs are added
here; the small machine-readable receipt is external. No simulation, new
diagnostic, new founder, deployment model or long-running job is launched.

Next authorization should cover implementation and synthetic qualification
of the saved-data comparison, with a measured time/storage gate before
actual development fits. It is not approval for another prospective cohort.
