# D117 — three read–erase–rewrite generations, then fresh terminal reading

2026-09-13. Prospective, before fresh main futures. User approved the
[D116 next lead](../reviews/L20_ACQUISITION_ONLY_2026-09-13.md).
One bounded qualification; L20 stays MIXED and L16 remains CLOSED/parked.

## Question and deliberate intervention

Can three successive fresh descendants rebuild a useful theta record from
what they read, without being taught the target again? Retained bytes alone
do not establish renewal. The primary branch therefore reads theta, erases
it, then rewrites it using the original V/R/theta update. Ordinary in-place
writing and exact copying remain separate controls. A positive in the stricter
branch is engineered read–erase–rewrite sufficiency, not proof that native
uninterrupted writing needs renewal or that this lifecycle arose autonomously.

Founder theta0 -> G1 reads/rewrites theta1 -> G2 reads/rewrites theta2 ->
G3 reads/rewrites theta3 -> a separate fresh, nonwriting terminal reader.
Thus there are **three renewal generations and a fourth transfer interface**
for testing theta3 itself. Reading only G3's body would test incoming theta2,
not the usefulness of G3's newly written record.

## Frozen physics, founders and independent units

Use D116's native16x16 periodic sheet and same two target recipes (launch1/3),
theta spatial std .3, rho .002, source lambda .001, parent gain .2. Eight
fresh random-stream/native-field blocks **60000–60007**, four paired lives
each. Only disposable **514217** is allowed in technical dynamics/timing.
No parameter/norm/target search or fresh-main pilot.

Founders use unchanged D116 common writing-off settlement120 and instructed
writing1000 steps at +/-1.2. Only writing-on founders are needed, one per
target role and paired life. Reuse the D116 parent RNG tag with these fresh
identities; descendant/permutation/probe streams use `l20-three-rewrite-v1`.
No founder filtering or extra teaching. All64 instructed founder paths remain.
Projection removes native spread scale; uniform well asymmetry cancels under
conserved drift apart from rounding. These are not eight distinct effective
physics families or new topology classes.

## Each fresh descendant and the declared packet

The ordinary interface takes exactly2048 little-endian float64 theta bytes,
fixed16x16 row-major, with public fixed host/configuration and generation/life
identity. No target label, parent V/EMA/R, RNG state, optimizer/actor/recurrent
state or held reader crosses. No such learner state exists in this sheet.
Targets remain only in founder instruction and external scoring. A fresh-
process technical check verifies the bytes-only lifecycle. Retained audit
arrays cannot be passed to the descendant interface.

At every generation, independently create V=.2 Gaussian, EMA=V and R=V.
Birth, reading noise and writing noise streams are new per generation but
paired across roles/conditions. Read for300 steps with theta held, reference
feedback off and rho unchanged. Then write for1000 steps with reference gain
.2 and the source cascade; no target clamp or reteaching. Immediately serialize
only final theta and discard all V/EMA/R/transient state before the next birth.

Eight serial conditions per role:

| Condition | Incoming record / reading | At the writing boundary |
| --- | --- | --- |
| rewrite (primary) | Correct founder record at G1, then preceding output | Erase theta to zero; write from current body/R using source lambda .001 |
| live | Same founder record | Keep incoming theta; ordinary in-place writing |
| copy | Same founder record | Keep theta and disable writing; exact transmitted bytes persist |
| write_off | Same as rewrite | Erase theta to zero and disable writing; no new record can be produced |
| read_off | Incoming packet retained but its influence disabled during each300-step read | Erase theta; enable writing from the resulting untaught body/R |
| wrong | Swap founder A/B records once at G1, then follow this branch's own output | Same erase/rewrite as primary; no later donor substitution |
| lesion | Uniformly permute the founder record once before G1 reading, preserving its exact values/norm | Same erase/rewrite; later generations receive only this branch's output |
| rescue | Same initial lesion, but restore the clean founder record before reading step101 in G1 | Same erase/rewrite; no rescue in G2/G3 |

The rescue is an explicitly **external positive control**, not evidence that
the primary repairs itself: it receives one additional2048-byte clean backup
in G1, for4096 bytes of available packet material at that interface. The
primary and other branches receive one2048-byte packet only. No backup enters
their writer or later generations. Declare this exception rather than count
the rescue as an exclusive-carrier success. Reversal is the wrong-content
swap; erasure and disabled reading/writing are separate ablations.

Erasing theta changes its initial norm to zero. On the first enabled writing
step, projection makes theta approximately `project(tanh(updated R), .3)`:
the positive lambda scale cancels unless the1e-9 denominator floor binds.
This can rapidly amplify a weak R trace. It is not an identified slow-filter
mechanism or an unchanged-native-lifecycle result. `live`/`copy` show what
happens without erasure. Writer-off legitimately remains zero; read-off writes
a norm-matched but uninstructed record and guards against a strength-only claim.

## Terminal readout, retention and identities

Read each theta3 in another common fresh body for300 steps, writing/reference
feedback off. Add ideal aligned and zero-theta instrument references for each
role. These are references, not learned records. No old founder field is given
to this reader except through the explicitly frozen-copy/rescue controls.

Per life:2 founder paths;16 serial branches x3 generations;20 terminal
readouts. Totals **64 founder,1536 renewing-generation and640 terminal paths**.
Keep founder native/projected theta, births/settlement/teaching checkpoints;
all incoming/outgoing packet bytes/hashes; rescue backups and permutations;
generation V/EMA/R/theta at0/1/100/101/300/301/600/1300 and the separate
post-read, pre-write erasure state; terminal V/EMA/R at0/1/100/300; observations,
parameters and RNG digests. Independently replay every fresh lifecycle.

Wrong branches alias the opposite role's rewrite branch under paired streams.
Terminal write-off equals zero theta; terminal read-off is role-independent.
Check six specified terminal alias pairs per life (192 total), without treating
them as extra evidence. Exact copying across generations is also a construction,
not a measured renewal success. Zero-state observer-role cancellation is not
a discovered chance level or absence theorem.

## Primary and prespecified qualification

Q is correct-sign sites satisfying strict abs(V)>.2 over all256 sites.
P=Qown-Qother. Keep sign-only scores secondary. Primary: **terminal
P(rewrite)-P(read_off)**, after the third rewritten record is passed to the
separate fresh reader. Average roles within life, four lives within block,
then eight equal blocks.10,000 whole-block percentile95% bootstrap draws.

Reading is qualified only if all target pairs disagree and both role-specific
ideal-minus-zero and copy-minus-zero terminal preference intervals have
positive lower95 bounds. Otherwise READOUT_NOT_QUALIFIED, not absent renewal.

QUALIFIED_READ_ERASE_REWRITE additionally requires:

1. Primary lower95>0 and both directional primary means>0.
2. The same rewrite-minus-read_off effect has lower95>0 and both directional
   means>0 when reading theta1 in G2 and theta2 in G3: all three renewed
   records, not a selected final rebound.
3. Terminal rewrite-minus-write_off lower95>0 and both directional means>0.

These are conjunctions, not alternative ways to pass. Else REWRITE_UNRESOLVED.
No absolute80% bar, equivalence claim, adaptive extension, exclusions, endpoint
switch or pooling with D116. One positive supports this engineered repeated
renewal channel only; it does not establish native necessity, arbitrary patterns,
permanent heredity, autonomous ontology, biology or the complete L17/L20 prose.

For each of G1/G2/G3 incoming-record readings and the terminal reader, retain
both observers and both roles/average for rewrite-minus-read_off, rewrite-
minus-write_off, live-minus-copy, rewrite-minus-copy, rewrite-minus-wrong,
rewrite-minus-lesion and rescue-minus-lesion. Terminal instrument contrasts
also retain both observers. These180 contrast rows and all absolute/timepoint
means stay visible. Lesion/rescue and ordinary in-place results are named
secondary tests; failure does not become evidence of robust self-repair, nor
can their success rescue the primary. Secondary intervals are pointwise.

## Source bridge, freeze, resources and stopping

Re-execute the known original E66 tissue0 writable-fast source/transplant using
the unchanged D116 bridge. Require exact .10546875 transplant margin and its
independent acquisition-prefix/transplant replay. Full original source executes,
but not every old fission is independently replayed and the four-tissue main
spread remains unavailable. Pin the prior D116 inputs, outputs and result
review, plus new code/protocol/tests and all used source dependencies.

Technical tests use known source, disposable514217 and algebra only. Include
a full three-generation disposable life plus terminal reading; independent
writer/reader/packet/provenance/statistic reconstruction, all gate failures,
rescue budget exception, byte-identical copy controls, erased write births,
the first-write projection identity, fresh-process lifecycle and corruption/
external/CPU/detachment guards. Retain every test report, including failures.

Freeze precedes a full-config disposable block benchmark and immutable main
preparation. Main forecast=8*checked block seconds+2*hash seconds+180, without
parallel-speedup credit. Storage forecast=8*raw block bytes+source/benchmark
bytes+32MiB, at most512MiB. The full-block benchmark guard uses four times
the one-full-life test duration plus60s, with an additional4x safety factor:
if >600s, it requires a separately detached stage. Main/replays forecast over
600s launch detached with a new session, exclusive log and stdin /dev/null;
**do not poll**, the user advances. No automatic retry or successor experiment.

At most six CPUs0–5, numerical threads one and bytecode off. All data, caches,
fixtures, logs and outputs under `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/`;
only code/docs here. Preserve4GiB+512MiB startup allowance. No source/frozen
file edits, cleanup, DoorKey germ change or reopening of parked laws.
