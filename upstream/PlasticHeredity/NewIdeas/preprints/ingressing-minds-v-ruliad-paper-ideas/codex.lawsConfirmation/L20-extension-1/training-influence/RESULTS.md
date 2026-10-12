# D158 — whole-founder training-influence audit

Completed and freshly audited **2026-09-20**.
[Fixed protocol](PROTOCOL_V1.md), [work log](WORKLOG.md),
[D157 training-target result](../target-averaging/RESULTS.md).

## Plain-language result

**The separate-reading minus-nudge lead survives removal of any single
founder from both training and scoring. The smaller mean-reading lead remains
fragile.** This strengthens one narrow development result, not the claim that
challenge is generally better than strong passive alternatives.

With the two diagnostic profiles supplied separately, control− beats matched
passive observation in all16 retraining-deletion panels at every setting.
Relative reductions in average four-future MSE range across deletions from
**0.823–3.816% / 0.545–2.024% / 0.212–1.026%**, at .001 / .01 / .1.
This is not just a single founder's contribution to the average score.

That statement does not extend to every future realization: some
individual-repeat scores disagree. The control also generally loses to
starting-only and one-copy baselines at .001/.01. No favorable setting is
selected to avoid those comparisons.

With averaged diagnostic profiles, the tiny control− advantage is favorable
in only8/16,15/16,15/16 retraining panels. At .01, score-only omission blamed
founder90012; refitting without90012 restores a small positive advantage,
while refitting without90010 reverses it. At .1, removal of90012 still reverses
the result. **A score contribution and training influence are different.**

Every founder stays in the full-cohort reference. Every deletion, repeat,
observer and setting is reported. These overlapping development panels are
not new independent replications or prospective confirmation. D141 remains
unresolved and L20 STRESS_TESTED / MIXED unchanged.

## What was changed, and what was held fixed

All16 original founders90000–90015, four lives/four family-writer groups:
256 cases with one original and four saved repeat futures each. Only the
fixed **future-mean training target** from D157 is used for new refits.
All12 observers and settings .001/.01/.1 stay. No new diagnostic, challenge,
feature, target family, guide, record, tissue dynamic, founder or outcome.

For each removed founder d, retain the other15 founders. For each of those
15 validation founders b, fit on the other14: neither d nor b can enter
fitting, group means, scaling or label offsets. Predict all16 cases of b.
The same group-sensitive ridge, common/deviation penalty ratio one,
training-only standardization and clipping to[-1,1] are retained.

This produces **8,640 new scientific fits and138,240 held-out forecasts**.
They are many forecasts of existing cases, not138,240 new biological samples.
The9,216 D157 mean-target reference forecasts are reused exactly; none of
those original models is refitted. Other D157 training arms and all earlier
apparatus controls remain pinned and unchanged.

Each setting has55 fixed observer-pair orientations. The full panel,
16 score-only deletion panels and16 retrained deletion panels retain
**5,445 observer-comparison records**. There are also672 direct refit-versus-
score-only training-effect records and165 full influence decompositions.
Both control directions, both mean-control-loss conditions and starting/one-copy
baselines stay. Mean control loss is an average of losses, not an ensemble.

## Separating composition from retraining

For each contrast, positive gain means reference MSE minus candidate MSE:

    G   = full-cohort gain using the original D157 forecasts
    S_d = gain after omitting founder d's scores, keeping those forecasts
    R_d = gain after removing d, refitting, and scoring the same remaining cases

    R_d − G = (S_d − G) + (R_d − S_d)
              score composition    training influence

This accounting holds for original, individual-future-average and mean-target
outcomes, each individual repeat, and every three-repeat score average.
The training term also equals the candidate's direct training-effect gain
minus the reference's direct training-effect gain. Both identities were
independently checked.

This is a controlled change to the predictor's training set, not an intervention
establishing a tissue mechanism. Removing training data changes sample size,
group centering/scaling, offsets and coefficients together. It does not show
that a founder is defective or ought to be excluded.

Concrete examples below use **×10⁻⁶ MSE** (squared fractional preference units),
not preference points:

| Comparison | Setting | Removed founder | Full G | Score-only S | Refit R | Training R−S |
|---|---|---|---:|---:|---:|---:|
| Mean control− / Mean passive | .01 | 90012 | +14.356 | −8.083 | +3.163 | +11.246 |
| Mean control− / Mean passive | .01 | 90010 | +14.356 | +8.942 | −5.126 | −14.069 |
| Mean control− / Mean passive | .1 | 90012 | +13.864 | −7.788 | −11.894 | −4.106 |
| Mean passive / Separate passive | .001 | 90014 | +236.020 | +69.850 | −64.641 | −134.491 |
| Mean passive / Separate passive | .1 | 90010 | +31.935 | +22.159 | −0.945 | −23.104 |

Thus a favorable score-only omission can turn unfavorable after refitting;
an unfavorable score-only omission can also recover. The .01 control− example
is not repaired by choosing which founder to exclude. All16 deletion panels
and the original full-cohort score stay.

## Focal comparisons, including cheaper observers

Full-cohort percentages reproduce D157's mean-target arm exactly. Deletion
counts score the average loss over all four futures. Ranges are observed
sensitivity ranges, **not confidence intervals**. Refit ranges use
×10⁻⁶ MSE; multiply by0.000001 for fractional-preference-squared units.

| Setting | Candidate / reference | Full-cohort MSE reduction | Positive score-only deletions | Positive refitted deletions | Refitted gain range (×10⁻⁶ MSE) |
|---|---|---|---|---|---|
| 0.001 | Separate: control − / Separate: passive | +2.234% | 16/16 | 16/16 | +57.315 to +244.105 |
| 0.001 | Mean: control − / Mean: passive | -0.008% | 6/16 | 8/16 | -33.544 to +51.795 |
| 0.001 | Mean: passive / Separate: passive | +3.412% | 16/16 | 15/16 | -64.641 to +439.653 |
| 0.001 | Mean: passive / One copy | -1.489% | 0/16 | 1/16 | -295.859 to +58.715 |
| 0.001 | Mean: passive / Starting only | -2.587% | 0/16 | 0/16 | -387.241 to -29.519 |
| 0.001 | Separate: control − / One copy | -2.727% | 0/16 | 1/16 | -501.860 to +22.937 |
| 0.001 | Separate: control − / Starting only | -3.838% | 0/16 | 0/16 | -593.242 to -29.397 |
| 0.01 | Separate: control − / Separate: passive | +1.295% | 16/16 | 16/16 | +36.891 to +124.816 |
| 0.01 | Mean: control − / Mean: passive | +0.222% | 15/16 | 15/16 | -5.126 to +46.519 |
| 0.01 | Mean: passive / Separate: passive | +2.995% | 16/16 | 16/16 | +71.516 to +328.709 |
| 0.01 | Mean: passive / One copy | +0.705% | 16/16 | 14/16 | -34.547 to +97.120 |
| 0.01 | Mean: passive / Starting only | +0.924% | 14/16 | 13/16 | -96.038 to +201.424 |
| 0.01 | Separate: control − / One copy | -1.036% | 1/16 | 1/16 | -241.767 to +1.999 |
| 0.01 | Separate: control − / Starting only | -0.812% | 2/16 | 2/16 | -303.257 to +127.710 |
| 0.1 | Separate: control − / Separate: passive | +0.715% | 16/16 | 16/16 | +14.689 to +69.761 |
| 0.1 | Mean: control − / Mean: passive | +0.203% | 15/16 | 15/16 | -11.894 to +32.316 |
| 0.1 | Mean: passive / Separate: passive | +0.467% | 16/16 | 15/16 | -0.945 to +97.130 |
| 0.1 | Mean: passive / One copy | +1.515% | 16/16 | 16/16 | +44.308 to +160.117 |
| 0.1 | Mean: passive / Starting only | +4.306% | 16/16 | 16/16 | +219.813 to +384.267 |
| 0.1 | Separate: control − / One copy | +1.760% | 16/16 | 16/16 | +41.331 to +176.514 |
| 0.1 | Separate: control − / Starting only | +4.545% | 16/16 | 16/16 | +216.693 to +377.474 |

The matched separate control− comparison stays positive under every deletion,
on both original-outcome and average-future MSE. Its mean-encoding equivalent
does not have that property. The separate observer still loses to starting-only
in every refit panel at .001; at .01 it beats starting-only in just2/16 panels
and one-copy in just1/16. At .1 both cheaper-baseline comparisons stay favorable
in every panel for average-future MSE. No setting is selected.

Mean-passive versus separate-passive now reverses after removing90014 at .001
or90010 at .1, although their score-only omissions were favorable. At .01 it
stays favorable under every refit deletion, but its advantage over one-copy
reverses on removing90007 or90014. Its .1 gains over starting-only and one-copy
remain favorable throughout. This is evidence of fitting/representation
sensitivity, not proof that a particular feature is causal or useless.

## Complete challenge/control panel

Entries show the unchanged full-cohort relative MSE reduction followed by
the number of positive refitted deletion panels. Passive uses the same
encoding and setting as its candidate. Every direction and challenge remains.

| Candidate / matched passive | 0.001 full reduction / positive refits | 0.01 full reduction / positive refits | 0.1 full reduction / positive refits |
|---|---|---|---|
| Separate: shuffle | +2.337% / 15/16 | +0.421% / 10/16 | -1.053% / 0/16 |
| Separate: attenuation | -1.294% / 2/16 | -1.574% / 1/16 | -1.547% / 0/16 |
| Separate: control + | -1.975% / 1/16 | -2.509% / 0/16 | -1.697% / 0/16 |
| Separate: control − | +2.234% / 16/16 | +1.295% / 16/16 | +0.715% / 16/16 |
| Separate: mean control loss | +0.129% / 7/16 | -0.607% / 1/16 | -0.491% / 1/16 |
| Mean: shuffle | +0.768% / 13/16 | -0.569% / 2/16 | -1.153% / 0/16 |
| Mean: attenuation | -0.725% / 2/16 | -1.048% / 0/16 | -1.018% / 0/16 |
| Mean: control + | -0.800% / 2/16 | -1.077% / 0/16 | -0.559% / 0/16 |
| Mean: control − | -0.008% / 8/16 | +0.222% / 15/16 | +0.203% / 15/16 |
| Mean: mean control loss | -0.404% / 1/16 | -0.428% / 0/16 | -0.178% / 1/16 |

Most attenuation and control+ panels are unfavorable, with isolated favorable
deletions retained. Shuffle depends on setting and encoding. Averaging the two
control losses does not deliver a consistent advantage. The control− direction
was a development lead before this audit; this result does not retroactively
make it the original registered challenge.

## Every deletion for the minus-nudge comparison

All entries are ×10⁻⁶ MSE gains against matched passive, averaged over all four
futures. Same deleted founder in the score-only and retrained columns.

Separate diagnostic profiles:

| Omitted founder | 0.001 score-only | 0.001 refitted | 0.01 score-only | 0.01 refitted | 0.1 score-only | 0.1 refitted |
|---|---|---|---|---|---|---|
| 90000 | +149.249 | +191.761 | +79.833 | +87.896 | +45.895 | +47.424 |
| 90001 | +161.077 | +141.012 | +94.557 | +96.901 | +53.286 | +55.302 |
| 90002 | +162.066 | +171.275 | +88.489 | +92.104 | +49.203 | +50.844 |
| 90003 | +165.009 | +141.090 | +99.716 | +91.863 | +71.364 | +69.761 |
| 90004 | +172.968 | +173.534 | +96.478 | +111.689 | +52.731 | +62.527 |
| 90005 | +160.280 | +200.328 | +92.826 | +107.268 | +49.688 | +51.266 |
| 90006 | +157.863 | +148.347 | +90.817 | +84.507 | +53.168 | +56.514 |
| 90007 | +140.041 | +57.315 | +77.722 | +55.456 | +41.353 | +29.578 |
| 90008 | +194.242 | +244.105 | +108.920 | +124.816 | +51.411 | +48.420 |
| 90009 | +171.739 | +171.839 | +99.942 | +104.056 | +56.956 | +60.110 |
| 90010 | +155.548 | +169.527 | +82.318 | +76.664 | +50.020 | +49.644 |
| 90011 | +160.934 | +133.316 | +91.813 | +94.156 | +52.508 | +65.641 |
| 90012 | +98.085 | +65.828 | +48.310 | +36.891 | +24.349 | +14.689 |
| 90013 | +156.830 | +147.413 | +85.700 | +81.668 | +50.709 | +43.818 |
| 90014 | +112.807 | +118.939 | +68.191 | +67.736 | +33.058 | +28.800 |
| 90015 | +153.403 | +184.879 | +75.618 | +85.395 | +46.938 | +54.813 |

Mean diagnostic profiles:

| Omitted founder | 0.001 score-only | 0.001 refitted | 0.01 score-only | 0.01 refitted | 0.1 score-only | 0.1 refitted |
|---|---|---|---|---|---|---|
| 90000 | -6.465 | -13.254 | +11.753 | +8.169 | +13.388 | +12.887 |
| 90001 | +2.029 | +3.567 | +17.166 | +17.963 | +16.145 | +15.864 |
| 90002 | -3.391 | -7.267 | +13.738 | +10.931 | +14.024 | +13.711 |
| 90003 | +10.614 | +3.429 | +24.990 | +21.729 | +32.920 | +32.316 |
| 90004 | +5.059 | +4.959 | +18.382 | +17.958 | +15.022 | +17.443 |
| 90005 | -4.888 | -27.493 | +16.020 | +14.114 | +13.827 | +14.623 |
| 90006 | -0.260 | -3.916 | +16.283 | +17.982 | +15.214 | +16.679 |
| 90007 | -8.183 | -31.588 | +9.222 | +0.615 | +12.796 | +8.630 |
| 90008 | +30.871 | +51.795 | +30.735 | +46.519 | +10.776 | +11.303 |
| 90009 | +12.243 | +18.896 | +24.862 | +28.947 | +17.080 | +19.264 |
| 90010 | -6.507 | -33.544 | +8.942 | -5.126 | +14.126 | +14.800 |
| 90011 | +1.521 | +13.425 | +16.845 | +19.029 | +14.949 | +16.514 |
| 90012 | -21.231 | +8.094 | -8.083 | +3.163 | -7.788 | -11.894 |
| 90013 | -5.049 | -10.392 | +12.067 | +6.913 | +15.077 | +11.747 |
| 90014 | -13.556 | -17.751 | +7.419 | +7.267 | +10.657 | +13.220 |
| 90015 | -1.137 | +20.825 | +9.346 | +17.693 | +13.614 | +16.298 |

Individual-future sensitivity is important even where the four-future average
is favorable. Here64=16 overlapping deletion panels times four repeat scores
(or four three-repeat averages). It is **not64 independent confirmations**.

| Setting | Encoding | Refitted four-future range (%) | Positive individual-repeat scores | Positive three-repeat averages |
|---|---|---|---|---|
| 0.001 | separate | +0.823 to +3.816 | 62/64 | 64/64 |
| 0.001 | mean | -0.474 to +0.835 | 23/64 | 30/64 |
| 0.01 | separate | +0.545 to +2.024 | 60/64 | 64/64 |
| 0.01 | mean | -0.075 to +0.777 | 43/64 | 53/64 |
| 0.1 | separate | +0.212 to +1.026 | 59/64 | 63/64 |
| 0.1 | mean | -0.173 to +0.479 | 50/64 | 60/64 |

For separate control−, the .1 panel omitting90012 becomes unfavorable when
future0 is also omitted from scoring: MSE gain−0.000003344. The individual
future exceptions and all corresponding negative cases are retained.
Consequently, “survives every founder deletion” must always be qualified as
the four-future-average result; it does not mean every outcome realization
or every joint omission is favorable.

## Training influence does not justify data pruning

For the same remaining15 founders, positive direct training-effect gain means
the newly refitted model has lower MSE than the unchanged D157 forecasts.
No scoring-composition difference enters this comparison.

| Setting | Observer | Lower MSE after refit | Training-effect gain range (×10⁻⁶ MSE) |
|---|---|---|---|
| 0.001 | Starting only | 2/16 | -165.164 to +53.579 |
| 0.001 | One copy | 4/16 | -212.925 to +29.914 |
| 0.001 | Separate: passive | 3/16 | -304.645 to +70.373 |
| 0.001 | Separate: control − | 4/16 | -273.169 to +70.472 |
| 0.001 | Mean: passive | 4/16 | -251.232 to +41.924 |
| 0.001 | Mean: control − | 4/16 | -255.427 to +35.136 |
| 0.01 | Starting only | 4/16 | -142.689 to +25.212 |
| 0.01 | One copy | 4/16 | -168.171 to +58.977 |
| 0.01 | Separate: passive | 4/16 | -177.737 to +42.169 |
| 0.01 | Separate: control − | 4/16 | -175.394 to +58.066 |
| 0.01 | Mean: passive | 4/16 | -185.752 to +27.438 |
| 0.01 | Mean: control − | 4/16 | -185.904 to +43.222 |
| 0.1 | Starting only | 3/16 | -189.242 to +26.826 |
| 0.1 | One copy | 3/16 | -192.111 to +43.791 |
| 0.1 | Separate: passive | 3/16 | -209.701 to +39.385 |
| 0.1 | Separate: control − | 3/16 | -196.568 to +36.395 |
| 0.1 | Mean: passive | 3/16 | -141.820 to +41.249 |
| 0.1 | Mean: control − | 4/16 | -140.256 to +41.777 |

For these focal observers, removing a training founder worsens prediction
more often than it improves it. Reduced training size is part of this
intervention. Neither a favorable deletion nor a large influence value
licenses discarding a founder, and these counts are not statistical tests.
All12 observers and both mean-control-loss versions are in the saved panel.

## Absolute errors

Lower MSE is better. Full original/future values are the unchanged D157
mean-target references. Refit ranges span the16 different retained-founder
panels; because those panels also differ in scored cases, comparing a range
endpoint to a full-cohort number does not isolate a training effect.
Use the paired training-effect records above for that purpose.

| Setting | Observer | Full original MSE | Full four-future MSE | Refitted four-future MSE range |
|---|---|---|---|---|
| 0.001 | Starting only | 0.006471015 | 0.006512956 | 0.006123010 to 0.006858785 |
| 0.001 | One copy | 0.006158928 | 0.006583402 | 0.006141241 to 0.006997739 |
| 0.001 | Separate: passive | 0.006715291 | 0.006917453 | 0.006396512 to 0.007371306 |
| 0.001 | Separate: shuffle | 0.006709497 | 0.006755819 | 0.006266840 to 0.007156610 |
| 0.001 | Separate: attenuation | 0.006407758 | 0.007006938 | 0.006503359 to 0.007459981 |
| 0.001 | Separate: control + | 0.006375928 | 0.007054102 | 0.006505896 to 0.007561642 |
| 0.001 | Separate: control − | 0.006503888 | 0.006762944 | 0.006152407 to 0.007201779 |
| 0.001 | Mean: passive | 0.006755282 | 0.006681433 | 0.006204090 to 0.007082948 |
| 0.001 | Mean: shuffle | 0.006770094 | 0.006630148 | 0.006116647 to 0.007047239 |
| 0.001 | Mean: attenuation | 0.006686134 | 0.006729898 | 0.006376090 to 0.007106623 |
| 0.001 | Mean: control + | 0.006620999 | 0.006734867 | 0.006387822 to 0.007124035 |
| 0.001 | Mean: control − | 0.006686808 | 0.006681954 | 0.006152296 to 0.007109933 |
| 0.01 | Starting only | 0.006375931 | 0.006528954 | 0.006168408 to 0.006847730 |
| 0.01 | One copy | 0.006074211 | 0.006514522 | 0.006042697 to 0.006869475 |
| 0.01 | Separate: passive | 0.006453351 | 0.006668324 | 0.006165515 to 0.007028369 |
| 0.01 | Separate: shuffle | 0.006570983 | 0.006640245 | 0.006105177 to 0.007012099 |
| 0.01 | Separate: attenuation | 0.006251638 | 0.006773291 | 0.006328645 to 0.007140189 |
| 0.01 | Separate: control + | 0.006212044 | 0.006835645 | 0.006323327 to 0.007232881 |
| 0.01 | Separate: control − | 0.006317063 | 0.006581996 | 0.006040698 to 0.006921176 |
| 0.01 | Mean: passive | 0.006280317 | 0.006468595 | 0.005984729 to 0.006826530 |
| 0.01 | Mean: shuffle | 0.006399812 | 0.006505433 | 0.006041370 to 0.006841826 |
| 0.01 | Mean: attenuation | 0.006269847 | 0.006536379 | 0.006139291 to 0.006896361 |
| 0.01 | Mean: control + | 0.006232577 | 0.006538280 | 0.006130627 to 0.006908147 |
| 0.01 | Mean: control − | 0.006210878 | 0.006454239 | 0.005938210 to 0.006810736 |
| 0.1 | Starting only | 0.006839276 | 0.007119920 | 0.006674763 to 0.007439452 |
| 0.1 | One copy | 0.006381320 | 0.006918103 | 0.006443195 to 0.007212293 |
| 0.1 | Separate: passive | 0.006377450 | 0.006845247 | 0.006358955 to 0.007153149 |
| 0.1 | Separate: shuffle | 0.006490306 | 0.006917299 | 0.006433812 to 0.007228754 |
| 0.1 | Separate: attenuation | 0.006374554 | 0.006951130 | 0.006513439 to 0.007270986 |
| 0.1 | Separate: control + | 0.006333758 | 0.006961445 | 0.006474286 to 0.007278013 |
| 0.1 | Separate: control − | 0.006290316 | 0.006796332 | 0.006310534 to 0.007091375 |
| 0.1 | Mean: passive | 0.006256152 | 0.006813313 | 0.006325961 to 0.007141964 |
| 0.1 | Mean: shuffle | 0.006385751 | 0.006891841 | 0.006436222 to 0.007200002 |
| 0.1 | Mean: attenuation | 0.006311586 | 0.006882647 | 0.006430568 to 0.007206173 |
| 0.1 | Mean: control + | 0.006264670 | 0.006851424 | 0.006379599 to 0.007177253 |
| 0.1 | Mean: control − | 0.006215452 | 0.006799448 | 0.006314658 to 0.007127164 |

All model MAE/RMSE/bias, group/block scores, every individual repeat and every
registered contrast remain in summary.json, alongside forecast-change
MAE/RMS/bias/max and group RMS. The full-cohort starting-only future RMSE is
8.0703/8.0802/8.4380 preference points; mean-passive is
8.1740/8.0428/8.2543. This keeps the cheaper baseline and absolute error size
visible rather than reporting only relative wins against a weak reference.

No new refitted forecast clipped (0/138,240); no reused mean-target reference
forecast clipped either. Each panel independently satisfies the identity
between individual-future MSE, mean-target MSE and that panel's within-case
future variance. Dispersion cancels in paired MSE gains. A deleted panel has
its own variance; the full-cohort variance is not blindly subtracted from
all deleted panels.

All signed/absolute/squared case errors and forecast changes are retained in
case_errors.npz:252 arrays. Deletion and validation identities are explicit in
fits.json; raw forecasts and all coefficients remain available for replay.

## Qualification, freeze, execution and fresh audit

**72 tests passed in59.03seconds**, no failures/skips. Qualification covers
both founder-exclusion boundaries, feature and target isolation, independent
group-coordinate SVD, permutations, constants/rank deficiency/clipping,
control-loss arithmetic, score/refit accounting, adverse corruption,
exact source identity, saved roundtrip and execution/resource guards.

Freeze17:05:46.497483 UTC pins2,171 inputs, including D157's full transitive
closure, fresh audit and result report. No new actual-case refit preceded it.
Qualified five-founder audit5.492seconds; benchmark forecast383.616seconds.

The complete16-founder synthetic benchmark, including saved independent
checks, took41.981570seconds; hashing9.526033seconds. Benchmark completed
17:07:02.114845 UTC,243,504,547bytes. Frozen main forecast223.015206seconds
and1,041,127,052bytes, within600seconds/1GiB with4GiB external reserve.

Actual manifest17:08:09.653908 UTC; COMPLETE17:09:08.699611 UTC.
Main59.045723seconds excluding preflight; **243,339,428bytes (232.066563MiB)**
output payload. Synthetic benchmark (~232MiB) and qualification fixtures
(~35MiB) remain separately on the external disk. Code/docs only here.
One numerical worker,threads one,affinity CPUs0–5; attached below600seconds.

Fresh saved audit completed17:10:31.118610 UTC in44.368567seconds:
**2,181 input hashes,10 indexed outputs, all8,640 double-exclusion fits,
138,240 new forecasts,252 case-error arrays and every score/decomposition pass**.
The30 source arrays are exact; all165 full-cohort comparison scores bridge
to D157. No old actual reference fits or tissue dynamics were recomputed.
Scientific fit counts exclude qualification, synthetic baseline/benchmark
and independent verification computations. No retry or automatic successor.

External root:

    /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/

Run/output basename:

    l20_extension1_training_influence_dev_v1_attempt1

Run manifests are in runs/<basename>/; outputs/<basename>/ contains dataset.npz,
baseline.npz, baseline_raw.npz, predictions.npz, raw_predictions.npz, fits.json,
case_errors.npz, summary.json, verification.json, input_hashes.sha256 and
output_hashes.sha256. Freeze/benchmark receipts are in tmp/, qualification
and fresh saved audit in logs/.

| Artifact | SHA256 |
|---|---|
| Freeze | 39ec4342295a1e761493b48e26abd37496cf04734a1b6939476426cdf8f08de3 |
| Manifest | 5788a03e438d0058dfba1b0f8ba9ec90b226d9c5af2cabaabed75cccc15b0e1f |
| COMPLETE | ad4e943be3b2bd86001d0be2050b309905ea1670cc47d98b0a57ec1e77e517f9 |
| Summary | 5ac123d5d351327159842fc779c7eccb2296357cae8a9c695a3e9c0ccafb9d1c |
| Verification | 12a919acdcc9c478b0e329db15c3b819b12cc789ff2b0f5fdc73186b344207fd |
| Output hash index | e1e0e52d50ae9a9f01b1fc74e171f9f4e76bbe34e1c96f3cde9c674a65267b0e |
| Fresh saved audit | 69d1bd0b994a347af5ee7a50edcdb1184ea54ee84425e96132e12dd4364d75f5 |

## Interpretation and next bounded proposal

This audit closes the specific single-founder influence question. The
separate-reading control− advantage in average-future scoring is not removed
by any single-founder retraining omission. That narrower result is stronger
than a score-only sensitivity check, but remains conditional on representation,
learner, setting, outcome summary and this already observed cohort.
It does not establish autonomous interface repair, complete shape preservation,
a biological heredity mechanism or a positive prospective D141 result.

A useful next check would inspect **what the two separate readings contribute**
using their already saved coefficients. Fix the training-fold-centered
decomposition into starting measurements, the shared mean of the two readings,
and their difference; reconstruct the existing raw forecasts exactly and
account for the existing squared-error gaps without new fits or replacement
forecasts. Include every passive/challenge/control condition, all three
settings, all full/deletion panels and cheaper baselines.

Such an accounting might locate the surviving separate-reading edge in the
mean or difference contribution. It would be representation-dependent
arithmetic, not a causal ablation or proof of independently predictive
information. Freeze/qualify that scope before analysis, retain unfavorable
components, and do not tune the challenge or select a favorable deletion.
**Proposal only—not launched.** Untouched founders and frozen rules would
still be required for a new prospective confirmation.
