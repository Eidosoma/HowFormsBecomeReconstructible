"""Exposed development cohort, fixed damage contrast and finite-state custody."""
from datetime import datetime,timezone
from pathlib import Path
from dataclasses import replace,asdict
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
UP,PRIOR=LANE/'TT032',LANE/'TT039'
SOURCE=UP/'source'
sys.path.insert(0,str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref
BLOCKS=(39010000,39010016,39010032,39010048)
EXCLUDED=(608280,608281)
DAMAGE=('mix000','mix050','mix100')
MIX=dict(zip(DAMAGE,(0.,.5,1.)))
KEYS=('V','ema','R','theta')
FAMILIES=('common','residual')
MASKS=('axis0_side0','axis0_side1','axis1_side0','axis1_side1')
SOURCES=('own','foreign','neutral')
CREDITS=('target','donor','template','opposite')
ARMS=('preserve','early','late','continuous')
BUDGETS=(0,100,100,1000)
WINDOWS=((0,0),(1,100),(901,1000),(1,1000))
SOURCE_SNAPSHOTS=(0,1,100,101,1000)
REPAIR_SNAPSHOTS=(0,1,100,101,900,901,1000,1001,1100,1500,1900)
START,END=1000,1900
SNAPSHOTS=(1000,1001,1100,1500,1900)
BODY_FIELDS=('body_preserve','body_early','body_late','body_full')
READER_FIELDS=('incoming','after100','after_late100','after1000')
OBS_KEYS=('scores','probabilities','correctness','margins')
GEOMETRIES=('positive_half_retained','negative_half_retained','both_polarities_retained')
GROUPS=('all','history:unique_pass','history:other','message:0','message:1','message:2','message:3')
VIEWS=('all_masks',)+tuple('mask:'+v for v in MASKS)+tuple('geometry:'+v for v in GEOMETRIES)
CONDITIONS=tuple('|'.join((f,g,v,o)) for f in FAMILIES for g in GROUPS for v in VIEWS for o in SOURCES)
INDEX={k:i for i,k in enumerate(CONDITIONS)}
SOURCE_CONTRASTS=tuple('|'.join((f,g,v,'own_minus_'+o)) for f in FAMILIES for g in GROUPS for v in VIEWS for o in SOURCES[1:])
SOURCE_INDEX={k:i for i,k in enumerate(SOURCE_CONTRASTS)}
COMPARISONS=('early_minus_late','late_minus_preserve','early_minus_preserve','late_minus_continuous','early_minus_continuous','continuous_minus_preserve')
PAIRS=((1,2),(2,0),(1,0),(2,3),(1,3),(3,0))
STAT_FIELDS=('mean_delta','paired_gain','paired_harm','paired_tie','fixed_gain','fixed_harm','fixed_tie','record_gain','record_harm','record_tie')
SIGNS=('harm','tie','gain')
def now():return datetime.now(timezone.utc).isoformat()
def digest(v):return hashlib.sha256(v).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def read(p):return json.loads(Path(p).read_text())
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(encoded(v))
def arrays(p,names=None):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in (z.files if names is None else names)}
def exact(a,b,label='array'):
    assert a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),label
def near(a,b):assert np.allclose(a,b,rtol=0,atol=2e-13,equal_nan=True),(a,b)
def identities(v):return {k:dict(shape=list(a.shape),dtype=str(a.dtype),sha256=digest(a.tobytes())) for k,a in v.items()}
def save(p,v):
    with Path(p).open('xb') as f:np.savez_compressed(f,**v)
    check=arrays(p);assert set(check)==set(v)
    for k in v:exact(check[k],v[k],k)
def verify(m):
    for p,h in m.items():assert sha(p)==h,p
ROLES=('qualification','benchmark','development')
TAG='TT040_packet_damage_timing_v1'
DISPOSABLE=EXCLUDED
def selected(role):
    assert role in ROLES
    return BLOCKS if role=='development' else EXCLUDED
def schedule(role):
    assert role in ROLES
    return (1,4,FAMILIES) if role=='development' else (1,1,FAMILIES)
def configs():
    return replace(model.CONFIG,replicates=4,sweeps=1000,times=SOURCE_SNAPSHOTS),replace(model.READOUT,parents=4,draws=1,sweeps=1000,times=(0,1,1000))
def body_context(ctx):
    return ctx|{'config':replace(ctx['config'],sweeps=END,times=REPAIR_SNAPSHOTS),
        'readout':replace(ctx['readout'],sweeps=END,times=(0,1,END))}
def codebook():
    y,x=np.indices((16,16));h=np.where(y<8,1.,-1.);v=np.where(x<8,1.,-1.)
    return np.stack((h,-h,v,-v))
def geometry(mi,w):
    retained=np.indices((16,16))[mi//2]//8==mi%2
    return {1.:0,-1.:1,0.:2}[float(codebook()[w//4][retained].mean())]
def labels(w,mi):return (w//4,(w//4+2)%4,mi^1,mi)
def credit(p,w,mi):return p[w,list(labels(w,mi))]
def address(role,index,c,d):
    assert role in ROLES and all(type(v) is int and v>=0 for v in (index,c,d))
    return int.from_bytes(hashlib.sha256(json.dumps([TAG,role,index,c,d],separators=(',',':')).encode()).digest()[:16],'little')
def corruption_seed(role,index,c):
    assert role in ROLES and all(type(v) is int and v>=0 for v in (index,c))
    return int.from_bytes(hashlib.sha256(json.dumps([TAG,'corruption',role,index,c],separators=(',',':')).encode()).digest()[:16],'little')
def state_bytes(state):
    assert set(state)==set(KEYS)
    return b''.join(state[k].tobytes() for k in KEYS)
def inputs():
    model.source.api()
    manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['native_code'])
    verify({p:v['sha256'] for p,v in manifest['copied_audited_code'].items()})
    files=set(ROOT.glob('*.py'))|{ROOT/n for n in ('PROTOCOL.md','SOURCE_MANIFEST.json','RANDOMNESS.json')}|{LANE/'run_python.sh'}
    files|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
    files|=set(map(Path,manifest['native_code']))
    for module in list(sys.modules.values()):
        p=getattr(module,'__file__',None)
        if p and SOURCE in Path(p).resolve().parents:assert Path(p).resolve() in files
        if p and 'ingressing-minds-v-ruliad-paper-ideas' in p:raise AssertionError('live upstream import')
    return {str(p):sha(p) for p in sorted(files)}
read_json=read
write_json=write
write_arrays=save
serialized=encoded
def boundary_checker():
    import importlib.util
    p=SOURCE/'codex.lawsConfirmation/scripts/check_l22_active_form_boundary.py'
    spec=importlib.util.spec_from_file_location('tt040_boundary_checker',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
