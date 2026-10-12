# E043 — extra settling does not establish a late-reader benefit

**Complete and independently verified: DELAYED_EXPRESSION_BENEFIT_NOT_ESTABLISHED.**
The workflow finished **5 October 2026 at 18:58:37 UTC**, in **4h00m29s**.
Independent replay passed at **18:58:36 UTC**; artifact closeout passed at
**19:18:29 UTC**. No experiment is running in this experiment tree.

For the normalized reader under scattered injury after 32 rebuilds, original and
extra-time schedules each retain **428/512 (83.59%)**, with no paired success/fail
changes between them. Delayed amplification retains **431/512 (84.18%)**: a gain
of **0.59 percentage points [−1.37,2.34]**, missing the frozen lower-bound-above-five
criterion. It rescues **17/84** original failures but loses **14/428** original
successes; 414 remain successful and 67 fail under both schedules.

In simple terms, waiting longer changes which records work, but the gains and
losses nearly cancel. This fixed timing change offers no clear overall improvement.
The result does not show that all remaining information is lost, or that every
possible reader change would fail. E041's previously verified rebuilding result
remains unchanged.

| Normalized reader at h32 | Intact success | Scattered success | Square success |
| --- | ---: | ---: | ---: |
| Original | 89.45% | 83.59% | 88.67% |
| Extra time alone | 89.45% | 83.59% | 88.67% |
| Delay with extra time | 88.48% | 84.18% | 88.48% |

At h24, delayed amplification gives **454/512 (88.67%)** scattered success versus
**460/512 (89.84%)** for the original and extra-time readers: eight rescues and
fourteen losses. All normalized panels retain their **24/24 context gates**.
The delayed h32 scattered interval is **[80.47%,87.50%]**, still above the 75%
absolute lower-bound threshold; this does not establish a relative timing benefit.
All three fixed-four schedules remain poor under scattered injury: h32 both-cue
success is 2.93%, 3.12% and 2.34%, respectively. All uncertainty intervals and
other controls are retained in the report and statistics.

This controlled receiving intervention reuses all **32 E041 blocks / 512 lineages**,
with unchanged full bridge-rewriting records at h24 and h32. It is not a fresh
replication or a test of a changed serial rebuilding policy. The 258,048
individual-cue scores are repeated observations; the 32 blocks are the inference
units. Secondary intervals and context gates are pointwise. E043's bootstrap
intervals do not replace E041's frozen inference.

| Reader schedule | Settling | Amplification | Total updates |
| --- | ---: | ---: | ---: |
| Original | 1024 | 1024 | 2048 |
| Extra time alone | 1024 | 3072 | 4096 |
| Delay with extra time | 3072 | 1024 | 4096 |

The primary compares delayed versus extra time alone after 32 rebuilds under
scattered damage with the normalized reader. It fixes total duration while
changing the allocation between settling and amplification. All cases, both
receivers, all injuries, cues and seven receiving arms were retained, with
paired noise prefixes and unchanged control packets. No selection of failures
or timing sweep occurred.

All eight excluded checks passed. Independent replay verified every receiving
update and omitted-array commitment, all **258,048 individual-cue scores**, all
statistics and gates, and all paired rescue/loss counts. The original reader
reproduces E041 mean ports exactly for both receivers and all controls. The
scientific figure was inspected. The earlier provisional snapshot matches the
final verified statistics exactly; it remains retained as a historical record.

Artifact closeout verified **33 fixture, 33 benchmark and 312 scientific original
outputs**, all **21 frozen inputs**, source provenance, operational receipts and
figure hashes. Scientific retention is **7,892,394 bytes**, below the forecast
including reserve of 249,656,960 bytes. There were 69,274,898,432 bytes free at
closeout. No frozen input or original output changed.

Simulation took **6,911.685s** and independent replay **7,513.980s**. The full
workflow took **14,429.036s**, exceeding the initial 11,807.699s forecast by
**43m41s**. Completion was at 18:58 UTC, just before the later rough 19:00–19:30
estimate. No new trajectories ran during closeout and no successor was started.

[E044](../E044_transition_diagnosis/README.md) completed the saved-history follow-up
on 6 October. Rescues and losses mostly switch locked-output responses; persistent
failures have much worse prior body histories and more strong connections
weakened in the latest rewrite, while returning-edge reconnection remains active.
It motivates a targeted rollback intervention, which has not started. These
associations do not establish why failures occur or change E043's negative result.

- [Scientific report](runs/expression_v1/REPORT.md)
- [All statistics](runs/expression_v1/summary.json)
- [Scientific figure](figures/expression_v1/expression.png)
- [Independent replay](runs/expression_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Historical provisional snapshot](analysis/provisional_status_v1.json)
- [Verified launch and original ETA](analysis/scientific_launch_verification_v1.json)
- [Completed job status](jobs/expression_v1/status.json)
- [Technical validation](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Frozen protocol](PROTOCOL.md)
- [Pinned prior evidence](SOURCE_DATA.json)
- [E042 diagnosis](../E042_late_failure_diagnosis/README.md)
- [E041 confirmation](../E041_full_rewrite_confirmation/README.md)
