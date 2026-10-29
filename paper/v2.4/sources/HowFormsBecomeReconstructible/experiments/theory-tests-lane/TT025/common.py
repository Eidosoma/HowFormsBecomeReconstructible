"""Local frozen physics, finite packets and evidence helpers for TT025."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
SOURCE = ROOT/'source'
sys.path.insert(0, str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref

BLOCKS = tuple(range(21000000, 21000004))
DISPOSABLE = (603210, 603211)
KEYS = ('V', 'ema', 'R', 'theta')
def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(serialized(value))
def arrays(path):
    with np.load(path, allow_pickle=False) as data: return {k: data[k].copy() for k in data.files}
def identities(values):
    return {k: dict(shape=list(v.shape), dtype=str(v.dtype), sha256=digest(v.tobytes())) for k, v in values.items()}
def write_arrays(path, values):
    with Path(path).open('xb') as stream: np.savez_compressed(stream, **values)
    assert identities(arrays(path)) == identities(values)
def verify(hashes):
    for path, expected in hashes.items(): assert sha(path) == expected, path
def source_check():
    source = read_json(ROOT/'SOURCE_MANIFEST.json')
    for row in source['files']: assert sha(ROOT/row['snapshot']) == row['sha256']
    assert sha(ROOT/'physical_reference.py') == source['reference_sha256']
    return len(source['files'])
def baseline_check():
    manifest = read_json(ROOT/'BASELINE_MANIFEST.json'); verify(manifest['evidence'])
    for entry in manifest['rows'].values():
        for name, value in entry['files'].items(): assert sha(ROOT/name) == value
    return len(manifest['rows'])
def runtime_hashes():
    model.source.api()
    names = ('common.py', 'design.py', 'prepare.py', 'kernel.py', 'audit.py', 'run.py', 'analysis.py',
             'qualify.py', 'execute.py', 'resources.py', 'freeze.py', 'physical_reference.py', 'PROTOCOL.md',
             'SOURCE_MANIFEST.json', 'BASELINE_MANIFEST.json', 'RANDOMNESS.json')
    files = {ROOT/n for n in names} | {LANE/'run_python.sh'}
    files |= {ROOT/row['snapshot'] for row in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    files |= {ROOT/path for row in read_json(ROOT/'BASELINE_MANIFEST.json')['rows'].values() for path in row['files']}
    files |= {path for path in (ROOT/'intake_inputs').rglob('*') if path.is_file()}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and SOURCE in Path(path).resolve().parents: assert Path(path).resolve() in files
        if path and 'ingressing-minds-v-ruliad-paper-ideas' in str(path): raise AssertionError('live upstream import')
    return {str(p): sha(p) for p in sorted(files)}
