# TT043 execution

Full excluded qualification completed at 2026-10-27T13:55:28.549692+00:00 in
1140.260 seconds. Its forecast was 1575 seconds and deadline
3150 seconds. All 656 physical batches passed independent replay and exact
serial/parallel comparison of the fixed preflight context.

Production froze at 2026-10-27T13:55:33.015607+00:00 and started at
2026-10-27T13:55:34.466267+00:00. It completed at 2026-10-27T14:55:18.228806+00:00 in
3583.763 seconds (59 minutes 44 seconds). The measured forecast
was 7111 seconds and fixed deadline
14222 seconds. Two normal-priority workers used CPUs 6/7
with one numerical thread each. The complete detached sequence took
4731.912 seconds, about 79 minutes.

Production retained 1,935,626,071 output bytes. Total study size
at closeout was 2,442,909,858 bytes, below the 6 GiB cap;
free space exceeded the 4 GiB reserve. There were no phase failures, retries,
extensions or scientific changes after qualification. The 1-MiB per physical
batch and phase-level storage allowances remained conservative.

One startup persistence check was performed. Further checks were only at the
user's explicit status requests. The final status turn first inspected new
production results after completion. Independent closeout passed in
42.192 seconds. The host check confirmed the controller, two
qualification workers and four production workers from successive block pairs
have exited. No automatic polling or successor is active.

Frozen protocol, source data, qualification and production artifacts are
unchanged. Earlier handoff versions are retained in
completion_handoff_inputs/MANIFEST.json. The revised interpretation is in
README.md; numerical review scope and bindings are in CLOSEOUT.json.
