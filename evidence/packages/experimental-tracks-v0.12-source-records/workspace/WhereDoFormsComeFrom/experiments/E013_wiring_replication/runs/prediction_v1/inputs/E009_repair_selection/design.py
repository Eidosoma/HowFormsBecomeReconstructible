"""Fixed repair menus and policies using the untouched E008 predictive map."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import rng
from E008_rewired_transfer import design as old
import numpy as np

CFG=old.CFG
IDS=tuple(range(7000,7064))
BENCH_ID=900109
MODEL_PATH=ROOT/"E008_rewired_transfer/runs/development_v1/models.json"
MODEL_SHA="c4dfd0030b5a22c48e0b78b3ad1781cf566f1f2be13549297dd6f8f8f7bca59f"
POLICIES=("map","source","heuristic","random")
N_OPTIONS=8
CONDITIONS=(dict(name="intact",damage=0.,mixture=0.,deletion=0.),
            dict(name="unrepaired",damage=0.,mixture=0.,deletion=.75),
            dict(name="foreign",damage=0.,mixture=1.,deletion=0.),
            dict(name="erased",damage=0.,mixture=0.,deletion=1.),
            *tuple(dict(name=f"repair_{i}",damage=0.,mixture=0.,deletion=.5) for i in range(N_OPTIONS)))


def make_menu(acquired,block):
    clean=old.tissue.unpack(acquired[:,0]).reshape(4,256)
    injury=[];restore=[];heuristic=[]
    for f in range(4):
        erased=rng("E009",block,f,"injury").choice(256,192,replace=False)
        mask=np.zeros(256,dtype=bool);mask[erased]=True
        selected=sorted(erased.tolist(),key=lambda i:(-abs(clean[f,i]),i))[:64]
        candidates=[tuple(sorted(selected))];seen=set(candidates)
        random=rng("E009",block,f,"repair_candidates")
        attempts=0
        while len(candidates)<N_OPTIONS:
            attempts+=1
            if attempts>100000:raise RuntimeError("Candidate generation limit exceeded")
            option=tuple(sorted(random.choice(erased,64,replace=False).tolist()))
            if option not in seen:candidates.append(option);seen.add(option)
        order=rng("E009",block,f,"menu_order").permutation(N_OPTIONS)
        options=np.zeros((N_OPTIONS,256),dtype=bool)
        for i,j in enumerate(order):options[i,list(candidates[int(j)])]=True
        injury.append(mask);restore.append(options);heuristic.append(int(np.flatnonzero(order==0)[0]))
    injury=np.array(injury);restore=np.array(restore)
    fields=np.repeat(clean[:,None],len(CONDITIONS),axis=1)
    fields[:,1]=np.where(injury,0.,clean)
    fields[:,2]=np.roll(clean,-1,axis=0)
    fields[:,3]=0.
    fields[:,4:]=np.where(injury[:,None]&~restore,0.,clean[:,None])
    packets=old.tissue.pack(fields.reshape(4,len(CONDITIONS),16,16))
    return dict(repair_injury=injury,repair_restoration=restore,
                repair_heuristic=np.array(heuristic,dtype=np.int64),repair_packets=packets)


def make_source(block,cfg=CFG):
    source=old.make_source(block,cfg)
    source.update(make_menu(source["acquired"],block))
    return source


def read(packets,block,body,neighbors,cfg=CFG):
    # Only packet values, graph and public stream coordinates enter the body.
    field=old.tissue.unpack(np.repeat(packets[:,None],cfg.recipients,axis=1))
    shape=(cfg.founders,cfg.recipients,1,cfg.side,cfg.side)
    birth=.2*old.tissue.centered(rng("E009",block,body,"birth").standard_normal(shape))
    v=np.repeat(birth,field.shape[2],axis=2);ema=v.copy();ref=v.copy()
    random=rng("E009",block,body,"read")
    for _ in range(cfg.read):
        v,ema,ref,_=old.step(v,ema,ref,field,random.standard_normal(shape),body,neighbors,cfg)
    return dict(packets=np.repeat(packets[:,None],cfg.recipients,axis=1),birth=birth,
                end=np.stack((v,ema,ref),axis=3),
                applied_neighbors=old.adjacency(old.native_edges()) if body=="A" else neighbors.copy())


def select(prototype,observed_a,heuristic,models):
    x=old.features(prototype,observed_a,CONDITIONS)["causal"]
    m=models["causal"]
    predicted=np.clip((x/np.array(m["scale"]))@np.array(m["coefficients"]),-1,1)
    predicted_margin=predicted[:,4:,0]-predicted[:,4:,1]
    source_margin=observed_a[:,4:,0]-observed_a[:,4:,1]
    choices=np.stack((np.argmax(predicted_margin,axis=1),np.argmax(source_margin,axis=1),heuristic),axis=1)
    weights=np.zeros((4,len(POLICIES),N_OPTIONS))
    for f in range(4):
        for p in range(3):weights[f,p,choices[f,p]]=1.
    weights[:,3]=1./N_OPTIONS
    return dict(predicted=predicted,choices=choices,weights=weights,observed_A=observed_a)
