"""Separate flat graph feature implementation; never reads labels or body states."""
import numpy as np


def features(packets):
    w=np.frombuffer(packets.tobytes(),'<f8').reshape(-1,2,256)
    right=np.array([16*y+(x+1)%16 for y in range(16) for x in range(16)])
    left=np.array([16*y+(x-1)%16 for y in range(16) for x in range(16)])
    down=np.array([16*((y+1)%16)+x for y in range(16) for x in range(16)])
    up=np.array([16*((y-1)%16)+x for y in range(16) for x in range(16)])
    ports=[[16*y+x for y in range(y0,y0+2) for x in range(x0,x0+2)] for y0,x0 in ((7,1),(3,10),(11,10))]
    absolute=np.abs(w);strength=absolute[:,0]+absolute[:,0,left]+absolute[:,1]+absolute[:,1,up]
    result=np.empty((len(w),6))
    for i in range(len(w)):
        nonzero=sorted(float(v) for v in absolute[i].ravel() if v>0)
        nodes=sorted(float(v) for v in strength[i] if v>0)
        def median(v):
            n=len(v);return v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2
        result[i,0]=1-len(nonzero)/512
        result[i,1]=sum(v<.1*median(nonzero) for v in nonzero)/len(nonzero) if nonzero else 1.
        result[i,2]=sum(v<.1*median(nodes) for v in strength[i])/256 if nodes else 1.
        result[i,3]=np.std(strength[i])/np.mean(strength[i]) if nodes else 0.
    denominator=strength.copy();denominator[denominator==0]=1.
    for j,weights in enumerate((w,absolute)):
        x=np.zeros((len(w),256));x[:,ports[0]]=1.
        for iteration in range(32):
            neighbor=weights[:,0]*x[:,right]+weights[:,0,left]*x[:,left]+weights[:,1]*x[:,down]+weights[:,1,up]*x[:,up]
            x=(x+neighbor/denominator)*.5;x[:,ports[0]]=1.
        p=x[:,ports[1]].mean(axis=1);q=x[:,ports[2]].mean(axis=1)
        if j:result[:,4]=np.minimum(p,q)
        else:result[:,5]=np.where(p*q<0,np.minimum(abs(p),abs(q)),0.)
    return result


def risk(model,features):
    coef=model['coefficients'];z=np.full(len(features),coef[0])
    for j in range(features.shape[1]):z+=coef[j+1]*(features[:,j]-model['center'][j])/model['scale'][j]
    return 1/(1+np.exp(-np.maximum(-40.,np.minimum(40.,z))))
