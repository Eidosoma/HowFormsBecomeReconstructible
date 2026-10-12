"""D105: local target-blind R repair, clean and wrong-content controls."""
from __future__ import annotations

from dataclasses import asdict,dataclass,replace
import importlib.util

import numpy as np

from . import l19_copy_damage as base
from .io import canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
mean,native=base.mean,base.native
api,context,balance=base.api,base.context,base.balance
FIELDS,METRICS,CONTROL_METRICS=base.FIELDS,base.METRICS,base.CONTROL_METRICS
RUN_ID='l19_internal_repair_v1_attempt1'
TAG='l19-internal-repair-v1'
TISSUES=tuple(range(50000,50008))
DISPOSABLE=514205
ARMS=('clean_on','damaged_on','repaired_on','clean_repaired_on',
      'wrong_on','wrong_repaired_on','damaged_off','repaired_off')
# name, gain, copy damage, local repair, initial R
CASES=(('clean_on',.2,False,False,'trained'),('damaged_on',.2,True,False,'trained'),
    ('repaired_on',.2,True,True,'trained'),('clean_repaired_on',.2,False,True,'trained'),
    ('wrong_on',.2,True,False,'shifted'),('wrong_repaired_on',.2,True,True,'shifted'),
    ('damaged_off',0.,True,False,'trained'),('repaired_off',0.,True,True,'trained'))
CONTENT_METRICS=('own_body_fidelity','own_regrown_correct','own_reference_sign','incoming_R_mae',
    'detail_total','detail_body_correct','detail_reference_correct','canonical_body_fidelity','own_minus_other_body')
# Coefficients act on arm-specific (trained or shifted) target fidelity.
CONTRASTS=(('repaired_minus_damaged',(0,-1,1,0,0,0,0,0)),
    ('clean_repaired_minus_clean',(-1,0,0,1,0,0,0,0)),
    ('damage_specific_repair_interaction',(1,-1,1,-1,0,0,0,0)),
    ('wrong_repaired_minus_wrong',(0,0,0,0,-1,1,0,0)),
    ('repaired_off_minus_damaged_off',(0,0,0,0,0,0,-1,1)),
    ('repaired_on_minus_off',(0,0,1,0,0,0,0,-1)),
    ('damaged_on_minus_off',(0,1,0,0,0,0,-1,0)),
    ('clean_minus_repaired',(1,0,-1,0,0,0,0,0)))
SCIENCE=('src/laws_confirmation/l19_internal_repair.py','src/laws_confirmation/l19_internal_repair_run.py',
    'scripts/audit_l19_internal_repair_outputs.py','tests/test_l19_internal_repair.py',
    'scripts/run_l19_internal_repair.sh','protocols/L19_INTERNAL_REPAIR_V1.md')


@dataclass(frozen=True)
class Config(base.base.Config):
    damage_pairs:int=32

    def __post_init__(self):
        super().__post_init__()
        if type(self.damage_pairs) is not int or not 1<=self.damage_pairs<=128:
            raise ValueError('one to 128 disjoint address pairs required')


CONFIG=Config()


def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def checker():
    spec=importlib.util.spec_from_file_location('d105_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def repair(ref):
    """One synchronous periodic 3x3 median pass; current R is the only input."""
    if (not isinstance(ref,np.ndarray) or ref.shape!=(16,16) or ref.dtype!=np.float64
            or not np.isfinite(ref).all()):
        raise ValueError('current finite float64 16x16 record required')
    neighbors=np.stack([np.roll(ref,(dy,dx),axis=(0,1)) for dy in (-1,0,1) for dx in (-1,0,1)])
    return np.median(neighbors,axis=0)


def branch(initial,theta,ctx,index,life,arm,cfg=CONFIG,tag=TAG):
    if arm not in ARMS: raise ValueError('undeclared arm')
    if initial.shape!=(3,16,16) or initial.dtype!=np.float64 or not np.isfinite(initial).all():
        raise ValueError('complete finite float64 initial state required')
    _,gain,damaged,repaired,record=CASES[ARMS.index(arm)]
    changed=ctx | dict(bp=replace(ctx['bp'],rho=0.,c_m=gain))
    state=initial.copy()
    if record=='shifted': state[2]=np.roll(state[2],cfg.shift,axis=-1)
    saved=[state.copy()]; masks=[]; digests=[]; traces=[]; maps=[]; copy_digests=[]; pre_repair=[]
    for c in range(1,cfg.cycles+1):
        random=rng(index,life,f'branch:{c}',tag); errors=rng(index,life,f'copy:{c}',tag)
        mapping=base.copy_map(errors,cfg)
        v,ref,fresh=ctx['api']['teaching'].fission_with_mask(state[0][None],state[2][None],ctx['tissue'],random)
        copied=base.copy_reference(ref[0],mapping,damaged); pre_repair.append(copied.copy())
        updated=repair(copied) if repaired else copied.copy()
        birth=np.stack((v[0],v[0],updated))
        release,trace=mean.window(birth,theta,changed,random,'mean',None,cfg)
        state=native.evolve(release,theta,changed,random,cfg.free)
        saved.extend((birth,release,state)); masks.append(fresh[0]); traces.append(trace); maps.append(mapping)
        digests.append(canonical_digest(random.bit_generator.state))
        copy_digests.append(canonical_digest(errors.bit_generator.state))
    return (np.stack(saved),np.stack(masks),digests,np.stack(traces),np.stack(maps),
        copy_digests,np.stack(pre_repair))


def content_measure(states,ancestor,fresh,arms,cfg):
    """Observer only; fixed detail mask distinguishes founder from public half-sheet."""
    canonical=np.full((16,16),-1.); canonical[:,:8]=1.
    rows=[]
    for ai,arm in enumerate(arms):
        shifted=CASES[ARMS.index(arm)][4]=='shifted'
        own=np.roll(ancestor,cfg.shift,axis=-1) if shifted else ancestor
        other=ancestor if shifted else np.roll(ancestor,cfg.shift,axis=-1)
        generic=np.roll(canonical,cfg.shift,axis=-1) if shifted else canonical
        detail=(own>0)!=(generic>0); incoming=states[ai,0,2]; counts=np.zeros((16,16),dtype=int)
        scores=[]
        for c in range(cfg.cycles+1):
            if c: counts+=fresh[c-1]
            v,_,ref=states[ai,3*c]; qualified=abs(v)>cfg.amp_threshold
            correct=((v>0)==(own>0)) & qualified
            other_correct=((v>0)==(other>0)) & qualified
            scores.append([correct.mean(),(correct & (counts>=2)).sum(),((ref>0)==(own>0)).mean(),
                abs(ref-incoming).mean(),detail.sum(),(correct & detail).sum(),
                (((ref>0)==(own>0)) & detail).sum(),(((v>0)==(generic>0)) & qualified).mean(),
                correct.mean()-other_correct.mean()])
        rows.append(scores)
    return np.asarray(rows,dtype=np.float64)


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
    outcomes=[branch(state,theta,ctx,index,life,arm,cfg) for arm in arms]
    for row in outcomes[1:]:
        np.testing.assert_array_equal(row[1],outcomes[0][1]); np.testing.assert_array_equal(row[4],outcomes[0][4])
    states=np.stack([r[0] for r in outcomes]); fresh=outcomes[0][1]
    raw=dict(theta=theta,ancestor=ancestor,training=np.stack(training),training_fresh=np.stack(training_fresh),
        states=states,fresh=fresh,values=native.measure(states,ancestor,fresh,cfg),
        control=np.stack([r[3] for r in outcomes]),copy_map=outcomes[0][4],
        pre_repair=np.stack([r[6] for r in outcomes]),content=content_measure(states,ancestor,fresh,arms,cfg))
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
        alias=branch(raw['training'][-1],raw['theta'],context(index),index,life,'repaired_on',cfg)
        for position,key in ((0,'states'),(3,'control'),(6,'pre_repair')):
            np.testing.assert_array_equal(alias[position],raw[key][2])
        np.testing.assert_array_equal(alias[1],raw['fresh']); np.testing.assert_array_equal(alias[4],raw['copy_map'])
        assert alias[2]==meta['branch_rng'][2] and alias[5]==meta['copy_rng'][2]
        meta['exact_alias_branches']=1; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight complete whole tissue blocks required')
    values=np.stack([b['values'] for b in blocks]); controls=np.stack([b['control'] for b in blocks])
    content=np.stack([b['content'] for b in blocks])
    if (values.shape!=(8,cfg.lives,8,cfg.cycles+1,15) or content.shape!=(8,cfg.lives,8,cfg.cycles+1,9)
            or controls.shape!=(8,cfg.lives,8,cfg.cycles,cfg.teaching,7)
            or not all(np.isfinite(x).all() for x in (values,content,controls))):
        raise ValueError('complete finite paired values, content and controls required')
    residual=float(abs(controls[:,:,:,:,:,1]).max())
    if residual>1e-12: raise ValueError('zero-mean control failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8))
    stats=lambda x:native.native.contrast_stats(x,samples)
    contrasts=[]
    for c in dict.fromkeys((cfg.primary_cycle,3)):
        den=values[:,:,:,c,13]
        if np.any(den<64) or any(not np.array_equal(den[:,:,0],den[:,:,a]) for a in range(8)):
            raise ValueError('paired regrowth denominator required')
        for observer,score in (('regrown',content[:,:,:,c,1]/den),('whole',content[:,:,:,c,0])):
            for name,coefs in CONTRASTS:
                effect=sum(coef*score[:,:,ai] for ai,coef in enumerate(coefs) if coef)
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
    primary=contrasts[0]
    return dict(schema='l19_internal_repair_summary_v1',tissues=list(TISSUES),arms=list(ARMS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),content_metrics=list(CONTENT_METRICS),
        cycles=list(range(cfg.cycles+1)),cell_means=values.mean(axis=(0,1)).tolist(),
        content_means=content.mean(axis=(0,1)).tolist(),window_control_means=controls.mean(axis=(0,1,4)).tolist(),
        max_controlled_mean_residual=residual,primary=primary,contrasts=contrasts,trajectories=trajectories,
        training_specificity=stats(values[:,:,0,0,0]-values[:,:,0,0,1]),
        label='LOCAL_REPAIR_BODY_BENEFIT' if primary['pointwise_block_bootstrap_95'][0]>0
              else 'NO_QUALIFIED_LOCAL_REPAIR_BODY_BENEFIT',
        blocks=8,lives_per_block=cfg.lives,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False,detail_missing_policy='null aggregate if any life has zero details; no exclusions')


def contract():
    return dict(schema='l19_internal_repair_v1',decision='D105',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,seed_tag=TAG,
        arms=list(ARMS),arm_parameters=[list(x) for x in CASES],fields=list(FIELDS),
        metrics=list(METRICS),control_metrics=list(CONTROL_METRICS),content_metrics=list(CONTENT_METRICS),
        primary='repaired_on-minus-damaged_on qualified founder fidelity, regrown>=2 since branch, cycle6',
        controller='unchanged D102 public zero mean, window-only, current V only',
        controller_state_bytes=0,reference_bytes=2048,protected_rho=0,repair_persistent_extra_bytes=0,
        repair='one synchronous periodic 3x3 median pass of current R after each copying boundary',
        repair_spatial_prior='isotropic 3x3 local smoothness; no specific coordinates or target',
        repair_preserves_mean_rms_multiset=False,backup_bytes=0,body_or_observer_read_by_repair=False,
        copy_damage='unchanged D104 32 disjoint swaps, separate paired RNG',
        wrong_content='eight-column translation of actual trained R once at branching',
        detail_observer='settled founder cells differing from public launch half-sheet, translated with wrong target',
        paired_fission_jitter_noise=True,reader_off_body_aliases=True,common_V_EMA_branch=True,
        fresh_branches=128,independent_life_replays=16,exact_alias_branches=16,
        source_anchor=dict(prior='D104',block=49000,lives=2,known_outcomes=True),
        state_atol=1e-10,metrics_atol=1e-12,mean_atol=1e-12,exact_signs=True,
        absolute_fidelity_gate=None,bootstrap_resamples=10000,independent_unit='eight equally weighted tissues',
        automatic_retry=False,automatic_follow_on=False,biological_or_carrier_only_or_necessity_claim=False)
