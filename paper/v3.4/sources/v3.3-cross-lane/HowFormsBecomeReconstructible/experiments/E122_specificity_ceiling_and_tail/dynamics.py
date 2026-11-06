"""Two renewal slots, same per-recipient streams and native float64 equations."""
import numpy as np
from common import rng
from E006_compact_renewal import run as compact
from E122_specificity_ceiling_and_tail.plan import CFG

tissue=compact.tissue

def read(packets,block,phase,factor,cfg=CFG):
    arms=tuple('slot_'+str(i) for i in range(packets.shape[2]))
    return tissue.read_packets(packets,block+1000000,phase,factor=factor,arms=arms,cfg=cfg)

def generation(packets,block,number,factor,cfg=CFG):
    state,birth,mask=read(packets,block,f'g{number}',factor,cfg)
    v,ema,ref=[state[:,:,:,i].copy() for i in range(3)]
    field=np.zeros_like(v)
    random=rng(tissue.TAG,block+1000000,f'g{number}','write')
    for _ in range(cfg.write):
        noise=random.standard_normal((4,2,1,16,16))
        v,ema,ref,field=tissue.step(v,ema,ref,field,noise,gain=cfg.gain,writing=True,cfg=cfg)
    return tissue.pack(field,factor),dict(read=state,birth=birth,mask=mask,written=np.stack((v,ema,ref,field),axis=3))

def counts(state,prototypes):
    """All-target sign/amplitude joint counts, with zero signed as nonpositive."""
    v=state[:,:,:,0]
    sign=(v[...,None,:,:]>0)==(prototypes[None,None,None]>0)
    amplitude=np.broadcast_to((abs(v)>.2)[...,None,:,:],sign.shape)
    joint=np.empty((*sign.shape[:-2],2,2),np.uint16)
    for s in range(2):
        for a in range(2):joint[...,s,a]=((sign==bool(s))&(amplitude==bool(a))).sum(axis=(-2,-1))
    assert (joint.sum(axis=(-2,-1))==256).all()
    return joint

def pair_counts(state,prototypes):
    v=state[:,:,:,0]; sign=(v>0)==(prototypes[:,None,None]>0);amp=abs(v)>.2
    result=[]
    for left,right in ((0,1),(2,3)):
        comparisons=[]
        for x in (sign&amp,sign,amp):
            l,r=x[:,:,left],x[:,:,right]
            comparisons.append(np.stack(((l&~r).sum(axis=(-2,-1)),(~l&r).sum(axis=(-2,-1))),axis=-1))
        result.append(np.stack(comparisons,axis=-2))
    return np.stack(result,axis=2).astype(np.uint16)
