# D180 — fixed pilot tables

2026-10-09. Completed pilot; **formal detached audit completion not yet reviewed**.
These describe the frozen outputs, not new simulations or fitted predictors.
[Interpretation and audit launch](PILOT_RESULTS.md); [fixed design](PROPOSAL_V1.md).

All four reused donor blocks, four lives per block and both families remain:
32 F0 records, 1,152 labelled lineages and 2,304 assay rows. Each family/writer/
assay group has 16 records with three recipient settings and two future replicas.
Common-reader B ordinary is focal (marked *); native-reader results are secondary.

Preference points = 100 times terminal own-minus-alternative preference, not
success percentages. Zero means no target preference; negative means preference
for the alternative. Means weight all four blocks/four lives/two replicas equally.
Couplings 0.75/1.0/1.25 are fixed model settings, not biological measurements.
Signed cross-replica components use original squared-score units (not points).
Negative estimates are retained; there are no variance percentages or confidence
intervals. All control cells and contrasts remain in the frozen JSON, even where
common-reader results are exact aliases across settings.

## Absolute preference, including every control

| Assay | Family | Condition | g=0.75 | g=1.0 | g=1.25 | Pooled |
| --- | --- | --- | --- | --- | --- | --- |
| common | A | ordinary | 43.2739 | 43.6768 | 43.8110 | 43.5872 |
| common | A | aligned | 44.4824 | 44.6533 | 44.6289 | 44.5882 |
| common | A | protected_copy | 42.9932 | 42.9932 | 42.9932 | 42.9932 |
| common | A | ordinary_read_off | 13.5742 | 18.2129 | 18.8110 | 16.8660 |
| common | A | aligned_read_off | 18.8843 | 20.2881 | 20.7153 | 19.9626 |
| common | A | write_off | 1.8311 | 1.8311 | 1.8311 | 1.8311 |
| common | B | ordinary | 19.3848 | 15.8325 | 13.5010 | 16.2394 |
| common | B | aligned | 25.7568 | 24.7803 | 22.8271 | 24.4548 |
| common | B | protected_copy | 28.0762 | 28.0762 | 28.0762 | 28.0762 |
| common | B | ordinary_read_off | -13.5742 | -18.2129 | -18.8110 | -16.8660 |
| common | B | aligned_read_off | -18.8843 | -20.2881 | -20.7153 | -19.9626 |
| common | B | write_off | -1.8311 | -1.8311 | -1.8311 | -1.8311 |
| native | A | ordinary | 42.6880 | 43.6768 | 44.0430 | 43.4692 |
| native | A | aligned | 43.8599 | 44.6533 | 44.8242 | 44.4458 |
| native | A | protected_copy | 42.3340 | 42.9932 | 43.2739 | 42.8670 |
| native | A | ordinary_read_off | 12.9517 | 18.2129 | 18.8599 | 16.6748 |
| native | A | aligned_read_off | 18.4692 | 20.2881 | 20.9229 | 19.8934 |
| native | A | write_off | 0.6226 | 1.8311 | 1.3428 | 1.2655 |
| native | B | ordinary | 19.5679 | 15.8325 | 13.4399 | 16.2801 |
| native | B | aligned | 25.5615 | 24.7803 | 22.6685 | 24.3368 |
| native | B | protected_copy | 28.2104 | 28.0762 | 27.9053 | 28.0640 |
| native | B | ordinary_read_off | -12.9517 | -18.2129 | -18.8599 | -16.6748 |
| native | B | aligned_read_off | -18.4692 | -20.2881 | -20.9229 | -19.8934 |
| native | B | write_off | -0.6226 | -1.8311 | -1.3428 | -1.2655 |

## All five fixed control contrasts, preference points

| Assay | Family | Contrast | g=0.75 | g=1.0 | g=1.25 | Pooled |
| --- | --- | --- | --- | --- | --- | --- |
| common | A | protected_copy minus write_off | 41.1621 | 41.1621 | 41.1621 | 41.1621 |
| common | A | ordinary minus ordinary_read_off | 29.6997 | 25.4639 | 25.0000 | 26.7212 |
| common | A | ordinary minus write_off | 41.4429 | 41.8457 | 41.9800 | 41.7562 |
| common | A | aligned minus aligned_read_off | 25.5981 | 24.3652 | 23.9136 | 24.6257 |
| common | A | aligned minus write_off | 42.6514 | 42.8223 | 42.7979 | 42.7572 |
| common | B | protected_copy minus write_off | 29.9072 | 29.9072 | 29.9072 | 29.9072 |
| common | B | ordinary minus ordinary_read_off | 32.9590 | 34.0454 | 32.3120 | 33.1055 |
| common | B | ordinary minus write_off | 21.2158 | 17.6636 | 15.3320 | 18.0705 |
| common | B | aligned minus aligned_read_off | 44.6411 | 45.0684 | 43.5425 | 44.4173 |
| common | B | aligned minus write_off | 27.5879 | 26.6113 | 24.6582 | 26.2858 |
| native | A | protected_copy minus write_off | 41.7114 | 41.1621 | 41.9312 | 41.6016 |
| native | A | ordinary minus ordinary_read_off | 29.7363 | 25.4639 | 25.1831 | 26.7944 |
| native | A | ordinary minus write_off | 42.0654 | 41.8457 | 42.7002 | 42.2038 |
| native | A | aligned minus aligned_read_off | 25.3906 | 24.3652 | 23.9014 | 24.5524 |
| native | A | aligned minus write_off | 43.2373 | 42.8223 | 43.4814 | 43.1803 |
| native | B | protected_copy minus write_off | 28.8330 | 29.9072 | 29.2480 | 29.3294 |
| native | B | ordinary minus ordinary_read_off | 32.5195 | 34.0454 | 32.2998 | 32.9549 |
| native | B | ordinary minus write_off | 20.1904 | 17.6636 | 14.7827 | 17.5456 |
| native | B | aligned minus aligned_read_off | 44.0308 | 45.0684 | 43.5913 | 44.2301 |
| native | B | aligned minus write_off | 26.1841 | 26.6113 | 24.0112 | 25.6022 |

## Signed cross-replica components

| Group | Record | Recipient | Interaction | Total |
| --- | --- | --- | --- | --- |
| common/A/ordinary | -0.000189668602 | -1.4702479e-06 | -4.14583418e-06 | -0.000195284684 |
| common/A/aligned | 0.000401814779 | 3.17891439e-07 | -3.17891439e-07 | 0.000401814779 |
| common/B/ordinary* | 0.0185439454 | 0.000580582354 | -0.000292466746 | 0.018832061 |
| common/B/aligned | 0.0194625325 | 0.000134110451 | 0.000404609574 | 0.0200012525 |
| native/A/ordinary | -0.000159568257 | 3.09613016e-05 | 1.67555279e-06 | -0.000126931402 |
| native/A/aligned | 0.000365893046 | 1.73118379e-05 | 6.95387522e-06 | 0.000390158759 |
| native/B/ordinary | 0.0184555451 | 0.000632855627 | -0.000244498253 | 0.0188439025 |
| native/B/aligned | 0.019309375 | 0.000143210093 | 0.000387138791 | 0.0198397239 |

## Separate-replica nonnegative partitions

| Group | Replica | Mean points | Record | Recipient | Interaction | Total |
| --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 0 | 43.4489 | 0.00127129422 | 2.36166848e-05 | 3.52991952e-05 | 0.0013302101 |
| common/A/ordinary | 1 | 43.7256 | 0.000509096517 | 1.58945719e-07 | 5.93927171e-05 | 0.000568648179 |
| common/A/aligned | 0 | 44.7266 | 0.000615437826 | 6.35782878e-07 | 2.22524007e-05 | 0.000638326009 |
| common/A/aligned | 1 | 44.4499 | 0.000485287772 | 1.00665622e-06 | 4.01073032e-05 | 0.000526401732 |
| common/B/ordinary* | 0 | 14.5915 | 0.0437904927 | 0.000683082475 | 0.00141182211 | 0.0458853973 |
| common/B/ordinary* | 1 | 17.8874 | 0.0303566986 | 0.000496798091 | 0.00145569113 | 0.0323091878 |
| common/B/aligned | 0 | 24.2025 | 0.0216719045 | 0.000252657466 | 0.000866320398 | 0.0227908823 |
| common/B/aligned | 1 | 24.7070 | 0.020485878 | 7.25189845e-05 | 0.00110240777 | 0.0216608047 |
| native/A/ordinary | 0 | 43.4001 | 0.00130117602 | 4.97632556e-05 | 4.28491169e-05 | 0.00139378839 |
| native/A/ordinary | 1 | 43.5384 | 0.00049800343 | 1.93251504e-05 | 5.73926502e-05 | 0.00057472123 |
| native/A/aligned | 0 | 44.4906 | 0.000616437859 | 2.29014291e-05 | 4.30080626e-05 | 0.000682347351 |
| native/A/aligned | 1 | 44.4010 | 0.000446955363 | 1.30865309e-05 | 5.19752502e-05 | 0.000512017144 |
| native/B/ordinary | 0 | 14.6077 | 0.0434242288 | 0.000715268983 | 0.00160046419 | 0.045739962 |
| native/B/ordinary | 1 | 17.9525 | 0.0303018093 | 0.000562522146 | 0.00135330359 | 0.032217635 |
| native/B/aligned | 0 | 24.1130 | 0.0214104586 | 0.000213834975 | 0.00105773078 | 0.0226820244 |
| native/B/aligned | 1 | 24.5605 | 0.0205669138 | 9.70760981e-05 | 0.00116029051 | 0.0218242804 |

## Record ranking across recipient settings

| Group | Pair | Spearman | Reversed | Unchanged | Tied | Replica-consistent reversal |
| --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 0.75 vs 1.0 | 0.933726 | 8 | 110 | 2 | 0 |
| common/A/ordinary | 0.75 vs 1.25 | 0.775812 | 21 | 95 | 4 | 3 |
| common/A/ordinary | 1.0 vs 1.25 | 0.873895 | 17 | 99 | 4 | 0 |
| common/A/aligned | 0.75 vs 1.0 | 0.956522 | 8 | 109 | 3 | 0 |
| common/A/aligned | 0.75 vs 1.25 | 0.938099 | 10 | 107 | 3 | 0 |
| common/A/aligned | 1.0 vs 1.25 | 0.977876 | 4 | 112 | 4 | 0 |
| common/B/ordinary* | 0.75 vs 1.0 | 0.977189 | 5 | 114 | 1 | 0 |
| common/B/ordinary* | 0.75 vs 1.25 | 0.897568 | 12 | 105 | 3 | 0 |
| common/B/ordinary* | 1.0 vs 1.25 | 0.917527 | 13 | 105 | 2 | 0 |
| common/B/aligned | 0.75 vs 1.0 | 0.973456 | 6 | 111 | 3 | 1 |
| common/B/aligned | 0.75 vs 1.25 | 0.925464 | 10 | 106 | 4 | 3 |
| common/B/aligned | 1.0 vs 1.25 | 0.956586 | 8 | 111 | 1 | 0 |
| native/A/ordinary | 0.75 vs 1.0 | 0.880532 | 13 | 103 | 4 | 0 |
| native/A/ordinary | 0.75 vs 1.25 | 0.791268 | 18 | 94 | 8 | 0 |
| native/A/ordinary | 1.0 vs 1.25 | 0.918705 | 12 | 102 | 6 | 0 |
| native/A/aligned | 0.75 vs 1.0 | 0.943871 | 9 | 106 | 5 | 0 |
| native/A/aligned | 0.75 vs 1.25 | 0.862426 | 14 | 99 | 7 | 2 |
| native/A/aligned | 1.0 vs 1.25 | 0.949041 | 7 | 107 | 6 | 0 |
| native/B/ordinary | 0.75 vs 1.0 | 0.979412 | 5 | 115 | 0 | 1 |
| native/B/ordinary | 0.75 vs 1.25 | 0.898381 | 12 | 106 | 2 | 1 |
| native/B/ordinary | 1.0 vs 1.25 | 0.927836 | 11 | 107 | 2 | 0 |
| native/B/aligned | 0.75 vs 1.0 | 0.975718 | 6 | 113 | 1 | 0 |
| native/B/aligned | 0.75 vs 1.25 | 0.928624 | 11 | 108 | 1 | 1 |
| native/B/aligned | 1.0 vs 1.25 | 0.952941 | 9 | 111 | 0 | 0 |

Each row compares 120 correlated record pairs, not 120 independent trials.
Replica-consistent reversal requires both futures to agree within each setting
and disagree between settings. Counts from different setting pairs overlap.

## Record shape and guide recognition, pooled over settings

| Family | Condition | F0 own corr | F3 own corr | F0 own-alt corr | F3 own-alt corr | Guide correct |
| --- | --- | --- | --- | --- | --- | --- |
| A | ordinary | 0.935126 | 0.936038 | 0.920808 | 0.917333 | 96/96 |
| A | aligned | 0.935126 | 0.953049 | 0.920808 | 0.941644 | 96/96 |
| A | protected_copy | 0.935126 | 0.935126 | 0.920808 | 0.920808 | 96/96 |
| A | ordinary_read_off | 0.935126 | 0.406100 | 0.920808 | 0.294100 | 81/96 |
| A | aligned_read_off | 0.935126 | 0.458356 | 0.920808 | 0.346931 | 90/96 |
| A | write_off | 0.935126 | 0.000000 | 0.920808 | 0.000000 | 0/96 |
| B | ordinary | 0.794609 | 0.524722 | 0.696171 | 0.353833 | 81/96 |
| B | aligned | 0.794609 | 0.650611 | 0.696171 | 0.509138 | 93/96 |
| B | protected_copy | 0.794609 | 0.794609 | 0.696171 | 0.696171 | 96/96 |
| B | ordinary_read_off | 0.794609 | 0.112000 | 0.696171 | -0.294100 | 15/96 |
| B | aligned_read_off | 0.794609 | 0.111425 | 0.696171 | -0.346931 | 6/96 |
| B | write_off | 0.794609 | 0.000000 | 0.696171 | 0.000000 | 0/96 |

Shape and terminal-guide values are identical for common/native assays of the
same packet; shown once to avoid presenting aliases as extra evidence. Counts
are labelled paths, not independent records. Correct labels do not establish
complete shape preservation. Zero write-off records use the fixed zero-correlation
convention and an unassigned guide family.

## Mandatory terminal-body diagnostics

| Assay | Family | Condition | Mean RMS | Mean clipped sites % | Maximum clipped sites % |
| --- | --- | --- | --- | --- | --- |
| common | A | ordinary | 0.971563 | 0.048828 | 0.390625 |
| common | A | aligned | 0.976466 | 0.048828 | 0.390625 |
| common | A | protected_copy | 0.972322 | 0.048828 | 0.390625 |
| common | A | ordinary_read_off | 0.943173 | 0.065104 | 0.390625 |
| common | A | aligned_read_off | 0.945098 | 0.061035 | 0.390625 |
| common | A | write_off | 0.732342 | 0.000000 | 0.000000 |
| common | B | ordinary | 0.934576 | 0.077311 | 0.390625 |
| common | B | aligned | 0.928871 | 0.040690 | 0.390625 |
| common | B | protected_copy | 0.911741 | 0.048828 | 0.390625 |
| common | B | ordinary_read_off | 0.943173 | 0.065104 | 0.390625 |
| common | B | aligned_read_off | 0.945098 | 0.061035 | 0.390625 |
| common | B | write_off | 0.732342 | 0.000000 | 0.000000 |
| native | A | ordinary | 0.971409 | 0.044759 | 0.390625 |
| native | A | aligned | 0.976350 | 0.052897 | 0.390625 |
| native | A | protected_copy | 0.972177 | 0.052897 | 0.390625 |
| native | A | ordinary_read_off | 0.943762 | 0.065104 | 0.390625 |
| native | A | aligned_read_off | 0.946234 | 0.061035 | 0.390625 |
| native | A | write_off | 0.735412 | 0.000000 | 0.000000 |
| native | B | ordinary | 0.935329 | 0.085449 | 0.390625 |
| native | B | aligned | 0.929534 | 0.040690 | 0.390625 |
| native | B | protected_copy | 0.911966 | 0.048828 | 0.390625 |
| native | B | ordinary_read_off | 0.943762 | 0.065104 | 0.390625 |
| native | B | aligned_read_off | 0.946234 | 0.061035 | 0.390625 |
| native | B | write_off | 0.735412 | 0.000000 | 0.000000 |

## Every donor block, all groups

| Group | Donor | g=0.75 points | g=1.0 points | g=1.25 points | Record | Recipient | Interaction | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 90000 | 44.2871 | 44.4824 | 44.6777 | -8.64664714e-05 | -2.11927626e-07 | -1.33514404e-05 | -0.000100029839 |
| common/A/ordinary | 90005 | 42.6758 | 42.7734 | 42.4805 | 0.00022761027 | -3.94185384e-05 | 1.27156576e-06 | 0.000189463298 |
| common/A/ordinary | 90010 | 43.7500 | 43.9941 | 44.1406 | -6.88764784e-05 | -4.76837158e-06 | 6.88764784e-06 | -6.67572021e-05 |
| common/A/ordinary | 90015 | 42.3828 | 43.4570 | 43.9453 | -0.000162442525 | 2.64909532e-05 | 6.35782878e-07 | -0.000135315789 |
| common/A/aligned | 90000 | 43.8965 | 43.6523 | 43.3105 | -8.79499647e-06 | 3.49680583e-06 | -1.66363186e-05 | -2.19345093e-05 |
| common/A/aligned | 90005 | 43.2617 | 43.4570 | 43.3594 | 0.000851631165 | -8.47710503e-07 | 1.27156576e-06 | 0.00085205502 |
| common/A/aligned | 90010 | 45.6055 | 45.7031 | 46.0449 | 0.000112745497 | 2.54313151e-06 | 6.78168403e-06 | 0.000122070312 |
| common/A/aligned | 90015 | 45.1660 | 45.8008 | 45.8008 | 0.000288645426 | 4.66240777e-06 | -1.27156576e-06 | 0.000292036268 |
| common/B/ordinary* | 90000 | 25.0488 | 20.2148 | 14.2578 | 0.00159623888 | 0.00181484222 | -0.00163216061 | 0.00177892049 |
| common/B/ordinary* | 90005 | 24.2676 | 19.9707 | 19.1406 | 0.00895436605 | 0.00010172526 | 3.94185384e-05 | 0.00909550985 |
| common/B/ordinary* | 90010 | 8.8867 | 8.3008 | 8.1543 | 0.0194979774 | -4.25974528e-05 | -2.01331245e-05 | 0.0194352468 |
| common/B/ordinary* | 90015 | 19.3359 | 14.8438 | 12.4512 | 0.0412114461 | 0.000754038493 | 0.000137329102 | 0.0421028137 |
| common/B/aligned | 90000 | 30.0781 | 27.2949 | 22.9492 | 0.00911076864 | 0.000615437826 | 0.000171661377 | 0.00989786784 |
| common/B/aligned | 90005 | 32.7148 | 32.8613 | 32.5684 | 0.0115822686 | -2.19345093e-05 | 8.46650865e-05 | 0.0116449992 |
| common/B/aligned | 90010 | 13.5742 | 13.9648 | 15.0391 | 0.0233413908 | 1.20798747e-05 | 0.000109142727 | 0.0234626134 |
| common/B/aligned | 90015 | 26.6602 | 25.0000 | 20.7520 | 0.0169798533 | 0.000580151876 | 0.000603675842 | 0.018163681 |
| native/A/ordinary | 90000 | 43.5059 | 44.4824 | 44.7754 | -0.000124189589 | 2.67028809e-05 | 7.20553928e-06 | -9.02811686e-05 |
| native/A/ordinary | 90005 | 42.2363 | 42.7734 | 42.9199 | 0.000247531467 | -1.05963813e-05 | 6.78168403e-06 | 0.00024371677 |
| native/A/ordinary | 90010 | 43.3594 | 43.9941 | 44.4824 | 6.65452745e-05 | 6.35782878e-07 | -7.41746691e-06 | 5.97635905e-05 |
| native/A/ordinary | 90015 | 41.6504 | 43.4570 | 43.9941 | -0.000100347731 | 8.98573134e-05 | 1.73780653e-05 | 6.88764784e-06 |
| native/A/aligned | 90000 | 43.1152 | 43.6523 | 43.4570 | -2.88221571e-05 | -4.02662489e-06 | -1.37752957e-05 | -4.66240777e-05 |
| native/A/aligned | 90005 | 42.8711 | 43.4570 | 43.6523 | 0.000756581624 | 1.08083089e-05 | 1.90734863e-06 | 0.000769297282 |
| native/A/aligned | 90010 | 44.8242 | 45.7031 | 46.3867 | 0.000148031447 | 4.00543213e-05 | 2.64909532e-05 | 0.000214576721 |
| native/A/aligned | 90015 | 44.6289 | 45.8008 | 45.8008 | 0.000264485677 | 2.86102295e-05 | 6.99361165e-06 | 0.000300089518 |
| native/B/ordinary | 90000 | 25.0488 | 20.2148 | 13.7207 | 0.00135093265 | 0.00204118093 | -0.00150924259 | 0.00188287099 |
| native/B/ordinary | 90005 | 24.9512 | 19.9707 | 19.3359 | 0.00913630591 | 0.000189781189 | 1.45170424e-05 | 0.00934060415 |
| native/B/ordinary | 90010 | 8.9355 | 8.3008 | 8.2520 | 0.0187848409 | -1.35633681e-05 | -6.86645508e-05 | 0.018702613 |
| native/B/ordinary | 90015 | 19.3359 | 14.8438 | 12.4512 | 0.0413248274 | 0.000747362773 | 0.000152058072 | 0.0422242483 |
| native/B/aligned | 90000 | 29.7852 | 27.2949 | 22.8027 | 0.00884257423 | 0.000609079997 | -4.11139594e-05 | 0.00941054026 |
| native/B/aligned | 90005 | 32.5195 | 32.8613 | 32.5684 | 0.0120382309 | -1.71661377e-05 | 0.000132878621 | 0.0121539434 |
| native/B/aligned | 90010 | 13.2812 | 13.9648 | 14.8926 | 0.0224367778 | 1.58945719e-05 | 0.000137964884 | 0.0225906372 |
| native/B/aligned | 90015 | 26.6602 | 25.0000 | 20.4102 | 0.0170699226 | 0.000650405884 | 0.000633451674 | 0.0183537801 |

## Every leave-one-donor description

| Group | Omitted | g=0.75 points | g=1.0 points | g=1.25 points | Record | Recipient | Interaction | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common/A/ordinary | 90000 | 42.9362 | 43.4082 | 43.5221 | -0.000259446509 | -2.20169256e-06 | -7.65294205e-07 | -0.000262413496 |
| common/A/ordinary | 90005 | 43.4733 | 43.9779 | 44.2546 | -0.000108730646 | 8.00615476e-06 | -2.77860665e-06 | -0.000103503098 |
| common/A/ordinary | 90010 | 43.1152 | 43.5710 | 43.7012 | -0.000187179189 | -9.01869786e-06 | 8.24162989e-07 | -0.000195373724 |
| common/A/ordinary | 90015 | 43.5710 | 43.7500 | 43.7663 | -0.000129040377 | -4.00307738e-06 | -1.25272774e-05 | -0.000145570731 |
| common/A/aligned | 90000 | 44.6777 | 44.9870 | 45.0684 | 0.000502963125 | 1.96621742e-06 | 2.41362018e-06 | 0.000507342963 |
| common/A/aligned | 90005 | 44.8893 | 45.0521 | 45.0521 | 0.000205039978 | 4.94497794e-07 | -6.35782878e-07 | 0.000204898693 |
| common/A/aligned | 90010 | 44.1081 | 44.3034 | 44.1569 | 0.000456845319 | 5.65140336e-07 | -3.67341218e-06 | 0.000453737047 |
| common/A/aligned | 90015 | 44.2546 | 44.2708 | 44.2383 | 0.000402073801 | -8.00615476e-07 | -3.29665196e-07 | 0.000400943521 |
| common/B/ordinary* | 90000 | 17.4967 | 14.3717 | 13.2487 | 0.0237127351 | 0.000279720919 | 4.35393534e-05 | 0.0240359954 |
| common/B/ordinary* | 90005 | 17.7572 | 14.4531 | 11.6211 | 0.022607874 | 0.000613495156 | -0.000276388945 | 0.0229449802 |
| common/B/ordinary* | 90010 | 22.8841 | 18.3431 | 15.2832 | 0.016560684 | 0.000974855305 | -0.00056979097 | 0.0169657484 |
| common/B/ordinary* | 90015 | 19.4010 | 16.1621 | 13.8509 | 0.010970516 | 0.000488222381 | -0.00040119077 | 0.0110575476 |
| common/B/aligned | 90000 | 24.3164 | 23.9421 | 22.7865 | 0.022679482 | 4.04193078e-05 | 0.000415507658 | 0.0231354089 |
| common/B/aligned | 90005 | 23.4375 | 22.0866 | 19.5801 | 0.0190593578 | 0.000241632815 | 0.000455750359 | 0.019756741 |
| common/B/aligned | 90010 | 29.8177 | 28.3854 | 25.4232 | 0.0137812179 | 0.000310638804 | 0.000367247028 | 0.0144591037 |
| common/B/aligned | 90015 | 25.4557 | 24.7070 | 23.5189 | 0.0204594224 | 1.58945719e-05 | 0.000307789555 | 0.0207831065 |
| native/A/ordinary | 90000 | 42.4154 | 43.4082 | 43.7988 | -0.000198446674 | 3.19892977e-05 | 2.23701383e-07 | -0.000166233675 |
| native/A/ordinary | 90005 | 42.8385 | 43.9779 | 44.4173 | -6.68278447e-05 | 4.3798376e-05 | 9.88995587e-07 | -2.20404731e-05 |
| native/A/ordinary | 90010 | 42.4642 | 43.5710 | 43.8965 | -0.000190970338 | 2.82334693e-05 | 1.75428979e-05 | -0.000145193971 |
| native/A/ordinary | 90015 | 43.0339 | 43.7500 | 44.0592 | -0.00010116012 | 1.79078844e-05 | -1.01372048e-05 | -9.33894405e-05 |
| native/A/aligned | 90000 | 44.1081 | 44.9870 | 45.2799 | 0.000455185219 | 2.47248897e-05 | 1.35633681e-05 | 0.000493473477 |
| native/A/aligned | 90005 | 44.1895 | 45.0521 | 45.2148 | 0.00020203767 | 1.95326629e-05 | 8.58306885e-06 | 0.000230153402 |
| native/A/aligned | 90010 | 43.5384 | 44.3034 | 44.3034 | 0.00040332182 | 1.27745263e-05 | -2.6020003e-06 | 0.000413494346 |
| native/A/aligned | 90015 | 43.6035 | 44.2708 | 44.4987 | 0.000367105743 | 1.29040377e-05 | 7.5822995e-06 | 0.00038759208 |
| native/B/ordinary | 90000 | 17.7409 | 14.3717 | 13.3464 | 0.0237182806 | 0.000318715602 | 2.17814504e-05 | 0.0240587776 |
| native/B/ordinary | 90005 | 17.7734 | 14.4531 | 11.4746 | 0.0222648809 | 0.00063907953 | -0.000189369107 | 0.0227145913 |
| native/B/ordinary | 90010 | 23.1120 | 18.3431 | 15.1693 | 0.0166618912 | 0.00106504228 | -0.000519823145 | 0.0172071104 |
| native/B/ordinary | 90015 | 19.6452 | 16.1621 | 13.7695 | 0.010818764 | 0.000556733873 | -0.000338730989 | 0.0110367669 |
| native/B/aligned | 90000 | 24.1536 | 23.9421 | 22.6237 | 0.0225698918 | 3.9971905e-05 | 0.000477837928 | 0.0230877017 |
| native/B/aligned | 90005 | 23.2422 | 22.0866 | 19.3685 | 0.0186641128 | 0.000259470057 | 0.00040909096 | 0.0193326738 |
| native/B/aligned | 90010 | 29.6549 | 28.3854 | 25.2604 | 0.013880035 | 0.000325002788 | 0.000330842571 | 0.0145358804 |
| native/B/aligned | 90015 | 25.1953 | 24.7070 | 23.4212 | 0.0202512388 | 2.45482833e-05 | 0.000254631042 | 0.0205304181 |

These are descriptive sensitivity checks, not independent replications or
population intervals. Within-donor lives are not independent founders.

## Complete machine-readable evidence

External run root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recipient_coupling_pilot_v1_attempt1`

- [Frozen summary](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recipient_coupling_pilot_v1_attempt1/summary.json): all eight groups, 32 donor summaries,
  32 omissions, 24 ranking comparisons, 576 absolute condition cells and 480 contrasts.
- [All assay rows](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/outputs/l20_extension1_recipient_coupling_pilot_v1_attempt1/records.json): 2,304 rows, no exclusions.
- Four `block_<id>/` directories retain all 16 NPZ/JSON life pairs.
- [Completion receipt](/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/runs/l20_extension1_recipient_coupling_pilot_v1_attempt1/COMPLETE.json): all 34 output hashes and replay proof.

Only this documentation is local. Numerical files and receipts remain on /mnt/bioIce1.
