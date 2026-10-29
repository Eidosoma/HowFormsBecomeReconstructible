"""D102: target-blind bounded zero-mean control during D101 teaching windows."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util

import numpy as np

from . import l19_broadcast_withdrawal as base
from .io import canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
Config,CONFIG=base.Config,base.CONFIG
api,context=base.api,base.context
FIELDS,METRICS=base.FIELDS,base.METRICS
RUN_ID='l19_mean_maintenance_v1_attempt1'
TAG='l19-mean-maintenance-v1'
TISSUES=tuple(range(47000,47008))
DISPOSABLE=514202
ARMS=('continued','withdrawn','mean_early','mean_late','spatial_rescue')
CONTROL_METRICS=('pre_mean','controlled_mean','uniform_offset','action_rms',
                 'saturation_fraction','maximum_change','after_update_mean')
PAIRS=(('mean_early_minus_withdrawn',2,1),('continued_minus_withdrawn',0,1),
       ('continued_minus_mean_early',0,2),('mean_late_minus_withdrawn',3,1),
       ('spatial_rescue_minus_withdrawn',4,1),('spatial_rescue_minus_mean_late',4,3),
       ('mean_early_minus_mean_late',2,3))
SCIENCE=('src/laws_confirmation/l19_mean_maintenance.py',
    'src/laws_confirmation/l19_mean_maintenance_run.py',
    'scripts/audit_l19_mean_maintenance_outputs.py','tests/test_l19_mean_maintenance.py',
    'scripts/run_l19_mean_maintenance.sh','protocols/L19_MEAN_MAINTENANCE_V1.md')


def rng(index,life,phase,tag=TAG):
    key=hashlib.sha256(f'{tag}:{index}:{life}:{phase}'.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(key[:16],'little')))


def checker():
    spec=importlib.util.spec_from_file_location('d102_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def balance(v):
    """Only the current body is read; no target mean or ancestral information."""
    if v.shape!=(16,16) or v.dtype!=np.float64 or not np.isfinite(v).all():
        raise ValueError('one finite float64 body field required')
    offset=-float(v.mean()); result=v+offset
    if result.min() < -2. or result.max() > 2.:
        lo,hi=-2.-float(v.max()),2.-float(v.min())
        for _ in range(64):
            mid=(lo+hi)/2.
            if np.clip(v+mid,-2.,2.).mean()>0: hi=mid
            else: lo=mid
        offset=(lo+hi)/2.; result=np.clip(v+offset,-2.,2.)
    if abs(result.mean())>1e-12 or np.max(abs(result))>2.:
        raise ArithmeticError('bounded zero-mean projection failed')
    return result,offset


def schedule(arm,ancestor,cfg=CONFIG):
    if arm not in ARMS: raise ValueError('undeclared arm')
    result=[]
    for cycle in range(1,cfg.cycles+1):
        if arm=='continued' or (arm=='spatial_rescue' and cycle>=cfg.rescue_cycle):
            result.append(('spatial',ancestor.copy()))
        elif arm=='mean_early' or (arm=='mean_late' and cycle>=cfg.rescue_cycle):
            result.append(('mean',None))
        else: result.append(('none',None))
    return tuple(result)


def window(state,theta,ctx,random,mode,teacher,cfg):
    if mode not in ('none','mean','spatial'): raise ValueError('invalid control mode')
    if mode!='spatial' and teacher is not None: raise ValueError('target forbidden in blind modes')
    if mode=='spatial' and (not isinstance(teacher,np.ndarray) or teacher.shape!=(16,16)
            or teacher.dtype!=np.float64 or not np.all(np.isin(teacher,(-1.,1.)))):
        raise ValueError('complete sign template required only for spatial teaching')
    v,ema,ref=(x[None].copy() for x in state); trace=[]
    for _ in range(cfg.teaching):
        old=v[0]; offset=0.
        if mode=='mean': controlled,offset=balance(old)
        elif mode=='spatial': controlled=cfg.amplitude*teacher
        else: controlled=old.copy()
        action=controlled-old
        row=[float(old.mean()),float(controlled.mean()),offset,
             float(np.sqrt((action*action).mean())),float((abs(controlled)==2).mean()),
             float(abs(action).max())]
        v,ema,ref=ctx['api']['blueprint_step'](controlled[None],ema,ref,theta,
            ctx['tissue'],ctx['ladder'],ctx['bp'],'T',random)
        trace.append(row+[float(v.mean())])
    return np.stack((v[0],ema[0],ref[0])),np.asarray(trace)


def branch(initial,theta,ctx,index,life,plan,cfg=CONFIG,tag=TAG):
    if len(plan)!=cfg.cycles: raise ValueError('one control entry per cycle required')
    state=initial.copy(); saved=[state.copy()]; masks=[]; digests=[]; traces=[]
    for c,(mode,teacher) in enumerate(plan,1):
        random=rng(index,life,f'branch:{c}',tag)
        v,ref,fresh=ctx['api']['teaching'].fission_with_mask(state[0][None],state[2][None],ctx['tissue'],random)
        birth=np.stack((v[0],v[0],ref[0]))
        release,trace=window(birth,theta,ctx,random,mode,teacher,cfg)
        state=base.evolve(release,theta,ctx,random,cfg.free)
        saved.extend((birth,release,state)); masks.append(fresh[0]); traces.append(trace)
        digests.append(canonical_digest(random.bit_generator.state))
    return np.stack(saved),np.stack(masks),digests,np.stack(traces)


def simulate_life(index,life,cfg=CONFIG,arms=ARMS):
    if type(life) is not int or not 0<=life<cfg.lives or not arms or any(a not in ARMS for a in arms):
        raise ValueError('declared nonempty arm list and life required')
    ctx=context(index); a=ctx['api']; random=rng(index,life,'founder')
    v,ema,ref,theta,_=a['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False)
    state=np.stack((v[0],ema[0],ref[0])); ancestor=np.sign(v[0]); ancestor[ancestor==0]=1.
    training=[state.copy()]; training_fresh=[]; training_rng=[]
    founder_rng=canonical_digest(random.bit_generator.state)
    for c in range(1,cfg.training_cycles+1):
        random=rng(index,life,f'training:{c}')
        phases,mask=base.cycle(state,theta,ctx,random,ancestor,cfg)
        state=phases[-1]; training.append(state); training_fresh.append(mask)
        training_rng.append(canonical_digest(random.bit_generator.state))
    outcomes=[branch(state,theta,ctx,index,life,schedule(arm,ancestor,cfg),cfg) for arm in arms]
    for row in outcomes[1:]: np.testing.assert_array_equal(row[1],outcomes[0][1])
    states=np.stack([r[0] for r in outcomes]); fresh=outcomes[0][1]
    raw=dict(theta=theta,ancestor=ancestor,training=np.stack(training),training_fresh=np.stack(training_fresh),
        states=states,fresh=fresh,values=base.measure(states,ancestor,fresh,cfg),
        control=np.stack([r[3] for r in outcomes]))
    meta=dict(index=index,life=life,config=asdict(cfg),arms=list(arms),tag=TAG,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        founder_rng=founder_rng,training_rng=training_rng,branch_rng=[r[2] for r in outcomes],
        theta_writable=False)
    return raw,meta


def execute_block(index,cfg=CONFIG):
    rows=[]; records=[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,cfg); meta['replay']=check.check_life(raw,meta,cfg)
        alias,mask,digests,trace=branch(raw['training'][-1],raw['theta'],context(index),index,life,
                                     (('mean',None),)*cfg.cycles,cfg)
        np.testing.assert_array_equal(alias,raw['states'][2]); np.testing.assert_array_equal(mask,raw['fresh'])
        np.testing.assert_array_equal(trace,raw['control'][2]); assert digests==meta['branch_rng'][2]
        meta['exact_alias_branches']=1; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight whole tissue blocks required')
    values=np.stack([b['values'] for b in blocks]); controls=np.stack([b['control'] for b in blocks])
    if (values.shape!=(8,cfg.lives,5,cfg.cycles+1,len(METRICS))
            or controls.shape!=(8,cfg.lives,5,cfg.cycles,cfg.teaching,7)
            or not np.isfinite(values).all() or not np.isfinite(controls).all()):
        raise ValueError('complete finite paired states/controls required')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8))
    stats=lambda v:base.native.contrast_stats(v,samples)
    contrasts=[]
    for c in (cfg.primary_cycle,cfg.cycles):
        den=values[:,:,:,c,13]
        if np.any(den<64) or any(not np.array_equal(den[:,:,0],den[:,:,i]) for i in range(5)):
            raise ValueError('nonempty paired regrowth denominators required')
        for observer,score in (('regrown',values[:,:,:,c,12]/den),('whole',values[:,:,:,c,0])):
            for name,a,b in PAIRS:
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    primary=contrasts[0]; trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den)))
    residual=max(float(abs(controls[:,:,2,:,:,1]).max()),
                 float(abs(controls[:,:,3,cfg.rescue_cycle-1:,:,1]).max()))
    if residual>1e-12: raise ValueError('zero-mean manipulation failed')
    return dict(schema='l19_mean_maintenance_summary_v1',tissues=list(TISSUES),arms=list(ARMS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,contrasts=contrasts,trajectories=trajectories,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        target_disagreement=[[(b['ancestor'][l]!=np.roll(b['ancestor'][l],cfg.shift,-1)).mean().item()
                            for l in range(cfg.lives)] for b in blocks],
        label='MEAN_ONLY_MAINTENANCE_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_MEAN_MAINTENANCE_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l19_mean_maintenance_v1',decision='D102',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,seed_tag=TAG,arms=list(ARMS),
        fields=list(FIELDS),metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),
        primary='mean_early-minus-withdrawn qualified founder fidelity, regrown>=2 since branch, cycle3',
        controller='clip(V+lambda,-2,2), public mean zero, fast centering or 64 bisections, window only',
        controller_state_bytes=0,controller_reads='current V only',controller_changes='V only before native step',
        paired_fission_jitter_noise=True,fresh_branches=80,independent_life_replays=16,exact_alias_branches=16,
        source_anchor=dict(prior='D101',block=46000,lives=2,known_outcomes=True),
        state_atol=1e-10,metrics_atol=1e-12,mean_atol=1e-12,exact_signs=True,
        absolute_fidelity_gate=None,bootstrap_resamples=10000,independent_unit='eight equally weighted tissues',
        automatic_retry=False,automatic_follow_on=False,biological_or_carrier_only_or_necessity_claim=False)
