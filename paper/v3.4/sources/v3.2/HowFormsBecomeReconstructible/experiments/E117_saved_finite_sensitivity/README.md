# E117 — saved finite-sensitivity diagnosis

**Complete and verified, 31 October 2026.** `diagnosis_v1` finished at
**11:31:12 UTC** in **5m16.03s** on one worker, below the 7m expected / 16m
conservative forecast. Closeout passed **12:39:23 UTC**: **133 outputs,
18 frozen inputs and 137 source files** verified; figure inspected.
All 32 sources and 32,768 condition rows remain; 577.32 MB retained.
No new trajectories were computed.

Rounding removes less than 0.00004% of the starting mixture records' raw
weight mass, but erased edges carried **11.19% intact / 17.02% pruned** of
their normalized input coupling, versus about **2%** for native records.
It newly isolates **9.84% / 13.66%** of mixture free cells. The floor alone
attenuates mean incoming drive by **11.58% / 15.36%**, without deleting edges.
Rounding removes **155 of 167** original immediate mixture pruning gains;
the combined finite arm retains 79 original later harms and adds 60 others.
These descriptions locate numerical vulnerability without proving mediation.
E116's failed primary remains unchanged.

[Interpretation](INTERPRETATION.md), [report](runs/diagnosis_v1/REPORT.md),
[statistics](runs/diagnosis_v1/summary.json),
[figure](runs/diagnosis_v1/diagnosis.png), [closeout](analysis/closeout_v1.json).

The user authorised the next lead after E116. E116's all-finite mixture primary
failed: immediate benefit became uncertain, absolute success fell to 36–42%,
and later harm remained. This diagnosis asks where the numerical sensitivity
appears in those saved records; it does not change E116's decision.

It keeps all 32 sources, eight regimes, all four original endpoints, both
common-reader endpoints and every individual harm. The measurements distinguish:

- Weights erased by the actual storage channel, including their small raw mass
  versus the normalized coupling they formerly supplied.
- Positive denominators below 1e−4, floor-induced attenuation and genuinely
  isolated cells.
- Selected versus outside edges, cells touching selected edges, their immediate
  ring, remote cells and the output ports.
- Lost or retained original pruning gains and later harms, while retaining all
  unchanged cases and absolute outcomes.

These are post hoc descriptions of known outcomes. No threshold sweep,
prospective predictor or causal mediation claim is introduced. Native and
mixture records remain separate. Any later change to the finite formulation
requires development followed by fresh validation.

Eleven known-answer checks passed. The two-source, full-width excluded benchmark
completed in **24.48 seconds**; all **40 outputs** verified and its figure was
inspected. It checked 118,198,784 metric values, 86,016 scores and 2,304 original
block values, with all earlier decisions unchanged. Its shortened-source
descriptions are technical evidence only. The scientific extraction froze
before launch, with **137 source files** pinned.

[Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[tests](analysis/tests_attempt_001.json), [source registry](SOURCE_DATA.json),
[qualification](analysis/qualification_v1.json), [freeze](SAMPLE_FREEZE.json),
[forecast](analysis/forecast_v1.json), [startup](jobs/diagnosis_v1/startup.json),
[decisions](DECISIONS.md).

Next: separately freeze finite acquisition and renewal from the beginning,
with matched reference histories, fresh sources, both endpoints and the same
absolute-performance criteria. No successor was launched at this closeout.
