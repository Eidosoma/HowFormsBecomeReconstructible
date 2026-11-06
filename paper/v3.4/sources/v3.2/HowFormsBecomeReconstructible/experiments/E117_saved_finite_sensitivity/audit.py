"""Indexed reconstruction and independent sums for all structural measurements."""
import numpy as np
PLUS=np.r_[np.arange(1,16),0];MINUS=np.r_[15,np.arange(15)]

def directions(w):
    return np.stack((w[...,0,:,:],np.take(w[...,0,:,:],MINUS,axis=-1),
                     w[...,1,:,:],np.take(w[...,1,:,:],MINUS,axis=-2)),axis=-3)

def structure(w,masks,floors):
    ok=~masks
    available=np.stack((ok&np.take(ok,PLUS,axis=-1),ok&np.take(ok,PLUS,axis=-2)),axis=-3)
    effective=w*available;raw=directions(effective)
    d=abs(raw[...,0,:,:])+abs(raw[...,1,:,:])+abs(raw[...,2,:,:])+abs(raw[...,3,:,:])
    floor=np.broadcast_to(np.asarray(floors)[...,None,None],d.shape)
    eff=d.copy();replace=(d>0)&(d<floor);eff[replace]=floor[replace]
    k=np.zeros_like(raw)
    for j in range(4):np.divide(raw[...,j,:,:],eff,out=k[...,j,:,:],where=eff>0)
    return dict(weights=effective,denominator=d,effective_denominator=eff,coupling=k,available=available)

def regions(selected,masks,shape):
    selected=np.broadcast_to(selected,(*shape,2,16,16));live=np.broadcast_to(~masks,(*shape,16,16))
    avail=np.stack((live&np.take(live,PLUS,axis=-1),live&np.take(live,PLUS,axis=-2)),axis=-3)
    edge=np.stack((selected&avail,avail&~selected,avail),axis=-4)
    cue=np.zeros((16,16),bool);cue[7:9,1:3]=True
    output=np.zeros((16,16),bool);output[3:5,10:12]=True;output[11:13,10:12]=True
    free=live&~cue
    nodes=directions(selected&avail).sum(axis=-3)>0
    near=np.zeros_like(nodes)
    for axis in (-1,-2):
        for ix in (PLUS,MINUS):near|=np.take(nodes,ix,axis=axis)
    cell=np.stack((nodes&free,near&~nodes&free,~nodes&~near&free,output&live,cue&live,free),axis=-3)
    return edge,cell

def total(values,mask,axes):
    return np.where(mask,values,0).reshape(*values.shape[:-axes],-1).sum(axis=-1)

def compare(before,after,masks,selected,before_floor,after_floor):
    a=structure(before,masks,before_floor);b=structure(after,masks,after_floor)
    x,y=a['weights'],b['weights'];old,new=a['coupling'],b['coupling']
    present=x!=0;current=y!=0;erased=present&~current
    edge,cell=regions(selected,masks,y.shape[:-3]);free=cell[...,-1,:,:]
    rows=[]
    for j in range(3):
        m=edge[...,j,:,:,:];dm=directions(m)&free[...,None,:,:]
        counts=[np.count_nonzero(m&z,axis=(-3,-2,-1)) for z in
            (np.ones_like(m),present,current,erased,~present&current,present&current&((x<0)!=(y<0)))]
        sums=[total(z,m,3) for z in (abs(x),abs(y),np.where(erased,abs(x),0),abs(y-x))]
        coupling=[total(z,dm,3) for z in (abs(old),abs(new),np.where(directions(erased),abs(old),0),abs(new-old))]
        rows.append(np.stack(counts+sums+coupling,axis=-1))
    d0,d1=a['denominator'],b['denominator'];atten=np.zeros_like(d1)
    good=d1>0;atten[good]=(b['effective_denominator'][good]-d1[good])/b['effective_denominator'][good]
    # Different but algebraically equivalent attenuation arithmetic has roundoff tolerance.
    rowsc=[]
    for j in range(6):
        m=cell[...,j,:,:]
        counts=[np.count_nonzero(m&z,axis=(-2,-1)) for z in
            (np.ones_like(m),d0==0,d1==0,(d0>0)&(d0<1e-4),(d1>0)&(d1<1e-4),(d0>0)&(d1==0))]
        sums=[total(z,m,2) for z in (d0,d1,atten,abs(new-old).sum(axis=-3))]
        rowsc.append(np.stack(counts+sums,axis=-1))
    return np.stack(rows,axis=-2),np.stack(rowsc,axis=-2),a,b

def scores(mean,founders):
    rules=np.array([1.,-1.,1.,-1.])[founders];m=np.empty(mean.shape[:-1])
    for c,cue in enumerate((1.,-1.)):
        m[...,c]=np.minimum(rules*cue*mean[...,c,0],-rules*cue*mean[...,c,1])
    transfer=((mean[...,0,0]-mean[...,1,0])-(mean[...,0,1]-mean[...,1,1]))/4
    return dict(both=(m>.25).all(axis=-1),minimum_margin=m.min(axis=-1),transfer=transfer,
                aligned_transfer=transfer*rules)
