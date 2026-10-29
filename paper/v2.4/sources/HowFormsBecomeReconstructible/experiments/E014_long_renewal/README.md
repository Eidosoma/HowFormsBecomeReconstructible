# E014 — longer renewal

Does founder-specific reconstruction persist through **16 body-written record
replacements**, and how does its fidelity change? This extends E007's unchanged
reader/writer apparatus using 64 fresh blocks and 128-/2048-byte records.

The [protocol](PROTOCOL.md) is fixed before scientific outcomes. Fresh checkpoint
readers follow completed rewrites 1, 3, 8 and 16 and do not feed back into the
lineage. The primary endpoint is the 128-byte after-16 own-versus-foreign-record
contrast. Absolute fidelity and the deficit relative to protected copying are
reported alongside it. All failed founders and control arms remain included.

Status: **complete and independently audited; all prespecified gates passed**.
The frozen 64-block cohort finished on 2026-09-18 at 12:46:52 UTC, in 829.30
seconds (13.82 minutes), including auditing and figures. The detached run used
at most 12 logical CPUs, with one numerical thread per worker. Results were
inspected on the user's subsequent status request; no job remains running.

All 256 founders were retained. Formation qualified 193/256 (75.39%), narrowly
above the 75% requirement; mean within-block sign disagreement was 18.98%.

| Record | After-16 own minus foreign record, percentage points [95%] | Own agreement after 3 → 16 rewrites | After-16 deficit versus protected copy |
| --- | --- | --- | --- |
| 128 bytes (primary) | +1.387 [+0.848, +1.954] | 66.91% → 64.38% | −3.883 points |
| 2048 bytes | +1.402 [+0.925, +1.909] | 71.24% → 65.60% | −10.950 points |

A modest signature of particular founder history remains detectable after
sixteen replacements while absolute fidelity declines. Compact-record
specificity showed no resolved change between rewrites 3 and 16; this is not
an equivalence or indefinite-stability result. The formation gate is close to
its cutoff, and positive average specificity does not imply every block passes.
This extends the tested horizon within the same machinery; task competence and
unrelated embodiments remain untested.

[Full report](runs/confirmation_v2/REPORT.md),
[summary and all contrasts](runs/confirmation_v2/summary.json),
[independent audit](runs/confirmation_v2/INDEPENDENT_AUDIT.json), and
[figure](figures/confirmation_v2/long_renewal.png).

- [Durable status](analysis/confirmation_v2_status.json),
  [workflow log](analysis/confirmation_v2.log),
  [launch receipt](analysis/confirmation_v2_launch.json) and
  [verified startup](analysis/confirmation_v2_startup.json).
- [Three fixture checks passed](analysis/fixtures_v1.log), including unchanged
  first-three trajectories and no checkpoint/observer feedback.
- [Disposable benchmark audit passed](runs/benchmark_v1/INDEPENDENT_AUDIT.json):
  every byte boundary, all 3200 score rows and all eight checkpoint reads checked.
- [Conservative forecast](analysis/forecast_v1.json): 1676 seconds (about 28
  minutes), including simulation, audit and reporting. Estimated raw data 3.29 GB.

The first sandboxed detach attempt (`confirmation_v1`) ended before creating a
scientific run or generating a block. Its [failure record](analysis/confirmation_v1_status.json)
and launch/log files are retained. Approved execution outside the sandbox allowed
the identical frozen workflow to survive the command's exit. No scientific
settings, code, cohort or scoring rules changed between attempts. A single
startup check verified the live workflow; no automatic progress polling followed.

The independent audit checked 128 lineage files, replayed all 512 checkpoint
readers exactly, and reproduced 204800 individual score rows and all decisions.
Completion/input hashes and figure provenance were rechecked at closeout, and the
final figure was visually inspected. Raw arrays, all controls, individual scores,
reports, PNG/SVG figures and the failed first launch remain retained. No tuning,
cohort extension or pooling with earlier cohorts occurred.

Executable components: [runner](run.py), [independent audit](audit.py),
[fixtures](tests.py), [fixed figures](plot.py), [workflow](workflow.py).
Everything above the experiment tree remains read-only to this agent;
manuscript work belongs to the other agent.

## Reviewer analysis — 10 October 2026

The [manuscript handoff](analysis/reviewer_specificity_v1/HANDOFF.md) supplies
figures, captions and a direct sign/amplitude decomposition of this experiment.
The [analysis package](analysis/reviewer_specificity_v1/README.md) includes
compact data and scripts suitable for another git checkout.

At sixteen rewrites, compact own-record, matched foreign-record and protected-copy
agreement is **64.383%, 62.996% and 68.266%**, respectively. The incremental
own-history effect is **1.387 percentage points**, distinct from total agreement.
The new figure shows all three curves on the native score scale at every saved
fresh checkpoint; the sixteen lineage reads are displayed separately.

From three to sixteen rewrites, compact sign agreement declines **3.005 points**
while amplitude qualification rises **0.892 points**. Qualified agreement falls
**2.529 points**. This post hoc analysis directly uses E014's retained fields:
declining agreement cannot be explained simply by fewer sites exceeding the
amplitude threshold. The decomposition describes the observer, not separate
causal mechanisms or translation-tolerant shape.

All 128 requested raw lineage files are in `runs/confirmation_v2/` on this host;
the repository's `**/*.npz` rule excludes them from git. Their original hashes
match. The portable count extracts reproduce all 204,800 individual published
scores and all 480 checked historical summaries exactly. An independent recount
and reaggregation verifies all 3,180 new summaries. The separate E001 homogeneous
pilot is also illustrated: its larger history effect coexists with failed
formation. Original experimental gates and results remain unchanged.
