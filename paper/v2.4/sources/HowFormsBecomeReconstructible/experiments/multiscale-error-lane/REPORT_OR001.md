# OR001: development result. Where do setpoints come from? Origin by selection

**Completed 25 October 2026, 13:51Z. Development screen, not confirmation.**

- **Design:** frozen before any selection outcome (commit e2b3d9d059, 12:24:05Z, digest `5c7ea563…`; REGISTRATION_OR001.md).
- **Qualification:** passed (a8b62f1383, 12:34Z).
- **Selection:** 96 runs, 48 environments × 2 seeds, 40 generations each, on engineering identities only. They took 8.9 CPU-hours on 8 cores, 12:35–13:41Z.
- **Reading:** on 16 fresh development blocks (910200–910215), 1.1 CPU-hours.

Every number comes from `results/or001/` (`genes.csv`, `contrasts.csv`, `summary.json`, `statements_scored.json`). Retention is body qualified agreement averaged over generations 1–6 of a lineage, paired by case, with 95% t intervals over 16 blocks.

## The arc

ME001 and ME002 asked when supplied setpoints and supplied rules help. OR001 gave a lineage heritable controller constants and let selection for keeping a form choose them, starting from almost no setpoint. In plain words:

1. **A setpoint evolves from almost nothing wherever there is a form to keep and the record is safe.** Selection builds site gains of 0.45–0.76, two to four times the native 0.2. These lineages keep forms better than the native hold route by +0.04 to +0.30 over six generations; at σ = 0.3 with no injuries, F0 goes from 0.651 to 0.918.
2. **Copying the record is selected; capture and record writing are not.** Where the record is safe, the packet becomes mostly the record itself (75–91%). Writing the record from the body evolves to nearly zero in all 48 environments.
3. **Where physics holds, selection builds a developmental programme.** At low noise the newborn reads its record harder while it forms (multiplier 1.2–3.9). Its first job is to build a body.
4. **When the record itself is unsafe, selection reorganises the whole architecture.** At low and middle noise, under record injuries:
   - the maintained setpoint is abandoned (gain about 0.02);
   - the developmental multiplier rises to 2.7–3.9;
   - the packet becomes the body's capture (w 0.14–0.25).

   The lineage reads its record only to build each body, then trusts physics, and passes on the body rather than the damaged record (+0.12 to +0.23 over native at σ = 0.05). No arm of ME001 or ME002 had this strategy.
5. **The scale profile follows the form and the damage.** Multi-scale BL evolves fine site gain. F0 under record injuries at native noise evolves coarse sheet gain, which is blind, and so immune, to the fine and regional damage hitting its record.
6. **A noise-only account of a setpoint's value is too narrow.** Strong maintenance gains also evolve at low noise when the body is injured, or when the form's curved walls are erased by curvature flow without any noise (BL). Physics forgets through injury and geometry as well as noise.

## Registered statements

| Id | Verdict | What was found |
|---|---|---|
| OS1a | FAILS | The maintained gain is larger at σ = 0.3 than at 0.05 in 5 of 8 cells (needed 7). The exceptions are body injuries (F0, BL) and BL without injuries, where strong gains evolve at every noise level |
| OS1b | HOLDS | The developmental multiplier exceeds 1 in all 8 low-noise cells (1.19–3.87), and is highest under record injuries |
| OS2 | HOLDS | The packet is mostly the record in all 16 cells where the record is safe (w 0.75–0.91) |
| OS3 | HOLDS | The write rate is below native in every cell without record injury; it is higher under record injury in 11 of 12 pairs, though tiny everywhere (at most 0.0004 against the native 0.002) |
| OS4 | HOLDS | For BL the site gain exceeds both coarse gains in all 16 cells |
| OS5 | HOLDS | All 96 evolved genomes keep forms at least as well as native hold (within −0.012) |

## Evolved architectures and their retention on fresh blocks

Each table gives the evolved genes (mean of 2 seeds) and the development retention of the evolved genome, the native hold route and the no-setpoint floor, with evolved − native hold for each seed (B benefit, H harm, = no meaningful difference, ? undecided).

#### F0, dose cost 0: evolved genes (mean of 2 seeds) and development retention

| σ | injuries | site | region | sheet | dev. multiplier | write rate | packet w (R share) | retention evolved | native hold | none | evolved − native hold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | none | 0.76 | 0.03 | 0.03 | 1.80 | 0.0001 | 0.73 | 0.995 | 0.944 | 0.501 | +0.052B / +0.052B |
| 0.05 | body | 0.66 | 0.09 | 0.04 | 1.57 | 0.0001 | 0.75 | 0.969 | 0.875 | 0.508 | +0.096B / +0.092B |
| 0.05 | record | 0.03 | 0.01 | 0.01 | 3.90 | 0.0004 | 0.15 | 0.790 | 0.562 | 0.501 | +0.222B / +0.234B |
| 0.05 | mixed | 0.08 | 0.02 | 0.03 | 2.79 | 0.0002 | 0.31 | 0.648 | 0.636 | 0.502 | +0.016B / +0.009? |
| 0.15 | none | 0.64 | 0.06 | 0.04 | 1.72 | 0.0001 | 0.83 | 0.988 | 0.900 | 0.485 | +0.092B / +0.085B |
| 0.15 | body | 0.63 | 0.12 | 0.03 | 1.38 | 0.0001 | 0.77 | 0.958 | 0.849 | 0.493 | +0.109B / +0.110B |
| 0.15 | record | 0.03 | 0.01 | 0.01 | 3.07 | 0.0002 | 0.20 | 0.611 | 0.535 | 0.485 | +0.079B / +0.072B |
| 0.15 | mixed | 0.12 | 0.01 | 0.10 | 1.85 | 0.0001 | 0.42 | 0.601 | 0.607 | 0.489 | -0.006= / -0.004= |
| 0.3 | none | 0.54 | 0.10 | 0.05 | 0.82 | 0.0000 | 0.86 | 0.918 | 0.651 | 0.436 | +0.264B / +0.269B |
| 0.3 | body | 0.60 | 0.13 | 0.06 | 1.69 | 0.0000 | 0.80 | 0.900 | 0.629 | 0.437 | +0.273B / +0.271B |
| 0.3 | record | 0.25 | 0.14 | 0.20 | 1.66 | 0.0000 | 0.71 | 0.485 | 0.464 | 0.436 | +0.020B / +0.021B |
| 0.3 | mixed | 0.40 | 0.23 | 0.09 | 1.31 | 0.0000 | 0.85 | 0.551 | 0.500 | 0.437 | +0.049B / +0.053B |

#### F0, dose cost 0.05: evolved genes (mean of 2 seeds) and development retention

| σ | injuries | site | region | sheet | dev. multiplier | write rate | packet w (R share) | retention evolved | native hold | none | evolved − native hold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | none | 0.50 | 0.03 | 0.03 | 1.93 | 0.0001 | 0.72 | 0.989 | 0.944 | 0.501 | +0.043B / +0.047B |
| 0.05 | body | 0.57 | 0.05 | 0.07 | 1.19 | 0.0001 | 0.85 | 0.968 | 0.875 | 0.508 | +0.091B / +0.095B |
| 0.05 | record | 0.02 | 0.01 | 0.01 | 3.87 | 0.0003 | 0.14 | 0.779 | 0.562 | 0.501 | +0.221B / +0.214B |
| 0.05 | mixed | 0.05 | 0.01 | 0.03 | 3.11 | 0.0002 | 0.33 | 0.661 | 0.636 | 0.502 | +0.029B / +0.022B |
| 0.15 | none | 0.49 | 0.04 | 0.03 | 1.37 | 0.0001 | 0.80 | 0.979 | 0.900 | 0.485 | +0.075B / +0.083B |
| 0.15 | body | 0.50 | 0.07 | 0.05 | 1.02 | 0.0000 | 0.87 | 0.955 | 0.849 | 0.493 | +0.104B / +0.109B |
| 0.15 | record | 0.02 | 0.01 | 0.01 | 3.26 | 0.0002 | 0.24 | 0.617 | 0.535 | 0.485 | +0.088B / +0.075B |
| 0.15 | mixed | 0.08 | 0.02 | 0.03 | 1.77 | 0.0001 | 0.36 | 0.604 | 0.607 | 0.489 | -0.003= / -0.002= |
| 0.3 | none | 0.59 | 0.09 | 0.05 | 0.83 | 0.0000 | 0.89 | 0.930 | 0.651 | 0.436 | +0.275B / +0.282B |
| 0.3 | body | 0.45 | 0.10 | 0.07 | 1.01 | 0.0000 | 0.91 | 0.887 | 0.629 | 0.437 | +0.265B / +0.252B |
| 0.3 | record | 0.02 | 0.02 | 0.22 | 0.56 | 0.0000 | 0.63 | 0.472 | 0.464 | 0.436 | +0.006B / +0.009B |
| 0.3 | mixed | 0.06 | 0.03 | 0.24 | 0.45 | 0.0000 | 0.86 | 0.538 | 0.500 | 0.437 | +0.036B / +0.038B |

#### BL, dose cost 0: evolved genes (mean of 2 seeds) and development retention

| σ | injuries | site | region | sheet | dev. multiplier | write rate | packet w (R share) | retention evolved | native hold | none | evolved − native hold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | none | 0.59 | 0.02 | 0.03 | 2.44 | 0.0001 | 0.71 | 0.953 | 0.863 | 0.498 | +0.094B / +0.086B |
| 0.05 | body | 0.72 | 0.05 | 0.02 | 1.37 | 0.0001 | 0.79 | 0.954 | 0.809 | 0.502 | +0.139B / +0.151B |
| 0.05 | record | 0.03 | 0.01 | 0.01 | 3.87 | 0.0003 | 0.16 | 0.683 | 0.559 | 0.498 | +0.121B / +0.127B |
| 0.05 | mixed | 0.17 | 0.01 | 0.02 | 2.92 | 0.0002 | 0.36 | 0.598 | 0.607 | 0.499 | -0.008H / -0.010H |
| 0.15 | none | 0.65 | 0.04 | 0.03 | 1.85 | 0.0001 | 0.79 | 0.950 | 0.813 | 0.490 | +0.129B / +0.145B |
| 0.15 | body | 0.76 | 0.04 | 0.03 | 1.28 | 0.0001 | 0.83 | 0.947 | 0.779 | 0.492 | +0.166B / +0.170B |
| 0.15 | record | 0.04 | 0.01 | 0.01 | 2.74 | 0.0002 | 0.25 | 0.555 | 0.533 | 0.490 | +0.020B / +0.024B |
| 0.15 | mixed | 0.26 | 0.03 | 0.02 | 2.06 | 0.0001 | 0.41 | 0.574 | 0.580 | 0.489 | -0.006H / -0.005H |
| 0.3 | none | 0.71 | 0.04 | 0.02 | 1.38 | 0.0001 | 0.75 | 0.887 | 0.599 | 0.435 | +0.279B / +0.298B |
| 0.3 | body | 0.62 | 0.07 | 0.02 | 0.91 | 0.0001 | 0.81 | 0.862 | 0.584 | 0.436 | +0.275B / +0.281B |
| 0.3 | record | 0.61 | 0.05 | 0.02 | 1.24 | 0.0001 | 0.73 | 0.497 | 0.469 | 0.435 | +0.028B / +0.028B |
| 0.3 | mixed | 0.66 | 0.05 | 0.03 | 0.84 | 0.0001 | 0.77 | 0.545 | 0.490 | 0.436 | +0.055B / +0.055B |

#### BL, dose cost 0.05: evolved genes (mean of 2 seeds) and development retention

| σ | injuries | site | region | sheet | dev. multiplier | write rate | packet w (R share) | retention evolved | native hold | none | evolved − native hold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | none | 0.72 | 0.03 | 0.02 | 1.77 | 0.0001 | 0.81 | 0.969 | 0.863 | 0.498 | +0.106B / +0.107B |
| 0.05 | body | 0.63 | 0.09 | 0.03 | 1.46 | 0.0001 | 0.74 | 0.944 | 0.809 | 0.502 | +0.134B / +0.138B |
| 0.05 | record | 0.03 | 0.01 | 0.01 | 3.86 | 0.0002 | 0.14 | 0.683 | 0.559 | 0.498 | +0.132B / +0.117B |
| 0.05 | mixed | 0.09 | 0.02 | 0.01 | 2.70 | 0.0002 | 0.32 | 0.601 | 0.607 | 0.499 | -0.006= / -0.006= |
| 0.15 | none | 0.65 | 0.05 | 0.02 | 1.36 | 0.0001 | 0.82 | 0.955 | 0.813 | 0.490 | +0.137B / +0.146B |
| 0.15 | body | 0.64 | 0.05 | 0.02 | 1.20 | 0.0000 | 0.87 | 0.944 | 0.779 | 0.492 | +0.166B / +0.165B |
| 0.15 | record | 0.03 | 0.01 | 0.01 | 3.32 | 0.0002 | 0.21 | 0.569 | 0.533 | 0.490 | +0.035B / +0.036B |
| 0.15 | mixed | 0.15 | 0.02 | 0.02 | 1.28 | 0.0001 | 0.26 | 0.574 | 0.580 | 0.489 | -0.006H / -0.007H |
| 0.3 | none | 0.66 | 0.03 | 0.03 | 0.80 | 0.0000 | 0.86 | 0.894 | 0.599 | 0.435 | +0.300B / +0.289B |
| 0.3 | body | 0.54 | 0.15 | 0.02 | 0.99 | 0.0000 | 0.83 | 0.855 | 0.584 | 0.436 | +0.251B / +0.291B |
| 0.3 | record | 0.06 | 0.03 | 0.02 | 0.45 | 0.0000 | 0.73 | 0.460 | 0.469 | 0.435 | -0.007H / -0.012H |
| 0.3 | mixed | 0.20 | 0.05 | 0.02 | 0.43 | 0.0000 | 0.73 | 0.513 | 0.490 | 0.436 | +0.024B / +0.022B |

## Caveats

- **The genome is small and supplied.** Six constants with fixed functional forms; no arbiter gate, no redundant record and no protected germline were available to selection. The evolved strategies are the best within this family, not the best possible.
- **Search quality.** Mean fitness rose from 0.548 to 0.780 and rose in 92 of 96 runs, and the two seeds agree on retention to a median 0.004. In seven cells the evolved genome ties native or is slightly worse (−0.002 to −0.012): mixed injuries at σ = 0.15 (both families), mixed injuries at σ = 0.05 (BL), each at both costs, and BL under record injury at σ = 0.3 with dose cost. Either nothing better exists there within this family, or the search did not find it.
- **Selection** uses lineage retention over 3 generations; the reading uses 6. Longer horizons might favour other trade-offs.
- **The evolved record-unsafe strategy relies on capture.** ME002 found capture lossy without injuries, so it is the better choice only when the record is worse.

## What this says about where setpoints come from

Selection rediscovers the lane's supplied rules in the environments where they pay, and rejects them where they do not:
- a strong, fine setpoint where forms are forgotten;
- copying the record, with no record writing from the body;
- coarse correction where the record's fine content is damaged.

It adds one strategy the lane had not tested. Where the record is unreliable and the body is stable, the record serves only as a developmental template, and the lineage transmits its body. A setpoint is therefore not a single invention but a portfolio, and the environment decides which parts are bought:
- the maintenance gain against forgetting;
- the developmental gain for building each body;
- the choice of packet for heredity;
- the scale profile against the damage spectrum.

## Next

- Give selection the remaining parts as genes, and see when each evolves: the provenance gate (latch and abort), a second voting record, a protected coarse germline, and phase-gated rewriting.
- Confirm the record-unsafe developmental strategy on fresh blocks with longer lineages.
- The GPU: a qualified port would allow much larger populations and genomes, once the allocation arrives.
