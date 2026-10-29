# Multiscale error detection and corrective action

> **State on 26 October 2026.** The text below this box is the design record of 24 October, kept as written.
>
> | | |
> |---|---|
> | Engine | `mse/`, qualified bit for bit against the legacy native code; engineering probes P1–P18b in [ENGINE.md](ENGINE.md); the any-size engine `msegrid/` (GW001 onwards) |
> | ME001 v2 | Done: [REGISTRATION.md](REGISTRATION.md), [REPORT.md](REPORT.md), `results/me001_v2/` |
> | ME002 | A wide development screen in six panels (time, coupling, breadth, storage, voting, heredity). Done: [REGISTRATION_ME002.md](REGISTRATION_ME002.md), [REPORT_ME002.md](REPORT_ME002.md), `results/me002/` |
> | OR001 | Origin by selection: which correction architectures evolve, in which environments. Done: [REGISTRATION_OR001.md](REGISTRATION_OR001.md), [REPORT_OR001.md](REPORT_OR001.md), `results/or001/` |
> | BR001 | Records in the tissue, after the biological review: record designs against lesion sizes, writing rules against damage and change, turnover. 5 of 10 statements hold. Done: [REGISTRATION_BR001.md](REGISTRATION_BR001.md), [REPORT_BR001.md](REPORT_BR001.md), `results/br001/` |
> | BR002 | Commitment and relations: committed write gates, damage inside an open plastic window, a record held in the relations between neighbours, and the wall geometry of consensus repair. 12 of 13 statements hold. Done: [REGISTRATION_BR002.md](REGISTRATION_BR002.md), [REPORT_BR002.md](REPORT_BR002.md), `results/br002/` |
> | GW001 | Geometry and wound kind on a sheet of any size (new engine `msegrid/`, equal to the old one at side 16): consensus repairs any wound clear of the walls given time (faster than area), never a large one touching a wall; reset wounds heal at once; the code is for walls and speed. 10 of 10 statements hold. Done: [REGISTRATION_GW001.md](REGISTRATION_GW001.md), [REPORT_GW001.md](REPORT_GW001.md), `results/gw001/` |
> | EN001 | The energy budget: does the plan hold when the budget falls? 10 of 11 statements hold. Thermal noise dissolves the pattern, activity-driven noise does not; the record outlives its expression; protect the record, not the body. Done: [REGISTRATION_EN001.md](REGISTRATION_EN001.md), [REPORT_EN001.md](REPORT_EN001.md), `results/en001/` |
> | DL001 | The design ledger: what a self-organising (lateral-inhibition) body gives for free, and what must still be paid for. 8 of 8 statements hold. The spacing comes free everywhere; layout, repair and cheap building of the native pattern only in quiet, clean tissue; off-scale patterns become expensive; what is free follows the match between pattern and body. Done: [REGISTRATION_DL001.md](REGISTRATION_DL001.md), [REPORT_DL001.md](REPORT_DL001.md), `results/dl001/` |
> | LR001 | Relations that learn and check themselves (a forked session; report by the lead). 10 of 10 statements hold. Learning relations is easy, keeping them needs two repair layers (plaquette parity and relearning) below a threshold; a coarse code in the relations' frame stops fighting minorities, a hybrid also repairs kills; defaults are not relations; relations survive renewal only if inherited; learning in life copies damage. Done: [REGISTRATION_LR001.md](REGISTRATION_LR001.md), [REPORT_LR001.md](REPORT_LR001.md), `results/lr001/` |
> | DL002 | Who supplies a pattern's relations: the body's physics, a record of relations, or positional anchors, along a disorder axis. 7 of 7 statements hold. A tissue-held record of relations holds native patterns on either body at any disorder (body physics then irrelevant); physics supplies relations only where disorder is weak; sparse anchors are a poor substitute; repair under disorder needs a self-repairing record. Done: [REGISTRATION_DL002.md](REGISTRATION_DL002.md), [REPORT_DL002.md](REPORT_DL002.md), `results/dl002/` |
> | EN002 | The energy budget on the self-organising body (a forked session; report by the lead). 8 of 8 statements hold. Thermal starvation erases placement in every body, activity starvation does not; the spacing returns in full after any starvation, placement only after mild starvation or with a record; activity starvation delays free repair, heat destroys it without a record; through the heat the record keeps most of the double well's higher-amplitude stripes; coarse domains outlast fine stripes. Done: [REGISTRATION_EN002.md](REGISTRATION_EN002.md), [REPORT_EN002.md](REPORT_EN002.md), `results/en002/` |
> | DL003 | Can a boundary register a self-organised pattern? 10 of 10 statements hold. In quiet tissue, stripes grown slowly out from a boundary across them are registered over the whole sheet (0.998); the same boundary built at once fades within about ten lines, and 64 scattered cells reach 0.891; growth must be slow and run along the stripes, and a front without the boundary's cells registers nothing; under disorder scattered cells win for building and holding, a boundary reaching only a few lines. Done: [REGISTRATION_DL003.md](REGISTRATION_DL003.md), [REPORT_DL003.md](REPORT_DL003.md), `results/dl003/` |
> | LR002 | Body and record correcting each other (a forked session; report by the lead). 8 of 8 statements hold. A record of relations cannot keep itself (its own two repair layers fail above a flip rate of about 10⁻³); relearning its bonds from a body that holds the pattern by itself keeps it at ten and thirty times that rate, a two-copy code; a body teaches only what it holds; under disorder it teaches the disorder, except for coarse domains; parity helps a learning body when errors are sparse and harms it when they are dense. Done: [REGISTRATION_LR002.md](REGISTRATION_LR002.md), [REPORT_LR002.md](REPORT_LR002.md), `results/lr002/` |
> | LR003 | Gated teaching: can a record take its body's help without its errors? 8 of 8 statements hold. Without noise every gate refuses the body's design and the field's distortions; checking whole sites rather than single bonds recovers the body's repair in quiet tissue; but noise opens the gate, which then passes the body's errors; with parity a gate at low noise is LR001's two layers; agreement gives a stronger signal, not new information. Telling a teacher's errors from the record's own needs a third source. Done: [REGISTRATION_LR003.md](REGISTRATION_LR003.md), [REPORT_LR003.md](REPORT_LR003.md), `results/lr003/` |
> | Notes | [THEORY.md](THEORY.md) (the mathematics), [BODIES.md](BODIES.md) (a literature map to biology), [REVIEW_BIOLOGY.md](REVIEW_BIOLOGY.md) (how biological the simulations are), [MODEL_LIMITS_AND_EXPANSION.md](MODEL_LIMITS_AND_EXPANSION.md) (an independent study of the model's limits and ranked expansions), the plans [PLAN_DL001.md](PLAN_DL001.md) and [PLAN_LR001.md](PLAN_LR001.md) |

**Created 24 October 2026 for manuscript v2.3. Status: design and synthetic operator fixtures only. No scientific results or launched jobs.**

How does a system detect a departure from an acquired pattern? How does that signal cause a useful action? Can correction at one scale damage organization at another, or improve the present body while harming its successor?

The ambition is to follow **discrepancy → sensing → action → present expression → outgoing record → future reconstruction**. We start with a controlled spatial model and then test whether a restricted controller predicts when to change the body, change its working reference, or wait. The reference, sensors and actions are supplied mechanisms; their autonomous origin is a separate question.

This lane has **12 dedicated CPUs and shared access to a GH200 GPU**. CPU is the reference implementation and first execution target. The work is designed for block-parallel computation, saved-state branching and repeated futures. GPU acceleration is a later, separately qualified option, not a prerequisite or an assumed speedup.

## Start here

- [Execution handoff](START_HERE.md): instructions for the agent running this lane.
- [Draft protocol](PROTOCOL.md): mechanisms, boundaries, controls, endpoints and staged studies.
- [Lessons and source map](LESSONS_AND_SOURCE_MAP.md): how the previous program constrains this design.
- [Design configuration](design.json): prospective parameters and hardware limits; not a frozen registration.
- [Source manifest](SOURCE_MANIFEST.json): fingerprints of consulted code and protocols.
- [Operator fixtures](operators.py) and [checks](check_design.py): executable mathematics only, not the tissue simulator or a completed interface audit.

Run the synthetic checks from this folder with `python3 check_design.py`. They do not launch a scientific experiment. **There is no scientific `run.py` yet:** source adaptation, independent numerical qualification and a full-cost benchmark are the first implementation tasks.

## Study sequence

| Study | Question | Status / advancement |
|---|---|---|
| ME000 | Are native dynamics, information boundaries and scale operators implemented correctly? | Implement and qualify first; synthetic fixtures alone do not pass this gate. |
| ME001 | Which sensed discrepancies and corrective routes help under body, record and combined damage? | First CPU development study; retain every outcome. |
| ME002 | Can a frozen restricted selector outperform the best fixed route on fresh blocks? | Freeze after development; no automatic confirmation launch. |
| ME003 | Does the advantage survive repeated futures and further record replacement? | Estimate conditional capacity, harms and uninterrupted performance separately. |
| ME004 | Does useful arbitration transfer to new patterns, spatial scales and communication constraints? | Ambitious transfer phase, separate from initial qualification. |

The initial record is a full 256-value reference. This makes mechanism identification tractable; it is not a compact memory claim. A later bottleneck study must count retained reliability state and shared machinery as well as the packet.

The main paper introduces the questions in [§7.3](../../MANUSCRIPT.md#multiscale-error); [SI P.1](../../SUPPORTING_INFORMATION.md#p1) labels this as a proposed study. Existing evidence notes remain unchanged.
