# E122 — protected-copy specificity scale and long-horizon tail

**Complete and verified, 2 November 2026.** Historical specificity remains
detectable after **256 rewrites**: **1.511 [0.956, 2.091] points** at 128 bytes
and **0.987 [0.514, 1.472] points** at 2,048 bytes. Relative to the matched
protected-copy gaps, the ratios are **0.856 [0.585, 1.125]** and
**0.377 [0.201, 0.546]** (Fieller 95%). These are not fractions of total
historical information or universal format-capacity bounds.

Both budgets satisfy the frozen **±0.25-point** equivalence criterion for the
history-gap change from 128 to 256. Very slow decay remains compatible with the
finite window. Sign agreement falls while amplitude qualification increases.
[Interpretation](INTERPRETATION.md), [figure](runs/continuation_v1/specificity.png),
[full report](runs/continuation_v1/REPORT.md).

`continuation_v1` finished **16:44:25 UTC**, **2h46m54s**, four workers. Verified
**418 outputs / 22 frozen inputs** and inspected the figure; closeout passed
**17:22:35 UTC**. All 64 source blocks and failures remain. Scientific launch
was **13:57:30 UTC**; no scientific outcomes were inspected at launch.

The user authorized proceeding after E119–E121 completed. All eight check
groups pass, including exact legacy projection, independently coded replay,
strict score boundaries, Fieller sets, synthetic tail models and the complete
export/analysis interface. Original failed test evidence is retained: a
degenerate Fieller set needed its all-real label corrected before launch.

`benchmark_v1` completed **2 November 12:15:54 UTC** in **8m39.69s**. Its **37
outputs** verified and figure passed inspection. Excluded source **900014**
ran both budgets through 256 rewrites with native dynamics, declared replay,
storage and fitting. The scientific settings froze at **13:56:32 UTC**, before
new scientific protected-foreign reads or continuations. No automatic successor
is configured.

Extend all 64 original E014 blocks, all 256 founders and both recipient
lineages, at **128 and 2,048 bytes**, through **32, 64, 128 and 256 rewrites**.
Keep own/foreign renewal and add matched protected-own/protected-foreign
readers. Report the renewed own-minus-foreign gap divided by the protected-copy
gap for the same budget, together with both raw gaps and their uncertainty.

Retain sign agreement, amplitude qualification and their joint categories.
Compare decay-plus-plateau with zero-plateau and slow-decay alternatives; a
flat-looking finite segment is not evidence of equivalence or indefinite
retention. Benchmark first, stream compact outcomes and retain selected fields.

All **192 scientific archives** (128 lineages and 64 sources), plus three
excluded benchmark archives, matched their original completion hashes:
**195 files / 3,338,662,865 bytes**. The source registry records actual current
hashes, paths and native schemas. No source was regenerated. The scientific
disk reserve is **3,790,424,704 bytes**, against 67.37 GB free at qualification.

[Detailed plan](PLAN.md), [planning source inventory](planning_inventory.json),
[E014 results and sign/amplitude handoff](../E014_long_renewal/README.md).

Current implementation: [protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md),
[verified sources](SOURCE_DATA.json), [passing checks](analysis/tests_attempt_002.json),
[qualification](analysis/qualification_v1.json), [scientific freeze](SAMPLE_FREEZE.json),
[measured forecast](analysis/forecast_v1.json),
[scientific startup](jobs/continuation_v1/startup.json), [decisions](DECISIONS.md).

The next retained-data task is [E123's external founder-identity audit](../E123_history_identity_audit/DECODER_DESIGN_V1.md).
Its source/prediction schema reuses the candidate prototypes, packets and
selected recipient/body fields retained here. Its full synthetic pipeline passed
and its analysis froze before E122's final outcomes were inspected. It adds an
auxiliary observer analysis, preserving E122's specificity endpoints.
