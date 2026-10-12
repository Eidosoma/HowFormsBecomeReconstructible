# E049 — persistence through three rebuilds after one rollback

User-authorized follow-up to E048, 8 October 2026. E048 found that one fixed half
rollback improved next-body recovery on existing first-failure cases and met all
three frozen requirements. Test whether that benefit remains by the third body
when ordinary full bridge rewriting resumes. Freeze before tests or receiving.

Use all 32 original E041 blocks 32000–32031, four founders and four descendants.
Derive first body failure under full bridge rewriting independently from E041
scores; audit derives scores from ports. Include first onsets at g1–g29, with
three observed later bodies: **281 eligible of 307 ever-failed lineages among
512**. Exclude 26 later first failures; 205 never fail. Cross-check E046 onset
and follow-up indicators. Do not select on any later outcome, E048 improvement,
edit count or injury. Retain zero-edit cases and empty blocks. This reduces the
E048 cohort from 301 for follow-up availability only; comparisons use the same
281 cases in every variant and body.

At the first failed body's outgoing packet only, construct the same E048 three
variants: original bytes unchanged, fixed half rollback, exact full rollback.
Target only currently physically available edges with incoming |weight| >0.5
and outgoing |weight| <=0.5. Half uses float64 `new + 0.5*(old-new)`; full copies
old exactly. g1 incoming is consistent acquisition; later incoming is the prior
original outgoing packet. Preserve all other values including injury erasures
and repairs of old-weak/zero edges. Half interpolates signed values; record
actual changed coordinates, sign changes, absolute-weight gain and L1 change.

Apply the intervention **once**, then simulate full boundaries for g+1, g+2,
g+3 under the original reader and full bridge rewriting. Each variant passes
its own computed outgoing packet to its next new body. Never reapply rollback
or reset altered packets to the original. Match original injuries, full-shape
birth/noise streams and two cues by block, founder, descendant and actual body
generation. Recompute normalized-reader denominators after each injury.
Scientific reading is 2,048 steps, with 1,024 settling steps (multiply the E041
saved base settling count by four exactly once).

Capture immediately after reading, **before** the inherited 128-step holding
phase. Use endpoint cue-contrast products wherever nonzero, ordinary two-cue
coactivity otherwise, with the E041 float64 operation order. Run the standard
holding dynamics on the available binary scaffold, gain 2, using full-shape
E022 write noise streams. Holding does not revise the already captured packet.
Full bridge rewriting replaces all physically available weights with fresh
capture; explicitly set erased outgoing weights to positive zero. Later bodies
start fresh from the matched birth noise, not from holding end states.

Every returned first-body reader array and all three variants' scores must
reproduce the E048 subset byte exactly. All three original body ports, margins,
scores and outgoing packet bytes must reproduce E041. Original recovery at
least once within three must reproduce E046: **243/281**. These are provenance
controls, not outcomes of the new intervention.

Primary outcome: both cues correct in **the third body only**, each signed
output margin strictly >0.25. Pool eligible-case numerators and denominators
across all 32 blocks. Draw 10,000 whole-block bootstrap samples using
('E049', 'bootstrap', 'rollback_persistence'), including empty blocks; report
two-sided pointwise percentile 95% intervals. Omit only zero-denominator draws
and report valid counts; absent estimates are null. E048 intervals remain as
originally recorded and are not replaced by this restricted cohort.

Joint third-body benefit requires all three lower confidence bounds:

1. Half minus original success >+0.05.
2. Half minus full rollback success >0.
3. Full-minus-half original-success losses >0, with **all 281 eligible cases**
   as denominator. A loss means original succeeds under both cues and the
   corresponding altered variant fails at the third body.

Status is THIRD_BODY_JOINT_BENEFIT_ESTABLISHED only if all three pass; otherwise
THIRD_BODY_JOINT_BENEFIT_NOT_ESTABLISHED. Technical runs have null decisions.
No dose, threshold, timepoint, cohort or criterion changes after seeing results.

Secondary reporting at each of the three offsets: both-cue success, individual
cue accuracy and margin, all three pairwise contrasts, paired rescues/losses
and retained successes/failures, success by rule, original-success losses and
their reduction. Also report all-three success (sustained), any-three success
(any recovery), and first-body success followed by failure in either later body
(relapse after first). All episode rates use the full eligible cohort, including
the relapse rate, which is not conditional on first-body success. Report all
three pairwise episode contrasts and the eight binary three-body histories.
Selection summaries retain the E048 nine edit fields and initially changed
edges surviving the next injury. Secondary intervals have no global
multiplicity guarantee and do not qualify a failed primary comparison.

Retain initial packets/addresses/masks/counts; all three variants' incoming,
effective, computed and outgoing packets at every boundary; denominator,
birth, read-end, late-port trace/mean, holding-end, injury masks and scores.
Commit every holding step's full two-cue voltage state by SHA256 per case and
variant. Full intermediate read voltages and noise are replayable, not retained.
Independent audit imports no production model/runner: use the frozen E048
independent reader and edit reconstruction, independently implement scalar
capture and incremental holding noise/dynamics, reconstruct every serial
packet, compare all saved arrays/commitments and source controls, and verify
all summaries, patterns, transitions and decisions. Prior inputs/data immutable.
Figures require audit PASS. Nineteen scientific input files are frozen.

Twelve checks use synthetic or excluded fixture inputs only: cohort boundaries;
E048 packet/first-body equivalence and timing; contrast/fallback/torus capture;
capture-before-holding; exact original serial replay including onset g29;
full holding noise streams; independent three-body replay; corruption
detection; full rewriting/positive-zero erasure; empty cohorts/pooled ratios;
episode/loss accounting; three strict primary thresholds. Excluded E041 fixture
900041 has R2, read24/settle12/write8. Mixed technical onset addresses are
(0,0,1), (1,1,2), (2,0,3), (3,1,5), (0,1,29); these are not a scientific cohort.
End-to-end fixture includes its eight actual first failures.

Benchmark excluded E041 900041 R1, read128/settle64/write128, with its four first
failures and corresponding E048 reference. Its R1 source has no E046 chronology;
derive onsets from source scores. Benchmark both simulation and independent
audit through all three boundaries. Forecast seconds =
3*(simulation-worker + audit-worker seconds)*16 read factor*4 maximum case-count
factor*ceil(32/workers)+120. Three boundaries are already included in benchmark
time: do not multiply by three again. Storage reserve =
ceil(1.5*benchmark run bytes*4*32)+128 MiB. Use up to eight workers, one numerical
thread each, within shared 12-CPU limit. Forecasts >600s run detached with stdin
/dev/null, unique log/PID, frozen inputs and durable status. One bounded startup
check, then await user polls; no automatic polling, restart or successor.
Preserve failures and version amended inputs before further trajectories.

This is a finite persistence test on selected existing cases. It does not
establish indefinite heredity, a deployable autonomous failure trigger, or
performance on fresh blocks. A passing result supports a fresh confirmation;
a fading result motivates diagnosing how normal rewriting removes the gain.
