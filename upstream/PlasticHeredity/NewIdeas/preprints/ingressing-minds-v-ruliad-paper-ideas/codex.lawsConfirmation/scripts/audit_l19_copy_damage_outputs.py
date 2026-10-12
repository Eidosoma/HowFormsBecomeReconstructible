"""D104 independently restated address damage, rescue, dynamics and pooling.

Only older independent D102 control / D101 fission-observer / D097 physics
are reused. No D104 production map, branch, diagnostics or summary is called.
"""
from dataclasses import asdict,replace

import numpy as np

from laws_confirmation import l19_mean_maintenance as prior
from laws_confirmation.io import canonical_digest

mean=prior.checker(); old=mean.old; physics=mean.physics
nested,compare,generator=mean.nested,mean.compare,mean.generator
TAG='l19-copy-damage-v1'
ARMS=('clean_on','damaged_on','rescue_on','clean_off','damaged_off','rescue_off')
CASES=(('clean_on',.2,False,False),('damaged_on',.2,True,False),
       ('rescue_on',.2,True,True),('clean_off',0.,False,False),
       ('damaged_off',0.,True,False),('rescue_off',0.,True,True))
PAIRS=(('clean_on_minus_damaged_on',0,1),('rescue_on_minus_damaged_on',2,1),
       ('clean_on_minus_rescue_on',0,2),('clean_off_minus_damaged_off',3,4),
       ('rescue_off_minus_damaged_off',5,4),('clean_on_minus_clean_off',0,3),
       ('damaged_on_minus_damaged_off',1,4),('rescue_on_minus_rescue_off',2,5))


def draw_map(random,pairs):
    addresses=random.choice(256,2*pairs,replace=False)
    mapping=list(range(256))
    for k in range(pairs):
        a,b=int(addresses[2*k]),int(addresses[2*k+1]); mapping[a],mapping[b]=b,a
    return np.asarray(mapping,dtype=np.int64)


def permute(ref,mapping):
    result=np.empty_like(ref)
    for dest,source in enumerate(mapping): result.flat[dest]=ref.flat[int(source)]
    return result


def one_cycle(state,theta,tissue,ladder,bp,random,mapping,damaged,restore,cfg):
    birth,mask=old.fission(state,tissue,random)
    copied=permute(birth[2,0],mapping) if damaged else birth[2,0].copy()
    birth[2,0]=copied if restore is None else restore
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
        training_fresh=(cfg.training_cycles,16,16),states=(6,3*cfg.cycles+1,3,16,16),
        fresh=(cfg.cycles,16,16),values=(6,cfg.cycles+1,15),control=(6,cfg.cycles,cfg.teaching,7),
        copy_map=(cfg.cycles,256),pre_restore=(6,cfg.cycles,16,16))
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
    initial=raw['training'][-1]; trained=initial[2]
    for key in ('branch_rng','copy_rng'):
        assert len(meta[key])==6 and all(len(x)==cfg.cycles and x==meta[key][0] for x in meta[key])
    assert len(meta['training_rng'])==cfg.training_cycles
    for c,mapping in enumerate(raw['copy_map'],1):
        np.testing.assert_array_equal(np.sort(mapping),np.arange(256))
        np.testing.assert_array_equal(mapping[mapping],np.arange(256))
        assert np.count_nonzero(mapping!=np.arange(256))==2*cfg.damage_pairs
        random=generator(TAG,meta['index'],meta['life'],f'copy:{c}')
        np.testing.assert_array_equal(mapping,draw_map(random,cfg.damage_pairs))
        assert meta['copy_rng'][0][c-1]==canonical_digest(random.bit_generator.state)
    for ai,(_,gain,damaged,rescue) in enumerate(CASES):
        np.testing.assert_array_equal(raw['states'][ai,0],initial)
        for c in range(1,cfg.cycles+1):
            prev=raw['states'][ai,3*(c-1),2]
            copied=permute(prev,raw['copy_map'][c-1]) if damaged else prev.copy()
            np.testing.assert_array_equal(raw['pre_restore'][ai,c-1],copied)
            expected=trained if rescue and c==cfg.rescue_cycle else copied
            np.testing.assert_array_equal(raw['states'][ai,3*c-2:3*c+1,2],np.broadcast_to(expected,(3,16,16)))
            np.testing.assert_array_equal(np.sort(expected,axis=None),np.sort(trained,axis=None))
            assert abs(expected.mean()-trained.mean())<=1e-12
            assert abs((expected*expected).mean()-(trained*trained).mean())<=1e-12
    for ai in (4,5):
        np.testing.assert_array_equal(raw['states'][ai,:,:2],raw['states'][3,:,:2])
        np.testing.assert_array_equal(raw['control'][ai],raw['control'][3])
    for left,right in ((1,2),(4,5)):
        stop=3*(cfg.rescue_cycle-1)+1
        np.testing.assert_array_equal(raw['states'][left,:stop],raw['states'][right,:stop])
        np.testing.assert_array_equal(raw['control'][left,:cfg.rescue_cycle-1],raw['control'][right,:cfg.rescue_cycle-1])
        np.testing.assert_array_equal(raw['pre_restore'][left,:cfg.rescue_cycle],raw['pre_restore'][right,:cfg.rescue_cycle])
        np.testing.assert_array_equal(raw['states'][left,stop,:2],raw['states'][right,stop,:2])
    for ai in range(3):
        np.testing.assert_array_equal(raw['states'][ai,:,2],raw['states'][ai+3,:,2])
    np.testing.assert_allclose(raw['values'],old.measurements(raw,cfg),rtol=0,atol=1e-12)
    assert np.all(raw['values'][:,cfg.primary_cycle,13]>=64)
    for ai in range(6):
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
        for ai,(_,gain,damaged,rescue) in enumerate(CASES):
            state=common.copy(); changed=replace(bp,rho=0.,c_m=gain)
            for c in range(1,cfg.cycles+1):
                random=generator(TAG,index,life,f'branch:{c}')
                errors=generator(TAG,index,life,f'copy:{c}'); mapping=draw_map(errors,cfg.damage_pairs)
                restore=common[2,0] if rescue and c==cfg.rescue_cycle else None
                phases,mask,trace,copied=one_cycle(state,theta,tissue,ladder,changed,random,mapping,damaged,restore,cfg)
                error=max(error,compare(raw['states'][ai,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_array_equal(raw['pre_restore'][ai,c-1],copied)
                np.testing.assert_allclose(raw['control'][ai,c-1],trace,rtol=0,atol=1e-12)
                np.testing.assert_array_equal(raw['fresh'][c-1],mask[0])
                assert meta['branch_rng'][ai][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,paired_masks_streams=True,
        common_branch=True,copy_maps_separate_and_matched=True,record_multisets_preserved=True,
        between_copy_R_unchanged=True,delayed_rescue_aliases=True,reader_off_body_aliases=True,
        rescue_external_single_write=True,public_zero_mean_verified=True,complete_observers=True)


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
    contrasts=[]
    for c in list(dict.fromkeys([cfg.primary_cycle,3,cfg.rescue_cycle])):
        den=values[:,:,:,c,13]; assert np.all(den>=64)
        assert all(np.array_equal(den[:,:,0],den[:,:,a]) for a in range(6))
        for observer in ('regrown','whole'):
            score=values[:,:,:,c,12]/den if observer=='regrown' else values[:,:,:,c,0]
            for name,a,b in PAIRS:
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    trajectories=[]; diagnostics=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den)))
            fields={k:[] for k in ('founder_sign','trained_sign','trained_mae','mean','rms','copy_sign_change')}
            for block in blocks:
                row={k:[] for k in fields}
                for life in range(cfg.lives):
                    ref=block['states'][life,ai,3*c,2]; trained=block['training'][life,-1,2]
                    ancestor=block['ancestor'][life]
                    row['founder_sign'].append(np.count_nonzero((ref>0)==(ancestor>0))/256)
                    row['trained_sign'].append(np.count_nonzero((ref>0)==(trained>0))/256)
                    row['trained_mae'].append(abs(ref-trained).sum()/256)
                    row['mean'].append(ref.sum()/256); row['rms'].append(np.sqrt((ref**2).sum()/256))
                    if c:
                        before=block['states'][life,ai,3*(c-1),2]; after=block['pre_restore'][life,ai,c-1]
                        row['copy_sign_change'].append(np.count_nonzero((before>0)!=(after>0))/256)
                for key in fields: fields[key].append(row[key])
            diagnostics.append(dict(arm=arm,cycle=c,**{key:None if key=='copy_sign_change' and c==0
                else stats(np.asarray(val)) for key,val in fields.items()}))
    residual=float(np.max(np.abs(controls[:,:,:,:,:,1]))); assert residual<=1e-12
    primary,rescue=contrasts[:2]
    expected=dict(schema='l19_copy_damage_summary_v1',tissues=list(range(49000,49008)),arms=list(ARMS),
        metrics=list(prior.METRICS),control_metrics=list(prior.CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,rescue_contrast=rescue,
        contrasts=contrasts,trajectories=trajectories,record_diagnostics=diagnostics,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='COPY_ADDRESS_DAMAGE_COST' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_COPY_ADDRESS_DAMAGE_COST',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_copy_damage_run import main
    main(default_command='audit')
