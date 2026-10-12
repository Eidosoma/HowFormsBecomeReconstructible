# Anytime change: qualification correction before main execution

**10 October 2026. No main cohort has run.**

Attempt-01 stopped at the posterior-category normalization assertion during
synthetic qualification, at 13:20:52 UTC. Its frozen design, source, scalar
reference, population, seeds and failure record remain untouched under
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/attempt-01/`.

The original main source SHA-256 is
`40cd76279c73f5a55f6b3debcf17c5eecfb03329f5a77c9e1c54ef2566268451`.
All 42 rational inference/planning cases, latent-path evidence checks, prior
checks and the same-support CT3-flat bridge passed before this assertion.

A separate one-CPU synthetic diagnostic repeated only the new learner on
qualification blocks 0 and 1 and inspected its state at the same assertion;
it did not bypass the failure or generate main results. Its record is
`/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1/diagnostic-01/NORMALIZATION.json`.
The maximum deviation when summing posterior categories was
**1.176836406102666e-14**, above the inherited-style **4e-15** tolerance.
The final underlying 301-component posterior summed to one within
**4.440892098500626e-16**; values were finite and positive. Grouping many
components accumulates floating-point rounding beyond the smaller model's
tolerance.

Change only this diagnostic assertion's absolute tolerance to
`2 * number_of_components * machine_epsilon`: **1.3367085216486885e-13**
for 301 double-precision components. This conservatively covers summing
normalized nonnegative components; relative tolerance stays zero. Belief
updates, actions, priors, scores, measurements, scientific criteria, design,
population and seed sets are unchanged. No output is renormalized or repaired.

Attempt-02 must freeze the corrected source, preserve this note and the
diagnostic, reexecute the complete qualification and benchmark, and verify
identical design/population/seeds before launching. The failed attempt is
part of the permanent record, not a scientific null result or discarded sample.
