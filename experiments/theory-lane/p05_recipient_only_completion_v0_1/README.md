# Completion from the surviving record

Development follow-up to approximate sign alignment. Test a frozen repair rule
that infers signs and one replacement magnitude from the outgoing record alone,
fills its zero lattice edges, and preserves observed weights. Historical controls
remove donor support, saved magnitudes and saved support in stages.

See PROTOCOL.md for the information boundary, primary forecast, controls and
budget. PREDICTION.json binds the forecast; EXPOSURE_AND_DECISIONS.json records
known evidence and actual implementation decisions. The panel is already exposed.

prepare.py independently checks the 64 sign solutions and all record constructions.
benchmark.py uses only known native streams. After validation, freeze.py copies all
inputs and launch.py starts one detached worker. The run writes raw records and
reads, analysis.json, VERIFICATION.json, REPORT.md and COMPLETE.json, or FAILED.json.
No automatic polling or successor is enabled. Completed inputs are immutable.
