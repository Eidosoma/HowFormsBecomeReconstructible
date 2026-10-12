# Generalization v1: preserved first-attempt failure and schema correction

**23 September 2026, before a second execution.** The first attempt completed
all 135 fixed-law integrations in memory, then failed during the known-control
bridge with `KeyError: 'task_headroom'`. In the old task-regret record that
field belongs to the controller summary, whereas the new checker mistakenly
looked inside its `no_update` arm. This is a record-schema lookup error.
The first attempt produced no `RESULTS.json` or completed manifest; its new
performance values and gates were not printed, inspected or used for revision.

Preserve the original [specification](FEP_GENERALIZATION_V1.md),
[checker](check_fep_generalization.py) and entire external `attempt-01` record.
The original checker SHA-256 is
`0bb15729648438af336b897d355e0ef03aef47e72e505a17db391c475fde8123`.
The failed record is 3,187,431 bytes and its `FAILURE.json` SHA-256 is
`0bf5826ec51b2ceef2d01a4ef7d727c01a500a60c2bfd46b5df68bb3bc85b43e`.
Its qualification passed 283,193 checks; failure occurred after nine bridge
assertions, with 560,518 assertions counted overall. This was an execution
failure, not a scientific gate failure or a completed evaluation.

The separately frozen [revision-two checker](check_fep_generalization_r2.py)
reads the old controller-level `task_headroom` field. All integration,
physical cost and regret formulas, populations, weights, policies, prices,
priors, comparison criteria and tie rules remain unchanged. Qualification
now also integrates the ten already-known cases fully and runs the exact
bridge before execution, directly exercising the failed record-reading path.
These qualification controls reveal no new-panel outcomes.

Record this correction, both source revisions, and every first-attempt
artifact in second-attempt provenance. Qualify and benchmark again, then
apply the same ten-minute detachment rule. Recompute the full evaluation
once under `attempt-02`; do not represent it as a first-attempt success or
claim no rerun/source correction occurred. Preserve either outcome and
complete the authorized reporting within the existing limits.
