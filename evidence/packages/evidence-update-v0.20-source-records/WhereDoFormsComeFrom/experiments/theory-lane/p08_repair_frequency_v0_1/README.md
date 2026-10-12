# Repair frequency development study

The accepted next step after P08 is a paired audit of seven saved failure states and a fixed curve of one, three, six, nine and eighteen repair calls. The three sparse schedules are new branches; nine/eighteen-call controls are reused exactly. All 256 exposed records remain enrolled.

PROTOCOL.md defines the complete contract. config.json and PREDICTION.json bind the schedules and descriptive analysis; EXPOSURE_AND_DECISIONS.json preserves known results and the execution decision. SOURCE_REUSE.json and sources/ bind prior code and data.

The frozen job runs in runs/pilot_v1. It waits for one CPU slot, runs qualification tests, the paired causal audit and a known-control benchmark, then starts new frequency trajectories only if every technical gate passes. QUALIFIED.json records that transition. No warning model is retuned and no new population threshold is claimed from development results.

The user requests status checks. COMPLETE.json and REPORT.md summarize completion; FAILED.json preserves any failure. No automatic scientific polling or fresh-cohort successor is permitted.
