"""Independent D117 lifecycle/byte lineage/observer and block inference checks."""
from dataclasses import asdict
import hashlib

import numpy as np

from laws_confirmation import l20_acquisition as previous
from laws_confirmation.io import canonical_digest

prior=previous.checker(); physics=prior.physics
compare,nested,generator=physics.compare,physics.nested,physics.generator
project,update,stats,check_source=prior.project,prior.update,prior.independent_stats,prior.check_source
TAG='l20-three-rewrite-v1'; PARENT_TAG='l20-acquisition-only-v1'
KINDS=('rewrite','live','copy','write_off','read_off','wrong','lesion','rescue')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PROBES=tuple((r,k) for r in (0,1) for k in KINDS+('ideal','zero'))
METRICS=('own_qualified','alternative_qualified','own_sign','alternative_sign','amp_fraction','body_mean',
    'body_rms','clip_fraction','roughness','reference_mean','reference_rms','vr_mae')


def packet(field): return field.astype('<f8').tobytes(order='C')
def unpack(value): return np.frombuffer(value,dtype='<f8').reshape(16,16).copy()
def sha(value): return hashlib.sha256(value).hexdigest()


def observe(states,targets,cases,cfg):
    result=np.empty(states.shape[:-3]+(12,))
    for ci,(role,_) in enumerate(cases):
        for address in np.ndindex(states[ci].shape[:-3]):
            v,_,ref=states[(ci,)+address]; eligible=abs(v)>cfg.amp_threshold
            own,other=(v>0)==(targets[role]>0),(v>0)==(targets[1-role]>0)
            rough=(abs(v-v[:,(np.arange(16)-1)%16]).sum()+abs(v-v[(np.arange(16)-1)%16,:]).sum())/512
            result[(ci,)+address]=[np.count_nonzero(own & eligible)/256,np.count_nonzero(other & eligible)/256,
                own.sum()/256,other.sum()/256,eligible.sum()/256,v.sum()/256,np.sqrt((v*v).sum()/256),
                np.count_nonzero(abs(v)==2)/256,rough,ref.sum()/256,np.sqrt((ref*ref).sum()/256),abs(v-ref).sum()/256]
    return result


def check_founders(raw,meta,cfg,replay):
    tissue,ladder,bp=physics.parameters(meta); index,life=meta['index'],meta['life']
    np.testing.assert_array_equal(raw['targets'],prior.targets())
    native=tissue.threshold_spread*generator(tissue.tissue_tag,index).standard_normal((16,16))
    theta=project(native); np.testing.assert_array_equal(raw['native_theta'],native)
    np.testing.assert_array_equal(raw['theta0'],theta)
    random=generator(PARENT_TAG,index,life,'parent_birth'); v=np.full((1,16,16),-1.); v[:,:,:8]=1.
    v=v+tissue.copy_jitter*random.standard_normal(v.shape); state=(v,v.copy(),v.copy())
    np.testing.assert_array_equal(raw['parent_birth'],np.stack(state)[:,0])
    assert meta['parent_birth_rng']==canonical_digest(random.bit_generator.state)
    random=generator(PARENT_TAG,index,life,'parent_settle'); maximum=0.
    for _ in range(cfg.settle):
        noise=random.standard_normal((1,16,16))
        if replay: state=physics.step(*state,theta,tissue,ladder,bp.c_m,bp.rho,noise)
    if replay: maximum=max(maximum,compare(raw['settled'],np.stack(state)[:,0]))
    assert meta['parent_settle_rng']==canonical_digest(random.bit_generator.state)
    endings=[]
    for role in (0,1):
        state=tuple(x[None].copy() for x in raw['settled']); field=theta[None].copy()
        initial=np.stack((*state,field))[:,0]; np.testing.assert_array_equal(raw['founder_states'][role,0],initial)
        saved=[initial]; random=generator(PARENT_TAG,index,life,'teaching')
        for t in range(1,cfg.teaching+1):
            noise=random.standard_normal((1,16,16))
            if replay:
                state=(1.2*prior.targets()[role][None],state[1],state[2])
                state,field=update(state,field,tissue,ladder,bp,noise,True)
                if t in cfg.parent_times: saved.append(np.stack((*state,field))[:,0])
        if replay: maximum=max(maximum,compare(raw['founder_states'][role],np.stack(saved)))
        assert raw['founder_packets'][role].tobytes()==packet(raw['founder_states'][role,-1,3])
        endings.append(canonical_digest(random.bit_generator.state))
    nested(meta['teaching_rng'],endings); assert len(set(endings))==1
    return maximum


def check_life(raw,meta,cfg,replay=True):
    keys={'index','life','config','cases','probes','tissue','ladder','blueprint','parent_birth_rng','parent_settle_rng',
        'teaching_rng','generations','terminal','times','probe_times','parent_tag','descendant_tag',
        'ordinary_packet_bytes','rescue_g1_extra_bytes','descendant_target_labels','renewal_generations','terminal_extra_transfer'}
    assert set(meta) in (keys,keys|{'replay'})
    shapes=dict(native_theta=(16,16),theta0=(16,16),parent_birth=(3,16,16),settled=(3,16,16),targets=(2,16,16),
        founder_states=(2,len(cfg.parent_times),4,16,16),permutations=(2,256),founder_packets=(2,2048),
        generation_states=(16,3,len(cfg.times),4,16,16),write_birth=(16,3,4,16,16),incoming=(16,3,2048),
        outgoing=(16,3,2048),probe_packets=(20,2048),probe_states=(20,len(cfg.probe_times),3,16,16),
        values=(16,3,len(cfg.times),12),probe_values=(20,len(cfg.probe_times),12))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        dtype=np.uint8 if key in ('founder_packets','incoming','outgoing','probe_packets') else np.int64 if key=='permutations' else np.float64
        assert raw[key].shape==shape and raw[key].dtype==dtype and np.isfinite(raw[key]).all()
    nested(meta['config'],asdict(cfg)); nested(meta['cases'],[list(c) for c in CASES]); nested(meta['probes'],[list(c) for c in PROBES])
    nested(meta['times'],list(cfg.times)); nested(meta['probe_times'],list(cfg.probe_times))
    assert meta['parent_tag']==PARENT_TAG and meta['descendant_tag']==TAG
    assert meta['ordinary_packet_bytes']==2048 and meta['rescue_g1_extra_bytes']==2048
    assert meta['descendant_target_labels'] is False and meta['renewal_generations']==3 and meta['terminal_extra_transfer'] is True
    tissue,ladder,bp=physics.parameters(meta); index,life=meta['index'],meta['life']
    assert type(life) is int and 0<=life<cfg.lives
    maximum=check_founders(raw,meta,cfg,replay)
    permutations=np.stack([generator(TAG,index,life,f'lesion:{r}').permutation(256) for r in (0,1)])
    np.testing.assert_array_equal(raw['permutations'],permutations)
    generations=[]
    for ci,(role,kind) in enumerate(CASES):
        initial=raw['founder_packets'][role].tobytes()
        if kind=='wrong': initial=raw['founder_packets'][1-role].tobytes()
        elif kind in ('lesion','rescue'):
            initial=packet(unpack(initial).ravel()[permutations[role]].reshape(16,16))
            np.testing.assert_array_equal(np.sort(unpack(initial).ravel()),np.sort(raw['founder_states'][role,-1,3].ravel()))
        records=[]
        for gi,g in enumerate((1,2,3)):
            incoming=initial if g==1 else raw['outgoing'][ci,gi-1].tobytes()
            assert raw['incoming'][ci,gi].tobytes()==incoming
            field=unpack(incoming); has_backup=kind=='rescue' and g==1
            backup=raw['founder_packets'][role].tobytes() if has_backup else None
            random=generator(TAG,index,life,f'g{g}:birth'); v=.2*random.standard_normal((1,16,16))
            birth_rng=canonical_digest(random.bit_generator.state); state=(v,v.copy(),v.copy())
            start=np.stack((*state,field[None]))[:,0]
            np.testing.assert_array_equal(raw['generation_states'][ci,gi,0],start)
            random=generator(TAG,index,life,f'g{g}:read'); saved=[start]
            for t in range(1,cfg.read_steps+1):
                if has_backup and t==cfg.rescue_after+1: field=unpack(backup)
                noise=random.standard_normal((1,16,16))
                if replay:
                    applied=field if kind!='read_off' else np.zeros_like(field)
                    state=physics.step(*state,applied,tissue,ladder,0.,bp.rho,noise)
                    if t in cfg.read_times: saved.append(np.stack((*state,field[None]))[:,0])
            read_rng=canonical_digest(random.bit_generator.state)
            # Validate erasure independently of whether dynamics are replayed now.
            read_end=raw['generation_states'][ci,gi,cfg.times.index(cfg.read_steps),:3]
            write_field=field.copy() if kind in ('live','copy') else np.zeros_like(field)
            expected_wb=np.concatenate((read_end,write_field[None]))
            np.testing.assert_array_equal(raw['write_birth'][ci,gi],expected_wb)
            if replay:
                maximum=max(maximum,compare(raw['generation_states'][ci,gi,:len(cfg.read_times)],np.stack(saved)))
                maximum=max(maximum,compare(read_end,np.stack(state)[:,0]))
            state=tuple(x[None].copy() for x in read_end); theta=write_field[None].copy()
            random=generator(TAG,index,life,f'g{g}:write'); written=[]
            writing=kind not in ('copy','write_off')
            for t in range(1,cfg.write_steps+1):
                noise=random.standard_normal((1,16,16))
                if replay:
                    state,theta=update(state,theta,tissue,ladder,bp,noise,writing)
                    if t in cfg.write_times: written.append(np.stack((*state,theta))[:,0])
            if replay: maximum=max(maximum,compare(raw['generation_states'][ci,gi,len(cfg.read_times):],np.stack(written)))
            last=raw['generation_states'][ci,gi,-1,3]; output=raw['outgoing'][ci,gi].tobytes()
            assert output==packet(last)
            if kind=='copy': assert output==initial
            if kind=='write_off': np.testing.assert_array_equal(last,np.zeros((16,16)))
            else: assert abs(float(last.std())-.3)<=1e-14 and abs(float(last.mean()))<=1e-14
            records.append(dict(generation=g,kind=kind,birth_rng=birth_rng,read_rng=read_rng,
                write_rng=canonical_digest(random.bit_generator.state),input_sha256=sha(incoming),output_sha256=sha(output),
                rescue_sha256=sha(backup) if has_backup else None,available_packet_bytes=4096 if has_backup else 2048,
                erased_before_writing=kind not in ('live','copy'),inherited_reader_enabled=kind!='read_off',writing_enabled=writing))
        generations.append(records)
    nested(meta['generations'],generations)
    terminal=[]
    for pi,(role,kind) in enumerate(PROBES):
        if kind=='ideal': expected=packet(project(np.tanh(1.5*prior.targets()[role])))
        elif kind=='zero': expected=packet(np.zeros((16,16)))
        else: expected=raw['outgoing'][CASES.index((role,kind)),-1].tobytes()
        assert raw['probe_packets'][pi].tobytes()==expected
        field=unpack(expected); random=generator(TAG,index,life,'terminal:birth')
        v=.2*random.standard_normal((1,16,16)); birth_rng=canonical_digest(random.bit_generator.state)
        state=(v,v.copy(),v.copy()); saved=[np.stack(state)[:,0]]
        np.testing.assert_array_equal(raw['probe_states'][pi,0],saved[0])
        random=generator(TAG,index,life,'terminal:read')
        for t in range(1,cfg.read_steps+1):
            noise=random.standard_normal((1,16,16))
            if replay:
                state=physics.step(*state,field,tissue,ladder,0.,bp.rho,noise)
                if t in cfg.probe_times: saved.append(np.stack(state)[:,0])
        if replay: maximum=max(maximum,compare(raw['probe_states'][pi],np.stack(saved)))
        terminal.append(dict(birth_rng=birth_rng,read_rng=canonical_digest(random.bit_generator.state),
            input_sha256=sha(expected),packet_bytes=2048,writing=False,gain=0.))
    nested(meta['terminal'],terminal)
    aliases=[((0,'rewrite'),(1,'wrong')),((1,'rewrite'),(0,'wrong')),((0,'write_off'),(1,'write_off')),
             ((0,'write_off'),(0,'zero')),((0,'zero'),(1,'zero')),((0,'read_off'),(1,'read_off'))]
    for a,b in aliases: np.testing.assert_array_equal(raw['probe_states'][PROBES.index(a)],raw['probe_states'][PROBES.index(b)])
    values=observe(raw['generation_states'][:,:,:,:3],raw['targets'],CASES,cfg)
    probes=observe(raw['probe_states'],raw['targets'],PROBES,cfg)
    np.testing.assert_allclose(raw['values'],values,atol=1e-12,rtol=0)
    np.testing.assert_allclose(raw['probe_values'],probes,atol=1e-12,rtol=0)
    return dict(full_life_replay=replay,dynamics_max_abs=maximum,
        metric_max_abs=max(float(abs(raw['values']-values).max()),float(abs(raw['probe_values']-probes).max())),
        exact_terminal_aliases=6,founder_paths=2,generation_paths=48,terminal_paths=20,
        primary_erased_writes=6,packet_lineage_checked=True,explicit_rescue_exception=True,exact_signs=True)


def check_block(raw,meta,cfg,replay=True):
    assert set(meta)=={'index','config','lives'} and type(meta['index']) is int
    assert meta['index'] in (*range(60000,60008),514217)
    nested(meta['config'],asdict(cfg)); assert len(meta['lives'])==cfg.lives
    assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,row in enumerate(meta['lives']):
        assert row['index']==meta['index'] and row['life']==life
        proof=row['replay']
        assert set(proof)=={'full_life_replay','dynamics_max_abs','metric_max_abs','exact_terminal_aliases','founder_paths',
            'generation_paths','terminal_paths','primary_erased_writes','packet_lineage_checked','explicit_rescue_exception','exact_signs'}
        assert all(proof[k] is True for k in ('full_life_replay','packet_lineage_checked','explicit_rescue_exception','exact_signs'))
        assert (proof['exact_terminal_aliases'],proof['founder_paths'],proof['generation_paths'],proof['terminal_paths'],proof['primary_erased_writes'])==(6,2,48,20,6)
        assert 0<=proof['dynamics_max_abs']<=1e-10 and 0<=proof['metric_max_abs']<=1e-12
        current=check_life({k:x[life] for k,x in raw.items()},row,cfg,replay)
        if replay: nested(proof,current)
    return True


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    v=np.stack([b['values'] for b in blocks]); q=np.stack([b['probe_values'] for b in blocks])
    assert v.shape==(8,cfg.lives,16,3,len(cfg.times),12) and q.shape==(8,cfg.lives,20,len(cfg.probe_times),12)
    assert np.isfinite(v).all() and np.isfinite(q).all()
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8)); rows=[]
    pairs=(('rewrite','read_off'),('rewrite','write_off'),('live','copy'),('rewrite','copy'),
           ('rewrite','wrong'),('rewrite','lesion'),('rescue','lesion'))
    for observer,col in (('qualified',0),('sign',2)):
        for stage in (1,2,3,4):
            readings=v[:,:,:,stage-1,list(cfg.times).index(cfg.read_steps)] if stage<4 else q[:,:,:,-1]
            cases=CASES if stage<4 else PROBES
            for left,right in pairs+((('ideal','zero'),('copy','zero')) if stage==4 else ()):
                effects=[]
                for role in (0,1):
                    li,ri=cases.index((role,left)),cases.index((role,right))
                    effects.append((readings[:,:,li,col]-readings[:,:,li,col+1])-(readings[:,:,ri,col]-readings[:,:,ri,col+1]))
                for role,effect in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=left+'_minus_'+right,stage=stage,role=role,observer=observer,**stats(effect,draws)))
    get=lambda name,stage=4,role='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(name,stage,role,'qualified'))
    primary=get('rewrite_minus_read_off'); directions=[get('rewrite_minus_read_off',role=r) for r in (0,1)]
    writer=get('rewrite_minus_write_off'); continuity=[get('rewrite_minus_read_off',stage=s) for s in (2,3,4)]
    gates=[get(n,role=r) for n in ('ideal_minus_zero','copy_minus_zero') for r in (0,1)]
    disagrees=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    readable=all(x>0 for row in disagrees for x in row) and all(x['pointwise_block_bootstrap_95'][0]>0 for x in gates)
    qualifies=all(x['pointwise_block_bootstrap_95'][0]>0 for x in continuity+[writer]) and all(
        get('rewrite_minus_read_off',stage=s,role=r)['mean']>0 for s in (2,3,4) for r in (0,1)) and all(
        get('rewrite_minus_write_off',role=r)['mean']>0 for r in (0,1))
    expected=dict(schema='l20_three_boundary_rewrite_v1',tissues=list(range(60000,60008)),
        label='READOUT_NOT_QUALIFIED' if not readable else 'QUALIFIED_READ_ERASE_REWRITE' if qualifies else 'REWRITE_UNRESOLVED',
        primary=primary,directional_primary=directions,writer_control=writer,continuity=continuity,readout_gates=gates,
        readout_qualified=bool(readable),target_disagreement_cells=disagrees,contrasts=rows,cases=[list(c) for c in CASES],
        probes=[list(c) for c in PROBES],times=list(cfg.times),probe_times=list(cfg.probe_times),metrics=list(METRICS),
        generation_cell_means=v.mean(axis=(0,1)).tolist(),probe_cell_means=q.mean(axis=(0,1)).tolist(),
        blocks=8,lives_per_block=cfg.lives,renewal_generations=3,transfer_interfaces_including_probe=4,
        ordinary_packet_bytes=2048,rescue_g1_available_bytes=4096,absolute_fidelity_gate=None,engineered_erasure=True,
        native_renewal_necessity=False,independent_confirmation=False,secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected); return True


if __name__=='__main__':
    from laws_confirmation.l20_three_rewrite_run import main
    main(default_command='audit')
