# P10 failure closeout: adaptive-clock overshoot

Stopped **2026-09-14 02:25:47 UTC**, after 17,858.6 seconds (about 4h58m).
Run: `runs/paper-contact-schedule-20260913T212804Z-22if1sgx`.
Job: `runs/jobs/paper-contact-schedule-20260913T212803Z-crxkdkyj`.
The run and its executed protocol/configuration/scripts/tests are preserved.

## What completed and why the panel stopped

All 60 initial cases produced outputs: two native historical replays, eight
common-graph calibrations and fifty screen cases, totaling 366 integration calls.
The original-P9 re-audit, historical replay gate and common-graph calibration
passed. All 25 screen coarse/fine comparisons agreed on their recorded categorical
outcomes. Nevertheless, the screen audit failed and no continuations were selected
or launched. No final successful panel audit exists.

Six first-isolation phases supplied only one sample: at 10,000,000 units coarse
or 5,000,000 fine, rather than a valid sequence over the intended 10,000-unit hold.
These were simultaneous-open for both M founder histories and sequential-cut for
the rewritten-restored-E history, each coarse/fine. The audit correctly rejected
their time axes.

A broader read-only check also found four more >10% endpoint overshoots not caught
by that original check: first isolation after 50% overlap in both coarse M founder
histories (26,208.4517 and 20,767.2678); first and second isolation after ordinary-M
coarse sequential cut (11,518.3535 and 11,353.9345). Therefore simply waiving the
six single-sample failures would not establish correctly timed comparisons.

## Cause and evidence

The original explicit adaptive Euler loop proposes its step from concentration
and voltage rates but does not limit that step to the requested end time or an
observation boundary. Near equilibrium, the native zero-slope convention can
produce a 10-million-unit coarse proposal (5 million fine). The loop advances
first, then records a sample and checks whether to continue.

A fresh read-only screen audit on September 14 exactly matched the saved failed
report: six failed checks out of 16,244 screen checks. All seven provenance and
integrity flags remained true. This is a numerical-validation failure, not evidence
that a PH mechanism is absent, and not a successful new PH demonstration.

## Interpretation and authorized recovery

Recorded labels provisionally favor sequential and several imperfect-contact
schedules over simultaneous contact, in both M founder histories. These are
diagnostic observations from a failed panel, not validated findings. The 50%
overlap candidate itself includes oversized holds, so selection must be repeated
under corrected timing.

The user authorized a separately versioned clock correction and renewed comparisons.
[P10R recovery protocol](PAPER_CONTACT_CLOCK_RECOVERY_PROTOCOL.md) caps adaptive
steps at exact phase/observation boundaries, records regular actual samples and
audits the complete step trace. Native equations remain unchanged; the integration
clock and sampling method are explicitly changed. It repeats the entire timing
screen with the new method, and only those new results can select continuations.
The old attempt remains failed; it is not overwritten, silently resumed or
reclassified as an independent successful replication.
