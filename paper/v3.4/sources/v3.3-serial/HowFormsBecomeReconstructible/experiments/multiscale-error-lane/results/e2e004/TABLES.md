# E2E004 tables: development

Endpoints (e2e001.sim.score, unchanged): q_r SR001's history specificity; u_r and u_v the record's and the successor body's agreement inside the injury patch, relative to the sheet's own orientation; a_r whole-sheet inversion-invariant agreement. g 0 is the restored record at t = 8,000. Routes: body (the body's co-activity), vote (vote2r with a second copy), record (the record keeping itself, with parity), vote1 (vote2r, the second copy abstaining). Packets: protected (R0) and post (the injured record). Item sets: native / particular (li4 x F0) / permissive.

## The statement candidates

| Id | Part | Value [95%] | SD (block, case) | Halves | Narrowest | Threshold | | Tasks | Aliased | native | particular | permissive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 | the vote keeps more history than the body route: q_r(vote/protected) - q_r(body/protected), g 8 | +0.2262 [+0.2134, +0.2390] | 0.0241 (0.0241, 0.0133) | +0.2349, +0.2175 | 0.18 | 0.18 | HOLDS | 128 of 128 | 0 | +0.1862 | +0.5044 | +0.1071 |
| G2 | the body route heals an inherited error more: u_r(body/post) - u_r(vote/post), g 8 | +0.3297 [+0.3059, +0.3535] | 0.0446 (0.0394, 0.0446) | +0.3262, +0.3333 | 0.25 | 0.2 | HOLDS | 128 of 128 | 0 | +0.4048 | +0.1414 | +0.3864 |
| G3 | the record route against the vote, keeping: q_r(record/protected) - q_r(vote/protected), g 8 | +0.2412 [+0.2338, +0.2486] | 0.0139 (0.0139, 0.0105) | +0.2479, +0.2346 | [0.21, 0.27] | [0.19, 0.27] | HOLDS | 128 of 128 | 0 | +0.2713 | +0.3274 | +0.1831 |
| G4 | the record route against the vote, healing: u_r(record/post) - u_r(vote/post), g 8 | -0.1687 [-0.1840, -0.1534] | 0.0288 (0.0160, 0.0288) | -0.1752, -0.1622 | [-0.22, -0.12] | [-0.28, -0.1] | HOLDS | 128 of 128 | 0 | -0.2458 | -0.1035 | -0.1627 |

## The trade-off reading (g 8), every route run (the plan's declared reading): the route that keeps the most history heals the least

| Set | q_r(protected) by route | u_r(post) by route | order by keeping (most first) | order by healing (least first) | reversed |
|---|---|---|---|---|---|
| particular | body 0.167, vote 0.671, record 0.998, vote1 0.362 | body 0.247, vote 0.106, record 0.002, vote1 0.290 | record > vote > vote1 > body | record < vote < body < vote1 | no |
| all | body 0.531, vote 0.757, record 0.998, vote1 0.404 | body 0.501, vote 0.171, record 0.002, vote1 0.365 | record > vote > body > vote1 | record < vote < vote1 < body | no |
| native | body 0.541, vote 0.727, record 0.998, vote1 0.403 | body 0.653, vote 0.248, record 0.002, vote1 0.394 | record > vote > body > vote1 | record < vote < vote1 < body | no |
| permissive | body 0.708, vote 0.815, record 0.998, vote1 0.425 | body 0.552, vote 0.165, record 0.002, vote1 0.387 | record > vote > body > vote1 | record < vote < vote1 < body | no |

## The trade-off reading (g 8), AR001's three fixed policies, body, vote and record (added to the reader after P60's values): the route that keeps the most history heals the least

| Set | q_r(protected) by route | u_r(post) by route | order by keeping (most first) | order by healing (least first) | reversed |
|---|---|---|---|---|---|
| particular | body 0.167, vote 0.671, record 0.998 | body 0.247, vote 0.106, record 0.002 | record > vote > body | record < vote < body | yes |
| all | body 0.531, vote 0.757, record 0.998 | body 0.501, vote 0.171, record 0.002 | record > vote > body | record < vote < body | yes |
| native | body 0.541, vote 0.727, record 0.998 | body 0.653, vote 0.248, record 0.002 | record > vote > body | record < vote < body | yes |
| permissive | body 0.708, vote 0.815, record 0.998 | body 0.552, vote 0.165, record 0.002 | record > vote > body | record < vote < body | yes |

## Reported contrasts

| Id | Part | Value [95%] | Halves | Tasks | native | particular | permissive |
|---|---|---|---|---|---|---|---|
| R-keep-vb-q_r-1 | q_r(vote/protected) - q_r(body/protected), g 1 | +0.0693 [+0.0553, +0.0833] | +0.0768, +0.0618 | 128 of 128 | +0.0726 | +0.1228 | +0.0409 |
| R-keep-rv-q_r-1 | q_r(record/protected) - q_r(vote/protected), g 1 | +0.0345 [+0.0319, +0.0371] | +0.0371, +0.0318 | 128 of 128 | +0.0374 | +0.0433 | +0.0286 |
| R-keep-v1v-q_r-1 | q_r(vote1/protected) - q_r(vote/protected), g 1 (the second copy) | -0.0483 [-0.0514, -0.0452] | -0.0497, -0.0469 | 128 of 128 | -0.0432 | -0.0498 | -0.0501 |
| R-keep-v1b-q_r-1 | q_r(vote1/protected) - q_r(body/protected), g 1 | +0.0210 [+0.0076, +0.0344] | +0.0271, +0.0149 | 128 of 128 | +0.0294 | +0.0730 | -0.0092 |
| R-keep-vb-u_r-1 | u_r(vote/protected) - u_r(body/protected), g 1 | +0.0311 [+0.0247, +0.0375] | +0.0331, +0.0291 | 128 of 128 | +0.0156 | +0.0911 | +0.0088 |
| R-keep-rv-u_r-1 | u_r(record/protected) - u_r(vote/protected), g 1 | +0.0103 [+0.0061, +0.0144] | +0.0118, +0.0087 | 128 of 128 | +0.0107 | +0.0137 | +0.0083 |
| R-keep-v1v-u_r-1 | u_r(vote1/protected) - u_r(vote/protected), g 1 (the second copy) | -0.0225 [-0.0315, -0.0136] | -0.0292, -0.0159 | 128 of 128 | -0.0222 | -0.0237 | -0.0221 |
| R-keep-v1b-u_r-1 | u_r(vote1/protected) - u_r(body/protected), g 1 | +0.0085 [-0.0014, +0.0185] | +0.0039, +0.0132 | 128 of 128 | -0.0066 | +0.0674 | -0.0133 |
| R-keep-vb-u_v-1 | u_v(vote/protected) - u_v(body/protected), g 1 | +0.0101 [+0.0033, +0.0170] | +0.0140, +0.0062 | 128 of 128 | +0.0100 | +0.0195 | +0.0055 |
| R-keep-rv-u_v-1 | u_v(record/protected) - u_v(vote/protected), g 1 | +0.0047 [-0.0013, +0.0107] | +0.0100, -0.0006 | 128 of 128 | +0.0042 | +0.0093 | +0.0027 |
| R-keep-v1v-u_v-1 | u_v(vote1/protected) - u_v(vote/protected), g 1 (the second copy) | -0.0048 [-0.0116, +0.0021] | -0.0096, +0.0001 | 128 of 128 | -0.0051 | -0.0063 | -0.0038 |
| R-keep-v1b-u_v-1 | u_v(vote1/protected) - u_v(body/protected), g 1 | +0.0054 [-0.0021, +0.0129] | +0.0044, +0.0063 | 128 of 128 | +0.0049 | +0.0132 | +0.0017 |
| R-heal-bv-u_r-1 | u_r(body/post) - u_r(vote/post), g 1 | +0.2058 [+0.1833, +0.2283] | +0.2111, +0.2006 | 128 of 128 | +0.2085 | +0.0798 | +0.2675 |
| R-heal-rv-u_r-1 | u_r(record/post) - u_r(vote/post), g 1 | -0.0173 [-0.0229, -0.0118] | -0.0210, -0.0137 | 128 of 128 | -0.0242 | -0.0112 | -0.0170 |
| R-heal-v1v-u_r-1 | u_r(vote1/post) - u_r(vote/post), g 1 (the second copy) | +0.0264 [+0.0195, +0.0332] | +0.0320, +0.0208 | 128 of 128 | +0.0227 | +0.0266 | +0.0281 |
| R-heal-v1b-u_r-1 | u_r(vote1/post) - u_r(body/post), g 1 | -0.1794 [-0.2005, -0.1584] | -0.1791, -0.1798 | 128 of 128 | -0.1858 | -0.0532 | -0.2394 |
| R-heal-bv-u_v-1 | u_v(body/post) - u_v(vote/post), g 1 | +0.0820 [+0.0678, +0.0962] | +0.0808, +0.0831 | 128 of 128 | +0.1350 | +0.0391 | +0.0769 |
| R-heal-rv-u_v-1 | u_v(record/post) - u_v(vote/post), g 1 | -0.0329 [-0.0413, -0.0245] | -0.0436, -0.0222 | 128 of 128 | -0.0527 | -0.0085 | -0.0352 |
| R-heal-v1v-u_v-1 | u_v(vote1/post) - u_v(vote/post), g 1 (the second copy) | +0.0183 [+0.0065, +0.0301] | +0.0203, +0.0164 | 128 of 128 | +0.0237 | +0.0061 | +0.0217 |
| R-heal-v1b-u_v-1 | u_v(vote1/post) - u_v(body/post), g 1 | -0.0637 [-0.0770, -0.0503] | -0.0605, -0.0668 | 128 of 128 | -0.1113 | -0.0330 | -0.0552 |
| R-heal-bv-q_r-1 | q_r(body/post) - q_r(vote/post), g 1 | -0.0662 [-0.0797, -0.0527] | -0.0730, -0.0594 | 128 of 128 | -0.0696 | -0.1161 | -0.0396 |
| R-heal-rv-q_r-1 | q_r(record/post) - q_r(vote/post), g 1 | +0.0319 [+0.0292, +0.0346] | +0.0336, +0.0303 | 128 of 128 | +0.0374 | +0.0369 | +0.0267 |
| R-heal-v1v-q_r-1 | q_r(vote1/post) - q_r(vote/post), g 1 (the second copy) | -0.0446 [-0.0482, -0.0411] | -0.0459, -0.0434 | 128 of 128 | -0.0419 | -0.0444 | -0.0461 |
| R-heal-v1b-q_r-1 | q_r(vote1/post) - q_r(body/post), g 1 | +0.0216 [+0.0090, +0.0341] | +0.0271, +0.0160 | 128 of 128 | +0.0277 | +0.0717 | -0.0066 |
| R-keep-vb-q_r-3 | q_r(vote/protected) - q_r(body/protected), g 3 | +0.1514 [+0.1321, +0.1707] | +0.1656, +0.1372 | 128 of 128 | +0.1483 | +0.3025 | +0.0774 |
| R-keep-rv-q_r-3 | q_r(record/protected) - q_r(vote/protected), g 3 | +0.1021 [+0.0966, +0.1077] | +0.1055, +0.0987 | 128 of 128 | +0.1148 | +0.1344 | +0.0797 |
| R-keep-v1v-q_r-3 | q_r(vote1/protected) - q_r(vote/protected), g 3 (the second copy) | -0.1631 [-0.1701, -0.1561] | -0.1710, -0.1553 | 128 of 128 | -0.1527 | -0.1586 | -0.1706 |
| R-keep-v1b-q_r-3 | q_r(vote1/protected) - q_r(body/protected), g 3 | -0.0117 [-0.0296, +0.0062] | -0.0053, -0.0181 | 128 of 128 | -0.0044 | +0.1439 | -0.0932 |
| R-keep-vb-u_r-3 | u_r(vote/protected) - u_r(body/protected), g 3 | +0.0699 [+0.0575, +0.0822] | +0.0748, +0.0649 | 128 of 128 | +0.0344 | +0.1973 | +0.0239 |
| R-keep-rv-u_r-3 | u_r(record/protected) - u_r(vote/protected), g 3 | +0.0319 [+0.0225, +0.0413] | +0.0260, +0.0377 | 128 of 128 | +0.0344 | +0.0486 | +0.0222 |
| R-keep-v1v-u_r-3 | u_r(vote1/protected) - u_r(vote/protected), g 3 (the second copy) | -0.0782 [-0.0924, -0.0641] | -0.0848, -0.0717 | 128 of 128 | -0.0684 | -0.1035 | -0.0706 |
| R-keep-v1b-u_r-3 | u_r(vote1/protected) - u_r(body/protected), g 3 | -0.0084 [-0.0268, +0.0101] | -0.0100, -0.0067 | 128 of 128 | -0.0339 | +0.0938 | -0.0466 |
| R-keep-vb-u_v-3 | u_v(vote/protected) - u_v(body/protected), g 3 | +0.0368 [+0.0263, +0.0473] | +0.0463, +0.0273 | 128 of 128 | +0.0327 | +0.0649 | +0.0248 |
| R-keep-rv-u_v-3 | u_v(record/protected) - u_v(vote/protected), g 3 | +0.0147 [+0.0048, +0.0246] | +0.0184, +0.0110 | 128 of 128 | +0.0217 | +0.0134 | +0.0118 |
| R-keep-v1v-u_v-3 | u_v(vote1/protected) - u_v(vote/protected), g 3 (the second copy) | -0.0326 [-0.0451, -0.0201] | -0.0424, -0.0228 | 128 of 128 | -0.0298 | -0.0483 | -0.0261 |
| R-keep-v1b-u_v-3 | u_v(vote1/protected) - u_v(body/protected), g 3 | +0.0042 [-0.0072, +0.0156] | +0.0039, +0.0045 | 128 of 128 | +0.0029 | +0.0166 | -0.0013 |
| R-heal-bv-u_r-3 | u_r(body/post) - u_r(vote/post), g 3 | +0.3268 [+0.3014, +0.3522] | +0.3215, +0.3320 | 128 of 128 | +0.3860 | +0.1189 | +0.4011 |
| R-heal-rv-u_r-3 | u_r(record/post) - u_r(vote/post), g 3 | -0.0651 [-0.0783, -0.0520] | -0.0579, -0.0724 | 128 of 128 | -0.0986 | -0.0396 | -0.0612 |
| R-heal-v1v-u_r-3 | u_r(vote1/post) - u_r(vote/post), g 3 (the second copy) | +0.1133 [+0.0974, +0.1291] | +0.1130, +0.1135 | 128 of 128 | +0.0928 | +0.1011 | +0.1296 |
| R-heal-v1b-u_r-3 | u_r(vote1/post) - u_r(body/post), g 3 | -0.2135 [-0.2374, -0.1896] | -0.2085, -0.2185 | 128 of 128 | -0.2932 | -0.0178 | -0.2715 |
| R-heal-bv-u_v-3 | u_v(body/post) - u_v(vote/post), g 3 | +0.1890 [+0.1707, +0.2072] | +0.1842, +0.1937 | 128 of 128 | +0.2551 | +0.1101 | +0.1953 |
| R-heal-rv-u_v-3 | u_v(record/post) - u_v(vote/post), g 3 | -0.0775 [-0.0931, -0.0619] | -0.0697, -0.0853 | 128 of 128 | -0.1350 | -0.0281 | -0.0735 |
| R-heal-v1v-u_v-3 | u_v(vote1/post) - u_v(vote/post), g 3 (the second copy) | +0.0664 [+0.0493, +0.0835] | +0.0758, +0.0570 | 128 of 128 | +0.0574 | +0.0415 | +0.0834 |
| R-heal-v1b-u_v-3 | u_v(vote1/post) - u_v(body/post), g 3 | -0.1226 [-0.1417, -0.1034] | -0.1084, -0.1367 | 128 of 128 | -0.1978 | -0.0686 | -0.1119 |
| R-heal-bv-q_r-3 | q_r(body/post) - q_r(vote/post), g 3 | -0.1469 [-0.1657, -0.1282] | -0.1575, -0.1363 | 128 of 128 | -0.1436 | -0.2909 | -0.0766 |
| R-heal-rv-q_r-3 | q_r(record/post) - q_r(vote/post), g 3 | +0.0956 [+0.0897, +0.1016] | +0.0992, +0.0920 | 128 of 128 | +0.1133 | +0.1194 | +0.0750 |
| R-heal-v1v-q_r-3 | q_r(vote1/post) - q_r(vote/post), g 3 (the second copy) | -0.1555 [-0.1625, -0.1486] | -0.1619, -0.1492 | 128 of 128 | -0.1465 | -0.1518 | -0.1619 |
| R-heal-v1b-q_r-3 | q_r(vote1/post) - q_r(body/post), g 3 | -0.0086 [-0.0245, +0.0073] | -0.0043, -0.0129 | 128 of 128 | -0.0029 | +0.1392 | -0.0853 |
| R-keep-vb-q_r-8 | q_r(vote/protected) - q_r(body/protected), g 8 | +0.2262 [+0.2134, +0.2390] | +0.2349, +0.2175 | 128 of 128 | +0.1862 | +0.5044 | +0.1071 |
| R-keep-rv-q_r-8 | q_r(record/protected) - q_r(vote/protected), g 8 | +0.2412 [+0.2338, +0.2486] | +0.2479, +0.2346 | 128 of 128 | +0.2713 | +0.3274 | +0.1831 |
| R-keep-v1v-q_r-8 | q_r(vote1/protected) - q_r(vote/protected), g 8 (the second copy) | -0.3535 [-0.3624, -0.3447] | -0.3564, -0.3506 | 128 of 128 | -0.3242 | -0.3086 | -0.3907 |
| R-keep-v1b-q_r-8 | q_r(vote1/protected) - q_r(body/protected), g 8 | -0.1274 [-0.1448, -0.1099] | -0.1215, -0.1332 | 128 of 128 | -0.1380 | +0.1958 | -0.2836 |
| R-keep-vb-u_r-8 | u_r(vote/protected) - u_r(body/protected), g 8 | +0.0987 [+0.0831, +0.1143] | +0.0908, +0.1066 | 128 of 128 | +0.0635 | +0.2585 | +0.0364 |
| R-keep-rv-u_r-8 | u_r(record/protected) - u_r(vote/protected), g 8 | +0.0901 [+0.0783, +0.1019] | +0.0953, +0.0848 | 128 of 128 | +0.0938 | +0.1475 | +0.0596 |
| R-keep-v1v-u_r-8 | u_r(vote1/protected) - u_r(vote/protected), g 8 (the second copy) | -0.1791 [-0.1970, -0.1611] | -0.1884, -0.1698 | 128 of 128 | -0.1528 | -0.2024 | -0.1805 |
| R-keep-v1b-u_r-8 | u_r(vote1/protected) - u_r(body/protected), g 8 | -0.0804 [-0.1012, -0.0596] | -0.0975, -0.0632 | 128 of 128 | -0.0894 | +0.0562 | -0.1442 |
| R-keep-vb-u_v-8 | u_v(vote/protected) - u_v(body/protected), g 8 | +0.0746 [+0.0594, +0.0898] | +0.0709, +0.0782 | 128 of 128 | +0.0750 | +0.1223 | +0.0505 |
| R-keep-rv-u_v-8 | u_v(record/protected) - u_v(vote/protected), g 8 | +0.0502 [+0.0365, +0.0640] | +0.0626, +0.0378 | 128 of 128 | +0.0637 | +0.0693 | +0.0339 |
| R-keep-v1v-u_v-8 | u_v(vote1/protected) - u_v(vote/protected), g 8 (the second copy) | -0.1187 [-0.1370, -0.1003] | -0.1298, -0.1075 | 128 of 128 | -0.1104 | -0.1072 | -0.1285 |
| R-keep-v1b-u_v-8 | u_v(vote1/protected) - u_v(body/protected), g 8 | -0.0441 [-0.0627, -0.0255] | -0.0588, -0.0293 | 128 of 128 | -0.0354 | +0.0151 | -0.0780 |
| R-heal-bv-u_r-8 | u_r(body/post) - u_r(vote/post), g 8 | +0.3297 [+0.3059, +0.3535] | +0.3262, +0.3333 | 128 of 128 | +0.4048 | +0.1414 | +0.3864 |
| R-heal-rv-u_r-8 | u_r(record/post) - u_r(vote/post), g 8 | -0.1687 [-0.1840, -0.1534] | -0.1752, -0.1622 | 128 of 128 | -0.2458 | -0.1035 | -0.1627 |
| R-heal-v1v-u_r-8 | u_r(vote1/post) - u_r(vote/post), g 8 (the second copy) | +0.1934 [+0.1762, +0.2105] | +0.2048, +0.1819 | 128 of 128 | +0.1458 | +0.1838 | +0.2219 |
| R-heal-v1b-u_r-8 | u_r(vote1/post) - u_r(body/post), g 8 | -0.1364 [-0.1672, -0.1055] | -0.1213, -0.1514 | 128 of 128 | -0.2590 | +0.0425 | -0.1644 |
| R-heal-bv-u_v-8 | u_v(body/post) - u_v(vote/post), g 8 | +0.1986 [+0.1785, +0.2187] | +0.1981, +0.1991 | 128 of 128 | +0.2893 | +0.1519 | +0.1766 |
| R-heal-rv-u_v-8 | u_v(record/post) - u_v(vote/post), g 8 | -0.1660 [-0.1861, -0.1458] | -0.1732, -0.1587 | 128 of 128 | -0.2534 | -0.0742 | -0.1681 |
| R-heal-v1v-u_v-8 | u_v(vote1/post) - u_v(vote/post), g 8 (the second copy) | +0.0992 [+0.0748, +0.1237] | +0.1023, +0.0962 | 128 of 128 | +0.0825 | +0.1360 | +0.0892 |
| R-heal-v1b-u_v-8 | u_v(vote1/post) - u_v(body/post), g 8 | -0.0994 [-0.1273, -0.0714] | -0.0958, -0.1029 | 128 of 128 | -0.2068 | -0.0159 | -0.0874 |
| R-heal-bv-q_r-8 | q_r(body/post) - q_r(vote/post), g 8 | -0.2210 [-0.2332, -0.2088] | -0.2278, -0.2141 | 128 of 128 | -0.1741 | -0.4939 | -0.1080 |
| R-heal-rv-q_r-8 | q_r(record/post) - q_r(vote/post), g 8 | +0.2288 [+0.2222, +0.2355] | +0.2344, +0.2233 | 128 of 128 | +0.2652 | +0.3018 | +0.1742 |
| R-heal-v1v-q_r-8 | q_r(vote1/post) - q_r(vote/post), g 8 (the second copy) | -0.3387 [-0.3474, -0.3299] | -0.3385, -0.3388 | 128 of 128 | -0.3148 | -0.2954 | -0.3722 |
| R-heal-v1b-q_r-8 | q_r(vote1/post) - q_r(body/post), g 8 | -0.1177 [-0.1327, -0.1027] | -0.1107, -0.1247 | 128 of 128 | -0.1407 | +0.1984 | -0.2642 |

## Levels: q_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.896 (0.890 / 0.834 / 0.930) | 0.745 (0.736 / 0.562 / 0.842) | 0.531 (0.541 / 0.167 / 0.708) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.965 (0.962 / 0.956 / 0.971) | 0.897 (0.884 / 0.864 / 0.919) | 0.757 (0.727 / 0.671 / 0.815) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (0.999 / 0.999 / 0.999) | 0.998 (0.998 / 0.998 / 0.998) |
| body/post | 0.957 (0.969 / 0.946 / 0.957) | 0.859 (0.862 / 0.793 / 0.891) | 0.714 (0.711 / 0.535 / 0.805) | 0.506 (0.528 / 0.149 / 0.674) |
| vote/post | 0.957 (0.969 / 0.946 / 0.957) | 0.925 (0.931 / 0.909 / 0.930) | 0.861 (0.855 / 0.826 / 0.882) | 0.727 (0.702 / 0.643 / 0.782) |
| record/post | 0.957 (0.969 / 0.946 / 0.957) | 0.957 (0.969 / 0.946 / 0.957) | 0.957 (0.968 / 0.945 / 0.957) | 0.956 (0.967 / 0.945 / 0.956) |
| vote1/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.917 (0.919 / 0.907 / 0.921) | 0.734 (0.732 / 0.706 / 0.749) | 0.404 (0.403 / 0.362 / 0.425) |
| vote1/post | 0.957 (0.969 / 0.946 / 0.957) | 0.881 (0.889 / 0.864 / 0.884) | 0.705 (0.708 / 0.674 / 0.720) | 0.389 (0.387 / 0.348 / 0.410) |

## Levels: u_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.959 (0.974 / 0.895 / 0.983) | 0.897 (0.930 / 0.753 / 0.953) | 0.809 (0.840 / 0.592 / 0.902) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.990 (0.989 / 0.986 / 0.992) | 0.967 (0.965 / 0.950 / 0.977) | 0.907 (0.904 / 0.850 / 0.938) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (0.999 / 0.999 / 0.999) | 0.998 (0.998 / 0.998 / 0.998) |
| body/post | 0.000 (0.000 / 0.000 / 0.000) | 0.223 (0.233 / 0.091 / 0.284) | 0.393 (0.486 / 0.159 / 0.463) | 0.501 (0.653 / 0.247 / 0.552) |
| vote/post | 0.000 (0.000 / 0.000 / 0.000) | 0.017 (0.024 / 0.011 / 0.017) | 0.066 (0.100 / 0.041 / 0.062) | 0.171 (0.248 / 0.106 / 0.165) |
| record/post | 0.000 (0.000 / 0.000 / 0.000) | 0.000 (0.000 / 0.000 / 0.000) | 0.001 (0.001 / 0.001 / 0.001) | 0.002 (0.002 / 0.002 / 0.002) |
| vote1/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.967 (0.967 / 0.963 / 0.970) | 0.889 (0.896 / 0.847 / 0.906) | 0.728 (0.751 / 0.648 / 0.757) |
| vote1/post | 0.000 (0.000 / 0.000 / 0.000) | 0.044 (0.047 / 0.038 / 0.045) | 0.179 (0.192 / 0.142 / 0.192) | 0.365 (0.394 / 0.290 / 0.387) |

## Levels: u_v by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| body/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.927 (0.980 / 0.753 / 0.988) | 0.890 (0.938 / 0.703 / 0.960) | 0.817 (0.854 / 0.591 / 0.911) |
| vote/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.937 (0.990 / 0.773 / 0.993) | 0.927 (0.971 / 0.768 / 0.984) | 0.892 (0.929 / 0.713 / 0.962) |
| record/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.942 (0.994 / 0.782 / 0.996) | 0.942 (0.993 / 0.782 / 0.996) | 0.942 (0.993 / 0.783 / 0.996) |
| body/post | 0.979 (0.968 / 0.989 / 0.979) | 0.252 (0.313 / 0.062 / 0.316) | 0.405 (0.518 / 0.153 / 0.474) | 0.503 (0.665 / 0.242 / 0.553) |
| vote/post | 0.979 (0.968 / 0.989 / 0.979) | 0.170 (0.178 / 0.022 / 0.239) | 0.216 (0.263 / 0.043 / 0.279) | 0.304 (0.375 / 0.090 / 0.376) |
| record/post | 0.979 (0.968 / 0.989 / 0.979) | 0.137 (0.125 / 0.014 / 0.204) | 0.138 (0.128 / 0.015 / 0.206) | 0.138 (0.122 / 0.016 / 0.208) |
| vote1/protected | 0.979 (0.968 / 0.989 / 0.979) | 0.932 (0.985 / 0.767 / 0.989) | 0.894 (0.941 / 0.720 / 0.958) | 0.773 (0.819 / 0.606 / 0.833) |
| vote1/post | 0.979 (0.968 / 0.989 / 0.979) | 0.188 (0.202 / 0.029 / 0.260) | 0.282 (0.320 / 0.084 / 0.362) | 0.404 (0.458 / 0.226 / 0.465) |

## Levels: a_r by lineage and generation (all; native / particular / permissive)

| Lineage | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| body/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.957 (0.969 / 0.897 / 0.981) | 0.892 (0.922 / 0.738 / 0.955) | 0.810 (0.852 / 0.574 / 0.907) |
| vote/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.989 (0.989 / 0.985 / 0.991) | 0.965 (0.964 / 0.947 / 0.974) | 0.911 (0.911 / 0.856 / 0.938) |
| record/protected | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 0.999 (0.999 / 1.000 / 0.999) |
| body/post | 0.984 (0.984 / 0.984 / 0.984) | 0.943 (0.956 / 0.880 / 0.967) | 0.879 (0.912 / 0.718 / 0.942) | 0.801 (0.847 / 0.570 / 0.894) |
| vote/post | 0.984 (0.984 / 0.984 / 0.984) | 0.974 (0.973 / 0.969 / 0.976) | 0.950 (0.949 / 0.932 / 0.959) | 0.897 (0.898 / 0.842 / 0.924) |
| record/post | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) | 0.984 (0.984 / 0.984 / 0.984) |
| vote1/protected | 1.000 (1.000 / 1.000 / 1.000) | 0.965 (0.967 / 0.958 / 0.968) | 0.881 (0.889 / 0.847 / 0.895) | 0.733 (0.753 / 0.662 / 0.758) |
| vote1/post | 0.984 (0.984 / 0.984 / 0.984) | 0.950 (0.952 / 0.943 / 0.953) | 0.869 (0.877 / 0.836 / 0.882) | 0.725 (0.746 / 0.657 / 0.749) |
