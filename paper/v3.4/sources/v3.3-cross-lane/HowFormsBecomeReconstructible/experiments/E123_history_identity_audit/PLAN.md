# E123 original planning draft — what history is externally recoverable?

Current implementation: [frozen scientific design](DECODER_DESIGN_V1.md),
[numerical amendment](DECODER_AMENDMENT_V2.md),
[qualified V2 implementation](DECODER_FREEZE_V2.json), [current status](README.md).
V1 launched on 2 November at 17:25:45 UTC after E122's verified closeout and
stopped at its optimizer cap. After a bounded diagnosis and repeated synthetic
qualification, V2 launched at 18:40:10 UTC. No final decoding result was available
at that launch. This file preserves the original planning decisions below; the
pre-update copy is retained in `analysis/delivery_v1_documents/`.

1 November 2026. User instruction: put the supplied “Measuring which history
each component makes recoverable” plan on the list next. Forms scope follows
E122, ahead of the deferred E118 diagnosis. TT021/NL003 interface work and the
other named lane handoffs remain separate; no duplicate analysis or simulation
is assigned to Forms. No manuscript change, decoder fitting or new dynamics
is authorized by this queue entry. Existing frozen outcomes retain their status.

2 November implementation update: the user authorized continuation. The first
[inventory/interface deliverable](HANDOFF.md) is complete: all 192 E014 archives
and 3,136 arrays verified, 12,288 original checkpoint count rows reconciled,
320 development cases checked. No decoder is fitted, and E122's running outputs
were not opened. The remaining plan below is a decoder design draft, not a freeze.

## Deliverable and source scope

Report three separate quantities per assay: representation size; recovery of a
declared historical identity by an external observer; and native reconstruction.
Do not add component scores into a causal information budget or turn byte counts
into historical bits.

Start with all eligible retained E014 blocks 12000–12063, all four founders and
both recipients, both record budgets and every declared checkpoint. All sources
and failed formations remain. Known cohorts make this a **post hoc** analysis,
including predictions held out from decoder development. A later fresh test
would need a separate freeze.

The local raw run is `E014_long_renewal/runs/confirmation_v2/`. The existing
[E122 inventory](../E122_specificity_ceiling_and_tail/planning_inventory.json)
lists 128 present factor-1/factor-4 lineage files, their sizes and original
completion hashes, plus the source-file count. Those hashes are expected source
hashes, not a new full-file verification. E123's
[completed inventory](analysis/inventory_v1/SOURCE_MANIFEST.json) now rehashes
every required archive and inventories all schemas and array content hashes.
E014's compact cell counts can
reconstruct existing scores but cannot support arbitrary field decoders.

## Target, candidate dictionary and boundaries

Primary proposed recognition task: identify the acquisition founder among the
**four observed founders from the same background block**, with a balanced
four-way prior and 25% chance accuracy. Founder labels are block-local; they
have no shared biological or semantic meaning across blocks. The supplied
prototype dictionary is an evaluator resource, not a native writer input.
Give every observer the identical complete dictionary, and count its cost.

Track two distinct labels: the historical donor that initialized a record, and
the own founder against whose prototype the native agreement is scored. They
coincide for own records and differ under the cyclic foreign mapping. Decode
the declared acquisition donor throughout a foreign lineage; do not quietly
relabel its donor as the recipient's own founder. Preserve the original native
own-target scores alongside this auxiliary target. Other control arms need
explicit target definitions or a no-history/null designation before inclusion.

Separate lifecycle interfaces from checkpoint interfaces:

- At a lifecycle boundary, R is the actual incoming packet, B is a specified
  retained body/reference state, and O is that body's actual written output.
  End-of-reading, pre-capture and post-writing bodies are different instants.
- At an independent checkpoint, R is the packet supplied to the fresh reader
  and B is that fresh recipient's retained field. The checkpoint does not write;
  no new outgoing packet may be invented for it. Its incoming packet can also
  be described as the preceding lifecycle's O, with the boundary made explicit.
- Protected own/foreign controls retain acquisition bytes. Their native reads
  can be compared with renewed records under the same candidate dictionary and
  matched recipient conditions. Identical protected fields across horizons are
  repeated measurements, not extra independent examples.

Coordinate-matched founder recognition is the proposed primary. Translation or
phase tolerance, family recognition and fine-detail recovery require separately
declared tasks and scores. Any shifted templates or alignment search count as
observer resources. Do not import the guided assays' family labels into E014.

## Allowed inputs and decoder safeguards

Inventory common setup A, packet R, body B, outgoing packet O and any actual
extra state Z. List masks, public coordinates, codecs, dtype, guide/calibration,
history-specific memory and candidate dictionaries separately. Do not create an
extra-state arm when no such state exists in the retained assay.

Compare setup/dictionary-only, record, body, joint record+body, and outgoing
inputs where the boundary contains them. The setup-only condition cannot include
the target, target-encoding seed, record filename, donor/arm label, hidden index
or row order. Grouping metadata and true labels stay outside decoder arrays.

Begin with inspectable template/candidate comparison and a regularized stronger
comparator using the same permitted cheap features. Candidate scoring should
respect candidate permutations, rather than exploiting arbitrary index order.
Freeze exact features, models, tuning grids, calibration, probability floor,
tie handling, inference budget and primary comparison before predictions.
The proposed primary comparison is joint versus record-only recognition at a
declared boundary; choose the boundary before fitting, not after results.

Use grouped outer validation by independent background/founder block. Keep all
lives, routes, budgets, horizons and related prototypes from a block within its
fold. A held-out block's full candidate dictionary may be supplied at prediction
time as declared observer input; it must not train fitted parameters. Scaling,
regularization and calibration use inner development folds only. Preserve all
eligible blocks or document a predetermined outcome-blind sample. A small fixed
interface export is development only, never the population estimate.

Check label balance within background/condition, exact duplicate inputs, target-
shuffled training controls, candidate permutation behavior and metadata leakage.
Seal held-out probability tables before scoring. Use the same inclusion set and
prior for paired observer comparisons; report missing fields rather than silently
changing the sample or synthesizing missing states.

## Scores and interpretation

Report accuracy, balanced accuracy where relevant, full confusion matrices,
declared ties and prior-only performance. Report all four probabilities per
case, log loss in bits, its probability-floor sensitivity and predictive
information relative to the declared prior. Freeze the entropy convention and
check the assumptions of the proposed variational interpretation with the common
theory-lane review. A negative empirical score is retained; accuracy is not
converted to bits by an ad hoc formula. Any confusion-matrix information
estimate needs a finite-sample bias check.

Resample whole blocks for paired observer differences and show regime/budget/
horizon results. Preserve the original qualified, sign-only and amplitude
outcomes alongside recognition, with all numerator and denominator counts.
Better observer decoding does not establish native reconstruction, unique
conditional information, causal use by the writer or additive component credit.
Redundancy and information accessible only jointly remain possible.

Measure feature construction, dictionary/template access, training, calibration
and per-case inference costs for every observer. A weak decoder's failure is
not an information limit of its input representation.

## Compact export and E122 integration

First export a source manifest with protocol/code/array hashes, raw run root,
inclusion/exposure status, missingness, boundary timing, array names/shapes,
native and exported dtype, bytes and every lossy transformation. Include the
candidate dictionary and masks/coordinate conventions. Large fields stay in
run storage with retrieval instructions.

The prediction table needs source block, paired record identity, condition,
budget, boundary/horizon, decoder, fold, historical donor target, candidate
mapping, all four probabilities and native outcomes. Labels and metadata are
joined only for scoring/grouping. Return per-block outcomes sufficient to
recompute the aggregate report, plus the reproducible analysis script.

E122 was queued when this plan was written; on 2 November its compatible
[export schema](../E122_specificity_ceiling_and_tail/DATA_DICTIONARY.md) passed
qualification and the scientific continuation launched with frozen inputs.
Consume its eventual protected-foreign and long-horizon fields without rerunning
trajectories or changing its primary specificity endpoints. Its retained native
checkpoint/body snapshots support this interface. Use the existing frozen
outputs or record missingness; do not amend the running protocol silently.

## Coordination and holds

The user's wider plan prioritizes retained TT021 and NL003 interfaces before
generalizing the common reporting format. Theory-tests owns TT021/D074/TT032 and
later TT014 exports; the multiscale lane owns NL003; L20/L22 owns guided-routing
interfaces; theory reviews information interpretation and decoder freezes.
Forms contributes E014/E122 exports to that common format. No messages, delegated
agent work or new runs have been triggered by adding this item.

Forecast calibration, E119–E121 pruning/regime tests and E122 long-horizon
specificity remain on their existing tracks. No additional FEP, cellular or
Hopfield launch is requested. The user's manuscript hold remains in effect;
verified exports and predictions would be evidence for a later separately
authorized integration, not permission to alter the manuscript now.
