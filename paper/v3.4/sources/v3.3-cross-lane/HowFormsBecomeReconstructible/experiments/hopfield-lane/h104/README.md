# H104 — diagnose the first transmission loss

**Completed 2 November 2026 at 16:22:50 UTC:**
**FRESH_WRITER_FIDELITY_AND_TASK_GAIN** on **32 fresh networks** at one actual
handoff. Both component verdicts pass: **FRESH_TASK_RETENTION_GAIN** and
**FRESH_CAPTURED_OUTPUT_GAIN**. All 13 fixture checks, serial/parallel
equivalence checks and main numerical audits pass. Independent saved-evidence
closeout **passed at 16:31:04 UTC**. It verified 602 sealed artifacts, 412 frozen
entries, 371 unchanged sources, 1,088 acquisition/rewrite packets, all 17,024
exported rows, 637 intervals and all 23 task/fidelity requirements. An additional
QR projector construction differed by at most 5.28e-16. Verification took
20.25 active seconds after 191.52 seconds waiting for capacity and acquired
no new dynamics.
[Closeout status](../.cache/h104_completion_status_v1.json).

The fixed primary uses actual supplying activity, fresh recipient births and
20% record damage. Query success requires at least 14/16 correct task bits.

| Writing rule / benchmark | Task success | Exact captured output |
|---|---:|---:|
| Ordinary Hebbian | 27.34% | 26.42% |
| Centered | 25.54% | 24.76% |
| Projection | **64.36%** | **77.44%** |
| Strength-matched ordinary | 27.29% | 26.51% |
| Protected copy | 73.58% | 47.80% |
| Other-founder record | 0.29% | 0.00% |
| Erased record | 0.05% | 0.00% |

Projection gains **37.01 points [33.45, 40.87]** in task success over ordinary
writing and **51.03 points [47.02, 55.11]** in exact captured-output recovery.
Against centered and strength-matched ordinary writing, task gains are
**38.82 [35.03, 42.92]** and **37.06 [33.59, 40.67]** points; captured-output
gains are **52.69 [48.44, 56.84]** and **50.93 [46.84, 54.93]**. All six
contrasts favor projection on **32/32 networks**, using the frozen 99.1667%
paired whole-network intervals. All 23 task/fidelity requirements pass.

Copying retains the original record and scores higher on the original task.
Its captured-output fidelity is relative to the later actual supplier, which
can contain errors; that column is not evidence of poorer task retention by
copying. Projection improves a complete rewrite with the same activity input
as the other writers, without establishing superiority to copying.

The diagnostics separate substantial storage and access limitations. Captured
free-pattern stability under damaged recipient matrices is **40.04%** for
ordinary writing and **99.07%** for projection. Starting at the captured
pattern raises ordinary task success from **27.34% to 51.12%** and projection
from **64.36% to 73.49%**; this start supplies extra state information. Actual
suppliers themselves score **73.54%**. Projection can preserve their mistakes:
successful capture alone does not reconstruct missing task information.

Using ancestral acquisition activity gives projection **96.14%** task success,
but supplies extra historical information. This source substitution is a
diagnostic comparison, not an admissible descendant's recovery. Matching
weight norm alone does not reproduce projection's gain. These controlled
writing/source/access effects do not isolate pattern correlation or stability
as the unique causal mediator.

A secondary matched comparison finds projection task success **3.96 points
[2.25, 5.71] higher with damaged than intact recipients** (64.36% versus
60.40%). This is a prespecified descriptive 95% comparison of assessment
conditions. It neither clears the five-point intervention threshold by its
point estimate nor follows a modified supplying body into a successor; it is
not the requested endpoint reversal.

The follow-up [H105 four-handoff test](../h105/README.md) has now completed with
passing independent closeout. Projection's comparative benefit survives all
four handoffs, but task success falls below its frozen 50% requirement at
G3/G4. Local capture fidelity passes separately. This preserves H104's positive
first-handoff result without extending it to sustained task competence.
H103 remains **NO_DEVELOPMENT_REVERSAL_LEAD**, its confirmation cohort remains
unacquired, and learned-reader extensions remain deferred.

The question is where an acquired task is lost between a supplying body and
a fresh recipient. Hold the supplier fixed and compare ordinary, centered,
projection and strength-matched ordinary writing. Cross each with intact versus
20%-damaged recipients and fresh versus captured-pattern initial activity.
Keep protected copies, other-founder records and erased records as controls.

The same four writers also receive ancestral acquisition activity in a
diagnostic branch. Both ancestral activity and captured-pattern starts provide
extra information; neither can qualify an ordinary descendant's recovery.
Copying also retains information that a complete activity-only rewrite lacks.
The primary uses actual supplying activity, fresh births and damaged records.

There are **32 fresh main networks**, four excluded engineering inputs and one
excluded fixture network. All 36 engineering/main tapes and all 371 source
files were frozen before the controller started acquisition. There is one
actual handoff. This is a controlled transmission diagnosis, not a pruning
reversal or a test of retention across multiple generations. H103's failed
reversal verdict and its 32 unacquired confirmation inputs remain intact.

Task retention and exact captured-output fidelity have separate verdicts.
Projection must beat each equally informed comparator by at least five points,
with a positive adjusted interval and support on at least 16/32 networks.
Absolute task and source-control requirements also apply. An informative
diagnostic contrast cannot replace a failed primary.

Projection is a fixed public-method comparator already used in H077. The
orthogonal cue columns give full rank without a singular-value cutoff. Every
written packet is checked against an independent rational/long-double reference;
every neural update is independently replayed. No tolerance or decision gate
will be changed after outcomes are seen.

All **40,992,768** main coordinate decisions were independently replayed;
1,024 rewritten packets, 45,056 static pattern checks and 17,024 score rows
passed. Maximum writer error was **2.94e-16**, field error **2.35e-15**, energy
error **6.47e-13** and minimum guarded neural margin **1.56e-7**. Projection's
independent reference used rational Gram inversion and long-double arithmetic.

Four workers achieved a **2.094-fold speedup**: 19.823 seconds serial versus
9.465 seconds parallel, with all 136 arrays and twelve compared files exactly
equal. The 32-network main phase took **52.50 seconds**. The controller elapsed
2,565.51 seconds, including 2,458.27 seconds waiting for shared capacity; the
earlier dispatcher wait was a separate 533.45 seconds. Every phase admitted
within the shared twelve-CPU ceiling, with one numerical thread per worker.

All 36 input tapes and 371 source files were frozen before acquisition.
Freeze SHA-256:
`21c398da8993dfb21a8a1699ab3ece0e99827dcc5826ed2afdb952c45b008549`.
Sealed run manifest SHA-256:
`8e144a854396fd7a34807a86e39be0cf64bea36b8e54045e62930b2f7a72fd3b`.

[Protocol](PROTOCOL.md) · [dispatcher status](../.cache/h104_dispatch_v1_status.json)
· [dispatcher log](../.cache/h104_dispatch_v1.log)
· [frozen dispatcher configuration](../.cache/h104_dispatch_v1_config.json).
[Sealed main report](../runs/h104_transmission_diagnosis_v1/main/REPORT.md),
[all scores and gates](../runs/h104_transmission_diagnosis_v1/main/summary.json),
[figure](../runs/h104_transmission_diagnosis_v1/main/transmission.png),
[numerical verification](../runs/h104_transmission_diagnosis_v1/main/verification.json),
[completed controller](../runs/h104_transmission_diagnosis_v1/STATUS.json),
[independent verification](../.cache/h104_completion_verification_v1.json),
[fixtures](../runs/h104_transmission_diagnosis_v1/fixtures.json),
[serial benchmark](../runs/h104_transmission_diagnosis_v1/engineering_serial/batch.json).

H095's two-handoff acquired retention and H097's original failed numerical
qualification remain unchanged. Learned-reader extensions remain deferred.
No public manuscript edits or private-source quotations are part of this test.
