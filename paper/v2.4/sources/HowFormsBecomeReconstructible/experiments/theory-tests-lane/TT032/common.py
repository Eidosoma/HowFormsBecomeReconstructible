"""Local physical sources and strict retained-artifact helpers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
UPSTREAM = LANE/'TT028'
SOURCE = ROOT/'source'
sys.path.insert(0, str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref

BLOCKS = tuple(range(28000000, 28000064))
DISPOSABLE = (608280, 608281)
KEYS = ('V', 'ema', 'R', 'theta')
def now(): return datetime.now(timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(serialized(value))
def arrays(path):
    with np.load(path, allow_pickle=False) as data: return {k:data[k].copy() for k in data.files}
def identities(values):
    return {k:dict(shape=list(v.shape), dtype=str(v.dtype), sha256=digest(v.tobytes())) for k,v in values.items()}
def write_arrays(path, values):
    with Path(path).open('xb') as f: np.savez_compressed(f, **values)
    assert identities(arrays(path)) == identities(values)
def verify(hashes):
    for p, expected in hashes.items(): assert sha(p) == expected, p
def source_check():
    s = read_json(ROOT/'SOURCE_MANIFEST.json')
    for r in s['files']: assert sha(ROOT/r['snapshot']) == r['sha256']
    for p,h in s['inherited_code'].items(): assert sha(ROOT/p) == h
    return len(s['files'])
def runtime_hashes():
    model.source.api()
    files = set(ROOT.glob('*.py')) | {ROOT/n for n in ('PROTOCOL.md','SOURCE_MANIFEST.json','INPUT_MANIFEST.json','RANDOMNESS.json')}
    files |= {LANE/'run_python.sh'}
    files |= {ROOT/r['snapshot'] for r in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    files |= {p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and SOURCE in Path(path).resolve().parents: assert Path(path).resolve() in files
        if path and 'ingressing-minds-v-ruliad-paper-ideas' in str(path): raise AssertionError('live upstream import')
    return {str(p):sha(p) for p in sorted(files)}

class Custody:
    def __init__(self, role):
        self.hashes = read_json(ROOT/'INPUT_MANIFEST.json')['production' if role=='development' else 'benchmark']
        self.used = {}
    def checked(self, path):
        path = Path(path); expected = self.hashes[str(path)]
        assert sha(path) == expected, str(path)
        self.used[str(path)] = expected
        return path
    def json(self, path): return read_json(self.checked(path))
    def arrays(self, path): return arrays(self.checked(path))
