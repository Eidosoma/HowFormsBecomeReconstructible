"""D106: native landmark writing, qualified reading, then fixed D105 repair."""
from __future__ import annotations

from dataclasses import asdict,replace
import importlib.util

import numpy as np

from . import l19_internal_repair as base
from .io import canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
api,context,native=base.api,base.context,base.native
repair,balance=base.repair,base.balance
Config,CONFIG=base.Config,base.CONFIG
RUN_ID='l19_written_landmarks_v1_attempt1'
QUAL_ID='l19_written_landmarks_qualification_v1_attempt1'
TAG='l19-written-landmarks-v1'
TISSUES=tuple(range(51000,51008))
QUAL_TISSUES=tuple(range(51500,51508))
DISPOSABLE=514206
QUAL_ARMS=('clean_on','clean_off')
MAIN_ARMS=('clean_on','damaged_on','repaired_on','clean_repaired_on','damaged_off','repaired_off')
CASES=(('clean_on',.2,False,False),('clean_off',0.,False,False),
    ('damaged_on',.2,True,False),('repaired_on',.2,True,True),
    ('clean_repaired_on',.2,False,True),('damaged_off',0.,True,False),('repaired_off',0.,True,True))
METRICS=('own_detail_body','other_detail_body','own_detail_R_sign','own_detail_R_projection',
    'whole_own_body','coarse_body','record_mean','record_rms','regrown_detail_correct',
    'regrown_detail_total','regrown_whole_correct','regrown_whole_total')
TRAIN_METRICS=('detail_R_projection','detail_R_sign','detail_body','whole_body')
GATES=('written_R_content','clean_read_correct_minus_swapped','clean_read_correct_minus_off')
SCIENCE=('src/laws_confirmation/l19_written_landmarks.py','src/laws_confirmation/l19_written_landmarks_run.py',
    'scripts/audit_l19_written_landmarks_outputs.py','tests/test_l19_written_landmarks.py',
    'scripts/run_l19_written_landmarks.sh','protocols/L19_WRITTEN_LANDMARKS_V1.md')


def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def arms_for(qualification):
    if type(qualification) is not bool: raise ValueError('boolean phase required')
    return QUAL_ARMS if qualification else MAIN_ARMS


def targets():
    """Equal-area half-sheets; two 2x2 sign-reversed landmarks at row 3 or 11."""
    coarse=np.full((16,16),-1.); coarse[:,:8]=1.
    taught=np.stack((coarse.copy(),coarse.copy()))
    for k,y in enumerate((3,11)):
        taught[k,y:y+2,3:5]=-1.; taught[k,y:y+2,11:13]=1.
    return taught,coarse,taught[0]!=taught[1]


def checker():
    spec=importlib.util.spec_from_file_location('d106_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def branch(initial,theta,ctx,index,life,arm,cfg=CONFIG,tag=TAG):
    if arm not in dict((x[0],x[1:]) for x in CASES): raise ValueError('undeclared arm')
    if initial.shape!=(3,16,16) or initial.dtype!=np.float64 or not np.isfinite(initial).all():
        raise ValueError('complete finite float64 initial state required')
    gain,damaged,repaired=dict((x[0],x[1:]) for x in CASES)[arm]
    changed=ctx | dict(bp=replace(ctx['bp'],rho=0.,c_m=gain))
    state=initial.copy(); saved=[state.copy()]; masks=[]; streams=[]; traces=[]; maps=[]; errors=[]; copied=[]
    for c in range(1,cfg.cycles+1):
        random=rng(index,life,f'branch:{c}',tag); copy_random=rng(index,life,f'copy:{c}',tag)
        mapping=base.base.copy_map(copy_random,cfg)
        v,ref,fresh=ctx['api']['teaching'].fission_with_mask(state[0][None],state[2][None],ctx['tissue'],random)
        incoming=base.base.copy_reference(ref[0],mapping,damaged); copied.append(incoming.copy())
        birth=np.stack((v[0],v[0],repair(incoming) if repaired else incoming))
        release,trace=base.mean.window(birth,theta,changed,random,'mean',None,cfg)
        state=native.evolve(release,theta,changed,random,cfg.free)
        saved.extend((birth,release,state)); masks.append(fresh[0]); traces.append(trace); maps.append(mapping)
        streams.append(canonical_digest(random.bit_generator.state)); errors.append(canonical_digest(copy_random.bit_generator.state))
    return np.stack(saved),np.stack(masks),streams,np.stack(traces),np.stack(maps),errors,np.stack(copied)


def measure(raw,cfg):
    taught,coarse,detail=targets(); result=[]
    for k in range(2):
        rows=[]
        for path in raw['states'][k]:
            scores=[]
            for c in range(cfg.cycles+1):
                v,_,ref=path[3*c]; mask=np.sum(raw['fresh'][:c],axis=0)>=2
                own=((v>0)==(taught[k]>0)) & (abs(v)>cfg.amp_threshold)
                other=((v>0)==(taught[1-k]>0)) & (abs(v)>cfg.amp_threshold)
                scores.append([own[detail].mean(),other[detail].mean(),((ref>0)==(taught[k]>0))[detail].mean(),
                    (ref*taught[k])[detail].mean(),own.mean(),
                    (((v>0)==(coarse>0)) & (abs(v)>cfg.amp_threshold))[~detail].mean(),
                    ref.mean(),np.sqrt(np.mean(ref*ref)),np.count_nonzero(own & mask & detail),
                    np.count_nonzero(mask & detail),np.count_nonzero(own & mask),np.count_nonzero(mask)])
            rows.append(scores)
        result.append(rows)
    return np.asarray(result,dtype=np.float64)


def training_measure(training,cfg):
    taught,_,detail=targets(); rows=[]
    for k in range(2):
        scores=[]
        for v,_,ref in training[k]:
            own=((v>0)==(taught[k]>0)) & (abs(v)>cfg.amp_threshold)
            scores.append([(ref*taught[k])[detail].mean(),((ref>0)==(taught[k]>0))[detail].mean(),
                own[detail].mean(),own.mean()])
        rows.append(scores)
    return np.asarray(rows,dtype=np.float64)


def simulate_life(index,life,qualification,cfg=CONFIG):
    arms=arms_for(qualification)
    if type(life) is not int or not 0<=life<cfg.lives: raise ValueError('declared life required')
    ctx=context(index); random=rng(index,life,'founder')
    v,ema,ref,theta,_=ctx['api']['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False); founder=np.stack((v[0],ema[0],ref[0])); founder_rng=canonical_digest(random.bit_generator.state)
    taught,_,_=targets(); training=[]; training_masks=[]; training_streams=[]; all_outcomes=[]
    for k in range(2):
        state=founder.copy(); saved=[state.copy()]; masks=[]; streams=[]
        for c in range(1,cfg.training_cycles+1):
            random=rng(index,life,f'training:{c}')
            phases,mask=native.cycle(state,theta,ctx,random,taught[k],cfg)
            saved.extend(phases); state=phases[-1]; masks.append(mask); streams.append(canonical_digest(random.bit_generator.state))
        training.append(np.stack(saved)); training_masks.append(np.stack(masks)); training_streams.append(streams)
        # Only learned R is transferred. The recipient V/EMA are the common pre-teaching founder.
        initial=founder.copy(); initial[2]=state[2]
        all_outcomes.append([branch(initial,theta,ctx,index,life,arm,cfg) for arm in arms])
    flat=[x for row in all_outcomes for x in row]
    for row in flat[1:]:
        np.testing.assert_array_equal(row[1],flat[0][1]); np.testing.assert_array_equal(row[4],flat[0][4])
    np.testing.assert_array_equal(training_masks[0],training_masks[1]); assert training_streams[0]==training_streams[1]
    raw=dict(theta=theta,founder=founder,training=np.stack(training),training_fresh=training_masks[0],
        states=np.asarray([[x[0] for x in row] for row in all_outcomes]),fresh=flat[0][1],
        control=np.asarray([[x[3] for x in row] for row in all_outcomes]),copy_map=flat[0][4],
        pre_repair=np.asarray([[x[6] for x in row] for row in all_outcomes]))
    raw['values']=measure(raw,cfg); raw['training_values']=training_measure(raw['training'],cfg)
    meta=dict(index=index,life=life,qualification=qualification,config=asdict(cfg),arms=list(arms),tag=TAG,
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        founder_rng=founder_rng,training_rng=training_streams,
        branch_rng=[[x[2] for x in row] for row in all_outcomes],copy_rng=[[x[5] for x in row] for row in all_outcomes],
        theta_writable=False,arm_parameters=[list(x) for a in arms for x in CASES if x[0]==a])
    return raw,meta


def execute_block(index,qualification,cfg=CONFIG):
    arms=arms_for(qualification); rows=[]; records=[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,qualification,cfg); meta['replay']=check.check_life(raw,meta,cfg)
        initial=raw['founder'].copy(); initial[2]=raw['training'][0,-1,2]
        alias=branch(initial,raw['theta'],context(index),index,life,arms[0],cfg)
        for pos,key in ((0,'states'),(3,'control'),(6,'pre_repair')): np.testing.assert_array_equal(alias[pos],raw[key][0,0])
        np.testing.assert_array_equal(alias[1],raw['fresh']); np.testing.assert_array_equal(alias[4],raw['copy_map'])
        assert alias[2]==meta['branch_rng'][0][0] and alias[5]==meta['copy_rng'][0][0]
        meta['exact_alias_branches']=1; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,qualification=qualification,config=asdict(cfg),lives=records)


def summarize(blocks,qualification,cfg=CONFIG):
    arms=arms_for(qualification)
    if len(blocks)!=8: raise ValueError('eight complete equally weighted tissues required')
    values=np.asarray([b['values'] for b in blocks]); controls=np.asarray([b['control'] for b in blocks])
    trained=np.asarray([b['training_values'] for b in blocks])
    if (values.shape!=(8,cfg.lives,2,len(arms),cfg.cycles+1,12)
            or controls.shape!=(8,cfg.lives,2,len(arms),cfg.cycles,cfg.teaching,7)
            or trained.shape!=(8,cfg.lives,2,3*cfg.training_cycles+1,4)
            or not all(np.isfinite(x).all() for x in (values,controls,trained))):
        raise ValueError('complete finite paired readout and training observations required')
    residual=float(abs(controls[...,1]).max())
    if residual>1e-12: raise ValueError('zero-mean support failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8)); stats=lambda x:native.native.contrast_stats(x,samples)
    # Average target histories within each life, then lives within tissue: never treat cells/targets as replicates.
    own=values[...,0].mean(axis=2); other=values[...,1].mean(axis=2)
    specificity=own-other
    clean=arms.index('clean_on'); contrasts=[]
    gates=[]
    if qualification:
        off=arms.index('clean_off')
        effects=(trained[:,:,:,-1,0].mean(axis=2)*2,specificity[:,:,clean,1],own[:,:,clean,1]-own[:,:,off,1])
        gates=[dict(name=name,**stats(effect)) for name,effect in zip(GATES,effects)]
    else:
        for c in (cfg.primary_cycle,3,1):
            for name,a,b in (('repair_minus_damage',2,1),('clean_repair_minus_clean',3,0),
                    ('clean_minus_repaired',0,2),('repair_reader_effect',2,5),('damage_reader_effect',1,4),
                    ('off_repair_alias',5,4)):
                for observer,score in (('landmark_specificity',specificity),('landmark_own',own),
                        ('whole',values[...,4].mean(axis=2)),('coarse',values[...,5].mean(axis=2))):
                    contrasts.append(dict(name=name,cycle=c,observer=observer,**stats(score[:,:,a,c]-score[:,:,b,c])))
    trajectories=[]
    for a,arm in enumerate(arms):
        for c in range(cfg.cycles+1):
            trajectories.append(dict(arm=arm,cycle=c,own=stats(own[:,:,a,c]),other=stats(other[:,:,a,c]),
                specificity=stats(specificity[:,:,a,c]),
                reference_sign=stats(values[:,:,:,a,c,2].mean(axis=2)),
                reference_projection=stats(values[:,:,:,a,c,3].mean(axis=2)),
                whole=stats(values[:,:,:,a,c,4].mean(axis=2)),coarse=stats(values[:,:,:,a,c,5].mean(axis=2)),
                reference_mean=stats(values[:,:,:,a,c,6].mean(axis=2)),reference_rms=stats(values[:,:,:,a,c,7].mean(axis=2)),
                per_target_own=[stats(values[:,:,k,a,c,0]) for k in range(2)],
                regrown_detail_denominators=values[:,:,:,a,c,9].astype(int).tolist(),
                regrown_whole_denominators=values[:,:,:,a,c,11].astype(int).tolist()))
    qualified=all(g['pointwise_block_bootstrap_95'][0]>0 for g in gates) if qualification else None
    primary=gates[1] if qualification else contrasts[0]
    label=('CLEAN_LANDMARK_READ_QUALIFIED' if qualified else 'CLEAN_LANDMARK_READ_NOT_QUALIFIED') if qualification else (
        'REPAIR_IMPROVES_LANDMARK_SPECIFICITY' if primary['pointwise_block_bootstrap_95'][0]>0 else
        'REPAIR_REDUCES_LANDMARK_SPECIFICITY' if primary['pointwise_block_bootstrap_95'][1]<0 else 'LANDMARK_REPAIR_EFFECT_UNRESOLVED')
    return dict(schema='l19_written_landmarks_summary_v1',qualification=qualification,qualified=qualified,label=label,
        tissues=list(QUAL_TISSUES if qualification else TISSUES),arms=list(arms),metrics=list(METRICS),training_metrics=list(TRAIN_METRICS),
        primary=primary,gates=gates,contrasts=contrasts,trajectories=trajectories,
        cell_means=values.mean(axis=(0,1)).tolist(),training_means=trained.mean(axis=(0,1)).tolist(),
        max_controlled_mean_residual=residual,blocks=8,lives_per_block=cfg.lives,landmark_cells=16,
        absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False,
        training_projection_trajectory=[stats(trained[:,:,:,c,0].mean(axis=2)*2) for c in range(3*cfg.training_cycles+1)])


def contract():
    taught,coarse,detail=targets()
    return dict(schema='l19_written_landmarks_v1',decision='D106',law='L19',run_id=RUN_ID,qualification_run_id=QUAL_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),qualification_tissues=list(QUAL_TISSUES),disposable=DISPOSABLE,seed_tag=TAG,
        qualification_arms=list(QUAL_ARMS),main_arms=list(MAIN_ARMS),arm_parameters=[list(x) for x in CASES],
        targets=taught.tolist(),coarse=coarse.tolist(),detail_cells=int(detail.sum()),
        teaching='native rho .002; three fissions, each 500 target-clamp updates plus 1000 free; retain all three phase states',
        recipient='same untouched pre-teaching founder V/EMA and fixed theta for both records and every arm',
        transferred_learned_field='only final native-written R; no taught V/EMA or injected ideal R',
        qualification_cycle=1,qualification_gates=list(GATES),qualification_rule='all three paired-effect block-bootstrap 95% lower bounds > 0',
        main_primary='repaired_on minus damaged_on target-averaged landmark own-minus-other fidelity, fixed 16 cells, cycle6',
        wrong_content='actual alternative-target trained R, common body and RNG; opposite-target scores of paired trajectories',
        record_bytes=2048,backup_bytes=0,repair_persistent_extra_bytes=0,protected_rho=0,
        repair='unchanged D105 synchronous periodic 3x3 median, current R only',
        copy_damage='unchanged D104 32 disjoint swaps per boundary',controller='unchanged D102 current-V zero mean',
        qualification_branches=64,main_branches=192,independent_life_replays_per_phase=16,exact_alias_branches_per_phase=16,
        state_atol=1e-10,metrics_atol=1e-12,exact_signs=True,absolute_fidelity_gate=None,
        bootstrap_resamples=10000,independent_unit='eight tissues; average two targets within life and two lives within tissue',
        qualification_failure_stops_main=True,automatic_retry=False,automatic_follow_on=False,
        hard_reset_or_carrier_only_or_biology_or_necessity_claim=False)
