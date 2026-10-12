# E016 — teaching consistency and routing capacity

Status: **complete and independently audited. Consistent teaching improves
conditional routing, but all three regimes fail the original reliability
criterion.** E015's failed feasibility result remains unchanged. No renewal
was started and no job remains running.

Exactly 32 fresh blocks (128 founders, 64512 scored trials) compared ordinary
teaching, coordinated opposing teaching episodes, and an engineered routing
record with the reader fixed at gain 2. Every founder, cue and failure counted.

| Record regime | Intact individual-cue success | Intact both-cue success | Scattered-loss individual-cue success | Original gates passed |
| --- | --- | --- | --- | --- |
| Ordinary teaching | 43.5% | 18.4% | 32.4% | 17/24 |
| Consistent teaching | 67.9% | 35.9% | 53.4% | 18/24 |
| Engineered capacity control | 66.5% | 33.0% | 56.2% | 18/24 |

The single prespecified primary comparison passed: consistent minus ordinary
intact **both-cue success increased by 17.58 percentage points [95% whole-block
interval 12.50, 23.05]**. Coordinating the two lessons helps these fresh bodies
respond appropriately to opposing inputs. It changes the joint teaching history
and record structure, so this does not isolate scalar cancellation as the sole
mediator. Secondary individual-cue improvement was 24.41 [18.46, 30.66] points
intact, 21.00 [16.41, 25.68] under scattered loss, and 26.56 [20.61, 32.71] under
square lesions; these intervals are pointwise.

Consistent and engineered records passed all control-advantage gates but failed
all six absolute reliability gates. The engineered record did not establish
sufficient capacity under this prescription, and is not an optimality bound.
Input-isolated controls had exactly identical responses to opposing cues and
zero both-cue successes. Inherited competence remains untested. How the input
controls the body's evolving response is a useful next diagnostic question;
no successor study has been launched.

A later [saved-trace diagnostic](analysis/saved_dynamics_v1/REPORT.md) found that
89.97% of intact failures with consistent records and 84.84% with the engineered
record had strongly wrong outputs that were quiet over the declared final
window. Engineered intact accuracy changed from 66.11% at step 256 to 66.50% at
512, while scattered-damage performance was still improving more. These are
post hoc clues. The next proposed test compares additional runtime with delayed
local self-amplification at matched total duration; finite-time quiet outputs
alone do not establish premature commitment or a stable attractor.

- [Frozen protocol](PROTOCOL.md), [full report](runs/comparison_v1/REPORT.md),
  [summary](runs/comparison_v1/summary.json).
- [Independent audit](runs/comparison_v1/INDEPENDENT_AUDIT.json),
  [figure](figures/comparison_v1/teaching_consistency.png),
  [closeout verification](analysis/closeout_v1.json).

Three corrected short fixtures and the full benchmark audit passed; the initial
technical fixture failures are retained. The 474.46-second conservative forecast
permitted foreground execution. Simulation took 122.62 seconds and audit 109.67;
the full workflow including figures took 233.69 seconds with at most 12 CPUs.
The audit replayed every teaching and reader trajectory exactly, reconstructed
records, masks, scores, intervals and gates, and verified input isolation.
Coordinated teaching symmetry held within 1.72e-14, below its declared 1e-10
tolerance. Frozen inputs, outputs and figure provenance passed closeout checks;
the figure was visually inspected. E014/E015 frozen inputs remain unchanged.

All writes stayed in the experiments tree. Teaching goals, episode coordination
and the engineered record are supplied apparatus; manuscript work remains with
the separate paper agent.
