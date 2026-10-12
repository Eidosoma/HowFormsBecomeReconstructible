# E012 — can target wiring improve repair selection?

Frozen before fitting or generating E012 outcomes. E009's post-hoc split-recipient
diagnostic found modest repeatable target-side ranking headroom. E010–E011 did
not establish a weak-site advantage over random. This test returns to ranking
equal-budget repairs, adding explicit target-graph information.

**Development:** reuse all 64 completed E009 blocks 7000–7063, all four founders
and all eight repairs. These previously examined cases are development data for
this new question, not fresh validation. Recompute A and B agreement from raw
endpoints against all four prototypes; specificity is own agreement minus the
mean of the other three. E010/E011 motivate the question but supply no fit rows.
E009's original results remain unchanged. No cross-validation search or feature
selection is performed.

**Fresh test:** blocks 10000–10063, four founders each, eight recipient futures
per body. Retain every founder and graph. Excluded benchmark 900412; fixtures
900413–900414. Reuse E009's menu and reader unchanged: erase 192/256 record
entries; each option restores 64 exact original values from an external backup.
The shuffled menu contains the strongest-value subset and seven distinct uniform
random subsets. Restore 512 value bytes; leave 128 entries erased. A uses the
native torus; B replaces exactly 25% of edges with degree-preserving long links.
The old semantic RNG tags are retained with disjoint block IDs. No new targets,
writer changes, amplitude normalization, body challenges or serial renewal.

**Fixed models:** predict B's within-menu specificity minus A's within-menu
specificity. Center every feature and outcome across the eight candidates within
each founder. Fit ridge regression without intercept to all 2048 development
rows, giving every block/founder equal weight. Divide each feature by its training
RMS (use 1 if below 1e-12); solve `(Z'Z + n*0.01 I) beta = Z'y`. Add the predicted
residual to centered A specificity. No clipping, tuning, refits or cohort extension.

The **native model** has these 17 source-only features, in order:

1. A own, mean-foreign, resolved and cardinal-neighbor sign agreement (4).
2. Applied record mean, mean absolute value and RMS (3).
3. Applied record dot own prototype sign and mean foreign prototype sign (2).
4. Mean record times its native neighbor mean (1).
5. Smooth A own and mean-foreign agreement (2).
6. Mean A terminal value times its native neighbor mean (1).
7. Native neighbor mean dotted with own and mean-foreign prototype signs (2).
8. Change in smooth own and mean-foreign agreement after a native coupling
   increment `v + 0.2 center(neighbor_A(v) - v)` (2).

The **graph model** adds six features:

1. Mean record times `(neighbor_B(record) - neighbor_A(record))`.
2. Mean A terminal value times `(neighbor_B(v) - neighbor_A(v))`.
3. That neighbor difference dotted with own and mean-foreign prototype signs (2).
4. Change in smooth own and mean-foreign agreement after
   `v + 0.2 center(neighbor_B(v) - neighbor_A(v))` (2).

Means cover sites and, for A terminal features, its eight recipients. Prototype
signs are +/-1. Smooth agreement with sign s is `sigmoid((s*v - 0.2)/0.2)`,
averaged over sites/recipients and separately over the three foreign references.
This is a fixed algebraic coupling feature, not a simulated B future. These
features are a limited mechanistic hypothesis, not a complete map of the dynamics.

**Policies:** graph model, native model, greatest observed A specificity, strongest
record entries, and exact expected uniform selection over all eight menu options.
Deterministic ties choose the lowest shuffled menu index. The native model controls
for task-specific fitting and access to packet locations, prototypes and raw A
states. Only the graph model sees the actual B graph. Models are hashed and
independently audited before fresh prediction; all choices, A states, menus and
graphs are hashed and audited before any scientific B read begins.

**Primary test:** B specificity recovery relative to unrepaired. Average recipients,
then four founders within each independent block. One six-gate conjunction:
graph exceeds each of native, source, strongest and uniform selection, and graph
has positive specificity and own-agreement recovery. Require every 95% interval's
lower endpoint above zero. Use 10000 whole-block bootstrap draws, tag
`E012:utility`. Full qualification needs all six gates; there is no substitution
of a favorable comparator, observer or subgroup. Report all intervals and gates.
Intervals describe individual contrasts, not simultaneous bands or equivalence.

**Secondary:** absolute agreement/specificity, noisy hindsight-best gaps, choice
agreement, centered prediction RMSE, native minus source utility, and each of the
three foreign-reference contrasts. Development fit errors are descriptive and
not evidence of generalization. No further target-side policy is trained here.

Raw endpoints, packets, graphs, source features, fit rows, coefficients, frozen
choices, per-founder CSVs, failures and provenance stay local. At most 12 CPUs,
one numerical thread per process. Benchmark before the fresh run; forecast over
600 seconds requires detachment and user-initiated polling. This tests an
externally supplied repair decision in related tissues with a shared coordinate
system, clean backup, prototypes and native-body probes; it does not establish
autonomous repair, an optimal selector or independent agency of forms.
