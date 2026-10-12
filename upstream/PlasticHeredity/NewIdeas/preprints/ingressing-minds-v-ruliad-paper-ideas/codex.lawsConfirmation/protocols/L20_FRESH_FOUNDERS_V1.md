# D140 — fresh-founder serial-address replication, prospective v1

Approved 2026-09-16 after completed D139. Park the slower-record / reference
hand-off branch. Replicate D135's aligned-versus-translated renewal comparison
on a new founder cohort, with its rules, guide, carrier and inference unchanged.
This protocol is written before any main-cohort dynamics or outcomes.

## Question and scope

Does D135's alignment advantage survive new taught founders and new
developmental histories? D135 found a pooled terminal advantage but used
already-known D132 founders/noise, with a larger B than A effect. D140 does
not reuse those founders, later states or noise streams, and does not pool
their outcomes into its primary. It retains the same two supplied pattern
families and the same single fitted D131 guide. This is a new-founder/history
replication conditional on that guide, not new ontology, unseen-family
generalization, biological evidence or a lossless-renewal claim.

Run `l20_fresh_founders_v1_attempt1`, tag `l20-fresh-founders-v1`.
Main identities78000–78007, four lives each, both A/B roles; disposable514240.
No main identity is generated during qualification. All eight blocks and
all lives/roles remain in the result. The old D132/D135 disposable bridge
is engineering-only and excluded from the result.

## New founders; fixed mechanism

Each new block draws its native tissue parameters/thresholds from the same
frozen public distribution. New tag/index/life/phase streams govern birth,
settling, teaching, initial reading/writing, descendant lives, and shuffles.
Matched conditions share their new phase streams as common random numbers;
they do not receive RNG state through the carrier.

Use the D132 acquisition recipe: native theta projected to norm.3, jittered
birth,120 settling steps, two1000-step acquisitions with the instructed
role pattern held at1.2, shared teaching noise across roles. Fresh300-step
initial readers provide F0-writer starts. Generate translated and aligned
1000-step F0 writers with the unchanged rules. Retain both, but only the
translated F0 record starts the primary, copy and ordinary controls.
The aligned F0 alternative is unused: no favorable F0 selection.

Both serial arms start from the EXACT same newly written translated
`f_written_fields[role,0]` record. Each G1–G3 descendant starts V as0.2
Gaussian, EMA=R=V, independently of the previous body. Read300 steps with
writing/reference gain off; erase incoming theta; start the writer's theta
at zero; write1000 steps with rho.002, gain.2, sigma.3, lambda.001, norm.3.
Aligned versus translated applied theta is the only writer-rule difference.
The outgoing packet is unchanged `project(tanh(R_final), .3)`,2048 bytes,
and becomes that arm's next input. G4 is a fresh non-writing terminal reader.

Ordinary descendants receive only the packet and fixed public host
machinery: the4096-byte learned guide and frozen rulebook distribution.
No previous V/EMA/R/theta, optimizer/recurrent state, outcome, family label,
historical displacement or RNG state crosses the reset. Writing receives
only the current read-end body, not the incoming packet or guide.
The guide is neither inherited nor refitted:
SHA256 `59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c`.

## Full control panel

Per role: translated, aligned, copy, aligned_read_off, aligned_write_off,
aligned_wrong, aligned_lesion, aligned_rescue. Every ordinary read uses
the same frozen learned selector. Translated/copy use translated writing;
aligned and its interventions use aligned writing.

Copy disables latent writing and retains input bytes unchanged. Write-off
disables latent writing and emits zeros. Read-off disables the packet in
G1–G3 reads, not the terminal read. Wrong starts from the opposite role's
translated F0 record. Lesion and rescue shuffle own F0 identically; rescue
alone receives an additional intact2048-byte backup at G1 read step101.
Later writers/generations cannot access this backup. This is externally
assisted rescue, not autonomous reconstruction.

Terminal probes: all eight chain outputs plus aligned post-selector shuffle,
aligned pre-selector shuffle, ideal canonical and zero, per role. Pre/post
use the same permutation; post-shuffle is not reselected. Preserve exact
wrong/opposite-role, disabled-reader/writer, identical-G1, first-write-step
and rescue-prefix aliases. No old trajectory equality is imposed on main.

Per life: two founder acquisitions, two pre-readers, four F0 source writers,
48 renewal read/write paths (36 enabled rewrites),24 terminal readers,
68 selector decisions,27 aliases. Main totals64 acquisitions,64 pre-readers,
128 F0 source writers,1536 generation paths,1152 enabled rewrites,
768 terminal readers,2176 selectors and864 aliases. Replays are not extra n.

Save native/normalized theta, birth/settled states, both instructed
acquisitions, their packets, pre-readers, both source-writer traces and F0
records under twelve `f_` fields. The unprefixed `founder_packets` are the
translated F0 records entering G1, not the acquisition packets. Save all
generation/terminal inputs, routed/backup/outgoing bytes,512-score maps,
V/EMA/R/theta checkpoints, observers and nested founder/descendant metadata.
Read times0,1,100,101,300; writer0,1,300,1000; terminal0,1,100,300.
Founder acquisition checkpoints follow the unchanged frozen config.

## Same inference as D135

Primary: G4 qualified own-minus-alternative preference, aligned minus
translated, roles averaged within four lives within eight new blocks.
10000 whole-block percentile bootstrap draws, D140 tag. Qualified observer:
strict abs(V)>.2, denominator all256 cells. Sign-only, stages and individual
roles remain secondary. No absolute80% gate, exclusions, equivalence
margin, adjusted multiplicity or post-hoc sample extension.

Instrument requires distinct targets and both directional ideal-minus-zero
AND copy-minus-zero terminal lower95>0. Aligned content requires both
directional aligned-minus-zero lower95>0 and supported pre/post-shuffle
contrasts. A supported contrast has pooled lower95>0 and both role means>0.
Continuity: aligned-minus-read_off and aligned-minus-write_off supported at
G2,G3,G4. Interventions: supported terminal aligned-minus-wrong,
aligned-minus-lesion and rescue-minus-lesion.

Primary gain: pooled lower95>0 and both directional means>0; harm:
upper95<0 and both means<0. Labels, unchanged:
READOUT_NOT_QUALIFIED; ALIGNED_SERIAL_RENEWAL_ADVANTAGE (gain plus all
renewal controls); ALIGNED_GAIN_WITHOUT_RENEWAL_QUALIFICATION (gain only);
ALIGNED_SERIAL_HARM_DETECTED; SERIAL_ADDRESS_EFFECT_UNRESOLVED.
Unresolved is not equivalence or absence. Retain asymmetry and every failed
control. A positive primary does not imply aligned equals copy.

All228 original contrast rows retained across two observers/A/B/pooled.
Only pooled G4 aligned-minus-translated is primary; do not substitute B or
an intermediate generation. Report D135 alongside D140 descriptively,
without pooling or a new retrospective success criterion.

## Verification, provenance and resources

Independent checker restates founder physics, all readers/writers, routing,
packet lineage, resets, aliases, raw observers and whole-block inference.
Exact packet/sign/alias checks; state tolerance1e-10, scores/metrics1e-12.
Independent saved audit verifies hashes and recomputes observers/inference
without new dynamics; all main physics already replayed inside the run.
Disposable-only tests include a known-stream bridge: with explicit test
monkeypatches of context/RNG, newly generated F0 and renewal traces must
exactly recover saved D132/D135 disposable outputs. Main code exposes no
old-stream override and cannot load old founders. Test guide immutability,
no old-source access, order independence, fresh-process descendants/audits,
all founder/raw/metadata corruption, inference failures and resource guards.

Pin D139 COMPLETE
`c7561277660284007342d3a8b35433608e38523db2b33c79b67c55ab36dde655`,
its1013-input/19-output closure, manifest/status/hash index, completed review,
six new science files and final test XML. Expected1043 source/science pins,
1044 at freeze,1048 at main preparation including benchmark/freeze artifacts.
Old frozen code/reviews remain immutable; only D140 live review and six
trackers may change after freeze. No main futures before qualification.

All data/outputs/fixtures/logs/caches stay under
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation`; code/docs only here.
At most six CPUs0–5 and six workers, numerical threads1, bytecode disabled.
512MiB study allowance and4GiB free reserve. No automatic retry/successor.

Benchmark forecast16*full-disposable-life test seconds+60. Main conservative
forecast8*checked-block seconds+2*hash seconds+180; storage eight raw blocks
+benchmark bytes+32MiB. Forecast above600s requires detached new session,
stdin/dev/null and external log. After ACK, no process/log/status/output
polling until user advancement. A detached benchmark cannot launch main.

L20 stays STRESS_TESTED/MIXED pending interpretation. These sheet records
are2048-byte carriers, not the separate DoorKey64-byte germ.
