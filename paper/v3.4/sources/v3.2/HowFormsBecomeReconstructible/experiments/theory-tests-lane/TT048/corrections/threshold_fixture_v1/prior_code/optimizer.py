"""Independent flat-graph implementation of the fixed optimization contract.

The forest uses Boruvka component cuts, not source Kruskal or its Prim checker.
No source module is imported. Solver arguments cannot carry missing own records,
task outcomes, writer provenance, assessment masks or body states.
"""
from fractions import Fraction
import math
import numpy as np
import native as n
import support as s

U=np.tile(np.arange(256),2);V=np.concatenate((n.RIGHT,n.DOWN))
COLOR=(n.Y+n.X)%2
ALL_PINS=sorted(np.concatenate(n.PORTS).tolist())
INPUT_PINS=sorted(n.PORTS[0].tolist())


def coupling(outgoing,donor=None):
    s.require(outgoing.shape==(2,256) and np.isfinite(outgoing).all(),'Finite outgoing record')
    a=abs(outgoing);h,v=a
    den=h+h[n.LEFT]+v+v[n.UP]
    edge=a.ravel();first=np.zeros(512);second=np.zeros(512)
    np.divide(edge,den[U],out=first,where=den[U]>0)
    np.divide(edge,den[V],out=second,where=den[V]>0)
    answer=.5*(first+second)*np.sign(outgoing.ravel())
    if donor is not None:
        s.require(donor.shape==outgoing.shape and np.isfinite(donor).all(),'Finite donor record')
        answer*=np.sign(donor.ravel())
    return answer


def groups(c):
    neighbors=[[] for _ in range(256)]
    for e in np.flatnonzero(c):
        u,v=int(U[e]),int(V[e]);neighbors[u].append(v);neighbors[v].append(u)
    unseen=set(range(256));answer=[]
    while unseen:
        todo=[min(unseen)];unseen.remove(todo[0]);nodes=[]
        while todo:
            u=todo.pop();nodes.append(u)
            for v in neighbors[u]:
                if v in unseen:unseen.remove(v);todo.append(v)
        answer.append(sorted(nodes))
    return answer


def canonical(states,components,pins):
    result=states.copy();fixed=set(pins)
    for nodes in components:
        if not fixed.intersection(nodes):result[:,nodes]*=result[:,nodes[0],None]
    return result


def forest(c,pins):
    # All pins are joined to virtual ground before maximum-forest construction.
    parent=list(range(257))
    def root(u):
        while parent[u]!=u:u=parent[u]
        return u
    for p in pins:parent[p]=256
    selected=[];edges=list(map(int,np.flatnonzero(c)))
    priority=lambda e:(-abs(float(c[e])),e)
    while True:
        cheapest={}
        for e in edges:
            a,b=root(int(U[e])),root(int(V[e]))
            if a==b:continue
            for component in (a,b):
                if component not in cheapest or priority(e)<priority(cheapest[component]):cheapest[component]=e
        if not cheapest:break
        for e in sorted(set(cheapest.values()),key=priority):
            a,b=root(int(U[e])),root(int(V[e]))
            if a!=b:parent[a]=b;selected.append(e)
    adjacency=[[] for _ in range(256)]
    for e in selected:
        u,v=int(U[e]),int(V[e]);sign=1 if c[e]>0 else -1
        adjacency[u].append((v,sign));adjacency[v].append((u,sign))
    answer=np.zeros(256,dtype=np.int8)
    for seed in list(pins)+list(range(256)):
        if answer[seed]:continue
        answer[seed]=1;todo=[seed]
        while todo:
            u=todo.pop()
            for v,sign in adjacency[u]:
                if not answer[v]:answer[v]=answer[u]*sign;todo.append(v)
                else:s.require(answer[v]==answer[u]*sign,'Forest is balanced')
    s.require(np.all(answer[pins]==1),'Forest respects pins')
    return answer


def field(states,c):
    h,v=c[:256],c[256:]
    return h*states[...,n.RIGHT]+h[n.LEFT]*states[...,n.LEFT]+v*states[...,n.DOWN]+v[n.UP]*states[...,n.UP]


def objective(state,c):
    return math.fsum(abs(float(c[e])) for e in range(512) if c[e]!=0 and int(state[U[e]])*int(state[V[e]])!=(1 if c[e]>0 else -1))


def rational_objective(state,c):
    total=Fraction()
    for e,weight in enumerate(c):
        if float(weight)*int(state[U[e]])*int(state[V[e]])<0:total+=Fraction.from_float(abs(float(weight)))
    return float(total)


def solve(c,pins,options):
    s.require(c.shape==(512,) and np.isfinite(c).all(),'Finite 512-edge coupling')
    pins=list(pins);s.require(len(pins)==len(set(pins)) and all(type(p) is int and 0<=p<256 for p in pins),'Valid unique pins')
    pins=sorted(pins);count=options['starts'];limit=options['maximum_sweeps']
    s.require(type(count) is int and count>=2 and type(limit) is int and limit>=1,'Finite positive optimization budget')
    random=np.random.Generator(np.random.PCG64(options['seed']))
    states=np.ones((count,256),np.int8);states[1]=forest(c,pins)
    states[2:]=1-2*random.integers(0,2,size=(count-2,256),dtype=np.int8)
    states[:,pins]=1;components=groups(c);states=canonical(states,components,pins);initial=states.copy()
    allowed=np.ones(256,bool);allowed[pins]=False;flips=np.zeros(count,dtype=np.int64)
    for sweep in range(1,limit+1):
        changed=False
        for color in (0,1):
            chosen=(states*field(states,c)<0)&allowed&(COLOR==color)
            flips+=np.count_nonzero(chosen,axis=1);changed=changed or bool(chosen.any());states[chosen]=-states[chosen]
        if not changed:break
    states=canonical(states,components,pins);candidates=np.vstack((initial,states))
    values=np.array([objective(g,c) for g in candidates]);winner=min(range(2*count),key=lambda i:(values[i],bytes(candidates[i]<0)))
    chosen=candidates[winner].copy();residual=((states*field(states,c)<0)&allowed).sum(axis=1)
    total=math.fsum(map(abs,map(float,c)))
    s.require(values[winner]<=values[0] and np.all(chosen[pins]==1),'Optimizer admissibility and identity bound')
    s.require(rational_objective(chosen,c)==values[winner],'Rational objective accumulation')
    return dict(signs=chosen.reshape(16,16),candidate_costs=values,flips=flips,final_improvable_nodes=residual,
        cost=float(values[winner]),initial_cost=float(values[0]),winner=winner,sweeps=sweep,
        selected_improvable_nodes=int(((chosen*field(chosen,c)<0)&allowed).sum()),
        total_weight=total,mismatch_fraction=float(values[winner]/total) if total else 0.)


def scalar_local_check(signs,c):
    """Independent incident-edge summation checks the flip-cost identity."""
    g=signs.ravel();expected=np.zeros(256);entries=[[] for _ in range(256)]
    for e,weight in enumerate(c):
        u,v=int(U[e]),int(V[e]);entries[u].append(float(weight)*int(g[v]));entries[v].append(float(weight)*int(g[u]))
    for u,terms in enumerate(entries):expected[u]=math.fsum(terms)
    return s.close(expected,field(g,c),2e-14,'Scalar edge-local field')
