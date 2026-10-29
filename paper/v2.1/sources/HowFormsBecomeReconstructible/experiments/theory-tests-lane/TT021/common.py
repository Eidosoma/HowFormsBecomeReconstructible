"""TT021 local files, unchanged physics sources, and immutable evidence."""
from datetime import datetime, timezone
import hashlib
import importlib.util
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

BLOCKS = tuple(range(21000000, 21000064))
DISPOSABLE = (603210, 603211)
KEYS = ('V', 'ema', 'R', 'theta')
FIELDS = ('accuracy', 'partner_accuracy', 'preference', 'projection_gap',
          'sign_fidelity', 'theta_corr_parent', 'theta_corr_partner')


def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(serialized(value))


def arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {k: saved[k].copy() for k in saved.files}


def identities(values):
    return {k: dict(dtype=str(v.dtype), shape=list(v.shape),
                   sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k,v in values.items()}


def write_arrays(path, values):
    with Path(path).open('xb') as f: np.savez_compressed(f, **values)
    result = arrays(path)
    assert identities(result) == identities(values)
    return result


def verify(hashes):
    for path, digest in hashes.items(): assert sha(path) == digest, path


def pointer(path, values):
    return dict(path=str(Path(path).resolve()), sha256=sha(path), arrays=identities(values))


def open_pointer(item):
    assert sha(item['path']) == item['sha256'], item['path']
    value = arrays(item['path'])
    assert identities(value) == item['arrays']
    return value


def physical_context(ctx): return {k:ctx[k] for k in ('config','tissue','ladder','bp')}


def boundary_checker():
    path = SOURCE/'codex.lawsConfirmation/scripts/check_l22_active_form_boundary.py'
    spec = importlib.util.spec_from_file_location('tt021_boundary_checker', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_check():
    manifest = read_json(ROOT/'SOURCE_MANIFEST.json')
    for item in manifest['files']: assert sha(ROOT/item['snapshot']) == item['sha256']
    for name, digest in manifest['independent_reference'].items(): assert sha(ROOT/name) == digest
    return len(manifest['files'])


def runtime_hashes():
    model.source.api()
    names = ('common.py','design.py','analysis.py','run.py','reference.py','tt019_reference.py',
             'qualify.py','execute.py','register.py','PROTOCOL.md','SOURCE_MANIFEST.json')
    files = {ROOT/name for name in names} | {LANE/'run_python.sh'}
    files |= {ROOT/item['snapshot'] for item in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and 'ingressing-minds-v-ruliad-paper-ideas' in str(name):
            raise AssertionError('live upstream import '+str(name))
        if name and SOURCE in Path(name).resolve().parents: assert Path(name).resolve() in files
    return {str(p):sha(p) for p in sorted(files)}
