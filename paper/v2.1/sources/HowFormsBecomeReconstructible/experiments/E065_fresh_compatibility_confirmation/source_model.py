"""Reduced exact shared-noise source and continuation; predecessor streams retained."""
import time
import numpy as np
from common import rng
from E022_reader_compensation import model as reader
from E055_stress_capture_recovery import model as pulse
from E055_stress_capture_recovery.model import capture
from E062_cross_stage_compatibility.model import digest
base=reader.base
P=base.PORTS

def rebuild(incoming, block, generation, cfg, cycle, namespace):
    started=time.monotonic()
    assert namespace in ('E022','E058')
    N,F,R = incoming.shape[:-1]
    assert F==4 and N in (1,2)
    masks=base.damage_masks(block,f'{namespace}_renewal_g{generation}',cfg)[:,:,1]
    available=reader.surviving_edges(masks)
    effective=base.decode(incoming).reshape(N,F,R,2,16,16)*available
    denominator=reader.incident_sum(abs(effective))
    stream=rng(namespace,block,'develop',generation)
    shape=(2,R,16,16)
    birth=cfg.birth_sd*base.paired_founders(stream.standard_normal(shape))
    v=np.broadcast_to(birth[None,:,:,None],(N,F,R,2,16,16)).copy()
    live=(~masks)[None,:,:,None]; cue=base.CUES.reshape(1,1,1,2,1)
    v*=live;v[...,P[0]]=cue; trace=[]; hashes=[]
    read_started=time.monotonic()
    for t in range(cycle['read_steps']):
        noise=base.paired_founders(stream.standard_normal(shape))[None,:,:,None]
        v=reader.compensated_step(v,effective[:,:,:,None],denominator[:,:,:,None],noise,cfg,t>=cycle['settling_steps'])
        v*=live;v[...,P[0]]=cue;hashes.append(digest(v))
        if t>=cycle['read_steps']-cfg.observe_steps:
            trace.append(np.stack([v[...,P[p]].mean(axis=-1) for p in (1,2)],axis=-1))
    read_seconds=time.monotonic()-read_started
    end=v.copy();trace=np.stack(trace)
    outgoing,ordinary,contrast,fallback=capture(end,available,cfg.writer_beta)
    stream=rng(namespace,block,'write',generation)
    scaffold=available[None,:,:,None].astype(float);write_hashes=[]
    write_started=time.monotonic()
    for _ in range(cycle['write_steps']):
        noise=base.paired_founders(stream.standard_normal(shape))[None,:,:,None]
        v=base.step(v,scaffold,2.,noise,cfg);v*=live;v[...,P[0]]=cue;write_hashes.append(digest(v))
    write_seconds=time.monotonic()-write_started
    raw=dict(incoming=incoming.copy(),masks=masks,effective_packets=base.encode(effective),
        denominator=denominator,birth=birth,end=end,late_ports=trace,mean_ports=trace.mean(axis=0),
        ordinary=ordinary,contrast=contrast,fallback=fallback,
        outgoing=base.encode(outgoing).reshape(incoming.shape),read_state_hashes=np.stack(hashes),
        write_end=v,write_state_hashes=np.stack(write_hashes))


    return raw,dict(read=read_seconds,write=write_seconds,static=time.monotonic()-started-read_seconds-write_seconds)


def perturb(packets,block,cfg):
    body=pulse.develop(base.decode(packets),block,cfg)
    out=pulse.transmit(body,cfg)
    for key in ('states','port_windows','mean_ports'):
        assert body[key][:,:,1].tobytes()==body[key][:,:,2].tobytes()
        body[key]=body[key][:,:,:2].copy()
    outgoing={key:out[key][0,:2].copy() for key in ('packets','ordinary','contrast','fallback')}
    return body,outgoing
