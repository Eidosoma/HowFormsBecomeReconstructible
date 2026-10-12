# E036 — can cue-sensitive writing survive repeated rebuilding?

**Complete and independently verified. The cue-contrast serial policy failed
both its primary improvement criterion and its durability requirements.**
Finished on **29 September 2026 at 09:04:54 UTC**, in 13h43m56s, about 2h58m31s
earlier than forecast. Independent replay verified all **1,591,296 terminal
and 114,688 body scores**, every source/serial/holding/terminal update, array
commitment, scalar capture/copying decision, statistic and conclusion.
The subsequent [E037 diagnosis](../E037_repair_support_diagnosis/README.md) is complete and retained; [E038](../E038_weak_bridge_capture/README.md) is complete: adding ordinary coactivity at exact-zero cue products passed the primary improvement and all sixteen-renewal durability requirements.

Under the common delayed normalized terminal reader, cue-contrast full
rewriting gives **0/512 scattered-damage both-cue successes at h8 and h16**.
The standard writer with strong preservation and delayed settling gives
**418/512 (81.64%) at h8** and **290/512 (56.64%) at h16**. The primary h16
candidate-minus-reference difference is **-56.64 points [-60.55, -52.54]**.
This is a large observed loss, not merely an imprecise benefit. Preserving
strong weights with cue-contrast capture also gives zero scattered successes
at h8/h16. Only initial acquisition passes the candidate's nine durability
requirements; eight fail.

All values below are normalized scattered-terminal both-cue success (%) on
the same 512 fresh lineages. Each policy generates its own serial history.

| Policy | h1 | h3 | h8 | h16 |
| --- | --- | --- | --- | --- |
| Standard / preserve strong / delayed settling | 100.00 | 96.68 | 81.64 | 56.64 |
| Standard / rewrite all / delayed settling | 100.00 | 96.48 | 76.56 | 39.06 |
| Cue contrast / preserve strong / delayed settling | 100.00 | 85.74 | 0.00 | 0.00 |
| Cue contrast / rewrite all / delayed settling | 100.00 | 85.94 | 0.00 | 0.00 |
| Standard / preserve strong / original settling | 100.00 | 95.12 | 67.38 | 32.81 |
| Cue contrast / reading blocked | 0.00 | 0.00 | 0.00 | 0.00 |
| Cue contrast / writing blocked | 0.00 | 0.00 | 0.00 | 0.00 |
| Protected copy | 100.00 | 100.00 | 100.00 | 100.00 |
| Cumulative damaged copy | 100.00 | 85.55 | 0.00 | 0.00 |

A positive **prespecified secondary result** comes from the standard writer.
Delaying renewal settling raises h8 scattered success from **67.38% to 81.64%**,
+14.26 points [10.16, 18.36], and h16 success from **32.81% to 56.64%**,
+23.83 points [18.75, 29.30]. Both comparisons hold final reading fixed.
Within delayed standard writing, strong preservation beats full rewriting
at h16 by **17.58 points [13.48, 21.88]**. These are pointwise secondary
intervals; the failed primary remains failed.

Delayed standard preservation has h8 scattered interval **[77.93%, 85.16%]**,
intact success 90.62%, and all 24 original context gates pass at that horizon.
At h16 its scattered interval is **[52.54%, 60.55%]**, intact success 64.84%,
and 18/24 context gates pass. Thus it delays deterioration and is a useful
lead, but sixteen-renewal reliability remains unestablished. A favorable h8
comparison cannot replace the frozen h16 candidate or decision.

Cue-contrast/full-rewriting body success also falls, to **4.30% at generation
8 and 0% at generation 16**. The collapse is not confined to terminal testing.
Its intact/square terminal success is only 1.76%/2.54% at h8 and zero at h16.
Protected copying retains 100% observed both-cue success at every measured
horizon; cumulative damaged copying collapses, and reading-/writing-blocked
chains score zero. The initial acquired records pass all original normalized
context gates. No earlier cohort is pooled with these results.

E035's single-boundary cue-filter benefit did not translate into a durable
serial policy. The subsequent E037 saved-record diagnosis found that pure contrast restored
zero of 572,280 returning connections, whereas standard writing restored
566,862, initially weak. With strong preservation, contrast support exactly
matched cumulative damaged copying. Under paired cue dynamics, returning cells
with zero incident inherited weights have zero cue difference, preventing pure
contrast recapture. E038 prospectively tested ordinary coactivity at exact-zero
cue products and reached 82.03% scattered success at h16 versus 57.81% for
standard delayed preservation on its fresh cohort. Primary improvement and
all nine durability gates passed. E037 ran no new trajectories; E036’s failed
primary is unchanged by this later, different policy.

All nine policies, seven active bodies, both terminal readers, three injuries,
seven terminal arms and initial/h1/h3/h8/h16 assays were retained. Each active
body loses 24 non-port cells at every renewal. Core policies use 1024 settling
steps in 2048 total steps; the original reference uses 256, with common
1024/2048 final reading for every policy. The candidate uses d_i*d_j, where
d is the difference between tanh-transformed activities under opposite cues,
divided by two. No desired output, donor packet or endpoint score enters it.

The original excluded validation's signed-zero auditor failure is preserved.
Revision 2 changed the auditor's scalar reduction convention while leaving
the production model byte-identical and all scientific settings unchanged.
All eight checks passed, including exact E031 reference agreement through all
sixteen boundaries. The fixture and benchmark independently replayed
24,864/12,432 terminal and 1,792/896 body scores. All 28 inputs were frozen.
The first prelaunch capacity failure and successful full recheck are retained;
no reserve was changed or bypassed. The run used eight workers, one numerical
thread each. Simulation took 24,797.198 seconds; audit took 24,636.037 seconds.

Artifact closeout passed at **04:15:45 UTC on 30 September**, verifying 56
fixture, 56 benchmark and 831 scientific original outputs, all 28 frozen
inputs, source provenance, operational receipts, the first failed attempt
and capacity recheck. All figure hashes passed and the scientific figure was
visually inspected. Scientific retention is 146,135,546 bytes, below the
499,610,528-byte forecast including reserve. Available space at closeout was
257,671,168 bytes. No new trajectories ran during closeout.

- [Scientific report](runs/serial_v1/REPORT.md)
- [All statistics](runs/serial_v1/summary.json)
- [Scientific figure](figures/serial_v1/serial_capture.png)
- [Independent verification](runs/serial_v1/INDEPENDENT_AUDIT.json)
- [Artifact closeout](analysis/closeout_v1.json)
- [Frozen protocol and technical revision](PROTOCOL.md)
- [Prior evidence index](SOURCE_DATA.json)
- [Preserved first attempt](../E036_serial_cue_capture/README.md)
- [Technical validation](analysis/technical_v1.json)
- [Runtime and storage forecast](analysis/forecast_v1.json)
- [Capacity recheck](analysis/prelaunch_capacity_recheck_v1.json)
- [Prelaunch verification](analysis/prelaunch_scientific_v1.json)
- [Verified launch and estimate](analysis/scientific_launch_verification_v1.json)
- [Durable job status](jobs/serial_v1/status.json)
