"""Independent flat consistent-teaching calculation."""
import hashlib
import json
import numpy as np


def teach(block,cfg):
    seed=int.from_bytes(hashlib.sha256(json.dumps(['E016',block,'teach',0],separators=(',',':')).encode()).digest()[:16],'little')
    right=np.array([16*y+(x+1)%16 for y in range(16) for x in range(16)])
    left=np.array([16*y+(x-1)%16 for y in range(16) for x in range(16)])
    down=np.array([16*((y+1)%16)+x for y in range(16) for x in range(16)])
    up=np.array([16*((y-1)%16)+x for y in range(16) for x in range(16)])
    ports=[[16*y+x for y in range(y0,y0+2) for x in range(x0,x0+2)] for y0,x0 in ((7,1),(3,10),(11,10))]
    rules=np.array([1.,-1.,1.,-1.]);total=np.zeros((4,2,256));births=[];ends=[];captures=[]
    for cue in (1.,-1.):
        random=np.random.Generator(np.random.PCG64(seed))
        birth=cue*cfg['birth_sd']*np.repeat(random.standard_normal((2,16,16)),2,axis=0).reshape(4,256)
        value=birth.copy();births.append(birth.reshape(4,16,16))
        targets=[np.full(4,cue),rules*cue,-rules*cue]
        for p in range(3):value[:,ports[p]]=targets[p][:,None]
        states=[]
        for t in range(cfg['teach_steps']):
            noise=cue*np.repeat(random.standard_normal((2,16,16)),2,axis=0).reshape(4,256)
            neighbor=value[:,right]+value[:,left]+value[:,down]+value[:,up]
            drift=value-value**3+cfg['teacher_gain']*(neighbor/4.-value)
            value=np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)
            for p in range(3):value[:,ports[p]]=targets[p][:,None]
            if t>=cfg['teach_steps']-cfg['capture_steps']:
                states.append(value.reshape(4,16,16).copy());x=np.tanh(cfg['writer_beta']*value)
                total+=np.stack((x*x[:,right],x*x[:,down]),axis=1)
        ends.append(value.reshape(4,16,16));captures.append(np.stack(states))
    weights=(total/(2*cfg['capture_steps'])).reshape(4,2,16,16)
    acquired=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(4,4096)
    return dict(birth=np.stack(births),end=np.stack(ends),capture_states=np.stack(captures),weights=weights,acquired=acquired)
