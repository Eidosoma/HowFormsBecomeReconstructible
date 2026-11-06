"""Static local geometry, weight mass and effective directed coupling."""
import numpy as np
from E117_saved_finite_sensitivity.plan import EDGE_REGIONS,CELL_REGIONS,EDGE_METRICS,CELL_METRICS,FEATURES

def ports():
    out=np.zeros((3,16,16),bool)
    for p,(y,x) in enumerate(((7,1),(3,10),(11,10))):out[p,y:y+2,x:x+2]=True
    return out
P=ports()

def decode(packets):
    assert packets.dtype==np.uint8 and packets.shape[-1]==4096
    return np.frombuffer(packets.tobytes(),dtype='<f8').reshape(*packets.shape[:-1],2,16,16).copy()

def directions(w):
    h,v=w[...,0,:,:],w[...,1,:,:]
    return np.stack((h,np.roll(h,1,-1),v,np.roll(v,1,-2)),axis=-3)

def structure(weights,masks,floors):
    live=~masks;available=np.stack((live&np.roll(live,-1,-1),live&np.roll(live,-1,-2)),axis=-3)
    w=weights*available;h,v=abs(w[...,0,:,:]),abs(w[...,1,:,:])
    d=h+np.roll(h,1,-1)+v+np.roll(v,1,-2)
    eff=np.where(d>0,np.maximum(d,np.asarray(floors)[...,None,None]),0.)
    raw=directions(w);k=np.divide(raw,eff[...,None,:,:],out=np.zeros_like(raw),where=eff[...,None,:,:]>0)
    return dict(weights=w,denominator=d,effective_denominator=eff,coupling=k,available=available)

def regions(selected,masks,shape):
    selected=np.broadcast_to(selected,(*shape,2,16,16));live=np.broadcast_to(~masks,(*shape,16,16))
    avail=np.stack((live&np.roll(live,-1,-1),live&np.roll(live,-1,-2)),axis=-3)
    edges=np.stack((selected&avail,~selected&avail,avail),axis=-4)
    nodes=directions(selected&avail).any(axis=-3);free=live&~P[0]
    touch=nodes&free;near=(np.roll(nodes,1,-1)|np.roll(nodes,-1,-1)|np.roll(nodes,1,-2)|np.roll(nodes,-1,-2))
    ring=near&~nodes&free;remote=free&~touch&~ring
    cells=np.stack((touch,ring,remote,live&(P[1]|P[2]),live&P[0],free),axis=-3)
    assert np.array_equal(cells[...,:3,:,:].sum(axis=-3),free.astype(int))
    return edges,cells

def compare(before,after,masks,selected,before_floor,after_floor):
    a=structure(before,masks,before_floor);b=structure(after,masks,after_floor)
    w0,w1=a['weights'],b['weights'];k0,k1=a['coupling'],b['coupling']
    lost=(w0!=0)&(w1==0);gained=(w0==0)&(w1!=0);same=(w0!=0)&(w1!=0)
    edges,cells=regions(selected,masks,w1.shape[:-3]);free=cells[...,-1,:,:]
    edge_values=[]
    for j in range(3):
        region=edges[...,j,:,:,:];directed=directions(region)&free[...,None,:,:]
        terms=(np.ones_like(w0),w0!=0,w1!=0,lost,gained,same&(np.signbit(w0)!=np.signbit(w1)),
               abs(w0),abs(w1),abs(w0)*lost,abs(w1-w0))
        raw=[(term*region).sum(axis=(-3,-2,-1)) for term in terms]
        normalized=[(v*directed).sum(axis=(-3,-2,-1)) for v in
            (abs(k0),abs(k1),abs(k0)*directions(lost),abs(k1-k0))]
        edge_values.append(np.stack(raw+normalized,axis=-1))
    d0,d1=a['denominator'],b['denominator'];eff=b['effective_denominator']
    attenuation=np.where(d1>0,1-np.divide(d1,eff,out=np.zeros_like(d1),where=eff>0),0.)
    terms=(np.ones_like(d0),d0==0,d1==0,(d0>0)&(d0<1e-4),(d1>0)&(d1<1e-4),
           (d0>0)&(d1==0),d0,d1,attenuation,abs(k1-k0).sum(axis=-3))
    cell_values=np.stack([np.stack([(v*region).sum(axis=(-2,-1)) for v in terms],axis=-1)
                          for region in np.moveaxis(cells,-3,0)],axis=-2)
    return np.stack(edge_values,axis=-2),cell_values,a,b

def features(edge,cell,channel):
    def e(region,key):return edge[...,EDGE_REGIONS.index(region),EDGE_METRICS.index(key)]
    def c(region,key):return cell[...,CELL_REGIONS.index(region),CELL_METRICS.index(key)]
    def q(region,key):return channel[...,EDGE_REGIONS.index(region),EDGE_METRICS.index(key)]
    nums=[c('free','reference_weak'),c('free','current_weak'),c('free','newly_isolated'),
        c('free','floor_attenuation_sum'),c('free','coupling_l1'),q('all','lost_edges'),
        q('all','lost_reference_mass'),q('all','lost_reference_coupling'),q('selected','lost_reference_coupling'),
        q('outside','lost_reference_coupling'),e('selected','coupling_l1'),c('outputs','coupling_l1')]
    dens=[c('free','cells')]*5+[q('all','reference_edges'),q('all','reference_mass')]+[q('all','reference_coupling_mass')]*3+[
        e('all','coupling_l1'),c('free','coupling_l1')]
    assert len(nums)==len(dens)==len(FEATURES)
    return np.stack(nums,axis=-1),np.stack(dens,axis=-1)
