"""Outcome-free graph controls. Donor information is explicitly supplied."""
from study import np, native, ARMS

EDGES = np.array([(16*y+x, 16*y+(x+1)%16) for y in range(16) for x in range(16)]
    +[(16*y+x,16*((y+1)%16)+x) for y in range(16) for x in range(16)],dtype=np.int16)
PORTS = native.P.reshape(3,256)

class Union:
    def __init__(self):self.p=list(range(256))
    def root(self,i):
        while self.p[i]!=i:self.p[i]=self.p[self.p[i]];i=self.p[i]
        return i
    def join(self,a,b):
        a,b=self.root(int(a)),self.root(int(b))
        if a==b:return False
        self.p[max(a,b)]=min(a,b);return True
    def labels(self):return np.array([self.root(i) for i in range(256)],np.int16)

def graph(w):
    flat=np.asarray(w).reshape(512);active=np.flatnonzero(flat!=0);u=Union()
    for e in active:u.join(*EDGES[e])
    labels=u.labels();degree=np.bincount(EDGES[active].ravel(),minlength=256).astype(np.int16)
    reach=np.stack([np.isin(labels,labels[PORTS[p]]) for p in range(3)])
    return degree,labels,reach

def control_one(w,eligible):
    w=w.reshape(512);eligible=eligible.reshape(512);assert (w[eligible]!=0).all()
    p=w.copy();p[eligible]=0.;u=Union()
    for e in np.flatnonzero(p):u.join(*EDGES[e])
    retained=[]
    for e in np.flatnonzero(eligible):
        if u.join(*EDGES[e]):retained.append(int(e))
    retained=np.array(retained,dtype=np.int16);count=len(retained)
    di,_,_=graph(w);dp,_,_=graph(p)
    newly=(di>0)&(dp==0)&~PORTS.any(axis=0)
    candidates=eligible.copy();targets=np.zeros(256,bool)
    for cell in np.flatnonzero(newly):
        trial=candidates & ~np.any(EDGES==cell,axis=1)
        if count>0 and np.count_nonzero(trial)>=count:
            candidates=trial;targets[cell]=True
    feasible=bool(targets.any());mapping=np.full(512,-1,np.int16)
    if feasible:
        available=list(np.flatnonzero(candidates));chosen=[]
        for donor in retained:
            pos=min(available,key=lambda e:(abs(np.log(abs(w[e]))-np.log(abs(w[donor]))),e))
            chosen.append(pos);mapping[pos]=donor;available.remove(pos)
        selected=np.array(chosen,np.int16)
    else:
        selected=retained.copy();mapping[selected]=retained
    rmask=np.zeros(512,bool);smask=rmask.copy();rmask[retained]=True;smask[selected]=True
    variants={name:p.copy() for name in ARMS};variants['I']=w.copy()
    variants['L_native'][selected]=w[selected]
    for location,sites,donors in [('C',retained,retained),('L',selected,mapping[selected])]:
        for suffix,sign,scale in [('',1.,1.),('_flip',-1.,1.),('_low',1.,.25),('_flip_low',-1.,.25)]:
            variants[location+suffix][sites]=w[donors]*sign*scale
    return np.stack([variants[a].reshape(2,16,16) for a in ARMS]),dict(
        retained_R=rmask.reshape(2,16,16),retained_S=smask.reshape(2,16,16),
        donor_at_S=mapping,forced_isolated=targets.reshape(16,16),
        newly_isolated_P=newly.reshape(16,16),feasible=np.array(feasible))

def construct(packets,eligible):
    w=native.base.decode(packets[:4]);shape=w.shape[:3]
    result=np.empty((len(ARMS),*w.shape),float);metadata={}
    for loc in np.ndindex(shape):
        variants,details=control_one(w[loc],eligible[loc]);result[(slice(None),)+loc]=variants
        for k,v in details.items():
            if k not in metadata:metadata[k]=np.empty((*shape,*v.shape),v.dtype)
            metadata[k][loc]=v
    return native.base.encode(result.reshape(len(ARMS)*4,*w.shape[1:])),metadata

def capture_controls(writer,eligible):
    w=native.base.decode(writer['outgoing']).reshape(len(ARMS),4,*eligible.shape[1:])
    ordinary=writer['ordinary'].reshape(w.shape);out=[];diagnostics=[]
    for name in ('P','C'):
        idx=ARMS.index(name);h=w[idx];o=h.copy();o[eligible]=ordinary[idx][eligible]
        s=h.copy();s[eligible]=np.copysign(abs(h[eligible]),o[eligible])
        m=h.copy();m[eligible]=np.copysign(abs(o[eligible]),h[eligible])
        out.extend((o,s,m));diagnostics.append((h!=0)!=(o!=0))
    return native.base.encode(np.concatenate(out)),dict(capture_support_disagreement=np.stack(diagnostics))

