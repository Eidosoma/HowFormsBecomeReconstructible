"""Fixed fresh-source one-read test of the TT048 graph majority screen."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, sys, itertools
import numpy as np
import support as s

ROOT=Path(__file__).resolve().parent;LANE=ROOT.parent
BLOCKS=tuple(range(49000000,49000032));QUAL=(49999996,49999998)
REGIMES=('original','missing10','signflip10','mixed_unmarked','opposite_history','balanced_aligned','balanced_wrong','erased')
ARMS=('P','G','S');PAIRS=tuple(itertools.combinations(range(3),2))
CONTRASTS=tuple(ARMS[j]+'_minus_'+ARMS[i] for i,j in PAIRS)
GROUPS=('all','initial_pass','initial_fail','history:0','history:1','history:2','history:3')
NS='TT049_majority_screen_assessment_v1';SOURCE_NS='TT049_majority_screen_source_v1'
PRIOR_PLAN=s.read(LANE/'TT014/plan.json')
NCFG=PRIOR_PLAN['native_config'];CYCLE=PRIOR_PLAN['native_cycle']
SCHEDULES=tuple(tuple(x) for x in PRIOR_PLAN['tolerance_generations']);TOLERANCE=1e-4
CFG=dict(random_namespace=NS,reader=dict(birth_sd=.05,dt=.2,noise=.02,observe_steps=32,margin=.25),
         injury_cells=24,budgets=[2048],settling_steps=1024)
LIMIT=2*1024**3;RESERVE=4*1024**3;BLOCK_LIMIT=32*1024**2;ADMIN_ALLOWANCE=64*1024**2
MAX_FORECAST=8*3600;QUAL_DEADLINE=3600
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return s.read(p)
def sha(p):return s.sha(p)
def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s.dump(p,v)
def replace(p,v):
 p=Path(p);q=p.with_name(p.name+'.pending');write(q,v);q.replace(p)
def arrays(p):return s.arrays(p)
def save(p,v):
 s.save(p,v);loaded=arrays(p)
 for k in v:exact(v[k],loaded[k],k)
def exact(a,b,label='array'):return s.equal(np.asarray(a),np.asarray(b),label)
def near(a,b,label='numeric',tol=1e-12):return s.close(a,b,tol,label)
def verify(files):
 for p,h in files.items():assert sha(p)==h,p
def selected(role):
 assert role in ('qualification','production')
 return QUAL if role=='qualification' else BLOCKS
def history(index):
 assert index in BLOCKS+QUAL
 return index%4
def source_identity(index,role):
 assert index in selected(role)
 return 34000 if role=='qualification' else SOURCE_NS+':'+str(index)
def size():return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
def space():assert size()<LIMIT and shutil.disk_usage(ROOT).free>=RESERVE,'TT049 disk cap/reserve'
def phase_bytes(role):return len(selected(role))*BLOCK_LIMIT+ADMIN_ALLOWANCE
def inputs():
 m=read(ROOT/'SOURCE_MANIFEST.json');verify(m['copied_files']);verify(m['evidence'])
 paths=set(ROOT.glob('*.py'))|{ROOT/'PROTOCOL.md',ROOT/'SOURCE_MANIFEST.json',ROOT/'SEEDS.json',LANE/'run_python.sh',LANE.parent/'RUN_POLICY.md',LANE/'TT014/plan.json'}
 paths|={Path(p) for p in m['copied_files']}
 paths|={p for p in (ROOT/'intake_inputs').rglob('*') if p.is_file()}
 return {str(p):sha(p) for p in sorted(paths)}
