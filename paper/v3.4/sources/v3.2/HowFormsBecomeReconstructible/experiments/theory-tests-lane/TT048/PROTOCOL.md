# TT048 — mixed unmarked corruption, graph repair and abstention

This implements the user's reviewer-directed extension of TT014. TT014 filled
exact zeros and preserved every nonzero weight. Its prospective result supports
that rule in its original damage setting; it does not establish repair of false
nonzero information. TT048 is a bounded one-read development study, before any
serial confirmation. Its eight exposed TT014 blocks are 14000000–14000003 and
14000032–14000035: positions 0 and 8 within each of the four ordered histories.
Enroll all 16 generation-14 records in each block, including all prior failures.
No block or record is selected using a new outcome. Qualification uses only
TT014's existing excluded fixture 14000999, with its saved known records.

The repair boundary receives only a 2-by-256 float64 packet and fixed options.
It receives no historical task, uncorrupted packet, damage locations, corruption
type, other body, assessment outcome or regime name. The supplied toroidal
lattice and four input pins are the same as TT014. Controls and scoring use
history in separate functions. Each returned packet is exactly 4,096 bytes.

Freeze eight input regimes for every enrolled record:

1. Original outgoing record, without additional corruption.
2. Additional missing edges: set floor(.10*m) nonzero edges to exact zero.
3. Misleading signs: flip floor(.10*m) nonzero edges.
4. Mixed unmarked damage: three disjoint sets of floor(.10*m) observed edges;
   replace the first with independent signs at .05 times the observed median
   magnitude, flip the second, and multiply the third by four. Alterations have
   no supplied marker; this creates no additional exact zeros. It is an amplitude
   and sign corruption model, not a claim about a fraction of information lost.
5. Actual opposite-history transplant: the paired opposite founder's original
   acquired teaching packet, repeated for that recipient. This is a real learned
   donor record, but internal perfect consistency is not assumed or selected.
6. Balanced aligned control: preserve the original packet's nonzero magnitudes,
   fill zeros with their median, and impose a balanced sign field with all input
   pins positive and both output patches expressing the original founder's rule.
7. Balanced wrong-task control: the identical unsigned control with the two
   output patches reversed. Every cycle is consistent and its pinned graph
   optimum is zero, just as in the aligned control. These two synthetic controls
   receive oracle labels only in the control generator and are not evidence that
   the repair recovered a hidden history. They expose false assurance from mere
   internal consistency. If the observed packet is empty, both remain empty.
8. Fully erased packet.

Use one new deterministic edge permutation per block/record, shared between
regimes 2–4. The two simple regimes use the same selected edge set; the mixed
sign-flip set is the second, disjoint slice. Signs for low-amplitude replacements
use the same corruption generator after the permutation. Save every mask and
actual edit, including unchanged coincidences. The namespace is
TT048_unmarked_one_read_v1, with compact-JSON SHA256 first 16 bytes little-endian;
corruption keys are [namespace,block,"corruption",record]. No outcomes determine
the damage construction. Existing natural zeros remain part of the input.

Compare six physical arms on every input: preservation P; the unchanged TT014
zero-filling rule Z; spanning-forest sign repair G; multi-start sign repair M;
and selective policies GA and MA. G uses TT014's deterministic maximum-weight
spanning forest with fixed input pins and no local search. M uses the unchanged
16-start, at-most-64-sweep optimizer, seed 2026101004. Both derive couplings from
the same directed-normalized absolute weights. Neither is claimed globally
optimal. Both sign-repair proposals retain all nonzero magnitudes and use the
same median for every zero edge, replacing signs by inferred node-sign products.
This matches their physical support/magnitude budgets while exposing differences
in inference and CPU work. Report additions, flips, unchanged edits, affected
planted/nonplanted edges, absolute weight and actual process time separately.

Abstention is a fixed, uncalibrated development rule. G is structurally eligible
only if its weighted disagreement is <= .05, every component with an observed
edge is connected to an input pin, and all cells within each output patch have
the same inferred sign. MA additionally requires the selected optimizer state
to have zero improving single-node moves and exactly the same inferred output
patch signs as G; its own weighted disagreement must be <= .05. GA/MA issue their
respective proposal when eligible; otherwise return the original input bytes.
An eligible proposal identical to the input is recorded as no-change, distinct
from an edit or an abstention. Empty inputs abstain. No outcome tunes these
thresholds; they are not calibrated confidence probabilities. Explicit historical
status is UNVERIFIED for every record: the algorithm cannot certify provenance
from these inputs, including when it finds zero structural disagreement.

The balanced correct/wrong pair has identical support, magnitudes, cycle parity,
and optimal structural cost. An arbitrary identical physical packet can also be
assigned either hidden historical target without changing any record-only action.
Qualify that information-boundary identity directly. With no trusted anchor the
repair cannot guarantee detecting the wrong acquired history. Success on local
corruption must never be advertised as solving this identifiability problem.

All six arms are read in four new, paired receiving futures per record, sharing
injury, reset and stochastic forcing across arms and input regimes. Four draws
give coarse conditional estimates. TT014's native paired cue noise remains;
new conditions do not imply independent teaching or cue noise. Use 24 randomly
missing non-port cells, 2,048 read updates, the first 1,024 settling updates,
dt .2, noise .02, birth SD .05 and the last 32 observations. Reading has no writing.
Assessment keys are the same TT014 key shapes under the new TT048 namespace:
[namespace,block,"injury",future,founder//2,recipient] and
[namespace,block,"read",future]. Qualification uses future 0 only.

The principal development panel is mixed unmarked damage. Report intended-task
success, opposite-task success, each minimum margin and all paired gains/harms
for every arm, regime, block, original history and original pass/fail group.
Success requires the strict minimum intended-task margin > .25 over both cues
and output ports. Keep all 15 pairwise arm contrasts. Both wrong-task controls
are separately reported and cannot be pooled away. No result is confirmatory.
Abstention coverage, edit/no-change coverage, unconditional performance (including
abstentions), eligible-case performance and eligible wrong-task frequency are
distinct quantities. Report differences between selected and all-case outcomes;
do not treat improved selected performance as a causal gain from abstention.

Average four futures within each actual record, then 16 records per source block,
then blocks equally (two per history). Dependent recipients, paired founders,
damages and future draws are not extra population blocks. Retain record-level
paired estimates, conditional Monte Carlo errors and all block effects. There
is no significance gate, adaptive threshold, outcome-based extension or serial
success claim. TT014 and subsequent native studies keep their earlier findings.

Bind original completion/closeout, selected generation-14 and teaching files,
and copied native code before any new production assay. Bridge original repair
outputs exactly to TT014. Independently check the forest with Kruskal traversal,
and optimizer with the unchanged Prim implementation; independently reconstruct
every proposal, gate, corruption and scalar resource count. Replay every reader
trajectory with the separately implemented flat reader, byte for byte, and
score the retained 32-observation windows with compensated scalar sums. Test
empty records, known balanced wrong records, exact gate boundaries, disconnected
components, graph/optimizer disagreement, protected magnitudes, hidden-input
exclusion, strict scoring, harmful repairs and altered-array rejection.

Use two normal-priority single-thread workers on CPUs 6/7 within the shared
12-CPU ceiling. Preflight, on the excluded fixture only, is limited to 600 seconds
and benchmarks three regimes with one future. Full excluded qualification runs
all eight regimes once and must match those serial preflight cases exactly.
Production forecast is 1.5 times four waves times four future scaling times the
measured qualification block time plus 120 seconds; ceiling six hours, deadline
twice forecast. Qualification deadline is twice its measured forecast, at least
600 seconds. A 1 GiB study cap, 64 MiB per production block and 4 GiB free reserve
are enforced. Keep raw states, windows, packets, decisions and hashes losslessly.

Run qualification and conditional production as one detached sequence. Check
resources once before each phase; stop on any mismatch or guard. Preserve failed
attempts, with no automatic retry or protocol change. After one startup check,
leave long work unpolled until the user requests status. The archive continues
independently; TT047 recovery is not launched by this study. No serial successor
is authorized by this protocol.
