# Resume of the interrupted fixed-injury probe

The original supervising execution session returned exit code 143 (SIGTERM).
No Python failure receipt was written. A host process check found no surviving
experiment launcher or worker. The exact sender/cause of the signal is unknown.
Block 34000 completed and its committed arrays, output windows and negative
control passed checkpoint validation; the other seven blocks are incomplete.

Preserve the original `runs/pilot_v1` directory and its added interruption
receipt. Copy the verified first block into `runs/pilot_v1_resume1`, retaining
its original receipt. Resume only missing blocks with the exact same scientific
configuration, source packets, masks, replicate identifiers and kernels.
No scientific outcomes were inspected to change the design. A partially
computed block is regenerated from its fixed stream; no result is overwritten.

The worker now runs as a detached host process, outside the transient execution
sandbox. Its files and caches remain in the authorized theory lane. A startup
pipe acknowledges successful input checking once; there is no polling loop.
A nonblocking file lock prevents duplicate recovery workers, and signal handlers
record SIGTERM/SIGINT when possible. This changes process supervision only.

The original automatic analysis, separate reader/table verification, report and
figure code remain unchanged. The new completion record identifies the reused
block and distinguishes new compute from the retained checkpoint. No automatic
successor is launched. User-requested status checks remain the only polling.
