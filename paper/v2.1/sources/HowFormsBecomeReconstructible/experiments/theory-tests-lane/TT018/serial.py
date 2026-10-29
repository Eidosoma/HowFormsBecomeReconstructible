"""Roll-based native reader and exact writer for arbitrary batches of restored futures."""
import hashlib
import numpy as np
import roll_dynamics as d
import support as s
from future_statistics import stream_key


class Draws:
    """Independent future/cue streams; a single draw is shared by every policy."""
    def __init__(self, record, futures, generation, cfg, terminal=False):
        s.require(len(futures)>0 and len(set(futures))==len(futures),'Distinct nonempty future batch')
        self.futures=list(map(int,futures)); self.steps=0; self.digest=hashlib.sha256()
        prefix='terminal_' if terminal else ''
        self.keys=[]; masks=[]; births=[]; self.noise_rng=[]
        eligible=np.flatnonzero(~d.PORTS.any(axis=0).ravel())
        for future in self.futures:
            keys=[stream_key(record,future,generation,prefix+'injury')]
            keys += [stream_key(record,future,generation,prefix+'reset',cue) for cue in (0,1)]
            keys += [stream_key(record,future,generation,prefix+'forcing',cue) for cue in (0,1)]
            self.keys.append(keys)
            rngs=[np.random.Generator(np.random.PCG64(int.from_bytes(bytes.fromhex(k)[:16],'little'))) for k in keys]
            mask=np.zeros((16,16),bool);mask.ravel()[rngs[0].choice(eligible,24,replace=False)]=True
            masks.append(mask)
            births.append(np.stack([r.standard_normal((16,16)) for r in rngs[1:3]])*cfg['birth_sd'])
            self.noise_rng.append(rngs[3:])
        self.masks=np.stack(masks);self.birth=np.stack(births)
        self.moments=np.zeros((len(futures),6))

    def noise(self):
        a=np.stack([np.stack([r.standard_normal((16,16)) for r in pair]) for pair in self.noise_rng])
        z,y=a[:,0],a[:,1]
        self.moments+=np.stack([z.sum(axis=(1,2)),y.sum(axis=(1,2)),(z*z).sum(axis=(1,2)),
            (y*y).sum(axis=(1,2)),(z*y).sum(axis=(1,2)),np.full(len(z),256.)],axis=1)
        self.digest.update(a.tobytes());self.steps+=1
        return a

    def evidence(self):
        return dict(noise_moments=self.moments.copy(),noise_digest=np.frombuffer(self.digest.digest(),np.uint8).copy(),
                    seed_keys=np.asarray(self.keys,dtype='U64'),forcing_steps=np.array(self.steps))


def capture(body,masks,beta):
    a=np.tanh(beta*body)
    difference=(a[:,:,0]-a[:,:,1])/2
    contrast=np.stack((difference*np.roll(difference,-1,-1),difference*np.roll(difference,-1,-2)),axis=-3)
    common=np.stack((a*np.roll(a,-1,-1),a*np.roll(a,-1,-2)),axis=-3).mean(axis=2)
    available=d.available_edges(masks)
    weights=np.where(available,np.where(contrast==0.,common,contrast),0.)
    return d.encode(weights),dict(available_edges=np.broadcast_to(available,weights.shape).sum(axis=(-3,-2,-1)),
        fallback_edges=((contrast==0.)&available).sum(axis=(-3,-2,-1)))


def read_packets(packets,draws,cfg,cycle,write=True):
    s.require(packets.dtype==np.uint8 and packets.ndim==3 and packets.shape[-1]==4096,'Policy/future/packet panel')
    policies,n=packets.shape[:2]
    s.require(policies>0 and n>0 and 0<cfg['observe_steps']<=cycle['read_steps'] and 0<=cycle['settling_steps']<=cycle['read_steps'],'Reader horizon')
    s.require(draws.masks.shape==(n,16,16) and draws.birth.shape==(n,2,16,16),'Fresh reader dimensions')
    s.require(draws.steps==0,'Unused forcing provider')
    s.require(draws.masks.dtype==bool and not draws.masks[:,d.PORTS.any(axis=0)].any(),'Preserved ports')
    weights=d.decode(packets)*d.available_edges(draws.masks)
    denominator=d.incident(abs(weights))[:,:,None]
    value=np.repeat(draws.birth[None],policies,axis=0)
    alive=(~draws.masks)[None,:,None]
    value*=alive;value[...,d.PORTS[0]]=d.CUES.reshape(1,1,2,1)
    late=[]
    for step in range(cycle['read_steps']):
        value=d.step(value,weights[:,:,None],denominator,draws.noise()[None],cfg,step>=cycle['settling_steps'])
        value*=alive;value[...,d.PORTS[0]]=d.CUES.reshape(1,1,2,1)
        if step>=cycle['read_steps']-cfg['observe_steps']:late.append(d.read_ports(value))
    windows=np.stack(late)
    result=dict(masks=draws.masks.copy(),birth=draws.birth.copy(),end=value,port_windows=windows,
                mean_ports=windows.mean(axis=0),**draws.evidence())
    if write:
        result['outgoing'],details=capture(value,draws.masks,cfg['writer_beta']);result.update(details)
    s.require(draws.steps==cycle['read_steps'],'Complete reader horizon')
    return result


def score(means,rules):
    rules=np.asarray(rules,float)
    s.require(means.ndim==4 and means.shape[-2:]==(2,2) and rules.shape==(means.shape[1],),'Task orientation per future')
    s.require(np.isin(rules,[-1.,1.]).all(),'Supplied binary task')
    s.require(np.isfinite(means).all(),'Finite port means')
    aligned=means*rules[None,:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    minimum=aligned.min(axis=(-2,-1));opposite=-aligned.max(axis=(-2,-1))
    return dict(min_margin=minimum,both_pass=minimum>.25,opposite_margin=opposite,opposite_pass=opposite>.25)
