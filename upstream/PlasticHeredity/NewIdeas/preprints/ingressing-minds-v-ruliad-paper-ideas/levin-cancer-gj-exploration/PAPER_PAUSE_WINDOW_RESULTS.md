# P26: a 25-unit early pause supports recovery and transmission

Completed **October 2, 2026 at 15:12:33 UTC**, **19 hours 35 minutes 1 second**
after launch, within the initial 14–22-hour estimate. All **396 cases / 2,628
integrations / 206,483 independent checks / 198 numerical pairs** meet the
technical requirements. Both software gates, verified historical evidence,
all three stage gates and the final independent audit pass. P26 is complete.

A pause beginning immediately supports final E retention and onward
transmission at all four tested durations: **25, 50, 75 and 100 model time
units**. Every tested delayed start of **25, 50, 75, 100, 150 or 200**, with
duration fixed at 100, fails both retention and transmission. Continuous
communication and a full 300-unit block also fail. Both incoming sequences,
both histories and both numerical resolutions agree.

The shortest successful tested pause permits temporary loss of E followed
by recovery. Longer successful pauses preserve sampled E during the first
challenge. Full blockade preserves the tracked cell's sampled E initially
but fails later renewal. Initial resistance, recovery and lasting transmission
therefore remain distinct outcomes.

## Registered grid and results

Use the unprepared all-before assembly, historical/17021 incoming sequences,
written/ordinary histories and two numerical resolutions. Five remaining
replacements give two total replacement cycles including the archived first
replacement. Only the timing of the one-time RNA pause changes between
schedule comparisons. There is no primary-state preparation or repeated pause.

Times below are relative to the first post-fork 300-unit challenge. A pause
blocks RNA transport on [start, start + duration). All later replacement
intervals have continuous open communication. A qualified chain requires
retained E in both parent isolation holds, positive open onward transmission,
negative RNA/cut readouts and qualified reference/anchor/capacity/wipe evidence.

| Condition | Start | Duration | Parents retaining E | Open readouts transmitting E | Tracked cell during first challenge |
|---|---:|---:|---:|---:|---|
| baseline | — | 0 | 0/8 | 0/8 | No E recovery by 300 |
| pause_0_25 | 0 | 25 | 8/8 | 8/8 | Sampled loss, then E recovery |
| pause_0_50 | 0 | 50 | 8/8 | 8/8 | Sampled E resistance |
| pause_0_75 | 0 | 75 | 8/8 | 8/8 | Sampled E resistance |
| pause_0_100 | 0 | 100 | 8/8 | 8/8 | Sampled E resistance |
| pause_25_100 | 25 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| pause_50_100 | 50 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| pause_75_100 | 75 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| pause_100_100 | 100 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| pause_150_100 | 150 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| pause_200_100 | 200 | 100 | 0/8 | 0/8 | No E recovery by 300 |
| full_block | 0 | 300 | 0/8 | 0/8 | Sampled E resistance |

Each row contains two histories × two sequences × two resolutions. These
related deterministic conditions are not independent biological replicates
or general success-rate estimates. Every parent receives every readout,
including failed parents. RNA-blocked and boundary-cut readouts each yield
**0/8** transmission positives in every row. Every successful row qualifies
as a pause-specific chain; every failed row fails retention and all readouts.

Across new parents, **32/96 retain E and 32/96 open readouts transmit E**.
Including the four positive archived reference readouts gives **36/100** open
positives. RNA blockade and boundary cuts each give **0/100** positives with
references included. Every positive open readout has all three recipients
stable E during contact and both isolated holds after donor removal. Every
negative readout has all three recipients stable M in all three phases.
Retaining donors end contact E even when RNA-blocked/cut recipients stay M;
failed donors end contact M.

## What the short pause does and does not preserve

The tracked cell is the archived first newcomer at column 0. The first
post-fork incoming cell is inserted at column 1 before this challenge; it is
a different cell. The common diagnostic samples times 0,15,...,300.

All eight `pause_0_25` parents show sampled M and later E recovery, and the
tracked cell is stable E in the final quarter of the first challenge. All
24 parents with durations 50/75/100 show E at every common first-challenge
sample. All eight full-block parents also show sampled E resistance and
first-challenge stability, yet fail final retention and onward transmission.
The remaining 56 parents, continuous-open or delayed-start, show M without
E recovery by 300.

All **96 parents replace every original carrier** and then undergo two
consecutive isolated 10000-unit holds. **None meets the stricter
every-renewal-window E criterion.** Final retention after replacement does
not imply uninterrupted E during the intervening renewal windows. Stability
requires the matching endpoint and at least 95% matching samples in the
final quarter; recipient transmission uses both isolated holds, with contact
stability reported separately.

## Tested bounds and interpretation

For each of the four history/sequence backgrounds, the registered boundary
summary is the same:

- Smallest successful **tested** duration with start zero: **25**.
- Latest successful **tested** start for a 100-unit pause: **0**.
- All tested durations 25–100 succeed at start zero; all tested starts 25–200
  fail for duration 100. These two sampled patterns have no reversals.
- The separate 300-unit full-block control fails. Success is therefore not
  globally monotone in pause duration across all tested durations.

Durations below 25 and starts strictly between 0 and 25 were not tested.
The findings do not establish an exact minimum duration, prove that every
positive delay fails, or locate a continuous-time boundary. The failed
300-unit block also leaves durations between 100 and 300 unresolved. No
monotonicity was assumed or fitted to fill these gaps.

P26 shows that a pause one quarter as long as P24's successful 100-unit pause
can still support the qualified chain in these two sequence backgrounds over
two cycles. P24's longer-cycle result for duration 100 does not establish
longer-cycle durability for duration 25. Both sequences were already studied;
there are no new random draws or biological replicates. Both histories agree,
providing no written-history advantage here.

The finite scheduled model comparisons do not establish autonomous
reproduction, a unique molecular memory carrier, or a biological treatment.
They suggest a follow-up focused on shorter immediate pauses and starts
between 0 and 25, with the recovery-versus-resistance distinction retained.
No follow-up protocol or simulation was registered or launched at closeout.

## Verification and numerical handling

[Executed protocol](PAPER_PAUSE_WINDOW_PROTOCOL.md). Every condition uses
twelve 25-unit first-challenge phases, with raw samples every 1.25 units and
maximum steps of 0.25/0.125 at the two resolutions. Actual state and identities
carry across segment boundaries. The common first-challenge diagnostic uses
the inherited 15-unit sample spacing; all raw samples are retained.

All **248 pairs with shared initial communication segments** agree exactly
over those segments, across every saved numerical array. All **16 retention
and 48 transmission anchors** reproduce the P24 baseline/0–100 outcomes in
both sequences, histories and resolutions. These anchors compare outcomes
across the changed discretization; they do not assert exact arrays between
P24's 100-unit and P26's 25-unit segments. The 12 reference readouts separately
replay their P25 numerical arrays exactly. All 198 registered coarse/fine
comparisons agree; different resolutions are not claimed to be byte-identical.

| Cumulative stage | Cases | Integrations | Numerical pairs |
|---|---:|---:|---:|
| Reference controls | 12 | 36 | 6 |
| Renewal | 108 | 1,764 | 54 |
| Onward transmission | 396 | 2,628 | 198 |

The prelaunch suite passed **43 tests in 655.903 seconds**; frozen verification
passed **43 in 653.058 seconds**. There were no invalid scientific cases or
retries. Verification, runner, audit and final exit codes are all zero.
Frozen software-log SHA-256:
`39af065ed48d9bc96cb7b6d37991ecc3a8b8685df99876b34352716994476a24`.

P25 and older completed mathematical/software evidence were verified through
pinned reports, logs and source/input hashes without repeating unchanged
historical mathematical audits. Every new trajectory was independently
reconstructed. Archived directory references remain references, not
independent backups. Executed code, configuration, draw book and protocol
remain frozen.

Job:
`/mnt/workspaces/levin-cancer-gj-exploration/p26-pause-window/jobs/p26-20261001T193708Z-gbmaqodx`.
Run:
`/mnt/workspaces/levin-cancer-gj-exploration/p26-pause-window/runs/p26-20261001T195350Z-agohmy4u`.

Final audit SHA-256:
`01240f9a94ec61a71ca84a3da89246fda22b2c58fae8f65d9e2e39516013711a`.

The [October 2 closeout](storage/p26-completion-integrity-20261002.json)
passes all **15 completion checks and ten provenance flags**. Fresh hashes
verify 396 result files, 2,628 raw phases, 192 assembly files, 249 execution
sources and 24,460 registered input paths, plus saved stage/audit/software
reports. No scientific integration or mathematical audit was repeated during
closeout. About **495.82 GiB remains externally and 65.34 GiB on the main
filesystem**, above the five-GiB reserve. The supervisor and audit child have
exited normally; no experiment is currently running.
