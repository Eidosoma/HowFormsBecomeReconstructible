# D184 identical record pilot results

12 October 2026. The complete 64-record development pilot passed its apparatus
checks but did not recover the missing within-pair identities. Bodies changed
the outgoing records and continuous fresh-read scores; that source sensitivity
did not become useful correction in the hard identical-record condition.

The damaged-but-informative comparison improved on average, but conventional
body averaging achieved the same pooled recognition. No claim of a distinctive
live-feedback advantage follows. L22 remains STRESS_TESTED / MIXED.

## Complete panel

All four preselected exposed blocks 30056–30059, four messages and four
replicates remain: 64 records, 144 repair paths, 204 named fresh-read assays
and 160 unique assays. Named assays sharing exact packet bytes and read mode
reuse one physical assay; these are not extra independent observations.
Each record has four fresh-reader draws. The disposable benchmark is excluded.

The [pilot protocol](PILOT_V1.md), [execution contract](PANEL_EXECUTION_V1.md)
and [qualification](PANEL_QUALIFICATION.md) remain unchanged. There was no
selection by performance and no new repair threshold.

## Recognition and shape are different results

Recognition is the percentage of fresh-reader draws assigned to the intended
one of four messages. Preference is own recognition minus recognition of its
fixed partner. Shape correlation compares the outgoing record with its
original acquired parent record, not with the resulting fresh body.

| Incoming record and treatment | Recognition percent | Preference points | Record correlation with own parent |
| --- | ---: | ---: | ---: |
| Identical within pair, unchanged | 50.0000 | 0.0000 | 0.795862 |
| Identical, own body, live feedback | 50.0000 | 0.0000 | 0.740144 |
| Identical, partner body, live feedback | 50.0000 | 0.0000 | 0.736155 |
| Identical, scrambled own body | 50.0000 | 0.0000 | 0.737402 |
| Identical, body history erased | 50.0000 | 0.0000 | 0.718086 |
| Identical, own body, fixed reader | 50.0000 | 0.0000 | 0.746873 |
| Identical, own body, conventional averaging | 50.0000 | 0.0000 | 0.726984 |
| Damaged informative, unchanged | 83.9844 | 76.9531 | 0.300000 |
| Damaged informative, own body, live feedback | 87.8906 | 83.2031 | 0.474446 |
| Damaged informative, partner body | 84.7656 | 74.6094 | 0.463813 |
| Damaged informative, own body, fixed reader | 86.3281 | 80.4688 | 0.450969 |
| Damaged informative, conventional averaging | 87.8906 | 83.2031 | 0.484678 |

In the identical-record condition, the four intended-message recognition
rates are **0, 100, 100, 0 percent**, before and after every treatment listed
above, in every block. The pooled 50 percent is not a near-miss around an
arbitrary 80-percent threshold: the same two intended directions are never
recovered in these reads. Each within-pair shared input still contains useful
pair-level content; it is not a blank record or a four-way chance control.

Own-body live repair changes the terminal fresh-reader projection gap by
+0.008364 on average compared with the common input, but changes record
correlation by **−0.055718**. Correlation falls in all four blocks. Own versus
partner body changes projection by +0.016729 and correlation by +0.003990 on
average, with opposite signs across some blocks. Thus numerical body influence
is not equivalent to restoration of the intended missing content.

The informative-record recognition gain is **3.90625 percentage points**.
Block gains are −1.5625, +6.2500, +7.8125 and +3.1250 points: not all improve.
Live repair minus averaging is 0, 0, +1.5625 and −1.5625 points respectively.
Their equal pooled recognition does not mean identical record-by-record
outcomes. Averaging also has higher pooled own-parent record correlation.

The native ema=V comparison reaches 86.71875-percent recognition, versus
87.890625 percent in the zero-reset comparison. These initialization conditions
are kept separate, not presented as an exact replication of one another.

## Controls and verification

Intact parent records and supplied positive records reconstruct every message
at 100 percent in every block. Disabled reading gives 25 percent pooled over
balanced messages in every block; individual message rates need not be 25
percent. These apparatus controls remain outside any claim of body correction.

The completed run includes independent replay using the shared native physical
API, not an independently invented physics implementation. All native state
and fresh-read replay discrepancies are exactly zero. The largest conventional
averaging discrepancy is 5.7732e-15, below the fixed 2e-12 tolerance. All
1,156 exact alias checks pass and all source arrays match frozen D079/D183.

User-advanced saved-only review reverified the 420 frozen inputs, 649 outputs,
receipt links, exact file sets, source identities, mappings, all per-record
scalar scores, controls and the recomputed complete descriptive summary.
The later [D185 diagnostic](TRACE_V1.md) binds these same original identities
without changing the pilot or generating new outcomes.

## Cost and immutable receipts

The panel completed at **15:01:10.159591 UTC**, 385.190685 seconds after its
manifest timestamp: about 6m25s on four single-thread workers. There are no
remaining D184 workers. Main outputs occupy **248,891,282 bytes** (237.36 MiB);
the stage including qualification and benchmark occupied about 606.5 MiB before
the final completion receipt. Peak worker RSS was about 120 MiB each. This is
measured cost, distinct from the prelaunch 12m10s engineering allowance.

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-pilot-v1`.
Run: `l22_active_form_pilot_v1_panel_attempt1`.
Complete arm/message/contrast/control tables: `outputs/<run>/SUMMARY.json`;
all individual record scores: `outputs/<run>/tissue_<index>/records.json`.

- Freeze SHA-256: `fad700044abf1a15bbad1558a8cc6d41c853ef597ecd8eb1dad660f7aaa153cf`.
- Manifest SHA-256: `b378a1d7f330686388e95befe29b957610b42e0390d14a4b21a4a6207f619f7e`.
- Completion SHA-256: `7b5851bb7c971dc9f74cc79a40eeb446751a5c286ee15731a2fb5741a02281eb`.
- Summary SHA-256: `25247d59e030e41de14196a3a54849e8b4dbc50a818bdd20651b97759937c7dd`.

This small, already-exposed development panel neither proves impossibility
under other conditions nor qualifies a fresh confirmation or three-boundary
renewal. The approved next step is retrospective localization in its saved
trajectories, with no tuning or new simulation.
