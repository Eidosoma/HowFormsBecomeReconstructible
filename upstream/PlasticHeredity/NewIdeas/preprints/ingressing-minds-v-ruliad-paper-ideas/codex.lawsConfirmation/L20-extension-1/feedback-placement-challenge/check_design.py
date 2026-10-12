"""D172 source/header and synthetic geometry checks only; no tissue or fitting.

Repository simulation modules are deliberately not imported. NPZ files are
hashed and their NPY headers inspected; no saved numerical array is loaded.
The optional write-once receipt is restricted to the external logs folder.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
SWAP = 'l20_extension1_address_swap_v1_attempt1'
SETTINGS = 'l20_extension1_settings_prediction_dev_v1_attempt1'
PINS = {
    f'runs/{SWAP}/COMPLETE.json': '898fd26329f89d8123abf6561ded22876e258612195d1b748d18e5df79e8dcd2',
    f'logs/{SWAP}_saved_audit_v1.json': 'f6a78b24b80bb5b1c953b234315e1457dc9cb54ca79da90565dcafafe28505fa',
    f'logs/{SWAP}_documentation_v1.json': '9ecfa1f9756422379acde4718340436a70f568d283b0664d906b4f64dbc88c54',
    f'runs/{SETTINGS}/COMPLETE.json': '41a9fa1d8d63bdcdfab971b5470ab614bf4d2b13cd3a73555a8f239130db51d4',
    f'logs/{SETTINGS}_saved_audit_v1.json': 'eb5b76b5d456fe8054a16e3de4270152158bef8f7437cae58a9f8123cae5fab2',
    f'logs/{SETTINGS}_documentation_v1.json': 'a156617c9f7f72edd45941a072936f07b8fa97325ebed45db95e06b54f47f287',
    f'tmp/{SETTINGS}_freeze.json': 'dea3c08f0de000ff827bd1d2dcc46dffab74952420a12beccb98c6bb712fed4a',
    'logs/d170_prediction_design_review_v1.json': '1c1262232c6ba7e7d40390d46da860ffc6134f28ef29b91c27a04941ee14f1d0',
}
CODE = (
    'src/laws_confirmation/l20_guide_renewal.py',
    'src/laws_confirmation/l20_learned_guide.py',
    *(f'L20-extension-1/src/l20_extension1/{name}.py' for name in (
        'diagnostics', 'heldout_diagnostics', 'pilot_diagnostics',
        'recovery_features', 'difference_ablation', 'group_models',
        'passive_feedback', 'address_swap', 'address_swap_check')),
)
HEADERS = {
    'founder_packets': ((4, 2, 2048), 'uint8'),
    'guide': ((4, 2, 16, 16), 'float64'),
    'input': ((4, 4, 3, 2048), 'uint8'),
    'routed': ((4, 4, 3, 2048), 'uint8'),
    'read_states': ((4, 4, 3, 5, 3, 16, 16), 'float64'),
    'write_states': ((4, 4, 3, 4, 4, 16, 16), 'float64'),
    'terminal_states': ((4, 4, 3, 4, 3, 16, 16), 'float64'),
    'diagnostic_features': ((4, 4, 3, 6), 'float64'),
    'initial_features': ((4, 4, 4), 'float64'),
    'shift': ((4, 4, 3, 2), 'int64'),
}
CASES = [[0, 'translated'], [0, 'aligned'], [1, 'translated'], [1, 'aligned']]


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def bind(path, expected, used):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or sha(path) != expected:
        raise ValueError('missing, changed or symlinked source: ' + str(path))
    key = str(path.resolve())
    if key in used and used[key] != expected:
        raise ValueError('conflicting source digest: ' + key)
    used[key] = expected


def merge(target, source):
    for path, digest in source.items():
        if path in target and target[path] != digest:
            raise ValueError('conflicting historical digest: ' + path)
        target[path] = digest


def source_headers(path):
    with zipfile.ZipFile(path) as archive:
        for key, (shape, dtype) in HEADERS.items():
            with archive.open(key + '.npy') as handle:
                version = np.lib.format.read_magic(handle)
                if version == (1, 0):
                    found = np.lib.format.read_array_header_1_0(handle)
                elif version == (2, 0):
                    found = np.lib.format.read_array_header_2_0(handle)
                else:
                    raise ValueError('unexpected array header version')
            assert found[0] == shape and found[1] is False
            assert found[2] == np.dtype(dtype) and not found[2].hasobject
    return len(HEADERS)


def metadata(meta, index, disposable=False):
    assert meta['index'] == index and len(meta['lives']) == 4
    tag = 'l20-extension1-' + ('pilot64' if disposable else 'heldout')
    tag += '-v1:diagnostics:' + ('disposable' if disposable else 'heldout')
    comparisons = 0
    for life, row in enumerate(meta['lives']):
        assert (row['index'], row['life'], row['host']['index']) == (index, life, index)
        assert row['tag'] == tag and row['cases'] == CASES
        assert row['branches'] == ['U0', 'U1', 'C1']
        assert not row['diagnostic_to_lineage'] and not row['predictor_has_parent_state']
        assert row['config']['source_steps'] == 1000 and row['config']['steps'] == 300
        assert row['config']['lam'] == .001 and row['config']['norm'] == .3
        for group, cells in enumerate(row['cycles']):
            u0, u1, _ = cells
            assert u0['trial'] == 0 and u1['trial'] == 1
            assert u1['mode'] == CASES[group][1]
            assert u1['writer']['theta_start_zero']
            assert not u1['writer']['incoming_packet_access']
            assert not u1['writer']['guide_access'] and not u1['writer']['target_labels']
            for section, key in (('reader', 'birth_rng'), ('reader', 'read_rng'),
                                 ('writer', 'noise_rng'), ('terminal_reader', 'birth_rng'),
                                 ('terminal_reader', 'read_rng')):
                assert u0[section][key] != u1[section][key]
                comparisons += 1
    return comparisons


def gather(field, shift):
    rows, columns = np.indices((16, 16))
    return field[(rows - shift[0]) % 16, (columns - shift[1]) % 16]


def synthetic():
    """Finite array identities, not a mock tissue simulation or fitted model."""
    y, x = np.indices((16, 16))
    targets = (np.where(y < 8, 1., -1.), np.where(x % 8 < 4, 1., -1.))
    pulse = (2, 1)
    active = [step for step in range(1, 1001) if 301 <= step <= 400]
    assert active == list(range(301, 401)) and len(active) == 100
    assert 1000 - active[-1] == 600
    field = (np.arange(256).reshape(16, 16) - 128).astype(float)
    rolled = np.roll(field, pulse, (0, 1))
    np.testing.assert_array_equal(rolled, gather(field, pulse))
    np.testing.assert_array_equal(np.sort(rolled.ravel()), np.sort(field.ravel()))
    assert np.sum(rolled) == np.sum(field) and np.sum(rolled**2) == np.sum(field**2)
    assert not np.array_equal(rolled, field)
    for invariant in (np.zeros((16, 16)), np.ones((16, 16))):
        np.testing.assert_array_equal(gather(invariant, pulse), invariant)
    geometric = boundary = 0
    for code in range(256):  # Include identity to check aligned/effective-zero cases.
        shift = divmod(code, 16)
        for target in targets:
            original = gather(target, shift)
            displaced = gather(original, pulse)
            assert np.mean(original * displaced) == .5
            assert np.mean((displaced - original)**2) == 1.
            geometric += 1
        for mode in ('translated', 'aligned'):
            effective = shift if mode == 'translated' else (0, 0)
            base = np.roll(field, effective, (0, 1))
            for step in (1, 300, 301, 400, 401, 1000):
                value = np.roll(base, pulse, (0, 1)) if 301 <= step <= 400 else base
                expected_shift = tuple((s + d) % 16 for s, d in zip(effective, pulse)) if step in (301, 400) else effective
                np.testing.assert_array_equal(value, gather(field, expected_shift))
                boundary += 1
            np.testing.assert_array_equal(np.roll(base, (0, 0), (0, 1)), base)
    return dict(ideal_template_shift_checks=geometric, mapping_boundary_checks=boundary,
                schedule_steps_checked=1000, pulse_steps=100, recovery_steps=600,
                pulse_shift=list(pulse), synthetic_geometry_only=True,
                actual_or_synthetic_tissue_steps=0, model_fits=0)


def review():
    used, expected = {}, {}
    for rel, digest in PINS.items():
        bind(ROOT / rel, digest, used)
    for name in (SWAP, SETTINGS):
        done = read(ROOT / 'runs' / name / 'COMPLETE.json')
        assert done['status'] == 'COMPLETE'
        path = ROOT / 'runs' / name / 'MANIFEST.json'
        bind(path, done['manifest_sha256'], used)
        merge(expected, read(path)['input_sha256'])
        audit = read(ROOT / 'logs' / (name + '_saved_audit_v1.json'))
        assert audit['passes'] and audit['complete_sha256'] == PINS[f'runs/{name}/COMPLETE.json']
        docs = read(ROOT / 'logs' / (name + '_documentation_v1.json'))
        assert docs['passes'] and docs['complete_sha256'] == PINS[f'runs/{name}/COMPLETE.json']
        merge(expected, docs['documentation_sha256'])
    merge(expected, read(ROOT / 'tmp' / (SETTINGS + '_freeze.json'))['input_sha256'])
    old_review = read(ROOT / 'logs/d170_prediction_design_review_v1.json')
    assert old_review['passes'] and old_review['new_dynamics'] == 0
    merge(expected, old_review['source_sha256'])
    for rel in (*CODE, 'L20-extension-1/address-swap/RESULTS.md',
                'L20-extension-1/address-aware-prediction/RESULTS.md'):
        path = WS / rel
        bind(path, expected[str(path)], used)
    headers = stream_comparisons = 0
    for index in (*range(90000, 90016), 514240):
        disposable = index == 514240
        folder = ROOT / ('tmp/l20_extension1_pilot64_v1_attempt1_benchmark' if disposable
                         else 'outputs/l20_extension1_heldout_v1_attempt1')
        npz, meta = (folder / f'diagnostic_{index}{suffix}' for suffix in ('.npz', '.json'))
        for path in (npz, meta):
            bind(path, expected[str(path)], used)
        headers += source_headers(npz)
        stream_comparisons += metadata(read(meta), index, disposable)
    # This legacy checker is inspected and newly bound, not falsely claimed
    # to appear in the shorter previously pinned consumed-input manifests.
    inspected = WS / 'scripts/audit_l20_guide_renewal_outputs.py'
    assert inspected.is_file() and not inspected.is_symlink()
    inspected_hash = {str(inspected): sha(inspected)}
    proofs = synthetic()
    links, documents = [], [HERE / name for name in (
        'README.md', 'DESIGN_REVIEW.md', 'PROPOSAL_V1.md', 'WORKLOG.md', 'check_design.py')]
    for path in documents:
        if path.suffix != '.md':
            continue
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent / link.split('#')[0]).resolve().is_file(), (path, link)
                links.append([str(path), link])
    for path, digest in used.items():
        assert sha(path) == digest
    assert sha(inspected) == inspected_hash[str(inspected)]
    return dict(status='DESIGN_CHECKED_NOT_QUALIFIED_FOR_EXECUTION', passes=True,
                sources_checked=len(used), source_sha256=used,
                newly_bound_inspected_source_sha256=inspected_hash,
                metadata_blocks=17, development_founders=16, development_cases=256,
                disposable_blocks=1, array_headers_checked=headers,
                independent_U0_U1_stream_fingerprints=stream_comparisons,
                synthetic=proofs, local_links_checked=len(links),
                documentation_sha256={str(p): sha(p) for p in documents
                                      if p.name not in ('README.md', 'WORKLOG.md')},
                proposed_counts=dict(new_pulsed_cycles=256, reproduced_U1_cycles=256,
                    production_cycles=512, independent_replay_cycles=512,
                    new_model_fits=48, new_out_of_fold_forecasts=768),
                saved_numerical_arrays_loaded=0, actual_outcome_arrays_loaded=0,
                new_dynamics=0, new_fits=0, new_forecasts=0, new_founders=0,
                physics_replayed=False, prospective_evidence=False,
                execution_authorized=False, automatic_successor=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if args.receipt:
        # Validate before work, then create exclusively; never overwrite evidence.
        path = args.receipt
        if path.parent.resolve() != (ROOT / 'logs').resolve() or path.suffix != '.json':
            raise ValueError('receipt must be a JSON file in the external logs folder')
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)
    started = time.monotonic()
    result = review()
    result.update(checked_utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic() - started)
    if args.receipt:
        with args.receipt.open('x') as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
