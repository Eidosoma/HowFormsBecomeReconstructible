"""Independent flat-index native replay, stream construction, writer and scalar scoring."""
import hashlib
import json
import math
import numpy as np
import support as s

CELLS=np.arange(256);YY,XX=np.divmod(CELLS,16)
RIGHT=16*YY+(XX+1)%16;LEFT=16*YY+(XX-1)%16
DOWN=16*((YY+1)%16)+XX;UP=16*((YY-1)%16)+XX
PORTS=[np.array([16*y+x for y in range(a,a+2) for x in range(b,b+2)]) for a,b in ((7,1),(3,10),(11,10))]
ELIGIBLE=np.array([i for i in range(256) if all(i not in p for p in PORTS)])


def key(record,future,generation,source,cue=None):
    payload=['TT018_DRAFT_STREAM_CONTRACT_V1',record,int(future),int(generation),source,cue]
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()


class Draws:
    def __init__(self,record,futures,generation,cfg,terminal=False):
        self.steps=0;self.digest=hashlib.sha256();self.keys=[];self.random=[]
        prefix='terminal_' if terminal else ''
        self.masks=np.zeros((len(futures),256),bool);self.birth=np.empty((len(futures),2,256))
        self.moments=np.zeros((len(futures),6))
        for i,future in enumerate(futures):
            ks=[key(record,future,generation,prefix+'injury')]
            for source in ('reset','forcing'):
                for cue in (0,1):ks.append(key(record,future,generation,prefix+source,cue))
            self.keys.append(ks)
            generators=[np.random.Generator(np.random.PCG64(int.from_bytes(bytes.fromhex(k)[0:16],byteorder='little'))) for k in ks]
            chosen=generators[0].choice(ELIGIBLE,24,replace=False)
            self.masks[i,chosen]=True
            for cue in (0,1):self.birth[i,cue]=generators[1+cue].standard_normal(256)*cfg['birth_sd']
            self.random.append(generators[3:])
        self.masks=self.masks.reshape(-1,16,16);self.birth=self.birth.reshape(-1,2,16,16)

    def noise(self):
        raw=np.empty((len(self.random),2,256))
        for i,generators in enumerate(self.random):
            for cue in (0,1):raw[i,cue]=generators[cue].standard_normal(256)
            x,y=raw[i]
            self.moments[i]+=np.array([x.sum(),y.sum(),(x*x).sum(),(y*y).sum(),(x*y).sum(),256.])
        result=raw.reshape(-1,2,16,16)
        self.digest.update(result.tobytes());self.steps+=1
        return result

    def evidence(self):
        return dict(noise_moments=self.moments.copy(),noise_digest=np.frombuffer(self.digest.digest(),np.uint8).copy(),
            seed_keys=np.asarray(self.keys,dtype='U64'),forcing_steps=np.array(self.steps))


def writer(value,masks,beta):
    a=np.tanh(beta*value)
    difference=(a[:,:,0]-a[:,:,1])/2
    q=np.stack((difference*difference[...,RIGHT],difference*difference[...,DOWN]),axis=-2)
    common=np.stack((a*a[...,RIGHT],a*a[...,DOWN]),axis=-2).mean(axis=2)
    live=~masks.reshape(-1,256)
    available=np.stack((live&live[:,RIGHT],live&live[:,DOWN]),axis=1)
    weights=np.where(available,np.where(q==0.,common,q),0.)
    packet=np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(*weights.shape[:2],4096)
    return packet,dict(available_edges=np.broadcast_to(available,q.shape).sum(axis=(-2,-1)),
        fallback_edges=((q==0.)&available).sum(axis=(-2,-1)))


def read_packets(packets,draws,cfg,cycle,write=True):
    p,n=packets.shape[:2]
    live=~draws.masks.reshape(n,256)
    available=np.stack((live&live[:,RIGHT],live&live[:,DOWN]),axis=1)
    weights=np.frombuffer(packets.tobytes(),dtype='<f8').reshape(p,n,2,256).copy()*available
    h,v=weights[:,:,0],weights[:,:,1];left=h[...,LEFT];up=v[...,UP]
    denominator=(abs(h)+abs(left)+abs(v)+abs(up))[:,:,None]
    h,left,v,up=[a[:,:,None] for a in (h,left,v,up)]
    value=np.broadcast_to(draws.birth.reshape(1,n,2,256),(p,n,2,256)).copy()
    value*=live[None,:,None];value[...,PORTS[0]]=np.array([1.,-1.])[None,None,:,None]
    windows=[]
    for step in range(cycle['read_steps']):
        incoming=h*value[...,RIGHT]+left*value[...,LEFT]+v*value[...,DOWN]+up*value[...,UP]
        local=np.divide(incoming,denominator,out=np.zeros_like(incoming),where=denominator>0)
        drift=(value-value**3 if step>=cycle['settling_steps'] else -value**3)+2.*(local-value)
        noise=draws.noise().reshape(1,n,2,256)
        value=np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)
        value*=live[None,:,None];value[...,PORTS[0]]=np.array([1.,-1.])[None,None,:,None]
        if step>=cycle['read_steps']-cfg['observe_steps']:
            windows.append(np.stack([value[...,port].mean(axis=-1) for port in PORTS[1:]],axis=-1))
    windows=np.stack(windows)
    result=dict(masks=draws.masks.copy(),birth=draws.birth.copy(),end=value.reshape(p,n,2,16,16),
                port_windows=windows,mean_ports=windows.mean(axis=0),**draws.evidence())
    if write:
        result['outgoing'],details=writer(value,draws.masks,cfg['writer_beta']);result.update(details)
    return result


def compare(actual,expected,label):
    s.require(set(actual)==set(expected),'Complete independent replay fields '+label)
    for field in actual:s.equal(actual[field],expected[field],label+'/'+field)
    return dict(status='PASS',label=label,arrays=len(actual),sha256={k:s.descriptor(v)['sha256'] for k,v in actual.items()})


def score(raw,rules,scored):
    windows=raw['port_windows'];maximum=0.;nearest=float('inf')
    for policy in range(windows.shape[1]):
        for future,rule in enumerate(rules):
            values=[]
            for cue in range(2):
                for port in range(2):
                    mean=math.fsum(map(float,windows[:,policy,future,cue,port]))/len(windows)
                    maximum=max(maximum,abs(mean-float(raw['mean_ports'][policy,future,cue,port])))
                    values.append(mean*float(rule)*(1 if cue==0 else -1)*(1 if port==0 else -1))
            minimum,opposite=min(values),-max(values)
            for field,truth in (('min_margin',minimum),('opposite_margin',opposite)):
                s.require(abs(float(scored[field][policy,future])-truth)<2e-14,'Independent scalar margin')
                nearest=min(nearest,abs(truth-.25))
            s.require(bool(scored['both_pass'][policy,future])==(minimum>.25),'Independent strict intended label')
            s.require(bool(scored['opposite_pass'][policy,future])==(opposite>.25),'Independent strict opposite label')
    return dict(status='PASS',contexts=int(windows.shape[1]*windows.shape[2]),
        task_flags=int(2*windows.shape[1]*windows.shape[2]),maximum_mean_error=maximum,nearest_threshold=nearest)
