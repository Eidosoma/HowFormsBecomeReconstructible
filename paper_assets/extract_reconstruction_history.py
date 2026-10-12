#!/usr/bin/env python3
"""Extract one declared D140 history from retained arrays; never run a model."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / 'paper_assets/data/reconstruction-history-selection-v1.json'
DEST = ROOT / 'paper_assets/data'
SOURCE_DEFAULT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/outputs/l20_fresh_founders_v1_attempt1')
REPORT = ROOT.parent / ('PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/'
                       'codex.lawsConfirmation/reviews/L20_FRESH_FOUNDERS_2026-09-16.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_sha(array):
    return hashlib.sha256(np.asarray(array, dtype=np.uint8).tobytes()).hexdigest()


def decode(array):
    raw = np.asarray(array, dtype=np.uint8)
    if raw.shape[-1] != 2048:
        raise ValueError('Expected a 2048-byte, 16 by 16 float64 record')
    return np.frombuffer(raw.tobytes(), dtype='<f8').reshape(*raw.shape[:-1], 16, 16).copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=SOURCE_DEFAULT)
    args = parser.parse_args()
    selected = json.loads(SELECTION.read_text())['D140']
    source = args.source_root.resolve()
    block, life = selected['block'], selected['life']
    roles, arms = selected['roles'], selected['arms']
    metadata_path = source / f'block_{block}.json'
    arrays_path = source / f'block_{block}.npz'
    hashes_path = source / 'output_hashes.sha256'
    completion = source.parent.parent / 'runs' / selected['campaign'] / 'COMPLETE.json'
    complete = json.loads(completion.read_text())
    if complete['status'] != 'COMPLETE' or complete['run_id'] != selected['campaign']:
        raise ValueError('The selected archive must be the completed D140 campaign')
    if sha(hashes_path) != complete['hash_file_sha256']:
        raise ValueError('Output hash manifest does not match completion record')
    expected = {Path(line.split(maxsplit=1)[1]).name: line.split(maxsplit=1)[0]
                for line in hashes_path.read_text().splitlines() if line.strip()}
    for path in (metadata_path, arrays_path):
        if sha(path) != expected[path.name]:
            raise ValueError(f'Retained file hash mismatch: {path.name}')
    metadata = json.loads(metadata_path.read_text())
    case = metadata['lives'][life]
    assert metadata['index'] == case['index'] == block and case['life'] == life
    cases = [tuple(x) for x in case['cases']]
    probes = [tuple(x) for x in case['probes']]
    indices = [[cases.index((r, a)) for a in arms] for r in roles]
    terminal_indices = [[probes.index((r, a)) for a in arms] for r in roles]
    read_i = case['read_times'].index(300)
    write_i = case['source_times'].index(1000)
    terminal_i = case['times'].index(300)
    arrays = {}
    with np.load(arrays_path, allow_pickle=False) as raw:
        def pick(key, index=indices):
            return np.stack([np.stack([raw[key][life, i] for i in row]) for row in index])

        arrays['targets'] = raw['targets'][life, roles].copy()
        arrays['initial_packets_u8'] = raw['founder_packets'][life, roles].copy()
        for name in ('incoming', 'routed', 'outgoing'):
            arrays[name + '_packets_u8'] = pick(name)
        reads = pick('generation_read_states')
        writes = pick('generation_write_states')
        arrays['read_end_bodies'] = reads[:, :, :, read_i, 0].copy()
        arrays['writer_end_bodies'] = writes[:, :, :, write_i, 0].copy()
        arrays['writer_end_references'] = writes[:, :, :, write_i, 2].copy()
        arrays['terminal_bodies'] = pick('terminal_states', terminal_indices)[:, :, terminal_i, 0].copy()
        arrays['terminal_input_packets_u8'] = pick('terminal_inputs', terminal_indices)
        arrays['generation_shifts'] = raw['generation_shifts'][life].copy()
    arrays['initial_records'] = decode(arrays['initial_packets_u8'])
    for name in ('incoming', 'routed', 'outgoing'):
        arrays[name + '_records'] = decode(arrays[name + '_packets_u8'])
    checks, lineage = [], []
    for ri, r in enumerate(roles):
        np.testing.assert_array_equal(arrays['incoming_packets_u8'][ri, 0, 0], arrays['initial_packets_u8'][ri])
        np.testing.assert_array_equal(arrays['incoming_packets_u8'][ri, 1, 0], arrays['initial_packets_u8'][ri])
        np.testing.assert_array_equal(arrays['read_end_bodies'][ri, 0, 0], arrays['read_end_bodies'][ri, 1, 0])
        checks.append(f'Role {r}: identical F0 bytes and first read-end body in both arms')
        for ai, arm in enumerate(arms):
            ci = indices[ri][ai]
            for gi in range(3):
                incoming = arrays['incoming_packets_u8'][ri, ai, gi]
                outgoing = arrays['outgoing_packets_u8'][ri, ai, gi]
                saved = case['generations'][ci][gi]
                assert bytes_sha(incoming) == saved['input_sha256']
                assert bytes_sha(outgoing) == saved['output_sha256']
                if gi < 2:
                    np.testing.assert_array_equal(outgoing, arrays['incoming_packets_u8'][ri, ai, gi + 1])
                else:
                    np.testing.assert_array_equal(outgoing, arrays['terminal_input_packets_u8'][ri, ai])
                lineage.append({'role': r, 'arm': arm, 'generation': gi + 1,
                                'input_sha256': saved['input_sha256'], 'output_sha256': saved['output_sha256'],
                                'guide_forward_shift': saved['selector']['chosen_forward_shift'],
                                'writer_shift': saved['writer']['shift']})
            checks.append(f'Role {r}, {arm}: packet hashes match and G1/G2/G3 outputs enter the next body exactly')
    for key, value in arrays.items():
        if value.dtype.kind == 'f' and not np.isfinite(value).all():
            raise ValueError(f'Nonfinite selected values: {key}')
    DEST.mkdir(exist_ok=True)
    output = DEST / 'retained-reconstruction-history-v1.npz'
    np.savez_compressed(output, **arrays)
    paths = [arrays_path, metadata_path, hashes_path, completion, REPORT]
    record = {
        'schema': 'forms_retained_d140_history_v1', 'selection': selected,
        'selection_file': str(SELECTION.relative_to(ROOT)), 'selection_sha256': sha(SELECTION),
        'sources': [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in paths],
        'data': str(output.relative_to(ROOT)), 'data_sha256': sha(output),
        'arrays': {key: {'shape': list(a.shape), 'dtype': str(a.dtype)} for key, a in arrays.items()},
        'state_axes': {'read': ['V', 'moving_average', 'R'], 'write': ['V', 'moving_average', 'R', 'theta']},
        'read_updates': 300, 'write_updates': 1000, 'terminal_read_updates': 300,
        'record': '256 little-endian float64 values, decoded exactly; inherited record is normalized tanh(final R), not final writer theta',
        'coordinates': 'Stored coordinates, origin upper left; existing guide routing is part of the simulated dynamics, not plotting alignment',
        'selection_checks': checks, 'packet_lineage': lineage,
        'interpretation': 'Two supplied roles in one paired life, illustrative only; not an independent replication or an effect estimate',
        'extraction': 'Exact selection and packet decoding from retained arrays; no smoothing, trajectory interpolation, or model import',
        'extractor': str(Path(__file__).relative_to(ROOT)), 'extractor_sha256': sha(Path(__file__)),
        'new_simulations': 0, 'new_statistical_tests': 0,
    }
    meta_output = DEST / 'retained-reconstruction-history-v1.json'
    meta_output.write_text(json.dumps(record, indent=2) + '\n')
    print(f'Extracted D140 block {block}, life {life}, both roles and arms. {len(checks)} lineage checks passed.')
    print(f'Portable data: {output.name} ({output.stat().st_size:,} bytes). No model executed.')


if __name__ == '__main__':
    main()
