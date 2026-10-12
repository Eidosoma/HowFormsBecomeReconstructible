"""D162 frozen deployment fits and strict two-copy inference interface."""
import numpy as np
from . import group_models as ridge, group_check as svd, target_models as target
from . import difference_ablation as tied, difference_check as tied_check
from . import recovery_features as features, recovery_check, target_check

ALPHAS=(.001,.01,.1)
EDITS=('passive','shuffle','attenuate','sham_plus','sham_minus')
OBSERVERS=target.OBSERVERS+tuple('tied:'+k for k in EDITS)
SELECTED={'tied:sham_minus':.01,'tied:passive':.01,'starting':.001,'one_copy':.01}


def matrices(data):
    if set(data)!={'start','endpoint','targeted'}:raise ValueError('only permitted measurements, no labels/IDs')
    a,e,t=(data[k] for k in ('start','endpoint','targeted'))
    if a.ndim!=4 or a.shape[1:]!=(4,4,7):
        raise ValueError('complete feature panel')
    if e.shape!=a.shape[:3]+(3,6) or t.shape!=e.shape:raise ValueError('two-copy endpoint shapes')
    if any(v.dtype!=np.float64 or not np.isfinite(v).all() for v in data.values()):raise ValueError('finite float64 features')
    result={'starting':a.copy(),'one_copy':np.concatenate((a,e[...,0,:]),axis=-1)}
    for k,second in zip(EDITS,(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])):
        joined=np.concatenate((a,e[...,0,:],second),axis=-1)
        result['separate:'+k]=joined;result['tied:'+k]=joined.copy()
        result['mean:'+k]=np.concatenate((a,(e[...,0,:]+second)/2),axis=-1)
    return result


def independent_matrices(data):
    # Separate column construction; never supply outcomes to forecast assembly.
    a,e,t=(data[k] for k in ('start','endpoint','targeted'))
    out={'starting':a.copy(),'one_copy':np.concatenate([a,e[:,:,:,0]],-1)}
    for j,name in enumerate(EDITS):
        s=e[:,:,:,j+1] if j<2 else t[:,:,:,j-2]
        out['separate:'+name]=np.concatenate([a,e[:,:,:,0],s],-1)
        out['tied:'+name]=np.concatenate([a,e[:,:,:,0],s],-1)
        out['mean:'+name]=np.concatenate([a,(e[:,:,:,0]+s)*.5],-1)
    return out


def extract(raw,edited):
    measured=features.extract({k:raw[k] for k in features.ALLOWED})
    recovery_check.check_features(measured,raw)
    return dict(start=measured['start'],endpoint=measured['endpoint'],targeted=edited['diagnostic_features'].copy())


def fit_all(data):
    target.validate(data)
    x=matrices({k:data[k] for k in ('start','endpoint','targeted')})
    y=data['futures'].mean(-1).ravel();g=np.tile(np.arange(4,dtype=np.int64),4*len(data['block_ids']))
    fitted={}
    for k in OBSERVERS:
        X=x[k].reshape(len(y),-1);fn=tied.fit if k.startswith('tied:') else ridge.fit
        fitted[k]=[fn(X,y,g,a) for a in ALPHAS]
    return dict(training_blocks=data['block_ids'].tolist(),target='four_future_mean',alphas=list(ALPHAS),
        selected=SELECTED.copy(),models=fitted,new_test_data_used=False)


def check_models(fitted,data):
    assert set(fitted)=={'training_blocks','target','alphas','selected','models','new_test_data_used'}
    assert fitted['training_blocks']==data['block_ids'].tolist() and fitted['target']=='four_future_mean'
    assert fitted['alphas']==list(ALPHAS) and fitted['selected']==SELECTED and fitted['new_test_data_used'] is False
    x=independent_matrices({k:data[k] for k in ('start','endpoint','targeted')})
    y=np.sum(data['futures'],axis=-1).ravel()/4;g=np.tile(np.arange(4,dtype=np.int64),len(y)//4)
    assert set(fitted['models'])==set(OBSERVERS)
    for k in OBSERVERS:
        X=x[k].reshape(len(y),-1)
        if k.startswith('tied:'):_,_,records=tied_check.svd_path(X,y,g,X,g)
        else:_,records=svd.svd_path(X,y,g,X,g);records=records[:3]
        recovery_check.same(fitted['models'][k],records)
        for i,model in enumerate(fitted['models'][k]):
            if k.startswith('tied:'):
                source=fitted['models']['separate:'+k.split(':')[1]][i]
                tied_check.geometry(source,model,X,y,g,X,g,target.raw_predict(source,X,g))
    return dict(passes=True,models=51,independent_group_svd=True,training_founders=len(data['block_ids']))


def predict(fitted,data):
    x=matrices(data);n=len(data['start']);g=np.tile(np.arange(4,dtype=np.int64),4*n)
    if fitted['selected']!=SELECTED or set(fitted['models'])!=set(OBSERVERS):raise ValueError('frozen model panel')
    raw={k:np.stack([target.raw_predict(m,x[k].reshape(n*16,-1),g).reshape(n,4,4)
        for m in fitted['models'][k]]) for k in OBSERVERS}
    return {k:np.clip(v,-1,1) for k,v in raw.items()},raw


def check_predictions(p,raw,fitted,data):
    x=independent_matrices(data);n=len(data['start']);g=np.tile(np.arange(4,dtype=np.int64),4*n)
    assert set(p)==set(raw)==set(OBSERVERS)
    for k in OBSERVERS:
        expected=np.stack([target_check.raw_forward(m,x[k].reshape(n*16,-1),g).reshape(n,4,4) for m in fitted['models'][k]])
        np.testing.assert_allclose(raw[k],expected,atol=2e-10,rtol=0)
        np.testing.assert_allclose(p[k],np.maximum(-1,np.minimum(1,expected)),atol=2e-10,rtol=0)
    return dict(passes=True,forecasts=n*16*51,clipped=int(sum(np.count_nonzero(p[k]!=raw[k]) for k in p)))


def fixture(n=4):
    rng=np.random.default_rng(16220260921);start=rng.normal(size=(n,4,4,7))
    return dict(start=start,endpoint=rng.normal(size=(n,4,4,3,6)),targeted=rng.normal(size=(n,4,4,3,6)),
        labels=np.tanh(start[...,0]),futures=np.tanh(start[...,0,None]+rng.normal(0,.4,size=(n,4,4,4))),
        block_ids=np.arange(90000,90000+n,dtype=np.int64))
