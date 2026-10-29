"""TT023 immutable inherited physics and checked first-episode source copies."""
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
import reference as ref

BLOCKS = tuple(range(21000000, 21000004))
DISPOSABLE = (603210, 603211)
KEYS = ('V', 'ema', 'R', 'theta')

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(serialized(value))

def arrays(path):
    with np.load(path, allow_pickle=False) as saved: return {k: saved[k].copy() for k in saved.files}

def identities(values):
    return {k: dict(dtype=str(v.dtype), shape=list(v.shape), sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in values.items()}

def write_arrays(path, values):
    with Path(path).open('xb') as stream: np.savez_compressed(stream, **values)
    assert identities(arrays(path)) == identities(values)

def verify(hashes):
    for path, digest in hashes.items(): assert sha(path) == digest, path

def source_check():
    value = read_json(ROOT/'SOURCE_MANIFEST.json')
    for row in value['files']: assert sha(ROOT/row['snapshot']) == row['sha256']
    for name, digest in value['independent_reference'].items(): assert sha(ROOT/name) == digest
    return len(value['files'])

def baseline_entry(role, index, future, family):
    entry = read_json(ROOT/'BASELINE_MANIFEST.json')['rows'][f'{role}:{index}:{future}:{family}']
    for name, digest in entry['hashes'].items(): assert sha(ROOT/name) == digest, name
    return entry

def baseline_check():
    value = read_json(ROOT/'BASELINE_MANIFEST.json'); verify(value['evidence'])
    for entry in value['rows'].values():
        for name, digest in entry['hashes'].items(): assert sha(ROOT/name) == digest
    return len(value['rows'])

def runtime_hashes():
    model.source.api()
    names = ('common.py','design.py','kernel.py','audit.py','run.py','analysis.py','qualify.py',
             'execute.py','freeze.py','resources.py','reference.py','tt019_reference.py','PROTOCOL.md',
             'SOURCE_MANIFEST.json','BASELINE_MANIFEST.json')
    files = {ROOT/name for name in names} | {LANE/'run_python.sh'}
    files |= {ROOT/row['snapshot'] for row in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    for entry in read_json(ROOT/'BASELINE_MANIFEST.json')['rows'].values(): files |= {ROOT/name for name in entry['hashes']}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and 'ingressing-minds-v-ruliad-paper-ideas' in str(name): raise AssertionError('live upstream import')
        if name and SOURCE in Path(name).resolve().parents: assert Path(name).resolve() in files
    return {str(path): sha(path) for path in sorted(files)}
