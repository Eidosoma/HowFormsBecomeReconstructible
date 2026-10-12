# E036 — preserved first technical attempt

The excluded validation failed two of eight checks because the independent
scalar auditor encoded negative zero where NumPy mean encoded positive zero.
All numerical values agreed. Exact original-policy agreement through all 16
boundaries passed. No scientific cohort, complete fixture or benchmark ran.

All first-attempt files, frozen snapshots and failure evidence are retained.
The production model is unchanged in the [corrected revision](../E036_serial_cue_capture_v2/README.md).

- [Failed validation](analysis/technical_v1.json)
- [Full test log](analysis/tests_v1.log)
- [Signed-zero diagnosis](analysis/signed_zero_diagnosis_v1.json)
