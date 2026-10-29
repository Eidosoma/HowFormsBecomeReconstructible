# E099 — capture on fixed E098 bodies

23 October 2026. **Complete and verified; primary conjunction not met.** All 32
blocks finished at **17:58:45 UTC**, in **1 h 24 min 42.40 s** on four one-thread
workers. Closeout passed at **18:50:30 UTC**: **606 outputs / 49 frozen inputs**
verified, final figure inspected. No E099 run is active.

The noise benefit repeated: pruned-mixture success rose **52.44% → 58.84%**,
**+6.396 points [3.955, 8.984]**. But hybrid versus ordinary capture at the
selected connections on the same body gave **−0.146 [−0.928, 0.488] points**,
unresolved; these are the two adjusted 97.5% primary intervals. Ordinary selected
capture retained a **+6.543-point** noise benefit (secondary 95% interval
**[4.346, 8.789]**). Mixture sign/magnitude component effects were unresolved.
Noise still helps rebuilding, but this selected capture-rule switch does not
explain its average benefit in the declared comparison. Individual harms and
all original endpoints remain visible. [Full interpretation](INTERPRETATION.md).

E098 changed the supplying body's cue noise and found better rebuilding of
pruned records. E099 holds each saved body fixed and changes only the originally
selected connections in its captured record. Compare usual hybrid capture (H)
with ordinary coactivity (O). On the independently noisy pruned body, also swap
signs and magnitudes separately: S uses H signs/O magnitudes, M O signs/H
magnitudes. Intact and paired-noise bodies remain as H/O controls.

The primary pooled-mixture conjunction requires H to outperform O on the same
independently noisy pruned body, and the pruned noise benefit to repeat under
new matched terminal readers. Both adjusted 97.5% whole-block intervals must be
positive. Component effects are secondary, pointwise 95% descriptions. Negative
and unresolved results, every individual harm and all original E098 endpoints
remain visible. No old outcome enters a new confidence interval.

All 32 E098 sources are reused, without filtering: 2,048 source contexts and
4,096 new case/draw rows. One original supplying body per noise/input condition,
two fresh terminal draws, 38 physical record slots, 77,824 terminal cue
observations. The unchanged paired-pruned H/O records are one checked physical
alias. No source ancestry or supplying writer dynamics are repeated.

- [Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md), [decisions](DECISIONS.md).
- [Passing tests](analysis/tests_attempt_002.json), [preserved first attempt](analysis/tests_attempt_001.json).
- [Pinned sources](SOURCE_DATA.json), [all-source structural preflight](analysis/prereader_support_v1.json).
- [Sample freeze](SAMPLE_FREEZE.json), [qualification](analysis/qualification_v1.json),
  [forecast](analysis/forecast_v1.json): 92 benchmark outputs / 45 inputs checked;
  scientific run/job each freeze 49 inputs. Benchmark completed in 63.66 seconds.
- [Launch](jobs/capture_v1/launch.json), [startup](jobs/capture_v1/startup.json),
  [durable status](runs/capture_v1/STATUS.json), [log](jobs/capture_v1/run.log).
- [Scientific report](runs/capture_v1/REPORT.md), [complete statistics](runs/capture_v1/summary.json),
  [individual cases](runs/capture_v1/cases.csv), [figure](runs/capture_v1/capture.png),
  [verified closeout](analysis/closeout_v1.json).
- [E098 interpretation](../E098_writer_pairing_tradeoff/INTERPRETATION.md).

The workflow refuses existing run paths. Technical qualification and the sample
freeze preceded scientific reads. Forecasts over ten minutes run detached,
with one bounded startup check and subsequent status checks on user request.
No automatic extension, restart or successor. Manuscript integration is separate.

The user subsequently authorized the reciprocal selected-content/outside-record
swap. [E100 is complete](../E100_saved_record_region_swap/INTERPRETATION.md):
selected content transfers a rebuilding benefit to the paired background, and
the outside record also contributes. Both primary requirements passed under
new matched readers; all original endpoints and individual harms remain.
