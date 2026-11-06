"""Independent indexed equations; never calls the production finite operators."""
import numpy as np
from E077_fresh_reconstruction_tradeoff import audit_model as legacy

P = legacy.P
PLUS = np.r_[np.arange(1,16),0]
MINUS = np.r_[15,np.arange(15)]


def quantize(packets, delta):
    if not delta: return packets.copy()
    w = legacy.unpack(packets); x = np.abs(w)/delta
    low = np.floor(x); fraction = x-low
    up = (fraction>.5) | ((fraction==.5)&(np.remainder(low,2)==1))
    return legacy.pack(np.copysign((low+up)*delta,w))


def capture(state, physical, tolerance, beta=3.):
    _, ordinary, contrast, _ = legacy.capture(state, physical, beta)
    valid = np.broadcast_to(physical, contrast.shape)
    fallback = valid & (contrast>=-tolerance) & (contrast<=tolerance)
    out = np.zeros(contrast.shape)
    out[valid] = contrast[valid]; out[fallback] = ordinary[fallback]
    return dict(pre_channel=legacy.pack(out), ordinary=ordinary, contrast=contrast, fallback=fallback)


def structure(packets, masks, floors):
    w = legacy.unpack(packets)*legacy.alive(masks)
    d, _ = legacy.coupling(w)
    effective = d.copy(); eps = np.broadcast_to(np.asarray(floors)[...,None,None],d.shape)
    positive = d>0; effective[positive & (d<eps)] = eps[positive & (d<eps)]
    raw = legacy.directions(w); k = np.zeros_like(raw)
    for direction in range(4):
        np.divide(raw[...,direction,:,:],effective,out=k[...,direction,:,:],where=positive)
    return w,d,effective,k


def simulate(packets, floors, contexts, task, cfg, phase, generation=0):
    R = cfg['config']['recipients']; c=cfg['config']; steps=cfg['steps']
    f,r = contexts.T; n=len(packets)
    masks = legacy.masks(task,R,phase+'_injury',generation)[f,r]
    w,d,effective,_ = structure(packets,masks,floors)
    stream=legacy.random('E077',task,phase,generation)
    birth=c['birth_sd']*legacy.pair(stream.standard_normal((2,R,16,16)))[f,r]
    v=np.empty((n,2,16,16));v[:,0]=birth;v[:,1]=birth
    live=(~masks)[:,None];clamp=np.array([1.,-1.])[None,:,None]
    v*=live;v[...,P[0]]=clamp
    right=w[:,None,0];left=np.take(right,MINUS,axis=-1)
    below=w[:,None,1];above=np.take(below,MINUS,axis=-2)
    trace=[];hashes=[];counts=np.zeros(n,np.int64)
    free=((~masks)&~P.any(axis=0))[:,None]
    for t in range(steps['read_steps']):
        eta=legacy.pair(stream.standard_normal((2,R,16,16)))[f,r][:,None]
        total=right*np.take(v,PLUS,axis=-1)
        total=total+left*np.take(v,MINUS,axis=-1)
        total=total+below*np.take(v,PLUS,axis=-2)
        total=total+above*np.take(v,MINUS,axis=-2)
        u=np.zeros_like(total)
        np.divide(total,effective[:,None],out=u,where=effective[:,None]>0)
        drift=(v-v**3 if t>=steps['settling_steps'] else -v**3)+2.*(u-v)
        v=np.clip(v+c['dt']*drift+c['noise']*eta,-2.,2.)
        v*=live;v[...,P[0]]=clamp
        hashes.append(legacy.digest(v));counts+=np.count_nonzero((abs(v)==2.)&free,axis=(1,2,3))
        if t>=steps['read_steps']-c['observe_steps']:
            trace.append(np.stack([v[...,P[i]].mean(axis=-1) for i in (1,2)],axis=-1))
    trace=np.array(trace)
    return dict(end=v,late_ports=np.moveaxis(trace,0,1),mean_ports=trace.mean(axis=0),
                boundary_counts=counts,state_hashes=np.array(hashes))


def scores(mean, founders, threshold=.25):
    rows=[]
    for x,f in zip(mean,founders):
        rule=(1.,-1.,1.,-1.)[f]; margins=[]; opposite=[]
        for c,cue in enumerate((1.,-1.)):
            a=rule*cue*x[c,0];b=-rule*cue*x[c,1]
            margins.append(min(a,b));opposite.append(min(-a,-b))
        tr=((x[0,0]-x[1,0])-(x[0,1]-x[1,1]))/4
        good=all(v>threshold for v in margins);wrong=any(v<0 for v in margins)
        rows.append(dict(both=good,minimum_margin=min(margins),transfer=tr,aligned_transfer=rule*tr,
            cue0_margin=margins[0],cue1_margin=margins[1],
            correct_signs_below_threshold=all(v>0 for v in margins) and not good,
            zero_without_wrong_sign=any(v==0 for v in margins) and not wrong,
            any_wrong_sign=wrong,opposite_rule_success=all(v>threshold for v in opposite)))
    return {k:np.array([r[k] for r in rows]) for k in rows[0]}
