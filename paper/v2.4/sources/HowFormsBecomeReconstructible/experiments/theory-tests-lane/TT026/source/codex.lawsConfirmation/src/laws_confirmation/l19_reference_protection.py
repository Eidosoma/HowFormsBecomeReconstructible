"""D103: protect the trained R; matched wrong content and reader-off controls."""
from __future__ import annotations

from dataclasses import asdict,dataclass,replace
import importlib.util

import numpy as np

from . import l19_mean_maintenance as base
from .io import canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
native=base.base
api,context,balance=base.api,base.context,base.balance
FIELDS,METRICS,CONTROL_METRICS=base.FIELDS,base.METRICS,base.CONTROL_METRICS
RUN_ID='l19_reference_protection_v1_attempt1'
TAG='l19-reference-protection-v1'
TISSUES=tuple(range(48000,48008))
DISPOSABLE=514203
ARMS=('live_on','held_on','wrong_on','live_off','held_off','wrong_off','spatial_on')
# name, rho, gain, starting record, window mode; training always uses native parameters.
CASES=(('live_on',.002,.2,'trained','mean'),('held_on',0.,.2,'trained','mean'),
       ('wrong_on',0.,.2,'shifted','mean'),('live_off',.002,0.,'trained','mean'),
       ('held_off',0.,0.,'trained','mean'),('wrong_off',0.,0.,'shifted','mean'),
       ('spatial_on',.002,.2,'trained','spatial'))
PAIRS=(('held_on_minus_live_on',1,0),('held_on_minus_wrong_on',1,2),
       ('held_off_minus_live_off',4,3),('held_off_minus_wrong_off',4,5),
       ('held_on_minus_held_off',1,4),('wrong_on_minus_wrong_off',2,5),
       ('live_on_minus_live_off',0,3),('spatial_on_minus_live_on',6,0),
       ('spatial_on_minus_held_on',6,1))
SCIENCE=('src/laws_confirmation/l19_reference_protection.py',
    'src/laws_confirmation/l19_reference_protection_run.py',
    'scripts/audit_l19_reference_protection_outputs.py','tests/test_l19_reference_protection.py',
    'scripts/run_l19_reference_protection.sh','protocols/L19_REFERENCE_PROTECTION_V1.md')


@dataclass(frozen=True)
class Config:
    lives:int=2
    settle:int=620
    training_cycles:int=3
    cycles:int=6
    primary_cycle:int=6
    teaching:int=500
    free:int=1000
    amplitude:float=1.2
    amp_threshold:float=.2
    shift:int=8

    def __post_init__(self):
        for key in ('lives','settle','training_cycles','cycles','primary_cycle','teaching','free','shift'):
            if type(getattr(self,key)) is not int or getattr(self,key)<=0:
                raise ValueError('positive integer required: '+key)
        if not 3<=self.primary_cycle<=self.cycles or not 0<self.shift<16:
            raise ValueError('at least three boundaries and nontrivial periodic shift required')
        if not (np.isfinite(self.amplitude) and 0<self.amplitude<=2
                and np.isfinite(self.amp_threshold) and 0<self.amp_threshold<self.amplitude):
            raise ValueError('physical finite amplitude and lower observer threshold required')


CONFIG=Config()


def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def checker():
    spec=importlib.util.spec_from_file_location('d103_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def configured(initial,ctx,arm,cfg=CONFIG):
    if arm not in ARMS: raise ValueError('undeclared arm')
    if initial.shape!=(3,16,16) or initial.dtype!=np.float64 or not np.isfinite(initial).all():
        raise ValueError('complete finite float64 initial state required')
    _,rho,gain,record,mode=CASES[ARMS.index(arm)]
    state=initial.copy()
    if record=='shifted': state[2]=np.roll(initial[2],cfg.shift,axis=-1)
    changed=ctx | dict(bp=replace(ctx['bp'],rho=rho,c_m=gain))
    return state,changed,mode


def branch(initial,theta,ctx,index,life,arm,cfg=CONFIG,tag=TAG,teacher=None):
    state,changed,mode=configured(initial,ctx,arm,cfg)
    if mode=='mean' and teacher is not None: raise ValueError('teacher forbidden in reference-test arms')
    if mode=='spatial' and teacher is None: raise ValueError('positive-control teacher required')
    plan=((mode,teacher),)*cfg.cycles
    return base.branch(state,theta,changed,index,life,plan,cfg,tag)


def simulate_life(index,life,cfg=CONFIG,arms=ARMS):
    if type(life) is not int or not 0<=life<cfg.lives or not arms or any(a not in ARMS for a in arms):
        raise ValueError('declared life and nonempty arm list required')
    ctx=context(index); random=rng(index,life,'founder')
    v,ema,ref,theta,_=ctx['api']['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False)
    state=np.stack((v[0],ema[0],ref[0])); ancestor=np.sign(v[0]); ancestor[ancestor==0]=1.
    training=[state.copy()]; training_fresh=[]; training_rng=[]
    founder_rng=canonical_digest(random.bit_generator.state)
    for c in range(1,cfg.training_cycles+1):
        random=rng(index,life,f'training:{c}')
        phases,mask=native.cycle(state,theta,ctx,random,ancestor,cfg)
        state=phases[-1]; training.append(state); training_fresh.append(mask)
        training_rng.append(canonical_digest(random.bit_generator.state))
    outcomes=[branch(state,theta,ctx,index,life,arm,cfg,
        teacher=ancestor if arm=='spatial_on' else None) for arm in arms]
    for row in outcomes[1:]: np.testing.assert_array_equal(row[1],outcomes[0][1])
    states=np.stack([r[0] for r in outcomes]); fresh=outcomes[0][1]
    raw=dict(theta=theta,ancestor=ancestor,training=np.stack(training),training_fresh=np.stack(training_fresh),
        states=states,fresh=fresh,values=native.measure(states,ancestor,fresh,cfg),
        control=np.stack([r[3] for r in outcomes]))
    meta=dict(index=index,life=life,config=asdict(cfg),arms=list(arms),tag=TAG,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        founder_rng=founder_rng,training_rng=training_rng,branch_rng=[r[2] for r in outcomes],
        theta_writable=False,arm_parameters=[list(CASES[ARMS.index(a)]) for a in arms])
    return raw,meta


def execute_block(index,cfg=CONFIG):
    rows=[]; records=[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,cfg); meta['replay']=check.check_life(raw,meta,cfg)
        alias,mask,digests,trace=branch(raw['training'][-1],raw['theta'],context(index),index,life,'held_on',cfg)
        np.testing.assert_array_equal(alias,raw['states'][1]); np.testing.assert_array_equal(mask,raw['fresh'])
        np.testing.assert_array_equal(trace,raw['control'][1]); assert digests==meta['branch_rng'][1]
        meta['exact_alias_branches']=1; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def record_diagnostics(blocks,cfg=CONFIG):
    result=[]
    for b in blocks:
        lives=[]
        for life in range(cfg.lives):
            ref=b['training'][life,-1,2]; wrong=np.roll(ref,cfg.shift,axis=-1)
            ancestor=b['ancestor'][life]
            lives.append(dict(mean=float(ref.mean()),shifted_mean=float(wrong.mean()),
                rms=float(np.sqrt((ref*ref).mean())),shifted_rms=float(np.sqrt((wrong*wrong).mean())),
                sign_disagreement=float(((ref>0)!=(wrong>0)).mean()),
                spatial_mae=float(abs(ref-wrong).mean()),
                founder_sign=float(((ref>0)==(ancestor>0)).mean()),
                shifted_founder_sign=float(((wrong>0)==(ancestor>0)).mean())))
        result.append(lives)
    return result


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight complete whole tissue blocks required')
    values=np.stack([b['values'] for b in blocks]); controls=np.stack([b['control'] for b in blocks])
    if (values.shape!=(8,cfg.lives,7,cfg.cycles+1,len(METRICS))
            or controls.shape!=(8,cfg.lives,7,cfg.cycles,cfg.teaching,7)
            or not np.isfinite(values).all() or not np.isfinite(controls).all()):
        raise ValueError('complete finite paired values and controls required')
    residual=float(abs(controls[:,:,:6,:,:,1]).max())
    if residual>1e-12: raise ValueError('zero-mean control failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8))
    stats=lambda x:native.native.contrast_stats(x,samples)
    contrasts=[]
    for c in dict.fromkeys((cfg.primary_cycle,3)):
        den=values[:,:,:,c,13]
        if np.any(den<64) or any(not np.array_equal(den[:,:,0],den[:,:,a]) for a in range(7)):
            raise ValueError('paired regrowth denominator required')
        for observer,score in (('regrown',values[:,:,:,c,12]/den),('whole',values[:,:,:,c,0])):
            for name,a,b in PAIRS:
                contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a]-score[:,:,b])))
    trajectories=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            den=values[:,:,ai,c,13]
            trajectories.append(dict(arm=arm,cycle=c,whole=stats(values[:,:,ai,c,0]),
                parent=stats(values[:,:,ai,c,11]),regrown_denominators=den.astype(int).tolist(),
                regrown=None if np.any(den==0) else stats(values[:,:,ai,c,12]/den)))
    primary,content=contrasts[:2]
    return dict(schema='l19_reference_protection_summary_v1',tissues=list(TISSUES),arms=list(ARMS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,content_contrast=content,
        contrasts=contrasts,trajectories=trajectories,record_diagnostics=record_diagnostics(blocks,cfg),
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='PROTECTED_REFERENCE_RETENTION_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_PROTECTED_REFERENCE_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l19_reference_protection_v1',decision='D103',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,seed_tag=TAG,
        arms=list(ARMS),arm_parameters=[list(x) for x in CASES],fields=list(FIELDS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),
        primary='held_on-minus-live_on qualified founder fidelity, regrown>=2 since branch, cycle6',
        controller='unchanged D102 public zero mean, window-only, current V only',
        controller_state_bytes=0,reference_bytes=2048,protected_rho=0,external_backup_restoration=False,
        wrong_content='eight-column periodic translation of actual trained R once at branching',
        paired_fission_jitter_noise=True,reader_off_body_aliases=True,common_V_EMA_birth=True,
        fresh_branches=112,independent_life_replays=16,exact_alias_branches=16,
        source_anchor=dict(prior='D102',block=47000,lives=2,known_outcomes=True),
        state_atol=1e-10,metrics_atol=1e-12,mean_atol=1e-12,exact_signs=True,
        absolute_fidelity_gate=None,bootstrap_resamples=10000,independent_unit='eight equally weighted tissues',
        automatic_retry=False,automatic_follow_on=False,biological_or_carrier_only_or_necessity_claim=False)
