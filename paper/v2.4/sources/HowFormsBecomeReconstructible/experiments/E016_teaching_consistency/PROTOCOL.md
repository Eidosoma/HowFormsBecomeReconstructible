# E016 — teaching consistency and routing capacity

Frozen before simulation, 2026-09-18. This separate prospective diagnostic tests
the E015 saved-data lead (D053). E015 remains a failed feasibility pilot. No
E015 data enter the estimates here; no renewal is authorized by these results.

## Fixed apparatus and intervention

Keep E015's 16×16 nearest-neighbor torus, reciprocal signed edges, cubic cell
equation, noise, ports, teaching labels, local correlation writer, 4096-byte
record, and test duration unchanged. Fix reader gain at 2, chosen from E015 for
this diagnostic, not as an E015-qualified setting. Exactly three record regimes:

1. **Ordinary:** two independent 512-step teaching episodes, cues +1 and -1.
   Both output ports are clamped to the supplied rule during teaching only.
2. **Consistent:** share the ordinary +1 episode. For the -1 episode, negate
   that +1 episode's initial fluctuations and every noise draw. Reverse the
   teaching clamps as usual. In real arithmetic the odd cell equation gives
   opposing trajectories and matching edge correlations; floating-point
   symmetry is checked with absolute tolerance 1e-10. This preserves each episode's
   marginal stochastic law while coordinating their joint history. The writer
   still sees only neighboring activities and averages the final 128 steps
   from each episode. This coordination is externally supplied; it changes
   record structure and diversity as well as cancellation, so a benefit would
   not uniquely identify scalar cancellation as the mediator.
3. **Engineered:** supply a sign field s=+1 everywhere, except set output A to
   the rule and output B to minus the rule; input remains +1. Install weights
   w_ij=s_i*s_j on every edge, with absolute strength one. This is a deliberately
   constructed capacity control, not a learned or optimal record. Under the
   change of variables u_i=s_i*v_i its deterministic coupling is the positive
   scaffold. The test reader receives only the resulting bytes. The field is
   saved for audit, never used by the reader. The stronger edge magnitudes are
   part of this capacity intervention, not an isolated test of consistency.

All other parameters are E015 defaults: dt .2, noise .02, birth SD .05,
teacher gain 2, tanh writer beta 3, 512 reading steps, final 32-step scoring,
strict output margin .25. Two matched founder pairs carry opposite supplied
rules (four founders per block); four fresh recipients, both cues, and three
damage conditions per founder. Preserve all cases and failures.

Use the same seven controls within each regime: own, paired opposite-rule,
shuffled edge values, erased, untrained positive scaffold, all communication
off, and input-incident edges cut. Permutations, fresh births, noise and damage
are paired across regimes and cues. No output clamp or rule enters reading.
As in E015, damage is intact, 24 randomly removed non-port cells, or a uniformly
chosen admissible 3×3 square. No connectivity or performance rejection.

## Fresh cohort and inference

Exactly **32 blocks 14000–14031** (128 founders, 64512 individual scored trials).
Excluded technical benchmark 900016; short fixtures use that identifier with
reduced duration. No new candidates or cohort extension after outcomes.

The **single primary comparison** is consistent-minus-ordinary probability that
the same founder/recipient answers **both opposing cues strictly correctly**, in
the intact condition. Average the 16 founder/recipient pairs within each block,
then compare paired block means. A lower two-sided 95% bootstrap bound above
zero supports improved conditional routing under this teaching intervention.
Report the effect size and interval, even if the test fails. This is not a new
criterion for E015 or a claim of inherited competence.

All other comparisons are secondary, pointwise descriptions: the same contrast
under both damage conditions; individual-cue accuracy contrasts; each regime's
accuracy, both-cue success and margins for every control/damage condition;
rule-specific own-record accuracy; and cancellation of absolute edge strength
when the two teaching episodes are averaged. No correlation screening or
additional primary endpoint is performed.

For continuity, separately display the original E015 feasibility gates for each
regime: each rule/damage own accuracy lower bound >.75 (six gates), and each
damage own-minus-each-control accuracy lower bound >.10 (18 gates). These do
not select another setting or start renewal. Passing with engineered records
would establish supplied capacity only; failing that control would not prove
every possible routing record fails. Passing with learned records would motivate
a separate fresh renewal protocol. Lower bounds and gates are pointwise.

Use 10000 whole-block percentile bootstrap draws, PCG64 seeded by SHA256 of
compact JSON ["E016","bootstrap","comparison"]. Simulation streams are
["E016",block,"teach",episode_index], ["E016",block,founder,"shuffle"], and
["E016",block,"reader"]. Retain the unchanged E015 damage generator with
stream ["E015",block,"E016","damage"]. Ordinary negative-cue episode uses
index 1; coordinated negative-cue episode negates index 0. No E015 simulation
block used these identifiers. Every scored record/cue/lesion is saved.

## Validation, execution and stopping

Reuse the unchanged E015 production cell equation and record codec; snapshot
their hashes. Test the coordinated-episode symmetry, the engineered record's
change-of-variable identity, reader exclusion of labels and exact input cuts,
and a short end-to-end independent audit. Independently replay all teaching
and reading dynamics and reconstruct bytes, masks, individual scores, block
statistics, intervals and gates. Audit does not import the production model or
runner; it may reuse the existing independent E015 equation and codec helpers.

At most 12 logical CPUs total, one numerical thread per worker. Benchmark one
full disposable block and audit it. Forecast simulation plus audit using
2*(worker_seconds+audit_seconds)*ceil(32/12)+90. If forecast exceeds 600 seconds,
launch detached with durable status, log and PID, then leave polling to the user.
Otherwise run in the foreground and report completion. Technical failures are
retained and corrected before fresh scientific execution; no outcome-based
retuning. Stop after this comparison, including if every scientific gate fails.

All writes remain inside experiments. Manuscript and sister experiments stay
read-only. This test concerns supplied teaching machinery and elementary local
routing, not autonomous goals, active repair, independently acting patterns,
or preservation of competence through record replacement.
