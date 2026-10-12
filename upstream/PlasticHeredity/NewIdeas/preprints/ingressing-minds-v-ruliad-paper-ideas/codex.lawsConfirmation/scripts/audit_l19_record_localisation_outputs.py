"""D107 independent source extraction, mosaics, recipient replay and factorial audit."""
from dataclasses import asdict,replace
from pathlib import Path

import numpy as np

from laws_confirmation import l19_written_landmarks as prior
from laws_confirmation import l15_repair_speed_run as files
from laws_confirmation.io import canonical_digest,external_root,sha256_file

previous=prior.checker(); old=previous.old; physics=previous.physics
nested,compare,generator=previous.nested,previous.compare,previous.generator
TAG='l19-record-localisation-v1'
HISTORIES=('clean','repaired'); MOSAICS=('AA','AB','BA','BB'); READERS=('on','off')
PHASES=('initial','birth','support_end','free_end')
METRICS=('A_detail','B_detail','A_minus_B','detail_amplitude','coarse_body',
    'R_A_projection','R_mean','R_rms','whole_A','whole_B')
FACTORS=((0,0),(0,1),(1,0),(1,1))
CONTRASTS=(('full_record_identity',(.5,0,0,-.5)),('inside_contribution',(.25,.25,-.25,-.25)),
    ('outside_contribution',(.25,-.25,.25,-.25)),('inside_minus_outside',(0,.5,-.5,0)),
    ('interaction',(.5,-.5,-.5,.5)),('inside_at_outside_A',(.5,0,-.5,0)),
    ('inside_at_outside_B',(0,.5,0,-.5)),('outside_at_inside_A',(.5,-.5,0,0)),('outside_at_inside_B',(0,0,.5,-.5)))


def source_expected(meta):
    index=meta['index']; assert type(index) is int
    root=external_root(meta['source']['source_root'])
    if index==514207:
        parent=514206; directory=root/'tmp'/'l19_written_landmarks_v1_attempt1_benchmark'; name='main'
    else:
        assert 52000<=index<=52007
        parent=index-1000; directory=root/'outputs'/'l19_written_landmarks_v1_attempt1'; name=f'block_{parent}'
    paths=[directory/(name+'.'+ext) for ext in ('npz','json')]
    assert all(not x.is_symlink() for x in paths)
    expected=dict(source_index=parent,source_run='l19_written_landmarks_v1_attempt1',source_cycle=6,
        source_arms=['clean_on','repaired_on'],paths=[str(x) for x in paths],sha256=[sha256_file(x) for x in paths],
        known_source_outcomes=True,source_root=str(root))
    nested(meta['source'],expected)
    parent_meta=files.read_json(paths[1]); assert parent_meta['index']==parent and parent_meta['qualification'] is False
    with np.load(paths[0],allow_pickle=False) as data:
        frames=data['states'][meta['life']]; records=np.empty((2,2,16,16),dtype=np.float64)
        for h,a in enumerate((0,2)):
            for target in range(2): records[h,target]=frames[target,a,18,2]
        theta=data['theta'][meta['life']].copy()
    return records,theta,parent


def mosaic_expected(refs):
    detail=previous.templates()[2]; result=np.empty((2,4,16,16),dtype=np.float64)
    for h in range(2):
        for m,(inside,outside) in enumerate(FACTORS):
            for y in range(16):
                for x in range(16): result[h,m,y,x]=refs[h,inside if detail[y,x] else outside,y,x]
    return result


def observations(states,cfg):
    targets,coarse,detail=previous.templates(); result=np.empty((*states.shape[:-3],10),dtype=np.float64)
    for address in np.ndindex(states.shape[:-3]):
        v,_,ref=states[address]; qualified=np.abs(v)>cfg.amp_threshold
        a=((v>0)==(targets[0]>0)) & qualified; b=((v>0)==(targets[1]>0)) & qualified
        ac=np.count_nonzero(a & detail)/16; bc=np.count_nonzero(b & detail)/16
        result[address]=[ac,bc,ac-bc,np.count_nonzero(qualified & detail)/16,
            np.count_nonzero(((v>0)==(coarse>0)) & qualified & ~detail)/240,
            np.sum((ref*targets[0])[detail])/16,np.sum(ref)/256,np.sqrt(np.sum(ref**2)/256),
            np.count_nonzero(a)/256,np.count_nonzero(b)/256]
    return result


def check_life(raw,meta,cfg,replay=True):
    shapes=dict(theta=(16,16),recipient=(3,16,16),source_R=(2,2,16,16),mosaics=(2,4,16,16),
        states=(2,4,2,4,3,16,16),fresh=(1,16,16),control=(2,4,2,1,cfg.teaching,7),copy_map=(1,256),
        pre_repair=(2,4,2,1,16,16),values=(2,4,2,4,10))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key=='fresh': assert raw[key].dtype==np.bool_ and raw[key].sum()==128
        elif key=='copy_map': assert raw[key].dtype==np.int64
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); assert meta['tag']==TAG and meta['theta_writable'] is False
    assert type(meta['life']) is int and 0<=meta['life']<2
    for name,values in (('histories',HISTORIES),('mosaics',MOSAICS),('readers',READERS),('phases',PHASES)):
        nested(meta[name],list(values))
    nested(meta['factors'],[list(x) for x in FACTORS])
    refs,theta,parent=source_expected(meta)
    np.testing.assert_array_equal(raw['source_R'],refs); np.testing.assert_array_equal(raw['theta'],theta)
    tissue,ladder,bp=physics.parameters(meta | dict(index=parent))
    np.testing.assert_array_equal(raw['mosaics'],mosaic_expected(refs))
    for h in range(2):
        np.testing.assert_array_equal(raw['mosaics'][h,0],refs[h,0]); np.testing.assert_array_equal(raw['mosaics'][h,3],refs[h,1])
    for key in ('branch_rng','copy_rng'):
        assert len(meta[key])==2 and all(len(h)==4 for h in meta[key])
        assert all(len(m)==2 for h in meta[key] for m in h)
        assert all(len(r)==1 and r==meta[key][0][0][0] for h in meta[key] for m in h for r in m)
    copy_random=generator(TAG,meta['index'],meta['life'],'copy:1')
    mapping=previous.copy.draw_map(copy_random,32)
    np.testing.assert_array_equal(raw['copy_map'][0],mapping)
    assert meta['copy_rng'][0][0][0][0]==canonical_digest(copy_random.bit_generator.state)
    for h in range(2):
        for m in range(4):
            for r in range(2):
                path=raw['states'][h,m,r]; record=raw['mosaics'][h,m]
                np.testing.assert_array_equal(path[0,:2],raw['recipient'][:2])
                np.testing.assert_array_equal(path[:,2],np.broadcast_to(record,(4,16,16)))
                np.testing.assert_array_equal(raw['pre_repair'][h,m,r,0],record)
                trace=raw['control'][h,m,r,0]; assert np.max(np.abs(trace[:,1]))<=1e-12
                assert abs(trace[0,0]-path[1,0].mean())<=1e-12 and abs(trace[-1,6]-path[2,0].mean())<=1e-12
                if r==1:
                    np.testing.assert_array_equal(path[:,:2],raw['states'][0,0,1,:,:2])
                    np.testing.assert_array_equal(raw['control'][h,m,r],raw['control'][0,0,1])
    np.testing.assert_allclose(raw['values'],observations(raw['states'],cfg),rtol=0,atol=1e-12)
    error=0.
    if replay:
        index,life=meta['index'],meta['life']; random=generator(TAG,index,life,'recipient')
        recipient,theta=physics.settle(tissue,ladder,random,1,cfg.settle)
        error=max(compare(raw['recipient'],recipient[:,0]),compare(raw['theta'],theta))
        assert meta['recipient_rng']==canonical_digest(random.bit_generator.state)
        expected_mosaics=mosaic_expected(refs)
        for h in range(2):
            for m in range(4):
                for r in range(2):
                    state=recipient.copy(); state[2,0]=expected_mosaics[h,m]
                    random=generator(TAG,index,life,'branch:1'); gain=.2 if r==0 else 0.
                    phases,mask,trace,copied=previous.oldcheck.one_cycle(state,theta,tissue,ladder,replace(bp,c_m=gain,rho=0.),
                        random,mapping,False,False,cfg)
                    error=max(error,compare(raw['states'][h,m,r,1:],phases[:,:,0]))
                    np.testing.assert_array_equal(raw['fresh'][0],mask[0])
                    np.testing.assert_allclose(raw['control'][h,m,r,0],trace,rtol=0,atol=1e-12)
                    assert meta['branch_rng'][h][m][r][0]==canonical_digest(random.bit_generator.state)
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,retained_source_R_verified=True,
        same_source_theta=True,fresh_common_recipient=True,regional_mosaics_verified=True,
        intact_sham_identity=True,paired_masks_streams=True,unchanged_R_readout=True,
        off_bodies_control_alias=True,public_zero_mean_verified=True,observers_verified=True)


def check_block(raw,meta,cfg,replay=True):
    nested(meta['config'],asdict(cfg)); assert type(meta['index']) is int
    assert len(meta['lives'])==2 and all(x.shape[0]==2 for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life and record['exact_alias_branches']==2
        result=check_life({k:v[life] for k,v in raw.items()},record,cfg,replay)
        if replay: nested(record['replay'],result)
        else:
            expected=result | dict(full_life_replay=True,max_abs=record['replay']['max_abs'])
            assert 0<=expected['max_abs']<=1e-10; nested(record['replay'],expected)
    return True


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    values=np.asarray([[observations(b['states'][life],cfg) for life in range(2)] for b in blocks])
    control=np.asarray([b['control'] for b in blocks]); samples=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8))
    def stats(lives):
        means=np.array([x.mean() for x in lives])
        out=dict(mean=float(means.mean()),block_means=means.tolist(),life_values=lives.tolist(),
            pointwise_block_bootstrap_95=np.quantile(means[samples].mean(axis=1),[.025,.975]).tolist())
        for prefix,x in (('block_',means),('life_',lives)):
            out[prefix+'positive']=int((x>1e-12).sum()); out[prefix+'negative']=int((x< -1e-12).sum())
            out[prefix+'tied']=int((abs(x)<=1e-12).sum())
        return out
    contrasts=[]
    for h,history in enumerate(HISTORIES):
        for phase in (3,2):
            for reader in ('on','off','on_minus_off'):
                if reader=='on_minus_off': score=values[:,:,h,:,0,phase,2]-values[:,:,h,:,1,phase,2]
                else: score=values[:,:,h,:,READERS.index(reader),phase,2]
                for name,coefficients in CONTRASTS:
                    effect=np.zeros((8,2))
                    for m in range(4):
                        if coefficients[m]: effect+=coefficients[m]*score[:,:,m]
                    contrasts.append(dict(history=history,phase=PHASES[phase],reader=reader,name=name,**stats(effect)))
    def select(history,name):
        return next(x for x in contrasts if x['history']==history and x['phase']=='free_end'
            and x['reader']=='on_minus_off' and x['name']==name)
    readability=[]
    for history in HISTORIES:
        effect=select(history,'full_record_identity')
        readability.append(dict(history=history,qualified=effect['pointwise_block_bootstrap_95'][0]>0,effect=effect))
    primary=select('repaired','inside_minus_outside'); lower,upper=primary['pointwise_block_bootstrap_95']
    if not readability[1]['qualified']: label='REPAIRED_RECORD_READ_NOT_QUALIFIED'
    elif lower>0: label='LANDMARK_REGION_DOMINATES'
    elif upper<0: label='SURROUNDING_REGION_DOMINATES'
    else: label='REGIONAL_ATTRIBUTION_UNRESOLVED'
    trajectories=[]
    for h,history in enumerate(HISTORIES):
        for m,mosaic in enumerate(MOSAICS):
            for r,reader in enumerate(READERS):
                for s,phase in enumerate(PHASES):
                    trajectories.append(dict(history=history,mosaic=mosaic,reader=reader,phase=phase,
                        A_detail=stats(values[:,:,h,m,r,s,0]),B_detail=stats(values[:,:,h,m,r,s,1]),
                        preference=stats(values[:,:,h,m,r,s,2]),coarse=stats(values[:,:,h,m,r,s,4])))
    residual=float(abs(control[...,1]).max()); assert residual<=1e-12
    expected=dict(schema='l19_record_localisation_summary_v1',label=label,primary=primary,readability=readability,
        contrasts=contrasts,trajectories=trajectories,cell_means=values.mean(axis=(0,1)).tolist(),
        tissues=list(range(52000,52008)),source_tissues=list(range(51000,51008)),histories=list(HISTORIES),
        mosaics=list(MOSAICS),readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),
        blocks=8,lives_per_block=2,landmark_cells=16,complement_cells=240,max_controlled_mean_residual=residual,
        absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False,
        source_records_previously_observed=True,fresh_physical_tissue_parameters=False)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_record_localisation_run import main
    main(default_command='audit')
