# E021 — function through three damaged renewal bodies

Fixed before new simulation, 19 September 2026. The user authorized damage
during renewal after E020 qualified three intact-body replacements. This is
a new prospective challenge informed by E019/E020, with no pooled observations.

## Fixed apparatus and injury

Keep E016 consistent acquisition, E017 staged reading and E019/E020 immediate
capture: 16×16 reciprocal torus, 512 float64 edges (4096 bytes), gain 2, 2048
reading updates with amplification off for the first 256, two opposing rules
and cues, strict ±0.25 margins, final-32-update assay averaging. Keep remaining
E015 defaults, 512 teaching updates per cue and final-128 capture unchanged.

Use **32 fresh blocks 19000–19031**, four founders and four lineages per founder:
128 founders, 512 lineages. All cases count without success filtering, retuning
or cohort extension. All unused acquisition byproducts remain audit evidence.

At the birth of each renewal body, remove **24 scattered non-port cells**.
Keep their activity zero and remove every incident edge throughout reading,
immediate capture and the 128-update holding window. Draw a new mask for every
generation and lineage, paired across opposite-rule founders, cues and damaged
conditions. Preserve ports and accept all masks without connectivity rejection.
This tests development with missing cells; it does not model acute injury to
an already functioning body or regrowth within a body. Successors are freshly
born on the full lattice before their own independent injury is applied.

After staged reading with only input clamped, erase effective incoming weights.
Apply the **unchanged immediate local correlation estimator** to current body
activity, averaging the two cue episodes. The capture API receives only activity
and fixed parameters, never injury masks, incoming packets, labels or targets.
Zero activity at absent cells gives zero incident correlations naturally; there
is no extra normalization, reconstruction, filling or repair rule in the writer.

Protect the resulting packet without feedback during the same 128-update
unit-positive-scaffold window. The scaffold has only the current surviving
edges, and cells remain absent. Discard the body afterward. Only its 4096-byte
outgoing packet reaches the next body; no output reteaching or assay feedback.

## Six matched chains and terminal assays

1. **renewed:** damaged development and immediate rewriting at every boundary.
2. **intact_renewed:** identical renewal with no cells removed, using paired
   births/noise; this controls the injury intervention within the fresh cohort.
3. **protected_copy:** preserve original packet bytes, explicitly bypassing bodies.
4. **masked_copy:** at each boundary set incident edges of the same 24-cell mask
   to zero in its own previous packet, preserving other edge values exactly.
   This record-only control accumulates erasures; it neither develops nor learns.
5. **read_blocked:** same damaged body and writer, with incoming read weights zero.
6. **write_blocked:** same damaged body, reading its own incoming packet normally;
   calculate and retain capture but transmit zeros after every boundary.

The masked-copy contrast describes whether effects exceed repeated coordinate
erasure alone. It is not equivalent to protected copying or a cost-matched
learning algorithm. Renewed bodies may write at previously missing coordinates
when those cells are present in a later body. Injury masks are not transmitted
as extra bytes; zeros in the fixed-size packet can reflect missing edges.

Assay the original at horizon 0 and all six chains after replacements 1 and 3,
using fresh bodies independent of renewal. Retain intact, 24 scattered-loss
and non-port 3×3-lesion terminal assays, with all seven arms: own, opposite-rule
foreign, shuffled, erased, untrained, communication-off and input-isolated.
Terminal injury masks are independent of renewal masks. Conditions share
terminal births/noise/masks/shuffles. Generation-2 boundary evidence is retained
without an extra assay. There are **279552** individual scores:
32 blocks × 13 panels × 4 founders × 4 lineages × 2 cues × 3 assay injuries × 7 arms.

## Endpoints and stopping

The **single primary** is intact-terminal-assay both-cue success after three
damaged-body replacements. Require its two-sided 95% whole-block bootstrap
lower bound **>0.75**. Both inputs must pass for a matched lineage.

Full qualification additionally requires damaged-renewal intact-assay both-cue
lower bound >0.75 after replacement one; all original 24 gates for damaged
renewal at horizons 1 and 3; all original 24 gates for the intact-renewal
reference at both horizons; and all 12 damaged-renewal reading/writing-dependence
gates. Original gates are six rule×assay-injury individual-cue reliability
lower bounds >0.75 and 18 own-minus-assay-control lower bounds >0.10. Boundary
gates require renewed-minus-read-blocked and renewed-minus-write-blocked
individual-cue lower bounds >0.10 for each assay injury and horizon.

Report primary and full conjunction separately, all failed gates, every arm,
rule-specific accuracy, margins, both-cue success, renewed-minus-each-other-chain
contrasts, and generation-3-minus-generation-1 changes for all chains. There
is no prespecified equivalence/noninferiority to intact renewal or copying,
superiority over masked copying, or zero-decay claim. Contrasts are secondary.

Use 10000 percentile resamples of independent whole blocks with seed
`["E021","bootstrap","renewal"]`. All secondary intervals and qualification
gates are pointwise. Founder pairs, lineages, cues and injury panels are nested
observations. Observed 100% and a degenerate interval do not prove population
certainty. Stop after this cohort regardless of outcome; no automatic rescue,
mask rejection, severity adjustment, parameter search or successor.

## Evidence and execution

Keep source streams `["E016",block,"teach",episode_index]` on fresh block IDs.
Renewal streams are `["E021",block,"develop",generation]` and
`["E021",block,"write",generation]`. Draw injury with unchanged E015 mask
generation `["E015",block,"E021_renewal_g{generation}","damage"]`, selecting its
scattered mask; the square-mask draw is unused. Terminal streams are
`["E021",block,"assay",horizon]`, shuffles
`["E021",block,"shuffle",horizon,founder]` and masks
`["E015",block,"E021_h{horizon}","damage"]`. Outcomes never enter a seed.

Retain teaching evidence, all renewal masks and incoming/effective/erased/
computed/outgoing packets, reading births/endpoints/final port windows, all
128 holding states, and assay packets/masks/births/endpoints/late means/final
port windows. Earlier updates replay exactly from frozen inputs and streams.
An independent audit imports no production model or runner, reproduces every
update, physical cell/edge deletion, packet, score, interval and gate, including
isolation at every reading/assay update. Keep the 1e-10 teaching-symmetry
tolerance and exact replay. All checks and audit must pass before any claim.

Four short fixtures verify exact E020 capture agreement and local arithmetic,
forbidden information paths/erasure order, serial packet reuse/fresh masks,
physical deletion/incident edges/masked-copy arithmetic, and independent
end-to-end replay. Preserve failures. Excluded benchmark **900021** uses full
durations and one lineage per founder. Its prior estimate is
`1.5*(13/9)*E020_benchmark_workflow_seconds`, below ten minutes. Benchmark
outcomes never select design. For the cohort use
`2.5*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/workers)+90`,
with `workers=min(12,available CPUs)`. The multiplier rises from 2 to 2.5
because E020 exceeded its forecast by 8.2%; the change precedes E021 outcomes.
Scale benchmark storage by 4×32 plus 1 GiB reserve.

Runs forecast over 600 seconds run detached, with frozen inputs, durable logs,
PID/status and automatic audit/figures; the user polls. Numerical libraries
use one thread per process, at most 12 CPUs total. All writes remain inside
experiments. Prior inputs, manuscripts and sister trees remain unchanged.

Any positive result concerns serial functional transmission through this
specified damaged development, with supplied acquisition, injury, reader clock,
scaffold and packet protection. It does not establish acute repair, regrowth,
autonomous timing, flexible compensation or indefinite renewal.
