"""Bounded weighted sign synchronization; inputs exclude hidden own signs/outcomes."""
import math
import numpy as np
from reader import PORTS,incident
from sign_graph import grid_edges,parity

U,V=grid_edges()
COLORS=np.indices((16,16)).sum(axis=0)%2


def influence(outgoing):
    magnitude=abs(outgoing);den=incident(magnitude)
    neighbor=np.stack((np.roll(den,-1,-1),np.roll(den,-1,-2)))
    first=np.divide(magnitude,den[None],out=np.zeros_like(magnitude),where=den[None]>0)
    second=np.divide(magnitude,neighbor,out=np.zeros_like(magnitude),where=neighbor>0)
    return .5*(first+second)


def forest(coupling,pins):
    weight=abs(coupling).ravel();relative=np.signbit(coupling).ravel()
    parent=list(range(257))
    def root(node):
        while parent[node]!=node:
            parent[node]=parent[parent[node]];node=parent[node]
        return node
    for p in pins:parent[root(int(p))]=root(256)
    selected=[]
    for edge in sorted(np.flatnonzero(weight),key=lambda e:(-float(weight[e]),int(e))):
        a,b=root(int(U[edge])),root(int(V[edge]))
        if a!=b:
            parent[a]=b;selected.append(edge)
    result=parity(256,U[selected],V[selected],relative[selected],pins)
    assert result['ok']
    return (1-2*result['bits'].astype(int)).reshape(16,16)


def canonical(states,coupling,pins):
    support=coupling.ravel()!=0
    groups=parity(256,U[support],V[support],np.zeros(support.sum(),int))['component']
    flat=states.reshape(len(states),256).copy();pinned=set(groups[pins])
    for component in set(groups)-pinned:
        nodes=np.flatnonzero(groups==component)
        flat[:,nodes]*=flat[:,nodes[0],None]
    return flat.reshape(states.shape)


def field(states,coupling):
    h,v=coupling
    return (h*np.roll(states,-1,-1)+np.roll(h,1,-1)*np.roll(states,1,-1)
            +v*np.roll(states,-1,-2)+np.roll(v,1,-2)*np.roll(states,1,-2))


def cost(signs,coupling):
    bad=np.signbit(coupling.ravel()) ^ (signs.ravel()[U]!=signs.ravel()[V])
    return math.fsum(abs(float(w)) for w in coupling.ravel()[bad])


def solve(coupling,pins,options):
    assert coupling.shape==(2,16,16) and np.isfinite(coupling).all()
    pins=np.asarray(sorted(pins),int)
    count,limit=options['starts'],options['maximum_sweeps']
    random=np.random.Generator(np.random.PCG64(options['seed']))
    states=np.ones((count,16,16),dtype=np.int8)
    states[1]=forest(coupling,pins)
    states[2:]=1-2*random.integers(0,2,size=(count-2,16,16),dtype=np.int8)
    states.reshape(count,256)[:,pins]=1
    states=canonical(states,coupling,pins);initial=states.copy()
    allowed=np.ones((16,16),bool);allowed.ravel()[pins]=False
    flips=np.zeros(count,int)
    for sweep in range(limit):
        changed=0
        for color in (0,1):
            flip=(states*field(states,coupling)<0)&allowed&(COLORS==color)
            changes=flip.sum(axis=(1,2));flips+=changes;changed+=int(changes.sum())
            states[flip]*=-1
        if not changed:break
    states=canonical(states,coupling,pins)
    candidates=np.concatenate((initial,states))
    values=[cost(g,coupling) for g in candidates]
    selected=min(range(len(candidates)),key=lambda i:(values[i],(candidates[i]<0).astype(np.uint8).tobytes()))
    selected_state=candidates[selected].copy()
    assert np.all(selected_state.ravel()[pins]==1) and values[selected]<=values[0]
    residual=((states*field(states,coupling)<0)&allowed).sum(axis=(1,2))
    total=math.fsum(abs(float(w)) for w in coupling.ravel())
    return dict(signs=selected_state,initial_cost=values[0],cost=values[selected],
        total_weight=total,mismatch_fraction=values[selected]/total if total else 0.,
        candidate_costs=np.array(values),winner=selected,sweeps=sweep+1,
        flips=flips,final_improvable_nodes=residual,
        selected_improvable_nodes=int(((selected_state*field(selected_state,coupling)<0)&allowed).sum()))


def align(outgoing,donor,options):
    overlap=(outgoing!=0)&(donor!=0)
    coupling=influence(outgoing)*np.sign(outgoing)*np.sign(donor)*overlap
    return solve(coupling,np.flatnonzero(PORTS.any(axis=0).ravel()),options)


def complete(outgoing,options):
    coupling=influence(outgoing)*np.sign(outgoing)
    return solve(coupling,np.flatnonzero(PORTS[0].ravel()),options)


def graft(outgoing,donor_signs,common,magnitudes,node_signs=None):
    assert not outgoing[common].any() and np.all(magnitudes[common]>0)
    result=outgoing.copy();signs=np.sign(donor_signs).copy()
    if node_signs is not None:
        signs*=np.stack((node_signs*np.roll(node_signs,-1,-1),node_signs*np.roll(node_signs,-1,-2)))
    assert np.all(abs(signs[common])==1)
    result[common]=magnitudes[common]*signs[common]
    return result
