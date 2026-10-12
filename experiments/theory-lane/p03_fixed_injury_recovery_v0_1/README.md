# Fixed-injury readout probe

This development run follows the P02 finding that its signed-transfer increment
was confined to currently failing cases. It tests all 64 such saved bodies by
freshly reading their incoming and O-rewritten packets under the original
generation-14 injury. An erased packet supplies the negative control.

Sixteen fresh random streams are shared across packet options; outputs are
measured at 1,536, 2,048 and 4,096 updates of one unchanged reader. The first four
streams form a direct-read probe baseline and the remaining twelve evaluate
five fixed record choices. No model fitting or long-lineage simulation occurs.

The known-control benchmark passed byte-exact replay and forecast 1,606.4
single-thread seconds (26.8 minutes), below the 3,600-second forecast ceiling.
That is an estimate, not a completion deadline. Nine tests check reader
agreement, coupling, trajectory prefixes, masking, strict scoring, amplification,
evaluation isolation, uncertainty calculations and the automatic table/report
interface on a labeled synthetic fixture. The independent reader also has a
full-length known native replay check before launch.

Run configuration and scientific boundaries are in [PROTOCOL.md](PROTOCOL.md),
[config.json](config.json), [prediction_manifest.json](prediction_manifest.json)
and [EXPOSURE_AND_DECISIONS.json](EXPOSURE_AND_DECISIONS.json). The prepared
packets, masks and enrollment list are retained under `prepared/` with their
source hashes. Benchmark outputs are under `benchmark/`.

`launch.py` freezes all inputs into `runs/pilot_v1/inputs`, starts one detached
single-thread process with `/dev/null` input, records its PID and log, and holds
the execution session with a single blocking OS wait. There is no polling loop.
The user's instruction is to leave long jobs unpolled until a requested status
check or completion notification.

The run automatically replays every known selected native read, performs the
fresh reads, writes raw endpoint bodies and output windows, summarizes results,
checks them with a separate reader and table implementation, and produces a
report plus PNG/SVG/PDF figures. `COMPLETE.json` appears only after those stages
pass; `FAILED.json` preserves an exception. `STATUS.json` is an atomic progress
record. A generated figure still needs visual inspection at a later user-requested
review; that does not require polling the running experiment.

This is an initial P03 probe of read time at fixed injury, with a P02 recovery
question. It is not a general damage/resource boundary test, an unexposed-context
confirmation, or a test of autonomous repair. No successor is launched.

All writers use exclusive creation. Repeated execution requires a new version
or explicitly separate run location; do not delete or overwrite historical
evidence to make a script run again.
