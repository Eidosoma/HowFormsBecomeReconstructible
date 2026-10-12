# H003: preserve cue-specific function during complete rewriting

Specified before H003 simulation on 11 October 2026. This is prospective
development, motivated by the separately retained post-hoc H002 diagnosis.
Its cohort is new; H002 outcomes are neither pooled nor reclassified.

## Lead and intervention

In H002's four-cue complete-writer panel, 49.74% of terminal readers gave the
same confident response to both opposite cues. Mean output-patch opposition
remained .993, while the signed cue/output connection fell from 1 to .084.
For this coactivity writer, identical responses to the opposite cues cancel
their contributions to the input/output connections. Protected records also
show reading ambiguity, despite retaining their original cue connections.
These observations motivate a causal test; they do not establish its outcome.

Use the H001 functional task and body-only writer with four clamped input sites,
50% fresh undirected-edge deletion per boundary and 16 full activity
replacements. Keep formation, base weights, two cue trials, eight sequential
reading sweeps, nine intervention arms and output thresholds unchanged.

Cross each arm with four fixed reader arrangements:

1. cue gain 1: the H002 four-site baseline;
2. cue gain 2: multiply edges between the four cue sites and other sites by 2;
3. cue gain 4: the same intervention with factor 4, the sole primary;
4. decoy gain 4: apply factor 4 to edges incident on four unclamped sites
   24–27, with the same number of changed undirected edges.

Apply gain symmetrically to the effective base-plus-record matrix for each
read; edges within the four selected sites are unchanged. Each read retains
fixed symmetric weights and zero diagonal. Gain changes coupling geometry
and cue influence; it is additional supplied apparatus, not acquired
competence. The outgoing writer receives only activity and never gains access
to the rule, desired outputs, incoming weights or teacher. No output site is
clamped after formation. Record payload and sweep budgets remain equal.
Uniform positive scaling of all effective weights cannot change this binary
threshold dynamics; an executable fixture checks that invariance.

The decoy is an address control, not a guaranteed inactive intervention. It
may affect dynamics. The gain-2 panel is a prespecified dose diagnostic and
cannot replace a failed gain-4 primary.

## Cohort, controls and stopping

24 independent base networks, seeds 13000–13023; four founders and four
descendant replicates per founder. Checkpoints: 0, 1, 4, 8, 16. Keep every
founder, descendant and block. No outcome-based exclusions or extensions.
The engineering benchmark uses seed 12900 and all 16 replacements to forecast
runtime accurately. Its verdict is engineering only; its data are excluded.

Arms: own-record renewal, opposite-rule foreign record, initial coordinate
scramble, erased acquisition, read blocked, write blocked, protected copying,
copying with cumulative damage, and scrambled writer addresses. Gain acts on
the matrix actually available to each reader, so read blocking leaves only
the correspondingly modified base matrix. All rewriting is complete; write
blocking produces zero. The permutation fixes the eight original potential
input sites. Copying arms require less computation than the diagnostic bodies
simulated for them. Preserve their information and resource accounting.

Share initial records, new random births, update orders and edge deletions
across reader arrangements and arms. Independent checkpoint readers never
write into the lineage. Success retains H002's endpoint: both output-patch
means under both cues must exceed .5 in their taught directions.

## Separate late-reading controls

At G16, take the actual baseline lineage records and read them with (a) cue
gain 4 for eight sweeps and (b) baseline gain for 32 sweeps. These two controls
leave lineage history unchanged and write nothing. Use the same terminal birth
and order tape as the primary readers, extending its order sequence for the
32-sweep control. This separates changing reading at the end from preventing
poor reads during serial rewriting. It also distinguishes insufficient
settling time from a change in attractor choice. Retain all nine record arms.

## Frozen development decisions

The sole primary is gain-4, own-record, complete rewriting. Candidate
qualification requires all of:

- At both G8 and G16, mean success >=.30, own-minus-foreign >=.15 and
  own-minus-cumulative-loss-copy >=.10.
- At both horizons, gain-4 own-minus-gain-1 own >=.10.
- At G16, gain-4 own-minus-decoy-gain-4 own >=.05.
- Positive Bonferroni-adjusted one-sided bootstrap lower bounds for all 17
  directional contrasts: seven own-minus-control contrasts plus gain-4 minus
  baseline at each of two horizons, and gain-4 minus decoy at G16.

The seven controls are foreign, initial scramble, erased, read blocked, write
blocked, cumulative-loss copy and scrambled writer addresses. Jointly resample
whole base networks for 20,000 draws, analysis seed 930003; use quantile
`.05/17` for this primary family. Other descriptive intervals are pointwise
two-sided 95% whole-block intervals. Report failed gates explicitly. Neither
gain 2, another horizon nor improved raw success can replace the primary.

A separate timing/mechanism contrast compares sustained gain 4 with late-only
gain 4 at G16. A mean advantage >=.10 with positive one-sided .05 bootstrap
lower bound supports benefit from earlier intervention. It is not required
for the primary candidate gate and cannot rescue it. The longer-read control,
response categories, cue connections, output opposition, record norms and
protected-copy deficit are descriptive diagnostics. Retain acquisition-to-G16
attrition and the original H002 failure.

## Execution and integrity

Single worker, single numerical thread. Retain all records, masks, bodies,
reader states, late readers, configs, source snapshots and checksums. Refuse
existing output paths. Audit every writer/copying boundary, source and raw
seals, cue clamps, stored endpoints, terminal replay, symmetric gain masks,
and exact protected-copy identity across arrangements and late rescue.
Run scalar dynamics, energy, endpoint and gain-invariance fixtures first.

Benchmark a full-horizon engineering block including I/O, audit and analysis.
Apply ../RUN_POLICY.md from the lane root: forecasts above 600 seconds run
detached with stdin disconnected, PID, log, frozen configuration and durable
status; no automatic polling. Each result concerns this supplied dense model,
not general continual learning or discovered reconstruction machinery. No
private source, trained state or data enters H003 or the forms manuscript.
