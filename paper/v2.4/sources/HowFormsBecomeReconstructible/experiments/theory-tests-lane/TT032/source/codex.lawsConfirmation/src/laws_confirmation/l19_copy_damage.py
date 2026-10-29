"""D104: address-copy errors in protected R, with explicit external rescue."""
from __future__ import annotations

from dataclasses import asdict,dataclass,replace
import importlib.util

import numpy as np

from . import l19_reference_protection as base
from .io import canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
mean,native=base.base,base.native
api,context,balance=base.api,base.context,base.balance
FIELDS,METRICS,CONTROL_METRICS=base.FIELDS,base.METRICS,base.CONTROL_METRICS
RUN_ID='l19_copy_damage_v1_attempt1'
TAG='l19-copy-damage-v1'
TISSUES=tuple(range(49000,49008))
DISPOSABLE=514204
ARMS=('clean_on','damaged_on','rescue_on','clean_off','damaged_off','rescue_off')
# name, reader gain, apply address swaps, allow one external restoration
CASES=(('clean_on',.2,False,False),('damaged_on',.2,True,False),
       ('rescue_on',.2,True,True),('clean_off',0.,False,False),
       ('damaged_off',0.,True,False),('rescue_off',0.,True,True))
PAIRS=(('clean_on_minus_damaged_on',0,1),('rescue_on_minus_damaged_on',2,1),
       ('clean_on_minus_rescue_on',0,2),('clean_off_minus_damaged_off',3,4),
       ('rescue_off_minus_damaged_off',5,4),('clean_on_minus_clean_off',0,3),
       ('damaged_on_minus_damaged_off',1,4),('rescue_on_minus_rescue_off',2,5))
SCIENCE=('src/laws_confirmation/l19_copy_damage.py',
    'src/laws_confirmation/l19_copy_damage_run.py','scripts/audit_l19_copy_damage_outputs.py',
    'tests/test_l19_copy_damage.py','scripts/run_l19_copy_damage.sh','protocols/L19_COPY_DAMAGE_V1.md')


@dataclass(frozen=True)
class Config(base.Config):
    rescue_cycle:int=4
    damage_pairs:int=32

    def __post_init__(self):
        super().__post_init__()
        if type(self.rescue_cycle) is not int or not 4<=self.rescue_cycle<=self.cycles:
            raise ValueError('at least three pre-rescue boundaries required')
        if type(self.damage_pairs) is not int or not 1<=self.damage_pairs<=128:
            raise ValueError('one to 128 disjoint address pairs required')


CONFIG=Config()


def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def checker():
    spec=importlib.util.spec_from_file_location('d104_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def copy_map(random,cfg=CONFIG):
    chosen=random.choice(256,2*cfg.damage_pairs,replace=False)
    mapping=np.arange(256,dtype=np.int64)
    mapping[chosen[::2]]=chosen[1::2]; mapping[chosen[1::2]]=chosen[::2]
    return mapping


def copy_reference(ref,mapping,damaged):
    if (not isinstance(ref,np.ndarray) or ref.shape!=(16,16) or ref.dtype!=np.float64
            or not np.isfinite(ref).all() or type(damaged) is not bool):
        raise ValueError('finite float64 record and explicit damage flag required')
    if (not isinstance(mapping,np.ndarray) or mapping.shape!=(256,) or mapping.dtype!=np.int64
            or not np.array_equal(np.sort(mapping),np.arange(256))
            or not np.array_equal(mapping[mapping],np.arange(256))):
        raise ValueError('bijective involutive address map required')
    return ref.reshape(-1)[mapping].reshape(16,16).copy() if damaged else ref.copy()


def branch(initial,theta,ctx,index,life,arm,cfg=CONFIG,tag=TAG,backup=None):
    if arm not in ARMS: raise ValueError('undeclared arm')
    _,gain,damaged,rescue=CASES[ARMS.index(arm)]
    if not rescue and backup is not None: raise ValueError('backup forbidden outside rescue arms')
    if rescue and (not isinstance(backup,np.ndarray) or backup.shape!=(16,16)
            or backup.dtype!=np.float64 or not np.isfinite(backup).all()):
        raise ValueError('explicit external finite float64 backup required')
    if (initial.shape!=(3,16,16) or initial.dtype!=np.float64 or not np.isfinite(initial).all()):
        raise ValueError('complete finite float64 initial state required')
    changed=ctx | dict(bp=replace(ctx['bp'],rho=0.,c_m=gain))
    state=initial.copy(); saved=[state.copy()]; masks=[]; digests=[]; traces=[]
    maps=[]; copy_digests=[]; pre_restore=[]
    for c in range(1,cfg.cycles+1):
        random=rng(index,life,f'branch:{c}',tag)
        errors=rng(index,life,f'copy:{c}',tag); mapping=copy_map(errors,cfg)
        v,ref,fresh=ctx['api']['teaching'].fission_with_mask(state[0][None],state[2][None],ctx['tissue'],random)
        copied=copy_reference(ref[0],mapping,damaged); pre_restore.append(copied.copy())
        if rescue and c==cfg.rescue_cycle: copied=backup.copy()
        birth=np.stack((v[0],v[0],copied))
        release,trace=mean.window(birth,theta,changed,random,'mean',None,cfg)
        state=native.evolve(release,theta,changed,random,cfg.free)
        saved.extend((birth,release,state)); masks.append(fresh[0]); traces.append(trace); maps.append(mapping)
        digests.append(canonical_digest(random.bit_generator.state))
        copy_digests.append(canonical_digest(errors.bit_generator.state))
    return (np.stack(saved),np.stack(masks),digests,np.stack(traces),np.stack(maps),
            copy_digests,np.stack(pre_restore))


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
    backup=state[2].copy(); backup.setflags(write=False)
    outcomes=[branch(state,theta,ctx,index,life,arm,cfg,
        backup=backup if CASES[ARMS.index(arm)][3] else None) for arm in arms]
    for row in outcomes[1:]:
        np.testing.assert_array_equal(row[1],outcomes[0][1])
        np.testing.assert_array_equal(row[4],outcomes[0][4])
    states=np.stack([r[0] for r in outcomes]); fresh=outcomes[0][1]
    raw=dict(theta=theta,ancestor=ancestor,training=np.stack(training),training_fresh=np.stack(training_fresh),
        states=states,fresh=fresh,values=native.measure(states,ancestor,fresh,cfg),
        control=np.stack([r[3] for r in outcomes]),copy_map=outcomes[0][4],
        pre_restore=np.stack([r[6] for r in outcomes]))
    meta=dict(index=index,life=life,config=asdict(cfg),arms=list(arms),tag=TAG,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        founder_rng=founder_rng,training_rng=training_rng,branch_rng=[r[2] for r in outcomes],
        copy_rng=[r[5] for r in outcomes],theta_writable=False,
        arm_parameters=[list(CASES[ARMS.index(a)]) for a in arms])
    return raw,meta


def execute_block(index,cfg=CONFIG):
    rows=[]; records=[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,cfg); meta['replay']=check.check_life(raw,meta,cfg)
        alias=branch(raw['training'][-1],raw['theta'],context(index),index,life,'damaged_on',cfg)
        for position,key in ((0,'states'),(3,'control'),(6,'pre_restore')):
            np.testing.assert_array_equal(alias[position],raw[key][1])
        np.testing.assert_array_equal(alias[1],raw['fresh']); np.testing.assert_array_equal(alias[4],raw['copy_map'])
        assert alias[2]==meta['branch_rng'][1] and alias[5]==meta['copy_rng'][1]
        meta['exact_alias_branches']=1; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def record_diagnostics(blocks,cfg,stats):
    refs=np.stack([b['states'][:,:,::3,2] for b in blocks])
    trained=np.stack([b['training'][:,-1,2] for b in blocks]); ancestor=np.stack([b['ancestor'] for b in blocks])
    pre=np.stack([b['pre_restore'] for b in blocks]); rows=[]
    for ai,arm in enumerate(ARMS):
        for c in range(cfg.cycles+1):
            ref=refs[:,:,ai,c]
            rows.append(dict(arm=arm,cycle=c,
                founder_sign=stats(((ref>0)==(ancestor>0)).mean(axis=(-2,-1))),
                trained_sign=stats(((ref>0)==(trained>0)).mean(axis=(-2,-1))),
                trained_mae=stats(abs(ref-trained).mean(axis=(-2,-1))),
                mean=stats(ref.mean(axis=(-2,-1))),rms=stats(np.sqrt((ref*ref).mean(axis=(-2,-1)))),
                copy_sign_change=None if c==0 else stats(((pre[:,:,ai,c-1]>0)!=
                    (refs[:,:,ai,c-1]>0)).mean(axis=(-2,-1)))))
    return rows


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight complete whole tissue blocks required')
    values=np.stack([b['values'] for b in blocks]); controls=np.stack([b['control'] for b in blocks])
    if (values.shape!=(8,cfg.lives,6,cfg.cycles+1,len(METRICS))
            or controls.shape!=(8,cfg.lives,6,cfg.cycles,cfg.teaching,7)
            or not np.isfinite(values).all() or not np.isfinite(controls).all()):
        raise ValueError('complete finite paired values and controls required')
    residual=float(abs(controls[:,:,:,:,:,1]).max())
    if residual>1e-12: raise ValueError('zero-mean control failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8))
    stats=lambda x:native.native.contrast_stats(x,samples)
    contrasts=[]
    for c in dict.fromkeys((cfg.primary_cycle,3,cfg.rescue_cycle)):
        den=values[:,:,:,c,13]
        if np.any(den<64) or any(not np.array_equal(den[:,:,0],den[:,:,a]) for a in range(6)):
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
    primary,rescue=contrasts[:2]
    return dict(schema='l19_copy_damage_summary_v1',tissues=list(TISSUES),arms=list(ARMS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),cycles=list(range(cfg.cycles+1)),
        cell_means=values.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,rescue_contrast=rescue,
        contrasts=contrasts,trajectories=trajectories,record_diagnostics=record_diagnostics(blocks,cfg,stats),
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='COPY_ADDRESS_DAMAGE_COST' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_COPY_ADDRESS_DAMAGE_COST',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False)


def contract():
    return dict(schema='l19_copy_damage_v1',decision='D104',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,seed_tag=TAG,
        arms=list(ARMS),arm_parameters=[list(x) for x in CASES],fields=list(FIELDS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),
        primary='clean_on-minus-damaged_on qualified founder fidelity, regrown>=2 since branch, cycle6',
        controller='unchanged D102 public zero mean, window-only, current V only',
        controller_state_bytes=0,reference_bytes=2048,protected_rho=0,
        copy_damage='32 disjoint random swaps of 64 distinct spatial addresses, each fission, separate RNG',
        rescue='one external restoration of common trained R after cycle4 copy damage; further damage continues',
        rescue_backup_bytes=2048,rescue_is_autonomous=False,amplitude_mean_multiset_preserved=True,
        paired_fission_jitter_noise=True,reader_off_body_aliases=True,common_V_EMA_R_branch=True,
        fresh_branches=96,independent_life_replays=16,exact_alias_branches=16,
        source_anchor=dict(prior='D103',block=48000,lives=2,known_outcomes=True),
        state_atol=1e-10,metrics_atol=1e-12,mean_atol=1e-12,exact_signs=True,
        absolute_fidelity_gate=None,bootstrap_resamples=10000,independent_unit='eight equally weighted tissues',
        automatic_retry=False,automatic_follow_on=False,biological_or_carrier_only_or_necessity_claim=False)
