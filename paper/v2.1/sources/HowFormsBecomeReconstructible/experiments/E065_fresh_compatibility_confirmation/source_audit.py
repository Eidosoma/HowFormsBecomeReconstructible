"""Independent equation replay of the retained source branches."""
import time
import numpy as np
from E015_functional_inheritance.audit import random,pair,unpack,pack,ports,advance
from E022_reader_compensation.audit import advance_compensated,source_record
from E055_stress_capture_recovery import audit_model as pulse
from E055_stress_capture_recovery.audit_model import masks,alive_edges as alive,digest
P=ports()

def rebuild(incoming,block,g,cfg,cycle,namespace):
    started=time.monotonic()
    assert namespace in ('E022','E058')
    N,F,R=incoming.shape[:-1]
    assert F==4 and N in (1,2)
    mask=masks(block,R,f'{namespace}_renewal_g{g}')[:,:,1]; physical=alive(mask)
    old=unpack(incoming).reshape(N,F,R,2,16,16)*physical
    d=np.empty((N,F,R,16,16));a=abs(old)
    for y,x in np.ndindex(16,16):
        d[...,y,x]=a[...,0,y,x]+a[...,0,y,(x-1)%16]+a[...,1,y,x]+a[...,1,(y-1)%16,x]
    stream=random(namespace,block,'develop',g); shape=(2,R,16,16)
    birth=cfg['birth_sd']*pair(stream.standard_normal(shape))
    v=np.empty((N,F,R,2,16,16))
    for n,c in np.ndindex(N,2):v[n,:,:,c]=birth
    live=(~mask)[None,:,:,None];cue=np.array([1.,-1.]).reshape(1,1,1,2,1)
    v*=live;v[...,P[0]]=cue;trace=[];hashes=[]
    read_started=time.monotonic()
    for t in range(cycle['read_steps']):
        eta=pair(stream.standard_normal(shape))[None,:,:,None]
        v=advance_compensated(v,old[:,:,:,None],d[:,:,:,None],eta,cfg,t>=cycle['settling_steps'])
        v*=live;v[...,P[0]]=cue;hashes.append(digest(v))
        if t>=cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
    read_seconds=time.monotonic()-read_started
    end=v.copy();trace=np.array(trace);x=np.tanh(cfg['writer_beta']*end)
    ordinary=np.empty_like(old);contrast=np.empty_like(old)
    for direction,y,col in np.ndindex(2,16,16):
        yy,xx=(y,(col+1)%16) if direction==0 else ((y+1)%16,col)
        a,b=x[...,y,col],x[...,yy,xx]
        contrast[...,direction,y,col]=((a[...,0]-a[...,1])/2)*((b[...,0]-b[...,1])/2)
        total=np.zeros(a.shape[:-1]);total+=a[...,0]*b[...,0];total+=a[...,1]*b[...,1];total/=2
        ordinary[...,direction,y,col]=total
    fallback=(contrast==0)&physical
    outgoing=np.zeros_like(contrast);good=np.broadcast_to(physical,contrast.shape)
    outgoing[good]=contrast[good];outgoing[fallback]=ordinary[fallback]
    stream=random(namespace,block,'write',g);scaffold=physical[None,:,:,None].astype(float);write_hashes=[]
    write_started=time.monotonic()
    for _ in range(cycle['write_steps']):
        eta=pair(stream.standard_normal(shape))[None,:,:,None]
        v=advance(v,scaffold,2.,eta,cfg);v*=live;v[...,P[0]]=cue;write_hashes.append(digest(v))
    write_seconds=time.monotonic()-write_started
    raw=dict(incoming=incoming.copy(),masks=mask,effective_packets=pack(old),denominator=d,
        birth=birth,end=end,late_ports=trace,mean_ports=trace.mean(axis=0),ordinary=ordinary,contrast=contrast,
        fallback=fallback,outgoing=pack(outgoing).reshape(incoming.shape),read_state_hashes=np.array(hashes),
        write_end=v,write_state_hashes=np.array(write_hashes))


    return raw,dict(read=read_seconds,write=write_seconds,static=time.monotonic()-started-read_seconds-write_seconds)


def perturb(packets,block,cfg):
    body=pulse.develop(unpack(packets),block,cfg)
    out=pulse.transmit(body,cfg)
    for key in ('states','port_windows','mean_ports'):
        assert np.array_equal(body[key][:,:,1].view(np.uint8),body[key][:,:,2].view(np.uint8))
        body[key]=body[key][:,:,:2].copy()
    outgoing={key:out[key][0,:2].copy() for key in ('packets','ordinary','contrast','fallback')}
    return body,outgoing
