# Second feedback v1: a little caution is corrected, but total cost rises

**Completed 22 September 2026; read back on the user's status request.**
The [frozen contract](FEP_SECOND_FEEDBACK_V1.md) and
[checker](check_fep_second_feedback.py) specify one additional retention
opportunity. The [launch checkpoint](FEP_SECOND_FEEDBACK_V1_CHECKPOINT.md)
remains an unchanged historical record of the detached launch and then-pending
outcomes. This report supplies the completed verdict.

**All three primary improvement criteria fail.** Full second-task retention
raises equal-panel mean cost from .076088423702 to .076132817774. It also
costs more than retaining just the second warning and more than the original
no-update agent. Model averaging has the same three failures. The agent makes
fewer paid checks, but its added mistakes cost more than those savings.

Some previously costly caution is corrected: 3.414912% of the identified
primary event probability returns to the old report, or 16.257489% with
averaging. That local benefit does not rescue total performance. The earlier
useful calibration and small first-task active-learning gain retain their
original scope; a second retained outcome has not established a better agent.

## Matched intervention and scope

All three retention arms share saved calibration, the frozen future-aware
first acquisition, first-task retention and the resulting second-task action.
There is no additional optional reference on task two. After that action:

- **Frozen:** keep the task-one posterior and table.
- **Warnings:** retain the second warning without its target.
- **Full:** retain the warning and its target if that action already purchased
  a reference; otherwise retain only the warning.

Each table then remains fixed for tasks 3–100. An unchecked report never
provides a label. The second reference costs the same .1, mistakes cost 1,
and calibration costs .001 per pair. All first and second costs are matched;
differences between the three arms come entirely from the final 98 tasks.
The original no-update agent is a contextual comparator with different first
actions. The first acquisition rule is not reoptimized for the new schedule.

Inference exactly sums latent error histories when either retained observation
is partial. The models, .9/.1 structural prior, reference-at-tie rule, saved
stopping distribution and whole known nine-environment panel are unchanged.
Both controllers and the original-prior control are retained. The old shared
case stays outside the panel aggregate. This is a prospective intervention
on a known panel, not a fresh validation population or continual learning
throughout the episode.

## Full costs and registered criteria

Costs include all references, mistakes and calibration, divided by 100 tasks.
Lower is better. Decimals are rounded; exact fractions are in the external record.

| Controller | Original no-update | One-update frozen | Second warning only | Full second retention |
|---|---:|---:|---:|---:|
| Primary MAP | .076026980104 | .076088423702 | .076104192035 | **.076132817774** |
| Model average | .076016683060 | .076037589155 | .076031570777 | **.076049574444** |

| Registered comparison | Primary difference | Verdict | Averaged difference | Verdict |
|---|---:|---|---:|---|
| Full minus frozen | +.000044394072 | Fail | +.000011985290 | Fail |
| Full minus warnings | +.000028625739 | Fail | +.000018003668 | Fail |
| Full minus original no-update | +.000105837670 | Fail | +.000032891384 | Fail |

Primary cost increases .058345% relative to one-update frozen; averaging
increases .015762%. Warnings-only retention itself worsens the primary mean
by .000015768333 but improves averaging by .000006018378. Thus the full-label
failure is not evidence that every second observation is harmful.

The primary improves only two of nine environments against frozen retention;
averaging improves three. Against warnings-only retention the counts are six
and two, respectively. Against original no updating they are two and six.
Those unweighted counts do not replace the registered equal-panel mean costs.
Neither controller is uniformly non-worse than frozen retention.

All three arms and the original no-update comparators still beat always asking
in the same six environments. The new full means are about 23.87% (primary)
and 23.95% (average) below its .1 cost. This preserves useful learned task
behavior while rejecting the proposed improvement.

## Every environment remains visible

A positive difference below is worse. The three contrasts use full retention
minus the named comparator. The first sensor's error rate is .05, .15 or .25,
the second's twice that; dependence is independent, midpoint or nested under
the frozen construction. These are not Pearson correlation labels.

| Environment | Primary − frozen | Primary − warnings | Primary − no-update | Average − frozen | Average − warnings | Average − no-update |
|---|---:|---:|---:|---:|---:|---:|
| .05 / independent | +.000014632561 | −.000002985488 | +.000014408304 | +.000012375408 | +.000011840185 | −.000000573594 |
| .05 / midpoint | +.000003669815 | −.000001012575 | +.000051639555 | +.000002381854 | +.000006633481 | +.000040391414 |
| .05 / nested | −.000058092275 | −.000057762424 | +.000143420916 | −.000133914300 | −.000138560491 | +.000046928532 |
| .15 / independent | −.000129285344 | −.000074429464 | −.000035920481 | −.000102271182 | −.000092760080 | −.000031747013 |
| .15 / midpoint | +.000313571182 | +.000177546660 | +.000433115982 | −.000005091774 | +.000073106772 | −.000008434225 |
| .15 / nested | +.000170330739 | +.000169675879 | +.000250362877 | +.000315303936 | +.000281130582 | +.000332492278 |
| .25 / independent | +.000009800374 | −.000000046258 | −.000022459949 | +.000003284685 | +.000008473339 | −.000032289318 |
| .25 / midpoint | +.000074005282 | +.000046793837 | +.000113688984 | +.000015423909 | +.000011887490 | −.000048981860 |
| .25 / nested | +.000000914313 | −.000000148513 | +.000004282845 | +.000000375071 | +.000000281729 | −.000001763760 |
| Old shared, excluded | −.000054291037 | −.000051042410 | −.000179749312 | −.000045883183 | −.000048533559 | −.000186387498 |

Two of the three previously harmed environments improve against frozen
retention: .05/nested and .15/independent. The third, .05/midpoint, worsens
slightly for both controllers. At .05/nested neither full controller recovers
its original no-update performance; at .15/independent both do.

The largest new primary harm is .15/midpoint, where full cost becomes
.113015207820. Averaging improves that environment slightly against frozen
but worsens .15/nested substantially, to .089755542148. The excluded shared
diagnostic improves to .096831374563 and .096828866043; it does not rescue
the declared panel verdict.

## Fewer references, more costly errors

| Full minus frozen, per original task | Primary | Average |
|---|---:|---:|
| Added later wrong-report loss | +.000245377969 | +.000136010625 |
| Saved later reference expense | −.000200983897 | −.000124025336 |
| **Net change** | **+.000044394072** | **+.000011985290** |

Across one 100-task episode, primary full retention removes .200984 expected
references and adds .024538 wrong reports. Averaging removes .124025 references
and adds .013601 wrong reports. At .1 per reference and 1 per error, the saved
references do not cover the added mistakes. This is the reverse of the
preceding attribution's excessive-checking pattern at the aggregate level.

Primary full retention changes the future response table on .713127% of
episodes, compared with .387458% for warnings-only retention. The second label
changes the warnings-only table on .402950%. Averaging gives .573755%, .305271%
and .331279%, respectively. Changed beliefs need not change actions, and a
changed table does not by itself establish useful learning.

Compared with the first-task posterior, full retention changes the MAP model
on .753874% of primary episodes and .750809% for averaging, where it is only
a model-label diagnostic. This study does not decompose those switches
causally; the exact action and error/reference costs determine the verdicts.

## Does the earlier costly caution persist?

The diagnostic includes only the same physically costly report-to-reference
events identified in the preceding attribution: an additional first reference
causes a later reference where the old passive report's physical error risk
is below .1. It is evaluated under every physical Q, and its starting event
probability reproduces that sealed analysis exactly. It is not a selected
replacement evaluation population.

| Panel persistence measure | Primary | Average |
|---|---:|---:|
| Original costly-reference event probability | .000707338261 | .000758136359 |
| Still a reference after second feedback | .000683183283 | .000634882426 |
| Returns to original report | .000024154979 | .000123253933 |
| Flips to opposite report | 0 | 0 |
| Fraction released | **3.414912%** | **16.257489%** |
| Later cost contribution of those changes | **−.000000709067** | **−.000005416014** |

The released fraction is a ratio of probability masses across the panel,
not a fraction of enumerated states or the mean of environment percentages.
Correction within this set is beneficial, but changes outside it contribute
+.000045103139 for the primary and +.000017401303 for averaging. Those
contributions plus the local savings exactly recover the total regressions.
The physical-Q diagnostic is not evaluated under the original prior; the
zero entries in the prior's `costly_caution` object are unused placeholders,
not a measured absence of prior events.

| Environment with positive starting event mass | Primary released fraction | Average released fraction |
|---|---:|---:|
| .05 / independent | .021935% | 3.903844% |
| .05 / midpoint | .000624% | 4.451260% |
| .05 / nested | 1.99134e−11% | 22.074343% |
| .15 / independent | 11.305180% | 8.174946% |
| .15 / nested | 85% | No starting events |
| .25 / nested | 75% | No starting events |
| Old shared, excluded | 90% | No starting events |

Neither controller has starting costly-reference events in .15/midpoint,
.25/independent or .25/midpoint. Large released fractions in some nested
primary environments refer to very small original event probabilities and
must not be confused with a large population benefit. The primary's
.05/nested cost improvement also largely comes from other decisions: almost
none of its identified costly agreement references are released after this
one further observation. All exact event masses and cost components remain
in the record.

## Prior control and FEP interpretation

| Own-prior mean cost | Frozen | Warnings | Full | Original no-update |
|---|---:|---:|---:|---:|
| Primary | .074077147989 | .074074551676 | .074070147834 | .074085969786 |
| Average | .074044460174 | .074041059797 | .074036205232 | .074066205219 |

Both controllers improve their integrated own-prior costs. Averaging has
full≤warnings≤frozen expected later cost conditional on every one of its
488,856 reachable first-observation branch classes. There are no violations.
These are complement-combined classes, not independent experiments.

MAP has no such conditional guarantee. Among 494,164 first-observation classes,
full is worse than frozen in 8,904, carrying .628617% prior probability;
full is worse than warnings in 5,544, carrying .407382%; warnings are worse
than frozen in 3,624, carrying .299408%. All are retained. Their probabilities
are not the unweighted ratios of those branch counts.

VFE/model evidence still implements correct belief updating, while acquisition
uses the previously fixed Bayesian task-cost rule. The prior refinement
control and the physical panel answer different questions: the panel does
not weight environments as the prior does. The present failure shows no
invalid posterior or general impossibility of online learning. It shows that
one further valid update, under this fixed acquisition and feedback schedule,
does not improve this declared task population. There is no new EFE or unique
FEP advantage established. Earlier useful calibration and earlier negative
results stand.

The next recommended work is a bounded audit of remaining task regret using
saved policies: compare the original no-update, one-update and two-update
agents with the best answer/reference decision if Q were known, separating
unnecessary checking, avoidable report errors and calibration expense. The
known-Q decision is an evaluator's bound, not knowledge supplied to an agent.
This would put the useful behavior and the remaining performance gap in one
accounting before selecting another model change. No such audit, third
feedback opportunity, tuned remedy, manuscript integration or sister work
is launched here.

## Execution and provenance

Preparation passed 176,619 checks. Independent rational third moments and
two-observation inference cover 70 small count states, including 384
two-partial-observation cases and 592 unchecked-second cases. Direct enumeration
of three fair targets and their errors checks costs without relying on
complement reduction. Original ties and prior refinement are covered. Forced
first purchases are qualification controls only; main decisions remain frozen.

Qualification took 7.396436539 seconds and the 512-row full-workload benchmark
.636443060 seconds. Its conservative 768.701885-second forecast exceeded
ten minutes. The job therefore launched detached at 16:36:40 UTC, PID 1269570,
with durable external logs and no automatic polling. The user's status request
triggered this completion readback. There was no duplicate launch.

Main execution ran from 2026-09-22T16:36:40.598332+00:00 to
2026-09-22T16:39:37.378091+00:00: **176.773341227 seconds wall** and
176.597781642 seconds CPU on one Python 3.10.12 process. All 36,824,879
assertions pass, mostly repeated exact invariants. The census includes 136,499
saved count rows and 259,142 reachable controller/count rows. The 306 bridge
checks reproduce prior full costs, first and second risks, calibration and
the physical caution-event probabilities. Assertions are not independent
experiments or scientific success criteria.

This was the first attempt, with no failed qualification or execution, frozen
source correction, rerun, sampling, price/prior tuning or acquisition
reoptimization. Readback verified 15 input, 31 output and 209 preserved entries
by size and SHA-256. The **5,390,552-byte** generated record is:

`/mnt/bioIce1/fep-ideas/formal-checks/fep-second-feedback-v1/attempt-01/`

It includes the new second-feedback tables, exact results by environment,
prior and persistence controls, frozen source snapshots, qualification,
launch metadata and durable logs. Earlier frozen inputs, reports and
manuscripts are unchanged. Source/research notes remain in this folder.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Contract | 7,804 | `51c9accd6d348081c2cbcee9a72581b5b19ff1a3e7daee29714242ed580f6a65` |
| Checker | 28,619 | `13012ae27267ac4b816d2918ae0ee82bfd41156897284daf6934292b03e6b955` |
| MANIFEST.json | 61,560 | `c277bee40484ded7c1393a17da7df005314c9218f6095ca2ad0b110d1a187d37` |
| RESULTS.json | 418,632 | `2341c4f74e03be9f55c188bcf722b5ed9ce3185778538f50f8eb1efca24f4cba` |
| PRIOR_CONTROL.json | 29,771 | `3e7643b9b89f992f8fd58404bfa55edbc737f5804790cd9dd17f40eaf0d9b363` |
| SECOND_TASK_TABLES.jsonl.gz | 3,799,673 | `6c4e7739452bd5a94a66c456e47d424a7524ddcfe2b3935e2e33eef7ca8dc5b9` |
| QUALIFICATION.json | 683 | `26ad67088cb36ea3623856440d2063165b0e0c00d994a0f2dd202111a8d199d8` |
| RUN_LOG.txt | 553 | `a728c3b9cd50b4a8186afab5005200dccfade9ac87ab2b2fffc99062c46f1c40` |
| DETACHED_STDOUT.txt | 387 | `a8cc79a305eb48224bcc3d12c6ae74a8a9867a8e9d16cf808bb47491be3a9167` |

The preceding attribution manifest remains
`657feb75ecca2ebf17b68ff58544247ec2071ff0649e8c165346289cd48cbd99`.
