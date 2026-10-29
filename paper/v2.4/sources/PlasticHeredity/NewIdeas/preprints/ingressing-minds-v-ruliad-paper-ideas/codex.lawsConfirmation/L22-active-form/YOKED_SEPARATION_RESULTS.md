# D194: real feedback separation, smaller changes in the stored record

**24 October 2026: COMPLETE / independently SAVED-CHECKED.**
[Fixed diagnostic](YOKED_SEPARATION_V1.md),
[mechanical tables](YOKED_SEPARATION_TABLES.md),
[D193 outcome](YOKED_REFERENCE_PANEL_RESULTS.md).

D193 changed the body-driving feedback signal, but the resulting outgoing
records and fresh-reader bodies differed much less on average. Its tied or
slightly worse recognition was not caused by accidentally replaying identical
inputs. These observations are consistent with buffering of the intervention
along the reconstruction process. They do not identify a unique mediating
step, prove equivalence, or rescue D193's failed positive pilot lead.

## What reached each stage

These are **mean relative RMS field differences**, expressed as percentages
of the two fields' pooled RMS amplitude. They are not percentages of lost
information. Each pair is measured before averaging roles, draws and futures;
all four exposed histories and 64 records remain. Different stages have
different amplitudes; these are descriptive distances, not causal attenuation
coefficients. Native RMS values and all distributions are in the tables.

| Stage at the final saved checkpoint | Common | Residual |
| --- | --- | --- |
| Body-driving feedback input | 6.986% | 7.869% |
| Recipient body V | 3.190% | 4.033% |
| Recipient's own reference R | 1.950% | 2.121% |
| Centered tanh writer drive | 3.173% | 3.214% |
| Outgoing record theta | 1.348% | 1.239% |
| Terminal fresh-reader body V | 1.101% | 1.306% |

The pattern holds at the history level: common terminal input differences
range 6.315–8.257% across history means, versus 1.024–1.773% for outgoing
theta; residual input means range 7.481–8.478%, versus 1.031–1.359% for theta.
This is not uniform smallness. The largest **record-mean** input differences
are 17.615% common and 18.263% residual. Largest record-mean outgoing-record
differences are 5.669% and 4.048%; terminal reader differences 5.624% and
6.536%. Individual draw differences can be larger than these averaged values.

Both arms are changing substantially relative to their own starting states:
LL body movement from birth is 75.262% common / 72.230% residual, own-reference
movement 52.206% / 47.730%, and theta movement from the incoming record
56.522% / 76.202%. YL movements are similar. The between-arm difference is
small compared with this shared reconstruction; the system is not simply idle.

All same-role LL/YL fields agree at birth and at step 1, as required by their
shared initial snapshot and paired body noise. By checkpoint 50, input
separation is about 1.51–1.55%, but outgoing-theta separation is only about
0.00035%. Record differences grow through checkpoints 250, 500 and 1000.
No claim is made about the exact first divergence time between saved points.

## The complete donor recordings and categorical outcomes

Across all 1,000 post-birth donor frames, mean A/B relative reference separation
is 5.152% common / 5.318% residual. At the final frame it is 6.983% / 7.870%,
with mean cosine similarity 0.996977 / 0.996355. These donors share the same
captured history and differ in their repair-noise stream. They supply a real
but closely related alternative, rather than a new recipient-specific event.

Recipient body states are saved at only six checkpoints. Full donor traces
cannot fill in the missing LL/YL recipient states, integrate their unsaved
writing history, or identify a continuous-time mediation pathway.

Every original recognition/preference/projection result was recovered. Common
recognition is unchanged on every paired draw. Residual LL loses recognition
on four role-specific draws from two records and never gains it: role-averaged
recognition changes by −0.390625 points, preference by −0.68359375 points.
Neither the sign nor the size of that D193 result is revised by this diagnostic.

The four changed draws have close competing terminal scores. Their
own-minus-strongest-other margins move from positive under YL to negative
under LL:

| History / future / record / draw | LL margin | YL margin |
| --- | --- | --- |
| 319100 / 1 / 14 / 0 | −0.021013000 | +0.014350540 |
| 319100 / 1 / 14 / 2 | −0.010658386 | +0.010833363 |
| 319101 / 1 / 15 / 2 | −0.000672030 | +0.011149682 |
| 319100 / 2 / 14 / 2 | −0.021353668 | +0.011791851 |

All four are residual, role A, message 3. For context, mean residual winner
gaps are about 0.4066. This is a descriptive comparison, not a fitted margin
threshold. One error is against a third template: its own-minus-partner gap
remains strongly positive (LL 0.861656, YL 0.862330), while another template
slightly overtakes the intended one. This makes the all-alternative margin
useful for diagnosis alongside the registered own-minus-partner measure.

For the changed draws, outgoing theta differs by 1.804% or 4.360% within the
affected role; terminal reader bodies differ by 3.427–7.919%. Those cases are
shown alongside, and never substituted for, the complete retained panel.
Categorical recognition misses many continuous changes elsewhere, but the
mean surviving reader differences are about 1.1–1.3%, not a concealed panel-wide
gain in reconstruction. No geometric difference is counted as successful repair.

## Checks, costs and limits

The code imports no simulator, writer or fresh-reader implementation. It only
reads immutable arrays, computes fixed distances/transforms/scores and checks
their addresses. All **151,168 field-pair rows**, **4,096 terminal reader
outcomes**, **1,760 address/self-replay identities** and original score bridges
passed independent scalar checks. Maximum scalar discrepancy was
6.661338147750939e−16. Reopened arrays independently reproduce all **462 views**.

Qualification attempt 1 retained 70 passes and two failures from a test-fixture
alias: changing the fake old count also mutated the observed fixture. Deep
copies and an explicit nonmutation assertion fixed the tests. Attempt 2 passed
**all 72 checks** in 33.463 s; full driver 35.992977734 s. No study quantities
were extracted during qualification. The complete synthetic trace pair took
1.615106732 s, giving a 205.842 s foreground allowance and 550 s stop guard.

Freeze completed **19:05:57.825125 UTC**, binding **16,989 inputs**, including
the original D193 evidence and qualified diagnostic. The analysis finished
**19:07:21.783590 UTC** in **42.795710395 s**. The separate saved check passed
at **19:08:20.389390 UTC**. No physical dynamics, model fitting or new scientific
run occurred. These are retrospective, exposed histories; not confirmation.

One CPU/thread, CPU6, nice10. Peak process RSS **241,541,120 B (230.352 MiB)**.
Derived arrays total **7,534,592 uncompressed bytes**. Stage retention before
COMPLETE was **22,415,678 B (21.377 MiB)**, including both qualification
attempts, under the separate 128 MiB cap. Raw source arrays were not copied.
All data/logs/fixtures/caches remain external; local additions are code/docs.

Root: `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-yoked-separation-v1`.
Exact freeze/manifest/completion/audit/summary identities and complete mean
tables are in [the generated report](YOKED_SEPARATION_TABLES.md); all per-record
arrays, strata, omission means and distributions remain in `outputs/`.

## Next question

A more direct next test of ongoing responsiveness would disturb the recipient
**after the sister recording has been sealed**, give the same disturbance to
LL and YL, and ask whether own-state feedback then improves recovery. Retain
the undisturbed controls, both families, the same writer and carrier, and
freeze the disturbance and comparisons before outcomes. This asks about an
unexpected recipient-specific event, rather than increasing noise until a
favorable answer appears. It has not been implemented or launched here.

D193's negative result remains. D194 narrows the interpretation to a real but
substantially buffered displacement around a shared history; it establishes
neither universal benefit nor absence of benefit from ongoing embodiment.
L20/L22 remain **STRESS_TESTED / MIXED**. The queued fresh-case recipient
matching decision test is still a separate requirement.
