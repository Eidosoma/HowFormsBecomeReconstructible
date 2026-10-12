# Magnitude-restoration and single-pulse pilot

This package runs the two recommended follow-ups to the partial sign-restoration result. The [protocol](PROTOCOL.md) and [configuration](config.json) were saved before any new-arm native trajectory. It is an eight-block development pilot using the same matched-cue contexts, not confirmation of RDT-P01.

The magnitude-restored writer keeps original edge magnitudes and connectivity while taking tolerance signs on nonzero tolerance edges. When a tolerance weight is zero, it keeps the original sign. This completion is fixed and its use is counted. Together with the earlier original, tolerance and sign-restored policies, it completes a four-policy sign/magnitude comparison. The analysis reports the interaction `(pO-pM)-(pS-pT)` on the additive success-probability scale, without claiming unique causal mediation.

The single-pulse policy uses tolerance writing at generation 3 only, then original writing at generations 4–32. Its initial altered packet and its first successor body must match the known tolerance branch; its next write must use the original rule. Its terminal outcomes are compared with both repeated tolerance and original writing, with rescued and harmed pairs retained.

One batch simulates the original reference and the two new policies for all eight blocks, with 128 matched lineage contexts per policy. It uses the native body, damage, noise and terminal scoring contracts. The original branch must replay E051 at every boundary. The previous pilot's tolerance and sign-restored cases are reused under verified hashes and clearly labeled in the combined tables. These reused observations are not extra independent replicates. All prior packages are preserved.

The [benchmark](benchmark/COMPLETE.json) replayed known original, tolerance and sign-restored arrays byte for byte, with no new-arm dynamics. A renewal took 7.50 seconds and the full terminal assay 30.35 seconds. The conservative forecast is 3,093 seconds, approximately **52 minutes**, below the declared one-hour CPU forecast ceiling. The previous three-arm pilot actually completed in 33 minutes; that is supporting cost evidence, not a promise about this run.

[Twelve checks passed](tests_final.log), covering the zero-edge convention, preserved magnitudes and support, the exactly-once pulse schedule, native dynamics/scoring, identity-preserving control reuse, paired outcome tables, writer-action labels and the factorial calculation. A separate standard-library verifier recalculates the endpoint tables and interaction before completion is declared.

The detached worker runs with closed stdin, one numerical thread and its own log. A quiet supervisor waits for it in a persistent command session to prevent sandbox cleanup from ending it; this uses a blocking OS wait, not periodic status queries. **Do not poll automatically.** The worker writes its report and COMPLETE or FAILED marker itself. Review the run only when the user requests status or a completion notification arrives.

The run directory is `runs/pilot_v1`. `LAUNCH.json`, `PID` and `EXECUTION_SESSION.json` identify the launch. `STATUS.json` records the phase, and `FAILED.json` preserves an error. After verified completion, `COMPLETE.json` binds the outputs; `REPORT.md`, `analysis.json`, `terminal_lineages.csv`, `generation_block_summaries.csv` and `sign_completion_block_summaries.csv` contain the findings. New raw branch boundaries and terminal arrays are retained. The launch freezes 264 native input files, eight reused case files, prior completion provenance and this implementation's source snapshot.

The body diagnostic fractions compare O and T on each current body. They are not counts of actual tolerance-writing events in the pulse arm. The history table separately records the writer used at each generation; the zero-sign completion table reports where M would need the declared completion.

Verify a completed run from the theory-lane directory with:

```bash
python3 -B p01_writer_factorial_pulse_v0_1/verify.py \
  p01_writer_factorial_pulse_v0_1/runs/pilot_v1
```

The [prior pilot report](../p01_native_writer_continuation_v0_1/runs/pilot_v1/REPORT.md) remains the authority for the existing sign-restoration result. The earlier first- and third-generation terminal forecast failures are unchanged.
