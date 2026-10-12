"""D151 post-result saved-case accounting; no dynamics or predictor fitting."""
import numpy as np
from . import placement_review as field

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
BRANCHES=('U0','U1','C1','attenuate','sham_plus','sham_minus')
GROUPS=('A ordinary','A aligned','B ordinary','B aligned')
CONTRASTS=(('attenuate','passive'),('attenuate','starting'),('attenuate','shuffle'),
 ('attenuate','sham_plus'),('attenuate','sham_minus'),('attenuate','mean_sham_loss'),
 ('sham_plus','passive'),('sham_minus','passive'),('passive','starting'),('shuffle','passive'))
STAGES=('selected_input',)+tuple('read_R_'+str(t) for t in (0,1,100,101,300))+tuple(
 'write_R_'+str(t) for t in (0,1,300,1000))+('outgoing_record','routed_outgoing')+tuple(
 'fresh_R_'+str(t) for t in (0,1,100,300))+tuple('fresh_V_'+str(t) for t in (0,1,100,300))
RESPONSE_BRANCHES=(0,2,3,4,5)


def unpack(value):
    assert value.dtype==np.uint8 and value.shape[-1]==2048
    return np.frombuffer(value.tobytes(),'<f8').reshape(value.shape[:-1]+(16,16))


def extract(raw,original):
    fields=np.empty((4,4,6,20,15));preference=np.empty((4,4,6,4))
    for branch in range(6):
        source,j=(original,branch) if branch<3 else (raw,branch-3)
        for group in range(4):
            role=group//2
            read=source['read_states'][:,group,j];write=source['write_states'][:,group,j]
            final=source['terminal_states'][:,group,j]
            assert read.shape==(4,5,3,16,16) and write.shape==(4,4,4,16,16) and final.shape==(4,4,3,16,16)
            np.testing.assert_array_equal(read[:,-1],write[:,0,:3])
            incoming=source['routed' if branch<3 else 'input'][:,group,j]
            v=np.concatenate((unpack(incoming)[:,None],read[:,:,2],write[:,:,2],
                unpack(source['outgoing'][:,group,j])[:,None],unpack(source['terminal_packet'][:,group,j])[:,None],
                final[:,:,2],final[:,:,0]),axis=1)
            assert v.shape==(4,20,16,16)
            fields[:,group,branch]=field.measure(v,role)
            code=field.codes(final[:,:,0],role)
            preference[:,group,branch]=((code==1).sum(-1)-(code==2).sum(-1))/256
            endpoint=source['diagnostic_features'][:,group,j]
            np.testing.assert_array_equal(preference[:,group,branch,-1],endpoint[:,4])
            for si,fi,ei in ((10,6,0),(10,8,1),(11,5,3),(19,1,5)):
                np.testing.assert_allclose(fields[:,group,branch,si,fi],endpoint[:,ei],atol=1e-11,rtol=0)
            if branch>=3:
                np.testing.assert_array_equal(read[:,0],original['read_states'][:,group,1,0])
                np.testing.assert_array_equal(final[:,0],original['terminal_states'][:,group,1,0])
    return dict(fields=fields,preference=preference)


def loss_terms(prediction,y):
    assert prediction.shape==y.shape+(6,) and y.ndim==3 and y.shape[1:]==(4,4)
    error=prediction-y[...,None];terms=[]
    for a,b in CONTRASTS:
        candidate=prediction[...,MODELS.index(a)]
        refs=('sham_plus','sham_minus') if b=='mean_sham_loss' else (b,)
        rows=[]
        for ref in refs:
            delta=candidate-prediction[...,MODELS.index(ref)];e=error[...,MODELS.index(ref)]
            square=delta*delta;cross=2*delta*e
            rows.append(np.stack((square,cross,square+cross),-1))
        terms.append(np.mean(rows,axis=0))
    return error,np.stack(terms,-2)


def describe(x):
    x=np.asarray(x);assert x.ndim==2 and x.shape[1]==4 and np.isfinite(x).all()
    return dict(mean=float(x.mean()),block_means=x.mean(axis=1).tolist(),positive=int((x>0).sum()),
        negative=int((x<0).sum()),zero=int((x==0).sum()))


def correlation(x,y):
    x=np.asarray(x).ravel();y=np.asarray(y).ravel()
    assert x.shape==y.shape and len(x)>1 and np.isfinite(x).all() and np.isfinite(y).all()
    if np.ptp(x)==0 or np.ptp(y)==0:return None
    a=x-x.mean();b=y-y.mean()
    return float(np.clip(np.dot(a,b)/np.sqrt(np.dot(a,a)*np.dot(b,b)),-1,1))


def association(x,y):
    assert x.shape==y.shape and x.ndim==2 and x.shape[1]==4
    return dict(cases=x.size,blocks=len(x),case_r=correlation(x,y),block_mean_r=correlation(x.mean(1),y.mean(1)))


def error_stats(e):
    return dict(mse=float(np.mean(e*e)),mae_points=float(np.mean(abs(e))*100),
        rmse_points=float(np.sqrt(np.mean(e*e))*100),bias_points=float(e.mean()*100),
        centered_error_variance=float(np.var(e)))


def assemble(blocks,data,predictions):
    assert len(blocks)==len(data['labels'])==32
    p=np.stack([predictions[k] for k in MODELS],-1);error,terms=loss_terms(p,data['labels'])
    fields=np.stack([b['fields'] for b in blocks]);preference=np.stack([b['preference'] for b in blocks])
    return dict(fields=fields,preference=preference,block_field_means=fields.mean(axis=1),
        block_preference_means=preference.mean(axis=1),
        start=data['start'].copy(),labels=data['labels'].copy(),futures=data['futures'].copy(),
        block_ids=data['block_ids'].copy(),predictions=p,error=error,absolute_error=abs(error),
        squared_error=error**2,comparison_terms=terms)


def architecture(fits):
    assert set(fits)==set(MODELS);rows=[]
    for mi,name in enumerate(MODELS):
        d=7 if mi==0 else 19;value=fits[name];assert len(value['folds'])==32
        assert [f['validation_block'] for f in value['folds']]==value['blocks']
        for fold in value['folds']:
            m=fold['model'];assert np.shape(m['beta'])==(d,) and np.shape(m['means'])==(4,d)
            assert np.shape(m['offsets'])==(4,) and np.shape(m['scale'])==(d,)
        rows.append(dict(model=name,folds=32,dimensions=d,group_intercepts=4,shared_slope_vectors_per_fold=1))
    return rows


def summarize(panel,arch,fixture=False):
    f,q=panel['fields'],panel['preference'];p,y,e=panel['predictions'],panel['labels'],panel['error']
    assert f.shape==(32,4,4,6,20,15) and q.shape==(32,4,4,6,4)
    assert p.shape==e.shape==(32,4,4,6) and y.shape==(32,4,4)
    assert panel['futures'].shape==(16,4,4,4) and panel['start'].shape==(32,4,4,7)
    assert all(np.isfinite(v).all() for v in panel.values())
    np.testing.assert_array_equal(e,p-y[...,None]);expected_e,t=loss_terms(p,y)
    np.testing.assert_allclose(panel['comparison_terms'],t,atol=1e-14,rtol=0)
    sections={}
    for cohort,a,b in (('all',0,32),('d135',0,8),('d140',8,16),('former_test',16,32)):
        errors=e[a:b];stats=[];pairs=[]
        for mi,name in enumerate(MODELS):
            v=errors[...,mi];total=float(np.sum(v*v));groups=[]
            for gi,g in enumerate(GROUPS):
                z=v[:,:,gi];item=error_stats(z)
                item.update(group=g,block_mse=np.mean(z*z,axis=1).tolist(),
                    squared_error_share_percent=100*float(np.sum(z*z))/total if total else None)
                groups.append(item)
            stats.append(dict(model=name,**error_stats(v),groups=groups))
        for ci,(candidate,reference) in enumerate(CONTRASTS):
            terms=t[a:b,...,ci,:]
            pairs.append(dict(candidate=candidate,reference=reference,terms=terms.mean(axis=(0,1,2)).tolist(),
                group_terms=terms.mean(axis=(0,1)).tolist(),block_terms=terms.mean(axis=(1,2)).tolist()))
        sections[cohort]=dict(blocks=b-a,cases=(b-a)*16,models=stats,comparisons=pairs)
    trajectories=[];responses=[];links=[];future_links=[]
    for gi,g in enumerate(GROUPS):
        for bi,branch in enumerate(BRANCHES):
            trajectories.append(dict(group=g,branch=branch,fields=f[:,:,gi,bi].mean(axis=(0,1)).tolist(),
                preference=q[:,:,gi,bi].mean(axis=(0,1)).tolist()))
        for bi in RESPONSE_BRANCHES:
            x=q[:,:,gi,bi,-1]-q[:,:,gi,1,-1]
            responses.append(dict(group=g,branch=BRANCHES[bi],matched_noise=bi!=0,endpoint=describe(x),
                fields=(f[:,:,gi,bi]-f[:,:,gi,1]).mean(axis=(0,1)).tolist(),
                preference=(q[:,:,gi,bi]-q[:,:,gi,1]).mean(axis=(0,1)).tolist()))
            targets=dict(starting_own_best=panel['start'][:,:,gi,0],original_outcome=y[:,:,gi],
                passive_signed_error=e[:,:,gi,1],passive_squared_error=e[:,:,gi,1]**2,
                attenuation_minus_passive_squared_error=e[:,:,gi,3]**2-e[:,:,gi,1]**2)
            for key,target in targets.items():links.append(dict(group=g,branch=BRANCHES[bi],target=key,**association(x,target)))
            for key,target in (('future_mean',panel['futures'][:,:,gi].mean(-1)),
                               ('future_sample_variance',panel['futures'][:,:,gi].var(-1,ddof=1))):
                future_links.append(dict(group=g,branch=BRANCHES[bi],target=key,**association(x[16:],target)))
    future=[];spread=panel['futures'].var(-1);mean=panel['futures'].mean(-1)
    for mi,name in enumerate(MODELS):
        individual=(p[16:,...,mi,None]-panel['futures'])**2;mean_loss=(p[16:,...,mi]-mean)**2
        np.testing.assert_allclose(individual.mean(-1),mean_loss+spread,atol=1e-14,rtol=0)
        future.append(dict(model=name,individual_mse=float(individual.mean()),mean_target_mse=float(mean_loss.mean()),
            within_future_population_variance=float(spread.mean()),
            group_individual_mse=individual.mean(axis=(0,1,3)).tolist(),group_mean_mse=mean_loss.mean(axis=(0,1)).tolist(),
            group_spread=spread.mean(axis=(0,1)).tolist()))
    return dict(schema='d151_saved_case_review_v1',posthoc=True,fixture=fixture,new_dynamics=0,new_models=0,
        prospective_evidence=False,all_cases_retained=True,blocks=32,cases=512,architecture=arch,
        model_order=list(MODELS),branch_order=list(BRANCHES),stage_order=list(STAGES),field_order=list(field.FIELDS),
        error_terms=['prediction_change_squared','twice_change_times_reference_error','candidate_minus_reference_loss'],
        sections=sections,trajectories=trajectories,responses=responses,associations=links,
        repeated_future_associations=future_links,repeated_future_accounting=future,
        no_observer_budget_claim_for_multibranch_review=True,repair_durability_measured=False)


def fixture(block,seed=151920):
    rng=np.random.default_rng(seed);y=rng.uniform(-.5,.5,(32,4,4))
    p={k:np.clip(y+rng.normal(0,.12,y.shape),-1,1) for k in MODELS}
    data=dict(labels=y,start=rng.normal(size=(32,4,4,7)),futures=rng.uniform(-.5,.5,(16,4,4,4)),
        block_ids=np.arange(32,dtype=np.int64))
    arch=[dict(model=k,folds=32,dimensions=7 if i==0 else 19,group_intercepts=4,shared_slope_vectors_per_fold=1) for i,k in enumerate(MODELS)]
    return assemble([block]*32,data,p),arch
