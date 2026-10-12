"""Independent D101 fission/schedule/observer/pooling, reusing D097 equations.

Never calls production D101 simulation, fission, schedule, measure or summary.
Shares parameter dataclasses and D097's already independent physics checker.
"""
from dataclasses import asdict

import numpy as np

from laws_confirmation import l15_repair_speed as native
from laws_confirmation.io import canonical_digest

physics=native.checker()
nested,compare,generator=physics.nested,physics.compare,physics.generator
TAG='l19-broadcast-withdrawal-v1'
ARMS=('continued','withdrawn','wrong','rescue')
METRICS=('body_founder_fidelity','body_wrong_fidelity','reference_founder_sign',
    'body_target_mae','reference_target_mae','vr_mae','body_mean','reference_mean',
    'body_rms','reference_rms','body_amp_fraction','parent_fidelity',
    'regrown_correct','regrown_total','regrown_parent_correct')


def free(state,theta,tissue,ladder,bp,random,steps,teacher=None,amplitude=1.2):
    v,ema,ref=(x.copy() for x in state)
    for _ in range(steps):
        if teacher is not None:
            v=amplitude*teacher.copy()
        v,ema,ref=physics.step(v,ema,ref,theta,tissue,ladder,bp.c_m,bp.rho,
                             random.standard_normal(v.shape))
    return np.stack((v,ema,ref))


def fission(state,tissue,random):
    v=state[0]; newborn=np.full_like(v,tissue.resting)
    axes=random.integers(0,2,len(v)); sides=random.integers(0,2,len(v))
    fresh=np.ones(v.shape,dtype=bool)
    for b,(axis,side) in enumerate(zip(axes,sides)):
        mask=np.zeros((16,16),dtype=bool)
        if axis==0:
            mask[8*side:8*(side+1),:]=True
        else:
            mask[:,8*side:8*(side+1)]=True
        newborn[b,mask]=v[b,mask]; fresh[b,mask]=False
    newborn=newborn+tissue.copy_jitter*random.standard_normal(v.shape)
    return np.stack((newborn,newborn.copy(),state[2].copy())),fresh


def advance(state,theta,tissue,ladder,bp,random,teacher,hold,steps,free_steps):
    birth,fresh=fission(state,tissue,random)
    release=free(birth,theta,tissue,ladder,bp,random,steps,teacher,hold)
    end=free(release,theta,tissue,ladder,bp,random,free_steps)
    return np.stack((birth,release,end)),fresh


def measurements(raw,cfg):
    ancestor=raw['ancestor']; wrong=ancestor[:,(np.arange(16)-cfg.shift)%16]
    result=[]
    for states in raw['states']:
        counts=np.zeros((16,16),dtype=np.int64); rows=[]; parent=states[0,0]
        for c in range(cfg.cycles+1):
            if c:
                counts+=raw['fresh'][c-1]
            v,_,ref=states[3*c]
            qualified=abs(v)>cfg.amp_threshold
            correct=(np.signbit(v)==np.signbit(ancestor)) & qualified
            wrong_ok=(np.signbit(v)==np.signbit(wrong)) & qualified
            parent_ok=((v>0)==(parent>0)) & qualified
            mask=counts>=2
            rows.append([correct.sum()/256,wrong_ok.sum()/256,
                np.count_nonzero((ref>0)==(ancestor>0))/256,
                abs(v-cfg.amplitude*ancestor).sum()/256,
                abs(ref-cfg.amplitude*ancestor).sum()/256,abs(v-ref).sum()/256,
                v.sum()/256,ref.sum()/256,np.sqrt((v*v).sum()/256),
                np.sqrt((ref*ref).sum()/256),qualified.sum()/256,parent_ok.sum()/256,
                np.count_nonzero(correct & mask),np.count_nonzero(mask),
                np.count_nonzero(parent_ok & mask)])
            parent=v
        result.append(rows)
    return np.asarray(result,dtype=np.float64)


def check_life(raw,meta,cfg,replay=True):
    expected_shapes=dict(theta=(16,16),ancestor=(16,16),
        training=(cfg.training_cycles+1,3,16,16),training_fresh=(cfg.training_cycles,16,16),
        states=(4,3*cfg.cycles+1,3,16,16),fresh=(cfg.cycles,16,16),
        values=(4,cfg.cycles+1,15))
    assert set(raw)==set(expected_shapes)
    for name,shape in expected_shapes.items():
        assert raw[name].shape==shape
        if name in ('fresh','training_fresh'):
            assert raw[name].dtype==np.bool_
            assert np.all(raw[name].sum(axis=(-2,-1))==128)
        else:
            assert raw[name].dtype==np.float64 and np.isfinite(raw[name]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['arms'],list(ARMS))
    assert type(meta['life']) is int and 0<=meta['life']<cfg.lives
    assert meta['theta_writable'] is False
    tissue,ladder,bp=physics.parameters(meta)
    assert np.all(np.isin(raw['ancestor'],(-1.,1.)))
    for arm in range(4):
        np.testing.assert_array_equal(raw['states'][arm,0],raw['training'][-1])
    cutoff=3*(cfg.rescue_cycle-1)+1
    np.testing.assert_array_equal(raw['states'][1,:cutoff],raw['states'][3,:cutoff])
    assert len(meta['training_rng'])==cfg.training_cycles
    assert len(meta['branch_rng'])==4 and all(len(x)==cfg.cycles for x in meta['branch_rng'])
    assert all(x==meta['branch_rng'][0] for x in meta['branch_rng'])
    values=measurements(raw,cfg)
    np.testing.assert_allclose(raw['values'],values,rtol=0,atol=1e-12)
    assert np.all(values[:,cfg.primary_cycle,13]>=64)
    error=0.
    if replay:
        index,life=meta['index'],meta['life']
        random=generator(TAG,index,life,'founder')
        state,theta=physics.settle(tissue,ladder,random,1,cfg.settle)
        error=max(compare(raw['theta'],theta),compare(raw['training'][0],state[:,0]))
        ancestor=np.sign(state[0]); ancestor[ancestor==0]=1.
        error=max(error,compare(raw['ancestor'],ancestor[0]))
        assert meta['founder_rng']==canonical_digest(random.bit_generator.state)
        for c in range(1,cfg.training_cycles+1):
            random=generator(TAG,index,life,f'training:{c}')
            phases,fresh=advance(state,theta,tissue,ladder,bp,random,ancestor,
                cfg.amplitude,cfg.teaching,cfg.free)
            state=phases[-1]
            error=max(error,compare(raw['training'][c],state[:,0]))
            np.testing.assert_array_equal(raw['training_fresh'][c-1],fresh[0])
            assert meta['training_rng'][c-1]==canonical_digest(random.bit_generator.state)
        common=state.copy()
        for ai,arm in enumerate(ARMS):
            state=common.copy()
            for c in range(1,cfg.cycles+1):
                random=generator(TAG,index,life,f'branch:{c}')
                teacher=None
                if arm=='continued' or (arm=='rescue' and c>=cfg.rescue_cycle):
                    teacher=ancestor.copy()
                elif arm=='wrong':
                    teacher=ancestor[:,:,(np.arange(16)-cfg.shift)%16].copy()
                phases,fresh=advance(state,theta,tissue,ladder,bp,random,teacher,
                    cfg.amplitude,cfg.teaching,cfg.free)
                error=max(error,compare(raw['states'][ai,3*c-2:3*c+1],phases[:,:,0]))
                np.testing.assert_array_equal(raw['fresh'][c-1],fresh[0])
                assert meta['branch_rng'][ai][c-1]==canonical_digest(random.bit_generator.state)
                state=phases[-1]
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,
        paired_masks_streams=True,common_birth=True,rescue_prebranch_alias=True,
        complete_observers=True)


def check_block(raw,meta,cfg,replay=True):
    nested(meta['config'],asdict(cfg))
    assert type(meta['index']) is int and meta['index']>=0
    assert len(meta['lives'])==cfg.lives and all(x.shape[0]==cfg.lives for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life
        assert record['exact_alias_branches']==1
        result=check_life({k:v[life] for k,v in raw.items()},record,cfg,replay)
        if replay:
            nested(record['replay'],result)
        else:
            expected=result | dict(full_life_replay=True,max_abs=record['replay']['max_abs'])
            assert 0<=expected['max_abs']<=1e-10
            nested(record['replay'],expected)
    return True


def check_source(raw,meta):
    assert set(raw)=={'theta','states','ancestor','fresh'}
    config=meta['config']; index=meta['index']
    tissue,ladder,bp=physics.parameters(meta)
    random=generator(config['trajectory_seed_tag'],'broadcast',500,index,'free',0.,0)
    state,theta=physics.settle(tissue,ladder,random,config['futures'],
                             config['settle_sweeps']+config['render_sweeps'])
    assert raw['states'].shape==(config['cycles']+1,3,config['futures'],16,16)
    assert raw['fresh'].shape==(config['cycles'],config['futures'],16,16)
    assert raw['fresh'].dtype==np.bool_ and len(meta['rng'])==config['cycles']+1
    error=max(compare(raw['theta'],theta),compare(raw['states'][0],state))
    ancestor=np.sign(state[0]); ancestor[ancestor==0]=1.
    error=max(error,compare(raw['ancestor'],ancestor))
    assert meta['rng'][0]==canonical_digest(random.bit_generator.state)
    counts=np.zeros(ancestor.shape,dtype=np.int32); tail=[]
    for c in range(config['cycles']):
        phases,fresh=advance(state,theta,tissue,ladder,bp,random,ancestor,
                            config['teach_hold'],500,config['free_sweeps'])
        state=phases[-1]; counts+=fresh
        error=max(error,compare(raw['states'][c+1],state))
        np.testing.assert_array_equal(raw['fresh'][c],fresh)
        assert meta['rng'][c+1]==canonical_digest(random.bit_generator.state)
        if c>=config['cycles']-3:
            ok=((state[0]>0)==(ancestor>0)) & (abs(state[0])>config['amp_threshold'])
            vals=[ok[b][counts[b]>=2].mean() for b in range(config['futures']) if (counts[b]>=2).any()]
            if vals: tail.append(float(np.mean(vals)))
    signs=state[0]>0
    divergence=float(np.mean([(signs[a]!=signs[b]).mean() for a in range(len(signs))
                             for b in range(a+1,len(signs))]))
    nested(meta['result'],dict(tissue=index,arm='broadcast',T=500,r_mode='free',sigma_r=0.,
        fidelity=float(np.mean(tail)) if tail else None,divergence=divergence,barcode=None))
    return dict(full_source_replay=True,max_abs=error,exact_signs=True,metrics_pass=True)


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    values=np.asarray([[measurements({k:v[l] for k,v in b.items()},cfg)
                        for l in range(cfg.lives)] for b in blocks])
    samples=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8))
    def stats(lives):
        means=np.array([v.mean() for v in lives])
        result=dict(mean=float(means.mean()),block_means=means.tolist(),life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(means[samples].mean(axis=1),[.025,.975]).tolist())
        for prefix,x in (('block_',means),('life_',lives)):
            result[prefix+'positive']=int((x>1e-12).sum())
            result[prefix+'negative']=int((x< -1e-12).sum())
            result[prefix+'tied']=int((abs(x)<=1e-12).sum())
        return result
    contrasts=[]
    for c in (cfg.primary_cycle,cfg.cycles):
        den=values[:,:,:,c,13]
        assert np.all(den>=64)
        assert all(np.array_equal(den[:,:,0],den[:,:,a]) for a in range(4))
        for observer in ('regrown','whole'):
            score=values[:,:,:,c,12]/den if observer=='regrown' else values[:,:,:,c,0]
            for name,a,b in (('continued_minus_withdrawn',0,1),('continued_minus_wrong',0,2),
                             ('rescue_minus_withdrawn',3,1)):
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    primary=contrasts[0]
    trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if (den==0).any() else stats(values[:,:,ai,c,12]/den)))
    expected=dict(schema='l19_broadcast_withdrawal_summary_v1',tissues=list(range(46000,46008)),
        arms=list(ARMS),metrics=list(METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),primary=primary,contrasts=contrasts,
        trajectories=trajectories,training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        target_disagreement=[[(b['ancestor'][l]!=b['ancestor'][l][:,(np.arange(16)-cfg.shift)%16]).mean().item()
                             for l in range(cfg.lives)] for b in blocks],
        label='CONTINUED_BROADCAST_ADVANTAGE' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_CONTINUED_ADVANTAGE',blocks=8,lives_per_block=cfg.lives,
        secondary_intervals_multiplicity_adjusted=False,absolute_fidelity_gate=None)
    nested(summary,expected)
    return True


if __name__=='__main__':
    from laws_confirmation.l19_broadcast_withdrawal_run import main
    main(default_command='audit')
