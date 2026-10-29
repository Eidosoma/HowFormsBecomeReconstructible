"""D108: factorial regional transfer of retained D106 records into fresh bodies."""
from __future__ import annotations

from dataclasses import asdict
import importlib.util

import numpy as np

from . import l19_record_localisation as base
from .io import DEFAULT_EXTERNAL_ROOT,canonical_digest

WS,ORIGIN=base.WS,base.ORIGIN
api=base.api
RUN_ID='l19_halo_localisation_v1_attempt1'
TAG='l19-halo-localisation-v1'
TISSUES=tuple(range(53000,53008))
SOURCE_TISSUES=tuple(range(51000,51008))
DISPOSABLE=514208
HISTORIES=('clean','repaired')
REGIONS=('landmark','near','far')
MOSAICS=('AAA','AAB','ABA','ABB','BAA','BAB','BBA','BBB')
FACTORS=tuple((l,n,f) for l in (0,1) for n in (0,1) for f in (0,1))
READERS=('on','off')
PHASES=('initial','birth','support_end','free_end')
METRICS=('A_detail','B_detail','A_minus_B','detail_amplitude','coarse_body',
    'R_A_projection','R_mean','R_rms','whole_A','whole_B')


def contrast_table():
    signs=np.asarray([[1-2*x for x in factors] for factors in FACTORS])
    terms=[('landmark_main',(0,)),('near_main',(1,)),('far_main',(2,)),
        ('landmark_near_interaction',(0,1)),('landmark_far_interaction',(0,2)),
        ('near_far_interaction',(1,2)),('three_way_interaction',(0,1,2))]
    out=[('full_record_identity',(.5,0,0,0,0,0,0,-.5))]
    for name,axes in terms: out.append((name,tuple(np.prod(signs[:,axes],axis=1)/8)))
    out.extend((('near_minus_far',tuple((signs[:,1]-signs[:,2])/8)),
        ('coupled_outside_contribution',(.25,0,0,-.25,.25,0,0,-.25)),
        ('coupled_landmark_contribution',(.25,0,0,.25,-.25,0,0,-.25)),
        ('coupled_inside_minus_outside',(0,0,0,.5,-.5,0,0,0))))
    for axis,region in enumerate(REGIONS):
        others=[k for k in range(3) if k!=axis]
        for u in (0,1):
            for v in (0,1):
                coefs=[.5*(1-2*factors[axis]) if factors[others[0]]==u and factors[others[1]]==v else 0.
                    for factors in FACTORS]
                name=region+'_at_'+REGIONS[others[0]]+'_'+'AB'[u]+'_'+REGIONS[others[1]]+'_'+'AB'[v]
                out.append((name,tuple(coefs)))
    return tuple(out)


CONTRASTS=contrast_table()
SCIENCE=('src/laws_confirmation/l19_halo_localisation.py','src/laws_confirmation/l19_halo_localisation_run.py',
    'scripts/audit_l19_halo_localisation_outputs.py','tests/test_l19_halo_localisation.py',
    'scripts/run_l19_halo_localisation.sh','protocols/L19_HALO_LOCALISATION_V1.md')


Config=base.Config
CONFIG=base.CONFIG


def bridge_index(index):
    if type(index) is not int: raise ValueError('declared integer readout identity required')
    if index==DISPOSABLE: return base.DISPOSABLE
    if index in TISSUES: return base.TISSUES[TISSUES.index(index)]
    raise ValueError('undeclared readout identity')


def source_index(index): return base.source_index(bridge_index(index))
def context(index): return base.context(bridge_index(index))
def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def checker():
    spec=importlib.util.spec_from_file_location('d108_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_paths(root,index): return base.source_paths(root,bridge_index(index))
def load_source(root,index): return base.load_source(root,bridge_index(index))


def regions():
    detail=base.base.targets()[2]
    expanded=np.logical_or.reduce([np.roll(detail,(dy,dx),(0,1)) for dy in (-1,0,1) for dx in (-1,0,1)])
    return np.stack((detail,expanded & ~detail,~expanded))


def mix(records,landmark,near,far):
    """One unchanged-size R; donor choices on D, its one-cell ring, and the remainder."""
    if (not isinstance(records,np.ndarray) or records.shape!=(2,16,16) or records.dtype!=np.float64
            or not np.isfinite(records).all()): raise ValueError('two finite float64 records required')
    if any(type(k) is not int or k not in (0,1) for k in (landmark,near,far)): raise ValueError('A/B selectors required')
    masks=regions()
    return np.where(masks[0],records[landmark],np.where(masks[1],records[near],records[far]))


def read(ref,recipient,theta,ctx,index,life,reader,cfg=CONFIG,tag=TAG):
    return base.read(ref,recipient,theta,ctx,index,life,reader,cfg,tag)


measure=base.measure


def simulate_life(index,life,refs,source,cfg=CONFIG):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives: raise ValueError('declared source life required')
    if not isinstance(refs,np.ndarray) or refs.shape!=(2,2,16,16) or refs.dtype!=np.float64 or not np.isfinite(refs).all():
        raise ValueError('complete source histories required')
    ctx=context(index); random=rng(index,life,'recipient')
    v,ema,ref,theta,_=ctx['api']['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False); recipient=np.stack((v[0],ema[0],ref[0])); initial_rng=canonical_digest(random.bit_generator.state)
    mosaics=np.asarray([[mix(refs[h],*factors) for factors in FACTORS] for h in range(2)])
    outcomes=[[[read(mosaics[h,m],recipient,theta,ctx,index,life,r,cfg) for r in READERS]
        for m in range(8)] for h in range(2)]
    flat=[row for history in outcomes for mosaic in history for row in mosaic]
    for row in flat[1:]:
        np.testing.assert_array_equal(row[1],flat[0][1]); np.testing.assert_array_equal(row[4],flat[0][4])
    raw=dict(regions=regions(),theta=theta,recipient=recipient,source_R=refs.copy(),mosaics=mosaics,
        states=np.asarray([[[r[0] for r in m] for m in h] for h in outcomes]),fresh=flat[0][1],
        control=np.asarray([[[r[3] for r in m] for m in h] for h in outcomes]),copy_map=flat[0][4],
        pre_repair=np.asarray([[[r[6] for r in m] for m in h] for h in outcomes]))
    raw['values']=measure(raw['states'],cfg)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,source=source,histories=list(HISTORIES),mosaics=list(MOSAICS),
        readers=list(READERS),factors=[list(x) for x in FACTORS],phases=list(PHASES),
        region_names=list(REGIONS),region_sizes=[16,48,192],partition='periodic_chebyshev_one_cell_ring',
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']),
        recipient_rng=initial_rng,branch_rng=[[[r[2] for r in m] for m in h] for h in outcomes],
        copy_rng=[[[r[5] for r in m] for m in h] for h in outcomes],theta_writable=False)
    return raw,meta


def execute_block(index,cfg=CONFIG,root=DEFAULT_EXTERNAL_ROOT):
    refs,source=load_source(root,index); rows=[]; records=[]; check=checker()
    for life in range(cfg.lives):
        raw,meta=simulate_life(index,life,refs[life],source,cfg); meta['replay']=check.check_life(raw,meta,cfg)
        # Bypass the regional constructor for the intact A alias in both histories.
        for h in range(2):
            alias=read(refs[life,h,0],raw['recipient'],raw['theta'],context(index),index,life,'on',cfg)
            for pos,key in ((0,'states'),(3,'control'),(6,'pre_repair')): np.testing.assert_array_equal(alias[pos],raw[key][h,0,0])
            np.testing.assert_array_equal(alias[1],raw['fresh']); np.testing.assert_array_equal(alias[4],raw['copy_map'])
            assert alias[2]==meta['branch_rng'][h][0][0] and alias[5]==meta['copy_rng'][h][0][0]
        meta['exact_alias_branches']=2; rows.append(raw); records.append(meta)
    return {k:np.stack([r[k] for r in rows]) for k in rows[0]},dict(index=index,config=asdict(cfg),lives=records)


def summarize(blocks,cfg=CONFIG):
    if len(blocks)!=8: raise ValueError('eight complete source-tissue blocks required')
    values=np.asarray([b['values'] for b in blocks]); control=np.asarray([b['control'] for b in blocks])
    if (values.shape!=(8,2,2,8,2,4,10) or control.shape!=(8,2,2,8,2,1,cfg.teaching,7)
            or not np.isfinite(values).all() or not np.isfinite(control).all()):
        raise ValueError('complete finite paired factorial data required')
    residual=float(abs(control[...,1]).max())
    if residual>1e-12: raise ValueError('public balance support failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8)); stats=lambda x:base.base.native.native.contrast_stats(x,samples)
    contrasts=[]
    for h,history in enumerate(HISTORIES):
        for phase in (3,2):
            y=values[:,:,h,:,:,phase,2]
            for mode,score in (('on',y[...,0]),('off',y[...,1]),('on_minus_off',y[...,0]-y[...,1])):
                for name,coefs in CONTRASTS:
                    effect=sum(coef*score[:,:,m] for m,coef in enumerate(coefs) if coef)
                    contrasts.append(dict(history=history,phase=PHASES[phase],reader=mode,name=name,**stats(effect)))
    select=lambda h,n:next(x for x in contrasts if x['history']==h and x['phase']=='free_end' and x['reader']=='on_minus_off' and x['name']==n)
    readability=[]
    for history in HISTORIES:
        intact=select(history,'full_record_identity'); outside=select(history,'coupled_outside_contribution')
        iq=intact['pointwise_block_bootstrap_95'][0]>0; oq=outside['pointwise_block_bootstrap_95'][0]>0
        readability.append(dict(history=history,qualified=iq and oq,intact_qualified=iq,outside_qualified=oq,
            intact_effect=intact,outside_effect=outside))
    primary=select('repaired','near_minus_far'); bounds=primary['pointwise_block_bootstrap_95']
    if not readability[1]['intact_qualified']: label='REPAIRED_RECORD_READ_NOT_QUALIFIED'
    elif not readability[1]['outside_qualified']: label='REPAIRED_OUTSIDE_SIGNAL_NOT_QUALIFIED'
    elif bounds[0]>0: label='NEAR_HALO_DOMINATES'
    elif bounds[1]<0: label='DISTANT_REGION_DOMINATES'
    else: label='NEAR_FAR_ATTRIBUTION_UNRESOLVED'
    trajectories=[]
    for h,history in enumerate(HISTORIES):
        for m,mosaic in enumerate(MOSAICS):
            for r,reader in enumerate(READERS):
                for s,phase in enumerate(PHASES):
                    trajectories.append(dict(history=history,mosaic=mosaic,reader=reader,phase=phase,
                        A_detail=stats(values[:,:,h,m,r,s,0]),B_detail=stats(values[:,:,h,m,r,s,1]),
                        preference=stats(values[:,:,h,m,r,s,2]),coarse=stats(values[:,:,h,m,r,s,4])))
    return dict(schema='l19_halo_localisation_summary_v1',label=label,primary=primary,readability=readability,
        contrasts=contrasts,trajectories=trajectories,cell_means=values.mean(axis=(0,1)).tolist(),
        tissues=list(TISSUES),source_tissues=list(SOURCE_TISSUES),histories=list(HISTORIES),mosaics=list(MOSAICS),
        readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),blocks=8,lives_per_block=2,
        landmark_cells=16,near_cells=48,far_cells=192,complement_cells=240,region_names=list(REGIONS),
        max_controlled_mean_residual=residual,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False,source_records_previously_observed=True,fresh_physical_tissue_parameters=False)


def contract():
    return dict(schema='l19_halo_localisation_v1',decision='D108',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),source_tissues=list(SOURCE_TISSUES),disposable=DISPOSABLE,
        disposable_source=base.base.DISPOSABLE,seed_tag=TAG,histories=list(HISTORIES),mosaics=list(MOSAICS),
        factors=[list(x) for x in FACTORS],readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),
        contrasts=[[name,list(coefs)] for name,coefs in CONTRASTS],
        source='retained D106 clean_on/repaired_on R after boundary6; known records, no new writers',
        source_records_previously_observed=True,fresh_physical_tissue_parameters=False,
        recipient='fresh D108 noisy settlement using matched source theta/tissue parameters; no donor V/EMA',
        regions='D:16; periodic one-cell Chebyshev ring:48; remaining cells:192; unequal areas, not density',
        partition='periodic_chebyshev_one_cell_ring',region_sizes=[16,48,192],
        R_bytes=2048,backup_bytes=0,extra_persistent_bytes=0,post_mix_repair_or_damage=False,
        rho_readout=0,reader_gain_on=.2,reader_gain_off=0,record_normalisation=False,
        primary='repaired-history near-minus-far mean factorial effect on A-minus-B preference, on-minus-off, free_end',
        contribution_scale='main and interaction coefficients are sign-product/8; conditional effects half A-minus-B',
        algebra='full identity = landmark + near + far + three-way; coupled outside = near + far',
        readability_gate='repaired full-record identity AND coupled-outside on-minus-off 95% lower bounds >0',
        gate_failure='report all effects but do not localise the previously observed surviving distinction',
        secondary_intervals_multiplicity_adjusted=False,absolute_fidelity_gate=None,
        independent_unit='eight known source tissues, paired with fresh readout futures; average two lives',
        fresh_branches=512,independent_life_replays=16,exact_alias_branches=32,
        bootstrap_resamples=10000,state_atol=1e-10,metrics_atol=1e-12,exact_signs=True,
        automatic_retry=False,automatic_follow_on=False,sole_location_or_bit_capacity_or_biology_claim=False)
