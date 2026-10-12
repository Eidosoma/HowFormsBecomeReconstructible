"""D131 independently restated training, selector, founder physics and inference."""
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l20_blind_alignment as old
from laws_confirmation.io import canonical_digest

prior=old.parent.checker();physics=prior.physics
previous=old.checker()
compare,nested,generator=physics.compare,physics.nested,physics.generator
project,observe,stats=prior.project,prior.observe,prior.stats
packet,unpack,sha=prior.packet,prior.unpack,prior.sha
TAG='l20-learned-guide-v1'
BASES=('native','learned','supplied','known','aligned','aligned_learned')
KINDS=('native','learned','supplied','known','aligned','aligned_learned',
    'native_shuffle','learned_shuffle','supplied_shuffle','known_shuffle','aligned_shuffle','aligned_learned_shuffle',
    'shuffle_learned','shuffle_supplied','aligned_shuffle_learned','wrong_guide','learned_sham',
    'learned_off','supplied_off','ideal','ideal_shifted','ideal_learned','ideal_supplied','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
METRICS=prior.METRICS
RULE='family tie: identity abstention; otherwise lexicographically first maximizing shift, then inverse'
FIT_RULE='arithmetic mean of all eight canonically aligned training packets per supplied family'
SOURCE_KEYS={'native_theta','theta0','parent_birth','settled','targets','founder_states','founder_packets',
    'pre_states','source_starts','source_shift','source_states','written_fields'}
SOURCE_META={'index','life','config','training','tag','modes','parent_times','times','source_times',
    'fresh_founders','reused_source_starts','source_theta_erased','source_shift_transmitted','source_gain','source_rho',
    'source_lambda','writer_rule','instructed_founders','unseen_pattern_families','parent_birth_rng','parent_settle_rng',
    'teaching_rng','pre_readers','writers','tissue','ladder','blueprint'}


def targets():
    y,x=np.indices((16,16))
    return np.stack((np.where(y<8,1.,-1.),np.where((x%8)<4,1.,-1.)))


def move(field,shift,inverse=True):
    dy,dx=map(int,shift);direction=1 if inverse else -1
    return field[np.ix_((np.arange(16)+direction*dy)%16,(np.arange(16)+direction*dx)%16)].copy()


def check_fit(packets,labels,guide):
    assert packets.dtype==np.uint8 and packets.shape==(16,2048)
    assert labels.dtype==np.int64 and labels.shape==(16,) and all(np.sum(labels==r)==8 for r in (0,1))
    assert guide.shape==(2,16,16) and guide.dtype==np.float64
    expected=np.zeros((2,16,16))
    for b,label in zip(packets,labels):expected[int(label)]+=unpack(b.tobytes())/8
    np.testing.assert_allclose(guide,expected,atol=1e-14,rtol=0)
    return float(np.max(abs(guide-expected)))


def select(supplied,guide):
    """FFT, separately normalized learned prototypes, modular permutation."""
    field=unpack(supplied);centered=field-field.mean();scale=float(np.sqrt(np.mean(centered**2)))
    scores=np.zeros((2,16,16))
    for r in (0,1):
        t=guide[r]-guide[r].mean();std=float(np.sqrt(np.mean(t*t)))
        assert std>1e-9
        if scale:scores[r]=np.fft.ifft2(np.fft.fft2(centered)*np.conj(np.fft.fft2(t))).real/(256*scale*std)
    maxima=np.max(scores,axis=(1,2));tie=bool(abs(maxima[0]-maxima[1])<=1e-12)
    family=-1 if tie else (0 if maxima[0]>maxima[1] else 1)
    mask=np.abs(scores-np.max(scores))<=1e-12;shift=(0,0)
    if not tie:
        mask=np.zeros((2,16,16),dtype=bool);mask[family]=abs(scores[family]-maxima[family])<=1e-12
        shift=min((y,x) for y in range(16) for x in range(16) if mask[family,y,x])
    output=packet(move(field,shift))
    return output,scores,dict(input_sha256=sha(supplied),output_sha256=sha(output),
        guide_sha256=sha(guide.astype('<f8').tobytes()),inferred_family=family,chosen_forward_shift=list(shift),
        family_maxima=maxima.tolist(),family_tie=tie,candidate_count=int(mask.sum()),candidate_mask_sha256=sha(mask.tobytes()),
        rule=RULE,tie_atol=1e-12,inputs=['packet_bytes','frozen_guide_bytes'],
        target_label_access=False,historical_shift_access=False,source_state_access=False,outcome_access=False,record_reprojected=False)


def reader_trace(supplied,tissue,ladder,bp,birth_random,read_random,cfg,enabled=True,replay=True):
    v=.2*birth_random.standard_normal((1,16,16));state=(v,v.copy(),v.copy())
    saved=[np.stack(state)[:,0]];birth=canonical_digest(birth_random.bit_generator.state)
    field=unpack(supplied) if enabled else np.zeros((16,16))
    for t in range(1,cfg.steps+1):
        noise=read_random.standard_normal((1,16,16))
        if replay:
            state=physics.step(*state,field,tissue,ladder,0.,bp.rho,noise)
            if t in cfg.times:saved.append(np.stack(state)[:,0])
    return np.stack(saved),dict(birth_rng=birth,read_rng=canonical_digest(read_random.bit_generator.state),
        input_sha256=sha(supplied),packet_bytes=2048,enabled=enabled,writing=False,gain=0.,target_labels=False)


def founder_check(raw,meta,cfg,replay,tag=TAG,index=None):
    index=meta['index'] if index is None else index;life=meta['life']
    tissue,ladder,bp=physics.parameters(meta);maximum=0.
    native=tissue.threshold_spread*generator(tissue.tissue_tag,index).standard_normal((16,16))
    np.testing.assert_array_equal(raw['native_theta'],native)
    theta0=project(native);np.testing.assert_array_equal(raw['theta0'],theta0)
    random=generator(tag,index,life,'parent_birth')
    v=np.full((1,16,16),-1.);v[:,:,:8]=1.;v=v+tissue.copy_jitter*random.standard_normal((1,16,16))
    state=(v,v.copy(),v.copy());np.testing.assert_array_equal(raw['parent_birth'],np.stack(state)[:,0])
    assert meta['parent_birth_rng']==canonical_digest(random.bit_generator.state)
    random=generator(tag,index,life,'parent_settle')
    for _ in range(cfg.settle):
        noise=random.standard_normal((1,16,16))
        if replay:state=physics.step(*state,theta0,tissue,ladder,bp.c_m,bp.rho,noise)
    if replay:maximum=max(maximum,compare(raw['settled'],np.stack(state)[:,0]))
    assert meta['parent_settle_rng']==canonical_digest(random.bit_generator.state)
    endings=[]
    for r in (0,1):
        state=tuple(x[None].copy() for x in raw['settled']);theta=theta0[None].copy()
        saved=[np.stack((*state,theta))[:,0]]
        np.testing.assert_array_equal(raw['founder_states'][r,0],saved[0])
        random=generator(tag,index,life,'teaching')
        for t in range(1,cfg.teaching+1):
            noise=random.standard_normal((1,16,16))
            if replay:
                state=(cfg.hold*targets()[r][None],state[1],state[2])
                state=physics.step(*state,theta,tissue,ladder,bp.c_m,bp.rho,noise)
                theta=project((1-cfg.lam)*theta+cfg.lam*np.tanh(state[2]))
                if t in cfg.parent_times:saved.append(np.stack((*state,theta))[:,0])
        if replay:maximum=max(maximum,compare(raw['founder_states'][r],np.stack(saved)))
        endings.append(canonical_digest(random.bit_generator.state))
        assert raw['founder_packets'][r].tobytes()==packet(raw['founder_states'][r,-1,3])
    nested(meta['teaching_rng'],endings)
    return maximum


def check_sources(raw,meta,cfg,replay=True):
    assert set(meta) in (SOURCE_META,SOURCE_META|{'replay'}) and set(raw)==SOURCE_KEYS
    index,life,training=meta['index'],meta['life'],meta['training']
    assert type(training) is bool and type(index) is int
    assert index in ((*range(72500,72502),514231) if training else (*range(72000,72008),514231))
    assert type(life) is int and 0<=life<cfg.lives
    modes=('aligned',) if training else ('translated','aligned')
    nested(meta['config'],asdict(cfg));nested(meta['modes'],list(modes))
    for key in ('parent_times','times','source_times'):nested(meta[key],list(getattr(cfg,key)))
    assert meta['tag']==TAG and meta['writer_rule']=='project(tanh(R_final), .3)'
    for key in ('fresh_founders','source_theta_erased','instructed_founders'):assert meta[key] is True
    for key in ('reused_source_starts','source_shift_transmitted','unseen_pattern_families'):assert meta[key] is False
    assert (meta['source_gain'],meta['source_rho'],meta['source_lambda'])==(.2,.002,.001)
    shapes=dict(native_theta=(16,16),theta0=(16,16),parent_birth=(3,16,16),settled=(3,16,16),targets=(2,16,16),
        founder_states=(2,len(cfg.parent_times),4,16,16),founder_packets=(2,2048),pre_states=(2,len(cfg.times),3,16,16),
        source_starts=(2,3,16,16),source_shift=(2,),source_states=(2,len(modes),len(cfg.source_times),4,16,16),
        written_fields=(2,len(modes),16,16))
    for key,shape in shapes.items():
        dtype=np.uint8 if key=='founder_packets' else np.int64 if key=='source_shift' else np.float64
        assert raw[key].shape==shape and raw[key].dtype==dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'],targets())
    tissue,ladder,bp=physics.parameters(meta);assert (tissue.sigma,bp.rho,bp.c_m)==(.3,.002,.2)
    founder=founder_check(raw,meta,cfg,replay);pre_max=0.;source_max=0.;reads=[];writers=[]
    shift=np.asarray(divmod(int(generator(TAG,index,life,'source_shift').integers(1,256)),16),dtype=np.int64)
    np.testing.assert_array_equal(raw['source_shift'],shift)
    for r in (0,1):
        path,record=reader_trace(raw['founder_packets'][r].tobytes(),tissue,ladder,bp,
            generator(TAG,index,life,'source_birth'),generator(TAG,index,life,'source_read'),cfg,replay=replay)
        np.testing.assert_array_equal(raw['pre_states'][r,0],path[0])
        if replay:pre_max=max(pre_max,compare(raw['pre_states'][r],path))
        reads.append(record);start=raw['pre_states'][r,-1]
        np.testing.assert_array_equal(raw['source_starts'][r],start);entries=[]
        for mi,mode in enumerate(modes):
            np.testing.assert_array_equal(raw['source_states'][r,mi,0],np.concatenate((start,np.zeros((1,16,16)))))
            random=generator(TAG,index,life,'source_write')
            if replay:
                path,entry=previous.replay_source(start,tissue,ladder,random,mode,shift,cfg)
                source_max=max(source_max,compare(raw['source_states'][r,mi],path))
            else:
                for _ in range(cfg.source_steps):random.standard_normal((1,16,16))
                entry=previous.source_metadata(random,mode,shift)
            ref=raw['source_states'][r,mi,-1,2];assert np.tanh(ref).std()>1e-9
            np.testing.assert_array_equal(raw['written_fields'][r,mi],project(np.tanh(ref)))
            entries.append(entry)
        writers.append(entries)
    nested(meta['pre_readers'],reads);nested(meta['writers'],writers)
    return dict(full_source_replay=replay,founder_max_abs=founder,pre_reader_max_abs=pre_max,source_max_abs=source_max,
        parent_acquisitions=2,pre_readers=2,source_writers=2*len(modes),fresh_founders=True)


def check_life(raw,meta,cfg,guide,replay=True):
    extra={'cases','guide_sha256','guide_fitted_on_test','guide_host_prior_bytes','ordinary_packet_bytes',
        'guide_variants','selector_inputs','selector_rule','selectors','readers'}
    assert set(meta) in (SOURCE_META|extra,SOURCE_META|extra|{'replay'}) and meta['training'] is False
    source=check_sources({k:raw[k] for k in SOURCE_KEYS},{k:meta[k] for k in SOURCE_META},cfg,replay)
    shapes=dict(guide=(2,16,16),guide_variants=(3,2,16,16),permutations=(2,256),selector_inputs=(2,6,2048),
        selector_outputs=(2,3,6,2048),selector_scores=(2,3,6,2,16,16),prepared_fields=(2,6,16,16),
        packets=(48,2048),states=(48,len(cfg.times),3,16,16),values=(48,len(cfg.times),12))
    assert set(raw)==SOURCE_KEYS|set(shapes)
    for key,shape in shapes.items():
        dtype=np.uint8 if key in ('selector_inputs','selector_outputs','packets') else np.int64 if key=='permutations' else np.float64
        assert raw[key].shape==shape and raw[key].dtype==dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['guide'],guide)
    variants=np.stack((guide,targets(),np.stack([move(t,(3,5),False) for t in guide])))
    np.testing.assert_array_equal(raw['guide_variants'],variants)
    nested(meta['cases'],[list(c) for c in CASES]);nested(meta['guide_variants'],['learned','supplied','wrong'])
    nested(meta['selector_inputs'],['native','aligned','native_shuffle','aligned_shuffle','ideal_shifted','zero'])
    assert meta['guide_sha256']==sha(guide.astype('<f8').tobytes()) and meta['guide_fitted_on_test'] is False
    assert (meta['guide_host_prior_bytes'],meta['ordinary_packet_bytes'])==(4096,2048) and meta['selector_rule']==RULE
    index,life=meta['index'],meta['life'];packets={};all_selections=[];score_max=0.
    zero=packet(np.zeros((16,16)));shift=raw['source_shift']
    for r in (0,1):
        perm=generator(TAG,index,life,f'shuffle:{r}').permutation(256)
        np.testing.assert_array_equal(raw['permutations'][r],perm)
        shuffle=lambda b:packet(unpack(b).ravel()[perm].reshape(16,16))
        native,aligned=(packet(x) for x in raw['written_fields'][r])
        ideal=packet(project(np.tanh(1.5*targets()[r])))
        inputs=(native,aligned,shuffle(native),shuffle(aligned),packet(move(unpack(ideal),shift,False)),zero)
        selections=[]
        for vi,variant in enumerate(variants):
            entries=[]
            for ii,b in enumerate(inputs):
                assert raw['selector_inputs'][r,ii].tobytes()==b
                output,scores,record=select(b,variant)
                assert raw['selector_outputs'][r,vi,ii].tobytes()==output
                np.testing.assert_allclose(raw['selector_scores'][r,vi,ii],scores,atol=1e-12,rtol=0)
                score_max=max(score_max,float(abs(raw['selector_scores'][r,vi,ii]-scores).max()))
                entries.append(record)
            selections.append(entries)
        selected=lambda vi,ii:raw['selector_outputs'][r,vi,ii].tobytes()
        base=dict(native=native,learned=selected(0,0),supplied=selected(1,0),known=packet(move(unpack(native),shift)),
            aligned=aligned,aligned_learned=selected(0,1))
        for bi,k in enumerate(BASES):np.testing.assert_array_equal(raw['prepared_fields'][r,bi],unpack(base[k]))
        row=base|{k+'_shuffle':shuffle(b) for k,b in base.items()}
        row.update(shuffle_learned=selected(0,2),shuffle_supplied=selected(1,2),aligned_shuffle_learned=selected(0,3),
            wrong_guide=selected(2,0),learned_sham=base['learned'],learned_off=base['learned'],supplied_off=base['supplied'],
            ideal=ideal,ideal_shifted=inputs[4],ideal_learned=selected(0,4),ideal_supplied=selected(1,4),zero=zero)
        assert row['ideal_supplied']==ideal
        for k,b in row.items():packets[r,k]=b
        all_selections.append(selections)
    nested(meta['selectors'],all_selections)
    tissue,ladder,bp=physics.parameters(meta);maximum=0.;readers=[]
    for ci,c in enumerate(CASES):
        b=packets[c];assert raw['packets'][ci].tobytes()==b
        path,entry=reader_trace(b,tissue,ladder,bp,generator(TAG,index,life,'birth'),generator(TAG,index,life,'read'),
            cfg,not c[1].endswith('_off'),replay)
        np.testing.assert_array_equal(raw['states'][ci,0],path[0])
        if replay:maximum=max(maximum,compare(raw['states'][ci],path))
        readers.append(entry)
    nested(meta['readers'],readers)
    pairs=[('learned','learned_sham'),('learned_off','zero'),('supplied_off','zero'),('ideal_supplied','ideal')]
    for r in (0,1):
        for a,b in pairs:np.testing.assert_array_equal(raw['states'][CASES.index((r,a))],raw['states'][CASES.index((r,b))])
    np.testing.assert_array_equal(raw['states'][23],raw['states'][47])
    values=observe(raw['states'],raw['targets'],CASES,cfg)
    np.testing.assert_allclose(raw['values'],values,atol=1e-12,rtol=0)
    return dict(full_life_replay=replay,dynamics_max_abs=maximum,founder_max_abs=source['founder_max_abs'],
        pre_reader_max_abs=source['pre_reader_max_abs'],source_max_abs=source['source_max_abs'],
        metric_max_abs=float(abs(raw['values']-values).max()),selector_max_abs=score_max,
        reader_paths=48,parent_acquisitions=2,pre_readers=2,source_writers=4,selector_decisions=36,primary_packets=12,
        exact_path_aliases=9,packet_lineage_checked=True,fresh_reset=True,exact_signs=True)


def check_block(raw,meta,cfg,guide,replay=True):
    assert set(meta)=={'index','config','guide_sha256','lives'}
    nested(meta['config'],asdict(cfg));assert len(meta['lives'])==cfg.lives
    assert meta['guide_sha256']==sha(guide.astype('<f8').tobytes())
    assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,row in enumerate(meta['lives']):
        assert row['index']==meta['index'] and row['life']==life
        proof=row['replay'];current=check_life({k:x[life] for k,x in raw.items()},row,cfg,guide,replay)
        expected=current.copy();expected['full_life_replay']=True
        for key in ('dynamics_max_abs','founder_max_abs','pre_reader_max_abs','source_max_abs','metric_max_abs','selector_max_abs'):
            assert 0<=proof[key]<=(1e-12 if key in ('metric_max_abs','selector_max_abs') else 1e-10)
            if not replay:expected[key]=proof[key]
        nested(proof,expected)
    return True


def check_training_block(raw,meta,cfg,replay=True):
    assert set(meta)=={'index','config','training','lives'} and meta['training'] is True
    nested(meta['config'],asdict(cfg));assert len(meta['lives'])==cfg.lives
    assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,row in enumerate(meta['lives']):
        assert row['index']==meta['index'] and row['life']==life
        proof=row['replay'];current=check_sources({k:x[life] for k,x in raw.items()},row,cfg,replay)
        expected=current.copy();expected['full_source_replay']=True
        for key in ('founder_max_abs','pre_reader_max_abs','source_max_abs'):
            assert 0<=proof[key]<=1e-10
            if not replay:expected[key]=proof[key]
        nested(proof,expected)
    return True


def check_bridge(raw,meta,founder,known):
    from laws_confirmation.l20_learned_guide import CONFIG as cfg
    assert set(raw)=={'native_theta','theta0','parent_birth','settled','targets','founder_states','founder_packets',
        'pre_states','source_shift','source_states','packets','states'}
    keys={'index','life','config','known_outcomes','qualification_pool','new_futures','parent_birth_rng','parent_settle_rng',
        'teaching_rng','pre_readers','writers','readers','cases','tissue','ladder','blueprint','host'}
    assert set(meta) in (keys,keys|{'replay'})
    assert meta['index']==514217 and meta['life']==0 and meta['new_futures']==0
    assert meta['known_outcomes'] is True and meta['qualification_pool'] is False
    nested(meta['config'],asdict(cfg));maximum=founder_check(raw,meta,cfg,True,'l20-acquisition-only-v1',514217)
    for key in ('native_theta','theta0','parent_birth','settled','targets','founder_states','founder_packets'):
        np.testing.assert_array_equal(raw[key],founder[key][0])
    tissue,ladder,bp=physics.parameters(meta);reads=[];writers=[]
    np.testing.assert_array_equal(raw['source_shift'],known['source_shifts'][0,0])
    for r in (0,1):
        path,record=reader_trace(raw['founder_packets'][r].tobytes(),tissue,ladder,bp,
            generator('l20-three-rewrite-v1',514217,0,'g1:birth'),generator('l20-three-rewrite-v1',514217,0,'g1:read'),cfg)
        maximum=max(maximum,compare(raw['pre_states'][r],path));reads.append(record)
        np.testing.assert_array_equal(raw['pre_states'][r],founder['generation_states'][0,8*r,0,[0,1,2,4],:3])
        entries=[]
        for mi,mode in enumerate(('translated','aligned')):
            path,entry=previous.replay_source(raw['pre_states'][r,-1],tissue,ladder,
                generator('l20-blind-alignment-v1',514230,0,'g1:source'),mode,raw['source_shift'],cfg)
            maximum=max(maximum,compare(raw['source_states'][r,mi],path));entries.append(entry)
        writers.append(entries)
    np.testing.assert_array_equal(raw['source_states'],known['source_states'][0,:,0])
    nested(meta['pre_readers'],reads);nested(meta['writers'],writers)
    cases=tuple((r,k) for r in (0,1) for k in ('native','blind','aligned','ideal','zero'))
    nested(meta['cases'],[list(c) for c in cases])
    assert set(meta['host'])=={'index','tissue','ladder','blueprint'} and meta['host']['index']==514230
    tissue,ladder,bp=physics.parameters(meta['host']);records=[]
    for ci,c in enumerate(cases):
        oldci=old.CASES.index(c)
        assert raw['packets'][ci].tobytes()==known['packets'][0,oldci,0].tobytes()
        path,record=reader_trace(raw['packets'][ci].tobytes(),tissue,ladder,bp,
            generator('l20-blind-alignment-v1',514230,0,'g1:birth'),generator('l20-blind-alignment-v1',514230,0,'g1:read'),cfg)
        maximum=max(maximum,compare(raw['states'][ci],path));records.append(record)
        np.testing.assert_array_equal(raw['states'][ci],known['states'][0,oldci,0])
    nested(meta['readers'],records)
    return dict(known_founder_acquisitions=2,known_pre_readers=2,known_source_writers=4,known_reader_paths=10,
        full_replay=True,max_abs=maximum,new_futures=0,whole_renewal_replayed=False,qualification_pool=False)


def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    values=np.stack([b['values'] for b in blocks])
    assert values.shape==(8,cfg.lives,48,len(cfg.times),12) and np.isfinite(values).all()
    names=['learned_minus_native','supplied_minus_native','learned_minus_supplied','known_minus_native',
        'learned_minus_known','learned_minus_aligned','aligned_learned_minus_aligned','learned_minus_wrong_guide']
    names += [k+'_minus_'+k+'_shuffle' for k in BASES]
    names += ['learned_minus_shuffle_learned','supplied_minus_shuffle_supplied','aligned_learned_minus_aligned_shuffle_learned']
    names += [k+'_minus_zero' for k in BASES]
    names += ['ideal_minus_zero','ideal_supplied_minus_ideal_shifted','ideal_learned_minus_ideal_shifted',
        'ideal_learned_minus_ideal','shuffle_learned_minus_native_shuffle','shuffle_supplied_minus_native_shuffle',
        'specificity_gain','matched_specificity_gain','source_interaction']
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for name in names:
            if name=='specificity_gain':weights={'learned':1,'learned_shuffle':-1,'native':-1,'native_shuffle':1}
            elif name=='matched_specificity_gain':weights={'learned':1,'shuffle_learned':-1,'native':-1,'native_shuffle':1}
            elif name=='source_interaction':weights={'learned':1,'native':-1,'aligned_learned':-1,'aligned':1}
            else:weights=dict(zip(name.split('_minus_'),(1,-1)))
            effects=[]
            for role in (0,1):
                effect=np.zeros((8,cfg.lives))
                for k,w in weights.items():
                    ci=CASES.index((role,k));effect+=w*(values[:,:,ci,-1,col]-values[:,:,ci,-1,col+1])
                effects.append(effect)
            for role,effect in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                rows.append(dict(name=name,role=role,observer=observer,**stats(effect,draws)))
    get=lambda name,role='both':next(r for r in rows if (r['name'],r['role'],r['observer'])==(name,role,'qualified'))
    good=lambda name,role='both':get(name,role)['pointwise_block_bootstrap_95'][0]>0
    means=lambda name:all(get(name,r)['mean']>0 for r in (0,1))
    gates=[get('ideal_minus_zero',r) for r in (0,1)]
    disagree=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    readable=bool(all(good('ideal_minus_zero',r) for r in (0,1)) and all(n>0 for row in disagree for n in row))
    content={k:bool(readable and good(k+'_minus_'+k+'_shuffle') and means(k+'_minus_'+k+'_shuffle')
        and all(good(k+'_minus_zero',r) for r in (0,1))) for k in BASES}
    matched={k:bool(readable and good(k+'_minus_'+v) and means(k+'_minus_'+v)) for k,v in (
        ('learned','shuffle_learned'),('supplied','shuffle_supplied'),('aligned_learned','aligned_shuffle_learned'))}
    calibrations={k:bool(readable and all(good('ideal_'+k+'_minus_ideal_shifted',r) for r in (0,1))) for k in ('learned','supplied')}
    guide_control=bool(readable and good('learned_minus_wrong_guide') and means('learned_minus_wrong_guide'))
    supplied=bool(content['supplied'] and matched['supplied'] and calibrations['supplied'])
    qualified=bool(content['learned'] and matched['learned'] and calibrations['learned'] and guide_control)
    primary=get('learned_minus_native');directions=[get('learned_minus_native',r) for r in (0,1)]
    label='READOUT_NOT_QUALIFIED' if not readable else 'SUPPLIED_CONTROL_NOT_QUALIFIED' if not supplied else 'LEARNED_EFFECT_UNRESOLVED'
    if readable and supplied:
        if good('learned_minus_native') and means('learned_minus_native'):
            label='LEARNED_GUIDE_QUALIFIED' if qualified else 'LEARNED_GAIN_WITHOUT_CONTROL_QUALIFICATION'
        elif primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions):label='LEARNED_HARM_DETECTED'
    expected=dict(schema='l20_learned_guide_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=content,matched_control_qualified=matched,calibration_qualified=calibrations,
        guide_control_qualified=guide_control,supplied_control_qualified=supplied,readout_qualified=readable,
        readout_gates=gates,contrasts=rows,target_disagreement_cells=disagree,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),cell_means=values.mean(axis=(0,1)).tolist(),
        test_blocks=list(range(72000,72008)),training_blocks=[72500,72501],blocks=8,lives_per_block=cfg.lives,
        reader_paths=8*cfg.lives*48,source_writers=8*cfg.lives*4,founder_acquisitions=8*cfg.lives*2,pre_readers=8*cfg.lives*2,
        training_records=16,guide_bytes=4096,packet_bytes=2048,conditional_on_one_fitted_guide=True,
        fit_rule=FIT_RULE,guide_labels_and_alignment_supplied=True,perfect_template_pixels_in_fit=False,
        fresh_founders=True,reused_source_starts=False,unseen_pattern_families=False,new_three_generation_chain=False,
        learned_ontology=False,absolute_fidelity_gate=None,equivalence_test=False,secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected);return True


if __name__=='__main__':
    from laws_confirmation.l20_learned_guide_run import main
    main(default_command='audit')
