# H006: perturb record organization while matching present function

Prospective development protocol, 11 October 2026. H005 found a small future
difference below its effect-size gate; 41 of its 106 matched pairs contained
identical packets. H006 instead intervenes on the same acquired packet. The
original H005 cohort, threshold and verdict are unchanged.

## Inputs and fixed split

Use only the gain-4-history G16 own packets from the sealed H003 development
run, with their original base networks and founder/replica addresses. Each
block supplies 16 packets. Seeds 13000–13007 are the eight dose-selection
blocks; seeds 13008–13023 are the 16 assay blocks. This numerical split is fixed
before any H006 probes. Both cohorts are previously exposed development
checkpoints; only the H006 probes and futures are new. Do not use H004's
confirmation cohort or any private data, model, result or implementation.

Engineering uses the separate, previously exposed seed 12900. It measures all
doses and exercises the future pipeline at the largest dose, 32, regardless of
the current gates. Its outcomes cannot select the study dose or qualify a
population claim. Do not change the design after opening this benchmark.

## Intervention and strength control

Three variants begin from each source packet: unchanged; sign flips on edges
from the four cue sites 0–3 to output sites 8–23; and sign flips from those
same cue sites to hidden sites 24–63. Hidden-site connections are an active
location control, not assumed irrelevant to function. Both sets receive the
same gain 4 in the supplied reader.

Candidate doses are 4, 8, 16, 24 and 32 unique undirected edges. Construct a
fixed nested ordering before probes: randomize cue-site order; for each of
four rounds, visit the four sites and choose one positive and one negative
edge in each location pool, without replacement. Prefixes give the doses.
Use semantic random keys indexed by base seed, founder, replica, location
and cue. The output and hidden variants have exactly the same number of
flips per cue, balanced positive/negative counts, and symmetric zero diagonals.

Each sign flip preserves entry magnitude. Therefore the complete weight
histogram, record Frobenius norm, number of nonzero entries and storage size
are exactly preserved. Perturbation Frobenius distance and gained perturbation
distance are also equal across the two locations. The base-plus-record norm
can differ because of base/record cross terms; retain it descriptively.
The shared machinery, birth tapes, schedules and time budgets are unchanged.

Require a structurally eligible source to have the fully aligned cue-to-output
block and at least four positive and four negative nonzero cue-to-hidden edges
per cue site. This one rule applies to every dose. Infeasible sources are
retained with unchanged placeholders and an explicit false eligibility flag;
they cannot enter any intervention comparison. In feasible packets the cue
association changes from 1 to 1 - dose/32 in the output intervention, and
remains 1 in the other two variants. These are controlled packet alterations;
they need not themselves be an unmodified two-body coactivity product. All
later renewal packets are complete body-only writes under the original rule.

## Present-only selection, then independent assay validation

For each dose-selection block, read all five doses and three variants with
eight new screening probes. A packet enters a dose's match only when all
three variants pass on every probe and their four task-aligned output means
are exactly equal on every probe. The observer and strict >.5 success rule
are unchanged. A further 64 independent probes validate the match and never
change membership. No present probe writes a packet.

A dose passes selection only with at least 64 matched packets across at least
six of the eight blocks; mean validation success >=.95 for all variants; and
90% whole-block bootstrap intervals within [-.01,.01] for all three pairwise
success differences and all twelve pairwise output-mean differences. This is
finite-observer equivalence with a one-point tolerance, not identity of latent
readout probabilities. Select the largest passing dose. If none passes,
finish as NO_ADMISSIBLE_DOSE without generating study futures. There is no
fallback zero dose, tolerance relaxation, added cohort or alternative split.

Seal the selection data, decision and chosen dose before probing the assay
blocks. On those 16 blocks, use only the selected dose, eight new screening
probes and 64 separate validation probes, with the same exact match and
one-point equivalence tests. Require >=64 matches in >=12 assay blocks and
mean validation success >=.95 for all three variants. Seal the full cohort,
current data, validation decision and directional forecast before any assay
future is generated. A failed assay gate finishes as PRESENT_GATE_FAILED;
it does not trigger another dose. Neither selection nor enrollment can access
H006 future outcomes. Whole-block means weight nonempty networks equally.

## Common future and record controls

If the current gates pass, simulate every assay candidate, including
nonmatches and marked infeasible placeholders, for eight independent future
branches and 16 additional replacements. The primary comparison uses only
the sealed eligible set. Descriptive all-candidate intervention summaries
must exclude structurally infeasible placeholders. Never stop a branch on
failure. All variants have the same future gain-4 reader, eight sweeps per cue,
complete body-only writer, fresh body initialization and independent 50%
undirected edge loss per replacement. Random tapes are paired across variants
and controls within a branch, and separate across branches and probe stages.

Seven arms apply to each variant: renewal; restored (replace the starting
packet by its unmodified source); opposite-rule foreign packet with donor
mapping [2,3,0,1]; protected copy; cumulative-loss copy; read off; write off.
Restored variants must have identical packets and bodies throughout. They
must also equal unchanged renewal. Protected packets never change. Copying
remains computationally cheaper. No further sign-flip intervention is applied
after the initial transplantation.

Primary endpoint is original-rule success in a fresh undamaged reader after
16 additional replacements. Also retain checkpoint success at 1, 4 and 8,
all damaged-body outcomes, and uninterrupted success through all bodies and
the terminal reader. Those outcomes cannot rescue a failed primary.

## Frozen future decision

Average branches and eligible packets within each block, then weight blocks
equally. Qualification requires all current and integrity gates and all six
directional contrasts below:

- unchanged renewal minus output-flip renewal >=.10;
- hidden-flip renewal minus output-flip renewal >=.10;
- unchanged renewal minus its foreign, read-off, write-off and damaged-copy
  arms each >=.15;
- every contrast has a positive one-sided Bonferroni bootstrap lower bound,
  using quantile .05/6 from 20,000 whole-block resamples.

Use seed 960006 and namespace `H006 whole-block bootstrap`, with separate
selection and assay keys. Reuse assay block resamples for current and future
estimates. Display marginal 95% intervals and all current 90% intervals.
The practical minima are requirements on point estimates. A positive smaller
effect still fails qualification. Do not enlarge the cohort or replace a
failed contrast with protected-copy, uninterrupted or intermediate outcomes.

This estimates the effect of two controlled packet alterations within the
declared present-matched set. It does not estimate a total history effect,
prove exact present equality, establish natural acquisition of these altered
packets, discover competence or identify a unique theory. The active hidden
control and explicit strength invariants narrow the mechanism question; they
do not establish that all possible state descriptors have been matched.

## Execution and retained evidence

Freeze this protocol, source, split and configuration before probes. Retain
source receipts, source bodies, intervention masks, feasibility, every probe,
every future packet/body/damage mask/reader and all decisions. Packet archival
codes are lossless int8 values scaled by 64. Audit source writer identity,
mutation support/counts/histograms/norms, original dynamics fixtures, exact
probe replays, seals, restored identities, all writing/loss boundaries,
independent scoring, and first/terminal reader replays.

Benchmark a complete engineering block, including both present stages, all
eight futures and audit. Forecast from that entire runtime times 24, plus
25% headroom and 60 seconds. This overcounts assay present work because the
engineering selection stage measures all five doses. If the forecast exceeds
600 seconds, detach with stdin disconnected, unique log/PID, frozen sources
and durable status; await user-requested status under ../RUN_POLICY.md. One
worker and one numerical thread. Preserve every failed attempt. No manuscript
edit or public release is part of this experiment.
