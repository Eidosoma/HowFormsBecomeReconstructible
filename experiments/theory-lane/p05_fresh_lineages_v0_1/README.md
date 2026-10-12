# Frozen repair on new lineages

Generate 16 new blocks and retain all 256 generation-14 records. Apply the frozen
recipient-only repair, with unchanged, shuffled-sign and erased controls. This
tests generalization beyond the selected development failures.

PROTOCOL.md defines the balanced history population and primary full-cohort
comparison. config.json and PREDICTION.json are frozen before new lineages.
benchmark.py uses known block 34000 only. After tests, freeze.py binds the
complete input snapshot; launch.py starts one detached worker. The worker saves
teaching, lineage boundaries, records and assessment reads, then automatically
analyzes and independently verifies them. REPORT.md and COMPLETE.json indicate
completion; FAILED.json preserves any failure. No automatic polling or successor.
