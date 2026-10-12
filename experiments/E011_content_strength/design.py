"""Fixed subsets crossed with original, low and high applied record values."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common import rng
from E010_record_strength import design as previous
import numpy as np

base=previous.base
CFG=base.CFG
IDS=tuple(range(9000,9064))
BENCH_ID=900311
POLICIES=("weak","strong","random")
MODES=("original","low","high")
LEVELS={"low":.15,"high":.40}
ARMS=tuple(mode+"_"+policy for mode in MODES for policy in POLICIES)
CONDITIONS=("intact","unrepaired","erased","foreign_1","foreign_2","foreign_3",*ARMS)
PRIMARY_CONTRASTS=("high_weak_minus_strong","high_weak_minus_random","weak_high_minus_low",
                   "interaction_strong","interaction_random")
observe=previous.observe


def make_repairs(acquired,block):
    clean=base.tissue.unpack(acquired[:,0]).reshape(4,256)
    injury=np.zeros((4,256),dtype=bool);restoration=np.zeros((4,3,256),dtype=bool)
    for f in range(4):
        sites=rng("E011",block,f,"injury").choice(256,192,replace=False)
        injury[f,sites]=True
        weak=sorted(sites.tolist(),key=lambda i:(abs(clean[f,i]),i))[:64]
        strong=sorted(sites.tolist(),key=lambda i:(-abs(clean[f,i]),i))[:64]
        random=rng("E011",block,f,"random_repair").choice(sites,64,replace=False)
        for j,subset in enumerate((weak,strong,random)):
            restoration[f,j,subset]=True
            if np.any(clean[f,subset]==0):raise ValueError("Selected zero backup value has no recorded sign")
    fields=np.repeat(clean[:,None],len(CONDITIONS),axis=1)
    fields[:,1]=np.where(injury,0.,clean);fields[:,2]=0.
    for offset in (1,2,3):fields[:,offset+2]=np.roll(clean,-offset,axis=0)
    for m,mode in enumerate(MODES):
        value=clean if mode=="original" else np.sign(clean)*LEVELS[mode]
        for j in range(3):
            fields[:,6+3*m+j]=np.where(restoration[:,j],value,np.where(injury,0.,clean))
    return dict(repair_injury=injury,repair_restoration=restoration,
        repair_packets=base.tissue.pack(fields.reshape(4,len(CONDITIONS),16,16)))


def make_source(block,cfg=CFG):
    source=base.make_source(block,cfg);source.update(make_repairs(source["acquired"],block));return source


def read(packets,block,body,neighbors,cfg=CFG):
    received=np.repeat(packets[:,None],cfg.recipients,axis=1);field=base.tissue.unpack(received)
    shape=(cfg.founders,cfg.recipients,1,cfg.side,cfg.side)
    birth=.2*base.tissue.centered(rng("E011",block,body,"birth").standard_normal(shape))
    v=np.repeat(birth,field.shape[2],axis=2);ema=v.copy();ref=v.copy()
    random=rng("E011",block,body,"read")
    for _ in range(cfg.read):v,ema,ref,_=base.step(v,ema,ref,field,random.standard_normal(shape),body,neighbors,cfg)
    return dict(packets=received,birth=birth,end=np.stack((v,ema,ref),axis=3),
        applied_neighbors=base.adjacency(base.native_edges()) if body=="A" else neighbors.copy())


def contrasts(utility):
    o_w,o_s,o_r,l_w,l_s,l_r,h_w,h_s,h_r=np.moveaxis(utility,-1,0)
    return dict(high_weak_minus_strong=h_w-h_s,high_weak_minus_random=h_w-h_r,
        weak_high_minus_low=h_w-l_w,strong_high_minus_low=h_s-l_s,random_high_minus_low=h_r-l_r,
        interaction_strong=(h_w-l_w)-(h_s-l_s),interaction_random=(h_w-l_w)-(h_r-l_r),
        low_weak_minus_strong=l_w-l_s,low_weak_minus_random=l_w-l_r,
        original_weak_minus_strong=o_w-o_s,original_weak_minus_random=o_w-o_r,
        high_weak_minus_original_weak=h_w-o_w)


def repair_descriptors(source):
    fields=base.tissue.unpack(source["repair_packets"]).reshape(4,15,256)[:,6:]
    restored=np.tile(source["repair_restoration"],(1,3,1))
    magnitude=(restored*abs(fields)).sum(axis=2)
    signs=source["prototype"].reshape(4,256)>0
    distinction=np.stack([(restored&(signs!=np.roll(signs,-offset,axis=0))[:,None]).sum(axis=2)/64
                          for offset in (1,2,3)],axis=-1)
    return dict(mean_absolute_value=magnitude/64,total_absolute_value=magnitude,
        applied_signed_sum=(restored*fields).sum(axis=2),centered_full_field_rms=fields.std(axis=2),
        distinguishing_by_foreign=distinction,distinguishing_fraction=distinction.mean(axis=2))
