# Observer Atlas V1 report

**Run status:** `completed`  
**Minimum completion gate:** `PASS`  
**Complete combined-reset profiles:** 21 memories across 13 BioModels

## Observer ladder

- `o_r`: 58.3% (14/24); 10 supporting BioModels.
- `o_trajectory`: 29.2% (7/24); 7 supporting BioModels.
- `o_state`: 8.3% (2/24); 2 supporting BioModels.
- `o_counterfactual`: 8.3% (2/24); 2 supporting BioModels.
- `o_relearning`: 8.3% (2/24); 2 supporting BioModels.
- `o_information`: 8.3% (2/24); 2 supporting BioModels.

## Mechanism labels

- `extinction-with-savings`: 1
- `invalid-or-dysfunctional`: 3
- `no-durable-reset`: 2
- `persistent-operational-reset-indeterminate`: 4
- `rehoming`: 8
- `temporary-suppression`: 6

## Ranked hypotheses

1. **generic-perturbation** — 12 memories / 9 BioModels. Next prediction: Control-only and combined histories remain counterfactually interchangeable.
2. **rehoming** — 9 memories / 8 BioModels. Next prediction: Response-level resets occupy a stable state distinguishable from both naive and trained references.
3. **temporary-suppression** — 6 memories / 5 BioModels. Next prediction: The learned response relapses with time or UCS reinstatement.
4. **damage-or-instability** — 3 memories / 3 BioModels. Next prediction: Apparent reset co-occurs with numerical failure or collapsed probe responsiveness.
5. **extinction-with-savings** — 1 memories / 1 BioModels. Next prediction: Reset states reacquire the learned response faster than paired naive states.
6. **functional-reversion** — 0 memories / 0 BioModels. Next prediction: Richer observers remain naive-like and relearning shows no savings.

## Claim boundary

Exploratory in-silico mechanism hypotheses only; no confirmed erasure, plastic-heredity, biological-safety, agency, or clinical claim.
Rates, decoder permutations, and clusters are descriptive tools for choosing the next experiment, not confirmatory evidence.
