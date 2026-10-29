# E001 — uninstructed formation, capture, and renewal

Version 1, 17 September 2026. Development pilot, specified before new cohort
outcomes. Inspired by D116/D117; no claim of an independent implementation
replication. No calibration on main founders or post-outcome parameter search.

## Question and independent units

Can a pattern that develops without a supplied target acquire a record that
selectively influences fresh bodies after three record replacements?

Eight independent random-stream blocks (0–7), four founders in each, two
formation backgrounds, two independent descendant lineages per founder/arm.
Both backgrounds use paired founder birth/noise streams. Heterogeneous founders
within a block share the same independently sampled threshold field, permitting
history specificity to be tested within the same apparatus. Blocks, not pixels,
recipients, or founders sharing a field, are the uncertainty units.

Technical checks use only block 900001, or algebraic fixtures. Main IDs are not
used in benchmarks. Retain all 64 founders even if formation is poor. Use at
most 12 CPUs total, one numerical thread per process. Main runtime budget is
20 minutes; a timeout is incomplete evidence, not a biological failure.

## Explicit model

16×16 periodic sheet, float64. With P denoting removal of each sheet's spatial
mean and C clipping to [-2,2], N the four-neighbor mean:

    U = C(V + .2 P[V - V**3 + theta + (N(V)-V)] + P[.30 noise])
    EMA' = .9 EMA + .1 U
    V' = C(U + .2 P[c (R-U)])           (feedback only if c > 0)
    R' = R + .002 (V'-R)
    theta' = project((1-.001) theta + .001 tanh(R'), SD=.3)

The last line applies only with writing enabled. Project subtracts the mean,
divides by max(SD,1e-9), and multiplies by .3. EMA is updated before feedback,
as in the native source. Noise is not multiplied by dt. Mean removal before
clipping does not imply exact conservation. No anchors, morphogen guide,
target label, reward, template clamp, or target-conditioned selector exists.

## A. Formation

Birth V is .2 times centered IID Gaussian noise; EMA=R=V. Develop for 1,000
steps with c=0 and theta held. Theta is zero in the homogeneous condition;
in the heterogeneous condition it is a block-shared Gaussian field projected
to SD .3. This is an explicit supplied spatial bias, not target-free physics
in the sense of lacking a rulebook or geometry.

Offline founder prototype F is the mean of V over steps 901–1000. It never
enters capture or descendant dynamics. Save its two half-window averages,
the formation endpoint, and the background. Formation qualifies descriptively
per founder if both signs occupy at least 10% of sites, at least 80% of sites
have |F|>.2, nearest-neighbor sign agreement is at least .65, and the two
half-window signs agree at least .80. Cohort diversity is the mean pairwise
sign disagreement within blocks; require >.10. Report every component and
all failures, without filtering.

## B. Capture

At step 1,000 remove the formation background. Branch identical V/EMA/R into
writing-on and writing-held histories, both with zero initial theta. Evolve
1,000 steps with c=.2. Only current V→R→theta writes the record. No offline
prototype is an input. The held branch has lambda=0 and emits zero theta.
Observation is at a fixed earlier time; subsequent drift during capture is
measured rather than selecting a more favorable later prototype.

## C. Fresh bodies and three replacements

Only a 2,048-byte little-endian row-major theta packet crosses. Recipient V is
fresh centered .2-Gaussian; EMA=R=V. Birth/read/write streams differ from
founder streams and between generations. Recipient streams are paired across
arms, with independent replicates. No background, founder RNG, V, EMA, R,
prototype, or family identity crosses the dynamics interface.

Every generation reads for 300 steps (c=0, R updating, theta held), then
erases theta and writes for 1,000 steps (c=.2). Three such generations are
followed by an independent 300-step nonwriting terminal reader of theta3.

| Arm | Initial record and subsequent procedure |
| --- | --- |
| rewrite | Own captured record; erase and body-write every generation. |
| foreign | Next founder's record cyclically within the same block/background at G1 only; then its own branch outputs. |
| shuffled | Permute own packet sites once at G1, preserving its exact value multiset. |
| erased | Zero the captured record at G1; later writing enabled. |
| held | Writing-held founder packet at G1; later writing enabled. Exact alias of erased, not independent evidence. |
| read_off | Own packet present but its theta influence disabled during every generation's read; erase and write normally. Terminal probe reads its final output normally. |
| write_off | Own packet read, then erased; all generation writing disabled. |
| copy | Preserve the exact original packet at all boundaries; no rewriting. Body still experiences the same elapsed time. |
| background | Supply the unlearned formation background once, then erase/rewrite. Tests the supplied bias's ability to substitute for acquisition. |
| challenged | Own record; flip V at a fixed random 25% of sites immediately after read step 150 in each generation and terminal reading. EMA/R are not reset. |

The same random mask/noise is used for matched comparisons. Foreign donors,
permutations, and challenge sites are chosen without outcomes. All new field
packets and read/write checkpoints are retained. Projection from zero can
amplify a weak R immediately; this is engineered reconstruction, not evidence
for slow filtering or autonomous origin of a writer.

## D. Endpoints and uncertainty

Q(V,F) is the fraction of all 256 sites matching sign(F) with |V|>.2. No
prototype-selected subset or alignment is used. Sign-only agreement and
own-minus-mean-other-founder preference are secondary. Primary is terminal
Q(rewrite, own F) − Q(foreign, own F), separately by formation background.
Average recipients then founders within each block. Report 10,000 block
bootstrap percentile 95% intervals; these are exploratory pointwise intervals,
not multiplicity-adjusted confirmations. The two backgrounds remain separate.

An exploratory origin-to-renewal qualification requires: at least 75% of
founders meet the formation criteria and diversity >.10; G1 copy-minus-erased
has positive lower bound (readable acquisition); own-minus-foreign lower bounds
are positive at G1, G2, G3, and terminal; terminal rewrite-minus-read_off and
rewrite-minus-write_off have positive lower bounds. Failure of formation,
acquisition, or renewal is reported separately. No absolute fidelity claim or
equivalence to copying follows from those gates.

Report raw Q and preference for all arms/stages, continuous prototype/endpoint
statistics, foreign-record donor agreement, copying gaps, scrambled/background
contrasts, and challenge effects. No selected examples substitute for the cohort.

## E. Secondary capacity test

Before any serial rewriting, encode each captured field by fixed 1×1, 2×2,
or 4×4 spatial block averages: 256, 64, or 16 float64 values (2,048, 512,
128 bytes). Shared decoding repeats each block over its fixed cells. No
post-decoding normalization or learned codebook. Test own, foreign, and zero
records in matched fresh 300-step readers. Save actual payloads, resulting
field SD, and scores. This tests spatial resolution and amplitude together;
it is not an isolated Shannon-capacity limit or a compressed serial-renewal
result. Full-field serial results must retain their full-field qualification.

## Checks, freeze, and stopping

Check local equations against extracted native function definitions, packet
round trips, invalid packet rejection, pairing, copy invariance, zero write
births, off-control aliases, and complete cohort counts. Save code/configuration
hashes before simulation; verify them again at completion. Raw NPZ files retain
arrays without pickle. Save run status and failures; never overwrite a run.
Perform an exact disposable replay and independently reconstruct primary scores
and intervals from saved fields. A positive development result motivates a
separately frozen fresh-cohort confirmation, not retrospective relabeling.
