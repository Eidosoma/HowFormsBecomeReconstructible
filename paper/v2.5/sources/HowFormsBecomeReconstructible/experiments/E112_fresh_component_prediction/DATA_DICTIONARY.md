# E112 retained evidence

- `SOURCE_DATA.json`: fresh-ID manifest audit, predecessor receipts, hashes of
  excluded golden NPZ files. The benchmark IDs were used before; scientific IDs
  are disjoint from prior E-series manifest block IDs.
- `SAMPLE_FREEZE.json`: full scientific recipe, sole primary, fixed cohort,
  qualification and forecast hashes, before scientific source generation.
- `runs/*/manifest.json`, `inputs/`: immutable source snapshots and hashes.
- `acquisition_*`, `source_boundary_*`, `body_*`, `outgoing_*`,
  `source_continuation_*`, `ancestry_*`, `source_mixture_*`, `source_recovery_*`,
  `source_pruning_*`: unchanged E098 ancestry artifacts and full independent replay.
- `writer_*`, `terminal_packets_*`, `assay_*`, `scores_*`,
  `terminal_diagnostics_*`, `terminal_coupling_*`: unchanged E098 writer and
  immediate/after-rewrite endpoint artifacts, for the current cohort.
- `donor_{capture,regions,components,arrangement}_*`: exact E099–E102 static
  transformations. No intermediate comparison readers are run.
- `witnesses_*`: raw first safe cycle, actually used four-edge cycle, cycle
  length/stratum, independently checked movable-edge counts, and eligibility.
  `longer_witness=True` is a preserved structural exclusion, never a replacement.
- `interventions_*`: D/W/C/F packets, used witness, eligibility, original masks,
  physical support and common cycle magnitude; same layout as E105.
- `component_diagnostics_*`: effective signed/unsigned coupling and input
  budgets before and after both injury masks, same layout as E105 diagnostics.
- `phase_assay_*_{ON,NO}`: two complete histories supplying halfway states and
  OON/NNO outcomes. Includes noise/state hashes, masks, birth, coupling and ports.
- `component_assay_*_{OOO,ONO,ONN,NOO,NON,NNN}`: six late continuations;
  source/injected/end states, absolute steps, hashes, effective coupling, ports.
- `component_scores_*`: eight conditions in OOO,OON,ONO,ONN,NOO,NON,NNO,NNN order,
  each C/F × eligible-context index, with all score fields and mean ports.
- `cases.csv`, `component_cases_*`: all context/injury rows including ineligible;
  identifiers task/arm/founder/recipient/draw, eligibility/affected/erased,
  absolute scores (null if unmeasured), C−F contrast, all factorial effects and
  `gross_shared_minus_cue_delta_both` (the one primary key).
- `events.csv`: full rows with any C/F discordance among eight conditions;
  it is an event listing, never an analysis denominator.
- `original_cases.csv`, `original_events.csv`, `original_two_draw_means.csv`,
  `erased_controls.csv`: new-cohort E098 endpoints and all individual harms,
  with intact/pruned immediate, paired rewrite and independent rewrite results.
- `summary.json`: ratio estimates with whole-source block sums/counts, 10,000
  bootstrap resamples, eligible denominators, empty resamples, sole primary
  decision, all secondary scopes, individual identities and injury recurrence.
- `REPORT.md`, `endpoints.png/.pdf`: human-readable results and native-scale
  endpoint/sensitivity plots. Benchmark figures are prominently labeled excluded.
- `worker_*`, `component_worker_*`: per-source timings, genealogy checks,
  structural checks, independent state replay and scalar port checks.
- `STATUS.json`, `COMPLETE.json` or `FAILED.json`: durable status; completed
  runs inventory every output hash. Failed attempts are retained and never reused.

O/N are stream labels of the same distribution, not ordered quality levels.
For a condition, positive C−F is a loss after sign flipping; negative is a gain.
Positive gross m−d means shared-component swaps change the C−F contrast more.
Native and mixture histories, matched founders, recipients, arms and both injuries
remain dependent within a source block; sources are the bootstrap units.
