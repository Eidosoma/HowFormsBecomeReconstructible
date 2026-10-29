# TT044 execution

Qualification completed at 2026-10-27T16:13:14.495187+00:00 in
658.263 seconds, against forecast 824 seconds and deadline
1648 seconds. All 656 physical batches passed independent replay and the fixed
preflight context matched the parallel execution byte for byte.

Production froze at 2026-10-27T16:13:16.195646+00:00, started at 2026-10-27T16:13:17.327626+00:00,
and completed at 2026-10-27T17:23:49.710566+00:00 in 4232.383 seconds
(70 minutes 32 seconds). The measured forecast was 6045
seconds; the fixed deadline was 12090 seconds. The whole
detached sequence took 4894.906 seconds.
Two normal-priority workers used CPUs 6/7 with one numerical thread each.

Production retained 2,899,631,460 output bytes. Total study size
at closeout was 3,416,469,679 bytes, below the 8 GiB cap;
free space exceeded the 4 GiB reserve. No phase failed, and there were no
retries, extensions or scientific changes after qualification.

One startup persistence check was performed; later checks were user requested.
The 28 October status turn first inspected production results after completion.
Independent saved-data review passed in 55.026 seconds. The host
check confirmed the controller, two qualification workers and four production
workers have exited. No successor or automatic polling is active.

Frozen artifacts remain unchanged. Earlier handoff versions are retained in
completion_handoff_inputs/MANIFEST.json. README.md contains the interpretation;
CLOSEOUT.json records the independent review scope and evidence bindings.
