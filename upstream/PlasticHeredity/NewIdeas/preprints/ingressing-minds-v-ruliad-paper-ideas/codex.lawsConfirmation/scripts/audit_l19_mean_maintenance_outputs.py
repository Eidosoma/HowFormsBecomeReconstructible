"""D102 independent mean control, schedules, traces and paired pooling.

Reuses only D101's independent fission/observer and D097's restated equations,
not the D102 production controller, simulation, schedule or summary.
"""
from dataclasses import asdict

import numpy as np

from laws_confirmation import l19_broadcast_withdrawal as prior
from laws_confirmation.io import canonical_digest

old=prior.checker(); physics=old.physics
nested,compare,generator=old.nested,old.compare,old.generator
TAG='l19-mean-maintenance-v1'
ARMS=('continued','withdrawn','mean_early','mean_late','spatial_rescue')
CONTROL_METRICS=('pre_mean','controlled_mean','uniform_offset','action_rms',
                 'saturation_fraction','maximum_change','after_update_mean')
PAIRS=(('mean_early_minus_withdrawn',2,1),('continued_minus_withdrawn',0,1),
       ('continued_minus_mean_early',0,2),('mean_late_minus_withdrawn',3,1),
       ('spatial_rescue_minus_withdrawn',4,1),('spatial_rescue_minus_mean_late',4,3),
       ('mean_early_minus_mean_late',2,3))


def project(v):
    assert v.shape==(16,16) and np.isfinite(v).all()
    offset=-float(np.mean(v)); answer=v+offset
    if np.min(answer)<-2. or np.max(answer)>2.:
        lower=-2.-float(np.max(v)); upper=2.-float(np.min(v))
        for _ in range(64):
            trial=(lower+upper)/2.
            average=np.mean(np.minimum(2.,np.maximum(-2.,v+trial)))
            if average>0: upper=trial
            else: lower=trial
        offset=(lower+upper)/2.
        answer=np.minimum(2.,np.maximum(-2.,v+offset))
    assert abs(np.mean(answer))<=1e-12 and np.max(abs(answer))<=2.
    return answer,offset


def mode_for(arm,cycle,cfg):
    if arm=='continued' or (arm=='spatial_rescue' and cycle>=cfg.rescue_cycle): return 'spatial'
    if arm=='mean_early' or (arm=='mean_late' and cycle>=cfg.rescue_cycle): return 'mean'
    return 'none'


def one_cycle(state,theta,tissue,ladder,bp,random,mode,ancestor,cfg):
    birth,mask=old.fission(state,tissue,random)
    v,ema,ref=(x.copy() for x in birth); trace=[]
    for _ in range(cfg.teaching):
        before=v[0]; offset=0.
        if mode=='mean': after,offset=project(before)
        elif mode=='spatial': after=cfg.amplitude*ancestor[0]
        else: after=before.copy()
        delta=after-before
        row=[float(before.sum()/256),float(after.sum()/256),offset,
            float(np.sqrt((delta*delta).sum()/256)),float(np.count_nonzero(abs(after)==2)/256),
            float(np.max(abs(delta)))]
        v,ema,ref=physics.step(after[None],ema,ref,theta,tissue,ladder,bp.c_m,bp.rho,
                             random.standard_normal(v.shape))
        trace.append(row+[float(v.sum()/256)])
    release=np.stack((v,ema,ref))
    end=old.free(release,theta,tissue,ladder,bp,random,cfg.free)
    return np.stack((birth,release,end)),mask,np.asarray(trace)


def check_life(raw,meta,cfg,replay=True):
    shapes=dict(theta=(16,16),ancestor=(16,16),training=(cfg.training_cycles+1,3,16,16),
        training_fresh=(cfg.training_cycles,16,16),states=(5,3*cfg.cycles+1,3,16,16),
        fresh=(cfg.cycles,16,16),values=(5,cfg.cycles+1,15),control=(5,cfg.cycles,cfg.teaching,7))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key in ('fresh','training_fresh'):
            assert raw[key].dtype==np.bool_ and np.all(raw[key].sum(axis=(-2,-1))==128)
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['arms'],list(ARMS)); assert meta['tag']==TAG
    assert type(meta['life']) is int and 0<=meta['life']<cfg.lives and meta['theta_writable'] is False
    tissue,ladder,bp=physics.parameters(meta)
    assert np.all(np.isin(raw['ancestor'],(-1.,1.)))
    for ai in range(5): np.testing.assert_array_equal(raw['states'][ai,0],raw['training'][-1])
    for ai in (3,4):
        np.testing.assert_array_equal(raw['states'][ai,:3*(cfg.rescue_cycle-1)+1],
                                      raw['states'][1,:3*(cfg.rescue_cycle-1)+1])
        np.testing.assert_array_equal(raw['control'][ai,:cfg.rescue_cycle-1],raw['control'][1,:cfg.rescue_cycle-1])
    assert len(meta['training_rng'])==cfg.training_cycles and len(meta['branch_rng'])==5
    assert all(len(x)==cfg.cycles and x==meta['branch_rng'][0] for x in meta['branch_rng'])
    np.testing.assert_allclose(raw['values'],old.measurements(raw,cfg),rtol=0,atol=1e-12)
    assert np.all(raw['values'][:,cfg.primary_cycle,13]>=64)
    for ai,arm in enumerate(ARMS):
        for c in range(1,cfg.cycles+1):
            trace=raw['control'][ai,c-1]; mode=mode_for(arm,c,cfg)
            assert np.all(trace[:,3]>=0) and np.all(trace[:,5]>=trace[:,3]-1e-12)
            assert np.all((trace[:,4]>=0)&(trace[:,4]<=1))
            assert abs(trace[0,0]-raw['states'][ai,3*c-2,0].mean())<=1e-12
            assert abs(trace[-1,6]-raw['states'][ai,3*c-1,0].mean())<=1e-12
            if mode=='mean': assert np.max(abs(trace[:,1]))<=1e-12
            else: assert np.all(trace[:,2]==0)
            if mode=='none':
                np.testing.assert_array_equal(trace[:,0],trace[:,1])
                assert np.all(trace[:,3]==0) and np.all(trace[:,5]==0)
            elif mode=='spatial':
                np.testing.assert_allclose(trace[:,1],cfg.amplitude*raw['ancestor'].mean(),rtol=0,atol=1e-12)
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
        for ai,arm in enumerate(ARMS):
            state=common.copy()
            for c in range(1,cfg.cycles+1):
                random=generator(TAG,index,life,f'branch:{c}')
                mode=mode_for(arm,c,cfg)
                phases,mask,trace=one_cycle(state,theta,tissue,ladder,bp,random,mode,
                    ancestor if mode=='spatial' else None,cfg)
                error=max(error,compare(raw['states'][ai,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_allclose(raw['control'][ai,c-1],trace,rtol=0,atol=1e-12)
                np.testing.assert_array_equal(raw['fresh'][c-1],mask[0])
                assert meta['branch_rng'][ai][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,paired_masks_streams=True,
        common_birth=True,delayed_aliases=True,public_zero_mean_verified=True,complete_observers=True)


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
    for c in (cfg.primary_cycle,cfg.cycles):
        den=values[:,:,:,c,13]; assert np.all(den>=64)
        assert all(np.array_equal(den[:,:,0],den[:,:,i]) for i in range(5))
        for observer in ('regrown','whole'):
            score=values[:,:,:,c,12]/den if observer=='regrown' else values[:,:,:,c,0]
            for name,a,b in PAIRS:
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    primary=contrasts[0]; trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den)))
    residual=max(np.max(np.abs(controls[:,:,2,:,:,1])),
                 np.max(np.abs(controls[:,:,3,cfg.rescue_cycle-1:,:,1])))
    assert residual<=1e-12
    expected=dict(schema='l19_mean_maintenance_summary_v1',tissues=list(range(47000,47008)),arms=list(ARMS),
        metrics=list(prior.METRICS),control_metrics=list(CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=float(residual),primary=primary,contrasts=contrasts,trajectories=trajectories,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        target_disagreement=[[(b['ancestor'][l]!=b['ancestor'][l][:,(np.arange(16)-cfg.shift)%16]).mean().item()
                            for l in range(cfg.lives)] for b in blocks],
        label='MEAN_ONLY_MAINTENANCE_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_MEAN_MAINTENANCE_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_mean_maintenance_run import main
    main(default_command='audit')
