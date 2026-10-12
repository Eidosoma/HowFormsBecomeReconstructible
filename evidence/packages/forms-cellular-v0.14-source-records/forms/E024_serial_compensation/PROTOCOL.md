# E024 — compensation through three damaged renewals

Fixed before new simulation, 20 September 2026. The user authorized the next
serial lead after E023 qualified one damaged renewal with a compensated
receiver. E021's failed serial test and E022/E023 results remain unchanged.

## Fixed intervention and cohort

Use **32 fresh blocks 22000–22031**, four founders and four lineages per founder:
128 founders and 512 lineages. The excluded benchmark is **900024**, one
lineage per founder. IDs were checked unused. Retain every case and mask.

Extend E022's eight renewal chains to exactly **three replacements**, handing
each chain its own immediately preceding outgoing packet. Keep E016 consistent
acquisition, the 16×16 reciprocal lattice, 512 float64 edges / 4096 bytes,
E017 staged reading (gain 2, 2048 updates, amplification off for the first 256),
noise .02, dt .2, birth SD .05, strict .25 port-average margins and final-32
observation window. Immediate capture still averages the two cue-specific
local products of tanh(3*activity), after incoming-weight erasure, followed
by 128 holding updates on the surviving unit-positive scaffold. The writer
receives only activity and fixed parameters. No assay result enters renewal.

Retain baseline fixed-four, physical-degree and local-strength compensated
damaged renewal, intact renewal with its original fixed-four reader, protected
copying, copying with cumulative matched edge erasures, and local-strength
reading-blocked/writing-blocked controls. The **strength-compensated chain
with the local-strength terminal receiver** is the fixed candidate.

At each renewal birth independently remove **24 scattered non-port cells**.
Pair the mask across damaged chains, opposite rules and cues; keep those cells
and their incident edges absent through reading, capture and holding. Each
generation gets fresh births, noise and masks. Successors start on the full
lattice before their own injury; the writer may write at a coordinate absent
in an earlier body when it is present now. Do not reject disconnected masks.

Protected copying preserves original bytes. Masked copying applies the new
mask to **its previous masked packet**, so erasures accumulate and no values
are reconstructed. Reading blocked supplies zero incoming weights at every
replacement; writing blocked retains its computed capture for audit but
transmits zeros at every replacement. Only packets cross boundaries. Injury
masks, body states and denominators are not transmitted as additional data.

## Assays and paired controls

Assay the initial packet and all eight chains at replacements **one and three**.
Retain generation-two boundary evidence and body scores without a terminal
assay. Apply both E023 terminal receivers: fixed denominator four and local
sum of absolute effective incident weights, computed after physical injury
and all record/communication controls. Zero strength gives zero incoming
contribution. Use the same packet, birth, noise, mask and shuffle for the two
receivers. No floor, retuning or output-dependent selection is introduced.

Retain intact, 24-cell scattered-loss and non-port 3×3 terminal lesions, and
all seven arms: own, opposite-rule foreign, shuffled, erased, untrained,
communication-off and source-cut. Terminal bodies and injury realizations
are independent of renewal, and each injury panel is a separate fresh body.
Pair terminal realizations across packet conditions and receiving readers.

There are **34 terminal panels**: initial fixed/normalized, then eight fixed
and eight normalized at each of horizons one and three. Retain **731136
terminal individual scores** and **18432 pre-capture body scores** across
all three generations, nested within the 32 independent blocks.

## Primary, full qualification and secondary contrasts

The **single primary** is absolute **intact-terminal both-cue success after
three damaged replacements**, for the strength-compensated chain with the
local-strength receiver. Require its two-sided 95% whole-block bootstrap
lower bound **>0.75**. This retains E021's serial reliability endpoint while
testing the compensated apparatus; it is not a primary improvement endpoint.

Full qualification additionally requires:

- Candidate both-cue lower bounds >.75 in intact bodies after one replacement
  and scattered-terminal bodies after both one and three replacements.
- All 24 original candidate gates at both horizons: six rule×injury individual-
  cue accuracy lower bounds >.75 and 18 own-minus-control lower bounds >.10.
- All 24 original intact-renewal reference gates at each horizon under **each**
  receiving reader, retaining the original reference and checking the new one.
- All 12 normalized candidate-minus-read/write-blocked individual-cue
  advantage lower bounds >.10 across three terminal injuries and both horizons.

Report the primary and full conjunction separately, every failed gate, every
arm, rule-specific accuracy, both-cue success, margins and all generation body
outputs. Secondary contrasts include normalized-minus-fixed receiver effects
for every packet; candidate-minus-each-other-chain within each receiver and
horizon; candidate-minus-masked-copy differences in receiver benefit; and
generation-three-minus-generation-one changes for every chain and receiver.
Also report the combined intervention, normalized candidate minus fixed-reader
baseline, at both horizons. These contrasts distinguish renewal and receiving
effects without selecting a new winning variant.

No superiority to copying, equivalence, noninferiority, zero decay or unique
mechanism is a qualification requirement. A positive serial endpoint alone
does not prove an improvement over baseline. Use 10000 percentile whole-block
resamples with stream `["E024","bootstrap","serial"]`; all secondary
intervals and qualification gates are pointwise. Descendants, readers, rules,
cues and injury panels are nested observations. Observed 100% is not population
certainty. No exclusions, retuning, severity changes or automatic successor.

## Evidence, fixtures and execution

Reuse E022/E023 numerical functions and their semantic streams on fresh IDs:
acquisition `["E016",block,"teach",episode]`; renewal `["E022",block,"develop",g]`
and `["E022",block,"write",g]`; terminal `["E022",block,"assay",h]` and
`["E022",block,"shuffle",h,founder]`; E015 injury phases
`E022_renewal_g{g}` and `E022_h{h}`. First-boundary behavior must exactly match
E023 on disposable inputs. Generation enters all renewal streams. No cohort
pooling; no feedback from outcomes to seeds or parameters.

Save all source evidence, every boundary's incoming/effective/erased/computed/
outgoing packets, masks, local denominators, births, reading endpoints and
port windows, all holding states, and all terminal evidence from E023.
Independent audit imports auditors only, never production model or runner;
replay every update using E022's independent boundary arithmetic and E023's
independent receiving arithmetic. Verify cumulative erasure, protected copies,
exact generation handoffs, physical zeros and source isolation, then every
CSV row, interval and gate. Retain teaching symmetry tolerance 1e-10.

Six short fixture tests cover first-boundary predecessor agreement, serial
handoff/fresh masks/cumulative erasure, local denominators after controls,
paired receivers, unchanged writer and forbidden information paths, receiving
invariants and independent three-generation end-to-end replay. Preserve all
attempts and failures; freeze scientific code before simulation. The fixture
suite is estimated below two minutes from E023's 33-second suite and the
additional serial panels.

The full-duration excluded benchmark's conservative pre-run estimate is
`1.5*(34/18)*E023_benchmark_workflow_seconds` = **1167.34 seconds (19.46 minutes)**,
including independent audit and figures. Run it **detached** under RUN_POLICY.md;
the user requests status checks. Its scientific criteria are descriptive only.
Do not automatically launch the cohort from the benchmark. Inspect completed
technical evidence and freeze the measured cohort forecast before cohort launch.

The full-cohort forecast remains
`2.5*(benchmark_worker_seconds+benchmark_audit_seconds)*4*ceil(32/workers)+90`;
storage scales benchmark bytes by 4×32 plus a 1 GiB reserve. At most 12 logical
CPUs total and one numerical thread per process. Runs forecast over 600 seconds
detach with frozen configuration, PID, log and durable status. All writes stay
inside experiments; manuscripts, sister trees and prior frozen files remain
unchanged. This tests supplied compensation during damaged development, not
acute repair, regrowth, autonomous timing or indefinite renewal.
