# H095 — context protection confirmed on 32 fresh networks

**Completed 27 October 2026 at 17:58:38 UTC; independently verified 28 October
at 11:08 UTC.** All 32 fresh networks finished, with four related births each
and two actual handoffs. The controller and dispatcher have exited.

| Complete tasks | Unprotected | Protected |
|---|---:|---:|
| G0 unseen | 109/128 | 128/128 |
| G2 unseen | 77/128 | 128/128 |
| G2 taught | 77/128 | 128/128 |

All protected primary responses are bit-exact through G2. The G2 unseen gain
is **51 tasks across 13 networks**, with no losses. Both copying controls and
the stronger native learners also reach **128/128**. Context transition,
initial capability, unseen retention and taught capability pass; pair-parent
benefit and strict comparator advantage remain absent.

Both conditions were acquired afresh with H093/H094 physics unchanged. The
hold preserves actual context for one query sweep, then releases it. Eight
unseen queries at each later generation begin with wrong context and recover
after release. There is no true-context resupply or extra observation.

All **16 fixtures and 8,261,033 main checks pass**. Independent closeout verifies
813 sealed artifacts, recounts 92,160 panel assays and 196,608 transition-query
records, and checks all six decisions. Main takes **18m30s** on four workers;
the full controller takes **58m06s**, including shared CPU waiting.

[Interpretation](INTERPRETATION.md),
[sealed report](../runs/h095_fresh_context_v1/main/REPORT.md),
[figure](../runs/h095_fresh_context_v1/main/overview.png),
[protocol](PROTOCOL.md),
[independent closeout](../.cache/h095_completion_verification_v1.json),
[transition diagnosis](../.cache/h095_transition_diagnosis_v1.json),
[status](../runs/h095_fresh_context_v1/STATUS.json).

Fresh finite-cohort confirmation is separate from population qualification,
RDT forecasting and comparative superiority. H096's transport control is a
separate engineering result. No public manuscript or private-source change.
