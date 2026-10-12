"""Independent D160 constrained group-coordinate SVD and source-score checks."""
import numpy as np
from . import target_check as old, influence_check as reference

ALPHAS=(.001,.01,.1)
EDITED=('passive','shuffle','attenuate','sham_plus','sham_minus')
NEW=tuple('tied:'+k for k in EDITED)
OBSERVERS=old.OBSERVERS+NEW
NEW_LOSS=NEW+('tied:mean_sham_loss',)
CLASS='raw_reading_difference_zero_original_ridge_penalty'


def specifications():
    pairs=[]
    for edit in EDITED:
        for ref in ('separate:'+edit,'mean:'+edit,'starting','one_copy'):pairs.append(('tied:'+edit,ref))
    for edit in EDITED[1:]+('mean_sham_loss',):pairs.append(('tied:'+edit,'tied:passive'))
    for edit in ('shuffle','sham_plus','sham_minus','mean_sham_loss'):pairs.append(('tied:attenuate','tied:'+edit))
    for ref in ('starting','one_copy','separate:mean_sham_loss','mean:mean_sham_loss'):
        pairs.append(('tied:mean_sham_loss',ref))
    return tuple(pairs)


def prepare(x,y,g):
    means=np.array([np.sum(x[g==v],axis=0)/np.count_nonzero(g==v) for v in range(4)])
    offsets=np.array([np.sum(y[g==v])/np.count_nonzero(g==v) for v in range(4)])
    centered=x-means[g];scales=np.sqrt(np.sum(centered**2,axis=0)/len(x));scales[scales<=1e-12]=1
    return means,offsets,scales,centered,y-offsets[g]


def reduced_features(centered,scales):
    scale_m=np.sqrt(scales[7:13]**2+scales[13:]**2)/2
    mean=(centered[:,7:13]+centered[:,13:])/2
    return np.concatenate([centered[:,:7]/scales[:7],mean/scale_m],axis=1)


def svd_path(x,y,g,test,h):
    mu,offset,s,centered,target=prepare(x,y,g)
    z=reduced_features(centered,s);test_z=reduced_features(test-mu[h],s)
    white=np.eye(4)+.25*np.ones((4,4))
    design=np.einsum('ig,ij->igj',white[g],z).reshape(len(x),52)
    u,singular,vh=np.linalg.svd(design/np.sqrt(len(y)),full_matrices=False)
    projected=u.T@(target/np.sqrt(len(y)))
    q=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]],dtype=float)/2
    records=[];raw=[]
    for alpha in ALPHAS:
        theta=(vh.T@((singular/(singular*singular+alpha))*projected)).reshape(4,13)
        slopes=white@theta
        reduced=np.vstack([np.sum(slopes,axis=0)/4,q.T@slopes])
        beta=np.zeros((4,19));beta[:,:7]=reduced[:,:7]
        norm=np.sqrt(s[7:13]**2+s[13:]**2)
        beta[:,7:13]=reduced[:,7:]*s[7:13]/norm
        beta[:,13:]=reduced[:,7:]*s[13:]/norm
        records.append(dict(alpha=alpha,means=mu.tolist(),offsets=offset.tolist(),scale=s.tolist(),
            coefficients=beta.tolist(),reduced_coefficients=reduced.tolist(),model_class=CLASS))
        raw.append(offset[h]+np.sum(test_z*slopes[h],axis=1))
    raw=np.stack(raw)
    return np.maximum(-1,np.minimum(1,raw)),raw,records


def explicit_design(z,g):
    q=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]],dtype=float)/2
    return np.hstack((z,z*q[g,0,None],z*q[g,1,None],z*q[g,2,None]))


def geometry(source,limited,x,y,g,test,h,source_raw):
    mu,offset,s,centered,target=prepare(x,y,g)
    for record in (source,limited):
        for k,v in (('means',mu),('offsets',offset),('scale',s)):
            np.testing.assert_allclose(record[k],v,atol=2e-10,rtol=0)
    a=explicit_design(centered/s,g);alpha=source['alpha']
    beta=np.asarray(source['coefficients']);limited_beta=np.asarray(limited['coefficients'])
    w=beta/s;level=w[:,7:13]+w[:,13:];difference=w[:,13:]-w[:,7:13]
    gamma=np.hstack((w[:,:7],level,difference))
    tz=test-mu[h];test_md=np.hstack((tz[:,:7],(tz[:,7:13]+tz[:,13:])/2,(tz[:,13:]-tz[:,7:13])/2))
    prediction=offset[h]+explicit_design(test_md,h)@gamma.ravel()
    np.testing.assert_allclose(prediction,source_raw,atol=2e-10,rtol=0)
    np.testing.assert_allclose(old.raw_forward(source,test,h),source_raw,atol=2e-10,rtol=0)
    # Full transformed metric, including the cross term when the scales differ.
    penalty=float(np.sum((w[:,:7]*s[:7])**2)
        +np.sum(.25*(s[7:13]**2+s[13:]**2)*(level**2+difference**2)
        +.5*(s[13:]**2-s[7:13]**2)*level*difference))
    original_penalty=float(np.sum(beta**2))
    np.testing.assert_allclose(penalty,original_penalty,atol=2e-10,rtol=0)
    normal=a.T@(a@beta.ravel()-target)/len(y)+alpha*beta.ravel()
    np.testing.assert_allclose(normal,0,atol=2e-10,rtol=0)
    reduced=explicit_design(reduced_features(centered,s),g);eta=np.asarray(limited['reduced_coefficients'])
    rnormal=reduced.T@(reduced@eta.ravel()-target)/len(y)+alpha*eta.ravel()
    np.testing.assert_allclose(rnormal,0,atol=2e-10,rtol=0)
    restriction=float(np.max(abs(limited_beta[:,13:]/s[13:]-limited_beta[:,7:13]/s[7:13])))
    assert restriction<=2e-10
    np.testing.assert_allclose(np.sum(limited_beta**2),np.sum(eta**2),atol=2e-10,rtol=0)
    original=float(np.sum((a@beta.ravel()-target)**2)/len(y)+alpha*original_penalty)
    restricted=float(np.sum((a@limited_beta.ravel()-target)**2)/len(y)+alpha*np.sum(limited_beta**2))
    assert restricted>=original-2e-10
    return dict(full_objective=original,restricted_objective=restricted,objective_increase=restricted-original,
        full_stationarity=float(np.max(abs(normal))),restricted_stationarity=float(np.max(abs(rnormal))),
        max_abs_reexpression=float(np.max(abs(prediction-source_raw))),penalty_identity_residual=abs(penalty-original_penalty),
        max_abs_raw_difference_slope=restriction)


def check_all(nb,nbr,npred,nraw,fits,data,b,br,p,raw,bfits,rfits):
    old.labels(data);n=len(data['block_ids']);assert n>=5;ids=data['block_ids']
    assert set(nb)==set(nbr)==set(npred)==set(nraw)==set(fits)==set(NEW)
    x=old.matrices(data);y=np.sum(data['futures'],axis=-1)/4;g=np.tile(np.arange(4,dtype=np.int64),4*n)
    counts=0;max_prediction=0.;max_difference=0.;max_geometry=0.;min_increase=float('inf')
    for name in NEW:
        source='separate:'+name.split(':')[1];X=x[source].reshape(n*16,19);Y=y.ravel();record=fits[name]
        old.same({k:v for k,v in bfits[source].items() if k!='folds'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            training_targets=list(old.TARGETS),model_class=old.group.CLASS,observer=source,
            preprocessing='training-only within each whole-founder fold',inner_selection=False,prospective_evidence=False))
        old.same({k:v for k,v in rfits[source].items() if k!='deletions'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            target='future_mean',observer=source,model_class=old.group.CLASS,training_blocks_per_fold=n-2,
            inner_selection=False,preprocessing='training-only; deletion and validation founder excluded'))
        assert br[source].shape==b[source].shape==(3,n,4,4)
        assert raw[source].shape==p[source].shape==(n,3,n-1,4,4)
        np.testing.assert_array_equal(b[source],np.maximum(-1,np.minimum(1,br[source])))
        np.testing.assert_array_equal(p[source],np.maximum(-1,np.minimum(1,raw[source])))
        assert nb[name].shape==nbr[name].shape==(3,n,4,4)
        assert npred[name].shape==nraw[name].shape==(n,3,n-1,4,4)
        for clipped,unclipped in ((nb[name],nbr[name]),(npred[name],nraw[name])):
            assert np.isfinite(clipped).all() and np.isfinite(unclipped).all()
            np.testing.assert_array_equal(clipped,np.maximum(-1,np.minimum(1,unclipped)))
        old.same({k:v for k,v in record.items() if k not in ('folds','deletions')},
            dict(observer=name,blocks=ids.tolist(),alphas=list(ALPHAS),target='future_mean',model_class=CLASS,
                full_training_blocks=n-1,deletion_training_blocks=n-2,
                restriction='zero raw half-difference slope in every public group',
                preprocessing='original nineteen-feature training-only group means and residual scales',
                reference_fits_recomputed=False,inner_selection=False))
        assert len(record['folds'])==len(record['deletions'])==n
        for d in [None]+list(range(n)):
            indices=list(range(n)) if d is None else [v for v in range(n) if v!=d]
            if d is None:folds=record['folds'];ref_folds=bfits[source]['folds']
            else:
                deletion=record['deletions'][d];ref_deletion=rfits[source]['deletions'][d]
                assert set(deletion)=={'deleted_block','remaining_blocks','folds'}
                assert deletion['deleted_block']==ref_deletion['deleted_block']==int(ids[d])
                assert deletion['remaining_blocks']==ref_deletion['remaining_blocks']==ids[indices].tolist()
                folds=deletion['folds'];ref_folds=ref_deletion['folds']
            assert len(folds)==len(ref_folds)==len(indices)
            for j,v in enumerate(indices):
                fold=folds[j];ref_fold=ref_folds[j];keep=[i for i in range(n) if i!=v and i!=d]
                assert set(fold)=={'validation_block','training_blocks','models','geometry'}
                assert fold['validation_block']==ref_fold['validation_block']==int(ids[v])
                assert fold['training_blocks']==ref_fold['training_blocks']==ids[keep].tolist()
                train=np.concatenate([np.arange(i*16,i*16+16) for i in keep]);test=np.arange(v*16,v*16+16)
                pred,unclipped,models=svd_path(X[train],Y[train],g[train],X[test],g[test])
                got,gotraw=(nb[name][:,v],nbr[name][:,v]) if d is None else (npred[name][d,:,j],nraw[name][d,:,j])
                refraw=br[source][:,v] if d is None else raw[source][d,:,j]
                np.testing.assert_allclose(got,pred.reshape(3,4,4),atol=2e-10,rtol=0)
                np.testing.assert_allclose(gotraw,unclipped.reshape(3,4,4),atol=2e-10,rtol=0)
                assert len(fold['models'])==len(fold['geometry'])==3
                references=ref_fold['models'][5] if d is None else ref_fold['models']
                for a,expected in enumerate(models):
                    actual=fold['models'][a];old.same(actual,expected)
                    assert references[a]['alpha']==ALPHAS[a] and references[a]['model_class']==old.group.CLASS
                    geo=geometry(references[a],actual,X[train],Y[train],g[train],X[test],g[test],refraw[a].ravel())
                    old.same(fold['geometry'][a],geo);counts+=1
                    max_prediction=max(max_prediction,float(np.max(abs(gotraw[a]-unclipped[a].reshape(4,4)))))
                    max_difference=max(max_difference,geo['max_abs_raw_difference_slope'])
                    max_geometry=max(max_geometry,geo['max_abs_reexpression'],geo['penalty_identity_residual'])
                    min_increase=min(min_increase,geo['objective_increase'])
    return dict(passes=True,new_fits=counts,new_predictions=16*counts,independent_group_svd=True,
        untouched_model_geometry_checks=counts,max_abs_svd_prediction_residual=max_prediction,
        max_abs_raw_difference_slope=max_difference,max_abs_geometry_residual=max_geometry,
        min_training_objective_increase=min_increase,reference_fits_recomputed=False,both_exclusions_checked=True)


def loss_panel(p,data,a):
    y=data['labels'];f=data['futures'];mu=np.sum(f,axis=-1)/4;loss={};models={}
    for name in OBSERVERS:
        q=p[name][a];e=q[...,None]-f
        loss[name]=(np.square(q-y),np.square(e),np.square(q-mu))
        np.testing.assert_allclose(np.sum(e*e,axis=-1)/4,loss[name][2]+np.sum((f-mu[...,None])**2,axis=-1)/4,atol=1e-14,rtol=0)
        models[name]=dict(original=old.error_stats(q-y),individual_futures=old.error_stats(e),
            mean_target=old.error_stats(q-mu),by_repeat=[old.error_stats(q-f[...,r]) for r in range(4)])
    for root in ('separate','mean','tied'):
        u,v=(loss[root+':'+k] for k in ('sham_plus','sham_minus'))
        loss[root+':mean_sham_loss']=tuple(.5*a+.5*b for a,b in zip(u,v))
    return loss,models


def panel(p,raw,data,a):
    loss,models=loss_panel(p,data,a)
    for k in OBSERVERS:models[k]['clipped_cases']=int(np.count_nonzero(abs(raw[k][a])>1))
    return dict(blocks=data['block_ids'].tolist(),models=models,
        comparisons=[dict(candidate=c,reference=r,**old.comparison(loss[c],loss[r])) for c,r in specifications()])


def metadata(n):
    return dict(schema='d160_difference_ablation_development_v1',blocks=n,cases=16*n,observers=list(OBSERVERS),
        new_observers=list(NEW),alphas=list(ALPHAS),groups=['A_ordinary','A_aligned','B_ordinary','B_aligned'],
        target='future_mean',new_fits=15*n*n,new_predictions=240*n*n,reference_forecasts_reused=576*n*n,
        untouched_model_geometry_checks=15*n*n,full_panels=1,deletion_panels=n,observer_orientations=99,
        observer_comparison_records=99*(2*n+1),training_effect_records=18*n,
        reference_observer_comparison_records=165*(2*n+1),reference_training_effect_records=42*n,
        free_coefficients=52,reference_coefficients=76,all_cases_retained=True,all_settings_retained=True,
        all_deletions_retained=True,all_repeats_retained=True,reference_fits_recomputed=False,
        penalty_geometry_matched=True,new_dynamics=0,new_diagnostic_cycles=0,new_founders=0,
        inner_selection=False,model_selected_for_deployment=False,confidence_intervals=False,
        mean_sham_is_loss_not_ensemble=True,posthoc=True,prospective_evidence=False,automatic_successor=False)


def check_summary(s,nb,nbr,npred,nraw,data,b,br,p,raw):
    n=len(data['block_ids']);old.labels(data)
    old.same({k:v for k,v in s.items() if k not in ('scores','within_future_variance')},metadata(n))
    assert set(s['scores'])==set(map(str,ALPHAS))
    full={**b,**nb};fullraw={**br,**nbr};refit={**p,**npred};refitraw={**raw,**nraw}
    for a,alpha in enumerate(ALPHAS):
        deletions=[]
        for d in range(n):
            keep=[j for j in range(n) if j!=d]
            reduced={k:data[k][keep] for k in ('start','endpoint','targeted','labels','futures','block_ids')}
            q={k:refit[k][d] for k in OBSERVERS};qr={k:refitraw[k][d] for k in OBSERVERS}
            reference_pred={k:full[k][:,keep] for k in OBSERVERS};reference_raw={k:fullraw[k][:,keep] for k in OBSERVERS}
            newloss,_=loss_panel(q,reduced,a);oldloss,_=loss_panel(reference_pred,reduced,a)
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),refitted=panel(q,qr,reduced,a),
                score_only=panel(reference_pred,reference_raw,reduced,a),
                training_effect=[dict(observer=k,**old.comparison(newloss[k],oldloss[k])) for k in NEW_LOSS]))
        old.same(s['scores'][str(alpha)],dict(full=panel(full,fullraw,data,a),deletions=deletions))
    expected=float(np.sum((data['futures']-np.sum(data['futures'],axis=-1,keepdims=True)/4)**2)/data['futures'].size)
    old.same(s['within_future_variance'],expected)
    return dict(passes=True,observer_comparison_records=99*(1+2*n),training_effect_records=18*n,
        absolute_model_score_records=51*(1+2*n),all_cases_and_repeats_retained=True)


def source_bridge(summary,source,data,b,br,p,raw):
    proof=reference.check_summary(source,p,raw,b,br,data)
    count=0
    for alpha in map(str,ALPHAS):
        s=summary['scores'][alpha];ref=source['scores'][alpha]
        panels=[(s['full'],ref['full'])]
        for x,y in zip(s['deletions'],ref['deletions']):
            assert x['deleted_block']==y['deleted_block'];panels.extend(((x['refitted'],y['refitted']),(x['score_only'],y['score_only'])))
        for x,y in panels:
            assert x['blocks']==y['blocks']
            for name in old.OBSERVERS:old.same(x['models'][name],y['models'][name]);count+=1
    return dict(passes=True,reference_check=proof,absolute_source_score_records=count,source_primary_unchanged=True)


def check_errors(arrays,nb,npred,b,p,data):
    n=len(data['block_ids']);keys=set()
    yy=np.stack([data['labels'][[i for i in range(n) if i!=d]] for d in range(n)])[:,None]
    ff=np.stack([data['futures'][[i for i in range(n) if i!=d]] for d in range(n)])[:,None]
    for prefix,values,refs,y,f in (('full',nb,b,data['labels'],data['futures']),('deletion',npred,p,yy,ff)):
        for name in NEW:
            cases=(('original',values[name]-y),('futures',values[name][...,None]-f),
                ('mean',values[name]-np.sum(f,axis=-1)/4),
                ('change_from_separate',values[name]-refs['separate:'+name.split(':')[1]]))
            for outcome,e in cases:
                for suffix,v in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
                    key=prefix+'__'+name+'__'+outcome+'__'+suffix;keys.add(key)
                    assert arrays[key].shape==v.shape
                    np.testing.assert_allclose(arrays[key],v,atol=1e-14,rtol=0)
    assert set(arrays)==keys
    return dict(passes=True,case_arrays=len(keys),all_cases_retained=True)
