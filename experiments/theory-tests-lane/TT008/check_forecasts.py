"""Synthetic checks of fitting, information isolation and kernel construction."""
import copy
import numpy as np
import forecast as f
import support as s


def run():
    rng=np.random.default_rng(801);x=rng.normal(size=(80,7));x[:,0]=1.;y=rng.integers(0,2,80).astype(float);train=np.arange(80)<64
    scaled,state=f.scale_fit(x[train]);s.close(scaled.mean(axis=0),np.zeros(7),1e-15)
    kernel,fit=f.kernel_block_fit(x[train],1.)
    # Scalar pair formula is independent of scipy.cdist and vector normalization.
    for i,j in [(0,0),(2,31),(40,7)]:
        distance=sum((float(scaled[i,k])-float(scaled[j,k]))**2 for k in range(7))/7
        s.close(kernel[i,j],np.exp(-distance/(2*fit['bandwidth'])),1e-14)
    s.require(np.linalg.eigvalsh(kernel).min()>-1e-12,'Kernel PSD')
    kk=f.fit_kernel([x[train]],y[train],1.,.01);p=f.kernel_predict([x[~train]],kk)
    fixed=f.fit_logistic(x[train],y[train]);z=f.logistic_predict(x[~train],fixed)
    xx=x.copy();xx[~train]=17;yy=y.copy();yy[~train]=1-yy[~train]
    s.require(kk==f.fit_kernel([xx[train]],yy[train],1.,.01),'Held-out fields changed kernel')
    s.require(fixed==f.fit_logistic(xx[train],yy[train]),'Held-out fields changed logistic')
    s.require(np.isfinite(p).all() and ((p>=0)&(p<=1)).all() and ((z>0)&(z<1)).all(),'Prediction range')
    a=np.c_[np.ones(80),x];w=rng.normal(size=8);_,gradient,hessian=f.logistic_loss(a,y,w);eps=1e-5;basis=np.eye(8)*eps
    numeric=np.array([(f.logistic_loss(a,y,w+d)[0]-f.logistic_loss(a,y,w-d)[0])/(2*eps) for d in basis]);s.close(gradient,numeric,1e-9)
    numeric_h=np.column_stack([(f.logistic_loss(a,y,w+d)[1]-f.logistic_loss(a,y,w-d)[1])/(2*eps) for d in basis]);s.close(hessian,numeric_h,1e-9)
    rows=[dict(history=s.HISTORIES[i%4],**{k:float(rng.random()) for k in [*s.FIELDS,'unsigned_access','signed_transfer']},terminal_success=i%2,block=i,founder=i,recipient=i) for i in range(32)]
    other=copy.deepcopy(rows)
    for row in other:
        for k in ['terminal_success','terminal_margin','block','founder','recipient','seed','future']:row[k]=99999
    for kind in ['expression_history','expression_unsigned','quadratic_unsigned','expression_unsigned_signed']:
        s.close(f.design(rows,kind)[0],f.design(other,kind)[0],0.,'Forbidden predictor field')
    return dict(status='PASS',groups=4,checks=['kernel_scalar_formula_and_PSD','heldout_training_isolation','finite_difference_gradient_and_Hessian','future_and_identity_field_exclusion'])


if __name__=='__main__':print(run())
