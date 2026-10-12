# Paper-to-source mapping: pilot scope and unresolved discrepancies

Inspected 2026-09-05. Source revision:
`b2cb370aaecbc8299f259bc4251d5396c81f19a6`. Paper: local
[748840 v1 PDF](/home/robert/2026.09.02.748840v1.full.pdf), particularly the
table images on PDF page 26 and their descriptions in the main text.

This is a source/document comparison, not an author-confirmed erratum and not
a full numerical replication. Do not silently change paper labels or saved
outputs to make them agree.

## What the pilot can reproduce

| Pilot target | Source and saved reference | Relation to the paper |
| --- | --- | --- |
| 25-cell isolation comparisons | `zombie.py`: `setup_basic_network`, `set_corner_tumor`, `disconnected_sim`, `sim_is_fixed`; `results_miRNA/tumor_isolate_1D_V1M` | Small-network version of the isolation mechanism; **not** Table 1's stated 3D geometry. |
| Eight neighbour-switching thresholds | `zombie.py`: `surround_flip_sims`, `surround_flip_sim`, `binSearch`; `results_miRNA/surround_flip_72` | Supporting network-state-switching experiment, not a one-to-one recreation of a numbered paper table. |
| 625-cell benchmark | Same isolation helpers, 1x25x25 grid; qualitative reference `results_miRNA/tumor_isolate_2D_V1M` | Runtime and one normalization outcome only, not the full size/underexpression sweep in Table 2. |

All paths above are relative to `upstream/bitsey/cancer_GJ_sims/`.
The actual pilot criteria were registered in [PILOT_PROTOCOL.md](PILOT_PROTOCOL.md).

The saved 1D isolation thresholds, in order none / voltage / underexpression /
both, are `7.18e-15 / 1.51e-13 / 9.41e-15 / 2.96e-13`. The corresponding 2D
values are `1.89e-15 / 6.58e-14 / 3.4e-15 / 1.28e-13`. The underexpression
factor is 0.5 in those historical outputs. These are distinct from Table 1.

## Table 1: geometry and result provenance still need matching

The main text specifies a 6x6x6 M-state block in a 25x25x25 field (15,625 cells).
Table 1 reports, in units of `1e-15 m^2/s`:

| Underexpression | None | Depolarization only | Underexpression only | Both |
| --- | ---: | ---: | ---: | ---: |
| 0.3 | 1.1 | 38 | 3.3 | 120 |
| 0.5 | 1.1 | 38 | 2.1 | 75 |
| 0.8 | 1.1 | 38 | 1.3 | 45 |

Neither the saved 1D nor the saved 2D threshold quartet is this table. The
pilot therefore cannot establish Table 1 reproduction even if every registered
1D outcome agrees. A full campaign needs the exact 3D run configuration and
the output file/revision used to produce this table.

## Table 2: apparent dimensional-description ambiguity

The main text says the setup follows Table 1, varying tumour size. However,
the visible table columns are 1x1 through 8x8, i.e. two-dimensional labels.
The pinned `zombie_tumor_isol` implementation performs its size sweep only
for 2D fields: it returns early for 3D or 1D, then tests `[1, size, size]`.

There is a numerical lead: the table's 0.5-underexpression, 6x6 entry is
`13e-14`, consistent after rounding with the historical 2D both-strategies
threshold `1.28e-13`. This suggests a 2D origin for at least that entry, but
does not prove every entry's provenance. Resolve the geometry before defining
an exact paper-reproduction target.

## Table 3: apparent column and row-label mismatch

The paper's Table 3 columns read **Depol / Hypol / Neighbor-depol**. In contrast,
the distinctive numerical triples match the repository notes and raw saved
outputs in the order **depol / nbrDepol / hypol**.

Moreover, after the first two rows, the paper's conductance labels do not match
the labels attached to the same numerical triples in those saved outputs:

| Paper row G_GJ0 | Paper's displayed triple | Saved row Kd_field matching that triple after rounding | Saved case |
| --- | --- | --- | ---: |
| 1e-16 | >100 / 45 / 48 | 1.00e-16 | 4 |
| 3e-16 | 95 / 14 / 17 | 2.97e-16 | 13 |
| 2.6e-15 | 45 / 4.1 / 6.0 | 8.80e-16 | 22 |
| 7.8e-15 | 21 / 1.5 / 2.4 | 2.61e-15 | 31 |
| 2.3e-14 | 11 / 3.3 / 1.4 | 7.75e-15 | 40 |

For example, the archived raw case 22 explicitly associates `depol=44.55`,
`nbrDepol=4.079`, and `hypol=5.982` with `Kd_field=8.80e-16`, `tumorness=1`,
`GJ_OiET=0.5`, and an 11-cell tumour. The paper attaches the rounded values to
`2.6e-15` and reverses the last two algorithm headings relative to that file.

Evidence can be inspected without running simulations:

```bash
sed -n '515,616p' upstream/bitsey/cancer_GJ_sims/0readme_miRNA.txt
gzip -cd upstream/bitsey/cancer_GJ_sims/results_miRNA/metas_algos_1D_V1M_0_81.gz | rg '^((4|13|22|31|40|49)\. Final)'
```

The notes' `Selections` block starts at line 606. Its named source archive is
present, and its corresponding raw records agree with the notes. This is
stronger evidence than a mismatch inferred solely from an informal summary.
For the first row, the archived depolarization entry is an invalid tumour-size
interval `[21,20]`, not a directly measured power threshold above 100; the
meaning of the paper's `>100` shorthand also needs checking.

These observations are consistent with a table-assembly/labeling problem, but
another output revision or an undocumented transformation has not been ruled
out. A single constant unit conversion does not explain a mapping that matches
the first two row labels but shifts the later ones. Do not report these as
confirmed author errors, or use the table to rank the two algorithms until
the correspondence is resolved. No metastasis threshold has been newly rerun
in this pilot.

## Consequence for the next decision

The code can still be a useful experimental platform if the bounded source
results reproduce. Exact publication replication additionally requires a
manifest mapping each table entry to revision, geometry, parameters, criterion,
raw output, and rounding/transformation. That provenance work is a separate
task from merely allocating more compute, and should precede a large sweep.
