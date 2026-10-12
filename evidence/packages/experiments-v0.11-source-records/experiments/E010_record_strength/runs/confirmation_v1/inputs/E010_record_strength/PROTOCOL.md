# E010 — which record values preserve a particular history?

Follow-up motivated by E009's post hoc association: strongest-value repairs
mostly restored sites shared by founders. This protocol is fixed before any
E010 scientific result. Test the intervention directly on fresh founders;
do not fit a model, search thresholds, expand the cohort, or revise the gates.

## Cohort, interventions and supplied resources

64 independent blocks 8000–8063, four founders per block, eight recipients per
body and condition. Retain every founder. Technical benchmark 900210; fixtures
900211–900212 are excluded. Use the existing native A formation and activity-
driven capture, 256-site float64 record and 300-step packet-only reader. Target
B uses E008's degree-four graph with exactly 128/512 edges rewired to long links;
one fresh graph and one formation background are shared by each block.

Erase a uniform random 192/256 entries separately for each founder. Restore
exactly 64 erased values from a declared clean backup using three fixed rules:

- Weak: the 64 smallest absolute backup values among the erased sites.
- Strong: the 64 largest absolute backup values among the erased sites.
- Random: one independent uniform 64-subset of the erased sites.

Ties use lower site index. Policies read only the backup and injury mask;
neither founder prototypes, foreign records nor any body outcome selects sites.
All three repairs transmit original values exactly, leave 128 sites erased,
and restore 512 value bytes. Addresses and the clean backup are supplied.
Amplitude is not normalized: equal counts/bytes deliberately do not mean
equal total amplitude or equal physical cost. This tests the complete selection
rule, not amplitude and location as separately controlled causes.

References: intact own record, unrepaired record, complete erasure, and intact
records from each of the three other founders. One injury and each fixed repair
are shared across recipients and bodies. Within a body, births/noise are paired
across conditions. A/B births/noise are independently seeded. Save source,
graph, masks and packets before reading bodies. No writer or body-flip challenge
acts during the read. Repair precedes fresh development, not autonomous repair
of a living body. Source and target responses cannot alter the fixed policies.

## Scores and prospective decision

Qualified agreement uses matching sign and recipient |V|>.2, exactly as before.
Score each endpoint against all four founder prototypes. Primary specificity:
own-founder agreement minus the mean agreement with all three foreign founders.
Primary utility is the specificity gain over the unrepaired record in B.
Average eight recipients, then four founders within each independent block.

The claim "weak-value restoration selectively improves reconstruction" passes
only if all four lower 95% bootstrap bounds are positive:

1. Weak minus strong specificity utility in B.
2. Weak minus random specificity utility in B.
3. Weak specificity recovery versus unrepaired in B.
4. Weak own-agreement recovery versus unrepaired in B.

Use 10000 whole-block percentile draws tagged E010:confirmation. This is a
conjunction; retain every failed contrast. B is primary because E009's repair
lead arose there; native A is a prespecified secondary transfer check, not
an alternative route to passing. A/B differences are secondary.

Also report absolute own/foreign agreement, own-agreement recovery, resolution,
all three individual foreign-founder offsets, all reference contrasts, and
per-founder observations. No selection based on the most favorable foreign
comparison. For each repair, record mean restored absolute magnitude, its
total absolute magnitude, and the fraction of restored sites distinguishing
the founder from each foreign founder. These are descriptive mechanism checks;
site composition alone cannot pass the outcome criterion.

## Verification and runtime

Freeze protocol, code and dependencies before running. Meaningful fixtures
check exact budgets, rank/tie rules, backup bytes, selection independence,
packet-only paired dynamics and the all-foreign observer. Independently replay
injuries/subsets, verify graph and packet receipts, rescore saved fields and
reproduce all intervals, CSV rows and gates. Preserve failures and old results.

Benchmark a complete excluded block with formation, capture, both body reads
and reporting. Conservative forecast: twice whole-block seconds * ceil(64/12)
+ 60 s. Above 600 s, launch detached and await the user's poll. Otherwise finish
and audit directly. At most 12 logical CPUs total, numerical threads one.
All writes remain under this experiment tree; source trees stay read-only.
