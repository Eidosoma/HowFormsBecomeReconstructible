# H089 interpretation — an inferable task, with an earlier neural retrieval failure

24 October 2026. H089 completed at **17:19:09 UTC**, covering all **16 fresh
networks**, four related births each, and two actual handoffs. The primary
neural branch solves **0/64 trained tasks at G0** and **0/64 held-out tasks at
G2**. Its G0 trained-query score is **120/512**; its G2 held-out-query score is
**0/512**. All four predeclared development findings are negative:

- `G0_TRAINED_CAPABILITY_SCREEN_FAILED`
- `G2_HELDOUT_CAPABILITY_SCREEN_FAILED`
- `NO_POSITIVE_G2_HELDOUT_INHERITED_TASK_DIFFERENCE`
- `NO_OBSERVED_G2_HELDOUT_ADVANTAGE_OVER_ALL_COMPARATORS`

These results do not show that the task is unlearnable. The independent ordinary
parity-rule learner gives **64/64 tasks and 512/512 exact queries on both panels
at every generation**. It receives the same eight training examples, its public
hypothesis family and encoding, and no hidden generating rule or held-out label.
That supplied inductive bias is an explicit difference between methods.

## What changed, and what crossed each boundary

Four contexts crossed with four queries supply sixteen combinations. The fixed
training set is [0,3,4,5,9,10,14,15]; its complement is held out. Every individual
context and query appears twice in training. Output bits follow signed parities
of the four binary input bits. All 32 signed parity functions have distinct
signatures on the eight training combinations. The task therefore contains
inferable unseen structure, rather than arbitrary withheld random labels.

The existing projection writer, delayed sequential reader and single-pair
intervention remain fixed. Only G0 receives correct teaching responses. Every
later reconstruction/native writer receives its own parent's eight actual
training responses, including errors. Copying receives the actual coefficients.
Held-out assays are independent and passive. Full analyst targets and generating
rule parameters are attached only after physical simulation.

Changing all held-out targets and hidden rule parameters leaves the complete
physical run exactly unchanged in a fixture. The parity fitter is checked on
all 256 possible eight-label columns, including inconsistent data and ties.
The original H086 engineering reader reproduces exactly in all 84 saved arrays.

## Memorization, generalization and neural retrieval are distinct here

G2 own-source scores below use pair-assisted parents and an ordinary recipient
for neural branches. Native independent lineages use their direct reader.
Each task consists of eight queries, each requiring at least 44/48 correct bits.

| Independent lineage | Trained tasks | Trained queries | Held-out tasks | Held-out queries | Held-out correct bits |
|---|---:|---:|---:|---:|---:|
| Reconstruction | 0/64 | 120/512 | 0/64 | 0/512 | 12,720/24,576 |
| Coefficient copying | 0/64 | 120/512 | 0/64 | 0/512 | 12,584/24,576 |
| Linear LS | 0/64 | 172/512 | 0/64 | 0/512 | 10,848/24,576 |
| Quadratic LS | 64/64 | 512/512 | 0/64 | 0/512 | 12,800/24,576 |
| Nearest-history | 64/64 | 512/512 | 0/64 | 0/512 | 11,992/24,576 |
| Parity ERM | 64/64 | 512/512 | 64/64 | 512/512 | 24,576/24,576 |

The previously perfect observed-history controls no longer settle the unseen
task. Quadratic fitting and nearest-history give a clean trained-success /
held-out-failure separation. The neural primary instead occupies **neither
success category in all 64 birth assays**. No assay completes the trained task
and then fails only at generalization. Its failure starts before the intended
generalization comparison can be interpreted as a test of competent retrieval.

All **512 G0 primary trained queries** and **512 G2 primary held-out queries**
end at conditional fixed states, with all **16,384 context bits correct** in
each panel. Across all logical neural case/panel rows, all 98,304 query endpoints
are conditionally fixed. Correct context and numerical settling therefore do
not imply correct responses. This supports a response-retrieval/representation
diagnosis; it does not yet distinguish basin access, record geometry or the
reader's response dynamics. No causal ablation of those mechanisms was run.

## Small response differences do not pass the capability gates

At G0, pair assistance gains eight trained queries without losing any, but gains
184 and loses 320 correct trained bits, for **136 fewer correct bits**. No task
is gained. At G2, under the fixed ordinary recipient, pair-parent records retain
the same **eight-query gain**, no task gain and **136-bit net trained loss**
against ordinary-parent records. The exact-query net difference is +22.

On held-out G2 responses, pair-parent versus ordinary-parent records gain 184
and lose 48 bits, a net **+136 bits**, with **zero task or query gains**. The
primary has 12,720 correct held-out bits (51.76%), compared with 12,324 for the
independent donor source and 12,168 after erasure. All three have zero successful
queries and tasks, so neither the 75% capability requirement nor the 25-point
source-control requirement passes. These bit differences cannot replace those
predeclared endpoints.

Against independent copying, reconstruction also has +136 held-out bits and
zero task/query differences. Against the **same-parent local copy**, every
primary G2 response bit is identical on both panels. It therefore shows no
benefit from rewriting over retaining that actual parent record in this assay.

All ten local/independent comparator contrasts remain in the report. Local
parity ERM, fitted to the neural parent's corrupted training packet, also gives
zero complete tasks and zero successful held-out queries. Exact performance
belongs to the independently propagated parity learner; it must not be credited
to a rule learner receiving a different, corrupted packet. Local parity and
local linear fits each trade 24 held-out bits with reconstruction, with zero
net difference. The independent parity learner exceeds reconstruction by all
64 tasks and 512 queries. Its exact ceiling precludes the joint superiority
label, as stated before running.

## Integrity and scope

All **21 fixtures** and **2,888,843 main numerical checks** pass. Verification
includes 4,848 records, 3,744 actual writer packets, 915 unique neural reads,
3,616 unique native reads, 45,827 literal table-row checks, 46,801 serialized
rows and 1,936 exact raw-array reloads. Maximum record, field and pair-energy
errors are respectively **2.60e-15**, **6.84e-14** and **1.65e-14**, within the
frozen bounds. No failure, exclusion, restart or protocol revision occurred.

The four-network benchmark took **157.86 seconds serially** and **63.13 seconds
with four workers**, a **2.501×** speedup; 524 arrays and 20 files match exactly.
Main took **200.31 seconds**. Total controller time was **507.95 seconds**,
including **30.46 seconds** waiting for capacity. The short run was watched
through completion; controller **3683363** has exited.

Independent closeout verifies **467 sealed artifacts, 261 frozen files and
256 unchanged sources**, plus the 520 H088 and 516 H086 artifacts. It separately
recounts 1,920 primary/comparator panel assays, 30 score groups, 22 paired
contrasts and the primary trained/held-out success categories. The figure was
visually checked. There are 16 independent networks; the related births and
descendants are not additional independent replicates. These are development
findings, not a population qualification or general impossibility result.

## Next bounded question

Diagnose the **failed taught-response retrieval first**, using the saved G0
records and trajectories: check the taught full patterns as fixed points,
locate when response errors enter, and compare the fields supporting the wrong
endpoint with those at the intended response. Keep ordinary/pair readers,
own/donor sources and the native controls separate. Only then choose a targeted
reader or representation intervention. More dynamical complexity by itself is
not supported as a remedy by this pilot. No successor is launched here.

H031 retains `DIRECTIONAL_EFFECT_ON_FRESH_NETWORKS` separately from
`NO_QUALIFIED_ENTRANT_PREDICTION_ADVANTAGE`. H033 retains
`NO_QUALIFIED_ADDITIONAL_OBSERVATION_GAIN` separately from
`NO_QUALIFIED_PERSISTENCE_REPRESENTATION_ADVANTAGE`. H086–H088 remain unchanged.
No predictor search, private quotation or public-manuscript edit is included.

[Sealed report](../runs/h089_composition_v1/main/REPORT.md),
[figure](../runs/h089_composition_v1/main/overview.png),
[verification](../runs/h089_composition_v1/main/verification.json),
[independent closeout](../.cache/h089_completion_verification_v1.json).

Freeze: `79f2eb03cc3d1a8d748ff04076d9c498e1ae639eacec9f0eb5e0d4febc9297c5`.
Manifest: `2d63b598db4f0ea75b86c49aacfbef7aae281cd10a7112919fa78beb324fadad`.
