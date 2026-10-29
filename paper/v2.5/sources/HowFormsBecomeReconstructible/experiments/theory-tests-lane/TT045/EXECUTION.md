# TT045 execution

Excluded qualification completed in 974.213 seconds
(16 minutes 14 seconds); all 656 physical batches and its serial/parallel
comparison passed. The original controller then stopped before production
because its measured forecast, 48,248 seconds, exceeded the original 12-hour
forecast ceiling. TT045/QUEUE_FAILED.json preserves that historical stop.

The authorized runtime_v2 amendment raised the forecast ceiling to 14 hours,
without changing the scientific code, 16-future design, source records, seeds,
18 GiB study cap or 4 GiB free-space reserve. No requalification or hidden
scientific retry occurred. Before production, the authorized archive moved
completed TT043/TT044 runs to /mnt/datasets, verifying all
20,154 files (4,840,262,813
bytes) and preserving original paths through symlinks. Its receipts remain in
storage_archives/2026-10-28_completed-runs_v1.

Production froze at 2026-10-28T16:45:54.111638+00:00, started at 2026-10-28T16:45:55.284046+00:00,
and completed at 2026-10-28T21:34:04.558381+00:00. Actual production time was
17289.274 seconds (4 hours 48 minutes 9 seconds), below the
48,248-second conservative forecast and 96496-second
deadline. Two workers used CPUs 6/7 with one numerical thread each and normal
priority. The amended archive/production sequence took
17375.553 seconds in total.

Production retained 12,337,857,530 bytes. At review the study
held 12,784,773,624 bytes and local free space was
13,397,168,128 bytes, within the cap and reserve. The separate
saved-data review passed in 310.777 seconds on one CPU with a
600-second deadline. It generated no new dynamics.

One startup persistence check followed each authorized launch; subsequent
production status checks were user requested. Production results were first
inspected after completion on this status turn. The controller and all old and
current workers have exited. There is no automatic polling, retry, extension
or successor. Previous handoff versions are preserved in
completion_handoff_inputs/MANIFEST.json. Frozen scientific inputs and earlier
failure/amendment evidence remain unchanged.
