"""Local immutable source, finite records and evidence helpers."""
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
def digest(data): return hashlib.sha256(data).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(serialized(value))
def arrays(path):
    with np.load(path, allow_pickle=False) as data: return {k:data[k].copy() for k in data.files}
def identities(values):
    return {k:dict(shape=list(v.shape), dtype=str(v.dtype), sha256=digest(v.tobytes())) for k,v in values.items()}
def write_arrays(path, values):
    with Path(path).open('xb') as stream: np.savez_compressed(stream, **values)
    assert identities(arrays(path)) == identities(values)
def verify(hashes):
    for p, expected in hashes.items(): assert sha(p) == expected, p
def source_check():
    source = read_json(ROOT/'SOURCE_MANIFEST.json')
    for row in source['files']: assert sha(ROOT/row['snapshot']) == row['sha256']
    for name, expected in source['inherited_code'].items(): assert sha(ROOT/name) == expected
    return len(source['files'])
def baseline_check():
    value = read_json(ROOT/'BASELINE_MANIFEST.json'); verify(value['evidence'])
    for entry in value['rows'].values():
        for name, expected in entry['files'].items(): assert sha(ROOT/name) == expected
    return len(value['rows'])
def runtime_hashes():
    model.source.api()
    names = ('common.py','design.py','prepare.py','baseline.py','kernel.py','audit.py','run.py','analysis.py',
        'qualify.py','execute.py','freeze.py','resources.py','physical_reference.py','inherited_repair.py',
        'receiving.py','receiving_audit.py','PROTOCOL.md','SOURCE_MANIFEST.json','BASELINE_MANIFEST.json','RANDOMNESS.json')
    files = {ROOT/n for n in names} | {LANE/'run_python.sh'}
    files |= {ROOT/row['snapshot'] for row in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    files |= {ROOT/p for row in read_json(ROOT/'BASELINE_MANIFEST.json')['rows'].values() for p in row['files']}
    files |= {p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and SOURCE in Path(path).resolve().parents: assert Path(path).resolve() in files
        if path and 'ingressing-minds-v-ruliad-paper-ideas' in str(path): raise AssertionError('live upstream import')
    return {str(p):sha(p) for p in sorted(files)}
