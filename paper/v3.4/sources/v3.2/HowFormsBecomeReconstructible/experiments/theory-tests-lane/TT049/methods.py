"""Packet-only maximum forest and the fixed opposite-majority screen."""
import math, statistics, time
import numpy as np
import native as n
import optimizer as opt
import optimizer_audit as oa
import independent
from study import exact

def build(outgoing):
 if type(outgoing) is not np.ndarray or outgoing.shape!=(2,256) or outgoing.dtype!=np.float64 or not np.isfinite(outgoing).all():
  raise ValueError('only a finite 2-by-256 float64 packet is accepted')
 before=outgoing.tobytes();start=time.process_time()
 c=opt.coupling(outgoing);g=opt.forest(c,opt.INPUT_PINS)
 observed=np.abs(outgoing[outgoing!=0]);median=float(np.median(observed)) if len(observed) else 0.
 proposal=(np.where(outgoing.ravel()!=0,abs(outgoing.ravel()),median)*g[opt.U]*g[opt.V]).reshape(2,256)
 sums=[int(g[p].sum()) for p in n.PORTS[1:]]
 eligible=bool(len(observed)>0 and sums[0]*sums[1]<0)
 rows=np.stack((outgoing,proposal,proposal if eligible else outgoing))
 elapsed=time.process_time()-start;assert outgoing.tobytes()==before
 decisions=[]
 for ai,(name,row) in enumerate(zip(('P','G','S'),rows)):
  edited=row.tobytes()!=before
  decisions.append(dict(arm=name,action='abstain' if ai==2 and not eligible else 'edit' if edited else 'no_change',
   eligible=eligible if ai==2 else None,historical_status='UNVERIFIED',changed_edges=int(np.count_nonzero(row!=outgoing)),
   flipped_nonzero_edges=int(np.count_nonzero((outgoing!=0)&(row*outgoing<0))),
   added_edges=int(np.count_nonzero((outgoing==0)&(row!=0))),total_abs_weight=math.fsum(map(abs,map(float,row.ravel())))))
 return rows,dict(signs=g,median=median,patch_sums=sums,eligible=eligible,cpu_seconds=elapsed,decisions=decisions)

def audit(outgoing,rows,meta):
 c=oa.independent_coupling(outgoing.reshape(2,16,16)).ravel();g=independent.forest(c,sorted(map(int,n.PORTS[0])))
 exact(g,meta['signs'],'independent Kruskal signs');_,edges=oa.geometry()
 observed=[abs(float(v)) for v in outgoing.ravel() if v!=0];median=float(statistics.median(observed)) if observed else 0.
 expected=[]
 for e,(u,v) in enumerate(edges):expected.append((abs(float(outgoing.ravel()[e])) if outgoing.ravel()[e] else median)*int(g[u])*int(g[v]))
 proposal=np.array(expected).reshape(2,256)
 positive=[sum(int(g[i])>0 for i in port) for port in n.PORTS[1:]]
 eligible=bool(observed) and ((positive[0]>2 and positive[1]<2) or (positive[0]<2 and positive[1]>2))
 exact(rows,np.stack((outgoing,proposal,proposal if eligible else outgoing)),'scalar proposals and abstention')
 assert eligible==meta['eligible'] and median==meta['median']
 for i,row in enumerate(rows):
  d=meta['decisions'][i];assert d['historical_status']=='UNVERIFIED'
  action='abstain' if i==2 and not eligible else 'no_change' if row.tobytes()==outgoing.tobytes() else 'edit'
  assert d['action']==action and d['changed_edges']==sum(a!=b for a,b in zip(row.ravel(),outgoing.ravel()))
 return dict(forest_checks=1,proposal_checks=3,screen_checks=1)
