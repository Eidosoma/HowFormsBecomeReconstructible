# E014 — sixteen body-written replacements

Frozen before scientific outcomes on 2026-09-18. This extends E007's duration,
not its dynamics, writer, reader, or observer. No manuscript edits are included.

- **Cohort:** 64 fresh blocks, 12000–12063, each with four founders and two
  recipient lineages per founder. Keep every founder, failed formation included.
  Disposable benchmark block 900014 is excluded from scientific estimates.
  No cohort extension, parameter tuning, or pooling with earlier experiments.
- **Apparatus:** unchanged E001 heterogeneous formation (1000 steps), generic
  capture (1000), 16×16 toroidal tissue, and E006 initial packets/generation
  function (300 reading + 1000 writing steps). Recipient stream is founder block
  + 1000000. The shared formation bias is removed before capture. Founder
  prototypes are offline observers, never reader/writer inputs.
- **Budgets:** factors 1 and 4: 2048 and 128 bytes, respectively, at acquisition
  and every subsequent boundary. Compression changes amplitude and spatial
  resolution together. Public coordinates, dynamics and codecs are outside the
  byte budget. Both sizes use paired founder/recipient randomness.
- **Arms:** unchanged rewrite, foreign, shuffled, erased, held, read_off,
  write_off, copy, background and challenged. The foreign founder is the next
  cyclic founder **at acquisition only**; its descendants then renew normally.
  Copy transmits exact initial bytes. Each other writer starts with a zero
  field; write_off remains zero. read_off disables incoming fields during each
  lifecycle read. Checkpoint readers apply the same enabled reader to all arms,
  testing the consequences of earlier reading/writing disruption. Challenges
  flip 64 outcome-independent sites halfway through each read.
- **Horizon:** sixteen complete read→erase→write replacements. Save all 16
  generation reads and every incoming/outgoing byte array. After replacements
  **1, 3, 8, 16**, branch a fresh checkpoint reader off the outgoing record;
  checkpoint bodies never contribute to the continuing lineage. Each checkpoint
  uses the original `terminal` random stream, independent of all lineage streams,
  paired across horizons/arms/budgets. Thus births/noise are deliberately shared
  between checkpoint probes; the protected-copy probe is exactly constant.
  This also preserves E007's three-replacement terminal probe byte-for-byte
  for identical founders/configuration. G1 is before the first replacement and
  must not be labelled "after one rewrite."

**Primary endpoint:** at 128 bytes, after 16 rewrites, qualified own-founder
agreement of rewrite minus foreign-record descendants. Qualified agreement is
the fraction of all 256 cells with |v| > 0.2 and the founder's sign. This is the
original E007 between-arm specificity contrast, not a newly selected observer.
Average founders and recipient replicates within each independent block;
10,000 whole-block bootstrap samples, SHA256/PCG64 seed `["E014","bootstrap"]`.
The sole primary success criterion is a positive lower two-sided 95% percentile
interval endpoint. Report it regardless of other gate outcomes.

**Full long-renewal criterion:** the following conjunction must pass at **both**
budgets: original formation gate (at least 75% qualify and mean within-block
pairwise sign disagreement > 0.10); G1 copy−erased readability; positive
rewrite−foreign at G1, G2 and G3 and each of the four post-rewrite checkpoints;
after-16 rewrite−read_off and rewrite−write_off positive. All contrast gates use
the same 95% rule. This is an all-required conjunction; individual secondary
intervals are pointwise, not simultaneous discoveries. Failure of the conjunction
does not by itself establish collapse or zero historical information.

**Prespecified secondary reporting:** every original eight arm contrasts at all
20 saved read stages; absolute own agreement; own minus mean agreement to the
other three founder prototypes within each arm; decoded incoming/checkpoint field
SD; protected-copy deficit; paired compact-minus-full-field own agreement at
each checkpoint; after-16 minus after-3 changes in absolute fidelity and in the
primary between-arm specificity contrast. Retain individual all-target scores,
block means and 95%/97.5% intervals. No fitted decay law or selected stopping time.

**Checks and execution:** reduced-step fixtures establish unchanged first-three
generation trajectories, the matching after-three terminal read, sixteen actual
boundaries, no checkpoint feedback, copy invariance and exact byte budgets.
An independent auditor reconstructs scores, intervals, formation and all gates;
checks input/output hashes, boundary continuity, erasure and encoded shuffles;
and independently replays every checkpoint read from outgoing bytes and public
random streams. Maximum 12 logical CPUs total, one numerical thread per worker.
Benchmark a complete disposable block and audit before scientific launch.
Forecast = 2 × (benchmark worker seconds + benchmark audit wall seconds) ×
ceil(64/12) + 120 seconds for orchestration/reporting. If over 600 seconds,
launch the entire simulation→audit→figure workflow detached with a log, PID,
frozen inputs and durable status. The user polls; no automatic assistant polling.
Runs are append-only; technical failures and fixes are recorded explicitly.

This tests sustained historical reconstruction within supplied machinery. It is
not a functional competence assay, unrelated-substrate transfer, or a test of
independently active Platonic patterns.
