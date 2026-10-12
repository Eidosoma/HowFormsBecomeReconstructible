# D155 — fixed mean-compression results

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[one-copy baseline](../one-copy-baseline/RESULTS.md).

## Plain-language result

A simpler way of feeding the same observations to the predictor helps on the
original outcomes, but does **not** establish an advantage from challenging
a copy.

Averaging the two undisturbed endpoint profiles lowers original-outcome MSE
by **9.091%, 7.381% and 4.514%** versus keeping them as separate inputs, at the
three fixed settings. This mean-passive predictor also beats the one-copy
baseline by **5.506%, 5.412% and 3.541%**, and starting-only by **3.195%, 5.291%
and 7.405%**. These original-outcome gains have the same sign in each cohort
and after every single-block score omission.

The earlier control-minus lead nearly disappears when both observers use
this encoding: its original MSE reduction over mean-passive is **−0.089%,
+0.095% and −0.037%**. Every setting's sign can reverse after one block's
scores are omitted. That is a small, unstable observed gap, not equivalence.

The saved repeated futures give a less favorable result. Mean-passive has
**0.970%, 0.251% and 0.168% higher MSE** than separate-passive. Across all
five observers and all three settings, mean encoding improves original MSE
in 15/15 comparisons but worsens repeated-future MSE in 14/15. The reversal
also occurs within the same 16 founders; it is not only a cohort-mix effect.

So D154's one-copy advantage was specific to the tested encoding and learner.
D155 supports taking representation seriously, not diagnosing overfitting,
choosing a winning penalty, or claiming a reliable challenge benefit.

All 32 observed blocks / 512 cases remain. Former held-out founders are now
DEVELOPMENT. No new tissue dynamics, diagnostics, outcomes or founders.
D141's unresolved prospective comparison and L20 STRESS_TESTED / MIXED stay.

## What changed

Each of five observers now gets the unchanged seven starting features plus
the componentwise arithmetic mean of its two allowed six-feature diagnostic
endpoint profiles: **13 inputs**, instead of 19. The mean is computed in raw
units before training-only standardization. Passive uses U0 and U1; shuffle
uses U0 and C1; attenuation and both residual controls use U0 and their
respective already saved edited-copy endpoint.

This averages measurements, not bodies, records, predictions or outcomes.
There is no extra diagnostic copy, physical reconstruction or weighted mean.
Between-copy differences are deliberately discarded.

The group-sensitive ridge model, common/deviation penalty ratio one, four
unpenalized group intercepts, training-only transformations and clipping to
[-1,1] are unchanged. Each of .001/.01/.1 is applied to every new observer.
Each of 32 whole-founder folds trains on the other 31 blocks. There is no
inner selection, future-label training or deployment fit.

All **480 new fits / 7,680 predictions** are independently reconstructed using
group-coordinate SVD. Seven fixed reference observers and six old nested
references are reused exactly, without refitting. The original 111 contrasts
remain unchanged and 90 specified contrasts are added: **201 total**.
Previous apparatus controls are hash-pinned outside the prediction contest;
they were not simulated again.

The mean and separate encodings have the same two-observation budget. Mean
and one-copy have the same feature count but different observation budgets.
Equal dimension or numeric alpha does not imply equal effective complexity.
This comparison changes information, dimension and penalty geometry together;
it does not isolate the cause of the change in performance.

## Original outcomes: absolute error

Lower is better. The target remains terminal own-minus-alternative preference
after three replacements. MSE uses squared fractional preference units.
These are not survival probabilities or complete-shape-preservation scores.

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006698674 | 0.006643819 | 0.007093564 |
| One undisturbed copy | 0.006862477 | 0.006652330 | 0.006809440 |
| Separate: Passive | 0.007133111 | 0.006793766 | 0.006878771 |
| Separate: Shuffle | 0.007254431 | 0.006862676 | 0.006941898 |
| Separate: Attenuation | 0.007644903 | 0.007013843 | 0.006922637 |
| Separate: Control + | 0.007326047 | 0.006893307 | 0.006897118 |
| Separate: Control − | 0.007072939 | 0.006729890 | 0.006860192 |
| Mean: Passive | 0.006484654 | 0.006292311 | 0.006568284 |
| Mean: Shuffle | 0.006644290 | 0.006399393 | 0.006617982 |
| Mean: Attenuation | 0.006763666 | 0.006456715 | 0.006632992 |
| Mean: Control + | 0.006562792 | 0.006335611 | 0.006581713 |
| Mean: Control − | 0.006490435 | 0.006286352 | 0.006570733 |

All five mean-encoded observers beat their separate-copy versions on original
MSE at every setting. Mean-passive beats both information baselines at every
setting. Shuffle, attenuation and control + still lose to mean-passive.
The control-minus difference is tiny and changes direction across settings.

New observers' absolute errors, in preference points:

| Setting | Mean observer | Original MAE | Original RMSE | Future MAE | Future RMSE |
|---|---|---:|---:|---:|---:|
| 0.001 | Passive | 4.7755 | 8.0527 | 4.9695 | 8.3672 |
| 0.001 | Shuffle | 4.8985 | 8.1513 | 5.1224 | 8.5323 |
| 0.001 | Attenuation | 4.8452 | 8.2242 | 5.0179 | 8.3960 |
| 0.001 | Control + | 4.7785 | 8.1011 | 4.9387 | 8.3126 |
| 0.001 | Control − | 4.7719 | 8.0563 | 4.9706 | 8.3917 |
| 0.01 | Passive | 4.7174 | 7.9324 | 4.8277 | 8.0546 |
| 0.01 | Shuffle | 4.8429 | 7.9996 | 4.9311 | 8.1557 |
| 0.01 | Attenuation | 4.7745 | 8.0354 | 4.8512 | 8.0621 |
| 0.01 | Control + | 4.7185 | 7.9597 | 4.8060 | 8.0303 |
| 0.01 | Control − | 4.7127 | 7.9287 | 4.8283 | 8.0501 |
| 0.1 | Passive | 4.9344 | 8.1045 | 4.9616 | 8.1566 |
| 0.1 | Shuffle | 5.0187 | 8.1351 | 5.0606 | 8.2402 |
| 0.1 | Attenuation | 4.9812 | 8.1443 | 4.9796 | 8.1774 |
| 0.1 | Control + | 4.9269 | 8.1128 | 4.9591 | 8.1562 |
| 0.1 | Control − | 4.9342 | 8.1060 | 4.9605 | 8.1485 |

Future columns are secondary, on the same saved repeated futures described
below. Reference MAE/RMSE remain exact in the embedded D154/D153 summaries
and their reports; none were refitted. Every model's group, cohort, block
and case-level errors are saved in the external summary and case arrays.

## All 90 new paired contrasts

Positive = candidate reduces MSE; negative = worse. Entries are
100 * (reference MSE − candidate MSE) / reference MSE. Three columns
times 30 declared pairs give all 90 new contrasts. No setting or control
direction was selected after seeing these results.

Original-outcome MSE reduction:

| Candidate / reference | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Mean: Passive / Separate: Passive | +9.091% | +7.381% | +4.514% |
| Mean: Shuffle / Separate: Shuffle | +8.411% | +6.751% | +4.666% |
| Mean: Attenuation / Separate: Attenuation | +11.527% | +7.943% | +4.184% |
| Mean: Control + / Separate: Control + | +10.418% | +8.090% | +4.573% |
| Mean: Control − / Separate: Control − | +8.236% | +6.591% | +4.219% |
| Mean: Passive / One copy | +5.506% | +5.412% | +3.541% |
| Mean: Passive / Starting only | +3.195% | +5.291% | +7.405% |
| Mean: Shuffle / One copy | +3.179% | +3.802% | +2.812% |
| Mean: Shuffle / Starting only | +0.812% | +3.679% | +6.704% |
| Mean: Attenuation / One copy | +1.440% | +2.941% | +2.591% |
| Mean: Attenuation / Starting only | −0.970% | +2.816% | +6.493% |
| Mean: Control + / One copy | +4.367% | +4.761% | +3.344% |
| Mean: Control + / Starting only | +2.028% | +4.639% | +7.216% |
| Mean: Control − / One copy | +5.421% | +5.501% | +3.506% |
| Mean: Control − / Starting only | +3.109% | +5.380% | +7.370% |
| Mean: Shuffle / Mean: Passive | −2.462% | −1.702% | −0.757% |
| Mean: Attenuation / Mean: Passive | −4.303% | −2.613% | −0.985% |
| Mean: Attenuation / Mean: Shuffle | −1.797% | −0.896% | −0.227% |
| Mean: Attenuation / Mean: Control + | −3.061% | −1.911% | −0.779% |
| Mean: Attenuation / Mean: Control − | −4.210% | −2.710% | −0.948% |
| Mean: Control + / Mean: Passive | −1.205% | −0.688% | −0.204% |
| Mean: Control + / Mean: Shuffle | +1.227% | +0.997% | +0.548% |
| Mean: Control − / Mean: Passive | −0.089% | +0.095% | −0.037% |
| Mean: Control − / Mean: Shuffle | +2.316% | +1.766% | +0.714% |
| Mean: Control − / Mean: Control + | +1.103% | +0.777% | +0.167% |
| Mean: mean control loss / Mean: Passive | −0.647% | −0.297% | −0.121% |
| Mean: mean control loss / One copy | +4.894% | +5.131% | +3.425% |
| Mean: mean control loss / Starting only | +2.569% | +5.010% | +7.293% |
| Mean: mean control loss / Separate: mean control loss | +9.346% | +7.349% | +4.397% |
| Mean: Attenuation / Mean: mean control loss | −3.632% | −2.309% | −0.863% |

“Mean control loss” averages the separate losses of control + and control −.
It is **not** an ensemble forecast or its loss. The averaged control loss
is worse than mean-passive at every setting on original outcomes.

The external summary embeds all 111 previous contrasts without alteration,
including starting-only, one-copy, separate-copy and nested references.
This report does not relabel any old comparison as fresh evidence.

## Cohort, founder and group checks

Original-outcome MSE reduction for the focal comparisons:

| Setting | Candidate / reference | D135 (8 blocks) | D140 (8) | Former test (16) |
|---|---|---:|---:|---:|
| 0.001 | Mean: Passive / Separate: Passive | +18.139% | +3.211% | +3.761% |
| 0.001 | Mean: Passive / One copy | +5.446% | +5.719% | +5.472% |
| 0.001 | Mean: Passive / Starting only | +4.675% | +3.759% | +1.938% |
| 0.001 | Mean: Control − / Mean: Passive | −0.161% | +0.668% | −0.304% |
| 0.01 | Mean: Passive / Separate: Passive | +10.565% | +4.029% | +6.114% |
| 0.01 | Mean: Passive / One copy | +2.845% | +7.599% | +6.429% |
| 0.01 | Mean: Passive / Starting only | +4.817% | +5.868% | +5.424% |
| 0.01 | Mean: Control − / Mean: Passive | −0.223% | +0.299% | +0.256% |
| 0.1 | Mean: Passive / Separate: Passive | +3.680% | +2.584% | +5.874% |
| 0.1 | Mean: Passive / One copy | +1.082% | +5.768% | +4.415% |
| 0.1 | Mean: Passive / Starting only | +5.392% | +5.939% | +9.418% |
| 0.1 | Mean: Control − / Mean: Passive | −0.258% | −0.218% | +0.201% |

Mean-passive's gains over separate-passive, one-copy and starting-only each
remain positive under all 32 single-block SCORE omissions at every setting.
The gains do not require dropping a founder. This is not a confidence interval:
score omission changes a saved average, not the fitted models or membership
of the reported study.

For control − versus mean-passive, the omitted-score average is positive
in 4/32, 30/32 and 7/32 omissions at .001/.01/.1. Each full-panel sign can
reverse. The mean control loss remains worse than mean-passive under every
original single-block score omission, at all three settings.

The improvements are not uniform across groups. Mean-passive beats one-copy
on original MSE in all four public family/writer groups at all settings.
Against separate-passive it improves all groups at .001/.01, but worsens
aligned B at .1. Against starting-only it still worsens ordinary B at the
two weaker settings, despite improving the aggregate.

Ordinary B accounts for much of the mean-versus-separate original gain,
but that same group worsens on saved-future MSE at all three settings.
Control − versus mean-passive worsens ordinary B and improves aligned B
on original MSE at every setting. No group has been filtered, reweighted,
or promoted to a new primary endpoint.

## Saved repeated futures: the important limit

There are four previously saved D142 futures per case on the 16 former-test
founder blocks: **1,024 outcomes**, not 1,024 independent founders. They are
secondary scoring labels only and never enter an outer fit. All four stay.

Individual-future MSE:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Starting only | 0.006934551 | 0.006542999 | 0.006932775 |
| One undisturbed copy | 0.006791235 | 0.006405755 | 0.006671629 |
| Separate: Passive | 0.006933798 | 0.006471422 | 0.006641863 |
| Separate: Shuffle | 0.007097728 | 0.006531997 | 0.006763317 |
| Separate: Attenuation | 0.007144561 | 0.006466938 | 0.006638654 |
| Separate: Control + | 0.006759403 | 0.006388323 | 0.006643264 |
| Separate: Control − | 0.006953838 | 0.006442691 | 0.006612408 |
| Mean: Passive | 0.007001032 | 0.006487682 | 0.006653043 |
| Mean: Shuffle | 0.007279984 | 0.006651484 | 0.006790027 |
| Mean: Attenuation | 0.007049290 | 0.006499778 | 0.006687043 |
| Mean: Control + | 0.006909992 | 0.006448634 | 0.006652310 |
| Mean: Control − | 0.007042102 | 0.006480429 | 0.006639730 |

The same 90 contrast definitions on the secondary outcomes:

| Candidate / reference | 0.001 | 0.01 | 0.1 |
|---|---:|---:|---:|
| Mean: Passive / Separate: Passive | −0.970% | −0.251% | −0.168% |
| Mean: Shuffle / Separate: Shuffle | −2.568% | −1.829% | −0.395% |
| Mean: Attenuation / Separate: Attenuation | +1.333% | −0.508% | −0.729% |
| Mean: Control + / Separate: Control + | −2.228% | −0.944% | −0.136% |
| Mean: Control − / Separate: Control − | −1.269% | −0.586% | −0.413% |
| Mean: Passive / One copy | −3.089% | −1.279% | +0.279% |
| Mean: Passive / Starting only | −0.959% | +0.845% | +4.035% |
| Mean: Shuffle / One copy | −7.197% | −3.836% | −1.775% |
| Mean: Shuffle / Starting only | −4.981% | −1.658% | +2.059% |
| Mean: Attenuation / One copy | −3.800% | −1.468% | −0.231% |
| Mean: Attenuation / Starting only | −1.655% | +0.661% | +3.544% |
| Mean: Control + / One copy | −1.749% | −0.669% | +0.290% |
| Mean: Control + / Starting only | +0.354% | +1.442% | +4.045% |
| Mean: Control − / One copy | −3.694% | −1.166% | +0.478% |
| Mean: Control − / Starting only | −1.551% | +0.956% | +4.227% |
| Mean: Shuffle / Mean: Passive | −3.984% | −2.525% | −2.059% |
| Mean: Attenuation / Mean: Passive | −0.689% | −0.186% | −0.511% |
| Mean: Attenuation / Mean: Shuffle | +3.169% | +2.281% | +1.517% |
| Mean: Attenuation / Mean: Control + | −2.016% | −0.793% | −0.522% |
| Mean: Attenuation / Mean: Control − | −0.102% | −0.299% | −0.713% |
| Mean: Control + / Mean: Passive | +1.300% | +0.602% | +0.011% |
| Mean: Control + / Mean: Shuffle | +5.082% | +3.050% | +2.028% |
| Mean: Control − / Mean: Passive | −0.587% | +0.112% | +0.200% |
| Mean: Control − / Mean: Shuffle | +3.268% | +2.572% | +2.213% |
| Mean: Control − / Mean: Control + | −1.912% | −0.493% | +0.189% |
| Mean: mean control loss / Mean: Passive | +0.357% | +0.357% | +0.106% |
| Mean: mean control loss / One copy | −2.721% | −0.918% | +0.384% |
| Mean: mean control loss / Starting only | −0.598% | +1.199% | +4.136% |
| Mean: mean control loss / Separate: mean control loss | −1.742% | −0.764% | −0.274% |
| Mean: Attenuation / Mean: mean control loss | −1.050% | −0.545% | −0.617% |

Mean-passive versus one-copy is −3.089%, −1.279%, +0.279%; versus starting-only,
−0.959%, +0.845%, +4.035%. Thus the simpler passive encoding does not beat the
cheaper baselines consistently across settings and outcome realizations.

For mean-passive versus separate-passive, original MSE improves on the same
16 former-test blocks by 3.761%, 6.114%, 5.874%, while repeated-future MSE
worsens by 0.970%, 0.251%, 0.168%. Comparing different cohorts cannot by itself
explain this reversal. This is not a new independent prospective test or
proof that stochastic variation is the sole cause.

The repeated-future mean-target MSE is also retained, with independent
variance and paired-loss identity checks. For a fixed forecast, individual-
future MSE equals squared error against the mean future plus within-case
future variance. The variance term is shared across observers, so changing
between these two squared-error targets does not change their absolute
paired MSE differences. Relative percentages do change with the denominator.

The mean control loss beats mean-passive on repeated-future MSE by
0.357%, 0.357%, 0.106%, and remains positive under all 16 secondary score
omissions. This contrasts with its original-outcome losses; it does not
establish a prospective challenge advantage or select a direction.

## Qualification, freeze, cost and audit

- First-version qualification: **60 tests passed**, none failed or skipped,
  in 186.98 seconds. Synthetic data only before the freeze.
- Freeze: **2026-09-20 15:22:36.626947 UTC**, 2,085 pinned inputs.
- Full synthetic benchmark, including independent checks and saved roundtrip:
  21.860960 seconds; input hashing 9.567763 seconds. Main forecast
  182.857444 seconds, projected storage 109,954,076 bytes.
- Main manifest prepared **15:24:37.484454 UTC**; COMPLETE
  **15:25:12.458186 UTC**. Main execution **34.973754 seconds** excluding
  preflight; **11,263,430 bytes / 10.741644 MiB** output payload externally.
- Fresh saved-output audit: **15:26:11.893066 UTC**, **36.194554 seconds**.
  All **2,094 input hashes / nine indexed outputs**, all new SVD fits,
  exact source arrays/reference predictions/summary, 201 contrasts and
  90 signed/absolute/squared case-error arrays pass.
- One numerical worker, numerical threads one, affinity CPUs 0–5. Runs were
  under the ten-minute detachment threshold. No retry, automatic successor,
  new dynamics or new prospective cohort.

The main payload size is not total storage including synthetic qualification,
benchmark files, logs and earlier studies. All such numerical artifacts,
fixtures and caches stay under /mnt/bioIce1; code and documents only here.

## Provenance

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`

Run: `l20_extension1_mean_compression_dev_v1_attempt1`.

Artifacts beneath that root:

- `tmp/l20_extension1_mean_compression_dev_v1_attempt1_freeze.json`
- `runs/l20_extension1_mean_compression_dev_v1_attempt1/MANIFEST.json`
- `runs/l20_extension1_mean_compression_dev_v1_attempt1/COMPLETE.json`
- `outputs/l20_extension1_mean_compression_dev_v1_attempt1/`:
  dataset, new predictions/fits, exact fixed/nested reference predictions,
  case errors, complete summary, verification and hash indexes.
- `logs/l20_extension1_mean_compression_dev_v1_attempt1_saved_audit_v1.json`
- `logs/d155_qualification_v1.xml`

SHA-256 identities:

| Artifact | SHA-256 |
|---|---|
| Freeze | `0d8cbcf68795ee5f2f2b381d5ab9d6844681961b2c8083a4ed1dfe20ca0214c1` |
| Manifest | `bf59987cba9b44f9e83a9570cdc58a4c0d41d0f61248c86921eb13504b2a8a65` |
| COMPLETE | `97ddacef96f392827bced34e09ded0ed502477f68193ea2ea6389cb54cc7b95c` |
| Summary | `f640f1f24635b2e5074c50332455db0bc6f2644606d92fbde2f9b54b3954fa61` |
| Verification | `2d7a939d2367478c695d09cbd8df3260bd8bae51f912f1319d9cccc8a810b8fa` |
| Output index | `0c45a353a602465a80cc5966839bac64e96742b6ffcf0d1a0f6dbe8796b44556` |
| Fresh audit | `153a32e6b9687aa25891f5c8290d7874c5750100af5cdc28ac103f450b1f0ff9` |

## What this changes, and the next proposal

D154 does not justify a general “one copy is enough” conclusion: averaging
the two profiles reverses its original-outcome ordering. Conversely D155
does not establish that averaging is generally best: its repeated-future
result is mixed, and it discards information that another learner might use.

There is still no dependable advantage specifically from the original
shuffle, targeted attenuation or a selected residual-control direction.
This remains post-result development, not a replacement for D141's registered
prospective comparison. L20 stays STRESS_TESTED / MIXED.

**Proposed next, not launched:** a fixed-prediction review of the original-
versus-repeated-future reversal on the same 16 founder blocks. Keep every
setting, observer, block and all four futures; inspect paired case/block
errors, group contributions and sensitivity to which saved future is scored.
Separate forecast bias against the mean future from variability among
futures. Do not refit, choose a favorable repeat, exclude a founder or call
the repeats independent founder replications. This would diagnose the next
uncertainty before proposing another encoding or a fresh prospective test.
