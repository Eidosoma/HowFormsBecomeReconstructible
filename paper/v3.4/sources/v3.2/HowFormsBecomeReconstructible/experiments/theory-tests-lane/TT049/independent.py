"""Independent Kruskal forest, scalar packets/gates and corruption reconstruction."""
from study import *
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
