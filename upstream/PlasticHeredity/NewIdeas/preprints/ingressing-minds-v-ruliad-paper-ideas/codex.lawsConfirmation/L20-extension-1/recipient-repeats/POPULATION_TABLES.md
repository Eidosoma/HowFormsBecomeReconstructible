# D181 Tables for the four future recurrence test

2026-10-10. Completed population results. [Interpretation and formal audit
closeout](POPULATION_RESULTS.md) and
[fixed protocol](PROTOCOL_V1.md). These tables are read-only views of the
frozen results, with no new trajectories, predictors or tuned comparisons.

All four reused founder blocks and all 32 F0 records remain. Each family
has 16 records, three settings and four fresh futures, or 192 labelled
paths per writer/control condition. Common-reader B ordinary is focal (*).
Native-reader and aligned-writing results do not replace it.

Preference points are 100 times own-minus-alternative preference, not success
percentages. Negative preferences favor the alternative. All means equally
weight the fixed donors, lives and futures. Signed components use original
squared-score units, not points or variance percentages; negatives remain.

Pair products share futures and are not independent replications. Neither
donor/future omission ranges nor ranking counts are confidence intervals.

All 1,152 absolute control cells, 960 paired contrasts and 4,608 per-assay
records remain in the immutable external JSON. Tables below aggregate controls
equally over donors/futures for readability, while retaining every condition.

## Absolute preference including every control

| Assay | Family | Condition | g 0.75 | g 1.0 | g 1.25 | Pooled |
| --- | --- | --- | --- | --- | --- | --- |
| common | A | ordinary | 43.3899 | 43.6035 | 43.7988 | 43.5974 |
| common | A | aligned | 43.7317 | 43.8660 | 44.0308 | 43.8761 |
| common | A | protected_copy | 42.8955 | 42.8955 | 42.8955 | 42.8955 |
| common | A | ordinary_read_off | 13.3057 | 17.1265 | 19.2932 | 16.5751 |
| common | A | aligned_read_off | 15.3320 | 18.4937 | 19.7571 | 17.8609 |
| common | A | write_off | 3.0273 | 3.0273 | 3.0273 | 3.0273 |
| common | B | ordinary | 19.0002 | 14.9170 | 12.6770 | 15.5314 |
| common | B | aligned | 26.1475 | 24.5667 | 22.3633 | 24.3591 |
| common | B | protected_copy | 28.7903 | 28.7903 | 28.7903 | 28.7903 |
| common | B | ordinary_read_off | -13.3057 | -17.1265 | -19.2932 | -16.5751 |
| common | B | aligned_read_off | -15.3320 | -18.4937 | -19.7571 | -17.8609 |
| common | B | write_off | -3.0273 | -3.0273 | -3.0273 | -3.0273 |
| native | A | ordinary | 42.9443 | 43.6035 | 44.0613 | 43.5364 |
| native | A | aligned | 43.3289 | 43.8660 | 44.2139 | 43.8029 |
| native | A | protected_copy | 42.5171 | 42.8955 | 43.1519 | 42.8548 |
| native | A | ordinary_read_off | 12.8967 | 17.1265 | 19.3787 | 16.4673 |
| native | A | aligned_read_off | 14.8132 | 18.4937 | 19.9585 | 17.7551 |
| native | A | write_off | 1.9775 | 3.0273 | 2.4902 | 2.4984 |
| native | B | ordinary | 19.2810 | 14.9170 | 12.5549 | 15.5843 |
| native | B | aligned | 26.3000 | 24.5667 | 22.1313 | 24.3327 |
| native | B | protected_copy | 29.0222 | 28.7903 | 28.3936 | 28.7354 |
| native | B | ordinary_read_off | -12.8967 | -17.1265 | -19.3787 | -16.4673 |
| native | B | aligned_read_off | -14.8132 | -18.4937 | -19.9585 | -17.7551 |
| native | B | write_off | -1.9775 | -3.0273 | -2.4902 | -2.4984 |

## All five fixed contrasts in preference points

| Assay | Family | Contrast | g 0.75 | g 1.0 | g 1.25 | Pooled |
| --- | --- | --- | --- | --- | --- | --- |
| common | A | protected_copy minus write_off | 39.8682 | 39.8682 | 39.8682 | 39.8682 |
| common | A | ordinary minus ordinary_read_off | 30.0842 | 26.4771 | 24.5056 | 27.0223 |
| common | A | ordinary minus write_off | 40.3625 | 40.5762 | 40.7715 | 40.5701 |
| common | A | aligned minus aligned_read_off | 28.3997 | 25.3723 | 24.2737 | 26.0152 |
| common | A | aligned minus write_off | 40.7043 | 40.8386 | 41.0034 | 40.8488 |
| common | B | protected_copy minus write_off | 31.8176 | 31.8176 | 31.8176 | 31.8176 |
| common | B | ordinary minus ordinary_read_off | 32.3059 | 32.0435 | 31.9702 | 32.1065 |
| common | B | ordinary minus write_off | 22.0276 | 17.9443 | 15.7043 | 18.5588 |
| common | B | aligned minus aligned_read_off | 41.4795 | 43.0603 | 42.1204 | 42.2201 |
| common | B | aligned minus write_off | 29.1748 | 27.5940 | 25.3906 | 27.3865 |
| native | A | protected_copy minus write_off | 40.5396 | 39.8682 | 40.6616 | 40.3564 |
| native | A | ordinary minus ordinary_read_off | 30.0476 | 26.4771 | 24.6826 | 27.0691 |
| native | A | ordinary minus write_off | 40.9668 | 40.5762 | 41.5710 | 41.0380 |
| native | A | aligned minus aligned_read_off | 28.5156 | 25.3723 | 24.2554 | 26.0478 |
| native | A | aligned minus write_off | 41.3513 | 40.8386 | 41.7236 | 41.3045 |
| native | B | protected_copy minus write_off | 30.9998 | 31.8176 | 30.8838 | 31.2337 |
| native | B | ordinary minus ordinary_read_off | 32.1777 | 32.0435 | 31.9336 | 32.0516 |
| native | B | ordinary minus write_off | 21.2585 | 17.9443 | 15.0452 | 18.0827 |
| native | B | aligned minus aligned_read_off | 41.1133 | 43.0603 | 42.0898 | 42.0878 |
| native | B | aligned minus write_off | 28.2776 | 27.5940 | 24.6216 | 26.8311 |

## Signed components averaged over six fresh pairs

| Group | record | recipient | interaction | total |
| --- | --- | --- | --- | --- |
| common/A/ordinary | 4.83217063e-05 | 2.5232633e-06 | 4.06415374e-06 | 5.49091233e-05 |
| common/A/aligned | 0.000335216522 | 1.39629399e-06 | 3.24845314e-06 | 0.000339861269 |
| common/B/ordinary* | 0.0205439384 | 0.000663622662 | 0.000430489028 | 0.0216380501 |
| common/B/aligned | 0.0226629321 | 0.00023704988 | 0.00045242133 | 0.0233524033 |
| native/A/ordinary | 4.74165987e-05 | 2.07115103e-05 | -2.83894715e-06 | 6.52891618e-05 |
| native/A/aligned | 0.000344311749 | 1.29220662e-05 | 3.64360986e-06 | 0.000360877426 |
| native/B/ordinary | 0.0205575393 | 0.000752127833 | 0.000390797853 | 0.021700465 |
| native/B/aligned | 0.0224690802 | 0.000287355096 | 0.000462780396 | 0.0232192156 |

## Historical and fixed fresh pair interaction estimates

| Group | Old 0,1 | Fresh 2,3 | Fresh 4,5 | Fresh six pair mean |
| --- | --- | --- | --- | --- |
| common/A/ordinary | -4.14583418e-06 | -7.54992167e-06 | 3.4570694e-06 | 4.06415374e-06 |
| common/A/aligned | -3.17891439e-07 | 4.33789359e-06 | 1.25832028e-06 | 3.24845314e-06 |
| common/B/ordinary* | -0.000292466746 | -7.37508138e-05 | 0.000675479571 | 0.000430489028 |
| common/B/aligned | 0.000404609574 | 0.00072491169 | 0.000392940309 | 0.00045242133 |
| native/A/ordinary | 1.67555279e-06 | -6.96049796e-06 | 4.72863515e-06 | -2.83894715e-06 |
| native/A/aligned | 6.95387522e-06 | 1.0477172e-05 | -2.78155009e-06 | 3.64360986e-06 |
| native/B/ordinary | -0.000244498253 | -0.000129209624 | 0.000560866462 | 0.000390797853 |
| native/B/aligned | 0.000387138791 | 0.000728680028 | 0.000419656436 | 0.000462780396 |

The old pair is shown for context only and is not pooled into fresh estimates.

## Every fresh pair signed product

| Group | Futures | record | recipient | interaction | total |
| --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 2,3 | 0.000427762667 | 5.56310018e-07 | -7.54992167e-06 | 0.000420769056 |
| common/A/ordinary | 2,4 | -3.42263116e-05 | 2.76168187e-06 | 4.12596597e-06 | -2.73386637e-05 |
| common/A/ordinary | 2,5 | -0.000100400713 | 2.40405401e-06 | 5.96708722e-06 | -9.20295715e-05 |
| common/A/ordinary | 3,4 | -5.10215759e-05 | 3.37759654e-06 | 1.02917353e-05 | -3.73522441e-05 |
| common/A/ordinary | 3,5 | -8.18835364e-05 | 2.18550364e-06 | 8.09298621e-06 | -7.16050466e-05 |
| common/A/ordinary | 4,5 | 0.000129699707 | 3.8544337e-06 | 3.4570694e-06 | 0.00013701121 |
| common/A/aligned | 2,3 | 0.000369283888 | 2.125899e-06 | 4.33789359e-06 | 0.000375747681 |
| common/A/aligned | 2,4 | 0.000304751926 | 8.34465027e-07 | 4.67565325e-06 | 0.000310262044 |
| common/A/aligned | 2,5 | 0.000397788154 | 1.07288361e-06 | 4.86108992e-06 | 0.000403722127 |
| common/A/aligned | 3,4 | 0.000358263652 | 1.82125303e-06 | 1.56958898e-06 | 0.000361654494 |
| common/A/aligned | 3,5 | 0.000356886122 | 1.76827113e-06 | 2.78817283e-06 | 0.000361442566 |
| common/A/aligned | 4,5 | 0.000224325392 | 7.54992167e-07 | 1.25832028e-06 | 0.000226338704 |
| common/B/ordinary* | 2,3 | 0.0194268227 | 0.000870810615 | -7.37508138e-05 | 0.0202238825 |
| common/B/ordinary* | 2,4 | 0.0228120751 | 0.000988271501 | 0.00138510598 | 0.0251854526 |
| common/B/ordinary* | 2,5 | 0.0214407444 | 0.000435352325 | 0.000964641571 | 0.0228407383 |
| common/B/ordinary* | 3,4 | 0.0201344093 | 0.000859869851 | -0.000175873439 | 0.0208184057 |
| common/B/ordinary* | 3,5 | 0.0226500697 | 0.000385522842 | -0.000192668703 | 0.0228429238 |
| common/B/ordinary* | 4,5 | 0.0167995095 | 0.000441908836 | 0.000675479571 | 0.0179168979 |
| common/B/aligned | 2,3 | 0.0249752402 | 0.00016687976 | 0.00072491169 | 0.0258670317 |
| common/B/aligned | 2,4 | 0.022260242 | 0.000265505579 | 0.000449962086 | 0.0229757097 |
| common/B/aligned | 2,5 | 0.0224066642 | 0.000301374329 | 0.000456902716 | 0.0231649412 |
| common/B/aligned | 3,4 | 0.022479905 | 0.000175052219 | 0.000363137987 | 0.0230180952 |
| common/B/aligned | 3,5 | 0.0223766764 | 0.000196999974 | 0.00032667319 | 0.0229003496 |
| common/B/aligned | 4,5 | 0.0214788649 | 0.000316487418 | 0.000392940309 | 0.0221882926 |
| native/A/ordinary | 2,3 | 0.000411616431 | 1.68151326e-05 | -6.96049796e-06 | 0.000421471066 |
| native/A/ordinary | 2,4 | -5.53660923e-05 | 2.05900934e-05 | -1.13712417e-05 | -4.61472405e-05 |
| native/A/ordinary | 2,5 | -8.23471281e-05 | 1.9285414e-05 | -1.37752957e-06 | -6.44392437e-05 |
| native/A/ordinary | 3,4 | -6.5697564e-05 | 2.36564212e-05 | -2.25173102e-06 | -4.42928738e-05 |
| native/A/ordinary | 3,5 | -5.44389089e-05 | 1.96165509e-05 | 1.98682149e-07 | -3.46236759e-05 |
| native/A/ordinary | 4,5 | 0.000130732854 | 2.43054496e-05 | 4.72863515e-06 | 0.000159766939 |
| native/A/aligned | 2,3 | 0.000397675567 | 9.2320972e-06 | 1.0477172e-05 | 0.000417384836 |
| native/A/aligned | 2,4 | 0.000310957432 | 1.25964483e-05 | 2.6623408e-06 | 0.000326216221 |
| native/A/aligned | 2,5 | 0.000397993459 | 1.03579627e-05 | 6.70221117e-06 | 0.000415053633 |
| native/A/aligned | 3,4 | 0.000384019481 | 1.61131223e-05 | -6.42405616e-07 | 0.000399490197 |
| native/A/aligned | 3,5 | 0.000355025132 | 1.21461021e-05 | 5.44389089e-06 | 0.000372615125 |
| native/A/aligned | 4,5 | 0.000220199426 | 1.70866648e-05 | -2.78155009e-06 | 0.000234504541 |
| native/B/ordinary | 2,3 | 0.0193875101 | 0.000944601165 | -0.000129209624 | 0.0202029016 |
| native/B/ordinary | 2,4 | 0.0227286551 | 0.00112952126 | 0.00130870607 | 0.0251668824 |
| native/B/ordinary | 2,5 | 0.021080229 | 0.000506414307 | 0.000962562031 | 0.0225492054 |
| native/B/ordinary | 3,4 | 0.0203780002 | 0.000962283876 | -0.00020315912 | 0.021137125 |
| native/B/ordinary | 3,5 | 0.0226632622 | 0.000440763103 | -0.000154978699 | 0.0229490466 |
| native/B/ordinary | 4,5 | 0.0171075794 | 0.000529183282 | 0.000560866462 | 0.0181976292 |
| native/B/aligned | 2,3 | 0.0246570375 | 0.000191509724 | 0.000728680028 | 0.0255772273 |
| native/B/aligned | 2,4 | 0.0221612785 | 0.000314308537 | 0.000466750728 | 0.0229423377 |
| native/B/aligned | 2,5 | 0.0221236547 | 0.000356680817 | 0.000434974829 | 0.0229153103 |
| native/B/aligned | 3,4 | 0.0223505232 | 0.000213762124 | 0.000399874316 | 0.0229641596 |
| native/B/aligned | 3,5 | 0.0220248964 | 0.000244398912 | 0.00032674604 | 0.0225960414 |
| native/B/aligned | 4,5 | 0.0214970907 | 0.000403470463 | 0.000419656436 | 0.0223202176 |

## Separate future means and nonnegative partitions

| Group | Future | Mean points | record | recipient | interaction | total |
| --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 2 | 43.7988 | 0.000682592392 | 3.13917796e-06 | 3.24646632e-05 | 0.000718196233 |
| common/A/ordinary | 3 | 42.9932 | 0.00055783987 | 3.01996867e-06 | 7.6452891e-05 | 0.00063731273 |
| common/A/ordinary | 4 | 43.5547 | 0.00140953064 | 5.28494517e-06 | 3.41335932e-05 | 0.00144894918 |
| common/A/ordinary | 5 | 44.0430 | 0.000255902608 | 2.90075938e-06 | 4.60545222e-05 | 0.00030485789 |
| common/A/aligned | 2 | 43.1641 | 0.000679016113 | 1.4702479e-06 | 1.63316727e-05 | 0.000696818034 |
| common/A/aligned | 3 | 43.8802 | 0.000582589044 | 3.98688846e-06 | 3.28885184e-05 | 0.00061946445 |
| common/A/aligned | 4 | 44.7103 | 0.00044353803 | 8.87446933e-07 | 9.49700673e-06 | 0.000453922484 |
| common/A/aligned | 5 | 43.7500 | 0.000526004367 | 8.34465027e-07 | 5.31143612e-06 | 0.000532150269 |
| common/B/ordinary* | 2 | 12.5326 | 0.0276091894 | 0.000980589125 | 0.00308990479 | 0.0316796833 |
| common/B/ordinary* | 3 | 13.9811 | 0.039854659 | 0.000779483053 | 0.00249161985 | 0.0431257619 |
| common/B/ordinary* | 4 | 13.7126 | 0.0316017403 | 0.00104722712 | 0.00167900986 | 0.0343279772 |
| common/B/ordinary* | 5 | 21.8994 | 0.0520496832 | 0.000193476677 | 0.000833524598 | 0.0530766845 |
| common/B/aligned | 2 | 23.8363 | 0.0259023176 | 0.000256273482 | 0.00157901976 | 0.0277376109 |
| common/B/aligned | 3 | 24.7477 | 0.0256174869 | 0.000109050009 | 0.0005837414 | 0.0263102783 |
| common/B/aligned | 4 | 24.4792 | 0.0218982697 | 0.000287307633 | 0.000643690427 | 0.0228292677 |
| common/B/aligned | 5 | 24.3734 | 0.0229689744 | 0.000355892711 | 0.00122953786 | 0.0245544049 |
| native/A/ordinary | 2 | 43.8314 | 0.000715441174 | 1.60667631e-05 | 3.77628538e-05 | 0.000769270791 |
| native/A/ordinary | 3 | 42.9362 | 0.000541792976 | 2.05172433e-05 | 6.70088662e-05 | 0.000629319085 |
| native/A/ordinary | 4 | 43.5221 | 0.00131638845 | 2.79082192e-05 | 4.09682592e-05 | 0.00138526493 |
| native/A/ordinary | 5 | 43.8558 | 0.000245670478 | 2.32590569e-05 | 4.75247701e-05 | 0.000316454305 |
| native/A/aligned | 2 | 43.2048 | 0.000695592827 | 9.58972507e-06 | 3.3431583e-05 | 0.000738614135 |
| native/A/aligned | 3 | 43.7907 | 0.000631696648 | 1.13778644e-05 | 4.24517526e-05 | 0.000685526265 |
| native/A/aligned | 4 | 44.5557 | 0.000424325466 | 2.292792e-05 | 1.71264013e-05 | 0.000464379787 |
| native/A/aligned | 5 | 43.6605 | 0.000493731764 | 1.30865309e-05 | 1.02255079e-05 | 0.000517043802 |
| native/B/ordinary | 2 | 12.5651 | 0.0271119012 | 0.00108406279 | 0.0031826761 | 0.0313786401 |
| native/B/ordinary | 3 | 13.9730 | 0.0397088197 | 0.000830266211 | 0.00255633725 | 0.0430954231 |
| native/B/ordinary | 4 | 13.9079 | 0.0314626098 | 0.00124380324 | 0.00175793966 | 0.0344643527 |
| native/B/ordinary | 5 | 21.8913 | 0.0521447659 | 0.000236603949 | 0.000942985217 | 0.053324355 |
| native/B/aligned | 2 | 23.9176 | 0.0256713695 | 0.000279042456 | 0.00153018369 | 0.0274805956 |
| native/B/aligned | 3 | 24.6094 | 0.0252111223 | 0.000131885211 | 0.000640802913 | 0.0259838104 |
| native/B/aligned | 4 | 24.4548 | 0.0220744279 | 0.000362488959 | 0.000692698691 | 0.0231296155 |
| native/B/aligned | 5 | 24.3490 | 0.0228093465 | 0.000456266933 | 0.00110669931 | 0.0243723128 |

## Four future mean rankings

| Group | Settings | Spearman | Reversed | Unchanged | Tied | All four consistent |
| --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 0.75 vs 1.0 | 0.923762455 | 8 | 104 | 8 | 0 |
| common/A/ordinary | 0.75 vs 1.25 | 0.865287107 | 14 | 98 | 8 | 0 |
| common/A/ordinary | 1.0 vs 1.25 | 0.898079764 | 12 | 102 | 6 | 0 |
| common/A/aligned | 0.75 vs 1.0 | 0.984547728 | 4 | 115 | 1 | 0 |
| common/A/aligned | 0.75 vs 1.25 | 0.956585984 | 8 | 111 | 1 | 0 |
| common/A/aligned | 1.0 vs 1.25 | 0.974963181 | 5 | 113 | 2 | 0 |
| common/B/ordinary* | 0.75 vs 1.0 | 0.964705882 | 7 | 113 | 0 | 0 |
| common/B/ordinary* | 0.75 vs 1.25 | 0.926470588 | 9 | 111 | 0 | 0 |
| common/B/ordinary* | 1.0 vs 1.25 | 0.979411765 | 4 | 116 | 0 | 0 |
| common/B/aligned | 0.75 vs 1.0 | 0.962472667 | 7 | 112 | 1 | 0 |
| common/B/aligned | 0.75 vs 1.25 | 0.936671576 | 10 | 108 | 2 | 3 |
| common/B/aligned | 1.0 vs 1.25 | 0.978661045 | 5 | 114 | 1 | 0 |
| native/A/ordinary | 0.75 vs 1.0 | 0.954243802 | 7 | 108 | 5 | 0 |
| native/A/ordinary | 0.75 vs 1.25 | 0.921828909 | 11 | 105 | 4 | 0 |
| native/A/ordinary | 1.0 vs 1.25 | 0.946125719 | 9 | 106 | 5 | 0 |
| native/A/aligned | 0.75 vs 1.0 | 0.980854197 | 4 | 114 | 2 | 0 |
| native/A/aligned | 0.75 vs 1.25 | 0.953574319 | 7 | 110 | 3 | 0 |
| native/A/aligned | 1.0 vs 1.25 | 0.973471156 | 6 | 111 | 3 | 0 |
| native/B/ordinary | 0.75 vs 1.0 | 0.971302691 | 5 | 114 | 1 | 0 |
| native/B/ordinary | 0.75 vs 1.25 | 0.933039252 | 7 | 112 | 1 | 0 |
| native/B/ordinary | 1.0 vs 1.25 | 0.979411765 | 4 | 116 | 0 | 0 |
| native/B/aligned | 0.75 vs 1.0 | 0.967647059 | 7 | 113 | 0 | 0 |
| native/B/aligned | 0.75 vs 1.25 | 0.935982593 | 10 | 109 | 1 | 3 |
| native/B/aligned | 1.0 vs 1.25 | 0.966887679 | 7 | 112 | 1 | 0 |

Each row concerns 120 overlapping record pairs, not independent trials. The
all-four rule is stricter than D180's two-future rule, so raw counts do not
measure improvement over D180. Interaction need not reverse rankings.

## Fixed two future rankings

| Group | Futures | Settings | Spearman | Reversed | Unchanged | Tied | Both consistent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 2,3 | 0.75 vs 1.0 | 0.908148148 | 9 | 103 | 8 | 0 |
| common/A/ordinary | 2,3 | 0.75 vs 1.25 | 0.804140927 | 18 | 96 | 6 | 0 |
| common/A/ordinary | 2,3 | 1.0 vs 1.25 | 0.88544194 | 13 | 101 | 6 | 0 |
| common/A/ordinary | 4,5 | 0.75 vs 1.0 | 0.96637049 | 3 | 103 | 14 | 1 |
| common/A/ordinary | 4,5 | 0.75 vs 1.25 | 0.831736356 | 16 | 99 | 5 | 3 |
| common/A/ordinary | 4,5 | 1.0 vs 1.25 | 0.843143526 | 12 | 96 | 12 | 0 |
| common/A/aligned | 2,3 | 0.75 vs 1.0 | 0.974055123 | 3 | 109 | 8 | 0 |
| common/A/aligned | 2,3 | 0.75 vs 1.25 | 0.922341315 | 11 | 103 | 6 | 1 |
| common/A/aligned | 2,3 | 1.0 vs 1.25 | 0.944569949 | 8 | 106 | 6 | 0 |
| common/A/aligned | 4,5 | 0.75 vs 1.0 | 0.9726342 | 3 | 110 | 7 | 0 |
| common/A/aligned | 4,5 | 0.75 vs 1.25 | 0.960029871 | 4 | 108 | 8 | 1 |
| common/A/aligned | 4,5 | 1.0 vs 1.25 | 0.982261909 | 3 | 111 | 6 | 0 |
| common/B/ordinary* | 2,3 | 0.75 vs 1.0 | 0.958823529 | 8 | 112 | 0 | 2 |
| common/B/ordinary* | 2,3 | 0.75 vs 1.25 | 0.908823529 | 15 | 105 | 0 | 3 |
| common/B/ordinary* | 2,3 | 1.0 vs 1.25 | 0.961764706 | 7 | 113 | 0 | 0 |
| common/B/ordinary* | 4,5 | 0.75 vs 1.0 | 0.916850874 | 9 | 110 | 1 | 0 |
| common/B/ordinary* | 4,5 | 0.75 vs 1.25 | 0.8903608 | 11 | 108 | 1 | 1 |
| common/B/ordinary* | 4,5 | 1.0 vs 1.25 | 0.988235294 | 4 | 116 | 0 | 0 |
| common/B/aligned | 2,3 | 0.75 vs 1.0 | 0.92862424 | 11 | 108 | 1 | 1 |
| common/B/aligned | 2,3 | 0.75 vs 1.25 | 0.927152569 | 13 | 106 | 1 | 3 |
| common/B/aligned | 2,3 | 1.0 vs 1.25 | 0.964705882 | 7 | 113 | 0 | 0 |
| common/B/aligned | 4,5 | 0.75 vs 1.0 | 0.949926362 | 8 | 110 | 2 | 3 |
| common/B/aligned | 4,5 | 0.75 vs 1.25 | 0.935982593 | 9 | 110 | 1 | 7 |
| common/B/aligned | 4,5 | 1.0 vs 1.25 | 0.996321094 | 1 | 118 | 1 | 0 |
| native/A/ordinary | 2,3 | 0.75 vs 1.0 | 0.862426979 | 12 | 101 | 7 | 0 |
| native/A/ordinary | 2,3 | 0.75 vs 1.25 | 0.847119645 | 15 | 100 | 5 | 0 |
| native/A/ordinary | 2,3 | 1.0 vs 1.25 | 0.90606608 | 10 | 103 | 7 | 0 |
| native/A/ordinary | 4,5 | 0.75 vs 1.0 | 0.887056562 | 9 | 97 | 14 | 1 |
| native/A/ordinary | 4,5 | 0.75 vs 1.25 | 0.75055371 | 19 | 96 | 5 | 3 |
| native/A/ordinary | 4,5 | 1.0 vs 1.25 | 0.892386299 | 9 | 98 | 13 | 1 |
| native/A/aligned | 2,3 | 0.75 vs 1.0 | 0.940135349 | 9 | 106 | 5 | 0 |
| native/A/aligned | 2,3 | 0.75 vs 1.25 | 0.908287999 | 12 | 102 | 6 | 2 |
| native/A/aligned | 2,3 | 1.0 vs 1.25 | 0.946627391 | 7 | 104 | 9 | 0 |
| native/A/aligned | 4,5 | 0.75 vs 1.0 | 0.937223043 | 8 | 107 | 5 | 0 |
| native/A/aligned | 4,5 | 0.75 vs 1.25 | 0.926090423 | 8 | 105 | 7 | 1 |
| native/A/aligned | 4,5 | 1.0 vs 1.25 | 0.994826584 | 0 | 114 | 6 | 0 |
| native/B/ordinary | 2,3 | 0.75 vs 1.0 | 0.958823529 | 8 | 112 | 0 | 2 |
| native/B/ordinary | 2,3 | 0.75 vs 1.25 | 0.908823529 | 15 | 105 | 0 | 3 |
| native/B/ordinary | 2,3 | 1.0 vs 1.25 | 0.961764706 | 7 | 113 | 0 | 0 |
| native/B/ordinary | 4,5 | 0.75 vs 1.0 | 0.93009591 | 8 | 111 | 1 | 0 |
| native/B/ordinary | 4,5 | 0.75 vs 1.25 | 0.908622207 | 10 | 107 | 3 | 1 |
| native/B/ordinary | 4,5 | 1.0 vs 1.25 | 0.991164551 | 2 | 116 | 2 | 0 |
| native/B/aligned | 2,3 | 0.75 vs 1.0 | 0.938235294 | 11 | 109 | 0 | 2 |
| native/B/aligned | 2,3 | 0.75 vs 1.25 | 0.938235294 | 12 | 108 | 0 | 3 |
| native/B/aligned | 2,3 | 1.0 vs 1.25 | 0.964705882 | 7 | 113 | 0 | 1 |
| native/B/aligned | 4,5 | 0.75 vs 1.0 | 0.946284289 | 9 | 110 | 1 | 2 |
| native/B/aligned | 4,5 | 0.75 vs 1.25 | 0.935294118 | 9 | 111 | 0 | 6 |
| native/B/aligned | 4,5 | 1.0 vs 1.25 | 0.993377752 | 2 | 117 | 1 | 0 |

## Shape and guide recognition pooled over settings

| Family | Condition | F0 own corr | F3 own corr | F0 own alt corr | F3 own alt corr | Guide correct |
| --- | --- | --- | --- | --- | --- | --- |
| A | ordinary | 0.935125959 | 0.942403467 | 0.920808133 | 0.927047803 | 192/192 |
| A | aligned | 0.935125959 | 0.948841109 | 0.920808133 | 0.938010497 | 192/192 |
| A | protected_copy | 0.935125959 | 0.935125959 | 0.920808133 | 0.920808133 | 192/192 |
| A | ordinary_read_off | 0.935125959 | 0.416608464 | 0.920808133 | 0.30626296 | 159/192 |
| A | aligned_read_off | 0.935125959 | 0.417912586 | 0.920808133 | 0.301277921 | 167/192 |
| A | write_off | 0.935125959 | 0 | 0.920808133 | 0 | 0/192 |
| B | ordinary | 0.794608663 | 0.51549403 | 0.696171141 | 0.333255394 | 153/192 |
| B | aligned | 0.794608663 | 0.655117174 | 0.696171141 | 0.510066907 | 184/192 |
| B | protected_copy | 0.794608663 | 0.794608663 | 0.696171141 | 0.696171141 | 192/192 |
| B | ordinary_read_off | 0.794608663 | 0.110345504 | 0.696171141 | -0.30626296 | 33/192 |
| B | aligned_read_off | 0.794608663 | 0.116634665 | 0.696171141 | -0.301277921 | 25/192 |
| B | write_off | 0.794608663 | 0 | 0.696171141 | 0 | 0/192 |

Shape and guide labels/addresses are aliases across the common/native assays
of each packet, so shown once. These are 192 labelled paths, not founders.
Write-off uses the fixed zero-correlation and unassigned-label convention.

## Every terminal guide label and address

| Target | Condition | Guide label | Forward shift | Paths |
| --- | --- | --- | --- | --- |
| A | ordinary | A | 0,0 | 5 |
| A | ordinary | A | 0,3 | 4 |
| A | ordinary | A | 0,4 | 1 |
| A | ordinary | A | 0,5 | 1 |
| A | ordinary | A | 0,7 | 2 |
| A | ordinary | A | 0,8 | 1 |
| A | ordinary | A | 0,13 | 3 |
| A | ordinary | A | 0,15 | 1 |
| A | ordinary | A | 1,4 | 1 |
| A | ordinary | A | 1,5 | 1 |
| A | ordinary | A | 1,6 | 2 |
| A | ordinary | A | 1,8 | 3 |
| A | ordinary | A | 1,9 | 4 |
| A | ordinary | A | 1,10 | 1 |
| A | ordinary | A | 1,13 | 3 |
| A | ordinary | A | 2,1 | 3 |
| A | ordinary | A | 2,7 | 2 |
| A | ordinary | A | 2,8 | 2 |
| A | ordinary | A | 2,10 | 2 |
| A | ordinary | A | 2,11 | 3 |
| A | ordinary | A | 3,0 | 3 |
| A | ordinary | A | 3,9 | 2 |
| A | ordinary | A | 3,12 | 1 |
| A | ordinary | A | 3,14 | 1 |
| A | ordinary | A | 3,15 | 2 |
| A | ordinary | A | 4,0 | 4 |
| A | ordinary | A | 4,1 | 1 |
| A | ordinary | A | 4,2 | 2 |
| A | ordinary | A | 4,6 | 1 |
| A | ordinary | A | 4,8 | 5 |
| A | ordinary | A | 4,9 | 2 |
| A | ordinary | A | 4,11 | 1 |
| A | ordinary | A | 4,12 | 2 |
| A | ordinary | A | 5,0 | 1 |
| A | ordinary | A | 5,2 | 4 |
| A | ordinary | A | 5,3 | 1 |
| A | ordinary | A | 5,6 | 3 |
| A | ordinary | A | 5,7 | 2 |
| A | ordinary | A | 5,15 | 5 |
| A | ordinary | A | 6,0 | 3 |
| A | ordinary | A | 6,2 | 5 |
| A | ordinary | A | 6,3 | 4 |
| A | ordinary | A | 6,6 | 1 |
| A | ordinary | A | 6,15 | 5 |
| A | ordinary | A | 7,0 | 1 |
| A | ordinary | A | 7,2 | 2 |
| A | ordinary | A | 7,3 | 2 |
| A | ordinary | A | 7,7 | 1 |
| A | ordinary | A | 8,0 | 3 |
| A | ordinary | A | 8,4 | 2 |
| A | ordinary | A | 8,7 | 5 |
| A | ordinary | A | 8,12 | 3 |
| A | ordinary | A | 9,4 | 3 |
| A | ordinary | A | 9,5 | 1 |
| A | ordinary | A | 9,11 | 3 |
| A | ordinary | A | 10,1 | 6 |
| A | ordinary | A | 10,5 | 1 |
| A | ordinary | A | 10,6 | 5 |
| A | ordinary | A | 10,7 | 3 |
| A | ordinary | A | 10,8 | 1 |
| A | ordinary | A | 10,9 | 2 |
| A | ordinary | A | 10,15 | 3 |
| A | ordinary | A | 11,10 | 1 |
| A | ordinary | A | 11,11 | 1 |
| A | ordinary | A | 11,12 | 1 |
| A | ordinary | A | 12,0 | 2 |
| A | ordinary | A | 12,4 | 5 |
| A | ordinary | A | 12,5 | 3 |
| A | ordinary | A | 13,0 | 1 |
| A | ordinary | A | 13,2 | 3 |
| A | ordinary | A | 13,4 | 1 |
| A | ordinary | A | 13,12 | 2 |
| A | ordinary | A | 13,13 | 1 |
| A | ordinary | A | 14,6 | 2 |
| A | ordinary | A | 14,8 | 1 |
| A | ordinary | A | 14,9 | 1 |
| A | ordinary | A | 14,10 | 2 |
| A | ordinary | A | 14,11 | 2 |
| A | ordinary | A | 15,0 | 3 |
| A | ordinary | A | 15,5 | 1 |
| A | ordinary | A | 15,10 | 5 |
| A | ordinary | A | 15,11 | 1 |
| A | aligned | A | 0,0 | 88 |
| A | aligned | A | 0,1 | 24 |
| A | aligned | A | 0,2 | 5 |
| A | aligned | A | 0,3 | 1 |
| A | aligned | A | 0,4 | 2 |
| A | aligned | A | 0,5 | 3 |
| A | aligned | A | 0,6 | 3 |
| A | aligned | A | 0,7 | 9 |
| A | aligned | A | 0,8 | 1 |
| A | aligned | A | 0,9 | 8 |
| A | aligned | A | 0,10 | 1 |
| A | aligned | A | 0,14 | 8 |
| A | aligned | A | 0,15 | 24 |
| A | aligned | A | 1,0 | 6 |
| A | aligned | A | 15,0 | 3 |
| A | aligned | A | 15,1 | 1 |
| A | aligned | A | 15,15 | 5 |
| A | protected_copy | A | 0,3 | 12 |
| A | protected_copy | A | 1,11 | 12 |
| A | protected_copy | A | 1,12 | 12 |
| A | protected_copy | A | 1,13 | 12 |
| A | protected_copy | A | 2,4 | 12 |
| A | protected_copy | A | 4,4 | 12 |
| A | protected_copy | A | 4,10 | 12 |
| A | protected_copy | A | 5,4 | 12 |
| A | protected_copy | A | 6,0 | 12 |
| A | protected_copy | A | 6,8 | 12 |
| A | protected_copy | A | 6,14 | 12 |
| A | protected_copy | A | 8,8 | 12 |
| A | protected_copy | A | 9,3 | 12 |
| A | protected_copy | A | 9,10 | 12 |
| A | protected_copy | A | 10,13 | 12 |
| A | protected_copy | A | 14,11 | 12 |
| A | ordinary_read_off | A | 0,4 | 1 |
| A | ordinary_read_off | A | 0,7 | 1 |
| A | ordinary_read_off | A | 0,8 | 2 |
| A | ordinary_read_off | A | 0,10 | 1 |
| A | ordinary_read_off | A | 0,11 | 2 |
| A | ordinary_read_off | A | 1,3 | 1 |
| A | ordinary_read_off | A | 1,4 | 1 |
| A | ordinary_read_off | A | 1,6 | 3 |
| A | ordinary_read_off | A | 1,8 | 2 |
| A | ordinary_read_off | A | 1,10 | 1 |
| A | ordinary_read_off | A | 1,11 | 1 |
| A | ordinary_read_off | A | 2,1 | 1 |
| A | ordinary_read_off | A | 2,2 | 2 |
| A | ordinary_read_off | A | 2,3 | 2 |
| A | ordinary_read_off | A | 2,4 | 1 |
| A | ordinary_read_off | A | 2,5 | 1 |
| A | ordinary_read_off | A | 2,7 | 1 |
| A | ordinary_read_off | A | 2,8 | 2 |
| A | ordinary_read_off | A | 2,11 | 2 |
| A | ordinary_read_off | A | 3,1 | 1 |
| A | ordinary_read_off | A | 3,2 | 1 |
| A | ordinary_read_off | A | 3,3 | 2 |
| A | ordinary_read_off | A | 3,6 | 1 |
| A | ordinary_read_off | A | 3,7 | 1 |
| A | ordinary_read_off | A | 3,8 | 2 |
| A | ordinary_read_off | A | 3,14 | 3 |
| A | ordinary_read_off | A | 4,1 | 1 |
| A | ordinary_read_off | A | 4,3 | 1 |
| A | ordinary_read_off | A | 4,4 | 1 |
| A | ordinary_read_off | A | 4,6 | 3 |
| A | ordinary_read_off | A | 4,7 | 1 |
| A | ordinary_read_off | A | 4,12 | 2 |
| A | ordinary_read_off | A | 4,13 | 1 |
| A | ordinary_read_off | A | 5,3 | 2 |
| A | ordinary_read_off | A | 5,7 | 2 |
| A | ordinary_read_off | A | 5,8 | 3 |
| A | ordinary_read_off | A | 5,9 | 2 |
| A | ordinary_read_off | A | 5,10 | 1 |
| A | ordinary_read_off | A | 5,11 | 2 |
| A | ordinary_read_off | A | 5,12 | 2 |
| A | ordinary_read_off | A | 5,14 | 3 |
| A | ordinary_read_off | A | 6,1 | 1 |
| A | ordinary_read_off | A | 6,3 | 1 |
| A | ordinary_read_off | A | 6,4 | 1 |
| A | ordinary_read_off | A | 6,6 | 1 |
| A | ordinary_read_off | A | 6,12 | 2 |
| A | ordinary_read_off | A | 6,15 | 1 |
| A | ordinary_read_off | A | 7,0 | 1 |
| A | ordinary_read_off | A | 7,2 | 1 |
| A | ordinary_read_off | A | 7,4 | 1 |
| A | ordinary_read_off | A | 7,5 | 1 |
| A | ordinary_read_off | A | 7,6 | 1 |
| A | ordinary_read_off | A | 7,8 | 1 |
| A | ordinary_read_off | A | 7,9 | 1 |
| A | ordinary_read_off | A | 7,10 | 2 |
| A | ordinary_read_off | A | 7,14 | 1 |
| A | ordinary_read_off | A | 8,0 | 1 |
| A | ordinary_read_off | A | 8,6 | 2 |
| A | ordinary_read_off | A | 8,8 | 3 |
| A | ordinary_read_off | A | 8,9 | 1 |
| A | ordinary_read_off | A | 8,12 | 2 |
| A | ordinary_read_off | A | 8,13 | 1 |
| A | ordinary_read_off | A | 8,15 | 3 |
| A | ordinary_read_off | A | 9,0 | 1 |
| A | ordinary_read_off | A | 9,2 | 1 |
| A | ordinary_read_off | A | 9,4 | 1 |
| A | ordinary_read_off | A | 9,10 | 1 |
| A | ordinary_read_off | A | 9,12 | 2 |
| A | ordinary_read_off | A | 9,14 | 1 |
| A | ordinary_read_off | A | 10,0 | 2 |
| A | ordinary_read_off | A | 10,9 | 4 |
| A | ordinary_read_off | A | 10,11 | 1 |
| A | ordinary_read_off | A | 10,12 | 3 |
| A | ordinary_read_off | A | 10,13 | 1 |
| A | ordinary_read_off | A | 10,14 | 3 |
| A | ordinary_read_off | A | 11,0 | 1 |
| A | ordinary_read_off | A | 11,7 | 1 |
| A | ordinary_read_off | A | 11,8 | 1 |
| A | ordinary_read_off | A | 11,15 | 2 |
| A | ordinary_read_off | A | 12,0 | 1 |
| A | ordinary_read_off | A | 12,2 | 1 |
| A | ordinary_read_off | A | 12,4 | 1 |
| A | ordinary_read_off | A | 12,6 | 1 |
| A | ordinary_read_off | A | 12,7 | 2 |
| A | ordinary_read_off | A | 12,8 | 2 |
| A | ordinary_read_off | A | 12,9 | 1 |
| A | ordinary_read_off | A | 12,13 | 1 |
| A | ordinary_read_off | A | 12,14 | 1 |
| A | ordinary_read_off | A | 12,15 | 1 |
| A | ordinary_read_off | A | 13,1 | 2 |
| A | ordinary_read_off | A | 13,4 | 1 |
| A | ordinary_read_off | A | 13,5 | 1 |
| A | ordinary_read_off | A | 13,6 | 1 |
| A | ordinary_read_off | A | 13,8 | 3 |
| A | ordinary_read_off | A | 13,9 | 1 |
| A | ordinary_read_off | A | 13,11 | 1 |
| A | ordinary_read_off | A | 13,13 | 1 |
| A | ordinary_read_off | A | 14,3 | 1 |
| A | ordinary_read_off | A | 14,4 | 1 |
| A | ordinary_read_off | A | 14,5 | 1 |
| A | ordinary_read_off | A | 14,8 | 1 |
| A | ordinary_read_off | A | 14,10 | 2 |
| A | ordinary_read_off | A | 15,6 | 1 |
| A | ordinary_read_off | A | 15,7 | 2 |
| A | ordinary_read_off | A | 15,8 | 4 |
| A | ordinary_read_off | A | 15,10 | 1 |
| A | ordinary_read_off | B | 1,3 | 1 |
| A | ordinary_read_off | B | 2,10 | 1 |
| A | ordinary_read_off | B | 2,14 | 3 |
| A | ordinary_read_off | B | 3,4 | 1 |
| A | ordinary_read_off | B | 3,6 | 1 |
| A | ordinary_read_off | B | 3,12 | 1 |
| A | ordinary_read_off | B | 4,1 | 2 |
| A | ordinary_read_off | B | 4,4 | 1 |
| A | ordinary_read_off | B | 4,7 | 1 |
| A | ordinary_read_off | B | 5,14 | 1 |
| A | ordinary_read_off | B | 6,8 | 1 |
| A | ordinary_read_off | B | 6,9 | 1 |
| A | ordinary_read_off | B | 7,3 | 1 |
| A | ordinary_read_off | B | 7,8 | 1 |
| A | ordinary_read_off | B | 7,9 | 2 |
| A | ordinary_read_off | B | 8,1 | 1 |
| A | ordinary_read_off | B | 8,2 | 1 |
| A | ordinary_read_off | B | 9,3 | 1 |
| A | ordinary_read_off | B | 9,10 | 1 |
| A | ordinary_read_off | B | 9,11 | 1 |
| A | ordinary_read_off | B | 9,13 | 2 |
| A | ordinary_read_off | B | 11,3 | 1 |
| A | ordinary_read_off | B | 11,9 | 1 |
| A | ordinary_read_off | B | 12,4 | 1 |
| A | ordinary_read_off | B | 13,4 | 1 |
| A | ordinary_read_off | B | 14,10 | 2 |
| A | ordinary_read_off | B | 15,0 | 1 |
| A | aligned_read_off | A | 0,6 | 1 |
| A | aligned_read_off | A | 0,8 | 1 |
| A | aligned_read_off | A | 0,10 | 1 |
| A | aligned_read_off | A | 0,11 | 3 |
| A | aligned_read_off | A | 0,12 | 1 |
| A | aligned_read_off | A | 0,13 | 2 |
| A | aligned_read_off | A | 1,0 | 1 |
| A | aligned_read_off | A | 1,1 | 2 |
| A | aligned_read_off | A | 1,4 | 1 |
| A | aligned_read_off | A | 1,7 | 1 |
| A | aligned_read_off | A | 1,8 | 2 |
| A | aligned_read_off | A | 1,10 | 1 |
| A | aligned_read_off | A | 1,12 | 5 |
| A | aligned_read_off | A | 1,14 | 1 |
| A | aligned_read_off | A | 2,1 | 2 |
| A | aligned_read_off | A | 2,2 | 1 |
| A | aligned_read_off | A | 2,4 | 5 |
| A | aligned_read_off | A | 2,5 | 1 |
| A | aligned_read_off | A | 2,6 | 2 |
| A | aligned_read_off | A | 2,8 | 1 |
| A | aligned_read_off | A | 2,12 | 1 |
| A | aligned_read_off | A | 2,13 | 1 |
| A | aligned_read_off | A | 2,15 | 1 |
| A | aligned_read_off | A | 3,1 | 2 |
| A | aligned_read_off | A | 3,2 | 3 |
| A | aligned_read_off | A | 3,4 | 1 |
| A | aligned_read_off | A | 3,5 | 1 |
| A | aligned_read_off | A | 3,6 | 1 |
| A | aligned_read_off | A | 3,9 | 1 |
| A | aligned_read_off | A | 3,10 | 1 |
| A | aligned_read_off | A | 3,11 | 1 |
| A | aligned_read_off | A | 4,1 | 2 |
| A | aligned_read_off | A | 4,2 | 1 |
| A | aligned_read_off | A | 4,3 | 1 |
| A | aligned_read_off | A | 4,4 | 1 |
| A | aligned_read_off | A | 4,5 | 1 |
| A | aligned_read_off | A | 4,10 | 1 |
| A | aligned_read_off | A | 4,14 | 1 |
| A | aligned_read_off | A | 5,1 | 1 |
| A | aligned_read_off | A | 5,3 | 1 |
| A | aligned_read_off | A | 5,4 | 1 |
| A | aligned_read_off | A | 5,5 | 3 |
| A | aligned_read_off | A | 5,6 | 1 |
| A | aligned_read_off | A | 5,7 | 1 |
| A | aligned_read_off | A | 5,8 | 5 |
| A | aligned_read_off | A | 5,9 | 1 |
| A | aligned_read_off | A | 5,12 | 2 |
| A | aligned_read_off | A | 5,13 | 1 |
| A | aligned_read_off | A | 6,0 | 1 |
| A | aligned_read_off | A | 6,2 | 1 |
| A | aligned_read_off | A | 6,3 | 2 |
| A | aligned_read_off | A | 6,6 | 2 |
| A | aligned_read_off | A | 6,7 | 1 |
| A | aligned_read_off | A | 6,8 | 1 |
| A | aligned_read_off | A | 6,10 | 2 |
| A | aligned_read_off | A | 6,12 | 2 |
| A | aligned_read_off | A | 6,14 | 3 |
| A | aligned_read_off | A | 6,15 | 1 |
| A | aligned_read_off | A | 7,2 | 2 |
| A | aligned_read_off | A | 7,8 | 1 |
| A | aligned_read_off | A | 7,9 | 3 |
| A | aligned_read_off | A | 7,10 | 1 |
| A | aligned_read_off | A | 7,13 | 1 |
| A | aligned_read_off | A | 7,14 | 1 |
| A | aligned_read_off | A | 8,2 | 1 |
| A | aligned_read_off | A | 8,3 | 1 |
| A | aligned_read_off | A | 8,4 | 1 |
| A | aligned_read_off | A | 8,5 | 1 |
| A | aligned_read_off | A | 8,8 | 1 |
| A | aligned_read_off | A | 8,12 | 1 |
| A | aligned_read_off | A | 8,13 | 1 |
| A | aligned_read_off | A | 8,14 | 1 |
| A | aligned_read_off | A | 9,1 | 1 |
| A | aligned_read_off | A | 9,3 | 2 |
| A | aligned_read_off | A | 9,5 | 2 |
| A | aligned_read_off | A | 9,10 | 1 |
| A | aligned_read_off | A | 9,12 | 2 |
| A | aligned_read_off | A | 9,13 | 1 |
| A | aligned_read_off | A | 9,15 | 2 |
| A | aligned_read_off | A | 10,0 | 1 |
| A | aligned_read_off | A | 10,1 | 1 |
| A | aligned_read_off | A | 11,2 | 1 |
| A | aligned_read_off | A | 11,3 | 1 |
| A | aligned_read_off | A | 11,5 | 1 |
| A | aligned_read_off | A | 11,6 | 1 |
| A | aligned_read_off | A | 11,7 | 2 |
| A | aligned_read_off | A | 11,11 | 3 |
| A | aligned_read_off | A | 11,15 | 1 |
| A | aligned_read_off | A | 12,1 | 1 |
| A | aligned_read_off | A | 12,3 | 1 |
| A | aligned_read_off | A | 12,6 | 3 |
| A | aligned_read_off | A | 12,7 | 2 |
| A | aligned_read_off | A | 12,8 | 2 |
| A | aligned_read_off | A | 12,10 | 2 |
| A | aligned_read_off | A | 12,11 | 1 |
| A | aligned_read_off | A | 12,14 | 2 |
| A | aligned_read_off | A | 12,15 | 1 |
| A | aligned_read_off | A | 13,1 | 1 |
| A | aligned_read_off | A | 13,5 | 1 |
| A | aligned_read_off | A | 13,6 | 1 |
| A | aligned_read_off | A | 13,10 | 1 |
| A | aligned_read_off | A | 13,12 | 1 |
| A | aligned_read_off | A | 13,13 | 2 |
| A | aligned_read_off | A | 14,3 | 1 |
| A | aligned_read_off | A | 14,5 | 1 |
| A | aligned_read_off | A | 14,8 | 1 |
| A | aligned_read_off | A | 14,15 | 2 |
| A | aligned_read_off | A | 15,4 | 2 |
| A | aligned_read_off | A | 15,5 | 1 |
| A | aligned_read_off | A | 15,6 | 1 |
| A | aligned_read_off | A | 15,7 | 2 |
| A | aligned_read_off | A | 15,10 | 1 |
| A | aligned_read_off | A | 15,11 | 1 |
| A | aligned_read_off | A | 15,12 | 1 |
| A | aligned_read_off | A | 15,15 | 1 |
| A | aligned_read_off | B | 0,5 | 2 |
| A | aligned_read_off | B | 2,8 | 1 |
| A | aligned_read_off | B | 2,12 | 2 |
| A | aligned_read_off | B | 3,12 | 1 |
| A | aligned_read_off | B | 5,1 | 1 |
| A | aligned_read_off | B | 5,2 | 1 |
| A | aligned_read_off | B | 5,3 | 1 |
| A | aligned_read_off | B | 6,10 | 1 |
| A | aligned_read_off | B | 7,3 | 1 |
| A | aligned_read_off | B | 8,12 | 1 |
| A | aligned_read_off | B | 9,3 | 2 |
| A | aligned_read_off | B | 9,5 | 1 |
| A | aligned_read_off | B | 9,13 | 1 |
| A | aligned_read_off | B | 10,9 | 1 |
| A | aligned_read_off | B | 11,10 | 2 |
| A | aligned_read_off | B | 12,9 | 1 |
| A | aligned_read_off | B | 12,10 | 1 |
| A | aligned_read_off | B | 14,13 | 2 |
| A | aligned_read_off | B | 15,5 | 1 |
| A | aligned_read_off | B | 15,8 | 1 |
| A | write_off | unassigned | 0,0 | 192 |
| B | ordinary | A | 0,2 | 3 |
| B | ordinary | A | 0,7 | 1 |
| B | ordinary | A | 0,11 | 1 |
| B | ordinary | A | 0,12 | 1 |
| B | ordinary | A | 1,6 | 3 |
| B | ordinary | A | 1,10 | 3 |
| B | ordinary | A | 1,13 | 3 |
| B | ordinary | A | 2,5 | 3 |
| B | ordinary | A | 2,7 | 1 |
| B | ordinary | A | 2,9 | 1 |
| B | ordinary | A | 2,10 | 3 |
| B | ordinary | A | 3,2 | 1 |
| B | ordinary | A | 4,0 | 3 |
| B | ordinary | A | 4,8 | 1 |
| B | ordinary | A | 6,13 | 1 |
| B | ordinary | A | 8,8 | 2 |
| B | ordinary | A | 10,12 | 2 |
| B | ordinary | A | 11,14 | 3 |
| B | ordinary | A | 14,3 | 1 |
| B | ordinary | A | 15,2 | 2 |
| B | ordinary | B | 0,2 | 2 |
| B | ordinary | B | 0,5 | 1 |
| B | ordinary | B | 0,7 | 1 |
| B | ordinary | B | 0,8 | 1 |
| B | ordinary | B | 0,10 | 1 |
| B | ordinary | B | 0,11 | 3 |
| B | ordinary | B | 1,0 | 3 |
| B | ordinary | B | 1,2 | 1 |
| B | ordinary | B | 1,4 | 1 |
| B | ordinary | B | 1,7 | 3 |
| B | ordinary | B | 1,8 | 2 |
| B | ordinary | B | 1,11 | 1 |
| B | ordinary | B | 2,0 | 4 |
| B | ordinary | B | 2,4 | 1 |
| B | ordinary | B | 2,5 | 2 |
| B | ordinary | B | 2,11 | 1 |
| B | ordinary | B | 3,0 | 3 |
| B | ordinary | B | 3,6 | 1 |
| B | ordinary | B | 3,7 | 1 |
| B | ordinary | B | 3,11 | 2 |
| B | ordinary | B | 3,13 | 1 |
| B | ordinary | B | 3,15 | 1 |
| B | ordinary | B | 4,0 | 2 |
| B | ordinary | B | 4,2 | 1 |
| B | ordinary | B | 4,5 | 1 |
| B | ordinary | B | 4,7 | 1 |
| B | ordinary | B | 4,9 | 2 |
| B | ordinary | B | 4,12 | 1 |
| B | ordinary | B | 4,15 | 1 |
| B | ordinary | B | 5,0 | 3 |
| B | ordinary | B | 5,2 | 2 |
| B | ordinary | B | 5,3 | 7 |
| B | ordinary | B | 5,5 | 1 |
| B | ordinary | B | 5,7 | 1 |
| B | ordinary | B | 5,12 | 1 |
| B | ordinary | B | 5,14 | 1 |
| B | ordinary | B | 5,15 | 3 |
| B | ordinary | B | 6,0 | 2 |
| B | ordinary | B | 6,8 | 1 |
| B | ordinary | B | 6,13 | 1 |
| B | ordinary | B | 6,14 | 3 |
| B | ordinary | B | 6,15 | 4 |
| B | ordinary | B | 7,0 | 1 |
| B | ordinary | B | 7,2 | 3 |
| B | ordinary | B | 7,4 | 1 |
| B | ordinary | B | 7,7 | 1 |
| B | ordinary | B | 8,0 | 1 |
| B | ordinary | B | 8,1 | 1 |
| B | ordinary | B | 8,4 | 1 |
| B | ordinary | B | 8,7 | 1 |
| B | ordinary | B | 9,0 | 1 |
| B | ordinary | B | 9,1 | 2 |
| B | ordinary | B | 9,4 | 1 |
| B | ordinary | B | 9,7 | 4 |
| B | ordinary | B | 10,0 | 3 |
| B | ordinary | B | 10,1 | 2 |
| B | ordinary | B | 10,3 | 3 |
| B | ordinary | B | 10,4 | 1 |
| B | ordinary | B | 10,7 | 2 |
| B | ordinary | B | 10,8 | 2 |
| B | ordinary | B | 10,15 | 2 |
| B | ordinary | B | 11,0 | 1 |
| B | ordinary | B | 11,3 | 1 |
| B | ordinary | B | 11,6 | 2 |
| B | ordinary | B | 11,7 | 1 |
| B | ordinary | B | 11,9 | 1 |
| B | ordinary | B | 11,12 | 1 |
| B | ordinary | B | 11,14 | 1 |
| B | ordinary | B | 12,0 | 1 |
| B | ordinary | B | 12,9 | 1 |
| B | ordinary | B | 12,10 | 1 |
| B | ordinary | B | 12,12 | 3 |
| B | ordinary | B | 12,14 | 1 |
| B | ordinary | B | 12,15 | 1 |
| B | ordinary | B | 13,0 | 3 |
| B | ordinary | B | 13,1 | 1 |
| B | ordinary | B | 13,4 | 2 |
| B | ordinary | B | 13,13 | 2 |
| B | ordinary | B | 14,2 | 2 |
| B | ordinary | B | 14,3 | 2 |
| B | ordinary | B | 14,5 | 4 |
| B | ordinary | B | 14,15 | 4 |
| B | ordinary | B | 15,2 | 1 |
| B | ordinary | B | 15,3 | 2 |
| B | ordinary | B | 15,4 | 1 |
| B | ordinary | B | 15,8 | 1 |
| B | ordinary | B | 15,10 | 2 |
| B | ordinary | B | 15,11 | 1 |
| B | aligned | A | 0,0 | 5 |
| B | aligned | A | 0,1 | 1 |
| B | aligned | A | 3,1 | 2 |
| B | aligned | B | 0,0 | 76 |
| B | aligned | B | 0,1 | 1 |
| B | aligned | B | 1,0 | 23 |
| B | aligned | B | 1,1 | 1 |
| B | aligned | B | 2,0 | 12 |
| B | aligned | B | 3,0 | 1 |
| B | aligned | B | 3,8 | 3 |
| B | aligned | B | 4,0 | 2 |
| B | aligned | B | 5,0 | 2 |
| B | aligned | B | 6,0 | 2 |
| B | aligned | B | 7,0 | 2 |
| B | aligned | B | 9,0 | 4 |
| B | aligned | B | 10,0 | 7 |
| B | aligned | B | 11,0 | 1 |
| B | aligned | B | 12,0 | 8 |
| B | aligned | B | 13,0 | 10 |
| B | aligned | B | 13,1 | 1 |
| B | aligned | B | 13,8 | 3 |
| B | aligned | B | 14,0 | 6 |
| B | aligned | B | 15,0 | 19 |
| B | protected_copy | B | 1,15 | 12 |
| B | protected_copy | B | 2,13 | 12 |
| B | protected_copy | B | 5,14 | 12 |
| B | protected_copy | B | 9,3 | 12 |
| B | protected_copy | B | 9,4 | 12 |
| B | protected_copy | B | 9,11 | 12 |
| B | protected_copy | B | 10,11 | 12 |
| B | protected_copy | B | 11,3 | 12 |
| B | protected_copy | B | 11,11 | 12 |
| B | protected_copy | B | 12,2 | 12 |
| B | protected_copy | B | 12,9 | 12 |
| B | protected_copy | B | 12,13 | 12 |
| B | protected_copy | B | 13,4 | 12 |
| B | protected_copy | B | 13,10 | 24 |
| B | protected_copy | B | 15,8 | 12 |
| B | ordinary_read_off | A | 0,4 | 1 |
| B | ordinary_read_off | A | 0,7 | 1 |
| B | ordinary_read_off | A | 0,8 | 2 |
| B | ordinary_read_off | A | 0,10 | 1 |
| B | ordinary_read_off | A | 0,11 | 2 |
| B | ordinary_read_off | A | 1,3 | 1 |
| B | ordinary_read_off | A | 1,4 | 1 |
| B | ordinary_read_off | A | 1,6 | 3 |
| B | ordinary_read_off | A | 1,8 | 2 |
| B | ordinary_read_off | A | 1,10 | 1 |
| B | ordinary_read_off | A | 1,11 | 1 |
| B | ordinary_read_off | A | 2,1 | 1 |
| B | ordinary_read_off | A | 2,2 | 2 |
| B | ordinary_read_off | A | 2,3 | 2 |
| B | ordinary_read_off | A | 2,4 | 1 |
| B | ordinary_read_off | A | 2,5 | 1 |
| B | ordinary_read_off | A | 2,7 | 1 |
| B | ordinary_read_off | A | 2,8 | 2 |
| B | ordinary_read_off | A | 2,11 | 2 |
| B | ordinary_read_off | A | 3,1 | 1 |
| B | ordinary_read_off | A | 3,2 | 1 |
| B | ordinary_read_off | A | 3,3 | 2 |
| B | ordinary_read_off | A | 3,6 | 1 |
| B | ordinary_read_off | A | 3,7 | 1 |
| B | ordinary_read_off | A | 3,8 | 2 |
| B | ordinary_read_off | A | 3,14 | 3 |
| B | ordinary_read_off | A | 4,1 | 1 |
| B | ordinary_read_off | A | 4,3 | 1 |
| B | ordinary_read_off | A | 4,4 | 1 |
| B | ordinary_read_off | A | 4,6 | 3 |
| B | ordinary_read_off | A | 4,7 | 1 |
| B | ordinary_read_off | A | 4,12 | 2 |
| B | ordinary_read_off | A | 4,13 | 1 |
| B | ordinary_read_off | A | 5,3 | 2 |
| B | ordinary_read_off | A | 5,7 | 2 |
| B | ordinary_read_off | A | 5,8 | 3 |
| B | ordinary_read_off | A | 5,9 | 2 |
| B | ordinary_read_off | A | 5,10 | 1 |
| B | ordinary_read_off | A | 5,11 | 2 |
| B | ordinary_read_off | A | 5,12 | 2 |
| B | ordinary_read_off | A | 5,14 | 3 |
| B | ordinary_read_off | A | 6,1 | 1 |
| B | ordinary_read_off | A | 6,3 | 1 |
| B | ordinary_read_off | A | 6,4 | 1 |
| B | ordinary_read_off | A | 6,6 | 1 |
| B | ordinary_read_off | A | 6,12 | 2 |
| B | ordinary_read_off | A | 6,15 | 1 |
| B | ordinary_read_off | A | 7,0 | 1 |
| B | ordinary_read_off | A | 7,2 | 1 |
| B | ordinary_read_off | A | 7,4 | 1 |
| B | ordinary_read_off | A | 7,5 | 1 |
| B | ordinary_read_off | A | 7,6 | 1 |
| B | ordinary_read_off | A | 7,8 | 1 |
| B | ordinary_read_off | A | 7,9 | 1 |
| B | ordinary_read_off | A | 7,10 | 2 |
| B | ordinary_read_off | A | 7,14 | 1 |
| B | ordinary_read_off | A | 8,0 | 1 |
| B | ordinary_read_off | A | 8,6 | 2 |
| B | ordinary_read_off | A | 8,8 | 3 |
| B | ordinary_read_off | A | 8,9 | 1 |
| B | ordinary_read_off | A | 8,12 | 2 |
| B | ordinary_read_off | A | 8,13 | 1 |
| B | ordinary_read_off | A | 8,15 | 3 |
| B | ordinary_read_off | A | 9,0 | 1 |
| B | ordinary_read_off | A | 9,2 | 1 |
| B | ordinary_read_off | A | 9,4 | 1 |
| B | ordinary_read_off | A | 9,10 | 1 |
| B | ordinary_read_off | A | 9,12 | 2 |
| B | ordinary_read_off | A | 9,14 | 1 |
| B | ordinary_read_off | A | 10,0 | 2 |
| B | ordinary_read_off | A | 10,9 | 4 |
| B | ordinary_read_off | A | 10,11 | 1 |
| B | ordinary_read_off | A | 10,12 | 3 |
| B | ordinary_read_off | A | 10,13 | 1 |
| B | ordinary_read_off | A | 10,14 | 3 |
| B | ordinary_read_off | A | 11,0 | 1 |
| B | ordinary_read_off | A | 11,7 | 1 |
| B | ordinary_read_off | A | 11,8 | 1 |
| B | ordinary_read_off | A | 11,15 | 2 |
| B | ordinary_read_off | A | 12,0 | 1 |
| B | ordinary_read_off | A | 12,2 | 1 |
| B | ordinary_read_off | A | 12,4 | 1 |
| B | ordinary_read_off | A | 12,6 | 1 |
| B | ordinary_read_off | A | 12,7 | 2 |
| B | ordinary_read_off | A | 12,8 | 2 |
| B | ordinary_read_off | A | 12,9 | 1 |
| B | ordinary_read_off | A | 12,13 | 1 |
| B | ordinary_read_off | A | 12,14 | 1 |
| B | ordinary_read_off | A | 12,15 | 1 |
| B | ordinary_read_off | A | 13,1 | 2 |
| B | ordinary_read_off | A | 13,4 | 1 |
| B | ordinary_read_off | A | 13,5 | 1 |
| B | ordinary_read_off | A | 13,6 | 1 |
| B | ordinary_read_off | A | 13,8 | 3 |
| B | ordinary_read_off | A | 13,9 | 1 |
| B | ordinary_read_off | A | 13,11 | 1 |
| B | ordinary_read_off | A | 13,13 | 1 |
| B | ordinary_read_off | A | 14,3 | 1 |
| B | ordinary_read_off | A | 14,4 | 1 |
| B | ordinary_read_off | A | 14,5 | 1 |
| B | ordinary_read_off | A | 14,8 | 1 |
| B | ordinary_read_off | A | 14,10 | 2 |
| B | ordinary_read_off | A | 15,6 | 1 |
| B | ordinary_read_off | A | 15,7 | 2 |
| B | ordinary_read_off | A | 15,8 | 4 |
| B | ordinary_read_off | A | 15,10 | 1 |
| B | ordinary_read_off | B | 1,3 | 1 |
| B | ordinary_read_off | B | 2,10 | 1 |
| B | ordinary_read_off | B | 2,14 | 3 |
| B | ordinary_read_off | B | 3,4 | 1 |
| B | ordinary_read_off | B | 3,6 | 1 |
| B | ordinary_read_off | B | 3,12 | 1 |
| B | ordinary_read_off | B | 4,1 | 2 |
| B | ordinary_read_off | B | 4,4 | 1 |
| B | ordinary_read_off | B | 4,7 | 1 |
| B | ordinary_read_off | B | 5,14 | 1 |
| B | ordinary_read_off | B | 6,8 | 1 |
| B | ordinary_read_off | B | 6,9 | 1 |
| B | ordinary_read_off | B | 7,3 | 1 |
| B | ordinary_read_off | B | 7,8 | 1 |
| B | ordinary_read_off | B | 7,9 | 2 |
| B | ordinary_read_off | B | 8,1 | 1 |
| B | ordinary_read_off | B | 8,2 | 1 |
| B | ordinary_read_off | B | 9,3 | 1 |
| B | ordinary_read_off | B | 9,10 | 1 |
| B | ordinary_read_off | B | 9,11 | 1 |
| B | ordinary_read_off | B | 9,13 | 2 |
| B | ordinary_read_off | B | 11,3 | 1 |
| B | ordinary_read_off | B | 11,9 | 1 |
| B | ordinary_read_off | B | 12,4 | 1 |
| B | ordinary_read_off | B | 13,4 | 1 |
| B | ordinary_read_off | B | 14,10 | 2 |
| B | ordinary_read_off | B | 15,0 | 1 |
| B | aligned_read_off | A | 0,6 | 1 |
| B | aligned_read_off | A | 0,8 | 1 |
| B | aligned_read_off | A | 0,10 | 1 |
| B | aligned_read_off | A | 0,11 | 3 |
| B | aligned_read_off | A | 0,12 | 1 |
| B | aligned_read_off | A | 0,13 | 2 |
| B | aligned_read_off | A | 1,0 | 1 |
| B | aligned_read_off | A | 1,1 | 2 |
| B | aligned_read_off | A | 1,4 | 1 |
| B | aligned_read_off | A | 1,7 | 1 |
| B | aligned_read_off | A | 1,8 | 2 |
| B | aligned_read_off | A | 1,10 | 1 |
| B | aligned_read_off | A | 1,12 | 5 |
| B | aligned_read_off | A | 1,14 | 1 |
| B | aligned_read_off | A | 2,1 | 2 |
| B | aligned_read_off | A | 2,2 | 1 |
| B | aligned_read_off | A | 2,4 | 5 |
| B | aligned_read_off | A | 2,5 | 1 |
| B | aligned_read_off | A | 2,6 | 2 |
| B | aligned_read_off | A | 2,8 | 1 |
| B | aligned_read_off | A | 2,12 | 1 |
| B | aligned_read_off | A | 2,13 | 1 |
| B | aligned_read_off | A | 2,15 | 1 |
| B | aligned_read_off | A | 3,1 | 2 |
| B | aligned_read_off | A | 3,2 | 3 |
| B | aligned_read_off | A | 3,4 | 1 |
| B | aligned_read_off | A | 3,5 | 1 |
| B | aligned_read_off | A | 3,6 | 1 |
| B | aligned_read_off | A | 3,9 | 1 |
| B | aligned_read_off | A | 3,10 | 1 |
| B | aligned_read_off | A | 3,11 | 1 |
| B | aligned_read_off | A | 4,1 | 2 |
| B | aligned_read_off | A | 4,2 | 1 |
| B | aligned_read_off | A | 4,3 | 1 |
| B | aligned_read_off | A | 4,4 | 1 |
| B | aligned_read_off | A | 4,5 | 1 |
| B | aligned_read_off | A | 4,10 | 1 |
| B | aligned_read_off | A | 4,14 | 1 |
| B | aligned_read_off | A | 5,1 | 1 |
| B | aligned_read_off | A | 5,3 | 1 |
| B | aligned_read_off | A | 5,4 | 1 |
| B | aligned_read_off | A | 5,5 | 3 |
| B | aligned_read_off | A | 5,6 | 1 |
| B | aligned_read_off | A | 5,7 | 1 |
| B | aligned_read_off | A | 5,8 | 5 |
| B | aligned_read_off | A | 5,9 | 1 |
| B | aligned_read_off | A | 5,12 | 2 |
| B | aligned_read_off | A | 5,13 | 1 |
| B | aligned_read_off | A | 6,0 | 1 |
| B | aligned_read_off | A | 6,2 | 1 |
| B | aligned_read_off | A | 6,3 | 2 |
| B | aligned_read_off | A | 6,6 | 2 |
| B | aligned_read_off | A | 6,7 | 1 |
| B | aligned_read_off | A | 6,8 | 1 |
| B | aligned_read_off | A | 6,10 | 2 |
| B | aligned_read_off | A | 6,12 | 2 |
| B | aligned_read_off | A | 6,14 | 3 |
| B | aligned_read_off | A | 6,15 | 1 |
| B | aligned_read_off | A | 7,2 | 2 |
| B | aligned_read_off | A | 7,8 | 1 |
| B | aligned_read_off | A | 7,9 | 3 |
| B | aligned_read_off | A | 7,10 | 1 |
| B | aligned_read_off | A | 7,13 | 1 |
| B | aligned_read_off | A | 7,14 | 1 |
| B | aligned_read_off | A | 8,2 | 1 |
| B | aligned_read_off | A | 8,3 | 1 |
| B | aligned_read_off | A | 8,4 | 1 |
| B | aligned_read_off | A | 8,5 | 1 |
| B | aligned_read_off | A | 8,8 | 1 |
| B | aligned_read_off | A | 8,12 | 1 |
| B | aligned_read_off | A | 8,13 | 1 |
| B | aligned_read_off | A | 8,14 | 1 |
| B | aligned_read_off | A | 9,1 | 1 |
| B | aligned_read_off | A | 9,3 | 2 |
| B | aligned_read_off | A | 9,5 | 2 |
| B | aligned_read_off | A | 9,10 | 1 |
| B | aligned_read_off | A | 9,12 | 2 |
| B | aligned_read_off | A | 9,13 | 1 |
| B | aligned_read_off | A | 9,15 | 2 |
| B | aligned_read_off | A | 10,0 | 1 |
| B | aligned_read_off | A | 10,1 | 1 |
| B | aligned_read_off | A | 11,2 | 1 |
| B | aligned_read_off | A | 11,3 | 1 |
| B | aligned_read_off | A | 11,5 | 1 |
| B | aligned_read_off | A | 11,6 | 1 |
| B | aligned_read_off | A | 11,7 | 2 |
| B | aligned_read_off | A | 11,11 | 3 |
| B | aligned_read_off | A | 11,15 | 1 |
| B | aligned_read_off | A | 12,1 | 1 |
| B | aligned_read_off | A | 12,3 | 1 |
| B | aligned_read_off | A | 12,6 | 3 |
| B | aligned_read_off | A | 12,7 | 2 |
| B | aligned_read_off | A | 12,8 | 2 |
| B | aligned_read_off | A | 12,10 | 2 |
| B | aligned_read_off | A | 12,11 | 1 |
| B | aligned_read_off | A | 12,14 | 2 |
| B | aligned_read_off | A | 12,15 | 1 |
| B | aligned_read_off | A | 13,1 | 1 |
| B | aligned_read_off | A | 13,5 | 1 |
| B | aligned_read_off | A | 13,6 | 1 |
| B | aligned_read_off | A | 13,10 | 1 |
| B | aligned_read_off | A | 13,12 | 1 |
| B | aligned_read_off | A | 13,13 | 2 |
| B | aligned_read_off | A | 14,3 | 1 |
| B | aligned_read_off | A | 14,5 | 1 |
| B | aligned_read_off | A | 14,8 | 1 |
| B | aligned_read_off | A | 14,15 | 2 |
| B | aligned_read_off | A | 15,4 | 2 |
| B | aligned_read_off | A | 15,5 | 1 |
| B | aligned_read_off | A | 15,6 | 1 |
| B | aligned_read_off | A | 15,7 | 2 |
| B | aligned_read_off | A | 15,10 | 1 |
| B | aligned_read_off | A | 15,11 | 1 |
| B | aligned_read_off | A | 15,12 | 1 |
| B | aligned_read_off | A | 15,15 | 1 |
| B | aligned_read_off | B | 0,5 | 2 |
| B | aligned_read_off | B | 2,8 | 1 |
| B | aligned_read_off | B | 2,12 | 2 |
| B | aligned_read_off | B | 3,12 | 1 |
| B | aligned_read_off | B | 5,1 | 1 |
| B | aligned_read_off | B | 5,2 | 1 |
| B | aligned_read_off | B | 5,3 | 1 |
| B | aligned_read_off | B | 6,10 | 1 |
| B | aligned_read_off | B | 7,3 | 1 |
| B | aligned_read_off | B | 8,12 | 1 |
| B | aligned_read_off | B | 9,3 | 2 |
| B | aligned_read_off | B | 9,5 | 1 |
| B | aligned_read_off | B | 9,13 | 1 |
| B | aligned_read_off | B | 10,9 | 1 |
| B | aligned_read_off | B | 11,10 | 2 |
| B | aligned_read_off | B | 12,9 | 1 |
| B | aligned_read_off | B | 12,10 | 1 |
| B | aligned_read_off | B | 14,13 | 2 |
| B | aligned_read_off | B | 15,5 | 1 |
| B | aligned_read_off | B | 15,8 | 1 |
| B | write_off | unassigned | 0,0 | 192 |

## Terminal body diagnostics

| Assay | Family | Condition | Mean RMS | Mean clipped sites percent | Maximum clipped sites percent |
| --- | --- | --- | --- | --- | --- |
| common | A | ordinary | 0.97127766 | 0.0549 | 0.3906 |
| common | A | aligned | 0.975597527 | 0.0671 | 0.3906 |
| common | A | protected_copy | 0.970900997 | 0.0671 | 0.3906 |
| common | A | ordinary_read_off | 0.951557816 | 0.0366 | 0.3906 |
| common | A | aligned_read_off | 0.953498202 | 0.0285 | 0.3906 |
| common | A | write_off | 0.73429849 | 0.0061 | 0.3906 |
| common | B | ordinary | 0.940851245 | 0.0407 | 0.3906 |
| common | B | aligned | 0.935713534 | 0.0366 | 0.3906 |
| common | B | protected_copy | 0.918977039 | 0.0427 | 0.3906 |
| common | B | ordinary_read_off | 0.951557816 | 0.0366 | 0.3906 |
| common | B | aligned_read_off | 0.953498202 | 0.0285 | 0.3906 |
| common | B | write_off | 0.73429849 | 0.0061 | 0.3906 |
| native | A | ordinary | 0.971231876 | 0.0590 | 0.3906 |
| native | A | aligned | 0.975500011 | 0.0671 | 0.3906 |
| native | A | protected_copy | 0.970772609 | 0.0671 | 0.7812 |
| native | A | ordinary_read_off | 0.95238921 | 0.0366 | 0.3906 |
| native | A | aligned_read_off | 0.954488959 | 0.0305 | 0.3906 |
| native | A | write_off | 0.736416942 | 0.0061 | 0.3906 |
| native | B | ordinary | 0.941554729 | 0.0448 | 0.3906 |
| native | B | aligned | 0.936357463 | 0.0346 | 0.3906 |
| native | B | protected_copy | 0.919206102 | 0.0427 | 0.3906 |
| native | B | ordinary_read_off | 0.95238921 | 0.0366 | 0.3906 |
| native | B | aligned_read_off | 0.954488959 | 0.0305 | 0.3906 |
| native | B | write_off | 0.736416942 | 0.0061 | 0.3906 |

These are terminal-only diagnostics; they do not establish absence of clipping
in intermediate states. Forward shifts are the guide-selected (row,column) addresses.

## Every donor description

| Group | index | g 0.75 points | g 1.0 points | g 1.25 points | record | recipient | interaction | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 90000 | 44.5312 | 44.2627 | 43.9941 | 4.68713266e-05 | 1.58945719e-06 | -9.14820918e-06 | 3.93125746e-05 |
| common/A/ordinary | 90005 | 42.4316 | 42.7002 | 43.3105 | 0.000203220933 | 1.20798747e-05 | 2.82570168e-07 | 0.000215583377 |
| common/A/ordinary | 90010 | 42.4805 | 43.0420 | 43.2129 | -0.000220475373 | 8.86563902e-06 | 1.18326258e-05 | -0.000199777109 |
| common/A/ordinary | 90015 | 44.1162 | 44.4092 | 44.6777 | 4.47167291e-05 | 2.01331245e-06 | -1.16560194e-06 | 4.55644396e-05 |
| common/A/aligned | 90000 | 42.3096 | 42.3096 | 42.5781 | 2.91400486e-06 | 1.18326258e-06 | 1.58945719e-07 | 4.25621315e-06 |
| common/A/aligned | 90005 | 42.6270 | 43.0908 | 43.6523 | 2.42833738e-05 | 1.53294316e-05 | -9.18353045e-07 | 3.86944524e-05 |
| common/A/aligned | 90010 | 45.0439 | 45.1904 | 45.0684 | 0.000452730391 | 3.35552074e-07 | 5.82800971e-07 | 0.000453648744 |
| common/A/aligned | 90015 | 44.9463 | 44.8730 | 44.8242 | 0.000356903783 | 1.76606355e-08 | 1.889688e-06 | 0.000358811131 |
| common/B/ordinary* | 90000 | 25.7080 | 16.8213 | 11.8408 | 0.0130696473 | 0.00312293017 | 0.000272786176 | 0.0164653637 |
| common/B/ordinary* | 90005 | 25.4395 | 21.6309 | 19.1406 | 0.0112533569 | 0.000660490107 | 0.000186655256 | 0.0121005023 |
| common/B/ordinary* | 90010 | 7.3486 | 6.0059 | 6.3965 | 0.0429537738 | 2.96698676e-06 | -3.82176152e-05 | 0.0429185232 |
| common/B/ordinary* | 90015 | 17.5049 | 15.2100 | 13.3301 | 0.008456707 | 0.000233314655 | -6.44789802e-05 | 0.00862554268 |
| common/B/aligned | 90000 | 30.0049 | 26.4893 | 23.1689 | 0.0128675214 | 0.000719070435 | 0.000256149857 | 0.0138427416 |
| common/B/aligned | 90005 | 33.0811 | 31.4209 | 31.0059 | 0.0159616647 | 7.37508138e-05 | 4.08313893e-05 | 0.0160762469 |
| common/B/aligned | 90010 | 14.3555 | 14.4531 | 14.6484 | 0.0277311184 | -4.18910274e-05 | 0.000426539668 | 0.028115767 |
| common/B/aligned | 90015 | 27.1484 | 25.9033 | 20.6299 | 0.0188880673 | 0.000741976279 | 0.000541457423 | 0.020171501 |
| native/A/ordinary | 90000 | 43.7744 | 44.2627 | 44.4336 | 2.4565944e-05 | 6.05759797e-06 | -9.94293778e-06 | 2.06806042e-05 |
| native/A/ordinary | 90005 | 42.0898 | 42.7002 | 43.3105 | 0.000220422392 | 2.3788876e-05 | 6.44613195e-06 | 0.000250657399 |
| native/A/ordinary | 90010 | 42.2119 | 43.0420 | 43.6279 | -0.000196403927 | 3.26368544e-05 | -8.68903266e-06 | -0.000172456106 |
| native/A/ordinary | 90015 | 43.7012 | 44.4092 | 44.8730 | 3.31490128e-05 | 1.99035362e-05 | 1.28922639e-06 | 5.43417754e-05 |
| native/A/aligned | 90000 | 41.5771 | 42.3096 | 42.6270 | 4.64474713e-06 | 1.84553641e-05 | -1.99565181e-06 | 2.11044594e-05 |
| native/A/aligned | 90005 | 42.3828 | 43.0908 | 43.8232 | 2.62083831e-05 | 3.15242343e-05 | 4.99795984e-06 | 6.27305773e-05 |
| native/A/aligned | 90010 | 44.5312 | 45.1904 | 45.3857 | 0.000424438053 | 1.30158884e-05 | 5.29819065e-08 | 0.000437506923 |
| native/A/aligned | 90015 | 44.8242 | 44.8730 | 45.0195 | 0.000350016135 | -9.88995587e-07 | 1.20092321e-06 | 0.000350228062 |
| native/B/ordinary | 90000 | 26.0986 | 16.8213 | 11.7432 | 0.0131704542 | 0.00336576391 | 0.000120586819 | 0.016656805 |
| native/B/ordinary | 90005 | 25.7812 | 21.6309 | 18.7256 | 0.0111469339 | 0.00082372736 | 0.000141814903 | 0.0121124762 |
| native/B/ordinary | 90010 | 7.4951 | 6.0059 | 6.2988 | 0.0427958524 | 4.09726743e-06 | -6.41434281e-05 | 0.0427358062 |
| native/B/ordinary | 90015 | 17.7490 | 15.2100 | 13.4521 | 0.0086251718 | 0.000237429584 | -5.75736717e-05 | 0.00880502771 |
| native/B/aligned | 90000 | 30.0293 | 26.4893 | 22.7783 | 0.0129754985 | 0.000813272264 | 0.000279991715 | 0.0140687625 |
| native/B/aligned | 90005 | 33.6426 | 31.4209 | 30.9082 | 0.0156563123 | 0.000133002246 | 4.50876024e-05 | 0.0158344022 |
| native/B/aligned | 90010 | 14.6240 | 14.4531 | 14.5752 | 0.0275297518 | -4.04958372e-05 | 0.000430654596 | 0.0279199106 |
| native/B/aligned | 90015 | 26.9043 | 25.9033 | 20.2637 | 0.0184858463 | 0.000807656182 | 0.000531373201 | 0.0198248757 |

## Every donor omission

| Group | omitted | g 0.75 points | g 1.0 points | g 1.25 points | record | recipient | interaction | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 90000 | 43.0094 | 43.3838 | 43.7337 | 3.0523465e-05 | 8.16510047e-06 | 3.13770624e-06 | 4.18262717e-05 |
| common/A/ordinary | 90005 | 43.7093 | 43.9046 | 43.9616 | -1.23918792e-05 | 6.94651663e-07 | 3.96775611e-06 | -7.72947147e-06 |
| common/A/ordinary | 90010 | 43.6930 | 43.7907 | 43.9941 | 0.000137955073 | 1.26764117e-06 | 6.16159949e-07 | 0.000139838874 |
| common/A/ordinary | 90015 | 43.1478 | 43.3350 | 43.5059 | 2.3983143e-05 | 1.57179656e-06 | 6.92885599e-06 | 3.24837955e-05 |
| common/A/aligned | 90000 | 44.2057 | 44.3848 | 44.5150 | 0.000352790817 | 1.33828371e-06 | 4.4073097e-06 | 0.00035853641 |
| common/A/aligned | 90005 | 44.0999 | 44.1243 | 44.1569 | 0.000414701156 | 2.3547514e-08 | 1.36575581e-06 | 0.000416090459 |
| common/A/aligned | 90010 | 43.2943 | 43.4245 | 43.6849 | 0.000233871947 | 2.4352054e-06 | 3.45167309e-06 | 0.000239758825 |
| common/A/aligned | 90015 | 43.3268 | 43.5303 | 43.7663 | 0.000283498332 | 3.04155389e-06 | 2.51565941e-06 | 0.000289055546 |
| common/B/ordinary* | 90000 | 16.7643 | 14.2822 | 12.9557 | 0.0238360593 | 0.000238842434 | 8.80677023e-05 | 0.0241629695 |
| common/B/ordinary* | 90005 | 16.8538 | 12.6790 | 10.5225 | 0.0218684762 | 0.000649346246 | 0.000527087553 | 0.02304491 |
| common/B/ordinary* | 90010 | 22.8841 | 17.8874 | 14.7705 | 0.0105079879 | 0.00108241839 | 0.000388147409 | 0.0119785536 |
| common/B/ordinary* | 90015 | 19.4987 | 14.8193 | 12.4593 | 0.0252474228 | 0.000835573722 | 0.000566963306 | 0.0266499598 |
| common/B/aligned | 90000 | 24.8617 | 23.9258 | 22.0947 | 0.0257928244 | 0.000127658922 | 0.000466562593 | 0.0263870459 |
| common/B/aligned | 90005 | 23.8363 | 22.2819 | 19.4824 | 0.0224317719 | 0.000318501712 | 0.000562599166 | 0.0233128728 |
| common/B/aligned | 90010 | 30.0781 | 27.9378 | 24.9349 | 0.0166660709 | 0.000436570909 | 0.000354507823 | 0.0174571496 |
| common/B/aligned | 90015 | 25.8138 | 24.1211 | 22.9411 | 0.0240717994 | 0.000125990974 | 0.000365492738 | 0.0245632831 |
| native/A/ordinary | 90000 | 42.6676 | 43.3838 | 43.9372 | 3.91300814e-05 | 2.66028039e-05 | -1.4776065e-06 | 6.42552788e-05 |
| native/A/ordinary | 90005 | 43.2292 | 43.9046 | 44.3115 | -2.12045363e-05 | 1.91205814e-05 | -5.36883319e-06 | -7.45278818e-06 |
| native/A/ordinary | 90010 | 43.1885 | 43.7907 | 44.2057 | 0.000132154535 | 1.71367033e-05 | -1.28922639e-06 | 0.000148002012 |
| native/A/ordinary | 90015 | 42.6921 | 43.3350 | 43.7907 | 2.75937618e-05 | 1.99349329e-05 | -3.16910292e-06 | 4.43595918e-05 |
| native/A/aligned | 90000 | 43.9128 | 44.3848 | 44.7428 | 0.000342716405 | 1.10732185e-05 | 5.52777891e-06 | 0.000359317403 |
| native/A/aligned | 90005 | 43.6442 | 44.1243 | 44.3441 | 0.000428949364 | 8.06698583e-06 | 1.84651756e-06 | 0.000438862867 |
| native/A/aligned | 90010 | 42.9281 | 43.4245 | 43.8232 | 0.000253534121 | 1.29786048e-05 | 4.75267324e-06 | 0.000271265399 |
| native/A/aligned | 90015 | 42.8304 | 43.5303 | 43.9453 | 0.000288498254 | 2.07159254e-05 | 1.30100015e-06 | 0.00031051518 |
| native/B/ordinary | 90000 | 17.0085 | 14.2822 | 12.8255 | 0.0237778695 | 0.000286904873 | 7.48791322e-05 | 0.0241396535 |
| native/B/ordinary | 90005 | 17.1143 | 12.6790 | 10.4980 | 0.0219660159 | 0.000709892791 | 0.000492160703 | 0.0231680693 |
| native/B/ordinary | 90010 | 23.2096 | 17.8874 | 14.6403 | 0.010560279 | 0.00121193364 | 0.000331982664 | 0.0121041953 |
| native/B/ordinary | 90015 | 19.7917 | 14.8193 | 12.2559 | 0.0252046879 | 0.00095783634 | 0.000506112605 | 0.0266686369 |
| native/B/aligned | 90000 | 25.0570 | 23.9258 | 21.9157 | 0.0255170104 | 0.000164308666 | 0.000471450664 | 0.0261527697 |
| native/B/aligned | 90005 | 23.8525 | 22.2819 | 19.2057 | 0.0221537543 | 0.000364132869 | 0.000576684504 | 0.0230945717 |
| native/B/aligned | 90010 | 30.1921 | 27.9378 | 24.6501 | 0.0165545283 | 0.00050944654 | 0.000360681196 | 0.017424656 |
| native/B/aligned | 90015 | 26.0986 | 24.1211 | 22.7539 | 0.0239589263 | 0.000174200584 | 0.000379636945 | 0.0245127639 |

## Every future omission

| Group | omitted | g 0.75 points | g 1.0 points | g 1.25 points | record | recipient | interaction | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 2 | 43.3350 | 43.4814 | 43.7744 | -1.06846845e-06 | 3.13917796e-06 | 7.28059698e-06 | 9.35130649e-06 |
| common/A/ordinary | 3 | 43.5547 | 43.8558 | 43.9860 | -1.6424391e-06 | 3.00672319e-06 | 4.51670753e-06 | 5.88099162e-06 |
| common/A/ordinary | 4 | 43.4245 | 43.6279 | 43.7826 | 8.18261394e-05 | 1.71528922e-06 | 2.17005059e-06 | 8.57114792e-05 |
| common/A/ordinary | 5 | 43.2454 | 43.4489 | 43.6523 | 0.000114171593 | 2.23186281e-06 | 2.28925988e-06 | 0.000118692716 |
| common/A/aligned | 2 | 43.9535 | 44.1243 | 44.2627 | 0.000313158388 | 1.44817211e-06 | 1.87202736e-06 | 0.000316478588 |
| common/A/aligned | 3 | 43.7663 | 43.8558 | 44.0023 | 0.000308955157 | 8.87446933e-07 | 3.59835448e-06 | 0.000313440959 |
| common/A/aligned | 4 | 43.4489 | 43.5710 | 43.7744 | 0.000374652721 | 1.65568458e-06 | 3.99571878e-06 | 0.000380304125 |
| common/A/aligned | 5 | 43.7581 | 43.9128 | 44.0837 | 0.000344099822 | 1.59387235e-06 | 3.52771194e-06 | 0.000349221406 |
| common/B/ordinary* | 2 | 19.7998 | 15.8854 | 13.9079 | 0.0198613295 | 0.000562433843 | 0.000102312477 | 0.0205260758 |
| common/B/ordinary* | 3 | 19.5150 | 15.2669 | 13.3626 | 0.0203507763 | 0.000621844221 | 0.00100840904 | 0.0219810296 |
| common/B/ordinary* | 4 | 19.2627 | 15.8285 | 13.3219 | 0.0211725456 | 0.000563895261 | 0.000232740685 | 0.0219691815 |
| common/B/ordinary* | 5 | 17.4235 | 12.6872 | 10.1156 | 0.0207911023 | 0.000906317322 | 0.000378493909 | 0.0220759136 |
| common/B/aligned | 2 | 26.3428 | 24.6745 | 22.5830 | 0.0221118154 | 0.000229513204 | 0.000360917162 | 0.0227022458 |
| common/B/aligned | 3 | 26.2207 | 24.4466 | 22.0215 | 0.0220485904 | 0.000294455776 | 0.00043326837 | 0.0227763145 |
| common/B/aligned | 4 | 26.0010 | 24.6175 | 22.3389 | 0.0232528603 | 0.000221751354 | 0.000502829198 | 0.0239774408 |
| common/B/aligned | 5 | 26.0254 | 24.5280 | 22.5098 | 0.0232384624 | 0.000202479186 | 0.000512670588 | 0.0239536122 |
| native/A/ordinary | 2 | 42.8304 | 43.4814 | 44.0023 | 3.5321271e-06 | 2.25261406e-05 | 8.91862092e-07 | 2.69501298e-05 |
| native/A/ordinary | 3 | 43.1152 | 43.8558 | 44.2383 | -2.32678873e-06 | 2.13936523e-05 | -2.6733787e-06 | 1.63934849e-05 |
| native/A/ordinary | 4 | 42.9688 | 43.6279 | 44.0267 | 9.16101314e-05 | 1.85723658e-05 | -2.71311513e-06 | 0.000107469382 |
| native/A/ordinary | 5 | 42.8630 | 43.4489 | 43.9779 | 9.6850925e-05 | 2.03538824e-05 | -6.86115689e-06 | 0.000110343651 |
| native/A/aligned | 2 | 43.4733 | 44.1243 | 44.4092 | 0.000319748013 | 1.51152964e-05 | 6.73311728e-07 | 0.000335536621 |
| native/A/aligned | 3 | 43.3268 | 43.8558 | 44.2383 | 0.000309716772 | 1.33470253e-05 | 2.19433396e-06 | 0.000325258131 |
| native/A/aligned | 4 | 43.1396 | 43.5710 | 43.9453 | 0.000383564719 | 1.05787207e-05 | 7.54109135e-06 | 0.000401684531 |
| native/A/aligned | 5 | 43.3757 | 43.9128 | 44.2627 | 0.000364217493 | 1.26472226e-05 | 4.1657024e-06 | 0.000381030418 |
| native/B/ordinary | 2 | 20.0928 | 15.8854 | 13.7939 | 0.0200496139 | 0.000644076754 | 6.75762141e-05 | 0.0207612669 |
| native/B/ordinary | 3 | 19.8568 | 15.2669 | 13.2406 | 0.0203054878 | 0.000721706284 | 0.000944044855 | 0.021971239 |
| native/B/ordinary | 4 | 19.4336 | 15.8285 | 13.1673 | 0.0210436671 | 0.000630592858 | 0.000226124569 | 0.0219003845 |
| native/B/ordinary | 5 | 17.7409 | 12.6872 | 10.0179 | 0.0208313885 | 0.00101213544 | 0.000325445776 | 0.0221689697 |
| native/B/aligned | 2 | 26.4730 | 24.6745 | 22.2656 | 0.0219575034 | 0.0002872105 | 0.000382092264 | 0.0226268062 |
| native/B/aligned | 3 | 26.4567 | 24.4466 | 21.8180 | 0.0219273413 | 0.000358153273 | 0.000440460664 | 0.0227259552 |
| native/B/aligned | 4 | 26.1312 | 24.6175 | 22.1273 | 0.0229351962 | 0.000264196484 | 0.000496800299 | 0.023696193 |
| native/B/aligned | 5 | 26.1393 | 24.5280 | 22.3145 | 0.0230562797 | 0.000239860128 | 0.000531768357 | 0.0238279082 |

## Immutable data references

External root: /mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1.

Population run: l20_extension1_recipient_repeats_population_v1_attempt1.

Full rows: outputs/<run>/records.json; full fixed summaries: outputs/<run>/summary.json.

COMPLETE SHA-256: 5b171e325d9c9703f58cc937a5a1877bc38e9f11e9032cf3b0823dd2baa4f0b3

Records SHA-256: 5af5ac095fcca27f5b3863fe527a4557a3b99b48a4cf3a4bc72599451e48dd65

Summary SHA-256: 6d51896d99bbdd16c5c4dc6814a3e7f3d932a44bdad48ff6b94e774276554431

D180 summary SHA-256: fd5988933f6105829e7a2e5e7a48131f1de39acafe59f3b92e0208d4c61a7d8b

The source code/inputs are frozen; this rendering tool is downstream documentation
and is not an executor dependency. Audit progress is not inspected. All complete
path-level measurements, including guide addresses, remain externally available.
