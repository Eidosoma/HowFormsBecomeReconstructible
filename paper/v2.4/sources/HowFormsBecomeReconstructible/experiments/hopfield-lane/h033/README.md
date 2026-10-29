# H033 — Early finite-response persistence

**PROSPECTIVE_DEVELOPMENT.** Completed at **23:34:08 UTC on 16 October 2026**,
in **8h05m04s**, including **2h27m53s** waiting for shared CPU capacity.
Run: [h033_prediction_v1](../runs/h033_prediction_v1/STATUS.json).
Controller PID **443450** has exited.

**NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN**;
**NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE**.

The question is whether observing a finite perturbation through six
replacements helps predict changed reconstruction at endpoints 13–24.
Two verdicts distinguish extra observation from a representation advantage:

- Compare the same persistence recipe after three and six replacements.
- Compare the six-step candidate with label, margin, full raw trajectory and
  nested same-observation alternatives receiving the same six-step records.

Use 128 fresh training and 128 fresh test networks under root 33033, all
three H031 settings, both probe selections, both doses/directions/signs and
four common continuations. All failures, unchanged pairs and sparse panels
were retained. Forecast sealing at **21:54:08.471467 UTC** precedes test
submission at **21:54:13.669288 UTC**. Every numerical stage qualified.

Only one test panel meets the predeclared event-information minimum:

| Cell | Probe | Flip events / 4,096 pairs | Event networks / 128 | Informative |
| --- | --- | --- | --- | --- |
| 0, weak coupling / recovery 1.5 | Fixed | 4 | 2 | No |
| 0, weak coupling / recovery 1.5 | Selected | 34 | 18 | Yes |
| 2, weak coupling / recovery 3 | Fixed | 8 | 3 | No |
| 2, weak coupling / recovery 3 | Selected | 20 | 6 | No |
| 15, reference | Fixed | 1 | 1 | No |
| 15, reference | Selected | 0 | 0 | No |

In the informative panel, three-step/six-step persistence Brier scores are
**0.008202 / 0.006419**. The improvement **0.001783** is below the required
**0.005**, with simultaneous 95% interval **[-0.000497, 0.004063]**. The
ordinary six-step label model scores **0.006507**, almost the same as the
candidate. The nested same-observation comparator selects exactly
**persistence6:ridge=0.1**, producing identical forecasts in all panels.
All 30 simultaneous intervals include zero; none clears the practical
improvement threshold. Classification error is no worse than the comparators,
so that veto is not the cause of either negative verdict.

[Protocol](PROTOCOL.md) · [Design](design.py) · [Controls](fixtures.py) ·
[Workflow](workflow.py). H031's directional intervention result and negative
prediction verdict remain separate and unchanged.
No private AI-lane text, code, results or citations enter this study, and no
manuscript edit or public release is performed.

All **102 frozen controls** passed in **353.911 seconds**. The serial and
four-worker benchmarks took **2,720.110 / 893.529 seconds** (3.04x), with
**1,156 arrays exactly equal**; four workers were selected. All **6,144 probe,
13,824 finite, 55,296 observation and 55,296 continuation paths** qualify at
three resolutions, including the separate legacy replay diagnostic.

Independent retained-data closeout passed on **17 October at 10:49:26 UTC**,
in **57.061 seconds**. It verified **2,365 final checksums**, 1,248 raw
resolution batches, 832 refinement pairs, 104 finite-diagnostic batches and
12,252 reproduced input/derived arrays. Saved worst arithmetic steps,
features, strict targets, forecasts, training scaling, selected CV scores,
complete evaluation and independently calculated network bootstrap intervals
reproduce. All ten external bindings and 91 live runtime/protocol files
verify. The plot was inspected. No trajectories were rerun or models refitted.

The user relayed reviewer guidance on **16 October**. Complete this study
with both verdicts explicit: benefit from additional observations, and
benefit beyond equally informed comparators. The frozen analysis/report
already implements both. At closeout, also state H031's two findings
separately: sensitive-direction interventions caused more reconstruction
changes in the two qualifying weak-coupling settings, while its entrant
predictor established no qualified forecast advantage. Neither result
replaces the other, and neither is a general claim about RDT.

The requested diagnosis was performed on retained evidence on **17 October**,
without fitting, changing predictions or moving qualification thresholds.
The main limitations are sparse events, a small absolute score gain and
little advantage over ordinary six-step observations. Five panels have
three-step comparator Brier scores below 0.005: even a perfect predictor
could not clear the declared absolute improvement in those realized panels.
This explains part of the design's limited ability to qualify an advantage;
it does not justify changing its rule after seeing the outcomes.

The negative verdicts do not mean the observations contain no predictive
information. Across the **24,576 test pairs**, there are **67 flips**.
Candidate Brier is **0.001997**, versus **0.002726** for always forecasting
zero change; the ordinary label model scores **0.001929**. These pooled
comparisons are descriptive, not additional qualification tests. Mean
candidate probability is **0.242** on flipped pairs versus **0.00231** on
unchanged pairs. Every test forecast is below 0.5 (maximum **0.426**), so the
fixed classification threshold detects no flips, with no false positives.
Changing that threshold after the result would be a new predictor search.

Ordinary endpoint-6 label disagreement precedes **66/67** test flips, but
also occurs in **132 pairs without a later flip**. In **93 test pairs**,
component labels differ within the scoring window while both trajectories
still fail the whole-window target. The four retrospective observer
categories contain **24,416 / 16 / 77 / 67** pairs: no component difference,
component-only difference, endpoint-label difference with unchanged target,
and target flip. Training has **77 flips**, categories **24,398 / 17 / 84 /
77**, and 75 flips with early endpoint disagreement versus 152 early
disagreements without a final flip. Cohorts remain separate.

Thus the present lead is conditional risk among early differences and the
conjunction required by the final observer. Simple labels already carry much
of the measured signal. These findings do not establish an irreducible
prediction ceiling or prove that a different model could not help.

The four H033 tails have different observed six-step prefixes, so their
outcome variation cannot estimate irreducible future uncertainty conditional
on an identical six-step observation. Resolving that specific limitation
would require a separately specified diagnostic that branches from identical
observed states. No new predictor tuning or campaign follows automatically.
Richer inherited tasks remain a separate research priority with their own
questions and evidence; success in this forecast lane is not a prerequisite.

The freeze SHA-256 is
c66434f069444f4b2f57dccea0c8cfe73d3d9b7f1a1a18a820e1a5502b53509b.

[Report](../runs/h033_prediction_v1/REPORT.md) ·
[Evaluation](../runs/h033_prediction_v1/evaluation.json) ·
[Figure](../runs/h033_prediction_v1/overview.png) ·
[Exportable PDF](../runs/h033_prediction_v1/overview.pdf) ·
[Numerical summary](../runs/h033_prediction_v1/summary.json) ·
[Closeout audit](../.cache/h033_closeout_v1.json) ·
[Retained-data diagnosis](../.cache/h033_diagnosis_v1.json) ·
[Frozen protocol](../runs/h033_prediction_v1/source/h033/PROTOCOL.md) ·
[Configuration](../runs/h033_prediction_v1/config.json) ·
[Launch record](../runs/h033_prediction_v1_launch.json) ·
[Log](../runs/h033_prediction_v1.log).
