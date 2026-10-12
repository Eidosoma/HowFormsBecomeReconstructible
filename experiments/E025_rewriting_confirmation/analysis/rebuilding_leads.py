"""Post hoc description of saved record support; no new simulated trajectories."""
import csv
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, sha
import numpy as np

RUN = HERE.parent/'runs/confirmation_v1'
OUTPUT = HERE/'rebuilding_leads_v1'
CHAINS = {'baseline': 0, 'degree_compensated': 1, 'strength_compensated': 2, 'masked_copy': 5}


def decode(packets):
    assert packets.dtype == np.uint8 and packets.shape[-1] == 4096
    return np.ascontiguousarray(packets).view('<f8').reshape(*packets.shape[:-1], 2, 16, 16)


def main():
    started = time.monotonic()
    cap_cpus(1)
    check_inputs(RUN)
    complete = json.loads((RUN/'COMPLETE.json').read_text())
    audit = json.loads((RUN/'INDEPENDENT_AUDIT.json').read_text())
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert audit['complete_sha256'] == sha(RUN/'COMPLETE.json')
    output = new_run(OUTPUT, [Path(__file__), ROOT/'common.py', ROOT/'run_python.sh',
        RUN/'manifest.json', RUN/'COMPLETE.json', RUN/'INDEPENDENT_AUDIT.json', RUN/'summary.json'],
        dict(kind='post_hoc_saved_packet_description', estimated_seconds=120,
            blocks=list(range(23000, 23032)), generations=[1, 2, 3], chains=CHAINS,
            nonzero_definition='exact numerical nonzero', strong_definition='absolute weight > 0.5',
            original_sign_reference='protected original packet, not a test of task correctness',
            causal_claim=False, new_trajectories=False, workers=1, numerical_threads=1))
    rows, source_hashes = [], {}
    for block in range(23000, 23032):
        cumulative = np.ones((4, 4, 2, 16, 16), dtype=bool)
        previous_outgoing = None
        for generation in (1, 2, 3):
            path = RUN/f'boundary_{block:06d}_g{generation}.npz'
            digest = sha(path)
            assert complete['outputs_sha256'][path.name] == digest
            source_hashes[path.name] = digest
            with np.load(path, allow_pickle=False) as arrays:
                incoming, outgoing = decode(arrays['incoming']), decode(arrays['outgoing'])
                mask = arrays['renewal_mask']
            assert incoming.shape == outgoing.shape == (8, 4, 4, 2, 16, 16)
            if previous_outgoing is not None:
                np.testing.assert_array_equal(incoming, previous_outgoing)
            alive = ~mask
            current = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
            cumulative &= current
            restored_coordinates = current & ~cumulative
            original = outgoing[4]
            np.testing.assert_array_equal(outgoing[5], original*cumulative)
            assert np.count_nonzero(original) == original.size
            for name, index in CHAINS.items():
                weights = outgoing[index]
                support = weights != 0
                assert not support[~current].any()
                if name == 'masked_copy': np.testing.assert_array_equal(support, cumulative)
                for founder in range(4):
                    for lineage in range(4):
                        w, original_w = weights[founder, lineage], original[founder, lineage]
                        present = support[founder, lineage]
                        now, ever = current[founder, lineage], cumulative[founder, lineage]
                        restored = restored_coordinates[founder, lineage]
                        restored_present = restored & present
                        shared = ever & present
                        rows.append(dict(block=block, generation=generation, condition=name,
                            founder=founder, lineage=lineage, total_edges=w.size,
                            physically_available=int(now.sum()), cumulative_survivors=int(ever.sum()),
                            nonzero_edges=int(present.sum()), strong_edges=int((np.abs(w) > .5).sum()),
                            old_loss_now_available=int(restored.sum()),
                            restored_nonzero=int(restored_present.sum()),
                            restored_strong=int((restored & (np.abs(w) > .5)).sum()),
                            mean_absolute_nonzero=float(np.abs(w[present]).mean()),
                            original_sign_agreement_nonzero=float((np.sign(w[present]) == np.sign(original_w[present])).mean()),
                            original_sign_agreement_shared=float((np.sign(w[shared]) == np.sign(original_w[shared])).mean()),
                            original_sign_agreement_restored=(float((np.sign(w[restored_present]) == np.sign(original_w[restored_present])).mean())
                                if restored_present.any() else None)))
            previous_outgoing = outgoing.copy()
    with (output/'lineages.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    metrics = list(rows[0])[5:]
    groups = {}
    for generation in (1, 2, 3):
        groups[str(generation)] = {}
        for name in CHAINS:
            selected = [r for r in rows if r['generation'] == generation and r['condition'] == name]
            assert len(selected) == 512
            groups[str(generation)][name] = dict(lineages=len(selected), **{
                key: (float(np.mean([r[key] for r in selected if r[key] is not None]))
                    if any(r[key] is not None for r in selected) else None) for key in metrics})
    # Means above describe equal-size lineages, not independent observations.
    result = dict(kind='post_hoc_descriptive_no_causal_identification', generations=groups,
        rows=len(rows), independent_blocks=32, lineages_per_condition_generation=512,
        source_complete_sha256=sha(RUN/'COMPLETE.json'), source_audit_sha256=sha(RUN/'INDEPENDENT_AUDIT.json'),
        source_boundary_sha256=source_hashes, verified_saved_boundaries=len(source_hashes),
        caveats=['Exact nonzero and magnitude do not establish useful connectivity or causal benefit.',
                 'Agreement with original signs is not equivalent to correct function.',
                 'Descendants and conditions are nested within blocks; no inferential test was run.',
                 'Counterfactual terminal assays would isolate final-packet contributions, not the entire renewal mechanism.'])
    dump(output/'summary.json', result)
    check_inputs(RUN)
    finish(output, started, dict(kind='post_hoc_saved_packet_description', source_boundaries_verified=96))
    print(json.dumps(dict(seconds=time.monotonic()-started, rows=len(rows), generations=groups), indent=2))


if __name__ == '__main__':
    main()
