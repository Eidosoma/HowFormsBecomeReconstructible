# Starting point: voltage-gated communication, rehoming, and plastic heredity

Date: 2026-09-05.

Scope: a lightweight exploration before deciding whether to commission a full
independent replication. This document records the preceding paper review and
public-repository availability check; it does not report new simulation results.

Subsequent execution update: the pinned source has now been cloned and three
bounded smoke checks passed without source modifications. See
[SMOKE_RESULTS.md](SMOKE_RESULTS.md) and [RUNNING.md](RUNNING.md). The initial
availability assessment below is retained as the historical starting point.

## 1. Paper and source provenance

**Paper:** Joel Grodstein, Juanita Mathews, and Michael Levin, *Membrane voltage
and connexin expression work together to enhance tumor growth and metastasis
in cancer*.

- DOI: [10.64898/2026.09.02.748840](https://doi.org/10.64898/2026.09.02.748840).
- Version reviewed: v1, posted September 3, 2026; not certified by peer review.
- Local PDF: [/home/robert/2026.09.02.748840v1.full.pdf](/home/robert/2026.09.02.748840v1.full.pdf).
- PDF SHA-256: `47269dee14c458315c01772b3415791c456cd0d538f14dd5163dbb4defab956a`.
- This is the cancer paper ending in **748840**, not the separately discussed
  bacterial paper ending in **748853**.

The PDF says all data and code are available on GitLab, but its data-availability
statement does not provide a repository URL or a publication-specific revision.

### Public repository checked on September 5, 2026

- Repository: [grodstein/bitsey](https://gitlab.com/grodstein/bitsey).
- GitLab project ID: `8132007`.
- Default branch: `master`.
- Latest observed commit: `b2cb370aaecbc8299f259bc4251d5396c81f19a6`, committed
  August 21, 2026; message: "Remove the old_code directory from git tracking".
- The cancer code was updated that day in
  [cf1ef210](https://gitlab.com/grodstein/bitsey/-/commit/cf1ef2104323b1eb73e736d3ea4c058333b94c59),
  and saved results were added in
  [82754975](https://gitlab.com/grodstein/bitsey/-/commit/82754975bcbe74392f3097bafef1b5e0eeb7a443).
- No tags or releases were returned by the public API at the time of checking.
- The other observed branch, `development`, had a 2020 tip; it was not a newer
  cancer-paper release.

Relevant paths at the observed revision:

| Material | Upstream location |
| --- | --- |
| Simulator and gap-junction implementation | Repository root, including `sim.py`, `sim_toolbox.py`, and `GJ_lib.py` |
| Cancer simulations | `cancer_GJ_sims/zombie.py` |
| miRNA regulatory model | `cancer_GJ_sims/GRN_miRNA.py` |
| Alternative protein model | `cancer_GJ_sims/GRN_proteins.py` |
| miRNA development notes and figure/table mapping | `cancer_GJ_sims/0readme_miRNA.txt` |
| Saved results and plotting scripts | `cancer_GJ_sims/results_miRNA/` and `results_TFs/` |

Useful fixed-revision links:

- [Cancer folder](https://gitlab.com/grodstein/bitsey/-/tree/b2cb370aaecbc8299f259bc4251d5396c81f19a6/cancer_GJ_sims).
- [miRNA notes](https://gitlab.com/grodstein/bitsey/-/blob/b2cb370aaecbc8299f259bc4251d5396c81f19a6/cancer_GJ_sims/0readme_miRNA.txt).
- [Root README](https://gitlab.com/grodstein/bitsey/-/blob/b2cb370aaecbc8299f259bc4251d5396c81f19a6/README.md).

**Availability verdict:** substantial relevant source, saved results, and notes
are public and were updated shortly before the preprint. Completeness, exact
publication-version correspondence, licensing for reuse, environment setup,
and reproducibility have not been established. The root README is minimal;
the detailed notes mix development history, incomplete/older runs, and references
to earlier numbered script versions. Do not silently equate latest `master`
with the exact version that produced the paper.

## 2. The mechanism in plain language

Cells have internal regulatory states, but their neighbours can influence those
states through gap junctions. Connexin expression affects the availability of
these channels, while voltage differences affect their conductance.

For the homotypic channels emphasized in the model, similar voltages at the two
ends favour communication. A voltage mismatch restricts it. This is a statement
about a difference between cells, not a universal healthy absolute voltage.

The proposed tumour scenario has two regimes:

1. A small tumour can resist surrounding tissue by reducing gap-junction density
   and becoming electrically mismatched to its healthy neighbours.
2. A larger, strongly interconnected tumour can reinforce its own regulatory
   state. Suitable connections across its boundary can then help it push
   neighbouring cells toward a tumour-associated state. Voltage matching can
   be achieved by changing tumour voltage or the voltage of nearby cells.

Consequently, increasing communication need not always improve tissue health:
the outcome depends on which populations are coupled and which state they
support. A "functional syncytium" here means an effectively integrated network,
not literal fusion of cells.

## 3. What the paper actually models

The study combines a numerical bioelectric/GRN model with a simplified analytical
description. Ion-channel, pump, transport, and regulatory dynamics are modeled;
this is not a new wet-lab validation of their combined hypothesis.

Each cell contains an epithelial–mesenchymal transition (EMT) circuit involving
miR200 and ZEB. The authors choose Snail conditions with two stable isolated-cell
states, excluding the hybrid state for simplicity. Exchange of miR200 through
gap junctions can change the regulatory state.

Reported model outcomes include greater resistance to normalization when
depolarization and connexin underexpression are combined, increasing resistance
with prescribed tumour size, and communication regimes that facilitate
neighbour-state switching.

Important boundaries:

- Bistability is a selected property of this regulatory model, not a newly
  discovered universal law of PH.
- The paper counts M-to-E switching as normalization and E-to-M switching of
  neighbours as a proxy for invasion. These readouts do not themselves establish
  cancer cure, cell migration, dissemination, or metastatic colonization.
- The voltage dependence of miRNA passage includes an assumption extrapolated
  from channel gating and molecular-size evidence. The authors explicitly report
  no known direct miRNA experiment establishing that gating behavior.
- Geometry, coupling strength, and internal regulatory resistance matter; this
  is not simply a universal "larger group wins" rule.
- Strategy language interprets the modeled configurations. It does not show a
  tumour learning or autonomously selecting its communication strategy.
- Persistence while connected to supportive neighbours is not a demonstration
  of persistence after decoupling, let alone inherited renewal.

## 4. Connection to our research

The strongest connection is to **control of state rewriting**, with a possible
later bridge to heredity.

| Local concept | Proposed connection | What remains to be shown |
| --- | --- | --- |
| Rehoming | Neighbours can change the regulatory state in which a recipient operates. | A durable change after removing the forcing; distinguish return to baseline from a different persistent state. |
| Memory protection | Internal reinforcement and restricted boundary access can resist rewriting. | Separate intracellular retention from continuing external support. |
| Collective boundaries | Voltage gating changes effective connectivity without physical relocation. | Measure whose influence actually controls the recipient, rather than infer membership from voltage alone. |
| Bounded observers | A coarse E/M label can conceal different histories and future responses. | Richer trajectory, perturbation, relapse, and relearning measurements. |
| Plastic heredity | An acquired state might influence descendants after separation. | A causal, content-specific carrier that crosses a defined bottleneck and is renewed. |

Our suggested interpretation is **rehoming without relocation**: a cell remains
in place while a change in communication changes which collective influences
it most. This is a research hypothesis, not an established result under our
rehoming criteria.

It also separates two questions often bundled together:

- What stores the acquired information?
- What controls whether another system can overwrite it?

Voltage and connectivity could be access controls, part of the carrier, a reader
context, or continuing external support. Their role must be determined rather
than named in advance.

### Relevant local evidence and caution

- The [GRN observer atlas](../../gre-2-ideas/runs/grn-observer-atlas-v1/report.md)
  reported 14/24 apparent resets under a response-only observer, but 2/24 under
  richer state-based criteria. Rehoming and temporary suppression were among
  the exploratory classifications; none establishes confirmed erasure or PH.
- The [constrained-recovery report](../../gre-2-ideas/runs/grn-constrained-basin-recovery-v1/report.md)
  found 0/5 robust constrained-basin tasks. Persistent states should not all be
  described as demonstrated restoring attractors.
- The [memory-manifold report](../../gre-2-ideas/runs/grn-memory-manifold-v1/report.md)
  leaves the sampled geometries mixed or unresolved.
- The [local synthesis](../RELATED_PAPERS_THEORY_SYNTHESIS.md) supplies the
  operational PH distinction: acquired information must cross a specified
  renewal boundary and make a content-specific causal contribution in
  descendants, with appropriate controls.

A bottleneck may remove both material information and the neighbours that
supported its expression. Loss after separation does not by itself distinguish
carrier loss from loss of the necessary reconstruction context.

## 5. Staged exploration, not a full campaign yet

### Stage A: establish source correspondence

Before running anything:

- Obtain a separate upstream checkout if/when exploration proceeds; record the
  full revision, keep upstream unchanged, and keep any patches separately.
- Identify the actual run entry points, dependencies, license, initial states,
  parameters, stopping criteria, and result-file formats.
- Map one tumour-isolation result and one neighbour-state-switching result to
  the corresponding paper table and saved output.
- Resolve document/code version ambiguities before interpreting mismatches as
  scientific failures. Ask the authors for the publication commit and commands
  if the public materials cannot settle this.

There is a specific documentation check worth retaining: the paper's Table 3
and the miRNA notes' final "Selections" block do not have an immediately clear
row/column correspondence. For example, the triplet `45 / 4.1 / 6.0` appears
against `2.6e-15` in the paper but against `8.80e-16` in those notes. The notes
use `Kd_field`, whereas the paper labels its parameter `G_GJ0`; conversion,
configuration, labels, and version history have not been reconciled. This is
an audit lead, not a demonstrated numerical or implementation error.

### Stage B: minimal source checks

Once source mapping is clear, agree a small runtime budget and numerical
comparison tolerances before execution. Start with isolated-cell state checks,
then one isolation case and one neighbour-switching case. Record discrepancies
and numerical sensitivity; do not change source assumptions to make a match
and then call the result an unchanged replication.

### Stage C: an exploratory rehoming probe

Only after the baseline is interpretable:

1. Use matched regulatory architectures and controlled exposure histories.
2. Apply a finite communication or voltage intervention.
3. Remove it and restore matched external conditions.
4. Compare trajectories and challenge responses against naive, exposed, sham,
   continuously supported, and decoupled controls.
5. Test whether retained effects are transient forcing, durable rehoming, or
   continued dependence on a collective scaffold.

Keep an exact naive return distinct from a third persistent state. A single
marker switch is not enough to establish memory erasure.

### Stage D: decide whether full replication is worthwhile

Reasons to proceed include tractable source reproduction, effects robust to
reasonable numerical checks, and a controllable distinction between internal
memory and external reinforcement.

Reasons to pause include unresolved provenance, missing essential inputs,
effects dependent on numerical failure, or no interpretable way to separate
ongoing forcing from retained state. A negative rehoming result can still be
informative; it does not invalidate a correctly reproduced communication model.

Full replication, broad sweeps, and any later agent handoff remain future work
to be agreed with the user.

## 6. Longer-term PH question

Do not collapse these four outcomes into one:

1. Temporary influence while the source remains connected.
2. Durable rehoming after the source is removed.
3. Horizontal propagation from the changed recipient to another recipient.
4. Renewable lineage inheritance across a specified bottleneck.

A later PH experiment would add division or fragmentation, controlled recipient
context, carrier ablation/rescue/content reversal, and renewal through material
turnover. It must distinguish passive carryover, repeated environmental
instruction, and generic stabilization from a history-specific inherited effect.

The candidate contribution is therefore narrow and testable: **the accessibility
of a regulatory state to rewriting may depend jointly on its internal feedback,
its supporting neighbours, and boundary permeability**. Whether this supports
renewable heredity is an additional question, not a conclusion of this paper.
