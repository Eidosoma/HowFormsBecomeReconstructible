import hashlib,json,time
from pathlib import Path
import numpy as np
from common import cap_cpus,sha,utc
cap_cpus(8);t=time.monotonic()
root=Path('E036_serial_cue_capture_v2/runs/serial_v1')
complete=json.loads((root/'COMPLETE.json').read_text())
def load(name):
 p=root/name;assert sha(p)==complete['outputs_sha256'][name]
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files if k!='__index__'}
def decode(p):return np.frombuffer(p.tobytes(),dtype='<f8').reshape(*p.shape[:-1],2,16,16)
totals={c:dict(opportunities=0,nonzero=0,strong=0) for c in (0,1,2,3,4,8)}
exact_support_matches=0;cases=0
zero_origin_nonzero={c:0 for c in (2,3)}
curve={c:[] for c in (0,2,3)}
for b in range(28000,28032):
 old=None;last=None
 for g in range(1,17):
  z=load(f'boundary_{b:06d}_g{g}.npz');new=decode(z['outgoing']);alive=~z['renewal_mask']
  live=np.stack((alive&np.roll(alive,-1,-1),alive&np.roll(alive,-1,-2)),axis=-3)
  cases+=16
  exact_support_matches+=int(((new[2]!=0)==(new[8]!=0)).all(axis=(-3,-2,-1)).sum())
  if last is not None:
   returning=live&~last
   for c in totals:
    totals[c]['opportunities']+=int(returning.sum())
    totals[c]['nonzero']+=int(np.count_nonzero(new[c][returning]))
    totals[c]['strong']+=int(np.count_nonzero(abs(new[c][returning])>.5))
   for c in zero_origin_nonzero:zero_origin_nonzero[c]+=int(np.count_nonzero((old[c]==0)&(new[c]!=0)&live))
  old=new;last=live
print(json.dumps(dict(utc=utc(),seconds=time.monotonic()-t,returning_edges=totals,
  comparison='contrast-preserve support equals cumulative-damage copy at every coordinate',
  exact_support_lineage_boundaries=exact_support_matches,total_lineage_boundaries=cases,
  new_nonzero_edges_from_available_exact_zeros=zero_origin_nonzero,
  source_complete_sha256=sha(root/'COMPLETE.json'),persisted=False),sort_keys=True))
