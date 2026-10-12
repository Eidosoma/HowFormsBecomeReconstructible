# E014 reviewer analysis: specificity, fidelity and amplitude

Requested 10 October 2026. This is a post hoc reanalysis of existing fields,
not a new simulation or a replacement of E014's frozen endpoints or decisions.
Use all 64 blocks 12000–12063, both record sizes, all founders, recipients and
ten arms. No success filtering. Primary displays use E014's fresh checkpoint
readers after 1, 3, 8 and 16 completed rewrites. Keep the 16 lineage reads in a
separate display: G1 precedes the first rewrite; G16 precedes the sixteenth.
Do not merge these different reader streams into one trajectory.

## Archive and provenance

The complete local archive is
`E014_long_renewal/runs/confirmation_v2/`, containing all 128 files
`block_012000_factor_{1,4}.npz` through `block_012063_factor_{1,4}.npz`.
Their combined size is 3,227,309,039 bytes. Repository-level `**/*.npz` excludes
them from git, explaining why a checkout can contain reports without these fields.
Verify original COMPLETE output hashes, frozen input snapshots and the recorded
independent audit before extraction. Preserve original files unchanged. Commit
derived integer cell counts, paired endpoint contingency tables, source hashes,
scripts, summaries, manuscript-ready prose and PNG/SVG/PDF figures. These compact
extracts reproduce the analysis without committing the multi-gigabyte archive;
they do not reconstruct continuous fields or constitute a complete raw backup.

## Original score and exact decomposition

The prototype belongs to the own founder even in the foreign-record arm. A
foreign donor is the next cyclic founder within the same background block, used
at acquisition; both chains then renew. Define, for all 256 coordinate-matched
sites, S=1[(v>0)==(prototype>0)] and A=1[abs(v)>.2]. Retain the original >0 sign
convention, including zeros, and strict amplitude threshold. No prototype-amplitude
filter and no conditioning of the denominator on resolved sites.

- Qualified agreement Q=mean(S*A), the original E014 endpoint.
- Sign agreement mean(S), counting even subthreshold signs.
- Amplitude qualification mean(A), regardless of correctness.
- Four disjoint categories: match/resolved, match/unresolved,
  mismatch/resolved, mismatch/unresolved. Their fractions sum to one.

Thus Q=sign agreement−matched-but-unresolved fraction exactly. Q is generally
not the product of the two marginal rates. Report each marginal, the joint
categories, and paired after16−after3 changes. Retain all stages and controls.

For additional endpoint accounting, cross-tabulate the four categories at
after3 and after16 at the same coordinates under the paired checkpoint random
streams. Net loss/gain of Q splits into sign-only endpoint differences (resolved
at both endpoints), amplitude-only differences (matching at both endpoints), and
both differences. Sum these net terms to recover delta Q. These compare fresh
bodies: they are not observed within-cell transitions, a count of intervening
crossings, or a causal allocation of interacting mechanisms.

## Inference and figures

Average founders and two recipients within each independent block. Reuse E014's
10,000 whole-block bootstrap indices `["E014","bootstrap"]`; reproduce all
existing qualified scores and their intervals. New intervals are descriptive,
pointwise 95% intervals, not new confirmatory gates or simultaneous discoveries.

Show own-record, matched foreign-record and protected-copy Q on the same native
0–1 scale at every checkpoint, with a clearly labeled same-unit zoom to make the
small own−foreign gap legible. Distinguish total agreement from this incremental
contrast; neither is a number of information bits. Plot sign/amplitude decomposition
for both record sizes. Include a separate lineage-read plot and compact tables.

The E001 homogeneous-versus-heterogeneous development pilot is a separate cohort
and apparatus setting: reproduce its history-specific contrast and formation
qualification from its audited archive, without pooling it with E014. Explain
that stronger historical dependence does not establish stable formation. The
manuscript's evidence labels E31/E43 refer here to E001/E004 and E014, not folders
named E031/E043. No parent manuscript files are edited by this analysis.

Use one numerical worker while E053 runs. This analysis does not poll or alter
E053 or launch E054. Save and commit only this review deliverable and its links.
