"""Fixed one-read mixed-corruption pilot on exposed TT014 records."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,sys,itertools
import numpy as np
import support as s
ROOT=Path(__file__).resolve().parent;LANE=ROOT.parent;PRIOR=LANE/'TT014'
BLOCKS=(14000000,14000001,14000002,14000003,14000032,14000033,14000034,14000035)
EXCLUDED=14000999
REGIMES=('original','missing10','signflip10','mixed_unmarked','opposite_history','balanced_aligned','balanced_wrong','erased')
ARMS=('P','Z','G','M','GA','MA')
PAIRS=tuple(itertools.combinations(range(6),2));CONTRASTS=tuple(ARMS[j]+'_minus_'+ARMS[i] for i,j in PAIRS)
GROUPS=('all','initial_pass','initial_fail','history:0','history:1','history:2','history:3')
OPTIONS=s.read(PRIOR/'plan.json')['optimizer']
NS='TT048_unmarked_one_read_v1'
CFG=dict(random_namespace=NS,reader=dict(birth_sd=.05,dt=.2,noise=.02,observe_steps=32,margin=.25),
 injury_cells=24,budgets=[2048],settling_steps=1024)
LIMIT=1024**3;RESERVE=4*1024**3;BLOCK_LIMIT=64*1024**2;ADMIN_ALLOWANCE=64*1024**2;MAX_FORECAST=6*3600
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return s.read(p)
def sha(p):return s.sha(p)
def write(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s.dump(p,value)
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(v):return hashlib.sha256(v).hexdigest()
def save(p,v):
 s.save(p,v);loaded=s.arrays(p)
 for k in v:s.equal(v[k],loaded[k],k)
def arrays(p):return s.arrays(p)
def exact(a,b,label='array'):return s.equal(np.asarray(a),np.asarray(b),label)
def near(a,b,label='numeric',tol=1e-12):return s.close(a,b,tol,label)
def verify(files):
 for p,h in files.items():assert sha(p)==h,p
def selected(role):
 assert role in ('qualification','development')
 return BLOCKS if role=='development' else (EXCLUDED,)
def futures(role):return list(range(4 if role=='development' else 1))
def size():return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
def space():assert size()<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE,'TT048 disk cap/reserve'
def phase_bytes(role):return len(selected(role))*BLOCK_LIMIT+ADMIN_ALLOWANCE
def inputs():
 m=read(ROOT/'SOURCE_MANIFEST.json');verify(m['unchanged_copies']);verify(m['evidence'])
 paths=set(ROOT.glob('*.py'))|{ROOT/'PROTOCOL.md',ROOT/'SOURCE_MANIFEST.json',ROOT/'SEEDS.json',LANE/'run_python.sh',LANE.parent/'RUN_POLICY.md',PRIOR/'plan.json'}
 paths|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
 return {str(p):sha(p) for p in sorted(paths)}
def source(role,index):
 paths=read(ROOT/'SOURCE_MANIFEST.json')['records'][str(index)]
 for name,p in paths.items():assert sha(p)==read(ROOT/'SOURCE_MANIFEST.json')['source_files'][p]
 prepared=arrays(paths['prepared']);teaching=arrays(paths['teaching'])
 assert prepared['packets'].shape==(16,4,4096) and teaching['acquired'].shape==(4,4096)
 return prepared,teaching,paths
