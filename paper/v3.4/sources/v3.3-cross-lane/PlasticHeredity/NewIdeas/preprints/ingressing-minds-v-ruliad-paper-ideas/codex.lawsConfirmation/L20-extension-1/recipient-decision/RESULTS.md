# D198: family context helps; extra record detail has not earned its place

30 October 2026. COMPLETE / SAVED-AUDITED.
[Contract](DEVELOPMENT_V1.md), [qualification](QUALIFICATION.md),
[complete tables](TABLES.md), [status and next gate](STATUS.md).

The record-based policy improved on a single reconstruction setting, but did
not improve on choosing by the known target family. The useful development
lead is **coupling 1.25 for A and 0.75 for B**. The more detailed policy made
only two different choices in nested validation, and both were worse.
This is development evidence; there has been no fresh-case decision contest.

## What was tested

D198 reused every main case from D180–D182. D180 and D181 share four starting
founder blocks and supply six distinct future-noise streams between them;
they were coalesced. D182 supplies four other blocks with four futures each.
The independent population is **eight founder blocks**, not twelve: 64 distinct
2,048-byte F0 packets and 128 packet/writer decisions. Both families, all four
lives and both descendant writers remain.

The deployment interface uses only F0, known family, known descendant writer
and the fixed guide. Six static features describe template correlation, guide
response, strength and roughness. There is no diagnostic read, parent body,
founder identity or later state in that interface. Family labels and templates
are supplied apparatus, not an independently learned ontology.

The fixed linear ridge rule predicts each setting's advantage over native
coupling 1.0, within each family/writer group. Its choices are 0.75, 1.0 or
1.25 for all three replacements. Utility is terminal own-minus-alternative
preference under the common evaluation reader.

Eight outer whole-founder folds tested the development procedure. Every
training fold selected regularization using only its own whole-founder inner
folds, fitted its own feature scales, and fitted all five simple baselines.
Futures were averaged within each record before equally weighting records
and founders. Six old futures therefore do not outweigh four new ones.

## Decision values

Values are preference fractions multiplied by 100, not success rates.
These comparisons use nested validation on previously observed development data.

| Policy | Mean preference points | Record rule minus policy | Record-rule gains / harms / ties |
| --- | ---: | ---: | ---: |
| Native 1.0 | 33.626302 | +1.289622 | 92 / 29 / 7 |
| Best common setting | 34.739939 | +0.175985 | 42 / 18 / 68 |
| Family-only choice | 34.920502 | −0.004578 | 0 / 2 / 126 |
| Writer-only choice | 34.739939 | +0.175985 | 42 / 18 / 68 |
| Family-by-writer table | 34.920502 | −0.004578 | 0 / 2 / 126 |
| Record-based rule | 34.915924 | — | — |

The common and writer-only rules chose 0.75 throughout. The family-only and
family-by-writer rules chose A→1.25, B→0.75 in every outer fold. Writer context
did not change their preferred action. The family rule's advantage over common
is **+0.180562 points**; over native it is **+1.294200 points**. These are still
development comparisons, not prospectively established improvements.

The detailed rule used 0.75 / 1.0 / 1.25 in **64 / 2 / 62** cases. Its two
departures from the family rule were ordinary-writer A records from founder
90015, lives 2 and 3. It chose 1.0 instead of 1.25, losing respectively
0.520833 and 0.065104 points on their six-future means. Seven founder
comparisons against the family rule tied; 90015 lost 0.036621 points.
This tiny negative average establishes neither equivalence nor universal
inferiority. The detailed rule added no measured value here.

Seven outer folds selected lambda100; the fold omitting 90015 selected 1.
Full-development selection chose **100**, the strongest predeclared value.
Its decisions match the family table on all 128 development cases. The stored
model remains feature-dependent and could choose differently on new packets;
this observed agreement is not an algebraic identity for every packet.
No feature or grid was tuned after results. No outer or final decision clipped
a feature. Full-data selection scores and in-sample values are not prospective.

## Transfers, future variation and shape

Training on the old blocks and testing on D182 gives **36.546326 points** for
both detailed and family rules, versus 36.360168 for common. Their decisions
agree on all 64 cases. Training on D182 and testing on the old blocks gives
**33.294678 points** for both rules, versus 33.119710 for common. Here equal
means conceal 12 different actions: the detailed rule has 6 gains, 5 harms
and 53 outcome ties. This is cancellation, not equivalence. Each direction
selects its model using only its four training blocks.

Nested detailed-minus-family means are negative in futures 0, 1, 3 and 4,
positive in 2 and 5. Futures 0–1 exist only for old blocks. All future and
block views remain in the report and tables; no favorable stream was selected.

Under the native evaluation reader, nested values are 35.056559 points for
the detailed rule and 35.065206 for the family rule. Final own-shape correlation
averages 0.815843 versus 0.815880; native-setting correlation is 0.792874.
These gains do not imply full preservation. The outcome-informed per-record
maximum is 35.113017 points. It maximizes noisy observed outcomes and is only
an optimistic retrospective reference, not deployable or a proven attainable
ceiling. No inferential interval is claimed from these development folds.

## Apparatus and integrity

All 11,520 saved rows were bridged to terminal observations and saved features.
Packet hashes matched original seals; shared D180/D181 F0 identity and disjoint
future addresses passed. All 64 feature vectors received independent spatial,
guide, strength and roughness checks. All 72 pooled control cells and their
eight founder values remain outside policy fitting.

Protected copying preserves incoming packet shape. At native coupling, B starts
at mean correlation 0.828325 and ends at 0.562120 with ordinary writing,
0.717430 with aligned writing, versus 0.828325 under protected copying.
Reading/writing-disabled controls remain in the tables, including adverse
preferences. Common-reader protected-copy and write-off preferences are
identical across recipient couplings, as required by their structural lack of
recipient-dependent written information.

The separate saved audit re-extracted the data, checked every model with
augmented least squares rather than the fitting solver, recomputed choices
and values independently, and verified all six output hashes. It made no
production fitting calls and generated no dynamics. The freeze binds 1,540
inputs and the passing 72-test qualification. Earlier engineering attempts
remain retained and documented.

Frozen **16:57:00.947213 UTC**; fitting completed **16:57:32.681592 UTC** in
**7.183214 seconds**; saved audit completed **16:58:13.046935 UTC** in
**7.183165 seconds**. One CPU6/thread, nice10; main peak RSS 73.109375 MiB.
External retention is 19,694,268 bytes (about 18.78 MiB), including all test
attempts, below the 128 MiB cap. Only code/docs were added locally. No worker
remains running.

## Interpretation and next gate

This moves the recipient interaction toward an explicit, testable decision.
So far, **known family context explains the apparent matching benefit**.
Fine packet detail has not provided an additional gain. Retain that negative
comparison, rather than revising features or the grid to improve it.

Next, test these unchanged rules on fresh founders, with the family rule
prominent. Freeze the cohort, block-level uncertainty and comparison hierarchy;
seal every case's choices before generating any descendant outcomes; benchmark
one complete disposable block to set the budget. A family rule beating common
would support useful coarse matching. A stronger record-matching claim requires
improvement over family and family-by-writer choices.

No fresh cohort, outcome executor, choice seal or benchmark was launched in
D198. It does not establish autonomous interface repair or alter the prior
challenge-prediction findings. D197's conditional embodiment findings retain
their separate scope. **L20/L22 remain STRESS_TESTED / MIXED.**

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-recipient-decision-development-v1`.
Pinned hashes are in [TABLES.md](TABLES.md#frozen-evidence).
