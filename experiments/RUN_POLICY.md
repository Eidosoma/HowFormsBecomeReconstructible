# Execution policy

User instruction, 17 September 2026: runs expected to take **over 10 minutes**
must run detached. The user will request status checks; do not spend turns or
tokens polling those runs automatically.

- Benchmark disposable inputs before a large run when runtime is uncertain.
- For a forecast over 600 seconds, use a detached process/session, stdin from
  `/dev/null`, a unique local log, PID, frozen configuration, and durable
  RUNNING/COMPLETE/FAILED status. Report the launch and await the user's poll.
- Do not repeatedly reconnect to or poll that detached job. Work that is
  independent of its results may continue within the shared CPU budget.
- At most 12 logical CPUs total; numerical libraries use one thread per process.
- All writes, caches, logs, outputs, and temporary experiment data stay inside
  this experiment tree. Other source trees are read-only.
- Never overwrite a run or silently change a frozen protocol. Preserve failures.
- Keep procedure proportionate: brief protocols, executable checks, retained raw
  evidence, and one discovery log. Routine authorized work needs no additional
  approval stage. Record actual decisions and failures, not ceremonial reviews.

This policy applies prospectively. The initial E001 and E002 pilots had already
completed in approximately 32 seconds and 6 seconds when this instruction
arrived. Their original input snapshots remain unchanged.
