# Prospective design: sensing and acting on errors across scales

**24 October 2026 — NOT FROZEN. No scientific results.** ME000–ME004 are lane-local study names. Numerical choices below are a concrete starting design; the execution agent must freeze an implementation and qualification plan before outcomes. Existing studies keep their own verdicts.

## 1. Question and scope

We want to distinguish an investigator measuring error from a system receiving a signal, and a signal being available from an action making useful corrections. The central causal questions are:

1. Which discrepancies can the implemented system detect at site, region and whole-sheet resolutions?
2. Which changes to the body or reference does that signal cause?
3. When do those changes preserve acquired history and help a fresh successor, rather than merely reduce mismatch now?

There are two independent axes: **spatial organization** and **time through replacement**. A region is not a generation. A coarse biological label is not a complete state, and a full-field reference is not a demonstrated organism-wide target sensor. Spatial pooling, coordinates, dynamics and action rules here are supplied. The first model does not identify a biological error-detecting molecule or establish endogenous agency.

## 2. Apparatus and the boundary

Use the 16 × 16 periodic reference-based sheet underlying L15/L17. Body V and working reference R are dimensionless fields; theta is a fixed, target-independent environmental field for a source block. The existing writable-theta branches provide lessons, not an interchangeable packet definition.

Native settings: dt = 0.2, four-neighbor coupling = 1, noise amplitude = 0.3, comparison gain c = 0.2, reference rate rho = 0.002. Preserve the exact native order:

1. Native sheet drift and mean-centered additive noise, then clip V to [−2, 2], producing V-tilde.
2. Update the fast moving average from V-tilde.
3. Compare incoming R with V-tilde; apply the selected body action, mean removal and clipping.
4. Compare R with the resulting body; apply the selected working-reference action. Native R writing is not mean-centered.
5. Update a **separate passive outgoing capture Q**, initialized to zero, from the resulting body: Q-next = Q + rho(V-next − Q). Q never feeds the current body or working reference.

In the identity reciprocal arm, steps 1–4 must match the native equations. With identity sensing/action, the supplied corrective increments are:

```
body:              + dt * center(c * (R - V_tilde)), followed by clipping
working reference: - rho * (R - V_after_body)
outgoing capture:  + rho * (V_after_body - Q)
```

This Q boundary follows the L17 read/write split. At replacement **only Q crosses**, as the next body's incoming R: 256 float64 entries, 2,048 bytes. Discard V, moving average, working R, sensor telemetry and controller scratch state. Future noise is newly addressed; no ancestral RNG state is transmitted. Theta is recreated from the same public block specification, independently of the target. A separate held-Q readout tests usefulness without another round of writing.

The packet is not the complete memory budget: V, moving average, R and Q together occupy 8,192 bytes per current case, before theta, sensor buffers, snapshots or policy state. Report these resources separately. Protected snapshots add storage; a future reliability trace retained across replacement would be an additional inherited channel and requires an amended boundary.

Keeping Q separate matters: improved retained R after a few updates may still be direct preservation of its initial values. It is not by itself de novo renewal. In this design, active adjustment of R can affect Q only through the body. Include an explicit Q-writing-off control, distinct from holding the working R fixed.

## 3. Acquisition and enrolled cases

Begin with the native four supplied balanced half-plane messages: left/right, top/bottom and their sign reversals, at teaching amplitude 1.2. This tests correction of a narrow declared target family. It does not establish arbitrary form acquisition. Pretraining: 120 settling updates, then 1,000 imposed-body teaching updates; R learns from the post-update body as in L15, rather than being replaced with a clean target field. Theta writing is off.

Draft ME001 cohort: **16 independent source blocks × four messages × two parent replicates = 128 acquired cases**. Each source block supplies all messages under the same environmental field. Retain every acquired case, including poor acquisition. Report acquisition success and damage efficacy separately; do not select only recoverable founders.

Teaching labels/prototypes remain evaluator-only after acquisition. Foreign controls use a fixed orthogonal-message permutation within block and replicate; both own and foreign outputs are scored against the same own target. Message and replicate draws are not independent source blocks. Reserve identity ranges before outcomes and keep engineering identities disjoint.

## 4. Separating sensing from action

For a discrepancy field d = R − V, define P4 as averaging each aligned 4 × 4 patch and broadcasting its mean, and P8 likewise for 8 × 8 patches. Let center remove the global mean.

| Sensing interface | What reaches the action stage | Supplied access |
|---|---|---|
| Site | Each site receives its own d_i | Local reference and body values; no central all-site selector in this arm |
| Region | Sixteen 4 × 4 patch means, broadcast within each patch | Shared grid, aggregation and local broadcast |
| Sheet | Four 8 × 8 quadrant means with their common mean removed | Three independent contrasts; aggregation across regions |

The whole-sheet mean alone is unsuitable as the collective sensor because native dynamics remove mean drift. The sheet sensor therefore measures **relationships among regions**, not a single average.

Independently apply one of three spatial action maps to the received signal: site-resolved identity, 4 × 4 block broadcast, or centered 8 × 8 broadcast. For body actions apply native mean removal afterward; for R actions do not silently remove the DC component. Gains and durations are frozen; do not normalize the response using a target score or globally measured error norm in a nominally local policy.

Identity sensing contains all spatial frequencies, although its access is local. It is not a fine-frequency-only channel. Nested projections can yield identical compositions, such as site-sensing/region-action and region-sensing/site-action. List and test these **aliases**; do not treat duplicate trajectories as independent effects. The factorial reveals distinguishable information/action constraints, not nine guaranteed distinct mechanisms.

In fact, the nine aligned linear compositions have only three distinct maps before native dynamics. That panel alone cannot attribute a shared effect uniquely to sensing versus actuation. Include a small spatial-placement panel: keep the sensor grid fixed while shifting the action grid by **one site along both axes**, separately for regional and sheet actions. Define the shifted operator as roll-back → block projection → roll-forward, with the sign convention frozen in code. Compare with aligned actuation under the same starting state and signal, and with the reciprocal sensor-only shift. These noncommuting placements test a supplied alignment relationship; they are not additional independent scales or a test of autonomous coordinate learning. A half-sheet-patch shift is unsuitable here: centered quadrant projections shifted by four sites in both axes annihilate each other's signals. The synthetic checks expose this special alias before any scientific outcome.

The initial aggregation is an idealized supplied communication operation. Log transmitted scalars and synchronization. ME004 replaces instantaneous aggregation with finite local communication and tests timing; initial results cannot establish equivalent biological communication costs.

## 5. Damage and fixed corrective routes

Branch each acquired case into **body-only**, **reference-only**, **both**, and sham damage. For each non-sham location, use fine, regional or coarse centered perturbations: ten conditions including the common sham. Generate perturbations by projecting independent Gaussian fields into the bands in section 7, then scale to draft pre-clipping RMS 0.5. Body damage is clipped to the physical range; reference damage follows the frozen reference-domain rule. In combined damage use independently addressed fields in the same band.

All arms within a case receive identical injury fields and subsequent noise. Record realized perturbation RMS, support, extrema and clipping: matching pre-clipping RMS does not match post-clipping damage or its functional effect. Damage masks, locations, clean states and injury labels are unavailable to the operational sensor/action interface. The damage generator and evaluator may retain them. Never feed the clipping residual back as a hidden injury mask.

Compare four **fixed routes** over 1,000 updates:

- **Inactive correction:** continue native body dynamics; comparison and working-reference adjustment off. Passive Q capture remains on.
- **Body-directed:** adjust V from the sensed mismatch; hold working R.
- **Reference-directed:** comparison into V off; update working R from activity. Under this boundary, R then cannot affect V or Q: this is an expected alias with inactive correction, a useful route check, not a useful controller by assumption.
- **Reciprocal:** allow both body and working-reference adjustment, in native sequential order.

This deliberately exposes a mechanistic constraint. Reference correction can affect future Q only if there is a route back into body activity. A later **write-then-read** schedule may open that route; it must be registered as a separate timing condition with equal total duration, not silently folded into the reference-only arm.

First panel: the three matched sensing/action resolutions × four routes × ten damage conditions. Second panel: the full 3 × 3 sensing/action factorial for body-directed correction across sham and singly damaged conditions. Reuse overlapping/identical branches explicitly. This is bounded development: no primary confirmatory claim is selected from the most favorable panel.

Add a fixed timing comparison at the site and regional resolutions: **write-then-read** uses 500 reference-only updates followed by 500 body-directed updates with R held; **wait-then-read** holds R and disables comparison for the first 500, then uses the same 500 body-directed updates. Capture Q runs for all 1,000 updates in both. Their comparison tests whether changing R becomes useful when it is subsequently read, with matched reading opportunity and elapsed time. Include these arms in the complete-cost forecast; do not insert them only after finding favorable reference changes.

Route controls on the matched-resolution panel:

- Clamp the sensed signal to zero while leaving the actuator connected.
- Permute signal placement using a fixed random permutation at the interface's resolution, preserving its values; optionally reverse sign in a separately labeled arm. Do not use a new permutation at every step unless predeclared.
- Disable the actuator while logging the sensor. Native evolution continues.
- Hold a body snapshot as the capture source; compare it with continued body-driven Q capture. It supplies a different information source and must be counted.
- Disable Q writing; erase Q; disable the fresh reader; use a matched foreign packet.
- Copy the **post-damage incoming R** without rewriting, and separately preserve the **pre-damage R** as a protected-backup comparator. The latter is privileged storage, not information available to the operational controller.
- A clean-target oracle may be used as an explicitly privileged instrument ceiling. It is not a learned correction result.

Use four independently initialized fresh recipient draws per outgoing packet in ME001, paired across arms and independent of founder noise. Hold Q as the read reference for 1,000 updates with native gain. No body fragment, incoming working R or selected future is carried into the fresh read.

## 6. What disagreement cannot identify

Use an exact interface fixture: in two constructed histories the accessible present state is V = Y, R = X, with all other visible fields identical. In one history X is the evaluated acquired target; in the other Y is. A deterministic memoryless controller sees the same input and must take the same action, although the preferable source differs.

This is an information limitation of that interface, not evidence against every possible controller. A retained history, redundancy or a reliable external cue could distinguish the cases, but must be explicit and budgeted. Do not quietly supply the pre-damage field as a small “trust” feature. If ME001 cannot identify source reliability from permitted signals, report that outcome. Do not encode which component the experimenter damaged into the proposed ME002 policy.

## 7. Separate endpoints

Offline decompose d into mutually orthogonal components on the aligned nested grid:

```
fine:       d - P4(d)
regional:   P4(d) - P8(d)
collective: P8(d) - mean(d)
constant:   mean(d)
```

Their sum is d; report each squared norm and the constant component separately. Reducing R–V mismatch can mean successful correction, mutual drift, or loss of both patterns. It is never sufficient by itself.

For body and fresh-recipient fields report, on all 256 sites:

1. Sign-only agreement with the evaluated target, with exact sign/tie convention frozen.
2. Amplitude eligibility: fraction with |V| > 0.2.
3. Qualified agreement: sign-match **and** amplitude eligibility, still dividing by 256.
4. Their 2 × 2 joint table, so sign and amplitude changes are not falsely treated as an additive decomposition of qualified agreement.
5. Own-versus-matched-foreign qualified agreement, target-decoder recognition with explicit tie splitting, and the distinct total agreement.
6. Continuous error and band-specific target error, separately from internal R–V discrepancy.
7. Fresh-reader success/recognition and paired rescue/loss counts relative to inactive correction and copying.

No new “form quality” scalar combines these outcomes. The initial primary development display is a paired plot of current-body versus fresh-recipient effect, faceted by damage and route, with block estimates. A decrease in one score cannot stand in for historical specificity or future capacity. Use an all-case table and show failed formation/acquisition separately.

**Detecting what, exactly?** Record sensor time courses and compare damaged cases with matched shams. Distinguish detecting an imposed perturbation from detecting loss of target fidelity, and both from predicting harm to a successor. A signal can distinguish an injury that has no functional consequence, or miss a harmful disturbance. For a later thresholded detector, freeze its threshold and time window using development/sham data only; report false alarms, missed consequential errors and latency on fresh blocks. Continuous feedback needs no binary alarm, but its action-versus-signal response still needs measurement. No detector performance is established merely by computing R−V.

## 8. Analysis, resources and independent checks

Pair interventions at the complete starting state and stochastic draws. Pool recipients and parent replicates within each block; weight blocks equally. Report per-block effects, whole-block intervals, paired harm/rescue counts and the exploratory status of ME001. Do not use cells, message variants, recipient draws or algebraic aliases as independent units. Any formal multiple-comparison allocation belongs in the later frozen confirmatory protocol.

Equal update windows do not imply equal cost. Record actual L1/L2 intervention increments, changed sites, reference/capture writes, sensor messages, pooling operations, retained bytes, CPU time, wall time and peak RAM. The two native gains have different physical roles; equating their numeric values would not equalize intervention dose. No ATP/viability claim follows from a computational cost.

CPU baseline: float64, up to 12 processes with one numerical thread each, disjoint block shards, deterministic RNG addressing and paired precomputed or reproducibly regenerated draws. Benchmark the entire workflow, including independent replay and I/O, before launch. Use batch limits determined from the actual machine. Draft ME001 wall ceiling: 48 hours; never infer feasibility from the CPU count alone. Compact results enter git, raw arrays an explicit external run directory.

Independent checks must cover equations/update order, read/write lesions, source isolation, zero-Q boundary, scoring, pairing, pooling, finite values, input hashes, parallel scheduling invariance and saved-output reanalysis. The synthetic operator checks in this folder establish none of the native-dynamics requirements. No scientific run is currently implemented or qualified.

## 9. Ambitious staged extensions

**ME002 — prospective arbitration.** From development, freeze one selector that chooses body correction, reciprocal updating, a specified write-then-read schedule, or waiting. State exactly which local/pooled signals and recent telemetry it receives. Prefer an inspectable rule or small fitted model to an unconstrained optimizer. Compare with the best development-selected fixed route, a local-information selector, signal/action lesions and copying. Use 64 fresh blocks, four taught messages and two parents per message, with eight paired recipient draws as a draft target. Freeze meaningful superiority and harm margins, uncertainty allocation and full-budget accounting before fresh outcomes. Confirmatory status requires success under those conditions, not merely a favorable mean.

**ME003 — conditional future usefulness.** Restore records from both currently failed and successful bodies using a prespecified all-block sampling rule. Target 64 records, 64 independent futures each, and horizons 1, 3, 8 and 16. Compare the frozen policy, its removal after one rescue, the best fixed route, post-damage copying and protected storage. Include own/foreign and disabled-reading conditions at declared horizons. Estimate immediate, terminal and uninterrupted outcomes separately. Quantify individual harms and uncertainty; repeated futures reduce sampling uncertainty for each record but do not create new population blocks. A full complete-cost benchmark and fresh protocol precede this stage.

**ME004 — generalization and collective coordination.** Test untouched pattern families beyond the four half-planes, translations relative to the pooling grid, and larger sheets. Define whether a size change means finer discretization or a larger domain and change equations consistently; these are not interchangeable. Test finite propagation delays, neighbor-only messages, asynchronous actions, and conflicting regional versus whole-sheet corrections. Separate controller transfer without refitting from retraining. Add compact-record budgets only after the full-record boundary works, including all retained reliability state. A useful result would predict correction under new organization or communication constraints; failure would identify the limits of the supplied scale hierarchy.

**Optional GH200 acceleration.** Port only after CPU qualification. Fix precision, reductions, clipping and stochastic draws; compare trajectories and near-threshold endpoints, then repeat a complete saved-state check. Document any numerical intervention separately from hardware speedup. Coordinate shared usage and retain a CPU fallback. No GPU run is launched or reserved by this design.

## 10. Outcomes that matter, including nulls

| Observation | Bounded interpretation |
|---|---|
| Correct sensing helps; silencing it removes benefit; actuator lesion also removes it | The declared signal and action route contribute causally. |
| Mismatch falls but own-history specificity or successor usefulness falls | The controller repairs its proxy at the expense of the evaluated distinction. |
| A coarse action helps coarse organization but harms finer distinctions | A scale-dependent trade-off within this apparatus. |
| Larger-scale access adds no benefit beyond a matched local comparator | No demonstrated value of that extra access under the tested task and budget. |
| Body-based updating helps corrupted R and harms intact R | Conditional source usefulness; disagreement alone still need not identify the right action. |
| No policy can choose better using the permitted signals | A limit of this information interface or candidate policy, not proof that arbitration is impossible. |
| Initial correction helps, but advantage disappears through renewal | A repair result without durable improvement in continuation capacity. |
| Protected copying remains stronger | Preserve that result; do not redefine rewriting as necessary. |

Finite nulls require adequate precision relative to frozen meaningful-effect margins. Failed qualification, wide intervals or saturation do not establish absence. Biological translation, emergent goal formation and independently active forms remain separate questions.
