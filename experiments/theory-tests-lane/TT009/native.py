"""Independent flat-index reader, mask generator, recapture and CSR diagnostics.

No P03 dynamics, random-stream, diagnostic or scoring functions are imported.
The arithmetic order of the declared native equation is retained for byte replay.
"""
import hashlib
import json
import numpy as np
from scipy.sparse import csr_matrix
import support as s

CELLS=np.arange(256);Y,X=np.divmod(CELLS,16)
RIGHT=16*Y+(X+1)%16;LEFT=16*Y+(X-1)%16
DOWN=16*((Y+1)%16)+X;UP=16*((Y-1)%16)+X
PORTS=[np.array([16*y+x for y in range(y0,y0+2) for x in range(x0,x0+2)]) for y0,x0 in [(7,1),(3,10),(11,10)]]
ELIGIBLE=np.array([i for i in range(256) if all(i not in p for p in PORTS)])


def random_stream(*parts):
    token=json.dumps(list(parts),separators=(',',':')).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(token).digest()[:16],'little')))


def available(mask):
    live=~mask.reshape(*mask.shape[:-2],256)
    return np.stack((live&live[...,RIGHT],live&live[...,DOWN]),axis=-2)


def decode(packets):return np.frombuffer(packets.tobytes(),dtype='<f8').reshape(*packets.shape[:-1],2,256).copy()
def encode(weights):return np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(*weights.shape[:-2],4096).copy()


def recapture(body,masks):
    x=np.tanh(3.*body.reshape(-1,2,256));plus,minus=x[:,0],x[:,1];d=(plus-minus)/2
    contrast=np.stack((d*d[:,RIGHT],d*d[:,DOWN]),axis=1)
    common=np.stack(((plus*plus[:,RIGHT]+minus*minus[:,RIGHT])/2,(plus*plus[:,DOWN]+minus*minus[:,DOWN])/2),axis=1)
    return encode(np.where(available(masks),np.where(contrast==0.,common,contrast),0.))


def fresh_masks(cfg,block,founders,recipients,reps):
    result=np.zeros((len(founders),len(reps),256),dtype=bool)
    for i,(founder,recipient) in enumerate(zip(founders,recipients,strict=True)):
        for j,rep in enumerate(reps):
            rng=random_stream(cfg['random_namespace'],int(block),'injury',int(rep),int(founder)//2,int(recipient))
            result[i,j,rng.choice(ELIGIBLE,cfg['injury_cells'],replace=False)]=True
    return result.reshape(len(founders),len(reps),16,16)


def scores(means,founders):
    # means: endpoint, case, variant, replicate, cue, port.
    answer=np.empty(means.shape[:-2])
    for i,founder in enumerate(founders):
        rule=1 if founder%2==0 else -1
        terms=[means[:,i,...,c,p]*rule*(1 if c==0 else -1)*(1 if p==0 else -1) for c in range(2) for p in range(2)]
        answer[:,i]=np.minimum.reduce(terms)
    return dict(min_margin=answer,both_pass=answer>.25)


def read_packets(packets,masks,founders,recipients,cfg,block,reps,budgets,original=False,progress=None):
    n,v=packets.shape[:2];r=len(reps);parameters=cfg['reader'];budgets=list(budgets)
    s.require(budgets==sorted(set(budgets)) and min(budgets)>=parameters['observe_steps'],'Read endpoints')
    s.require(masks.dtype==bool and masks.shape in [(n,16,16),(n,r,16,16)],'Read masks')
    if masks.ndim==3:masks=np.repeat(masks[:,None],r,axis=1)
    live=~masks.reshape(n,r,256);s.require(live[...,np.concatenate(PORTS)].all(),'Ports preserved')
    weights=decode(packets)[:,:,None]*available(masks)[:,None]
    h=weights[...,0,:];vweights=weights[...,1,:];left=h[...,LEFT];up=vweights[...,UP]
    den=(abs(h)+abs(left)+abs(vweights)+abs(up))[:,:,:,None,:]
    h,left,vweights,up=[a[:,:,:,None,:] for a in (h,left,vweights,up)]
    rngs=[random_stream('E022',int(block),'develop',14) if original else random_stream(cfg['random_namespace'],int(block),'read',int(rep)) for rep in reps]
    contexts=founders//2*4+recipients
    def draw():
        panel=np.stack([rng.standard_normal(2048).reshape(8,256) for rng in rngs])
        selected=panel[:,contexts].transpose(1,0,2)
        return np.repeat(selected[:,:,None],2,axis=2)
    birth=parameters['birth_sd']*draw();value=np.repeat(birth[:,None],packets.shape[1],axis=1)
    alive=live[:,None,:,None];cue=np.array([1.,-1.])[None,None,None,:,None]
    value*=alive;value[...,PORTS[0]]=cue
    endpoints=[];windows=[];means=[];recent=[]
    for step in range(max(budgets)):
        noise=draw()[:,None]
        incoming=h*value[...,RIGHT]+left*value[...,LEFT]+vweights*value[...,DOWN]+up*value[...,UP]
        local=np.divide(incoming,den,out=np.zeros_like(incoming),where=den>0)
        drift=(value-value**3 if step>=cfg['settling_steps'] else -value**3)+2.*(local-value)
        value=np.clip(value+parameters['dt']*drift+parameters['noise']*noise,-2.,2.)
        value*=alive;value[...,PORTS[0]]=cue
        if any(b-parameters['observe_steps']<=step<b for b in budgets):
            recent.append(np.stack([value[...,port].mean(axis=-1) for port in PORTS[1:]],axis=-1))
        if step+1 in budgets:
            s.require(len(recent)==parameters['observe_steps'],'Complete endpoint window')
            window=np.stack(recent);windows.append(window);means.append(window.mean(axis=0))
            endpoints.append(value.copy().reshape(n,packets.shape[1],r,2,16,16));recent=[]
        if progress and (step+1)%512==0:progress(step+1)
    return dict(budgets=np.array(budgets),birth=birth.reshape(n,r,2,16,16),end=np.stack(endpoints),port_windows=np.stack(windows),mean_ports=np.stack(means))


def replay(kind,block,source,cfg,reps=None,progress=None):
    reps=cfg['replicates'] if reps is None else list(reps)
    indices=[cfg['replicates'].index(rep) for rep in reps];n=len(source['founders'])
    if kind=='fixed':
        raw=read_packets(source['packets'],source['masks'],source['founders'],source['recipients'],cfg,block,reps,cfg['budgets'],progress=progress)
        raw.update(scores(raw['mean_ports'],source['founders']));return raw
    masks=np.take(source['masks'],indices,axis=2)
    raw=read_packets(np.concatenate((source['packets'],source['packets'])),masks.reshape(2*n,len(reps),16,16),
        np.tile(source['founders'],2),np.tile(source['recipients'],2),cfg,block,reps,cfg['budgets'],progress=progress)
    result=dict(budgets=raw['budgets'],birth=raw['birth'].reshape(2,n,len(reps),2,16,16),
        end=raw['end'][0].reshape(2,n,4,len(reps),2,16,16),
        port_windows=raw['port_windows'][0].reshape(32,2,n,4,len(reps),2,2).transpose(1,0,2,3,4,5,6),
        mean_ports=raw['mean_ports'][0].reshape(2,n,4,len(reps),2,2))
    result.update(scores(result['mean_ports'],source['founders']));return result


def compare_replay(kind,raw,expected,reps,cfg):
    indices=[cfg['replicates'].index(r) for r in reps]
    axes={'budgets':None,'birth':1 if kind=='fixed' else 2,'end':3,'port_windows':4,'mean_ports':3,'min_margin':3,'both_pass':3}
    for field,axis in axes.items():
        target=expected[field] if axis is None else np.take(expected[field],indices,axis=axis)
        s.equal(raw[field],target,kind+'/'+field)
    return dict(status='PASS',arrays=len(axes),array_sha256={k:s.descriptor(raw[k])['sha256'] for k in axes})


def diagnostic_csr(packet,mask,rule,steps=64):
    weights=decode(packet)*available(mask);h,v=weights
    values=np.stack((h,h[LEFT],v,v[UP]))
    den=np.sum(abs(values),axis=0);values=np.divide(values,den,out=np.zeros_like(values),where=den>0)
    cols=np.stack((RIGHT,LEFT,DOWN,UP));rows=np.tile(CELLS,(4,1))
    matrix=csr_matrix((values.ravel(),(rows.ravel(),cols.ravel())),shape=(256,256))
    results=[]
    for operator in [matrix,abs(matrix)]:
        state=np.zeros(256);state[PORTS[0]]=1.
        for _ in range(steps):state=operator@state;state[PORTS[0]]=1.
        s.require(np.max(abs(state))<=1+1e-12,'Linear transfer bound')
        results.append([float(state[port].mean()) for port in PORTS[1:]])
    return min(rule*results[0][0],-rule*results[0][1]),min(results[1])


def diagnostic(packet,mask,rule,steps=64):
    # Retain the declared addition order for exact diagnostic-tie decisions;
    # diagnostic_csr provides the separately assembled numerical cross-check.
    weights=decode(packet)*available(mask);h,v=weights
    rows=np.stack((h,h[LEFT],v,v[UP]));den=abs(rows).sum(axis=0)
    rows=np.divide(rows,den,out=np.zeros_like(rows),where=den>0);answer=[]
    for operator in (rows,abs(rows)):
        state=np.zeros(256);state[PORTS[0]]=1.
        for _ in range(steps):
            state=operator[0]*state[RIGHT]+operator[1]*state[LEFT]+operator[2]*state[DOWN]+operator[3]*state[UP]
            state[PORTS[0]]=1.
        answer.append([float(state[p].mean()) for p in PORTS[1:]])
    return min(rule*answer[0][0],-rule*answer[0][1]),min(answer[1])
