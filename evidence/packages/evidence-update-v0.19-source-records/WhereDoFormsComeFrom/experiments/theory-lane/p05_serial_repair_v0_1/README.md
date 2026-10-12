# Repeated repair through generation 32

Follow all 256 exposed generation-14 records through four repair schedules and
18 further body-written renewals. The primary comparison is repeated repair minus
baseline uninterrupted success across generations 15 to 32.

The fixed rule and population are specified in PROTOCOL.md and config.json.
PREDICTION.json fixes interpretation before the scientific continuation is run.
EXPOSURE_AND_DECISIONS.json records the known evidence and implementation decisions.
Run evidence, analysis and internal verification are saved under runs/pilot_v1.
The worker writes REPORT.md only after verification passes.

Long runs are detached without automatic polling or an automatic successor.
