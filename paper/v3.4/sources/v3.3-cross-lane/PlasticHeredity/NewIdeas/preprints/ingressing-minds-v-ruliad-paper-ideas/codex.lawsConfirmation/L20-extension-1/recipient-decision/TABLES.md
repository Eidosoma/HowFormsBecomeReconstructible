# D198 complete development tables

Generated from pinned outputs by `scripts/report_l20_recipient_decision.py`.
[Interpretation](RESULTS.md). All values are development evidence.
Preference and paired changes are multiplied by 100 (points). Correlations,
RMS and clipping remain in native units; guide retention is percent.
Independent unit: founder block. No inferential interval is supplied.
A/B are known target families; writer context is also supplied.
Action-count columns are in order 0.75 / 1.0 / 1.25.

## Nested whole-founder validation

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 33.626302083 | 33.626302083 | 0/128/0 | 0.792873571 | 0.716187536 | 96.289062 | 0.950918670 | 0.000465393 |
| common | 34.739939372 | 34.562174479 | 128/0/0 | 0.811526789 | 0.739247613 | 97.005208 | 0.949073518 | 0.000470479 |
| family | 34.920501709 | 35.065205892 | 64/0/64 | 0.815880139 | 0.745767025 | 97.005208 | 0.948895118 | 0.000470479 |
| writer | 34.739939372 | 34.562174479 | 128/0/0 | 0.811526789 | 0.739247613 | 97.005208 | 0.949073518 | 0.000470479 |
| family_writer | 34.920501709 | 35.065205892 | 64/0/64 | 0.815880139 | 0.745767025 | 97.005208 | 0.948895118 | 0.000470479 |
| record_rule | 34.915924072 | 35.056559245 | 64/2/62 | 0.815842729 | 0.745662115 | 97.005208 | 0.948897883 | 0.000470479 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.289621989 | 92 | 29 | 7 | +1.418050130 | -0.128428141 |
| common | +0.175984701 | 42 | 18 | 68 | +0.228627523 | -0.052642822 |
| family | -0.004577637 | 0 | 2 | 126 | +0.000000000 | -0.004577637 |
| writer | +0.175984701 | 42 | 18 | 68 | +0.228627523 | -0.052642822 |
| family_writer | -0.004577637 | 0 | 2 | 126 | +0.000000000 | -0.004577637 |

Optimistic retrospective per-record maximum: 35.113016764 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Final fit on its own development cases

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 33.626302083 | 33.626302083 | 0/128/0 | 0.792873571 | 0.716187536 | 96.289062 | 0.950918670 | 0.000465393 |
| common | 34.739939372 | 34.562174479 | 128/0/0 | 0.811526789 | 0.739247613 | 97.005208 | 0.949073518 | 0.000470479 |
| family | 34.920501709 | 35.065205892 | 64/0/64 | 0.815880139 | 0.745767025 | 97.005208 | 0.948895118 | 0.000470479 |
| writer | 34.739939372 | 34.562174479 | 128/0/0 | 0.811526789 | 0.739247613 | 97.005208 | 0.949073518 | 0.000470479 |
| family_writer | 34.920501709 | 35.065205892 | 64/0/64 | 0.815880139 | 0.745767025 | 97.005208 | 0.948895118 | 0.000470479 |
| record_rule | 34.920501709 | 35.065205892 | 64/0/64 | 0.815880139 | 0.745767025 | 97.005208 | 0.948895118 | 0.000470479 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.294199626 | 94 | 29 | 5 | +1.422627767 | -0.128428141 |
| common | +0.180562337 | 42 | 18 | 68 | +0.233205160 | -0.052642822 |
| family | +0.000000000 | 0 | 0 | 128 | +0.000000000 | +0.000000000 |
| writer | +0.180562337 | 42 | 18 | 68 | +0.233205160 | -0.052642822 |
| family_writer | +0.000000000 | 0 | 0 | 128 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 35.113016764 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Development cohort transfer: new_to_old

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 31.904093424 | 31.904093424 | 0/64/0 | 0.766086135 | 0.678365069 | 94.531250 | 0.955108274 | 0.000518799 |
| common | 33.119710286 | 32.948811849 | 64/0/0 | 0.787315000 | 0.701762639 | 95.572917 | 0.953176571 | 0.000528971 |
| family | 33.294677734 | 33.475748698 | 32/0/32 | 0.791384873 | 0.707838192 | 95.572917 | 0.952992811 | 0.000528971 |
| writer | 33.119710286 | 32.948811849 | 64/0/0 | 0.787315000 | 0.701762639 | 95.572917 | 0.953176571 | 0.000528971 |
| family_writer | 33.294677734 | 33.475748698 | 32/0/32 | 0.791384873 | 0.707838192 | 95.572917 | 0.952992811 | 0.000528971 |
| record_rule | 33.294677734 | 33.425903320 | 32/12/20 | 0.791316809 | 0.707450310 | 95.572917 | 0.953069732 | 0.000528971 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.390584310 | 41 | 10 | 13 | +1.512654622 | -0.122070312 |
| common | +0.174967448 | 18 | 10 | 36 | +0.204467773 | -0.029500326 |
| family | +0.000000000 | 6 | 5 | 53 | +0.020345052 | -0.020345052 |
| writer | +0.174967448 | 18 | 10 | 36 | +0.204467773 | -0.029500326 |
| family_writer | +0.000000000 | 6 | 5 | 53 | +0.020345052 | -0.020345052 |

Optimistic retrospective per-record maximum: 33.540852865 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Development cohort transfer: old_to_new

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 35.348510742 | 35.348510742 | 0/64/0 | 0.819661006 | 0.754010004 | 98.046875 | 0.946729067 | 0.000411987 |
| common | 36.360168457 | 36.175537109 | 64/0/0 | 0.835738577 | 0.776732587 | 98.437500 | 0.944970466 | 0.000411987 |
| family | 36.546325684 | 36.654663086 | 32/0/32 | 0.840375405 | 0.783695858 | 98.437500 | 0.944797424 | 0.000411987 |
| writer | 36.360168457 | 36.175537109 | 64/0/0 | 0.835738577 | 0.776732587 | 98.437500 | 0.944970466 | 0.000411987 |
| family_writer | 36.546325684 | 36.654663086 | 32/0/32 | 0.840375405 | 0.783695858 | 98.437500 | 0.944797424 | 0.000411987 |
| record_rule | 36.546325684 | 36.654663086 | 32/0/32 | 0.840375405 | 0.783695858 | 98.437500 | 0.944797424 | 0.000411987 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.197814941 | 48 | 13 | 3 | +1.312255859 | -0.114440918 |
| common | +0.186157227 | 23 | 8 | 33 | +0.242614746 | -0.056457520 |
| family | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |
| writer | +0.186157227 | 23 | 8 | 33 | +0.242614746 | -0.056457520 |
| family_writer | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 36.685180664 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 90000

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 32.950846354 | 32.950846354 | 0/16/0 | 0.775840084 | 0.710433571 | 96.875000 | 0.948161014 | 0.000366211 |
| common | 35.701497396 | 35.367838542 | 16/0/0 | 0.804861868 | 0.745674539 | 98.958333 | 0.945810873 | 0.000325521 |
| family | 35.640462240 | 35.786946615 | 8/0/8 | 0.808437500 | 0.750871494 | 98.958333 | 0.945598117 | 0.000325521 |
| writer | 35.701497396 | 35.367838542 | 16/0/0 | 0.804861868 | 0.745674539 | 98.958333 | 0.945810873 | 0.000325521 |
| family_writer | 35.640462240 | 35.786946615 | 8/0/8 | 0.808437500 | 0.750871494 | 98.958333 | 0.945598117 | 0.000325521 |
| record_rule | 35.640462240 | 35.786946615 | 8/0/8 | 0.808437500 | 0.750871494 | 98.958333 | 0.945598117 | 0.000325521 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +2.689615885 | 11 | 3 | 2 | +2.734375000 | -0.044759115 |
| common | -0.061035156 | 1 | 4 | 11 | +0.020345052 | -0.081380208 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | -0.061035156 | 1 | 4 | 11 | +0.020345052 | -0.081380208 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 35.725911458 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 90005

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 34.729003906 | 34.729003906 | 0/16/0 | 0.823677144 | 0.756288398 | 98.958333 | 0.953820097 | 0.000447591 |
| common | 35.839843750 | 35.864257812 | 16/0/0 | 0.843928212 | 0.785727860 | 100.000000 | 0.950983202 | 0.000488281 |
| family | 36.149088542 | 36.429850260 | 8/0/8 | 0.850086475 | 0.794685969 | 100.000000 | 0.950453250 | 0.000488281 |
| writer | 35.839843750 | 35.864257812 | 16/0/0 | 0.843928212 | 0.785727860 | 100.000000 | 0.950983202 | 0.000488281 |
| family_writer | 36.149088542 | 36.429850260 | 8/0/8 | 0.850086475 | 0.794685969 | 100.000000 | 0.950453250 | 0.000488281 |
| record_rule | 36.149088542 | 36.429850260 | 8/0/8 | 0.850086475 | 0.794685969 | 100.000000 | 0.950453250 | 0.000488281 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.420084635 | 13 | 3 | 0 | +1.464843750 | -0.044759115 |
| common | +0.309244792 | 7 | 1 | 8 | +0.321451823 | -0.012207031 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.309244792 | 7 | 1 | 8 | +0.321451823 | -0.012207031 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 36.234537760 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 90010

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 27.445475260 | 27.445475260 | 0/16/0 | 0.681330188 | 0.557728237 | 90.625000 | 0.959966555 | 0.000488281 |
| common | 27.522786458 | 27.343750000 | 16/0/0 | 0.699634563 | 0.567723760 | 91.666667 | 0.958166555 | 0.000528971 |
| family | 27.718098958 | 27.945963542 | 8/0/8 | 0.702877609 | 0.572726876 | 91.666667 | 0.957926684 | 0.000528971 |
| writer | 27.522786458 | 27.343750000 | 16/0/0 | 0.699634563 | 0.567723760 | 91.666667 | 0.958166555 | 0.000528971 |
| family_writer | 27.718098958 | 27.945963542 | 8/0/8 | 0.702877609 | 0.572726876 | 91.666667 | 0.957926684 | 0.000528971 |
| record_rule | 27.718098958 | 27.945963542 | 8/0/8 | 0.702877609 | 0.572726876 | 91.666667 | 0.957926684 | 0.000528971 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.272623698 | 10 | 6 | 0 | +0.703938802 | -0.431315104 |
| common | +0.195312500 | 5 | 3 | 8 | +0.260416667 | -0.065104167 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.195312500 | 5 | 3 | 8 | +0.260416667 | -0.065104167 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 28.466796875 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 90015

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 32.491048177 | 32.491048177 | 0/16/0 | 0.783497125 | 0.689010070 | 91.666667 | 0.958485428 | 0.000773112 |
| common | 33.414713542 | 33.219401042 | 16/0/0 | 0.800835357 | 0.707924399 | 91.666667 | 0.957745653 | 0.000773112 |
| family | 33.671061198 | 33.740234375 | 8/0/8 | 0.804137908 | 0.713068428 | 91.666667 | 0.957993193 | 0.000773112 |
| writer | 33.414713542 | 33.219401042 | 16/0/0 | 0.800835357 | 0.707924399 | 91.666667 | 0.957745653 | 0.000773112 |
| family_writer | 33.671061198 | 33.740234375 | 8/0/8 | 0.804137908 | 0.713068428 | 91.666667 | 0.957993193 | 0.000773112 |
| record_rule | 33.634440104 | 33.671061198 | 8/2/6 | 0.803838626 | 0.712229149 | 91.666667 | 0.958015317 | 0.000773112 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.143391927 | 10 | 4 | 2 | +1.192220052 | -0.048828125 |
| common | +0.219726563 | 6 | 2 | 8 | +0.256347656 | -0.036621094 |
| family | -0.036621094 | 0 | 2 | 14 | +0.000000000 | -0.036621094 |
| writer | +0.219726563 | 6 | 2 | 8 | +0.256347656 | -0.036621094 |
| family_writer | -0.036621094 | 0 | 2 | 14 | +0.000000000 | -0.036621094 |

Optimistic retrospective per-record maximum: 33.736165365 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 120000

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 38.385009766 | 38.385009766 | 0/16/0 | 0.881085209 | 0.830268572 | 100.000000 | 0.944945875 | 0.000183105 |
| common | 39.636230469 | 39.300537109 | 16/0/0 | 0.896348856 | 0.855156571 | 100.000000 | 0.943038821 | 0.000122070 |
| family | 39.703369141 | 39.709472656 | 8/0/8 | 0.898336241 | 0.859332984 | 100.000000 | 0.942630864 | 0.000122070 |
| writer | 39.636230469 | 39.300537109 | 16/0/0 | 0.896348856 | 0.855156571 | 100.000000 | 0.943038821 | 0.000122070 |
| family_writer | 39.703369141 | 39.709472656 | 8/0/8 | 0.898336241 | 0.859332984 | 100.000000 | 0.942630864 | 0.000122070 |
| record_rule | 39.703369141 | 39.709472656 | 8/0/8 | 0.898336241 | 0.859332984 | 100.000000 | 0.942630864 | 0.000122070 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.318359375 | 12 | 4 | 0 | +1.440429688 | -0.122070312 |
| common | +0.067138672 | 5 | 3 | 8 | +0.219726562 | -0.152587891 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.067138672 | 5 | 3 | 8 | +0.219726562 | -0.152587891 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 39.880371094 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 120005

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 32.135009766 | 32.135009766 | 0/16/0 | 0.750648617 | 0.662660452 | 93.750000 | 0.950291875 | 0.000610352 |
| common | 32.165527344 | 31.927490234 | 16/0/0 | 0.759071945 | 0.663992121 | 93.750000 | 0.950039408 | 0.000610352 |
| family | 32.324218750 | 32.476806641 | 8/0/8 | 0.763755470 | 0.670458844 | 93.750000 | 0.949681092 | 0.000610352 |
| writer | 32.165527344 | 31.927490234 | 16/0/0 | 0.759071945 | 0.663992121 | 93.750000 | 0.950039408 | 0.000610352 |
| family_writer | 32.324218750 | 32.476806641 | 8/0/8 | 0.763755470 | 0.670458844 | 93.750000 | 0.949681092 | 0.000610352 |
| record_rule | 32.324218750 | 32.476806641 | 8/0/8 | 0.763755470 | 0.670458844 | 93.750000 | 0.949681092 | 0.000610352 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.189208984 | 11 | 5 | 0 | +0.451660156 | -0.262451172 |
| common | +0.158691406 | 6 | 2 | 8 | +0.213623047 | -0.054931641 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.158691406 | 6 | 2 | 8 | +0.213623047 | -0.054931641 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 32.611083984 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 120010

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 36.090087891 | 36.090087891 | 0/16/0 | 0.837291751 | 0.781952451 | 98.437500 | 0.945219535 | 0.000427246 |
| common | 37.609863281 | 37.353515625 | 16/0/0 | 0.850456424 | 0.804917287 | 100.000000 | 0.942905234 | 0.000488281 |
| family | 37.908935547 | 37.933349609 | 8/0/8 | 0.856576132 | 0.813325715 | 100.000000 | 0.943296146 | 0.000427246 |
| writer | 37.609863281 | 37.353515625 | 16/0/0 | 0.850456424 | 0.804917287 | 100.000000 | 0.942905234 | 0.000488281 |
| family_writer | 37.908935547 | 37.933349609 | 8/0/8 | 0.856576132 | 0.813325715 | 100.000000 | 0.943296146 | 0.000427246 |
| record_rule | 37.908935547 | 37.933349609 | 8/0/8 | 0.856576132 | 0.813325715 | 100.000000 | 0.943296146 | 0.000427246 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.818847656 | 13 | 1 | 2 | +1.824951172 | -0.006103516 |
| common | +0.299072266 | 7 | 1 | 8 | +0.305175781 | -0.006103516 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.299072266 | 7 | 1 | 8 | +0.305175781 | -0.006103516 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 37.927246094 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_block: 120015

16 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 34.783935547 | 34.783935547 | 0/16/0 | 0.809618448 | 0.741158540 | 100.000000 | 0.946458983 | 0.000427246 |
| common | 36.029052734 | 36.120605469 | 16/0/0 | 0.837077084 | 0.782864368 | 100.000000 | 0.943898402 | 0.000427246 |
| family | 36.248779297 | 36.499023438 | 8/0/8 | 0.842833779 | 0.791665887 | 100.000000 | 0.943581595 | 0.000488281 |
| writer | 36.029052734 | 36.120605469 | 16/0/0 | 0.837077084 | 0.782864368 | 100.000000 | 0.943898402 | 0.000427246 |
| family_writer | 36.248779297 | 36.499023438 | 8/0/8 | 0.842833779 | 0.791665887 | 100.000000 | 0.943581595 | 0.000488281 |
| record_rule | 36.248779297 | 36.499023438 | 8/0/8 | 0.842833779 | 0.791665887 | 100.000000 | 0.943581595 | 0.000488281 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.464843750 | 12 | 3 | 1 | +1.531982422 | -0.067138672 |
| common | +0.219726562 | 5 | 2 | 9 | +0.231933594 | -0.012207031 |
| family | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |
| writer | +0.219726562 | 5 | 2 | 9 | +0.231933594 | -0.012207031 |
| family_writer | +0.000000000 | 0 | 0 | 16 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 36.322021484 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_group: A ordinary

32 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 43.780517578 | 43.780517578 | 0/32/0 | 0.943191180 | 0.927481266 | 100.000000 | 0.970460579 | 0.000478109 |
| common | 43.459065755 | 42.996215820 | 32/0/0 | 0.937136543 | 0.918751295 | 100.000000 | 0.970098316 | 0.000508626 |
| family | 43.886311849 | 44.067382812 | 0/0/32 | 0.945699056 | 0.931835493 | 100.000000 | 0.970402090 | 0.000508626 |
| writer | 43.459065755 | 42.996215820 | 32/0/0 | 0.937136543 | 0.918751295 | 100.000000 | 0.970098316 | 0.000508626 |
| family_writer | 43.886311849 | 44.067382812 | 0/0/32 | 0.945699056 | 0.931835493 | 100.000000 | 0.970402090 | 0.000508626 |
| record_rule | 43.868001302 | 44.032796224 | 0/2/30 | 0.945549415 | 0.931415853 | 100.000000 | 0.970413153 | 0.000508626 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.087483724 | 18 | 9 | 5 | +0.197347005 | -0.109863281 |
| common | +0.408935547 | 22 | 8 | 2 | +0.538126628 | -0.129191081 |
| family | -0.018310547 | 0 | 2 | 30 | +0.000000000 | -0.018310547 |
| writer | +0.408935547 | 22 | 8 | 2 | +0.538126628 | -0.129191081 |
| family_writer | -0.018310547 | 0 | 2 | 30 | +0.000000000 | -0.018310547 |

Optimistic retrospective per-record maximum: 44.039916992 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_group: A aligned

32 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 44.046020508 | 44.046020508 | 0/32/0 | 0.948752744 | 0.937048170 | 100.000000 | 0.973795180 | 0.000518799 |
| common | 43.859863281 | 43.414306641 | 32/0/0 | 0.943910609 | 0.929804379 | 100.000000 | 0.974405217 | 0.000518799 |
| family | 44.154866536 | 44.355265299 | 0/0/32 | 0.952761498 | 0.942797828 | 100.000000 | 0.973387839 | 0.000518799 |
| writer | 43.859863281 | 43.414306641 | 32/0/0 | 0.943910609 | 0.929804379 | 100.000000 | 0.974405217 | 0.000518799 |
| family_writer | 44.154866536 | 44.355265299 | 0/0/32 | 0.952761498 | 0.942797828 | 100.000000 | 0.973387839 | 0.000518799 |
| record_rule | 44.154866536 | 44.355265299 | 0/0/32 | 0.952761498 | 0.942797828 | 100.000000 | 0.973387839 | 0.000518799 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.108846029 | 21 | 10 | 1 | +0.183105469 | -0.074259440 |
| common | +0.295003255 | 20 | 10 | 2 | +0.376383464 | -0.081380208 |
| family | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| writer | +0.295003255 | 20 | 10 | 2 | +0.376383464 | -0.081380208 |
| family_writer | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 44.253540039 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_group: B ordinary

32 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 18.173217773 | 18.173217773 | 0/32/0 | 0.562119955 | 0.398634796 | 87.239583 | 0.932632163 | 0.000417074 |
| common | 21.710205078 | 21.962483724 | 32/0/0 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |
| family | 21.710205078 | 21.962483724 | 32/0/0 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |
| writer | 21.710205078 | 21.962483724 | 32/0/0 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |
| family_writer | 21.710205078 | 21.962483724 | 32/0/0 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |
| record_rule | 21.710205078 | 21.962483724 | 32/0/0 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +3.536987305 | 30 | 2 | 0 | +3.588867188 | -0.051879883 |
| common | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| family | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| writer | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| family_writer | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 21.824137370 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_group: B aligned

32 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 28.505452474 | 28.505452474 | 0/32/0 | 0.717430405 | 0.601585912 | 97.916667 | 0.926786759 | 0.000447591 |
| common | 29.930623372 | 29.875691732 | 32/0/0 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |
| family | 29.930623372 | 29.875691732 | 32/0/0 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |
| writer | 29.930623372 | 29.875691732 | 32/0/0 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |
| family_writer | 29.930623372 | 29.875691732 | 32/0/0 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |
| record_rule | 29.930623372 | 29.875691732 | 32/0/0 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.425170898 | 23 | 8 | 1 | +1.702880859 | -0.277709961 |
| common | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| family | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| writer | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |
| family_writer | +0.000000000 | 0 | 0 | 32 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 30.334472656 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_family: 0

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 43.913269043 | 43.913269043 | 0/64/0 | 0.945971962 | 0.932264718 | 100.000000 | 0.972127880 | 0.000498454 |
| common | 43.659464518 | 43.205261230 | 64/0/0 | 0.940523576 | 0.924277837 | 100.000000 | 0.972251766 | 0.000513713 |
| family | 44.020589193 | 44.211324056 | 0/0/64 | 0.949230277 | 0.937316660 | 100.000000 | 0.971894965 | 0.000513713 |
| writer | 43.659464518 | 43.205261230 | 64/0/0 | 0.940523576 | 0.924277837 | 100.000000 | 0.972251766 | 0.000513713 |
| family_writer | 44.020589193 | 44.211324056 | 0/0/64 | 0.949230277 | 0.937316660 | 100.000000 | 0.971894965 | 0.000513713 |
| record_rule | 44.011433919 | 44.194030762 | 0/2/62 | 0.949155456 | 0.937106841 | 100.000000 | 0.971900496 | 0.000513713 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.098164876 | 39 | 19 | 6 | +0.190226237 | -0.092061361 |
| common | +0.351969401 | 42 | 18 | 4 | +0.457255046 | -0.105285645 |
| family | -0.009155273 | 0 | 2 | 62 | +0.000000000 | -0.009155273 |
| writer | +0.351969401 | 42 | 18 | 4 | +0.457255046 | -0.105285645 |
| family_writer | -0.009155273 | 0 | 2 | 62 | +0.000000000 | -0.009155273 |

Optimistic retrospective per-record maximum: 44.146728516 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_family: 1

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 23.339335124 | 23.339335124 | 0/64/0 | 0.639775180 | 0.500110354 | 92.578125 | 0.929709461 | 0.000432332 |
| common | 25.820414225 | 25.919087728 | 64/0/0 | 0.682530001 | 0.554217389 | 94.010417 | 0.925895271 | 0.000427246 |
| family | 25.820414225 | 25.919087728 | 64/0/0 | 0.682530001 | 0.554217389 | 94.010417 | 0.925895271 | 0.000427246 |
| writer | 25.820414225 | 25.919087728 | 64/0/0 | 0.682530001 | 0.554217389 | 94.010417 | 0.925895271 | 0.000427246 |
| family_writer | 25.820414225 | 25.919087728 | 64/0/0 | 0.682530001 | 0.554217389 | 94.010417 | 0.925895271 | 0.000427246 |
| record_rule | 25.820414225 | 25.919087728 | 64/0/0 | 0.682530001 | 0.554217389 | 94.010417 | 0.925895271 | 0.000427246 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +2.481079102 | 53 | 10 | 1 | +2.645874023 | -0.164794922 |
| common | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |
| family | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |
| writer | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |
| family_writer | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 26.079305013 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_writer: 0

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 30.976867676 | 30.976867676 | 0/64/0 | 0.752655567 | 0.663058031 | 93.619792 | 0.951546371 | 0.000447591 |
| common | 32.584635417 | 32.479349772 | 64/0/0 | 0.777131031 | 0.695015546 | 94.791667 | 0.948802195 | 0.000457764 |
| family | 32.798258464 | 33.014933268 | 32/0/32 | 0.781412288 | 0.701557645 | 94.791667 | 0.948954083 | 0.000457764 |
| writer | 32.584635417 | 32.479349772 | 64/0/0 | 0.777131031 | 0.695015546 | 94.791667 | 0.948802195 | 0.000457764 |
| family_writer | 32.798258464 | 33.014933268 | 32/0/32 | 0.781412288 | 0.701557645 | 94.791667 | 0.948954083 | 0.000457764 |
| record_rule | 32.789103190 | 32.997639974 | 32/2/30 | 0.781337467 | 0.701347825 | 94.791667 | 0.948959614 | 0.000457764 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.812235514 | 48 | 11 | 5 | +1.893107096 | -0.080871582 |
| common | +0.204467773 | 22 | 8 | 34 | +0.269063314 | -0.064595540 |
| family | -0.009155273 | 0 | 2 | 62 | +0.000000000 | -0.009155273 |
| writer | +0.204467773 | 22 | 8 | 34 | +0.269063314 | -0.064595540 |
| family_writer | -0.009155273 | 0 | 2 | 62 | +0.000000000 | -0.009155273 |

Optimistic retrospective per-record maximum: 32.932027181 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested by_writer: 1

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 36.275736491 | 36.275736491 | 0/64/0 | 0.833091574 | 0.769317041 | 98.958333 | 0.950290970 | 0.000483195 |
| common | 36.895243327 | 36.644999186 | 64/0/0 | 0.845922546 | 0.783479680 | 99.218750 | 0.949344841 | 0.000483195 |
| family | 37.042744954 | 37.115478516 | 32/0/32 | 0.850347990 | 0.789976405 | 99.218750 | 0.948836153 | 0.000483195 |
| writer | 36.895243327 | 36.644999186 | 64/0/0 | 0.845922546 | 0.783479680 | 99.218750 | 0.949344841 | 0.000483195 |
| family_writer | 37.042744954 | 37.115478516 | 32/0/32 | 0.850347990 | 0.789976405 | 99.218750 | 0.948836153 | 0.000483195 |
| record_rule | 37.042744954 | 37.115478516 | 32/0/32 | 0.850347990 | 0.789976405 | 99.218750 | 0.948836153 | 0.000483195 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.767008464 | 44 | 18 | 2 | +0.942993164 | -0.175984701 |
| common | +0.147501628 | 20 | 10 | 34 | +0.188191732 | -0.040690104 |
| family | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |
| writer | +0.147501628 | 20 | 10 | 34 | +0.188191732 | -0.040690104 |
| family_writer | +0.000000000 | 0 | 0 | 64 | +0.000000000 | +0.000000000 |

Optimistic retrospective per-record maximum: 37.294006348 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 0 (available cases only)

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 31.787109375 | 31.787109375 | 0/64/0 | 0.759811084 | 0.670619694 | 95.312500 | 0.953166417 | 0.000488281 |
| common | 32.818603516 | 32.476806641 | 64/0/0 | 0.779460262 | 0.692770810 | 96.875000 | 0.951769724 | 0.000488281 |
| family | 33.148193359 | 33.166503906 | 32/0/32 | 0.784282072 | 0.700394354 | 96.875000 | 0.951439369 | 0.000488281 |
| writer | 32.818603516 | 32.476806641 | 64/0/0 | 0.779460262 | 0.692770810 | 96.875000 | 0.951769724 | 0.000488281 |
| family_writer | 33.148193359 | 33.166503906 | 32/0/32 | 0.784282072 | 0.700394354 | 96.875000 | 0.951439369 | 0.000488281 |
| record_rule | 33.111572266 | 33.142089844 | 32/2/30 | 0.784084387 | 0.700076762 | 96.875000 | 0.951357584 | 0.000488281 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.324462891 | 31 | 17 | 16 | +1.641845703 | -0.317382812 |
| common | +0.292968750 | 19 | 8 | 37 | +0.396728516 | -0.103759766 |
| family | -0.036621094 | 0 | 2 | 62 | +0.000000000 | -0.036621094 |
| writer | +0.292968750 | 19 | 8 | 37 | +0.396728516 | -0.103759766 |
| family_writer | -0.036621094 | 0 | 2 | 62 | +0.000000000 | -0.036621094 |

Optimistic retrospective per-record maximum: 33.544921875 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 1 (available cases only)

64 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 32.684326172 | 32.684326172 | 0/64/0 | 0.771873101 | 0.688124094 | 95.312500 | 0.953209203 | 0.000671387 |
| common | 33.630371094 | 33.361816406 | 64/0/0 | 0.795200270 | 0.716394828 | 95.312500 | 0.951211126 | 0.000610352 |
| family | 33.642578125 | 33.831787109 | 32/0/32 | 0.798282751 | 0.722363167 | 95.312500 | 0.951431151 | 0.000610352 |
| writer | 33.630371094 | 33.361816406 | 64/0/0 | 0.795200270 | 0.716394828 | 95.312500 | 0.951211126 | 0.000610352 |
| family_writer | 33.642578125 | 33.831787109 | 32/0/32 | 0.798282751 | 0.722363167 | 95.312500 | 0.951431151 | 0.000610352 |
| record_rule | 33.636474609 | 33.813476562 | 32/2/30 | 0.798199376 | 0.722180120 | 95.312500 | 0.951433285 | 0.000610352 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +0.952148438 | 32 | 16 | 16 | +1.367187500 | -0.415039062 |
| common | +0.006103516 | 12 | 12 | 40 | +0.268554688 | -0.262451172 |
| family | -0.006103516 | 0 | 1 | 63 | +0.000000000 | -0.006103516 |
| writer | +0.006103516 | 12 | 12 | 40 | +0.268554688 | -0.262451172 |
| family_writer | -0.006103516 | 0 | 1 | 63 | +0.000000000 | -0.006103516 |

Optimistic retrospective per-record maximum: 34.442138672 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 2 (available cases only)

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 33.007812500 | 33.007812500 | 0/128/0 | 0.784222746 | 0.698703525 | 94.531250 | 0.949231655 | 0.000274658 |
| common | 34.274291992 | 34.167480469 | 128/0/0 | 0.808018877 | 0.729020408 | 94.531250 | 0.946793048 | 0.000274658 |
| family | 34.426879883 | 34.591674805 | 64/0/64 | 0.811584596 | 0.734341515 | 94.531250 | 0.946645517 | 0.000274658 |
| writer | 34.274291992 | 34.167480469 | 128/0/0 | 0.808018877 | 0.729020408 | 94.531250 | 0.946793048 | 0.000274658 |
| family_writer | 34.426879883 | 34.591674805 | 64/0/64 | 0.811584596 | 0.734341515 | 94.531250 | 0.946645517 | 0.000274658 |
| record_rule | 34.442138672 | 34.600830078 | 64/2/62 | 0.811718055 | 0.734482233 | 94.531250 | 0.946669382 | 0.000274658 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.434326172 | 62 | 28 | 38 | +1.724243164 | -0.289916992 |
| common | +0.167846680 | 30 | 15 | 83 | +0.274658203 | -0.106811523 |
| family | +0.015258789 | 1 | 0 | 127 | +0.015258789 | +0.000000000 |
| writer | +0.167846680 | 30 | 15 | 83 | +0.274658203 | -0.106811523 |
| family_writer | +0.015258789 | 1 | 0 | 127 | +0.015258789 | +0.000000000 |

Optimistic retrospective per-record maximum: 34.951782227 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 3 (available cases only)

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 33.013916016 | 33.013916016 | 0/128/0 | 0.782369781 | 0.705020450 | 96.875000 | 0.955512772 | 0.000396729 |
| common | 34.109497070 | 33.923339844 | 128/0/0 | 0.802517278 | 0.729230033 | 96.875000 | 0.953174384 | 0.000366211 |
| family | 34.405517578 | 34.567260742 | 64/0/64 | 0.807712544 | 0.736554969 | 96.875000 | 0.952807682 | 0.000396729 |
| writer | 34.109497070 | 33.923339844 | 128/0/0 | 0.802517278 | 0.729230033 | 96.875000 | 0.953174384 | 0.000366211 |
| family_writer | 34.405517578 | 34.567260742 | 64/0/64 | 0.807712544 | 0.736554969 | 96.875000 | 0.952807682 | 0.000396729 |
| record_rule | 34.393310547 | 34.552001953 | 64/2/62 | 0.807648392 | 0.736460325 | 96.875000 | 0.952794553 | 0.000396729 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.379394531 | 63 | 36 | 29 | +1.806640625 | -0.427246094 |
| common | +0.283813477 | 30 | 16 | 82 | +0.393676758 | -0.109863281 |
| family | -0.012207031 | 0 | 2 | 126 | +0.000000000 | -0.012207031 |
| writer | +0.283813477 | 30 | 16 | 82 | +0.393676758 | -0.109863281 |
| family_writer | -0.012207031 | 0 | 2 | 126 | +0.000000000 | -0.012207031 |

Optimistic retrospective per-record maximum: 35.009765625 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 4 (available cases only)

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 33.660888672 | 33.660888672 | 0/128/0 | 0.786929865 | 0.717927203 | 96.093750 | 0.948859928 | 0.000579834 |
| common | 35.052490234 | 34.906005859 | 128/0/0 | 0.804293707 | 0.737508941 | 99.218750 | 0.946627596 | 0.000610352 |
| family | 35.110473633 | 35.305786133 | 64/0/64 | 0.808748321 | 0.744164926 | 99.218750 | 0.946670008 | 0.000610352 |
| writer | 35.052490234 | 34.906005859 | 128/0/0 | 0.804293707 | 0.737508941 | 99.218750 | 0.946627596 | 0.000610352 |
| family_writer | 35.110473633 | 35.305786133 | 64/0/64 | 0.808748321 | 0.744164926 | 99.218750 | 0.946670008 | 0.000610352 |
| record_rule | 35.092163086 | 35.281372070 | 64/2/62 | 0.808528982 | 0.743715862 | 99.218750 | 0.946726867 | 0.000610352 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.431274414 | 62 | 30 | 36 | +1.663208008 | -0.231933594 |
| common | +0.039672852 | 26 | 25 | 77 | +0.216674805 | -0.177001953 |
| family | -0.018310547 | 0 | 2 | 126 | +0.000000000 | -0.018310547 |
| writer | +0.039672852 | 26 | 25 | 77 | +0.216674805 | -0.177001953 |
| family_writer | -0.018310547 | 0 | 2 | 126 | +0.000000000 | -0.018310547 |

Optimistic retrospective per-record maximum: 35.452270508 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Nested future 5 (available cases only)

128 record/writer decisions.

| Policy | Common preference | Native preference | Actions | F3 own corr | F3 corr margin | Guide % | Body RMS | Clip fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| native | 34.490966797 | 34.490966797 | 0/128/0 | 0.818215935 | 0.742092142 | 96.875000 | 0.951990790 | 0.000549316 |
| common | 35.418701172 | 35.281372070 | 128/0/0 | 0.831262026 | 0.758410890 | 96.875000 | 0.951385192 | 0.000610352 |
| family | 35.638427734 | 35.772705078 | 64/0/64 | 0.835577556 | 0.764466120 | 96.875000 | 0.951014815 | 0.000579834 |
| writer | 35.418701172 | 35.281372070 | 128/0/0 | 0.831262026 | 0.758410890 | 96.875000 | 0.951385192 | 0.000610352 |
| family_writer | 35.638427734 | 35.772705078 | 64/0/64 | 0.835577556 | 0.764466120 | 96.875000 | 0.951014815 | 0.000579834 |
| record_rule | 35.647583008 | 35.772705078 | 64/2/62 | 0.835643657 | 0.764489971 | 96.875000 | 0.951003637 | 0.000579834 |

| Record rule minus | Net points | Gains | Harms | Ties | Positive contribution | Negative contribution |
| --- | --- | --- | --- | --- | --- | --- |
| native | +1.156616211 | 63 | 31 | 34 | +1.428222656 | -0.271606445 |
| common | +0.228881836 | 30 | 13 | 85 | +0.311279297 | -0.082397461 |
| family | +0.009155273 | 1 | 0 | 127 | +0.009155273 | +0.000000000 |
| writer | +0.228881836 | 30 | 13 | 85 | +0.311279297 | -0.082397461 |
| family_writer | +0.009155273 | 1 | 0 | 127 | +0.009155273 | +0.000000000 |

Optimistic retrospective per-record maximum: 35.983276367 points. This maximizes noisy observed outcomes; it is not a deployable policy or a proven attainable ceiling.

## Selected regularization and final simple rules

| Omitted founder | Selected lambda |
| --- | --- |
| 90000 | 100.0 |
| 90005 | 100.0 |
| 90010 | 100.0 |
| 90015 | 1.0 |
| 120000 | 100.0 |
| 120005 | 100.0 |
| 120010 | 100.0 |
| 120015 | 100.0 |

| Full-development lambda | Selection value (points) |
| --- | --- |
| 0.0001 | 34.874979655 |
| 0.001 | 34.879557292 |
| 0.01 | 34.870656331 |
| 0.1 | 34.887695312 |
| 1.0 | 34.913126628 |
| 10.0 | 34.915924072 |
| 100.0 | 34.920501709 |

Final selected lambda: 100.0. These selection scores are not prospective evidence.

| Simple rule | A ordinary | A aligned | B ordinary | B aligned |
| --- | --- | --- | --- | --- |
| common | 0.75 | 0.75 | 0.75 | 0.75 |
| family | 1.25 | 1.25 | 0.75 | 0.75 |
| family_writer | 1.25 | 1.25 | 0.75 | 0.75 |
| native | 1.0 | 1.0 | 1.0 | 1.0 |
| writer | 0.75 | 0.75 | 0.75 | 0.75 |

| Outer set | Records with any clipped feature | Total features clipped |
| --- | --- | --- |
| 90000 | 0 | 0 |
| 90005 | 0 | 0 |
| 90010 | 0 | 0 |
| 90015 | 0 | 0 |
| 120000 | 0 | 0 |
| 120005 | 0 | 0 |
| 120010 | 0 | 0 |
| 120015 | 0 | 0 |

| Transfer set | Records with any clipped feature | Total features clipped |
| --- | --- | --- |
| old_to_new | 0 | 0 |
| new_to_old | 0 | 0 |

| Final set | Records with any clipped feature | Total features clipped |
| --- | --- | --- |
| all | 0 | 0 |

## Complete control panel: pooled and founder values

Controls are excluded from policy fitting. Pooled rows weight each founder equally.
Coupling specifies the reconstruction setting; common/native assay labels
specify the terminal evaluation reader.

| Founder | Assay | Family | Condition | Coupling | Preference | F0 own corr | F0 margin | F3 own corr | F3 margin | Guide % | Body RMS | Clip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pooled | common | A | ordinary | 0.75 | 43.459065755 | 0.932061265 | 0.916899718 | 0.937136543 | 0.918751295 | 100.000000 | 0.970098316 | 0.000508626 |
| 90000 | common | A | ordinary | 0.75 | 44.449869792 | 0.915634225 | 0.906156900 | 0.948010947 | 0.931710010 | 100.000000 | 0.966310260 | 0.000325521 |
| 90005 | common | A | ordinary | 0.75 | 42.513020833 | 0.921236109 | 0.903719580 | 0.925914366 | 0.904246323 | 100.000000 | 0.972882499 | 0.000651042 |
| 90010 | common | A | ordinary | 0.75 | 42.903645833 | 0.950583251 | 0.932174534 | 0.928904495 | 0.910625520 | 100.000000 | 0.966957999 | 0.000325521 |
| 90015 | common | A | ordinary | 0.75 | 43.538411458 | 0.953050250 | 0.941181517 | 0.937089768 | 0.917695242 | 100.000000 | 0.978073743 | 0.000813802 |
| 120000 | common | A | ordinary | 0.75 | 44.409179688 | 0.948982398 | 0.939348254 | 0.948506682 | 0.930700685 | 100.000000 | 0.975125701 | 0.000000000 |
| 120005 | common | A | ordinary | 0.75 | 42.895507812 | 0.932801971 | 0.912726754 | 0.925838954 | 0.907542534 | 100.000000 | 0.967945368 | 0.000488281 |
| 120010 | common | A | ordinary | 0.75 | 43.164062500 | 0.912717494 | 0.893541307 | 0.934374834 | 0.916704036 | 100.000000 | 0.965660027 | 0.000732422 |
| 120015 | common | A | ordinary | 0.75 | 43.798828125 | 0.921484421 | 0.906348900 | 0.948452296 | 0.930786010 | 100.000000 | 0.967830927 | 0.000732422 |
| pooled | common | A | ordinary | 1.0 | 43.780517578 | 0.932061265 | 0.916899718 | 0.943191180 | 0.927481266 | 100.000000 | 0.970460579 | 0.000478109 |
| 90000 | common | A | ordinary | 1.0 | 44.335937500 | 0.915634225 | 0.906156900 | 0.952297548 | 0.937936616 | 100.000000 | 0.966660440 | 0.000325521 |
| 90005 | common | A | ordinary | 1.0 | 42.724609375 | 0.921236109 | 0.903719580 | 0.934664254 | 0.915592096 | 100.000000 | 0.973568792 | 0.000651042 |
| 90010 | common | A | ordinary | 1.0 | 43.359375000 | 0.950583251 | 0.932174534 | 0.934598812 | 0.918212298 | 100.000000 | 0.966804797 | 0.000325521 |
| 90015 | common | A | ordinary | 1.0 | 44.091796875 | 0.953050250 | 0.941181517 | 0.945086246 | 0.929143017 | 100.000000 | 0.979587901 | 0.000813802 |
| 120000 | common | A | ordinary | 1.0 | 44.506835938 | 0.948982398 | 0.939348254 | 0.950545151 | 0.935931321 | 100.000000 | 0.975099687 | 0.000000000 |
| 120005 | common | A | ordinary | 1.0 | 43.286132812 | 0.932801971 | 0.912726754 | 0.931032858 | 0.914428641 | 100.000000 | 0.967555901 | 0.000488281 |
| 120010 | common | A | ordinary | 1.0 | 43.774414062 | 0.912717494 | 0.893541307 | 0.942451070 | 0.927370007 | 100.000000 | 0.966761288 | 0.000488281 |
| 120015 | common | A | ordinary | 1.0 | 44.165039062 | 0.921484421 | 0.906348900 | 0.954853502 | 0.941236137 | 100.000000 | 0.967645823 | 0.000732422 |
| pooled | common | A | ordinary | 1.25 | 43.886311849 | 0.932061265 | 0.916899718 | 0.945699056 | 0.931835493 | 100.000000 | 0.970402090 | 0.000508626 |
| 90000 | common | A | ordinary | 1.25 | 44.222005208 | 0.915634225 | 0.906156900 | 0.952403465 | 0.939975989 | 100.000000 | 0.966159419 | 0.000325521 |
| 90005 | common | A | ordinary | 1.25 | 43.033854167 | 0.921236109 | 0.903719580 | 0.939772904 | 0.924283710 | 100.000000 | 0.972997570 | 0.000651042 |
| 90010 | common | A | ordinary | 1.25 | 43.522135417 | 0.950583251 | 0.932174534 | 0.936497324 | 0.922014937 | 100.000000 | 0.966580402 | 0.000325521 |
| 90015 | common | A | ordinary | 1.25 | 44.433593750 | 0.953050250 | 0.941181517 | 0.948141095 | 0.934277391 | 100.000000 | 0.979887830 | 0.000813802 |
| 120000 | common | A | ordinary | 1.25 | 44.238281250 | 0.948982398 | 0.939348254 | 0.951057989 | 0.937299825 | 100.000000 | 0.974616300 | 0.000000000 |
| 120005 | common | A | ordinary | 1.25 | 43.334960938 | 0.932801971 | 0.912726754 | 0.934632323 | 0.919542809 | 100.000000 | 0.967198029 | 0.000488281 |
| 120010 | common | A | ordinary | 1.25 | 43.945312500 | 0.912717494 | 0.893541307 | 0.945235250 | 0.932261109 | 100.000000 | 0.967604150 | 0.000488281 |
| 120015 | common | A | ordinary | 1.25 | 44.360351562 | 0.921484421 | 0.906348900 | 0.957852095 | 0.945028171 | 100.000000 | 0.968173023 | 0.000976562 |
| pooled | common | A | aligned | 0.75 | 43.859863281 | 0.932061265 | 0.916899718 | 0.943910609 | 0.929804379 | 100.000000 | 0.974405217 | 0.000518799 |
| 90000 | common | A | aligned | 0.75 | 42.838541667 | 0.915634225 | 0.906156900 | 0.921221979 | 0.908297357 | 100.000000 | 0.971429098 | 0.000488281 |
| 90005 | common | A | aligned | 0.75 | 42.838541667 | 0.921236109 | 0.903719580 | 0.931183456 | 0.913778909 | 100.000000 | 0.977117891 | 0.000651042 |
| 90010 | common | A | aligned | 0.75 | 45.231119792 | 0.950583251 | 0.932174534 | 0.967809327 | 0.957014123 | 100.000000 | 0.974633564 | 0.000325521 |
| 90015 | common | A | aligned | 0.75 | 45.019531250 | 0.953050250 | 0.941181517 | 0.966145295 | 0.956303369 | 100.000000 | 0.982730911 | 0.000976562 |
| 120000 | common | A | aligned | 0.75 | 44.970703125 | 0.948982398 | 0.939348254 | 0.961807321 | 0.945547246 | 100.000000 | 0.978352817 | 0.000000000 |
| 120005 | common | A | aligned | 0.75 | 43.701171875 | 0.932801971 | 0.912726754 | 0.937281400 | 0.924723966 | 100.000000 | 0.970239195 | 0.000488281 |
| 120010 | common | A | aligned | 0.75 | 43.310546875 | 0.912717494 | 0.893541307 | 0.930031337 | 0.915921614 | 100.000000 | 0.969731000 | 0.000488281 |
| 120015 | common | A | aligned | 0.75 | 42.968750000 | 0.921484421 | 0.906348900 | 0.935804755 | 0.916848451 | 100.000000 | 0.971007257 | 0.000732422 |
| pooled | common | A | aligned | 1.0 | 44.046020508 | 0.932061265 | 0.916899718 | 0.948752744 | 0.937048170 | 100.000000 | 0.973795180 | 0.000518799 |
| 90000 | common | A | aligned | 1.0 | 42.757161458 | 0.915634225 | 0.906156900 | 0.926046670 | 0.914663890 | 100.000000 | 0.971373883 | 0.000488281 |
| 90005 | common | A | aligned | 1.0 | 43.212890625 | 0.921236109 | 0.903719580 | 0.937292675 | 0.923209551 | 100.000000 | 0.976291796 | 0.000651042 |
| 90010 | common | A | aligned | 1.0 | 45.361328125 | 0.950583251 | 0.932174534 | 0.971240217 | 0.962678885 | 100.000000 | 0.974245129 | 0.000325521 |
| 90015 | common | A | aligned | 1.0 | 45.182291667 | 0.953050250 | 0.941181517 | 0.967403966 | 0.958387842 | 100.000000 | 0.981250113 | 0.000976562 |
| 120000 | common | A | aligned | 1.0 | 45.312500000 | 0.948982398 | 0.939348254 | 0.965162001 | 0.951000056 | 100.000000 | 0.977664537 | 0.000000000 |
| 120005 | common | A | aligned | 1.0 | 43.847656250 | 0.932801971 | 0.912726754 | 0.942476304 | 0.932289611 | 100.000000 | 0.969905269 | 0.000488281 |
| 120010 | common | A | aligned | 1.0 | 43.530273438 | 0.912717494 | 0.893541307 | 0.937434443 | 0.925990957 | 100.000000 | 0.969687066 | 0.000488281 |
| 120015 | common | A | aligned | 1.0 | 43.164062500 | 0.921484421 | 0.906348900 | 0.942965676 | 0.928164568 | 100.000000 | 0.969943649 | 0.000732422 |
| pooled | common | A | aligned | 1.25 | 44.154866536 | 0.932061265 | 0.916899718 | 0.952761498 | 0.942797828 | 100.000000 | 0.973387839 | 0.000518799 |
| 90000 | common | A | aligned | 1.25 | 42.822265625 | 0.915634225 | 0.906156900 | 0.931131989 | 0.920819200 | 100.000000 | 0.970728915 | 0.000488281 |
| 90005 | common | A | aligned | 1.25 | 43.554687500 | 0.921236109 | 0.903719580 | 0.941957968 | 0.929573959 | 100.000000 | 0.974883011 | 0.000651042 |
| 90010 | common | A | aligned | 1.25 | 45.393880208 | 0.950583251 | 0.932174534 | 0.973188681 | 0.965637170 | 100.000000 | 0.974051678 | 0.000325521 |
| 90015 | common | A | aligned | 1.25 | 45.149739583 | 0.953050250 | 0.941181517 | 0.968304173 | 0.960297337 | 100.000000 | 0.981906984 | 0.000976562 |
| 120000 | common | A | aligned | 1.25 | 45.410156250 | 0.948982398 | 0.939348254 | 0.967205551 | 0.955653757 | 100.000000 | 0.977230393 | 0.000000000 |
| 120005 | common | A | aligned | 1.25 | 43.896484375 | 0.932801971 | 0.912726754 | 0.947222131 | 0.938590583 | 100.000000 | 0.969553271 | 0.000488281 |
| 120010 | common | A | aligned | 1.25 | 43.725585938 | 0.912717494 | 0.893541307 | 0.943649753 | 0.933998256 | 100.000000 | 0.969350529 | 0.000488281 |
| 120015 | common | A | aligned | 1.25 | 43.286132812 | 0.921484421 | 0.906348900 | 0.949431736 | 0.937812363 | 100.000000 | 0.969397932 | 0.000732422 |
| pooled | common | A | protected_copy | 0.75 | 42.878214518 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.969846014 | 0.000549316 |
| 90000 | common | A | protected_copy | 0.75 | 41.813151042 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.965137815 | 0.000488281 |
| 90005 | common | A | protected_copy | 0.75 | 42.513020833 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.972024505 | 0.000651042 |
| 90010 | common | A | protected_copy | 0.75 | 43.408203125 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.969935523 | 0.000325521 |
| 90015 | common | A | protected_copy | 0.75 | 43.977864583 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.978401028 | 0.000976562 |
| 120000 | common | A | protected_copy | 0.75 | 44.287109375 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.973755747 | 0.000000000 |
| 120005 | common | A | protected_copy | 0.75 | 42.626953125 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.966770930 | 0.000488281 |
| 120010 | common | A | protected_copy | 0.75 | 42.260742188 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.965268060 | 0.000732422 |
| 120015 | common | A | protected_copy | 0.75 | 42.138671875 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.967474504 | 0.000732422 |
| pooled | common | A | protected_copy | 1.0 | 42.878214518 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.969846014 | 0.000549316 |
| 90000 | common | A | protected_copy | 1.0 | 41.813151042 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.965137815 | 0.000488281 |
| 90005 | common | A | protected_copy | 1.0 | 42.513020833 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.972024505 | 0.000651042 |
| 90010 | common | A | protected_copy | 1.0 | 43.408203125 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.969935523 | 0.000325521 |
| 90015 | common | A | protected_copy | 1.0 | 43.977864583 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.978401028 | 0.000976562 |
| 120000 | common | A | protected_copy | 1.0 | 44.287109375 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.973755747 | 0.000000000 |
| 120005 | common | A | protected_copy | 1.0 | 42.626953125 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.966770930 | 0.000488281 |
| 120010 | common | A | protected_copy | 1.0 | 42.260742188 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.965268060 | 0.000732422 |
| 120015 | common | A | protected_copy | 1.0 | 42.138671875 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.967474504 | 0.000732422 |
| pooled | common | A | protected_copy | 1.25 | 42.878214518 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.969846014 | 0.000549316 |
| 90000 | common | A | protected_copy | 1.25 | 41.813151042 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.965137815 | 0.000488281 |
| 90005 | common | A | protected_copy | 1.25 | 42.513020833 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.972024505 | 0.000651042 |
| 90010 | common | A | protected_copy | 1.25 | 43.408203125 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.969935523 | 0.000325521 |
| 90015 | common | A | protected_copy | 1.25 | 43.977864583 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.978401028 | 0.000976562 |
| 120000 | common | A | protected_copy | 1.25 | 44.287109375 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.973755747 | 0.000000000 |
| 120005 | common | A | protected_copy | 1.25 | 42.626953125 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.966770930 | 0.000488281 |
| 120010 | common | A | protected_copy | 1.25 | 42.260742188 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.965268060 | 0.000732422 |
| 120015 | common | A | protected_copy | 1.25 | 42.138671875 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.967474504 | 0.000732422 |
| pooled | common | A | ordinary_read_off | 0.75 | 16.136678060 | 0.932061265 | 0.916899718 | 0.405820739 | 0.272518392 | 80.729167 | 0.937082846 | 0.000366211 |
| 90000 | common | A | ordinary_read_off | 0.75 | 15.250651042 | 0.915634225 | 0.906156900 | 0.380725289 | 0.249319369 | 79.166667 | 0.945271673 | 0.000325521 |
| 90005 | common | A | ordinary_read_off | 0.75 | 12.500000000 | 0.921236109 | 0.903719580 | 0.323009616 | 0.184738137 | 83.333333 | 0.932646476 | 0.000162760 |
| 90010 | common | A | ordinary_read_off | 0.75 | 10.742187500 | 0.950583251 | 0.932174534 | 0.364066623 | 0.226798881 | 70.833333 | 0.933108359 | 0.000325521 |
| 90015 | common | A | ordinary_read_off | 0.75 | 15.087890625 | 0.953050250 | 0.941181517 | 0.393879843 | 0.263951394 | 75.000000 | 0.940227428 | 0.000651042 |
| 120000 | common | A | ordinary_read_off | 0.75 | 13.916015625 | 0.948982398 | 0.939348254 | 0.353408605 | 0.213010175 | 81.250000 | 0.934411842 | 0.000000000 |
| 120005 | common | A | ordinary_read_off | 0.75 | 17.456054688 | 0.932801971 | 0.912726754 | 0.420386906 | 0.270338641 | 81.250000 | 0.928934585 | 0.000244141 |
| 120010 | common | A | ordinary_read_off | 0.75 | 20.166015625 | 0.912717494 | 0.893541307 | 0.462156235 | 0.355146223 | 87.500000 | 0.942741331 | 0.000976562 |
| 120015 | common | A | ordinary_read_off | 0.75 | 23.974609375 | 0.921484421 | 0.906348900 | 0.548932791 | 0.416844320 | 87.500000 | 0.939321070 | 0.000244141 |
| pooled | common | A | ordinary_read_off | 1.0 | 19.803873698 | 0.932061265 | 0.916899718 | 0.468338360 | 0.363779281 | 88.541667 | 0.949478748 | 0.000447591 |
| 90000 | common | A | ordinary_read_off | 1.0 | 20.035807292 | 0.915634225 | 0.906156900 | 0.458550578 | 0.352414530 | 83.333333 | 0.952283763 | 0.000488281 |
| 90005 | common | A | ordinary_read_off | 1.0 | 16.569010417 | 0.921236109 | 0.903719580 | 0.392408245 | 0.271556073 | 95.833333 | 0.955123747 | 0.000488281 |
| 90010 | common | A | ordinary_read_off | 1.0 | 16.438802083 | 0.950583251 | 0.932174534 | 0.412634807 | 0.291820235 | 87.500000 | 0.941713502 | 0.000488281 |
| 90015 | common | A | ordinary_read_off | 1.0 | 16.910807292 | 0.953050250 | 0.941181517 | 0.422712221 | 0.328488041 | 79.166667 | 0.951201422 | 0.000651042 |
| 120000 | common | A | ordinary_read_off | 1.0 | 19.897460938 | 0.948982398 | 0.939348254 | 0.440115302 | 0.326679827 | 93.750000 | 0.948103082 | 0.000244141 |
| 120005 | common | A | ordinary_read_off | 1.0 | 20.605468750 | 0.932801971 | 0.912726754 | 0.503244811 | 0.394195508 | 93.750000 | 0.949459027 | 0.000000000 |
| 120010 | common | A | ordinary_read_off | 1.0 | 21.166992188 | 0.912717494 | 0.893541307 | 0.488318551 | 0.412827036 | 87.500000 | 0.948995447 | 0.000976562 |
| 120015 | common | A | ordinary_read_off | 1.0 | 26.806640625 | 0.921484421 | 0.906348900 | 0.628722366 | 0.532252999 | 87.500000 | 0.948949993 | 0.000244141 |
| pooled | common | A | ordinary_read_off | 1.25 | 21.452840169 | 0.932061265 | 0.916899718 | 0.505931747 | 0.424348655 | 88.541667 | 0.957996759 | 0.000457764 |
| 90000 | common | A | ordinary_read_off | 1.25 | 20.817057292 | 0.915634225 | 0.906156900 | 0.469765353 | 0.377172790 | 87.500000 | 0.956110918 | 0.000325521 |
| 90005 | common | A | ordinary_read_off | 1.25 | 18.440755208 | 0.921236109 | 0.903719580 | 0.440221353 | 0.350776120 | 79.166667 | 0.963301920 | 0.000325521 |
| 90010 | common | A | ordinary_read_off | 1.25 | 17.822265625 | 0.950583251 | 0.932174534 | 0.444480431 | 0.354870322 | 87.500000 | 0.953109023 | 0.000488281 |
| 90015 | common | A | ordinary_read_off | 1.25 | 19.449869792 | 0.953050250 | 0.941181517 | 0.454813046 | 0.374597218 | 91.666667 | 0.961055940 | 0.000813802 |
| 120000 | common | A | ordinary_read_off | 1.25 | 24.145507812 | 0.948982398 | 0.939348254 | 0.554383994 | 0.468662755 | 100.000000 | 0.956712326 | 0.000000000 |
| 120005 | common | A | ordinary_read_off | 1.25 | 22.827148438 | 0.932801971 | 0.912726754 | 0.543703187 | 0.474056973 | 87.500000 | 0.960356899 | 0.000244141 |
| 120010 | common | A | ordinary_read_off | 1.25 | 21.386718750 | 0.912717494 | 0.893541307 | 0.504012440 | 0.434059647 | 87.500000 | 0.955530724 | 0.001220703 |
| 120015 | common | A | ordinary_read_off | 1.25 | 26.733398438 | 0.921484421 | 0.906348900 | 0.636074176 | 0.560593411 | 87.500000 | 0.957796323 | 0.000244141 |
| pooled | common | A | aligned_read_off | 0.75 | 17.370605469 | 0.932061265 | 0.916899718 | 0.411775241 | 0.268838228 | 87.239583 | 0.938499687 | 0.000386556 |
| 90000 | common | A | aligned_read_off | 0.75 | 16.503906250 | 0.915634225 | 0.906156900 | 0.375775783 | 0.230815429 | 91.666667 | 0.939788729 | 0.000162760 |
| 90005 | common | A | aligned_read_off | 0.75 | 15.836588542 | 0.921236109 | 0.903719580 | 0.390935977 | 0.242262434 | 83.333333 | 0.938979123 | 0.000325521 |
| 90010 | common | A | aligned_read_off | 0.75 | 15.983072917 | 0.950583251 | 0.932174534 | 0.391747880 | 0.247645961 | 75.000000 | 0.944126394 | 0.000325521 |
| 90015 | common | A | aligned_read_off | 0.75 | 17.740885417 | 0.953050250 | 0.941181517 | 0.391604213 | 0.251046854 | 91.666667 | 0.934436304 | 0.000813802 |
| 120000 | common | A | aligned_read_off | 0.75 | 14.282226562 | 0.948982398 | 0.939348254 | 0.338320634 | 0.196020938 | 81.250000 | 0.939642799 | 0.000244141 |
| 120005 | common | A | aligned_read_off | 0.75 | 19.311523438 | 0.932801971 | 0.912726754 | 0.472678216 | 0.323238095 | 93.750000 | 0.935446101 | 0.000244141 |
| 120010 | common | A | aligned_read_off | 0.75 | 18.701171875 | 0.912717494 | 0.893541307 | 0.440444787 | 0.296878221 | 87.500000 | 0.937917823 | 0.000732422 |
| 120015 | common | A | aligned_read_off | 0.75 | 20.605468750 | 0.921484421 | 0.906348900 | 0.492694440 | 0.362797887 | 93.750000 | 0.937660226 | 0.000244141 |
| pooled | common | A | aligned_read_off | 1.0 | 20.608520508 | 0.932061265 | 0.916899718 | 0.468823120 | 0.359095961 | 94.270833 | 0.952649348 | 0.000457764 |
| 90000 | common | A | aligned_read_off | 1.0 | 20.296223958 | 0.915634225 | 0.906156900 | 0.469557238 | 0.355666857 | 100.000000 | 0.954170862 | 0.000325521 |
| 90005 | common | A | aligned_read_off | 1.0 | 17.692057292 | 0.921236109 | 0.903719580 | 0.422877248 | 0.294875057 | 83.333333 | 0.958442694 | 0.000162760 |
| 90010 | common | A | aligned_read_off | 1.0 | 19.205729167 | 0.950583251 | 0.932174534 | 0.446731249 | 0.339941436 | 87.500000 | 0.951924600 | 0.000488281 |
| 90015 | common | A | aligned_read_off | 1.0 | 19.173177083 | 0.953050250 | 0.941181517 | 0.410554724 | 0.313371024 | 95.833333 | 0.947657414 | 0.000488281 |
| 120000 | common | A | aligned_read_off | 1.0 | 18.603515625 | 0.948982398 | 0.939348254 | 0.405272280 | 0.280203477 | 93.750000 | 0.959180669 | 0.000244141 |
| 120005 | common | A | aligned_read_off | 1.0 | 23.071289062 | 0.932801971 | 0.912726754 | 0.568646911 | 0.456612813 | 93.750000 | 0.952529174 | 0.000488281 |
| 120010 | common | A | aligned_read_off | 1.0 | 20.776367188 | 0.912717494 | 0.893541307 | 0.443648292 | 0.342407143 | 100.000000 | 0.948133843 | 0.001220703 |
| 120015 | common | A | aligned_read_off | 1.0 | 26.049804688 | 0.921484421 | 0.906348900 | 0.583297021 | 0.489689880 | 100.000000 | 0.949155529 | 0.000244141 |
| pooled | common | A | aligned_read_off | 1.25 | 21.976725260 | 0.932061265 | 0.916899718 | 0.503180386 | 0.417419974 | 92.968750 | 0.960427120 | 0.000417074 |
| 90000 | common | A | aligned_read_off | 1.25 | 20.491536458 | 0.915634225 | 0.906156900 | 0.488434492 | 0.390509751 | 91.666667 | 0.959827534 | 0.000488281 |
| 90005 | common | A | aligned_read_off | 1.25 | 19.140625000 | 0.921236109 | 0.903719580 | 0.455478902 | 0.372585925 | 83.333333 | 0.968128081 | 0.000162760 |
| 90010 | common | A | aligned_read_off | 1.25 | 20.312500000 | 0.950583251 | 0.932174534 | 0.481318329 | 0.396746973 | 91.666667 | 0.956824798 | 0.000488281 |
| 90015 | common | A | aligned_read_off | 1.25 | 20.361328125 | 0.953050250 | 0.941181517 | 0.451707934 | 0.362478666 | 95.833333 | 0.954069305 | 0.000488281 |
| 120000 | common | A | aligned_read_off | 1.25 | 22.656250000 | 0.948982398 | 0.939348254 | 0.513129110 | 0.418167777 | 100.000000 | 0.964014945 | 0.000000000 |
| 120005 | common | A | aligned_read_off | 1.25 | 27.075195312 | 0.932801971 | 0.912726754 | 0.617183215 | 0.543592838 | 87.500000 | 0.961124924 | 0.000488281 |
| 120010 | common | A | aligned_read_off | 1.25 | 20.996093750 | 0.912717494 | 0.893541307 | 0.463119520 | 0.380141146 | 100.000000 | 0.963389968 | 0.000976562 |
| 120015 | common | A | aligned_read_off | 1.25 | 24.780273438 | 0.921484421 | 0.906348900 | 0.555071588 | 0.475136718 | 93.750000 | 0.956037405 | 0.000244141 |
| pooled | common | A | write_off | 0.75 | 2.312215169 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | A | write_off | 0.75 | 0.537109375 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | A | write_off | 0.75 | -1.595052083 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | A | write_off | 0.75 | 9.521484375 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | A | write_off | 0.75 | 2.050781250 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | A | write_off | 0.75 | 3.735351562 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | A | write_off | 0.75 | 0.610351562 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | A | write_off | 0.75 | 3.051757812 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | A | write_off | 0.75 | 0.585937500 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | common | A | write_off | 1.0 | 2.312215169 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | A | write_off | 1.0 | 0.537109375 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | A | write_off | 1.0 | -1.595052083 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | A | write_off | 1.0 | 9.521484375 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | A | write_off | 1.0 | 2.050781250 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | A | write_off | 1.0 | 3.735351562 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | A | write_off | 1.0 | 0.610351562 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | A | write_off | 1.0 | 3.051757812 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | A | write_off | 1.0 | 0.585937500 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | common | A | write_off | 1.25 | 2.312215169 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | A | write_off | 1.25 | 0.537109375 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | A | write_off | 1.25 | -1.595052083 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | A | write_off | 1.25 | 9.521484375 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | A | write_off | 1.25 | 2.050781250 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | A | write_off | 1.25 | 3.735351562 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | A | write_off | 1.25 | 0.610351562 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | A | write_off | 1.25 | 3.051757812 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | A | write_off | 1.25 | 0.585937500 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | common | B | ordinary | 0.75 | 21.710205078 | 0.828325394 | 0.746388980 | 0.617125520 | 0.471279796 | 89.583333 | 0.927506075 | 0.000406901 |
| 90000 | common | B | ordinary | 0.75 | 25.488281250 | 0.803029948 | 0.769306605 | 0.627930172 | 0.507449778 | 95.833333 | 0.925887466 | 0.000325521 |
| 90005 | common | B | ordinary | 0.75 | 25.048828125 | 0.875762523 | 0.844002803 | 0.691266690 | 0.570685808 | 100.000000 | 0.929482659 | 0.000488281 |
| 90010 | common | B | ordinary | 0.75 | 7.861328125 | 0.695684702 | 0.515800898 | 0.402880649 | 0.162560795 | 66.666667 | 0.944708296 | 0.000813802 |
| 90015 | common | B | ordinary | 0.75 | 18.115234375 | 0.803957480 | 0.655574258 | 0.583237956 | 0.387093782 | 79.166667 | 0.937030221 | 0.000651042 |
| 120000 | common | B | ordinary | 0.75 | 30.029296875 | 0.907038700 | 0.872970997 | 0.769920668 | 0.668633425 | 100.000000 | 0.906411224 | 0.000000000 |
| 120005 | common | B | ordinary | 0.75 | 17.504882812 | 0.785661814 | 0.647875433 | 0.545302161 | 0.390313684 | 75.000000 | 0.932408659 | 0.000732422 |
| 120010 | common | B | ordinary | 0.75 | 25.878906250 | 0.889802804 | 0.850077254 | 0.662040978 | 0.549836362 | 100.000000 | 0.923228979 | 0.000244141 |
| 120015 | common | B | ordinary | 0.75 | 23.754882812 | 0.865665183 | 0.815503594 | 0.654424883 | 0.533664736 | 100.000000 | 0.920891097 | 0.000000000 |
| pooled | common | B | ordinary | 1.0 | 18.173217773 | 0.828325394 | 0.746388980 | 0.562119955 | 0.398634796 | 87.239583 | 0.932632163 | 0.000417074 |
| 90000 | common | B | ordinary | 1.0 | 17.952473958 | 0.803029948 | 0.769306605 | 0.540940544 | 0.395011091 | 87.500000 | 0.933788074 | 0.000488281 |
| 90005 | common | B | ordinary | 1.0 | 21.077473958 | 0.875762523 | 0.844002803 | 0.624408055 | 0.477030675 | 95.833333 | 0.935697500 | 0.000325521 |
| 90010 | common | B | ordinary | 1.0 | 6.770833333 | 0.695684702 | 0.515800898 | 0.360938848 | 0.131401929 | 66.666667 | 0.948812723 | 0.000651042 |
| 90015 | common | B | ordinary | 1.0 | 15.087890625 | 0.803957480 | 0.655574258 | 0.525920793 | 0.320800696 | 79.166667 | 0.939433792 | 0.000651042 |
| 120000 | common | B | ordinary | 1.0 | 24.951171875 | 0.907038700 | 0.872970997 | 0.704363759 | 0.559190932 | 100.000000 | 0.915285806 | 0.000244141 |
| 120005 | common | B | ordinary | 1.0 | 17.382812500 | 0.785661814 | 0.647875433 | 0.526971350 | 0.377009098 | 75.000000 | 0.932264357 | 0.000732422 |
| 120010 | common | B | ordinary | 1.0 | 20.996093750 | 0.889802804 | 0.850077254 | 0.611012989 | 0.468681852 | 93.750000 | 0.930196882 | 0.000244141 |
| 120015 | common | B | ordinary | 1.0 | 21.166992188 | 0.865665183 | 0.815503594 | 0.602403298 | 0.459952096 | 100.000000 | 0.925578167 | 0.000000000 |
| pooled | common | B | ordinary | 1.25 | 15.423583984 | 0.828325394 | 0.746388980 | 0.512874290 | 0.344924740 | 79.427083 | 0.935717142 | 0.000427246 |
| 90000 | common | B | ordinary | 1.25 | 12.646484375 | 0.803029948 | 0.769306605 | 0.485027368 | 0.313512196 | 79.166667 | 0.937251645 | 0.000325521 |
| 90005 | common | B | ordinary | 1.25 | 19.140625000 | 0.875762523 | 0.844002803 | 0.574927538 | 0.425962516 | 87.500000 | 0.940386945 | 0.000325521 |
| 90010 | common | B | ordinary | 1.25 | 6.982421875 | 0.695684702 | 0.515800898 | 0.325145603 | 0.117975211 | 66.666667 | 0.950325572 | 0.000651042 |
| 90015 | common | B | ordinary | 1.25 | 13.037109375 | 0.803957480 | 0.655574258 | 0.480215544 | 0.271892032 | 70.833333 | 0.942307944 | 0.000651042 |
| 120000 | common | B | ordinary | 1.25 | 19.335937500 | 0.907038700 | 0.872970997 | 0.636822936 | 0.458611642 | 87.500000 | 0.924099109 | 0.000244141 |
| 120005 | common | B | ordinary | 1.25 | 17.431640625 | 0.785661814 | 0.647875433 | 0.508630214 | 0.376498518 | 75.000000 | 0.930415016 | 0.000732422 |
| 120010 | common | B | ordinary | 1.25 | 17.089843750 | 0.889802804 | 0.850077254 | 0.540964428 | 0.393500380 | 81.250000 | 0.931411094 | 0.000488281 |
| 120015 | common | B | ordinary | 1.25 | 17.724609375 | 0.865665183 | 0.815503594 | 0.551260687 | 0.401445429 | 87.500000 | 0.929539814 | 0.000000000 |
| pooled | common | B | aligned | 0.75 | 29.930623372 | 0.828325394 | 0.746388980 | 0.747934483 | 0.637154982 | 98.437500 | 0.924284466 | 0.000447591 |
| 90000 | common | B | aligned | 0.75 | 30.029296875 | 0.803029948 | 0.769306605 | 0.722284373 | 0.635241010 | 100.000000 | 0.919616669 | 0.000162760 |
| 90005 | common | B | aligned | 0.75 | 32.958984375 | 0.875762523 | 0.844002803 | 0.827348336 | 0.754200398 | 100.000000 | 0.924449759 | 0.000162760 |
| 90010 | common | B | aligned | 0.75 | 14.095052083 | 0.695684702 | 0.515800898 | 0.498943782 | 0.240694603 | 100.000000 | 0.946366359 | 0.000651042 |
| 90015 | common | B | aligned | 0.75 | 26.985677083 | 0.803957480 | 0.655574258 | 0.716868407 | 0.570605203 | 87.500000 | 0.933147735 | 0.000651042 |
| 120000 | common | B | aligned | 0.75 | 39.135742188 | 0.907038700 | 0.872970997 | 0.905160755 | 0.875744927 | 100.000000 | 0.912265541 | 0.000488281 |
| 120005 | common | B | aligned | 0.75 | 24.560546875 | 0.785661814 | 0.647875433 | 0.627865263 | 0.433388301 | 100.000000 | 0.929564410 | 0.000732422 |
| 120010 | common | B | aligned | 0.75 | 38.085937500 | 0.889802804 | 0.850077254 | 0.875378549 | 0.837207134 | 100.000000 | 0.913000928 | 0.000488281 |
| 120015 | common | B | aligned | 0.75 | 33.593750000 | 0.865665183 | 0.815503594 | 0.809626402 | 0.750158277 | 100.000000 | 0.915864326 | 0.000244141 |
| pooled | common | B | aligned | 1.0 | 28.505452474 | 0.828325394 | 0.746388980 | 0.717430405 | 0.601585912 | 97.916667 | 0.926786759 | 0.000447591 |
| 90000 | common | B | aligned | 1.0 | 26.757812500 | 0.803029948 | 0.769306605 | 0.684075574 | 0.594122687 | 100.000000 | 0.920821658 | 0.000162760 |
| 90005 | common | B | aligned | 1.0 | 31.901041667 | 0.875762523 | 0.844002803 | 0.798343594 | 0.709321271 | 100.000000 | 0.929722301 | 0.000162760 |
| 90010 | common | B | aligned | 1.0 | 14.290364583 | 0.695684702 | 0.515800898 | 0.458542875 | 0.218619835 | 95.833333 | 0.950003572 | 0.000651042 |
| 90015 | common | B | aligned | 1.0 | 25.602213542 | 0.803957480 | 0.655574258 | 0.695577496 | 0.547708726 | 87.500000 | 0.933669904 | 0.000651042 |
| 120000 | common | B | aligned | 1.0 | 38.769531250 | 0.907038700 | 0.872970997 | 0.904269926 | 0.874951978 | 100.000000 | 0.911733471 | 0.000488281 |
| 120005 | common | B | aligned | 1.0 | 24.023437500 | 0.785661814 | 0.647875433 | 0.602113956 | 0.426914459 | 100.000000 | 0.931441973 | 0.000732422 |
| 120010 | common | B | aligned | 1.0 | 36.059570312 | 0.889802804 | 0.850077254 | 0.858268501 | 0.805766987 | 100.000000 | 0.914232904 | 0.000488281 |
| 120015 | common | B | aligned | 1.0 | 30.639648438 | 0.865665183 | 0.815503594 | 0.738251317 | 0.635281358 | 100.000000 | 0.922668292 | 0.000244141 |
| pooled | common | B | aligned | 1.25 | 26.441446940 | 0.828325394 | 0.746388980 | 0.676220026 | 0.552511854 | 97.135417 | 0.929237373 | 0.000406901 |
| 90000 | common | B | aligned | 1.25 | 23.095703125 | 0.803029948 | 0.769306605 | 0.625348893 | 0.526687385 | 100.000000 | 0.925226784 | 0.000162760 |
| 90005 | common | B | aligned | 1.25 | 31.526692708 | 0.875762523 | 0.844002803 | 0.762258008 | 0.664435863 | 100.000000 | 0.933157548 | 0.000000000 |
| 90010 | common | B | aligned | 1.25 | 14.778645833 | 0.695684702 | 0.515800898 | 0.420878135 | 0.208940932 | 95.833333 | 0.951690156 | 0.000651042 |
| 90015 | common | B | aligned | 1.25 | 20.670572917 | 0.803957480 | 0.655574258 | 0.632911775 | 0.446508517 | 87.500000 | 0.933318435 | 0.000488281 |
| 120000 | common | B | aligned | 1.25 | 37.866210938 | 0.907038700 | 0.872970997 | 0.897439868 | 0.861798301 | 100.000000 | 0.912121540 | 0.000488281 |
| 120005 | common | B | aligned | 1.25 | 22.924804688 | 0.785661814 | 0.647875433 | 0.578435841 | 0.420909843 | 93.750000 | 0.933419981 | 0.000732422 |
| 120010 | common | B | aligned | 1.25 | 34.106445312 | 0.889802804 | 0.850077254 | 0.811808319 | 0.735454647 | 100.000000 | 0.918106442 | 0.000488281 |
| 120015 | common | B | aligned | 1.25 | 26.562500000 | 0.865665183 | 0.815503594 | 0.680679368 | 0.555359347 | 100.000000 | 0.926858098 | 0.000244141 |
| pooled | common | B | protected_copy | 0.75 | 31.204223633 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.910944235 | 0.000406901 |
| 90000 | common | B | protected_copy | 0.75 | 32.259114583 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.904384984 | 0.000162760 |
| 90005 | common | B | protected_copy | 0.75 | 37.500000000 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.915688770 | 0.000000000 |
| 90010 | common | B | protected_copy | 0.75 | 17.464192708 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.922889348 | 0.000813802 |
| 90015 | common | B | protected_copy | 0.75 | 26.985677083 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.923296826 | 0.000813802 |
| 120000 | common | B | protected_copy | 0.75 | 38.452148438 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.905615436 | 0.000244141 |
| 120005 | common | B | protected_copy | 0.75 | 23.901367188 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.906479626 | 0.000488281 |
| 120010 | common | B | protected_copy | 0.75 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.904941162 | 0.000488281 |
| 120015 | common | B | protected_copy | 0.75 | 35.717773438 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.904257727 | 0.000244141 |
| pooled | common | B | protected_copy | 1.0 | 31.204223633 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.910944235 | 0.000406901 |
| 90000 | common | B | protected_copy | 1.0 | 32.259114583 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.904384984 | 0.000162760 |
| 90005 | common | B | protected_copy | 1.0 | 37.500000000 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.915688770 | 0.000000000 |
| 90010 | common | B | protected_copy | 1.0 | 17.464192708 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.922889348 | 0.000813802 |
| 90015 | common | B | protected_copy | 1.0 | 26.985677083 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.923296826 | 0.000813802 |
| 120000 | common | B | protected_copy | 1.0 | 38.452148438 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.905615436 | 0.000244141 |
| 120005 | common | B | protected_copy | 1.0 | 23.901367188 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.906479626 | 0.000488281 |
| 120010 | common | B | protected_copy | 1.0 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.904941162 | 0.000488281 |
| 120015 | common | B | protected_copy | 1.0 | 35.717773438 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.904257727 | 0.000244141 |
| pooled | common | B | protected_copy | 1.25 | 31.204223633 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.910944235 | 0.000406901 |
| 90000 | common | B | protected_copy | 1.25 | 32.259114583 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.904384984 | 0.000162760 |
| 90005 | common | B | protected_copy | 1.25 | 37.500000000 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.915688770 | 0.000000000 |
| 90010 | common | B | protected_copy | 1.25 | 17.464192708 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.922889348 | 0.000813802 |
| 90015 | common | B | protected_copy | 1.25 | 26.985677083 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.923296826 | 0.000813802 |
| 120000 | common | B | protected_copy | 1.25 | 38.452148438 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.905615436 | 0.000244141 |
| 120005 | common | B | protected_copy | 1.25 | 23.901367188 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.906479626 | 0.000488281 |
| 120010 | common | B | protected_copy | 1.25 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.904941162 | 0.000488281 |
| 120015 | common | B | protected_copy | 1.25 | 35.717773438 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.904257727 | 0.000244141 |
| pooled | common | B | ordinary_read_off | 0.75 | -16.136678060 | 0.828325394 | 0.746388980 | 0.133302346 | -0.272518392 | 19.270833 | 0.937082846 | 0.000366211 |
| 90000 | common | B | ordinary_read_off | 0.75 | -15.250651042 | 0.803029948 | 0.769306605 | 0.131405920 | -0.249319369 | 20.833333 | 0.945271673 | 0.000325521 |
| 90005 | common | B | ordinary_read_off | 0.75 | -12.500000000 | 0.875762523 | 0.844002803 | 0.138271480 | -0.184738137 | 16.666667 | 0.932646476 | 0.000162760 |
| 90010 | common | B | ordinary_read_off | 0.75 | -10.742187500 | 0.695684702 | 0.515800898 | 0.137267743 | -0.226798881 | 29.166667 | 0.933108359 | 0.000325521 |
| 90015 | common | B | ordinary_read_off | 0.75 | -15.087890625 | 0.803957480 | 0.655574258 | 0.129928449 | -0.263951394 | 25.000000 | 0.940227428 | 0.000651042 |
| 120000 | common | B | ordinary_read_off | 0.75 | -13.916015625 | 0.907038700 | 0.872970997 | 0.140398430 | -0.213010175 | 18.750000 | 0.934411842 | 0.000000000 |
| 120005 | common | B | ordinary_read_off | 0.75 | -17.456054688 | 0.785661814 | 0.647875433 | 0.150048265 | -0.270338641 | 18.750000 | 0.928934585 | 0.000244141 |
| 120010 | common | B | ordinary_read_off | 0.75 | -20.166015625 | 0.889802804 | 0.850077254 | 0.107010012 | -0.355146223 | 12.500000 | 0.942741331 | 0.000976562 |
| 120015 | common | B | ordinary_read_off | 0.75 | -23.974609375 | 0.865665183 | 0.815503594 | 0.132088470 | -0.416844320 | 12.500000 | 0.939321070 | 0.000244141 |
| pooled | common | B | ordinary_read_off | 1.0 | -19.803873698 | 0.828325394 | 0.746388980 | 0.104559079 | -0.363779281 | 11.458333 | 0.949478748 | 0.000447591 |
| 90000 | common | B | ordinary_read_off | 1.0 | -20.035807292 | 0.803029948 | 0.769306605 | 0.106136047 | -0.352414530 | 16.666667 | 0.952283763 | 0.000488281 |
| 90005 | common | B | ordinary_read_off | 1.0 | -16.569010417 | 0.875762523 | 0.844002803 | 0.120852173 | -0.271556073 | 4.166667 | 0.955123747 | 0.000488281 |
| 90010 | common | B | ordinary_read_off | 1.0 | -16.438802083 | 0.695684702 | 0.515800898 | 0.120814572 | -0.291820235 | 12.500000 | 0.941713502 | 0.000488281 |
| 90015 | common | B | ordinary_read_off | 1.0 | -16.910807292 | 0.803957480 | 0.655574258 | 0.094224179 | -0.328488041 | 20.833333 | 0.951201422 | 0.000651042 |
| 120000 | common | B | ordinary_read_off | 1.0 | -19.897460938 | 0.907038700 | 0.872970997 | 0.113435475 | -0.326679827 | 6.250000 | 0.948103082 | 0.000244141 |
| 120005 | common | B | ordinary_read_off | 1.0 | -20.605468750 | 0.785661814 | 0.647875433 | 0.109049303 | -0.394195508 | 6.250000 | 0.949459027 | 0.000000000 |
| 120010 | common | B | ordinary_read_off | 1.0 | -21.166992188 | 0.889802804 | 0.850077254 | 0.075491516 | -0.412827036 | 12.500000 | 0.948995447 | 0.000976562 |
| 120015 | common | B | ordinary_read_off | 1.0 | -26.806640625 | 0.865665183 | 0.815503594 | 0.096469367 | -0.532252999 | 12.500000 | 0.948949993 | 0.000244141 |
| pooled | common | B | ordinary_read_off | 1.25 | -21.452840169 | 0.828325394 | 0.746388980 | 0.081583093 | -0.424348655 | 11.458333 | 0.957996759 | 0.000457764 |
| 90000 | common | B | ordinary_read_off | 1.25 | -20.817057292 | 0.803029948 | 0.769306605 | 0.092592563 | -0.377172790 | 12.500000 | 0.956110918 | 0.000325521 |
| 90005 | common | B | ordinary_read_off | 1.25 | -18.440755208 | 0.875762523 | 0.844002803 | 0.089445234 | -0.350776120 | 20.833333 | 0.963301920 | 0.000325521 |
| 90010 | common | B | ordinary_read_off | 1.25 | -17.822265625 | 0.695684702 | 0.515800898 | 0.089610108 | -0.354870322 | 12.500000 | 0.953109023 | 0.000488281 |
| 90015 | common | B | ordinary_read_off | 1.25 | -19.449869792 | 0.803957480 | 0.655574258 | 0.080215828 | -0.374597218 | 8.333333 | 0.961055940 | 0.000813802 |
| 120000 | common | B | ordinary_read_off | 1.25 | -24.145507812 | 0.907038700 | 0.872970997 | 0.085721239 | -0.468662755 | 0.000000 | 0.956712326 | 0.000000000 |
| 120005 | common | B | ordinary_read_off | 1.25 | -22.827148438 | 0.785661814 | 0.647875433 | 0.069646214 | -0.474056973 | 12.500000 | 0.960356899 | 0.000244141 |
| 120010 | common | B | ordinary_read_off | 1.25 | -21.386718750 | 0.889802804 | 0.850077254 | 0.069952792 | -0.434059647 | 12.500000 | 0.955530724 | 0.001220703 |
| 120015 | common | B | ordinary_read_off | 1.25 | -26.733398438 | 0.865665183 | 0.815503594 | 0.075480765 | -0.560593411 | 12.500000 | 0.957796323 | 0.000244141 |
| pooled | common | B | aligned_read_off | 0.75 | -17.370605469 | 0.828325394 | 0.746388980 | 0.142937014 | -0.268838228 | 12.760417 | 0.938499687 | 0.000386556 |
| 90000 | common | B | aligned_read_off | 0.75 | -16.503906250 | 0.803029948 | 0.769306605 | 0.144960353 | -0.230815429 | 8.333333 | 0.939788729 | 0.000162760 |
| 90005 | common | B | aligned_read_off | 0.75 | -15.836588542 | 0.875762523 | 0.844002803 | 0.148673543 | -0.242262434 | 16.666667 | 0.938979123 | 0.000325521 |
| 90010 | common | B | aligned_read_off | 0.75 | -15.983072917 | 0.695684702 | 0.515800898 | 0.144101919 | -0.247645961 | 25.000000 | 0.944126394 | 0.000325521 |
| 90015 | common | B | aligned_read_off | 0.75 | -17.740885417 | 0.803957480 | 0.655574258 | 0.140557359 | -0.251046854 | 8.333333 | 0.934436304 | 0.000813802 |
| 120000 | common | B | aligned_read_off | 0.75 | -14.282226562 | 0.907038700 | 0.872970997 | 0.142299695 | -0.196020938 | 18.750000 | 0.939642799 | 0.000244141 |
| 120005 | common | B | aligned_read_off | 0.75 | -19.311523438 | 0.785661814 | 0.647875433 | 0.149440121 | -0.323238095 | 6.250000 | 0.935446101 | 0.000244141 |
| 120010 | common | B | aligned_read_off | 0.75 | -18.701171875 | 0.889802804 | 0.850077254 | 0.143566566 | -0.296878221 | 12.500000 | 0.937917823 | 0.000732422 |
| 120015 | common | B | aligned_read_off | 0.75 | -20.605468750 | 0.865665183 | 0.815503594 | 0.129896552 | -0.362797887 | 6.250000 | 0.937660226 | 0.000244141 |
| pooled | common | B | aligned_read_off | 1.0 | -20.608520508 | 0.828325394 | 0.746388980 | 0.109727160 | -0.359095961 | 5.729167 | 0.952649348 | 0.000457764 |
| 90000 | common | B | aligned_read_off | 1.0 | -20.296223958 | 0.803029948 | 0.769306605 | 0.113890381 | -0.355666857 | 0.000000 | 0.954170862 | 0.000325521 |
| 90005 | common | B | aligned_read_off | 1.0 | -17.692057292 | 0.875762523 | 0.844002803 | 0.128002191 | -0.294875057 | 16.666667 | 0.958442694 | 0.000162760 |
| 90010 | common | B | aligned_read_off | 1.0 | -19.205729167 | 0.695684702 | 0.515800898 | 0.106789812 | -0.339941436 | 12.500000 | 0.951924600 | 0.000488281 |
| 90015 | common | B | aligned_read_off | 1.0 | -19.173177083 | 0.803957480 | 0.655574258 | 0.097183700 | -0.313371024 | 4.166667 | 0.947657414 | 0.000488281 |
| 120000 | common | B | aligned_read_off | 1.0 | -18.603515625 | 0.907038700 | 0.872970997 | 0.125068803 | -0.280203477 | 6.250000 | 0.959180669 | 0.000244141 |
| 120005 | common | B | aligned_read_off | 1.0 | -23.071289062 | 0.785661814 | 0.647875433 | 0.112034098 | -0.456612813 | 6.250000 | 0.952529174 | 0.000488281 |
| 120010 | common | B | aligned_read_off | 1.0 | -20.776367188 | 0.889802804 | 0.850077254 | 0.101241150 | -0.342407143 | 0.000000 | 0.948133843 | 0.001220703 |
| 120015 | common | B | aligned_read_off | 1.0 | -26.049804688 | 0.865665183 | 0.815503594 | 0.093607141 | -0.489689880 | 0.000000 | 0.949155529 | 0.000244141 |
| pooled | common | B | aligned_read_off | 1.25 | -21.976725260 | 0.828325394 | 0.746388980 | 0.085760412 | -0.417419974 | 7.031250 | 0.960427120 | 0.000417074 |
| 90000 | common | B | aligned_read_off | 1.25 | -20.491536458 | 0.803029948 | 0.769306605 | 0.097924741 | -0.390509751 | 8.333333 | 0.959827534 | 0.000488281 |
| 90005 | common | B | aligned_read_off | 1.25 | -19.140625000 | 0.875762523 | 0.844002803 | 0.082892978 | -0.372585925 | 16.666667 | 0.968128081 | 0.000162760 |
| 90010 | common | B | aligned_read_off | 1.25 | -20.312500000 | 0.695684702 | 0.515800898 | 0.084571356 | -0.396746973 | 8.333333 | 0.956824798 | 0.000488281 |
| 90015 | common | B | aligned_read_off | 1.25 | -20.361328125 | 0.803957480 | 0.655574258 | 0.089229268 | -0.362478666 | 4.166667 | 0.954069305 | 0.000488281 |
| 120000 | common | B | aligned_read_off | 1.25 | -22.656250000 | 0.907038700 | 0.872970997 | 0.094961333 | -0.418167777 | 0.000000 | 0.964014945 | 0.000000000 |
| 120005 | common | B | aligned_read_off | 1.25 | -27.075195312 | 0.785661814 | 0.647875433 | 0.073590376 | -0.543592838 | 12.500000 | 0.961124924 | 0.000488281 |
| 120010 | common | B | aligned_read_off | 1.25 | -20.996093750 | 0.889802804 | 0.850077254 | 0.082978374 | -0.380141146 | 0.000000 | 0.963389968 | 0.000976562 |
| 120015 | common | B | aligned_read_off | 1.25 | -24.780273438 | 0.865665183 | 0.815503594 | 0.079934870 | -0.475136718 | 6.250000 | 0.956037405 | 0.000244141 |
| pooled | common | B | write_off | 0.75 | -2.312215169 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | B | write_off | 0.75 | -0.537109375 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | B | write_off | 0.75 | 1.595052083 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | B | write_off | 0.75 | -9.521484375 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | B | write_off | 0.75 | -2.050781250 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | B | write_off | 0.75 | -3.735351562 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | B | write_off | 0.75 | -0.610351562 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | B | write_off | 0.75 | -3.051757812 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | B | write_off | 0.75 | -0.585937500 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | common | B | write_off | 1.0 | -2.312215169 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | B | write_off | 1.0 | -0.537109375 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | B | write_off | 1.0 | 1.595052083 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | B | write_off | 1.0 | -9.521484375 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | B | write_off | 1.0 | -2.050781250 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | B | write_off | 1.0 | -3.735351562 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | B | write_off | 1.0 | -0.610351562 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | B | write_off | 1.0 | -3.051757812 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | B | write_off | 1.0 | -0.585937500 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | common | B | write_off | 1.25 | -2.312215169 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | common | B | write_off | 1.25 | -0.537109375 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | common | B | write_off | 1.25 | 1.595052083 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | common | B | write_off | 1.25 | -9.521484375 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | common | B | write_off | 1.25 | -2.050781250 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | common | B | write_off | 1.25 | -3.735351562 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | common | B | write_off | 1.25 | -0.610351562 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | common | B | write_off | 1.25 | -3.051757812 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | common | B | write_off | 1.25 | -0.585937500 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | native | A | ordinary | 0.75 | 42.996215820 | 0.932061265 | 0.916899718 | 0.937136543 | 0.918751295 | 100.000000 | 0.976319648 | 0.000508626 |
| 90000 | native | A | ordinary | 0.75 | 43.684895833 | 0.915634225 | 0.906156900 | 0.948010947 | 0.931710010 | 100.000000 | 0.972870557 | 0.000325521 |
| 90005 | native | A | ordinary | 0.75 | 42.138671875 | 0.921236109 | 0.903719580 | 0.925914366 | 0.904246323 | 100.000000 | 0.979573756 | 0.000651042 |
| 90010 | native | A | ordinary | 0.75 | 42.594401042 | 0.950583251 | 0.932174534 | 0.928904495 | 0.910625520 | 100.000000 | 0.973287543 | 0.000325521 |
| 90015 | native | A | ordinary | 0.75 | 43.017578125 | 0.953050250 | 0.941181517 | 0.937089768 | 0.917695242 | 100.000000 | 0.984210440 | 0.000813802 |
| 120000 | native | A | ordinary | 0.75 | 43.774414062 | 0.948982398 | 0.939348254 | 0.948506682 | 0.930700685 | 100.000000 | 0.981111066 | 0.000000000 |
| 120005 | native | A | ordinary | 0.75 | 42.578125000 | 0.932801971 | 0.912726754 | 0.925838954 | 0.907542534 | 100.000000 | 0.974138317 | 0.000488281 |
| 120010 | native | A | ordinary | 0.75 | 42.675781250 | 0.912717494 | 0.893541307 | 0.934374834 | 0.916704036 | 100.000000 | 0.972112573 | 0.000488281 |
| 120015 | native | A | ordinary | 0.75 | 43.505859375 | 0.921484421 | 0.906348900 | 0.948452296 | 0.930786010 | 100.000000 | 0.973252936 | 0.000976562 |
| pooled | native | A | ordinary | 1.0 | 43.780517578 | 0.932061265 | 0.916899718 | 0.943191180 | 0.927481266 | 100.000000 | 0.970460579 | 0.000478109 |
| 90000 | native | A | ordinary | 1.0 | 44.335937500 | 0.915634225 | 0.906156900 | 0.952297548 | 0.937936616 | 100.000000 | 0.966660440 | 0.000325521 |
| 90005 | native | A | ordinary | 1.0 | 42.724609375 | 0.921236109 | 0.903719580 | 0.934664254 | 0.915592096 | 100.000000 | 0.973568792 | 0.000651042 |
| 90010 | native | A | ordinary | 1.0 | 43.359375000 | 0.950583251 | 0.932174534 | 0.934598812 | 0.918212298 | 100.000000 | 0.966804797 | 0.000325521 |
| 90015 | native | A | ordinary | 1.0 | 44.091796875 | 0.953050250 | 0.941181517 | 0.945086246 | 0.929143017 | 100.000000 | 0.979587901 | 0.000813802 |
| 120000 | native | A | ordinary | 1.0 | 44.506835938 | 0.948982398 | 0.939348254 | 0.950545151 | 0.935931321 | 100.000000 | 0.975099687 | 0.000000000 |
| 120005 | native | A | ordinary | 1.0 | 43.286132812 | 0.932801971 | 0.912726754 | 0.931032858 | 0.914428641 | 100.000000 | 0.967555901 | 0.000488281 |
| 120010 | native | A | ordinary | 1.0 | 43.774414062 | 0.912717494 | 0.893541307 | 0.942451070 | 0.927370007 | 100.000000 | 0.966761288 | 0.000488281 |
| 120015 | native | A | ordinary | 1.0 | 44.165039062 | 0.921484421 | 0.906348900 | 0.954853502 | 0.941236137 | 100.000000 | 0.967645823 | 0.000732422 |
| pooled | native | A | ordinary | 1.25 | 44.067382812 | 0.932061265 | 0.916899718 | 0.945699056 | 0.931835493 | 100.000000 | 0.963918858 | 0.000559489 |
| 90000 | native | A | ordinary | 1.25 | 44.547526042 | 0.915634225 | 0.906156900 | 0.952403465 | 0.939975989 | 100.000000 | 0.959304242 | 0.000325521 |
| 90005 | native | A | ordinary | 1.25 | 43.180338542 | 0.921236109 | 0.903719580 | 0.939772904 | 0.924283710 | 100.000000 | 0.966394355 | 0.000488281 |
| 90010 | native | A | ordinary | 1.25 | 43.912760417 | 0.950583251 | 0.932174534 | 0.936497324 | 0.922014937 | 100.000000 | 0.960261324 | 0.000488281 |
| 90015 | native | A | ordinary | 1.25 | 44.580078125 | 0.953050250 | 0.941181517 | 0.948141095 | 0.934277391 | 100.000000 | 0.972968483 | 0.000976562 |
| 120000 | native | A | ordinary | 1.25 | 44.458007812 | 0.948982398 | 0.939348254 | 0.951057989 | 0.937299825 | 100.000000 | 0.968215799 | 0.000000000 |
| 120005 | native | A | ordinary | 1.25 | 43.408203125 | 0.932801971 | 0.912726754 | 0.934632323 | 0.919542809 | 100.000000 | 0.960895213 | 0.000488281 |
| 120010 | native | A | ordinary | 1.25 | 43.969726562 | 0.912717494 | 0.893541307 | 0.945235250 | 0.932261109 | 100.000000 | 0.961026098 | 0.000732422 |
| 120015 | native | A | ordinary | 1.25 | 44.482421875 | 0.921484421 | 0.906348900 | 0.957852095 | 0.945028171 | 100.000000 | 0.962285352 | 0.000976562 |
| pooled | native | A | aligned | 0.75 | 43.414306641 | 0.932061265 | 0.916899718 | 0.943910609 | 0.929804379 | 100.000000 | 0.980841488 | 0.000539144 |
| 90000 | native | A | aligned | 0.75 | 42.089843750 | 0.915634225 | 0.906156900 | 0.921221979 | 0.908297357 | 100.000000 | 0.978154384 | 0.000488281 |
| 90005 | native | A | aligned | 0.75 | 42.545572917 | 0.921236109 | 0.903719580 | 0.931183456 | 0.913778909 | 100.000000 | 0.984107027 | 0.000651042 |
| 90010 | native | A | aligned | 0.75 | 44.628906250 | 0.950583251 | 0.932174534 | 0.967809327 | 0.957014123 | 100.000000 | 0.980716011 | 0.000488281 |
| 90015 | native | A | aligned | 0.75 | 44.759114583 | 0.953050250 | 0.941181517 | 0.966145295 | 0.956303369 | 100.000000 | 0.989426443 | 0.000976562 |
| 120000 | native | A | aligned | 0.75 | 44.506835938 | 0.948982398 | 0.939348254 | 0.961807321 | 0.945547246 | 100.000000 | 0.984946510 | 0.000000000 |
| 120005 | native | A | aligned | 0.75 | 43.017578125 | 0.932801971 | 0.912726754 | 0.937281400 | 0.924723966 | 100.000000 | 0.976829220 | 0.000488281 |
| 120010 | native | A | aligned | 0.75 | 42.895507812 | 0.912717494 | 0.893541307 | 0.930031337 | 0.915921614 | 100.000000 | 0.975901754 | 0.000488281 |
| 120015 | native | A | aligned | 0.75 | 42.871093750 | 0.921484421 | 0.906348900 | 0.935804755 | 0.916848451 | 100.000000 | 0.976650556 | 0.000732422 |
| pooled | native | A | aligned | 1.0 | 44.046020508 | 0.932061265 | 0.916899718 | 0.948752744 | 0.937048170 | 100.000000 | 0.973795180 | 0.000518799 |
| 90000 | native | A | aligned | 1.0 | 42.757161458 | 0.915634225 | 0.906156900 | 0.926046670 | 0.914663890 | 100.000000 | 0.971373883 | 0.000488281 |
| 90005 | native | A | aligned | 1.0 | 43.212890625 | 0.921236109 | 0.903719580 | 0.937292675 | 0.923209551 | 100.000000 | 0.976291796 | 0.000651042 |
| 90010 | native | A | aligned | 1.0 | 45.361328125 | 0.950583251 | 0.932174534 | 0.971240217 | 0.962678885 | 100.000000 | 0.974245129 | 0.000325521 |
| 90015 | native | A | aligned | 1.0 | 45.182291667 | 0.953050250 | 0.941181517 | 0.967403966 | 0.958387842 | 100.000000 | 0.981250113 | 0.000976562 |
| 120000 | native | A | aligned | 1.0 | 45.312500000 | 0.948982398 | 0.939348254 | 0.965162001 | 0.951000056 | 100.000000 | 0.977664537 | 0.000000000 |
| 120005 | native | A | aligned | 1.0 | 43.847656250 | 0.932801971 | 0.912726754 | 0.942476304 | 0.932289611 | 100.000000 | 0.969905269 | 0.000488281 |
| 120010 | native | A | aligned | 1.0 | 43.530273438 | 0.912717494 | 0.893541307 | 0.937434443 | 0.925990957 | 100.000000 | 0.969687066 | 0.000488281 |
| 120015 | native | A | aligned | 1.0 | 43.164062500 | 0.921484421 | 0.906348900 | 0.942965676 | 0.928164568 | 100.000000 | 0.969943649 | 0.000732422 |
| pooled | native | A | aligned | 1.25 | 44.355265299 | 0.932061265 | 0.916899718 | 0.952761498 | 0.942797828 | 100.000000 | 0.966677029 | 0.000518799 |
| 90000 | native | A | aligned | 1.25 | 42.903645833 | 0.915634225 | 0.906156900 | 0.931131989 | 0.920819200 | 100.000000 | 0.963601696 | 0.000488281 |
| 90005 | native | A | aligned | 1.25 | 43.766276042 | 0.921236109 | 0.903719580 | 0.941957968 | 0.929573959 | 100.000000 | 0.967900845 | 0.000651042 |
| 90010 | native | A | aligned | 1.25 | 45.719401042 | 0.950583251 | 0.932174534 | 0.973188681 | 0.965637170 | 100.000000 | 0.967383164 | 0.000325521 |
| 90015 | native | A | aligned | 1.25 | 45.279947917 | 0.953050250 | 0.941181517 | 0.968304173 | 0.960297337 | 100.000000 | 0.974950817 | 0.000976562 |
| 120000 | native | A | aligned | 1.25 | 45.458984375 | 0.948982398 | 0.939348254 | 0.967205551 | 0.955653757 | 100.000000 | 0.970634385 | 0.000000000 |
| 120005 | native | A | aligned | 1.25 | 44.384765625 | 0.932801971 | 0.912726754 | 0.947222131 | 0.938590583 | 100.000000 | 0.962785692 | 0.000244141 |
| 120010 | native | A | aligned | 1.25 | 43.920898438 | 0.912717494 | 0.893541307 | 0.943649753 | 0.933998256 | 100.000000 | 0.962727975 | 0.000732422 |
| 120015 | native | A | aligned | 1.25 | 43.408203125 | 0.921484421 | 0.906348900 | 0.949431736 | 0.937812363 | 100.000000 | 0.963431657 | 0.000732422 |
| pooled | native | A | protected_copy | 0.75 | 42.456054688 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.976095223 | 0.000539144 |
| 90000 | native | A | protected_copy | 0.75 | 41.324869792 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.971547084 | 0.000488281 |
| 90005 | native | A | protected_copy | 0.75 | 42.073567708 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.978484535 | 0.000651042 |
| 90010 | native | A | protected_copy | 0.75 | 42.903645833 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.975592376 | 0.000488281 |
| 90015 | native | A | protected_copy | 0.75 | 43.522135417 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.985138555 | 0.000976562 |
| 120000 | native | A | protected_copy | 0.75 | 43.994140625 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.980177713 | 0.000000000 |
| 120005 | native | A | protected_copy | 0.75 | 42.382812500 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.972910701 | 0.000488281 |
| 120010 | native | A | protected_copy | 0.75 | 41.625976562 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.971562625 | 0.000488281 |
| 120015 | native | A | protected_copy | 0.75 | 41.821289062 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.973348199 | 0.000732422 |
| pooled | native | A | protected_copy | 1.0 | 42.878214518 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.969846014 | 0.000549316 |
| 90000 | native | A | protected_copy | 1.0 | 41.813151042 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.965137815 | 0.000488281 |
| 90005 | native | A | protected_copy | 1.0 | 42.513020833 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.972024505 | 0.000651042 |
| 90010 | native | A | protected_copy | 1.0 | 43.408203125 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.969935523 | 0.000325521 |
| 90015 | native | A | protected_copy | 1.0 | 43.977864583 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.978401028 | 0.000976562 |
| 120000 | native | A | protected_copy | 1.0 | 44.287109375 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.973755747 | 0.000000000 |
| 120005 | native | A | protected_copy | 1.0 | 42.626953125 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.966770930 | 0.000488281 |
| 120010 | native | A | protected_copy | 1.0 | 42.260742188 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.965268060 | 0.000732422 |
| 120015 | native | A | protected_copy | 1.0 | 42.138671875 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.967474504 | 0.000732422 |
| pooled | native | A | protected_copy | 1.25 | 43.123372396 | 0.932061265 | 0.916899718 | 0.932061265 | 0.916899718 | 100.000000 | 0.963205361 | 0.000488281 |
| 90000 | native | A | protected_copy | 1.25 | 42.171223958 | 0.915634225 | 0.906156900 | 0.915634225 | 0.906156900 | 100.000000 | 0.958448532 | 0.000325521 |
| 90005 | native | A | protected_copy | 1.25 | 42.692057292 | 0.921236109 | 0.903719580 | 0.921236109 | 0.903719580 | 100.000000 | 0.965282569 | 0.000651042 |
| 90010 | native | A | protected_copy | 1.25 | 43.684895833 | 0.950583251 | 0.932174534 | 0.950583251 | 0.932174534 | 100.000000 | 0.963480291 | 0.000325521 |
| 90015 | native | A | protected_copy | 1.25 | 44.222005208 | 0.953050250 | 0.941181517 | 0.953050250 | 0.941181517 | 100.000000 | 0.971415477 | 0.001139323 |
| 120000 | native | A | protected_copy | 1.25 | 44.580078125 | 0.948982398 | 0.939348254 | 0.948982398 | 0.939348254 | 100.000000 | 0.967189171 | 0.000000000 |
| 120005 | native | A | protected_copy | 1.25 | 43.090820312 | 0.932801971 | 0.912726754 | 0.932801971 | 0.912726754 | 100.000000 | 0.960202084 | 0.000244141 |
| 120010 | native | A | protected_copy | 1.25 | 42.529296875 | 0.912717494 | 0.893541307 | 0.912717494 | 0.893541307 | 100.000000 | 0.958618146 | 0.000732422 |
| 120015 | native | A | protected_copy | 1.25 | 42.016601562 | 0.921484421 | 0.906348900 | 0.921484421 | 0.906348900 | 100.000000 | 0.961006616 | 0.000488281 |
| pooled | native | A | ordinary_read_off | 0.75 | 15.689086914 | 0.932061265 | 0.916899718 | 0.405820739 | 0.272518392 | 80.729167 | 0.947636407 | 0.000417074 |
| 90000 | native | A | ordinary_read_off | 0.75 | 14.680989583 | 0.915634225 | 0.906156900 | 0.380725289 | 0.249319369 | 79.166667 | 0.955579803 | 0.000325521 |
| 90005 | native | A | ordinary_read_off | 0.75 | 12.158203125 | 0.921236109 | 0.903719580 | 0.323009616 | 0.184738137 | 83.333333 | 0.943133461 | 0.000162760 |
| 90010 | native | A | ordinary_read_off | 0.75 | 10.384114583 | 0.950583251 | 0.932174534 | 0.364066623 | 0.226798881 | 70.833333 | 0.944553190 | 0.000325521 |
| 90015 | native | A | ordinary_read_off | 0.75 | 14.436848958 | 0.953050250 | 0.941181517 | 0.393879843 | 0.263951394 | 75.000000 | 0.950869928 | 0.000813802 |
| 120000 | native | A | ordinary_read_off | 0.75 | 13.696289062 | 0.948982398 | 0.939348254 | 0.353408605 | 0.213010175 | 81.250000 | 0.946070704 | 0.000000000 |
| 120005 | native | A | ordinary_read_off | 0.75 | 17.089843750 | 0.932801971 | 0.912726754 | 0.420386906 | 0.270338641 | 81.250000 | 0.939471053 | 0.000244141 |
| 120010 | native | A | ordinary_read_off | 0.75 | 19.750976562 | 0.912717494 | 0.893541307 | 0.462156235 | 0.355146223 | 87.500000 | 0.952121582 | 0.001220703 |
| 120015 | native | A | ordinary_read_off | 0.75 | 23.315429688 | 0.921484421 | 0.906348900 | 0.548932791 | 0.416844320 | 87.500000 | 0.949291539 | 0.000244141 |
| pooled | native | A | ordinary_read_off | 1.0 | 19.803873698 | 0.932061265 | 0.916899718 | 0.468338360 | 0.363779281 | 88.541667 | 0.949478748 | 0.000447591 |
| 90000 | native | A | ordinary_read_off | 1.0 | 20.035807292 | 0.915634225 | 0.906156900 | 0.458550578 | 0.352414530 | 83.333333 | 0.952283763 | 0.000488281 |
| 90005 | native | A | ordinary_read_off | 1.0 | 16.569010417 | 0.921236109 | 0.903719580 | 0.392408245 | 0.271556073 | 95.833333 | 0.955123747 | 0.000488281 |
| 90010 | native | A | ordinary_read_off | 1.0 | 16.438802083 | 0.950583251 | 0.932174534 | 0.412634807 | 0.291820235 | 87.500000 | 0.941713502 | 0.000488281 |
| 90015 | native | A | ordinary_read_off | 1.0 | 16.910807292 | 0.953050250 | 0.941181517 | 0.422712221 | 0.328488041 | 79.166667 | 0.951201422 | 0.000651042 |
| 120000 | native | A | ordinary_read_off | 1.0 | 19.897460938 | 0.948982398 | 0.939348254 | 0.440115302 | 0.326679827 | 93.750000 | 0.948103082 | 0.000244141 |
| 120005 | native | A | ordinary_read_off | 1.0 | 20.605468750 | 0.932801971 | 0.912726754 | 0.503244811 | 0.394195508 | 93.750000 | 0.949459027 | 0.000000000 |
| 120010 | native | A | ordinary_read_off | 1.0 | 21.166992188 | 0.912717494 | 0.893541307 | 0.488318551 | 0.412827036 | 87.500000 | 0.948995447 | 0.000976562 |
| 120015 | native | A | ordinary_read_off | 1.0 | 26.806640625 | 0.921484421 | 0.906348900 | 0.628722366 | 0.532252999 | 87.500000 | 0.948949993 | 0.000244141 |
| pooled | native | A | ordinary_read_off | 1.25 | 21.581013997 | 0.932061265 | 0.916899718 | 0.505931747 | 0.424348655 | 88.541667 | 0.950068347 | 0.000376383 |
| 90000 | native | A | ordinary_read_off | 1.25 | 20.996093750 | 0.915634225 | 0.906156900 | 0.469765353 | 0.377172790 | 87.500000 | 0.947560382 | 0.000325521 |
| 90005 | native | A | ordinary_read_off | 1.25 | 18.587239583 | 0.921236109 | 0.903719580 | 0.440221353 | 0.350776120 | 79.166667 | 0.954933931 | 0.000325521 |
| 90010 | native | A | ordinary_read_off | 1.25 | 17.724609375 | 0.950583251 | 0.932174534 | 0.444480431 | 0.354870322 | 87.500000 | 0.944659406 | 0.000488281 |
| 90015 | native | A | ordinary_read_off | 1.25 | 19.514973958 | 0.953050250 | 0.941181517 | 0.454813046 | 0.374597218 | 91.666667 | 0.952549327 | 0.000651042 |
| 120000 | native | A | ordinary_read_off | 1.25 | 24.389648438 | 0.948982398 | 0.939348254 | 0.554383994 | 0.468662755 | 100.000000 | 0.949347778 | 0.000000000 |
| 120005 | native | A | ordinary_read_off | 1.25 | 23.046875000 | 0.932801971 | 0.912726754 | 0.543703187 | 0.474056973 | 87.500000 | 0.952852574 | 0.000000000 |
| 120010 | native | A | ordinary_read_off | 1.25 | 21.411132812 | 0.912717494 | 0.893541307 | 0.504012440 | 0.434059647 | 87.500000 | 0.947264097 | 0.000976562 |
| 120015 | native | A | ordinary_read_off | 1.25 | 26.977539062 | 0.921484421 | 0.906348900 | 0.636074176 | 0.560593411 | 87.500000 | 0.951379283 | 0.000244141 |
| pooled | native | A | aligned_read_off | 0.75 | 17.039998372 | 0.932061265 | 0.916899718 | 0.411775241 | 0.268838228 | 87.239583 | 0.949789975 | 0.000447591 |
| 90000 | native | A | aligned_read_off | 0.75 | 16.113281250 | 0.915634225 | 0.906156900 | 0.375775783 | 0.230815429 | 91.666667 | 0.950933319 | 0.000488281 |
| 90005 | native | A | aligned_read_off | 0.75 | 15.039062500 | 0.921236109 | 0.903719580 | 0.390935977 | 0.242262434 | 83.333333 | 0.951950358 | 0.000651042 |
| 90010 | native | A | aligned_read_off | 0.75 | 15.494791667 | 0.950583251 | 0.932174534 | 0.391747880 | 0.247645961 | 75.000000 | 0.955378313 | 0.000325521 |
| 90015 | native | A | aligned_read_off | 0.75 | 17.480468750 | 0.953050250 | 0.941181517 | 0.391604213 | 0.251046854 | 91.666667 | 0.944937481 | 0.000651042 |
| 120000 | native | A | aligned_read_off | 0.75 | 14.379882812 | 0.948982398 | 0.939348254 | 0.338320634 | 0.196020938 | 81.250000 | 0.952175165 | 0.000244141 |
| 120005 | native | A | aligned_read_off | 0.75 | 19.018554688 | 0.932801971 | 0.912726754 | 0.472678216 | 0.323238095 | 93.750000 | 0.947109676 | 0.000244141 |
| 120010 | native | A | aligned_read_off | 0.75 | 18.725585938 | 0.912717494 | 0.893541307 | 0.440444787 | 0.296878221 | 87.500000 | 0.948328834 | 0.000732422 |
| 120015 | native | A | aligned_read_off | 0.75 | 20.068359375 | 0.921484421 | 0.906348900 | 0.492694440 | 0.362797887 | 93.750000 | 0.947506658 | 0.000244141 |
| pooled | native | A | aligned_read_off | 1.0 | 20.608520508 | 0.932061265 | 0.916899718 | 0.468823120 | 0.359095961 | 94.270833 | 0.952649348 | 0.000457764 |
| 90000 | native | A | aligned_read_off | 1.0 | 20.296223958 | 0.915634225 | 0.906156900 | 0.469557238 | 0.355666857 | 100.000000 | 0.954170862 | 0.000325521 |
| 90005 | native | A | aligned_read_off | 1.0 | 17.692057292 | 0.921236109 | 0.903719580 | 0.422877248 | 0.294875057 | 83.333333 | 0.958442694 | 0.000162760 |
| 90010 | native | A | aligned_read_off | 1.0 | 19.205729167 | 0.950583251 | 0.932174534 | 0.446731249 | 0.339941436 | 87.500000 | 0.951924600 | 0.000488281 |
| 90015 | native | A | aligned_read_off | 1.0 | 19.173177083 | 0.953050250 | 0.941181517 | 0.410554724 | 0.313371024 | 95.833333 | 0.947657414 | 0.000488281 |
| 120000 | native | A | aligned_read_off | 1.0 | 18.603515625 | 0.948982398 | 0.939348254 | 0.405272280 | 0.280203477 | 93.750000 | 0.959180669 | 0.000244141 |
| 120005 | native | A | aligned_read_off | 1.0 | 23.071289062 | 0.932801971 | 0.912726754 | 0.568646911 | 0.456612813 | 93.750000 | 0.952529174 | 0.000488281 |
| 120010 | native | A | aligned_read_off | 1.0 | 20.776367188 | 0.912717494 | 0.893541307 | 0.443648292 | 0.342407143 | 100.000000 | 0.948133843 | 0.001220703 |
| 120015 | native | A | aligned_read_off | 1.0 | 26.049804688 | 0.921484421 | 0.906348900 | 0.583297021 | 0.489689880 | 100.000000 | 0.949155529 | 0.000244141 |
| pooled | native | A | aligned_read_off | 1.25 | 22.121175130 | 0.932061265 | 0.916899718 | 0.503180386 | 0.417419974 | 92.968750 | 0.952243590 | 0.000345866 |
| 90000 | native | A | aligned_read_off | 1.25 | 20.817057292 | 0.915634225 | 0.906156900 | 0.488434492 | 0.390509751 | 91.666667 | 0.950908842 | 0.000162760 |
| 90005 | native | A | aligned_read_off | 1.25 | 19.482421875 | 0.921236109 | 0.903719580 | 0.455478902 | 0.372585925 | 83.333333 | 0.960294599 | 0.000162760 |
| 90010 | native | A | aligned_read_off | 1.25 | 20.361328125 | 0.950583251 | 0.932174534 | 0.481318329 | 0.396746973 | 91.666667 | 0.948562425 | 0.000488281 |
| 90015 | native | A | aligned_read_off | 1.25 | 20.458984375 | 0.953050250 | 0.941181517 | 0.451707934 | 0.362478666 | 95.833333 | 0.945687015 | 0.000488281 |
| 120000 | native | A | aligned_read_off | 1.25 | 22.583007812 | 0.948982398 | 0.939348254 | 0.513129110 | 0.418167777 | 100.000000 | 0.955533274 | 0.000000000 |
| 120005 | native | A | aligned_read_off | 1.25 | 27.099609375 | 0.932801971 | 0.912726754 | 0.617183215 | 0.543592838 | 87.500000 | 0.953262221 | 0.000488281 |
| 120010 | native | A | aligned_read_off | 1.25 | 21.093750000 | 0.912717494 | 0.893541307 | 0.463119520 | 0.380141146 | 100.000000 | 0.954961013 | 0.000732422 |
| 120015 | native | A | aligned_read_off | 1.25 | 25.073242188 | 0.921484421 | 0.906348900 | 0.555071588 | 0.475136718 | 93.750000 | 0.948739328 | 0.000244141 |
| pooled | native | A | write_off | 0.75 | 1.315307617 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.733315022 | 0.000111898 |
| 90000 | native | A | write_off | 0.75 | 0.244140625 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.725577573 | 0.000162760 |
| 90005 | native | A | write_off | 0.75 | -0.895182292 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.736250110 | 0.000000000 |
| 90010 | native | A | write_off | 0.75 | 5.777994792 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.734997681 | 0.000000000 |
| 90015 | native | A | write_off | 0.75 | 0.976562500 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.733325593 | 0.000000000 |
| 120000 | native | A | write_off | 0.75 | 1.733398438 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.730484480 | 0.000000000 |
| 120005 | native | A | write_off | 0.75 | -0.659179688 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.737739907 | 0.000244141 |
| 120010 | native | A | write_off | 0.75 | 2.685546875 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.735647122 | 0.000244141 |
| 120015 | native | A | write_off | 0.75 | 0.659179688 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.732497713 | 0.000244141 |
| pooled | native | A | write_off | 1.0 | 2.312215169 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | native | A | write_off | 1.0 | 0.537109375 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | native | A | write_off | 1.0 | -1.595052083 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | native | A | write_off | 1.0 | 9.521484375 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | native | A | write_off | 1.0 | 2.050781250 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | native | A | write_off | 1.0 | 3.735351562 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | native | A | write_off | 1.0 | 0.610351562 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | native | A | write_off | 1.0 | 3.051757812 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | native | A | write_off | 1.0 | 0.585937500 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | native | A | write_off | 1.25 | 2.347819010 | 0.932061265 | 0.916899718 | 0.000000000 | 0.000000000 | 0.000000 | 0.741511313 | 0.000020345 |
| 90000 | native | A | write_off | 1.25 | -0.260416667 | 0.915634225 | 0.906156900 | 0.000000000 | 0.000000000 | 0.000000 | 0.744655809 | 0.000162760 |
| 90005 | native | A | write_off | 1.25 | -1.188151042 | 0.921236109 | 0.903719580 | 0.000000000 | 0.000000000 | 0.000000 | 0.740568711 | 0.000000000 |
| 90010 | native | A | write_off | 1.25 | 8.626302083 | 0.950583251 | 0.932174534 | 0.000000000 | 0.000000000 | 0.000000 | 0.745233796 | 0.000000000 |
| 90015 | native | A | write_off | 1.25 | 1.253255208 | 0.953050250 | 0.941181517 | 0.000000000 | 0.000000000 | 0.000000 | 0.737788286 | 0.000000000 |
| 120000 | native | A | write_off | 1.25 | 6.689453125 | 0.948982398 | 0.939348254 | 0.000000000 | 0.000000000 | 0.000000 | 0.735963882 | 0.000000000 |
| 120005 | native | A | write_off | 1.25 | 1.831054688 | 0.932801971 | 0.912726754 | 0.000000000 | 0.000000000 | 0.000000 | 0.748540786 | 0.000000000 |
| 120010 | native | A | write_off | 1.25 | 3.466796875 | 0.912717494 | 0.893541307 | 0.000000000 | 0.000000000 | 0.000000 | 0.740265646 | 0.000000000 |
| 120015 | native | A | write_off | 1.25 | -1.635742188 | 0.921484421 | 0.906348900 | 0.000000000 | 0.000000000 | 0.000000 | 0.739073587 | 0.000000000 |
| pooled | native | B | ordinary | 0.75 | 21.962483724 | 0.828325394 | 0.746388980 | 0.617125520 | 0.471279796 | 89.583333 | 0.942563848 | 0.000498454 |
| 90000 | native | B | ordinary | 0.75 | 25.748697917 | 0.803029948 | 0.769306605 | 0.627930172 | 0.507449778 | 95.833333 | 0.941232295 | 0.000651042 |
| 90005 | native | B | ordinary | 0.75 | 25.504557292 | 0.875762523 | 0.844002803 | 0.691266690 | 0.570685808 | 100.000000 | 0.944970694 | 0.000651042 |
| 90010 | native | B | ordinary | 0.75 | 7.975260417 | 0.695684702 | 0.515800898 | 0.402880649 | 0.162560795 | 66.666667 | 0.957145975 | 0.000813802 |
| 90015 | native | B | ordinary | 0.75 | 18.277994792 | 0.803957480 | 0.655574258 | 0.583237956 | 0.387093782 | 79.166667 | 0.950861362 | 0.000651042 |
| 120000 | native | B | ordinary | 0.75 | 30.371093750 | 0.907038700 | 0.872970997 | 0.769920668 | 0.668633425 | 100.000000 | 0.923841334 | 0.000000000 |
| 120005 | native | B | ordinary | 0.75 | 17.651367188 | 0.785661814 | 0.647875433 | 0.545302161 | 0.390313684 | 75.000000 | 0.946287531 | 0.000732422 |
| 120010 | native | B | ordinary | 0.75 | 25.927734375 | 0.889802804 | 0.850077254 | 0.662040978 | 0.549836362 | 100.000000 | 0.940290868 | 0.000488281 |
| 120015 | native | B | ordinary | 0.75 | 24.243164062 | 0.865665183 | 0.815503594 | 0.654424883 | 0.533664736 | 100.000000 | 0.935880727 | 0.000000000 |
| pooled | native | B | ordinary | 1.0 | 18.173217773 | 0.828325394 | 0.746388980 | 0.562119955 | 0.398634796 | 87.239583 | 0.932632163 | 0.000417074 |
| 90000 | native | B | ordinary | 1.0 | 17.952473958 | 0.803029948 | 0.769306605 | 0.540940544 | 0.395011091 | 87.500000 | 0.933788074 | 0.000488281 |
| 90005 | native | B | ordinary | 1.0 | 21.077473958 | 0.875762523 | 0.844002803 | 0.624408055 | 0.477030675 | 95.833333 | 0.935697500 | 0.000325521 |
| 90010 | native | B | ordinary | 1.0 | 6.770833333 | 0.695684702 | 0.515800898 | 0.360938848 | 0.131401929 | 66.666667 | 0.948812723 | 0.000651042 |
| 90015 | native | B | ordinary | 1.0 | 15.087890625 | 0.803957480 | 0.655574258 | 0.525920793 | 0.320800696 | 79.166667 | 0.939433792 | 0.000651042 |
| 120000 | native | B | ordinary | 1.0 | 24.951171875 | 0.907038700 | 0.872970997 | 0.704363759 | 0.559190932 | 100.000000 | 0.915285806 | 0.000244141 |
| 120005 | native | B | ordinary | 1.0 | 17.382812500 | 0.785661814 | 0.647875433 | 0.526971350 | 0.377009098 | 75.000000 | 0.932264357 | 0.000732422 |
| 120010 | native | B | ordinary | 1.0 | 20.996093750 | 0.889802804 | 0.850077254 | 0.611012989 | 0.468681852 | 93.750000 | 0.930196882 | 0.000244141 |
| 120015 | native | B | ordinary | 1.0 | 21.166992188 | 0.865665183 | 0.815503594 | 0.602403298 | 0.459952096 | 100.000000 | 0.925578167 | 0.000000000 |
| pooled | native | B | ordinary | 1.25 | 15.345255534 | 0.828325394 | 0.746388980 | 0.512874290 | 0.344924740 | 79.427083 | 0.922842304 | 0.000447591 |
| 90000 | native | B | ordinary | 1.25 | 12.402343750 | 0.803029948 | 0.769306605 | 0.485027368 | 0.313512196 | 79.166667 | 0.924471756 | 0.000325521 |
| 90005 | native | B | ordinary | 1.25 | 18.929036458 | 0.875762523 | 0.844002803 | 0.574927538 | 0.425962516 | 87.500000 | 0.927300982 | 0.000325521 |
| 90010 | native | B | ordinary | 1.25 | 6.949869792 | 0.695684702 | 0.515800898 | 0.325145603 | 0.117975211 | 66.666667 | 0.939546729 | 0.000651042 |
| 90015 | native | B | ordinary | 1.25 | 13.118489583 | 0.803957480 | 0.655574258 | 0.480215544 | 0.271892032 | 70.833333 | 0.930493188 | 0.000813802 |
| 120000 | native | B | ordinary | 1.25 | 19.091796875 | 0.907038700 | 0.872970997 | 0.636822936 | 0.458611642 | 87.500000 | 0.909324183 | 0.000244141 |
| 120005 | native | B | ordinary | 1.25 | 17.431640625 | 0.785661814 | 0.647875433 | 0.508630214 | 0.376498518 | 75.000000 | 0.917287395 | 0.000732422 |
| 120010 | native | B | ordinary | 1.25 | 17.065429688 | 0.889802804 | 0.850077254 | 0.540964428 | 0.393500380 | 81.250000 | 0.918027849 | 0.000488281 |
| 120015 | native | B | ordinary | 1.25 | 17.773437500 | 0.865665183 | 0.815503594 | 0.551260687 | 0.401445429 | 87.500000 | 0.916286347 | 0.000000000 |
| pooled | native | B | aligned | 0.75 | 29.875691732 | 0.828325394 | 0.746388980 | 0.747934483 | 0.637154982 | 98.437500 | 0.941689791 | 0.000447591 |
| 90000 | native | B | aligned | 0.75 | 29.947916667 | 0.803029948 | 0.769306605 | 0.722284373 | 0.635241010 | 100.000000 | 0.938171551 | 0.000162760 |
| 90005 | native | B | aligned | 0.75 | 33.268229167 | 0.875762523 | 0.844002803 | 0.827348336 | 0.754200398 | 100.000000 | 0.942874953 | 0.000162760 |
| 90010 | native | B | aligned | 0.75 | 14.176432292 | 0.695684702 | 0.515800898 | 0.498943782 | 0.240694603 | 100.000000 | 0.958708101 | 0.000651042 |
| 90015 | native | B | aligned | 0.75 | 26.822916667 | 0.803957480 | 0.655574258 | 0.716868407 | 0.570605203 | 87.500000 | 0.949661449 | 0.000651042 |
| 120000 | native | B | aligned | 0.75 | 38.549804688 | 0.907038700 | 0.872970997 | 0.905160755 | 0.875744927 | 100.000000 | 0.932398259 | 0.000488281 |
| 120005 | native | B | aligned | 0.75 | 24.462890625 | 0.785661814 | 0.647875433 | 0.627865263 | 0.433388301 | 100.000000 | 0.944791772 | 0.000732422 |
| 120010 | native | B | aligned | 0.75 | 37.915039062 | 0.889802804 | 0.850077254 | 0.875378549 | 0.837207134 | 100.000000 | 0.932201930 | 0.000488281 |
| 120015 | native | B | aligned | 0.75 | 33.862304688 | 0.865665183 | 0.815503594 | 0.809626402 | 0.750158277 | 100.000000 | 0.934710316 | 0.000244141 |
| pooled | native | B | aligned | 1.0 | 28.505452474 | 0.828325394 | 0.746388980 | 0.717430405 | 0.601585912 | 97.916667 | 0.926786759 | 0.000447591 |
| 90000 | native | B | aligned | 1.0 | 26.757812500 | 0.803029948 | 0.769306605 | 0.684075574 | 0.594122687 | 100.000000 | 0.920821658 | 0.000162760 |
| 90005 | native | B | aligned | 1.0 | 31.901041667 | 0.875762523 | 0.844002803 | 0.798343594 | 0.709321271 | 100.000000 | 0.929722301 | 0.000162760 |
| 90010 | native | B | aligned | 1.0 | 14.290364583 | 0.695684702 | 0.515800898 | 0.458542875 | 0.218619835 | 95.833333 | 0.950003572 | 0.000651042 |
| 90015 | native | B | aligned | 1.0 | 25.602213542 | 0.803957480 | 0.655574258 | 0.695577496 | 0.547708726 | 87.500000 | 0.933669904 | 0.000651042 |
| 120000 | native | B | aligned | 1.0 | 38.769531250 | 0.907038700 | 0.872970997 | 0.904269926 | 0.874951978 | 100.000000 | 0.911733471 | 0.000488281 |
| 120005 | native | B | aligned | 1.0 | 24.023437500 | 0.785661814 | 0.647875433 | 0.602113956 | 0.426914459 | 100.000000 | 0.931441973 | 0.000732422 |
| 120010 | native | B | aligned | 1.0 | 36.059570312 | 0.889802804 | 0.850077254 | 0.858268501 | 0.805766987 | 100.000000 | 0.914232904 | 0.000488281 |
| 120015 | native | B | aligned | 1.0 | 30.639648438 | 0.865665183 | 0.815503594 | 0.738251317 | 0.635281358 | 100.000000 | 0.922668292 | 0.000244141 |
| pooled | native | B | aligned | 1.25 | 26.261393229 | 0.828325394 | 0.746388980 | 0.676220026 | 0.552511854 | 97.135417 | 0.913804019 | 0.000325521 |
| 90000 | native | B | aligned | 1.25 | 22.786458333 | 0.803029948 | 0.769306605 | 0.625348893 | 0.526687385 | 100.000000 | 0.909486009 | 0.000162760 |
| 90005 | native | B | aligned | 1.25 | 31.461588542 | 0.875762523 | 0.844002803 | 0.762258008 | 0.664435863 | 100.000000 | 0.916408861 | 0.000000000 |
| 90010 | native | B | aligned | 1.25 | 14.680989583 | 0.695684702 | 0.515800898 | 0.420878135 | 0.208940932 | 95.833333 | 0.940356456 | 0.000488281 |
| 90015 | native | B | aligned | 1.25 | 20.312500000 | 0.803957480 | 0.655574258 | 0.632911775 | 0.446508517 | 87.500000 | 0.919110175 | 0.000488281 |
| 120000 | native | B | aligned | 1.25 | 37.670898438 | 0.907038700 | 0.872970997 | 0.897439868 | 0.861798301 | 100.000000 | 0.893009132 | 0.000244141 |
| 120005 | native | B | aligned | 1.25 | 23.120117188 | 0.785661814 | 0.647875433 | 0.578435841 | 0.420909843 | 93.750000 | 0.919385429 | 0.000732422 |
| 120010 | native | B | aligned | 1.25 | 33.862304688 | 0.889802804 | 0.850077254 | 0.811808319 | 0.735454647 | 100.000000 | 0.900951540 | 0.000244141 |
| 120015 | native | B | aligned | 1.25 | 26.196289062 | 0.865665183 | 0.815503594 | 0.680679368 | 0.555359347 | 100.000000 | 0.911724547 | 0.000244141 |
| pooled | native | B | protected_copy | 0.75 | 31.419881185 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.928680366 | 0.000508626 |
| 90000 | native | B | protected_copy | 0.75 | 32.307942708 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.923052932 | 0.000325521 |
| 90005 | native | B | protected_copy | 0.75 | 37.646484375 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.934573100 | 0.000162760 |
| 90010 | native | B | protected_copy | 0.75 | 18.017578125 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.938107533 | 0.000813802 |
| 90015 | native | B | protected_copy | 0.75 | 27.034505208 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.939370958 | 0.000813802 |
| 120000 | native | B | protected_copy | 0.75 | 38.330078125 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.925049485 | 0.000488281 |
| 120005 | native | B | protected_copy | 0.75 | 24.804687500 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.921916298 | 0.000488281 |
| 120010 | native | B | protected_copy | 0.75 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.924076399 | 0.000732422 |
| 120015 | native | B | protected_copy | 0.75 | 35.864257812 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.923296224 | 0.000244141 |
| pooled | native | B | protected_copy | 1.0 | 31.204223633 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.910944235 | 0.000406901 |
| 90000 | native | B | protected_copy | 1.0 | 32.259114583 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.904384984 | 0.000162760 |
| 90005 | native | B | protected_copy | 1.0 | 37.500000000 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.915688770 | 0.000000000 |
| 90010 | native | B | protected_copy | 1.0 | 17.464192708 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.922889348 | 0.000813802 |
| 90015 | native | B | protected_copy | 1.0 | 26.985677083 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.923296826 | 0.000813802 |
| 120000 | native | B | protected_copy | 1.0 | 38.452148438 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.905615436 | 0.000244141 |
| 120005 | native | B | protected_copy | 1.0 | 23.901367188 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.906479626 | 0.000488281 |
| 120010 | native | B | protected_copy | 1.0 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.904941162 | 0.000488281 |
| 120015 | native | B | protected_copy | 1.0 | 35.717773438 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.904257727 | 0.000244141 |
| pooled | native | B | protected_copy | 1.25 | 30.979410807 | 0.828325394 | 0.746388980 | 0.828325394 | 0.746388980 | 100.000000 | 0.893769128 | 0.000396729 |
| 90000 | native | B | protected_copy | 1.25 | 32.177734375 | 0.803029948 | 0.769306605 | 0.803029948 | 0.769306605 | 100.000000 | 0.886880322 | 0.000162760 |
| 90005 | native | B | protected_copy | 1.25 | 37.662760417 | 0.875762523 | 0.844002803 | 0.875762523 | 0.844002803 | 100.000000 | 0.897162655 | 0.000000000 |
| 90010 | native | B | protected_copy | 1.25 | 16.292317708 | 0.695684702 | 0.515800898 | 0.695684702 | 0.515800898 | 100.000000 | 0.908573407 | 0.000651042 |
| 90015 | native | B | protected_copy | 1.25 | 26.790364583 | 0.803957480 | 0.655574258 | 0.803957480 | 0.655574258 | 100.000000 | 0.907531912 | 0.000651042 |
| 120000 | native | B | protected_copy | 1.25 | 38.696289062 | 0.907038700 | 0.872970997 | 0.907038700 | 0.872970997 | 100.000000 | 0.886748629 | 0.000244141 |
| 120005 | native | B | protected_copy | 1.25 | 23.486328125 | 0.785661814 | 0.647875433 | 0.785661814 | 0.647875433 | 100.000000 | 0.890984890 | 0.000732422 |
| 120010 | native | B | protected_copy | 1.25 | 37.353515625 | 0.889802804 | 0.850077254 | 0.889802804 | 0.850077254 | 100.000000 | 0.885980820 | 0.000488281 |
| 120015 | native | B | protected_copy | 1.25 | 35.375976562 | 0.865665183 | 0.815503594 | 0.865665183 | 0.815503594 | 100.000000 | 0.886290389 | 0.000244141 |
| pooled | native | B | ordinary_read_off | 0.75 | -15.689086914 | 0.828325394 | 0.746388980 | 0.133302346 | -0.272518392 | 19.270833 | 0.947636407 | 0.000417074 |
| 90000 | native | B | ordinary_read_off | 0.75 | -14.680989583 | 0.803029948 | 0.769306605 | 0.131405920 | -0.249319369 | 20.833333 | 0.955579803 | 0.000325521 |
| 90005 | native | B | ordinary_read_off | 0.75 | -12.158203125 | 0.875762523 | 0.844002803 | 0.138271480 | -0.184738137 | 16.666667 | 0.943133461 | 0.000162760 |
| 90010 | native | B | ordinary_read_off | 0.75 | -10.384114583 | 0.695684702 | 0.515800898 | 0.137267743 | -0.226798881 | 29.166667 | 0.944553190 | 0.000325521 |
| 90015 | native | B | ordinary_read_off | 0.75 | -14.436848958 | 0.803957480 | 0.655574258 | 0.129928449 | -0.263951394 | 25.000000 | 0.950869928 | 0.000813802 |
| 120000 | native | B | ordinary_read_off | 0.75 | -13.696289062 | 0.907038700 | 0.872970997 | 0.140398430 | -0.213010175 | 18.750000 | 0.946070704 | 0.000000000 |
| 120005 | native | B | ordinary_read_off | 0.75 | -17.089843750 | 0.785661814 | 0.647875433 | 0.150048265 | -0.270338641 | 18.750000 | 0.939471053 | 0.000244141 |
| 120010 | native | B | ordinary_read_off | 0.75 | -19.750976562 | 0.889802804 | 0.850077254 | 0.107010012 | -0.355146223 | 12.500000 | 0.952121582 | 0.001220703 |
| 120015 | native | B | ordinary_read_off | 0.75 | -23.315429688 | 0.865665183 | 0.815503594 | 0.132088470 | -0.416844320 | 12.500000 | 0.949291539 | 0.000244141 |
| pooled | native | B | ordinary_read_off | 1.0 | -19.803873698 | 0.828325394 | 0.746388980 | 0.104559079 | -0.363779281 | 11.458333 | 0.949478748 | 0.000447591 |
| 90000 | native | B | ordinary_read_off | 1.0 | -20.035807292 | 0.803029948 | 0.769306605 | 0.106136047 | -0.352414530 | 16.666667 | 0.952283763 | 0.000488281 |
| 90005 | native | B | ordinary_read_off | 1.0 | -16.569010417 | 0.875762523 | 0.844002803 | 0.120852173 | -0.271556073 | 4.166667 | 0.955123747 | 0.000488281 |
| 90010 | native | B | ordinary_read_off | 1.0 | -16.438802083 | 0.695684702 | 0.515800898 | 0.120814572 | -0.291820235 | 12.500000 | 0.941713502 | 0.000488281 |
| 90015 | native | B | ordinary_read_off | 1.0 | -16.910807292 | 0.803957480 | 0.655574258 | 0.094224179 | -0.328488041 | 20.833333 | 0.951201422 | 0.000651042 |
| 120000 | native | B | ordinary_read_off | 1.0 | -19.897460938 | 0.907038700 | 0.872970997 | 0.113435475 | -0.326679827 | 6.250000 | 0.948103082 | 0.000244141 |
| 120005 | native | B | ordinary_read_off | 1.0 | -20.605468750 | 0.785661814 | 0.647875433 | 0.109049303 | -0.394195508 | 6.250000 | 0.949459027 | 0.000000000 |
| 120010 | native | B | ordinary_read_off | 1.0 | -21.166992188 | 0.889802804 | 0.850077254 | 0.075491516 | -0.412827036 | 12.500000 | 0.948995447 | 0.000976562 |
| 120015 | native | B | ordinary_read_off | 1.0 | -26.806640625 | 0.865665183 | 0.815503594 | 0.096469367 | -0.532252999 | 12.500000 | 0.948949993 | 0.000244141 |
| pooled | native | B | ordinary_read_off | 1.25 | -21.581013997 | 0.828325394 | 0.746388980 | 0.081583093 | -0.424348655 | 11.458333 | 0.950068347 | 0.000376383 |
| 90000 | native | B | ordinary_read_off | 1.25 | -20.996093750 | 0.803029948 | 0.769306605 | 0.092592563 | -0.377172790 | 12.500000 | 0.947560382 | 0.000325521 |
| 90005 | native | B | ordinary_read_off | 1.25 | -18.587239583 | 0.875762523 | 0.844002803 | 0.089445234 | -0.350776120 | 20.833333 | 0.954933931 | 0.000325521 |
| 90010 | native | B | ordinary_read_off | 1.25 | -17.724609375 | 0.695684702 | 0.515800898 | 0.089610108 | -0.354870322 | 12.500000 | 0.944659406 | 0.000488281 |
| 90015 | native | B | ordinary_read_off | 1.25 | -19.514973958 | 0.803957480 | 0.655574258 | 0.080215828 | -0.374597218 | 8.333333 | 0.952549327 | 0.000651042 |
| 120000 | native | B | ordinary_read_off | 1.25 | -24.389648438 | 0.907038700 | 0.872970997 | 0.085721239 | -0.468662755 | 0.000000 | 0.949347778 | 0.000000000 |
| 120005 | native | B | ordinary_read_off | 1.25 | -23.046875000 | 0.785661814 | 0.647875433 | 0.069646214 | -0.474056973 | 12.500000 | 0.952852574 | 0.000000000 |
| 120010 | native | B | ordinary_read_off | 1.25 | -21.411132812 | 0.889802804 | 0.850077254 | 0.069952792 | -0.434059647 | 12.500000 | 0.947264097 | 0.000976562 |
| 120015 | native | B | ordinary_read_off | 1.25 | -26.977539062 | 0.865665183 | 0.815503594 | 0.075480765 | -0.560593411 | 12.500000 | 0.951379283 | 0.000244141 |
| pooled | native | B | aligned_read_off | 0.75 | -17.039998372 | 0.828325394 | 0.746388980 | 0.142937014 | -0.268838228 | 12.760417 | 0.949789975 | 0.000447591 |
| 90000 | native | B | aligned_read_off | 0.75 | -16.113281250 | 0.803029948 | 0.769306605 | 0.144960353 | -0.230815429 | 8.333333 | 0.950933319 | 0.000488281 |
| 90005 | native | B | aligned_read_off | 0.75 | -15.039062500 | 0.875762523 | 0.844002803 | 0.148673543 | -0.242262434 | 16.666667 | 0.951950358 | 0.000651042 |
| 90010 | native | B | aligned_read_off | 0.75 | -15.494791667 | 0.695684702 | 0.515800898 | 0.144101919 | -0.247645961 | 25.000000 | 0.955378313 | 0.000325521 |
| 90015 | native | B | aligned_read_off | 0.75 | -17.480468750 | 0.803957480 | 0.655574258 | 0.140557359 | -0.251046854 | 8.333333 | 0.944937481 | 0.000651042 |
| 120000 | native | B | aligned_read_off | 0.75 | -14.379882812 | 0.907038700 | 0.872970997 | 0.142299695 | -0.196020938 | 18.750000 | 0.952175165 | 0.000244141 |
| 120005 | native | B | aligned_read_off | 0.75 | -19.018554688 | 0.785661814 | 0.647875433 | 0.149440121 | -0.323238095 | 6.250000 | 0.947109676 | 0.000244141 |
| 120010 | native | B | aligned_read_off | 0.75 | -18.725585938 | 0.889802804 | 0.850077254 | 0.143566566 | -0.296878221 | 12.500000 | 0.948328834 | 0.000732422 |
| 120015 | native | B | aligned_read_off | 0.75 | -20.068359375 | 0.865665183 | 0.815503594 | 0.129896552 | -0.362797887 | 6.250000 | 0.947506658 | 0.000244141 |
| pooled | native | B | aligned_read_off | 1.0 | -20.608520508 | 0.828325394 | 0.746388980 | 0.109727160 | -0.359095961 | 5.729167 | 0.952649348 | 0.000457764 |
| 90000 | native | B | aligned_read_off | 1.0 | -20.296223958 | 0.803029948 | 0.769306605 | 0.113890381 | -0.355666857 | 0.000000 | 0.954170862 | 0.000325521 |
| 90005 | native | B | aligned_read_off | 1.0 | -17.692057292 | 0.875762523 | 0.844002803 | 0.128002191 | -0.294875057 | 16.666667 | 0.958442694 | 0.000162760 |
| 90010 | native | B | aligned_read_off | 1.0 | -19.205729167 | 0.695684702 | 0.515800898 | 0.106789812 | -0.339941436 | 12.500000 | 0.951924600 | 0.000488281 |
| 90015 | native | B | aligned_read_off | 1.0 | -19.173177083 | 0.803957480 | 0.655574258 | 0.097183700 | -0.313371024 | 4.166667 | 0.947657414 | 0.000488281 |
| 120000 | native | B | aligned_read_off | 1.0 | -18.603515625 | 0.907038700 | 0.872970997 | 0.125068803 | -0.280203477 | 6.250000 | 0.959180669 | 0.000244141 |
| 120005 | native | B | aligned_read_off | 1.0 | -23.071289062 | 0.785661814 | 0.647875433 | 0.112034098 | -0.456612813 | 6.250000 | 0.952529174 | 0.000488281 |
| 120010 | native | B | aligned_read_off | 1.0 | -20.776367188 | 0.889802804 | 0.850077254 | 0.101241150 | -0.342407143 | 0.000000 | 0.948133843 | 0.001220703 |
| 120015 | native | B | aligned_read_off | 1.0 | -26.049804688 | 0.865665183 | 0.815503594 | 0.093607141 | -0.489689880 | 0.000000 | 0.949155529 | 0.000244141 |
| pooled | native | B | aligned_read_off | 1.25 | -22.121175130 | 0.828325394 | 0.746388980 | 0.085760412 | -0.417419974 | 7.031250 | 0.952243590 | 0.000345866 |
| 90000 | native | B | aligned_read_off | 1.25 | -20.817057292 | 0.803029948 | 0.769306605 | 0.097924741 | -0.390509751 | 8.333333 | 0.950908842 | 0.000162760 |
| 90005 | native | B | aligned_read_off | 1.25 | -19.482421875 | 0.875762523 | 0.844002803 | 0.082892978 | -0.372585925 | 16.666667 | 0.960294599 | 0.000162760 |
| 90010 | native | B | aligned_read_off | 1.25 | -20.361328125 | 0.695684702 | 0.515800898 | 0.084571356 | -0.396746973 | 8.333333 | 0.948562425 | 0.000488281 |
| 90015 | native | B | aligned_read_off | 1.25 | -20.458984375 | 0.803957480 | 0.655574258 | 0.089229268 | -0.362478666 | 4.166667 | 0.945687015 | 0.000488281 |
| 120000 | native | B | aligned_read_off | 1.25 | -22.583007812 | 0.907038700 | 0.872970997 | 0.094961333 | -0.418167777 | 0.000000 | 0.955533274 | 0.000000000 |
| 120005 | native | B | aligned_read_off | 1.25 | -27.099609375 | 0.785661814 | 0.647875433 | 0.073590376 | -0.543592838 | 12.500000 | 0.953262221 | 0.000488281 |
| 120010 | native | B | aligned_read_off | 1.25 | -21.093750000 | 0.889802804 | 0.850077254 | 0.082978374 | -0.380141146 | 0.000000 | 0.954961013 | 0.000732422 |
| 120015 | native | B | aligned_read_off | 1.25 | -25.073242188 | 0.865665183 | 0.815503594 | 0.079934870 | -0.475136718 | 6.250000 | 0.948739328 | 0.000244141 |
| pooled | native | B | write_off | 0.75 | -1.315307617 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.733315022 | 0.000111898 |
| 90000 | native | B | write_off | 0.75 | -0.244140625 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.725577573 | 0.000162760 |
| 90005 | native | B | write_off | 0.75 | 0.895182292 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.736250110 | 0.000000000 |
| 90010 | native | B | write_off | 0.75 | -5.777994792 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.734997681 | 0.000000000 |
| 90015 | native | B | write_off | 0.75 | -0.976562500 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.733325593 | 0.000000000 |
| 120000 | native | B | write_off | 0.75 | -1.733398438 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.730484480 | 0.000000000 |
| 120005 | native | B | write_off | 0.75 | 0.659179688 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.737739907 | 0.000244141 |
| 120010 | native | B | write_off | 0.75 | -2.685546875 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.735647122 | 0.000244141 |
| 120015 | native | B | write_off | 0.75 | -0.659179688 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.732497713 | 0.000244141 |
| pooled | native | B | write_off | 1.0 | -2.312215169 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.733550526 | 0.000081380 |
| 90000 | native | B | write_off | 1.0 | -0.537109375 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.729421934 | 0.000162760 |
| 90005 | native | B | write_off | 1.0 | 1.595052083 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.736003690 | 0.000000000 |
| 90010 | native | B | write_off | 1.0 | -9.521484375 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.734818457 | 0.000000000 |
| 90015 | native | B | write_off | 1.0 | -2.050781250 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.734341226 | 0.000000000 |
| 120000 | native | B | write_off | 1.0 | -3.735351562 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.732031454 | 0.000000000 |
| 120005 | native | B | write_off | 1.0 | -0.610351562 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.736289833 | 0.000244141 |
| 120010 | native | B | write_off | 1.0 | -3.051757812 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.734178631 | 0.000244141 |
| 120015 | native | B | write_off | 1.0 | -0.585937500 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.731318981 | 0.000000000 |
| pooled | native | B | write_off | 1.25 | -2.347819010 | 0.828325394 | 0.746388980 | 0.000000000 | 0.000000000 | 0.000000 | 0.741511313 | 0.000020345 |
| 90000 | native | B | write_off | 1.25 | 0.260416667 | 0.803029948 | 0.769306605 | 0.000000000 | 0.000000000 | 0.000000 | 0.744655809 | 0.000162760 |
| 90005 | native | B | write_off | 1.25 | 1.188151042 | 0.875762523 | 0.844002803 | 0.000000000 | 0.000000000 | 0.000000 | 0.740568711 | 0.000000000 |
| 90010 | native | B | write_off | 1.25 | -8.626302083 | 0.695684702 | 0.515800898 | 0.000000000 | 0.000000000 | 0.000000 | 0.745233796 | 0.000000000 |
| 90015 | native | B | write_off | 1.25 | -1.253255208 | 0.803957480 | 0.655574258 | 0.000000000 | 0.000000000 | 0.000000 | 0.737788286 | 0.000000000 |
| 120000 | native | B | write_off | 1.25 | -6.689453125 | 0.907038700 | 0.872970997 | 0.000000000 | 0.000000000 | 0.000000 | 0.735963882 | 0.000000000 |
| 120005 | native | B | write_off | 1.25 | -1.831054688 | 0.785661814 | 0.647875433 | 0.000000000 | 0.000000000 | 0.000000 | 0.748540786 | 0.000000000 |
| 120010 | native | B | write_off | 1.25 | -3.466796875 | 0.889802804 | 0.850077254 | 0.000000000 | 0.000000000 | 0.000000 | 0.740265646 | 0.000000000 |
| 120015 | native | B | write_off | 1.25 | 1.635742188 | 0.865665183 | 0.815503594 | 0.000000000 | 0.000000000 | 0.000000 | 0.739073587 | 0.000000000 |

## Nested record decisions and values

| Founder/life/family/writer | native setting / points | common setting / points | family setting / points | writer setting / points | family_writer setting / points | record_rule setting / points |
| --- | --- | --- | --- | --- | --- | --- |
| 90000/0/0/0 | 1.0 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 1.25 / 44.661458333 |
| 90000/0/0/1 | 1.0 / 43.164062500 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 90000/0/1/0 | 1.0 / 33.007812500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 90000/0/1/1 | 1.0 / 35.351562500 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 |
| 90000/1/0/0 | 1.0 / 43.880208333 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 1.25 / 43.554687500 |
| 90000/1/0/1 | 1.0 / 41.796875000 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 1.25 / 41.861979167 |
| 90000/1/1/0 | 1.0 / 27.604166667 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 |
| 90000/1/1/1 | 1.0 / 34.049479167 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 |
| 90000/2/0/0 | 1.0 / 44.921875000 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 1.25 / 44.791666667 |
| 90000/2/0/1 | 1.0 / 43.554687500 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 1.25 / 43.294270833 |
| 90000/2/1/0 | 1.0 / 4.557291667 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 |
| 90000/2/1/1 | 1.0 / 7.812500000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 |
| 90000/3/0/0 | 1.0 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 1.25 / 43.880208333 |
| 90000/3/0/1 | 1.0 / 42.513020833 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 1.25 / 42.773437500 |
| 90000/3/1/0 | 1.0 / 6.640625000 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 |
| 90000/3/1/1 | 1.0 / 29.817708333 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 |
| 90005/0/0/0 | 1.0 / 41.861979167 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 1.25 / 42.057291667 |
| 90005/0/0/1 | 1.0 / 44.596354167 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 1.25 / 45.247395833 |
| 90005/0/1/0 | 1.0 / 18.945312500 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 |
| 90005/0/1/1 | 1.0 / 34.765625000 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 |
| 90005/1/0/0 | 1.0 / 42.122395833 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90005/1/0/1 | 1.0 / 42.578125000 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 1.25 / 42.057291667 |
| 90005/1/1/0 | 1.0 / 38.606770833 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 |
| 90005/1/1/1 | 1.0 / 42.968750000 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 |
| 90005/2/0/0 | 1.0 / 43.619791667 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 1.25 / 43.489583333 |
| 90005/2/0/1 | 1.0 / 43.229166667 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90005/2/1/0 | 1.0 / 20.572916667 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 |
| 90005/2/1/1 | 1.0 / 38.281250000 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 |
| 90005/3/0/0 | 1.0 / 43.294270833 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 1.25 / 43.489583333 |
| 90005/3/0/1 | 1.0 / 42.447916667 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 90005/3/1/0 | 1.0 / 6.184895833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 |
| 90005/3/1/1 | 1.0 / 11.588541667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 |
| 90010/0/0/0 | 1.0 / 42.447916667 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90010/0/0/1 | 1.0 / 46.419270833 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 90010/0/1/0 | 1.0 / 39.518229167 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 |
| 90010/0/1/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 |
| 90010/1/0/0 | 1.0 / 43.359375000 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 1.25 / 43.684895833 |
| 90010/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 1.25 / 42.643229167 |
| 90010/1/1/0 | 1.0 / -3.971354167 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 |
| 90010/1/1/1 | 1.0 / 4.427083333 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 |
| 90010/2/0/0 | 1.0 / 44.921875000 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90010/2/0/1 | 1.0 / 47.265625000 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 1.25 / 47.135416667 |
| 90010/2/1/0 | 1.0 / -7.161458333 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 |
| 90010/2/1/1 | 1.0 / 6.705729167 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 |
| 90010/3/0/0 | 1.0 / 42.708333333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 1.25 / 42.317708333 |
| 90010/3/0/1 | 1.0 / 45.442708333 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 1.25 / 45.117187500 |
| 90010/3/1/0 | 1.0 / -1.302083333 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 |
| 90010/3/1/1 | 1.0 / 3.710937500 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 |
| 90015/0/0/0 | 1.0 / 44.335937500 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90015/0/0/1 | 1.0 / 45.182291667 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 1.25 / 45.507812500 |
| 90015/0/1/0 | 1.0 / 30.078125000 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 |
| 90015/0/1/1 | 1.0 / 39.388020833 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 |
| 90015/1/0/0 | 1.0 / 43.619791667 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90015/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 1.25 / 42.187500000 |
| 90015/1/1/0 | 1.0 / 24.609375000 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 |
| 90015/1/1/1 | 1.0 / 32.552083333 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 |
| 90015/2/0/0 | 1.0 / 43.424479167 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 1.0 / 43.424479167 |
| 90015/2/0/1 | 1.0 / 46.093750000 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 1.25 / 45.963541667 |
| 90015/2/1/0 | 1.0 / 13.020833333 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 |
| 90015/2/1/1 | 1.0 / 28.059895833 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 |
| 90015/3/0/0 | 1.0 / 44.986979167 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 1.0 / 44.986979167 |
| 90015/3/0/1 | 1.0 / 47.135416667 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 1.25 / 46.940104167 |
| 90015/3/1/0 | 1.0 / -7.356770833 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 |
| 90015/3/1/1 | 1.0 / 2.408854167 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 |
| 120000/0/0/0 | 1.0 / 43.359375000 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/0/0/1 | 1.0 / 45.507812500 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 1.25 / 45.410156250 |
| 120000/0/1/0 | 1.0 / 33.203125000 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 |
| 120000/0/1/1 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 |
| 120000/1/0/0 | 1.0 / 43.750000000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 120000/1/0/1 | 1.0 / 45.898437500 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 1.25 / 46.093750000 |
| 120000/1/1/0 | 1.0 / 37.890625000 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 |
| 120000/1/1/1 | 1.0 / 44.628906250 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 |
| 120000/2/0/0 | 1.0 / 46.191406250 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 1.25 / 46.289062500 |
| 120000/2/0/1 | 1.0 / 43.945312500 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 1.25 / 44.140625000 |
| 120000/2/1/0 | 1.0 / 17.773437500 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 |
| 120000/2/1/1 | 1.0 / 31.738281250 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 |
| 120000/3/0/0 | 1.0 / 44.726562500 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/3/0/1 | 1.0 / 45.898437500 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 1.25 / 45.996093750 |
| 120000/3/1/0 | 1.0 / 10.937500000 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 |
| 120000/3/1/1 | 1.0 / 35.156250000 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 |
| 120005/0/0/0 | 1.0 / 45.117187500 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 1.25 / 45.214843750 |
| 120005/0/0/1 | 1.0 / 43.945312500 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 1.25 / 44.238281250 |
| 120005/0/1/0 | 1.0 / 36.621093750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 |
| 120005/0/1/1 | 1.0 / 38.476562500 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120005/1/0/0 | 1.0 / 42.187500000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/0/1 | 1.0 / 43.066406250 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/1/0 | 1.0 / 0.585937500 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 |
| 120005/1/1/1 | 1.0 / 11.035156250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 |
| 120005/2/0/0 | 1.0 / 42.382812500 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120005/2/0/1 | 1.0 / 45.996093750 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 1.25 / 46.191406250 |
| 120005/2/1/0 | 1.0 / -5.468750000 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 |
| 120005/2/1/1 | 1.0 / 4.785156250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 |
| 120005/3/0/0 | 1.0 / 43.457031250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 1.25 / 43.847656250 |
| 120005/3/0/1 | 1.0 / 42.382812500 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/3/1/0 | 1.0 / 37.792968750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 |
| 120005/3/1/1 | 1.0 / 41.796875000 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 |
| 120010/0/0/0 | 1.0 / 40.722656250 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 1.25 / 40.820312500 |
| 120010/0/0/1 | 1.0 / 41.210937500 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 1.25 / 41.113281250 |
| 120010/0/1/0 | 1.0 / 25.390625000 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 |
| 120010/0/1/1 | 1.0 / 35.253906250 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 120010/1/0/0 | 1.0 / 44.433593750 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/0/1 | 1.0 / 44.335937500 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/1/0 | 1.0 / 32.812500000 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 |
| 120010/1/1/1 | 1.0 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 |
| 120010/2/0/0 | 1.0 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 1.25 / 45.703125000 |
| 120010/2/0/1 | 1.0 / 46.582031250 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 120010/2/1/0 | 1.0 / 25.488281250 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 |
| 120010/2/1/1 | 1.0 / 39.941406250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120010/3/0/0 | 1.0 / 44.238281250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/3/0/1 | 1.0 / 41.992187500 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 1.25 / 42.480468750 |
| 120010/3/1/0 | 1.0 / 0.292968750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 |
| 120010/3/1/1 | 1.0 / 26.562500000 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 |
| 120015/0/0/0 | 1.0 / 43.359375000 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 120015/0/0/1 | 1.0 / 41.503906250 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120015/0/1/0 | 1.0 / 21.875000000 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 |
| 120015/0/1/1 | 1.0 / 30.664062500 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 |
| 120015/1/0/0 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 1.25 / 44.531250000 |
| 120015/1/0/1 | 1.0 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 1.25 / 44.335937500 |
| 120015/1/1/0 | 1.0 / 22.167968750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 |
| 120015/1/1/1 | 1.0 / 38.574218750 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 |
| 120015/2/0/0 | 1.0 / 44.238281250 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 1.25 / 44.433593750 |
| 120015/2/0/1 | 1.0 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120015/2/1/0 | 1.0 / 5.078125000 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 |
| 120015/2/1/1 | 1.0 / 11.035156250 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 |
| 120015/3/0/0 | 1.0 / 45.507812500 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 1.25 / 45.312500000 |
| 120015/3/0/1 | 1.0 / 43.359375000 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 1.25 / 43.457031250 |
| 120015/3/1/0 | 1.0 / 35.546875000 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 |
| 120015/3/1/1 | 1.0 / 42.285156250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 |

## Final in-sample record decisions and values

| Founder/life/family/writer | native setting / points | common setting / points | family setting / points | writer setting / points | family_writer setting / points | record_rule setting / points |
| --- | --- | --- | --- | --- | --- | --- |
| 90000/0/0/0 | 1.0 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 1.25 / 44.661458333 |
| 90000/0/0/1 | 1.0 / 43.164062500 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 90000/0/1/0 | 1.0 / 33.007812500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 90000/0/1/1 | 1.0 / 35.351562500 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 |
| 90000/1/0/0 | 1.0 / 43.880208333 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 1.25 / 43.554687500 |
| 90000/1/0/1 | 1.0 / 41.796875000 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 1.25 / 41.861979167 |
| 90000/1/1/0 | 1.0 / 27.604166667 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 |
| 90000/1/1/1 | 1.0 / 34.049479167 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 |
| 90000/2/0/0 | 1.0 / 44.921875000 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 1.25 / 44.791666667 |
| 90000/2/0/1 | 1.0 / 43.554687500 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 1.25 / 43.294270833 |
| 90000/2/1/0 | 1.0 / 4.557291667 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 |
| 90000/2/1/1 | 1.0 / 7.812500000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 |
| 90000/3/0/0 | 1.0 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 1.25 / 43.880208333 |
| 90000/3/0/1 | 1.0 / 42.513020833 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 1.25 / 42.773437500 |
| 90000/3/1/0 | 1.0 / 6.640625000 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 |
| 90000/3/1/1 | 1.0 / 29.817708333 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 |
| 90005/0/0/0 | 1.0 / 41.861979167 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 1.25 / 42.057291667 |
| 90005/0/0/1 | 1.0 / 44.596354167 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 1.25 / 45.247395833 |
| 90005/0/1/0 | 1.0 / 18.945312500 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 |
| 90005/0/1/1 | 1.0 / 34.765625000 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 |
| 90005/1/0/0 | 1.0 / 42.122395833 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90005/1/0/1 | 1.0 / 42.578125000 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 1.25 / 42.057291667 |
| 90005/1/1/0 | 1.0 / 38.606770833 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 |
| 90005/1/1/1 | 1.0 / 42.968750000 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 |
| 90005/2/0/0 | 1.0 / 43.619791667 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 1.25 / 43.489583333 |
| 90005/2/0/1 | 1.0 / 43.229166667 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90005/2/1/0 | 1.0 / 20.572916667 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 |
| 90005/2/1/1 | 1.0 / 38.281250000 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 |
| 90005/3/0/0 | 1.0 / 43.294270833 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 1.25 / 43.489583333 |
| 90005/3/0/1 | 1.0 / 42.447916667 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 90005/3/1/0 | 1.0 / 6.184895833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 |
| 90005/3/1/1 | 1.0 / 11.588541667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 |
| 90010/0/0/0 | 1.0 / 42.447916667 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90010/0/0/1 | 1.0 / 46.419270833 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 90010/0/1/0 | 1.0 / 39.518229167 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 |
| 90010/0/1/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 |
| 90010/1/0/0 | 1.0 / 43.359375000 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 1.25 / 43.684895833 |
| 90010/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 1.25 / 42.643229167 |
| 90010/1/1/0 | 1.0 / -3.971354167 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 |
| 90010/1/1/1 | 1.0 / 4.427083333 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 |
| 90010/2/0/0 | 1.0 / 44.921875000 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90010/2/0/1 | 1.0 / 47.265625000 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 1.25 / 47.135416667 |
| 90010/2/1/0 | 1.0 / -7.161458333 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 |
| 90010/2/1/1 | 1.0 / 6.705729167 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 |
| 90010/3/0/0 | 1.0 / 42.708333333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 1.25 / 42.317708333 |
| 90010/3/0/1 | 1.0 / 45.442708333 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 1.25 / 45.117187500 |
| 90010/3/1/0 | 1.0 / -1.302083333 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 |
| 90010/3/1/1 | 1.0 / 3.710937500 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 |
| 90015/0/0/0 | 1.0 / 44.335937500 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90015/0/0/1 | 1.0 / 45.182291667 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 1.25 / 45.507812500 |
| 90015/0/1/0 | 1.0 / 30.078125000 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 |
| 90015/0/1/1 | 1.0 / 39.388020833 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 |
| 90015/1/0/0 | 1.0 / 43.619791667 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90015/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 1.25 / 42.187500000 |
| 90015/1/1/0 | 1.0 / 24.609375000 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 |
| 90015/1/1/1 | 1.0 / 32.552083333 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 |
| 90015/2/0/0 | 1.0 / 43.424479167 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 1.25 / 43.945312500 |
| 90015/2/0/1 | 1.0 / 46.093750000 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 1.25 / 45.963541667 |
| 90015/2/1/0 | 1.0 / 13.020833333 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 |
| 90015/2/1/1 | 1.0 / 28.059895833 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 |
| 90015/3/0/0 | 1.0 / 44.986979167 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 1.25 / 45.052083333 |
| 90015/3/0/1 | 1.0 / 47.135416667 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 1.25 / 46.940104167 |
| 90015/3/1/0 | 1.0 / -7.356770833 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 |
| 90015/3/1/1 | 1.0 / 2.408854167 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 |
| 120000/0/0/0 | 1.0 / 43.359375000 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/0/0/1 | 1.0 / 45.507812500 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 1.25 / 45.410156250 |
| 120000/0/1/0 | 1.0 / 33.203125000 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 |
| 120000/0/1/1 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 |
| 120000/1/0/0 | 1.0 / 43.750000000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 120000/1/0/1 | 1.0 / 45.898437500 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 1.25 / 46.093750000 |
| 120000/1/1/0 | 1.0 / 37.890625000 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 |
| 120000/1/1/1 | 1.0 / 44.628906250 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 |
| 120000/2/0/0 | 1.0 / 46.191406250 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 1.25 / 46.289062500 |
| 120000/2/0/1 | 1.0 / 43.945312500 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 1.25 / 44.140625000 |
| 120000/2/1/0 | 1.0 / 17.773437500 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 |
| 120000/2/1/1 | 1.0 / 31.738281250 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 |
| 120000/3/0/0 | 1.0 / 44.726562500 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/3/0/1 | 1.0 / 45.898437500 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 1.25 / 45.996093750 |
| 120000/3/1/0 | 1.0 / 10.937500000 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 |
| 120000/3/1/1 | 1.0 / 35.156250000 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 |
| 120005/0/0/0 | 1.0 / 45.117187500 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 1.25 / 45.214843750 |
| 120005/0/0/1 | 1.0 / 43.945312500 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 1.25 / 44.238281250 |
| 120005/0/1/0 | 1.0 / 36.621093750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 |
| 120005/0/1/1 | 1.0 / 38.476562500 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120005/1/0/0 | 1.0 / 42.187500000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/0/1 | 1.0 / 43.066406250 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/1/0 | 1.0 / 0.585937500 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 |
| 120005/1/1/1 | 1.0 / 11.035156250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 |
| 120005/2/0/0 | 1.0 / 42.382812500 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120005/2/0/1 | 1.0 / 45.996093750 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 1.25 / 46.191406250 |
| 120005/2/1/0 | 1.0 / -5.468750000 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 |
| 120005/2/1/1 | 1.0 / 4.785156250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 |
| 120005/3/0/0 | 1.0 / 43.457031250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 1.25 / 43.847656250 |
| 120005/3/0/1 | 1.0 / 42.382812500 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/3/1/0 | 1.0 / 37.792968750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 |
| 120005/3/1/1 | 1.0 / 41.796875000 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 |
| 120010/0/0/0 | 1.0 / 40.722656250 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 1.25 / 40.820312500 |
| 120010/0/0/1 | 1.0 / 41.210937500 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 1.25 / 41.113281250 |
| 120010/0/1/0 | 1.0 / 25.390625000 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 |
| 120010/0/1/1 | 1.0 / 35.253906250 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 120010/1/0/0 | 1.0 / 44.433593750 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/0/1 | 1.0 / 44.335937500 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/1/0 | 1.0 / 32.812500000 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 |
| 120010/1/1/1 | 1.0 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 |
| 120010/2/0/0 | 1.0 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 1.25 / 45.703125000 |
| 120010/2/0/1 | 1.0 / 46.582031250 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 120010/2/1/0 | 1.0 / 25.488281250 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 |
| 120010/2/1/1 | 1.0 / 39.941406250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120010/3/0/0 | 1.0 / 44.238281250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/3/0/1 | 1.0 / 41.992187500 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 1.25 / 42.480468750 |
| 120010/3/1/0 | 1.0 / 0.292968750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 |
| 120010/3/1/1 | 1.0 / 26.562500000 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 |
| 120015/0/0/0 | 1.0 / 43.359375000 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 120015/0/0/1 | 1.0 / 41.503906250 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120015/0/1/0 | 1.0 / 21.875000000 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 |
| 120015/0/1/1 | 1.0 / 30.664062500 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 |
| 120015/1/0/0 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 1.25 / 44.531250000 |
| 120015/1/0/1 | 1.0 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 1.25 / 44.335937500 |
| 120015/1/1/0 | 1.0 / 22.167968750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 |
| 120015/1/1/1 | 1.0 / 38.574218750 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 |
| 120015/2/0/0 | 1.0 / 44.238281250 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 1.25 / 44.433593750 |
| 120015/2/0/1 | 1.0 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120015/2/1/0 | 1.0 / 5.078125000 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 |
| 120015/2/1/1 | 1.0 / 11.035156250 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 |
| 120015/3/0/0 | 1.0 / 45.507812500 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 1.25 / 45.312500000 |
| 120015/3/0/1 | 1.0 / 43.359375000 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 1.25 / 43.457031250 |
| 120015/3/1/0 | 1.0 / 35.546875000 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 |
| 120015/3/1/1 | 1.0 / 42.285156250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 |

## new_to_old record decisions and values

| Founder/life/family/writer | native setting / points | common setting / points | family setting / points | writer setting / points | family_writer setting / points | record_rule setting / points |
| --- | --- | --- | --- | --- | --- | --- |
| 90000/0/0/0 | 1.0 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 0.75 / 44.661458333 | 1.25 / 44.661458333 | 1.0 / 44.661458333 |
| 90000/0/0/1 | 1.0 / 43.164062500 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 0.75 / 43.489583333 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 90000/0/1/0 | 1.0 / 33.007812500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 90000/0/1/1 | 1.0 / 35.351562500 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 | 0.75 / 36.848958333 |
| 90000/1/0/0 | 1.0 / 43.880208333 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 0.75 / 43.815104167 | 1.25 / 43.554687500 | 1.25 / 43.554687500 |
| 90000/1/0/1 | 1.0 / 41.796875000 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 0.75 / 41.536458333 | 1.25 / 41.861979167 | 1.25 / 41.861979167 |
| 90000/1/1/0 | 1.0 / 27.604166667 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 | 0.75 / 32.942708333 |
| 90000/1/1/1 | 1.0 / 34.049479167 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 | 0.75 / 35.937500000 |
| 90000/2/0/0 | 1.0 / 44.921875000 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 0.75 / 45.442708333 | 1.25 / 44.791666667 | 1.0 / 44.921875000 |
| 90000/2/0/1 | 1.0 / 43.554687500 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 0.75 / 43.554687500 | 1.25 / 43.294270833 | 1.25 / 43.294270833 |
| 90000/2/1/0 | 1.0 / 4.557291667 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 | 0.75 / 16.341145833 |
| 90000/2/1/1 | 1.0 / 7.812500000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 | 0.75 / 15.234375000 |
| 90000/3/0/0 | 1.0 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 0.75 / 43.880208333 | 1.25 / 43.880208333 | 1.25 / 43.880208333 |
| 90000/3/0/1 | 1.0 / 42.513020833 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 0.75 / 42.773437500 | 1.25 / 42.773437500 | 1.25 / 42.773437500 |
| 90000/3/1/0 | 1.0 / 6.640625000 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 | 0.75 / 17.317708333 |
| 90000/3/1/1 | 1.0 / 29.817708333 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 | 0.75 / 32.096354167 |
| 90005/0/0/0 | 1.0 / 41.861979167 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 0.75 / 41.210937500 | 1.25 / 42.057291667 | 1.0 / 41.861979167 |
| 90005/0/0/1 | 1.0 / 44.596354167 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 0.75 / 44.075520833 | 1.25 / 45.247395833 | 1.25 / 45.247395833 |
| 90005/0/1/0 | 1.0 / 18.945312500 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 | 0.75 / 25.781250000 |
| 90005/0/1/1 | 1.0 / 34.765625000 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 | 0.75 / 36.263020833 |
| 90005/1/0/0 | 1.0 / 42.122395833 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 0.75 / 42.187500000 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90005/1/0/1 | 1.0 / 42.578125000 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 0.75 / 42.252604167 | 1.25 / 42.057291667 | 1.25 / 42.057291667 |
| 90005/1/1/0 | 1.0 / 38.606770833 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 | 0.75 / 39.192708333 |
| 90005/1/1/1 | 1.0 / 42.968750000 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 | 0.75 / 42.903645833 |
| 90005/2/0/0 | 1.0 / 43.619791667 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 0.75 / 43.294270833 | 1.25 / 43.489583333 | 1.25 / 43.489583333 |
| 90005/2/0/1 | 1.0 / 43.229166667 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 0.75 / 42.968750000 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90005/2/1/0 | 1.0 / 20.572916667 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 | 0.75 / 26.302083333 |
| 90005/2/1/1 | 1.0 / 38.281250000 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 | 0.75 / 38.736979167 |
| 90005/3/0/0 | 1.0 / 43.294270833 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 0.75 / 43.359375000 | 1.25 / 43.489583333 | 1.0 / 43.294270833 |
| 90005/3/0/1 | 1.0 / 42.447916667 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 0.75 / 42.057291667 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 90005/3/1/0 | 1.0 / 6.184895833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 | 0.75 / 8.919270833 |
| 90005/3/1/1 | 1.0 / 11.588541667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 | 0.75 / 13.932291667 |
| 90010/0/0/0 | 1.0 / 42.447916667 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 0.75 / 41.731770833 | 1.25 / 43.098958333 | 1.25 / 43.098958333 |
| 90010/0/0/1 | 1.0 / 46.419270833 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 0.75 / 45.963541667 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 90010/0/1/0 | 1.0 / 39.518229167 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 | 0.75 / 41.341145833 |
| 90010/0/1/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 | 0.75 / 42.057291667 |
| 90010/1/0/0 | 1.0 / 43.359375000 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 0.75 / 42.903645833 | 1.25 / 43.684895833 | 1.0 / 43.359375000 |
| 90010/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 0.75 / 42.057291667 | 1.25 / 42.643229167 | 1.25 / 42.643229167 |
| 90010/1/1/0 | 1.0 / -3.971354167 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 | 0.75 / -3.710937500 |
| 90010/1/1/1 | 1.0 / 4.427083333 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 | 0.75 / 9.700520833 |
| 90010/2/0/0 | 1.0 / 44.921875000 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 0.75 / 44.270833333 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90010/2/0/1 | 1.0 / 47.265625000 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 0.75 / 47.330729167 | 1.25 / 47.135416667 | 1.0 / 47.265625000 |
| 90010/2/1/0 | 1.0 / -7.161458333 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 | 0.75 / -5.468750000 |
| 90010/2/1/1 | 1.0 / 6.705729167 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 | 0.75 / 2.539062500 |
| 90010/3/0/0 | 1.0 / 42.708333333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 0.75 / 42.708333333 | 1.25 / 42.317708333 | 1.0 / 42.708333333 |
| 90010/3/0/1 | 1.0 / 45.442708333 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 0.75 / 45.572916667 | 1.25 / 45.117187500 | 1.0 / 45.442708333 |
| 90010/3/1/0 | 1.0 / -1.302083333 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 | 0.75 / -0.716145833 |
| 90010/3/1/1 | 1.0 / 3.710937500 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 | 0.75 / 2.083333333 |
| 90015/0/0/0 | 1.0 / 44.335937500 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 0.75 / 43.945312500 | 1.25 / 44.986979167 | 1.25 / 44.986979167 |
| 90015/0/0/1 | 1.0 / 45.182291667 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 0.75 / 44.531250000 | 1.25 / 45.507812500 | 1.25 / 45.507812500 |
| 90015/0/1/0 | 1.0 / 30.078125000 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 | 0.75 / 33.138020833 |
| 90015/0/1/1 | 1.0 / 39.388020833 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 | 0.75 / 39.062500000 |
| 90015/1/0/0 | 1.0 / 43.619791667 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 0.75 / 42.773437500 | 1.25 / 43.750000000 | 1.25 / 43.750000000 |
| 90015/1/0/1 | 1.0 / 42.317708333 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 0.75 / 42.057291667 | 1.25 / 42.187500000 | 1.25 / 42.187500000 |
| 90015/1/1/0 | 1.0 / 24.609375000 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 | 0.75 / 27.408854167 |
| 90015/1/1/1 | 1.0 / 32.552083333 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 | 0.75 / 33.658854167 |
| 90015/2/0/0 | 1.0 / 43.424479167 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 0.75 / 42.968750000 | 1.25 / 43.945312500 | 1.0 / 43.424479167 |
| 90015/2/0/1 | 1.0 / 46.093750000 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 0.75 / 46.289062500 | 1.25 / 45.963541667 | 1.0 / 46.093750000 |
| 90015/2/1/0 | 1.0 / 13.020833333 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 | 0.75 / 18.164062500 |
| 90015/2/1/1 | 1.0 / 28.059895833 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 | 0.75 / 32.486979167 |
| 90015/3/0/0 | 1.0 / 44.986979167 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 0.75 / 44.466145833 | 1.25 / 45.052083333 | 1.0 / 44.986979167 |
| 90015/3/0/1 | 1.0 / 47.135416667 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 0.75 / 47.200520833 | 1.25 / 46.940104167 | 1.0 / 47.135416667 |
| 90015/3/1/0 | 1.0 / -7.356770833 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 | 0.75 / -6.250000000 |
| 90015/3/1/1 | 1.0 / 2.408854167 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 | 0.75 / 2.734375000 |

## old_to_new record decisions and values

| Founder/life/family/writer | native setting / points | common setting / points | family setting / points | writer setting / points | family_writer setting / points | record_rule setting / points |
| --- | --- | --- | --- | --- | --- | --- |
| 120000/0/0/0 | 1.0 / 43.359375000 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 0.75 / 42.382812500 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/0/0/1 | 1.0 / 45.507812500 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 0.75 / 45.605468750 | 1.25 / 45.410156250 | 1.25 / 45.410156250 |
| 120000/0/1/0 | 1.0 / 33.203125000 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 | 0.75 / 35.449218750 |
| 120000/0/1/1 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 | 0.75 / 43.164062500 |
| 120000/1/0/0 | 1.0 / 43.750000000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 0.75 / 44.042968750 | 1.25 / 43.359375000 | 1.25 / 43.359375000 |
| 120000/1/0/1 | 1.0 / 45.898437500 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 0.75 / 45.019531250 | 1.25 / 46.093750000 | 1.25 / 46.093750000 |
| 120000/1/1/0 | 1.0 / 37.890625000 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 | 0.75 / 41.113281250 |
| 120000/1/1/1 | 1.0 / 44.628906250 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 | 0.75 / 44.824218750 |
| 120000/2/0/0 | 1.0 / 46.191406250 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 0.75 / 45.996093750 | 1.25 / 46.289062500 | 1.25 / 46.289062500 |
| 120000/2/0/1 | 1.0 / 43.945312500 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.140625000 | 1.25 / 44.140625000 |
| 120000/2/1/0 | 1.0 / 17.773437500 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 | 0.75 / 24.902343750 |
| 120000/2/1/1 | 1.0 / 31.738281250 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 | 0.75 / 32.421875000 |
| 120000/3/0/0 | 1.0 / 44.726562500 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 0.75 / 45.214843750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120000/3/0/1 | 1.0 / 45.898437500 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 0.75 / 45.898437500 | 1.25 / 45.996093750 | 1.25 / 45.996093750 |
| 120000/3/1/0 | 1.0 / 10.937500000 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 | 0.75 / 18.652343750 |
| 120000/3/1/1 | 1.0 / 35.156250000 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 | 0.75 / 36.132812500 |
| 120005/0/0/0 | 1.0 / 45.117187500 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 0.75 / 45.019531250 | 1.25 / 45.214843750 | 1.25 / 45.214843750 |
| 120005/0/0/1 | 1.0 / 43.945312500 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 0.75 / 43.652343750 | 1.25 / 44.238281250 | 1.25 / 44.238281250 |
| 120005/0/1/0 | 1.0 / 36.621093750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 | 0.75 / 37.011718750 |
| 120005/0/1/1 | 1.0 / 38.476562500 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120005/1/0/0 | 1.0 / 42.187500000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 0.75 / 41.601562500 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/0/1 | 1.0 / 43.066406250 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 0.75 / 43.066406250 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/1/1/0 | 1.0 / 0.585937500 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 | 0.75 / -0.390625000 |
| 120005/1/1/1 | 1.0 / 11.035156250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 | 0.75 / 10.253906250 |
| 120005/2/0/0 | 1.0 / 42.382812500 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 0.75 / 42.089843750 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120005/2/0/1 | 1.0 / 45.996093750 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 0.75 / 45.605468750 | 1.25 / 46.191406250 | 1.25 / 46.191406250 |
| 120005/2/1/0 | 1.0 / -5.468750000 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 | 0.75 / -4.785156250 |
| 120005/2/1/1 | 1.0 / 4.785156250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 | 0.75 / 6.738281250 |
| 120005/3/0/0 | 1.0 / 43.457031250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 0.75 / 42.871093750 | 1.25 / 43.847656250 | 1.25 / 43.847656250 |
| 120005/3/0/1 | 1.0 / 42.382812500 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 0.75 / 42.480468750 | 1.25 / 42.578125000 | 1.25 / 42.578125000 |
| 120005/3/1/0 | 1.0 / 37.792968750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 | 0.75 / 38.183593750 |
| 120005/3/1/1 | 1.0 / 41.796875000 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 | 0.75 / 40.527343750 |
| 120010/0/0/0 | 1.0 / 40.722656250 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 0.75 / 39.843750000 | 1.25 / 40.820312500 | 1.25 / 40.820312500 |
| 120010/0/0/1 | 1.0 / 41.210937500 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 0.75 / 41.015625000 | 1.25 / 41.113281250 | 1.25 / 41.113281250 |
| 120010/0/1/0 | 1.0 / 25.390625000 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 | 0.75 / 32.617187500 |
| 120010/0/1/1 | 1.0 / 35.253906250 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 | 0.75 / 35.351562500 |
| 120010/1/0/0 | 1.0 / 44.433593750 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 0.75 / 44.726562500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/0/1 | 1.0 / 44.335937500 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 0.75 / 44.433593750 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/1/1/0 | 1.0 / 32.812500000 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 | 0.75 / 34.472656250 |
| 120010/1/1/1 | 1.0 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 | 0.75 / 42.480468750 |
| 120010/2/0/0 | 1.0 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 0.75 / 45.312500000 | 1.25 / 45.703125000 | 1.25 / 45.703125000 |
| 120010/2/0/1 | 1.0 / 46.582031250 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 0.75 / 46.386718750 | 1.25 / 46.679687500 | 1.25 / 46.679687500 |
| 120010/2/1/0 | 1.0 / 25.488281250 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 | 0.75 / 29.492187500 |
| 120010/2/1/1 | 1.0 / 39.941406250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 | 0.75 / 40.722656250 |
| 120010/3/0/0 | 1.0 / 44.238281250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 0.75 / 42.773437500 | 1.25 / 44.628906250 | 1.25 / 44.628906250 |
| 120010/3/0/1 | 1.0 / 41.992187500 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 0.75 / 41.406250000 | 1.25 / 42.480468750 | 1.25 / 42.480468750 |
| 120010/3/1/0 | 1.0 / 0.292968750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 | 0.75 / 6.933593750 |
| 120010/3/1/1 | 1.0 / 26.562500000 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 | 0.75 / 33.789062500 |
| 120015/0/0/0 | 1.0 / 43.359375000 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 0.75 / 43.261718750 | 1.25 / 43.164062500 | 1.25 / 43.164062500 |
| 120015/0/0/1 | 1.0 / 41.503906250 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 0.75 / 41.796875000 | 1.25 / 41.699218750 | 1.25 / 41.699218750 |
| 120015/0/1/0 | 1.0 / 21.875000000 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 | 0.75 / 24.511718750 |
| 120015/0/1/1 | 1.0 / 30.664062500 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 | 0.75 / 35.644531250 |
| 120015/1/0/0 | 1.0 / 43.554687500 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 0.75 / 43.164062500 | 1.25 / 44.531250000 | 1.25 / 44.531250000 |
| 120015/1/0/1 | 1.0 / 44.140625000 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 0.75 / 43.359375000 | 1.25 / 44.335937500 | 1.25 / 44.335937500 |
| 120015/1/1/0 | 1.0 / 22.167968750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 | 0.75 / 26.074218750 |
| 120015/1/1/1 | 1.0 / 38.574218750 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 | 0.75 / 38.867187500 |
| 120015/2/0/0 | 1.0 / 44.238281250 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 0.75 / 43.554687500 | 1.25 / 44.433593750 | 1.25 / 44.433593750 |
| 120015/2/0/1 | 1.0 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 0.75 / 43.652343750 | 1.25 / 43.652343750 | 1.25 / 43.652343750 |
| 120015/2/1/0 | 1.0 / 5.078125000 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 | 0.75 / 9.570312500 |
| 120015/2/1/1 | 1.0 / 11.035156250 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 | 0.75 / 17.187500000 |
| 120015/3/0/0 | 1.0 / 45.507812500 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 0.75 / 45.214843750 | 1.25 / 45.312500000 | 1.25 / 45.312500000 |
| 120015/3/0/1 | 1.0 / 43.359375000 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 0.75 / 43.066406250 | 1.25 / 43.457031250 | 1.25 / 43.457031250 |
| 120015/3/1/0 | 1.0 / 35.546875000 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 | 0.75 / 34.863281250 |
| 120015/3/1/1 | 1.0 / 42.285156250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 | 0.75 / 42.675781250 |

## Frozen evidence

External root: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-recipient-decision-development-v1`.

| Artifact | SHA-256 |
| --- | --- |
| FREEZE.json | b70e4035116cca270ed9e1dd534b7ec57d72503b6d9c7b303480ae1bb5f87eb4 |
| run/COMPLETE.json | 7d9aee8256cfe9df47b2e221b3c6b98c89cad4a343aae7b5012b5d84b2971700 |
| run/outputs/REPORT.json | c2ee92add8083329627e51066bba8d9991d4da3682efc414add351945ad5d780 |
| run/outputs/FEATURE_AUDIT.json | 82bfd64a0eb58df0b89d24afeaf07d2d03f175f2e961f66549e604dc6dd6c5bd |
| run/outputs/FIT.json | bc8af965fa4693768d71fa9ef876fa797f92a222f33aa947a847b43e4c47fb7c |
| run/outputs/POLICY.json | 65dc094d8167cb63de7a36455d03aa63f5428148b931edabd37a35872d9329cd |
| AUDIT.json | 37c52fa29a4b2981886539b1d669e4661b49714efd50ab30e1c38c8fc30437a3 |

