"""D109 independent native-parent replay, in-block transfer and fixed factorial audit."""
from dataclasses import asdict,replace
from pathlib import Path

import numpy as np

from laws_confirmation import l19_written_landmarks as prior
from laws_confirmation import l15_repair_speed_run as files
from laws_confirmation.io import canonical_digest,external_root,sha256_file

previous=prior.checker(); old=previous.old; physics=previous.physics
nested,compare,generator=previous.nested,previous.compare,previous.generator
TAG='l19-fresh-halo-v1'
HISTORIES=('clean','repaired'); MOSAICS=('AAA','AAB','ABA','ABB','BAA','BAB','BBA','BBB'); READERS=('on','off')
PHASES=('initial','birth','support_end','free_end')
METRICS=('A_detail','B_detail','A_minus_B','detail_amplitude','coarse_body',
    'R_A_projection','R_mean','R_rms','whole_A','whole_B')
REGIONS=('landmark','near','far')
FACTORS=((0,0,0),(0,0,1),(0,1,0),(0,1,1),(1,0,0),(1,0,1),(1,1,0),(1,1,1))
CONTRASTS=(('full_record_identity',(.5,0,0,0,0,0,0,-.5)),)
SIGN_ROWS=(
    ('landmark_main',(1,1,1,1,-1,-1,-1,-1)),
    ('near_main',(1,1,-1,-1,1,1,-1,-1)),
    ('far_main',(1,-1,1,-1,1,-1,1,-1)),
    ('landmark_near_interaction',(1,1,-1,-1,-1,-1,1,1)),
    ('landmark_far_interaction',(1,-1,1,-1,-1,1,-1,1)),
    ('near_far_interaction',(1,-1,-1,1,1,-1,-1,1)),
    ('three_way_interaction',(1,-1,-1,1,-1,1,1,-1)))
CONTRASTS+=tuple((name,tuple(x/8 for x in row)) for name,row in SIGN_ROWS)
CONTRASTS+=(('near_minus_far',(0,.25,-.25,0,0,.25,-.25,0)),
    ('coupled_outside_contribution',(.25,0,0,-.25,.25,0,0,-.25)),
    ('coupled_landmark_contribution',(.25,0,0,.25,-.25,0,0,-.25)),
    ('coupled_inside_minus_outside',(0,0,0,.5,-.5,0,0,0)))
# Half A-minus-B at each of the four fixed backgrounds, independently indexed.
for region,axis in zip(REGIONS,(0,1,2)):
    others=tuple(k for k in (0,1,2) if k!=axis)
    for a in (0,1):
        for b in (0,1):
            row=[0.]*8
            address=[0,0,0]; address[others[0]]=a; address[others[1]]=b
            for value,weight in ((0,.5),(1,-.5)):
                address[axis]=value
                row[4*address[0]+2*address[1]+address[2]]=weight
            name=region+'_at_'+REGIONS[others[0]]+'_'+'AB'[a]+'_'+REGIONS[others[1]]+'_'+'AB'[b]
            CONTRASTS+=((name,tuple(row)),)


def source_expected(raw,meta,parent_cfg,replay):
    index=meta['index']; assert type(index) is int
    if index==514210: parent=514209
    else:
        assert 55000<=index<=55007
        parent=index-1000
    expected=dict(source_index=parent,source_run='l19_fresh_halo_v1_attempt1',source_cycle=parent_cfg.cycles,
        source_arms=['clean_on','repaired_on'],source_seed_tag='l19-written-landmarks-v1',
        source_storage='parent_* arrays in this block',known_source_outcomes=False,
        fresh_physical_tissue_parameters=True)
    nested(meta['source'],expected); nested(meta['parent_config'],asdict(parent_cfg))
    parent_meta=meta['parent']
    assert type(parent_meta['index']) is int and parent_meta['index']==parent
    assert type(parent_meta['life']) is int and parent_meta['life']==meta['life']
    assert parent_meta['qualification'] is False and parent_meta['exact_alias_branches']==1
    parent_replay=previous.check_life(raw,parent_meta,parent_cfg,replay)
    records=np.empty((2,2,16,16),dtype=np.float64)
    for h,arm in enumerate((0,2)):
        for target in range(2): records[h,target]=raw['states'][target,arm,3*parent_cfg.cycles,2]
    return records,raw['theta'],parent,parent_replay


def masks_expected():
    detail=previous.templates()[2]; near=np.zeros((16,16),dtype=bool)
    for y in range(16):
        for x in range(16):
            if not detail[y,x]:
                near[y,x]=any(detail[(y+dy)%16,(x+dx)%16] for dy in (-1,0,1) for dx in (-1,0,1))
    return np.stack((detail,near,~(detail|near)))


def mosaic_expected(refs):
    masks=masks_expected(); result=np.empty((2,8,16,16),dtype=np.float64)
    for h in range(2):
        for m,factors in enumerate(FACTORS):
            for y in range(16):
                for x in range(16):
                    region=0 if masks[0,y,x] else 1 if masks[1,y,x] else 2
                    result[h,m,y,x]=refs[h,factors[region],y,x]
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


def check_life(raw,meta,cfg,parent_cfg=prior.CONFIG,replay=True):
    parent_raw={k[7:]:v for k,v in raw.items() if k.startswith('parent_')}
    raw={k:v for k,v in raw.items() if not k.startswith('parent_')}
    shapes=dict(regions=(3,16,16),theta=(16,16),recipient=(3,16,16),source_R=(2,2,16,16),mosaics=(2,8,16,16),
        states=(2,8,2,4,3,16,16),fresh=(1,16,16),control=(2,8,2,1,cfg.teaching,7),copy_map=(1,256),
        pre_repair=(2,8,2,1,16,16),values=(2,8,2,4,10))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        assert raw[key].shape==shape
        if key=='regions': assert raw[key].dtype==np.bool_
        elif key=='fresh': assert raw[key].dtype==np.bool_ and raw[key].sum()==128
        elif key=='copy_map': assert raw[key].dtype==np.int64
        else: assert raw[key].dtype==np.float64 and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); assert meta['tag']==TAG and meta['theta_writable'] is False
    assert type(meta['life']) is int and 0<=meta['life']<2
    for name,values in (('histories',HISTORIES),('mosaics',MOSAICS),('readers',READERS),('phases',PHASES)):
        nested(meta[name],list(values))
    nested(meta['factors'],[list(x) for x in FACTORS])
    nested(meta['region_names'],list(REGIONS)); nested(meta['region_sizes'],[16,48,192])
    assert meta['partition']=='periodic_chebyshev_one_cell_ring'
    np.testing.assert_array_equal(raw['regions'],masks_expected())
    np.testing.assert_array_equal(raw['regions'].sum((1,2)),[16,48,192])
    assert np.all(raw['regions'].sum(axis=0)==1)
    refs,theta,parent,parent_replay=source_expected(parent_raw,meta,parent_cfg,replay)
    np.testing.assert_array_equal(raw['source_R'],refs); np.testing.assert_array_equal(raw['theta'],theta)
    tissue,ladder,bp=physics.parameters(meta | dict(index=parent))
    np.testing.assert_array_equal(raw['mosaics'],mosaic_expected(refs))
    for h in range(2):
        np.testing.assert_array_equal(raw['mosaics'][h,0],refs[h,0]); np.testing.assert_array_equal(raw['mosaics'][h,7],refs[h,1])
    for key in ('branch_rng','copy_rng'):
        assert len(meta[key])==2 and all(len(h)==8 for h in meta[key])
        assert all(len(m)==2 for h in meta[key] for m in h)
        assert all(len(r)==1 and r==meta[key][0][0][0] for h in meta[key] for m in h for r in m)
    copy_random=generator(TAG,meta['index'],meta['life'],'copy:1')
    mapping=previous.copy.draw_map(copy_random,32)
    np.testing.assert_array_equal(raw['copy_map'][0],mapping)
    assert meta['copy_rng'][0][0][0][0]==canonical_digest(copy_random.bit_generator.state)
    for h in range(2):
        for m in range(8):
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
    error=parent_replay['max_abs']
    if replay:
        index,life=meta['index'],meta['life']; random=generator(TAG,index,life,'recipient')
        recipient,theta=physics.settle(tissue,ladder,random,1,cfg.settle)
        error=max(error,compare(raw['recipient'],recipient[:,0]),compare(raw['theta'],theta))
        assert meta['recipient_rng']==canonical_digest(random.bit_generator.state)
        expected_mosaics=mosaic_expected(refs)
        for h in range(2):
            for m in range(8):
                for r in range(2):
                    state=recipient.copy(); state[2,0]=expected_mosaics[h,m]
                    random=generator(TAG,index,life,'branch:1'); gain=.2 if r==0 else 0.
                    phases,mask,trace,copied=previous.oldcheck.one_cycle(state,theta,tissue,ladder,replace(bp,c_m=gain,rho=0.),
                        random,mapping,False,False,cfg)
                    error=max(error,compare(raw['states'][h,m,r,1:],phases[:,:,0]))
                    np.testing.assert_array_equal(raw['fresh'][0],mask[0])
                    np.testing.assert_allclose(raw['control'][h,m,r,0],trace,rtol=0,atol=1e-12)
                    assert meta['branch_rng'][h][m][r][0]==canonical_digest(random.bit_generator.state)
    return dict(full_life_replay=replay,max_abs=error,exact_signs=True,fresh_source_R_verified=True,parent_replay=parent_replay,
        same_source_theta=True,fresh_common_recipient=True,regional_mosaics_verified=True,
        intact_sham_identity=True,paired_masks_streams=True,unchanged_R_readout=True,
        off_bodies_control_alias=True,public_zero_mean_verified=True,observers_verified=True)


def check_block(raw,meta,cfg,replay=True,parent_cfg=prior.CONFIG):
    nested(meta['parent_config'],asdict(parent_cfg))
    nested(meta['config'],asdict(cfg)); assert type(meta['index']) is int
    assert len(meta['lives'])==2 and all(x.shape[0]==2 for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life and record['exact_alias_branches']==2
        result=check_life({k:v[life] for k,v in raw.items()},record,cfg,parent_cfg,replay)
        if replay: nested(record['replay'],result)
        else:
            expected=result | dict(full_life_replay=True,max_abs=record['replay']['max_abs'])
            parent_expected=result['parent_replay'] | dict(full_life_replay=True,
                max_abs=record['replay']['parent_replay']['max_abs'])
            expected['parent_replay']=parent_expected
            assert 0<=parent_expected['max_abs']<=expected['max_abs']<=1e-10
            nested(record['replay'],expected)
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
                    for m in range(8):
                        if coefficients[m]: effect+=coefficients[m]*score[:,:,m]
                    contrasts.append(dict(history=history,phase=PHASES[phase],reader=reader,name=name,**stats(effect)))
    def select(history,name):
        return next(x for x in contrasts if x['history']==history and x['phase']=='free_end'
            and x['reader']=='on_minus_off' and x['name']==name)
    readability=[]
    for history in HISTORIES:
        intact=select(history,'full_record_identity'); outside=select(history,'coupled_outside_contribution')
        iq=intact['pointwise_block_bootstrap_95'][0]>0; oq=outside['pointwise_block_bootstrap_95'][0]>0
        readability.append(dict(history=history,qualified=iq and oq,intact_qualified=iq,outside_qualified=oq,
            intact_effect=intact,outside_effect=outside))
    primary=select('repaired','near_minus_far'); lower,upper=primary['pointwise_block_bootstrap_95']
    if not readability[1]['intact_qualified']: label='REPAIRED_RECORD_READ_NOT_QUALIFIED'
    elif not readability[1]['outside_qualified']: label='REPAIRED_OUTSIDE_SIGNAL_NOT_QUALIFIED'
    elif lower>0: label='NEAR_HALO_DOMINATES'
    elif upper<0: label='DISTANT_REGION_DOMINATES'
    else: label='NEAR_FAR_ATTRIBUTION_UNRESOLVED'
    trajectories=[]
    for h,history in enumerate(HISTORIES):
        for m,mosaic in enumerate(MOSAICS):
            for r,reader in enumerate(READERS):
                for s,phase in enumerate(PHASES):
                    trajectories.append(dict(history=history,mosaic=mosaic,reader=reader,phase=phase,
                        A_detail=stats(values[:,:,h,m,r,s,0]),B_detail=stats(values[:,:,h,m,r,s,1]),
                        preference=stats(values[:,:,h,m,r,s,2]),coarse=stats(values[:,:,h,m,r,s,4])))
    residual=float(abs(control[...,1]).max()); assert residual<=1e-12
    expected=dict(schema='l19_fresh_halo_summary_v1',label=label,primary=primary,readability=readability,
        contrasts=contrasts,trajectories=trajectories,cell_means=values.mean(axis=(0,1)).tolist(),
        tissues=list(range(55000,55008)),source_tissues=list(range(54000,54008)),histories=list(HISTORIES),
        mosaics=list(MOSAICS),readers=list(READERS),phases=list(PHASES),metrics=list(METRICS),
        blocks=8,lives_per_block=2,landmark_cells=16,near_cells=48,far_cells=192,complement_cells=240,
        region_names=list(REGIONS),max_controlled_mean_residual=residual,
        absolute_fidelity_gate=None,secondary_intervals_multiplicity_adjusted=False,
        source_records_previously_observed=False,fresh_physical_tissue_parameters=True)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l19_fresh_halo_run import main
    main(default_command='audit')
