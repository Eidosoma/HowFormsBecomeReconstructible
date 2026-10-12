# S8P — Strict-8 stronger-reading probe
# (exploratory preregistration, written 2026-08-16 BEFORE the campaign ran)

**Status: separate from the current paper.** One campaign, three
registered readouts, launched from the archived Phase H certified
episodes. Exploratory: predictions are registered for honesty, but
nothing here carries confirmatory weight for the current paper, and
its results are reported only in this directory.

## Question

The "stronger reading" of the strict-8 event would treat certified
episodes as something like nascent individuals. Three named tests:

- **R1 (recurrence):** do strict-8 coherent episodes recur after
  perturbation, beyond what matched ordinary states produce?
- **R2 (accumulation):** does anything accumulate *within* a natural
  episode that increases future durability — with no external
  controller?
- **R3 (dissipation):** does persistence correlate with dissipation
  (activity/turnover), the accessible analog of "dissipative
  adaptation" (England-style: persistent states of driven matter as
  high-dissipation histories)?

## Cohort (deterministic, outcome-blind beyond Phase H positivity)

From `replication/results_strict8_occurrence/strict8_units.pkl`
(sealed Phase H archive; its preregistration froze it for a later
separate study): per candidate, select up to 240 positive episodes
breadth-first — for each matrix ascending, positives ordered by
(landmark, branch); round j takes the j-th positive of every matrix
until the cap. Each selected episode contributes its stored
P_old-distinct daughters D_1…D_8 and its launching restored landmark
state (the matched natural control from the same matrix).

## Campaign (seed domain 26, entropy tag "strict8-prep" / 2026-08-16)

Per episode, six arms × 24 branches × F24 fresh futures:

| arm | launch state | perturbation |
|---|---|---|
| ep8-none | D_8 (episode end, age 8) | none |
| ep8-k4 | D_8 | k=4 random type swaps (frozen F3/F4 helper) |
| ep8-k8 | D_8 | k=8 swaps |
| ep1-none | D_1 (episode start, age 1) | none |
| nat-none | restored landmark state | none |
| nat-k8 | restored landmark state | k=8 swaps |

Growth streams: (26, 0, cand_i, m, lm, b, arm_i, br); perturbation
streams: (26, 1, …, arm_i). Candidates never pooled; the catalytic
matrix is the bootstrap unit (2,048 draws, seed 11); all intervals
are descriptive.

## Registered endpoints per future (frozen before running)

- t_break: first boundary with H ≤ 0.9; censored at 25 if none in 24.
- COH8: exists a window of 8 consecutive inherited boundaries whose 8
  daughters are pairwise > 0.9 (28 pairs; no break precondition).
- Episode identity anchor: the normalized centroid of the stored
  D_1…D_8. SAME8 = COH8 window with all 8 daughters > 0.9 to the
  anchor; NEW8 = COH8 window with all 8 daughters ≤ 0.85 to the
  anchor. First qualifying window recorded.
- Dissipation proxy: candidate 02 — leave-event churn per fission,
  (updates − net mass gain)/2, exact from the Gillespie contract;
  candidate 03 — vector-Poisson step count (activity proxy only;
  caveat registered). Early-window dissipation = mean over fissions
  1…min(6, realized).

## Registered analyses

- **R1:** per arm: P(COH8), P(SAME8), P(NEW8), mean t_break. Key
  contrasts (paired per episode, matrix bootstrap): ep8-k8 − nat-k8
  on SAME8 and COH8; ep8-none − nat-none as the unperturbed baseline.
- **R2:** paired per-episode ep8-none − ep1-none on mean t_break and
  P(COH8). Positive = natural within-episode accumulation. Also
  descriptive: Spearman of the episode's stored observable run length
  (beyond 8) vs its ep8-none persistence.
- **R3:** within-episode Spearman across the 24 ep8-none branches of
  (early churn, t_break); aggregate = mean rho with matrix-bootstrap
  CI, plus median. Also paired episode-vs-natural early-churn
  contrast (are certified-episode states more dissipative than
  matched ordinary states?).

## Registered predictions (from the current paper's body of results)

- R1: NO same-identity recurrence advantage after k8 (Phase E basin
  radius 0; G1 relaxation to matrix-typical): SAME8 after k8 ≈ 0 in
  both classes; any COH8 recovery is matrix-level, so
  ep8-k8 ≈ nat-k8 on COH8.
- R2: ≈ 0 or weakly positive (G3 hysteresis existed only under
  sustained external steering; natural episodes may self-select
  stability rather than accumulate it).
- R3: registered two-sided; mechanistic lean positive (tight webs
  have high bn, hence high turnover at fixed mass — the persistent
  states should also be the fast-cycling ones), which would be the
  dissipative-adaptation-consistent sign.

## Boundary

Occurrence-adjacent probing only: no model fitting, no controller,
no beta surgery. Whatever the outcome, it establishes correlations
and conditional rates in this simulator — not individuality, not
memory, not thermodynamics (the churn proxy is event-counting, not
an entropy production measurement).

---

# RESULTS (appended 2026-08-16; nothing above edited)

Campaign: 480 episodes (240/candidate, 142 matrices each), six arms ×
24 branches × F24; self-test 5/5; 769 s on 12 workers. Raw units in
`results/s8p_units.pkl`; aggregates in `results/s8p_results.json`.
t_break is censored at 25 (~40% of branches reach the horizon).

## R1 — recurrence: REAL but small, mostly matrix-level, and
## remarkably shock-proof (registered prediction WRONG)

SAME8 (re-certifying a coherent-8 matching the episode's own
centroid), cand 02 / 03: ep8-none 0.168/0.174; **ep8-k8 0.161/0.166**
— a k8 shock barely dents same-identity recurrence. Matched natural
states from the same matrix: nat-none 0.141/0.149, nat-k8
0.135/0.132. Paired episode-minus-natural contrasts (matrix
bootstrap): SAME8 after k8 **+0.0219 [+0.0075,+0.0390] /
+0.0299 [+0.0136,+0.0490]**; COH8 after k8 +0.0158 [+0.0019,+0.0311]
/ +0.0242 [+0.0088,+0.0424]; unperturbed baselines similar. We
registered SAME8 ≈ 0 after k8 and no episode advantage; both were
wrong. Reading: the episode identity is regenerated primarily by the
MATRIX (natural states re-certify it at 13–15% — these episodes live
in high-occupancy composomes, consistent with the F6 distributional
attractor), plus a small, real, perturbation-robust state-level
increment (+2–3 points) for having been at the episode's end.

## R2 — accumulation: ABSENT; if anything, slight decay with age
## (self-selection, not accumulation)

Paired ep8-none − ep1-none (same episode, age 8 vs age 1): t_break
**−0.62 [−0.89,−0.33] / −0.39 [−0.71,−0.06]** fissions; COH8
−0.009 [−0.021,+0.003] / **−0.015 [−0.028,−0.003]**. Nothing
accumulates within a natural episode; the episode start is marginally
its most durable moment. Meanwhile BETWEEN episodes, longer observed
run length predicts more persistent futures (Spearman +0.228/+0.235)
— stability is a property of the episode/matrix (selection), not a
quantity the lineage builds up (accumulation). This dissociation is
exactly the registered alternative to G3's steering-induced
hysteresis, which does not appear under natural conditions.

## R3 — dissipation: POSITIVE persistence–turnover coupling, the
## dissipative-adaptation-consistent sign

Within-episode across branches, Spearman(early leave-event churn,
t_break): **+0.248 [+0.214,+0.278]** (02, exact churn) and
**+0.169 [+0.136,+0.203]** (03, step-count proxy; registered
caveat); n ≈ 224 episodes each. Branches that cycle faster early
persist longer. Episode states are also more dissipative than
matched natural states in 03 (+3.4 [+2.2,+5.0] events/fission; 02
+4.6 [−3.4,+10.3], CI spans 0). Mechanism as leaned in the
registration: tight catalytic webs raise bn, hence turnover at fixed
mass — persistence and dissipation are coupled through web
tightness. Correlational only: no entropy-production measurement and
no causal dose test was run.

## Prediction scorecard

R1 registered "no same-identity advantage after k8" — WRONG (small
robust advantage; SAME8 after k8 is 16%, not ≈0). R2 registered "≈0
or weakly positive" — sign came out weakly NEGATIVE; the
self-selection alternative named in the registration is what the
data support. R3 registered two-sided with a mechanistic lean
positive — positive, both candidates.

## Boundary (unchanged)

Correlations and conditional rates in this simulator, launched from
Phase-H-certified states. Not individuality, not memory, not
thermodynamics. Not part of the current paper.
