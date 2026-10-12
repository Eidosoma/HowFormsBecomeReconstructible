# Equal-count writing schedules: unrun development proposal

Status: DRAFT_NOT_FROZEN. This follows the completed pulse recovery analysis.
It is a concrete next design, not a launched experiment, a fitted forecast or
a prospective confirmation of RDT-P01.

Compare six tolerance-writing events with the original writer at every other
generation. Use the same generation-3 pre-write boundary, damage and randomness
as the development pilots. Hold the first event at generation 3, the last at
13, and all subsequent writes at generations 14–32 to O.

| Schedule | Tolerance-writing generations | Original writes after final event |
|---|---|---:|
| Spaced | 3, 5, 7, 9, 11, 13 | 19 |
| Initial event followed by a late cluster | 3, 9, 10, 11, 12, 13 | 19 |

Both schedules have six T events and the same first and last event. The late
cluster deliberately retains the common initial event; a wholly consecutive
six-event burst would otherwise change the first event while matching the last.
Spacing is the assigned treatment. Intermediate body states are expected to
differ and are consequences of that treatment, not variables to match afterward.

Six events give a bounded intermediate dose between the tested one-event pulse
and tolerance writing at every generation 3–32. Existing continuous-tolerance
histories already lose body performance after several writes. This choice is
outcome-informed development design; it does not constitute a power calculation
or promise a detectable difference. The generation-13 cutoff leaves 19 original
writes in both arms to distinguish final competence from immediate post-pulse
expression. No dose or schedule sweep is proposed.

Simulate only the two new schedules and an O replay reference on the same eight
development blocks. Reuse the completed O/P/T controls with explicit provenance,
without increasing the count of independent observations. Require the first
altered packet to match both completed T and P records, the shared initial
bodies to match, and O to reproduce every boundary and terminal assay. Record
the actual writer at every generation; after generation 13 it is O in both
new arms. Freeze code, endpoints and schedule masks before simulation.

The primary descriptive contrast is spaced minus late-cluster strict both-cue
success in the generation-32 scattered terminal assay, with paired rescued and
harmed lineages and all eight block contrasts. Body success, margins and
outgoing transmission over the whole history are secondary. Report outcomes
after the final pulse separately from the final assay. Use the existing fixed
64-step diagnostic; do not select a new propagation depth from these outcomes.

Candidate directional hypothesis: interposed original writes improve terminal
success at a fixed number and span of tolerance events. A positive difference
supports a benefit of this spacing schedule, not return to the original network
or a universal repair interval. A near-zero result leaves the hypothesis
unsupported and may expose ceiling/floor limitations; report those limitations
without changing dose afterward. A negative difference contradicts the proposed
direction and may indicate that early separated insults are more damaging than
the late cluster in this domain. None of these outcomes alone confirms P01.

Before execution, benchmark the implementation on known trajectories and retain
the existing one-hour conservative CPU ceiling for a three-policy, eight-block
pilot. Use one numerical thread. If the forecast exceeds the ceiling, revise
the resource plan explicitly before observing new schedule outcomes. If longer
than 600 seconds, run detached with frozen inputs, automatic verification and
COMPLETE/FAILED receipts, leaving it unpolled as the user requested.

An eventual predictor test is separate: fit on declared development histories,
include future writer schedule in the forecast contract, freeze an early-probe
budget and quantitative scoring rule, and then predict a new schedule and new
blocks before viewing their outcomes. Compare against expression/context
baselines and a conventional dynamical model. All currently inspected E051
blocks are burned for such a holdout.
