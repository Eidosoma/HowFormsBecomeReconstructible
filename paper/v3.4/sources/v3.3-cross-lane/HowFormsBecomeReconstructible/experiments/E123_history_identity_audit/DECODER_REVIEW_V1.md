# Forms implementation review: E123 identity observers

2 November 2026. Reviewed against the theory lane's
[common reporting contract](../theory-lane/rdt_information_source_reporting_v0_1/reviews_2026_11_02/COMMON_REPORTING_FORMAT.txt)
and its [TT052 implementation criteria](../theory-lane/rdt_information_source_reporting_v0_1/reviews_2026_11_02/TT052_REVIEW.txt).
This is the Forms implementation review; it is not a new review decision from
the theory lane and does not alter either lane's protocol.

The [design](DECODER_DESIGN_V1.md) names the regularized joint-versus-record
log-loss comparison at 128 bytes/g256 as primary. The template comparison,
protected records, other horizons/budget and supplying-lifecycle applications
remain separately reported. The target is acquisition donor, with four equally
likely block-local candidates, not the native own-founder scoring target.

The held-out dictionary is explicitly an observer resource. All four candidates
are supplied identically to every input view. It is never sent to a native
writer. Setup is constant within balanced strata, making the uniform predictor
an appropriate design baseline. Masks and generated births are inventoried but
excluded from this release's observers. Learned `ref` remains in B. Fixed
coordinates and the absence of alignment search are declared.

Whole-source folds include every descendant and dictionary copy. Features use
no labels or grouping metadata. Every inner scaler, ridge fit and temperature
selection receives development rows only. Eight outer/four inner folds, four
ridge values, eight inverse temperatures and one block-wise label permutation
are fixed. A fit failure stops the release. Null fitting is limited to the
primary budget; the actual models cover both budgets. Additional null budgets
or model searches would be a later declared analysis.

The [full synthetic qualification](analysis/decoder_full_tests_001/RESULT.json)
passed. It includes gradient/optimizer checks; held-out-label and held-out-feature
perturbation; whole-source exclusion; row/candidate permutation; native-shaped
packet/body conversion; exact repeated-input features; 32,512 repeated-input
probability checks; complete prediction tables; a model/target/probability seal;
and subsequent scoring. The intentionally tampered synthetic seal is retained
as an expected rejection fixture. No retained E014/E122 decoder was fitted.

Cross-batch identical features use per-case reductions, avoiding a dependency
on matrix multiplication's batch-dependent summation order. This numerical
implementation choice changes no scientific feature definition. Actual
probabilities from identical permitted inputs must agree within 1e-12 under
the same model. Candidate ties use prototype hashes, with the declared residual
rule for genuinely identical prototypes.

The two-bit prior and normalized probability smoothing are explicit. The
population variational inequality is checked against equation 3 of
[Barber and Agakov (2003)](https://proceedings.neurips.cc/paper_files/paper/2003/file/a6ea8471c120fe8cc35a2954c9b9c595-Paper.pdf).
Empirical predictive information can be negative. Neither a gain between two
imperfect observers nor a successful external recognition score measures unique
conditional information or allocates native success to components.

These B states are generated from R in fresh readers. A joint observer may
benefit from that computation without acquiring independent historical content.
The already incurred native-reader cost is retained separately from retrieval,
feature construction, model fitting, calibration, inference and scoring costs.
Protected copies and descendants are dependent observations, not additional
independent blocks. Confidence intervals describe saved cross-fitted predictions;
they do not remove overlap between training sets or prior mechanism exposure.

The full synthetic pipeline took 78.24 seconds for 16 excluded groups, including
the complete output and scoring path. Its timing is more informative than the
earlier engine-only benchmark. The updated forecast uses that complete path
scaled to 64 sources plus an explicit source-verification allowance; it is not
a measured retained-data runtime.

The live-data gate requires E122 completion and verified closeout, all original
source hashes, exact E014/E122 overlap and compatible donor/route metadata. It
cannot consume partial E122 files. The remaining source gate is checked during
explicit ingestion; no synthetic qualification is represented as verifying
unopened scientific arrays. All scientific choices above precede that ingestion.
No manuscript change is authorized by this audit.
