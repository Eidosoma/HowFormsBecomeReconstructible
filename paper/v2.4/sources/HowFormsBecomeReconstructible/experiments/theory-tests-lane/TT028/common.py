"""Local immutable sources, fresh identities and experiment artifact helpers."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
SOURCE=ROOT/'source'
sys.path.insert(0,str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref

BLOCKS=tuple(range(28000000,28000064))
DISPOSABLE=(608280,608281)
KEYS=('V','ema','R','theta')
def now():return datetime.now(timezone.utc).isoformat()
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def read_json(path):return json.loads(Path(path).read_text())
def serialized(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(serialized(value))
def arrays(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k].copy() for k in data.files}
def identities(values):return {k:dict(shape=list(v.shape),dtype=str(v.dtype),sha256=digest(v.tobytes())) for k,v in values.items()}
def write_arrays(path,values):
    with Path(path).open('xb') as stream:np.savez_compressed(stream,**values)
    assert identities(arrays(path))==identities(values)
def verify(hashes):
    for p,expected in hashes.items():assert sha(p)==expected,p
def source_check():
    value=read_json(ROOT/'SOURCE_MANIFEST.json')
    for row in value['files']:assert sha(ROOT/row['snapshot'])==row['sha256']
    for name,expected in value['inherited_code'].items():assert sha(ROOT/name)==expected
    for name,entry in value['adaptations'].items():assert sha(ROOT/name)==entry['sha256']
    return len(value['files'])
def evidence_check():verify(read_json(ROOT/'EVIDENCE.json')['files'])
def boundary_checker():
    path=SOURCE/'codex.lawsConfirmation/scripts/check_l22_active_form_boundary.py'
    spec=importlib.util.spec_from_file_location('tt028_boundary_checker',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
def runtime_hashes():
    model.source.api()
    names=('common.py','design.py','prepare.py','baseline.py','kernel.py','audit.py','intervention.py',
        'intervention_audit.py','run.py','analysis.py','inference.py','qualify.py','execute.py','freeze.py',
        'resources.py','physical_reference.py','capture_reference.py','inherited_repair.py','receiving.py',
        'receiving_audit.py','PROTOCOL.md','SOURCE_MANIFEST.json','EVIDENCE.json','RANDOMNESS.json')
    files={ROOT/n for n in names}|{LANE/'run_python.sh'}
    files|={ROOT/row['snapshot'] for row in read_json(ROOT/'SOURCE_MANIFEST.json')['files']}
    files|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
    for module in list(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path and SOURCE in Path(path).resolve().parents:assert Path(path).resolve() in files
        if path and 'ingressing-minds-v-ruliad-paper-ideas' in str(path):raise AssertionError('live upstream import')
    return {str(p):sha(p) for p in sorted(files)}
