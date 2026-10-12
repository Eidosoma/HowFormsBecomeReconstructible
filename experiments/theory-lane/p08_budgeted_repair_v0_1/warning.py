"""Fixed, task-label-free incoming-record features and penalized logistic fit."""
import numpy as np

NAMES=['zero_edge_fraction','weak_observed_edge_fraction','weak_node_fraction',
       'node_strength_cv','unsigned_output_reach','signed_output_separation']
PORTS=[(slice(y,y+2),slice(x,x+2)) for y,x in ((7,1),(3,10),(11,10))]


def incident(w):
    return w[:,0]+np.roll(w[:,0],1,-1)+w[:,1]+np.roll(w[:,1],1,-2)


def features(packets):
    assert packets.ndim==2 and packets.shape[1]==4096 and packets.dtype==np.uint8
    w=np.frombuffer(packets.tobytes(),'<f8').reshape(-1,2,16,16)
    a=abs(w);observed=a>0;strength=incident(a)
    result=np.zeros((len(w),6));result[:,0]=(~observed).mean(axis=(1,2,3))
    for i in range(len(w)):
        edges=a[i][observed[i]];nodes=strength[i][strength[i]>0]
        result[i,1]=float((edges<.1*np.median(edges)).mean()) if len(edges) else 1.
        result[i,2]=float((strength[i]<.1*np.median(nodes)).mean()) if len(nodes) else 1.
        result[i,3]=strength[i].std()/strength[i].mean() if len(nodes) else 0.
    denominator=np.where(strength>0,strength,1.)
    for unsigned in (False,True):
        weights=a if unsigned else w
        x=np.zeros((len(w),16,16));x[:,PORTS[0][0],PORTS[0][1]]=1.
        for _ in range(32):
            neighbor=(weights[:,0]*np.roll(x,-1,-1)+np.roll(weights[:,0],1,-1)*np.roll(x,1,-1)
                      +weights[:,1]*np.roll(x,-1,-2)+np.roll(weights[:,1],1,-2)*np.roll(x,1,-2))
            x=.5*(x+neighbor/denominator);x[:,PORTS[0][0],PORTS[0][1]]=1.
        p,q=(x[:,s[0],s[1]].mean(axis=(1,2)) for s in PORTS[1:])
        if unsigned:result[:,4]=np.minimum(p,q)
        else:result[:,5]=.5*(abs(p)+abs(q)-abs(p+q))
    assert np.isfinite(result).all()
    return result


def sigmoid(x):return 1./(1.+np.exp(-np.clip(x,-40.,40.)))


def fit(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    assert len(x)==len(y) and 0<y.sum()<len(y)
    center=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale>1e-12,scale,1.)
    design=np.column_stack((np.ones(len(y)),(x-center)/scale))
    coef=np.zeros(design.shape[1]);coef[0]=np.log(y.mean()/(1-y.mean()))
    penalty=np.eye(len(coef));penalty[0,0]=0.
    def objective(v):
        z=design@v
        return float(np.logaddexp(0,z).sum()-y@z+.5*v@penalty@v)
    converged=False
    for iteration in range(100):
        p=sigmoid(design@coef)
        gradient=design.T@(p-y)+penalty@coef
        if abs(gradient).max()<1e-7:converged=True;break
        hessian=design.T@((p*(1-p))[:,None]*design)+penalty
        delta=np.linalg.solve(hessian,gradient);step=1.;before=objective(coef)
        while objective(coef-step*delta)>before-1e-4*step*(gradient@delta):
            step*=.5
            assert step>2**-40,'logistic line search stalled'
        coef-=step*delta
    assert converged,'logistic fit did not converge'
    return dict(center=center.tolist(),scale=scale.tolist(),coefficients=coef.tolist(),
                iterations=iteration+1,converged=converged,ridge=1.,n=int(len(y)),events=int(y.sum()))


def predict(model,x):
    z=(np.asarray(x)-model['center'])/model['scale'];c=np.array(model['coefficients'])
    return sigmoid(c[0]+z@c[1:])


def metrics(y,p):
    y=np.asarray(y,bool);p=np.asarray(p,float);eps=np.finfo(float).eps
    loss=-(y*np.log(np.clip(p,eps,1-eps))+(~y)*np.log(np.clip(1-p,eps,1-eps))).mean()
    order=np.argsort(-p,kind='stable');a=y[order];s=p[order]
    ends=np.r_[np.flatnonzero(np.diff(s)!=0),len(y)-1]
    tp=np.cumsum(a)[ends];fp=ends+1-tp
    # Threshold-grouped AP and trapezoidal ROC handle equal scores without case-order bias.
    precision=tp/(ends+1);recall=tp/y.sum()
    ap=np.sum(np.diff(np.r_[0.,recall])*precision)
    auc=np.trapezoid(np.r_[0.,recall],np.r_[0.,fp/(~y).sum()])
    return dict(log_loss=float(loss),brier=float(((p-y)**2).mean()),AUROC=float(auc),average_precision=float(ap))
