# Bounded pilot results

Date: 2026-09-05. Status: bounded pilot complete, including the explicitly
logged runtime-only neighbour follow-up.

## Outcome

The small isolation mechanism reproduces under the pinned source. All nine
registered baseline isolation comparisons, all three sensitivity checks, and
the 625-cell benchmark passed. The original grouped neighbour experiment hit
its 900-second limit after completing seven of eight thresholds; all seven
were within 0.1% of their saved references. Its original status remains a
timeout, not a pass. A separate 260.7-second follow-up completed the missing
threshold and reproduced the other threshold in that pair. Across both runs,
**all eight unique neighbour thresholds matched within 0.09%** of the saved
values, comfortably inside the predeclared 2% gate.

This is promising as an executable platform for communication-boundary and
rehoming experiments. It is not a complete reproduction of the paper, an
independent implementation, a PH demonstration, or biological validation.

## Provenance and artifacts

- Source: BITSEY `b2cb370aaecbc8299f259bc4251d5396c81f19a6`, unmodified.
- Environment: Python 3.13.5; NumPy 2.5.2; SciPy 1.18.1; Matplotlib 3.11.1.
  Full pins: [requirements-smoke.txt](requirements-smoke.txt).
- Host: x86-64 KVM environment, reported Intel Xeon 2.20 GHz, 24 logical CPUs.
  The pilot used at most two processes, with numerical libraries limited to
  one thread each. Timings are observations on this shared machine.
- Pre-run criteria: [PILOT_PROTOCOL.md](PILOT_PROTOCOL.md) and
  [configs/pilot_v1.json](configs/pilot_v1.json).
- Original run: [summary.json](runs/pilot-20260905T232334Z-uw_m4g5f/summary.json).
  It ran for 900.016 wall seconds and recorded **13 passes, one timeout**.
- The runtime-only follow-up was declared separately in
  [PILOT_FOLLOWUP_PROTOCOL.md](PILOT_FOLLOWUP_PROTOCOL.md), without changing
  scientific parameters or the 2% threshold-agreement criterion.
- Follow-up artifacts:
  [summary.json](runs/pilot-neighbour-followup-20260905T233905Z-5s_lckl8/summary.json).
  Both five-neighbour directions passed; process wall time was 260.688 s.
- Raw artifacts are ignored, not vendored. Commands to regenerate them are in
  [RUNNING.md](RUNNING.md). Upstream files were clean after both runs; no
  unrelated PH or sister-folder data was changed.

The original manifest hashes the simulation source files, saved references,
configuration, protocol, and runner. Its runner SHA-256 is
`4d029b5ac660258592475b406401c9db1f8f62b5f8c65642c1f1f678203077d5`;
configuration hash is
`2a5794290b10d6dcb6183043b0afb9ac017a9d4932f1b3227be67162e0e58613`.

## 1. Isolation comparisons

Each baseline case starts with six M-like cells in a 25-cell line, the rest
E-like. Snail is 72; medium-size miRNA has effective valence -1. Preparation
uses 500 model-time units with miRNA transfer off, followed by 20000 units
at the specified coupling. Underexpression is 0.5 where used.

| Strategy | Kd | Expected normalized? | Observed normalized? | Final E / M / X | Process wall time |
| --- | ---: | --- | --- | --- | ---: |
| None | 6.25e-15 | No | No | 20 / 5 / 0 | 31.9 s |
| None | 1.25e-14 | Yes | Yes | 25 / 0 / 0 | 37.8 s |
| Underexpression | 8e-15 | No | No | 20 / 5 / 0 | 30.8 s |
| Underexpression | 1.25e-14 | Yes | Yes | 25 / 0 / 0 | 40.7 s |
| Voltage | 1e-13 | No | No | 19 / 6 / 0 | 67.7 s |
| Voltage | 2e-13 | Yes | Yes | 25 / 0 / 0 | 72.4 s |
| Both | 2e-13 | No | No | 19 / 6 / 0 | 59.0 s |
| Both | 4e-13 | Yes | Yes | 25 / 0 / 0 | 80.5 s |
| Voltage, matched comparison | 1.25e-14 | No | No | 19 / 6 / 0 | 77.3 s |

Two useful same-coupling comparisons follow directly:

- At `1.25e-14`, no isolation produces all E-like cells, while voltage isolation
  preserves the six-cell M-like patch.
- At `2e-13`, voltage isolation alone permits complete normalization, while
  voltage isolation plus reduced connexin expression preserves the patch.

This supports the modeled boundary mechanism: which cells effectively exchange
regulatory material affects whether a pre-existing state persists or is
overwritten. At sufficiently high tested coupling, even the combined strategy
fails to protect it. “Not normalized” is not equivalent to “unchanged”: the
two weakest ungated cases lose one of their six initial M-like cells.

These are matches to brackets around historical 1D thresholds, not fresh
measurements of all four exact threshold values. They do not reproduce
Table 1's stated 3D geometry.

## 2. Neighbour-switching thresholds

The native experiment has a central cell and 2–5 oppositely initialized
neighbours in a star. Both switching directions are tested. Here “E to M”
means an E-initialized centre surrounded by M-initialized neighbours.

| Neighbours | Direction | Saved threshold | Rerun threshold | Relative difference |
| --- | --- | ---: | ---: | ---: |
| 2 | E to M | 1.129e-15 | 1.130e-15 | 0.0886% |
| 2 | M to E | 1.005e-15 | 1.005e-15 | 0% at printed precision |
| 3 | E to M | 7.124e-16 | 7.129e-16 | 0.0702% |
| 3 | M to E | 6.442e-16 | 6.442e-16 | 0% at printed precision |
| 4 | E to M | 5.212e-16 | 5.212e-16 | 0% at printed precision |
| 4 | M to E | 4.740e-16 | 4.740e-16 | 0% at printed precision |
| 5 | E to M | 4.108e-16 | 4.108e-16 | 0% at printed precision |
| 5 | M to E | 3.748e-16 | 3.750e-16, follow-up | 0.0534% |

Reference: `results_miRNA/surround_flip_72`. These are rounded source-output
values; agreement at printed precision is not bitwise equality. The binary
search's own bracket tolerance is approximately 0.1%, and our predeclared
reference-agreement gate is 2%.

The original eight-search process timed out while starting the final pair's
M-centre trials. To complete that comparison, the separately logged subset
adapter runs the five-neighbour pair in the original E-then-M order, using
the original builder, initialization helpers, simulator, predicate, and binary
search. It repeated the already-completed E-centre threshold as a check and
obtained the same printed `4.108e-16` value. Only the outer orchestration was
reconstructed; the equations were not. All eight unique threshold comparisons
passed. The grouped-process timeout remains visible in its original manifest.

The completed results show that more same-state neighbours require less
coupling per connection to switch the centre. The success criterion is a
finite-horizon concentration comparison to the neighbours' prepared state,
not an assertion of an asymptotic attractor or lifelong memory.

## 3. Numerical sensitivity and nonstationarity

| Comparison to baseline | Cell labels preserved? | Largest absolute endpoint difference, all concentrations | Selected regulatory-marker differences |
| --- | --- | ---: | --- |
| Voltage at 2e-13, finer settings | Yes; all E | 0.03623 | miR200_total 0.03623; ZEB_prot 0.00000362 |
| Both at 2e-13, finer settings | Yes; 6 M, 19 E | 0.03506 | miR200_total 0.03506; ZEB_prot 0.00001070 |
| Both at 2e-13, connected horizon 40000 instead of 20000 | Yes; 6 M, 19 E | 4.71338 | miR200_total 0.27449; ZEB_prot 0.37175 |

The tighter cases halve the minimum step and both adaptive increment bounds,
including during preparation. They are paired configuration-sensitivity
checks, not an isolation of the connected-phase numerical error alone.

The longer run's largest differences are in potassium and chloride, about
4.71 and 4.70 scaled concentration units respectively. Therefore, preservation
of E/M labels must not be described as proof that every state variable has
converged. All differences above are in the source's scaled coordinates, not
clinical concentration measurements.

The original suite completed 195 audited integration calls, including 169
completed calls from the timed-out neighbour process, containing 51,358
returned snapshots. All checked snapshots and final states were finite and
nonnegative. This does not check every internal step. The largest difference
between a returned last snapshot and its live final state was about 2.665;
this reinforces the need to retain the upstream experiment's exact sampling
and endpoint definition when comparing threshold values. The follow-up added
50 completed integration calls and 13,138 returned snapshots, all checked
finite and nonnegative. Combined audit totals include repeated searches and
must not be presented as independent experimental replicates.

Non-fatal invalid-escape `SyntaxWarning`s came from `edebug.py` and `eplot.py`.
The warnings were not suppressed by source edits. The reporting harness's
five unit tests passed, and `pip check` found no broken requirements.

## 4. Larger-network timing

The 1x25x25 grid starts with a 1x6x6 M-like corner (36 M cells, 589 E cells).
With no isolation, `Kd=1.25e-14`, and the same 500/20000 horizons, it finished
with **625 E-like cells and no M/X cells**, passing the native normalization
criterion.

- Process wall time: **101.024 s**.
- Measured in-worker experiment wall time: **100.353 s**.
- In-worker CPU time: **100.334 s**.
- Peak worker resident memory: **137.3 MiB**.
- Matched 25-cell experiment wall time: **37.167 s**, excluding process startup.
- Observed 625/25-cell wall-time ratio: **2.70**, not 25.

This single comparison shows that small and medium experiments are practical
on this machine. It does not establish linear scaling, benchmark 15,625-cell
3D systems, or estimate the whole paper's cost. Adaptive integration and
different trajectories make cell count alone a poor runtime predictor.

## 5. Decision and implications for PH

**Proceed with a small, controlled follow-up track; do not yet claim complete
publication replication.** The core historical behavior is reproducible and
the small/medium runs are affordable. Ordinary 25-cell baseline cases took
roughly 31–81 seconds here; threshold searches take minutes because they
repeat simulations. Full sweeps should be budgeted from a manifest of the
actual required trials, not from the time for one case.

The immediate obstacle to exact paper replication is also provenance, not
just computing time. [PAPER_OUTPUT_MAP.md](PAPER_OUTPUT_MAP.md) documents a
Table 2 geometry ambiguity and apparent Table 3 column/row-label mismatches
against the archived raw outputs. Resolve those before launching expensive
table-reproduction sweeps. They do not by themselves refute the mechanism.

For our work, the useful bridge is **state-dependent communication controlling
pattern survival and overwriting**. A subsequent rehoming study could move the
same initialized pattern into differently coupled recipient environments.
That would still be weaker than PH. Testing PH would additionally require
serial bottlenecks, renewable carrier production in recipients, and causal
removal/rescue controls separating renewed inheritance from residual material,
continuing external forcing, or ordinary horizontal state propagation.

No new lineage experiment, wet-lab result, therapy claim, or evidence for a
Platonic-space/Ruliad ontology follows from this pilot.
