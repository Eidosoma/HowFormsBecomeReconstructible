# H089 — inherited responses to unseen context/query combinations

24 October 2026. Authorized after H088. A **fresh development pilot**, root
seed **89089**, with **16 independent networks**, four related births each,
and four separate engineering networks. Freeze before new cohort outcomes.
Use the existing 128-unit projection architecture, sequential delayed reader
and single-pair assistance. This changes the task, not the update rule.

## Structured task and fixed observation boundary

Two context bits and two query bits specify 16 combinations. Encode each
context bit in 16 identical units and each query bit in 24 identical units,
giving the existing 32 context, 48 query and 48 response units. All methods
receive this same public encoding. No latent teaching rule enters a reader.

Index a combination by `context + 4*query`, with each integer in 0..3 and
least-significant bits first. Teach the eight edges `query=context` or
`query=(context+1) mod 4`: **[0,3,4,5,9,10,14,15]**. Hold out the complement
**[1,2,6,7,8,11,12,13]**. Every context and every query occurs twice in teaching;
every held-out pairing is new. The split is fixed across cohorts and generations.

Each output bit is a signed parity of a subset of the four input bits. The
focal and donor rules are generated independently. Include masks 1,2,4,8 once,
draw 44 additional nonempty masks uniformly from 1..15, shuffle all 48 output
positions, and draw independent output signs. This guarantees distinct full
response vectors for distinct input combinations, while allowing different
parity orders and rule geometries across networks. The generator is supplied
task structure; it is not discovered by the neural writer.

The 32 signed parity functions, including constants for fitting corrupted
packets, have distinct signatures on the eight teaching combinations. Check
this exhaustively before simulation. Consequently every teacher output bit
is identifiable from the observed examples within the declared rule family.
This is a finite learnability certificate, not a claim that a Hopfield writer
will infer that structure. No arbitrary unseen random labels are withheld.

Only G0 acquisition receives eight correct teaching responses. During both
actual handoffs **G0 → G1 → G2**, every writer receives only the same eight
training inputs and its parent's actual responses there, including errors.
Unseen-combination assays are passive, reset independently from the common
birth, and never enter a writer. No success filter, original labels, hidden
teacher masks, older record or held-out response enters reconstruction/native
writer packets. Keep all failures and descendants. No G2 writer or G3.

## Lineages, readers and equally observed controls

Keep ordinary and pair-assisted reconstruction parents as separate fixed
policies, alongside corresponding independent coefficient-copy lineages.
Propagate independent linear LS, quadratic LS, nearest-history and **parity
ERM** lineages from their own actual training responses. At G1/G2 also keep
same-parent local copies and all four local same-packet native fits.

Parity ERM searches all 32 signed parity functions independently for each
response bit, minimizing disagreements on the eight permitted observations.
Ties use mask order 0..15, positive then negative sign. It receives no hidden
mask or held-out label. Its native record contains 48 mask indices and 48
signs; the public decoder/hypothesis family is supplied apparatus. If parental
responses are inconsistent, retain the deterministic best fit and every error.
This strong ordinary rule learner is an explicit positive control. Perfect
generalization by it would establish feasibility, not neural superiority.

Linear/quadratic fits retain the existing input-only rank-four PCA and
minimum-norm polynomial fits; nearest-history stores the eight observed
examples. Copying retains explicit coefficient access. No method receives
extra teaching data. Report representation/payload differences, including the
rule learner's supplied inductive bias; no storage or computation match.

At every record use the original four context sweeps, four gap sweeps, eight
delayed query sweeps, and eight ordinary continuation sweeps or the existing
single-pair step plus eight continuation sweeps. Score both ordinary and pair
recipients; only the declared parent policy supplies training emissions.
There are no simultaneous updates or new repair rules. Assay all 16 combinations
independently under common births and order tapes. Own, independent-donor and
fully erased native records remain passive source controls. Donor scores use
their own targets in separate columns.

## Scores and predeclared findings

Report trained and held-out panels separately. Each has eight queries with
the unchanged >=44/48 criterion and all-eight-query complete-task criterion.
Keep exact-query/bit scores, every paired gain/loss, all original expression,
inherited-policy, comparator, source and generation contrasts, and G2−G0
contrasts. Also retain the four trained-task/held-out-task success combinations
for every assay; a held-out failure after failed trained retrieval is distinct
from trained success without generalization.

The primary held-out endpoint is **G2, own source, pair-assisted parents,
ordinary recipient**. Separate finite development findings are:

1. **G0 trained capability:** pair-parent reconstruction under its actual pair
   reader completes at least 75% of the trained tasks.
2. **G2 held-out capability:** primary completion is at least 75%, with at least
   25 percentage points over both donor and erased controls. The parity-rule
   positive control must remain exact, as independently checked.
3. **Inherited parental-policy benefit:** primary held-out task gains exceed
   losses against ordinary-parent records under the fixed ordinary recipient.
4. **Comparator gaps:** retain all ten local/independent copy/native comparisons.
   The joint descriptive advantage label requires positive task and nonnegative
   query differences against every comparator. The exact rule positive control
   leaves no strict-superiority headroom if it remains perfect; this pilot's
   open objective is inherited generalization, not beating a ceiling.

The 75%/25-point screens are bounded development criteria, not population
qualifications. No resampling of related births as independent networks,
test-based model selection, alternate split, selective enrollment or replacement
of a failed primary by trained-query or assisted-recipient scores.

## Validation, execution and scope

Strict physics inputs contain only eight teaching outputs, common external
tapes and cue values. Full analyst targets are attached to saved results only
after simulation. Changing held-out labels must leave physics inputs and
emitted training packets unchanged. Check actual ancestry, copied coefficients,
every writer's training-only packet and every passive source/read alias.

Independently rebuild records using exact integer-Gram projection, alternative
native fits and exhaustive scalar parity matching. Replay all unique neural
trajectories in extended precision, including pair-energy differences. Retain
record tolerance 4e-14, fields/energies 2e-11 and decision exclusion 5e-14.
Fixtures verify the fixed split, identifiable rule signatures, inconsistent
packet fitting/ties, held-out isolation, erased birth holding, old-reader
equivalence, corrupted packets/predecessors/fields/rows, all tables and reports.
Reload every raw array and causal graph. Keep immutable failures and sources.

Benchmark identical four engineering networks with one/four workers; require
exact arrays, audits and tables, and choose four only at speedup >=1.15.
Forecast main as 1.25 times the selected four-network duration times four plus
90 seconds. Use one numerical thread per worker and shared twelve-CPU admission.
Watch short runs and leave longer/capacity-delayed work detached under lane
policy. No automatic successor or public-manuscript edit. Private AI lanes
supply no quoted text, result or implementation here. H031 causal/forecasting,
H033 observation/comparator and H086–H088 verdicts remain unchanged.
