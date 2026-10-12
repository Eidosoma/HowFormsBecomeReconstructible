# P2 — Durable population restoration and communication context

Registered 2026-09-09 before any P2 native integration. Authorized by the
user's “let's go” after the proposed combined reversal/communication study.
This is the first stage only: no 2D/3D campaign or serial-lineage extension.

## Question and deliberately limited claim

P1 showed acquisition, isolated retention and one onward M-state handover
in 16/24 main conditions. Here we ask whether E neighbours can restore those
actually exposed cells to E, whether restoration persists after helpers AND
the intervention are removed, and whether two fixed cells can transmit E.
This extends the paper's normalization-versus-spread question. E/M labels
are regulatory states, not diagnoses; no proliferation, movement, survival,
new attractors, autonomous reproduction or clinical treatment is simulated.

One known positive P1 history is intentionally selected for this discovery
experiment: bridge__depol__s6__p60 from
runs/paper-memory-20260909T094809Z-yna2d02r. Its isolated_2 LIVE final array
contains 19 originally E cells, original:06 through original:24, now M.
Use its first 2, 6 or 11 cells, without resampling or rewriting any regulator.
This is not independent replication across acquisition histories. The P1
results informed this design, but no P2 pilot or parameter search is allowed.

Fresh E helpers use that history's last RETURNED preparation snapshot,
column 6; fresh M probe cells use column 0. They are separately supplied
reference cells, not offspring and not age-matched to the exposed cells.
Source arrays and identities must be copied exactly. Original P1 M donors,
restoration helpers and diagnostic outputs never become onward carriers.

## Registered 48-case panel

Six gate cases precede the 42 new continuations:

- Four exact P1 replays: the onward_contact and two onward isolated holds
  of depol/s6/p60, depol/s6/p8, hypol/s11/p60, nbrDepol/s11/p8. Rebuild from
  those cases' held carriers and reference snapshots. Require bit-identical
  initial/final/sampled trajectories and identity/settings agreement with P1.
- Two neutral-assay controls: two ordinary E or two ordinary M reference
  cells flank a fresh M cell. E must install retained E; M must retain M.
  A failed assay/source gate stops the panel without changing it or retrying.

The 42 continuations are:

- 24 factorial cases: patch sizes 2/6/11 in a 25-cell line, two base miRNA
  diffusion settings (1.25e-14, 2e-13), four intervention combinations.
- Six border controls: each size and voltage setting, at 1.25e-14 with
  M-associated expression power 60, changing GJ_OiET from .5 to 0.
- Four miRNA-blocked controls: size 6, low diffusion, all four interventions;
  miRNA is blocked during restoration only. Ion communication remains.
- Two helper-free controls: six actual exposed cells, either voltage rule,
  zero intercellular transport during the age-matched restoration interval.
- Six finer continuations: size 6, all four interventions at low diffusion,
  plus neither/both at high diffusion. Refine all NEW phases, not P1 history.

The four factorial interventions use unchanged native algorithm_on rules:

| Name | Native voltage mode | M-associated junction power |
| --- | --- | --- |
| neither | depol | 60 |
| voltage | hypol | 60 |
| expression | depol | 1 |
| both | hypol | 1 |

“Expression restoration” removes the M-associated overexpression advantage;
it is NOT a uniform increase in communication. The two base diffusion values
separately vary the miRNA communication background. Native small-ion base
diffusion is unchanged. Border-only comparisons preserve power 60 within
M-like groups while changing the mixed-state edge expression rule. These
rules depend continuously on cell state, not on permanently labelled regions.

Source hypol is a code identifier, not a physically calibrated hyperpolarizing
treatment: it removes the extra state-dependent K gate. Actual voltages and
border/internal expression factors must be recorded. Native Cx45 voltage
gating remains present; no voltage clamp or direct concentration edit is used.
No underexpression mechanism or claimed exact Table 1 replication is added.

## Restoration, intervention withdrawal and a common onward assay

Place the selected held patch first, followed by 25-minus-size fresh E helpers.
Apply the registered settings for 20,000 model units. In helper-free controls,
there are just six isolated exposed cells for the same duration.

Remove ALL helpers. Retain the actual final patch array, return every condition
to the common native depol rule/power 1, and turn off all junction transport
for 10,000 + 10,000 units. There is no neighbour-reading rule in these P2
conditions. This tests retention without either continuing helper contact or
continuing voltage/expression intervention. Retain finite negative/mixed states.

Always take original:06 and original:07, even if either failed restoration.
For larger patches these lie away from the helper-facing edge. Partial edge
restoration may therefore coexist with a failed fixed-carrier assay; both
graded patch counts and the selected carrier outcomes must be reported.
Place one fresh M reference cell between them in a three-cell line. This is
a neutral majority-E-capability assay, NOT a repeat of P1's two-to-14 invasion
test: native hypol, power 1, GJ_OiET=.5, miRNA diffusion 1.25e-14, for 20,000.
Remove both carriers and return the recipient to depol/power 1, fully isolated,
for 10,000 + 10,000. Every branch receives this identical assay, including
failed, helper-free and restoration-blocked branches. No winners are selected.

This small calibrated assay prevents “no onward restoration” being confused
with an assay where even ordinary E carriers cannot transmit. It measures
one finite transfer, not a spreading E population or self-renewing heredity.

48 cases, 270 native integrations (six gate cases x three phases, 42 x six).
No additional integrations or continuation rounds are started automatically.

## Independent outcomes, provenance and limits

Independently reconstruct native E/M/X (strict +/-2 mRNA-total difference),
actual voltage, Cx45 gating, continuous M-associated expression, native
potassium rule, topology, all array/identity handovers and fixed reference
inputs. Save full trajectories, native live endpoints and physical settings.
The unchanged adaptive integrator may overshoot its requested horizon on the
last step; preserve its actual sample times instead of imposing a new solver
or an arbitrary one-unit overshoot limit. All durations are model-time units.

Report patch E count and helper M count after contact (including harmful
spread), stable patch E after withdrawal, the two fixed carrier labels, and
retained E in the fresh probe. A strict retained label requires the final
label and >=95% of late-quarter samples in BOTH isolated holds. Strict onward
restoration additionally requires BOTH fixed carriers stably E. Never infer
an outcome from successful software execution or require positive new science.

Compare the four settings at matched size/background; report combined versus
single-factor effects without declaring mathematical synergy by inspection.
Border controls distinguish within-group reinforcement from boundary access.
Finer continuations must agree in endpoint labels/outcome counts; continuous
differences are reported. Disagreement is not silently retuned away.

Re-audit P1 read-only before all new integration. Freeze configuration,
protocol, all execution dependencies/tests, native revision, predecessor
audit, and the exact source artifacts before gate cases. Require unmodified
BITSEY b2cb370aaecbc8299f259bc4251d5396c81f19a6 and unchanged older artifacts.
The registered source/table discrepancies remain unresolved.

Two single-threaded workers, 5,400 seconds/case, 28,800 seconds (eight hours)
for the panel. Detached supervisor caps: runner 29,100; final audit 900;
overall 30,300 seconds. At least 5 GiB free. No deletion, automatic retry,
outcome-based source choice, alternate protocol or follow-on launch. Planning
estimate 3–6 hours, uncertain with shared-host load. Runs over ten minutes
stay detached for user polling. Software fixtures precede native integration.
