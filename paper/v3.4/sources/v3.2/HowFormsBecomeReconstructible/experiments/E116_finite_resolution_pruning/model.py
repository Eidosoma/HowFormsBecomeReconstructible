"""Finite capture/storage and vectorized, per-context matched dynamics."""
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff import model as old

base, reader, P = old.base, old.reader, old.P


def quantize(packets, delta):
    if not delta: return packets.copy()
    w = base.decode(packets)
    return base.encode(delta*np.rint(w/delta))


def capture(state, physical, tolerance, beta=3.):
    _, ordinary, contrast, _ = old.capture(state, physical, beta)
    fallback = (np.abs(contrast) <= tolerance) & physical
    out = np.where(physical, np.where(fallback, ordinary, contrast), 0.)
    return dict(pre_channel=base.encode(out), ordinary=ordinary, contrast=contrast, fallback=fallback)


def structure(packets, masks, floor):
    w = base.decode(packets) * reader.surviving_edges(masks)
    d = reader.incident_sum(abs(w))
    effective_d = np.where(d > 0, np.maximum(d, np.asarray(floor)[...,None,None]), 0.)
    directed = old.directed(w)
    k = np.divide(directed, effective_d[...,None,:,:], out=np.zeros_like(directed),
                  where=effective_d[...,None,:,:] > 0)
    return w, d, effective_d, k


def simulate(packets, floors, contexts, task, cfg, phase, generation=0):
    """Flat records; noise still drawn at the entire original recipient width."""
    R = cfg['config']['recipients']; c = cfg['config']; steps = cfg['steps']
    f, r = contexts.T; n = len(packets)
    masks = old.masks(task, R, phase+'_injury', generation)[f,r]
    w, d, eff, _ = structure(packets, masks, floors)
    stream = rng('E077', task, phase, generation); shape = (2,R,16,16)
    birth = c['birth_sd'] * base.paired_founders(stream.standard_normal(shape))[f,r]
    v = np.broadcast_to(birth[:,None], (n,2,16,16)).copy()
    live = (~masks)[:,None]; cues = np.array([1.,-1.])[None,:,None]
    v *= live; v[...,P[0]] = cues
    conf = base.Config(recipients=R, dt=c['dt'], noise=c['noise'])
    trace, hashes = [], []
    counts = np.zeros(n, np.int64); free = ((~masks)&~P.any(axis=0))[:,None]
    for t in range(steps['read_steps']):
        noise = base.paired_founders(stream.standard_normal(shape))[f,r][:,None]
        v = reader.compensated_step(v, w[:,None], eff[:,None], noise, conf,
                                   t >= steps['settling_steps'])
        v *= live; v[...,P[0]] = cues
        hashes.append(old.digest(v))
        counts += ((abs(v)==2.) & free).sum(axis=(1,2,3))
        if t >= steps['read_steps']-c['observe_steps']:
            trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
    trace = np.stack(trace)
    return dict(end=v, late_ports=np.moveaxis(trace,0,1), mean_ports=trace.mean(axis=0),
                boundary_counts=counts, state_hashes=np.stack(hashes))


def scores(mean, founders, margin=.25):
    desired = np.array([1.,-1.,1.,-1.])[founders,None] * np.array([1.,-1.])
    a,b = desired*mean[...,0], -desired*mean[...,1]
    m = np.minimum(a,b)
    tr = ((mean[:,0,0]-mean[:,1,0])-(mean[:,0,1]-mean[:,1,1]))/4
    success = (m>margin).all(axis=-1); wrong = (m<0).any(axis=-1)
    return dict(both=success, minimum_margin=m.min(axis=-1), transfer=tr,
        aligned_transfer=tr*np.array([1.,-1.,1.,-1.])[founders], cue0_margin=m[:,0],cue1_margin=m[:,1],
        correct_signs_below_threshold=(m>0).all(axis=-1)&~success,
        zero_without_wrong_sign=(m==0).any(axis=-1)&~wrong, any_wrong_sign=wrong,
        opposite_rule_success=(np.minimum(-a,-b)>margin).all(axis=-1))
