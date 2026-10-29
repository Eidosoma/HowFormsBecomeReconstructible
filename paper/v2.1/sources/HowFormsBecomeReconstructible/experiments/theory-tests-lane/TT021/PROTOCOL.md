# TT021: prospective early-capture confirmation

14 October 2026. Authorized after TT020's completed reconstruction and closeout.
The exposed four-block result is known: common-record recognition rises from
50.00% to 77.73% with capture; held memory reaches 75.00%, matched averaging
64.06%, and informative-record recognition falls from 87.89% to 84.77%.
These observations motivate this design and do not enter its test cohort.
Registration must bind this protocol, all code, successful qualification,
benchmark, and a bounded seed-collision search before any new cohort generation.

Enroll all 64 new tissue blocks 21000000–21000063, with all four intended messages
and four parent replicas per message: 1,024 records in each condition. Eligibility
does not depend on teaching, body expression, record quality or later success.
Do not replace failed or unfavorable cases. Disposable blocks 603210 and 603211
are excluded from science and used only for qualification and timing.
The proposed range is reserved only by RESERVATION.json and REGISTRATION.json.
The bounded search covers accessible metadata/code in both project trees; it
cannot establish independent custody, technical blinding or absence on unavailable
storage. No prior parent, repair path or receiving assay supplies a test outcome.

Use byte-identical copied D186 sources and TT020 independent physical/scoring
references. Tissue parameters, threshold fields, parent teaching and all noise
are generated from the original hash-addressed laws at new tissue identities.
Retain original source, repair, shuffle, birth and assay namespaces. Distinct
tissue identities receive distinct pseudorandom streams. Within a block, arm
names are absent from the noise keys: repair and receiving challenges are paired
across conditions. Noise is also coupled across intended messages as in D186;
replicas and the four receiving draws occupy distinct positions within those
streams. Reader birth and ongoing noise have distinct phase keys. This tests
the original pairing regime, not robustness to independently perturbed messages.

Settling, teaching and repair last 120, 1,000 and 1,000 updates respectively.
Fresh readout uses four draws per record and 1,000 updates. Preserve physical
rates, damage .3, writer rate .001, record norm .3, 16-by-16 sheet and binary64
arithmetic. Repair checkpoints are 0, 1, 50, 250, 500 and 1,000; reader checkpoints
are 0, 1 and 1,000. Only the 256 float64 theta values, 2,048 bytes per record,
cross to the fresh body; body, memory, parent record and labels do not cross.

Early capture sets R0 equal to the current injured V0, including its fresh fill;
ema starts at zero. It does not access intact parental memory. Held memory keeps
that snapshot constant, so it is a protected information source. Updated memory
retains the original update rule. Ordinary repair starts with zero memory.
Fixed reading uses incoming theta throughout repair; live reading uses the
evolving theta. Captured averaging observes V0 through Vt, while ordinary
averaging observes V1 through Vt. Both write 1,000 times, with no birth write.
The fixed-reading average and memory writer see the same body stream. Live
feedback can change that stream and does not isolate a writer-only effect.

Prespecify 20 repair paths, ten per record family. In each family retain ordinary
own-body live and fixed repair; captured own-body live, fixed, held memory and
disabled writing; and captured partner, own-scrambled, partner-scrambled and
history-erased live repair. Retain all four corresponding own-body averages,
both unchanged inputs, intact-parent and supplied-positive packets, and disabled
reading using the common carrier. These make 29 named packets per block.
This focused confirmation omits the old native-reset family and redundant
factorial paths before outcomes. Both injured-record families, unfavorable
directions and all selected controls remain. Positive controls are reported;
unfavorable biological outcomes never become enrollment exclusions.

The endpoint is intended-message recognition in the fresh recipient. Preserve
the original equal fractional credit for tied maximal projection scores within
absolute 1e-12. Average four draws within each record, then all 16 records within
each block; average the 64 paired block contrasts equally. The population unit
is the tissue block. Four draws do not precisely estimate individual capacity.
Keep partner recognition, projection gaps, sign fidelity and record correlations
separate. Preserve paired improvements, harms, ties and all message/block strata.

The single primary claim is common-record captured live minus ordinary live
recognition exceeding five percentage points. Four additional directional claims
are fixed: common-record live minus held memory exceeds two points; common-record
captured fixed minus matched average exceeds two points; common-record captured
own minus partner body exceeds five points; and informative-record ordinary live
minus captured live exceeds two points (a harm claim). These operational margins
express required effect size, not theoretical constants or outcome-derived
estimates. A secondary result cannot rescue the primary.

The five claims share a .05 family error budget through Bonferroni: alpha=.01
per one-sided test. For each claim use the paired-block mean minus the .99
Student-t quantile at 63 degrees of freedom times the sample standard error.
A claim passes only when this lower bound is strictly above its fixed margin;
otherwise classify NOT_CONFIRMED, which is not proof of absence or equivalence.
With zero observed variance, use the bounded-contrast lower bound with radius
sqrt(2*log(100)/64). Report two-sided pointwise 95% intervals separately, together
with the conservative bounded lower sensitivity for every registered claim.
Student-t coverage and the resulting family control are approximate; the nested
draws do not increase the degrees of freedom. All other contrasts are descriptive.
No sample extension, arm selection, rate tuning or stopping based on outcomes.

Before acquisition, qualify the selected full workflow and exact agreement with
TT020 archived controls, independent repair/read dynamics, scalar scores,
information boundaries, saved-evidence checks, inference and a two-worker versus
serial execution bridge. Corrupted arrays, routes and rows must be detected.
Native checkpoints require exact dtype, shape and bytes; averaging and continuous
record diagnostics retain absolute 2e-12, scalar projections 2e-13, zero relative
tolerance. No threshold changes after failure. The analysis includes a planning
sensitivity grid, not a claim that four exposed blocks estimate variance reliably.

Benchmark two disposable blocks with full parent preparation and 100-step repair
and reading at the same record/draw counts. Conservatively scale elapsed batch
time tenfold and by 32 batches; do not discount fixed parent or I/O costs. Record
storage and peak memory. Admission requires forecast below 16 hours, deadline
three times forecast plus ten minutes below 48 hours, estimated panel storage
within a three-GiB allowance, and one additional GiB free. Check storage before
each batch and retain a numerical/storage failure without replacement or retry.

Use two worker processes, one numerical thread and one allowed CPU per worker,
at nice 10, subject to the shared 12-CPU ceiling. A coordinator does no physical
simulation. Any run over ten minutes launches detached with stdin disconnected,
unique log/PID, registration and RUNNING/COMPLETE/FAILED receipts. Each block
passes saved-evidence checks before completion; hashes, scores, summary and
report are rechecked at completion. Leave the job unpolled after one startup
acknowledgment until the user asks. No automatic successor or external messages.

This is a new-cohort test within the supplied simulator and the stated pairing
regime. It does not test serial heredity, autonomy, a unique theoretical law,
biological transfer or independently perturbed cue/message environments.
