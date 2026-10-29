# Multiscale lane review — 27 October 2026

The lane has progressed from the 24 October design to **fourteen completed development reports**. Its newest study, LR004, is frozen and technically qualified, but this checkout contains no development result for it. This review changes neither the manuscript nor the experimental protocols and launches no computations.

The strongest emerging contribution is a conditional mechanism of **reciprocal maintenance**: a body can help maintain the record that helps maintain it, while the same feedback can copy the body's distortions into memory. The new question is consequently not just whether an error signal exists, but whether it identifies the source that should be corrected.

## What is complete

All entries are development studies or screens, not independent confirmatory campaigns. Predicted failures count among statements marked HOLDS; a high statement-pass count is not a universal repair success rate.

| Studies | Main contribution | Important boundary |
|---|---|---|
| ME001, ME002 | Separate sensor scale, action scale, change detection, writing and successor usefulness; test random injury timing and eight-generation continuation. | Some gains disappear under matched correction dose; damage can be mistaken for a lasting new target; repeated noisy capture loses information. |
| OR001 | Selection among supplied controller parameters favors different maintenance/development/transmission strategies in different environments. | Goals, controller vocabulary, stored targets and fitness are supplied; this is not the spontaneous origin of agency. |
| BR001, BR002 | Put record state inside cells; test local wounds, plastic windows, turnover and records stored in relations between neighbors. | An open learning window can import damage. Coarse consensus can erase small legitimate features. |
| GW001 | Vary sheet size, lesion type and proximity to pattern boundaries. | The earlier small/large-wound explanation needed revision: boundary contact, inversion versus reset and available time matter. |
| EN001, EN002 | Separate persistence of the record from current expression under imposed resource reductions. | Results depend on how the model scales noise with activity. The budget is not an experimentally calibrated ATP or metabolic model. |
| DL001, DL002 | Separate the structure supplied by body dynamics from the particular arrangement supplied by records. | Physics can supply a preferred spacing while failing to preserve which stripe occupied which location. Strong relational records are substantial supplied information. |
| DL003 | Test whether sparse positional cues and a growth front can register a pattern across a sheet. | Benefits require compatible dynamics, direction, time and low disorder; scattered cues perform better in other conditions. |
| LR001 | Learn neighbor relations and maintain them through local consistency checks and relearning. | Error thresholds remain; arbitrary defaults are not acquired relations; cell replacement can erase information if relations are not transmitted. |
| LR002 | Use the body to repair its own relational record. | The body also teaches its preferred pattern and environmental distortions. |
| LR003 | Gate body-to-record teaching using agreement and local inconsistency. | Tested gates trade repair against importing teacher error; no rule wins throughout the tested conditions. |

See the [lane index](../experiments/multiscale-error-lane/README.md). Its boxed progress table supersedes the intentionally preserved original design text below it. In particular, the old text saying that no scientific runner exists is historical, not the current implementation status. ME002 is now a broad development screen, not the fresh confirmation originally proposed under that name.

## The strongest active-embodiment result

[LR002](../experiments/multiscale-error-lane/REPORT_LR002.md) tests a body reading a relational record while that record's connections undergo random sign errors. The record can relearn from itself or from the body's activity.

On clean period-eight stripes in the stripe-forming body, at a bond-flip probability of 0.01 per update and after 4,000 updates:

| Record maintenance | Agreement of the record's signs with the pattern |
|---|---:|
| No repair | 50.01% |
| Relearning from the record | 49.70% |
| Record relearning plus local parity repair | 50.13% |
| Relearning from the body | **97.02%** |

These values were checked directly in the committed compact summary. They are average **site-sign agreement**, not the percentage of successful lineages, and are based on 16 development blocks with eight dependent cases per block. They describe maintenance inside the coupled system, not a separate fresh-successor assay.

This makes the body's contribution concrete: the expressed organization supplies useful information for maintaining its record when the record's own tested repair machinery fails. However, under the full imposed environmental field, body teaching falls to approximately 61% in the same stripe condition. On an incompatible pattern, it can rewrite the record toward what the body's dynamics favors. The positive and negative results belong together.

## What detects error, and what acts on it

The implemented signals now include:

- Disagreement between current activity and a stored reference.
- Recent movement of the body, used as evidence about which source changed.
- Inconsistency between a connection's sign and the values of its neighboring record cells.
- Inconsistency around small loops of connections.

The implemented actions include pulling activity toward the record, rewriting record values, relearning connections from body or record activity, and changing which connections are allowed to learn. These are actual update rules, not labels assigned by the scientific observer. Their machinery is still supplied.

[LR003](../experiments/multiscale-error-lane/REPORT_LR003.md) provides a particularly clear scale comparison. In the clean stripe-body condition above, checking a single inconsistent connection gives approximately **70.0%** record agreement. Allowing all connections around an affected site to learn gives **96.0%**. But when the body itself is distorted, noise opens this broader gate and allows those distortions into the record. Under the full field at this error rate, the tested teachers retain only about 50–61% of stripes and labyrinths.

The defensible inference is that **the tested local consistency signals do not reliably distinguish record error from teacher error across these conditions**. Wording such as “two copies can never decide” or “a third copy is always necessary” would be too broad: temporal history, source reliability and further observations could also provide information. Likewise, the report's biological predictions are hypotheses, not demonstrations in tissue.

## Other results worth retaining

**Embodiment supplies structure, but not necessarily historical placement.** In DL001/EN002, the stripe-forming dynamics can recover a characteristic wavelength after strong disturbance while losing the original arrangement. A retained reference restores placement in the tested cases. This is a useful concrete distinction between generating the same kind of form and recovering the particular form learned earlier. [EN002](../experiments/multiscale-error-lane/REPORT_EN002.md)

**Developmental history changes what sparse instructions can achieve.** DL003 uses 64 positional cells in a 32 × 32 sheet. In quiet tissue, building stripes gradually outward from a suitably oriented boundary gives **99.82% sign agreement**, versus **68.71%** when the same boundary is used while the entire sheet develops at once. Scattered cells give approximately 89.1%. Direction and speed matter; disorder reverses the advantage. Equal numbers of instructed cells do not make this an equal-time or equal-computation comparison. [DL003](../experiments/multiscale-error-lane/REPORT_DL003.md)

**Coarser correction has a cost.** It can ignore fine noise but also miss real fine distinctions. Relational records help retain small minority features that ordinary neighbor consensus erases. This should remain a scale-and-task claim, not “larger-scale control is better.” [LR001](../experiments/multiscale-error-lane/REPORT_LR001.md)

**The lane has corrected some of its own attractive early explanations.** ME002 removes much of an apparent voting advantage by matching correction dose. GW001 shows that a wound's relation to pattern boundaries and its type matter beyond its size. Several early broad statements therefore need the later qualifications beside them. [ME002](../experiments/multiscale-error-lane/REPORT_ME002.md), [GW001](../experiments/multiscale-error-lane/REPORT_GW001.md)

**Serial renewal is not yet solved by these mechanisms.** ME002's body-capture chain declines from 76.5% to 58.1% qualified agreement over eight generations without injury, while copying the record remains around 84%. Under repeated record injury at the tested higher noise, all live strategies decline toward chance; in-life repair fails its registered slope criterion. Later LR002/LR003 maintenance results should not silently become claims of sustained fresh-body reconstruction. [ME002](../experiments/multiscale-error-lane/REPORT_ME002.md)

## Latest status: LR004

[LR004](../experiments/multiscale-error-lane/REGISTRATION_LR004.md) asks whether two records and a body can arbitrate disagreements more effectively than the tested two-source arrangements. It compares:

- A majority vote of body and two records with separately sampled noise.
- Two records alone, without a tie-breaker.
- Protected acquired signs at sparse positional anchors.
- Earlier self-repair, body-teaching and site-gating controls.

The design froze at **09:35:12 UTC on 27 October**. Its qualification passed at **09:45:47 UTC**. The 74 current frozen source hashes match; the qualification receipt matches the design digest and reports all ten checks passing. No `results/lr004/` or `REPORT_LR004.md` is present. The run storage is on another machine and unavailable here, so production progress or completion cannot be inferred from the planned runtime. The engineering probe values in the registration are not development outcomes.

Separately sampled noise is not a guarantee that interacting records' eventual errors remain independent. Correlated injuries and shared biases are important tests of any later redundancy benefit.

## Recommendation for the paper and next tests

The strongest compact addition would pair **LR002's reciprocal maintenance** with **LR003's failure to identify a trustworthy teacher**, using the scale and growth results as support. These directly develop the paper's active-embodiment argument. They should enter as bounded development evidence and retain the supplied machinery and native endpoints.

After LR004, a valuable confirmation would freeze one chosen mechanism and challenge it with new pattern instances, correlated body/record damage and matched total storage/action budgets. Then restore selected outgoing records into fresh bodies and sample multiple continuations. That would connect this lane's maintenance mechanisms to the paper's conditional reconstruction capacity, while testing whether the new information improves a usable decision rather than only an internal consistency score.

The review checked reports, compact results, selected code paths and five frozen source sets (LR001–LR004 and DL003). All checked source hashes and qualification digests matched, and the available compact results have the matching design digests. It did not rerun dynamics or audit the absent raw archives. See [verification record](MULTISCALE_LANE_REVIEW_2026-10-27.json).
