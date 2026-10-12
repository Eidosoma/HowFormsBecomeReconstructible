"""D105 independent local repair, content observers, replay and pooling."""
from dataclasses import asdict,replace

import numpy as np

from laws_confirmation import l19_copy_damage as prior
from laws_confirmation.io import canonical_digest

copy=prior.checker(); mean=copy.mean; old=copy.old; physics=copy.physics
nested,compare,generator=copy.nested,copy.compare,copy.generator
TAG='l19-internal-repair-v1'
ARMS=('clean_on','damaged_on','repaired_on','clean_repaired_on',
      'wrong_on','wrong_repaired_on','damaged_off','repaired_off')
CASES=(('clean_on',.2,False,False,'trained'),('damaged_on',.2,True,False,'trained'),
    ('repaired_on',.2,True,True,'trained'),('clean_repaired_on',.2,False,True,'trained'),
    ('wrong_on',.2,True,False,'shifted'),('wrong_repaired_on',.2,True,True,'shifted'),
    ('damaged_off',0.,True,False,'trained'),('repaired_off',0.,True,True,'trained'))
CONTENT_METRICS=('own_body_fidelity','own_regrown_correct','own_reference_sign','incoming_R_mae',
    'detail_total','detail_body_correct','detail_reference_correct','canonical_body_fidelity','own_minus_other_body')
CONTRASTS=(('repaired_minus_damaged',(0,-1,1,0,0,0,0,0)),
    ('clean_repaired_minus_clean',(-1,0,0,1,0,0,0,0)),
    ('damage_specific_repair_interaction',(1,-1,1,-1,0,0,0,0)),
    ('wrong_repaired_minus_wrong',(0,0,0,0,-1,1,0,0)),
    ('repaired_off_minus_damaged_off',(0,0,0,0,0,0,-1,1)),
    ('repaired_on_minus_off',(0,0,1,0,0,0,0,-1)),
    ('damaged_on_minus_off',(0,1,0,0,0,0,-1,0)),
    ('clean_minus_repaired',(1,0,-1,0,0,0,0,0)))


def shifted(ref,cfg): return ref[:,(np.arange(16)-cfg.shift)%16].copy()


def median_pass(ref):
    result=np.empty_like(ref)
    for y in range(16):
        for x in range(16):
            values=[ref[(y+dy)%16,(x+dx)%16] for dy in (-1,0,1) for dx in (-1,0,1)]
            result[y,x]=sorted(values)[4]
    return result


def content_observers(raw,cfg):
    canonical=np.where(np.arange(16)[None,:]<8,1.,-1.)*np.ones((16,1)); result=[]
    for ai in range(8):
        own=shifted(raw['ancestor'],cfg) if ai in (4,5) else raw['ancestor']
        other=raw['ancestor'] if ai in (4,5) else shifted(raw['ancestor'],cfg)
        generic=shifted(canonical,cfg) if ai in (4,5) else canonical
        detail=np.signbit(own)!=np.signbit(generic); rows=[]
        for c in range(cfg.cycles+1):
            mask=np.sum(raw['fresh'][:c],axis=0)>=2
            v,_,ref=raw['states'][ai,3*c]; amp=abs(v)>cfg.amp_threshold
            correct=(np.signbit(v)==np.signbit(own)) & amp
            alternative=(np.signbit(v)==np.signbit(other)) & amp
            rows.append([np.count_nonzero(correct)/256,np.count_nonzero(correct & mask),
                np.count_nonzero((ref>0)==(own>0))/256,abs(ref-raw['states'][ai,0,2]).sum()/256,
                np.count_nonzero(detail),np.count_nonzero(correct & detail),
                np.count_nonzero(((ref>0)==(own>0)) & detail),
                np.count_nonzero((np.signbit(v)==np.signbit(generic)) & amp)/256,
                (np.count_nonzero(correct)-np.count_nonzero(alternative))/256])
        result.append(rows)
    return np.asarray(result,dtype=np.float64)


def one_cycle(state,theta,tissue,ladder,bp,random,mapping,damaged,repaired,cfg):
    birth,mask=old.fission(state,tissue,random)
    copied=copy.permute(birth[2,0],mapping) if damaged else birth[2,0].copy()
    birth[2,0]=median_pass(copied) if repaired else copied
    v,ema,ref=(x.copy() for x in birth); trace=[]
    for _ in range(cfg.teaching):
        before=v[0]; after,offset=mean.project(before); delta=after-before
        row=[float(before.sum()/256),float(after.sum()/256),offset,
            float(np.sqrt((delta*delta).sum()/256)),float(np.count_nonzero(abs(after)==2)/256),
            float(np.max(abs(delta)))]
        v,ema,ref=physics.step(after[None],ema,ref,theta,tissue,ladder,bp.c_m,0.,
                             random.standard_normal(v.shape))
        trace.append(row+[float(v.sum()/256)])
    release=np.stack((v,ema,ref)); end=old.free(release,theta,tissue,ladder,bp,random,cfg.free)
    return np.stack((birth,release,end)),mask,np.asarray(trace),copied


def check_life(raw,meta,cfg,replay=True):
    shapes=dict(theta=(16,16),ancestor=(16,16),training=(cfg.training_cycles+1,3,16,16),
        training_fresh=(cfg.training_cycles,16,16),states=(8,3*cfg.cycles+1,3,16,16),
        fresh=(cfg.cycles,16,16),values=(8,cfg.cycles+1,15),control=(8,cfg.cycles,cfg.teaching,7),
        copy_map=(cfg.cycles,256),pre_repair=(8,cfg.cycles,16,16),content=(8,cfg.cycles+1,9))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key in ('fresh','training_fresh'):
            assert raw[key].dtype==np.bool_ and np.all(raw[key].sum(axis=(-2,-1))==128)
        elif key=='copy_map': assert raw[key].dtype==np.int64
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['arms'],list(ARMS))
    nested(meta['arm_parameters'],[list(x) for x in CASES]); assert meta['tag']==TAG
    assert type(meta['life']) is int and 0<=meta['life']<cfg.lives and meta['theta_writable'] is False
    tissue,ladder,bp=physics.parameters(meta)
    assert np.all(np.isin(raw['ancestor'],(-1.,1.)))
    initial=raw['training'][-1]; trained=initial[2]; wrong=shifted(trained,cfg)
    assert not np.array_equal(trained,wrong)
    np.testing.assert_array_equal(np.sort(wrong,axis=None),np.sort(trained,axis=None))
    for key in ('branch_rng','copy_rng'):
        assert len(meta[key])==8 and all(len(x)==cfg.cycles and x==meta[key][0] for x in meta[key])
    assert len(meta['training_rng'])==cfg.training_cycles
    for c,mapping in enumerate(raw['copy_map'],1):
        np.testing.assert_array_equal(np.sort(mapping),np.arange(256))
        np.testing.assert_array_equal(mapping[mapping],np.arange(256))
        assert np.count_nonzero(mapping!=np.arange(256))==2*cfg.damage_pairs
        random=generator(TAG,meta['index'],meta['life'],f'copy:{c}')
        np.testing.assert_array_equal(mapping,copy.draw_map(random,cfg.damage_pairs))
        assert meta['copy_rng'][0][c-1]==canonical_digest(random.bit_generator.state)
    for ai,(_,gain,damaged,repaired,record) in enumerate(CASES):
        np.testing.assert_array_equal(raw['states'][ai,0,:2],initial[:2])
        np.testing.assert_array_equal(raw['states'][ai,0,2],wrong if record=='shifted' else trained)
        for c in range(1,cfg.cycles+1):
            prev=raw['states'][ai,3*(c-1),2]
            copied=copy.permute(prev,raw['copy_map'][c-1]) if damaged else prev.copy()
            np.testing.assert_array_equal(raw['pre_repair'][ai,c-1],copied)
            np.testing.assert_array_equal(np.sort(copied,axis=None),np.sort(prev,axis=None))
            expected=median_pass(copied) if repaired else copied
            assert expected.min()>=copied.min() and expected.max()<=copied.max()
            np.testing.assert_array_equal(raw['states'][ai,3*c-2:3*c+1,2],np.broadcast_to(expected,(3,16,16)))
    np.testing.assert_array_equal(raw['states'][6,:,:2],raw['states'][7,:,:2])
    np.testing.assert_array_equal(raw['control'][6],raw['control'][7])
    for left,right in ((1,6),(2,7)):
        np.testing.assert_array_equal(raw['states'][left,:,2],raw['states'][right,:,2])
        np.testing.assert_array_equal(raw['pre_repair'][left],raw['pre_repair'][right])
    np.testing.assert_allclose(raw['values'],old.measurements(raw,cfg),rtol=0,atol=1e-12)
    np.testing.assert_array_equal(raw['content'],content_observers(raw,cfg))
    assert np.all(raw['values'][:,cfg.primary_cycle,13]>=64)
    for ai in range(8):
        for c in range(1,cfg.cycles+1):
            trace=raw['control'][ai,c-1]
            assert np.max(abs(trace[:,1]))<=1e-12
            assert np.all(trace[:,3]>=0) and np.all(trace[:,5]>=trace[:,3]-1e-12)
            assert np.all((trace[:,4]>=0)&(trace[:,4]<=1))
            assert abs(trace[0,0]-raw['states'][ai,3*c-2,0].mean())<=1e-12
            assert abs(trace[-1,6]-raw['states'][ai,3*c-1,0].mean())<=1e-12
    error=0.
    if replay:
        index,life=meta['index'],meta['life']; random=generator(TAG,index,life,'founder')
        state,theta=physics.settle(tissue,ladder,random,1,cfg.settle)
        error=max(compare(raw['theta'],theta),compare(raw['training'][0],state[:,0]))
        ancestor=np.sign(state[0]); ancestor[ancestor==0]=1.
        error=max(error,compare(raw['ancestor'],ancestor[0]))
        assert meta['founder_rng']==canonical_digest(random.bit_generator.state)
        for c in range(1,cfg.training_cycles+1):
            random=generator(TAG,index,life,f'training:{c}')
            phases,mask=old.advance(state,theta,tissue,ladder,bp,random,ancestor,cfg.amplitude,cfg.teaching,cfg.free)
            state=phases[-1]; error=max(error,compare(raw['training'][c],state[:,0]))
            np.testing.assert_array_equal(raw['training_fresh'][c-1],mask[0])
            assert meta['training_rng'][c-1]==canonical_digest(random.bit_generator.state)
        common=state.copy()
        for ai,(_,gain,damaged,repaired,record) in enumerate(CASES):
            state=common.copy(); changed=replace(bp,rho=0.,c_m=gain)
            if record=='shifted': state[2,0]=shifted(common[2,0],cfg)
            for c in range(1,cfg.cycles+1):
                random=generator(TAG,index,life,f'branch:{c}')
                errors=generator(TAG,index,life,f'copy:{c}'); mapping=copy.draw_map(errors,cfg.damage_pairs)
                phases,mask,trace,copied=one_cycle(state,theta,tissue,ladder,changed,random,mapping,damaged,repaired,cfg)
                error=max(error,compare(raw['states'][ai,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_array_equal(raw['pre_repair'][ai,c-1],copied)
                np.testing.assert_allclose(raw['control'][ai,c-1],trace,rtol=0,atol=1e-12)
                np.testing.assert_array_equal(raw['fresh'][c-1],mask[0])
                assert meta['branch_rng'][ai][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,paired_masks_streams=True,
        common_V_EMA=True,copy_maps_separate_and_matched=True,copy_multiset_preserved=True,
        local_median_verified=True,between_boundary_R_unchanged=True,wrong_initial_R_verified=True,
        reader_off_body_aliases=True,public_zero_mean_verified=True,complete_content_and_detail_observers=True)


def check_block(raw,meta,cfg,replay=True):
    nested(meta['config'],asdict(cfg)); assert type(meta['index']) is int and meta['index']>=0
    assert len(meta['lives'])==cfg.lives and all(v.shape[0]==cfg.lives for v in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life and record['exact_alias_branches']==1
        result=check_life({k:v[life] for k,v in raw.items()},record,cfg,replay)
        if replay: nested(record['replay'],result)
        else:
            expected=result | dict(full_life_replay=True,max_abs=record['replay']['max_abs'])
            assert 0<=expected['max_abs']<=1e-10; nested(record['replay'],expected)
    return True


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    values=np.asarray([[old.measurements({k:v[l] for k,v in b.items()},cfg) for l in range(cfg.lives)] for b in blocks])
    content=np.asarray([[content_observers({k:v[l] for k,v in b.items()},cfg) for l in range(cfg.lives)] for b in blocks])
    controls=np.asarray([b['control'] for b in blocks]); samples=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8))
    def stats(lives):
        means=np.array([x.mean() for x in lives])
        out=dict(mean=float(means.mean()),block_means=means.tolist(),life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(means[samples].mean(axis=1),[.025,.975]).tolist())
        for prefix,x in (('block_',means),('life_',lives)):
            out[prefix+'positive']=int((x>1e-12).sum()); out[prefix+'negative']=int((x< -1e-12).sum())
            out[prefix+'tied']=int((abs(x)<=1e-12).sum())
        return out
    contrasts=[]
    for c in list(dict.fromkeys([cfg.primary_cycle,3])):
        den=values[:,:,:,c,13]; assert np.all(den>=64)
        assert all(np.array_equal(den[:,:,0],den[:,:,a]) for a in range(8))
        for observer in ('regrown','whole'):
            score=content[:,:,:,c,1]/den if observer=='regrown' else content[:,:,:,c,0]
            for name,coefs in CONTRASTS:
                effect=np.zeros((8,cfg.lives))
                for ai in range(8):
                    if coefs[ai]: effect+=coefs[ai]*score[:,:,ai]
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(effect)))
    trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]; details=content[:,:,ai,c,4]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(content[:,:,ai,c,0]),
                founder_whole=stats(values[:,:,ai,c,0]),parent=stats(values[:,:,ai,c,11]),
                own_minus_other=stats(content[:,:,ai,c,8]),canonical=stats(content[:,:,ai,c,7]),
                own_reference_sign=stats(content[:,:,ai,c,2]),incoming_R_mae=stats(content[:,:,ai,c,3]),
                record_mean=stats(values[:,:,ai,c,7]),record_rms=stats(values[:,:,ai,c,9]),
                regrown_denominators=den.astype(int).tolist(),detail_denominators=details.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(content[:,:,ai,c,1]/den),
                detail_body=None if np.any(details==0) else stats(content[:,:,ai,c,5]/details),
                detail_reference=None if np.any(details==0) else stats(content[:,:,ai,c,6]/details)))
    residual=float(np.max(np.abs(controls[:,:,:,:,:,1]))); assert residual<=1e-12
    primary=contrasts[0]
    expected=dict(schema='l19_internal_repair_summary_v1',tissues=list(range(50000,50008)),arms=list(ARMS),
        metrics=list(prior.METRICS),control_metrics=list(prior.CONTROL_METRICS),content_metrics=list(CONTENT_METRICS),
        cycles=list(range(cfg.cycles+1)),cell_means=values.mean(axis=(0,1)).tolist(),
        content_means=content.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,contrasts=contrasts,trajectories=trajectories,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='LOCAL_REPAIR_BODY_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_LOCAL_REPAIR_BODY_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False,detail_missing_policy='null aggregate if any life has zero details; no exclusions')
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_internal_repair_run import main
    main(default_command='audit')
