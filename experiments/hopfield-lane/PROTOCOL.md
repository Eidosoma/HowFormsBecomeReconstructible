# H001: Hopfield reconstruction feasibility

Status: exploratory development, specified before the first H001 run on
11 October 2026. This is a new model implementation and a mechanistic
translation of selected forms assays. It is not a numerical reproduction of
their original simulators or an independent confirmation of their claims.

## Questions and model choice

Can a symmetric associative network support (1) capture of an unprescribed
history, (2) renewal of a taught conditional response, and (3) repair using
surviving organization? Can continuous Hopfield state distinguish current
classification from readiness to transmit through member replacement?

Binary asynchronous dynamics provide an exact fixed-weight energy check and
a deliberately different update rule from the existing continuous spatial
networks. A small graded-response model preserves amplitudes for the cellular
question. Both belong to the Hopfield family. No model superiority is claimed
from these unequal tasks or budgets.

## Binary apparatus

64 binary neurons; eight fixed input sites, two eight-site output patches,
and 40 other sites. Dense symmetric target-free Gaussian base connectivity has
scale 0.12/sqrt(64), zero diagonal, and is shared by the four founders in each
independent block. Each site update uses the sign of its local field, keeping
the previous bit at zero. A sweep updates every site sequentially in a random
order. Reading uses 8 sweeps; formation/teaching uses 24.

The acquired record is J_ij = mean_t(x_ti x_tj)/64 with zero diagonal.
The writer has only the developed activity, and reconstructs all entries.
No incoming weights, target, prototype, desired label, or old activity are
arguments to the writer. Records are symmetric matrices: 2016 unique float64
entries (16128 payload bytes); the implementation stores both triangles in
32768 bytes. Neither allocation is an estimate of information content.

Capture founders form under the random base matrix, with the same eight input
sites held at +1 for every history. No history-specific image is supplied.
The resulting observed state is the offline reference. Fixed input sites are
excluded from agreement scores. They are a supplied orientation convention
which breaks global sign ambiguity, and remain present in every control.

Functional founders receive only input/output teaching clamps for two opposite
cues. Rule I requires (A,B)=(cue,-cue); rule II requires (-cue,cue). Hidden sites
develop under the shared random base. Two teaching states write one record.
Descendants receive only the input cue; output labels are confined to teaching
and offline scoring. The two read trials start independently; their coactivity
is averaged at writing. No cue-difference division or weight normalization is
used. Success requires both output means, under both cues, to exceed 0.5 in the
required direction. Capture reports signed agreement and >=0.9 completion.

## Replacement and controls

Default cohort: 12 independent blocks, four founders and four descendant
replicates per founder, 16 replacements. Development seeds start at 11000.
This is a small development cohort, not a powered confirmation. All founders
and replicates remain in every analysis. Founder stability/diversity are
reported rather than used to select favorable cases.

Every boundary discards activity. New random bits, edge erasures and update
orders are paired across arms. A new 50% undirected-edge erasure acts before
each read, without rescaling. Rewriting constructs the outgoing record solely
from the body that read that damaged record. Checkpoint readers at generations
0, 1, 4, 8 and 16 are independent fresh bodies and cannot update the lineage.

Arms: full renewal; foreign-founder renewal within the same base block;
coordinate-scrambled initial record; erased initial record; record reading
blocked at every renewal; writing blocked at every renewal; protected copying;
copying with cumulative damage; and a writer whose output addresses are
permuted at every boundary. All coordinate permutations fix the input sites
and preserve record spectrum, norm and value distribution. Foreign functional
records come from the opposite rule. Copy arms do not receive the rewrite.

The primary descriptive comparisons are own minus foreign at the final fresh
reader; renewal minus damaged copy; renewal minus protected copy; and renewal
minus each route/address control. Body performance and independent-reader
performance are recorded separately. No aggregate novelty/qualification gate
is retrofitted. Whole-block paired 95% bootstrap intervals (4000 resamples)
are exploratory, pointwise, and not adjusted for the several comparisons.

## Reciprocal repair translation

Use the same capture founders and matched records corrupted to correlation
0.3 at exactly the original Frobenius norm. Half the noninput body sites retain
founder activity; the remaining sites receive matched fresh bits. Scrambling
permutes only surviving values among surviving sites, exactly preserving their
histogram and the fill values. The input convention is preserved.

For 16 sweeps, a writer blends 0.8 of its current record with 0.2 of body
coactivity. The fixed reader always reads the initial damaged record. The live
reader reads the current rewritten record. Compare kept and scrambled bodies
for each reader, a live reader with record input disabled, and the original
damaged record without repair. Only the final record reaches a fresh assay.
Live minus fixed and kept minus scrambled are distinct questions. This repair
assay allows old-record retention; the serial-renewal assay above does not.

## Continuous cellular analogue

Three graded units obey du/dt = -u + W tanh(2u) + I. Each has self-coupling
1.2 or 1.6; every inter-unit coupling is 0.2, 0.4, 0.6 or 0.8. This is an
eight-point deterministic parameter screen, not eight independent replicates.
It has no ionic species, RNA, cell geometry or calibrated biological time.

Compare three positive states at amplitude 0.03 with their states after one
unit of isolated preparation. Replace one unit by -1.5, then evolve for three
time units; repeat cyclically for nine replacements. Whole initial membership
is gone after three replacements. The transmitted material is the complete
state of surviving units; the coupling matrix remains supplied apparatus.
Record every member identity and state. Compare open communication, fully
blocked communication, immediate 0.5-time-unit pause and a delayed pause
between times 0.5 and 1.0 of each replacement interval. Onward transmission
continues with the actual final three units for another complete turnover.

For an editing assay, prepare a positive population, transmit through nine
replacements, apply a negative input I=-4 for two time units to the actual
descendants, then hold for three and transmit through nine positive newcomers.
Sham input and blocked-contact controls run at equal clocks. Each sign is a
coarse expression label; final success requires all desired signed outputs
tanh(2u)>0.5. All panels run with RK4 dt=0.025 and dt=0.0125. Report both
continuous discrepancies and classification agreement.

## Integrity and limits

Freeze protocol, configuration and executable sources by SHA-256 before each
run; retain raw arrays, seed identities, environment and results. Runs refuse
existing output paths. Validate binary energy descent, continuous energy
descent, scalar/vectorized agreement, copying/erasure, writer isolation,
matched scrambling and numerical refinement. All writes stay in this lane.
Use one CPU thread and follow ../RUN_POLICY.md; benchmark before expansion.

Only locally generated H001 evidence and public Hopfield sources may support
a future forms paragraph. Private background lanes supply no imported code,
data, trained state, quotations, reported results or bibliography entries.
The existing manuscripts remain source material. Any later inclusion needs
fresh validation and an explicit statement of what these models omit.
