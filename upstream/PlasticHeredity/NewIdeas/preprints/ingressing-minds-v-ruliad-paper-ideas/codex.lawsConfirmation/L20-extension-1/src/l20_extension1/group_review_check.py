"""Independent forward, score and selection arithmetic for D152 saved fits."""
import numpy as np
from .recovery_check import same

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
ARCH=('shared','group_sensitive');ALPHAS=(.001,.01,.1,1.,10.,100.)
PAIRS=(('passive','starting'),('shuffle','starting'),('shuffle','passive'),
    ('attenuate','starting'),('attenuate','passive'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('sham_plus','starting'),
    ('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','starting'),
    ('sham_minus','passive'),('sham_minus','shuffle'),('sham_minus','sham_plus'),
    ('attenuate','mean_sham_loss'),('mean_sham_loss','starting'),('mean_sham_loss','passive'))
COHORTS=(('d135',0,8),('d140',8,16),('former_test',16,32))


def specs():
    return [dict(candidate_arch=a,candidate=c,reference_arch=a,reference=r) for a in ARCH for c,r in PAIRS]+[
        dict(candidate_arch='group_sensitive',candidate=k,reference_arch='shared',reference=k) for k in MODELS]


def index(mean):return sorted([j for j,v in enumerate(mean) if v<=min(mean)+1e-12])[-1]


def forward(m,x,architecture):
    rows=x.reshape(16,-1);g=np.tile(np.arange(4),4);d=rows.shape[-1]
    mu=np.asarray(m['means']);scale=np.asarray(m['scale']);offset=np.asarray(m['offsets']);z=(rows-mu[g])/scale
    if architecture=='shared':contribution=z*np.asarray(m['beta'])
    else:
        beta=np.asarray(m['coefficients']);design=np.hstack([z]+[
            z*np.array(sign)[g,None]/2 for sign in ((-1,-1,1,1),(-1,1,-1,1),(1,-1,-1,1))])
        contribution=(design*beta.ravel()).reshape(16,4,d).sum(axis=1)
    pieces=np.zeros((16,5));pieces[:,0]=offset[g]
    for column,(l,r) in enumerate(((0,7),(7,13),(13,19)),1):pieces[:,column]=np.sum(contribution[:,l:r],axis=1)
    raw=np.sum(pieces,axis=1);p=np.maximum(-1,np.minimum(1,raw));pieces[:,-1]=p-raw
    return p.reshape(4,4),pieces.reshape(4,4,5)


def model_predictions(panel,s,which):
    a=ARCH.index(s[which+'_arch']);name=s[which];indexes=[4,5] if name=='mean_sham_loss' else [MODELS.index(name)]
    return panel['predictions'][a,indexes]


def direct_terms(c,r,y):
    a=np.zeros(y.shape+(3,))
    for candidate in c:
        for reference in r:
            delta=np.broadcast_to(candidate-reference,y.shape)
            a[...,0]+=np.square(reference-y)-np.square(candidate-y)
            a[...,1]+=np.square(delta);a[...,2]+=2*(reference-y)*delta
    return a/(len(c)*len(r))


def check_panel(panel,data,predictions,fits):
    expected={'block_ids','labels','futures','predictions','parts','selected','inner_losses','inner_means',
        'drop_selected','selection_gaps','signed','absolute','squared','contrast_terms','future_terms'}
    assert set(panel)==expected and set(predictions)==set(fits)==set(ARCH)
    shapes=dict(block_ids=(32,),labels=(32,4,4),futures=(16,4,4,4),predictions=(2,6,32,4,4),
        parts=(2,6,32,4,4,5),selected=(2,6,32),inner_losses=(2,6,32,31,6),inner_means=(2,6,32,6),
        drop_selected=(2,6,32,31),selection_gaps=(2,6,32,2),signed=(2,6,32,4,4),
        absolute=(2,6,32,4,4),squared=(2,6,32,4,4),contrast_terms=(42,32,4,4,3),future_terms=(42,16,4,4,4,3))
    for k,shape in shapes.items():
        assert panel[k].shape==shape and np.isfinite(panel[k]).all()
        assert panel[k].dtype==(np.int64 if k in ('block_ids','selected','drop_selected') else np.float64)
    for k in ('block_ids','labels','futures'):np.testing.assert_array_equal(panel[k],data[k])
    ids=panel['block_ids'];a,e,t=data['start'],data['endpoint'],data['targeted']
    x=[a]+[np.concatenate([a,e[...,0,:],second],axis=-1) for second in (e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])]
    for ai,arch in enumerate(ARCH):
        assert set(predictions[arch])==set(fits[arch])==set(MODELS)
        for ki,k in enumerate(MODELS):
            np.testing.assert_array_equal(panel['predictions'][ai,ki],predictions[arch][k]);record=fits[arch][k]
            assert record['blocks']==ids.tolist() and record['alphas']==list(ALPHAS) and len(record['folds'])==32
            for b,fold in enumerate(record['folds']):
                others=[int(ids[j]) for j in range(32) if j!=b]
                assert fold['validation_block']==int(ids[b]) and fold['training_blocks']==fold['inner_validation_blocks']==others
                curve=np.array(fold['inner_block_mse']);assert curve.shape==(31,6) and (curve>=0).all()
                np.testing.assert_array_equal(panel['inner_losses'][ai,ki,b],curve)
                mean=np.sum(curve,axis=0)/31;np.testing.assert_allclose(mean,fold['inner_mean_mse'],atol=1e-14,rtol=0)
                chosen=index(mean);assert panel['selected'][ai,ki,b]==fold['selected_index']==chosen
                assert fold['model']['alpha']==ALPHAS[chosen]
                np.testing.assert_allclose(panel['inner_means'][ai,ki,b],mean,atol=1e-14,rtol=0)
                for row in range(31):
                    reduced=np.sum(curve[[j for j in range(31) if j!=row]],axis=0)/30
                    assert panel['drop_selected'][ai,ki,b,row]==index(reduced)
                gap=[mean[chosen]-min(mean),min(mean[j] for j in range(6) if j!=chosen)-mean[chosen]]
                np.testing.assert_allclose(panel['selection_gaps'][ai,ki,b],gap,atol=1e-14,rtol=0)
                p,parts=forward(fold['model'],x[ki][b],arch)
                np.testing.assert_allclose(p,panel['predictions'][ai,ki,b],atol=2e-10,rtol=0)
                np.testing.assert_allclose(parts,panel['parts'][ai,ki,b],atol=2e-10,rtol=0)
    errors=panel['predictions']-panel['labels']
    for k,value in (('signed',errors),('absolute',np.maximum(errors,-errors)),('squared',np.square(errors))):
        np.testing.assert_array_equal(panel[k],value)
    for i,s in enumerate(specs()):
        c,r=(model_predictions(panel,s,which) for which in ('candidate','reference'))
        ordinary=direct_terms(c,r,panel['labels']);future=direct_terms(c[:,16:,...,None],r[:,16:,...,None],panel['futures'])
        np.testing.assert_allclose(panel['contrast_terms'][i],ordinary,atol=1e-14,rtol=0)
        np.testing.assert_allclose(panel['future_terms'][i],future,atol=1e-14,rtol=0)
        for value in (ordinary,future):np.testing.assert_allclose(value[...,0],-value[...,1]-value[...,2],atol=1e-14,rtol=0)
        mean=direct_terms(c[:,16:],r[:,16:],np.sum(panel['futures'],axis=-1)/4)
        np.testing.assert_allclose(np.sum(future,axis=-2)/4,mean,atol=1e-14,rtol=0)
    return dict(passes=True,saved_models=12,outer_predictions=6144,contrasts=42,inner_score_rows=11904,
        new_fits=0,new_predictions=0,new_dynamics=0)


def error_stats(p,y):
    e=p-y;count=e.size;mean=float(np.sum(e)/count);mse=float(np.sum(np.square(e))/count)
    return dict(outcomes=count,mse=mse,mae_points=float(np.sum(np.abs(e))*100/count),rmse_points=float(np.sqrt(mse)*100),
        bias_points=mean*100,error_variance=float(np.sum(np.square(e-mean))/count))


def basic(terms,c,r,ids):
    n=len(ids)
    if not n:return dict(blocks=0,cases=0,block_ids=[],mse_reduction=None,candidate_mse=None,reference_mse=None,
        relative_reduction_percent=None,change_cost=None,error_correction=None,block_reductions=[],positive_blocks=0,
        negative_blocks=0,zero_blocks=0,group_reductions=[],group_contributions=[])
    count=c.size;gain=float(np.sum(terms[...,0])/count);ref=float(np.sum(r)/count)
    blocks=np.sum(terms[...,0],axis=(1,2))/16;groups=np.sum(terms[...,0],axis=(0,1))/(n*4)
    return dict(blocks=n,cases=count,block_ids=ids.tolist(),mse_reduction=gain,candidate_mse=float(np.sum(c)/count),reference_mse=ref,
        relative_reduction_percent=100*gain/ref if ref else None,change_cost=float(np.sum(terms[...,1])/count),
        error_correction=float(-np.sum(terms[...,2])/count),block_reductions=blocks.tolist(),
        positive_blocks=int(np.count_nonzero(blocks>0)),negative_blocks=int(np.count_nonzero(blocks<0)),
        zero_blocks=int(np.count_nonzero(blocks==0)),group_reductions=groups.tolist(),group_contributions=(groups/4).tolist())


def detailed(terms,c,r,ids):
    result=basic(terms,c,r,ids);n=len(ids);g=terms[...,0];block=np.sum(g,axis=(1,2))/16
    deleted=np.array([sum(block[k] for k in range(n) if k!=j)/(n-1) for j in range(n)])
    result.update(block_contributions=(block/n).tolist(),block_order_best_first=[int(ids[j]) for j in sorted(range(n),key=lambda j:-block[j])],
        case_order_best_first=sorted(range(g.size),key=lambda j:-g.flat[j]),case_gains=int(np.count_nonzero(g>0)),
        case_losses=int(np.count_nonzero(g<0)),case_ties=int(np.count_nonzero(g==0)),leave_one_score_block_out=deleted.tolist(),
        leave_one_min=float(min(deleted)),leave_one_max=float(max(deleted)),leave_one_positive=int(np.count_nonzero(deleted>0)),
        leave_one_negative=int(np.count_nonzero(deleted<0)),leave_one_zero=int(np.count_nonzero(deleted==0)))
    return result


def relation(panel,s,terms,c,r,ids,future=False):
    if s['candidate_arch']!=s['reference_arch'] or s['candidate']=='mean_sham_loss' or s['reference']=='mean_sham_loss':return None
    ai=ARCH.index(s['candidate_arch']);ci=MODELS.index(s['candidate']);ri=MODELS.index(s['reference']);start=16 if future else 0
    a,b=panel['selected'][ai,ci,start:],panel['selected'][ai,ri,start:];partitions={}
    for name,mask in (('same',a==b),('different',a!=b)):
        value=basic(terms[mask],c[mask],r[mask],ids[mask]);value['contribution_to_full_mse_reduction']=float(np.sum(terms[mask,...,0])/terms[...,0].size)
        partitions[name]=value
    means=panel['inner_means'][ai]
    return dict(partitions=partitions,candidate_indices=a.tolist(),reference_indices=b.tolist(),
        candidate_inner_cost_at_reference_index=[float(means[ci,start+i,b[i]]-means[ci,start+i,a[i]]) for i in range(len(ids))],
        reference_inner_cost_at_candidate_index=[float(means[ri,start+i,a[i]]-means[ri,start+i,b[i]]) for i in range(len(ids))],
        causal_isolation=False,new_outer_forecasts=False)


def check_summary(summary,panel):
    ids=panel['block_ids'];models={};selections={}
    for ai,a in enumerate(ARCH):
        models[a]={};selections[a]={}
        for ki,k in enumerate(MODELS):
            p=panel['predictions'][ai,ki];y=panel['labels'];f=panel['futures'];parts=panel['parts'][ai,ki]
            models[a][k]=dict(original=error_stats(p,y),groups=[error_stats(p[:,:,g],y[:,:,g]) for g in range(4)],
                blocks=[error_stats(p[b],y[b]) for b in range(32)],
                cohorts={name:error_stats(p[l:r],y[l:r]) for name,l,r in COHORTS},
                individual_futures=error_stats(p[16:,...,None],f),future_mean=error_stats(p[16:],np.sum(f,axis=-1)/4),
                future_groups=[error_stats(p[16:,:,g,None],f[:,:,g,:]) for g in range(4)],
                future_blocks=[error_stats(p[b+16,...,None],f[b]) for b in range(16)],
                future_variance=float(np.sum((f-np.sum(f,axis=-1,keepdims=True)/4)**2)/1024),
                parts_means=(np.sum(parts,axis=(0,1,2))/512).tolist(),parts_group_means=(np.sum(parts,axis=(0,1))/128).tolist(),
                parts_block_means=(np.sum(parts,axis=(1,2))/16).tolist())
            values=models[a][k]
            np.testing.assert_allclose(values['original']['mse'],values['original']['error_variance']+(values['original']['bias_points']/100)**2,atol=1e-14,rtol=0)
            np.testing.assert_allclose(values['individual_futures']['mse'],values['future_mean']['mse']+values['future_variance'],atol=1e-14,rtol=0)
            selected=panel['selected'][ai,ki];drop=panel['drop_selected'][ai,ki]
            selections[a][k]=dict(selected_indices=selected.tolist(),alpha_counts={str(v):int(np.count_nonzero(selected==j)) for j,v in enumerate(ALPHAS)},
                cohorts={name:{str(v):int(np.count_nonzero(selected[l:r]==j)) for j,v in enumerate(ALPHAS)} for name,l,r in COHORTS},
                score_row_deletion_changed_counts=[sum(int(d!=s) for d in row) for s,row in zip(selected,drop)],
                score_row_deletion_alpha_counts=[int(np.count_nonzero(drop==j)) for j in range(6)],
                selected_minus_minimum=panel['selection_gaps'][ai,ki,:,0].tolist(),runner_up_minus_selected=panel['selection_gaps'][ai,ki,:,1].tolist(),
                complete_founder_retraining=False,new_outer_predictions=False)
    comparisons=[]
    for i,s in enumerate(specs()):
        cp,rp=(model_predictions(panel,s,which) for which in ('candidate','reference'))
        c=np.sum((cp-panel['labels'])**2,axis=0)/len(cp);r=np.sum((rp-panel['labels'])**2,axis=0)/len(rp)
        fc=np.sum((cp[:,16:,...,None]-panel['futures'])**2,axis=(0,-1))/(4*len(cp))
        fr=np.sum((rp[:,16:,...,None]-panel['futures'])**2,axis=(0,-1))/(4*len(rp))
        terms=panel['contrast_terms'][i];ft=np.sum(panel['future_terms'][i],axis=-2)/4
        comparisons.append(dict(**s,original=detailed(terms,c,r,ids),secondary=detailed(ft,fc,fr,ids[16:]),
            cohorts={name:basic(terms[l:h],c[l:h],r[l:h],ids[l:h]) for name,l,h in COHORTS},
            alpha_relation=relation(panel,s,terms,c,r,ids),future_alpha_relation=relation(panel,s,ft,fc,fr,ids[16:],True)))
    expected=dict(schema='d152_saved_fit_review_v1',posthoc=True,prospective_evidence=False,all_cases_retained=True,
        blocks=32,cases=512,architectures=list(ARCH),observers=list(MODELS),groups=['A_ordinary','A_aligned','B_ordinary','B_aligned'],
        parts=['intercept','starting','U0','second','clipping'],models=models,selection=selections,comparisons=comparisons,
        new_fits=0,new_predictions=0,new_dynamics=0,repeated_future_blocks=16,repeated_outcomes=1024,source_primary_unchanged=True,
        confidence_intervals=False,causal_regularization_claim=False,automatic_successor=False,
        deleted_score_rows_are_not_retrained_folds=True,mean_sham_is_loss_not_ensemble=True)
    same(summary,expected)
    return dict(passes=True,models=12,comparisons=42,blocks=32,cases=512,future_outcomes=1024,new_fits=0,new_dynamics=0)


def source_bridge(summary,source):
    for a in ARCH:
        for k in MODELS:
            actual=summary['models'][a][k];prior=source['architectures'][a]['models'][k]
            for name in ('mse','mae_points','rmse_points'):same(actual['original'][name],prior[name])
            same([v['mse'] for v in actual['groups']],prior['group_mse'])
            same([v['mse'] for v in actual['blocks']],prior['block_mse'])
            for cohort in ('d135','d140','former_test'):
                for name in ('mse','mae_points','rmse_points'):same(actual['cohorts'][cohort][name],prior['cohorts'][cohort][name])
            repeat=source['architectures'][a]['repeated_future_models'][k]
            same(actual['individual_futures']['mse'],repeat['individual_future_mse'])
            same(actual['individual_futures']['mae_points'],repeat['individual_future_mae_points'])
            same(actual['future_mean']['mse'],repeat['mean_target_mse'])
            same([v['mse'] for v in actual['future_groups']],repeat['individual_future_group_mse'])
            same([v['mse'] for v in actual['future_blocks']],repeat['individual_future_block_mse'])
            assert summary['selection'][a][k]['alpha_counts']==prior['alpha_counts']
        for comparison in source['architectures'][a]['comparisons']:
            row=next(r for r in summary['comparisons'] if r['candidate_arch']==r['reference_arch']==a and
                r['candidate']==comparison['candidate'] and r['reference']==comparison['reference'])
            same(row['original']['mse_reduction'],comparison['mse_reduction'])
            same(row['original']['block_reductions'],comparison['block_differences'])
    for comparison in source['architecture_comparisons']:
        row=next(r for r in summary['comparisons'] if r['candidate_arch']=='group_sensitive' and r['reference_arch']=='shared'
            and r['candidate']==r['reference']==comparison['model'])
        same(row['original']['mse_reduction'],comparison['original']['mse_reduction'])
        same(row['secondary']['mse_reduction'],comparison['individual_futures']['mse_reduction'])
    return dict(passes=True,source_models=12,source_observer_contrasts=20,source_architecture_contrasts=6)
