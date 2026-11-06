"""Fixed fresh-source test of damage-dependent one-read packet usefulness."""
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import replace, asdict
import hashlib, json, sys, shutil
import numpy as np
ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
PRIOR = LANE/'TT045'; SOURCE = LANE/'TT032/source'
sys.path.insert(0, str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref
BLOCKS = tuple(range(46010000, 46010032))
EXCLUDED = DISPOSABLE = (608280, 608281)
ROLES = ('qualification', 'confirmation')
FAMILIES = ('residual',)
SOURCES = ('own',)
DAMAGE = ('mix000', 'mix050', 'mix100')
MIX = dict(mix000=0., mix050=.5, mix100=1.)
MASKS = ('axis0_side0', 'axis0_side1', 'axis1_side0', 'axis1_side1')
KEYS = ('V', 'ema', 'R', 'theta'); BODY_KEYS = ('V', 'ema', 'R')
TIMES = (0, 1, 100, 500, 900, 1000); START, END = 0, 1000
SOURCE_SNAPSHOTS = (0, 1, 100, 101, 1000)
WRITER_TIMES = (0, 1, 100, 900, 901, 1000)
WINDOWS = ((0, 0), (901, 1000))
PROFILES = ('continuing', 'fresh'); ARMS = ('C_T0', 'C_T1', 'F_T0', 'F_T1')
CREDITS = ('target', 'donor', 'template', 'opposite')
OBS_KEYS = ('scores', 'probabilities', 'correctness', 'margins')
GEOMETRIES = ('positive_half_retained', 'negative_half_retained', 'both_polarities_retained')
GROUPS = ('all', 'history:unique_pass', 'history:other', 'message:0', 'message:1', 'message:2', 'message:3')
VIEWS = ('all_masks',)+tuple('mask:'+m for m in MASKS)+tuple('geometry:'+g for g in GEOMETRIES)
CONDITIONS = tuple('|'.join((d, f, g, v, s)) for d in DAMAGE for f in FAMILIES for g in GROUPS for v in VIEWS for s in SOURCES)
INDEX = {k:i for i,k in enumerate(CONDITIONS)}
COMPARISONS = ('packet_C', 'packet_F', 'state_with_T0', 'state_with_T1', 'F_T1_minus_C_T0', 'C_T1_minus_F_T0', 'state_packet_interaction')
COEFFICIENTS = np.array([[-1,1,0,0],[0,0,-1,1],[-1,0,1,0],[0,-1,0,1],[-1,0,0,1],[0,1,-1,0],[1,-1,-1,1]], dtype=np.int64)
NCON = len(COMPARISONS); COMPARISON_INDEX = {n:i for i,n in enumerate(COMPARISONS)}
SIGNS = ('harm', 'tie', 'gain')
LIMIT = 18*1024**3; RESERVE = 4*1024**3; BATCH_BYTES = 700*1024
SOURCE_BYTES = 32*1024**2; PHASE_BYTES = 1024**3; ADMIN_BYTES = 64*1024**2
MAX_FORECAST = 14*3600; ALPHA = .05/4
ARCHIVE = LANE/'storage_archives/2026-10-28_completed-runs_v2'
def now(): return datetime.now(timezone.utc).isoformat()
def digest(x): return hashlib.sha256(x).hexdigest()
def sha(p): return digest(Path(p).read_bytes())
def read(p): return json.loads(Path(p).read_text())
def encoded(v): return (json.dumps(v, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f: f.write(encoded(v))
def arrays(p,names=None):
    with np.load(p, allow_pickle=False) as z: return {k:z[k] for k in (z.files if names is None else names)}
def exact(a,b,label='array'):
    assert a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(), label
def near(a,b): assert np.allclose(a,b,rtol=0,atol=2e-13,equal_nan=True),(a,b)
def identities(v): return {k:dict(shape=list(a.shape),dtype=str(a.dtype),sha256=digest(a.tobytes())) for k,a in v.items()}
def save(p,v):
    with Path(p).open('xb') as f: np.savez_compressed(f,**v)
    check=arrays(p); assert set(v)==set(check)
    for k in v: exact(v[k],check[k],k)
def verify(m):
    for p,h in m.items(): assert sha(p)==h,p
def state_bytes(s): return b''.join(s[k].tobytes() for k in KEYS)
def codebook():
    y,x=np.indices((16,16)); h=np.where(y<8,1.,-1.); v=np.where(x<8,1.,-1.)
    return np.stack((h,-h,v,-v))
def geometry(mi,w):
    keep=np.indices((16,16))[mi//2]//8==mi%2
    return {1.:0,-1.:1,0.:2}[float(codebook()[w//4][keep].mean())]
def labels(w,mi): return (w//4,(w//4+2)%4,mi^1,mi)
def credit(p,w,mi): return p[w,list(labels(w,mi))]
def key(a): return (a['damage'],a['family'],a['mask'],a['body_source'])
def case_key(a): return (*key(a),a['world'])
def selected(role):
    assert role in ROLES
    return BLOCKS if role=='confirmation' else EXCLUDED
def births(role): return 4 if role=='confirmation' else 1
def futures(role): return 8 if role=='confirmation' else 2
def initial_count(profile,role): return 1 if profile=='continuing' else births(role)
def seeded(kind,role,index,k):
    assert kind in ('corruption','birth','future') and role in ROLES and index in selected(role) and type(k) is int and k>=0
    assert k < (1 if kind=='corruption' else births(role) if kind=='birth' else futures(role))
    payload=['TT046_damage_confirmation_v1',kind,role,index,k]
    return int.from_bytes(hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).digest()[:16],'little')
def corruption_seed(role,index,c): return seeded('corruption',role,index,c)
def birth_address(role,index,b): return seeded('birth',role,index,b)
def future_address(role,index,k): return seeded('future',role,index,k)
def configs():
    return replace(model.CONFIG,replicates=4,sweeps=1000,times=SOURCE_SNAPSHOTS), replace(model.READOUT,parents=4,draws=1,sweeps=1000,times=(0,1,1000))
def context(index):
    cfg,rcfg=configs(); ctx=model.source.context(index,cfg)|{'readout':rcfg}
    exact(ctx['codes'],codebook()); return ctx
def with_times(ctx,times): return ctx|{'config':replace(ctx['config'],times=times)}
def size(): return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
def space(): assert size()<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE,'TT046 storage cap/reserve'
def batch_space(): assert shutil.disk_usage(ROOT).free>=RESERVE,'TT046 free-space reserve'
def physical_bound(role): return 3*(8+5*births(role))*futures(role)
def phase_bound(role): return len(selected(role))*(physical_bound(role)*BATCH_BYTES+SOURCE_BYTES)+PHASE_BYTES
def inputs():
    model.source.api(); m=read(ROOT/'SOURCE_MANIFEST.json'); verify(m['native_code']); verify(m['unchanged_copies'])
    paths=set(ROOT.glob('*.py'))|{ROOT/n for n in ('PROTOCOL.md','SOURCE_MANIFEST.json','RESERVATION.json','RESERVATION_REVIEW.json','SEEDS.json','admin/review_reservation.py',
        'corrections/metadata_pairing_v1/CORRECTION.json','corrections/metadata_pairing_v1/MANIFEST.json')}
    paths|={LANE/'run_python.sh',LANE.parent/'RUN_POLICY.md'}
    paths|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}; paths|=set(map(Path,m['native_code']))
    for module in list(sys.modules.values()):
        p=getattr(module,'__file__',None)
        if p and SOURCE in Path(p).resolve().parents: assert Path(p).resolve() in paths
    return {str(p):sha(p) for p in sorted(paths)}
read_json=read; write_json=write; write_arrays=save; serialized=encoded
def boundary_checker():
    import importlib.util
    p=SOURCE/'codex.lawsConfirmation/scripts/check_l22_active_form_boundary.py'
    spec=importlib.util.spec_from_file_location('tt046_boundary_checker',p)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
