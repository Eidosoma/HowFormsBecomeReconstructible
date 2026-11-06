"""Independent indexed-neighbor implementation of the carried-state dynamics.

No production dynamics functions are imported. Keep the published floating-point
operation order for exact replay of a numerically sensitive writer.
"""
import hashlib
import json
import numpy as np
import support as s

PLUS=(np.arange(16)+1)%16;MINUS=(np.arange(16)-1)%16
PORTS=np.zeros((3,16,16),bool)
for i,(y,x) in enumerate([(7,1),(3,10),(11,10)]):PORTS[i,y:y+2,x:x+2]=True
RULES=np.array([1.,-1.,1.,-1.]);CUES=np.array([1.,-1.])


def rng(tag,*parts):
    raw=json.dumps([tag,*parts],separators=(',',':')).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(raw).digest()[:16],'little')))


def horizontal(a,indices):return np.take(a,indices,axis=-1)
def vertical(a,indices):return np.take(a,indices,axis=-2)
def paired(x):return np.repeat(x,2,axis=0)
def cues(x):return np.repeat(paired(x)[:,:,None],2,axis=2)
def available(mask):
    live=~mask;return np.stack((live&horizontal(live,PLUS),live&vertical(live,PLUS)),axis=-3)
def decode(packet):return np.frombuffer(packet.tobytes(),dtype='<f8').reshape(*packet.shape[:-1],2,16,16).copy()
def encode(weights):return np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(*weights.shape[:-3],4096).copy()


def neighbors(value,h,hl,v,vu):
    return h*horizontal(value,PLUS)+hl*horizontal(value,MINUS)+v*vertical(value,PLUS)+vu*vertical(value,MINUS)


def step(value,edges,noise,cfg,amplification,normalized=True):
    h,hl,v,vu,den=edges;incoming=neighbors(value,h,hl,v,vu)
    local=np.divide(incoming,den,out=np.zeros_like(incoming),where=den>0) if normalized else incoming/4.
    drift=(value-value**3 if amplification else -value**3)+2.*(local-value)
    return np.clip(value+cfg['dt']*drift+cfg['noise']*noise,-2.,2.)


def edge_views(weights):
    h=weights[...,0,:,:];v=weights[...,1,:,:];hl=horizontal(h,MINUS);vu=vertical(v,MINUS)
    return h,hl,v,vu,abs(h)+abs(hl)+abs(v)+abs(vu)


def masks(block,phase,recipients):
    allowed=np.flatnonzero(~PORTS.any(axis=0).ravel());squares=[]
    for y in range(16):
        for x in range(16):
            mask=np.zeros((16,16),bool)
            for dy in [-1,0,1]:
                for dx in [-1,0,1]:mask[(y+dy)%16,(x+dx)%16]=True
            if not (mask&PORTS.any(axis=0)).any():squares.append(mask)
    random=rng('E015',block,phase,'damage');result=np.zeros((2,recipients,3,16,16),bool)
    for founder in range(2):
        for recipient in range(recipients):
            result[founder,recipient,1].ravel()[random.choice(allowed,24,replace=False)]=True
            result[founder,recipient,2]=squares[int(random.integers(len(squares)))]
    return paired(result)


def correlations(value,beta):
    activated=np.tanh(beta*value)
    return np.stack((activated*horizontal(activated,PLUS),activated*vertical(activated,PLUS)),axis=-3)


def teacher_episode(block,polarity,cfg):
    random=rng('E016',block,'teach',0);birth=polarity*cfg['birth_sd']*paired(random.standard_normal((2,16,16)))
    value=birth.copy();targets=np.stack((np.full(4,polarity),RULES*polarity,-RULES*polarity),axis=1)
    for p in range(3):value[:,PORTS[p]]=targets[:,p,None]
    captured=[];edge=edge_views(np.ones((2,16,16)))
    for t in range(cfg['teach_steps']):
        noise=polarity*paired(random.standard_normal((2,16,16)));value=step(value,edge,noise,cfg,True,False)
        for p in range(3):value[:,PORTS[p]]=targets[:,p,None]
        if t>=cfg['teach_steps']-cfg['capture_steps']:captured.append(value.copy())
    return dict(birth=birth,end=value,captured=np.stack(captured))


def teaching(block,cfg):
    episodes=[teacher_episode(block,sign,cfg) for sign in [1.,-1.]];total=np.zeros((4,2,16,16))
    for episode in episodes:
        for value in episode['captured']:total+=correlations(value,cfg['writer_beta'])
    weights=total/(2*cfg['capture_steps'])
    return dict(birth=np.stack([x['birth'] for x in episodes]),end=np.stack([x['end'] for x in episodes]),
        captured=np.stack([x['captured'] for x in episodes]),weights=weights,acquired=encode(weights))


def capture(body,damage,writer_codes,beta,tolerance):
    activated=np.tanh(beta*body);difference=(activated[:,:,:,0]-activated[:,:,:,1])/2.
    q=np.stack((difference*horizontal(difference,PLUS),difference*vertical(difference,PLUS)),axis=-3)
    common=np.stack((activated*horizontal(activated,PLUS),activated*vertical(activated,PLUS)),axis=-3).mean(axis=3)
    selected=np.empty_like(q)
    for arm,code in enumerate(writer_codes):selected[arm]=np.where(abs(q[arm])<=tolerance if code else q[arm]==0.,common[arm],q[arm])
    return encode(np.where(available(damage),selected,0.))


def read_ports(value):return np.stack([value[...,PORTS[p]].mean(axis=-1) for p in [1,2]],axis=-1)


def rebuild(packets,block,generation,writer_codes,cfg,cycle,tolerance):
    damage=masks(block,f'E022_renewal_g{generation}',cfg['recipients'])[:,:,1]
    effective=decode(packets)*available(damage);edge=edge_views(effective[:,:, :,None])
    random=rng('E022',block,'develop',generation);shape=(2,cfg['recipients'],16,16)
    birth=cfg['birth_sd']*cues(random.standard_normal(shape));value=np.repeat(birth[None],len(packets),axis=0)
    alive=(~damage)[None,:,:,None];cue=CUES.reshape(1,1,1,2,1);value*=alive;value[...,PORTS[0]]=cue;late=[]
    for t in range(cycle['read_steps']):
        noise=cues(random.standard_normal(shape))[None];value=step(value,edge,noise,cfg,t>=cycle['settling_steps']);value*=alive;value[...,PORTS[0]]=cue
        if t>=cycle['read_steps']-cfg['observe_steps']:late.append(read_ports(value))
    return dict(masks=damage,birth=birth,end=value,outgoing=capture(value,damage,writer_codes,cfg['writer_beta'],tolerance),mean_ports=np.stack(late).mean(axis=0))


def assay(packets,block,horizon,cfg,cycle):
    packets=np.concatenate((packets,np.zeros_like(packets[:1])),axis=0);damage=masks(block,f'E022_h{horizon}',cfg['recipients'])
    effective=decode(packets)[:,:,:,None]*available(damage)[None];edge=edge_views(effective[:,:,:,None])
    random=rng('E022',block,'assay',horizon);shape=(2,cfg['recipients'],3,16,16)
    birth=cfg['birth_sd']*paired(random.standard_normal(shape));value=np.broadcast_to(birth[None,:,:,None],(len(packets),4,cfg['recipients'],2,3,16,16)).copy()
    alive=(~damage)[None,:,:,None];cue=CUES.reshape(1,1,1,2,1,1);value*=alive;value[...,PORTS[0]]=cue;late=[]
    for t in range(cycle['read_steps']):
        noise=paired(random.standard_normal(shape))[None,:,:,None];value=step(value,edge,noise,cfg,t>=cycle['settling_steps']);value*=alive;value[...,PORTS[0]]=cue
        if t>=cycle['read_steps']-cfg['observe_steps']:late.append(read_ports(value))
    return dict(masks=damage,birth=birth,end=value,mean_ports=np.stack(late).mean(axis=0))


def equal(observed,expected,label):
    s.require(set(observed)==set(expected),'Replay fields '+label)
    for name in observed:
        a,b=observed[name],expected[name];s.require(a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes(),'Byte replay '+label+'/'+name)
    return dict(status='PASS',label=label,arrays=len(observed),sha256={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in observed.items()})
