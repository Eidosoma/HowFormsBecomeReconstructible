"""Equal-count restoration by record magnitude; prototypes enter observers only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import rng
from E008_rewired_transfer import design as base
import numpy as np

CFG=base.CFG
IDS=tuple(range(8000,8064))
BENCH_ID=900210
POLICIES=("weak","strong","random")
CONDITIONS=("intact","unrepaired","erased","foreign_1","foreign_2","foreign_3",*POLICIES)


def make_repairs(acquired,block):
    clean=base.tissue.unpack(acquired[:,0]).reshape(4,256)
    injury=np.zeros((4,256),dtype=bool)
    restoration=np.zeros((4,3,256),dtype=bool)
    for f in range(4):
        sites=rng("E010",block,f,"injury").choice(256,192,replace=False)
        injury[f,sites]=True
        weak=sorted(sites.tolist(),key=lambda i:(abs(clean[f,i]),i))[:64]
        strong=sorted(sites.tolist(),key=lambda i:(-abs(clean[f,i]),i))[:64]
        random=rng("E010",block,f,"random_repair").choice(sites,64,replace=False)
        for j,subset in enumerate((weak,strong,random)):restoration[f,j,subset]=True
    fields=np.repeat(clean[:,None],len(CONDITIONS),axis=1)
    fields[:,1]=np.where(injury,0.,clean);fields[:,2]=0.
    for offset in (1,2,3):fields[:,offset+2]=np.roll(clean,-offset,axis=0)
    fields[:,6:]=np.where(injury[:,None]&~restoration,0.,clean[:,None])
    return dict(repair_injury=injury,repair_restoration=restoration,
        repair_packets=base.tissue.pack(fields.reshape(4,len(CONDITIONS),16,16)))


def make_source(block,cfg=CFG):
    source=base.make_source(block,cfg)
    source.update(make_repairs(source["acquired"],block))
    return source


def read(packets,block,body,neighbors,cfg=CFG):
    received=np.repeat(packets[:,None],cfg.recipients,axis=1)
    field=base.tissue.unpack(received)
    shape=(cfg.founders,cfg.recipients,1,cfg.side,cfg.side)
    birth=.2*base.tissue.centered(rng("E010",block,body,"birth").standard_normal(shape))
    v=np.repeat(birth,field.shape[2],axis=2);ema=v.copy();ref=v.copy()
    random=rng("E010",block,body,"read")
    for _ in range(cfg.read):
        v,ema,ref,_=base.step(v,ema,ref,field,random.standard_normal(shape),body,neighbors,cfg)
    return dict(packets=received,birth=birth,end=np.stack((v,ema,ref),axis=3),
        applied_neighbors=base.adjacency(base.native_edges()) if body=="A" else neighbors.copy())


def observe(raw,prototype):
    v=raw["end"][:,:,:,0];resolved=abs(v)>.2;sign=v>0
    agreement=(resolved[:,:,:,None] & (sign[:,:,:,None]==(prototype[None,None,None]>0))).mean(axis=(-2,-1))
    own=np.stack([agreement[f,:,:,f] for f in range(4)])
    foreign=(agreement.sum(axis=3)-own)/3
    neighbor=((sign==np.roll(sign,1,-1)).mean(axis=(-2,-1))+(sign==np.roll(sign,1,-2)).mean(axis=(-2,-1)))/2
    individual=np.stack((own,foreign,resolved.mean(axis=(-2,-1)),neighbor),axis=-1)
    return dict(agreement=agreement,individual=individual,observed=individual.mean(axis=1))


def repair_descriptors(source):
    clean=base.tissue.unpack(source["acquired"][:,0]).reshape(4,256)
    signs=source["prototype"].reshape(4,256)>0
    restoration=source["repair_restoration"]
    magnitude=(restoration*abs(clean[:,None])).sum(axis=2)
    distinguishing=np.stack([(restoration&(signs!=np.roll(signs,-offset,axis=0))[:,None]).sum(axis=2)/64
                            for offset in (1,2,3)],axis=-1)
    return dict(mean_absolute_value=magnitude/64,total_absolute_value=magnitude,
                distinguishing_by_foreign=distinguishing,
                distinguishing_fraction=distinguishing.mean(axis=2))
