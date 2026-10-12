"""Independent two-chain source equations; no production source imports."""
import numpy as np
from E015_functional_inheritance.audit import random, pair, unpack, pack, ports, advance
from E022_reader_compensation.audit import advance_compensated, masks_for, source_record
from E055_stress_capture_recovery.audit_model import alive_edges
from E056_sign_magnitude_substitution.audit_model import digest


def rebuild(incoming, block, g, cfg, cycle):
    R = cfg['recipients']; p = ports()
    mask = masks_for(block, g, R, renewal=True)[:, :, 1]
    physical = alive_edges(mask); old = unpack(incoming)*physical
    denominator = np.empty(old.shape[:-3]+(16,16))
    for y,x in np.ndindex(16,16):
        a=abs(old)
        denominator[...,y,x]=a[...,0,y,x]+a[...,0,y,(x-1)%16]+a[...,1,y,x]+a[...,1,(y-1)%16,x]
    stream=random('E022',block,'develop',g); innovation=random('E051',block,'innovation',g)
    shape=(2,R,16,16); z=stream.standard_normal(shape); innovation.standard_normal(shape)
    birth=np.empty((2,4,R,2,16,16))
    for n,c in np.ndindex(2,2): birth[n,:,:,c]=cfg['birth_sd']*pair(z)
    v=birth.copy(); live=(~mask)[None,:,:,None]
    cue=np.array([1.,-1.]).reshape(1,1,1,2,1)
    v*=live; v[...,p[0]]=cue
    trace=[]; hashes=[]; moments=np.zeros((2,6))
    for t in range(cycle['read_steps']):
        z,e=stream.standard_normal(shape),innovation.standard_normal(shape)
        eta=np.empty((2,4,R,2,16,16))
        eta[0,:,:,0]=pair(z); eta[0,:,:,1]=pair(z)
        eta[1,:,:,0]=pair(z); eta[1,:,:,1]=pair(0.*z+np.sqrt(1.)*e)
        a,b=eta[:,:,:,0],eta[:,:,:,1]
        for k,term in enumerate((a,b,a*a,b*b,a*b)): moments[:,k]+=term.sum(axis=(1,2,3,4))
        moments[:,5]+=a[0].size
        v=advance_compensated(v,old[:,:,:,None],denominator[:,:,:,None],eta,cfg,t>=cycle['settling_steps'])
        v*=live;v[...,p[0]]=cue;hashes.append(np.array([digest(x) for x in v]))
        if t>=cycle['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,p[1]].mean(axis=-1),v[...,p[2]].mean(axis=-1)),axis=-1))
    end=v.copy();trace=np.array(trace); x=np.tanh(cfg['writer_beta']*end)
    ordinary=np.empty((2,4,R,2,16,16));contrast=np.empty_like(ordinary)
    for direction,y,col in np.ndindex(2,16,16):
        yy,xx=(y,(col+1)%16) if direction==0 else ((y+1)%16,col)
        a,b=x[...,y,col],x[...,yy,xx]
        contrast[...,direction,y,col]=((a[...,0]-a[...,1])/2)*((b[...,0]-b[...,1])/2)
        # NumPy's mean starts its reduction at positive zero. Preserve that
        # signed-zero behavior for byte-exact replay of absent-cell products.
        total=np.zeros(a.shape[:-1])
        total+=a[...,0]*b[...,0];total+=a[...,1]*b[...,1];total/=2
        ordinary[...,direction,y,col]=total
    fallback=(contrast==0)&physical
    outgoing=np.zeros_like(contrast)
    for n in range(2):
        good=np.broadcast_to(physical,contrast[n].shape)
        outgoing[n][good]=contrast[n][good]
        outgoing[n][fallback[n]]=ordinary[n][fallback[n]]
    stream=random('E022',block,'write',g); scaffold=physical[None,:,:,None].astype(float)
    write_hashes=[]
    for _ in range(cycle['write_steps']):
        eta=pair(stream.standard_normal(shape))[None,:,:,None]
        v=advance(v,scaffold,2.,eta,cfg);v*=live;v[...,p[0]]=cue
        write_hashes.append(np.array([digest(x) for x in v]))
    return dict(incoming=incoming.copy(),masks=mask,effective_packets=pack(old),denominator=denominator,
        birth=birth,end=end,late_ports=trace,mean_ports=trace.mean(axis=0),ordinary=ordinary,
        contrast=contrast,fallback=fallback,outgoing=pack(outgoing),noise_moments=moments,
        read_state_hashes=np.array(hashes),write_end=v,write_state_hashes=np.array(write_hashes))
