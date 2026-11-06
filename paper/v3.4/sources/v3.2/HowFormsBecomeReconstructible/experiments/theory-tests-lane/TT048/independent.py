"""Independent Kruskal forest, scalar packets/gates and corruption reconstruction."""
from common import *
import math,statistics
import native as n
import optimizer_audit as oa

def forest(c,pins):
 _,edges=oa.geometry();parent=list(range(257));adj=[[] for _ in range(256)]
 def root(i):
  while parent[i]!=i:i=parent[i]
  return i
 for pin in pins:parent[pin]=256
 for e in sorted(range(512),key=lambda e:(-abs(float(c[e])),e)):
  if c[e]==0:continue
  u,v=edges[e];a,b=root(u),root(v)
  if a==b:continue
  parent[a]=b;sgn=1 if c[e]>0 else -1;adj[u].append((v,sgn));adj[v].append((u,sgn))
 g=np.zeros(256,np.int8)
 for pin in pins:g[pin]=1
 for seed in list(pins)+list(range(256)):
  if g[seed]==0:g[seed]=1
  stack=[seed];visited=set()
  while stack:
   u=stack.pop()
   if u in visited:continue
   visited.add(u)
   for v,sgn in adj[u]:
    if not g[v]:g[v]=g[u]*sgn
    else:assert g[v]==g[u]*sgn
    if v not in visited:stack.append(v)
 return g

def gate(g,c,pins,graph=None,improvable=0):
 _,edges=oa.geometry();adj=[[] for _ in range(256)];cost=[];total=[]
 for (u,v),weight in zip(edges,c):
  if weight:
   adj[u].append(v);adj[v].append(u);total.append(abs(float(weight)))
   if int(g[u])*int(g[v])!=(1 if weight>0 else -1):cost.append(abs(float(weight)))
 seen=set();anchored=True
 for seed in range(256):
  if seed in seen:continue
  group=[seed];seen.add(seed)
  for u in group:
   for v in adj[u]:
    if v not in seen:seen.add(v);group.append(v)
  if adj[seed] and not any(p in group for p in pins):anchored=False
 den=math.fsum(total);fraction=math.fsum(cost)/den if den else 0.
 uniform=all(all(g[i]==g[port[0]] for i in port) for port in n.PORTS[1:])
 agree=graph is None or all(g[i]==graph[i] for port in n.PORTS[1:] for i in port)
 return bool(den>0 and fraction<=.05 and anchored and uniform and agree and improvable==0),fraction

def methods(o,rows,meta):
 c=oa.independent_coupling(o.reshape(2,16,16)).ravel();pins=sorted(map(int,n.PORTS[0]))
 g=forest(c,pins);exact(g,meta['graph_signs'],'Kruskal forest')
 solved=oa.solve(c.reshape(2,16,16),pins,OPTIONS)
 for k in solved:exact(solved[k],meta['optimizer'][k],'Prim optimizer '+k)
 median=float(statistics.median(abs(float(v)) for v in o.ravel() if v!=0)) if np.any(o) else 0.
 assert median==meta['median'];m=solved['signs'].reshape(256);_,edges=oa.geometry()
 z=o.copy().ravel();gp=np.empty(512);mp=np.empty(512)
 for e,(u,v) in enumerate(edges):
  magnitude=abs(float(o.ravel()[e])) if o.ravel()[e] else median
  gp[e]=magnitude*int(g[u])*int(g[v]);mp[e]=magnitude*int(m[u])*int(m[v])
  if o.ravel()[e]==0 and median>0:z[e]=median*int(m[u])*int(m[v])
 ga,gcost=gate(g,c,pins);ma,mcost=gate(m,c,pins,g,solved['selected_improvable_nodes'])
 expected=np.stack((o.ravel(),z,gp,mp,gp if ga else o.ravel(),mp if ma else o.ravel())).reshape(6,2,256)
 exact(rows,expected,'independent proposals')
 for a,(name,row) in enumerate(zip(ARMS,rows)):
  d=meta['decisions'][a];is_eligible=ga if name in ('G','GA') else ma if name in ('M','MA') else None
  assert d['historical_status']=='UNVERIFIED' and d['structurally_eligible']==is_eligible
  abstain=name in ('GA','MA') and not is_eligible
  action='abstain' if abstain else 'edit' if row.tobytes()!=o.tobytes() else 'no_change'
  assert d['action']==action
  if abstain:exact(row,o,'abstention byte preservation')
  assert d['added_edges']==sum(x==0 and y!=0 for x,y in zip(o.ravel(),row.ravel()))
  assert d['flipped_nonzero_edges']==sum(x!=0 and x*y<0 for x,y in zip(o.ravel(),row.ravel()))
  assert d['changed_edge_values']==sum(x!=y for x,y in zip(o.ravel(),row.ravel()))
  assert d['total_abs_weight']==math.fsum(abs(float(y)) for y in row.ravel())
 return dict(forest_checks=1,optimizer_checks=1,packet_proposals=6,abstention_gates=2)

def corruption(original,acquired,block,case,rows,meta):
 raw=json.dumps([NS,int(block),'corruption',int(case)],separators=(',',':')).encode()
 seed=int.from_bytes(hashlib.sha256(raw).digest()[:16],'little');rng=np.random.Generator(np.random.PCG64(seed))
 observed=np.array([i for i,v in enumerate(original.ravel()) if v!=0],dtype=int)
 order=rng.permutation(observed);k=len(observed)//10;signs=1-2*rng.integers(0,2,k)
 exact(order,meta['permutation'],'corruption order');exact(signs,meta['low_amplitude_signs'],'corruption signs')
 median=float(statistics.median(abs(float(v)) for v in original.ravel() if v!=0)) if len(observed) else 0.
 expected=np.repeat(original.reshape(1,512),8,axis=0)
 for e in order[:k]:expected[1,e]=0.;expected[2,e]=-expected[2,e]
 for pos,e in enumerate(order[:k]):expected[3,e]=.05*median*int(signs[pos])
 for e in order[k:2*k]:expected[3,e]=-expected[3,e]
 for e in order[2*k:3*k]:expected[3,e]*=4
 expected[4]=acquired[(case//4)^1].ravel();_,edges=oa.geometry()
 g=np.ones(256,np.int8);rule=1 if (case//4)%2==0 else -1
 for i in n.PORTS[1]:g[i]=rule
 for i in n.PORTS[2]:g[i]=-rule
 wrong=g.copy()
 for port in n.PORTS[1:]:
  for i in port:wrong[i]=-wrong[i]
 for e,(u,v) in enumerate(edges):
  magnitude=abs(float(original.ravel()[e])) if original.ravel()[e] else median
  expected[5,e]=magnitude*int(g[u])*int(g[v]);expected[6,e]=magnitude*int(wrong[u])*int(wrong[v])
 expected[7]=0.
 exact(rows.reshape(8,512),expected,'independent corrupted records')
 exact(g,meta['balanced_signs'],'aligned field');exact(wrong,meta['wrong_signs'],'wrong field')
 for ri,field in ((5,g),(6,wrong)):
  c=oa.independent_coupling(rows[ri].reshape(2,16,16)).ravel()
  assert gate(field,c,sorted(map(int,n.PORTS[0])))[1]==0
  # Elementary cycle parity (zeros excluded) and input pin identities.
  assert all(field[p]==1 for p in n.PORTS[0])
 return dict(corruption_cases=1,balanced_zero_cost_controls=2)
