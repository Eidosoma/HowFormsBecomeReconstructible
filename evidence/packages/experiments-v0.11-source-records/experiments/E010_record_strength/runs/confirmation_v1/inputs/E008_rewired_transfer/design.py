"""E003 assay with a degree-four target graph containing 25% long-range edges."""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E003_cross_embodiment import design as base
import numpy as np

CFG = base.CFG
DEV_IDS = tuple(range(5000,5016))
TEST_IDS = tuple(range(6000,6032))
BENCH_ID = 900008
REFERENCE = base.REFERENCE
DEVELOPMENT = base.DEVELOPMENT
JOINT = base.JOINT
TEST = base.TEST
MODELS = base.MODELS
observations = base.observations
features = base.features
fit_ridge = base.fit_ridge
predict = base.predict
tissue = base.tissue


def native_edges():
    edges = set()
    for y in range(16):
        for x in range(16):
            i = 16*y+x
            for j in (16*y+(x+1)%16,16*((y+1)%16)+x):
                edges.add(tuple(sorted((i,j))))
    return edges


def distance(a,b):
    ay,ax = divmod(a,16); by,bx = divmod(b,16)
    dx = abs(ax-bx); dy = abs(ay-by)
    return min(dx,16-dx)+min(dy,16-dy)


def adjacency(edges):
    lists = [[] for _ in range(256)]
    for a,b in edges: lists[a].append(b); lists[b].append(a)
    if any(len(x)!=4 for x in lists): raise ValueError("Degree four required")
    return np.array([sorted(x) for x in lists],dtype=np.int64)


def connected(edges):
    graph = adjacency(edges)
    seen = {0}; stack = [0]
    while stack:
        for n in graph[stack.pop()]:
            n = int(n)
            if n not in seen: seen.add(n); stack.append(n)
    return len(seen)==256


def rewire(block):
    original = native_edges(); edges = original.copy(); remaining = sorted(original)
    random = rng("E008",block,"rewiring")
    swaps = []; attempts = 0
    while len(swaps)<64:
        attempts += 1
        if attempts>100000: raise RuntimeError("Rewiring proposal limit exceeded")
        i,j = random.choice(len(remaining),size=2,replace=False)
        first,second = remaining[int(i)],remaining[int(j)]
        a,b = first; c,e = second
        flip = bool(random.integers(0,2))
        if len({a,b,c,e})!=4: continue
        proposed = ((a,e),(b,c)) if flip else ((a,c),(b,e))
        proposed = tuple(tuple(sorted(edge)) for edge in proposed)
        if any(edge in edges or distance(*edge)<4 for edge in proposed): continue
        trial = edges-{first,second}|set(proposed)
        if not connected(trial): continue
        swaps.append((first,second,*proposed)); edges = trial
        remaining = [edge for edge in remaining if edge not in (first,second)]
    assert len(original-edges)==128 and len(edges-original)==128
    return dict(graph_original_edges=np.array(sorted(original),dtype=np.int64),
                graph_edges=np.array(sorted(edges),dtype=np.int64), graph_neighbors=adjacency(edges),
                graph_swaps=np.array(swaps,dtype=np.int64), graph_attempts=np.array(attempts))


def make_source(block,cfg=CFG):
    source = base.make_source(block,cfg)
    source.update(rewire(block))
    return source


def step(v,ema,ref,field,noise,embodiment,neighbors=None,cfg=CFG):
    if embodiment=="A": return tissue.step(v,ema,ref,field,noise,cfg=cfg)
    if embodiment!="B" or neighbors is None: raise ValueError("B needs its public adjacency")
    flat = v.reshape(*v.shape[:-2],256)
    neighbor_mean = flat[...,neighbors].mean(axis=-1).reshape(v.shape)
    drift = tissue.centered(v-v**3+field+(neighbor_mean-v))
    v = np.clip(v+cfg.dt*drift+tissue.centered(cfg.sigma*noise),-2.,2.)
    ema = .9*ema+.1*v
    ref = ref+cfg.rho*(v-ref)
    return v,ema,ref,field


def read(acquired,block,embodiment,conditions,neighbors,cfg=CFG):
    packets,masks,deleted = base.packets_and_masks(acquired,block,conditions,cfg)
    field = tissue.unpack(packets)
    shape = (cfg.founders,cfg.recipients,1,cfg.side,cfg.side)
    birth = .2*tissue.centered(rng("E003",block,embodiment,"birth").standard_normal(shape))
    v = np.repeat(birth,len(conditions),axis=2)
    ema = v.copy(); ref = v.copy()
    random = rng("E003",block,embodiment,"read")
    before = after = None
    for t in range(1,cfg.read+1):
        v,ema,ref,_ = step(v,ema,ref,field,random.standard_normal(shape),embodiment,neighbors,cfg)
        if t==cfg.challenge_time:
            before = v.copy(); v = np.where(masks,-v,v); after = v.copy()
    if before is None: raise ValueError("Challenge time outside read")
    return dict(packets=packets,birth=birth,body_masks=masks,deletion_masks=deleted,
                before_damage=before,after_damage=after,end=np.stack((v,ema,ref),axis=3),
                applied_neighbors=adjacency(native_edges()) if embodiment=="A" else neighbors.copy())
