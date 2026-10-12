# P32 results: a short early RNA pause supports retention and onward transmission

Completed **October 12, 2026 at 09:18:13 UTC**, after **3 days 21 hours
33 minutes 49 seconds** from job launch. All **856 cases / 7352 integrations /
525505 independent checks** pass. All three stage gates and the final
independent audit pass. P32 qualifies its complete registered timing panel
and fresh-recipient transmission assays.

Protocol: [P32 registration](PAPER_CONVERGED_PAUSE_BOUNDARY_PROTOCOL.md).
Predecessor: [P31 focused numerical repair](PAPER_DELAYED_PAUSE_CONVERGENCE_RESULTS.md).

## Main finding

An immediate five-unit pause in RNA communication, the shortest tested,
supports retention of E through the registered cell replacements and
transmission of E to fresh recipients in every tested variant. The recipients
remain stably E during both isolated holds after donor removal. Continuous
RNA communication fails both retention and transmission. These are model
time units and controlled computational comparisons.

Every tested immediate duration of 5, 10, 15, 20, 25 and 100 succeeds.
For a pause lasting 100 units, starts at 0, 5 and 10 succeed; starts at 15,
20 and 25 fail. Blocking RNA transport throughout the 300-unit first
challenge also fails. Both written and ordinary histories show the same
categorical pattern under both incoming sequences, both archived source
bundles, and both numerical settings.

P32 therefore supports a timing-dependent route to retention and onward
state transfer in this model. It establishes no written-history advantage.
It extends the earlier successful pause examples into the complete
registered short-duration and delayed-start panel.

## Complete retention and transmission table

Each retention denominator contains 16 variants: two histories × two fixed
incoming sequences × two source bundles × two numerical settings. Each
readout column tests all 16 resulting parents, including retention failures.
These variants are not independent biological replicates.

| First-challenge schedule | Parents retaining E | Open readout transmits E | RNA-blocked readout transmits E | Boundary-cut readout transmits E |
| --- | ---: | ---: | ---: | ---: |
| Continuous RNA communication | 0/16 | 0/16 | 0/16 | 0/16 |
| Immediate pause, duration 5 | 16/16 | 16/16 | 0/16 | 0/16 |
| Immediate pause, duration 10 | 16/16 | 16/16 | 0/16 | 0/16 |
| Immediate pause, duration 15 | 16/16 | 16/16 | 0/16 | 0/16 |
| Immediate pause, duration 20 | 16/16 | 16/16 | 0/16 | 0/16 |
| Immediate pause, duration 25 | 16/16 | 16/16 | 0/16 | 0/16 |
| Immediate pause, duration 100 | 16/16 | 16/16 | 0/16 | 0/16 |
| Pause starts at 5, duration 100 | 16/16 | 16/16 | 0/16 | 0/16 |
| Pause starts at 10, duration 100 | 16/16 | 16/16 | 0/16 | 0/16 |
| Pause starts at 15, duration 100 | 0/16 | 0/16 | 0/16 | 0/16 |
| Pause starts at 20, duration 100 | 0/16 | 0/16 | 0/16 | 0/16 |
| Pause starts at 25, duration 100 | 0/16 | 0/16 | 0/16 | 0/16 |
| RNA blocked throughout 300-unit challenge | 0/16 | 0/16 | 0/16 | 0/16 |

Across the eight successful schedules, **128/128** parents retain E and
**128/128** open readouts transmit it. All **256** matched RNA-blocked or
boundary-cut readouts prevent transmission. The other **80** parents fail
retention, and all **240** readouts from those parents fail transmission.
The 24 reference readouts also pass their registered controls.

All original carriers are replaced. No parent passes the stricter
every-renewal-window E criterion. The sampled tracked cell loses E and later
recovers under immediate 5–25-unit pauses and 100-unit pauses beginning at
5 or 10. An immediate 100-unit pause preserves its sampled E during the
first challenge. Full blockade also preserves that cell's initial sampled
E but fails the later retention and transmission tests. These distinctions
separate temporary resistance, recovery and long-term retention.

## Meaning of a positive readout

The parent trio undergoes the fixed replacement schedule and two isolated
10000-unit holds. Its actual final state is then contacted with three fresh
M recipients for 20000 units; all six cells evolve. The actual recipients
are isolated for two further 10000-unit holds after donor removal.

Retention and transmission require all three relevant cells to satisfy the
native E endpoint and 95%-of-final-quarter stability rule in both isolated
holds. Readouts use no donor clamp, recipient reset or added timing pause.
RNA blockade removes the registered RNA transport coefficient; boundary
cut removes the donor–recipient edges. Their negative results support
dependence on those routes in the tested readout. They do not identify a
unique molecular memory carrier.

## Numerical and source agreement

All **428 q32/q64 comparisons** and **214 source-bundle comparisons at q64**
pass. Every registered phase inventory, complete outcome, phase-end
classification and renewal diagnostic agrees as required. The normalized
primary-sample error is abs(x−y)/max(1,abs(x),abs(y)); the limit is 0.01.

| Stage | Numerical pairs | Largest numerical error | Source pairs | Largest source error |
| --- | ---: | ---: | ---: | ---: |
| controls | 12 | 0.0000216949 | 6 | 0.0000268535 |
| renewal | 104 | 0.0008655716 | 52 | 0.0012162757 |
| onward | 312 | 0.0000400191 | 156 | 0.0000258912 |

All **32 exact P31 parent replays**, **80 retention anchors**, **240 onward
anchors**, **24 reference controls**, and **576 shared schedule-prefix
comparisons** pass. The start-15 diagnostic contains 41 saved third-cell
samples in each of 16 parent cases. All eight target numerical pairs and
four target source pairs agree on sampled labels and transition brackets.
Closeout independently reconstructed all 16 diagnostics from the raw arrays.

This qualifies the new P32 panel. P27 and P30 keep their original failed
gates. P32 tests agreement at two refined settings across the full grid;
it does not establish full-grid 16/32/64 contraction or regenerate the
complete ancestral trajectory.

## Verification and preservation

Both complete **60-test software suites** passed: 985.260 seconds before
launch and 922.449 seconds against the frozen source. Stage totals are
24/72, 232/5480 and 856/7352 cases/integrations. The last stage has 525492
checks; the final independent audit adds 13.

All **27 completion-preservation checks** pass. The
[completion review](storage/p32-completion-integrity-20261012.json) freshly
verified **301 execution sources, 46068 original input paths, 856 results,
7352 raw phases and 416 assembly files**. It checked saved audit consistency,
raw outcome tables, sampled classifier neighborhoods, absent registered
processes and the released lock. No simulation or full mathematical audit
was rerun during closeout.

Job: /mnt/workspaces/levin-cancer-gj-exploration/p32-converged-pause-boundary/jobs/p32-20261008T114402Z-v1pxbdt1.
Run: /mnt/workspaces/levin-cancer-gj-exploration/p32-converged-pause-boundary/runs/p32-20261008T115952Z-6hfxhzzo.
Native BITSEY revision: b2cb370aaecbc8299f259bc4251d5396c81f19a6.

## Scope and remaining questions

Five is the smallest successful tested immediate duration, not an exact
minimum. Ten is the latest successful tested start for a 100-unit pause;
untested starts between 10 and 15 are unresolved. The successful short
duration grid does not imply success for every longer pause: the complete
300-unit blockade fails. Only the registered schedules are qualified.

The study introduces no new random draws or biological replicates. It does
not test a full start-by-duration factorial, autonomous reproduction, a
biological treatment effect, or a written-history advantage. Its retained
capacity/wipe evidence is inherited from earlier qualified work.

P32 is complete. No simulation remains running and no further study has
been launched. Finer timing boundaries, independent incoming sequences and
broader model generalization remain questions for separate registrations.
