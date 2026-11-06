"""Local paths and immutable run contracts; no outcome access on import."""
import hashlib, io, json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
FORMS = LANE.parent
sys.path.insert(0, str(FORMS))
import forms_model as native
os.environ['MPLCONFIGDIR'] = str(LANE/'.cache/matplotlib')
os.environ['XDG_CACHE_HOME'] = str(LANE/'.cache')
BLOCKS = list(range(41000,41008))
ARMS = ('I','P','C','L_native','L','C_flip','L_flip','C_low','L_low','C_flip_low','L_flip_low')
EXTRA = ('P_O','P_S','P_M','C_O','C_S','C_M')
LABELS = [(a,0) for a in ARMS]+[(a,1) for a in ARMS]+[(a,1) for a in EXTRA]
CONFIG = dict(recipients=4, dt=.2, noise=.02, birth_sd=.05, writer_beta=3., observe_steps=32, margin=.25)
STEPS = dict(read_steps=2048, settling_steps=1024)
RESERVE = 4*2**30
STUDY_LIMIT = 2*2**30
BLOCK_LIMIT = 192*2**20

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path, data):
    with Path(path).open('x') as f: json.dump(data,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
def replace(path,data):
    p=Path(path); q=p.with_name(p.name+f'.{os.getpid()}.tmp'); write(q,data); q.replace(p)
def save(path, arrays):
    assert all(isinstance(v,np.ndarray) and np.isfinite(v).all() for v in arrays.values())
    with Path(path).open('xb') as f: np.savez_compressed(f,**arrays)
def load(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def size(path): return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())
def guard(block=None):
    assert shutil.disk_usage(ROOT).free>=RESERVE, 'Four GiB free reserve'
    assert size(ROOT)<STUDY_LIMIT, 'Two GiB study ceiling'
    if block: assert size(block)<BLOCK_LIMIT, '192 MiB block ceiling'
def verify_inputs():
    frozen=read(ROOT/'FROZEN.json')
    for p,h in frozen['inputs'].items():assert sha(p)==h,p
    return frozen
def source(block, technical=False, recipients=None):
    m=read(ROOT/'SOURCES.json')['technical' if technical else 'development']
    path=Path(m['path']); result={}
    for prefix in ('source','interventions','rewrite'):
        name=f'{prefix}_{block:06d}.npz';p=path/name
        assert sha(p)==m['files'][name],str(p)
        # rewrite contains a known writer, not terminal receiving outcomes.
        result[prefix]=load(p)
    a=native.old.intervene(result['source']); native.equal(a,result['interventions'])
    b=native.independent.legacy.intervene(result['source']);native.equal(a,b)
    if recipients is not None and recipients!=a['packets'].shape[2]:
        assert technical and a['packets'].shape[2]==1
        a={k:np.repeat(v,recipients,axis=2) for k,v in a.items()}
    return a,result['rewrite']

