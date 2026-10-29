# OR001 registration: where do setpoints come from? Origin by selection

**Frozen 25 October 2026 at 12:24:05Z, before any selection outcome. Development screen, not confirmation.** The design is `or001/design.py`, digest `5c7ea5633c086b9698e354b7aa3ee251807377344c3f0fb250c182f479354874`; the source hashes, the registered statements and the qualification receipt are in `or001/frozen/`. Selection runs only on engineering identities. The evolved genomes are read once on fresh development blocks beside fixed reference genomes.

## The question

ME001 and ME002 ask when a supplied setpoint and supplied correction rules help. OR001 asks where they come from. A lineage's controller constants are made heritable, and the lineages are selected for keeping a form across generations. Which architectures evolve, starting from almost no setpoint, in which environments? THEORY.md §7 frames the expectation as an optimal investment: a stored setpoint pays where native physics forgets faster than a lifetime, concentrated on the scales the body cannot restore by itself; record writing pays only where the record is the less reliable copy.

## Genome

Six real genes, decoded by logistic maps to bounded values:

| Gene | Range | Meaning |
|---|---|---|
| g_site, g_region, g_sheet | 0–1 | maintenance body gains on R − V-tilde at site, region (4 × 4) and sheet (quadrant) resolution, summed, then mean removal and clipping as in the engine |
| m_dev | 0–5 | multiplier on those gains for a newborn's first 300 updates: a developmental programme |
| rho_w | 0–0.02 | rate at which the record is written from the body (native reciprocal: 0.002) |
| w | 0–1 | packet passed on = w·R + (1 − w)·Q: the record itself versus the body's passive capture |

The controller reads only V-tilde and R. A genome with only g_site = 0.2 (the native gain) is ME001's hold route bit for bit (`tests/test_or001.py`). Selection starts from X0: every gain 0.02, m_dev = 1, rho_w = 0.0002, w = 0.5, so there is almost no setpoint to speak of.

## Environments

48 environments: family {F0, BL} (ME002's aligned half-planes and multi-scale blobs) × noise σ {0.05, 0.15, 0.3} × injuries {none, body, record, mixed} × dose cost λ {0, 0.05}.

- **Injuries:** one per life, at an onset drawn from 700–1,100 of a 1,500-update life, RMS 2, band drawn uniformly. Mixed means body 0.4, record 0.4, both 0.2.
- **Dose cost:** λ × (body correction L1 per life) / 10⁴. At λ = 0.05 the native gain costs about 0.03 per life at σ = 0.3.

## Selection

- **Algorithm:** antithetic evolution strategies, two independent seeds per environment, 40 generations, population 16, perturbation 0.5 in logit units, step 0.2 decaying linearly to 0.05, centred-rank utilities.
- **Fitness:** a lineage of a founder and 3 newborn generations. Fitness is the mean body qualified agreement with the founder's taught target at the end of lives 1–3, minus the dose cost.
- **Identities:** every selection generation k draws new founders, theta, noise and injuries through its own tag (`mse-or001-s{seed}-sel{k}`) on engineering blocks 900970–900971. All genomes of a generation share them (common random numbers).
- **Founders:** acquired as in ME002: message-neutral birth, 120 settling updates, 1,000 imposed teaching updates, 200-update release.
- **Evolved genome:** the mean of the search point over the last 10 generations.

## Reading

Six genomes per environment run 6-generation chains from the same founders on 16 fresh development blocks (910200–910215) × 4 messages × 2 parents, under tag `mse-or001`:
- the two evolved genomes;
- `none`, all gains zero;
- `native_hold`, g_site = 0.2 with the Q packet;
- `native_copy`, the same with the R packet;
- `native_reciprocal`, g_site = 0.2 and rho_w = 0.002, with the Q packet.

The endpoint is development retention: body qualified agreement averaged over generations 1–6, paired by case, summarised over 16 block means with a 95% t interval and read with ME002's rules (margin 0.02).

## Registered statements

| Id | Claim | Genes or endpoint | Rule |
|---|---|---|---|
| OS1a | A maintained setpoint is bought where physics forgets: the evolved maintenance gain is larger at sigma = 0.3 than at sigma = 0.05 | g_site + g_region + g_sheet, mean of the two seeds; 2 families x 4 injury regimes at dose cost 0.05 | HOLDS if total gain(sigma 0.3) > total gain(sigma 0.05) in >= 7 of 8 cells, else FAILS |
| OS1b | Where physics holds a formed pattern, selection buys a developmental programme instead: newborns read their record hard early | m_dev, mean of the two seeds; sigma 0.05 at dose cost 0.05, 2 families x 4 injury regimes | HOLDS if m_dev > 1 in >= 6 of 8 cells, else FAILS |
| OS2 | Copying the record evolves where the record is safe: the packet is mostly the record, not the captured body | w (packet = w R + (1 - w) Q), mean of the two seeds; sigma 0.15 and 0.3 x injuries none and body x 2 families x 2 costs = 16 | HOLDS if w > 0.5 in >= 14 of 16 cells, else FAILS |
| OS3 | Writing the record from the body is selected against unless the record itself is injured | rho_w, mean of the two seeds | HOLDS if rho_w < 0.002 (the native rate) in >= 75% of the cells without record injuries (none, body; 24 cells) and rho_w(record) > rho_w(none) in >= 75% of the 12 (family, sigma, cost) pairs, else FAILS |
| OS4 | Fine features need fine gains: for the multi-scale family the evolved site gain exceeds both coarse gains | g_site vs g_region and g_sheet, mean of the two seeds; BL at sigma 0.15 and 0.3 x 4 injury regimes x 2 costs = 16 | HOLDS if g_site > max(g_region, g_sheet) in >= 75% of cells, else FAILS |
| OS5 | Selection finds at least the native architecture: evolved genomes keep forms on fresh blocks as well as the native hold route | development retention: body qualified agreement averaged over generations 1-6, paired by case, block means | HOLDS if evolved - native_hold >= -0.02 (point estimate) for >= 90% of the 96 evolved genomes, else FAILS |

## Information boundary

Within a life the controller sees V-tilde and R only. Fitness uses the founder's target, but only across generations, through selection on public constants; no target, label or score enters a life. Selection never touches development identities.

## Qualification

Fixed in `or001/checks.py` before their results, on a debug selection (3 generations, every environment, debug tag) and a preflight reading on engineering blocks 900972–900973:
- **O1** unit checks;
- **O2** determinism of a repeated selection run;
- **O3** a complete and finite reading;
- **O4** a reader dry run that scores every statement, with every git file at 256 KB or less;
- **O5** a forecast of 12 h or less on 16 workers.

The selection and the development reading refuse to run unless the digest and sources equal the frozen ones; the reading also refuses selection outputs that are debug runs or come from another design.

## What ran before the freeze (disclosed)

- **Unit checks** of the genome controller.
- **A 3-generation debug selection** in two environments (debug tag, 11:59Z), for plumbing and timing only: about 7.5 s per selection generation.
- **A debug pass of the whole pipeline** (12:13–12:24Z, ending before the freeze):
  - a 3-generation debug selection in all 48 environments (debug tag);
  - a preflight reading on 900972–900973;
  - the reader's dry run;
  - checks O1–O5, PASS after one fix: a numpy boolean in O5 could not be written to JSON.

  The genes and statement scores of that pass were not opened. Its receipt was deleted, so qualification runs again after the freeze.

No statement or rule was changed after any selection outcome.

## What each outcome would mean

- **OS1a.** If maintenance gain evolves where physics forgets and not where it holds, a setpoint is an investment against forgetting, not a default.
- **OS1b.** If a developmental multiplier evolves where physics holds, lineages buy a record mainly to build each new body, then let physics maintain it, so the first function of a setpoint is development.
- **OS2.** If the packet evolves toward the record, copying beats capture as a selected property, not only a comparison.
- **OS3.** If writing evolves only under record injury, consolidation from the body is a repair mechanism, not a default.
- **OS4.** If fine gains evolve for multi-scale forms, the multi-scale profile of correction follows the form's own scales.
- **OS5.** If any of these fail while OS5 holds, the theory is wrong, not the search. If OS5 fails, the search is too weak to read the others.
