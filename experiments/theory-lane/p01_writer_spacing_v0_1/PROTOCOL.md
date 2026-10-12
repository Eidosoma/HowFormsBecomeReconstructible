# Six tolerance writes: spacing versus a late cluster

Status: development timing intervention, not a confirmatory RDT-P01 test.
Authorized by the user's "lets go" after the pulse recovery analysis and its
explicit next-experiment draft. Both schedules, cohort, endpoints and analyses
are fixed before new schedule trajectories are run. No schedule or dose sweep.

The single generation-3 pulse gave 116/128 terminal successes, compared with
120/128 under the original writer O and 3/128 under repeated tolerance T. The
completed recovery analysis found preservation of function without rapid
contraction toward the paired O reader network. Prior passive P01 predictors
failed. These observations informed this design. All 32 E051 blocks and the
two eight-block pilots are exposed development evidence; the eight blocks used
here are not an independent replication cohort.

Use the same blocks 34000–34007, four founders and four recipients per block,
common generation-3 pre-write bodies, matched future damage and random draws.
The two new histories use T at the following generations and O everywhere else:

| Schedule | Tolerance-writing generations |
|---|---|
| Spaced | 3, 5, 7, 9, 11, 13 |
| Initial pulse plus late cluster | 3, 9, 10, 11, 12, 13 |

Both have six events, first at 3 and last at 13, followed by 19 O writes at
14–32. A wholly consecutive six-event burst would change the first event;
retaining the common initial pulse makes the endpoints of exposure identical.
Intermediate bodies are consequences of the schedules, not post-hoc matching
variables. Six is an outcome-informed intermediate dose, not a power estimate.

Simulate only O and the two new schedules. Reuse the completed T and single-pulse
P histories/endpoints under hashes, preserving lineage identities. The analyzed
order is O, T, P, spaced, cluster, then erased for terminal assays. Reused controls
do not increase the inference-unit count. Eight blocks are the units of inference.

Retain all native equations, 16x16 geometry, 24 absent non-port cells, fixed 1e-4
tolerance, 2048 reader steps with 1024 settling steps, noise, founder rules,
ports, scoring, damage and random-stream contracts. Hold-phase omission follows
the already replay-validated pilot engine: capture precedes holding, holding
bodies are discarded, and the holding stream cannot affect later renewal.
Teaching and assay cue randomness remain matched. No reader, writer threshold,
task, dose or timing is adjusted after observing these schedule outcomes.

The primary endpoint is h32 scattered-terminal strict both-cue success, native
margin greater than 0.25. The sole primary contrast is spaced minus cluster.
Report all paired rescued/harmed counts, per-block differences and equal-block
mean, whether positive, zero or negative. The proposed direction is positive;
a negative result contradicts that direction in this domain. A small or zero
effect is unsupported or unresolved without an equivalence margin. No
confirmatory p-value, tuned cutoff, or universal spacing claim is specified.

Secondary endpoints are intact/square terminal assays, native body success and
margins, and fixed 64-step outgoing signed cue transfer and unsigned access.
Report each new arm versus O, T and P as secondary comparisons. The first body
after the final pulse is generation 14: it reads the generation-13 T packet
before performing its own O write. Explicitly report this body's result and
the final terminal assay separately; an additional horizon-13 terminal assay
is not part of the design. Save every generation and label the actual writer.
Hypothetical O-to-T diagnostic fractions on bodies using O are not T events.
Linear transfer remains a surrogate, never a native success probability.

Verification requirements:

- O reproduces every saved native boundary, score and terminal assay; the erased
  terminal assay also matches. Reused O scores and diagnostics agree.
- Both new generation-3 packets match saved T and P. Each new branch matches P's
  bodies through its first extra T write (generation 5 or 9), and P's outgoing
  packets strictly before that write. This checks read-before-write timing.
- Recompute every branch capture independently from its saved body with the
  previously checked diagnostic writer equations. Verify exact packet bytes and
  actual event codes. Both new arms contain exactly six T writes and use O after
  generation 13.
- Independently reconstruct terminal/body tables, paired counts, schedule labels
  and selected normalized transfer calculations without importing production
  analysis. Store failures and stop; do not reinterpret partial outcomes.

Benchmark only already known O/T/O histories, including a full native read and
terminal assay at the planned three-policy batch size. Forecast full work using
1.5 times timed compute plus 180 seconds for source verification, compression,
all-generation diagnostics, analysis and independent table verification. Preserve
the one-hour conservative CPU ceiling; revise the resource plan before new
outcomes if exceeded. Numerical computation uses one process and one thread.
If longer than 600 seconds, launch detached under a quiet blocking supervisor,
with frozen inputs, logs, automatic COMPLETE/FAILED receipts and no automatic
polling or successor run. User-requested status checks remain available.

A favorable result supports this finite schedule contrast, not contraction to
the original network, unique causal mediation or P01 confirmation. Predictor
development and an unseen-condition evaluation remain separate work.
