# D195 qualification and freeze

27 October 2026. [Fixed design](RECIPIENT_PULSE_V1.md),
[current execution status](RECIPIENT_PULSE_STATUS.md).

**205 tests passed on the first qualification attempt**, with no failures,
errors or skips. The original 102 D193 kernel checks and 103 D195 checks
remain separate from scientific results. Synthetic qualification started
13:19:11.371949 UTC and completed **13:19:50.065143 UTC**; XML runtime
37.763 s, full driver **38.692357973 s**. The manifest binds 99 inputs;
7,228 retained artifacts include fixture and negative-test copies.

The D195 checker independently reconstructs the pulse, reference routing,
writing, all raw fields, outgoing bytes and RNG end states. It shares native
ladder physics and historical scalar helpers; this is not a clean-room test.
Full 1,000-step synthetic pulse replays cover both families, both roles and
LL/YL/writer-off pulse paths. Undisturbed paths and complete donor recordings
bridge exactly to the original D193 kernel. Earlier modules remain unchanged.

Complete miniature workflow checks cover all 32 paths, 37 named packets,
two futures, 32 comparisons, equal within-record role/future pooling,
writer/read-disabled and protected snapshot/trace controls. Donor sealing
must precede every recipient. Perturbed pre-step and post-step states are
retained, with only the declared V patch changing at intervention. Wrong
timing, patch, hidden channels, memory/writer alterations and RNG changes
are rejected. Rehashed source/trace/packet/reader/score/admission/summary
corruption is rejected; saved audits advance no dynamics.

Resource, source/cohort admission, write-once output, symlink, crash retention,
freeze drift, qualification binding and startup-only detached launch checks
pass. Main-cohort execution remains disabled. The complete benchmark and its
saved audit have **not** been certified by these synthetic tests.

Freeze completed **13:21:16.538235 UTC**, binding **16,283 inputs / 80
repository modules**. It includes qualified code and fixtures, inherited
kernel evidence, D191 source provenance, and the pinned D193 benchmark closure.
Scientific baselines must match the old undisturbed donor traces before the
new recipients begin, and twenty unchanged paths / fifty named reads at
completion. Original read addresses are reused; these bridges are apparatus
checks rather than additional independent scientific evidence.

External stage:
`/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-recipient-pulse-benchmark-v1`.
Qualification: `qualification/workflow_attempt1`. One CPU6/thread, nice10.
Pre-freeze retention **502,608,004 B**, including qualification. Analytical
benchmark bound **360,973,312 B**, including **4,718,592 B** extra event
arrays and 64 MiB metadata/container allowance, below its 512 MiB reservation.
The complete stage is capped at 2 GiB, with 64 MiB headroom and 4 GiB
free-volume reserve. No compression savings are needed for admission.

The full-block allowance remains **1,200 s (20 minutes)**, not an observed
runtime. Launch detached, acknowledge startup, then leave completion readback
and a separate saved-only audit to the user's next status. No automatic
polling, retry, main launch or successor. No scientific inference from tests.

Exact identities:

| Artifact | SHA-256 |
| --- | --- |
| Qualification MANIFEST.json | `de8abf89e94768ee98bab8c28ae92809c4506c75dd0f14b1e3c3372ba490fa42` |
| Qualification COMPLETE.json | `9dc782dda5fd5917d5251b673c49d750a00035b7c9b798b0121c155d62954574` |
| tests.xml | `ea0736103edec575da4defa6380286b075975eddcf1b80659a5924e5dcf7bd23` |
| tests.log | `e54e720f3463abfe9446242620f635868378e18eda105e68cec597972e554d0b` |
| Execution FREEZE.json | `ded7aadbdb12128fa61d5eeda2f36fccbf1c32f20de77214e1e562811088ade1` |
