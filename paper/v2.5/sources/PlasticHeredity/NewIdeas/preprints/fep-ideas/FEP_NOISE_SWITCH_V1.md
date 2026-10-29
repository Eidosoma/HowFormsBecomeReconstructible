# One hidden change in sensor reliability

Specified 29 October 2026 before qualification or calculation. The user's
next “lets go” approves the bounded test proposed in the
[continuous-noise report](FEP_NOISE_INTERVAL_V1_REPORT.md).

## Scope and primary question

Keep the five frozen graphs and both episode-start mixtures from the
interval study. Keep T=10, reversal probability rho=1/2, a uniform hidden
reversal onset conditional on reversal, accurate purchases at .1, unit
unaided-error cost and hidden unbought targets/losses. The actual sensor
noise now changes once: **4% to 6% or 6% to 4%**, starting at task sigma in
{2,...,10}. There are 18 switch schedules. Noise bits remain independent
conditional on the schedule. Reversal onset and the fixed schedule are
crossed in offline evaluation; the controller receives neither true onset
nor noise schedule.

The joint mixture continues its existing three-class constant-noise inference;
the fixed-pool components and hybrid keep their .05 likelihood. Neither the
posterior graph, action rule nor mixture weight changes. No dynamic model,
switch detector, new policy, optimization or deterministic search is included.

Evaluate each schedule separately in the orientation-stable world and all
ten reversal worlds. “Stable” here means no orientation reversal: sensor
reliability still changes. S is that world's cost per task; B includes the
entire episode under the unchanged reversal prior; R averages post-reversal
cost per remaining task over onsets. Every feedback fee is charged, including
fees before either event. Keep K=19568652557/204800000000.

For **every one** of the 18 schedules, each mixture must satisfy S<=K,
R<.1 and R<R_hybrid under the same schedule. Overall success requires all
three inequalities in all schedules. Do not average schedule failures away.
Also report matched-hybrid stable comparison, B against hybrid/always buying,
and J=B+R against the other mixture as secondary comparisons. Keep component
outcomes separate. No new optimality claim follows from a frozen-policy test.

Include constant 4%, 5% and 6% schedules as integrity controls, reproducing
all shared costs from the sealed interval polynomials exactly. These are
three controls, not additional switch conditions. This study does not prove
arbitrary changes within [4%,6%], intermediate switch amplitudes, repeated
changes, rate-correlated noise, a new reversal prior or larger-model transfer.

## Evidence acquisition, interpretation and economics

Retain errors, purchases, full/post-reversal costs, capped first-purchase
delay after reversal and the probability of no later purchase, as before.
Also record errors, purchases, capped first-purchase delay and missing
purchase probability after the reliability switch. The switch purchase
diagnostics are null for constant controls. Do not confuse the two event
times: a purchase after one event can precede the other.

Score the retained probability of reversal before each action against the
actual orientation using binary Brier loss. For joint-model graphs, sum the
posterior mass across noise classes before scoring. Report orientation-stable,
full-prior and post-switch average scores. Mixture scores average component
scores while retaining component identity. Always purchasing has analytic
physical costs and acquisition timing; do not invent a belief score for it.

These diagnostics can distinguish missing purchases, inaccurate orientation
beliefs and unfavorable purchase/error accounting. They do not by themselves
identify a causal failure of evidence acquisition or interpretation, or prove
calibration. Physical difficulty and selected observation histories change
too. A constant-noise joint posterior is not a learned switching model.

Save signed per-onset full/recovery differences against the hybrid and
always purchasing, including onset-3 harms previously found under fixed
noise. Report every adverse result and equality. Select worst schedules by
the declared metrics, preserving ties; do not change criteria afterward.

## Qualification and independent verification

Use rational backward graph recursion with the appropriate rate at each
task. Freeze the protocol, new evaluator and independent verifier, any
imported helper source, and the preceding interval protocol/report and
graph/result/manifest/readback records before qualification.

Enumerate all 3, 15 and 255 contingent trees through T=3 with joint-noise
beliefs. Compare every world under all short one-switch schedules and the
three constant controls against full binary-noise replay. Include nominal
.05-belief fixtures, rho=1/3, an erased-label purchase sequence and a fixed
mixture. Check that switching at task 1 or after the last task reduces to
the appropriate constant profile. Check identical reversal/switch times and
separate their delay metrics when the times differ.

The independent verifier imports no evaluator. For every main graph/world,
replay all 2^10 noise bitstrings with integer mass
`product_t(n_t if flipped else 100-n_t) / 100^10`.
Rebuild physical metrics, graph visits and Brier scores from those visits.
Verify exact graph/weight identities, time-specific probability mass, mixture
arithmetic, both event-time diagnostics, every gate, signed comparisons and
constant-rate reproduction. Verify analytic always-purchase accounting.
This is separate reconstruction, not external replication or sampled evidence.

## Execution and closure

All generated records use
`/mnt/bioIce1/fep-ideas/formal-checks/fep-noise-switch-v1/` on the verified
mounted drive. Code and small notes stay here. Sisters and manuscripts are
read-only. Preserve every sealed predecessor and failed attempt.

Benchmark both directions with a task-4 switch on the five graphs truncated
after task 7, using rho=1/3 for physical weighting only. Earlier decisions and
beliefs stay frozen. This is timing only. Forecast main plus verification as
`120 + 6*(21/2)*2^(10-7)*benchmark_seconds`, with a two-hour feasibility
ceiling. Use one CPU at nice 10, library threads one and no bytecode. Forecasts
above ten minutes run detached with durable logs, one startup check and no
automatic polling. Do not resize or extend a failed calculation.

Finish the report and six live notes, or a durable detached checkpoint.
Record sources, hashes, exact outcomes, resources and reporting provenance
separately from sealed calculation outputs. No automatic successor, adaptive
likelihood model, wider switch family, deterministic search, manuscript or
larger-model integration is included.

The FEP question is whether evidence-guided action remains useful when
observation reliability violates the model's constant-parameter assumption.
Bayesian/VFE updating remains part of that interpretation; the action target
is constrained task cost, not a new canonical EFE or uniquely FEP advantage.
Keep the larger model's previous baseline and failed joint criterion intact.
