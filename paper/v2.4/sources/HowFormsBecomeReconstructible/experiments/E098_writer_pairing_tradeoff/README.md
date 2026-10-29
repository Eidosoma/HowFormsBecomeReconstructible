# E098 — does writer cue pairing cause the pruning penalty?

23 October 2026. **Complete and verified; primary prediction passed.** All 32
fresh source blocks completed at **14:27:42 UTC**, in **2 h 27 min 41.56 s** on
four workers. Closeout passed at **15:49:03 UTC**, verifying **1,997 outputs / 64
frozen inputs**, job snapshots and the inspected final figure. No run is active.

Independent writer noise raises pruned-mixture rebuilding success from **55.71%
to 60.99%**, a **+5.273-point** gain with adjusted **97.5% interval [2.734, 7.812]**.
The pruning interaction is **+5.469 [2.539, 8.398]** points; the paired baseline
cost is negative. Native pruned success also improves, **76.61% to 84.42%**, as
a secondary result. Individual harms remain: **161 gains / 53 harms** in
mixtures and **170 / 10** in natives, each across 2,048 dependent comparisons.
This establishes a writer-pairing dependency, not exclusive fallback mediation
or a universally beneficial rule. [Full interpretation](INTERPRETATION.md).

Compare intact and once-pruned records while changing only noise pairing across
the two cue episodes that supply **one subsequent rewrite**. Compare matched
noise with independent noise, keeping birth activity, injury, marginal noise,
capture and all terminal-reader conditions fixed. Use 32 new source blocks,
native/mixture × sham/pulse, four founders, four recipients and two matched fresh
terminal draws. The unchanged source history has 32 ancestry rewrites and three
post-pulse continuation rewrites; the causal intervention adds just one rewrite.

The primary prediction concerns mixtures: independent writer noise both reduces
the pruning penalty and improves the pruned records themselves. Both adjusted
whole-block intervals must be positive. Worsening intact records alone cannot
meet this criterion. A penalty-attenuation claim additionally requires a negative
paired-noise baseline contrast. Native outcomes, margins, signed transfer,
normalized coupling, all gains/harms and complete immediate/later tables remain
visible regardless of the primary result.

The hypothesis was proposed after known E051 and E073–E097 outcomes. E098 uses
new scientific sources and a decision rule fixed before their generation. Noise
can change the supplying body's dynamics beyond fallback use, so this test
cannot isolate exclusive fallback mediation.

- [Protocol](PROTOCOL.md), [data dictionary](DATA_DICTIONARY.md), [decision record](DECISIONS.md).
- [Tests](analysis/tests_attempt_001.json): all checks passed in 24.58 seconds.
- [Source registry](SOURCE_DATA.json): scientific IDs 980000–980031; excluded
  benchmark IDs 9000980/9000981 and fixture IDs 9000982/9000983.
- [Sample freeze](SAMPLE_FREEZE.json), [qualification](analysis/qualification_v1.json)
  and [forecast](analysis/forecast_v1.json): 194 benchmark outputs and 61 frozen
  inputs checked; scientific run/job each freeze 64 inputs. Benchmark runtime
  77.28 seconds. Storage reserve 5.01 GB, with 44.58 GB free at launch.
- [Launch](jobs/confirmation_v1/launch.json), [startup](jobs/confirmation_v1/startup.json),
  [durable status](runs/confirmation_v1/STATUS.json), [log](jobs/confirmation_v1/run.log).
- [Scientific report](runs/confirmation_v1/REPORT.md), [figure](runs/confirmation_v1/endpoints.png),
  [complete tables](runs/confirmation_v1/summary.json), [closeout](analysis/closeout_v1.json).
- [Predecessor proposal](../E097_pruning_endpoint_synthesis/NEXT_PREDICTION.md).

## Reproduction

From the experiments directory, use `bash run_python.sh` for all Python commands.
Existing runs and evidence are never overwritten. Technical checks preceded the
benchmark; visual inspection preceded qualification. The scientific launch
required the passing test receipt, benchmark qualification and sample freeze.

```sh
bash run_python.sh E098_writer_pairing_tradeoff/tests.py
bash run_python.sh E098_writer_pairing_tradeoff/run.py run --mode benchmark --name benchmark_v1 --workers 1
bash run_python.sh E098_writer_pairing_tradeoff/run.py qualify --name benchmark_v1 --figures-inspected
bash run_python.sh E098_writer_pairing_tradeoff/run.py launch --name confirmation_v1 --workers 4
```

Those commands describe the original sequence; choose a new name for any
additional explicitly justified run. A new passing test receipt changes the
frozen-input set and requires an explicit qualification update. Scientific runs
detach with one bounded startup check. Status checks are user-driven; there is
no automatic extension, restart or successor. Manuscript integration is separate.

The targeted capture follow-up using saved E098 bodies is complete as
[E099](../E099_saved_body_capture/INTERPRETATION.md). The noise benefit repeated
under new matched terminal readers, but a same-body hybrid-versus-ordinary
selected capture benefit was not established. Ordinary selected capture retained
the noise gain; its location within the changed record remains open.
