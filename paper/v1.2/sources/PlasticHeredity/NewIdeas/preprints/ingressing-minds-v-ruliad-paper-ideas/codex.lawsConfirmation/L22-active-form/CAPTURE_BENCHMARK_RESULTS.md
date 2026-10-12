# D186 early capture benchmark results

12 October 2026. The disposable benchmark completed at **16:34:44.038427 UTC**
in **321.755694 seconds** on one single-thread process, CPU 6, nice 10.
The user-requested saved audit verified all **1,093 frozen inputs**, **289
output files**, every saved case/control and **569 exact alias checks** in
8.40 seconds, without new dynamics. All 16 records, 68 repair paths, 93 named
reads and 44 contrasts were retained; exact packet aliases reduced the actual
fresh-read executions to 72. All repairs and unique reads had full independent
replay during the run. No benchmark worker remained at that status check.

## Preliminary signal and its limits

The [frozen intervention](CAPTURE_V1.md) captures the allowed post-injury body
into the existing R reference once. Subsequent rates and dynamics are unchanged.
No old parent reference is supplied; only the ordinary theta record enters
the fresh reader. This is a combined maintenance-and-writing intervention.

| Common record condition | Correct recognition | Own minus partner preference | Correlation with original record |
| --- | ---: | ---: | ---: |
| Unchanged input | 50.000% | 0.000 | 0.799566 |
| Ordinary zero-start live writing | 50.000% | 0.000 | 0.790030 |
| Captured reference, live writing | 62.500% | 0.250 | 0.744078 |
| Captured reference, fixed reading | 56.250% | 0.125 | 0.793548 |
| Capture-matched conventional averaging | 56.250% | 0.125 | 0.795075 |
| Captured reference held unchanged | 64.0625% | 0.28125 | 0.702717 |
| Captured reference, writing disabled | 50.000% | 0.000 | 0.799566 |
| Partner body captured, live writing | 37.500% | -0.250 | 0.372100 |

The ordinary common-input and zero-start message accuracies were
`[0, 1, 1, 0]`. Captured live writing produced `[0.25, 1, 1, 0.25]`:
both previously missing identities recovered partly, rather than only a
decline in alternative recognition. Fixed reading and its matched averaging
comparator produced `[0.25, 1, 1, 0]`; they did not recover the fourth identity.
These are averages over four records and four readouts per record in **one
disposable founder block**, not independent replication blocks.

Directionality follows the donor: the partner-body capture reverses the
common own-minus-partner preference. Own-scrambled capture gave 43.75 percent
own recognition and zero net preference; history-erased capture gave 37.5
percent own recognition and zero preference. Turning writing off preserved
the input packet exactly and removed the gain. These selective controls
support a body-dependent lead in this block, not a general correction result.

Captured live writing also increased common sign fidelity from 0.709839 to
0.787720 and projection gap from zero to 0.331022. However, correlation with
the original record declined from 0.799566 to 0.744078. Better recognition is
not complete record or shape preservation. The held-reference improvement is
explicitly protected snapshot memory and is not substituted for the updating
reference result.

Informative-residual input recognition was 76.5625 percent. Ordinary live
writing also gave 76.5625 percent; captured live writing gave 85.9375 percent.
Captured fixed reading gave 90.625 percent and its matched averaging gave
87.5 percent. Thus the live loop does **not** beat averaging in both packet
conditions, and not every residual message improves. Positive intact-parent
and supplied-target controls read at 100 percent for every message. Disabled
reading gave 25 percent pooled, not 25 percent for each message.

## Resource measurement and next test

Benchmark outputs occupy **115,027,960 bytes** (109.70 MiB); uncompressed
arrays total **178,745,472 bytes** (170.46 MiB). Complete stage retention at
the user-owned check was **305,648,344 bytes** (291.49 MiB), including all
qualification artifacts and receipts. Peak process RSS was **178,540,544
bytes** (170.27 MiB). Data and logs are external; no evidence was deleted.

The unchanged 64-record panel remains the next development test, not a new
confirmation. Its [separate execution contract](CAPTURE_PANEL_EXECUTION_V1.md)
retains all four previously declared blocks and all controls. Budget roughly
21m27s by serial extrapolation, with a conservative 45m54s allowance on one
low-priority CPU. Its separate 2.5 GiB stage cap includes retained qualification
attempts and leaves the original benchmark cap untouched. The initial 1.5 GiB
panel estimate was rejected before freeze, with no main dynamics or deletions.
The benchmark is excluded from panel estimates. No favorable
outcome changes a setting, case, threshold or comparator.

L20/L22 remain STRESS_TESTED / MIXED. This result does not establish autonomous
interface repair, prospective prediction improvement or serial renewal.

## Immutable evidence

External root:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-early-capture-v1`.
Run: `l22_early_capture_v1_benchmark_attempt1`.

- Freeze: `runs/FREEZE_<run>.json`, SHA-256
  `ada81e6c4bad1985ffa6cbe758891da8d4e7c49101d68803ec59f3e6bcf0d8e9`.
- Completion: `runs/<run>/COMPLETE.json`, SHA-256
  `56cf6fe5096bde632814bf6a242a73675e4d316db57b2ae895f33f9e83e1fc6a`.
- Scores, comparisons, mappings, arrays and full replay proof:
  `outputs/<run>/{records.json,contrasts.json,read_map.json,CHECK.json,...}`.
- Startup and log: `logs/<run>_launch.json` and `logs/<run>.log`.

The status-turn saved audit was read-only; it did not create a new receipt.
The panel freeze will bind a fresh saved-benchmark check, this report and the
original immutable completion evidence before panel acquisition.
