# H002: complete rewriting with reduced cue support

Frozen before H002 outcomes, 11 October 2026. This is a prospective development
experiment on new base networks. It tests a candidate forms contribution;
publication confirmation remains a later rung. H001 is the disclosed model
development source, and its data are neither pooled nor reused.

## Model and question

Use the lane's H001 binary asynchronous Hopfield model unchanged: 64 sites,
target-free symmetric Gaussian base weights of scale .12/sqrt(64), four
founders, four descendant replicates per founder, 24 formation sweeps and eight
reading sweeps. Capture forms without a prescribed image; teach the two
opposing conditional rules in a separate task. The two tasks do not establish
the same origin claim. All initial records are the mean body coactivity / 64,
with a zero diagonal. The apparatus and encoder are supplied.

The single added stressor is reduced input support. Compare the first eight
input sites clamped to the cue with only the first four clamped. Formation
always uses the original eight input sites. The remaining formerly clamped
sites are free during the reduced-support reads. Capture scoring still
excludes all eight original input sites, so the observed target is unchanged.

At every boundary erase activity, erase a new independently drawn 50% of
undirected record edges without rescaling, and develop a fresh random body.
Compare two outgoing-record rules:

- complete: `J_next = write_body(developed_activity)`;
- retained: `J_next = .5 * surviving_J + .5 * write_body(developed_activity)`.

Only the retained rule receives surviving incoming weights. Neither rule can
access deleted entries, founder activity, target labels or an ancestral archive.
Each conditional record uses both independent cue trials. Records, births,
damage masks, orders, clocks and endpoints are paired across interventions.
The added support factor changes the set of clamped sites, not the input tape.
The blend changes both record content and strength; there is no norm matching
or gain compensation. A difference between the writers cannot isolate access
to old material from this strength change. Report terminal record norms as a
descriptive diagnostic. Each rule's reconstruction qualification stands alone.

## Cohort and interventions

Use 24 independent random-base blocks, seeds 12000–12023, 16 replacements and
fresh-reader checkpoints 0, 1, 4, 8, 16. Keep all founders and descendants.
There is no outcome-based selection, extension, stopping or exclusion. The
engineering benchmark uses seed 11900 and two replacements and is excluded.
This sample is a bounded development cohort, not a power-qualified confirmation.

Cross each support level and writer rule with all nine H001 arms: own record,
foreign record, coordinate-scrambled founder record, erased founder record,
read blocked, body write blocked, protected copy, cumulative-loss copy and
scrambled writer addresses. Foreign functional records carry the opposite
taught rule. Permutations fix all eight potential cue sites and permute the
remaining addresses. Scrambled writer addresses affect the newly written body
component; the retained component keeps its addresses.

Body-write blocking removes the body-derived term. It leaves zero in the
complete condition and `.5 * surviving_J` in the retained condition. Read
blocking suppresses the record in body development only. Protected copying
bypasses edge loss and rewriting; cumulative-loss copying transmits the damaged
record without rewriting. These copying arms are identical across writer
labels, an exact audit requirement. Their storage allocation is equal, while
their computation requirements are lower. Bodies generated in copying arms
are diagnostics and are not necessary for copying.

Checkpoint readers are independent fresh bodies, receive only the outgoing
record plus the fixed base machinery, and never write into the lineage.
The capture endpoint is >=90% signed agreement outside the original eight
cue sites. Functional success requires both output means under both cues to
exceed .5 in their taught directions. Ordinary resemblance, body expression
and outgoing-record usefulness are reported separately.

## Frozen development decisions

The reduced-support condition (four clamps) is the sole primary panel. Each
task and each writer receives its own candidate qualification; retained
rewriting cannot qualify complete rewriting. Qualification requires:

1. mean fresh-reader completion >=.30 at both G8 and G16;
2. own-minus-foreign completion >=.15 at both horizons;
3. own-minus-cumulative-loss copying >=.10 at both horizons;
4. positive simultaneous lower bounds for the own-minus-control differences
   at both horizons for foreign, initial scramble, erased acquisition,
   read blocking, body-write blocking, cumulative-loss copy and writer-address
   scramble (14 directional contrasts per task/writer).

Resample whole base blocks jointly with 20,000 bootstrap draws and a fixed
analysis seed 920002. Use one-sided Bonferroni percentile lower bounds at
`.05/14` within each declared task/writer family. Four families have separate
verdicts; there is no pooled overall success claim or cross-family guarantee.
The baseline eight-clamp panel, full-minus-retained differences, cue-support
differences, attrition and deficits relative to protected copying are descriptive
paired estimates with pointwise two-sided 95% intervals. Do not substitute a
baseline or another horizon for a failed primary. All contrasts are retained.

The protected-copy comparison describes the cost of replacing storage with
reconstruction; beating protected storage is not a success requirement. This
experiment tests a finite horizon in one supplied architecture, not discovered
competence, evolved machinery, arbitrary damage tolerance or universal renewal.

## Records and execution

Retain full body states, all incoming/outgoing records, masks, reader states,
founders, seed identities, configuration, executable snapshots and SHA-256
seals. Audit each boundary's writer equation and copying identity, G1 body
identity across writer rules, identical copying arms across writer labels,
symmetry, zero diagonals, damaged-entry handling and fresh terminal replays.
The source must import only the lane's public H001 model and standard numeric
libraries. No private source, learned state or data enters this experiment.

Benchmark one block including saving, analysis and audit, then follow the
experiment tree's ten-minute detachment policy. Single numerical thread;
all writes remain here. Preserve existing runs and failures.
