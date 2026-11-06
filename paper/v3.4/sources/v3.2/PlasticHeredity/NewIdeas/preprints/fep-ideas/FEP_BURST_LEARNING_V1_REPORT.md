# FEP 2: reliability learning protects stable costs but fails timing transfer

Completed and independently verified 30 October 2026 under the
[prospective protocol](FEP_BURST_LEARNING_V1.md). This completes the second
of the user's two authorised side studies. The first is reported in
[FEP 1: correlated errors](FEP_BURST_CONFIDENCE_V1_REPORT.md).

**This candidate does not pass the recovery criteria.** It satisfies the
stable-cost constraint at all five new persistence settings and suppresses
high-confidence orientation mistakes. Nevertheless, its full-prior recovery
cost is .210–.219, against .1 for always purchasing and .094–.096 for the
previous hybrid. Every withheld even reversal onset is worse than the hybrid,
both on full-episode cost and recovery. All feedback fees are included.

Reliability updating helps some outcomes, but the predeclared causal criterion
fails: the full agent has higher R and B+R than its frozen-reliability ablation
at every held-out setting. It beats the conservative rule and the selected
fixed schedule, yet those controls also fail recovery. Ordinary Bayesian
planning with the same model and objective agrees with the candidate.

The sharp timing failure limits what this experiment says about reliability
learning. Selection assigned zero loss weight to even reversal onsets, while
evaluation restored their original weight. The controller still represented
those onsets in its beliefs. Thus a correct planner could neglect losses that
were absent from its training objective. This is a failed transfer test of
the specified candidate, not a general impossibility result for reliability
learning or a comparison that isolates richer inference from the changed
training objective of earlier controllers.

## What was frozen and tested

The ten-task horizon, reversal probability 1/2, full generative prior over ten
onsets, error marginal .05, accurate-feedback price .1 and unit unaided-error
cost remain fixed. The stable budget is K=.0955500613134765625. Unbought
targets/losses and the true hidden states are unavailable to the controller.

The model has 44 hidden states: eleven reversal possibilities, two persistence
classes a in {0,.75}, and the current binary sensor-error state. Classes have
equal prior probability. The error process advances on every task, including
tasks without a purchase. Purchased targets reveal the discrepancy between
the sensor and the correct answer. The agent infers current reliability and
persistence; the stationary 5% base error rate is supplied, not learned.

Selection used stable worlds and odd onsets {1,3,5,7,9} at a=0 and .75.
It minimized mean(B_odd+R_odd), with a separate stable constraint at each
training persistence. Six exact full-horizon planners used penalties
mu={0,1,2,4,8,16}; a never-purchase floor completed the seven-policy pool.
The finite-pool mixture solver enumerated twelve feasible vertices and chose:

| Component | Exact episode weight | Approximate weight |
| --- | --- | --- |
| full_mu00 | 1366232085590/1622358440173 | .842127148 |
| full_mu01 | 256126354583/1622358440173 | .157872852 |

Training objective C=.1447341571. Training S values are exactly K and
.0666428591. This is optimality within the declared pool, not all possible
policies. The selected mixture, controls and training evidence were frozen
before any new-candidate even-onset or new-duration scores were computed.

All 1,024 fixed purchase schedules were considered with the full reliability
filter and posterior-MAP unaided answers. The best feasible training schedule
buys on tasks **2,3,5,7,9** (mask 342), C=.1847555499, with training stable
costs .0930304594 and .0646845303. Its optimality is within this specified
schedule/MAP class. The conservative control buys on 2,4,6,8,10 and changes
direction after two successive purchased labels favour the opposite direction.

The reliability ablation preserves the updated onset marginal but resets
its conditional persistence/error state after observations, also in imagined
updates. It retains observation access and orientation learning. It uses the
same mu values and selected component weights, with no separate retuning.
The two agents face the same physical path distribution but can buy different
subsets of observations. The intervention includes effects on planned
information use; it is not merely an offline change to confidence scores.

New physical persistence values are .125,.375,.625,.875,.95. Their underlying
mean error-run lengths are approximately 1.203,1.684,2.807,8.421,21.053 tasks;
the actual observation horizon remains ten tasks. None of these persistence
values was in FEP 1 or the fitted model's two-class support. Even onset losses
were held out from new-candidate selection, although even onsets were already
known to the project and remained in the generative prior.

## Held-out costs and recovery

S is stable-world cost per task. B is full-episode cost per task under the
original deployment prior. R averages normalized post-reversal cost over all
ten onsets. Each held-out setting must satisfy S<=K, R<.1 and R<R_hybrid.

| Persistence | New S | New B | New R | New even-onset R | Hybrid R |
| --- | --- | --- | --- | --- | --- |
| .125 | .093201201 | .105755507 | .210717603 | .345062192 | .095802589 |
| .375 | .085481743 | .099710130 | .210470683 | .351078122 | .094519682 |
| .625 | .073829048 | .091032419 | .212356082 | .361556754 | .093807035 |
| .875 | .058580515 | .079828622 | .216720545 | .376943584 | .093968267 |
| .95 | .053301056 | .075983653 | .218718323 | .382742752 | .094052503 |

Stable cost passes all five settings; both recovery comparisons fail all five.
Odd-onset recovery is .076373,.069863,.063155,.056498,.054694 respectively.
All odd onsets improve over the hybrid in both full cost and recovery; all
even onsets worsen in both. Recovery still exceeds .1 when onset 10 is removed:
.146828,.141931,.137591,.134329,.133810. The failure is not confined to the
terminal task.

After freezing, full-prior diagnostics at the training persistence values also
fail recovery: R=.211596158 at a=0 and .214171003 at a=.75. Even-onset recovery
there is .343665678 and .368571584. Changing the duration is therefore not
necessary for this timing-transfer failure.

The comparison below counts settings with strictly lower cost among the five
new durations. Counts describe a finite test grid, not probabilities.

| Comparator | New S lower | New B lower | New R lower | New B+R lower |
| --- | --- | --- | --- | --- |
| Previous joint reserve mixture | 5 | 3 | 0 | 0 |
| Previous fixed reserve mixture | 5 | 3 | 0 | 0 |
| Hybrid | 5 | 3 | 0 | 0 |
| Always purchasing | 5 | 4 | 0 | 0 |
| Conservative rule | 3 | 5 | 5 | 5 |
| Best training fixed schedule | 2 | 5 | 5 | 5 |
| Frozen-reliability ablation | 5 | 4 | 0 | 0 |
| Matched Bayesian planner | 0 | 0 | 0 | 0 |

The matched planner ties exactly in every case. The fixed schedule and
conservative rule satisfy K at all five settings but fail both recovery
comparisons throughout. Beating them establishes neither joint success nor
the necessity of richer inference. In particular, the fixed schedule already
uses the same reliability posterior: that comparison concerns adaptive
purchasing versus a fixed schedule within this model.

The older joint reserve mixture satisfies K at .125 and .95; the older fixed
mixture and hybrid do so only at .95. Both older reserve mixtures fail the
hybrid recovery comparison at .875 and .95. The earlier independent-noise
guarantees remain valid within their declared assumptions. Always purchasing
costs .1 and exceeds K, while remaining the stated recovery reference.

## The ablation: useful stable protection, unsuccessful recovery

| Persistence | Full S | Ablated S | Full R | Ablated R | Full minus ablated B+R |
| --- | --- | --- | --- | --- | --- |
| .125 | .093201201 | .093780118 | .210717603 | .152665536 | +.061279846 |
| .375 | .085481743 | .100446095 | .210470683 | .150609116 | +.054220852 |
| .625 | .073829048 | .096550298 | .212356082 | .151090555 | +.050518156 |
| .875 | .058580515 | .075759254 | .216720545 | .158430001 | +.049483162 |
| .95 | .053301056 | .065073234 | .218718323 | .163521023 | +.048727904 |

Updating reliability reduces stable cost at every held-out setting and reduces
B at four of five. The ablation exceeds K at .375 and .625, so those two
comparisons do not compare two budget-feasible controllers. The full agent's
R and B+R are nevertheless worse at all five, including the three settings
where both satisfy K. There is no positive result on the predeclared joint
mechanism criterion. Both improvements and harms are retained.

## Beliefs, purchases and delayed adoption are different outcomes

At a=.625, a representative interior held-out setting:

| Quantity | Full reliability | Frozen reliability | Previous joint mixture |
| --- | --- | --- | --- |
| Stable purchases per episode | 5.147697 | 5.682024 | 8.342998 |
| Stable unaided errors per episode | .223521 | .397301 | .208083 |
| Stable wrong-confidence task frequency | .005636 | .046384 | .032637 |
| Stable orientation Brier loss | .044334 | .062114 | .047084 |
| Full-prior orientation Brier loss | .091581 | .100985 | .087205 |
| Mean purchases before reversal | 2.558619 | 2.510749 | 3.263312 |
| Mean purchases after reversal | 1.954797 | 1.768394 | 2.670357 |
| Capped delay to first post-reversal purchase | .502591 | .553332 | .209621 |
| Probability of no post-reversal purchase | .103201 | .061976 | .023876 |
| Capped delay to 90% orientation adoption | 3.313849 | 2.302409 | 2.087270 |
| Probability of no 90% orientation adoption | .454579 | .291984 | .201678 |

Stable purchases are counted, not automatically called unnecessary: the agent
does not know that its current world will remain stable. Their fees and errors
are separately retained, with S=(errors+.1*purchases)/10. At this setting the
full agent saves both errors and fees relative to the ablation. Relative to
the older joint mixture it saves fees while making slightly more stable errors.

Wrong confidence means at least 95% mass on the incorrect orientation before
acting, scored over all tasks. It is lower than the ablation and the older
joint mixture at every held-out setting. However, full-prior Brier loss remains
higher than the older joint mixture throughout. Lower high-confidence error
frequency is not a general calibration or functional-success guarantee.

Acquisition and interpretation both matter. At a=.375 and reversal onset 10,
the full agent purchases only .090680 targets on that remaining task; it
gets no post-reversal feedback with probability .909320. Its recovery bill
is .827329, compared with .231037 for the ablation and .103797 for the hybrid.
At a=.95 the corresponding full-agent purchase probability falls to .008737
and recovery cost rises to .982893. There is a directly observed acquisition
failure at those timings, not merely an erroneous interpretation of evidence
that was actually purchased.

The full agent also takes longer than the ablation to reach 90% orientation
confidence at every held-out setting, but this is not a measure of first
useful action. At a=.625 its mean first-inversion delay is shorter than the
ablation's, despite slower confident adoption and worse recovery. Persistent
sensor errors can compensate orientation changes, as FEP 1 already showed.
Literal inversion, orientation belief, acquisition and useful cost therefore
remain separate metrics. The conservative rule has no invented posterior score.

The exact records retain every onset, all purchased-feedback costs, repeated
wrong-message updates, false adoption and both positive and negative contrasts.
This ablation changes the policy's chosen observations as intended; these
data do not isolate an interpretation-only causal effect while holding the
observed history identical.

## Verification and disposition

Qualification passed 82 assertions, including twelve exhaustive short-horizon
oracle comparisons, posterior projection preserving onset marginals, stationary
propagation, the independent-noise reduction, short fixed schedules and a
three-component mixture fixture. Qualification took .275 seconds. The forecast
was 261.947 seconds, below the ten-minute detachment threshold. The main
calculation took 47.732 seconds on one CPU at nice 10, with library threads
one and no bytecode. All generated data use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-learning-v1/attempt-01/`.

Independent verification passed **1,250,798 assertions** in **201.088 seconds**.
It checked 354,288 Bellman states across all twelve planners, all 2,782
candidate graph decisions, all 1,024 fixed schedules and 924 physical
graph/world settings. It reconstructs normalized Bayesian expectations and
posterior updates without importing the planner, uses a separate Cramer-rule
mixture calculation and independently propagates physical/diagnostic metrics.
The Bayesian comparison is therefore backed by an independent optimality
audit, not just by assigning two names to the same output.

Candidate graphs and training evidence were frozen at
19:19:34.521239 UTC; held-out evaluation began at 19:19:34.599346 UTC.
All sixteen frozen input identities, four source snapshots, forty training
artifacts and forty-four manifested outputs verify. No failed attempt or
post-result policy tuning occurred. The sealed attempt occupies
**35,493,858 bytes**. Manifest SHA-256:
`b961bacb5ab36ab89d159c5ef1e7f06a94efdecd3879efb6b5e2dd73de2596ae`.
Reporting and completion provenance are stored separately under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-learning-v1/reporting-2026-10-30/`.
The calculation and required verification are finished; nothing remains running.

The FEP contribution is now a specific model-assumption failure plus a bounded
mechanism test. FEP 1 shows why repeated correlated agreement can create false
confidence. FEP 2 shows that explicit reliability learning can protect stable
cost and suppress that confidence, while still failing the operational recovery
goal. Bayesian/VFE belief inference remains the FEP-related component; actions
optimize declared constrained task costs. Matched Bayesian agreement is a
legitimate result, not a missing unique-FEP advantage.

Do not adopt this candidate into the larger model. A proposed next lead is to
retain loss on every deployment onset while learning reliability, and reserve
new burst laws or reversal-prior distributions for transfer testing. That
would be a separate prospective study, not a repair of these frozen outcomes.
No third study, retuning, manuscript integration or sister-project write is
part of this result.
