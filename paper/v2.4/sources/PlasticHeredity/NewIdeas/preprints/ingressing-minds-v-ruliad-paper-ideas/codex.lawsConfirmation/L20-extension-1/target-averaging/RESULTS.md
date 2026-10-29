# D157 — training on averaged reconstruction outcomes

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[D156 predecessor](../future-stability/RESULTS.md).

## Plain-language result

**Better training targets help prediction generally; they have not established
a dependable challenge advantage.** Learning from the mean of four saved
outcomes reduces average future MSE for all 12 observers at all three fixed
settings, compared with learning from the original single outcome on the
same founders. Reductions range from **2.011% to 21.148%**.

This helps starting-only and passive observation too. For the observer using
the mean of two passive diagnostic profiles, the reductions are
**16.357% / 10.730% / 3.578%** at settings .001 / .01 / .1.
Starting-only improves **15.454% / 9.903% / 2.011%**. These are relative
reductions in squared prediction error, not preference-point gains or
percentages of additional surviving tissue.

The small control-minus nudge remains an interesting but conditional lead.
With the two diagnostic profiles supplied separately, it beats matched passive
observation by **2.234% / 1.295% / 0.715%**, with favorable scores on every
individual repeat and every single-founder score omission. But it still loses
to starting-only and one-copy observation at .001 and .01. With the simpler
mean-profile encoding, its matched-passive advantage is only
**−0.008% / +0.222% / +0.203%**. Omitting founder90012's scores reverses both
positive mean-encoding results. Every founder remains in the reported result.

Thus there is a useful general prediction improvement and a narrow,
encoding-sensitive nudge lead—not confirmation that a challenge reveals
future survival better than strong passive alternatives. This is development
on previously observed founders, not fresh prospective evidence.

## Fixed comparison and information boundaries

Retained all 16 repeat-covered founders90000–90015, four lives and four
family/writer groups: **256 cases**, with one original and four saved future
outcomes each. Older D135/D140 founders have no matching four-repeat labels,
so none is added to any new fitting arm. Their earlier artifacts/results remain
unchanged. The present 15-founder training folds are not comparable to the old
31-founder folds as if only the training labels had changed.

Six training targets: original, future0, future1, future2, future3, and the
arithmetic mean of all four futures. All 12 observers receive all six arms and
the same three fixed regularization settings .001/.01/.1. No selection,
deployment fit, new feature, dose, diagnostic, simulation, lineage or founder.

Whole-founder cross-validation: train on the other15 founders, then predict
all16 cases of the excluded founder. All of that founder's original/repeat
outcomes are absent from fitting and preprocessing. Models remain the fixed
group-sensitive ridge class with four public-group intercepts, common plus
zero-sum group deviations, penalty ratio one, training-only standardization
and clipping to[-1,1]. Feature counts: starting7, one-copy13, separate-copy19,
mean-copy13. Public target family and writer condition remain available to all.

Mean-target training uses four outcome labels per training case instead of
one. That extra training information is equally available to every observer;
diagnostic-copy budgets are unchanged. Mean diagnostic inputs and mean outcome
labels are distinct operations, and are crossed rather than conflated here.

Saved **3,456 scientific fits and55,296 held-out forecasts**, including raw
unclipped predictions and fit records. The full panel retains990 observer
contrasts plus294 training-target contrasts: **1,284 total**. Both control
directions and both mean-control-loss conditions stay. A mean control loss
is an average of separate losses, not an ensemble forecast.

D141's unresolved prospective result and L20 STRESS_TESTED / MIXED are
unchanged. Existing apparatus/control artifacts remain pinned in the source
closure; their tissue dynamics were not rerun. There are no new confidence
intervals, p-values, equivalence claims or independent replications.

## General benefit of averaging training outcomes

Positive percentages below mean lower MSE against the four individual held-out
futures, averaged equally. Both candidate and reference use the same observer,
setting and whole-founder folds. Candidate training uses the four-future mean;
reference training uses the original single outcome.

| Observer | 0.001 | 0.01 | 0.1 |
|---|---|---|---|
| Starting only | +15.454% | +9.903% | +2.011% |
| One copy | +15.043% | +8.654% | +2.709% |
| Separate: passive | +16.362% | +8.341% | +5.314% |
| Separate: shuffle | +21.148% | +9.948% | +4.885% |
| Separate: attenuation | +20.516% | +5.708% | +3.766% |
| Separate: control + | +14.196% | +4.263% | +3.514% |
| Separate: control − | +18.245% | +8.910% | +5.281% |
| Mean: passive | +16.357% | +10.730% | +3.578% |
| Mean: shuffle | +18.768% | +11.907% | +3.810% |
| Mean: attenuation | +16.581% | +9.751% | +3.222% |
| Mean: control + | +14.913% | +9.041% | +3.226% |
| Mean: control − | +16.871% | +10.788% | +3.449% |

Original-outcome MSE also improves in all36 observer/setting combinations.
That does not make the original and repeated outcomes interchangeable, or
establish the causal source of earlier reversals.

Every three-of-four repeat score average remains favorable for these target
contrasts. Individual futures sometimes disagree; for example, mean-passive
at .1 loses to original-target training on future1 alone. Every single-founder
score omission remains favorable except starting-only at .1 when founder90010
is omitted (absolute MSE gain−0.000001306). Omissions are sensitivity summaries,
not refits, exclusions or confidence levels.

Against the **average loss of all four individually trained future-target
models**, rather than choosing a favorable single future:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---|---|---|
| Starting only | +13.581% | +7.271% | +2.460% |
| One copy | +18.415% | +10.092% | +3.873% |
| Separate: passive | +23.685% | +13.467% | +4.846% |
| Separate: shuffle | +25.630% | +15.120% | +5.698% |
| Separate: attenuation | +24.945% | +13.887% | +4.717% |
| Separate: control + | +22.279% | +12.820% | +4.794% |
| Separate: control − | +24.373% | +13.510% | +4.884% |
| Mean: passive | +20.234% | +10.984% | +3.869% |
| Mean: shuffle | +19.012% | +10.897% | +4.267% |
| Mean: attenuation | +21.078% | +11.173% | +3.838% |
| Mean: control + | +20.121% | +10.825% | +3.923% |
| Mean: control − | +20.427% | +11.158% | +3.904% |

All these aggregate gains and all their individual-repeat, repeat-omission and
founder-score-omission gains are positive. The crucial qualification is that
most of this second comparison has a built-in averaging benefit, as below.
It is not an independent discovery of challenge-specific information.

## Linearity: do not mistake arithmetic for a new mechanism

At fixed inputs, preprocessing and penalty, ridge coefficients/intercepts
are linear in the training labels. Independently verified:

    fit(mean of four labels) = mean of the four fitted coefficient vectors
    raw mean-target forecast = mean of the four single-target raw forecasts

Maximum coefficient/intercept residual:2.90601e−14.
Maximum raw-forecast residual:9.21485e−15.

If clipping does not intervene, for any scored outcome y:

    mean_j (prediction_j − y)^2 − (mean_j prediction_j − y)^2
      = mean_j (prediction_j − mean_j prediction_j)^2

Consequently, lower loss than the average single-target-model loss is largely
an arithmetic consequence of averaging. It does not by itself show that the
challenge learned anything extra, identify noise as the causal source of past
failure, or prove a benefit on new founders.

Only **one of55,296** forecasts clipped: separate attenuation trained on future1
at .001. No mean-target forecast clipped. For that observer/setting, the
maximum difference between the mean-target forecast and the mean of the
already clipped single-target forecasts is0.027573522 (2.75735 preference
points). Everywhere else it is numerical roundoff. No additional ensemble
was scored or substituted into the registered panel.

Also verified, case by case:

    mean_r (prediction − future_r)^2
      = (prediction − mean_future)^2 + within-case future variance

The pooled finite-sample variance remains0.004140891134738922, divisor four.
It cancels from paired MSE gains. It is neither a known population variance
nor a proven irreducible prediction limit. The mean of four futures remains
an imperfect estimate of a case's expected continuation.

## Does challenge add anything after equal training?

All following observers use **mean-target training**. Each challenged
observer is compared with passive observation using its own encoding.

| Candidate / matched passive | 0.001 | 0.01 | 0.1 |
|---|---|---|---|
| Separate: shuffle | +2.337% | +0.421% | -1.053% |
| Separate: attenuation | -1.294% | -1.574% | -1.547% |
| Separate: control + | -1.975% | -2.509% | -1.697% |
| Separate: control − | +2.234% | +1.295% | +0.715% |
| Separate: mean control loss | +0.129% | -0.607% | -0.491% |
| Mean: shuffle | +0.768% | -0.569% | -1.153% |
| Mean: attenuation | -0.725% | -1.048% | -1.018% |
| Mean: control + | -0.800% | -1.077% | -0.559% |
| Mean: control − | -0.008% | +0.222% | +0.203% |
| Mean: mean control loss | -0.404% | -0.428% | -0.178% |

Attenuation and control+ worsen future MSE at every setting in both encodings.
Shuffle's signs depend on setting and encoding; no setting is selected to
make it win. Mean control loss does not yield a consistent advantage.

Control− with separate inputs has the most consistent matched-passive lead in
this panel. Its scores remain positive across all four repeats and all16
single-founder score omissions at each setting. Much of its group-level gain
is in aligned B; it is not uniformly favorable in every group (aligned A is
negative at .01 and .1).

That lead shrinks sharply with mean-profile inputs. At .01, omitting future0
changes its MSE gain to−0.000000977. At .01/.1, omitting founder90012's scores
changes gains to−0.000008083/−0.000007788. At .001 the aggregate is already
slightly unfavorable, not evidence of equivalence. All founders/futures stay.

The complete fixed focal comparisons keep the cheaper baselines prominent.
“Positive repeats” scores each future alone; “positive repeat omissions”
averages the remaining three individual-future losses; “positive founder
omissions” drops one founder's scores from the four-future aggregate.
**These omissions do not remove that founder from other folds' training.**

| Setting | Candidate / reference | Original | Four-future average | Positive repeats | Positive repeat omissions | Positive founder omissions |
|---|---|---|---|---|---|---|
| 0.001 | Mean: passive / Separate: passive | -0.596% | +3.412% | 4/4 | 4/4 | 16/16 |
| 0.001 | Mean: passive / One copy | -9.683% | -1.489% | 2/4 | 0/4 | 0/16 |
| 0.001 | Mean: passive / Starting only | -4.393% | -2.587% | 2/4 | 0/4 | 0/16 |
| 0.001 | Separate: control − / Separate: passive | +3.148% | +2.234% | 4/4 | 4/4 | 16/16 |
| 0.001 | Separate: control − / One copy | -5.601% | -2.727% | 1/4 | 0/4 | 0/16 |
| 0.001 | Separate: control − / Starting only | -0.508% | -3.838% | 2/4 | 0/4 | 0/16 |
| 0.001 | Mean: control − / Mean: passive | +1.014% | -0.008% | 1/4 | 3/4 | 6/16 |
| 0.01 | Mean: passive / Separate: passive | +2.681% | +2.995% | 4/4 | 4/4 | 16/16 |
| 0.01 | Mean: passive / One copy | -3.393% | +0.705% | 3/4 | 4/4 | 16/16 |
| 0.01 | Mean: passive / Starting only | +1.500% | +0.924% | 2/4 | 4/4 | 14/16 |
| 0.01 | Separate: control − / Separate: passive | +2.112% | +1.295% | 4/4 | 4/4 | 16/16 |
| 0.01 | Separate: control − / One copy | -3.998% | -1.036% | 2/4 | 1/4 | 1/16 |
| 0.01 | Separate: control − / Starting only | +0.923% | -0.812% | 2/4 | 2/4 | 2/16 |
| 0.01 | Mean: control − / Mean: passive | +1.106% | +0.222% | 3/4 | 3/4 | 15/16 |
| 0.1 | Mean: passive / Separate: passive | +1.902% | +0.467% | 3/4 | 4/4 | 16/16 |
| 0.1 | Mean: passive / One copy | +1.961% | +1.515% | 4/4 | 4/4 | 16/16 |
| 0.1 | Mean: passive / Starting only | +8.526% | +4.306% | 4/4 | 4/4 | 16/16 |
| 0.1 | Separate: control − / Separate: passive | +1.366% | +0.715% | 4/4 | 4/4 | 16/16 |
| 0.1 | Separate: control − / One copy | +1.426% | +1.760% | 4/4 | 4/4 | 16/16 |
| 0.1 | Separate: control − / Starting only | +8.027% | +4.545% | 4/4 | 4/4 | 16/16 |
| 0.1 | Mean: control − / Mean: passive | +0.651% | +0.203% | 3/4 | 4/4 | 15/16 |

Mean-passive beats separate-passive on average future MSE at all settings,
with favorable results under every repeat and founder-score omission. It
does not beat one-copy or starting-only at .001. At .01 its edge over starting
is sensitive to founder/repeat scoring; at .1 its edges over starting and
one-copy remain favorable across every individual repeat and score omission.

This is not a reason to select .1 after inspecting the results. Starting-only
at .001 still has lower absolute future MSE than mean-passive at .1. The full
setting panel, not a favorable within-setting ranking, is the evidence.

## Absolute errors and complete training-target panel

All values below are MSE in squared fractional preference units; lower is
better. Columns refer to what labels trained the model. The scored outcome is
always the same average loss against all four held-out futures. No single
training repeat or setting is selected.

| Setting | Observer | Train original | Train future 0 | Train future 1 | Train future 2 | Train future 3 | Train future mean |
|---|---|---|---|---|---|---|---|
| 0.001 | Starting only | 0.007703476 | 0.006814801 | 0.008505213 | 0.007431513 | 0.007394402 | 0.006512956 |
| 0.001 | One copy | 0.007749071 | 0.007223755 | 0.008944682 | 0.008162717 | 0.007946336 | 0.006583402 |
| 0.001 | Separate: passive | 0.008270753 | 0.007747765 | 0.011708844 | 0.008527495 | 0.008273489 | 0.006917453 |
| 0.001 | Separate: shuffle | 0.008567748 | 0.008152831 | 0.009872487 | 0.008723303 | 0.009587810 | 0.006755819 |
| 0.001 | Separate: attenuation | 0.008815524 | 0.007946095 | 0.012169250 | 0.008560407 | 0.008666989 | 0.007006938 |
| 0.001 | Separate: control + | 0.008221137 | 0.008118632 | 0.010889169 | 0.008620480 | 0.008676340 | 0.007054102 |
| 0.001 | Separate: control − | 0.008272192 | 0.007642992 | 0.011518508 | 0.008439933 | 0.008168407 | 0.006762944 |
| 0.001 | Mean: passive | 0.007988078 | 0.007340020 | 0.010042583 | 0.008131931 | 0.007990445 | 0.006681433 |
| 0.001 | Mean: shuffle | 0.008161980 | 0.007687771 | 0.008888932 | 0.007982610 | 0.008186878 | 0.006630148 |
| 0.001 | Mean: attenuation | 0.008067619 | 0.007396082 | 0.010470481 | 0.008186906 | 0.008055764 | 0.006729898 |
| 0.001 | Mean: control + | 0.007915278 | 0.007483770 | 0.009989172 | 0.008212710 | 0.008039584 | 0.006734867 |
| 0.001 | Mean: control − | 0.008038013 | 0.007373357 | 0.010053537 | 0.008180130 | 0.007981999 | 0.006681954 |
| 0.01 | Starting only | 0.007246610 | 0.006699535 | 0.007329255 | 0.007210606 | 0.006924075 | 0.006528954 |
| 0.01 | One copy | 0.007131690 | 0.006791252 | 0.007446807 | 0.007635276 | 0.007109705 | 0.006514522 |
| 0.01 | Separate: passive | 0.007275164 | 0.007205081 | 0.008515782 | 0.007823339 | 0.007280352 | 0.006668324 |
| 0.01 | Separate: shuffle | 0.007373780 | 0.007319188 | 0.007740831 | 0.008166261 | 0.008066106 | 0.006640245 |
| 0.01 | Separate: attenuation | 0.007183282 | 0.007356223 | 0.008788880 | 0.007919264 | 0.007397915 | 0.006773291 |
| 0.01 | Separate: control + | 0.007140015 | 0.007481399 | 0.008391883 | 0.007964937 | 0.007525270 | 0.006835645 |
| 0.01 | Separate: control − | 0.007225829 | 0.007100987 | 0.008471461 | 0.007690430 | 0.007177454 | 0.006581996 |
| 0.01 | Mean: passive | 0.007246092 | 0.006910346 | 0.007745897 | 0.007340095 | 0.007070815 | 0.006468595 |
| 0.01 | Mean: shuffle | 0.007384759 | 0.007114610 | 0.007371324 | 0.007408108 | 0.007309912 | 0.006505433 |
| 0.01 | Mean: attenuation | 0.007242600 | 0.006996026 | 0.007887886 | 0.007439552 | 0.007110847 | 0.006536379 |
| 0.01 | Mean: control + | 0.007188144 | 0.007056910 | 0.007741207 | 0.007409992 | 0.007119843 | 0.006538280 |
| 0.01 | Mean: control − | 0.007234696 | 0.006897117 | 0.007753334 | 0.007351996 | 0.007057004 | 0.006454239 |
| 0.1 | Starting only | 0.007266041 | 0.007169008 | 0.007252125 | 0.007462683 | 0.007314131 | 0.007119920 |
| 0.1 | One copy | 0.007110768 | 0.007026555 | 0.007241744 | 0.007360452 | 0.007158485 | 0.006918103 |
| 0.1 | Separate: passive | 0.007229418 | 0.007106361 | 0.007270038 | 0.007330029 | 0.007068974 | 0.006845247 |
| 0.1 | Separate: shuffle | 0.007272562 | 0.007234927 | 0.007303900 | 0.007498513 | 0.007303668 | 0.006917299 |
| 0.1 | Separate: attenuation | 0.007223166 | 0.007222138 | 0.007301223 | 0.007474786 | 0.007182983 | 0.006951130 |
| 0.1 | Separate: control + | 0.007214974 | 0.007255006 | 0.007322941 | 0.007480608 | 0.007189311 | 0.006961445 |
| 0.1 | Separate: control − | 0.007175259 | 0.007048071 | 0.007240770 | 0.007287918 | 0.007004555 | 0.006796332 |
| 0.1 | Mean: passive | 0.007066132 | 0.007015342 | 0.007102832 | 0.007186049 | 0.007045897 | 0.006813313 |
| 0.1 | Mean: shuffle | 0.007164856 | 0.007191314 | 0.007129777 | 0.007296058 | 0.007178860 | 0.006891841 |
| 0.1 | Mean: attenuation | 0.007111809 | 0.007100192 | 0.007139402 | 0.007275871 | 0.007113930 | 0.006882647 |
| 0.1 | Mean: control + | 0.007079798 | 0.007087538 | 0.007117258 | 0.007239515 | 0.007080426 | 0.006851424 |
| 0.1 | Mean: control − | 0.007042318 | 0.006998606 | 0.007098974 | 0.007178027 | 0.007026996 | 0.006799448 |

Under mean-target training, original-outcome MSE is:

| Observer | 0.001 | 0.01 | 0.1 |
|---|---|---|---|
| Starting only | 0.006471015 | 0.006375931 | 0.006839276 |
| One copy | 0.006158928 | 0.006074211 | 0.006381320 |
| Separate: passive | 0.006715291 | 0.006453351 | 0.006377450 |
| Separate: shuffle | 0.006709497 | 0.006570983 | 0.006490306 |
| Separate: attenuation | 0.006407758 | 0.006251638 | 0.006374554 |
| Separate: control + | 0.006375928 | 0.006212044 | 0.006333758 |
| Separate: control − | 0.006503888 | 0.006317063 | 0.006290316 |
| Mean: passive | 0.006755282 | 0.006280317 | 0.006256152 |
| Mean: shuffle | 0.006770094 | 0.006399812 | 0.006385751 |
| Mean: attenuation | 0.006686134 | 0.006269847 | 0.006311586 |
| Mean: control + | 0.006620999 | 0.006232577 | 0.006264670 |
| Mean: control − | 0.006686808 | 0.006210878 | 0.006215452 |

MSE against the four-future mean is obtained by subtracting the same
0.004140891134738922 from each future-MSE entry. Absolute paired MSE
differences therefore agree across these two outcome summaries; relative
percentages need not.

To put error size into preference-point units, here are the starting,
one-copy and mean-passive baselines under mean-target training:

| Setting | Observer | Future MAE (points) | Future RMSE (points) | Signed error (points) |
|---|---|---|---|---|
| 0.001 | Starting only | 5.0098 | 8.0703 | 0.0155 |
| 0.001 | One copy | 4.8223 | 8.1138 | 0.0437 |
| 0.001 | Mean: passive | 4.8802 | 8.1740 | 0.0521 |
| 0.01 | Starting only | 5.0493 | 8.0802 | -0.0175 |
| 0.01 | One copy | 4.8706 | 8.0713 | -0.0066 |
| 0.01 | Mean: passive | 4.8361 | 8.0428 | -0.0074 |
| 0.1 | Starting only | 5.4182 | 8.4380 | -0.1194 |
| 0.1 | One copy | 5.1885 | 8.3175 | -0.1121 |
| 0.1 | Mean: passive | 5.1334 | 8.2543 | -0.1038 |

Small pooled signed errors do not imply accurate individual forecasts.
All groups, founder scores, individual repeats, original/future/mean-target
MAE/RMSE/bias and every contrast remain in summary.json. All signed,
absolute and squared case errors are in case_errors.npz (108 arrays).
Original and repeated outcomes are paired case measurements, not independent
founder replications.

## Qualification, freeze, execution and fresh audit

All **62 qualification tests passed in41.21seconds**, with no failures/skips.
Tests cover independent group-coordinate SVD fits, every target and observer,
held-out label/feature isolation, target isolation, linearity and clipping,
constant/rank-deficient data, group permutation, adverse fit/summary/error
corruption, source identity, saved roundtrip and resource/detachment guards.

Freeze16:38:48.389755 UTC pins2,142 inputs, including D156's complete transitive
closure, fresh audit and result report. No new actual-case fits preceded it.
Full synthetic comparison plus independent saved checks took12.496736seconds;
hashing10.178485seconds. Frozen main forecast165.350443seconds; projected
storage301,613,840bytes, below512MiB allowance with4GiB free reserve.

Main manifest16:40:32.729041 UTC; COMPLETE16:41:00.867464 UTC.
Main28.138445seconds excluding preflight; **58,392,445bytes (55.687375MiB)**
output payload. Benchmark (~56MiB) and qualification fixtures (~20MiB) are
retained separately on the external disk. One numerical worker, threads one,
affinity CPUs0–5. Attached execution was below the600second detach threshold.

Fresh saved-output audit completed16:41:43.726419 UTC in24.985531seconds:
**2,150 input hashes, eight indexed outputs, all3,456 fits,1,284 contrasts,
55,296 forecasts and108 case-error arrays pass**. The audit independently
recomputes numerical fits/checks; it does not rerun tissue dynamics or refit old
reference studies. Scientific fit counts above exclude qualification,
benchmark and verification computations. No retry or automatic successor.

External root:

    /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/

Run/output basename:

    l20_extension1_target_averaging_dev_v1_attempt1

Artifacts: runs/<basename>/MANIFEST.json and COMPLETE.json;
outputs/<basename>/dataset.npz, predictions.npz, raw_predictions.npz, fits.json,
case_errors.npz, summary.json, verification.json, input_hashes.sha256 and
output_hashes.sha256. Freeze and benchmark receipts are in tmp/; qualification
XML and fresh audit are in logs/. Code/docs only in the workspace.

| Artifact | SHA256 |
|---|---|
| Freeze | 8629ba093f51ef382922b1c556e6209ccb74889bc451ef2cd3b85bcd6b0708f3 |
| Manifest | 95554597dce270ffbbdea6e84a239647baac0e1dc1f0878f0fd02c9357c2bef5 |
| COMPLETE | 47af756037fe868f90e93858fd8d127e339d6d2e2e537ffaa9489f3870e6a913 |
| Summary | d16cff89d2f826a2355c7f582afcdcdaf7badd83ef337ae45133bc8cacb7299d |
| Verification | 7f0463d38cc9378e29b5451258966b8025ef75f32d1692a0f2595f2f41dae7f3 |
| Output hash index | a67735e12eab9abffbd629ab6ab47a751548b7e152ad2e4ed871182801e9b098 |
| Fresh saved audit | 1e5b1ea708da3ddb0f278982564da4ec8072de652cedb2bf14e1759c44f67cd9 |

## Interpretation and next bounded proposal

This extends the external observer's ability to forecast an acquired record's
continuation through the existing three replacements. It does not change the
record/writer/guide, demonstrate autonomous repair, complete shape preservation,
a biological genome mechanism, or upgrade the original L20 verdict.

The narrow surviving lead is the control− result's dependence on encoding
and founder composition. A useful next development check would be a
**whole-founder training-influence audit** of the fixed mean-target arm:
remove each founder in turn, refit whole-founder out-of-fold predictions on
the remaining founders, and retain every deletion panel for all12 observers
and all three settings. Compare full-data and refitted panels, with unchanged
challenges, both controls and starting/one-copy baselines.

Unlike the score omissions already reported, this would also remove each
founder's influence on the other models' training. It is not a proposal to
discard90012, pick a favorable deletion or tune the challenge. Existing
full-cohort results remain primary development records. Register/qualify/freeze
and benchmark that scope before fitting; no new simulation is required.
**Proposal only—not launched.** Any eventual confirmation needs untouched
founders and frozen prediction rules; these development passes cannot turn
D141's unresolved result into a positive prospective test.

