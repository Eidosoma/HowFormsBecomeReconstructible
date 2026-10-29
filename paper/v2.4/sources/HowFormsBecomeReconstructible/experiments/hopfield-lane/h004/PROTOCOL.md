# H004: fresh confirmation of functional renewal with stronger cue coupling

Frozen before confirmation inputs on 11 October 2026. H003 is development;
H004 tests its selected intervention on new independent base networks. No
development block is pooled into the confirmation estimate.

## Model and boundary

Execute the unchanged H003 lineage implementation. Each independent block has
a symmetric 64-neuron base network, four taught founders (two opposite rules)
and four descendants per founder. Formation uses 24 asynchronous sweeps with
input/output teaching. Thereafter only input sites 0–3 are clamped. Each body
has two opposite cue trials, each with eight sequential sweeps. Zero local
fields retain the previous bit. A fresh body replaces all activity at every
boundary; 50% independent undirected edge deletion precedes each lineage read.

The outgoing record is mean body coactivity divided by 64, with zero diagonal.
It receives no teacher, desired output or incoming record. The explicitly
designated copying controls bypass this writer. All 16 replacements, checkpoints
0/1/4/8/16, response thresholds and random-tape conventions remain unchanged.
Success requires the means of both eight-site output patches, under both cues,
to exceed .5 in their originally taught directions. A matching output pattern
without the correct cue dependence fails.

Retain all four reader arrangements: cue gain 1, cue gain 2, primary cue gain 4,
and gain 4 at unrelated unclamped sites 24–27. Gain multiplies the symmetric
base-plus-record edges joining the four selected sites to all other sites;
within-group edges are unchanged. It changes 240 unique effective edges and is
supplied reader machinery. There is no new output teaching after formation.

Retain all nine arms: renewal, opposite-rule foreign record, initial coordinate
scramble, erased acquisition, read blocked, write blocked, protected copying,
cumulative-loss copying, and scrambled writer addresses. Pair births, update
orders and damage across arms and arrangements. Checkpoint readers never write.
Retain late-only gain-4 and 32-sweep baseline reads of the actual G16 baseline
lineage records, with the same terminal birth and the same update-tape prefix.
These controls do not change lineage history.

## Sample size and stopping

Use 72 new independent base networks, seeds 14000–14071. Every founder,
descendant and block is retained. The independent unit is the base network,
not one of its 16 related descendants. There is no interim decision, optional
stopping, outcome-based exclusion, replacement seed or sample-size extension.

The executable development-only calculation is in `plan.py` and
`SAMPLE_SIZE.json`. Plan for marginal 95% interval half-widths of five percentage
points for the 17 primary differences, gain-4 success at G8 and G16, and the
early-versus-late difference. For each, calculate its H003 sample standard
deviation across the 24 independent blocks, inflate that deviation by 25%,
and require `n >= (1.96 * 1.25 * sd / .05)^2`. Use the largest requirement,
round up to eight blocks, with a minimum of 48. The largest requirement is 71
blocks (gain-4 minus decoy at G16); rounding gives 72. This is a transparent
precision planning approximation, not guaranteed coverage, simultaneous
five-point precision, or a power calculation for the adjusted tests. Report
the attained intervals even if they are wider than planned.

The engineering replay uses already exposed benchmark seed 12900, excluded
from confirmation. Every array must match the retained H003 benchmark exactly.
The model source files must match H003's frozen development sources byte for
byte. Technical failures remain recorded; any necessary scientific change
requires another protocol/run rather than altering this frozen confirmation.

## Decisions and inference

Preserve H003's complete primary decision without retuning:

- At both G8 and G16: gain-4 mean success >=.30; own minus foreign >=.15;
  own minus cumulative-loss copying >=.10; gain-4 own minus baseline own >=.10.
- At G16: gain-4 own minus decoy own >=.05.
- All 17 directional lower bounds must be positive: seven own-minus-control
  contrasts plus gain-4-minus-baseline at each of G8 and G16, and
  gain-4-minus-decoy at G16. The seven controls exclude protected copying.

Jointly resample whole base networks for 20,000 bootstrap draws, analysis seed
940004 and namespace `H004 whole-block bootstrap`. Use one-sided percentile
lower bounds at `.05/17`; other displayed intervals are marginal two-sided
95% percentile intervals. Minimum effects above concern the point estimates;
the adjusted lower-bound requirement is greater than zero, not greater than
those minimum effects. A fixed-seed percentile bootstrap is approximate
inference, including when a control has no observed successes.

Only if the complete primary qualifies, evaluate a secondary timing claim:
sustained gain 4 minus late-only gain 4 at G16 must average >=.10 and have a
positive one-sided .05 whole-block bootstrap lower bound. Report its numerical
contrast regardless, but it cannot qualify a separate confirmation claim if
the primary fails. This fixed order keeps the secondary claim behind the
primary family. Gain 2, another horizon or a descriptive diagnostic cannot
replace a failed primary.

Report all failed gates, protected-copy deficit, initial-to-terminal attrition,
response categories, cue links, norms, longer-read results and all block-level
outcomes. The gain's geometry and address convention, dense record, shared base
and taught rule remain supplied apparatus. Copying does not need the simulated
diagnostic bodies or coactivity writer and is cheaper. Confirmation concerns
this fixed model, task, damage law and horizon; it does not establish useful
reciprocal repair, discovered competence, superiority to copying or general
continual learning. Matched-present-expression continuation is a later study.

## Execution and integrity

Prepare config and a portable source snapshot, checksum them, then execute only
that snapshot. Retain every mask, body, record, reader state and endpoint. Run
the existing scientific fixtures and all boundary/endpoint/replay audits; also
check exact development replay and confirmation cohort separation. Float64
discrete simulations require exact array equality in replay. The scalar
energy fixture allows rounding error of 1e-12. No numerical failure is silently
excluded. Final qualification additionally requires all integrity checks.

One worker, one numerical thread. Benchmark the full wrapper before launch.
Follow `../RUN_POLICY.md` from the lane root: a forecast above 600 seconds is
detached, with disconnected stdin, PID, log and durable status; await a
user-requested status check. Preserve existing runs. No private source, trained
state, results or manuscript text enters the confirmation. Manuscript insertion
and public release are outside this run.
