# D135 — identical-input serial writer address, prospective v1

Approved 2026-09-16 after D134's modest local writer-address benefit. One
three-generation conditional chain comparison; no new founders, fitted
guide, threshold search, exclusions or automatic successor.

## Fixed causal question

Does applying aligned rather than translated theta feedback during every
writer phase improve inherited content after three hard-reset generations?
Both chains start from the SAME original D132 translated F0 record, use the
same frozen D131 guide and share original D132 birth/read/write noise streams.
Every newly written packet becomes that chain's next input. Later starting
bodies are allowed to diverge through this transmission; do not overwrite
them with D132's saved read-end states as D134 deliberately did.

This is not D132's already-aligned chain, which had a different F0 record
and uncorrected reader. It is not a fresh-founder replication: both founders
and the ordinary trajectory are already known. Infer conditional on these
eight source blocks and one guide, not newly sampled pattern families.

## Identities and lifecycle

Run `l20_serial_address_v1_attempt1`; bootstrap tag `l20-serial-address-v1`.
Main 75000–75007 maps to source 73000–73007; disposable 514235 maps to 514232.
All four lives, two roles and source blocks retained. Initial packet is the
saved translated F0 `written_fields[role,0]`, never the aligned F0 packet.

Each G1–G3 descendant receives only ordinary 2048-byte packet plus fixed
public host machinery: the same 4096-byte guide and rulebook. V starts as
0.2 Gaussian, EMA=R=V, independent of the previous body. Read 300 steps with
writing/reference feedback off; erase incoming theta; write 1000 steps with
theta initially zero, rho .002, gain .2, sigma .3, lambda .001, norm .3.
Only applied theta's position differs between aligned/translated writers.
Outgoing record remains `project(tanh(R_final), .3)`, not latent theta.
No old body/reference/EMA, running writer state or RNG state is inherited.
Use distinct original phase streams for each generation, freshly initialized
from public identities; this common-random-number coupling is experimental,
not an inherited RNG payload. G4 is a fresh non-writing terminal reader.

## Complete conditions

Per role: translated, aligned, copy, aligned_read_off, aligned_write_off,
aligned_wrong, aligned_lesion, aligned_rescue. Translated and copy must exactly
reproduce the corresponding D132 learned/copy trajectories and packets.
All conditions use the SAME frozen learned selector at each read. Aligned
and its controls use aligned writing; ordinary/copy use translated writing.

Copy disables latent writing and explicitly retains incoming bytes unchanged.
Write-off disables latent writing AND emits exact zeros. Read-off disables
the packet only during G1–G3 reading, not G4. Wrong starts from the opposite
role's translated F0 record. Lesion/rescue shuffle own F0 identically; rescue
alone receives an extra intact 2048-byte backup at G1 read step101. Writers
and later generations cannot access it. Rescue is externally assisted,
not autonomous reconstruction. Preserve all exact wrong/off/prefix aliases.

G4 probes include all eight chain outputs plus aligned post-selector shuffle,
aligned pre-selector shuffle, ideal canonical and zero, per role. The same
permutation is used for pre/post probes; post-shuffle is not reselected.
48 generation read/write paths, 36 enabled rewrites, 24 terminal reads and
68 selector decisions (including two backup reads) per life. Main totals:
1536 generation paths, 1152 enabled rewrites, 768 terminal reads, 2176
selectors. Replays and aliases are engineering checks, not independent n.

Save read checkpoints0,1,100,101,300; writer0,1,300,1000; terminal0,1,100,300.
Store incoming/routed/backup/outgoing bytes, full 512-score maps, raw V/EMA/R/
theta states, all metadata, observer values and exact source hashes.

## Frozen inference

Primary: G4 qualified own-minus-alternative preference, aligned minus
translated, roles averaged within four lives within each of eight blocks.
10000 whole-block percentile bootstrap draws from the new tag. Qualified
observer keeps strict abs(V)>.2 with all 256 cells in denominator. Sign-only,
raw agreements, stage-specific and role-specific contrasts are secondary.
No absolute 80% bar, equivalence margin or multiplicity adjustment.

Instrument: distinct targets; both directional ideal-zero AND copy-zero
terminal lower95>0. Aligned content: both aligned-zero directional lower95>0,
and each pre/post-shuffle contrast pooled lower95>0 with both means positive.
Continuity: aligned-read_off and aligned-write_off have pooled lower95>0 and
both means positive at G2, G3 and G4. Interventions: terminal aligned-wrong,
aligned-lesion and rescue-lesion each meet the same supported-contrast rule.

Primary gain requires pooled lower95>0 and both directional means positive.
Primary harm uses upper95<0 and both means negative. Labels in order:
READOUT_NOT_QUALIFIED; ALIGNED_SERIAL_RENEWAL_ADVANTAGE (gain plus all renewal
controls); ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION (gain only);
ALIGNED_SERIAL_HARM_DETECTED; SERIAL_ADDRESS_EFFECT_UNRESOLVED.
Keep failed controls and losses visible; no automatic absence/equivalence claim.

At all four reads compare aligned with translated, copy, read_off, write_off,
wrong, lesion; also rescue-minus-lesion and translated-minus-copy. Terminal adds aligned pre/post shuffle,
ideal-zero, copy-zero, aligned-zero and translated-zero: 228 rows across two
observers and A/B/pooled summaries. Only the pooled G4 aligned-translated row
is primary. Copy comparison tests preservation; an advantage over translated
alone cannot establish equivalence to copying or universal cleaner layers.

## Verification and execution

Pin D134 COMPLETE `73553d2aecf50c36629d266b34a95784bc4accc534d4e4fb6495c199dd6fd43f`,
its flat 886-input/19-output closure, manifest/status/index and completed D134
review, plus six new science files and final XML. Older frozen code/reviews
are immutable. Only D135 live review and six trackers remain mutable.

Independently replay every body/writer using restated physics and FFT routing;
check resets, source ordinary/copy equality, bytes and lineage, no backup
outside G1, raw observers and block statistics. Exact signs/packets/aliases;
state tolerance1e-10, score/metric1e-12. Saved audit verifies all hashes and
rebuilds observers/inference without new dynamics. Fresh-process descendant
and saved-check tests must pass. No main counterfactual before freeze.

All outputs/logs/caches/fixtures external under /mnt/bioIce1/PlasticHeredity/
codex.lawsConfirmation; code/docs only here. At most six CPUs0–5, one numeric
thread each, bytecode off. 4 GiB reserve and 512 MiB study allowance.
Single-use freeze/benchmark/main; no automatic retry or successor.

Benchmark forecast16*full-disposable-life test seconds+60. Main conservative
forecast8*checked-block seconds+2*hash seconds+180; storage eight raw blocks
+benchmark bytes+32 MiB. Above600s, detach with new session, stdin/dev/null
and external log. After ACK no process/log/status/output polling until user
advancement. A detached benchmark never auto-launches main.

L20 remains STRESS_TESTED / MIXED. Sheet records are not DoorKey64-byte germs;
this cannot establish natural genomes, autonomous concepts, unseen-family
capacity, native necessity or universally faithful renewal.
