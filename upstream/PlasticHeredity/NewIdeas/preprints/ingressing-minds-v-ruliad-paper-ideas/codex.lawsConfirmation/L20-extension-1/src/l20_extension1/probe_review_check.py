"""Independent FFT extraction and scalar error/association accounting for D151."""
import math
import numpy as np
from . import placement_review_check as fields

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
BRANCHES=('U0','U1','C1','attenuate','sham_plus','sham_minus')
GROUPS=('A ordinary','A aligned','B ordinary','B aligned')
PAIRS=((3,1),(3,0),(3,2),(3,4),(3,5),(3,None),(4,1),(5,1),(1,0),(2,1))
STAGES=['selected_input']+['read_R_'+str(t) for t in (0,1,100,101,300)]+['write_R_'+str(t) for t in (0,1,300,1000)]+[
 'outgoing_record','routed_outgoing']+['fresh_R_'+str(t) for t in (0,1,100,300)]+['fresh_V_'+str(t) for t in (0,1,100,300)]


def reconstruct(raw,original):
    value=np.zeros((4,4,6,20,15));pref=np.zeros((4,4,6,4))
    for bi in range(6):
        source,j=(original,bi) if bi<3 else (raw,bi-3)
        for gi in range(4):
            for life in range(4):
                packet=lambda key:np.frombuffer(source[key][life,gi,j].tobytes(),'<f8').reshape(16,16)
                read=source['read_states'][life,gi,j];write=source['write_states'][life,gi,j]
                final=source['terminal_states'][life,gi,j]
                np.testing.assert_array_equal(write[0,:3],read[-1])
                if bi>=3:
                    np.testing.assert_array_equal(read[0],original['read_states'][life,gi,1,0])
                    np.testing.assert_array_equal(final[0],original['terminal_states'][life,gi,1,0])
                stages=[packet('routed' if bi<3 else 'input')]+list(read[:,2])+list(write[:,2])+[
                    packet('outgoing'),packet('terminal_packet')]+list(final[:,2])+list(final[:,0])
                value[life,gi,bi]=fields.measure(np.stack(stages),gi//2)
                codes=fields.states(final[:,0],gi//2)
                pref[life,gi,bi]=np.sum((codes==1).astype(int)-(codes==2).astype(int),axis=-1)/256
                endpoint=source['diagnostic_features'][life,gi,j]
                assert pref[life,gi,bi,-1]==endpoint[4]
                for a,b,c in ((10,6,0),(10,8,1),(11,5,3),(19,1,5)):
                    assert abs(value[life,gi,bi,a,b]-endpoint[c])<1e-11
    return dict(fields=value,preference=pref)


def check_block(actual,raw,original):
    expected=reconstruct(raw,original);assert set(actual)==set(expected)
    for k,v in expected.items():
        assert actual[k].shape==v.shape and actual[k].dtype==v.dtype
        np.testing.assert_allclose(actual[k],v,atol=1e-11,rtol=0)
    return dict(passes=True,cases=16,branches=6,field_checkpoints=1920,new_dynamics=0)


def moments(e):
    values=np.asarray(e).ravel().tolist();n=len(values);mu=math.fsum(values)/n
    mse=math.fsum(v*v for v in values)/n;variance=math.fsum((v-mu)**2 for v in values)/n
    assert abs(mse-mu*mu-variance)<1e-13
    return dict(mse=mse,mae_points=100*math.fsum(abs(v) for v in values)/n,
        rmse_points=100*math.sqrt(mse),bias_points=100*mu,centered_error_variance=variance)


def pearson(x,y):
    a=np.asarray(x).ravel().tolist();b=np.asarray(y).ravel().tolist();assert len(a)==len(b)>1
    if min(a)==max(a) or min(b)==max(b):return None
    ma=math.fsum(a)/len(a);mb=math.fsum(b)/len(b)
    u=[v-ma for v in a];v=[w-mb for w in b]
    r=math.fsum(x*y for x,y in zip(u,v))/math.sqrt(math.fsum(x*x for x in u)*math.fsum(y*y for y in v))
    return max(-1.,min(1.,r))


def describe(x):
    return dict(mean=float(x.sum()/x.size),block_means=(x.sum(axis=1)/4).tolist(),
        positive=int(np.count_nonzero(x>0)),negative=int(np.count_nonzero(x<0)),zero=int(np.count_nonzero(x==0)))


def association(x,y):
    return dict(cases=x.size,blocks=len(x),case_r=pearson(x,y),block_mean_r=pearson(x.sum(1)/4,y.sum(1)/4))


def reconstruct_terms(p,y):
    errors=p-y[...,None];result=np.empty(y.shape+(10,3))
    for bi in range(len(y)):
        for life in range(4):
            for group in range(4):
                for ci,(left,right) in enumerate(PAIRS):
                    refs=(4,5) if right is None else (right,);parts=[]
                    for ref in refs:
                        delta=p[bi,life,group,left]-p[bi,life,group,ref]
                        cross=2*delta*errors[bi,life,group,ref]
                        net=errors[bi,life,group,left]**2-errors[bi,life,group,ref]**2
                        assert abs(delta**2+cross-net)<1e-13
                        parts.append((delta**2,cross,net))
                    result[bi,life,group,ci]=np.sum(parts,axis=0)/len(parts)
    return errors,result


def check_summary(actual,panel,arch,fixture=False):
    p,y,f,q=panel['predictions'],panel['labels'],panel['fields'],panel['preference']
    assert p.shape==(32,4,4,6) and y.shape==(32,4,4) and f.shape==(32,4,4,6,20,15) and q.shape==(32,4,4,6,4)
    expected_arch=[dict(model=k,folds=32,dimensions=7 if i==0 else 19,group_intercepts=4,shared_slope_vectors_per_fold=1) for i,k in enumerate(MODELS)]
    fields.same(arch,expected_arch);e,t=reconstruct_terms(p,y)
    np.testing.assert_array_equal(panel['error'],e)
    np.testing.assert_array_equal(panel['absolute_error'],np.abs(e))
    np.testing.assert_array_equal(panel['squared_error'],np.square(e))
    np.testing.assert_allclose(panel['block_field_means'],np.sum(f,axis=1)/4,atol=1e-13,rtol=0)
    np.testing.assert_array_equal(panel['block_preference_means'],np.sum(q,axis=1)/4)
    np.testing.assert_allclose(panel['comparison_terms'],t,atol=1e-13,rtol=0)
    sections={}
    for cohort,a,b in (('all',0,32),('d135',0,8),('d140',8,16),('former_test',16,32)):
        rows=[];pairs=[]
        for mi,name in enumerate(MODELS):
            v=e[a:b,...,mi];total=math.fsum(float(z*z) for z in v.ravel());groups=[]
            for gi,g in enumerate(GROUPS):
                z=v[:,:,gi];item=moments(z)
                item.update(group=g,block_mse=[moments(row)['mse'] for row in z],
                    squared_error_share_percent=100*math.fsum(float(w*w) for w in z.ravel())/total if total else None)
                groups.append(item)
            rows.append(dict(model=name,**moments(v),groups=groups))
        for ci,(left,right) in enumerate(PAIRS):
            term=t[a:b,...,ci,:]
            pairs.append(dict(candidate=MODELS[left],reference=MODELS[right] if right is not None else 'mean_sham_loss',
                terms=(term.sum(axis=(0,1,2))/((b-a)*16)).tolist(),group_terms=(term.sum(axis=(0,1))/((b-a)*4)).tolist(),
                block_terms=(term.sum(axis=(1,2))/16).tolist()))
        sections[cohort]=dict(blocks=b-a,cases=(b-a)*16,models=rows,comparisons=pairs)
    trajectories=[];responses=[];links=[];future_links=[]
    for gi,g in enumerate(GROUPS):
        for bi,name in enumerate(BRANCHES):
            trajectories.append(dict(group=g,branch=name,fields=(f[:,:,gi,bi].sum(axis=(0,1))/128).tolist(),
                preference=(q[:,:,gi,bi].sum(axis=(0,1))/128).tolist()))
        for bi in (0,2,3,4,5):
            x=q[:,:,gi,bi,-1]-q[:,:,gi,1,-1]
            responses.append(dict(group=g,branch=BRANCHES[bi],matched_noise=bi!=0,endpoint=describe(x),
                fields=((f[:,:,gi,bi]-f[:,:,gi,1]).sum(axis=(0,1))/128).tolist(),
                preference=((q[:,:,gi,bi]-q[:,:,gi,1]).sum(axis=(0,1))/128).tolist()))
            targets=(('starting_own_best',panel['start'][:,:,gi,0]),('original_outcome',y[:,:,gi]),
                ('passive_signed_error',e[:,:,gi,1]),('passive_squared_error',e[:,:,gi,1]**2),
                ('attenuation_minus_passive_squared_error',e[:,:,gi,3]**2-e[:,:,gi,1]**2))
            for key,target in targets:links.append(dict(group=g,branch=BRANCHES[bi],target=key,**association(x,target)))
            a=panel['futures'][:,:,gi];m=a.sum(-1)/4;variance=np.sum((a-m[...,None])**2,axis=-1)/3
            for key,target in (('future_mean',m),('future_sample_variance',variance)):
                future_links.append(dict(group=g,branch=BRANCHES[bi],target=key,**association(x[16:],target)))
    future=[];a=panel['futures'];m=a.sum(-1)/4;spread=np.sum((a-m[...,None])**2,axis=-1)/4
    for mi,name in enumerate(MODELS):
        individual=(p[16:,...,mi,None]-a)**2;mean_loss=(p[16:,...,mi]-m)**2
        np.testing.assert_allclose(individual.sum(-1)/4,mean_loss+spread,atol=1e-13,rtol=0)
        future.append(dict(model=name,individual_mse=float(individual.sum()/1024),mean_target_mse=float(mean_loss.sum()/256),
            within_future_population_variance=float(spread.sum()/256),group_individual_mse=(individual.sum(axis=(0,1,3))/256).tolist(),
            group_mean_mse=(mean_loss.sum(axis=(0,1))/64).tolist(),group_spread=(spread.sum(axis=(0,1))/64).tolist()))
    expected=dict(schema='d151_saved_case_review_v1',posthoc=True,fixture=fixture,new_dynamics=0,new_models=0,
        prospective_evidence=False,all_cases_retained=True,blocks=32,cases=512,architecture=expected_arch,
        model_order=list(MODELS),branch_order=list(BRANCHES),stage_order=STAGES,field_order=list(fields.FIELDS),
        error_terms=['prediction_change_squared','twice_change_times_reference_error','candidate_minus_reference_loss'],
        sections=sections,trajectories=trajectories,responses=responses,associations=links,
        repeated_future_associations=future_links,repeated_future_accounting=future,
        no_observer_budget_claim_for_multibranch_review=True,repair_durability_measured=False)
    fields.same(actual,expected)
    return dict(passes=True,cases=512,blocks=32,groups=4,models=6,branches=6,comparisons=10,
        associations=100,secondary_associations=40,new_dynamics=0,new_models=0,prospective_evidence=False)


def source_scores(summary,original):
    """Bridge every model/error contrast to the unchanged D151 score panel."""
    rows=summary['sections']['all']['models']
    for row in rows:
        old=original['models'][row['model']]
        for key in ('mse','mae_points','rmse_points'):fields.same(row[key],old[key])
        fields.same([g['mse'] for g in row['groups']],old['group_mse'])
    for row,old in zip(summary['sections']['all']['comparisons'],original['comparisons']):
        assert row['candidate']==old['candidate'] and row['reference']==old['reference']
        fields.same(row['terms'][-1],-old['mse_reduction'])
    future={r['model']:r for r in summary['repeated_future_accounting']}
    for name,row in future.items():
        old=original['repeated_future_models'][name]
        fields.same(row['individual_mse'],old['individual_future_mse'])
        fields.same(row['mean_target_mse'],old['mean_target_mse'])
    for left,right in PAIRS:
        a=future[MODELS[left]];refs=[future[MODELS[j]] for j in ((4,5) if right is None else (right,))]
        individual=a['individual_mse']-sum(v['individual_mse'] for v in refs)/len(refs)
        mean=a['mean_target_mse']-sum(v['mean_target_mse'] for v in refs)/len(refs)
        fields.same(individual,mean)
    return dict(passes=True,models=6,comparisons=10,original_primary_unchanged=True)
