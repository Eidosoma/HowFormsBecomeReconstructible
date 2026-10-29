"""Count actual independent array comparisons on an excluded saved input."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import run,intervention_audit

p=ROOT/'checks/qualification_v1/serial/tissue_608280'
ctx=run.context(EXCLUDED[0]);data=arrays(p/'baseline/initial_residual.npz')
values=arrays(p/'physical/input_0_residual.npz');metadata=read(p/'physical/input_0_residual.json')['metadata']
original=ref.exact;observed=[]
def counted(a,b,label='array'):
    original(a,b,label);observed.append(label)
try:
    ref.exact=counted
    declared=intervention_audit.check(ctx,data,'qualification',0,values,metadata)
finally:ref.exact=original
assert len(observed)==15 and declared==7
write(ROOT/'checks/INPUT_COUNTER_DIAGNOSIS.json',dict(status='BOOKKEEPING_UNDERCOUNT',recorded_utc=now(),
    declared_arrays=declared,actual_exact_comparisons=len(observed),labels=observed,
    source_sha256=sha(ROOT/'intervention_audit.py'),excluded_input_hashes={str(x):sha(x) for x in (
        p/'baseline/initial_residual.npz',p/'physical/input_0_residual.npz',p/'physical/input_0_residual.json')},
    correction='Change only return 7 to return 15; no physical or scoring operation changes',new_production_outcomes=0))
print(dict(status='DIAGNOSED',declared=declared,actual=len(observed),new_production_outcomes=0))
