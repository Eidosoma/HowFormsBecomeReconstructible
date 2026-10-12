"""D103 independent reference interventions, invariants and paired pooling.

Reuse the independently restated D102 balance/cycle and D097 physics, not
D103 production configuration, branch simulation, diagnostics or summary.
"""
from dataclasses import asdict,replace

import numpy as np

from laws_confirmation import l19_mean_maintenance as prior
from laws_confirmation.io import canonical_digest

mean=prior.checker(); old=mean.old; physics=mean.physics
nested,compare,generator=mean.nested,mean.compare,mean.generator
TAG='l19-reference-protection-v1'
ARMS=('live_on','held_on','wrong_on','live_off','held_off','wrong_off','spatial_on')
CASES=(('live_on',.002,.2,'trained','mean'),('held_on',0.,.2,'trained','mean'),
       ('wrong_on',0.,.2,'shifted','mean'),('live_off',.002,0.,'trained','mean'),
       ('held_off',0.,0.,'trained','mean'),('wrong_off',0.,0.,'shifted','mean'),
       ('spatial_on',.002,.2,'trained','spatial'))
PAIRS=(('held_on_minus_live_on',1,0),('held_on_minus_wrong_on',1,2),
       ('held_off_minus_live_off',4,3),('held_off_minus_wrong_off',4,5),
       ('held_on_minus_held_off',1,4),('wrong_on_minus_wrong_off',2,5),
       ('live_on_minus_live_off',0,3),('spatial_on_minus_live_on',6,0),
       ('spatial_on_minus_held_on',6,1))


def shifted(ref,cfg): return ref[:,(np.arange(16)-cfg.shift)%16].copy()


def check_life(raw,meta,cfg,replay=True):
    shapes=dict(theta=(16,16),ancestor=(16,16),training=(cfg.training_cycles+1,3,16,16),
        training_fresh=(cfg.training_cycles,16,16),states=(7,3*cfg.cycles+1,3,16,16),
        fresh=(cfg.cycles,16,16),values=(7,cfg.cycles+1,15),control=(7,cfg.cycles,cfg.teaching,7))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key in ('fresh','training_fresh'):
            assert raw[key].dtype==np.bool_ and np.all(raw[key].sum(axis=(-2,-1))==128)
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['arms'],list(ARMS))
    nested(meta['arm_parameters'],[list(x) for x in CASES]); assert meta['tag']==TAG
    assert type(meta['life']) is int and 0<=meta['life']<cfg.lives and meta['theta_writable'] is False
    tissue,ladder,bp=physics.parameters(meta)
    assert np.all(np.isin(raw['ancestor'],(-1.,1.)))
    initial=raw['training'][-1]; correct=initial[2]; wrong=shifted(correct,cfg)
    assert not np.array_equal(correct,wrong),'declared wrong record must differ'
    np.testing.assert_array_equal(np.sort(wrong,axis=None),np.sort(correct,axis=None))
    assert abs(correct.mean()-wrong.mean())<=1e-12
    assert abs((correct*correct).mean()-(wrong*wrong).mean())<=1e-12
    for ai in range(7):
        np.testing.assert_array_equal(raw['states'][ai,0,:2],initial[:2])
        expected=wrong if ai in (2,5) else correct
        np.testing.assert_array_equal(raw['states'][ai,0,2],expected)
        if ai in (1,2,4,5):
            np.testing.assert_array_equal(raw['states'][ai,:,2],
                np.broadcast_to(expected,(3*cfg.cycles+1,16,16)))
    for ai in (4,5):
        np.testing.assert_array_equal(raw['states'][ai,:,:2],raw['states'][3,:,:2])
        np.testing.assert_array_equal(raw['control'][ai],raw['control'][3])
    assert len(meta['training_rng'])==cfg.training_cycles and len(meta['branch_rng'])==7
    assert all(len(x)==cfg.cycles and x==meta['branch_rng'][0] for x in meta['branch_rng'])
    np.testing.assert_allclose(raw['values'],old.measurements(raw,cfg),rtol=0,atol=1e-12)
    assert np.all(raw['values'][:,cfg.primary_cycle,13]>=64)
    for ai in range(7):
        for c in range(1,cfg.cycles+1):
            trace=raw['control'][ai,c-1]
            assert np.all(trace[:,3]>=0) and np.all(trace[:,5]>=trace[:,3]-1e-12)
            assert np.all((trace[:,4]>=0)&(trace[:,4]<=1))
            assert abs(trace[0,0]-raw['states'][ai,3*c-2,0].mean())<=1e-12
            assert abs(trace[-1,6]-raw['states'][ai,3*c-1,0].mean())<=1e-12
            if ai<6: assert np.max(abs(trace[:,1]))<=1e-12
            else:
                assert np.all(trace[:,2]==0)
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
        for ai,(_,rho,gain,record,mode) in enumerate(CASES):
            state=common.copy()
            if record=='shifted': state[2,0]=shifted(common[2,0],cfg)
            changed=replace(bp,rho=rho,c_m=gain)
            for c in range(1,cfg.cycles+1):
                random=generator(TAG,index,life,f'branch:{c}')
                phases,mask,trace=mean.one_cycle(state,theta,tissue,ladder,changed,random,mode,
                    ancestor if mode=='spatial' else None,cfg)
                error=max(error,compare(raw['states'][ai,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_allclose(raw['control'][ai,c-1],trace,rtol=0,atol=1e-12)
                np.testing.assert_array_equal(raw['fresh'][c-1],mask[0])
                assert meta['branch_rng'][ai][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,paired_masks_streams=True,
        common_V_EMA=True,protected_R_unchanged=True,wrong_R_matched=True,reader_off_body_aliases=True,
        public_zero_mean_verified=True,complete_observers=True)


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
    for c in list(dict.fromkeys([cfg.primary_cycle,3])):
        den=values[:,:,:,c,13]; assert np.all(den>=64)
        assert all(np.array_equal(den[:,:,0],den[:,:,a]) for a in range(7))
        for observer in ('regrown','whole'):
            score=values[:,:,:,c,12]/den if observer=='regrown' else values[:,:,:,c,0]
            for name,a,b in PAIRS:
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den)))
    diagnostics=[]
    for block in blocks:
        row=[]
        for life in range(cfg.lives):
            ref=block['training'][life,-1,2]; wrong=shifted(ref,cfg); ancestor=block['ancestor'][life]
            row.append(dict(mean=float(ref.sum()/256),shifted_mean=float(wrong.sum()/256),
                rms=float(np.sqrt((ref**2).sum()/256)),shifted_rms=float(np.sqrt((wrong**2).sum()/256)),
                sign_disagreement=float(np.count_nonzero((ref>0)!=(wrong>0))/256),
                spatial_mae=float(abs(ref-wrong).sum()/256),
                founder_sign=float(np.count_nonzero((ref>0)==(ancestor>0))/256),
                shifted_founder_sign=float(np.count_nonzero((wrong>0)==(ancestor>0))/256)))
        diagnostics.append(row)
    residual=float(np.max(np.abs(controls[:,:,:6,:,:,1]))); assert residual<=1e-12
    primary,content=contrasts[:2]
    expected=dict(schema='l19_reference_protection_summary_v1',tissues=list(range(48000,48008)),arms=list(ARMS),
        metrics=list(prior.METRICS),control_metrics=list(prior.CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,content_contrast=content,
        contrasts=contrasts,trajectories=trajectories,record_diagnostics=diagnostics,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='PROTECTED_REFERENCE_RETENTION_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_PROTECTED_REFERENCE_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_reference_protection_run import main
    main(default_command='audit')
