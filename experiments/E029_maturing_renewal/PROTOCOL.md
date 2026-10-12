# E029 — preserve strong connections, continue refreshing weak repairs

Prospective policy test authorized on 23 September 2026. E028 showed that weak
precursors could support useful rewriting within full-rebuilding histories;
E027's exact-zero infill policy failed. This experiment tests a new serial
policy on fresh cases. It does not pool earlier histories or tune thresholds.

## Fixed policy and cohort

32 fresh blocks **25000–25031**, four founders and four recipient lineages per
founder: 128 founders, 512 lineages. Disposable block **900029** is excluded.
All blocks, failures and score rows are retained. No outcome-dependent stops,
screening, replacement cases, candidate selection or automatic successor.

At every renewal, physically unavailable edges are zero. Available incoming
weights with **absolute value strictly greater than 0.5** are copied exactly.
Every other available coordinate, including exactly ±0.5, tiny nonzero values
and exact zeros, receives the immediate local activity capture. Strength is a
supplied proxy for maturity; 0.5 is motivated by E028's descriptive convention,
not an established biological or dynamical boundary. No alternative cutoff is
tested. Negative and positive values receive the same rule.

Each chain generates its own record/body history. The selector explicitly sees
the surviving incoming weights for copying and thresholding. Capture itself
uses only the present body: the unchanged tanh-product edge correlations,
averaged over opposing cues, followed by the unchanged 4096-byte float64 packet.
No ancestral masks, repair-age labels, donor packets or terminal outcomes enter
renewal. No additional metadata is transmitted.

The E024/E027 scientific timing and apparatus are unchanged: 16×16 periodic
body, three renewals, 24 independently resampled non-port cells removed at each
renewal birth, read 2048 steps including 256 settling steps, immediate capture,
128 holding steps, teaching 512/capture 128/observe 32, gain 2, dt 0.2,
noise 0.02, birth SD 0.05, writer beta 3 and strict margin >0.25.
Each generation uses the existing E022 semantic random streams. Birth, noise,
damage and terminal challenges are paired across compared chains.

Condition order is frozen:

1. `maturing`: new preserve-strong/refresh-weak policy.
2. `maturing_read_blocked`: incoming body reader zero; strong copying remains.
3. `strength_compensated`: unchanged normalized full rewriting.
4. `intact_renewed`: unchanged intact renewal with fixed-four body reader.
5. `protected_copy`: unchanged initial packet at each boundary.
6. `masked_copy`: initial packet with cumulative matched physical erasures.
7. `read_blocked`: unchanged full rewriting with incoming reader zero.
8. `write_blocked`: unchanged full rewriting with outgoing packet zero.
9. `selective`: E027 exact-zero infill, preserving every available nonzero.
10. `maturing_refresh_blocked`: normal incoming reading and strong copying;
    eligible weak coordinates emit zero instead of captured values. The body
    capture is still calculated and retained for auditing.

The eight active bodies are conditions 1,2,3,4,7,8,9,10; all except condition 4
use their own incident absolute-strength denominator. No drive is supplied at
zero strength. The four selectors are active positions 0,1,6,7, with cutoffs
0.5,0.5,0,0.5 and refreshing enabled except in the last.

## Endpoints and decisions

The initial packet and all chains after renewals one and three face both
fixed-four and normalized receivers, giving **42 terminal panels**. Each panel
includes intact, scattered-24 and square-3×3 injuries, both cues and the seven
unchanged arms: own, foreign, shuffled, erased, untrained, communication off
and source cut. Receiver denominators are computed after packet controls and
physical damage. Full cohort: **903168 terminal / 24576 body score rows**.

The single primary endpoint is own-packet **both-cue success after renewal 3,
scattered terminal injury, normalized receiver**. The paired new-policy minus
old `selective` effect must have a two-sided 95% whole-block bootstrap lower
bound **>0.10**. Separately, new policy minus full rebuilding on that endpoint
must have a lower bound **>−0.05**: a prospectively chosen five-percentage-point
noninferiority requirement. This is not an equivalence test. Superiority over
full rebuilding is not required.

All **14 additional qualifications** must also pass:

- New-policy normalized both-cue lower bound >0.75 for intact/scattered
  terminal injury at renewals 1 and 3 (four flags).
- New-policy normalized original 24 reliability/control gates at both
  horizons (two flags): own accuracy lower >0.75 separately for both rules
  and all three injuries, and own-minus-each-of-six-controls lower >0.10.
- Intact-renewal reference passes those 24 gates at both horizons and both
  receiving rules (four flags).
- New policy minus cumulative masked copying, primary endpoint, lower >0.10.
- New policy minus its reading-blocked control, primary endpoint, lower >0.
- New policy minus its refresh-blocked control, primary endpoint, lower >0.
- All 12 unchanged full-rebuilding reading/writing necessity gates: own
  accuracy versus full reading-/writing-blocked chains, lower >0.10, both
  horizons and all three injuries with the normalized receiver (one conjunction).

Intervals resample whole blocks 10000 times, seed namespace
`["E029","bootstrap","maturing"]`. Effects are paired within blocks. Report
all raw counts, block means, intervals, individual-rule outcomes, terminal
controls, receiver contrasts, generation changes and pre-capture body outcomes.
Other comparisons and additional gates use pointwise intervals. Report primary,
noninferiority, additional qualifications and their conjunction separately;
`MATURING_RENEWAL_QUALIFIED` requires all, otherwise
`MATURING_RENEWAL_NOT_ESTABLISHED`. Technical runs report `TECHNICAL_ONLY`
and withhold all four scientific decision flags.

## Evidence, validation and execution

Freeze 23 scientific inputs before any simulation: inherited production/audit
dependencies, E027 model for reference fixtures and the seven local scientific
files. Scientific files are immutable once fixtures run. Failures and input
snapshots are retained; corrections require a recorded new revision/attempt.

Retain source teaching states, all masks, incoming/erased/retained/outgoing
packets, selector masks, body end states, late-port traces and terminal arrays.
To fit current storage, retain every holding update as a separate SHA256 digest
for each active branch: contiguous little-endian float64 C-order body bytes,
digest array shape `(128,8,32)`, uint8. Dynamics and holding end states are
unchanged. Independent replay reconstructs and checks **every** holding digest,
along with every read/assay update and every score. Intermediate holding arrays
are reconstructible by replay but cannot be directly inspected from raw storage.
Holding occurs after capture and never changes outgoing packets.

Eight disposable checks cover exact cutoff and weak maturation, serial handoff
and unchanged E027 reference trajectories, both endpoint axes, activity-only
capture and explicit copying access, normalization and terminal replay, blocked
refresh/zero drive, rejection of a corrupted holding digest, and a complete
independent end-to-end fixture. Short fixture: R2, teach12/capture6/observe4,
read24/settle6/hold8, all three renewals and all 42 panels.

The excluded throughput benchmark uses R1, teaching/capture/observe and holding
at their full settings, but **read512/settle64**. It includes all three renewals,
eight bodies, 42 panels, audit and figures. This shorter-duration benchmark
estimates runtime and storage; it is not full-duration scientific validation.
Pre-benchmark forecast from the completed E027 full-duration R1 benchmark is
`1.5*(worker+audit)*(42/34)*((512+128)/(2048+128))+60` seconds. If >600 seconds,
detach; otherwise it may run in the foreground. No technical score changes the
scientific design or enables launching on scientific performance grounds.

After technical success, scientific runtime forecast is
`2.5*(benchmark_worker+benchmark_audit)*4_read_duration*4_recipients*ceil(32/workers)+90`.
Use at most eight workers and eight-CPU affinity, numerical threads one. Storage
forecast is `source_bytes*32+(benchmark_total_bytes-source_bytes)*4*32+1GiB`:
the teaching source has no recipient axis; remaining files conservatively scale
with lineages. The extra read duration does not enlarge fixed retained traces
or holding digests. Require that reserve before launch. Never delete old evidence
to make room. Every run gets immutable input snapshots and COMPLETE/FAILED
receipts; audit and figure provenance are checked separately.

Follow RUN_POLICY: forecast >600 seconds requires detached host execution,
stdin `/dev/null`, local logs, PID, bounded startup verification, durable status
and no automatic polling. No sign-mechanism, long-horizon, manuscript or next
experiment work is included in this run.
