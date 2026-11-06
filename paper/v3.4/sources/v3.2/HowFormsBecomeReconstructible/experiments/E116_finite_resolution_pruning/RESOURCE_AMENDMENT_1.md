# E116 resource amendment 1 — before finite scientific outcomes

30 October 2026. The completed excluded benchmark passed all numerical checks
and output verification in 329.54 seconds. Its scientific design and numerical
implementation remain unchanged. This amendment changes resource accounting
and the planning allowance only; it does not add sources, readers, horizons,
conditions, retries or extensions.

The original storage formula multiplies every retained array by the sixteenfold
increase in read length. Most arrays have fixed shapes: packet weights, masks,
denominators, couplings, final states and the final 32 observations. Only the
per-step state-hash traces grow with read length. The former formula reserves
128,892,967,072 bytes, exceeding current free space despite an anticipated
fixed-shape scientific payload of only about 5.3 GB before padding.

The corrected upper bound separates uncompressed NPY members by role. Ordinary
arrays scale sixteenfold from two to 32 sources. `state_hashes.npy` members in
the replay archives scale both with source count and with read length. Other
files retain the existing conservative 32-fold allowance. A factor 1.5 and
one GiB reserve remain. Packet and recipient widths, observation counts and
the maximum number of panels are identical in timing and scientific execution;
archived reference reuse can only reduce the scientific number of new chunks.
No outcome-dependent reduction enters this bound.

The unchanged runtime method forecasts about 5.15 hours on four workers, with
about 15.20 hours using its existing threefold timing margin. The draft's
12-hour conservative qualification ceiling therefore does not cover that
margin. The effective planning ceiling is raised to **18 hours (64,800 s)**
before finite scientific outcomes. The full fixed-cohort comparison is already
authorised, and the user explicitly requested running as long as good science
requires. Both independent replay and the common-reader controls answer
material numerical/mechanism questions and are retained. No additional work is
being added to fill this allowance; it is not a minimum runtime or a sample
extension. There is no automatic retry or successor.

The former 12-hour value remains in the immutable benchmark implementation and
settings as historical provenance. The new effective allowance is stated in
the qualification, forecast and scientific freeze through this amendment.
`admin/qualify_resource_v1.py` performs the amended qualification without
modifying any benchmark-frozen code, protocol or result file. The ordinary
scientific runner continues to verify those same frozen numerical inputs and
the amendment's pinned evidence before execution.
