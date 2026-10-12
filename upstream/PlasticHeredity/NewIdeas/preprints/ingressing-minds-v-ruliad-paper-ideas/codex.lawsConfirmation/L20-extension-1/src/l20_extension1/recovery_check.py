"""Independent FFT features, source labels, nested SVD fits and D150 scores."""
import numpy as np
from pathlib import Path
from laws_confirmation import l15_repair_speed_run as io
from . import audit as old_audit,diagnostics as old_sources

ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
CASES=((0,'translated'),(0,'aligned'),(1,'translated'),(1,'aligned'))
MODELS=('starting','passive_endpoint','challenge_endpoint','passive_recovery','challenge_recovery')
ALPHAS=(.001,.01,.1,1.,10.,100.)
CONTRASTS=(('challenge_recovery','passive_recovery'),('challenge_endpoint','passive_endpoint'),
    ('passive_recovery','passive_endpoint'),('challenge_recovery','challenge_endpoint'),
    ('passive_endpoint','starting'),('challenge_endpoint','starting'),
    ('passive_recovery','starting'),('challenge_recovery','starting'))
yy,xx=np.indices((16,16));T=np.stack((np.where(yy<8,1.,-1.),np.where(xx%8<4,1.,-1.)))


def same(a,b):
    if isinstance(b,dict):
        assert isinstance(a,dict) and set(a)==set(b)
        for k in b:same(a[k],b[k])
    elif isinstance(b,(list,tuple)):
        assert isinstance(a,(list,tuple)) and len(a)==len(b)
        for x,y in zip(a,b):same(x,y)
    elif isinstance(b,(float,np.floating)):
        assert not isinstance(a,bool)
        np.testing.assert_allclose(a,b,atol=2e-10,rtol=0)
    else:assert a==b,(a,b)


def unpack(p):
    assert p.dtype==np.uint8 and p.shape==(2048,)
    f=np.frombuffer(p.tobytes(),dtype='<f8').reshape(16,16)
    assert np.isfinite(f).all()
    return f


def shape(f,role):
    values=old_audit.corr(f,T).max(axis=(1,2))
    return values[[role,1-role]]


def axes(f,role):
    z=f-np.sum(f)/256;row=np.sum(z,axis=1)/16;col=np.sum(z,axis=0)/16
    residual=z-row[:,None]-col[None,:]
    a,b=np.sqrt(np.sum(row*row)/16),np.sqrt(np.sum(col*col)/16)
    return [a if role==0 else b,b if role==0 else a,float(np.sqrt(np.sum(residual*residual)/256))]


def check_features(actual,raw):
    assert set(actual)=={'start','endpoint','recovery','stages'}
    assert actual['start'].shape==(4,4,7) and actual['endpoint'].shape==actual['recovery'].shape==(4,4,3,6)
    assert actual['stages'].shape==(4,4,3,4,2)
    initial=np.empty((4,4,7));endpoint=np.empty((4,4,3,6));stages=np.empty((4,4,3,4,2));recovery=np.empty((4,4,3,6))
    for l in range(4):
        for ci,(role,_) in enumerate(CASES):
            packet=raw['founder_packets'][l,role];f=unpack(packet)
            first=old_audit.record_features(packet.tobytes(),role,raw['guide'][l])
            np.testing.assert_allclose(first,raw['initial_features'][l,ci],atol=1e-12,rtol=0)
            initial[l,ci]=np.r_[first,axes(f,role)]
            for copy in range(3):
                outgoing=raw['outgoing'][l,ci,copy].tobytes()
                endpoint[l,ci,copy]=np.r_[old_audit.record_features(outgoing,role,raw['guide'][l]),
                    old_audit.terminal_features(raw['terminal_states'][l,ci,copy,-1,0],role)]
                np.testing.assert_allclose(endpoint[l,ci,copy],raw['diagnostic_features'][l,ci,copy],atol=1e-12,rtol=0)
                np.testing.assert_array_equal(raw['write_states'][l,ci,copy,0,:3],raw['read_states'][l,ci,copy,-1])
                source=(unpack(raw['routed'][l,ci,copy]),raw['read_states'][l,ci,copy,-1,2],
                    raw['write_states'][l,ci,copy,2,2],raw['write_states'][l,ci,copy,-1,2])
                for time,f in enumerate(source):stages[l,ci,copy,time]=shape(f,role)
                a,b,c,d=stages[l,ci,copy]
                recovery[l,ci,copy]=np.concatenate((b-a,c-b,d-c))
    for key,wanted in dict(start=initial,endpoint=endpoint,recovery=recovery,stages=stages).items():
        assert actual[key].dtype==np.float64 and np.isfinite(actual[key]).all()
        np.testing.assert_allclose(actual[key],wanted,atol=1e-12,rtol=0)
    return dict(passes=True,cases=16,diagnostic_copies=48,recovery_values=288,new_dynamics=0)


def body(v,role):
    qualified=abs(v)>.2
    n=[np.count_nonzero(qualified&((v>0)==(target>0))) for target in T]
    return (n[role]-n[1-role])/256


def check_labels(spec,value,disposable=False):
    if spec[0] in ('d135','d140','disposable_dev'):
        source=('disposable',514240) if disposable else spec
        _,_,expected,_=old_sources.source_inputs(*source)
    else:
        run='l20_extension1_heldout_v1_attempt1';stem=f'lineage_{spec[1]}'
        folder=ROOT/('tmp' if disposable else 'outputs')/(run+('_benchmark' if disposable else ''))
        raw=io.load_npz(folder/(stem+'.npz'));meta=io.read_json(folder/(stem+'.json'));expected=np.empty((4,4))
        for life in range(4):
            for ci,(role,kind) in enumerate(CASES):
                p=meta['lives'][life]['probes'].index([role,kind])
                expected[life,ci]=body(raw['terminal_states'][life,p,-1,0],role)
                assert expected[life,ci]==raw['terminal_values'][life,p,-1,0]-raw['terminal_values'][life,p,-1,1]
    np.testing.assert_array_equal(value,expected)
    return True


def check_futures(index,value):
    directory=ROOT/'outputs/l20_extension1_repeated_futures_v1_attempt1'
    raw=io.load_npz(directory/f'block_{index}.npz');meta=io.read_json(directory/f'block_{index}.json')
    assert meta['index']==index and value.shape==(4,4,4)
    for life in range(4):
        for copy in range(4):
            for ci,(role,_) in enumerate(CASES):
                wanted=body(raw['terminal_states'][life,copy,ci,-1,0],role)
                assert wanted==value[life,ci,copy]
                assert wanted==raw['terminal_values'][life,copy,ci,-1,0]-raw['terminal_values'][life,copy,ci,-1,1]
    return True


def matrices(data):
    a,e,r=data['start'],data['endpoint'],data['recovery'];values={'starting':a.copy()}
    for observer,copy in (('passive',1),('challenge',2)):
        values[observer+'_endpoint']=np.concatenate([a,e[...,0,:],e[...,copy,:]],axis=-1)
        values[observer+'_recovery']=np.concatenate([a,e[...,0,:],e[...,copy,:],r[...,0,:],r[...,copy,:]],axis=-1)
    return {k:values[k] for k in MODELS}


def svd_path(x,y,g,test,h):
    assert np.isfinite(x).all() and np.isfinite(y).all() and set(g.tolist())==set(range(4))
    mu=np.stack([np.sum(x[g==j],axis=0)/np.count_nonzero(g==j) for j in range(4)])
    offset=np.array([np.sum(y[g==j])/np.count_nonzero(g==j) for j in range(4)])
    centered=x-mu[g];sd=np.sqrt(np.sum(centered*centered,axis=0)/len(y));sd[sd<=1e-12]=1
    z=centered/sd;target=y-offset[g]
    u,s,vh=np.linalg.svd(z/np.sqrt(len(y)),full_matrices=False)
    projection=u.T@(target/np.sqrt(len(y)));rows=[];models=[]
    for alpha in ALPHAS:
        beta=vh.T@((s/(s*s+alpha))*projection)
        guesses=offset[h]+((test-mu[h])/sd)@beta
        rows.append(np.minimum(1.,np.maximum(-1.,guesses)))
        models.append(dict(alpha=alpha,means=mu.tolist(),offsets=offset.tolist(),scale=sd.tolist(),beta=beta.tolist()))
    return np.stack(rows,axis=-1),models


def check_nested(predictions,metadata,x,y,ids):
    n=len(x);assert x.shape[:3]==y.shape==(n,4,4) and len(ids)==n
    X=x.reshape(n*16,-1);Y=y.reshape(n*16);g=np.tile(np.arange(4,dtype=np.int64),n*4)
    expected=[];values=np.empty((n,4,4))
    for outer in range(n):
        blocks=[i for i in range(n) if i!=outer];losses=[]
        rows=lambda indexes:np.concatenate([np.arange(16*i,16*i+16) for i in indexes])
        for inner in blocks:
            train=rows([i for i in blocks if i!=inner]);test=rows([inner])
            p,_=svd_path(X[train],Y[train],g[train],X[test],g[test])
            losses.append(np.sum((p-Y[test,None])**2,axis=0)/16)
        errors=np.asarray(losses);mean=np.sum(errors,axis=0)/(n-1)
        ai=[i for i,v in enumerate(mean) if v<=min(mean)+1e-12][-1]
        train=rows(blocks);test=rows([outer]);p,models=svd_path(X[train],Y[train],g[train],X[test],g[test])
        values[outer]=p[:,ai].reshape(4,4)
        expected.append(dict(validation_block=int(ids[outer]),training_blocks=[int(ids[b]) for b in blocks],
            inner_validation_blocks=[int(ids[b]) for b in blocks],inner_block_mse=errors.tolist(),
            inner_mean_mse=mean.tolist(),selected_index=ai,model=models[ai]))
    np.testing.assert_allclose(predictions,values,atol=2e-10,rtol=0)
    same(metadata,dict(blocks=ids.tolist(),alphas=list(ALPHAS),folds=expected,
        preprocessing='training-only in every inner and outer fold',prospective_evidence=False))
    return dict(passes=True,outer_folds=n,inner_folds=n*(n-1),rows=n*16,prospective_evidence=False)


def check_fits(predictions,fits,data,y,ids):
    assert set(predictions)==set(fits)==set(MODELS)
    x=matrices(data)
    checks={k:check_nested(predictions[k],fits[k],x[k],y,ids) for k in MODELS}
    return dict(passes=True,models=5,outer_folds=5*len(ids),inner_folds=5*len(ids)*(len(ids)-1),
        rows=len(ids)*16,prospective_evidence=False,checks=checks)


def error_stats(prediction,y):
    e=prediction-y;n=len(y);mse=float(np.sum(e*e)/(n*16))
    return dict(mse=mse,mae_points=float(np.sum(abs(e))*100/(n*16)),rmse_points=float(np.sqrt(mse)*100),
        block_mse=(np.sum(e*e,axis=(1,2))/16).tolist(),block_mae_points=(np.sum(abs(e),axis=(1,2))*100/16).tolist(),
        group_mse=(np.sum(e*e,axis=(0,1))/(n*4)).tolist())


def reduction(candidate,reference):
    n=len(candidate);delta=np.sum(reference-candidate,axis=(1,2))/16;mean=float(sum(delta)/n);base=float(np.sum(reference)/(n*16))
    return dict(mse_reduction=mean,relative_reduction_percent=100*mean/base if base else None,
        block_differences=delta.tolist(),positive_blocks=int(np.count_nonzero(delta>0)),
        negative_blocks=int(np.count_nonzero(delta<0)),zero_blocks=int(np.count_nonzero(delta==0)))


def check_summary(summary,predictions,fits,y,futures,specs):
    assert y.shape==(32,4,4) and futures.shape==(16,4,4,4)
    assert [s[0] for s in specs]==['d135']*8+['d140']*8+['former_test']*16
    scores={};repeated={};errors={};future_errors={};mean_errors={}
    for name in MODELS:
        p=predictions[name];errors[name]=(p-y)**2;score=error_stats(p,y)
        score['cohorts']={key:error_stats(p[a:b],y[a:b]) for key,a,b in (('d135',0,8),('d140',8,16),('former_test',16,32))}
        selected=[fold['model']['alpha'] for fold in fits[name]['folds']]
        score['selected_alphas']=selected;score['alpha_counts']={str(a):sum(v==a for v in selected) for a in ALPHAS}
        scores[name]=score
        e=p[16:,...,None]-futures;future_errors[name]=np.sum(e*e,axis=-1)/4
        mean_errors[name]=(p[16:]-np.sum(futures,axis=-1)/4)**2
        repeated[name]=dict(individual_future_mse=float(np.sum(e*e)/1024),individual_future_mae_points=float(np.sum(abs(e))*100/1024),
            individual_future_block_mse=(np.sum(e*e,axis=(1,2,3))/64).tolist(),
            individual_future_group_mse=(np.sum(e*e,axis=(0,1,3))/256).tolist(),
            mean_target_mse=float(np.sum(mean_errors[name])/256),mean_target_block_mse=(np.sum(mean_errors[name],axis=(1,2))/16).tolist(),
            mean_target_group_mse=(np.sum(mean_errors[name],axis=(0,1))/64).tolist())
    pairs=[];rep=[]
    for candidate,reference in CONTRASTS:
        pairs.append(dict(candidate=candidate,reference=reference,**reduction(errors[candidate],errors[reference])))
        a=reduction(future_errors[candidate],future_errors[reference]);b=reduction(mean_errors[candidate],mean_errors[reference])
        np.testing.assert_allclose(a['block_differences'],b['block_differences'],atol=1e-14,rtol=0)
        rep.append(dict(candidate=candidate,reference=reference,individual_futures=a,mean_target=b))
    expected=dict(schema='d150_recovery_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',prospective_evidence=False,
        all_cases_retained=True,blocks=32,cases=512,diagnostic_cycles=1536,new_dynamics=0,new_founders=0,
        former_test_is_now_development=True,models=scores,comparisons=pairs,central_comparison=pairs[0],
        repeated_future_models=repeated,repeated_future_comparisons=rep,repeated_future_blocks=16,
        repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,confidence_intervals=False,
        success_threshold=False,model_selected_for_deployment=False,new_challenge_selected=False,automatic_successor=False,
        interpretation='Exploratory nested whole-founder validation on observed cohorts; not new prospective evidence.')
    same(summary,expected)
    return dict(passes=True,models=5,comparisons=8,blocks=32,cases=512,repeated_blocks=16,repeated_outcomes=1024,
        prospective_evidence=False,confidence_intervals=False,new_dynamics=0)
