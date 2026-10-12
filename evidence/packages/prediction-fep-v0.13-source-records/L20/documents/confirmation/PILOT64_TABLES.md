# D162 — complete audited numerical tables

2026-09-22. Companion to [the results report](PILOT64_RESULTS.md).
Source: audited external `outputs/l20_extension1_pilot64_v1_attempt1/summary.json`,
SHA256 `b979292bf0bb3f59bbc0073bd60beed4562b93b8b0870f845a9975c250538283`.

These are documentation tables transcribed from existing results, not new
experiments, refits, settings, significance searches or outcome-selected cases.
All 51 model/settings, 264 same-setting contrasts, four selected-baseline
contrasts, 64 primary founder differences and 228 apparatus contrasts are kept.
Only tied:sham_minus versus tied:passive at .01 is confirmatory; all remaining
intervals are pointwise descriptive and not multiplicity-adjusted.

Observer names are the frozen machine identifiers. `separate` retains separate
reading slopes; `mean` fits averaged readings after its own preprocessing;
`tied` equates raw slopes under the original penalty. `sham_plus/minus` are
the fixed equal-dose residual directions. `mean_sham_loss` is the arithmetic
mean of two LOSSES, never a forecast ensemble or a third diagnostic copy.
All predictions had zero clipping.

For prediction comparisons gain = reference MSE − candidate MSE; positive
means lower candidate error. Intervals use 20,000 whole-founder draws.
Control effects are left-minus-right preference in points (100 × preference).
Numeric display rounds existing quantities only; full precision and all
absolute per-block/group/future scores remain in the external summary.

## All 51 absolute score rows

Calibration intercept is in raw preference units, not preference points.
Bias = predicted minus observed preference, in points.

| Observer | Alpha | MSE | RMSE points | MAE points | Bias points | Calibration intercept | Calibration slope | Clipped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean:attenuate | 0.001 | 0.006051188882 | 7.778939 | 4.658351 | -0.277701 | +0.010907336 | 0.976449808 | 0 |
| mean:attenuate | 0.01 | 0.005954647253 | 7.716636 | 4.635105 | -0.135808 | +0.000415730 | 1.002718432 | 0 |
| mean:attenuate | 0.1 | 0.006105714477 | 7.813907 | 4.784367 | -0.038479 | -0.020773005 | 1.060863639 | 0 |
| mean:passive | 0.001 | 0.006071172366 | 7.791773 | 4.645071 | -0.295565 | +0.013035587 | 0.970787481 | 0 |
| mean:passive | 0.01 | 0.005950885648 | 7.714198 | 4.611180 | -0.160103 | +0.002331832 | 0.997890343 | 0 |
| mean:passive | 0.1 | 0.006058968837 | 7.783938 | 4.747184 | -0.063799 | -0.019249249 | 1.057250388 | 0 |
| mean:sham_minus | 0.001 | 0.006066672631 | 7.788885 | 4.638949 | -0.280431 | +0.012712545 | 0.971297679 | 0 |
| mean:sham_minus | 0.01 | 0.005954775851 | 7.716719 | 4.609139 | -0.148271 | +0.001964428 | 0.998609863 | 0 |
| mean:sham_minus | 0.1 | 0.006072741303 | 7.792780 | 4.754809 | -0.053184 | -0.019695733 | 1.058212329 | 0 |
| mean:sham_plus | 0.001 | 0.005993611314 | 7.741842 | 4.630820 | -0.267748 | +0.010695844 | 0.976780811 | 0 |
| mean:sham_plus | 0.01 | 0.005913384718 | 7.689854 | 4.609232 | -0.142227 | +0.000882106 | 1.001558509 | 0 |
| mean:sham_plus | 0.1 | 0.006063753381 | 7.787011 | 4.753940 | -0.060637 | -0.019401369 | 1.057592028 | 0 |
| mean:shuffle | 0.001 | 0.006206887481 | 7.878380 | 4.716937 | -0.253870 | +0.008922093 | 0.981522717 | 0 |
| mean:shuffle | 0.01 | 0.006066267264 | 7.788625 | 4.682118 | -0.137369 | -0.000647860 | 1.005831873 | 0 |
| mean:shuffle | 0.1 | 0.006147750414 | 7.840759 | 4.810497 | -0.060559 | -0.020573576 | 1.060963844 | 0 |
| one_copy | 0.001 | 0.006159271189 | 7.848102 | 4.718506 | -0.221808 | +0.010777296 | 0.975247554 | 0 |
| one_copy | 0.01 | 0.006019101537 | 7.758287 | 4.663300 | -0.077209 | +0.000253693 | 1.001492904 | 0 |
| one_copy | 0.1 | 0.006138762271 | 7.835025 | 4.785386 | +0.023010 | -0.022955424 | 1.065257440 | 0 |
| separate:attenuate | 0.001 | 0.006240179017 | 7.899480 | 4.757118 | -0.114810 | +0.011765180 | 0.969391146 | 0 |
| separate:attenuate | 0.01 | 0.005944077047 | 7.709784 | 4.649375 | -0.057940 | -0.000006021 | 1.001684991 | 0 |
| separate:attenuate | 0.1 | 0.006075901555 | 7.794807 | 4.755500 | +0.000876 | -0.021163767 | 1.060786801 | 0 |
| separate:passive | 0.001 | 0.006149272113 | 7.841729 | 4.702781 | -0.116787 | +0.010989571 | 0.971682571 | 0 |
| separate:passive | 0.01 | 0.005941476229 | 7.708097 | 4.621415 | -0.049265 | +0.000926879 | 0.998750496 | 0 |
| separate:passive | 0.1 | 0.006019327765 | 7.758433 | 4.714889 | -0.014308 | -0.019245416 | 1.055735230 | 0 |
| separate:sham_minus | 0.001 | 0.006270600472 | 7.918712 | 4.780768 | -0.070640 | +0.011040715 | 0.970244230 | 0 |
| separate:sham_minus | 0.01 | 0.006000716815 | 7.746429 | 4.659843 | -0.010816 | -0.000218401 | 1.000938660 | 0 |
| separate:sham_minus | 0.1 | 0.006053775599 | 7.780601 | 4.733628 | +0.011021 | -0.020163108 | 1.057603190 | 0 |
| separate:sham_plus | 0.001 | 0.006219305842 | 7.886258 | 4.733151 | -0.165171 | +0.012761233 | 0.967924849 | 0 |
| separate:sham_plus | 0.01 | 0.005921300450 | 7.694999 | 4.622573 | -0.083244 | +0.001299602 | 0.998654416 | 0 |
| separate:sham_plus | 0.1 | 0.006022572419 | 7.760523 | 4.720044 | -0.026953 | -0.019226677 | 1.056065223 | 0 |
| separate:shuffle | 0.001 | 0.006375167437 | 7.984465 | 4.784687 | -0.099817 | +0.010335216 | 0.973093074 | 0 |
| separate:shuffle | 0.01 | 0.006112908209 | 7.818509 | 4.686654 | -0.060243 | +0.000217664 | 1.001107532 | 0 |
| separate:shuffle | 0.1 | 0.006106039849 | 7.814115 | 4.758698 | -0.012892 | -0.021043769 | 1.060861692 | 0 |
| starting | 0.001 | 0.006215812899 | 7.884043 | 4.860798 | -0.125582 | -0.000383317 | 1.004727063 | 0 |
| starting | 0.01 | 0.006221001152 | 7.887332 | 4.870370 | -0.019224 | -0.006955054 | 1.020548901 | 0 |
| starting | 0.1 | 0.006485434131 | 8.053219 | 5.060639 | +0.024814 | -0.027729045 | 1.078909362 | 0 |
| tied:attenuate | 0.001 | 0.006075162276 | 7.794333 | 4.661286 | -0.278909 | +0.011838205 | 0.973787541 | 0 |
| tied:attenuate | 0.01 | 0.005957939364 | 7.718769 | 4.629597 | -0.141269 | +0.001078761 | 1.000963453 | 0 |
| tied:attenuate | 0.1 | 0.006076901084 | 7.795448 | 4.756414 | -0.045378 | -0.019499075 | 1.057408821 | 0 |
| tied:passive | 0.001 | 0.006094392152 | 7.806659 | 4.649603 | -0.297420 | +0.013901961 | 0.968328706 | 0 |
| tied:passive | 0.01 | 0.005961523977 | 7.721091 | 4.607874 | -0.165044 | +0.003117898 | 0.995763212 | 0 |
| tied:passive | 0.1 | 0.006031986048 | 7.766586 | 4.719506 | -0.070992 | -0.017803333 | 1.053306057 | 0 |
| tied:sham_minus | 0.001 | 0.006089039773 | 7.803230 | 4.643264 | -0.283286 | +0.013657285 | 0.968641037 | 0 |
| tied:sham_minus | 0.01 | 0.005964223422 | 7.722838 | 4.605210 | -0.152744 | +0.002701622 | 0.996611140 | 0 |
| tied:sham_minus | 0.1 | 0.006046191218 | 7.775726 | 4.725932 | -0.058494 | -0.018308253 | 1.054380482 | 0 |
| tied:sham_plus | 0.001 | 0.006019152420 | 7.758320 | 4.636893 | -0.266425 | +0.011633538 | 0.974028177 | 0 |
| tied:sham_plus | 0.01 | 0.005911408518 | 7.688568 | 4.602323 | -0.144211 | +0.001474090 | 0.999907732 | 0 |
| tied:sham_plus | 0.1 | 0.006034920727 | 7.768475 | 4.726805 | -0.066883 | -0.018024877 | 1.053819269 | 0 |
| tied:shuffle | 0.001 | 0.006224012374 | 7.889241 | 4.721889 | -0.256747 | +0.009349692 | 0.980366628 | 0 |
| tied:shuffle | 0.01 | 0.006093437763 | 7.806048 | 4.688487 | -0.144108 | -0.000018354 | 1.004211082 | 0 |
| tied:shuffle | 0.1 | 0.006141229756 | 7.836600 | 4.795825 | -0.062848 | -0.019648772 | 1.058371534 | 0 |

## All 264 same-setting prediction contrasts

Gain and interval columns are in **millionths of MSE**, not preference points.
Primary marking does not change the order or omit any secondary row.

| Candidate | Reference | Alpha | Gain ×10⁻⁶ | 95% interval ×10⁻⁶ | Relative gain % | Role |
| --- | --- | --- | --- | --- | --- | --- |
| separate:passive | starting | 0.001 | +66.540786 | [-123.714256, +250.827733] | +1.070508 | secondary |
| separate:shuffle | starting | 0.001 | -159.354538 | [-367.941100, +48.806177] | -2.563696 | secondary |
| separate:shuffle | separate:passive | 0.001 | -225.895324 | [-365.107080, -96.123636] | -3.673529 | secondary |
| separate:attenuate | starting | 0.001 | -24.366119 | [-196.590526, +143.955387] | -0.392002 | secondary |
| separate:attenuate | separate:passive | 0.001 | -90.906904 | [-183.007500, -1.178888] | -1.478336 | secondary |
| separate:attenuate | separate:shuffle | 0.001 | +134.988420 | [+1.218768, +272.391674] | +2.117410 | secondary |
| separate:attenuate | separate:sham_plus | 0.001 | -20.873175 | [-122.869324, +80.443354] | -0.335619 | secondary |
| separate:attenuate | separate:sham_minus | 0.001 | +30.421454 | [-53.898834, +115.930390] | +0.485144 | secondary |
| separate:sham_plus | starting | 0.001 | -3.492943 | [-164.738804, +152.892541] | -0.056194 | secondary |
| separate:sham_plus | separate:passive | 0.001 | -70.033729 | [-209.924457, +69.312652] | -1.138895 | secondary |
| separate:sham_plus | separate:shuffle | 0.001 | +155.861595 | [+0.661672, +316.969930] | +2.444824 | secondary |
| separate:sham_minus | starting | 0.001 | -54.787573 | [-253.416851, +138.919837] | -0.881422 | secondary |
| separate:sham_minus | separate:passive | 0.001 | -121.328358 | [-196.985900, -52.937725] | -1.973052 | secondary |
| separate:sham_minus | separate:shuffle | 0.001 | +104.566966 | [-24.884283, +233.317081] | +1.640223 | secondary |
| separate:sham_minus | separate:sham_plus | 0.001 | -51.294630 | [-185.920836, +83.250553] | -0.824765 | secondary |
| separate:attenuate | separate:mean_sham_loss | 0.001 | +4.774139 | [-61.548429, +67.494785] | +0.076448 | secondary |
| separate:mean_sham_loss | starting | 0.001 | -29.140258 | [-197.140319, +134.658402] | -0.468808 | secondary |
| separate:mean_sham_loss | separate:passive | 0.001 | -95.681044 | [-186.564242, -8.606346] | -1.555973 | secondary |
| one_copy | starting | 0.001 | +56.541710 | [-71.531987, +180.045101] | +0.909643 | secondary |
| separate:passive | one_copy | 0.001 | +9.999076 | [-131.313317, +154.118224] | +0.162342 | secondary |
| separate:shuffle | one_copy | 0.001 | -215.896248 | [-376.533157, -54.896810] | -3.505224 | secondary |
| separate:attenuate | one_copy | 0.001 | -80.907828 | [-198.214085, +41.035481] | -1.313594 | secondary |
| separate:sham_plus | one_copy | 0.001 | -60.034653 | [-175.265061, +49.593932] | -0.974704 | secondary |
| separate:sham_minus | one_copy | 0.001 | -111.329283 | [-254.836721, +34.741841] | -1.807507 | secondary |
| separate:mean_sham_loss | one_copy | 0.001 | -85.681968 | [-196.723904, +24.570992] | -1.391106 | secondary |
| mean:passive | separate:passive | 0.001 | +78.099747 | [-43.394117, +199.735456] | +1.270065 | secondary |
| mean:shuffle | separate:shuffle | 0.001 | +168.279956 | [+18.768168, +322.408814] | +2.639616 | secondary |
| mean:attenuate | separate:attenuate | 0.001 | +188.990136 | [+63.014907, +315.552412] | +3.028601 | secondary |
| mean:sham_plus | separate:sham_plus | 0.001 | +225.694528 | [+128.566979, +331.590402] | +3.628934 | secondary |
| mean:sham_minus | separate:sham_minus | 0.001 | +203.927840 | [+64.919476, +347.997886] | +3.252126 | secondary |
| mean:passive | one_copy | 0.001 | +88.098823 | [-0.868827, +178.427625] | +1.430345 | secondary |
| mean:passive | starting | 0.001 | +144.640533 | [-6.320652, +291.899070] | +2.326977 | secondary |
| mean:shuffle | one_copy | 0.001 | -47.616292 | [-162.744623, +65.353630] | -0.773083 | secondary |
| mean:shuffle | starting | 0.001 | +8.925418 | [-127.450402, +148.521120] | +0.143592 | secondary |
| mean:attenuate | one_copy | 0.001 | +108.082307 | [+33.448882, +182.759691] | +1.754791 | secondary |
| mean:attenuate | starting | 0.001 | +164.624017 | [+40.122807, +287.896707] | +2.648471 | secondary |
| mean:sham_plus | one_copy | 0.001 | +165.659875 | [+82.599645, +248.786782] | +2.689602 | secondary |
| mean:sham_plus | starting | 0.001 | +222.201585 | [+93.008718, +348.484033] | +3.574779 | secondary |
| mean:sham_minus | one_copy | 0.001 | +92.598558 | [+6.723755, +178.797455] | +1.503401 | secondary |
| mean:sham_minus | starting | 0.001 | +149.140268 | [+2.951035, +294.598183] | +2.399369 | secondary |
| mean:shuffle | mean:passive | 0.001 | -135.715115 | [-235.449253, -34.935435] | -2.235402 | secondary |
| mean:attenuate | mean:passive | 0.001 | +19.983484 | [-29.205451, +68.448677] | +0.329154 | secondary |
| mean:attenuate | mean:shuffle | 0.001 | +155.698599 | [+58.175615, +254.138837] | +2.508481 | secondary |
| mean:attenuate | mean:sham_plus | 0.001 | -57.577567 | [-96.835051, -18.875549] | -0.960649 | secondary |
| mean:attenuate | mean:sham_minus | 0.001 | +15.483749 | [-34.293009, +61.965716] | +0.255226 | secondary |
| mean:sham_plus | mean:passive | 0.001 | +77.561051 | [+19.187309, +137.572841] | +1.277530 | secondary |
| mean:sham_plus | mean:shuffle | 0.001 | +213.276167 | [+113.267953, +315.783585] | +3.436121 | secondary |
| mean:sham_minus | mean:passive | 0.001 | +4.499735 | [-19.085824, +28.982716] | +0.074116 | secondary |
| mean:sham_minus | mean:shuffle | 0.001 | +140.214850 | [+35.954400, +244.528893] | +2.259020 | secondary |
| mean:sham_minus | mean:sham_plus | 0.001 | -73.061317 | [-134.260300, -12.388164] | -1.218987 | secondary |
| mean:mean_sham_loss | mean:passive | 0.001 | +41.030393 | [+8.032151, +75.449244] | +0.675823 | secondary |
| mean:mean_sham_loss | one_copy | 0.001 | +129.129216 | [+51.144628, +208.537651] | +2.096502 | secondary |
| mean:mean_sham_loss | starting | 0.001 | +185.670926 | [+49.942410, +318.822365] | +2.987074 | secondary |
| mean:mean_sham_loss | separate:mean_sham_loss | 0.001 | +214.811184 | [+111.001114, +324.765326] | +3.439757 | secondary |
| mean:attenuate | mean:mean_sham_loss | 0.001 | -21.046909 | [-54.202556, +8.443253] | -0.349028 | secondary |
| tied:passive | separate:passive | 0.001 | +54.879961 | [-68.951691, +179.124232] | +0.892463 | secondary |
| tied:passive | mean:passive | 0.001 | -23.219786 | [-35.933370, -10.823105] | -0.382460 | secondary |
| tied:passive | starting | 0.001 | +121.420747 | [-34.498993, +272.409657] | +1.953417 | secondary |
| tied:passive | one_copy | 0.001 | +64.879037 | [-29.228898, +159.239782] | +1.053356 | secondary |
| tied:shuffle | separate:shuffle | 0.001 | +151.155063 | [+2.626110, +304.716557] | +2.370998 | secondary |
| tied:shuffle | mean:shuffle | 0.001 | -17.124893 | [-23.725634, -10.772462] | -0.275901 | secondary |
| tied:shuffle | starting | 0.001 | -8.199475 | [-147.498778, +134.715313] | -0.131913 | secondary |
| tied:shuffle | one_copy | 0.001 | -64.741185 | [-181.298680, +50.724392] | -1.051118 | secondary |
| tied:attenuate | separate:attenuate | 0.001 | +165.016741 | [+38.420015, +290.994509] | +2.644423 | secondary |
| tied:attenuate | mean:attenuate | 0.001 | -23.973395 | [-39.169389, -9.210852] | -0.396177 | secondary |
| tied:attenuate | starting | 0.001 | +140.650623 | [+9.586987, +268.794963] | +2.262787 | secondary |
| tied:attenuate | one_copy | 0.001 | +84.108913 | [+2.773703, +165.429236] | +1.365566 | secondary |
| tied:sham_plus | separate:sham_plus | 0.001 | +200.153422 | [+105.981203, +302.369460] | +3.218260 | secondary |
| tied:sham_plus | mean:sham_plus | 0.001 | -25.541105 | [-40.885756, -11.144731] | -0.426139 | secondary |
| tied:sham_plus | starting | 0.001 | +196.660479 | [+60.505017, +329.625492] | +3.163874 | secondary |
| tied:sham_plus | one_copy | 0.001 | +140.118769 | [+50.519965, +229.065598] | +2.274925 | secondary |
| tied:sham_minus | separate:sham_minus | 0.001 | +181.560699 | [+40.248082, +326.902119] | +2.895428 | secondary |
| tied:sham_minus | mean:sham_minus | 0.001 | -22.367142 | [-35.543550, -9.397851] | -0.368689 | secondary |
| tied:sham_minus | starting | 0.001 | +126.773126 | [-24.331377, +276.079515] | +2.039526 | secondary |
| tied:sham_minus | one_copy | 0.001 | +70.231416 | [-20.033821, +161.034738] | +1.140255 | secondary |
| tied:shuffle | tied:passive | 0.001 | -129.620222 | [-231.031822, -27.109804] | -2.126877 | secondary |
| tied:attenuate | tied:passive | 0.001 | +19.229876 | [-30.571107, +68.322787] | +0.315534 | secondary |
| tied:sham_plus | tied:passive | 0.001 | +75.239732 | [+14.515391, +137.184499] | +1.234573 | secondary |
| tied:sham_minus | tied:passive | 0.001 | +5.352379 | [-18.374594, +29.911018] | +0.087825 | secondary |
| tied:mean_sham_loss | tied:passive | 0.001 | +40.296055 | [+6.543074, +75.645800] | +0.661199 | secondary |
| tied:attenuate | tied:shuffle | 0.001 | +148.850098 | [+48.916862, +249.686741] | +2.391546 | secondary |
| tied:attenuate | tied:sham_plus | 0.001 | -56.009857 | [-96.172358, -16.074323] | -0.930527 | secondary |
| tied:attenuate | tied:sham_minus | 0.001 | +13.877497 | [-36.820863, +61.639777] | +0.227909 | secondary |
| tied:attenuate | tied:mean_sham_loss | 0.001 | -21.066180 | [-54.399327, +9.069837] | -0.347966 | secondary |
| tied:mean_sham_loss | starting | 0.001 | +161.716803 | [+20.959681, +298.698855] | +2.601700 | secondary |
| tied:mean_sham_loss | one_copy | 0.001 | +105.175093 | [+20.748482, +189.874624] | +1.707590 | secondary |
| tied:mean_sham_loss | separate:mean_sham_loss | 0.001 | +190.857060 | [+88.164248, +299.770105] | +3.056181 | secondary |
| tied:mean_sham_loss | mean:mean_sham_loss | 0.001 | -23.954124 | [-38.118545, -10.359049] | -0.397240 | secondary |
| separate:passive | starting | 0.01 | +279.524923 | [+118.844381, +444.215243] | +4.493247 | secondary |
| separate:shuffle | starting | 0.01 | +108.092944 | [-43.621710, +262.857321] | +1.737549 | secondary |
| separate:shuffle | separate:passive | 0.01 | -171.431979 | [-280.766025, -67.902506] | -2.885343 | secondary |
| separate:attenuate | starting | 0.01 | +276.924106 | [+143.030986, +409.165489] | +4.451440 | secondary |
| separate:attenuate | separate:passive | 0.01 | -2.600817 | [-66.115447, +58.504682] | -0.043774 | secondary |
| separate:attenuate | separate:shuffle | 0.01 | +168.831162 | [+68.416664, +272.118584] | +2.761880 | secondary |
| separate:attenuate | separate:sham_plus | 0.01 | -22.776596 | [-84.423233, +36.596981] | -0.384655 | secondary |
| separate:attenuate | separate:sham_minus | 0.01 | +56.639769 | [-13.459693, +125.393195] | +0.943883 | secondary |
| separate:sham_plus | starting | 0.01 | +299.700702 | [+175.071683, +425.255715] | +4.817564 | secondary |
| separate:sham_plus | separate:passive | 0.01 | +20.175779 | [-67.335676, +107.623633] | +0.339575 | secondary |
| separate:sham_plus | separate:shuffle | 0.01 | +191.607758 | [+88.387065, +296.142931] | +3.134478 | secondary |
| separate:sham_minus | starting | 0.01 | +220.284337 | [+54.750130, +388.985655] | +3.540979 | secondary |
| separate:sham_minus | separate:passive | 0.01 | -59.240586 | [-108.166808, -10.295609] | -0.997068 | secondary |
| separate:sham_minus | separate:shuffle | 0.01 | +112.191393 | [+4.955053, +221.046559] | +1.835319 | secondary |
| separate:sham_minus | separate:sham_plus | 0.01 | -79.416365 | [-176.121842, +13.285333] | -1.341198 | secondary |
| separate:attenuate | separate:mean_sham_loss | 0.01 | +16.931586 | [-27.792997, +61.060345] | +0.284039 | secondary |
| separate:mean_sham_loss | starting | 0.01 | +259.992520 | [+121.229016, +400.573677] | +4.179271 | secondary |
| separate:mean_sham_loss | separate:passive | 0.01 | -19.532404 | [-73.044154, +32.262631] | -0.328747 | secondary |
| one_copy | starting | 0.01 | +201.899616 | [+99.014584, +303.841865] | +3.245452 | secondary |
| separate:passive | one_copy | 0.01 | +77.625308 | [-41.260439, +206.377441] | +1.289649 | secondary |
| separate:shuffle | one_copy | 0.01 | -93.806672 | [-206.089745, +21.445573] | -1.558483 | secondary |
| separate:attenuate | one_copy | 0.01 | +75.024490 | [-7.166784, +161.816637] | +1.246440 | secondary |
| separate:sham_plus | one_copy | 0.01 | +97.801087 | [+23.055020, +172.367455] | +1.624845 | secondary |
| separate:sham_minus | one_copy | 0.01 | +18.384721 | [-100.719764, +146.078438] | +0.305440 | secondary |
| separate:mean_sham_loss | one_copy | 0.01 | +58.092904 | [-29.489891, +151.334487] | +0.965142 | secondary |
| mean:passive | separate:passive | 0.01 | -9.409419 | [-108.788433, +87.871142] | -0.158368 | secondary |
| mean:shuffle | separate:shuffle | 0.01 | +46.640945 | [-54.644497, +149.521567] | +0.762991 | secondary |
| mean:attenuate | separate:attenuate | 0.01 | -10.570206 | [-91.212658, +66.430915] | -0.177828 | secondary |
| mean:sham_plus | separate:sham_plus | 0.01 | +7.915732 | [-38.006558, +54.285090] | +0.133682 | secondary |
| mean:sham_minus | separate:sham_minus | 0.01 | +45.940965 | [-62.735758, +155.837431] | +0.765591 | secondary |
| mean:passive | one_copy | 0.01 | +68.215889 | [-3.222114, +140.103695] | +1.133323 | secondary |
| mean:passive | starting | 0.01 | +270.115505 | [+147.855045, +393.111095] | +4.341994 | secondary |
| mean:shuffle | one_copy | 0.01 | -47.165727 | [-138.225656, +43.426263] | -0.783601 | secondary |
| mean:shuffle | starting | 0.01 | +154.733889 | [+40.687499, +272.629518] | +2.487283 | secondary |
| mean:attenuate | one_copy | 0.01 | +64.454284 | [+6.016096, +122.561652] | +1.070829 | secondary |
| mean:attenuate | starting | 0.01 | +266.353900 | [+158.386829, +375.390618] | +4.281528 | secondary |
| mean:sham_plus | one_copy | 0.01 | +105.716819 | [+41.365731, +169.734991] | +1.756355 | secondary |
| mean:sham_plus | starting | 0.01 | +307.616434 | [+196.279166, +421.257261] | +4.944806 | secondary |
| mean:sham_minus | one_copy | 0.01 | +64.325686 | [-3.962379, +131.422671] | +1.068692 | secondary |
| mean:sham_minus | starting | 0.01 | +266.225302 | [+146.136041, +390.239852] | +4.279461 | secondary |
| mean:shuffle | mean:passive | 0.01 | -115.381616 | [-195.055282, -36.640413] | -1.938898 | secondary |
| mean:attenuate | mean:passive | 0.01 | -3.761605 | [-42.873211, +32.195290] | -0.063211 | secondary |
| mean:attenuate | mean:shuffle | 0.01 | +111.620011 | [+34.380164, +188.770062] | +1.840011 | secondary |
| mean:attenuate | mean:sham_plus | 0.01 | -41.262534 | [-69.923825, -12.835495] | -0.697782 | secondary |
| mean:attenuate | mean:sham_minus | 0.01 | +0.128598 | [-39.339618, +34.696152] | +0.002160 | secondary |
| mean:sham_plus | mean:passive | 0.01 | +37.500930 | [-0.650962, +75.910244] | +0.630174 | secondary |
| mean:sham_plus | mean:shuffle | 0.01 | +152.882545 | [+76.872454, +230.033249] | +2.520208 | secondary |
| mean:sham_minus | mean:passive | 0.01 | -3.890203 | [-23.788994, +16.483196] | -0.065372 | secondary |
| mean:sham_minus | mean:shuffle | 0.01 | +111.491413 | [+28.915831, +194.986688] | +1.837892 | secondary |
| mean:sham_minus | mean:sham_plus | 0.01 | -41.391132 | [-82.195503, -0.537111] | -0.699957 | secondary |
| mean:mean_sham_loss | mean:passive | 0.01 | +16.805363 | [-5.892609, +39.667554] | +0.282401 | secondary |
| mean:mean_sham_loss | one_copy | 0.01 | +85.021253 | [+21.190031, +147.748210] | +1.412524 | secondary |
| mean:mean_sham_loss | starting | 0.01 | +286.920868 | [+172.457860, +403.921884] | +4.612133 | secondary |
| mean:mean_sham_loss | separate:mean_sham_loss | 0.01 | +26.928348 | [-47.048302, +99.795744] | +0.451741 | secondary |
| mean:attenuate | mean:mean_sham_loss | 0.01 | -20.566968 | [-48.701444, +3.636092] | -0.346591 | secondary |
| tied:passive | separate:passive | 0.01 | -20.047748 | [-119.000379, +76.312567] | -0.337420 | secondary |
| tied:passive | mean:passive | 0.01 | -10.638329 | [-22.004811, +0.839757] | -0.178769 | secondary |
| tied:passive | starting | 0.01 | +259.477176 | [+132.578116, +385.601774] | +4.170987 | secondary |
| tied:passive | one_copy | 0.01 | +57.577560 | [-19.709169, +134.726768] | +0.956581 | secondary |
| tied:shuffle | separate:shuffle | 0.01 | +19.470445 | [-81.786658, +123.222603] | +0.318514 | secondary |
| tied:shuffle | mean:shuffle | 0.01 | -27.170500 | [-40.192505, -14.360912] | -0.447895 | secondary |
| tied:shuffle | starting | 0.01 | +127.563389 | [+6.997667, +251.252833] | +2.050528 | secondary |
| tied:shuffle | one_copy | 0.01 | -74.336226 | [-170.219810, +20.867822] | -1.235005 | secondary |
| tied:attenuate | separate:attenuate | 0.01 | -13.862317 | [-96.553625, +64.320891] | -0.233212 | secondary |
| tied:attenuate | mean:attenuate | 0.01 | -3.292111 | [-13.572478, +6.857958] | -0.055286 | secondary |
| tied:attenuate | starting | 0.01 | +263.061788 | [+151.654078, +376.314950] | +4.228609 | secondary |
| tied:attenuate | one_copy | 0.01 | +61.162173 | [-2.207731, +122.961273] | +1.016135 | secondary |
| tied:sham_plus | separate:sham_plus | 0.01 | +9.891932 | [-36.071757, +55.984492] | +0.167057 | secondary |
| tied:sham_plus | mean:sham_plus | 0.01 | +1.976200 | [-6.816242, +10.414019] | +0.033419 | secondary |
| tied:sham_plus | starting | 0.01 | +309.592634 | [+195.439191, +425.699895] | +4.976573 | secondary |
| tied:sham_plus | one_copy | 0.01 | +107.693018 | [+39.831205, +175.172378] | +1.789188 | secondary |
| tied:sham_minus | separate:sham_minus | 0.01 | +36.493394 | [-73.112596, +145.755307] | +0.608151 | secondary |
| tied:sham_minus | mean:sham_minus | 0.01 | -9.447571 | [-20.478805, +1.749963] | -0.158655 | secondary |
| tied:sham_minus | starting | 0.01 | +256.777731 | [+132.438886, +383.918698] | +4.127595 | secondary |
| tied:sham_minus | one_copy | 0.01 | +54.878115 | [-17.808643, +126.763259] | +0.911733 | secondary |
| tied:shuffle | tied:passive | 0.01 | -131.913787 | [-217.065723, -47.543373] | -2.212753 | secondary |
| tied:attenuate | tied:passive | 0.01 | +3.584613 | [-38.980925, +43.076808] | +0.060129 | secondary |
| tied:sham_plus | tied:passive | 0.01 | +50.115458 | [+6.623706, +94.403003] | +0.840648 | secondary |
| tied:sham_minus | tied:passive | 0.01 | -2.699445 | [-23.801300, +19.234350] | -0.045281 | PRIMARY |
| tied:mean_sham_loss | tied:passive | 0.01 | +23.708007 | [-2.390284, +50.179120] | +0.397684 | secondary |
| tied:attenuate | tied:shuffle | 0.01 | +135.498399 | [+54.671329, +217.212223] | +2.223677 | secondary |
| tied:attenuate | tied:sham_plus | 0.01 | -46.530846 | [-77.891229, -15.478344] | -0.787136 | secondary |
| tied:attenuate | tied:sham_minus | 0.01 | +6.284058 | [-35.758995, +43.752262] | +0.105363 | secondary |
| tied:attenuate | tied:mean_sham_loss | 0.01 | -20.123394 | [-49.920413, +5.486857] | -0.338902 | secondary |
| tied:mean_sham_loss | starting | 0.01 | +283.185182 | [+165.686895, +402.256641] | +4.552084 | secondary |
| tied:mean_sham_loss | one_copy | 0.01 | +81.285567 | [+13.886820, +147.259198] | +1.350460 | secondary |
| tied:mean_sham_loss | separate:mean_sham_loss | 0.01 | +23.192663 | [-51.468828, +96.739761] | +0.389073 | secondary |
| tied:mean_sham_loss | mean:mean_sham_loss | 0.01 | -3.735686 | [-13.065855, +5.577208] | -0.062953 | secondary |
| separate:passive | starting | 0.1 | +466.106366 | [+310.023967, +626.694477] | +7.186972 | secondary |
| separate:shuffle | starting | 0.1 | +379.394282 | [+228.351350, +539.320783] | +5.849944 | secondary |
| separate:shuffle | separate:passive | 0.1 | -86.712084 | [-160.959758, -16.009540] | -1.440561 | secondary |
| separate:attenuate | starting | 0.1 | +409.532576 | [+267.661608, +555.397260] | +6.314652 | secondary |
| separate:attenuate | separate:passive | 0.1 | -56.573791 | [-108.182874, -11.975854] | -0.939869 | secondary |
| separate:attenuate | separate:shuffle | 0.1 | +30.138294 | [-34.943249, +98.160644] | +0.493582 | secondary |
| separate:attenuate | separate:sham_plus | 0.1 | -53.329136 | [-94.299222, -14.590388] | -0.885488 | secondary |
| separate:attenuate | separate:sham_minus | 0.1 | -22.125956 | [-73.791584, +19.397010] | -0.365490 | secondary |
| separate:sham_plus | starting | 0.1 | +462.861712 | [+310.976474, +620.750583] | +7.136943 | secondary |
| separate:sham_plus | separate:passive | 0.1 | -3.244655 | [-46.004442, +36.807134] | -0.053904 | secondary |
| separate:sham_plus | separate:shuffle | 0.1 | +83.467430 | [+14.120828, +158.313698] | +1.366965 | secondary |
| separate:sham_minus | starting | 0.1 | +431.658532 | [+278.823486, +588.270586] | +6.655816 | secondary |
| separate:sham_minus | separate:passive | 0.1 | -34.447835 | [-68.582600, -0.907560] | -0.572287 | secondary |
| separate:sham_minus | separate:shuffle | 0.1 | +52.264250 | [-18.242099, +124.671584] | +0.855943 | secondary |
| separate:sham_minus | separate:sham_plus | 0.1 | -31.203180 | [-80.376797, +19.166653] | -0.518104 | secondary |
| separate:attenuate | separate:mean_sham_loss | 0.1 | -37.727546 | [-75.018248, -4.375265] | -0.624817 | secondary |
| separate:mean_sham_loss | starting | 0.1 | +447.260122 | [+296.855971, +601.640228] | +6.896379 | secondary |
| separate:mean_sham_loss | separate:passive | 0.1 | -18.846245 | [-47.646288, +8.871003] | -0.313096 | secondary |
| one_copy | starting | 0.1 | +346.671860 | [+227.108071, +471.990659] | +5.345392 | secondary |
| separate:passive | one_copy | 0.1 | +119.434506 | [+29.030995, +215.377187] | +1.945580 | secondary |
| separate:shuffle | one_copy | 0.1 | +32.722422 | [-43.872494, +110.248838] | +0.533046 | secondary |
| separate:attenuate | one_copy | 0.1 | +62.860716 | [-0.302869, +125.649821] | +1.023997 | secondary |
| separate:sham_plus | one_copy | 0.1 | +116.189852 | [+36.534579, +197.638866] | +1.892724 | secondary |
| separate:sham_minus | one_copy | 0.1 | +84.986672 | [+4.893930, +171.935379] | +1.384427 | secondary |
| separate:mean_sham_loss | one_copy | 0.1 | +100.588262 | [+23.597748, +180.058438] | +1.638576 | secondary |
| mean:passive | separate:passive | 0.1 | -39.641073 | [-95.632194, +15.274101] | -0.658563 | secondary |
| mean:shuffle | separate:shuffle | 0.1 | -41.710566 | [-95.631617, +13.948071] | -0.683103 | secondary |
| mean:attenuate | separate:attenuate | 0.1 | -29.812922 | [-72.142581, +15.888788] | -0.490675 | secondary |
| mean:sham_plus | separate:sham_plus | 0.1 | -41.180962 | [-76.235234, -4.943482] | -0.683777 | secondary |
| mean:sham_minus | separate:sham_minus | 0.1 | -18.965704 | [-77.245799, +40.423844] | -0.313287 | secondary |
| mean:passive | one_copy | 0.1 | +79.793434 | [+6.932038, +157.269995] | +1.299829 | secondary |
| mean:passive | starting | 0.1 | +426.465294 | [+286.393327, +574.443651] | +6.575740 | secondary |
| mean:shuffle | one_copy | 0.1 | -8.988144 | [-95.232470, +80.114293] | -0.146416 | secondary |
| mean:shuffle | starting | 0.1 | +337.683716 | [+199.384482, +484.815624] | +5.206802 | secondary |
| mean:attenuate | one_copy | 0.1 | +33.047794 | [-31.636400, +101.936479] | +0.538346 | secondary |
| mean:attenuate | starting | 0.1 | +379.719654 | [+248.383235, +518.600944] | +5.854961 | secondary |
| mean:sham_plus | one_copy | 0.1 | +75.008890 | [+3.275221, +151.514936] | +1.221889 | secondary |
| mean:sham_plus | starting | 0.1 | +421.680750 | [+284.482059, +568.640626] | +6.501966 | secondary |
| mean:sham_minus | one_copy | 0.1 | +66.020968 | [-3.114963, +140.682706] | +1.075477 | secondary |
| mean:sham_minus | starting | 0.1 | +412.692828 | [+272.166722, +559.452904] | +6.363380 | secondary |
| mean:shuffle | mean:passive | 0.1 | -88.781577 | [-155.801458, -25.356204] | -1.465292 | secondary |
| mean:attenuate | mean:passive | 0.1 | -46.745640 | [-71.998962, -23.033461] | -0.771511 | secondary |
| mean:attenuate | mean:shuffle | 0.1 | +42.035937 | [-22.202779, +108.435281] | +0.683761 | secondary |
| mean:attenuate | mean:sham_plus | 0.1 | -41.961096 | [-66.377858, -18.282195] | -0.691999 | secondary |
| mean:attenuate | mean:sham_minus | 0.1 | -32.973174 | [-59.931122, -7.819772] | -0.542970 | secondary |
| mean:sham_plus | mean:passive | 0.1 | -4.784544 | [-24.780853, +14.107054] | -0.078966 | secondary |
| mean:sham_plus | mean:shuffle | 0.1 | +83.997033 | [+20.303957, +151.674266] | +1.366305 | secondary |
| mean:sham_minus | mean:passive | 0.1 | -13.772466 | [-31.971109, +2.999200] | -0.227307 | secondary |
| mean:sham_minus | mean:shuffle | 0.1 | +75.009111 | [+10.479401, +143.246056] | +1.220107 | secondary |
| mean:sham_minus | mean:sham_plus | 0.1 | -8.987922 | [-36.060351, +18.495675] | -0.148224 | secondary |
| mean:mean_sham_loss | mean:passive | 0.1 | -9.278505 | [-21.743840, +2.835255] | -0.153137 | secondary |
| mean:mean_sham_loss | one_copy | 0.1 | +70.514929 | [+1.515387, +145.036489] | +1.148683 | secondary |
| mean:mean_sham_loss | starting | 0.1 | +417.186789 | [+278.659485, +563.301664] | +6.432673 | secondary |
| mean:mean_sham_loss | separate:mean_sham_loss | 0.1 | -30.073333 | [-75.206172, +16.652740] | -0.498053 | secondary |
| mean:attenuate | mean:mean_sham_loss | 0.1 | -37.467135 | [-58.904042, -16.858318] | -0.617429 | secondary |
| tied:passive | separate:passive | 0.1 | -12.658283 | [-65.717342, +39.590555] | -0.210294 | secondary |
| tied:passive | mean:passive | 0.1 | +26.982789 | [+12.648287, +41.590588] | +0.445336 | secondary |
| tied:passive | starting | 0.1 | +453.448083 | [+306.463655, +606.664928] | +6.991792 | secondary |
| tied:passive | one_copy | 0.1 | +106.776223 | [+27.961290, +189.610948] | +1.739377 | secondary |
| tied:shuffle | separate:shuffle | 0.1 | -35.189908 | [-89.147807, +20.329036] | -0.576313 | secondary |
| tied:shuffle | mean:shuffle | 0.1 | +6.520658 | [-7.658688, +20.650628] | +0.106066 | secondary |
| tied:shuffle | starting | 0.1 | +344.204374 | [+199.034762, +497.811824] | +5.307345 | secondary |
| tied:shuffle | one_copy | 0.1 | -2.467486 | [-92.312468, +90.844011] | -0.040195 | secondary |
| tied:attenuate | separate:attenuate | 0.1 | -0.999529 | [-40.192227, +43.024563] | -0.016451 | secondary |
| tied:attenuate | mean:attenuate | 0.1 | +28.813393 | [+15.572015, +42.310057] | +0.471909 | secondary |
| tied:attenuate | starting | 0.1 | +408.533047 | [+269.705157, +553.515509] | +6.299240 | secondary |
| tied:attenuate | one_copy | 0.1 | +61.861187 | [-7.763906, +135.073300] | +1.007714 | secondary |
| tied:sham_plus | separate:sham_plus | 0.1 | -12.348308 | [-45.312645, +22.321926] | -0.205034 | secondary |
| tied:sham_plus | mean:sham_plus | 0.1 | +28.832654 | [+16.833552, +40.891611] | +0.475492 | secondary |
| tied:sham_plus | starting | 0.1 | +450.513404 | [+306.471204, +602.656367] | +6.946542 | secondary |
| tied:sham_plus | one_copy | 0.1 | +103.841543 | [+28.648370, +183.911191] | +1.691571 | secondary |
| tied:sham_minus | separate:sham_minus | 0.1 | +7.584381 | [-49.344974, +66.189770] | +0.125283 | secondary |
| tied:sham_minus | mean:sham_minus | 0.1 | +26.550085 | [+12.158107, +41.072747] | +0.437201 | secondary |
| tied:sham_minus | starting | 0.1 | +439.242913 | [+291.351528, +591.765622] | +6.772760 | secondary |
| tied:sham_minus | one_copy | 0.1 | +92.571053 | [+17.962955, +171.480422] | +1.507976 | secondary |
| tied:shuffle | tied:passive | 0.1 | -109.243709 | [-183.178705, -38.531656] | -1.811074 | secondary |
| tied:attenuate | tied:passive | 0.1 | -44.915037 | [-73.251462, -18.589216] | -0.744614 | secondary |
| tied:sham_plus | tied:passive | 0.1 | -2.934680 | [-27.041352, +20.038636] | -0.048652 | secondary |
| tied:sham_minus | tied:passive | 0.1 | -14.205170 | [-34.091275, +4.421396] | -0.235497 | secondary |
| tied:mean_sham_loss | tied:passive | 0.1 | -8.569925 | [-23.871128, +6.366663] | -0.142075 | secondary |
| tied:attenuate | tied:shuffle | 0.1 | +64.328672 | [-5.548311, +137.353956] | +1.047488 | secondary |
| tied:attenuate | tied:sham_plus | 0.1 | -41.980357 | [-67.783452, -16.901471] | -0.695624 | secondary |
| tied:attenuate | tied:sham_minus | 0.1 | -30.709866 | [-60.620949, -3.271091] | -0.507921 | secondary |
| tied:attenuate | tied:mean_sham_loss | 0.1 | -36.345112 | [-59.510016, -14.424416] | -0.601685 | secondary |
| tied:mean_sham_loss | starting | 0.1 | +444.878158 | [+300.269430, +595.608434] | +6.859651 | secondary |
| tied:mean_sham_loss | one_copy | 0.1 | +98.206298 | [+24.734719, +176.282821] | +1.599774 | secondary |
| tied:mean_sham_loss | separate:mean_sham_loss | 0.1 | -2.381963 | [-45.823228, +42.953875] | -0.039448 | secondary |
| tied:mean_sham_loss | mean:mean_sham_loss | 0.1 | +27.691369 | [+14.797821, +40.712885] | +0.456332 | secondary |

## All four selected cheaper-baseline comparisons

Unlike same-setting rows above, these use each cheap baseline's own frozen
development-selected setting.

| Candidate | Candidate alpha | Reference | Reference alpha | Gain ×10⁻⁶ | 95% interval ×10⁻⁶ | Relative gain % |
| --- | --- | --- | --- | --- | --- | --- |
| tied:sham_minus | 0.01 | starting | 0.001 | +251.589477 | [+120.424011, +382.580293] | +4.047572 |
| tied:sham_minus | 0.01 | one_copy | 0.01 | +54.878115 | [-17.808643, +126.763259] | +0.911733 |
| tied:passive | 0.01 | starting | 0.001 | +254.288922 | [+121.844800, +386.326966] | +4.091000 |
| tied:passive | 0.01 | one_copy | 0.01 | +57.577560 | [-19.709169, +134.726768] | +0.956581 |

## Every primary founder difference

One row per founder, already averaged over four lives, four groups and four
futures. These are descriptive contributions, not 64 independent hypothesis
tests. 30 are positive; 34 negative; none excluded.

| Founder | Gain ×10⁻⁶ MSE |
| --- | --- |
| 100000 | -13.771104 |
| 100001 | +25.296795 |
| 100002 | -6.116253 |
| 100003 | -9.778130 |
| 100004 | -19.400398 |
| 100005 | +10.529836 |
| 100006 | -115.534525 |
| 100007 | -81.371787 |
| 100008 | -30.406384 |
| 100009 | +29.385556 |
| 100010 | +9.946455 |
| 100011 | +41.930450 |
| 100012 | +81.947484 |
| 100013 | -38.257284 |
| 100014 | +36.179877 |
| 100015 | +26.800781 |
| 100016 | -10.403012 |
| 100017 | -206.962697 |
| 100018 | -0.372644 |
| 100019 | -18.506327 |
| 100020 | -149.618472 |
| 100021 | -32.784298 |
| 100022 | +113.788666 |
| 100023 | +86.103690 |
| 100024 | +35.228732 |
| 100025 | -42.319093 |
| 100026 | +70.337403 |
| 100027 | +32.844220 |
| 100028 | +167.254066 |
| 100029 | -32.467408 |
| 100030 | +10.133884 |
| 100031 | +398.200520 |
| 100032 | -46.761616 |
| 100033 | -13.296471 |
| 100034 | +44.570624 |
| 100035 | -118.997426 |
| 100036 | -283.971082 |
| 100037 | -27.717211 |
| 100038 | -43.733783 |
| 100039 | -12.678304 |
| 100040 | -46.216665 |
| 100041 | -38.583444 |
| 100042 | +88.098173 |
| 100043 | +45.543293 |
| 100044 | +2.926783 |
| 100045 | +108.934913 |
| 100046 | -10.359584 |
| 100047 | -29.542220 |
| 100048 | -15.578724 |
| 100049 | +9.165015 |
| 100050 | +30.804533 |
| 100051 | -0.690194 |
| 100052 | -101.025806 |
| 100053 | +20.854713 |
| 100054 | -115.534807 |
| 100055 | -68.225495 |
| 100056 | -35.369370 |
| 100057 | +27.753797 |
| 100058 | +81.772060 |
| 100059 | +42.405148 |
| 100060 | +28.105563 |
| 100061 | -110.692148 |
| 100062 | +41.183313 |
| 100063 | +6.253357 |

## All terminal apparatus conditions

A and B are supplied target families. Each entry averages all founders/lives
under future0; controls were not independently repeated in futures1–3.
Qualified/sign entries are own-minus-alternative preference in points.

| Target | Condition | Qualified preference points | Sign preference points |
| --- | --- | --- | --- |
| A | translated | 43.574524 | 44.073486 |
| A | aligned | 43.902588 | 44.497681 |
| A | copy | 42.988586 | 43.399048 |
| A | aligned_read_off | 18.440247 | 18.563843 |
| A | aligned_write_off | -0.520325 | -0.616455 |
| A | aligned_wrong | -29.365540 | -29.898071 |
| A | aligned_lesion | 17.160034 | 17.156982 |
| A | aligned_rescue | 43.815613 | 44.384766 |
| A | aligned_post_shuffle | -0.866699 | -0.830078 |
| A | aligned_pre_shuffle | 2.561951 | 2.575684 |
| A | ideal | 47.027588 | 47.665405 |
| A | zero | -0.520325 | -0.616455 |
| B | translated | 21.144104 | 21.414185 |
| B | aligned | 29.365540 | 29.898071 |
| B | copy | 33.848572 | 34.420776 |
| B | aligned_read_off | -18.440247 | -18.563843 |
| B | aligned_write_off | 0.520325 | 0.616455 |
| B | aligned_wrong | -43.902588 | -44.497681 |
| B | aligned_lesion | -19.323730 | -19.534302 |
| B | aligned_rescue | 27.088928 | 27.526855 |
| B | aligned_post_shuffle | 1.208496 | 1.199341 |
| B | aligned_pre_shuffle | -2.084351 | -2.261353 |
| B | ideal | 45.191956 | 46.035767 |
| B | zero | 0.520325 | 0.616455 |

## All 228 apparatus contrasts

Stages1–3 are descendant reads; stage4 is the terminal fresh read. Role0=A,
role1=B, role both=their equally weighted mean. Positive does not universally
mean a required passing gate: protected-copy comparisons, early-stage zeros and
directional exceptions must remain visible.

| Contrast | Stage | Role | Readout | Effect points | 95% interval points |
| --- | --- | --- | --- | --- | --- |
| aligned_minus_translated | 1 | 0 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 1 | 1 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 1 | both | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | 0 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | 1 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | both | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_read_off | 1 | 0 | qualified | +43.229675 | [+41.743469, +44.717407] |
| aligned_minus_aligned_read_off | 1 | 1 | qualified | +33.137512 | [+31.339989, +34.960976] |
| aligned_minus_aligned_read_off | 1 | both | qualified | +38.183594 | [+37.587700, +38.752747] |
| aligned_minus_aligned_write_off | 1 | 0 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_write_off | 1 | 1 | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_write_off | 1 | both | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_wrong | 1 | 0 | qualified | +76.367188 | [+75.175400, +77.505493] |
| aligned_minus_aligned_wrong | 1 | 1 | qualified | +76.367188 | [+75.175400, +77.505493] |
| aligned_minus_aligned_wrong | 1 | both | qualified | +76.367188 | [+75.175400, +77.505493] |
| aligned_minus_aligned_lesion | 1 | 0 | qualified | +40.599060 | [+39.263916, +41.888428] |
| aligned_minus_aligned_lesion | 1 | 1 | qualified | +37.246704 | [+35.739136, +38.777199] |
| aligned_minus_aligned_lesion | 1 | both | qualified | +38.922882 | [+37.930279, +39.875813] |
| aligned_rescue_minus_aligned_lesion | 1 | 0 | qualified | +40.605164 | [+39.263916, +41.899109] |
| aligned_rescue_minus_aligned_lesion | 1 | 1 | qualified | +37.260437 | [+35.752831, +38.790894] |
| aligned_rescue_minus_aligned_lesion | 1 | both | qualified | +38.932800 | [+37.935638, +39.889545] |
| translated_minus_copy | 1 | 0 | qualified | +0.000000 | [+0.000000, +0.000000] |
| translated_minus_copy | 1 | 1 | qualified | +0.000000 | [+0.000000, +0.000000] |
| translated_minus_copy | 1 | both | qualified | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 2 | 0 | qualified | +0.271606 | [-0.068665, +0.616455] |
| aligned_minus_translated | 2 | 1 | qualified | +3.042603 | [+2.073631, +4.020691] |
| aligned_minus_translated | 2 | both | qualified | +1.657104 | [+1.127625, +2.177429] |
| aligned_minus_copy | 2 | 0 | qualified | +0.697327 | [+0.524864, +0.871277] |
| aligned_minus_copy | 2 | 1 | qualified | -1.789856 | [-2.276611, -1.295433] |
| aligned_minus_copy | 2 | both | qualified | -0.546265 | [-0.802612, -0.283051] |
| aligned_minus_aligned_read_off | 2 | 0 | qualified | +43.138123 | [+41.792259, +44.519043] |
| aligned_minus_aligned_read_off | 2 | 1 | qualified | +32.148743 | [+30.313110, +33.888245] |
| aligned_minus_aligned_read_off | 2 | both | qualified | +37.643433 | [+36.917114, +38.352985] |
| aligned_minus_aligned_write_off | 2 | 0 | qualified | +43.138123 | [+41.792259, +44.519043] |
| aligned_minus_aligned_write_off | 2 | 1 | qualified | +32.148743 | [+30.313110, +33.888245] |
| aligned_minus_aligned_write_off | 2 | both | qualified | +37.643433 | [+36.917114, +38.352985] |
| aligned_minus_aligned_wrong | 2 | 0 | qualified | +75.286865 | [+73.834229, +76.705971] |
| aligned_minus_aligned_wrong | 2 | 1 | qualified | +75.286865 | [+73.834229, +76.705971] |
| aligned_minus_aligned_wrong | 2 | both | qualified | +75.286865 | [+73.834229, +76.705971] |
| aligned_minus_aligned_lesion | 2 | 0 | qualified | +30.041504 | [+28.565979, +31.547546] |
| aligned_minus_aligned_lesion | 2 | 1 | qualified | +46.995544 | [+45.188904, +48.854065] |
| aligned_minus_aligned_lesion | 2 | both | qualified | +38.518524 | [+37.393932, +39.661427] |
| aligned_rescue_minus_aligned_lesion | 2 | 0 | qualified | +29.588318 | [+28.128014, +31.085205] |
| aligned_rescue_minus_aligned_lesion | 2 | 1 | qualified | +44.151306 | [+42.228661, +46.096840] |
| aligned_rescue_minus_aligned_lesion | 2 | both | qualified | +36.869812 | [+35.768127, +37.999744] |
| translated_minus_copy | 2 | 0 | qualified | +0.425720 | [+0.106812, +0.737000] |
| translated_minus_copy | 2 | 1 | qualified | -4.832458 | [-5.921936, -3.793335] |
| translated_minus_copy | 2 | both | qualified | -2.203369 | [-2.777100, -1.645660] |
| aligned_minus_translated | 3 | 0 | qualified | +0.631714 | [+0.379906, +0.883484] |
| aligned_minus_translated | 3 | 1 | qualified | +5.084229 | [+3.689537, +6.465149] |
| aligned_minus_translated | 3 | both | qualified | +2.857971 | [+2.149944, +3.563709] |
| aligned_minus_copy | 3 | 0 | qualified | +0.779724 | [+0.601196, +0.959778] |
| aligned_minus_copy | 3 | 1 | qualified | -3.450012 | [-4.338112, -2.578735] |
| aligned_minus_copy | 3 | both | qualified | -1.335144 | [-1.789093, -0.884991] |
| aligned_minus_aligned_read_off | 3 | 0 | qualified | +44.926453 | [+43.214378, +46.623230] |
| aligned_minus_aligned_read_off | 3 | 1 | qualified | +29.470825 | [+26.829453, +32.142639] |
| aligned_minus_aligned_read_off | 3 | both | qualified | +37.198639 | [+36.344128, +38.046265] |
| aligned_minus_aligned_write_off | 3 | 0 | qualified | +44.926453 | [+43.214378, +46.623230] |
| aligned_minus_aligned_write_off | 3 | 1 | qualified | +29.470825 | [+26.829453, +32.142639] |
| aligned_minus_aligned_write_off | 3 | both | qualified | +37.198639 | [+36.344128, +38.046265] |
| aligned_minus_aligned_wrong | 3 | 0 | qualified | +74.397278 | [+72.688255, +76.092529] |
| aligned_minus_aligned_wrong | 3 | 1 | qualified | +74.397278 | [+72.688255, +76.092529] |
| aligned_minus_aligned_wrong | 3 | both | qualified | +74.397278 | [+72.688255, +76.092529] |
| aligned_minus_aligned_lesion | 3 | 0 | qualified | +27.804565 | [+26.309166, +29.330482] |
| aligned_minus_aligned_lesion | 3 | 1 | qualified | +49.021912 | [+46.897888, +51.188698] |
| aligned_minus_aligned_lesion | 3 | both | qualified | +38.413239 | [+37.214642, +39.612617] |
| aligned_rescue_minus_aligned_lesion | 3 | 0 | qualified | +27.624512 | [+26.126099, +29.147339] |
| aligned_rescue_minus_aligned_lesion | 3 | 1 | qualified | +46.485901 | [+44.352722, +48.625183] |
| aligned_rescue_minus_aligned_lesion | 3 | both | qualified | +37.055206 | [+35.896282, +38.211079] |
| translated_minus_copy | 3 | 0 | qualified | +0.148010 | [-0.109863, +0.401306] |
| translated_minus_copy | 3 | 1 | qualified | -8.534241 | [-10.084572, -7.015953] |
| translated_minus_copy | 3 | both | qualified | -4.193115 | [-4.985828, -3.417206] |
| aligned_minus_translated | 4 | 0 | qualified | +0.328064 | [+0.027466, +0.631714] |
| aligned_minus_translated | 4 | 1 | qualified | +8.221436 | [+6.384277, +10.151711] |
| aligned_minus_translated | 4 | both | qualified | +4.274750 | [+3.352337, +5.246735] |
| aligned_minus_copy | 4 | 0 | qualified | +0.914001 | [+0.672913, +1.159668] |
| aligned_minus_copy | 4 | 1 | qualified | -4.483032 | [-5.474854, -3.498840] |
| aligned_minus_copy | 4 | both | qualified | -1.784515 | [-2.278137, -1.301575] |
| aligned_minus_aligned_read_off | 4 | 0 | qualified | +25.462341 | [+23.762512, +27.131653] |
| aligned_minus_aligned_read_off | 4 | 1 | qualified | +47.805786 | [+45.190392, +50.442543] |
| aligned_minus_aligned_read_off | 4 | both | qualified | +36.634064 | [+35.694103, +37.557240] |
| aligned_minus_aligned_write_off | 4 | 0 | qualified | +44.422913 | [+42.948914, +45.904541] |
| aligned_minus_aligned_write_off | 4 | 1 | qualified | +28.845215 | [+26.583824, +31.111145] |
| aligned_minus_aligned_write_off | 4 | both | qualified | +36.634064 | [+35.694103, +37.557240] |
| aligned_minus_aligned_wrong | 4 | 0 | qualified | +73.268127 | [+71.388206, +75.114479] |
| aligned_minus_aligned_wrong | 4 | 1 | qualified | +73.268127 | [+71.388206, +75.114479] |
| aligned_minus_aligned_wrong | 4 | both | qualified | +73.268127 | [+71.388206, +75.114479] |
| aligned_minus_aligned_lesion | 4 | 0 | qualified | +26.742554 | [+25.201416, +28.285217] |
| aligned_minus_aligned_lesion | 4 | 1 | qualified | +48.689270 | [+46.356125, +51.091042] |
| aligned_minus_aligned_lesion | 4 | both | qualified | +37.715912 | [+36.374664, +39.077015] |
| aligned_rescue_minus_aligned_lesion | 4 | 0 | qualified | +26.655579 | [+25.163269, +28.166199] |
| aligned_rescue_minus_aligned_lesion | 4 | 1 | qualified | +46.412659 | [+44.078064, +48.791504] |
| aligned_rescue_minus_aligned_lesion | 4 | both | qualified | +36.534119 | [+35.230980, +37.851715] |
| translated_minus_copy | 4 | 0 | qualified | +0.585938 | [+0.286865, +0.891113] |
| translated_minus_copy | 4 | 1 | qualified | -12.704468 | [-14.762917, -10.726929] |
| translated_minus_copy | 4 | both | qualified | -6.059265 | [-7.129669, -5.023937] |
| aligned_minus_aligned_post_shuffle | 4 | 0 | qualified | +44.769287 | [+43.304443, +46.261597] |
| aligned_minus_aligned_post_shuffle | 4 | 1 | qualified | +28.157043 | [+25.796394, +30.484047] |
| aligned_minus_aligned_post_shuffle | 4 | both | qualified | +36.463165 | [+35.152435, +37.764759] |
| aligned_minus_aligned_pre_shuffle | 4 | 0 | qualified | +41.340637 | [+40.020752, +42.665100] |
| aligned_minus_aligned_pre_shuffle | 4 | 1 | qualified | +31.449890 | [+29.161072, +33.766212] |
| aligned_minus_aligned_pre_shuffle | 4 | both | qualified | +36.395264 | [+35.145531, +37.670898] |
| ideal_minus_zero | 4 | 0 | qualified | +47.547913 | [+46.099815, +49.011307] |
| ideal_minus_zero | 4 | 1 | qualified | +44.671631 | [+43.196068, +46.133461] |
| ideal_minus_zero | 4 | both | qualified | +46.109772 | [+45.983887, +46.235657] |
| copy_minus_zero | 4 | 0 | qualified | +43.508911 | [+42.057762, +44.970741] |
| copy_minus_zero | 4 | 1 | qualified | +33.328247 | [+31.401024, +35.209656] |
| copy_minus_zero | 4 | both | qualified | +38.418579 | [+37.820435, +38.996143] |
| aligned_minus_zero | 4 | 0 | qualified | +44.422913 | [+42.948914, +45.904541] |
| aligned_minus_zero | 4 | 1 | qualified | +28.845215 | [+26.583824, +31.111145] |
| aligned_minus_zero | 4 | both | qualified | +36.634064 | [+35.694103, +37.557240] |
| translated_minus_zero | 4 | 0 | qualified | +44.094849 | [+42.611656, +45.599403] |
| translated_minus_zero | 4 | 1 | qualified | +20.623779 | [+17.636070, +23.541260] |
| translated_minus_zero | 4 | both | qualified | +32.359314 | [+31.008911, +33.659363] |
| aligned_minus_translated | 1 | 0 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 1 | 1 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 1 | both | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | 0 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | 1 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_copy | 1 | both | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_read_off | 1 | 0 | sign | +43.786621 | [+42.208862, +45.355225] |
| aligned_minus_aligned_read_off | 1 | 1 | sign | +33.798218 | [+31.912155, +35.720825] |
| aligned_minus_aligned_read_off | 1 | both | sign | +38.792419 | [+38.182068, +39.384460] |
| aligned_minus_aligned_write_off | 1 | 0 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_write_off | 1 | 1 | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_write_off | 1 | both | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_aligned_wrong | 1 | 0 | sign | +77.584839 | [+76.364136, +78.768921] |
| aligned_minus_aligned_wrong | 1 | 1 | sign | +77.584839 | [+76.364136, +78.768921] |
| aligned_minus_aligned_wrong | 1 | both | sign | +77.584839 | [+76.364136, +78.768921] |
| aligned_minus_aligned_lesion | 1 | 0 | sign | +41.171265 | [+39.840698, +42.477417] |
| aligned_minus_aligned_lesion | 1 | 1 | sign | +38.015747 | [+36.480713, +39.578247] |
| aligned_minus_aligned_lesion | 1 | both | sign | +39.593506 | [+38.607788, +40.550232] |
| aligned_rescue_minus_aligned_lesion | 1 | 0 | sign | +41.180420 | [+39.852829, +42.483521] |
| aligned_rescue_minus_aligned_lesion | 1 | 1 | sign | +38.009644 | [+36.477661, +39.566040] |
| aligned_rescue_minus_aligned_lesion | 1 | both | sign | +39.595032 | [+38.613892, +40.550270] |
| translated_minus_copy | 1 | 0 | sign | +0.000000 | [+0.000000, +0.000000] |
| translated_minus_copy | 1 | 1 | sign | +0.000000 | [+0.000000, +0.000000] |
| translated_minus_copy | 1 | both | sign | +0.000000 | [+0.000000, +0.000000] |
| aligned_minus_translated | 2 | 0 | sign | +0.128174 | [-0.222778, +0.491333] |
| aligned_minus_translated | 2 | 1 | sign | +3.134155 | [+2.127075, +4.153442] |
| aligned_minus_translated | 2 | both | sign | +1.631165 | [+1.071129, +2.183571] |
| aligned_minus_copy | 2 | 0 | sign | +0.698853 | [+0.500488, +0.906372] |
| aligned_minus_copy | 2 | 1 | sign | -1.849365 | [-2.340698, -1.348877] |
| aligned_minus_copy | 2 | both | sign | -0.575256 | [-0.828552, -0.309753] |
| aligned_minus_aligned_read_off | 2 | 0 | sign | +43.829346 | [+42.443848, +45.263748] |
| aligned_minus_aligned_read_off | 2 | 1 | sign | +32.449341 | [+30.526733, +34.274368] |
| aligned_minus_aligned_read_off | 2 | both | sign | +38.139343 | [+37.422142, +38.847351] |
| aligned_minus_aligned_write_off | 2 | 0 | sign | +43.829346 | [+42.443848, +45.263748] |
| aligned_minus_aligned_write_off | 2 | 1 | sign | +32.449341 | [+30.526733, +34.274368] |
| aligned_minus_aligned_write_off | 2 | both | sign | +38.139343 | [+37.422142, +38.847351] |
| aligned_minus_aligned_wrong | 2 | 0 | sign | +76.278687 | [+74.844284, +77.694702] |
| aligned_minus_aligned_wrong | 2 | 1 | sign | +76.278687 | [+74.844284, +77.694702] |
| aligned_minus_aligned_wrong | 2 | both | sign | +76.278687 | [+74.844284, +77.694702] |
| aligned_minus_aligned_lesion | 2 | 0 | sign | +30.337524 | [+28.857422, +31.851196] |
| aligned_minus_aligned_lesion | 2 | 1 | sign | +47.708130 | [+45.864868, +49.603348] |
| aligned_minus_aligned_lesion | 2 | both | sign | +39.022827 | [+37.878418, +40.185547] |
| aligned_rescue_minus_aligned_lesion | 2 | 0 | sign | +29.882813 | [+28.399658, +31.396484] |
| aligned_rescue_minus_aligned_lesion | 2 | 1 | sign | +44.808960 | [+42.855835, +46.789551] |
| aligned_rescue_minus_aligned_lesion | 2 | both | sign | +37.345886 | [+36.216736, +38.493347] |
| translated_minus_copy | 2 | 0 | sign | +0.570679 | [+0.192261, +0.952148] |
| translated_minus_copy | 2 | 1 | sign | -4.983521 | [-6.112747, -3.903122] |
| translated_minus_copy | 2 | both | sign | -2.206421 | [-2.824402, -1.611290] |
| aligned_minus_translated | 3 | 0 | sign | +0.686646 | [+0.369263, +0.997925] |
| aligned_minus_translated | 3 | 1 | sign | +5.218506 | [+3.839111, +6.607132] |
| aligned_minus_translated | 3 | both | sign | +2.952576 | [+2.239990, +3.660622] |
| aligned_minus_copy | 3 | 0 | sign | +0.759888 | [+0.546265, +0.961304] |
| aligned_minus_copy | 3 | 1 | sign | -3.479004 | [-4.397583, -2.578735] |
| aligned_minus_copy | 3 | both | sign | -1.359558 | [-1.840210, -0.883484] |
| aligned_minus_aligned_read_off | 3 | 0 | sign | +45.474243 | [+43.722534, +47.204590] |
| aligned_minus_aligned_read_off | 3 | 1 | sign | +29.962158 | [+27.239990, +32.690506] |
| aligned_minus_aligned_read_off | 3 | both | sign | +37.718201 | [+36.848450, +38.583374] |
| aligned_minus_aligned_write_off | 3 | 0 | sign | +45.474243 | [+43.722534, +47.204590] |
| aligned_minus_aligned_write_off | 3 | 1 | sign | +29.962158 | [+27.239990, +32.690506] |
| aligned_minus_aligned_write_off | 3 | both | sign | +37.718201 | [+36.848450, +38.583374] |
| aligned_minus_aligned_wrong | 3 | 0 | sign | +75.436401 | [+73.696899, +77.166748] |
| aligned_minus_aligned_wrong | 3 | 1 | sign | +75.436401 | [+73.696899, +77.166748] |
| aligned_minus_aligned_wrong | 3 | both | sign | +75.436401 | [+73.696899, +77.166748] |
| aligned_minus_aligned_lesion | 3 | 0 | sign | +28.152466 | [+26.599121, +29.708862] |
| aligned_minus_aligned_lesion | 3 | 1 | sign | +49.688721 | [+47.546310, +51.870728] |
| aligned_minus_aligned_lesion | 3 | both | sign | +38.920593 | [+37.686119, +40.159607] |
| aligned_rescue_minus_aligned_lesion | 3 | 0 | sign | +27.905273 | [+26.382446, +29.449463] |
| aligned_rescue_minus_aligned_lesion | 3 | 1 | sign | +47.094727 | [+44.979858, +49.209671] |
| aligned_rescue_minus_aligned_lesion | 3 | both | sign | +37.500000 | [+36.323509, +38.676453] |
| translated_minus_copy | 3 | 0 | sign | +0.073242 | [-0.238037, +0.369339] |
| translated_minus_copy | 3 | 1 | sign | -8.697510 | [-10.287476, -7.147217] |
| translated_minus_copy | 3 | both | sign | -4.312134 | [-5.128517, -3.511047] |
| aligned_minus_translated | 4 | 0 | sign | +0.424194 | [+0.088501, +0.756836] |
| aligned_minus_translated | 4 | 1 | sign | +8.483887 | [+6.622314, +10.421753] |
| aligned_minus_translated | 4 | both | sign | +4.454041 | [+3.532410, +5.422974] |
| aligned_minus_copy | 4 | 0 | sign | +1.098633 | [+0.860596, +1.339798] |
| aligned_minus_copy | 4 | 1 | sign | -4.522705 | [-5.578613, -3.485031] |
| aligned_minus_copy | 4 | both | sign | -1.712036 | [-2.252235, -1.181030] |
| aligned_minus_aligned_read_off | 4 | 0 | sign | +25.933838 | [+24.203491, +27.621460] |
| aligned_minus_aligned_read_off | 4 | 1 | sign | +48.461914 | [+45.806808, +51.135254] |
| aligned_minus_aligned_read_off | 4 | both | sign | +37.197876 | [+36.230469, +38.151588] |
| aligned_minus_aligned_write_off | 4 | 0 | sign | +45.114136 | [+43.551636, +46.676636] |
| aligned_minus_aligned_write_off | 4 | 1 | sign | +29.281616 | [+26.904297, +31.686401] |
| aligned_minus_aligned_write_off | 4 | both | sign | +37.197876 | [+36.230469, +38.151588] |
| aligned_minus_aligned_wrong | 4 | 0 | sign | +74.395752 | [+72.460938, +76.303177] |
| aligned_minus_aligned_wrong | 4 | 1 | sign | +74.395752 | [+72.460938, +76.303177] |
| aligned_minus_aligned_wrong | 4 | both | sign | +74.395752 | [+72.460938, +76.303177] |
| aligned_minus_aligned_lesion | 4 | 0 | sign | +27.340698 | [+25.814743, +28.869705] |
| aligned_minus_aligned_lesion | 4 | 1 | sign | +49.432373 | [+47.088623, +51.849365] |
| aligned_minus_aligned_lesion | 4 | both | sign | +38.386536 | [+37.048302, +39.747658] |
| aligned_rescue_minus_aligned_lesion | 4 | 0 | sign | +27.227783 | [+25.714111, +28.747559] |
| aligned_rescue_minus_aligned_lesion | 4 | 1 | sign | +47.061157 | [+44.702148, +49.453735] |
| aligned_rescue_minus_aligned_lesion | 4 | both | sign | +37.144470 | [+35.842896, +38.459778] |
| translated_minus_copy | 4 | 0 | sign | +0.674438 | [+0.347900, +1.000977] |
| translated_minus_copy | 4 | 1 | sign | -13.006592 | [-15.109253, -10.986328] |
| translated_minus_copy | 4 | both | sign | -6.166077 | [-7.250977, -5.113220] |
| aligned_minus_aligned_post_shuffle | 4 | 0 | sign | +45.327759 | [+43.817139, +46.872025] |
| aligned_minus_aligned_post_shuffle | 4 | 1 | sign | +28.698730 | [+26.321335, +31.036377] |
| aligned_minus_aligned_post_shuffle | 4 | both | sign | +37.013245 | [+35.668907, +38.349953] |
| aligned_minus_aligned_pre_shuffle | 4 | 0 | sign | +41.921997 | [+40.591431, +43.252563] |
| aligned_minus_aligned_pre_shuffle | 4 | 1 | sign | +32.159424 | [+29.776001, +34.564285] |
| aligned_minus_aligned_pre_shuffle | 4 | both | sign | +37.040710 | [+35.729942, +38.374329] |
| ideal_minus_zero | 4 | 0 | sign | +48.281860 | [+46.762085, +49.816895] |
| ideal_minus_zero | 4 | 1 | sign | +45.419312 | [+43.859787, +46.978760] |
| ideal_minus_zero | 4 | both | sign | +46.850586 | [+46.719360, +46.983376] |
| copy_minus_zero | 4 | 0 | sign | +44.015503 | [+42.486496, +45.550537] |
| copy_minus_zero | 4 | 1 | sign | +33.804321 | [+31.771774, +35.797195] |
| copy_minus_zero | 4 | both | sign | +38.909912 | [+38.301086, +39.500465] |
| aligned_minus_zero | 4 | 0 | sign | +45.114136 | [+43.551636, +46.676636] |
| aligned_minus_zero | 4 | 1 | sign | +29.281616 | [+26.904297, +31.686401] |
| aligned_minus_zero | 4 | both | sign | +37.197876 | [+36.230469, +38.151588] |
| translated_minus_zero | 4 | 0 | sign | +44.689941 | [+43.121338, +46.273804] |
| translated_minus_zero | 4 | 1 | sign | +20.797729 | [+17.694092, +23.864822] |
| translated_minus_zero | 4 | both | sign | +32.743835 | [+31.387329, +34.048500] |
