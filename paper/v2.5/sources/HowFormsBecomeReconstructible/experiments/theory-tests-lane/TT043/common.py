"""Fixed receiving-regime experiment and source custody."""
from datetime import datetime,timezone
from pathlib import Path
from dataclasses import replace,asdict
import hashlib,json,sys,shutil
import numpy as np
ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
UP=LANE/'TT040';PRIOR=LANE/'TT042';SOURCE=LANE/'TT032/source'
sys.path.insert(0,str(SOURCE/'codex.lawsConfirmation/src'))
from laws_confirmation import l22_early_capture as model
from laws_confirmation import l22_fixed_record_readout as reader
import physical_reference as ref
BLOCKS=(39010000,39010016,39010032,39010048)
EXCLUDED=(608280,608281)
DAMAGE=('mix000','mix050','mix100')
FAMILIES=('common','residual')
MASKS=('axis0_side0','axis0_side1','axis1_side0','axis1_side1')
SOURCES=('own','foreign','neutral')
KEYS=('V','ema','R','theta')
BODY_KEYS=('V','ema','R')
TIMES=(0,1,100,500,900,1000)
BODY_ANCHOR_TIMES=(0,1,100,500,900)
PROFILES=('continuing','fresh')
FULL_TIMES=(0,1,100,101,900,901,1000,1001,1100,1500,1900)
START,END=0,1000
ARMS=('F0T0','F0T1','F1T0','F1T1')
CROSSES=((0,0),(0,1),(1,0),(1,1))
CREDITS=('target','donor','template','opposite')
OBS_KEYS=('scores','probabilities','correctness','margins')
GEOMETRIES=('positive_half_retained','negative_half_retained','both_polarities_retained')
GROUPS=('all','history:unique_pass','history:other','message:0','message:1','message:2','message:3')
VIEWS=('all_masks',)+tuple('mask:'+m for m in MASKS)+tuple('geometry:'+g for g in GEOMETRIES)
CONDITIONS=tuple('|'.join((d,f,g,v,s)) for d in DAMAGE for f in FAMILIES for g in GROUPS for v in VIEWS for s in SOURCES)
INDEX={k:i for i,k in enumerate(CONDITIONS)}
COMPARISONS=('packet_feedback_off','packet_feedback_on','feedback_with_T0','feedback_with_T1','on_late_vs_off_preserved','off_late_vs_on_preserved','interaction')
COEFFICIENTS=np.array([[-1,1,0,0],[0,0,-1,1],[-1,0,1,0],[0,-1,0,1],[-1,0,0,1],[0,1,-1,0],[1,-1,-1,1]],dtype=np.int64)
SIGNS=('harm','tie','gain')
LIMIT=6*1024**3;RESERVE=4*1024**3
def now():return datetime.now(timezone.utc).isoformat()
def digest(x):return hashlib.sha256(x).hexdigest()
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
 check=arrays(p);assert set(v)==set(check)
 for k in v:exact(v[k],check[k],k)
def verify(m):
 for p,h in m.items():assert sha(p)==h,p
def state_bytes(s):return b''.join(s[k].tobytes() for k in KEYS)
def codebook():
 y,x=np.indices((16,16));h=np.where(y<8,1.,-1.);v=np.where(x<8,1.,-1.)
 return np.stack((h,-h,v,-v))
def geometry(mi,w):
 keep=np.indices((16,16))[mi//2]//8==mi%2
 return {1.:0,-1.:1,0.:2}[float(codebook()[w//4][keep].mean())]
def labels(w,mi):return (w//4,(w//4+2)%4,mi^1,mi)
def credit(p,w,mi):return p[w,list(labels(w,mi))]
def key(a):return (a['damage'],a['family'],a['mask'],a['body_source'])
def case_key(a):return (*key(a),a['world'])
def folder(role,index):return UP/'runs'/('damage_v1' if role=='development' else 'benchmark_v1')/f'tissue_{index}'
def selected(role):return BLOCKS if role=='development' else EXCLUDED
def address(index):
 return int.from_bytes(hashlib.sha256(json.dumps(['TT022_serial_capture_v1',index,0,1,'repair'],separators=(',',':')).encode()).digest()[:16],'little')
def reader_address(role,index,d):
 return int.from_bytes(hashlib.sha256(json.dumps(['TT040_packet_damage_timing_v1','development' if role=='development' else 'benchmark',index,0,d],separators=(',',':')).encode()).digest()[:16],'little')
def context(index):
 cfg=replace(model.CONFIG,replicates=4,sweeps=END,times=TIMES)
 rcfg=replace(model.READOUT,parents=4,draws=1,sweeps=END,times=(0,1,END))
 ctx=model.source.context(index,cfg)|{'readout':rcfg};exact(ctx['codes'],codebook());return ctx
def size():return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
def space():assert size()<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE,'TT043 storage limit/reserve'
def inputs():
 model.source.api();m=read(ROOT/'SOURCE_MANIFEST.json');verify(m['native_code']);verify(m['copied_code'])
 paths=set(ROOT.glob('*.py'))|{ROOT/'PROTOCOL.md',ROOT/'SOURCE_MANIFEST.json',ROOT/'LAYOUT.json',ROOT/'LAYOUT_INPUTS.json',LANE/'run_python.sh',LANE.parent/'RUN_POLICY.md'}
 paths|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()};paths|=set(map(Path,m['native_code']))
 for module in list(sys.modules.values()):
  p=getattr(module,'__file__',None)
  if p and SOURCE in Path(p).resolve().parents:assert Path(p).resolve() in paths
 return {str(p):sha(p) for p in sorted(paths)}
class Custody:
 def __init__(self,role):self.bound=read(ROOT/'SOURCE_MANIFEST.json')[role];self.used={}
 def checked(self,p):
  p=Path(p);h=self.bound[str(p)];assert sha(p)==h,p;self.used[str(p)]=h;return p
 def json(self,p):return read(self.checked(p))
 def npz(self,p,names=None):return arrays(self.checked(p),names)

def draws(role):return 4 if role=='development' else 1
def exchange_folder(role,index):return PRIOR/'runs'/('exchange_v1' if role=='development' else 'qualification_v1')/f'tissue_{index}'
