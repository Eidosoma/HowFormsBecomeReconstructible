# D143 — crossed feedback address and other noise, v1

Declared 2026-09-17 following user approval of D142's saved-stage lead.
Freeze source closure, implementations, independent checks, tests and this
protocol before any new main-panel off-diagonal outcome. No alteration of
D141's unresolved challenge contest or D142's completed primary results.

## Question and fixed panel

Does ordinary rewriting's variation chiefly reflect changing spatial feedback
addresses, other random effects, or their interaction? Recombine the existing
D142 four address sequences with its four non-address noise histories in a
complete 4×4 crossing. Retain all 16 blocks 90000–90015, four lives, two target
families and ordinary/translated versus aligned writers. No selected shifts,
failed-record subsets, new founders, new guide/predictor or fitted rule.

Keep original D141 F0 bytes, hosts, guide, 2048-byte float64 carrier, reader,
writer, projection and G1–G3 rewrite/fresh-G4-read horizon unchanged. Each cell
starts from its original F0, never another crossed cell. Each reader is fresh;
writer theta is erased as before. Public guide/host rules are not inherited
body state. Persistent record-versus-host contributions are not isolated.

Noise ID n=0..3 supplies every D142 birth/read/source_write stream, including
terminal birth/read, under `l20-extension1-repeated-futures-v1:future{n}`.
Address ID a=0..3 supplies only the three `g1:source_shift`, `g2:source_shift`,
`g3:source_shift` streams under that same D142 prefix with future{a}. Preserve
the original integer draw 1..255 and divmod(...,16) rule, without resampling
coincident shifts. A sequence is held fixed across noise rows within each
block/life, not a universal fixed offset across hosts or generations.
All other phase names and RNG mapping remain unchanged. The n=a diagonal
must match D142 byte for byte, not just statistically. Both target families
and writers keep matched underlying streams within each crossed cell.

The complete panel contains 4096 labelled terminal cells (256 cases ×16).
For ordinary writing all 16 combinations are retained per record–host pair.
Aligned feedback ignores the supplied displacement, so its four address
columns must be exact dynamic aliases for each noise row (metadata and the
saved unused shift differ). They are not extra random futures or independent
evidence. There are 2560 distinct condition/stream cells by design: 2048
ordinary plus 512 aligned, and 1536 declared aligned aliases. Coincident
address sequences may produce additional ordinary aliases; retain/report
them without claiming new independent information. All cells are recomputed
and independently replayed as apparatus checks, not all claimed as novel.

1024 labelled diagonal cells reproduce already-observed D142 trajectories.
Only 1536 ordinary off-diagonal outcomes are novel recombinations; aligned
off-diagonals repeat known address-invariant dynamics. No new noise vectors
or founder cohort are sampled. This is a specified mechanistic crossing on
known samples, not an untouched prospective cohort or a new challenge test.

## Primary characterization

Terminal outcome remains qualified own-minus-alternative preference: strict
abs(V)>0.2, sign V>0, all 256 cells in the denominator. Analyze each family /
writer separately. No survival threshold, optimization or binary law gate.

For each record–host–writer case let Y[n,a] be its 4×4 terminal panel. Let m
be its grand mean, u[n]=mean_a(Y[n,a])-m, v[a]=mean_n(Y[n,a])-m, and
e[n,a]=Y[n,a]-m-u[n]-v[a]. Define finite-panel sums of squares:

- S_N = mean_n(u²), S_A = mean_a(v²), S_I = mean_na(e²).
- S_T = mean_na((Y-m)²) = S_N+S_A+S_I.

These nonnegative finite-grid quantities are retained, but they are not
unbiased population variance components. The main method-of-moments crossed
estimates correct for finite four-level sampling:

- V_I = (16/9) S_I.
- V_N = (4/3) S_N - (4/9) S_I.
- V_A = (4/3) S_A - (4/9) S_I.
- T = V_N+V_A+V_I; address-minus-other-noise contrast D = V_A-V_N.

Average these per-case quantities equally across 64 cases within each group.
Do not pool raw variance across groups with different means. Report all
V_N,V_A,V_I,T,D estimates and intervals; retain negative method-of-moments
estimates rather than clipping them. They indicate sampling uncertainty,
not negative physical variability. V_I includes non-additive address/noise
dependence, not a separately sampled residual noise source. No percentages
of biological loss, autonomous repair or general address superiority follow.

Also report conditional variances with the unchanged sample divisor three:
W_N = mean_a Var_n(Y|a) = V_N+V_I, and
W_A = mean_n Var_a(Y|n) = V_A+V_I.
These answer what varies while the other factor is held fixed. They both
include interaction and must not be added as independent contributions.

Uncertainty: 10,000 whole-founder-block bootstrap draws, seed 14320260917.
Resample all 16 blocks, retaining four lives, both targets/writers, all noise
rows/address columns together. Recalculate group mean components/contrasts.
Pointwise 95% percentile intervals, not multiplicity-adjusted. Four levels per
factor do not ensure precise population component estimates. No bootstrap
across aliases or treating 4096 cells as independent founders.

## Fixed secondary descriptions and apparatus checks

Retain full 4×4 terminal panels and per-case components, all G1–G4 read-end
preferences/guide labels, and F0–F3 best-own record correlation over every
translation. Report group mean preference, negative/zero counts, and stage
conditional variances without new intervals. Shape is checked by direct and
FFT methods; correct labels are not complete fidelity. Counts include their
labelled-cell denominator and distinct-cell/alias accounting.

Every diagonal raw array must reproduce D142 (including all saved states,
packets, scores, observations, shifts and guide), and corresponding reader /
writer metadata must agree. Aligned non-address arrays are invariant across
addresses. G1 reader states and writing times 0/1 are invariant across address
columns at fixed noise for both writers; later histories can differ. Inspect
all four conditions, not only B. A violation fails the apparatus audit and
stops execution; it is not excluded as an inconvenient numerical case.
Previously qualified D141 controls remain retained; no new read-off/copy
panel is simulated. No new forecasts or challenge tuning.

## Sources, qualification, resources and launch

D142 source COMPLETE SHA256:
`a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72`.
Saved-stage review COMPLETE SHA256:
`e7893b713dce4796bfe16fffa820f1df060941c0dcd86b92db4a9e389f47533a`.
Pin full source input/output closures, original models/guide, completed review,
new code/tests and passing qualification. Do not edit existing frozen files.

Qualification and benchmark use only the already-observed disposable block
514240. No main-panel off-diagonal simulation during qualification/benchmark.
Test independent explicit-physics replay, seed factorization, all diagonal
bridges, aligned aliases, corruption, moment denominators/negative estimates,
interaction, block normalization, resource guards and detached startup.

Run identity `l20_extension1_crossed_address_noise_v1_attempt1`.
Benchmark a complete block: four lives × four noise IDs × four address IDs ×
four conditions, full independent replay, serialization and saved checks,
plus independent statistics on a clearly labelled repeated disposable fixture.
Benchmark forecast =64*qualified_full_disposable_cell_seconds+90.
Main forecast =16*checked_block_seconds+2*hash_seconds+180, no parallel credit.
Storage budget =16*uncompressed_block_bytes+benchmark_bytes+64MiB.

At most six workers/CPUs, numerical threads one, affinity 0–5. All data,
arrays, logs, caches, manifests and test artifacts under the existing
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/` root;
code/docs only in the repository. 2GiB stage allowance plus 4GiB free reserve.
Any forecast above 600s must run detached with durable logs, null stdin, a
new session and one bounded startup acknowledgement. No automated progress
polling or successor launch. Single-use paths; failures preserve partial
artifacts and stop without retry. The user advances completion/audit.
