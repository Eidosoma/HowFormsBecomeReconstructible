# S8-Core confirmation report

This report is generated from the frozen clean-room protocol and fresh
confirmation matrices. Estimates are whole-matrix means with 95%
whole-matrix bootstrap intervals unless stated otherwise.

## Integrity and registered gates

- Confirmation matrices: 96
- Exact base and result replay: PASS
- Repertoire-definition gate: FAIL
- Conditional rehoming gate: FAIL
- Prospective hold-control gate: FAIL
- Frozen occupancy floor: 0.02
- Frozen edit caliper: 0.005

A failed gate is retained as a result; no candidate is rescued by pooling.

## 1. Form repertoire and traffic atlas

### Candidate C02

- Stable form count: 7.990 [7.115, 8.844]
- Wandering traffic: 0.397 [0.341, 0.454]
- Matched-half fraction: 0.759 [0.720, 0.796]
- Half-traffic Spearman rho: 0.333 [0.237, 0.425]
- Exact molecule-relabeling audit: PASS
- Rarefaction (launches: mean stable forms / wandering):

  - 32: 2.917 / 0.458
  - 64: 5.198 / 0.395
  - 128: 5.760 / 0.400
  - 256: 8.188 / 0.375
  - 512: 7.990 / 0.397

### Candidate C03

- Stable form count: 7.844 [6.948, 8.698]
- Wandering traffic: 0.412 [0.356, 0.469]
- Matched-half fraction: 0.756 [0.713, 0.795]
- Half-traffic Spearman rho: 0.302 [0.203, 0.398]
- Exact molecule-relabeling audit: PASS
- Rarefaction (launches: mean stable forms / wandering):

  - 32: 2.729 / 0.476
  - 64: 5.406 / 0.405
  - 128: 5.635 / 0.415
  - 256: 8.021 / 0.395
  - 512: 7.844 / 0.412

## 2. Conditional rehoming chain

### c02_h0

- Own minus foreign cross-fit location score: 0.705 [0.668, 0.741]
- OWN minus MISMATCH incumbent return, given break: 0.020 [0.007, 0.039]
- MISMATCH active minus original destination score: 0.889 [0.826, 0.936]
- RELABEL minus OWN active capture: 0.003 [-0.008, 0.013]
- Cell gate: PASS

### c02_h1

- Own minus foreign cross-fit location score: 0.707 [0.669, 0.741]
- OWN minus MISMATCH incumbent return, given break: 0.017 [0.005, 0.037]
- MISMATCH active minus original destination score: 0.918 [0.887, 0.944]
- RELABEL minus OWN active capture: 0.008 [-0.002, 0.020]
- Cell gate: PASS

### c03_h0

- Own minus foreign cross-fit location score: 0.695 [0.651, 0.736]
- OWN minus MISMATCH incumbent return, given break: 0.017 [0.008, 0.028]
- MISMATCH active minus original destination score: 0.895 [0.845, 0.933]
- RELABEL minus OWN active capture: 0.018 [-0.004, 0.048]
- Cell gate: FAIL

### c03_h1

- Own minus foreign cross-fit location score: 0.695 [0.648, 0.736]
- OWN minus MISMATCH incumbent return, given break: 0.020 [0.007, 0.038]
- MISMATCH active minus original destination score: 0.899 [0.859, 0.932]
- RELABEL minus OWN active capture: -0.004 [-0.016, 0.007]
- Cell gate: PASS

## 3. Identical-natural-break hold assay

Eligible states: 596 / 596.

### c02_h0

- HIGH minus LOW strict-hold probability: 0.007 [-0.000, 0.014]
- HIGH minus NOOP: 0.006 [-0.001, 0.013]
- NOOP minus LOW: 0.001 [-0.004, 0.006]
- RANDOM minus NOOP: 0.005 [-0.002, 0.012]
- NOOP Brier score: 0.038 [0.021, 0.060]
- Matrix-centred state-rank rho: -0.058
- Cell control gate: FAIL

### c02_h1

- HIGH minus LOW strict-hold probability: -0.002 [-0.011, 0.004]
- HIGH minus NOOP: -0.001 [-0.006, 0.004]
- NOOP minus LOW: -0.001 [-0.013, 0.008]
- RANDOM minus NOOP: -0.002 [-0.007, 0.003]
- NOOP Brier score: 0.037 [0.022, 0.056]
- Matrix-centred state-rank rho: 0.093
- Cell control gate: FAIL

### c03_h0

- HIGH minus LOW strict-hold probability: 0.000 [-0.006, 0.006]
- HIGH minus NOOP: 0.002 [-0.004, 0.008]
- NOOP minus LOW: -0.002 [-0.007, 0.004]
- RANDOM minus NOOP: 0.001 [-0.006, 0.007]
- NOOP Brier score: 0.043 [0.029, 0.060]
- Matrix-centred state-rank rho: -0.013
- Cell control gate: FAIL

### c03_h1

- HIGH minus LOW strict-hold probability: -0.004 [-0.010, 0.002]
- HIGH minus NOOP: 0.000 [-0.006, 0.007]
- NOOP minus LOW: -0.004 [-0.009, 0.001]
- RANDOM minus NOOP: 0.001 [-0.004, 0.006]
- NOOP Brier score: 0.043 [0.029, 0.061]
- Matrix-centred state-rank rho: 0.027
- Cell control gate: FAIL

## 4. Three-generation branching boundary

### C02 — CERTIFIED

Audits: 83 across 47 matrices.

- Generation 1: certified-form retention 0.686 [0.580, 0.782]; any-repertoire retention 0.729 [0.628, 0.824]; branch-pair coherence 0.702 [0.596, 0.809].
- Generation 2: certified-form retention 0.513 [0.423, 0.604]; any-repertoire retention 0.620 [0.516, 0.720]; branch-pair coherence 0.449 [0.360, 0.540].
- Generation 3: certified-form retention 0.408 [0.330, 0.491]; any-repertoire retention 0.580 [0.480, 0.672]; branch-pair coherence 0.344 [0.268, 0.424].

### C02 — FAILED_GEOMETRY

Audits: 168 across 84 matrices.

- Generation 1: certified-form retention 0.173 [0.122, 0.229]; any-repertoire retention 0.381 [0.310, 0.452]; branch-pair coherence 0.256 [0.181, 0.333].
- Generation 2: certified-form retention 0.097 [0.062, 0.137]; any-repertoire retention 0.347 [0.284, 0.412]; branch-pair coherence 0.148 [0.106, 0.192].
- Generation 3: certified-form retention 0.083 [0.050, 0.123]; any-repertoire retention 0.346 [0.289, 0.403]; branch-pair coherence 0.117 [0.081, 0.157].

### C03 — CERTIFIED

Audits: 89 across 47 matrices.

- Generation 1: certified-form retention 0.777 [0.702, 0.846]; any-repertoire retention 0.824 [0.739, 0.899]; branch-pair coherence 0.766 [0.670, 0.862].
- Generation 2: certified-form retention 0.585 [0.508, 0.660]; any-repertoire retention 0.737 [0.657, 0.814]; branch-pair coherence 0.505 [0.426, 0.580].
- Generation 3: certified-form retention 0.455 [0.394, 0.518]; any-repertoire retention 0.614 [0.540, 0.687]; branch-pair coherence 0.305 [0.243, 0.367].

### C03 — FAILED_GEOMETRY

Audits: 166 across 83 matrices.

- Generation 1: certified-form retention 0.105 [0.063, 0.154]; any-repertoire retention 0.422 [0.352, 0.491]; branch-pair coherence 0.235 [0.163, 0.307].
- Generation 2: certified-form retention 0.084 [0.054, 0.119]; any-repertoire retention 0.393 [0.325, 0.460]; branch-pair coherence 0.166 [0.126, 0.210].
- Generation 3: certified-form retention 0.080 [0.053, 0.109]; any-repertoire retention 0.373 [0.312, 0.437]; branch-pair coherence 0.123 [0.092, 0.158].

## Claim boundary

These results concern a reconstructed abstract stochastic model and the
registered strict-hold component. They do not establish life, autonomous
agency, biological memory, real prebiotic chemistry, permanent identity,
or full branching reproductive fidelity.
