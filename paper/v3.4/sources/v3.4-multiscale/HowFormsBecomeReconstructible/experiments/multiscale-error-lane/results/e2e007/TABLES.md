# E2E007 tables: development

Rows: the response {none; raise = the reading gain x (1 + kappa x), E2E006's; relax = gain / (1 + kappa x)} x the injury's target {memory: the generation's patch flipped in the incoming record at update 0, E2E003's; body: the same patch flipped in the newborn's V and E at update 2000, the record untouched}. Endpoints (e2e001.sim.score, unchanged, as E2E003 and E2E006 read them): U_v the body's agreement on the union of every patch injured so far (present organization, the field present where the row has one); q_r SR001's history specificity of the record; a_v whole-sheet agreement. The fresh successor (x) is a field-free newborn reading the outgoing record for one generation, never in the lineage. Item sets: native / particular (li4 x F0, read first) / permissive.

## The statement candidates

| Id | Part | Value [95%] | SD (block, case) | Halves | Narrowest | Registers | Band (a null) | Threshold | | Tasks | native | particular | permissive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 | the opposite response under memory injury, present organization: U_v(relax/memory) - U_v(none/memory), g 8 | +0.2132 [+0.2037, +0.2226] | 0.0177 (0.0177, 0.0151) | +0.2153, +0.2111 | 0.18 | True | [0.18, 0.25] | 0.17 | HOLDS | 128 of 128 | +0.2997 | +0.1433 | +0.2049 |
| Z2 | the opposite response under memory injury, history: q_r(relax/memory) - q_r(none/memory), g 8 | +0.1150 [+0.1079, +0.1222] | 0.0135 (0.0135, 0.0113) | +0.1189, +0.1112 | 0.09 | True | [0.09, 0.14] | 0.09 | HOLDS | 128 of 128 | +0.1300 | +0.1400 | +0.0951 |
| Z3 | the ruled response under body injury, present organization: U_v(raise/body) - U_v(none/body), g 8 (at most: reversed after P66's values, Amendment 1) | -0.0203 [-0.0253, -0.0152] | 0.0095 (0.0095, 0.0069) | -0.0171, -0.0234 | 0.0 | True | [-0.04, 0.0] | 0.02 | HOLDS | 128 of 128 | -0.0538 | +0.0087 | -0.0180 |
| Z4 | the interaction: [U_v(raise/body) - U_v(none/body)] - [U_v(raise/memory) - U_v(none/memory)], g 8 | +0.1008 [+0.0864, +0.1152] | 0.0270 (0.0270, 0.0161) | +0.1084, +0.0932 | 0.05 | True | [0.05, 0.15] | 0.07 | HOLDS | 128 of 128 | +0.0751 | -0.0042 | +0.1662 |
| Z5 | the opposite response under body injury: U_v(relax/body) - U_v(none/body), g 8 | -0.0533 [-0.0590, -0.0476] | 0.0107 (0.0087, 0.0107) | -0.0539, -0.0528 | -0.03 | True | [-0.08, -0.03] | -0.03 | HOLDS | 128 of 128 | -0.0073 | -0.0649 | -0.0705 |
| Z1x | what the record carries, the opposite response under memory injury: the fresh successor's U_v, relax/memory - none/memory, after g 8 | +0.2293 [+0.2189, +0.2397] | 0.0195 (0.0195, 0.0184) | +0.2334, +0.2252 | 0.19 | True | [0.19, 0.27] | 0.19 | HOLDS | 128 of 128 | +0.2520 | +0.1609 | +0.2521 |
| Z3x | what the record carries, the ruled response under body injury: the fresh successor's U_v, raise/body - none/body, after g 8 (at most: reversed after P66's values, Amendment 1) | -0.0284 [-0.0324, -0.0244] | 0.0075 (0.0075, 0.0063) | -0.0249, -0.0319 | -0.01 | True | [-0.05, -0.01] | -0.01 | HOLDS | 128 of 128 | -0.0343 | -0.0464 | -0.0165 |

Aliased tasks (two compared labels on one row): {'raise/body | none/body': 0, 'raise/memory | none/memory': 0, 'relax-matched/memory | none/memory': 0, 'relax-matched/memory | relax/memory': 0, 'relax/body | none/body': 0, 'relax/memory | none/memory': 0}

## The realized exposures

x(t) is the exposure the response reads at update t; kappa x x summed over the generation (the response acts in every update). raise and relax read the same kind of exposure; their bodies differ, so their exposures differ.

| Row | g | mean x | x, updates 1-4,000 | x, 4,001-8,000 | integrated kappa x x |
|---|---|---|---|---|---|
| raise/memory | 1 | 0.4261 | 0.4240 | 0.4283 | 6627 |
| raise/memory | 2 | 0.4358 | 0.4334 | 0.4382 | 6778 |
| raise/memory | 3 | 0.4450 | 0.4423 | 0.4477 | 6920 |
| raise/memory | 4 | 0.4552 | 0.4528 | 0.4577 | 7080 |
| raise/memory | 5 | 0.4637 | 0.4612 | 0.4662 | 7211 |
| raise/memory | 6 | 0.4727 | 0.4701 | 0.4752 | 7351 |
| raise/memory | 7 | 0.4811 | 0.4786 | 0.4837 | 7482 |
| raise/memory | 8 | 0.4881 | 0.4855 | 0.4908 | 7592 |
| relax/memory | 1 | 0.6542 | 0.6535 | 0.6548 | 10174 |
| relax/memory | 2 | 0.6675 | 0.6651 | 0.6700 | 10382 |
| relax/memory | 3 | 0.6772 | 0.6728 | 0.6816 | 10532 |
| relax/memory | 4 | 0.6927 | 0.6849 | 0.7005 | 10773 |
| relax/memory | 5 | 0.7010 | 0.6928 | 0.7091 | 10901 |
| relax/memory | 6 | 0.7101 | 0.7006 | 0.7197 | 11044 |
| relax/memory | 7 | 0.7197 | 0.7091 | 0.7304 | 11193 |
| relax/memory | 8 | 0.7250 | 0.7152 | 0.7348 | 11275 |
| raise/body | 1 | 0.4240 | 0.4215 | 0.4265 | 6594 |
| raise/body | 2 | 0.4316 | 0.4292 | 0.4340 | 6712 |
| raise/body | 3 | 0.4382 | 0.4355 | 0.4410 | 6815 |
| raise/body | 4 | 0.4457 | 0.4432 | 0.4482 | 6931 |
| raise/body | 5 | 0.4514 | 0.4489 | 0.4539 | 7020 |
| raise/body | 6 | 0.4577 | 0.4552 | 0.4601 | 7118 |
| raise/body | 7 | 0.4636 | 0.4611 | 0.4661 | 7210 |
| raise/body | 8 | 0.4682 | 0.4655 | 0.4708 | 7281 |
| relax/body | 1 | 0.6486 | 0.6441 | 0.6531 | 10087 |
| relax/body | 2 | 0.6593 | 0.6555 | 0.6632 | 10254 |
| relax/body | 3 | 0.6664 | 0.6623 | 0.6705 | 10364 |
| relax/body | 4 | 0.6759 | 0.6720 | 0.6798 | 10512 |
| relax/body | 5 | 0.6874 | 0.6808 | 0.6940 | 10691 |
| relax/body | 6 | 0.6958 | 0.6877 | 0.7038 | 10821 |
| relax/body | 7 | 0.7024 | 0.6936 | 0.7112 | 10924 |
| relax/body | 8 | 0.7088 | 0.6985 | 0.7192 | 11024 |
| relax-matched/memory | 1 | 0.6128 | 0.6120 | 0.6135 | 6863 |
| relax-matched/memory | 2 | 0.6235 | 0.6233 | 0.6238 | 6984 |
| relax-matched/memory | 3 | 0.6298 | 0.6292 | 0.6304 | 7053 |
| relax-matched/memory | 4 | 0.6400 | 0.6391 | 0.6410 | 7168 |
| relax-matched/memory | 5 | 0.6467 | 0.6461 | 0.6474 | 7244 |
| relax-matched/memory | 6 | 0.6509 | 0.6504 | 0.6513 | 7290 |
| relax-matched/memory | 7 | 0.6580 | 0.6559 | 0.6601 | 7370 |
| relax-matched/memory | 8 | 0.6601 | 0.6584 | 0.6617 | 7393 |

relax/memory over raise/memory, integrated kappa x exposure by generation: g 1 1.535, g 2 1.532, g 3 1.522, g 4 1.522, g 5 1.512, g 6 1.502, g 7 1.496, g 8 1.485

relax/body over raise/body, integrated kappa x exposure by generation: g 1 1.530, g 2 1.528, g 3 1.521, g 4 1.517, g 5 1.523, g 6 1.520, g 7 1.515, g 8 1.514

relax-matched/memory over raise/memory, integrated kappa x exposure by generation: g 1 1.036, g 2 1.030, g 3 1.019, g 4 1.012, g 5 1.005, g 6 0.992, g 7 0.985, g 8 0.974

## The observer: the body's agreement with its own record on the generation's patch (output only)

The share of the patch's cells where sign V = sign r, after the body step of the update shown (the body injury just before update 2000's body step). All; native / particular / permissive.

| Row | g | pre (1999) | p80 (2100) | p16 (2500) | p4 (4000) | end (8000) |
|---|---|---|---|---|---|---|
| none/memory | 1 | 0.825 (0.810 / 0.950 / 0.769) | 0.835 (0.815 / 0.956 / 0.785) | 0.865 (0.823 / 0.943 / 0.847) | 0.887 (0.848 / 0.914 / 0.892) | 0.912 (0.888 / 0.887 / 0.936) |
| none/memory | 2 | 0.823 (0.829 / 0.933 / 0.766) | 0.830 (0.827 / 0.932 / 0.780) | 0.859 (0.836 / 0.928 / 0.836) | 0.879 (0.851 / 0.909 / 0.878) | 0.902 (0.891 / 0.882 / 0.917) |
| none/memory | 3 | 0.809 (0.800 / 0.918 / 0.759) | 0.818 (0.805 / 0.917 / 0.775) | 0.847 (0.820 / 0.916 / 0.827) | 0.867 (0.834 / 0.897 / 0.869) | 0.896 (0.887 / 0.892 / 0.902) |
| none/memory | 4 | 0.817 (0.813 / 0.899 / 0.777) | 0.827 (0.832 / 0.898 / 0.790) | 0.851 (0.836 / 0.901 / 0.833) | 0.861 (0.851 / 0.889 / 0.852) | 0.897 (0.882 / 0.902 / 0.903) |
| none/memory | 5 | 0.812 (0.813 / 0.895 / 0.770) | 0.820 (0.818 / 0.893 / 0.784) | 0.848 (0.828 / 0.889 / 0.837) | 0.865 (0.841 / 0.879 / 0.871) | 0.898 (0.895 / 0.876 / 0.911) |
| none/memory | 6 | 0.794 (0.800 / 0.879 / 0.749) | 0.803 (0.806 / 0.882 / 0.763) | 0.833 (0.820 / 0.882 / 0.816) | 0.861 (0.843 / 0.877 / 0.861) | 0.901 (0.889 / 0.890 / 0.913) |
| none/memory | 7 | 0.805 (0.808 / 0.866 / 0.772) | 0.815 (0.815 / 0.868 / 0.788) | 0.838 (0.818 / 0.871 / 0.832) | 0.852 (0.847 / 0.871 / 0.845) | 0.892 (0.890 / 0.897 / 0.891) |
| none/memory | 8 | 0.790 (0.794 / 0.860 / 0.753) | 0.802 (0.800 / 0.865 / 0.772) | 0.827 (0.816 / 0.863 / 0.814) | 0.854 (0.840 / 0.869 / 0.854) | 0.891 (0.887 / 0.898 / 0.889) |
| raise/memory | 1 | 0.924 (0.955 / 0.977 / 0.881) | 0.928 (0.958 / 0.977 / 0.888) | 0.942 (0.957 / 0.982 / 0.915) | 0.949 (0.958 / 0.979 / 0.929) | 0.968 (0.970 / 0.984 / 0.959) |
| raise/memory | 2 | 0.926 (0.954 / 0.949 / 0.899) | 0.931 (0.958 / 0.952 / 0.907) | 0.938 (0.957 / 0.958 / 0.919) | 0.948 (0.961 / 0.959 / 0.935) | 0.962 (0.967 / 0.971 / 0.956) |
| raise/memory | 3 | 0.919 (0.952 / 0.942 / 0.890) | 0.921 (0.951 / 0.944 / 0.895) | 0.932 (0.955 / 0.945 / 0.913) | 0.940 (0.958 / 0.949 / 0.926) | 0.951 (0.959 / 0.961 / 0.942) |
| raise/memory | 4 | 0.916 (0.949 / 0.928 / 0.894) | 0.923 (0.956 / 0.935 / 0.900) | 0.930 (0.961 / 0.934 / 0.912) | 0.938 (0.958 / 0.940 / 0.927) | 0.951 (0.965 / 0.948 / 0.946) |
| raise/memory | 5 | 0.920 (0.955 / 0.932 / 0.896) | 0.924 (0.954 / 0.938 / 0.901) | 0.930 (0.955 / 0.941 / 0.912) | 0.937 (0.956 / 0.938 / 0.926) | 0.951 (0.960 / 0.944 / 0.951) |
| raise/memory | 6 | 0.915 (0.949 / 0.927 / 0.891) | 0.917 (0.949 / 0.932 / 0.893) | 0.928 (0.953 / 0.931 / 0.913) | 0.935 (0.953 / 0.938 / 0.925) | 0.949 (0.964 / 0.948 / 0.942) |
| raise/memory | 7 | 0.918 (0.949 / 0.927 / 0.899) | 0.922 (0.947 / 0.933 / 0.904) | 0.925 (0.947 / 0.933 / 0.910) | 0.933 (0.951 / 0.936 / 0.924) | 0.951 (0.959 / 0.950 / 0.948) |
| raise/memory | 8 | 0.919 (0.941 / 0.918 / 0.908) | 0.924 (0.948 / 0.925 / 0.911) | 0.928 (0.949 / 0.922 / 0.921) | 0.932 (0.953 / 0.929 / 0.924) | 0.950 (0.959 / 0.943 / 0.949) |
| relax/memory | 1 | 0.605 (0.474 / 0.859 / 0.545) | 0.623 (0.491 / 0.854 / 0.573) | 0.701 (0.601 / 0.829 / 0.686) | 0.779 (0.793 / 0.766 / 0.779) | 0.823 (0.893 / 0.697 / 0.851) |
| relax/memory | 2 | 0.603 (0.493 / 0.848 / 0.535) | 0.621 (0.506 / 0.848 / 0.565) | 0.694 (0.597 / 0.823 / 0.677) | 0.762 (0.759 / 0.770 / 0.761) | 0.809 (0.871 / 0.728 / 0.819) |
| relax/memory | 3 | 0.593 (0.495 / 0.828 / 0.524) | 0.614 (0.518 / 0.831 / 0.552) | 0.686 (0.602 / 0.801 / 0.671) | 0.760 (0.760 / 0.752 / 0.764) | 0.808 (0.870 / 0.725 / 0.818) |
| relax/memory | 4 | 0.614 (0.501 / 0.822 / 0.566) | 0.630 (0.514 / 0.814 / 0.596) | 0.689 (0.597 / 0.797 / 0.682) | 0.732 (0.746 / 0.752 / 0.715) | 0.775 (0.855 / 0.720 / 0.762) |
| relax/memory | 5 | 0.601 (0.501 / 0.799 / 0.552) | 0.612 (0.505 / 0.795 / 0.573) | 0.666 (0.577 / 0.781 / 0.653) | 0.735 (0.736 / 0.762 / 0.722) | 0.797 (0.862 / 0.756 / 0.785) |
| relax/memory | 6 | 0.589 (0.505 / 0.796 / 0.527) | 0.602 (0.508 / 0.791 / 0.554) | 0.669 (0.583 / 0.771 / 0.661) | 0.739 (0.754 / 0.732 / 0.734) | 0.787 (0.864 / 0.721 / 0.782) |
| relax/memory | 7 | 0.609 (0.523 / 0.795 / 0.559) | 0.624 (0.528 / 0.800 / 0.584) | 0.682 (0.610 / 0.781 / 0.669) | 0.740 (0.733 / 0.771 / 0.727) | 0.775 (0.843 / 0.740 / 0.759) |
| relax/memory | 8 | 0.574 (0.499 / 0.779 / 0.508) | 0.591 (0.511 / 0.784 / 0.536) | 0.660 (0.584 / 0.775 / 0.640) | 0.728 (0.723 / 0.742 / 0.723) | 0.779 (0.839 / 0.737 / 0.770) |
| none/body | 1 | 0.924 (0.968 / 0.785 / 0.972) | 0.920 (0.971 / 0.763 / 0.972) | 0.927 (0.971 / 0.786 / 0.976) | 0.927 (0.972 / 0.782 / 0.977) | 0.930 (0.974 / 0.791 / 0.978) |
| none/body | 2 | 0.920 (0.960 / 0.793 / 0.963) | 0.918 (0.963 / 0.780 / 0.965) | 0.929 (0.967 / 0.803 / 0.972) | 0.931 (0.972 / 0.801 / 0.975) | 0.936 (0.974 / 0.814 / 0.977) |
| none/body | 3 | 0.913 (0.955 / 0.782 / 0.957) | 0.909 (0.954 / 0.777 / 0.953) | 0.917 (0.955 / 0.792 / 0.961) | 0.923 (0.961 / 0.796 / 0.966) | 0.924 (0.962 / 0.797 / 0.969) |
| none/body | 4 | 0.919 (0.952 / 0.817 / 0.953) | 0.916 (0.954 / 0.802 / 0.954) | 0.922 (0.957 / 0.814 / 0.959) | 0.924 (0.958 / 0.817 / 0.960) | 0.928 (0.961 / 0.827 / 0.961) |
| none/body | 5 | 0.923 (0.956 / 0.812 / 0.963) | 0.917 (0.959 / 0.781 / 0.963) | 0.929 (0.962 / 0.819 / 0.968) | 0.924 (0.960 / 0.804 / 0.966) | 0.928 (0.963 / 0.812 / 0.969) |
| none/body | 6 | 0.911 (0.944 / 0.808 / 0.946) | 0.907 (0.946 / 0.795 / 0.944) | 0.920 (0.950 / 0.822 / 0.953) | 0.922 (0.954 / 0.823 / 0.955) | 0.929 (0.958 / 0.834 / 0.962) |
| none/body | 7 | 0.911 (0.939 / 0.815 / 0.944) | 0.909 (0.943 / 0.801 / 0.947) | 0.914 (0.942 / 0.812 / 0.950) | 0.916 (0.947 / 0.815 / 0.951) | 0.921 (0.951 / 0.824 / 0.953) |
| none/body | 8 | 0.911 (0.938 / 0.818 / 0.944) | 0.904 (0.940 / 0.792 / 0.942) | 0.913 (0.945 / 0.810 / 0.948) | 0.913 (0.947 / 0.804 / 0.951) | 0.918 (0.949 / 0.815 / 0.953) |
| raise/body | 1 | 0.973 (0.980 / 0.957 / 0.978) | 0.975 (0.982 / 0.957 / 0.981) | 0.978 (0.986 / 0.958 / 0.984) | 0.977 (0.985 / 0.958 / 0.983) | 0.980 (0.990 / 0.957 / 0.987) |
| raise/body | 2 | 0.967 (0.976 / 0.948 / 0.972) | 0.969 (0.975 / 0.952 / 0.974) | 0.971 (0.980 / 0.948 / 0.978) | 0.974 (0.984 / 0.946 / 0.982) | 0.976 (0.987 / 0.951 / 0.983) |
| raise/body | 3 | 0.965 (0.973 / 0.952 / 0.967) | 0.965 (0.974 / 0.951 / 0.969) | 0.969 (0.974 / 0.958 / 0.972) | 0.972 (0.979 / 0.955 / 0.977) | 0.970 (0.973 / 0.957 / 0.976) |
| raise/body | 4 | 0.963 (0.968 / 0.958 / 0.963) | 0.967 (0.971 / 0.962 / 0.968) | 0.969 (0.974 / 0.961 / 0.970) | 0.970 (0.975 / 0.963 / 0.971) | 0.971 (0.975 / 0.963 / 0.973) |
| raise/body | 5 | 0.966 (0.973 / 0.951 / 0.971) | 0.968 (0.976 / 0.953 / 0.971) | 0.971 (0.977 / 0.954 / 0.976) | 0.969 (0.976 / 0.951 / 0.974) | 0.971 (0.977 / 0.954 / 0.977) |
| raise/body | 6 | 0.956 (0.969 / 0.943 / 0.956) | 0.960 (0.969 / 0.952 / 0.961) | 0.964 (0.969 / 0.955 / 0.966) | 0.964 (0.973 / 0.952 / 0.966) | 0.971 (0.981 / 0.958 / 0.973) |
| raise/body | 7 | 0.961 (0.974 / 0.958 / 0.957) | 0.961 (0.974 / 0.952 / 0.959) | 0.964 (0.976 / 0.955 / 0.963) | 0.964 (0.973 / 0.958 / 0.963) | 0.966 (0.976 / 0.957 / 0.965) |
| raise/body | 8 | 0.957 (0.966 / 0.955 / 0.953) | 0.959 (0.969 / 0.954 / 0.957) | 0.961 (0.970 / 0.954 / 0.961) | 0.963 (0.970 / 0.957 / 0.962) | 0.965 (0.971 / 0.959 / 0.965) |
| relax/body | 1 | 0.848 (0.918 / 0.642 / 0.917) | 0.800 (0.909 / 0.591 / 0.850) | 0.834 (0.916 / 0.640 / 0.889) | 0.837 (0.922 / 0.632 / 0.898) | 0.841 (0.927 / 0.633 / 0.903) |
| relax/body | 2 | 0.842 (0.911 / 0.634 / 0.910) | 0.799 (0.906 / 0.622 / 0.835) | 0.832 (0.919 / 0.649 / 0.881) | 0.841 (0.921 / 0.654 / 0.895) | 0.843 (0.922 / 0.659 / 0.896) |
| relax/body | 3 | 0.836 (0.899 / 0.649 / 0.898) | 0.781 (0.890 / 0.615 / 0.810) | 0.821 (0.904 / 0.652 / 0.865) | 0.826 (0.908 / 0.639 / 0.878) | 0.831 (0.911 / 0.650 / 0.881) |
| relax/body | 4 | 0.839 (0.897 / 0.682 / 0.888) | 0.792 (0.882 / 0.660 / 0.812) | 0.829 (0.905 / 0.694 / 0.859) | 0.838 (0.904 / 0.702 / 0.873) | 0.838 (0.912 / 0.691 / 0.875) |
| relax/body | 5 | 0.848 (0.903 / 0.683 / 0.903) | 0.784 (0.894 / 0.611 / 0.816) | 0.822 (0.906 / 0.662 / 0.859) | 0.827 (0.910 / 0.671 / 0.863) | 0.824 (0.912 / 0.670 / 0.857) |
| relax/body | 6 | 0.826 (0.897 / 0.656 / 0.876) | 0.782 (0.892 / 0.629 / 0.804) | 0.809 (0.903 / 0.660 / 0.837) | 0.811 (0.903 / 0.660 / 0.841) | 0.820 (0.911 / 0.680 / 0.845) |
| relax/body | 7 | 0.816 (0.888 / 0.647 / 0.864) | 0.770 (0.884 / 0.615 / 0.790) | 0.800 (0.890 / 0.653 / 0.828) | 0.804 (0.899 / 0.648 / 0.834) | 0.807 (0.899 / 0.661 / 0.834) |
| relax/body | 8 | 0.828 (0.887 / 0.649 / 0.888) | 0.785 (0.882 / 0.628 / 0.815) | 0.814 (0.888 / 0.652 / 0.858) | 0.815 (0.893 / 0.647 / 0.860) | 0.812 (0.895 / 0.643 / 0.855) |
| relax-matched/memory | 1 | 0.657 (0.531 / 0.879 / 0.610) | 0.674 (0.543 / 0.877 / 0.637) | 0.729 (0.618 / 0.855 / 0.722) | 0.792 (0.787 / 0.790 / 0.797) | 0.841 (0.898 / 0.734 / 0.865) |
| relax-matched/memory | 2 | 0.649 (0.556 / 0.868 / 0.587) | 0.667 (0.571 / 0.865 / 0.615) | 0.722 (0.626 / 0.850 / 0.706) | 0.794 (0.753 / 0.807 / 0.808) | 0.836 (0.875 / 0.753 / 0.857) |
| relax-matched/memory | 3 | 0.644 (0.556 / 0.853 / 0.583) | 0.661 (0.570 / 0.855 / 0.609) | 0.719 (0.631 / 0.828 / 0.709) | 0.787 (0.748 / 0.793 / 0.804) | 0.837 (0.881 / 0.753 / 0.856) |
| relax-matched/memory | 4 | 0.655 (0.571 / 0.838 / 0.605) | 0.669 (0.580 / 0.834 / 0.632) | 0.723 (0.638 / 0.822 / 0.716) | 0.774 (0.766 / 0.788 / 0.771) | 0.828 (0.859 / 0.778 / 0.838) |
| relax-matched/memory | 5 | 0.650 (0.561 / 0.825 / 0.606) | 0.659 (0.563 / 0.822 / 0.624) | 0.699 (0.615 / 0.804 / 0.689) | 0.764 (0.744 / 0.790 / 0.761) | 0.827 (0.872 / 0.766 / 0.835) |
| relax-matched/memory | 6 | 0.626 (0.563 / 0.814 / 0.564) | 0.638 (0.569 / 0.805 / 0.590) | 0.701 (0.628 / 0.795 / 0.691) | 0.766 (0.759 / 0.770 / 0.768) | 0.829 (0.859 / 0.765 / 0.846) |
| relax-matched/memory | 7 | 0.647 (0.573 / 0.810 / 0.603) | 0.663 (0.583 / 0.815 / 0.627) | 0.719 (0.648 / 0.802 / 0.714) | 0.769 (0.747 / 0.781 / 0.773) | 0.826 (0.855 / 0.779 / 0.835) |
| relax-matched/memory | 8 | 0.626 (0.565 / 0.800 / 0.570) | 0.639 (0.572 / 0.801 / 0.592) | 0.700 (0.632 / 0.797 / 0.686) | 0.761 (0.738 / 0.773 / 0.766) | 0.816 (0.847 / 0.769 / 0.825) |

## Reported contrasts

| Id | Part | Value [95%] | Halves | Tasks | native | particular | permissive |
|---|---|---|---|---|---|---|---|
| R-Z1-1 | the opposite response under memory injury, present organization: U_v(relax/memory) - U_v(none/memory), g 8 [at g 1] | +0.1854 [+0.1716, +0.1992] | +0.1912, +0.1796 | 128 of 128 | +0.3262 | +0.1047 | +0.1553 |
| R-Z2-1 | the opposite response under memory injury, history: q_r(relax/memory) - q_r(none/memory), g 8 [at g 1] | +0.0203 [+0.0178, +0.0227] | +0.0224, +0.0182 | 128 of 128 | +0.0237 | +0.0276 | +0.0149 |
| R-Z3-1 | the ruled response under body injury, present organization: U_v(raise/body) - U_v(none/body), g 8 (at most: reversed after P66's values, Amendment 1) [at g 1] | +0.0168 [+0.0104, +0.0232] | +0.0158, +0.0178 | 128 of 128 | -0.0270 | +0.1063 | -0.0061 |
| R-Z4-1 | the interaction: [U_v(raise/body) - U_v(none/body)] - [U_v(raise/memory) - U_v(none/memory)], g 8 [at g 1] | +0.1057 [+0.0946, +0.1168] | +0.1084, +0.1030 | 128 of 128 | +0.1144 | +0.1055 | +0.1014 |
| R-Z5-1 | the opposite response under body injury: U_v(relax/body) - U_v(none/body), g 8 [at g 1] | +0.0070 [-0.0024, +0.0165] | +0.0076, +0.0065 | 128 of 128 | +0.1039 | -0.0438 | -0.0159 |
| R-Z1-3 | the opposite response under memory injury, present organization: U_v(relax/memory) - U_v(none/memory), g 8 [at g 3] | +0.2178 [+0.2054, +0.2301] | +0.2305, +0.2051 | 128 of 128 | +0.3275 | +0.1269 | +0.2084 |
| R-Z2-3 | the opposite response under memory injury, history: q_r(relax/memory) - q_r(none/memory), g 8 [at g 3] | +0.0509 [+0.0463, +0.0556] | +0.0551, +0.0468 | 128 of 128 | +0.0562 | +0.0662 | +0.0407 |
| R-Z3-3 | the ruled response under body injury, present organization: U_v(raise/body) - U_v(none/body), g 8 (at most: reversed after P66's values, Amendment 1) [at g 3] | +0.0082 [+0.0024, +0.0140] | +0.0099, +0.0065 | 128 of 128 | -0.0300 | +0.0756 | -0.0064 |
| R-Z4-3 | the interaction: [U_v(raise/body) - U_v(none/body)] - [U_v(raise/memory) - U_v(none/memory)], g 8 [at g 3] | +0.1388 [+0.1281, +0.1494] | +0.1433, +0.1342 | 128 of 128 | +0.1292 | +0.1013 | +0.1623 |
| R-Z5-3 | the opposite response under body injury: U_v(relax/body) - U_v(none/body), g 8 [at g 3] | -0.0346 [-0.0402, -0.0289] | -0.0347, -0.0345 | 128 of 128 | +0.0209 | -0.0786 | -0.0403 |
| R-raise-none-memory-U_v-1 | U_v(raise/memory) - U_v(none/memory), g 1 | -0.0889 [-0.1002, -0.0776] | -0.0926, -0.0852 | 128 of 128 | -0.1414 | +0.0009 | -0.1075 |
| R-raise-none-memory-q_r-1 | q_r(raise/memory) - q_r(none/memory), g 1 | -0.0207 [-0.0226, -0.0187] | -0.0216, -0.0197 | 128 of 128 | -0.0228 | -0.0316 | -0.0141 |
| R-raise-none-memory-a_v-1 | a_v(raise/memory) - a_v(none/memory), g 1 | +0.0311 [+0.0284, +0.0337] | +0.0295, +0.0327 | 128 of 128 | -0.0023 | +0.1267 | -0.0001 |
| R-raise-none-memory-U-1 | U(raise/memory) - U(none/memory), g 1 | -0.0842 [-0.0957, -0.0726] | -0.0848, -0.0836 | 128 of 128 | -0.0730 | -0.0763 | -0.0937 |
| R-relax-none-memory-U_v-1 | U_v(relax/memory) - U_v(none/memory), g 1 | +0.1854 [+0.1716, +0.1992] | +0.1912, +0.1796 | 128 of 128 | +0.3262 | +0.1047 | +0.1553 |
| R-relax-none-memory-q_r-1 | q_r(relax/memory) - q_r(none/memory), g 1 | +0.0203 [+0.0178, +0.0227] | +0.0224, +0.0182 | 128 of 128 | +0.0237 | +0.0276 | +0.0149 |
| R-relax-none-memory-a_v-1 | a_v(relax/memory) - a_v(none/memory), g 1 | -0.0661 [-0.0724, -0.0598] | -0.0635, -0.0687 | 128 of 128 | -0.0349 | -0.1195 | -0.0550 |
| R-relax-none-memory-U-1 | U(relax/memory) - U(none/memory), g 1 | +0.1835 [+0.1686, +0.1985] | +0.1917, +0.1754 | 128 of 128 | +0.2302 | +0.1547 | +0.1746 |
| R-raise-none-body-U_v-1 | U_v(raise/body) - U_v(none/body), g 1 | +0.0168 [+0.0104, +0.0232] | +0.0158, +0.0178 | 128 of 128 | -0.0270 | +0.1063 | -0.0061 |
| R-raise-none-body-q_r-1 | q_r(raise/body) - q_r(none/body), g 1 | -0.0183 [-0.0202, -0.0164] | -0.0193, -0.0172 | 128 of 128 | -0.0195 | -0.0355 | -0.0091 |
| R-raise-none-body-a_v-1 | a_v(raise/body) - a_v(none/body), g 1 | +0.0349 [+0.0321, +0.0377] | +0.0335, +0.0363 | 128 of 128 | +0.0006 | +0.1337 | +0.0026 |
| R-raise-none-body-U-1 | U(raise/body) - U(none/body), g 1 | -0.0043 [-0.0068, -0.0019] | -0.0041, -0.0046 | 128 of 128 | -0.0009 | -0.0149 | -0.0008 |
| R-relax-none-body-U_v-1 | U_v(relax/body) - U_v(none/body), g 1 | +0.0070 [-0.0024, +0.0165] | +0.0076, +0.0065 | 128 of 128 | +0.1039 | -0.0438 | -0.0159 |
| R-relax-none-body-q_r-1 | q_r(relax/body) - q_r(none/body), g 1 | +0.0096 [+0.0082, +0.0110] | +0.0107, +0.0084 | 128 of 128 | +0.0093 | +0.0196 | +0.0047 |
| R-relax-none-body-a_v-1 | a_v(relax/body) - a_v(none/body), g 1 | -0.0702 [-0.0767, -0.0638] | -0.0676, -0.0729 | 128 of 128 | -0.0421 | -0.1212 | -0.0588 |
| R-relax-none-body-U-1 | U(relax/body) - U(none/body), g 1 | +0.0014 [-0.0005, +0.0034] | +0.0014, +0.0015 | 128 of 128 | -0.0002 | +0.0082 | -0.0011 |
| R-relax-raise-memory-U_v-1 | U_v(relax/memory) - U_v(raise/memory), g 1 | +0.2743 [+0.2565, +0.2921] | +0.2838, +0.2648 | 128 of 128 | +0.4675 | +0.1039 | +0.2629 |
| R-relax-raise-memory-q_r-1 | q_r(relax/memory) - q_r(raise/memory), g 1 | +0.0409 [+0.0376, +0.0443] | +0.0440, +0.0379 | 128 of 128 | +0.0464 | +0.0592 | +0.0290 |
| R-relax-raise-memory-a_v-1 | a_v(relax/memory) - a_v(raise/memory), g 1 | -0.0972 [-0.1059, -0.0885] | -0.0930, -0.1014 | 128 of 128 | -0.0327 | -0.2462 | -0.0549 |
| R-relax-raise-memory-U-1 | U(relax/memory) - U(raise/memory), g 1 | +0.2677 [+0.2485, +0.2869] | +0.2765, +0.2589 | 128 of 128 | +0.3032 | +0.2310 | +0.2683 |
| R-relax-raise-body-U_v-1 | U_v(relax/body) - U_v(raise/body), g 1 | -0.0097 [-0.0239, +0.0044] | -0.0082, -0.0113 | 128 of 128 | +0.1309 | -0.1501 | -0.0098 |
| R-relax-raise-body-q_r-1 | q_r(relax/body) - q_r(raise/body), g 1 | +0.0279 [+0.0254, +0.0304] | +0.0300, +0.0257 | 128 of 128 | +0.0288 | +0.0551 | +0.0138 |
| R-relax-raise-body-a_v-1 | a_v(relax/body) - a_v(raise/body), g 1 | -0.1051 [-0.1142, -0.0960] | -0.1010, -0.1091 | 128 of 128 | -0.0427 | -0.2549 | -0.0614 |
| R-relax-raise-body-U-1 | U(relax/body) - U(raise/body), g 1 | +0.0058 [+0.0024, +0.0091] | +0.0055, +0.0060 | 128 of 128 | +0.0006 | +0.0231 | -0.0003 |
| R-matched-none-memory-U_v-1 | U_v(relax-matched/memory) - U_v(none/memory), g 1 | +0.1544 [+0.1421, +0.1666] | +0.1568, +0.1519 | 128 of 128 | +0.2886 | +0.0894 | +0.1198 |
| R-matched-none-memory-q_r-1 | q_r(relax-matched/memory) - q_r(none/memory), g 1 | +0.0166 [+0.0144, +0.0188] | +0.0172, +0.0159 | 128 of 128 | +0.0209 | +0.0237 | +0.0108 |
| R-matched-none-memory-a_v-1 | a_v(relax-matched/memory) - a_v(none/memory), g 1 | -0.0474 [-0.0540, -0.0409] | -0.0453, -0.0496 | 128 of 128 | -0.0211 | -0.1028 | -0.0329 |
| R-matched-none-memory-U-1 | U(relax-matched/memory) - U(none/memory), g 1 | +0.1511 [+0.1372, +0.1650] | +0.1561, +0.1461 | 128 of 128 | +0.2150 | +0.1324 | +0.1285 |
| R-matched-relax-memory-U_v-1 | U_v(relax-matched/memory) - U_v(relax/memory), g 1 | -0.0310 [-0.0405, -0.0216] | -0.0344, -0.0276 | 128 of 128 | -0.0376 | -0.0154 | -0.0356 |
| R-matched-relax-memory-q_r-1 | q_r(relax-matched/memory) - q_r(relax/memory), g 1 | -0.0037 [-0.0048, -0.0026] | -0.0051, -0.0023 | 128 of 128 | -0.0028 | -0.0039 | -0.0041 |
| R-matched-relax-memory-a_v-1 | a_v(relax-matched/memory) - a_v(relax/memory), g 1 | +0.0187 [+0.0173, +0.0201] | +0.0182, +0.0191 | 128 of 128 | +0.0139 | +0.0167 | +0.0221 |
| R-matched-relax-memory-U-1 | U(relax-matched/memory) - U(relax/memory), g 1 | -0.0324 [-0.0398, -0.0251] | -0.0356, -0.0292 | 128 of 128 | -0.0153 | -0.0222 | -0.0461 |
| R-inter-q_r-1 | the interaction in q_r, g 1 | +0.0024 [+0.0011, +0.0036] | +0.0023, +0.0025 | 128 of 128 | +0.0033 | -0.0038 | +0.0050 |
| R-raise-none-memory-U_v-3 | U_v(raise/memory) - U_v(none/memory), g 3 | -0.1306 [-0.1405, -0.1207] | -0.1335, -0.1277 | 128 of 128 | -0.1592 | -0.0257 | -0.1687 |
| R-raise-none-memory-q_r-3 | q_r(raise/memory) - q_r(none/memory), g 3 | -0.0516 [-0.0551, -0.0481] | -0.0534, -0.0499 | 128 of 128 | -0.0560 | -0.0729 | -0.0388 |
| R-raise-none-memory-a_v-3 | a_v(raise/memory) - a_v(none/memory), g 3 | +0.0062 [+0.0032, +0.0092] | +0.0046, +0.0078 | 128 of 128 | -0.0216 | +0.0703 | -0.0119 |
| R-raise-none-memory-U-3 | U(raise/memory) - U(none/memory), g 3 | -0.1142 [-0.1237, -0.1047] | -0.1167, -0.1118 | 128 of 128 | -0.0950 | -0.0815 | -0.1402 |
| R-relax-none-memory-U_v-3 | U_v(relax/memory) - U_v(none/memory), g 3 | +0.2178 [+0.2054, +0.2301] | +0.2305, +0.2051 | 128 of 128 | +0.3275 | +0.1269 | +0.2084 |
| R-relax-none-memory-q_r-3 | q_r(relax/memory) - q_r(none/memory), g 3 | +0.0509 [+0.0463, +0.0556] | +0.0551, +0.0468 | 128 of 128 | +0.0562 | +0.0662 | +0.0407 |
| R-relax-none-memory-a_v-3 | a_v(relax/memory) - a_v(none/memory), g 3 | -0.0580 [-0.0638, -0.0522] | -0.0530, -0.0630 | 128 of 128 | -0.0184 | -0.0999 | -0.0568 |
| R-relax-none-memory-U-3 | U(relax/memory) - U(none/memory), g 3 | +0.2603 [+0.2447, +0.2759] | +0.2769, +0.2437 | 128 of 128 | +0.3016 | +0.2049 | +0.2674 |
| R-raise-none-body-U_v-3 | U_v(raise/body) - U_v(none/body), g 3 | +0.0082 [+0.0024, +0.0140] | +0.0099, +0.0065 | 128 of 128 | -0.0300 | +0.0756 | -0.0064 |
| R-raise-none-body-q_r-3 | q_r(raise/body) - q_r(none/body), g 3 | -0.0480 [-0.0507, -0.0452] | -0.0489, -0.0470 | 128 of 128 | -0.0526 | -0.0860 | -0.0266 |
| R-raise-none-body-a_v-3 | a_v(raise/body) - a_v(none/body), g 3 | +0.0157 [+0.0123, +0.0191] | +0.0147, +0.0167 | 128 of 128 | -0.0148 | +0.0835 | -0.0029 |
| R-raise-none-body-U-3 | U(raise/body) - U(none/body), g 3 | -0.0206 [-0.0235, -0.0177] | -0.0204, -0.0207 | 128 of 128 | -0.0181 | -0.0524 | -0.0059 |
| R-relax-none-body-U_v-3 | U_v(relax/body) - U_v(none/body), g 3 | -0.0346 [-0.0402, -0.0289] | -0.0347, -0.0345 | 128 of 128 | +0.0209 | -0.0786 | -0.0403 |
| R-relax-none-body-q_r-3 | q_r(relax/body) - q_r(none/body), g 3 | +0.0228 [+0.0204, +0.0252] | +0.0237, +0.0218 | 128 of 128 | +0.0191 | +0.0489 | +0.0115 |
| R-relax-none-body-a_v-3 | a_v(relax/body) - a_v(none/body), g 3 | -0.0662 [-0.0717, -0.0607] | -0.0625, -0.0699 | 128 of 128 | -0.0382 | -0.1070 | -0.0598 |
| R-relax-none-body-U-3 | U(relax/body) - U(none/body), g 3 | +0.0057 [+0.0034, +0.0081] | +0.0052, +0.0063 | 128 of 128 | +0.0004 | +0.0199 | +0.0013 |
| R-relax-raise-memory-U_v-3 | U_v(relax/memory) - U_v(raise/memory), g 3 | +0.3484 [+0.3329, +0.3638] | +0.3639, +0.3328 | 128 of 128 | +0.4866 | +0.1526 | +0.3771 |
| R-relax-raise-memory-q_r-3 | q_r(relax/memory) - q_r(raise/memory), g 3 | +0.1026 [+0.0963, +0.1089] | +0.1085, +0.0967 | 128 of 128 | +0.1122 | +0.1390 | +0.0795 |
| R-relax-raise-memory-a_v-3 | a_v(relax/memory) - a_v(raise/memory), g 3 | -0.0642 [-0.0723, -0.0561] | -0.0576, -0.0707 | 128 of 128 | +0.0032 | -0.1702 | -0.0449 |
| R-relax-raise-memory-U-3 | U(relax/memory) - U(raise/memory), g 3 | +0.3745 [+0.3556, +0.3935] | +0.3936, +0.3555 | 128 of 128 | +0.3966 | +0.2864 | +0.4076 |
| R-relax-raise-body-U_v-3 | U_v(relax/body) - U_v(raise/body), g 3 | -0.0427 [-0.0532, -0.0323] | -0.0445, -0.0410 | 128 of 128 | +0.0509 | -0.1542 | -0.0338 |
| R-relax-raise-body-q_r-3 | q_r(relax/body) - q_r(raise/body), g 3 | +0.0707 [+0.0670, +0.0744] | +0.0726, +0.0688 | 128 of 128 | +0.0717 | +0.1349 | +0.0381 |
| R-relax-raise-body-a_v-3 | a_v(relax/body) - a_v(raise/body), g 3 | -0.0819 [-0.0905, -0.0734] | -0.0772, -0.0867 | 128 of 128 | -0.0234 | -0.1905 | -0.0569 |
| R-relax-raise-body-U-3 | U(relax/body) - U(raise/body), g 3 | +0.0263 [+0.0226, +0.0300] | +0.0256, +0.0270 | 128 of 128 | +0.0185 | +0.0723 | +0.0072 |
| R-matched-none-memory-U_v-3 | U_v(relax-matched/memory) - U_v(none/memory), g 3 | +0.1879 [+0.1754, +0.2003] | +0.1990, +0.1767 | 128 of 128 | +0.2993 | +0.1085 | +0.1718 |
| R-matched-none-memory-q_r-3 | q_r(relax-matched/memory) - q_r(none/memory), g 3 | +0.0413 [+0.0370, +0.0455] | +0.0434, +0.0392 | 128 of 128 | +0.0504 | +0.0580 | +0.0283 |
| R-matched-none-memory-a_v-3 | a_v(relax-matched/memory) - a_v(none/memory), g 3 | -0.0360 [-0.0417, -0.0302] | -0.0319, -0.0401 | 128 of 128 | -0.0056 | -0.0848 | -0.0268 |
| R-matched-none-memory-U-3 | U(relax-matched/memory) - U(none/memory), g 3 | +0.2123 [+0.1977, +0.2269] | +0.2250, +0.1996 | 128 of 128 | +0.2800 | +0.1743 | +0.1974 |
| R-matched-relax-memory-U_v-3 | U_v(relax-matched/memory) - U_v(relax/memory), g 3 | -0.0299 [-0.0368, -0.0231] | -0.0314, -0.0284 | 128 of 128 | -0.0282 | -0.0184 | -0.0365 |
| R-matched-relax-memory-q_r-3 | q_r(relax-matched/memory) - q_r(relax/memory), g 3 | -0.0097 [-0.0119, -0.0074] | -0.0117, -0.0076 | 128 of 128 | -0.0057 | -0.0081 | -0.0124 |
| R-matched-relax-memory-a_v-3 | a_v(relax-matched/memory) - a_v(relax/memory), g 3 | +0.0220 [+0.0185, +0.0255] | +0.0211, +0.0229 | 128 of 128 | +0.0128 | +0.0151 | +0.0301 |
| R-matched-relax-memory-U-3 | U(relax-matched/memory) - U(relax/memory), g 3 | -0.0480 [-0.0551, -0.0410] | -0.0519, -0.0442 | 128 of 128 | -0.0216 | -0.0306 | -0.0699 |
| R-inter-q_r-3 | the interaction in q_r, g 3 | +0.0037 [+0.0012, +0.0062] | +0.0045, +0.0029 | 128 of 128 | +0.0034 | -0.0131 | +0.0122 |
| R-raise-none-memory-U_v-8 | U_v(raise/memory) - U_v(none/memory), g 8 | -0.1211 [-0.1320, -0.1102] | -0.1255, -0.1167 | 128 of 128 | -0.1289 | +0.0129 | -0.1841 |
| R-raise-none-memory-q_r-8 | q_r(raise/memory) - q_r(none/memory), g 8 | -0.0945 [-0.1000, -0.0890] | -0.0966, -0.0923 | 128 of 128 | -0.1044 | -0.1058 | -0.0838 |
| R-raise-none-memory-a_v-8 | a_v(raise/memory) - a_v(none/memory), g 8 | -0.0333 [-0.0369, -0.0298] | -0.0356, -0.0310 | 128 of 128 | -0.0581 | -0.0013 | -0.0370 |
| R-raise-none-memory-U-8 | U(raise/memory) - U(none/memory), g 8 | -0.0943 [-0.1044, -0.0842] | -0.0993, -0.0893 | 128 of 128 | -0.0793 | -0.0089 | -0.1444 |
| R-relax-none-memory-U_v-8 | U_v(relax/memory) - U_v(none/memory), g 8 | +0.2132 [+0.2037, +0.2226] | +0.2153, +0.2111 | 128 of 128 | +0.2997 | +0.1433 | +0.2049 |
| R-relax-none-memory-q_r-8 | q_r(relax/memory) - q_r(none/memory), g 8 | +0.1150 [+0.1079, +0.1222] | +0.1189, +0.1112 | 128 of 128 | +0.1300 | +0.1400 | +0.0951 |
| R-relax-none-memory-a_v-8 | a_v(relax/memory) - a_v(none/memory), g 8 | -0.0335 [-0.0374, -0.0296] | -0.0319, -0.0351 | 128 of 128 | +0.0263 | -0.0520 | -0.0541 |
| R-relax-none-memory-U-8 | U(relax/memory) - U(none/memory), g 8 | +0.2780 [+0.2677, +0.2882] | +0.2838, +0.2721 | 128 of 128 | +0.2939 | +0.2256 | +0.2962 |
| R-raise-none-body-U_v-8 | U_v(raise/body) - U_v(none/body), g 8 | -0.0203 [-0.0253, -0.0152] | -0.0171, -0.0234 | 128 of 128 | -0.0538 | +0.0087 | -0.0180 |
| R-raise-none-body-q_r-8 | q_r(raise/body) - q_r(none/body), g 8 | -0.0968 [-0.1016, -0.0919] | -0.0968, -0.0967 | 128 of 128 | -0.1154 | -0.1498 | -0.0609 |
| R-raise-none-body-a_v-8 | a_v(raise/body) - a_v(none/body), g 8 | -0.0190 [-0.0230, -0.0151] | -0.0205, -0.0176 | 128 of 128 | -0.0511 | +0.0064 | -0.0157 |
| R-raise-none-body-U-8 | U(raise/body) - U(none/body), g 8 | -0.0461 [-0.0493, -0.0429] | -0.0441, -0.0481 | 128 of 128 | -0.0469 | -0.1000 | -0.0187 |
| R-relax-none-body-U_v-8 | U_v(relax/body) - U_v(none/body), g 8 | -0.0533 [-0.0590, -0.0476] | -0.0539, -0.0528 | 128 of 128 | -0.0073 | -0.0649 | -0.0705 |
| R-relax-none-body-q_r-8 | q_r(relax/body) - q_r(none/body), g 8 | +0.0536 [+0.0495, +0.0576] | +0.0559, +0.0512 | 128 of 128 | +0.0488 | +0.1124 | +0.0266 |
| R-relax-none-body-a_v-8 | a_v(relax/body) - a_v(none/body), g 8 | -0.0632 [-0.0677, -0.0587] | -0.0617, -0.0648 | 128 of 128 | -0.0230 | -0.0742 | -0.0779 |
| R-relax-none-body-U-8 | U(relax/body) - U(none/body), g 8 | +0.0174 [+0.0151, +0.0196] | +0.0180, +0.0167 | 128 of 128 | +0.0078 | +0.0503 | +0.0057 |
| R-relax-raise-memory-U_v-8 | U_v(relax/memory) - U_v(raise/memory), g 8 | +0.3342 [+0.3233, +0.3452] | +0.3408, +0.3277 | 128 of 128 | +0.4286 | +0.1304 | +0.3890 |
| R-relax-raise-memory-q_r-8 | q_r(relax/memory) - q_r(raise/memory), g 8 | +0.2095 [+0.2000, +0.2190] | +0.2155, +0.2035 | 128 of 128 | +0.2344 | +0.2458 | +0.1789 |
| R-relax-raise-memory-a_v-8 | a_v(relax/memory) - a_v(raise/memory), g 8 | -0.0002 [-0.0052, +0.0049] | +0.0038, -0.0041 | 128 of 128 | +0.0844 | -0.0507 | -0.0172 |
| R-relax-raise-memory-U-8 | U(relax/memory) - U(raise/memory), g 8 | +0.3722 [+0.3587, +0.3858] | +0.3831, +0.3614 | 128 of 128 | +0.3732 | +0.2345 | +0.4406 |
| R-relax-raise-body-U_v-8 | U_v(relax/body) - U_v(raise/body), g 8 | -0.0331 [-0.0410, -0.0251] | -0.0368, -0.0293 | 128 of 128 | +0.0465 | -0.0736 | -0.0526 |
| R-relax-raise-body-q_r-8 | q_r(relax/body) - q_r(raise/body), g 8 | +0.1503 [+0.1446, +0.1560] | +0.1528, +0.1479 | 128 of 128 | +0.1642 | +0.2622 | +0.0875 |
| R-relax-raise-body-a_v-8 | a_v(relax/body) - a_v(raise/body), g 8 | -0.0442 [-0.0497, -0.0387] | -0.0412, -0.0472 | 128 of 128 | +0.0281 | -0.0806 | -0.0622 |
| R-relax-raise-body-U-8 | U(relax/body) - U(raise/body), g 8 | +0.0634 [+0.0592, +0.0677] | +0.0621, +0.0648 | 128 of 128 | +0.0547 | +0.1503 | +0.0244 |
| R-matched-none-memory-U_v-8 | U_v(relax-matched/memory) - U_v(none/memory), g 8 | +0.1831 [+0.1724, +0.1937] | +0.1869, +0.1793 | 128 of 128 | +0.2635 | +0.1095 | +0.1796 |
| R-matched-none-memory-q_r-8 | q_r(relax-matched/memory) - q_r(none/memory), g 8 | +0.0920 [+0.0855, +0.0985] | +0.0928, +0.0912 | 128 of 128 | +0.1136 | +0.1116 | +0.0714 |
| R-matched-none-memory-a_v-8 | a_v(relax-matched/memory) - a_v(none/memory), g 8 | -0.0085 [-0.0128, -0.0043] | -0.0058, -0.0113 | 128 of 128 | +0.0310 | -0.0413 | -0.0119 |
| R-matched-none-memory-U-8 | U(relax-matched/memory) - U(none/memory), g 8 | +0.2210 [+0.2107, +0.2313] | +0.2268, +0.2152 | 128 of 128 | +0.2590 | +0.1794 | +0.2228 |
| R-matched-relax-memory-U_v-8 | U_v(relax-matched/memory) - U_v(relax/memory), g 8 | -0.0301 [-0.0360, -0.0242] | -0.0284, -0.0318 | 128 of 128 | -0.0361 | -0.0338 | -0.0253 |
| R-matched-relax-memory-q_r-8 | q_r(relax-matched/memory) - q_r(relax/memory), g 8 | -0.0230 [-0.0269, -0.0192] | -0.0261, -0.0200 | 128 of 128 | -0.0164 | -0.0284 | -0.0237 |
| R-matched-relax-memory-a_v-8 | a_v(relax-matched/memory) - a_v(relax/memory), g 8 | +0.0250 [+0.0218, +0.0281] | +0.0261, +0.0238 | 128 of 128 | +0.0047 | +0.0107 | +0.0422 |
| R-matched-relax-memory-U-8 | U(relax-matched/memory) - U(relax/memory), g 8 | -0.0570 [-0.0623, -0.0516] | -0.0571, -0.0569 | 128 of 128 | -0.0349 | -0.0462 | -0.0734 |
| R-inter-q_r-8 | the interaction in q_r, g 8 | -0.0023 [-0.0079, +0.0034] | -0.0002, -0.0043 | 128 of 128 | -0.0110 | -0.0440 | +0.0229 |
| R-raise-none-memory-fresh-U_v-8 | the fresh successor's U_v, raise/memory - none/memory, after g 8 | -0.0549 [-0.0640, -0.0458] | -0.0541, -0.0558 | 128 of 128 | -0.0479 | +0.0045 | -0.0882 |
| R-raise-none-memory-fresh-q_r-8 | the fresh successor's q_r, raise/memory - none/memory, after g 8 | -0.0927 [-0.0981, -0.0873] | -0.0949, -0.0904 | 128 of 128 | -0.1032 | -0.1034 | -0.0821 |
| R-raise-none-memory-fresh-a_v-8 | the fresh successor's a_v, raise/memory - none/memory, after g 8 | -0.0372 [-0.0394, -0.0350] | -0.0381, -0.0363 | 128 of 128 | -0.0410 | -0.0408 | -0.0335 |
| R-raise-none-memory-fresh-q_v-8 | the fresh successor's q_v, raise/memory - none/memory, after g 8 | -0.0846 [-0.0906, -0.0786] | -0.0871, -0.0820 | 128 of 128 | -0.0923 | -0.0821 | -0.0819 |
| R-relax-none-memory-fresh-U_v-8 | the fresh successor's U_v, relax/memory - none/memory, after g 8 | +0.2293 [+0.2189, +0.2397] | +0.2334, +0.2252 | 128 of 128 | +0.2520 | +0.1609 | +0.2521 |
| R-relax-none-memory-fresh-q_r-8 | the fresh successor's q_r, relax/memory - none/memory, after g 8 | +0.1120 [+0.1056, +0.1183] | +0.1151, +0.1089 | 128 of 128 | +0.1260 | +0.1337 | +0.0941 |
| R-relax-none-memory-fresh-a_v-8 | the fresh successor's a_v, relax/memory - none/memory, after g 8 | +0.0487 [+0.0464, +0.0511] | +0.0506, +0.0469 | 128 of 128 | +0.0543 | +0.0415 | +0.0496 |
| R-relax-none-memory-fresh-q_v-8 | the fresh successor's q_v, relax/memory - none/memory, after g 8 | +0.1153 [+0.1081, +0.1226] | +0.1218, +0.1089 | 128 of 128 | +0.1248 | +0.1233 | +0.1066 |
| R-raise-none-body-fresh-U_v-8 | the fresh successor's U_v, raise/body - none/body, after g 8 | -0.0284 [-0.0324, -0.0244] | -0.0249, -0.0319 | 128 of 128 | -0.0343 | -0.0464 | -0.0165 |
| R-raise-none-body-fresh-q_r-8 | the fresh successor's q_r, raise/body - none/body, after g 8 | -0.0931 [-0.0978, -0.0883] | -0.0935, -0.0927 | 128 of 128 | -0.1118 | -0.1423 | -0.0591 |
| R-raise-none-body-fresh-a_v-8 | the fresh successor's a_v, raise/body - none/body, after g 8 | -0.0309 [-0.0326, -0.0292] | -0.0308, -0.0309 | 128 of 128 | -0.0365 | -0.0527 | -0.0172 |
| R-raise-none-body-fresh-q_v-8 | the fresh successor's q_v, raise/body - none/body, after g 8 | -0.0794 [-0.0849, -0.0738] | -0.0796, -0.0791 | 128 of 128 | -0.0990 | -0.1092 | -0.0546 |
| R-relax-none-body-fresh-U_v-8 | the fresh successor's U_v, relax/body - none/body, after g 8 | +0.0123 [+0.0091, +0.0155] | +0.0139, +0.0107 | 128 of 128 | +0.0071 | +0.0276 | +0.0072 |
| R-relax-none-body-fresh-q_r-8 | the fresh successor's q_r, relax/body - none/body, after g 8 | +0.0511 [+0.0472, +0.0549] | +0.0536, +0.0486 | 128 of 128 | +0.0461 | +0.1097 | +0.0242 |
| R-relax-none-body-fresh-a_v-8 | the fresh successor's a_v, relax/body - none/body, after g 8 | +0.0145 [+0.0134, +0.0156] | +0.0155, +0.0135 | 128 of 128 | +0.0093 | +0.0304 | +0.0092 |
| R-relax-none-body-fresh-q_v-8 | the fresh successor's q_v, relax/body - none/body, after g 8 | +0.0557 [+0.0508, +0.0607] | +0.0596, +0.0519 | 128 of 128 | +0.0426 | +0.1205 | +0.0299 |
| R-matched-none-memory-fresh-U_v-8 | the fresh successor's U_v, relax-matched/memory - none/memory, after g 8 | +0.1782 [+0.1676, +0.1887] | +0.1831, +0.1732 | 128 of 128 | +0.2212 | +0.1258 | +0.1828 |
| R-matched-none-memory-fresh-q_r-8 | the fresh successor's q_r, relax-matched/memory - none/memory, after g 8 | +0.0889 [+0.0829, +0.0948] | +0.0893, +0.0885 | 128 of 128 | +0.1113 | +0.1050 | +0.0696 |
| R-matched-none-memory-fresh-a_v-8 | the fresh successor's a_v, relax-matched/memory - none/memory, after g 8 | +0.0388 [+0.0365, +0.0411] | +0.0404, +0.0371 | 128 of 128 | +0.0488 | +0.0356 | +0.0354 |
| R-matched-none-memory-fresh-q_v-8 | the fresh successor's q_v, relax-matched/memory - none/memory, after g 8 | +0.0879 [+0.0817, +0.0942] | +0.0909, +0.0850 | 128 of 128 | +0.1098 | +0.0947 | +0.0736 |
| R-matched-relax-memory-fresh-U_v-8 | the fresh successor's U_v, relax-matched/memory - relax/memory, after g 8 | -0.0511 [-0.0567, -0.0456] | -0.0503, -0.0519 | 128 of 128 | -0.0308 | -0.0351 | -0.0693 |
| R-matched-relax-memory-fresh-q_r-8 | the fresh successor's q_r, relax-matched/memory - relax/memory, after g 8 | -0.0231 [-0.0268, -0.0193] | -0.0258, -0.0204 | 128 of 128 | -0.0146 | -0.0287 | -0.0245 |
| R-matched-relax-memory-fresh-a_v-8 | the fresh successor's a_v, relax-matched/memory - relax/memory, after g 8 | -0.0100 [-0.0112, -0.0087] | -0.0101, -0.0098 | 128 of 128 | -0.0055 | -0.0058 | -0.0143 |
| R-matched-relax-memory-fresh-q_v-8 | the fresh successor's q_v, relax-matched/memory - relax/memory, after g 8 | -0.0274 [-0.0326, -0.0222] | -0.0309, -0.0239 | 128 of 128 | -0.0150 | -0.0286 | -0.0331 |
| R-inter-fresh-U_v-8 | the interaction in the fresh successor's U_v, after g 8 | +0.0265 [+0.0155, +0.0376] | +0.0291, +0.0239 | 128 of 128 | +0.0135 | -0.0509 | +0.0717 |
| R-agree_pre-raise-none-body-1 | the observer's agreement at 'pre', raise/body - none/body, g 1 | +0.0491 [+0.0401, +0.0580] | +0.0470, +0.0511 | 128 of 128 | +0.0120 | +0.1719 | +0.0062 |
| R-agree_pre-relax-none-body-1 | the observer's agreement at 'pre', relax/body - none/body, g 1 | -0.0756 [-0.0841, -0.0672] | -0.0721, -0.0791 | 128 of 128 | -0.0493 | -0.1433 | -0.0549 |
| R-agree_pre-raise-none-memory-1 | the observer's agreement at 'pre', raise/memory - none/memory, g 1 | +0.0989 [+0.0863, +0.1116] | +0.0999, +0.0980 | 128 of 128 | +0.1453 | +0.0269 | +0.1118 |
| R-agree_pre-relax-none-memory-1 | the observer's agreement at 'pre', relax/memory - none/memory, g 1 | -0.2192 [-0.2359, -0.2025] | -0.2241, -0.2142 | 128 of 128 | -0.3357 | -0.0913 | -0.2249 |
| R-agree_pre-matched-none-memory-1 | the observer's agreement at 'pre', relax-matched/memory - none/memory, g 1 | -0.1672 [-0.1825, -0.1518] | -0.1696, -0.1648 | 128 of 128 | -0.2783 | -0.0710 | -0.1597 |
| R-agree_p80-raise-none-body-1 | the observer's agreement at 'p80', raise/body - none/body, g 1 | +0.0557 [+0.0475, +0.0639] | +0.0536, +0.0579 | 128 of 128 | +0.0117 | +0.1941 | +0.0085 |
| R-agree_p80-relax-none-body-1 | the observer's agreement at 'p80', relax/body - none/body, g 1 | -0.1197 [-0.1328, -0.1066] | -0.1125, -0.1268 | 128 of 128 | -0.0613 | -0.1724 | -0.1226 |
| R-agree_p80-raise-none-memory-1 | the observer's agreement at 'p80', raise/memory - none/memory, g 1 | +0.0927 [+0.0805, +0.1049] | +0.0903, +0.0951 | 128 of 128 | +0.1428 | +0.0217 | +0.1031 |
| R-agree_p80-relax-none-memory-1 | the observer's agreement at 'p80', relax/memory - none/memory, g 1 | -0.2123 [-0.2295, -0.1952] | -0.2181, -0.2065 | 128 of 128 | -0.3232 | -0.1021 | -0.2120 |
| R-agree_p80-matched-none-memory-1 | the observer's agreement at 'p80', relax-matched/memory - none/memory, g 1 | -0.1612 [-0.1769, -0.1455] | -0.1617, -0.1606 | 128 of 128 | -0.2712 | -0.0781 | -0.1477 |
| R-agree_p16-raise-none-body-1 | the observer's agreement at 'p16', raise/body - none/body, g 1 | +0.0512 [+0.0416, +0.0609] | +0.0538, +0.0486 | 128 of 128 | +0.0154 | +0.1729 | +0.0083 |
| R-agree_p16-relax-none-body-1 | the observer's agreement at 'p16', relax/body - none/body, g 1 | -0.0933 [-0.1034, -0.0831] | -0.0881, -0.0984 | 128 of 128 | -0.0547 | -0.1455 | -0.0864 |
| R-agree_p16-raise-none-memory-1 | the observer's agreement at 'p16', raise/memory - none/memory, g 1 | +0.0771 [+0.0666, +0.0876] | +0.0688, +0.0853 | 128 of 128 | +0.1335 | +0.0396 | +0.0676 |
| R-agree_p16-relax-none-memory-1 | the observer's agreement at 'p16', relax/memory - none/memory, g 1 | -0.1642 [-0.1785, -0.1500] | -0.1708, -0.1577 | 128 of 128 | -0.2222 | -0.1135 | -0.1606 |
| R-agree_p16-matched-none-memory-1 | the observer's agreement at 'p16', relax-matched/memory - none/memory, g 1 | -0.1356 [-0.1502, -0.1211] | -0.1401, -0.1311 | 128 of 128 | -0.2051 | -0.0876 | -0.1249 |
| R-agree_p4-raise-none-body-1 | the observer's agreement at 'p4', raise/body - none/body, g 1 | +0.0505 [+0.0416, +0.0594] | +0.0529, +0.0481 | 128 of 128 | +0.0132 | +0.1765 | +0.0061 |
| R-agree_p4-relax-none-body-1 | the observer's agreement at 'p4', relax/body - none/body, g 1 | -0.0894 [-0.0992, -0.0796] | -0.0847, -0.0941 | 128 of 128 | -0.0493 | -0.1497 | -0.0793 |
| R-agree_p4-raise-none-memory-1 | the observer's agreement at 'p4', raise/memory - none/memory, g 1 | +0.0623 [+0.0542, +0.0705] | +0.0591, +0.0656 | 128 of 128 | +0.1104 | +0.0652 | +0.0369 |
| R-agree_p4-relax-none-memory-1 | the observer's agreement at 'p4', relax/memory - none/memory, g 1 | -0.1080 [-0.1234, -0.0925] | -0.1093, -0.1067 | 128 of 128 | -0.0554 | -0.1487 | -0.1139 |
| R-agree_p4-matched-none-memory-1 | the observer's agreement at 'p4', relax-matched/memory - none/memory, g 1 | -0.0945 [-0.1098, -0.0792] | -0.0962, -0.0929 | 128 of 128 | -0.0615 | -0.1248 | -0.0959 |
| R-agree_end-raise-none-body-1 | the observer's agreement at 'end', raise/body - none/body, g 1 | +0.0498 [+0.0414, +0.0582] | +0.0470, +0.0526 | 128 of 128 | +0.0154 | +0.1663 | +0.0088 |
| R-agree_end-relax-none-body-1 | the observer's agreement at 'end', relax/body - none/body, g 1 | -0.0889 [-0.0998, -0.0779] | -0.0905, -0.0873 | 128 of 128 | -0.0479 | -0.1577 | -0.0750 |
| R-agree_end-raise-none-memory-1 | the observer's agreement at 'end', raise/memory - none/memory, g 1 | +0.0563 [+0.0466, +0.0659] | +0.0560, +0.0565 | 128 of 128 | +0.0813 | +0.0969 | +0.0234 |
| R-agree_end-relax-none-memory-1 | the observer's agreement at 'end', relax/memory - none/memory, g 1 | -0.0886 [-0.1045, -0.0727] | -0.0853, -0.0919 | 128 of 128 | +0.0042 | -0.1897 | -0.0845 |
| R-agree_end-matched-none-memory-1 | the observer's agreement at 'end', relax-matched/memory - none/memory, g 1 | -0.0711 [-0.0886, -0.0537] | -0.0693, -0.0729 | 128 of 128 | +0.0100 | -0.1531 | -0.0707 |
| R-agree_pre-raise-none-body-3 | the observer's agreement at 'pre', raise/body - none/body, g 3 | +0.0521 [+0.0441, +0.0601] | +0.0490, +0.0553 | 128 of 128 | +0.0183 | +0.1697 | +0.0103 |
| R-agree_pre-relax-none-body-3 | the observer's agreement at 'pre', relax/body - none/body, g 3 | -0.0767 [-0.0880, -0.0654] | -0.0782, -0.0752 | 128 of 128 | -0.0564 | -0.1331 | -0.0587 |
| R-agree_pre-raise-none-memory-3 | the observer's agreement at 'pre', raise/memory - none/memory, g 3 | +0.1093 [+0.0954, +0.1231] | +0.1132, +0.1053 | 128 of 128 | +0.1519 | +0.0237 | +0.1307 |
| R-agree_pre-relax-none-memory-3 | the observer's agreement at 'pre', relax/memory - none/memory, g 3 | -0.2167 [-0.2383, -0.1951] | -0.2170, -0.2163 | 128 of 128 | -0.3054 | -0.0901 | -0.2356 |
| R-agree_pre-matched-none-memory-3 | the observer's agreement at 'pre', relax-matched/memory - none/memory, g 3 | -0.1654 [-0.1817, -0.1491] | -0.1603, -0.1705 | 128 of 128 | -0.2437 | -0.0652 | -0.1764 |
| R-agree_p80-raise-none-body-3 | the observer's agreement at 'p80', raise/body - none/body, g 3 | +0.0563 [+0.0461, +0.0664] | +0.0502, +0.0624 | 128 of 128 | +0.0195 | +0.1736 | +0.0160 |
| R-agree_p80-relax-none-body-3 | the observer's agreement at 'p80', relax/body - none/body, g 3 | -0.1281 [-0.1444, -0.1118] | -0.1224, -0.1338 | 128 of 128 | -0.0647 | -0.1624 | -0.1427 |
| R-agree_p80-raise-none-memory-3 | the observer's agreement at 'p80', raise/memory - none/memory, g 3 | +0.1033 [+0.0902, +0.1164] | +0.1107, +0.0959 | 128 of 128 | +0.1462 | +0.0271 | +0.1200 |
| R-agree_p80-relax-none-memory-3 | the observer's agreement at 'p80', relax/memory - none/memory, g 3 | -0.2045 [-0.2274, -0.1817] | -0.2010, -0.2080 | 128 of 128 | -0.2869 | -0.0859 | -0.2227 |
| R-agree_p80-matched-none-memory-3 | the observer's agreement at 'p80', relax-matched/memory - none/memory, g 3 | -0.1574 [-0.1734, -0.1414] | -0.1482, -0.1666 | 128 of 128 | -0.2349 | -0.0623 | -0.1663 |
| R-agree_p16-raise-none-body-3 | the observer's agreement at 'p16', raise/body - none/body, g 3 | +0.0516 [+0.0416, +0.0616] | +0.0447, +0.0586 | 128 of 128 | +0.0188 | +0.1658 | +0.0110 |
| R-agree_p16-relax-none-body-3 | the observer's agreement at 'p16', relax/body - none/body, g 3 | -0.0962 [-0.1092, -0.0831] | -0.0956, -0.0968 | 128 of 128 | -0.0508 | -0.1404 | -0.0968 |
| R-agree_p16-raise-none-memory-3 | the observer's agreement at 'p16', raise/memory - none/memory, g 3 | +0.0844 [+0.0703, +0.0985] | +0.0928, +0.0760 | 128 of 128 | +0.1348 | +0.0298 | +0.0865 |
| R-agree_p16-relax-none-memory-3 | the observer's agreement at 'p16', relax/memory - none/memory, g 3 | -0.1611 [-0.1817, -0.1405] | -0.1565, -0.1656 | 128 of 128 | -0.2175 | -0.1145 | -0.1561 |
| R-agree_p16-matched-none-memory-3 | the observer's agreement at 'p16', relax-matched/memory - none/memory, g 3 | -0.1279 [-0.1463, -0.1095] | -0.1211, -0.1348 | 128 of 128 | -0.1885 | -0.0872 | -0.1180 |
| R-agree_p4-raise-none-body-3 | the observer's agreement at 'p4', raise/body - none/body, g 3 | +0.0491 [+0.0398, +0.0583] | +0.0479, +0.0503 | 128 of 128 | +0.0173 | +0.1584 | +0.0103 |
| R-agree_p4-relax-none-body-3 | the observer's agreement at 'p4', relax/body - none/body, g 3 | -0.0970 [-0.1088, -0.0851] | -0.0968, -0.0972 | 128 of 128 | -0.0535 | -0.1570 | -0.0887 |
| R-agree_p4-raise-none-memory-3 | the observer's agreement at 'p4', raise/memory - none/memory, g 3 | +0.0725 [+0.0638, +0.0812] | +0.0795, +0.0656 | 128 of 128 | +0.1243 | +0.0518 | +0.0570 |
| R-agree_p4-relax-none-memory-3 | the observer's agreement at 'p4', relax/memory - none/memory, g 3 | -0.1072 [-0.1260, -0.0885] | -0.1117, -0.1028 | 128 of 128 | -0.0740 | -0.1453 | -0.1049 |
| R-agree_p4-matched-none-memory-3 | the observer's agreement at 'p4', relax-matched/memory - none/memory, g 3 | -0.0804 [-0.0989, -0.0620] | -0.0845, -0.0764 | 128 of 128 | -0.0864 | -0.1042 | -0.0656 |
| R-agree_end-raise-none-body-3 | the observer's agreement at 'end', raise/body - none/body, g 3 | +0.0461 [+0.0374, +0.0548] | +0.0425, +0.0497 | 128 of 128 | +0.0107 | +0.1597 | +0.0070 |
| R-agree_end-relax-none-body-3 | the observer's agreement at 'end', relax/body - none/body, g 3 | -0.0934 [-0.1059, -0.0810] | -0.0933, -0.0936 | 128 of 128 | -0.0513 | -0.1477 | -0.0874 |
| R-agree_end-raise-none-memory-3 | the observer's agreement at 'end', raise/memory - none/memory, g 3 | +0.0548 [+0.0442, +0.0654] | +0.0552, +0.0544 | 128 of 128 | +0.0720 | +0.0691 | +0.0391 |
| R-agree_end-relax-none-memory-3 | the observer's agreement at 'end', relax/memory - none/memory, g 3 | -0.0882 [-0.1041, -0.0723] | -0.0896, -0.0868 | 128 of 128 | -0.0171 | -0.1670 | -0.0844 |
| R-agree_end-matched-none-memory-3 | the observer's agreement at 'end', relax-matched/memory - none/memory, g 3 | -0.0593 [-0.0743, -0.0443] | -0.0664, -0.0522 | 128 of 128 | -0.0063 | -0.1387 | -0.0461 |
| R-agree_pre-raise-none-body-8 | the observer's agreement at 'pre', raise/body - none/body, g 8 | +0.0462 [+0.0375, +0.0550] | +0.0500, +0.0424 | 128 of 128 | +0.0281 | +0.1372 | +0.0098 |
| R-agree_pre-relax-none-body-8 | the observer's agreement at 'pre', relax/body - none/body, g 8 | -0.0826 [-0.0941, -0.0711] | -0.0874, -0.0778 | 128 of 128 | -0.0503 | -0.1694 | -0.0553 |
| R-agree_pre-raise-none-memory-8 | the observer's agreement at 'pre', raise/memory - none/memory, g 8 | +0.1283 [+0.1106, +0.1460] | +0.1331, +0.1235 | 128 of 128 | +0.1467 | +0.0579 | +0.1543 |
| R-agree_pre-relax-none-memory-8 | the observer's agreement at 'pre', relax/memory - none/memory, g 8 | -0.2167 [-0.2359, -0.1974] | -0.2137, -0.2196 | 128 of 128 | -0.2952 | -0.0815 | -0.2450 |
| R-agree_pre-matched-none-memory-8 | the observer's agreement at 'pre', relax-matched/memory - none/memory, g 8 | -0.1641 [-0.1816, -0.1466] | -0.1639, -0.1642 | 128 of 128 | -0.2295 | -0.0601 | -0.1833 |
| R-agree_p80-raise-none-body-8 | the observer's agreement at 'p80', raise/body - none/body, g 8 | +0.0551 [+0.0460, +0.0641] | +0.0521, +0.0580 | 128 of 128 | +0.0288 | +0.1621 | +0.0146 |
| R-agree_p80-relax-none-body-8 | the observer's agreement at 'p80', relax/body - none/body, g 8 | -0.1193 [-0.1335, -0.1051] | -0.1216, -0.1171 | 128 of 128 | -0.0586 | -0.1641 | -0.1273 |
| R-agree_p80-raise-none-memory-8 | the observer's agreement at 'p80', raise/memory - none/memory, g 8 | +0.1216 [+0.1057, +0.1375] | +0.1217, +0.1215 | 128 of 128 | +0.1482 | +0.0605 | +0.1388 |
| R-agree_p80-relax-none-memory-8 | the observer's agreement at 'p80', relax/memory - none/memory, g 8 | -0.2109 [-0.2302, -0.1917] | -0.2075, -0.2144 | 128 of 128 | -0.2891 | -0.0808 | -0.2369 |
| R-agree_p80-matched-none-memory-8 | the observer's agreement at 'p80', relax-matched/memory - none/memory, g 8 | -0.1631 [-0.1795, -0.1466] | -0.1644, -0.1617 | 128 of 128 | -0.2285 | -0.0637 | -0.1801 |
| R-agree_p16-raise-none-body-8 | the observer's agreement at 'p16', raise/body - none/body, g 8 | +0.0486 [+0.0413, +0.0560] | +0.0483, +0.0490 | 128 of 128 | +0.0249 | +0.1443 | +0.0127 |
| R-agree_p16-relax-none-body-8 | the observer's agreement at 'p16', relax/body - none/body, g 8 | -0.0990 [-0.1127, -0.0853] | -0.1072, -0.0908 | 128 of 128 | -0.0571 | -0.1582 | -0.0903 |
| R-agree_p16-raise-none-memory-8 | the observer's agreement at 'p16', raise/memory - none/memory, g 8 | +0.1012 [+0.0865, +0.1159] | +0.1012, +0.1012 | 128 of 128 | +0.1331 | +0.0586 | +0.1066 |
| R-agree_p16-relax-none-memory-8 | the observer's agreement at 'p16', relax/memory - none/memory, g 8 | -0.1672 [-0.1845, -0.1500] | -0.1665, -0.1680 | 128 of 128 | -0.2317 | -0.0881 | -0.1746 |
| R-agree_p16-matched-none-memory-8 | the observer's agreement at 'p16', relax-matched/memory - none/memory, g 8 | -0.1266 [-0.1421, -0.1112] | -0.1230, -0.1302 | 128 of 128 | -0.1841 | -0.0664 | -0.1281 |
| R-agree_p4-raise-none-body-8 | the observer's agreement at 'p4', raise/body - none/body, g 8 | +0.0494 [+0.0423, +0.0565] | +0.0493, +0.0494 | 128 of 128 | +0.0225 | +0.1531 | +0.0110 |
| R-agree_p4-relax-none-body-8 | the observer's agreement at 'p4', relax/body - none/body, g 8 | -0.0981 [-0.1115, -0.0848] | -0.1064, -0.0898 | 128 of 128 | -0.0542 | -0.1565 | -0.0909 |
| R-agree_p4-raise-none-memory-8 | the observer's agreement at 'p4', raise/memory - none/memory, g 8 | +0.0779 [+0.0678, +0.0879] | +0.0767, +0.0791 | 128 of 128 | +0.1128 | +0.0603 | +0.0692 |
| R-agree_p4-relax-none-memory-8 | the observer's agreement at 'p4', relax/memory - none/memory, g 8 | -0.1265 [-0.1432, -0.1098] | -0.1180, -0.1349 | 128 of 128 | -0.1169 | -0.1265 | -0.1312 |
| R-agree_p4-matched-none-memory-8 | the observer's agreement at 'p4', relax-matched/memory - none/memory, g 8 | -0.0935 [-0.1094, -0.0776] | -0.0931, -0.0939 | 128 of 128 | -0.1016 | -0.0957 | -0.0884 |
| R-agree_end-raise-none-body-8 | the observer's agreement at 'end', raise/body - none/body, g 8 | +0.0473 [+0.0393, +0.0553] | +0.0482, +0.0464 | 128 of 128 | +0.0225 | +0.1433 | +0.0117 |
| R-agree_end-relax-none-body-8 | the observer's agreement at 'end', relax/body - none/body, g 8 | -0.1059 [-0.1185, -0.0933] | -0.1111, -0.1007 | 128 of 128 | -0.0535 | -0.1726 | -0.0988 |
| R-agree_end-raise-none-memory-8 | the observer's agreement at 'end', raise/memory - none/memory, g 8 | +0.0593 [+0.0469, +0.0716] | +0.0582, +0.0603 | 128 of 128 | +0.0718 | +0.0449 | +0.0602 |
| R-agree_end-relax-none-memory-8 | the observer's agreement at 'end', relax/memory - none/memory, g 8 | -0.1121 [-0.1278, -0.0964] | -0.1166, -0.1077 | 128 of 128 | -0.0486 | -0.1614 | -0.1193 |
| R-agree_end-matched-none-memory-8 | the observer's agreement at 'end', relax-matched/memory - none/memory, g 8 | -0.0746 [-0.0928, -0.0565] | -0.0734, -0.0759 | 128 of 128 | -0.0403 | -0.1299 | -0.0642 |

## Levels: U_v by row and generation (all; native / particular / permissive)

| Row | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| none/memory | 0.335 (0.255 / 0.090 / 0.497) | 0.324 (0.299 / 0.109 / 0.445) | 0.334 (0.335 / 0.129 / 0.436) | 0.366 (0.384 / 0.172 / 0.453) |
| raise/memory | 0.335 (0.255 / 0.090 / 0.497) | 0.235 (0.158 / 0.110 / 0.337) | 0.203 (0.176 / 0.103 / 0.267) | 0.244 (0.255 / 0.185 / 0.269) |
| relax/memory | 0.335 (0.255 / 0.090 / 0.497) | 0.510 (0.626 / 0.214 / 0.600) | 0.552 (0.663 / 0.256 / 0.644) | 0.579 (0.683 / 0.315 / 0.658) |
| none/body | 0.335 (0.255 / 0.090 / 0.497) | 0.643 (0.629 / 0.442 / 0.751) | 0.784 (0.806 / 0.596 / 0.868) | 0.833 (0.864 / 0.645 / 0.911) |
| raise/body | 0.335 (0.255 / 0.090 / 0.497) | 0.660 (0.602 / 0.548 / 0.745) | 0.792 (0.776 / 0.671 / 0.861) | 0.812 (0.810 / 0.654 / 0.893) |
| relax/body | 0.335 (0.255 / 0.090 / 0.497) | 0.650 (0.732 / 0.398 / 0.735) | 0.750 (0.827 / 0.517 / 0.827) | 0.779 (0.857 / 0.580 / 0.840) |
| relax-matched/memory | 0.335 (0.255 / 0.090 / 0.497) | 0.479 (0.588 / 0.198 / 0.564) | 0.522 (0.634 / 0.237 / 0.608) | 0.549 (0.647 / 0.281 / 0.633) |

## Levels: q_r by row and generation (all; native / particular / permissive)

| Row | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| none/memory | 0.937 (0.937 / 0.918 / 0.947) | 0.873 (0.870 / 0.835 / 0.894) | 0.765 (0.753 / 0.701 / 0.804) | 0.534 (0.509 / 0.424 / 0.602) |
| raise/memory | 0.937 (0.937 / 0.918 / 0.947) | 0.852 (0.847 / 0.803 / 0.880) | 0.714 (0.697 / 0.628 / 0.765) | 0.440 (0.405 / 0.318 / 0.518) |
| relax/memory | 0.937 (0.937 / 0.918 / 0.947) | 0.893 (0.894 / 0.862 / 0.909) | 0.816 (0.809 / 0.767 / 0.845) | 0.649 (0.639 / 0.564 / 0.697) |
| none/body | 0.937 (0.937 / 0.918 / 0.947) | 0.902 (0.896 / 0.870 / 0.921) | 0.842 (0.826 / 0.792 / 0.876) | 0.707 (0.673 / 0.610 / 0.773) |
| raise/body | 0.937 (0.937 / 0.918 / 0.947) | 0.884 (0.877 / 0.835 / 0.912) | 0.794 (0.773 / 0.706 / 0.849) | 0.611 (0.558 / 0.460 / 0.712) |
| relax/body | 0.937 (0.937 / 0.918 / 0.947) | 0.911 (0.905 / 0.890 / 0.925) | 0.865 (0.845 / 0.840 / 0.887) | 0.761 (0.722 / 0.723 / 0.799) |
| relax-matched/memory | 0.937 (0.937 / 0.918 / 0.947) | 0.890 (0.891 / 0.859 / 0.905) | 0.807 (0.803 / 0.759 / 0.832) | 0.626 (0.623 / 0.535 / 0.674) |

## Levels: a_v by row and generation (all; native / particular / permissive)

| Row | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| none/memory | 0.928 (0.973 / 0.770 / 0.984) | 0.911 (0.953 / 0.754 / 0.968) | 0.878 (0.913 / 0.721 / 0.938) | 0.801 (0.823 / 0.646 / 0.867) |
| raise/memory | 0.928 (0.973 / 0.770 / 0.984) | 0.942 (0.950 / 0.881 / 0.968) | 0.884 (0.892 / 0.792 / 0.926) | 0.767 (0.765 / 0.645 / 0.830) |
| relax/memory | 0.928 (0.973 / 0.770 / 0.984) | 0.845 (0.918 / 0.635 / 0.913) | 0.820 (0.895 / 0.622 / 0.882) | 0.767 (0.849 / 0.594 / 0.813) |
| none/body | 0.928 (0.973 / 0.770 / 0.984) | 0.920 (0.964 / 0.759 / 0.979) | 0.906 (0.948 / 0.738 / 0.970) | 0.873 (0.908 / 0.690 / 0.946) |
| raise/body | 0.928 (0.973 / 0.770 / 0.984) | 0.955 (0.965 / 0.893 / 0.982) | 0.922 (0.933 / 0.821 / 0.967) | 0.854 (0.857 / 0.696 / 0.931) |
| relax/body | 0.928 (0.973 / 0.770 / 0.984) | 0.850 (0.922 / 0.638 / 0.920) | 0.840 (0.910 / 0.631 / 0.910) | 0.810 (0.885 / 0.616 / 0.869) |
| relax-matched/memory | 0.928 (0.973 / 0.770 / 0.984) | 0.863 (0.931 / 0.651 / 0.935) | 0.842 (0.908 / 0.637 / 0.912) | 0.792 (0.854 / 0.604 / 0.855) |

## Levels: U by row and generation (all; native / particular / permissive)

| Row | g 0 | g 1 | g 3 | g 8 |
|---|---|---|---|---|
| none/memory | 0.333 (0.157 / 0.221 / 0.476) | 0.314 (0.210 / 0.213 / 0.417) | 0.310 (0.251 / 0.211 / 0.389) | 0.335 (0.321 / 0.221 / 0.398) |
| raise/memory | 0.333 (0.157 / 0.221 / 0.476) | 0.230 (0.137 / 0.137 / 0.323) | 0.196 (0.156 / 0.130 / 0.248) | 0.240 (0.242 / 0.212 / 0.254) |
| relax/memory | 0.333 (0.157 / 0.221 / 0.476) | 0.498 (0.440 / 0.368 / 0.591) | 0.570 (0.553 / 0.416 / 0.656) | 0.613 (0.615 / 0.447 / 0.694) |
| none/body | 0.333 (0.157 / 0.221 / 0.476) | 0.667 (0.590 / 0.604 / 0.736) | 0.811 (0.779 / 0.762 / 0.852) | 0.847 (0.839 / 0.777 / 0.887) |
| raise/body | 0.333 (0.157 / 0.221 / 0.476) | 0.662 (0.589 / 0.589 / 0.735) | 0.791 (0.761 / 0.709 / 0.846) | 0.801 (0.792 / 0.677 / 0.868) |
| relax/body | 0.333 (0.157 / 0.221 / 0.476) | 0.668 (0.590 / 0.613 / 0.735) | 0.817 (0.780 / 0.781 / 0.853) | 0.865 (0.847 / 0.828 / 0.892) |
| relax-matched/memory | 0.333 (0.157 / 0.221 / 0.476) | 0.465 (0.425 / 0.346 / 0.545) | 0.522 (0.531 / 0.385 / 0.586) | 0.556 (0.580 / 0.400 / 0.621) |

## The fresh successors: U_v after generation g, field-free (all; native / particular / permissive)

| Row | after g 8 |
|---|---|
| none/memory | 0.377 (0.400 / 0.179 / 0.465) |
| raise/memory | 0.322 (0.352 / 0.184 / 0.377) |
| relax/memory | 0.607 (0.652 / 0.340 / 0.717) |
| none/body | 0.828 (0.859 / 0.638 / 0.907) |
| raise/body | 0.800 (0.824 / 0.592 / 0.891) |
| relax/body | 0.840 (0.866 / 0.666 / 0.915) |
| relax-matched/memory | 0.555 (0.621 / 0.305 / 0.648) |

## The fresh successors: q_r after generation g, field-free (all; native / particular / permissive)

| Row | after g 8 |
|---|---|
| none/memory | 0.518 (0.490 / 0.404 / 0.589) |
| raise/memory | 0.425 (0.387 / 0.301 / 0.507) |
| relax/memory | 0.630 (0.616 / 0.538 / 0.683) |
| none/body | 0.687 (0.652 / 0.579 / 0.758) |
| raise/body | 0.594 (0.540 / 0.437 / 0.699) |
| relax/body | 0.738 (0.698 / 0.689 / 0.783) |
| relax-matched/memory | 0.607 (0.602 / 0.509 / 0.658) |

## The fresh successors: a_v after generation g, field-free (all; native / particular / permissive)

| Row | after g 8 |
|---|---|
| none/memory | 0.796 (0.817 / 0.639 / 0.864) |
| raise/memory | 0.759 (0.776 / 0.598 / 0.830) |
| relax/memory | 0.845 (0.872 / 0.680 / 0.913) |
| none/body | 0.867 (0.901 / 0.682 / 0.942) |
| raise/body | 0.836 (0.865 / 0.629 / 0.925) |
| relax/body | 0.881 (0.910 / 0.712 / 0.951) |
| relax-matched/memory | 0.835 (0.866 / 0.674 / 0.899) |

## The injury checks (share of lineage-cases where the injury flipped exactly its patch)

| Row | g 1 | g 2 | g 3 | g 4 | g 5 | g 6 | g 7 | g 8 |
|---|---|---|---|---|---|---|---|---|
| none/memory | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| raise/memory | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| relax/memory | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| none/body | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| raise/body | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| relax/body | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
| relax-matched/memory | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) | 1.000 (1.000 / 1.000 / 1.000) |
