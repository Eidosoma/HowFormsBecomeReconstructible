"""Independent Prim initialization, flat local search, and direct edge costs."""
import heapq
import math
import numpy as np


def geometry():
    neighbors=np.array([[16*y+(x+1)%16,16*y+(x-1)%16,16*((y+1)%16)+x,16*((y-1)%16)+x]
                        for y in range(16) for x in range(16)])
    edges=[(16*y+x,16*y+(x+1)%16) for y in range(16) for x in range(16)]
    edges += [(16*y+x,16*((y+1)%16)+x) for y in range(16) for x in range(16)]
    return neighbors,edges


def independent_coupling(outgoing,donor=None):
    neighbors,edges=geometry();w=outgoing.ravel();den=np.zeros(256)
    # Match the native right, left, down, up accumulation order independently.
    for i in range(256):
        den[i]=abs(w[i])+abs(w[neighbors[i,1]])+abs(w[256+i])+abs(w[256+neighbors[i,3]])
    result=np.zeros(512)
    for e,(a,b) in enumerate(edges):
        if w[e]==0 or (donor is not None and donor.ravel()[e]==0):continue
        magnitude=.5*(abs(w[e])/den[a]+abs(w[e])/den[b])
        sign=(-1 if w[e]<0 else 1)*(1 if donor is None or donor.ravel()[e]>0 else -1)
        result[e]=magnitude*sign
    return result.reshape(2,16,16)


def solve(coupling,pins,options):
    neighbors,edges=geometry();j=coupling.ravel()
    adjacency=[[] for _ in range(256)]
    for edge,(a,b) in enumerate(edges):
        if j[edge]!=0:
            adjacency[a].append((b,edge));adjacency[b].append((a,edge))
    assigned=np.zeros(256,bool);tree=np.ones(256,np.int8);queue=[]
    def add(node):
        assigned[node]=True
        for other,edge in adjacency[node]:heapq.heappush(queue,(-abs(float(j[edge])),edge,node,other))
    for node in pins:add(int(node))
    while True:
        while queue:
            _,edge,a,b=heapq.heappop(queue)
            if assigned[b]:continue
            tree[b]=tree[a]*(1 if j[edge]>0 else -1);add(b)
        unseen=np.flatnonzero(~assigned)
        if not len(unseen):break
        add(int(unseen[0]))
    components=[];seen=set()
    for root in range(256):
        if root in seen:continue
        nodes=[root];seen.add(root)
        for node in nodes:
            for other,_ in adjacency[node]:
                if other not in seen:seen.add(other);nodes.append(other)
        if not set(nodes).intersection(int(p) for p in pins):components.append(sorted(nodes))
    def orient(states):
        states=states.copy()
        for group in components:states[:,group]*=states[:,group[0],None]
        return states
    random=np.random.Generator(np.random.PCG64(options['seed']))
    states=np.ones((options['starts'],256),np.int8);states[1]=tree
    states[2:]=(1-2*random.integers(0,2,(options['starts']-2,16,16),dtype=np.int8)).reshape(options['starts']-2,256)
    states[:,pins]=1;states=orient(states);initial=states.copy()
    directed=np.array([[j[i],j[neighbors[i,1]],j[256+i],j[256+neighbors[i,3]]] for i in range(256)])
    eligible=np.ones(256,bool);eligible[pins]=False
    colors=np.array([(i//16+i%16)%2 for i in range(256)])
    def local(state):
        return (directed[:,0]*state[:,neighbors[:,0]]+directed[:,1]*state[:,neighbors[:,1]]
                +directed[:,2]*state[:,neighbors[:,2]]+directed[:,3]*state[:,neighbors[:,3]])
    flips=np.zeros(len(states),int)
    for sweep in range(options['maximum_sweeps']):
        changed=0
        for color in (0,1):
            flip=(states*local(states)<0)&eligible&(colors==color)
            counts=flip.sum(axis=1);flips+=counts;changed+=int(counts.sum());states[flip]*=-1
        if changed==0:break
    states=orient(states)
    candidates=np.concatenate((initial,states))
    costs=[]
    for state in candidates:
        terms=[abs(float(j[e])) for e,(a,b) in enumerate(edges) if (state[a]*state[b]<0)!=(j[e]<0)]
        costs.append(math.fsum(terms))
    winner=min(range(len(candidates)),key=lambda i:(costs[i],bytes((candidates[i]<0).astype(np.uint8))))
    return dict(signs=candidates[winner].reshape(16,16),cost=costs[winner],initial_cost=costs[0],
                candidate_costs=np.array(costs),winner=winner,sweeps=sweep+1,flips=flips,
                final_improvable_nodes=((states*local(states)<0)&eligible).sum(axis=1),
                selected_improvable_nodes=int(((candidates[winner:winner+1]*local(candidates[winner:winner+1])<0)&eligible).sum()))
