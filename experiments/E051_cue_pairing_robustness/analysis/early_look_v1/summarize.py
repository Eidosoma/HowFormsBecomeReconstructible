"""Requested descriptive look at the first eight completed E051 blocks.

Does not replay dynamics, compute inferential gates, or alter the running study.
Writes only a new receipt in this analysis directory; refuses to overwrite it.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'E051_cue_pairing_robustness/runs/robustness_v1'
BLOCKS = list(range(34000, 34008))
HORIZONS = (0, 8, 16, 24, 32)
INJURIES = ('intact', 'scattered', 'square')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def main():
    assert not (HERE / 'snapshot.json').exists()
    started = datetime.now(timezone.utc).isoformat()
    manifest = json.loads((RUN / 'manifest.json').read_text())
    contract = manifest['contract']
    assert contract['blocks'][:8] == BLOCKS
    assert contract['config']['founders'] == contract['config']['recipients'] == 4
    assert contract['config']['margin'] == .25
    assert contract['mode'] == 'scientific'
    conditions = contract['conditions']
    assert len(conditions) == 35
    for rel, expected in manifest['inputs_sha256'].items():
        assert digest(ROOT / rel) == digest(RUN / 'inputs' / rel) == expected, rel
    hashes = {}
    data = []
    for block in BLOCKS:
        worker = RUN / f'worker_{block}.json'
        assert json.loads(worker.read_text())['generations'] == 32
        source_path = RUN / f'source_{block:06d}.npz'
        assert digest(source_path) == json.loads(worker.read_text())['source_sha256']
        source = arrays(source_path)
        target = (source['rules'][None, :, None, None, None]
                  * source['cues'][None, None, None, :, None])
        case_path = RUN / f'cases_{block:06d}.npz'
        case = arrays(case_path)
        for path in (worker, source_path, case_path):
            hashes[str(path.relative_to(ROOT))] = digest(path)
        for horizon in HORIZONS:
            path = RUN / f'assay_{block:06d}_h{horizon}.npz'
            raw = arrays(path)
            metadata = json.loads(raw['__index__'].tobytes())
            assert metadata['kind'] == 'assay'
            ports = raw['mean_ports']
            entry = metadata['arrays']['mean_ports']
            assert list(ports.shape) == entry['shape'] and ports.dtype.str == entry['dtype']
            assert hashlib.sha256(ports.tobytes()).hexdigest() == entry['sha256']
            assert np.isfinite(ports).all()
            margin = np.minimum(target * ports[..., 0], -target * ports[..., 1])
            np.testing.assert_array_equal(margin > .25, case[f'assay_h{horizon}_correct'])
            np.testing.assert_array_equal(margin, case[f'assay_h{horizon}_margin'])
            np.testing.assert_array_equal(ports, case[f'assay_h{horizon}_ports'])
            hashes[str(path.relative_to(ROOT))] = digest(path)
        data.append(case)
    results = {}
    for horizon in HORIZONS:
        names = ['initial', 'erased'] if horizon == 0 else [*conditions, 'erased']
        for index, name in enumerate(names):
            for injury_index, injury in enumerate(INJURIES):
                per_block = [int(d[f'assay_h{horizon}_correct'][index, :, :, :, injury_index]
                                 .all(axis=2).sum()) for d in data]
                results[f'assay/{horizon}/{name}/{injury}'] = dict(
                    successes=sum(per_block), total=128,
                    percent=100 * sum(per_block) / 128, successes_by_block=per_block)
    mechanism = {}
    for index, name in enumerate(conditions):
        counts = np.array([d['counts'][1:, index].sum(axis=(0, 1, 2)) for d in data])
        sums = np.array([d['sums'][1:, index].sum(axis=(0, 1, 2)) for d in data])
        assert (counts[:, 3] > 0).all() and (counts[:, 10] > 0).all()
        rates = {
            'exact_zero_returning': counts[:, 4] / counts[:, 3],
            'ordinary_selected_returning': counts[:, 5] / counts[:, 3],
            'nonzero_returning': counts[:, 6] / counts[:, 3],
            'returning_reachable_after': counts[:, 12] / counts[:, 10],
            'mean_abs_returning_weight': sums[:, 0] / counts[:, 3],
            'mean_abs_returning_contrast': sums[:, 1] / counts[:, 3],
        }
        mechanism[name] = {k: dict(mean=float(v.mean()), block_values=v.tolist())
                           for k, v in rates.items()}
    snapshot = dict(
        status='DESCRIPTIVE_INTERIM_UNAUDITED', experiment='E051', run=str(RUN.relative_to(ROOT)),
        requested_look_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
        cohort_rule='First scheduled batch, all eight blocks completed; selected before reading outcomes.',
        blocks=BLOCKS, planned_blocks=32, lineages_per_condition=128, planned_lineages_per_condition=512,
        independent_unit='block', primary_decision=None, confidence_intervals_computed=False,
        dynamics_replayed=False, protocol_or_run_changed=False,
        checks=dict(original_and_frozen_input_hashes=len(manifest['inputs_sha256']),
                    all_selected_workers_complete=True, assay_arrays_rescored=40,
                    mean_port_commitments_match=True, exported_scores_match=True),
        caveats=['Incomplete first batch; descriptive counts are not the final inferential result.',
                 'The independent full trajectory audit has not been completed.',
                 'Only rebuilding cue pairing is changed; teaching and terminal assays remain paired.',
                 'Diagnostics are descriptive and do not establish a causal explanation.',
                 'No interim stopping, tuning, or sample-size change.'],
        results=results, mechanism=mechanism, read_file_sha256=hashes,
        script_sha256=digest(Path(__file__)))
    with (HERE / 'snapshot.json').open('x') as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps(snapshot['checks'], sort_keys=True))
    for pairing, _, _ in contract['pairings']:
        values = [results[f'assay/32/{pairing}/{writer}/scattered']['successes']
                  for writer in contract['writers']]
        print(pairing, dict(zip(contract['writers'], values)))
    print('All counts out of 128; no final decision or confidence intervals computed.')


if __name__ == '__main__':
    main()
