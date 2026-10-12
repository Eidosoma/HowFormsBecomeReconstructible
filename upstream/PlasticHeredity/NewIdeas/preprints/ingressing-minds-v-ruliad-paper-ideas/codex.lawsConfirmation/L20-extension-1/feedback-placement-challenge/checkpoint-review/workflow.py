"""D175 write-once, outcome-free saved-checkpoint workflow; no simulator imports."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import measure as m
import verify as v

HERE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN = 'l20_extension1_feedback_pulse_checkpoint_v1_attempt1'
OLD = 'l20_extension1_feedback_pulse_dev_v1_attempt1'
SOURCE = ROOT / 'outputs' / OLD
OUTPUT = ROOT / 'outputs' / RUN
FREEZE = ROOT / 'tmp' / (RUN + '_freeze.json')
BENCHMARK = ROOT / 'tmp' / (RUN + '_benchmark.json')
COMPLETE = ROOT / 'runs' / RUN / 'COMPLETE.json'
AUDIT = ROOT / 'logs' / (RUN + '_audit.json')
QUALIFICATION = ROOT / 'logs' / (RUN + '_qualification_v1.xml')
CODE = ('PROTOCOL_V1.md', 'measure.py', 'verify.py', 'workflow.py', 'test_review.py')
GUIDE_SHA = '59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
PINS = {
    ROOT / 'tmp' / (OLD + '_freeze.json'): 'd0e7e0a784d19c3a42da9325c3ce129f88e7592c2cb384c5186427ce1af1a66b',
    ROOT / 'runs' / OLD / 'COMPLETE.json': '97c1a81a18a6186f4dfc3ddb22eaff81a6f707275a78fb0732ab3c188937ccea',
    ROOT / 'logs' / (OLD + '_saved_audit_v1.json'): 'ac8b1b3d7841beb9744817b6b83742d5365765d9a6217fcf0fcfe9b673840815',
    SOURCE / 'DIAGNOSTICS_SEALED.json': '2b09b9426fa1d6ad5222194245e6b97c041a8237b5a6f103fe8a37d1f536aa5f',
}


def utc(): return datetime.now(timezone.utc).isoformat()
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(paths): return {str(p): digest(p) for p in paths}
def read_json(path): return json.loads(Path(path).read_text())


def verify_hashes(pins):
    for p, h in pins.items():
        assert not Path(p).is_symlink() and digest(p) == h, str(p)


def external(path):
    path = Path(path)
    assert path.is_absolute() and ROOT in path.resolve().parents and path.name.startswith(RUN) or (
        path.is_absolute() and ROOT in path.resolve().parents and any(p.name.startswith(RUN) for p in path.parents))
    return path


def write(path, payload):
    p = external(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())


def save_json(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())


def save_npz(path, arrays):
    stream = io.BytesIO(); np.savez_compressed(stream, **arrays); write(path, stream.getvalue())


def npz(path, keys):
    with zipfile.ZipFile(path) as archive:
        assert sorted(archive.namelist()) == sorted(k+'.npy' for k in keys), 'exact NPZ schema required'
    with np.load(path, allow_pickle=False) as archive:
        return {k: archive[k] for k in keys}


def resources():
    assert set(os.sched_getaffinity(0)) <= set(range(6))
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
    assert shutil.disk_usage(ROOT).free >= 4*1024**3
    files = []
    for area in ('tmp', 'logs', 'outputs', 'runs'):
        for p in (ROOT / area).glob(RUN+'*'):
            assert not p.is_symlink()
            files.extend([p] if p.is_file() else [x for x in p.rglob('*') if x.is_file() and not x.is_symlink()])
    size = sum(p.stat().st_size for p in set(files))
    assert size < 32*1024**2, 'retain evidence; stop at allowance'
    return dict(retained_bytes=size, files=len(set(files)), maximum_cpus=6, numerical_threads=1)


def sources():
    verify_hashes(PINS)
    seal = read_json(SOURCE / 'DIAGNOSTICS_SEALED.json')
    assert seal['blocks'] == list(m.IDS) and seal['cohort'] == 'development'
    assert seal['cases'] == 256 and seal['diagnostic_cycles'] == 512
    assert not seal['actual_future_arrays_loaded']
    assert seal['freeze_sha256'] == PINS[ROOT / 'tmp' / (OLD+'_freeze.json')]
    wanted = {str(SOURCE / f'diagnostic_{i}.{ext}') for i in m.IDS for ext in ('npz', 'json')}
    assert set(seal['artifact_sha256']) == wanted
    done = read_json(ROOT / 'runs' / OLD / 'COMPLETE.json')
    assert all(done['output_sha256'][p] == h for p, h in seal['artifact_sha256'].items())
    assert read_json(ROOT / 'logs' / (OLD+'_saved_audit_v1.json'))['passes']
    verify_hashes(seal['artifact_sha256'])
    return {**{str(p): h for p, h in PINS.items()}, **seal['artifact_sha256']}


def freeze():
    resources()
    tree = ET.parse(QUALIFICATION).getroot()
    tests = tree.findall('.//testcase')
    assert len(tests) >= 20 and not any(tree.findall('.//'+k) for k in ('failure', 'error', 'skipped'))
    start = time.monotonic(); inputs = sources(); seconds = time.monotonic()-start
    code = hashes([HERE / p for p in CODE] + [QUALIFICATION])
    record = dict(schema='d175_checkpoint_freeze_v1', frozen_utc=utc(), input_sha256=inputs,
        code_sha256=code, qualification_tests=len(tests), source_hash_seconds=seconds,
        python=sys.version, numpy=np.__version__, blocks=list(m.IDS), protocol='PROTOCOL_V1.md',
        actual_outcomes_loaded=False, new_dynamics=0, new_fits=0, automatic_successor=False)
    save_json(FREEZE, record)
    return record


def frozen():
    f = read_json(FREEZE)
    verify_hashes(f['code_sha256']); verify_hashes(f['input_sha256'])
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert f['blocks'] == list(m.IDS) and not f['actual_outcomes_loaded']
    return f


def validate_meta(raw, meta, index):
    assert meta['index'] == index and meta['cohort'] == 'development'
    assert len(meta['lives']) == 4 and len(meta['proofs']) == 4
    for life, entry in enumerate(meta['lives']):
        assert entry['index'] == entry['host']['index'] == index and entry['life'] == life
        assert entry['branches'] == ['U1', 'P1'] and entry['write_times'] == list(m.TIMES)
        assert entry['cases'] == [[0, 'translated'], [0, 'aligned'], [1, 'translated'], [1, 'aligned']]
        assert entry['pulse_shift'] == [2, 1] and entry['pulse_bounds'] == [301, 400]
        assert not entry['actual_outcomes_accessed'] and not entry['diagnostic_to_lineage']
        assert entry['guide_sha256'] == GUIDE_SHA
        assert hashlib.sha256(raw['guide'][life].astype('<f8').tobytes()).hexdigest() == GUIDE_SHA
        assert meta['proofs'][life]['passes'] and meta['proofs'][life]['full_physics_replayed']
        for g in range(4):
            u, p = entry['cycles'][g]
            for section, key in (('reader', 'birth_rng'), ('reader', 'read_rng'), ('writer', 'noise_rng'),
                                 ('terminal_reader', 'birth_rng'), ('terminal_reader', 'read_rng')):
                assert u[section][key] == p[section][key]
            for a, cycle in enumerate((u, p)):
                writer = cycle['writer']
                assert writer['pulse_enabled'] == bool(a)
                assert writer['shift'] == raw['shift'][life, g, a].tolist()
                assert writer['mode'] == ('aligned' if g % 2 else 'translated')


def load_block(index, pins):
    assert type(index) is int and index in m.IDS, 'only fixed diagnostic founders'
    array, meta = (SOURCE / f'diagnostic_{index}.{ext}' for ext in ('npz', 'json'))
    assert str(array) in pins and str(meta) in pins
    verify_hashes({str(p): pins[str(p)] for p in (array, meta)})
    raw, record = npz(array, m.SHAPES), read_json(meta)
    validate_meta(raw, record, index)
    return raw


def synthetic(seed):
    """Algebra fixture, not a tissue simulation or scientific diagnostic."""
    rng = np.random.default_rng(seed)
    raw = {k: np.zeros(shape, dtype=np.uint8 if k in m.PACKETS else np.int64 if k == 'shift' else np.float64)
           for k, shape in m.SHAPES.items()}
    raw['write_states'][:] = rng.normal(size=raw['write_states'].shape)
    raw['write_states'][:, :, :, 0, 3] = 0
    raw['write_states'][:, :, 1, :3] = raw['write_states'][:, :, 0, :3]
    raw['read_states'][:, :, :, -1] = raw['write_states'][:, :, :, 0, :3]
    raw['terminal_states'][:] = rng.normal(size=raw['terminal_states'].shape)
    raw['terminal_states'][:, :, 1, 0] = raw['terminal_states'][:, :, 0, 0]
    raw['shift'][:] = rng.integers(0, 16, size=(4, 1, 1, 2))
    packet = m.project(np.tanh(raw['write_states'][..., -1, 2, :, :]))
    raw['outgoing'][:] = np.ascontiguousarray(packet.astype('<f8')).view(np.uint8).reshape(4, 4, 2, 2048)
    raw['terminal_packet'][:] = raw['outgoing']
    raw['diagnostic_features'][..., :4] = rng.normal(size=(4, 4, 2, 4))
    for g in range(4):
        raw['scores'][:, g, :, 1, g//2, 0, 0] = 1
        vfield = raw['terminal_states'][:, g, :, -1, 0]
        counts = np.mean(((vfield[:, :, None] > 0) == (m.targets()[[g//2, 1-g//2]] > 0)) &
                         (abs(vfield[:, :, None]) > .2), axis=(-2, -1))
        raw['diagnostic_features'][:, g, :, 4] = counts[..., 0]-counts[..., 1]
        raw['diagnostic_features'][:, g, :, 5] = m.rms(vfield)
    return raw


def stack(rows):
    assert len(rows) == 16 and all(set(x) == set(rows[0]) for x in rows)
    return {key: np.stack([row[key] for row in rows]) for key in rows[0]}


def benchmark():
    f = frozen(); resources(); start = time.monotonic()
    rows = []
    for i in range(16):
        raw = synthetic(17520261008+i); got = m.extract(raw); v.block(raw, got); rows.append(got)
    arrays = stack(rows); report = m.summary(arrays); proof = v.summary(arrays, report)
    directory = ROOT / 'tmp' / (RUN+'_benchmark')
    save_npz(directory / 'measurements.npz', arrays); save_json(directory / 'summary.json', report)
    back = npz(directory / 'measurements.npz', arrays)
    for key in arrays: np.testing.assert_array_equal(back[key], arrays[key])
    assert read_json(directory / 'summary.json') == m.summary(back)
    seconds = time.monotonic()-start
    result = dict(passes=True, seconds=seconds, attached_bound_seconds=4*seconds+4*f['source_hash_seconds']+30,
        freeze_sha256=digest(FREEZE), proof=proof, synthetic_only=True, outcomes_loaded=False,
        input_bytes=0, output_bytes=sum(p.stat().st_size for p in directory.iterdir()),
        resources=resources(), automatic_successor=False)
    save_json(BENCHMARK, result)
    return result


def run():
    f = frozen(); budget = read_json(BENCHMARK); resources()
    assert budget['passes'] and budget['freeze_sha256'] == digest(FREEZE)
    assert budget['attached_bound_seconds'] <= 600, 'stop: detached execution required'
    assert not OUTPUT.exists() and not COMPLETE.exists() and not AUDIT.exists()
    start = time.monotonic(); rows, proofs = [], []
    for index in m.IDS:
        raw = load_block(index, f['input_sha256']); got = m.extract(raw)
        proofs.append(dict(index=index, **v.block(raw, got))); rows.append(got)
    arrays = stack(rows); report = m.summary(arrays); proof = v.summary(arrays, report)
    save_npz(OUTPUT / 'measurements.npz', arrays); save_json(OUTPUT / 'summary.json', report)
    back = npz(OUTPUT / 'measurements.npz', arrays)
    for key in arrays: np.testing.assert_array_equal(back[key], arrays[key])
    assert read_json(OUTPUT / 'summary.json') == m.summary(back)
    inputs = f['input_sha256']; verify_hashes(inputs)
    result = dict(passes=True, completed_utc=utc(), seconds=time.monotonic()-start,
        freeze_sha256=digest(FREEZE), input_sha256=inputs,
        output_sha256=hashes(sorted(OUTPUT.iterdir())), physical_measurement_checks=proofs,
        summary_check=proof, output_bytes=sum(p.stat().st_size for p in OUTPUT.iterdir()),
        new_dynamics=0, new_fits=0, outcomes_loaded=False, automatic_successor=False)
    save_json(COMPLETE, result)
    return result


def audit():
    f = frozen(); resources(); done = read_json(COMPLETE); verify_hashes(done['output_sha256'])
    assert done['freeze_sha256'] == digest(FREEZE)
    start = time.monotonic(); arrays = npz(OUTPUT / 'measurements.npz', ('distance', 'shape_valid', 'entry', 'q', 'endpoint', 'routing'))
    proofs = []
    for b, index in enumerate(m.IDS):
        raw = load_block(index, f['input_sha256'])
        got = {k: value[b] for k, value in arrays.items()}
        proofs.append(dict(index=index, **v.block(raw, got)))
    report = read_json(OUTPUT / 'summary.json'); proof = v.summary(arrays, report)
    assert report == m.summary(arrays)
    result = dict(passes=True, completed_utc=utc(), seconds=time.monotonic()-start,
        complete_sha256=digest(COMPLETE), freeze_sha256=digest(FREEZE), checks=proofs,
        summary_check=proof, new_dynamics=0, new_fits=0, outcomes_loaded=False,
        automatic_successor=False, resources=resources())
    save_json(AUDIT, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('freeze', 'benchmark', 'run', 'audit'))
    stage = parser.parse_args().stage
    log = ROOT / 'logs' / (RUN+'_'+stage+'.log')
    external(log).parent.mkdir(parents=True, exist_ok=True)
    with log.open('x') as stream:
        try:
            result = globals()[stage]()
            stream.write(json.dumps(result, sort_keys=True, indent=2)+'\n'); stream.flush()
            print(json.dumps({k: value for k, value in result.items() if k not in
                ('input_sha256', 'code_sha256', 'output_sha256', 'physical_measurement_checks', 'checks')}, sort_keys=True))
        except Exception:
            traceback.print_exc(file=stream); stream.flush(); raise


if __name__ == '__main__': main()
