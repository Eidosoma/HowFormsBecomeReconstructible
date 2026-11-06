# Information retained by records, bodies and supplied apparatus

**1 November 2026. Working audit for v3.3; manuscript changes deferred.** This responds to the reviewer requesting a per-assay information budget. It checks retained methods, protocols, implementation interfaces and selected local artifacts. It does not rerun simulations or fit decoders. The manuscript, supporting information, evidence ledger and running protocols remain unchanged.

This pass covers the assays named in the comment and their nearest controls. It is not a completed decoding inventory of every campaign in the research program.

The audit supports the reviewer's concern: several successful assays use information outside the nominal inherited packet. That information has different roles. A shared guide supplies a repertoire and a way to orient a record. Acquired anchors retain part of a particular history. A family-dependent control signal can identify the family. An evaluator's knowledge of the answer is not necessarily information available to the developing body.

The next measurements should distinguish those roles rather than assign one additive percentage of success to each component. The accompanying [decoding plan and lane handoffs](INFORMATION_DECODING_PLAN_V3.3.md) specify how. [Reproducible calculations](information_audit_calculations_v3_3.py) and their [retained output](INFORMATION_AUDIT_CALCULATIONS_V3.3.json) cover only the analytic deductions below.

## Three quantities to report separately

1. **Stored representation:** arrays, dimensions, dtypes, bytes, masks and persistent controller state. This describes the implemented boundary, not how many independent historical bits it retains.
2. **Recoverable identity:** how well a declared observer predicts a specified founder, message or learned orientation from permitted inputs on held-out blocks. This depends on the target, candidate set, prior, decoder and budget.
3. **Causal usefulness:** what changes when those inputs or their relationships are intervened on while a native recipient reconstructs. Information may be decodable but unused, or useful only jointly with another input.

A fixed guide can contain no information about which randomly assigned founder produced a packet, conditional on the shared setting, yet be essential to reading it. Conversely, an apparatus chosen as a function of the taught family can convey that family even when its numerical writer receives no explicit label. Redundancy and joint dependence prevent a simple additive division into record, body and apparatus contributions.

Throughout this audit, **common setup** means the rules, geometry and settings held fixed across the competing identities. Message-conditioned choices, acquired anchors and labelled task knowledge are listed separately. Seeds, filenames and row positions that encode labels are bookkeeping, not admissible decoder inputs.

## Representation accounting

These are payload or logical counts, not estimates of acquired information or complete implementation size. Runtime state, source code and shared parameters are additional unless explicitly included.

| Assay | Incoming and outgoing inherited state | Other information retained or supplied |
|---|---|---|
| Unprescribed spatial renewal, E004/E014 | Full: 256 float64 values, **2,048 bytes**. Compact: 16 float64 values, **128 bytes**, with the declared codec. | Shared dynamics, geometry and codec. Founder prototypes are retained for offline scoring. No founder target is supplied to the native reconstruction procedure. |
| Reciprocal repair, D073/D074; early capture, TT021 | Final 256-value theta record, **2,048 bytes**, enters a fresh-body readout. | Surviving body activity, working reference, moving average and reset/fill conditions can influence repair before the boundary. They are not all part of the transmitted packet. |
| Guided reconstruction, D135/D140 | A 256-value record, **2,048 bytes**; the outgoing record is derived from the final working reference. | Shared guide of two 256-value float64 templates, **4,096 bytes**; fixed host parameters; guide routing procedure. The guide is not inherited or refitted per lineage. |
| Compatible writer placement, D145 | Same record and shared guide as above. | An external family-aware procedure selects a compatible spatial offset. The numerical writer receives that offset. |
| Functional reconstruction and fixed repair, TT014/TT016/TT018 | 512 float64 weights, **4,096 bytes**. | Lattice, cue/input pins, reader, teaching protocol, writer or optimizer. Task labels used for evaluation are not inputs to the fixed repair. Repeated repair retains the supplied algorithm across generations. |
| Forecasting, TT008 and manuscript evidence E107 | The functional packet is the object being forecast; diagnostic branches are discarded. | Forecaster receives declared history/features and task knowledge. Successor probes perform additional writes/reads under a supplied apparatus. These computations are not an extra inherited packet. |
| Current-success promotion guard | Either the incoming or candidate outgoing 4,096-byte packet is selected. | Protected access to the incoming packet during candidate evaluation; true taught orientation for the success test. Two representations coexist at selection, but only the chosen packet is transmitted. |
| Hierarchical record and anchor gate, NL003 | The inherited package depends on recipient condition: local reference/bonds; optionally regional and block codes; optionally surviving anchor mask and signs. | On a 64×64 sheet, quarter-density anchors initially retain **1,024 sign values** beyond the regional codes. Ideally bit-packed binary signs alone would occupy **128 bytes**, excluding locations, masks, gauge/calibration and other records. Native arrays are dense, so this is not their actual serialized size. |

The corresponding source details follow. No new bits-based budget can be inferred simply by adding these byte counts.

## Spatial history and reciprocal repair

### Unprescribed renewal

The [E014 protocol](../experiments/E014_long_renewal/PROTOCOL.md) compares histories under the same background and evaluates both own and foreign records against the own-founder prototype. The developmental background is removed before capture. The prototype is an observer-side reference, not a template passed into the writer or reader.

A new identity decoder needs a declared candidate dictionary: founder numbers in different independent blocks are arbitrary labels. For example, identify the correct founder among four candidates sharing a background, while keeping all descendants and candidate prototypes from a source block together in held-out evaluation. Do not give the system the prototype merely because the external evaluator needs it.

The [reviewer-specificity handoff](../experiments/E014_long_renewal/analysis/reviewer_specificity_v1/HANDOFF.md) supplies compact derived counts and reproducible earlier analyses. Those counts are not general-purpose field exports. In this checkout, `runs/confirmation_v2` exists but contains no NPZ files; the named `block_012000_factor_4.npz` is absent. That is a local availability finding, not a claim that the remote archives were lost.

### Reciprocal repair and body-derived message content

The [fresh repair protocol](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/protocols/L22_FRESH_WRITING_REPLICATION_V1.md) and [body-source protocol](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/protocols/L22_BODY_SOURCE_V1.md) hold damaged records matched while changing body organization. The body-source test preserves body values while rearranging their spatial placement. Only the repaired theta record crosses into the fresh assay; activity, moving average and working reference do not.

D074 establishes that spatial organization changes later record usefulness. Its failed donor-redirection criterion still leaves open whether the body supplies corrective message content or helps use residual information in the damaged record. A better decoder cannot retrospectively turn that causal distinction into a passed result.

[TT021](../experiments/theory-tests-lane/TT021/PROTOCOL.md) offers a cleaner conditional information test. Its common incoming packets are byte-identical within opposite-message pairs. Early capture initializes the working reference from the injured body, including fresh fill. Partner-body and held-snapshot conditions separate the source of message content from the incremental value of continued feedback.

**Analytic bound, not a new decoder result:** with four equally likely messages, two indistinguishable opposite-message pairs, and setup that does not reveal polarity, an incoming-packet-only decoder can identify at most half the messages correctly. It carries at most one bit of the two-bit message identity, and no polarity information within a known pair. These are upper bounds; distinguishability between the pairs is not assumed. A decoder that exceeds them must have received additional information, or the assumed identity construction is wrong.

This makes the priority comparison: common incoming packet and shared setup, then add the permitted body state, then inspect the outgoing packet after early capture and after partner substitution. Use the full state available at the specified instant; a voltage image alone is not the whole repair-time body/reference interface.

The [TT021 closeout](../experiments/theory-tests-lane/TT021/CLOSEOUT_HANDOFF.json) documents saved records. Its execution record names `TT021/runs/confirmation_continuation_v1`; that directory is absent in this checkout. Export the existing inputs and outputs from their retained archive before proposing another simulation.

### Reset structure is a separate supplied input

[TT032, manuscript evidence E105](../experiments/theory-tests-lane/TT032/PROTOCOL.md), changes reset structure on previously exposed histories. For resting voltage r and fresh-cell mask F, the compared working references are V−rF, V−r/2 and V−r(1−F). These conditions preserve a mean correction while changing spatial placement. The mask is therefore an explicit apparatus input, although it need not encode the acquired message.

Decode two distinct targets: original message identity and reset-template identity. Include the mask and correction field in the inventory, and measure whether a neutral body follows the reset template. Do not treat the roughly 31–34% versus 74–78% recognition contrast as an estimate of bits supplied by the reset. This is a different cohort and intervention from TT021; it cannot retrospectively decompose TT021's effect.

## Shared guides and family-dependent controls

### What the guide does

The [serial-address protocol](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/protocols/L20_SERIAL_ADDRESS_V1.md), [fresh-founder protocol](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/protocols/L20_FRESH_FOUNDERS_V1.md) and [guide implementation](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/src/laws_confirmation/l20_learned_guide.py) specify a common two-template guide fitted on separate development records. It searches both families and translations, then inverse-translates the incoming field. It does not replace packet pixels with a canonical template. Ties and constant fields have declared handling.

The numerical writer does not receive the guide or incoming packet directly. It does inherit the body, moving average and working reference produced during reading, so information acquired through guided reading can still affect writing. The outgoing packet is derived from the final reference, not copied from the final applied theta field. This indirect route must remain visible.

A guide held identical across randomized founder identities cannot identify the realized founder by itself. That does not make it irrelevant: it supplies a coordinate system, family repertoire and interpretation. Test family identity separately from within-family founder identity and phase. Guide-only, record-only and record-plus-guide decoders answer different questions from a native guide ablation.

The retained [D140 example](../paper_assets/data/retained-reconstruction-history-v1.npz) contains packets and body/reference fields for one illustrative source block, selected by the documented figure rule. It is suitable for checking interfaces and drawing an example, not for estimating held-out decoder performance. It also does not contain every moving-average state.

### A selected offset can itself convey family identity

The [D145 protocol](../../PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/L20-extension-1/serial-compatible-feedback/PROTOCOL_V1.md) explicitly calls the external address rule family-aware. Compatible nonzero offsets are sampled uniformly from pools of 15 for family A and 31 for family B. The pools intersect at only one offset, (0, 8).

**Exact protocol calculation:** under a balanced A/B prior, an observer who knows those pools and sees one selected offset can classify family with optimal accuracy **61/62 = 98.3871%**. The mutual information between family and that single offset is **0.954946 bits**. The [calculation script](information_audit_calculations_v3_3.py) enumerates the pools and probabilities directly.

This is information in a supplied control signal. It is not a measured decoder result, an estimate of the native writer's use of the signal, or the fraction of reconstruction caused by the apparatus. D145's primary comparison is within family B; when family is fixed, its entropy is zero. The calculation instead exposes why a two-family reconstruction result cannot be described as depending only on an inherited packet plus identity-independent machinery.

## Functional repair, diagnostics and promotion

### Fixed completion of erased connections

The [TT014 protocol](../experiments/theory-tests-lane/TT014/PROTOCOL.md) supplies the lattice, input-pin constraints and frozen optimizer. The optimizer sees the surviving record and its exactly zero entries, preserves nonzero weights, and fills selected zeros. It does not receive the clean ancestor, desired output orientation, donor body or future outcomes. Fixed positive input pins are shared between the two learned output orientations; they should not be mistaken for a supplied output label.

Audit the original, repaired and shuffled-addition records under the same task-identity decoder, then compare native recipient outcomes. A repair can preserve, expose or impose interpretable structure. Decoding the desired orientation after repair alone cannot distinguish those possibilities; label-blind repair inputs, matched controls and acquired-history comparisons remain necessary. [TT016](../experiments/theory-tests-lane/TT016/PROTOCOL.md) and [TT018](../experiments/theory-tests-lane/TT018/PROTOCOL.md) add later boundaries, while the repair algorithm remains supplied.

### Forecast task knowledge belongs to the observer

TT008's signed diagnostic uses task orientation and ports. The [equal-read forecast protocol](../experiments/theory-lane/rdt_fresh_equal_read_v0_1/protocol.json) likewise defines supplied knowledge and diagnostic branches. If the forecaster receives the true binary orientation, asking whether its full input decodes that orientation is trivial: the label is already present. Its scientific task is forecasting future success, not discovering the label.

List the forecaster's inputs separately from what the native body and writer receive. Report the budget for direct reads, successor writes/reads and feature computation. The packet alone still has a legitimate identity-decoding question, but it must use an explicitly label-blind observer. Do not add discarded diagnostic branches to the transmitted payload, or attribute their information to a native reader that never receives them.

### The promotion guard uses a history-specific scoring signal

The [guard implementation](../experiments/theory-lane/rdt_success_guard_allocation_replication_v0_1/sr_policy.py) evaluates cue windows using the true taught orientation and can retain the protected incoming packet. Those are resources available to selection, beyond the native candidate writer. The candidate and backup must both appear in the resource inventory, even though only one is transmitted.

Comparisons that remove task knowledge or backup access are new policy tests, not reanalyses that can silently redefine the qualified policy. They belong in later frozen studies if the existing work does not already cover them. Decoder analyses can describe the selected outputs now; they cannot establish that an autonomous system could perform the same selection without that information.

## Multiscale codes and acquired anchors

The [NL003 protocol](../experiments/multiscale-error-lane/REGISTRATION_NL003.md), [report](../experiments/multiscale-error-lane/REPORT_NL003.md) and [implementation](../experiments/multiscale-error-lane/nl003/sim.py) distinguish the local reference and relational bonds, regional codes, block codes, and a gate using acquired local signs. The anchors are additional acquired state. They are not merely another way of reading the same damaged regional code.

On the main 64×64 sheet, quarter-density selection initially provides 1,024 anchor locations and their signs. Injury can remove anchors. The gate depends on the live mask and signs, and recipient conditions differ in whether those values accompany the other codes. Count the actual package for each recipient condition, including gauge and positional information. The 256 regional codes must not automatically be called 256 independent bits, and the anchor count must not be called 1,024 bits of founder identity.

Separate target questions: distinguish the A/B taught alternatives; recover regional distinctions; recover fine-cell signs; preserve phase or polarity when identifiable. A/B identity has at most one bit under a balanced prior, even though decoding all fine signs is a much larger task. Joint decoding should test whether anchors add useful identity information beyond the codes, and whether wrong or foreign anchors redirect the outgoing record.

There is an additional export issue: [the worker](../experiments/multiscale-error-lane/nl003/worker.py) saves reference and body snapshots as float32 and bonds/sign arrays as int8. Decoding those exports measures information accessible through that saved representation. Do not silently treat it as decoding the complete native-precision state. The [run record](../experiments/multiscale-error-lane/results/nl003/RUN.md) locates the retained development archive and hashes; retrieve its fields and verify their dtypes before fitting.

## What can be done now and what is still missing

| Work | Current status | Next deliverable |
|---|---|---|
| Boundary inventory and payload arithmetic | Completed in this audit from retained sources. | Review against each lane's exact export manifest. |
| D145 family information in one selected offset | Analytic result, reproducible without trajectory files. | Optional empirical frequency check against the frozen offset schedule; do not reinterpret the primary effect. |
| TT021 common-packet information limit | Conditional bound from paired packet identity. | Verify byte equality in the retrieved arrays and fit matched input-set decoders. |
| E014 founder decoding | Compact endpoint/count tables available; full named fields absent locally. | Retrieve existing founder and checkpoint exports, including the candidate dictionary and full inclusion manifest. |
| D135/D140 guide and record decomposition | One retained illustrative trajectory is local. | Obtain the full cohort or a prospectively fixed, unselected block sample; no cohort inference from the illustration. |
| NL003 anchor/code decomposition | Code and summaries available; native and saved representations differ. | Export permitted component fields, masks and recipient conditions from retained development runs. |
| Functional identity and repair decoding | Protocols define interfaces; no new decoding performed. | Export matched incoming/outgoing/control records and block IDs without exposing labels to the repair. |
| Forecast and guard information | Inputs checked; known labels and protected storage identified. | Keep existing forecast reporting work separate; describe source knowledge and costs explicitly. |

The [lane handoffs](INFORMATION_DECODING_PLAN_V3.3.md) prioritize TT021 and NL003 because they most directly distinguish additional historical content from shared reconstruction machinery. This is a common auxiliary assay across models, not yet a common measure of all form, competence or continuation. Native reconstruction and intervention endpoints remain essential.
