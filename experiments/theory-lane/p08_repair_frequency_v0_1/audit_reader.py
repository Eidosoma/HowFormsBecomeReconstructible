"""Separate native reader using flat explicit neighbor indices, no reader import."""
from collections import deque
import hashlib
import json

import numpy as np


def replay(packets,mask,founder,recipient,block,replicate,cfg,budgets=None,original=False,generation=14,rhos=None):
    if original:
        parts=['E022',block,'develop',generation]
    else:
        parts=[cfg['random_namespace'],block,'read',replicate]
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    random=np.random.Generator(np.random.PCG64(seed))
    innovation_parts=[cfg['innovation_namespace'],block,'innovation',generation]
    innovation_seed=int.from_bytes(hashlib.sha256(json.dumps(innovation_parts,separators=(',',':')).encode()).digest()[:16],'little')
    innovation=np.random.Generator(np.random.PCG64(innovation_seed))
    rhos=np.repeat(cfg['correlations'],2) if rhos is None else rhos
    assert len(rhos)==len(packets) and original
    parameters=cfg['reader']
    budgets=cfg['budgets'] if budgets is None else budgets
    n=len(packets)
    weight=np.frombuffer(packets.tobytes(),dtype='<f8').reshape(n,2,16,16).copy()
    ij=np.arange(256).reshape(16,16)
    right=np.array([ij[y,(x+1)%16] for y in range(16) for x in range(16)])
    left=np.array([ij[y,(x-1)%16] for y in range(16) for x in range(16)])
    down=np.array([ij[(y+1)%16,x] for y in range(16) for x in range(16)])
    up=np.array([ij[(y-1)%16,x] for y in range(16) for x in range(16)])
    dead=mask.ravel()
    h=weight[:,0].reshape(n,256)*((~dead)&(~dead[right]))
    v=weight[:,1].reshape(n,256)*((~dead)&(~dead[down]))
    directions=[h,h[:,left],v,v[:,up]]
    denom=abs(h)+abs(h[:,left])+abs(v)+abs(v[:,up])
    port_indices=[[16*y+x for y in range(row,row+2) for x in range(col,col+2)]
                  for row,col in ((7,1),(3,10),(11,10))]
    base=random.standard_normal((2,4,16,16))[founder//2,recipient].ravel()
    innovation.standard_normal((2,4,16,16))
    birth=np.stack([parameters['birth_sd']*base]*2)
    value=np.repeat(birth[None],n,axis=0)
    value*=(~dead)[None,None]
    value[:,:,port_indices[0]]=np.array([1.,-1.])[None,:,None]
    ends,means,windows=[],[],[]
    recent=deque(maxlen=parameters['observe_steps'])
    for t in range(max(budgets)):
        z=random.standard_normal((2,4,16,16))[founder//2,recipient].ravel()
        e=innovation.standard_normal((2,4,16,16))[founder//2,recipient].ravel()
        noise=np.stack([np.stack((z,z.copy() if rho==1. else rho*z+np.sqrt(1.-rho*rho)*e)) for rho in rhos])
        incoming=(directions[0][:,None]*value[:,:,right]+directions[1][:,None]*value[:,:,left]
                  +directions[2][:,None]*value[:,:,down]+directions[3][:,None]*value[:,:,up])
        local=np.divide(incoming,denom[:,None],out=np.zeros_like(incoming),where=denom[:,None]>0)
        drift=(value-value**3 if t>=cfg['settling_steps'] else -value**3)+2.*(local-value)
        value=np.clip(value+parameters['dt']*drift+parameters['noise']*noise,-2.,2.)
        value*=(~dead)[None,None]
        value[:,:,port_indices[0]]=np.array([1.,-1.])[None,:,None]
        if any(b-parameters['observe_steps']<=t<b for b in budgets):
            recent.append(np.stack([value[:,:,p].mean(axis=-1) for p in port_indices[1:]],axis=-1))
        if t+1 in budgets:
            window=np.stack(recent)
            ends.append(value.copy().reshape(n,2,16,16));means.append(window.mean(axis=0));windows.append(window)
            recent.clear()
    return dict(birth=birth.reshape(2,16,16),end=np.stack(ends),mean_ports=np.stack(means),port_windows=np.stack(windows))


def transfer(packets,mask,founder,steps):
    # Dense operator check of the fixed masked signed and unsigned diagnostics.
    n=len(packets)
    weights=np.frombuffer(packets.tobytes(),dtype='<f8').reshape(n,2,16,16)
    result=np.zeros((n,2))
    ports=[[16*y+x for y in range(row,row+2) for x in range(col,col+2)]
           for row,col in ((7,1),(3,10),(11,10))]
    for variant in range(n):
        op=np.zeros((256,256))
        for y in range(16):
            for x in range(16):
                for plane,(yy,xx) in enumerate(((y,(x+1)%16),((y+1)%16,x))):
                    w=0. if mask[y,x] or mask[yy,xx] else weights[variant,plane,y,x]
                    op[16*y+x,16*yy+xx]=op[16*yy+xx,16*y+x]=w
        denominator=abs(op).sum(axis=1)
        op=np.divide(op,denominator[:,None],out=np.zeros_like(op),where=denominator[:,None]>0)
        for kind,matrix in enumerate((op,abs(op))):
            field=np.zeros(256);field[ports[0]]=1.
            for _ in range(steps):
                field=matrix@field;field[ports[0]]=1.
            a,b=(field[p].mean() for p in ports[1:])
            rule=1 if founder%2==0 else -1
            result[variant,kind]=min(rule*a,-rule*b) if kind==0 else min(a,b)
    return result
