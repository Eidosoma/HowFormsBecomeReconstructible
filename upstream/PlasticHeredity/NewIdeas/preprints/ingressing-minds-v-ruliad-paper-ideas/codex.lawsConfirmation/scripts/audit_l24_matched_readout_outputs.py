"""D088 independent sphere geometry, anchor/alias and pooled observer checks.

Physical replay and per-snapshot metrics use D086's frozen independent checker.
No calls to the new record builder or production summary are made here.
"""
import numpy as np
from laws_confirmation import l24_descendant_pilot as previous

PAIRS=((2,0),(2,3),(2,4),(2,1),(1,5),(1,6),(1,0))
LABELS=('directed_minus_clean','directed_minus_reversed','directed_minus_shuffled','directed_minus_actual',
        'actual_minus_reversed','actual_minus_shuffled','source_actual_minus_clean')


def close(a,b):
    assert np.shape(a)==np.shape(b) and np.isfinite(a).all() and np.isfinite(b).all()
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def size(x): return float(np.linalg.norm(np.ravel(x))/16)


def check_geometry(original,result):
    b,actual=original['records'][:2];r=size(b);d=size(actual-b)
    assert abs(b.mean())<1e-12 and abs(r-.3)<1e-12 and 0<d<2*r
    assert result['records'].shape==(7,16,16)
    np.testing.assert_array_equal(result['records'][:2],original['records'][:2])
    np.testing.assert_array_equal(result['targets'],original['targets'])
    np.testing.assert_array_equal(result['permutation'],original['permutation'])
    np.testing.assert_array_equal(np.sort(result['permutation']),np.arange(256))
    goal=original['records'][5]-original['records'][4];change=actual-b;perm=original['permutation']
    directions=np.array([goal,goal.reshape(256)[perm].reshape(16,16),change,change.reshape(256)[perm].reshape(16,16)])
    errors=[close(result['directions'],directions)]
    units=[];baseline=b.ravel();baseline_squared=np.dot(baseline,baseline)
    for direction in directions:
        u=direction.ravel()-sum(direction.ravel())/256
        u=u-baseline*(np.dot(u,baseline)/baseline_squared)
        norm=np.linalg.norm(u)/16
        assert norm>1e-12
        u=(u/norm).reshape(16,16);units.append(u)
        close(np.mean(u*b),0.);close(u.mean(),0.);close(size(u),1.)
    units=np.array(units);errors.append(close(result['units'],units))
    # Independent angular form, rather than the production chord expansion.
    angle=2*np.arcsin(d/(2*r));cosine=np.cos(angle);amplitude=r*np.sin(angle)
    move=lambda u:cosine*b+amplitude*u
    expected=np.stack((b,actual,move(units[0]),move(-units[0]),move(units[1]),move(-units[2]),move(units[3])))
    errors.append(close(result['records'],expected))
    errors.append(close(result['geometry_parameters'],[r,d,cosine,amplitude]))
    errors.append(close(result['reconstructed_actual'],move(units[2])))
    errors.append(close(result['reconstructed_actual'],actual))
    stats=[];available=[];direction=(original['targets'][1]-original['targets'][0])/2
    for record in result['records']:
        q=record-b;flat=q.ravel();total=float(np.dot(flat,flat));quarter=q[:,12:].ravel()
        stats.append((size(record),size(q),sum(record.ravel())/256,np.dot(flat,direction.ravel())/256,
            np.dot(quarter,quarter)/total if total>0 else 0.,max(abs(flat))))
        available.append(total>0)
    errors.append(close(result['geometry'],np.array(stats)))
    np.testing.assert_array_equal(result['geometry_energy_available'],available)
    for i in range(7):
        errors.extend((close(size(result['records'][i]),r),close(result['records'][i].mean(),0.)))
        errors.append(close(size(result['records'][i]-b),0. if i==0 else d))
    # Reversal means opposite tangent direction, not negating the full baseline.
    errors.append(close(result['records'][2]+result['records'][3],2*cosine*b))
    errors.append(close(result['reconstructed_actual']+result['records'][5],2*cosine*b))
    return max(errors)


def check_anchors_and_aliases(original,payload):
    raw,old=payload['descendants'],original['descendants']
    np.testing.assert_array_equal(raw[:,:,:,:,:2],old[:,:,:,:,:2])
    close(payload['values'][:,:,:,:2],original['values'][:,:,:,:2])
    np.testing.assert_array_equal(raw[0,0],raw[1,0])
    np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not raw[:,0,2].any() and not raw[1,:,2].any()
    for record in range(7):
        np.testing.assert_array_equal(raw[:,:,:,1,record],old[:,:,:,1,0])
        np.testing.assert_array_equal(raw[:,0,:,0,record],raw[:,0,:,1,0])
        close(payload['values'][:,:,1,record],original['values'][:,:,1,0])
    scores=payload['values']
    np.testing.assert_array_equal(scores[...,0,0]+scores[...,0,1],np.ones_like(scores[...,0,0]))
    np.testing.assert_array_equal(scores[...,1,0],scores[...,1,1])
    np.testing.assert_array_equal(scores[...,1,3],scores[...,1,4])
    return True


def check_summary(blocks,summary,rows,original_focal=None):
    a=np.asarray(blocks);assert a.ndim==9 and a.shape[5]==7 and np.isfinite(a).all()
    assert set(summary)=={'means'} and len(rows)==42
    expected=sum(np.sum(b,axis=(0,5)) for b in a)/(len(a)*a.shape[1]*a.shape[6])
    close(summary['means'],expected)
    indices=previous.checker().generator(0,0,'block_bootstrap').integers(0,len(a),(10000,len(a)))
    for group,metric in enumerate((0,2,4)):
        for reader in range(2):
            for position,(positive,negative) in enumerate(PAIRS):
                row=rows[14*group+7*reader+position]
                assert row['reader']==('native_T','theta_only')[reader] and row['label']==LABELS[position]
                assert row['metric']==('damage_fidelity','damage_projection','damage_squared_error')[group]
                assert row['reused_source_contrast']==(position==6)
                cases=np.array([[[b[p,reader,-1,0,positive,d,0,metric]-b[p,reader,-1,0,negative,d,0,metric]
                    for d in range(a.shape[6])] for p in range(a.shape[1])] for b in a])
                means=np.array([sum(b.ravel())/b.size for b in cases])
                close(row['block_means'],means);close(row['parent_means'],cases.mean(axis=-1))
                close(row['mean'],means.mean());close(row['minimum'],min(means));close(row['maximum'],max(means))
                ci=np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5))
                close(row['pointwise_block_bootstrap_95'],ci)
                for prefix,v in (('',means),('paired_',cases)):
                    assert row[prefix+'positive']==int(np.count_nonzero(v>1e-12))
                    assert row[prefix+'negative']==int(np.count_nonzero(v< -1e-12))
                    assert row[prefix+'tied']==int(np.count_nonzero(abs(v)<=1e-12))
                if group==0 and position==6 and original_focal is not None:
                    source=original_focal[4*reader+3]
                    for key,value in source.items():
                        if key=='label': continue
                        if isinstance(value,str): assert row[key]==value
                        else: close(row[key],value)
    return True
