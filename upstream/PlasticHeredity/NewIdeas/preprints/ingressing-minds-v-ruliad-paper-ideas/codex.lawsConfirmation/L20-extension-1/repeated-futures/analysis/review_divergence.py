"""Saved D142 stage measurements only: no dynamics or fitted predictors."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import time
import xml.etree.ElementTree as ET

import numpy as np

BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_repeated_futures_v1_attempt1'
SOURCE = BASE / 'outputs' / RUN
COMPLETE = BASE / 'runs' / RUN / 'COMPLETE.json'
COMPLETE_SHA = 'a04ec3a673e4794ecad5c6662891c30b74ab2e76a2731897b8efc7568416ad72'
DEST = BASE / 'analyses/d142_saved_divergence_v1'
BLOCKS = tuple(range(90000, 90016))
GROUPS = ('A_translated', 'A_aligned', 'B_translated', 'B_aligned')
KEYS = ('read_preference', 'read_shape', 'write_preference', 'write_shape',
        'terminal_preference', 'terminal_shape', 'phase_shape', 'guide_family')
READ_TIMES, WRITE_TIMES, TERMINAL_TIMES = (0, 1, 100, 101, 300), (0, 1, 300, 1000), (0, 1, 100, 300)
PHASES = ('incoming', 'routed', 'read_end_R', 'write_end_R', 'outgoing')
SEGMENTS = ('routing', 'reading_reference', 'writing_reference', 'record_construction')
YY, XX = np.indices((16, 16))
TARGETS = np.stack((np.where(YY < 8, 1., -1.), np.where(XX % 8 < 4, 1., -1.)))
BANK = np.stack([[np.roll(t, divmod(i, 16), (0, 1)) for i in range(256)] for t in TARGETS])
SCIENCE = tuple(Path(__file__).with_name(n) for n in
                ('SCOPE_V1.md', 'review_divergence.py', 'audit_divergence.py', 'test_divergence.py'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    with Path(path).open('x') as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())


def write_npz(path, data):
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **data)
        f.flush(); os.fsync(f.fileno())


def verify_sources():
    if sha(COMPLETE) != COMPLETE_SHA:
        raise ValueError('D142 COMPLETE changed')
    receipt = read_json(COMPLETE)
    assert receipt['status'] == 'COMPLETE' and receipt['run_id'] == RUN
    outputs = receipt['output_sha256']
    assert len(outputs) == 36 and sha(SOURCE/'output_hashes.sha256') == receipt['hash_file_sha256']
    for name, wanted in outputs.items():
        path = Path(name)
        assert path.parent.resolve() == SOURCE.resolve()
        if sha(path) != wanted:
            raise ValueError(f'sealed D142 output changed: {path.name}')
    inputs = {}
    for row in (SOURCE/'input_hashes.sha256').read_text().splitlines():
        wanted, name = row.split(maxsplit=1)
        path = Path(name.lstrip('*'))
        assert path.is_absolute() and str(path) not in inputs
        if sha(path) != wanted:
            raise ValueError(f'frozen D142 input changed: {path}')
        inputs[str(path)] = wanted
    assert len(inputs) == 1265
    return dict(source_complete_sha256=COMPLETE_SHA, source_output_sha256=outputs,
                source_hash_index_sha256=receipt['hash_file_sha256'], source_input_hashes=1265)


def fields(value):
    a = np.asarray(value)
    if a.shape[-2:] != (16, 16) or not np.isfinite(a).all():
        raise ValueError('finite 16-by-16 fields required')
    return a


def decode(packets):
    a = np.asarray(packets)
    if a.shape[-1] != 2048 or a.dtype != np.uint8:
        raise ValueError('ordinary 2048-byte records required')
    return fields(np.ascontiguousarray(a).view('<f8').reshape(*a.shape[:-1], 16, 16))


def best(a, role):
    if role not in (0, 1):
        raise ValueError('target family required')
    a = fields(a)
    centered = a-a.mean(axis=(-2, -1), keepdims=True)
    scale = np.sqrt(np.mean(centered**2, axis=(-2, -1)))
    scores = np.einsum('...ij,sij->...s', centered, BANK[role], optimize=False).max(axis=-1)
    result = np.zeros_like(scale, dtype=float)
    np.divide(scores, 256*scale, out=result, where=scale > 0)
    return result


def preference(a, role):
    if role not in (0, 1):
        raise ValueError('target family required')
    a = fields(a)
    active = abs(a) > .2
    own = (a > 0) == (TARGETS[role] > 0)
    other = (a > 0) == (TARGETS[1-role] > 0)
    return (np.count_nonzero(own & active, axis=(-2, -1))-
            np.count_nonzero(other & active, axis=(-2, -1)))/256


def load_block(index):
    if index not in BLOCKS:
        raise ValueError('existing complete cohort only')
    with np.load(SOURCE/f'block_{index}.npz', allow_pickle=False) as f:
        raw = {k: f[k] for k in f.files}
    meta = read_json(SOURCE/f'block_{index}.json')
    return raw, meta


def measure_block(raw, meta):
    assert meta['index'] in BLOCKS and len(meta['lives']) == 4
    assert meta['config']['steps'] == 300 and meta['config']['source_steps'] == 1000
    assert meta['config']['rescue_after'] == 100 and meta['config']['amp_threshold'] == .2
    for life in range(4):
        assert len(meta['lives'][life]) == 4
        for future in range(4):
            entry = meta['lives'][life][future]
            assert (entry['index'], entry['life'], entry['future']) == (meta['index'], life, future)
            assert entry['cases'] == [[0, 'translated'], [0, 'aligned'], [1, 'translated'], [1, 'aligned']]
            assert entry['namespace'] == f'l20-extension1-repeated-futures-v1:future{future}'
            assert entry['replay']['full_dynamics_replayed'] is True
            np.testing.assert_array_equal(raw['targets'][life, future], TARGETS)
            np.testing.assert_array_equal(raw['founder_packets'][life, future], raw['founder_packets'][life, 0])
    assert raw['read_states'].shape == (4, 4, 4, 3, 5, 3, 16, 16)
    assert raw['write_states'].shape == (4, 4, 4, 3, 4, 4, 16, 16)
    assert raw['terminal_states'].shape == (4, 4, 4, 4, 3, 16, 16)
    np.testing.assert_array_equal(raw['write_states'][..., 0, :3, :, :], raw['read_states'][..., -1, :, :, :])
    assert not np.count_nonzero(raw['write_states'][..., 0, 3, :, :])
    np.testing.assert_array_equal(raw['incoming'][..., 1:, :], raw['outgoing'][..., :-1, :])
    np.testing.assert_array_equal(raw['terminal_input'], raw['outgoing'][..., -1, :])
    for role in (0, 1):
        for ci in (2*role, 2*role+1):
            np.testing.assert_array_equal(raw['incoming'][:, :, ci, 0], raw['founder_packets'][:, :, role])
        np.testing.assert_array_equal(raw['read_states'][:, :, 2*role, 0], raw['read_states'][:, :, 2*role+1, 0])
        np.testing.assert_array_equal(raw['write_states'][:, :, 2*role, 0, :2], raw['write_states'][:, :, 2*role+1, 0, :2])
    result = {}
    for prefix in ('read', 'write', 'terminal'):
        states = raw[prefix+'_states']
        result[prefix+'_preference'] = np.stack([preference(states[:, :, c, ..., 0, :, :], c//2) for c in range(4)], axis=2)
        result[prefix+'_shape'] = np.stack([best(states[:, :, c, ..., 2, :, :], c//2) for c in range(4)], axis=2)
    result['phase_shape'] = np.stack([
        np.stack([best(decode(raw['incoming'][:, :, c]), c//2), best(decode(raw['routed'][:, :, c]), c//2),
                  result['read_shape'][:, :, c, :, -1], result['write_shape'][:, :, c, :, -1],
                  best(decode(raw['outgoing'][:, :, c]), c//2)], axis=-1) for c in range(4)], axis=2)
    result['guide_family'] = np.array([[[[p['selector']['inferred_family'] if p['selector']['inferred_family'] is not None else -1
        for p in entry['paths'][c]['generations']+[entry['paths'][c]['terminal']]] for c in range(4)]
        for entry in life] for life in meta['lives']], dtype=np.int64)
    for prefix, saved in (('read', 'values'), ('terminal', 'terminal_values')):
        np.testing.assert_array_equal(result[prefix+'_preference'], raw[saved][..., 0]-raw[saved][..., 1])
    assert set(result) == set(KEYS)
    for a in result.values():
        assert a.shape[:3] == (4, 4, 4) and np.isfinite(a).all()
    return result


def profile(y, counts=False):
    y = np.asarray(y, float)
    if y.shape[:3] != (16, 4, 4) or not np.isfinite(y).all():
        raise ValueError('16 blocks, four lives, four finite futures required')
    means, variances = y.mean(axis=2), y.var(axis=2, ddof=1)
    result = dict(mean=means.mean(axis=(0, 1)).tolist(), within_pair_variance=variances.mean(axis=(0, 1)).tolist(),
                  block_mean=means.mean(axis=1).tolist(), block_within_pair_variance=variances.mean(axis=1).tolist())
    if counts:
        result.update(negative_count=(y < 0).sum(axis=(0, 1, 2)).tolist(), zero_count=(y == 0).sum(axis=(0, 1, 2)).tolist())
    return result


def decomposition(y):
    if np.shape(y) != (16, 4, 4, 3, 5) or not np.isfinite(y).all():
        raise ValueError('complete three-generation five-phase panel required')
    x, z = y[..., :-1], y[..., 1:]
    d = z-x
    wx, wz, wd = (a.var(axis=2, ddof=1) for a in (x, z, d))
    covariance = ((x-x.mean(axis=2, keepdims=True))*(d-d.mean(axis=2, keepdims=True))).sum(axis=2)/3
    np.testing.assert_allclose(wz-wx, wd+2*covariance, atol=1e-12, rtol=0)
    np.testing.assert_allclose(d.sum(axis=-1), y[..., -1]-y[..., 0], atol=1e-12, rtol=0)
    np.testing.assert_allclose((wz-wx).sum(axis=-1), y[..., -1].var(axis=2, ddof=1)-y[..., 0].var(axis=2, ddof=1), atol=1e-12, rtol=0)
    avg = lambda a: a.mean(axis=(0, 1)).tolist()
    return dict(mean_change=d.mean(axis=(0, 1, 2)).tolist(), within_before=avg(wx), within_after=avg(wz),
        within_change=avg(wz-wx), within_increment=avg(wd), twice_covariance=avg(2*covariance),
        pairs_spread_decreased=((wz-wx) < -1e-12).sum(axis=(0, 1)).tolist(),
        futures_fidelity_decreased=(d < -1e-12).sum(axis=(0, 1, 2)).tolist(),
        max_identity_error=float(np.max(abs((wz-wx)-(wd+2*covariance)))))


def summarize(data):
    assert set(data) == set(KEYS) and all(a.shape[:4] == (16, 4, 4, 4) for a in data.values())
    groups, moments = {}, {}
    for ci, name in enumerate(GROUPS):
        p = {k: a[:, :, :, ci] for k, a in data.items()}
        p['reader_endpoints'] = np.concatenate((p['read_preference'][..., -1], p['terminal_preference'][..., -1, None]), axis=-1)
        p['record_endpoints'] = np.concatenate((p['phase_shape'][..., 0, 0, None], p['phase_shape'][..., -1]), axis=-1)
        p['read_endpoint_increments'] = np.diff(p['reader_endpoints'], axis=-1)
        metrics = {k: profile(a, 'preference' in k or k in ('reader_endpoints', 'read_endpoint_increments'))
                   for k, a in p.items() if k != 'guide_family'}
        for k, a in p.items():
            if k != 'guide_family':
                moments[f'{name}__{k}__mean'] = a.mean(axis=2)
                moments[f'{name}__{k}__variance'] = a.var(axis=2, ddof=1)
        groups[name] = dict(metrics=metrics, phase_decomposition=decomposition(p['phase_shape']),
            non_own_guide_counts=(p['guide_family'] != ci//2).sum(axis=(0, 1, 2)).tolist())
    matched = {}
    for role in (0, 1):
        matched['AB'[role]] = {}
        for key in KEYS[:-1]:
            x, y = data[key][:, :, :, 2*role], data[key][:, :, :, 2*role+1]
            matched['AB'[role]][key] = dict(mean_aligned_minus_ordinary=(y-x).mean(axis=(0, 1, 2)).tolist(),
                within_variance_aligned_minus_ordinary=(y.var(axis=2, ddof=1)-x.var(axis=2, ddof=1)).mean(axis=(0, 1)).tolist())
    return dict(schema='d142_saved_divergence_v1', scientific_status='POST_RESULT_EXPLORATORY_DESCRIPTION',
        independent_blocks=16, cases=256, futures=1024, new_dynamics=0, refitted_models=0,
        excluded_cases=0, read_times=list(READ_TIMES), write_times=list(WRITE_TIMES), terminal_times=list(TERMINAL_TIMES),
        phases=list(PHASES), segments=list(SEGMENTS), groups=groups, matched_writers=matched,
        no_new_intervals=True, no_causal_phase_allocation=True, primary_results_unchanged=True), moments


def check_endpoints(summary):
    old = read_json(SOURCE/'summary.json')
    for name, group in summary['groups'].items():
        m = group['metrics']; previous = old['groups'][name]
        np.testing.assert_allclose(m['reader_endpoints']['mean'], previous['mean_preference_G1_G4'], atol=1e-14, rtol=0)
        assert m['reader_endpoints']['negative_count'] == previous['negative_preference_G1_G4']
        assert group['non_own_guide_counts'] == previous['non_own_guide_G1_G4']
        np.testing.assert_allclose(m['record_endpoints']['mean'], previous['mean_record_best_F0_F3'], atol=1e-12, rtol=0)
        assert abs(m['reader_endpoints']['within_pair_variance'][-1]-previous['primary']['within_future_variance']['estimate']) < 1e-14


def resources():
    assert not os.environ.get('PYTHONPYCACHEPREFIX')
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
    assert set(os.sched_getaffinity(0)) <= set(range(6))
    assert shutil.disk_usage(BASE).free >= 4*1024**3+128*1024**2


def analysis_hashes():
    return {str(p.resolve()): sha(p) for p in SCIENCE}


def freeze(report):
    resources()
    report = Path(report).resolve()
    assert report.is_relative_to(BASE.resolve())
    tests = list(ET.parse(report).getroot().iter('testcase'))
    assert len(tests) >= 20 and len({(t.get('classname'), t.get('name')) for t in tests}) == len(tests)
    assert not any(t.find(k) is not None for t in tests for k in ('failure', 'error', 'skipped'))
    source = verify_sources()
    manifest = dict(frozen_utc=datetime.now(timezone.utc).isoformat(), analysis_inputs=analysis_hashes(),
        qualification_report=str(report), qualification_sha256=sha(report), qualification_tests=len(tests),
        source=source, numerical_workers=1, numerical_threads=1, python=platform.python_version(), numpy=np.__version__)
    DEST.mkdir(parents=True, exist_ok=False)
    write_json(DEST/'FREEZE.json', manifest)
    return dict(status='FROZEN', destination=str(DEST), tests=len(tests), freeze_sha256=sha(DEST/'FREEZE.json'))


def frozen():
    f = read_json(DEST/'FREEZE.json')
    assert f['analysis_inputs'] == analysis_hashes()
    assert sha(f['qualification_report']) == f['qualification_sha256']
    assert (f['python'], f['numpy']) == (platform.python_version(), np.__version__)
    return f


def benchmark():
    import audit_divergence as audit
    resources(); f = frozen()
    assert set(p.name for p in DEST.iterdir()) == {'FREEZE.json'}
    began = time.monotonic(); assert verify_sources() == f['source']
    hash_seconds = time.monotonic()-began
    began = time.monotonic()
    raw, meta = load_block(BLOCKS[0]); measured = measure_block(raw, meta)
    proof = audit.check_block(raw, meta, measured)
    seconds = time.monotonic()-began
    # Includes two full checked extraction passes, then hash/summary/I/O allowance.
    forecast = 32*seconds+4*hash_seconds+120
    timing = dict(status='COMPLETE', block=BLOCKS[0], checked_block_seconds=seconds,
        source_hash_seconds=hash_seconds, conservative_full_seconds=forecast, new_dynamics=0,
        output_allowance_bytes=128*1024**2, proof=proof, freeze_sha256=sha(DEST/'FREEZE.json'),
        completed_utc=datetime.now(timezone.utc).isoformat())
    write_json(DEST/'benchmark.json', timing)
    return timing


def execute():
    import audit_divergence as audit
    resources(); f = frozen(); timing = read_json(DEST/'benchmark.json')
    assert timing['freeze_sha256'] == sha(DEST/'FREEZE.json')
    assert timing['conservative_full_seconds'] <= 600, 'Detach separately if forecast exceeds ten minutes; do not run foreground'
    assert set(p.name for p in DEST.iterdir()) == {'FREEZE.json', 'benchmark.json'}
    began = time.monotonic()
    write_json(DEST/'STARTED.json', dict(started_utc=datetime.now(timezone.utc).isoformat(),
        freeze_sha256=sha(DEST/'FREEZE.json'), benchmark_sha256=sha(DEST/'benchmark.json'), automatic_retry=False))
    try:
        assert verify_sources() == f['source']
        blocks, proofs = [], []
        for index in BLOCKS:
            raw, meta = load_block(index); data = measure_block(raw, meta)
            proofs.append(dict(block=index, **audit.check_block(raw, meta, data)))
            blocks.append(data)
        all_data = {k: np.stack([b[k] for b in blocks]) for k in KEYS}
        summary, moments = summarize(all_data); check_endpoints(summary)
        audit.check_summary(all_data, summary, moments)
        assert verify_sources() == f['source'] and f == frozen()
        write_npz(DEST/'measurements.npz', all_data); write_npz(DEST/'pair_moments.npz', moments)
        write_json(DEST/'summary.json', summary)
        write_json(DEST/'verification.json', dict(passes=True, blocks=proofs, new_dynamics=0,
            independent_statistics=True, endpoints_match_D142=True, source_verified_before_after=True))
        names = ('FREEZE.json', 'benchmark.json', 'STARTED.json', 'measurements.npz', 'pair_moments.npz', 'summary.json', 'verification.json')
        receipt = dict(status='COMPLETE', completed_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic()-began, output_bytes=sum((DEST/n).stat().st_size for n in names),
            output_sha256={n: sha(DEST/n) for n in names}, source_complete_sha256=COMPLETE_SHA,
            cases=256, futures=1024, new_dynamics=0, automatic_successor=False)
        write_json(DEST/'COMPLETE.json', receipt)
        return dict(destination=str(DEST), **receipt)
    except Exception as e:
        write_json(DEST/'FAILED.json', dict(failed_utc=datetime.now(timezone.utc).isoformat(),
            error_type=type(e).__name__, error=str(e), automatic_retry=False))
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--freeze', metavar='QUALIFICATION_XML'); g.add_argument('--benchmark', action='store_true')
    g.add_argument('--execute', action='store_true')
    args = p.parse_args()
    result = freeze(args.freeze) if args.freeze else benchmark() if args.benchmark else execute()
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
