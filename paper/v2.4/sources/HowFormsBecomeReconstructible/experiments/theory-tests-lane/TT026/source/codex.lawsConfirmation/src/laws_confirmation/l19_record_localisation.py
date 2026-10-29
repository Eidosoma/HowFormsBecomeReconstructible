"""D107: factorial regional transfer of retained D106 records into fresh bodies."""
from __future__ import annotations

from dataclasses import asdict,dataclass
import importlib.util
from pathlib import Path

import numpy as np

from . import l19_written_landmarks as base
from . import l15_repair_speed_run as files
from .io import DEFAULT_EXTERNAL_ROOT,canonical_digest,sha256_file

WS,ORIGIN=base.WS,base.ORIGIN
api=base.api
RUN_ID='l19_record_localisation_v1_attempt1'
TAG='l19-record-localisation-v1'
TISSUES=tuple(range(52000,52008))
SOURCE_TISSUES=tuple(range(51000,51008))
DISPOSABLE=514207
HISTORIES=('clean','repaired')
MOSAICS=('AA','AB','BA','BB')
FACTORS=((0,0),(0,1),(1,0),(1,1))
READERS=('on','off')
PHASES=('initial','birth','support_end','free_end')
METRICS=('A_detail','B_detail','A_minus_B','detail_amplitude','coarse_body',
    'R_A_projection','R_mean','R_rms','whole_A','whole_B')
CONTRASTS=(('full_record_identity',(.5,0,0,-.5)),
    ('inside_contribution',(.25,.25,-.25,-.25)),
    ('outside_contribution',(.25,-.25,.25,-.25)),
    ('inside_minus_outside',(0,.5,-.5,0)),
    ('interaction',(.5,-.5,-.5,.5)),
    ('inside_at_outside_A',(.5,0,-.5,0)),('inside_at_outside_B',(0,.5,0,-.5)),
    ('outside_at_inside_A',(.5,-.5,0,0)),('outside_at_inside_B',(0,0,.5,-.5)))
SCIENCE=('src/laws_confirmation/l19_record_localisation.py','src/laws_confirmation/l19_record_localisation_run.py',
    'scripts/audit_l19_record_localisation_outputs.py','tests/test_l19_record_localisation.py',
    'scripts/run_l19_record_localisation.sh','protocols/L19_RECORD_LOCALISATION_V1.md')


@dataclass(frozen=True)
class Config:
    lives:int=2
    settle:int=620
    teaching:int=500
    free:int=1000
    cycles:int=1
    damage_pairs:int=32  # unused paired copy map is drawn by unchanged D106 branch
    amp_threshold:float=.2

    def __post_init__(self):
        for key in ('lives','settle','teaching','free'):
            if type(getattr(self,key)) is not int or getattr(self,key)<=0: raise ValueError('positive integral '+key+' required')
        if self.lives!=2 or type(self.cycles) is not int or self.cycles!=1:
            raise ValueError('two source lives and one diagnostic boundary required')
        if type(self.damage_pairs) is not int or self.damage_pairs!=32:
            raise ValueError('unchanged unused copy-map clock required')
        if type(self.amp_threshold) not in (int,float) or not np.isfinite(self.amp_threshold) or not 0<self.amp_threshold<2:
            raise ValueError('finite physical observation threshold required')


CONFIG=Config()


def source_index(index):
    if type(index) is not int: raise ValueError('declared integer readout identity required')
    if index==DISPOSABLE: return base.DISPOSABLE
    if index in TISSUES: return SOURCE_TISSUES[TISSUES.index(index)]
    raise ValueError('undeclared readout identity')


def context(index): return base.context(source_index(index))
def rng(index,life,phase,tag=TAG): return base.rng(index,life,phase,tag)


def checker():
    spec=importlib.util.spec_from_file_location('d107_independent_checker',WS/SCIENCE[2])
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_paths(root,index):
    source=source_index(index)
    if index==DISPOSABLE:
        directory=root/'tmp'/f'{base.RUN_ID}_benchmark'; name='main'
    else:
        directory=root/'outputs'/base.RUN_ID; name=f'block_{source}'
    paths=tuple(directory/(name+'.'+ext) for ext in ('npz','json'))
    for path in paths:
        files.require_beneath(path,root)
        if path.is_symlink(): raise ValueError('direct retained source required')
    return paths


def load_source(root,index):
    api(); paths=source_paths(root,index)
    raw,meta=files.load_npz(paths[0]),files.read_json(paths[1])
    assert meta['index']==source_index(index) and meta['qualification'] is False
    assert base.checker().check_block(raw,meta,base.CONFIG,replay=False)
    # life, source history, target, y, x; both histories at the completed sixth boundary.
    refs=np.stack([raw['states'][:,:,a,18,2] for a in (0,2)],axis=1)
    assert refs.shape==(2,2,2,16,16) and refs.dtype==np.float64 and np.isfinite(refs).all()
    return refs,dict(source_index=source_index(index),source_run=base.RUN_ID,source_cycle=6,
        source_arms=['clean_on','repaired_on'],paths=[str(x) for x in paths],
        sha256=[sha256_file(x) for x in paths],known_source_outcomes=True,source_root=str(root))


def mix(records,inside,outside):
    """Assemble one 2048-byte record; selections address D and its fixed complement."""
    if (not isinstance(records,np.ndarray) or records.shape!=(2,16,16) or records.dtype!=np.float64
            or not np.isfinite(records).all()): raise ValueError('two finite float64 records required')
    if any(type(k) is not int or k not in (0,1) for k in (inside,outside)): raise ValueError('A/B selectors required')
    detail=base.targets()[2]
    return np.where(detail,records[inside],records[outside])


def read(ref,recipient,theta,ctx,index,life,reader,cfg=CONFIG,tag=TAG):
    if reader not in READERS: raise ValueError('declared reader required')
    if not isinstance(ref,np.ndarray) or ref.shape!=(16,16) or ref.dtype!=np.float64 or not np.isfinite(ref).all():
        raise ValueError('finite float64 R required')
    if not isinstance(recipient,np.ndarray) or recipient.shape!=(3,16,16) or recipient.dtype!=np.float64 or not np.isfinite(recipient).all():
        raise ValueError('complete common recipient required')
    initial=recipient.copy(); initial[2]=ref
    return base.branch(initial,theta,ctx,index,life,'clean_'+reader,cfg,tag)


def measure(states,cfg):
    targets,coarse,detail=base.targets(); v=states[...,0,:,:]; ref=states[...,2,:,:]
    qualified=abs(v)>cfg.amp_threshold
    a=((v>0)==(targets[0]>0)) & qualified; b=((v>0)==(targets[1]>0)) & qualified
    am=a[...,detail].mean(axis=-1); bm=b[...,detail].mean(axis=-1)
    return np.stack((am,bm,am-bm,qualified[...,detail].mean(axis=-1),
        (((v>0)==(coarse>0)) & qualified)[...,~detail].mean(axis=-1),
        (ref*targets[0])[...,detail].mean(axis=-1),ref.mean(axis=(-2,-1)),
        np.sqrt((ref*ref).mean(axis=(-2,-1))),a.mean(axis=(-2,-1)),b.mean(axis=(-2,-1))),axis=-1)


def simulate_life(index,life,refs,source,cfg=CONFIG):
    source_index(index)
    if type(life) is not int or not 0<=life<cfg.lives: raise ValueError('declared source life required')
    if not isinstance(refs,np.ndarray) or refs.shape!=(2,2,16,16) or refs.dtype!=np.float64 or not np.isfinite(refs).all():
        raise ValueError('complete source histories required')
    ctx=context(index); random=rng(index,life,'recipient')
    v,ema,ref,theta,_=ctx['api']['settle_with_blueprint'](ctx['tissue'],ctx['bp'],'T',random,None,1,cfg.settle)
    theta.setflags(write=False); recipient=np.stack((v[0],ema[0],ref[0])); initial_rng=canonical_digest(random.bit_generator.state)
    mosaics=np.asarray([[mix(refs[h],inside,outside) for inside,outside in FACTORS] for h in range(2)])
    outcomes=[[[read(mosaics[h,m],recipient,theta,ctx,index,life,r,cfg) for r in READERS]
        for m in range(4)] for h in range(2)]
    flat=[row for history in outcomes for mosaic in history for row in mosaic]
    for row in flat[1:]:
        np.testing.assert_array_equal(row[1],flat[0][1]); np.testing.assert_array_equal(row[4],flat[0][4])
    raw=dict(theta=theta,recipient=recipient,source_R=refs.copy(),mosaics=mosaics,
        states=np.asarray([[[r[0] for r in m] for m in h] for h in outcomes]),fresh=flat[0][1],
        control=np.asarray([[[r[3] for r in m] for m in h] for h in outcomes]),copy_map=flat[0][4],
        pre_repair=np.asarray([[[r[6] for r in m] for m in h] for h in outcomes]))
    raw['values']=measure(raw['states'],cfg)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,source=source,histories=list(HISTORIES),mosaics=list(MOSAICS),
        readers=list(READERS),factors=[list(x) for x in FACTORS],phases=list(PHASES),
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
    if (values.shape!=(8,2,2,4,2,4,10) or control.shape!=(8,2,2,4,2,1,cfg.teaching,7)
            or not np.isfinite(values).all() or not np.isfinite(control).all()):
        raise ValueError('complete finite paired factorial data required')
    residual=float(abs(control[...,1]).max())
    if residual>1e-12: raise ValueError('public balance support failed')
    samples=rng(0,0,'bootstrap').integers(0,8,(10000,8)); stats=lambda x:base.native.native.contrast_stats(x,samples)
    contrasts=[]
    for h,history in enumerate(HISTORIES):
        for phase in (3,2):
            y=values[:,:,h,:,:,phase,2]
            for mode,score in (('on',y[...,0]),('off',y[...,1]),('on_minus_off',y[...,0]-y[...,1])):
                for name,coefs in CONTRASTS:
                    effect=sum(coef*score[:,:,m] for m,coef in enumerate(coefs) if coef)
                    contrasts.append(dict(history=history,phase=PHASES[phase],reader=mode,name=name,**stats(effect)))
    select=lambda h,n:next(x for x in contrasts if x['history']==h and x['phase']=='free_end' and x['reader']=='on_minus_off' and x['name']==n)
    readability=[dict(history=h,qualified=select(h,'full_record_identity')['pointwise_block_bootstrap_95'][0]>0,
        effect=select(h,'full_record_identity')) for h in HISTORIES]
    primary=select('repaired','inside_minus_outside'); bounds=primary['pointwise_block_bootstrap_95']
    if not readability[1]['qualified']: label='REPAIRED_RECORD_READ_NOT_QUALIFIED'
    elif bounds[0]>0: label='LANDMARK_REGION_DOMINATES'
    elif bounds[1]<0: label='SURROUNDING_REGION_DOMINATES'
    else: label='REGIONAL_ATTRIBUTION_UNRESOLVED'
    trajectories=[]
    for h,history in enumerate(HISTORIES):
        for m,mosaic in enumerate(MOSAICS):
            for r,reader in enumerate(READERS):
                for s,phase in enumerate(PHASES):
                    trajectories.append(dict(history=history,mosaic=mosaic,reader=reader,phase=phase,
                        A_detail=stats(values[:,:,h,m,r,s,0]),B_detail=stats(values[:,:,h,m,r,s,1]),
                        preference=stats(values[:,:,h,m,r,s,2]),coarse=stats(values[:,:,h,m,r,s,4])))
    return dict(schema='l19_record_localisation_summary_v1',label=label,primary=primary,readability=readability,
        contrasts=contrasts,trajectories=trajectories,cell_means=values.mean(axis=(0,1)).tolist(),
        tissues=list(TISSUES),source_tissues=list(SOURCE_TISSUES),histories=list(HISTORIES),mosaics=list(MOSAICS),
        readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),blocks=8,lives_per_block=2,
        landmark_cells=16,complement_cells=240,max_controlled_mean_residual=residual,absolute_fidelity_gate=None,
        secondary_intervals_multiplicity_adjusted=False,source_records_previously_observed=True,fresh_physical_tissue_parameters=False)


def contract():
    return dict(schema='l19_record_localisation_v1',decision='D107',law='L19',run_id=RUN_ID,
        config=asdict(CONFIG),tissues=list(TISSUES),source_tissues=list(SOURCE_TISSUES),disposable=DISPOSABLE,
        disposable_source=base.DISPOSABLE,seed_tag=TAG,histories=list(HISTORIES),mosaics=list(MOSAICS),
        factors=[list(x) for x in FACTORS],readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),
        contrasts=[[name,list(coefs)] for name,coefs in CONTRASTS],
        source='retained D106 clean_on/repaired_on R after boundary6; known records, no new writers',
        source_records_previously_observed=True,fresh_physical_tissue_parameters=False,
        recipient='fresh D107 noisy settlement using matched source theta/tissue parameters; no donor V/EMA',
        regions='unchanged D106 16-cell disagreement mask and 240-cell complement; fixed engineered addresses',
        R_bytes=2048,backup_bytes=0,extra_persistent_bytes=0,post_mix_repair_or_damage=False,
        rho_readout=0,reader_gain_on=.2,reader_gain_off=0,record_normalisation=False,
        primary='repaired-history inside-minus-outside contribution to A-minus-B preference, on-minus-off, free_end',
        contribution_scale='inside/outside coefficient .25; sum equals .5*(AA-BB); dominance .5*(AB-BA)',
        readability_gate='repaired full-record identity on-minus-off 95% block-bootstrap lower bound >0',
        gate_failure='report all effects but do not localise the previously observed surviving distinction',
        secondary_intervals_multiplicity_adjusted=False,absolute_fidelity_gate=None,
        independent_unit='eight known source tissues, paired with fresh readout futures; average two lives',
        fresh_branches=256,independent_life_replays=16,exact_alias_branches=32,
        bootstrap_resamples=10000,state_atol=1e-10,metrics_atol=1e-12,exact_signs=True,
        automatic_retry=False,automatic_follow_on=False,sole_location_or_bit_capacity_or_biology_claim=False)
