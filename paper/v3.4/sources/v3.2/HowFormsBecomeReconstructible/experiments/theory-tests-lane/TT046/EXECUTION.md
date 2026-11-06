# TT046 execution and closeout

The detached sequence began on 28 October 2026 at 22:44 UTC and finished on
29 October at 05:06:54 UTC, after 22973.516 seconds (6 hours
22 minutes 54 seconds). It used two normal-priority single-thread workers on
CPUs 6/7. One startup persistence check was followed only by user-requested
status review; no production outcomes were inspected before completion.

The completed TT045 raw run was archived to
/mnt/datasets/theory-tests-lane-archive/2026-10-28_completed-runs_v2.
All 64,966 files (12,353,527,672 bytes) were verified
before releasing the local copy. Original paths remain readable through a
symlink. Archive time was 809.510 seconds (13 minutes 30 seconds),
above its 508-second estimate but below its 1524-second deadline.

Full excluded qualification passed in 192.129 seconds
(3 minutes 12 seconds), with 156 receiving batches and exact serial/parallel
agreement. Production froze at 2026-10-28T23:00:45.433335+00:00, started at
2026-10-28T23:00:46.604072+00:00, and finished at 2026-10-29T05:06:52.782067+00:00.
Production took 21966.178 seconds (6 hours 6 minutes 6 seconds),
below its 29328-second forecast (8 hours 8 minutes
48 seconds) and 58656-second deadline. No scientific
phase failed, and no production retry, extension or protocol change occurred.

Production retained 12,581,198,316 bytes. The study held
12,750,429,970 bytes at review, below its 18 GiB cap, with
11,883,900,928 local bytes free, above the 4 GiB reserve.
All 35 recorded controller/worker process IDs had exited at the host check.
There is no successor or automatic polling.

Before launch, the administrative reservation traversal timed out; a later scan
required a numeric-boundary correction and review of five self-declarations.
Those attempts and the bounded scan scope are retained. Physical preflight_v1
passed; a cached/live checkpoint-key representation issue was then reproduced
and fixed before full qualification. Preflight_v2 passed with the added
regression check. Dynamics, seeds and cohort were unchanged.

The initial completion checker matched saved writer starting arrays but used
the reader's concatenated-byte hash format for a writer checksum. The writer
uses per-array dtype/shape/bytes hashes inside canonical JSON. The checker was
corrected, with a matching-format fixture and rejected one-ULP mutation. The
old checker and failure remain in admin/review.py and
COMPLETION_REVIEW_FAILED.json; COMPLETION_REVIEW_CORRECTION.json explains the
supersession. Corrected admin/review_v2.py passed the full saved-data review in
229.991 seconds, under its 600-second deadline. This generated no
new dynamics and changed no frozen input or production output.

The completed review independently verified all four primary tests and retained
the inconclusive Hoeffding sensitivity. Earlier handoff files are preserved in
completion_handoff_inputs/MANIFEST.json. FINDINGS.json and CLOSEOUT.json bind the
interpretation and verification scope. Prior study classifications are unchanged.
