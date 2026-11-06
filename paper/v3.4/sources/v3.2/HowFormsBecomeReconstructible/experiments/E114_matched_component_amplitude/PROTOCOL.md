# E114 — matched-amplitude shared/cue component intervention

Fix this design before new matched-reader outcomes. E112 outcomes and E113
descriptions are known. All 32 E112 sources (1120000–1120031), 4,096 context/
injury identities, 554 eligible rows, 3,542 empty-witness rows, two injuries,
earlier endpoints and individual harms remain. Excluded IDs 9000980/9000981
qualify implementation and runtime. No source selection, longer-cycle addition,
writer rerun, dose sweep, new stream or sample extension.

## Intervention

Use the saved halfway O and N states from E112 ON/NO phase readers. For each
eligible identity/injury and record v=C,F compute m=(x⁺+x⁻)/2, d=(x⁺−x⁻)/2.
The norm A_c of Δc=c_N−c_O is mean absolute change across living cells outside
the cue clamp, including output ports, pooled equally across C/F. Choose
t=min(A_m,A_d); α_c=t/A_c for A_c>0 and zero otherwise. Use the **same α_c
for C and F**. Pair-averaged norms match; each record's norm individually need
not match across components. Zero targets remain, with exact zero component
contrasts; no tolerance-based case selection.

For each component set its two levels to

    c_low  = (c_O+c_N)/2 − α_c (c_N−c_O)/2
    c_high = (c_O+c_N)/2 + α_c (c_N−c_O)/2.

This centers each attenuated range at its original midpoint and treats O/N
symmetrically. α=1 uses the exact original component; full-scale OO/NN states
pass through unchanged. α=0 uses the identical midpoint at both levels.
Inject x⁺=m+d and x⁻=m−d for all four matched component combinations and each
original later stream O/N: eight conditions, retaining the m/d/later letters.
Verify actual matched norms and component isolation to machine precision, dead
cells and cue clamps exactly, and state bounds [-2,2] without initial clipping.
Every state lies in the convex hull of the validated four original component
combinations, up to floating arithmetic. Never amplify the smaller direction.

Continue only the original later interval (1024–2047 scientific;
256–511 excluded), preserving later noise ownership/absolute offsets, coupling,
normalization, update equation, observation window, and original strict 0.25
success rule. Paired cue noise and the same birth/reset apparatus remain.
Independently reconstruct normalization and each injected state; independently
replay every later step and compare hashes, final fields, windows and scores.
Empty-witness rows run no component readers; absolute crossed scores stay null,
known contrasts stay zero. Erased eligible witnesses remain exact C/F no-ops.

## One declared focal contrast

Let Δ_q(c,l)=q_C(c,l)−q_F(c,l) at matched component levels c and later stream l.
For each eligible row, G_m is the average of |Δ_q(N,d,l)−Δ_q(O,d,l)| over both
d levels and both later streams; define G_d analogously over m and later l.
The **sole primary** is the eligible pooled-mixture mean G_m−G_d for binary
both-cue success. A whole-source 95% interval with lower bound strictly above
zero supports greater shared-component sensitivity at this matched norm/dose.
An interval entirely below zero supports reversed ordering; overlap with zero
is unresolved, not equivalence. This is a new controlled intervention on known
sources, not a fresh-source confirmation. E112's original unresolved primary,
its source sums and original interval remain unchanged and separately reported.

Fix 10,000 E114-seeded whole-source bootstrap resamples, including all 32 blocks
and those with zero eligible cases. Use ratios of resampled sums/counts, not
means of nonempty source means. Retain native/mixture, sham/pulse/pooled, each
injury/pooled, and all/eligible/affected/erased scopes. Native, continuous scores,
other strata, signed effects and matched-minus-original excess are secondary
pointwise descriptions, not substitutes for the primary. Preserve all eight
absolute C/F outcomes, original immediate and after-rewrite endpoints, all
success patterns, gains/harms and individual transition ledgers. Retain total
absolute movement and cancellation as in E113 alongside the C−F contrast.

## Interpretation and resources

The test concerns the archived directions, pair-averaged L1 norm, midpoint and
smaller dose. Attenuation changes the rectangle's component levels as well as
its side lengths; the matched-minus-original comparison is not an isolated
unit-effect estimate. It does not establish global intrinsic importance or a
unique network mediator. Current noise pairing, precision and normalization
limitations remain. Do not divide old effects by norms and call that the new
intervention; new reader outcomes are required.

Run analytic/excluded tests and the complete excluded pipeline first. Pin all
inputs and copied endpoint files by completion hashes. Price all 32 sources and
554 eligible rows from the closed inventory, including all eight continuations
and independent replay (8,864 variant continuations), static checks and summaries.
Use at most four workers, one numerical thread each, within the shared twelve-CPU
ceiling; retain a 3× timing allowance. Detach above ten minutes under RUN_POLICY.md,
with one bounded startup check and user-driven status thereafter. Keep failed
attempts and frozen inputs immutable. No automatic restart, extension or successor.
