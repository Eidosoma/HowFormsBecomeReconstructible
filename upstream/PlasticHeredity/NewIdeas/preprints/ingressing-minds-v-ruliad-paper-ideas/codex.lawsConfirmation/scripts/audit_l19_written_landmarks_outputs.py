"""D106 independent targets, writing/reading replay, observations and adjudication."""
from dataclasses import asdict,replace

import numpy as np

from laws_confirmation import l19_internal_repair as prior
from laws_confirmation.io import canonical_digest

oldcheck=prior.checker(); copy=oldcheck.copy; mean=oldcheck.mean; old=oldcheck.old; physics=oldcheck.physics
nested,compare,generator=oldcheck.nested,oldcheck.compare,oldcheck.generator
TAG='l19-written-landmarks-v1'
QUAL_ARMS=('clean_on','clean_off')
MAIN_ARMS=('clean_on','damaged_on','repaired_on','clean_repaired_on','damaged_off','repaired_off')
PARAMETERS={'clean_on':(.2,False,False),'clean_off':(0.,False,False),
    'damaged_on':(.2,True,False),'repaired_on':(.2,True,True),'clean_repaired_on':(.2,False,True),
    'damaged_off':(0.,True,False),'repaired_off':(0.,True,True)}
METRICS=('own_detail_body','other_detail_body','own_detail_R_sign','own_detail_R_projection',
    'whole_own_body','coarse_body','record_mean','record_rms','regrown_detail_correct',
    'regrown_detail_total','regrown_whole_correct','regrown_whole_total')
TRAIN_METRICS=('detail_R_projection','detail_R_sign','detail_body','whole_body')
GATES=('written_R_content','clean_read_correct_minus_swapped','clean_read_correct_minus_off')


def templates():
    coarse=np.ones((16,16),dtype=np.float64)
    for x in range(8,16): coarse[:,x]=-1.
    a=coarse.copy(); b=coarse.copy()
    for matrix,ys in ((a,(3,4)),(b,(11,12))):
        for y in ys:
            for x in (3,4,11,12): matrix[y,x]=-coarse[y,x]
    return np.stack((a,b)),coarse,np.not_equal(a,b)


def observations(raw,cfg):
    taught,coarse,detail=templates(); result=[]; denominator=np.count_nonzero(detail)
    for k in (0,1):
        rows=[]
        for path in raw['states'][k]:
            cycle_rows=[]
            for c in range(cfg.cycles+1):
                v,_,ref=path[3*c]; qualified=np.abs(v)>cfg.amp_threshold
                counts=np.zeros((16,16),dtype=int)
                for mask in raw['fresh'][:c]: counts+=mask
                regrown=counts>=2
                correct=np.logical_and((v>0)==(taught[k]>0),qualified)
                wrong=np.logical_and((v>0)==(taught[1-k]>0),qualified)
                cycle_rows.append([np.count_nonzero(correct & detail)/denominator,
                    np.count_nonzero(wrong & detail)/denominator,
                    np.count_nonzero(((ref>0)==(taught[k]>0)) & detail)/denominator,
                    np.sum((ref*taught[k])[detail])/denominator,np.count_nonzero(correct)/256,
                    np.count_nonzero(((v>0)==(coarse>0)) & qualified & ~detail)/(256-denominator),
                    np.sum(ref)/256,np.sqrt(np.sum(ref**2)/256),np.count_nonzero(correct & regrown & detail),
                    np.count_nonzero(regrown & detail),np.count_nonzero(correct & regrown),np.count_nonzero(regrown)])
            rows.append(cycle_rows)
        result.append(rows)
    training=[]
    for k in (0,1):
        rows=[]
        for v,_,ref in raw['training'][k]:
            correct=((v>0)==(taught[k]>0)) & (np.abs(v)>cfg.amp_threshold)
            rows.append([np.sum((ref*taught[k])[detail])/denominator,
                np.count_nonzero(((ref>0)==(taught[k]>0)) & detail)/denominator,
                np.count_nonzero(correct & detail)/denominator,np.count_nonzero(correct)/256])
        training.append(rows)
    return np.asarray(result,dtype=np.float64),np.asarray(training,dtype=np.float64)


def check_life(raw,meta,cfg,replay=True):
    assert type(meta['qualification']) is bool
    arms=QUAL_ARMS if meta['qualification'] else MAIN_ARMS; n=len(arms)
    shapes=dict(theta=(16,16),founder=(3,16,16),training=(2,3*cfg.training_cycles+1,3,16,16),
        training_fresh=(cfg.training_cycles,16,16),states=(2,n,3*cfg.cycles+1,3,16,16),
        fresh=(cfg.cycles,16,16),control=(2,n,cfg.cycles,cfg.teaching,7),copy_map=(cfg.cycles,256),
        pre_repair=(2,n,cfg.cycles,16,16),values=(2,n,cfg.cycles+1,12),training_values=(2,3*cfg.training_cycles+1,4))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key in ('fresh','training_fresh'):
            assert raw[key].dtype==np.bool_ and np.all(raw[key].sum(axis=(-2,-1))==128)
        elif key=='copy_map': assert raw[key].dtype==np.int64
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['arms'],list(arms))
    nested(meta['arm_parameters'],[[a,*PARAMETERS[a]] for a in arms])
    assert meta['tag']==TAG and type(meta['life']) is int and 0<=meta['life']<cfg.lives
    assert meta['theta_writable'] is False
    tissue,ladder,bp=physics.parameters(meta); taught,_,_=templates()
    assert len(meta['training_rng'])==2 and meta['training_rng'][0]==meta['training_rng'][1]
    assert len(meta['training_rng'][0])==cfg.training_cycles
    for key in ('branch_rng','copy_rng'):
        assert len(meta[key])==2 and all(len(x)==n for x in meta[key])
        assert all(len(row)==cfg.cycles and row==meta[key][0][0] for pattern in meta[key] for row in pattern)
    for k in range(2): np.testing.assert_array_equal(raw['training'][k,0],raw['founder'])
    for c,mapping in enumerate(raw['copy_map'],1):
        np.testing.assert_array_equal(np.sort(mapping),np.arange(256))
        np.testing.assert_array_equal(mapping[mapping],np.arange(256))
        assert np.count_nonzero(mapping!=np.arange(256))==2*cfg.damage_pairs
        random=generator(TAG,meta['index'],meta['life'],f'copy:{c}')
        np.testing.assert_array_equal(mapping,copy.draw_map(random,cfg.damage_pairs))
        assert meta['copy_rng'][0][0][c-1]==canonical_digest(random.bit_generator.state)
    for k in range(2):
        for a,arm in enumerate(arms):
            _,damaged,repaired=PARAMETERS[arm]
            np.testing.assert_array_equal(raw['states'][k,a,0,:2],raw['founder'][:2])
            np.testing.assert_array_equal(raw['states'][k,a,0,2],raw['training'][k,-1,2])
            for c in range(1,cfg.cycles+1):
                before=raw['states'][k,a,3*(c-1),2]
                incoming=copy.permute(before,raw['copy_map'][c-1]) if damaged else before.copy()
                np.testing.assert_array_equal(raw['pre_repair'][k,a,c-1],incoming)
                np.testing.assert_array_equal(np.sort(before,axis=None),np.sort(incoming,axis=None))
                after=oldcheck.median_pass(incoming) if repaired else incoming
                np.testing.assert_array_equal(raw['states'][k,a,3*c-2:3*c+1,2],np.broadcast_to(after,(3,16,16)))
                trace=raw['control'][k,a,c-1]
                assert np.max(np.abs(trace[:,1]))<=1e-12
                assert abs(trace[0,0]-raw['states'][k,a,3*c-2,0].mean())<=1e-12
                assert abs(trace[-1,6]-raw['states'][k,a,3*c-1,0].mean())<=1e-12
    off=[(k,a) for k in range(2) for a,arm in enumerate(arms) if PARAMETERS[arm][0]==0]
    for k,a in off[1:]:
        np.testing.assert_array_equal(raw['states'][k,a,:,:2],raw['states'][off[0][0],off[0][1],:,:2])
        np.testing.assert_array_equal(raw['control'][k,a],raw['control'][off[0][0],off[0][1]])
    expected,training=observations(raw,cfg)
    np.testing.assert_allclose(raw['values'],expected,rtol=0,atol=1e-12)
    np.testing.assert_allclose(raw['training_values'],training,rtol=0,atol=1e-12)
    error=0.
    if replay:
        index,life=meta['index'],meta['life']; random=generator(TAG,index,life,'founder')
        founder,theta=physics.settle(tissue,ladder,random,1,cfg.settle)
        error=max(compare(raw['theta'],theta),compare(raw['founder'],founder[:,0]))
        assert meta['founder_rng']==canonical_digest(random.bit_generator.state)
        for k in range(2):
            state=founder.copy()
            for c in range(1,cfg.training_cycles+1):
                random=generator(TAG,index,life,f'training:{c}')
                phases,mask=old.advance(state,theta,tissue,ladder,bp,random,taught[k][None],cfg.amplitude,cfg.teaching,cfg.free)
                error=max(error,compare(raw['training'][k,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_array_equal(raw['training_fresh'][c-1],mask[0])
                assert meta['training_rng'][k][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
            common=founder.copy(); common[2]=state[2]
            for a,arm in enumerate(arms):
                gain,damaged,repaired=PARAMETERS[arm]; state=common.copy(); changed=replace(bp,rho=0.,c_m=gain)
                for c in range(1,cfg.cycles+1):
                    random=generator(TAG,index,life,f'branch:{c}'); errors=generator(TAG,index,life,f'copy:{c}')
                    mapping=copy.draw_map(errors,cfg.damage_pairs)
                    phases,mask,trace,copied=oldcheck.one_cycle(state,theta,tissue,ladder,changed,random,mapping,damaged,repaired,cfg)
                    error=max(error,compare(raw['states'][k,a,3*c-2:3*c+1],phases[:,:,0]))
                    np.testing.assert_array_equal(raw['pre_repair'][k,a,c-1],copied)
                    np.testing.assert_allclose(raw['control'][k,a,c-1],trace,rtol=0,atol=1e-12)
                    np.testing.assert_array_equal(raw['fresh'][c-1],mask[0])
                    assert meta['branch_rng'][k][a][c-1]==canonical_digest(random.bit_generator.state)
                    state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,native_written_records=True,
        common_untrained_recipient=True,paired_masks_streams=True,copy_maps_separate_and_matched=True,
        local_median_verified=True,between_boundary_R_unchanged=True,reader_off_body_aliases=True,
        public_zero_mean_verified=True,landmark_and_training_observers=True)


def check_block(raw,meta,cfg,replay=True):
    nested(meta['config'],asdict(cfg)); assert type(meta['index']) is int and meta['index']>=0
    assert type(meta['qualification']) is bool and len(meta['lives'])==cfg.lives
    assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life
        assert record['qualification'] is meta['qualification'] and record['exact_alias_branches']==1
        result=check_life({k:v[life] for k,v in raw.items()},record,cfg,replay)
        if replay: nested(record['replay'],result)
        else:
            expected=result | dict(full_life_replay=True,max_abs=record['replay']['max_abs'])
            assert 0<=expected['max_abs']<=1e-10; nested(record['replay'],expected)
    return True


def check_summary(summary,blocks,qualification,cfg):
    assert len(blocks)==8 and type(qualification) is bool
    arms=QUAL_ARMS if qualification else MAIN_ARMS
    observed=[[observations({k:v[l] for k,v in b.items()},cfg) for l in range(cfg.lives)] for b in blocks]
    values=np.asarray([[row[0] for row in b] for b in observed])
    training=np.asarray([[row[1] for row in b] for b in observed])
    controls=np.asarray([b['control'] for b in blocks])
    samples=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8))
    def stats(lives):
        means=np.array([x.mean() for x in lives])
        out=dict(mean=float(means.mean()),block_means=means.tolist(),life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(means[samples].mean(axis=1),[.025,.975]).tolist())
        for prefix,x in (('block_',means),('life_',lives)):
            out[prefix+'positive']=int((x>1e-12).sum()); out[prefix+'negative']=int((x< -1e-12).sum())
            out[prefix+'tied']=int((abs(x)<=1e-12).sum())
        return out
    own=(values[:,:,0,:,:,0]+values[:,:,1,:,:,0])/2
    other=(values[:,:,0,:,:,1]+values[:,:,1,:,:,1])/2
    specificity=own-other; contrasts=[]; gates=[]
    if qualification:
        effects=(training[:,:,0,-1,0]+training[:,:,1,-1,0],specificity[:,:,0,1],own[:,:,0,1]-own[:,:,1,1])
        gates=[dict(name=name,**stats(effect)) for name,effect in zip(GATES,effects)]
    else:
        for c in (cfg.primary_cycle,3,1):
            for name,a,b in (('repair_minus_damage',2,1),('clean_repair_minus_clean',3,0),
                    ('clean_minus_repaired',0,2),('repair_reader_effect',2,5),('damage_reader_effect',1,4),
                    ('off_repair_alias',5,4)):
                scores={'landmark_specificity':specificity,'landmark_own':own,
                    'whole':(values[:,:,0,:,:,4]+values[:,:,1,:,:,4])/2,
                    'coarse':(values[:,:,0,:,:,5]+values[:,:,1,:,:,5])/2}
                for observer,score in scores.items():
                    contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a,c]-score[:,:,b,c])))
    trajectories=[]
    for a,arm in enumerate(arms):
        for c in range(cfg.cycles+1):
            row=dict(arm=arm,cycle=c,own=stats(own[:,:,a,c]),other=stats(other[:,:,a,c]),specificity=stats(specificity[:,:,a,c]))
            for name,col in (('reference_sign',2),('reference_projection',3),('whole',4),('coarse',5),
                    ('reference_mean',6),('reference_rms',7)):
                row[name]=stats((values[:,:,0,a,c,col]+values[:,:,1,a,c,col])/2)
            row['per_target_own']=[stats(values[:,:,k,a,c,0]) for k in range(2)]
            row['regrown_detail_denominators']=values[:,:,:,a,c,9].astype(int).tolist()
            row['regrown_whole_denominators']=values[:,:,:,a,c,11].astype(int).tolist()
            trajectories.append(row)
    qualified=all(g['pointwise_block_bootstrap_95'][0]>0 for g in gates) if qualification else None
    primary=gates[1] if qualification else contrasts[0]
    if qualification:
        label='CLEAN_LANDMARK_READ_QUALIFIED' if qualified else 'CLEAN_LANDMARK_READ_NOT_QUALIFIED'
    elif primary['pointwise_block_bootstrap_95'][0]>0: label='REPAIR_IMPROVES_LANDMARK_SPECIFICITY'
    elif primary['pointwise_block_bootstrap_95'][1]<0: label='REPAIR_REDUCES_LANDMARK_SPECIFICITY'
    else: label='LANDMARK_REPAIR_EFFECT_UNRESOLVED'
    residual=float(np.max(np.abs(controls[...,1]))); assert residual<=1e-12
    expected=dict(schema='l19_written_landmarks_summary_v1',qualification=qualification,qualified=qualified,label=label,
        tissues=list(range(51500,51508) if qualification else range(51000,51008)),arms=list(arms),
        metrics=list(METRICS),training_metrics=list(TRAIN_METRICS),primary=primary,gates=gates,contrasts=contrasts,
        trajectories=trajectories,cell_means=values.mean(axis=(0,1)).tolist(),training_means=training.mean(axis=(0,1)).tolist(),
        max_controlled_mean_residual=residual,blocks=8,lives_per_block=cfg.lives,landmark_cells=16,
        absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False,
        training_projection_trajectory=[stats(training[:,:,0,c,0]+training[:,:,1,c,0]) for c in range(3*cfg.training_cycles+1)])
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_written_landmarks_run import main
    main(default_command='audit')
