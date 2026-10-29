# TT022: repeated capture does not preserve the one-read advantage

The completed four-block pilot gives a negative result for extending TT021's
one-read capture advantage to this repeated-capture policy. After eight body
replacements, common-record recognition is 48.438% with repeated capture and
50.391% with ordinary repair, a descriptive difference of −1.953 percentage
points. Keeping the first captured record without later writing reaches
68.750%. Repeated capture therefore loses 20.312 points against its identical
starting-packet control. For informative records, repeated capture reaches
48.438%, versus ordinary repair at 80.469% and one-time capture at 89.453%.

These are mean terminal fresh-recipient recognition scores, retaining
fractional tie credit. Each policy/family has 256 future chains from 64 starting
positions, nested in just four exposed population blocks. There are four
futures per record. No significance gate, population confidence interval or
fresh-population confirmation is claimed.

| Policy | Common records: terminal recognition | Informative records: terminal recognition |
| --- | ---: | ---: |
| Ordinary repair | 50.391% | 80.469% |
| Repeated capture with memory updates | 48.438% | 48.438% |
| Fresh held snapshot each cycle | 28.906% | 30.078% |
| Captured fixed-reading writer | 55.078% | 59.766% |
| Fixed-reader averaging | 57.031% | 69.531% |
| Keep first captured record; no later writing | 68.750% | 89.453% |
| Keep original input; no writing | 50.000% | 85.547% |

For the primary capture-minus-ordinary comparison, the four block differences
are +3.125, −3.125, −7.812 and 0.000 points in identity order
21000000–21000003. The small pooled difference must not be called equivalence.
Repeated-minus-one-time differences are negative in every block: −12.500,
−25.000, −18.750 and −25.000 points for common records; −28.125, −54.688,
−35.938 and −45.312 points for informative records. All blocks, messages,
records and failed chains remain in the analysis.

| Planned terminal contrast | Common difference | Informative difference |
| --- | ---: | ---: |
| Capture minus ordinary | −1.953 pp | −32.031 pp |
| Capture minus held | +19.531 pp | +18.359 pp |
| Repeated minus one-time capture | −20.312 pp | −41.016 pp |
| Capture minus unchanged input | −1.562 pp | −37.109 pp |
| Fixed writer minus average | −1.953 pp | −9.766 pp |
| Capture minus average | −8.594 pp | −21.094 pp |

The updated-memory policy does outperform repeatedly recaptured held snapshots,
which deteriorate further. That contrast does not rescue the primary result.
The serial fixed-writer advantage also fails directionally against averaging
in these cases. These are whole-policy comparisons: starting packets differ
between most arms, and later reading streams diverge as their packets diverge.
They do not isolate the effect of a writer on the same body stream. Both fixed
and average execute and save both native and averaging traces, inheriting only
their declared output; there is no equal-compute or efficiency claim.

Individual adverse changes are substantial. Common-record capture versus
ordinary improves 24, worsens 29 and ties 11 of the 64 four-future record means.
Repeated versus one-time capture improves 16, worsens 42 and ties six. For
informative records, capture versus ordinary improves eight, worsens 48 and
ties eight; repeated versus one-time improves three, worsens 56 and ties five.
Four-future means are coarse estimates, so these are observed paired changes,
not precise estimates of each record's latent capacity.

Terminal usefulness and uninterrupted body performance agree on the main
direction but remain different endpoints. The following percentages require
uniquely correct recognition at every one of the eight specified endpoints;
ties count as failure. They do not assert correctness between measured endpoints.

| Family | Policy | All eight developed bodies pass | All eight repaired bodies pass |
| --- | --- | ---: | ---: |
| Common | Ordinary | 41.406% | 32.422% |
| Common | Repeated capture | 21.484% | 15.234% |
| Common | One-time capture | 66.797% | 52.734% |
| Informative | Ordinary | 70.703% | 67.578% |
| Informative | Repeated capture | 21.875% | 12.891% |
| Informative | One-time capture | 69.141% | 47.266% |

The saved generation curves locate a useful next diagnostic. Before the first
new injury, repeated and one-time capture have identical incoming packets and
identical developed-body recognition: 69.922% common and 90.234% informative.
By the second developed body, repeated capture is at 64.844% and 61.328%, while
the no-later-writing control is at 69.141% and 89.844%. At generation eight,
repeated capture is at 47.656% and 44.531%. This pattern motivates examining the
first rewriting step, especially for informative records. It does not by itself
identify a causal failure mechanism or prove monotonic decline in every chain.

Keeping the original captured packet is the best observed terminal policy in
this panel. That control benefits from exact preservation of the record: the
protocol repeatedly injures and replaces bodies but adds no new record damage
after the starting packet. Its advantage cannot establish that rewriting is
unnecessary when the record itself is corrupted, or that an autonomous system
can supply this protected storage. Only each actual 2,048-byte outgoing packet
crosses a replacement; no ancestral body or captured memory crosses. The
reader, task apparatus, intervention schedule and original message-noise
pairing remain supplied.

TT021's registered one-read finding is unchanged. TT022 shows that extending
the intervention through eight replacements does not automatically retain its
benefit in these exposed cases. The strongest next lead is to diagnose the
first capture/write transition against the same-packet no-writing control,
then decide whether a limited-writing policy merits a separately frozen new
cohort. This is a post-result proposal; no successor or additional trajectories
are launched here.

All four blocks completed their physical replay and saved checks. The original
execution stopped at 16:58:09 UTC on 15 October 2026, 75 minutes 13 seconds after
startup, on a report-order assertion. JSON key sorting changed table order;
the summary and every reported value were intact. The original failed run,
report and summary remain unchanged. A separately retained recovery, written
after acquisition and before effect inspection, completes saved verification
and renders the report in stable JSON order. It reproduces the summary
byte-for-byte and changes only report row order. No dynamics are rerun.

Closeout passes: 328 frozen inputs, 10,100 original run files, 68,032 saved
array identities, 3,584 record rows and 2,016 batch inheritance transitions.
Acquisition replay matched all 45,696 native checkpoint arrays exactly; maximum
averaging discrepancy is 7.11e−15 against the unchanged 2e−12 tolerance.
The saved recovery took 59.70 seconds and preserved every original file.
Original run storage is 1,167,733,216 bytes, below the four-GiB cap.

See the [checked report](checks/report_recovery_v1/REPORT.md),
[full summary](checks/report_recovery_v1/SUMMARY.json),
[closeout](CLOSEOUT.json), [recovery disclosure](REPORT_RECOVERY.md),
[protocol](PROTOCOL.md) and [execution record](EXECUTION.md).
