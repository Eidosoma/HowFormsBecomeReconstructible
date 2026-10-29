# E098 retained data

`SOURCE_DATA.json` reserves new block IDs and pins prior exposure manifests,
E097 closeout and excluded E077 benchmark inputs. `SAMPLE_FREEZE.json` confirms
the fixed sample and completed runtime review before scientific generation.
Run manifests snapshot the local import closure, protocol, dictionary, registry
and passing tests. Benchmark and scientific configurations are distinct.

Source archives retain acquisition, all 32 ancestry boundaries, pulse body,
three continuation boundaries, native/mixture source construction, first
recovery and the selected-edge pruning intervention. Packet bytes encode
little-endian float64 symmetric lattice weights; selection uses the unchanged
zero-incoming/nonzero-outgoing exact-fallback rule.

`writer_TASK.npz` has 18 slots: paired I/P/erased (0–8) then independent I/P/erased
(9–17). Arm order native sham, native pulse, mixture sham, mixture pulse.
Input packets, masks, common birth, effective weights, coupling, final state,
32-observation window, ordinary/contrast/fallback arrays, outgoing packets and
holding end state are retained. Full-state hashes and paired-half hashes cover
every update; common/innovation Gaussian hashes identify both cue-noise streams.

`writer_scores_TASK.npz` and `writer_end_scores_TASK.npz` preserve the window and
final pre-capture state separately. `writer_diagnostics_TASK.npz` stores selected
edge counts and product/weight sums for every slot/founder/recipient. Writers
have one realization per source case; duplication in terminal-row exports does
not add writer draws.

`terminal_packets_TASK.npz`: 27 slots = nine original I0/P0/erased, nine paired
writer outputs, nine independent writer outputs. `assay_TASK_rDRAW.npz` retains
injury, birth, effective weights, denominators, couplings, final/window states
and per-update hashes. `scores_TASK_rDRAW.npz` gives function; `coupling` files
retain uninjured and postinjury selected share, mass, denominator and isolated
fraction. Selected share sums all receiver inputs, including clamps.

`cases.csv` has one task/arm/founder/recipient/draw row. Six original endpoints
are I0/P0/I1_paired/P1_paired/I1_independent/P1_independent. All success is strict
minimum of four signed responses >.25. Opposite founder rules remain separate;
`transfer` is signed and `aligned_transfer` incorporates the rule. Each fixed
contrast is after-minus-before in the order given by plan.py. The interaction
is (Pind−Iind)−(Ppaired−Ipaired), not an individual rescue indicator.

`individual_two_draw_means.csv` preserves every context and harm/gain counts.
`events.csv` retains all nonzero binary contrasts, including interaction values
of ±2; these interactions are labeled contrasts, not automatically harms or
rescues. Individual gains/harms for each direct comparison remain separate.
`erased_controls.csv` retains every measured erased record. `summary.json`
contains block means, original confidence levels, all endpoint tables, empty
conditional denominators, writer outcomes and draw recurrence.

`worker_TASK.json`, `CHECKS.json`, `COMPLETE.json`, frozen manifests and launch
receipts distinguish technical verification from the scientific criterion.
No control outcome or empty category is dropped. Scientific plots show both
endpoints and all individual gains/harms; intervals are not independent tests.
