# TT022: serial durability of body-derived capture

15 October 2026. Authorized after TT021's completed confirmation and closeout.
This is a bounded development experiment on exposed starting records. TT021
showed a strong one-read capture benefit, a useful held-snapshot comparator,
a matched-writer gain, and no confirmed informative-record harm above two points.
Those results informed this design. No TT022 serial outcome may be generated
before FREEZE.json binds the protocol, sources, baselines, qualification,
benchmark and resource admission. No new population confirmation is claimed.

## Enrollment and policies

Take TT021's first four identities, 21000000–21000003, all sixteen message/replica
positions and both common and informative (residual) record families. Selection
uses identity order, not success. Baseline packet bytes are copied with their
original checksum bindings. All 64 starting positions per family remain, with
four stochastic futures each: 256 chains per family and policy. There are only
four population blocks. The 64 starting positions are not 64 independent blocks.
Excluded qualification and benchmark packets come from TT021's disposable
603210/603211 runs; they never enter the scientific panel.

Seven policies are fixed. Each starts from the corresponding TT021 stage-zero
outgoing packet, so the main serial comparison asks whether the already obtained
benefit survives policy continuation. It does not isolate only the later rule.

| Policy | Starting packet | Rule after each subsequent body develops and is injured |
| --- | --- | --- |
| ordinary | Ordinary own-body live repair | Zero starting memory, live writer |
| capture | Captured own-body live repair | Capture the current injured body, update memory and write live |
| held | Captured own-body held snapshot | Capture the current injured body and hold that snapshot for this repair |
| fixed | Captured own-body fixed reading | Capture and update memory; read the incoming packet throughout repair |
| average | Captured own-body matched average | Average the fixed-reader body including its birth observation; inherit the average writer's packet |
| capture_once | Same starting packet as capture | Disable all later writing; preserve the initial captured packet |
| unchanged | Original common or informative input | Disable all later writing; preserve the original packet |

The last two controls still undergo body development, injury and ordinary
zero-memory repair with the writer disabled. Their packet bytes must remain
unchanged. There are no rescue calls, outcome-dependent interventions, stopping,
replacement, exclusions or tuning. Every chain continues after failure.

## One replacement cycle

Restore the previous outgoing packet into a fresh body using the unchanged
TT021 theta-only reader: centered birth noise with scale .2, zero R, fresh ema,
1,000 updates, fixed theta, no writing or memory feedback. Score the developed
body offline. No ancestral body, captured snapshot, label or teacher crosses.

Next retain one randomly selected spatial half of that developed body, fill the
other half at the native resting level, and add the original copy-jitter law.
Reset ema and R to zero; for capture/held/fixed/average set R to exactly this
injured V0, including fresh fill. Apply the relevant unchanged physical writer
for 1,000 updates. The held snapshot is newly captured each cycle, not a protected
ancestral body carried across cycles. Ordinary/capture/held read evolving theta;
fixed/average read the incoming theta. The average includes V0 and makes 1,000
writes without a birth write. Save body performance after repair separately.

Only the resulting 256 finite float64 theta values per record (2,048 bytes)
enter the next body. The first injury is already represented in TT021's imported
stage-zero packet. Subsequent cycles do not re-average paired parental records
or inject further record damage: they inherit their own actual packet. Thus
this tests full body replacement and repeated half-body injury under this
specified channel, not a recurring common-record erasure intervention.

Run eight such cycles. After cycle eight, assay the final packet in one additional
fresh recipient, with no repair or writing and a separate terminal environment.
This terminal recipient never supplies an intermediate body or a new inherited
record. Identical tissue parameters and the original four-message task remain
supplied apparatus. All native physical rates, writer rate .001, normalization
.3 and binary64 operation order remain unchanged.

## Randomness and information boundary

The address is the compact JSON list
`["TT022_serial_capture_v1", tissue, future, generation, phase]`, with phases
`develop`, `fission`, `repair`, `terminal`. SHA-256's first sixteen bytes, little
endian, become a nonnegative integer used in the original phase-specific RNG
factories. Futures are 0–3, replacement generations 1–8; terminal uses generation
8 with its distinct phase. Tissue parameters retain the original tissue identity;
the address changes only the stochastic environment. Fresh-reader birth and
forcing also retain their separate native subphase keys.

Policies and record family are absent from the address, so corresponding branches
share realized challenges. Replicas occupy distinct vector draws. Noise remains
coupled across intended messages as in TT021; this is not independent-message
robustness. Different futures, generations and phases use distinct initialized
pseudorandom streams. Check equal paired draws, distinct future/generation draws,
native RNG digests and every address, not just hash uniqueness.

Offline codebooks score outputs but are excluded from the repair context. The
fresh-reader API accepts only packet bytes as inherited information. Independent
reference physics replay every development, repair and terminal trajectory.
Independently reconstruct injury masks and jitter and verify every inherited
packet, memory reset, held snapshot and unchanged control. Native checkpoints
at 0, 1 and 1,000 must match exactly; conventional averaging retains absolute
2e-12, scalar projections 2e-13 and tie detection 1e-12, all with zero relative
tolerance. Failed checks remain failures; tolerances never change after them.

## Endpoints and interpretation

The primary descriptive contrast is common-record terminal recognition under
capture minus ordinary repair, averaged first over four futures and sixteen
positions per block and then equally over four blocks. Report both arms and all
four block differences. Keep the original fractional credit for tied maxima.
Do not label a four-block descriptive result a prospective confirmation.

Prespecify capture minus held, capture minus capture_once, capture minus
unchanged, fixed minus average and capture minus average in each record family,
along with capture minus ordinary in the informative family. Retain all message
strata, individual improvements/harms/ties and all seven policies. No significance
gate, population confidence claim or sample extension is attached to this pilot.
Four futures per record give coarse conditional estimates, not precise capacity.

Separate endpoints are the fraction of chains with uniquely correct body
recognition at every development endpoint, and at every post-repair endpoint,
over cycles 1–8. Ties count as failure for these uninterrupted binary endpoints.
Save per-generation fractional recognition as well as both uninterrupted flags.
Terminal success is never substituted for uninterrupted body performance.
Baseline packet reliability in the same terminal environment is visible in the
capture_once and unchanged controls. All starting packets and raw trajectories
remain retained irrespective of results.

Fixed and average use equal observation schedules, write counts and physical
reading rules. Their realized body streams can diverge after different packets
have been inherited. The serial comparison therefore compares policies, not
the isolated writer effect from TT021's matched one-read experiment. The average
implementation computes an unused native writer as a checked sidecar; timing and
work counts disclose that overhead. No optimal scheduling or matched-compute
claim is made. Protected snapshots and repeated external scheduling remain
resources supplied by the experiment.

## Qualification and execution

Qualify on excluded miniature packets: independent dynamics and scoring,
cross-cycle packet routing, counterfactual controls, corruption rejection,
randomness pairing/separation and exact serial/two-worker agreement. Then time
two excluded full-size blocks, two futures, two cycles at 100 updates per phase.
Conservatively scale elapsed time by 10*2*2*4=160 for the full four-block,
four-future, eight-cycle panel; add 120 seconds for final saved checks. Do not
discount fixed or terminal costs. Scale benchmark bytes by 2*2*4 with 50%
headroom. Admission requires forecast below 16 hours, deadline 3*forecast+600
below 48 hours, estimated output below four GiB, and six GiB initially free.

Use two single-thread workers on two admitted CPUs at nice 10 within the shared
12-CPU ceiling. Check free space before each block/future; maintain two GiB
free reserve and a four-GiB output bound. Preserve every failure and stop without
automatic retry or replacement. Runs above ten minutes detach with stdin
disconnected, unique log, PID, frozen inputs and RUNNING/COMPLETE/FAILED receipts.
Collect one startup acknowledgment, then leave the study unpolled until the user
asks. No automatic successor, sample extension or external message.

The resulting evidence is exposed-starting-record serial development. It does
not establish fresh-population replication, precision of individual capacity,
autonomy, robustness beyond this noise law, biological transfer or a unique
theoretical law. A subsequent confirmation would require a separately frozen
design and genuinely unexposed starting cases.
