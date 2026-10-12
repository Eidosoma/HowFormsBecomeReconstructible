# TT012 execution and completion

The full audit completed at 2026-10-10T19:51:57.185767+00:00 in 2567.521
seconds (42 minutes 48 seconds), below the conservative 76.2-minute forecast.
The user's status request triggered this closeout; the long job was not
polled automatically after its single startup check. No successor was launched.

- Job: `jobs/audit_v1`; output: `runs/audit_v1`.
- Job SHA-256: `370fd81d0154d7448029d95d128addcc59f0d83179db5dcb0aa8ee01c18d8497`.
- Completion SHA-256: `8dc434566d1d142b03c75d572f3cdb346383c5fbb505221821764bb7cc7198eb`.
- All 138 frozen inputs and 28 committed outputs verified at closeout.
- All 192 optimizations and 128 hybrid equivalence comparisons pass.
- All 64 known originals and 9,792 experimental contexts reproduce byte for byte;
  152 native array comparisons pass.
- All 9,792 saved endpoints and 19,584 strict task flags, three tables and
  whole-block bootstrap summaries reproduce independently.
- No TT012 failure or retry; both historical source validation failures retained.

The primary alignment forecast passes: +4.938 pp [+0.853, +9.487].
Recipient-based sign completion scores 26.737%, compared with
14.366% for aligned donors and 26.939% for own backups.
Completion still receives protected support and magnitudes. This is exposed
selected development evidence, not an autonomous-inheritance or unique RDT result.

The [checked interpretation](INTERPRETATION.md), [full report](runs/audit_v1/REPORT.md),
[closeout](CLOSEOUT.json) and [protocol](PROTOCOL.md) give the scope and evidence.
Launch-era execution and qualification remain in [closeout_inputs](closeout_inputs/MANIFEST.json).
Frozen job/source evidence has not been modified. The source aggregate result
was first inspected at this user-requested completion review; the earlier
benchmark's raw-data exposure is documented in the launch-era record.
