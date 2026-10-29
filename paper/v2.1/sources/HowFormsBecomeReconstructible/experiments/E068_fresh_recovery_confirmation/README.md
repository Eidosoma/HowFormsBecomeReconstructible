# E068 — fresh-source recovery confirmation

**Complete: partial recovery confirmed on fresh sources.** All **32 new source
blocks (40000–40031)** finished on **14 October 2026 at 14:15:34 UTC**, in
**2 h 1 min 31 s** on three single-thread workers. Independent replay passed;
figure inspection and artifact closeout passed at **14:21:52 UTC**. E067
contributes no cases to this estimate. Another agent handles manuscript integration.

| Pooled condition | Before | After one cycle | After three cycles |
| --- | ---: | ---: | ---: |
| Mixture, rewritten | **30.37%** | **50.78%** | **59.47%** |
| Native, rewritten | 87.79% | 87.30% | 86.62% |
| Mixture, cumulative erasure | 30.37% | 17.48% | 4.39% |
| Erased start, rewritten | 0% | 0% | 0% |

All three h3 primary requirements passed: absolute recovery **+29.10 points
[23.44, 34.83]**, benefit over matched erasure **+55.08 [50.78, 59.77]**, and
advantage over erased-start rewriting **+59.47 [54.79, 64.26]**, using
family-adjusted 98.3333% intervals. There were **367 gains and 69 losses** among
1,024 paired mixture cases. Recovery is incomplete: the h3 mixture remains
**27.15 points below native**. Signed transfer also improved.

Closeout verified **1,617 original outputs, 43 frozen inputs and 927 summaries**;
the run retains **1.174 GB**. Actual runtime was below the 2 h 38 min benchmark
estimate. No successor, sample/horizon extension or additional simulation started.

The primary question was whether ordinary rewriting again improves the mixture
absolutely, outperforms matched cumulative erasure, and retains the original
learned response above erased-start rewriting. All three h3 effects must have
strictly positive family-adjusted intervals, with numerical controls passing.
The conjunction passed (`FRESH_RECOVERY_CONFIRMED`). This confirms recovery
within the same apparatus, not robustness to changed pairing or normalization.

Nine development checks passed in **2.704 seconds**. Fixture/benchmark finished
in **9.69/36.86 seconds**. Full source regeneration, independent replay and
technical archive projections passed; each run verified **98 original outputs
and 927 summaries**, and both figures were inspected before qualification.
The freeze contains **43 source/dependency files**.
The benchmark includes acquisition, 32 ancestry cycles, sham/pulse capture,
three source continuations, three recovery cycles, fresh readers and audits.
No unrelated compatibility factorial or extra horizons are included.

[Protocol](PROTOCOL.md) · [Settings](plan.py) ·
[Data dictionary](DATA_DICTIONARY.md) · [Decisions](DECISIONS.md) ·
[Source registry](SOURCE_DATA.json) · [Development checks](analysis/tests_v1.log) ·
[Qualification](analysis/technical_v1.json) · [Forecast](analysis/forecast_v1.json) ·
[Launch](jobs/confirmation_v1/launch.json) · [Startup](jobs/confirmation_v1/startup.json) ·
[Status](jobs/confirmation_v1/status.json) ·
[Interpretation and integration wording](INTERPRETATION.md) ·
[Report](runs/confirmation_v1/REPORT.md) · [Figure](runs/confirmation_v1/rebuilding.png) ·
[Independent audit](runs/confirmation_v1/INDEPENDENT_AUDIT.json) ·
[Closeout](analysis/closeout_v1.json) ·
[Motivating E067 result](../E067_ordinary_mixture_rebuilding/INTERPRETATION.md).
