# A local correction makes some original decisions certifiable

**Completed 20 September 2026.** The local conditional correction gives a
useful improvement over the previous signed certificate. At the primary
checkpoint, it certifies **1,298 original decisions as safe**, where the
previous envelope left every original decision unresolved. Grouped beliefs
retain **82.72% of the exact model's mean precision allowance**, up from
73.99%, while every certified policy stays below the unchanged 10% model-risk
limit. Across the earlier checkpoints it also certifies **603 original
decisions as unsafe**, correctly according to their exact-model evaluations.

All **1,384,104 assertions passed in 26.126205 seconds** on one process.
The audit retains all 96 saved checkpoints and 13,056 original query policies,
with 26,112 new certified policies and 13,056 reproduced signed policies.
These are mathematical checks on eight deterministic conditional model
fixtures, not independent empirical observations or measured physical safety.

## What the agent can calculate

The [frozen specification](FEP_LOCAL_RISK_CORRECTION_V1.md) derives the method
before substitution. For each queried edge, fix T=(P_i+P_j)/2, the equal
mixture of one exact conditional update at either endpoint. This operator
preserves the known model's posterior expectation. Therefore

```text
pi(f)-Q(f) = Q(Tf-f) + [pi(Tf)-Q(Tf)].
```

The first term is a signed correction available from model and Q. The second
is bounded using the previous upward/downward mismatch bounds and directional
coordinate increments of Tf. These transformed functions can increase or
decrease with a cause; both directions are retained in the remainder bound.
The expectation and all increments use at most eight local causes on the grid.
No posterior normalizer, exact marginal or action-error label enters certificate
construction. No Gibbs chain is sampled and Q is not updated.

The corrected interval is intersected with the previous signed interval.
This guarantees a combined interval no wider than before, even if correction
alone were worse. The declared correction-only control is retained. On every
saved query, it actually improves the upper bound at the original choice
and permits a strictly larger certified allowance; no standalone loss or tie
occurs at the 1e-12 descriptive threshold. Correction-only and combined
allowances, classifications and reported original-interval widths coincide
on this record. That observation is not a theorem of universal dominance.

All readouts remain capped at the original Q-based allowance. The objective,
original predicted-risk constraint and 10% model-risk limit are preserved.
This tests how much of the existing choice can be certified, without allowing
extra precision beyond what the approximate agent originally selected.

## Primary checkpoint

The primary budget is 4096 logical units per edge. Means weight each fixture
and update order equally; counts count directed query evaluations. Each belief
method contributes 2,176 primary queries. The exact mean precision allowance
is 0.1532759084. An allowance is a probability of using the precision action;
its ratio to the exact allowance is not a percentage of task performance or
a confidence level.

| Quantity | MF independent beliefs | Block joint beliefs |
|---|---:|---:|
| Original, uncertified mean allowance | 0.118219446 | 0.134216376 |
| Previous signed certificate | 0.084002017 | 0.113406061 |
| Corrected/combined certificate | **0.102888098** | **0.126785501** |
| Corrected allowance / exact mean | 67.13% | **82.72%** |
| Corrected allowance / original mean | 87.03% | **94.46%** |
| Relative allowance gain over signed bound | 22.48% | 11.80% |
| Zero allowances, signed → combined | 460 → **0** | 116 → **0** |
| Original choices certified safe | **634** | **664** |
| Original choices certified unsafe | 0 | 0 |
| Original choices unresolved | 1,542 | 1,512 |
| Largest certified-policy model risk | 9.910096% | **9.991196%** |
| Mean true objective regret, signed → combined | 0.195130 → 0.137338 | 0.107911 → 0.067890 |

Each of the 4,352 primary allowances improves. For the 1,298 original policies
certified safe, the full original allowance is retained exactly; the remaining
policies are trimmed to a certified level. True objective regret falls 29.62%
for MF and 37.09% for Block relative to the signed bound. The exact reference
is risk-binding throughout these saved cases, and every certified allowance
is no larger than its exact constrained optimum. The observed regret ordering
uses that verified regime, not a general monotonic-utility assumption.

Mean original-policy interval width falls from 0.00862820 to 0.00558682 for
MF and from 0.00488194 to 0.00318807 for Block, reductions of 35.25% and
34.70%. Mean signed corrections to the original predicted risk are
-0.001797644 and -0.000983878 respectively. Correction alone is not a safety
test: the retained remainder is essential.

At this primary checkpoint, exact evaluation finds **200 unsafe original MF
choices and 156 unsafe original Block choices** at the fixed 1e-10 reference
tolerance. Every one remains unresolved by the certificate. No primary unsafe
choice is falsely called safe, but the method does not identify these smaller
violations as unsafe. The unresolved category contains both safe and unsafe
choices; absence of an unsafe certificate is not a safety conclusion.

## Every primary fixture and update order

Allowance cells show previous signed → corrected/combined. L4 has 48 directed
queries per belief; L8 has 224. The final columns count original choices
certified safe. Every corrected-policy allowance is positive in every row.

| Fixture | Order | MF mean allowance | Block mean allowance | Exact mean | MF safe | Block safe |
|---|---|---:|---:|---:|---:|---:|
| L4, h=1e-6, failure | forward | 0.02287095 → 0.04692073 | 0.06725264 → 0.08243794 | 0.11297034 | 24 | 38 |
| L4, h=1e-6, failure | reverse | 0.02287100 → 0.04692076 | 0.06725264 → 0.08243794 | 0.11297034 | 24 | 38 |
| L4, h=1e-6, mixed | forward | 0.10495697 → 0.11927562 | 0.13744559 → 0.15753580 | 0.20443543 | 26 | 20 |
| L4, h=1e-6, mixed | reverse | 0.10495697 → 0.11927562 | 0.13746746 → 0.15753438 | 0.20443543 | 26 | 20 |
| L4, h=.01, failure | forward | 0.08835345 → 0.10646216 | 0.11866640 → 0.12489011 | 0.13423097 | 0 | 0 |
| L4, h=.01, failure | reverse | 0.08835345 → 0.10646216 | 0.11866640 → 0.12489011 | 0.13423097 | 0 | 0 |
| L4, h=.01, mixed | forward | 0.15814053 → 0.18432879 | 0.19973711 → 0.20966528 | 0.22483583 | 0 | 0 |
| L4, h=.01, mixed | reverse | 0.15814053 → 0.18432879 | 0.19973711 → 0.20966528 | 0.22483583 | 0 | 0 |
| L8, h=1e-6, failure | forward | 0.02013344 → 0.03796667 | 0.03878832 → 0.05554386 | 0.08590219 | 152 | 203 |
| L8, h=1e-6, failure | reverse | 0.02013373 → 0.03796673 | 0.03878830 → 0.05554386 | 0.08590219 | 152 | 203 |
| L8, h=1e-6, mixed | forward | 0.07639705 → 0.09002477 | 0.09609045 → 0.11686067 | 0.16866982 | 115 | 71 |
| L8, h=1e-6, mixed | reverse | 0.07639705 → 0.09002477 | 0.09612905 → 0.11685793 | 0.16866982 | 115 | 71 |
| L8, h=.01, failure | forward | 0.07068834 → 0.08453449 | 0.08883065 → 0.09545647 | 0.10535193 | 0 | 0 |
| L8, h=.01, failure | reverse | 0.07068834 → 0.08453449 | 0.08883065 → 0.09545647 | 0.10535193 | 0 | 0 |
| L8, h=.01, mixed | forward | 0.13047522 → 0.15359151 | 0.16040710 → 0.17189595 | 0.18981075 | 0 | 0 |
| L8, h=.01, mixed | reverse | 0.13047522 → 0.15359151 | 0.16040710 → 0.17189595 | 0.18981075 | 0 | 0 |

The difficult L8 rare-failure Block case now retains 64.66% of the exact
mean allowance, up from 45.15%, and certifies 203 of 224 original choices
safe in each order. Its allowance is still below the exact 0.08590219 mean.
In L8 rare-mixed, Block retains about 69.28% of exact and certifies 71 original
choices safe per order. The previous 54 zero allowances per order disappear.

At the primary checkpoint the smallest corrected allowance is 0.000113411
for MF and 0.009747357 for Block. Thus eliminating zeros does not mean every
case permits substantial precision. Block's corrected mean exceeds MF's in
every matched fixture/order; that is a case-mean statement, not per-query
dominance between inference methods.

## All budgets and the unsafe certificates

The original-choice classifications below use the combined envelope. All
corrected-policy zero counts are zero. Every certified-policy risk is below
10%, including where the original policy is certified unsafe.

| Budget | Beliefs | Signed mean allowance | Corrected mean allowance | Original safe | Original unsafe | Unresolved | Largest certified risk |
|---:|---|---:|---:|---:|---:|---:|---:|
| 256 | MF | 0.079604339 | 0.101914580 | 670 | 0 | 1,506 | 9.906165% |
| 256 | Block | 0.120796372 | 0.131252968 | 579 | 603 | 994 | 9.981042% |
| 1024 | MF | 0.083162927 | 0.102737232 | 637 | 0 | 1,539 | 9.910388% |
| 1024 | Block | 0.113163921 | 0.126746324 | 681 | 0 | 1,495 | 9.991048% |
| 4096 | MF | 0.084002017 | 0.102888098 | 634 | 0 | 1,542 | 9.910096% |
| 4096 | Block | 0.113406061 | 0.126785501 | 664 | 0 | 1,512 | 9.991196% |

Across all saved checkpoints, **3,865 original choices are certified safe,
603 unsafe and 8,588 unresolved**. Exact-reference readback finds no false
safe or false unsafe classifications. Every one of the 13,056 combined
allowances strictly improves over the preceding signed allowance.

All 603 unsafe certificates occur for Block at budget 256 and h=.01:
L4 failure has 30/29 forward/reverse, L4 mixed 7/10, L8 failure 198/198,
and L8 mixed 68/63. The smallest certified unsafe margin is 1.79307e-6 in
risk probability, above the 1e-10 reference tolerance. At that budget, exact
evaluation finds 1,124 unsafe original Block choices: 603 are identified and
521 remain unresolved. The 579 safe certificates all agree with exact risk;
473 other safe choices remain unresolved. These are descriptive coverage
counts on fixed queries, not estimated population error rates.

The smallest safe-certificate margin over all budgets is 1.48303e-6. Primary
minimum safe margins are 0.000106086 for MF and 2.84105e-6 for Block. The
classifications are not numerical decisions made at a 1e-30 padding scale.

More variational work still does not monotonically increase certified action.
Block's mean allowance is higher at 256 than at 1024 or 4096, even after
the correction. No best budget or stopping rule is selected from this result.
Earlier scalar KL baselines remain unchanged and permit essentially zero
precision; their saved summaries are reused without repeating root solves.

## Qualification, precision and cost

All thirteen accepted mathematical cases pass: twelve two-node checks and
the noncontractive antitone K4. The increasing-factor control is rejected
before certification. Independent full-state enumeration verifies the local
update formulas, posterior expectation invariance, signed correction identity,
Q expectations and both positive and negative coordinate increments. Risk
coverage is checked at fixed policy points and all chosen policies. The K4
bound remains valid with alpha greater than one; no contraction is presumed.

Certificate construction uses 60-digit Decimal arithmetic with fixed 1e-30
guards. The largest saved-reference discrepancy is 1.88738e-15. Independent
posterior-conditional checks differ by at most 3e-60; the correction identity
residual is at most 1.28e-60 and operator-invariance residual at most 1e-60.
Original signed vectors and policy values reproduce their preceding record.
These numerical checks accompany the analytic proof; they are not a formal
interval-arithmetic verification.

The grid operators use five to eight causes. On L4/L8, their Q marginal sums
cover 2,560/19,968 assignments per belief and 7,680/59,904 expectation terms
for the three compiled functions per edge. Preparation is shared across
beliefs for each model: operator construction takes 39.92–394.27 ms, and
total model-plus-operator preparation 49.94–443.45 ms.

At the primary checkpoint, Q reconstruction plus the complete combined
certificate averages **165.30 ms for MF** and **149.21 ms for Block**.
Ranges are 39.57–307.51 ms and 37.98–284.06 ms respectively. Correction/query
work alone averages 121.43 ms for MF and 92.95 ms for Block. These timings
exclude exact-reference evaluation and integrity I/O; shared preparation is
reported separately. The block factorization changes the local marginalization
work, so more structured beliefs need not cost more in this readout.

The complete audit takes **26.049731 CPU seconds** and **26.126205 wall
seconds**, using one Python 3.10.12 process. The new bound costs more than
the previous signed readout. Original primary inference costs remain
0.496–1.906 seconds for MF and 0.170–0.357 seconds for Block, while exact
inference costs 0.127–0.175 seconds and was faster in each matched case.
Adding the correction does not establish an end-to-end computational advantage.
At these sizes, the result's value is a guarantee available without exact
answers, not evidence that approximate inference is the cheaper solution.

## Record, FEP interpretation and next question

The first attempt began at **2026-09-20T16:34:43.142205+00:00**. The
41,914,252-byte record is at
`/mnt/bioIce1/fep-ideas/formal-checks/fep-local-risk-correction-v1/attempt-01/`.
All sixteen input/seven output identities match. Independent readback of the
query file reproduces all 96 case summaries, classifications, regrets, zeros,
risk maxima and allowance ordering, and checks every stated safe/unsafe
classification against its exact risk. All prior records and manuscripts
retain their identities.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Specification | 10,865 | `28ed641d0dc3328d0dcfb2bd885ae8a43a1f8b2750ddc30617b4258d529f4e00` |
| Checker | 29,112 | `2dc09583c43bdc236506d262de84cbc36b859656cff2449bba3392e6ea09368f` |
| Manifest | 5,871 | `dddd352612b2c8c1f0d2d19c8625e2ad0e725ffe60f81838e2cb4e2977c739bf` |
| Results | 4,507,897 | `fc60b86911fa8a790d0f81d347ad5706c797855c558b9b3f7e0826943cfea940` |
| Queries | 37,308,693 | `cc4bc5354f082c2b3df199a32b0e1f5c97f2da0f49a8f4fc4bbfdc0b22772754` |
| Run log | 2,250 | `b112bb896e62b78709480321e06deb010b7e925fee3e83a0d1348145c167a699` |

No failed attempt, post-execution source correction, duplicate scientific
run, inference update, scale run, outcome retuning or manuscript integration
occurred. Sister projects were neither searched nor edited. The original
structured-inference mechanism gate remains failed and its scale phase skipped.

The FEP contribution is a concrete connection from imperfect variational
beliefs to useful, model-certified action. A local conditional correction
can distinguish some overly cautious predictions from some unsafe original
choices, using information available to the agent. A lower internal objective
alone is still insufficient, and a matched Bayesian agent can use the same
certificate. No FEP-exclusive advantage, model-adequacy guarantee or autonomous
maintenance mechanism has been demonstrated.

The next useful question is **how much decision quality the agent can prove
it is still missing**, without an exact answer. Derive a bound on true
decision regret from the available risk intervals and unchanged objective,
including the unknown exact feasible optimum. Such a bound could support a
declared decision-based stopping tolerance. Derive feasibility, cost and
failure conditions before testing it; do not select a favourable inference
budget or tolerance from these outcomes. This proposes a bounded analytic
follow-up, not a new inference campaign or revival of the failed scale gate.
