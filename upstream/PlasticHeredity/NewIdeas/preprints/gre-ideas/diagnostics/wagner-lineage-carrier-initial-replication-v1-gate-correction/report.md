# Wagner lineage bounded-replication gate correction

> Post-run audit; the sealed source run was not modified.

## Corrected verdict: **PASS**

- Actual discovery-selected arm: `natural-full`
- That arm's archived verdict: **PASS**
- Generation-4 risk gain: 0.649169921875
- Generation-8 risk lower bound: 0.5755360921223959
- Split-half reliability: 1.0

## Gate setup error

The archived selected-targeted-k10 row required superiority over matched-random-k10, but at k=10=genes both retain every carrier entry and are the same arm.
The archived duplicate row failed only `beats_registered_controls`. After treating the structurally identical random-k10 comparison as not applicable, that duplicate row also passes every remaining criterion.

## Interpretation

The actual discovery-selected natural-full arm passed every registered criterion. The duplicate k=10 row was falsely marked failed solely by an impossible superiority comparison.
This correction does not upgrade the compute-bounded cohort into the original full confirmation.
