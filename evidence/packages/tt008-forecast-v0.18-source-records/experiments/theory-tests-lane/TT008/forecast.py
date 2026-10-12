"""Frozen model families: logistic and conventional Gaussian kernel regression."""
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from scipy.special import expit
from scipy.spatial.distance import cdist
import support as s


def design(rows,kind):
    names=list(s.FIELDS)
    if kind!='expression_history':names+=['unsigned_access']
    x=np.array([[r[k] for k in names]+[float(r['history']==h) for h in s.HISTORIES[1:]] for r in rows])
    names+=['history='+h for h in s.HISTORIES[1:]]
    if kind=='quadratic_unsigned':
        products=[]
        for i in range(4):
            for j in range(i,4):products.append(x[:,i]*x[:,j]);names.append(s.FIELDS[i]+'*'+s.FIELDS[j])
        x=np.column_stack([x,*products])
    if kind=='expression_unsigned_signed':x=np.c_[x,[r['signed_transfer'] for r in rows]];names+=['signed_transfer']
    s.require(np.isfinite(x).all(),'Nonfinite design');return x,names


def scale_fit(x):
    mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale<=1e-12]=1.
    return (x-mean)/scale,dict(mean=mean.tolist(),scale=scale.tolist())


def scale_apply(x,state):return (x-np.array(state['mean']))/np.array(state['scale'])


def logistic_loss(a,y,w):
    z=a@w;p=expit(z);ridge=s.CFG['candidate_ridge']
    loss=float(np.mean(np.logaddexp(0,z)-y*z)+.5*ridge*np.dot(w[1:],w[1:]))
    grad=a.T@(p-y)/len(y);grad[1:]+=ridge*w[1:]
    hess=(a.T*(p*(1-p)))@a/len(y);hess[np.arange(1,len(w)),np.arange(1,len(w))]+=ridge
    return loss,grad,hess


def fit_logistic(x,y):
    z,scaling=scale_fit(x);a=np.c_[np.ones(len(x)),z];w=np.zeros(a.shape[1]);s.require(0<y.sum()<len(y),'Degenerate target')
    for step in range(100):
        loss,g,h=logistic_loss(a,y,w)
        if np.max(abs(g))<=1e-10:return dict(type='logistic',scaling=scaling,coefficients=w.tolist(),loss=loss,maximum_gradient=float(max(abs(g))),iterations=step)
        direction=np.linalg.solve(h,g);fraction=1.
        for _ in range(50):
            proposal=w-fraction*direction
            if logistic_loss(a,y,proposal)[0]<=loss-1e-4*fraction*float(g@direction)+1e-15:break
            fraction*=.5
        else:raise ArithmeticError('Logistic line search')
        w=proposal
    raise ArithmeticError('Logistic convergence')


def logistic_predict(x,fit):return expit(np.c_[np.ones(len(x)),scale_apply(x,fit['scaling'])]@np.array(fit['coefficients']))


def kernel_block_fit(x,multiplier):
    z,scaling=scale_fit(x);distance=cdist(z,z,'sqeuclidean')/z.shape[1];positive=distance[np.triu_indices(len(x),1)];positive=positive[positive>0]
    bandwidth=float(np.median(positive))*multiplier**2 if len(positive) else 1.
    return np.exp(-distance/(2*bandwidth)),dict(scaling=scaling,training=z.tolist(),bandwidth=bandwidth)


def kernel_block_predict(x,state):
    z=scale_apply(x,state['scaling']);training=np.array(state['training'])
    return np.exp(-cdist(z,training,'sqeuclidean')/(z.shape[1]*2*state['bandwidth']))


def fit_kernel(channels,y,multiplier,ridge):
    pieces=[kernel_block_fit(x,multiplier) for x in channels];kernel=sum(p[0] for p in pieces)/len(pieces)
    center=float(y.mean());alpha=cho_solve(cho_factor(kernel+len(y)*ridge*np.eye(len(y)),lower=True),y-center)
    residual=float(np.max(abs((kernel+len(y)*ridge*np.eye(len(y)))@alpha-(y-center))))
    s.require(residual<1e-10,'Kernel linear solve residual')
    return dict(type='kernel',channels=[p[1] for p in pieces],center=center,alpha=alpha.tolist(),ridge=ridge,maximum_residual=residual)


def kernel_predict(channels,fit):
    s.require(len(channels)==len(fit['channels']),'Kernel channel identity')
    kernel=sum(kernel_block_predict(x,state) for x,state in zip(channels,fit['channels'],strict=True))/len(channels)
    return np.clip(fit['center']+kernel@np.array(fit['alpha']),0.,1.)


def candidates():
    result=[dict(id='candidate',family='logistic',kind='expression_unsigned_signed',role='candidate')]
    result.extend(dict(id=name,family='logistic',kind=name,role='expression_rival') for name in s.CFG['logistic_baselines'])
    for kind in s.CFG['kernel_baselines']:
        for bandwidth in s.CFG['kernel_bandwidth_multipliers']:
            for ridge in s.CFG['kernel_ridge']:
                result.append(dict(id=f'{kind}_rbf_b{bandwidth:g}_r{ridge:g}',family='kernel',kind=kind,bandwidth=bandwidth,ridge=ridge,
                    role='full_record_rival' if kind=='packet_plus_expression' else 'expression_rival'))
    return result


def fit_predict(spec,rows,packets,y,train,test):
    kind=spec['kind'] if spec['family']=='logistic' else 'expression_unsigned';x,names=design(rows,kind)
    if spec['family']=='logistic':fit=fit_logistic(x[train],y[train]);p=logistic_predict(x[test],fit)
    else:
        channels=[x]+([packets] if spec['kind']=='packet_plus_expression' else [])
        fit=fit_kernel([c[train] for c in channels],y[train],spec['bandwidth'],spec['ridge']);p=kernel_predict([c[test] for c in channels],fit)
    fit.update(spec=spec,columns=names);return p,fit
