# D147 — matched stopping-time readouts

Approved 2026-09-19 following the D146 saved-state review. This is a specified
mechanism follow-up on an already observed cohort, **not fresh held-out evidence**.
Freeze this protocol, qualified code and provenance before generating any new
main readouts. Preserve all D146 files and its unresolved primary comparison.

## Question and sole primary

From the SAME saved extended-writing trajectory, does the record emitted at
writing step 1300 reconstruct better than the record emitted at step 1000?
The earlier snapshot is a diagnostic branch, not a replacement ancestor.

The sole primary is **B intact G3, 1300 minus 1000 fresh-reader
own-minus-alternative preference**. Each assay lasts exactly 300 updates, with
matched birth and noise streams. Use the original strict abs(V)>0.2 and sign
V>0 score, denominator 256. Report raw scores and preference points (100×score),
not success percentages. Average four lives and two noise replicas within each
of 16 blocks. Use 10,000 whole-founder-block bootstrap draws, seed 14720260919.
Positive 95% interval favors continuation; negative favors stopping; otherwise
unresolved, not equivalence. No fitted stopping rule or new fidelity threshold.

This estimates the immediate effect of another 300 writing updates on emitted
record/readout quality, conditional on each existing extended-writing history.
It does NOT estimate a lineage that stopped early at every previous boundary.
At G2/G3 the previous generations are still D146's 1300-step ancestors.

## Cohort, records, matching and provenance

Use ALL D146 blocks 93000–93015, four lives, both families, two replicas and all
three generations. No selection by current shape, sign, guide label or review
stratum. There are 256 family/life/replica cases, 128 per family, but only
16 independent blocks. Reuse disposable source block 514246 only for tests and
benchmarking. Generate no new founders and no new upstream reading/writing.

Keep the original 2048-byte carrier, 4096-byte frozen public guide, encoding,
host parameters and compatible-feedback addresses. In particular, form records
from saved R via the original normalized tanh(R) encoder, NOT writer theta.
The extended arm's checkpoint indices 3 and 4 are times 1000 and 1300.

D147 bookkeeping namespace: `l20-extension1-stopping-time-v1`. Physics deliberately
REUSES `l20-extension1-phase-budget-v1` terminal birth/read streams, separately
for each block/life/replica/generation. This provides exact endpoint bridges;
it is not another independent-noise replication. Readers see only routed bytes,
fixed public host/guide and their own fresh state, never source-body state.
Neither diagnostic bodies nor their records enter a subsequent lineage.

## Complete panel and exact reuse

For each stop, family and generation retain intact, protected-copy,
lineage-read-off and write-off conditions. Read-off disables lineage reading,
not the final assay. Copy transmits F0; write-off transmits zeros.

| Stop/condition | Endpoint source |
|---|---|
| 1300, all four conditions | Exact saved D146 `write` condition/control |
| 1000, intact G1 | Exact saved D146 `base` G1, after shared-prefix check |
| 1000, intact G2/G3 | NEW assay of R1000 from the D146 `write` history |
| 1000, read-off, all generations | D146 `base_read_off`, after exact prefix checks |
| 1000, copy/write-off | Same saved copy/zero endpoints as at 1300 |

Disabled lineage reading removes incoming-packet dependence, so base/read-off
and extended/read-off bodies and writing prefixes match at every generation.
Verify this equality rather than merely assuming it. Verify G1 intact prefixes
and all copy/zero aliases. If any bridge fails, stop; do not silently substitute
another source or generate additional outcomes under this version.

Accounting: **6144 labelled assay cells**, of which **512 are genuinely new
assays** (intact early-stop G2/G3), and 5632 are reused/aliased labels. Reusing
endpoints across stops does not create independent observations. Save explicit
source mapping and full provenance for every labelled cell. Seal `CELL_PLAN.json`
before any new main assay; this is a provenance plan, not a forecast seal.

At each stop/family/generation report copy-minus-write-off, intact-minus-read-off
and intact-minus-write-off: 36 apparatus checks. All lower pointwise bounds >0
qualifies the apparatus. Any failure narrows interpretation but never suppresses
the numerical primary, removes a case or triggers tuning.

## Secondary reporting

Report all 48 condition/stop/family/generation groups, 24 paired stop contrasts,
12 intact-minus-copy comparisons, and 16 G3-minus-G1 changes. Include every
individual value and block mean, positive/negative/zero changes, negative/zero
absolute preferences, guide labels and margins, outgoing own shape, own-minus-
alternative shape, canonical shape margin and fresh-reference shape/profiles.
Shape is a continuous correlation, not a fraction of information preserved.
All nonprimary intervals are pointwise and unadjusted.

The seven previously identified negative D146 writing-B cases may be displayed
as a clearly post-hoc descriptive stratum, never as a new primary or exclusion
rule. G1 is an already known bridge. The new G2/G3 readouts can localize immediate
loss but cannot prospectively validate the earlier review's apparent warning sign.

## Qualification and execution

Pin D146's 1522 inputs, 37 indexed outputs, completion/manifest/status/hash
index, result report, and saved-review inputs/code/results/qualification/audit.
D146 COMPLETE SHA256:
`3d057c9123cf3a10d6068c356dae6b4632834c9da4f87a88f431d8ce2f5789e0`.
Review COMPLETE SHA256:
`c6655c7d778e05574bb74acc4064b89b85210e5ed6a7dafafd74069117df56c0`.
Pin all eight D147 scientific files and passing qualification XML. Independently
check encoding, routing, bridge/alias identity, metadata, metrics and every saved
checkpoint. Independently replay all 512 NEW main assays. Previously completed
assays retain D146's physics replay provenance; do not claim to replay them anew.
Saved-output audits run zero new dynamics. Independently reconstruct statistics.

Benchmark a complete disposable block: four lives, 384 labelled cells, 32 new
assays plus their independent replay, all controls/bridges, saved checks, and a
16-copy synthetic statistical fixture (explicitly not scientific evidence).
Qualification forecast for benchmark: 4×complete-life test seconds +90.
Conservative main forecast: 16×checked-block seconds +2×hash-check seconds +180,
without parallel speed credit. Byte budget: 16×uncompressed block bytes + measured
benchmark bytes +64 MiB, bounded by a 1 GiB allowance with a 4 GiB free reserve.

All numerical outputs, fixtures, caches and logs stay under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`.
Code/docs only here. Maximum six CPUs (affinity 0–5); numerical threads one.
Run IDs and outputs are single-use. Forecasts above 600 seconds require a
detached session, null stdin and durable logs. Startup handshake only; no
automatic progress polling, retry, tuning, successor or next-stage launch after
a detached job. Failure artifacts are retained. User advances detached work.

No outcome establishes autonomous interface repair, complete shape preservation,
or a validated general stopping policy. D141–D146 claims and L20's status remain
separate from this conditional, fixed-reader intervention.
