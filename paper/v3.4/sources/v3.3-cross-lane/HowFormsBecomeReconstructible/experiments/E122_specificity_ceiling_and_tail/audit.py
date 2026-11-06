"""Independent indexed stencil, codec and semantic RNG for declared replay windows."""
import hashlib,json
import numpy as np
from E122_specificity_ceiling_and_tail.plan import CFG

def random_for(*parts):
    key=json.dumps(list(parts),separators=(',',':')).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(key).digest()[:16],'little')))

def center(v):return v-v.mean(axis=(-2,-1),keepdims=True)

def decode(p,factor):
    assert p.dtype==np.uint8 and p.shape[-1]==2048//factor**2
    v=np.frombuffer(p.tobytes(),dtype='<f8').reshape(*p.shape[:-1],16//factor,16//factor)
    return v.repeat(factor,axis=-2).repeat(factor,axis=-1)

def encode(v,factor):
    if factor>1:v=v.reshape(*v.shape[:-2],16//factor,factor,16//factor,factor).mean(axis=(-3,-1))
    return np.ascontiguousarray(v,dtype='<f8').view(np.uint8).reshape(*v.shape[:-2],-1).copy()

def step(v,ema,ref,field,noise,writing,cfg):
    prev=(np.arange(16)-1)%16; nxt=(np.arange(16)+1)%16
    neighbors=(v[...,prev,:]+v[...,nxt,:]+v[...,:,prev]+v[...,:,nxt])/4.
    drift=center(v-v**3+field+(neighbors-v))
    v=np.clip(v+cfg.dt*drift+center(cfg.sigma*noise),-2.,2.)
    ema=.9*ema+.1*v
    if writing:v=np.clip(v+cfg.dt*center(cfg.gain*(ref-v)),-2.,2.)
    ref=ref+cfg.rho*(v-ref)
    if writing:
        proposed=center((1-cfg.lam)*field+cfg.lam*np.tanh(ref))
        field=proposed*(cfg.norm/np.maximum(proposed.std(axis=(-2,-1),keepdims=True),1e-9))
    return v,ema,ref,field

def read(packets,block,phase,factor,cfg=CFG):
    prefix=('forms-e001-unprescribed-v1',block+1000000,phase);shape=(4,2,1,16,16)
    birth=.2*center(random_for(*prefix,'birth').standard_normal(shape))
    v=birth.repeat(packets.shape[2],axis=2);ema=v.copy();ref=v.copy();field=decode(packets,factor)
    random=random_for(*prefix,'read')
    ranks=random_for(*prefix,'challenge').random((4,2,256))
    mask=(np.argsort(np.argsort(ranks,axis=-1),axis=-1)<64).reshape(4,2,16,16)
    for _ in range(cfg.read):v,ema,ref,_=step(v,ema,ref,field,random.standard_normal(shape),False,cfg)
    return np.stack((v,ema,ref),axis=3),birth,mask

def generation(packets,block,g,factor,cfg=CFG):
    state,birth,mask=read(packets,block,f'g{g}',factor,cfg)
    v,ema,ref=[state[:,:,:,i].copy() for i in range(3)];field=np.zeros_like(v)
    random=random_for('forms-e001-unprescribed-v1',block+1000000,f'g{g}','write')
    for _ in range(cfg.write):v,ema,ref,field=step(v,ema,ref,field,random.standard_normal((4,2,1,16,16)),True,cfg)
    return encode(field,factor),dict(read=state,birth=birth,mask=mask,written=np.stack((v,ema,ref,field),axis=3))

def compare(left,right):
    assert left.keys()==right.keys()
    for k in left:np.testing.assert_array_equal(left[k],right[k],err_msg=k)

def counts(state,prototypes,observed):
    for f,r,a,t in np.ndindex(4,2,state.shape[2],4):
        v=state[f,r,a,0];p=prototypes[t];sign=(v>0)==(p>0);amp=abs(v)>.2
        expected=np.array([[np.count_nonzero(~sign&~amp),np.count_nonzero(~sign&amp)],
                           [np.count_nonzero(sign&~amp),np.count_nonzero(sign&amp)]],dtype=np.uint16)
        np.testing.assert_array_equal(observed[f,r,a,t],expected)
