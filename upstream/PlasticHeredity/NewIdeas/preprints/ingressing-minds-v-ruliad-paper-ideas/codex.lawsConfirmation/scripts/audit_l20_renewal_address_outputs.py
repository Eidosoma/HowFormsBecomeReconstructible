"""D134 independent writer/reader physics, routing, lineage, observers and inference."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.io import canonical_digest,sha256_file

prior=old.checker(); physics=prior.physics
compare,nested,generator=physics.compare,physics.nested,physics.generator
project,packet,unpack,sha,observe,stats=prior.project,prior.packet,prior.unpack,prior.sha,prior.observe,prior.stats
TAG='l20-renewal-address-v1'
MODES=('translated','aligned')
KINDS=('translated','aligned','translated_pre_shuffle','aligned_pre_shuffle',
    'translated_post_shuffle','aligned_post_shuffle','translated_off','aligned_off',
    'translated_wrong','aligned_wrong','ideal','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PAIRS=(('aligned','translated'),('translated','translated_pre_shuffle'),('translated','translated_post_shuffle'),
    ('translated','translated_off'),('translated','translated_wrong'),('aligned','aligned_pre_shuffle'),
    ('aligned','aligned_post_shuffle'),('aligned','aligned_off'),('aligned','aligned_wrong'),
    ('translated','zero'),('aligned','zero'),('ideal','zero'))
GUIDE_SHA='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'

def check_life(raw,meta,cfg,source,replay=True):
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(74000,74008),514234)
    assert type(life) is int and 0<=life<cfg.lives
    si=514232 if index==514234 else index-1000
    assert meta['source_index']==si and meta['tag']==TAG
    nested(meta['config'],asdict(cfg));nested(meta['cases'],[list(c) for c in CASES]);nested(meta['modes'],list(MODES))
    nested(meta['times'],list(cfg.times));nested(meta['source_times'],[0,1,300,1000])
    for k in ('source_noise_reused','source_starts_reused','translated_exact_replay'):assert meta[k] is True
    for k in ('fresh_founders','new_renewal_cohort','guide_refitted','latent_theta_transmitted','target_labels_in_writer'):assert meta[k] is False
    assert meta['writer_rule']=='project(tanh(R_final), .3)' and meta['writer_inputs']==['R_final']
    assert (meta['public_guide_bytes'],meta['packet_bytes'])==(4096,2048)
    assert meta['guide_sha256']==sha(raw['guide'].astype('<f8').tobytes())==GUIDE_SHA
    keys={'index','source_index','life','config','tag','cases','modes','times','source_times','source_context',
        'tissue','ladder','blueprint','writers','selectors','readers','source_noise_reused','source_starts_reused',
        'translated_exact_replay','fresh_founders','new_renewal_cohort','guide_refitted','latent_theta_transmitted',
        'guide_sha256','public_guide_bytes','packet_bytes','writer_rule','writer_inputs','target_labels_in_writer'}
    assert set(meta) in (keys,keys|{'replay'})
    shapes=dict(targets=(2,16,16),guide=(2,16,16),source_starts=(2,3,3,16,16),source_shifts=(3,2),
        source_states=(2,3,2,4,4,16,16),written_fields=(2,3,2,16,16),permutations=(2,3,256),
        inputs=(24,3,2048),packets=(24,3,2048),scores=(24,3,2,16,16),
        states=(24,3,len(cfg.times),3,16,16),values=(24,3,len(cfg.times),12))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('inputs','packets') else np.int64 if k in ('source_shifts','permutations') else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'],source['targets'][life]);np.testing.assert_array_equal(raw['guide'],source['guide'][life])
    st,sl,sb=physics.parameters(meta['source_context']);rt,rl,rb=physics.parameters(meta)
    assert set(meta['source_context'])=={'index','tissue','ladder','blueprint'} and meta['source_context']['index']==si
    assert (st.sigma,sb.rho,sb.c_m,rt.sigma,rb.rho)==(.3,.002,.2,.3,.002)
    # Host parameters are checked against their frozen public contexts, not fitted here.
    for idx,record in ((si,meta['source_context']),(index,meta)):
        ctx=old.context(idx)
        for k in ('tissue','ladder','blueprint'):nested(record[k],asdict(ctx['bp' if k=='blueprint' else k]))
    writer_max=reader_max=score_max=0.;writers=[];selectors=[];readers=[]
    for role,ci in ((0,0),(1,11)):
        generations=[]
        for gi in range(3):
            start=source['generation_read_states'][life,ci,gi,-1]
            np.testing.assert_array_equal(raw['source_starts'][role,gi],start)
            shift=np.asarray(divmod(int(generator('l20-guide-renewal-v1',si,life,f'g{gi+1}:source_shift').integers(1,256)),16),np.int64)
            np.testing.assert_array_equal(raw['source_shifts'][gi],shift)
            np.testing.assert_array_equal(shift,source['generation_shifts'][life,gi])
            modes=[]
            for mi,mode in enumerate(MODES):
                path,entry=prior.write_trace(start,st,sl,generator('l20-guide-renewal-v1',si,life,f'g{gi+1}:source_write'),mode,shift,old.CONFIG,replay=replay)
                np.testing.assert_array_equal(raw['source_states'][role,gi,mi,0],path[0])
                if replay:writer_max=max(writer_max,compare(raw['source_states'][role,gi,mi],path))
                theta=raw['source_states'][role,gi,mi,1:,3]
                np.testing.assert_allclose(theta.mean(axis=(-2,-1)),0,atol=1e-14,rtol=0)
                np.testing.assert_allclose(theta.std(axis=(-2,-1)),.3,atol=1e-14,rtol=0)
                ref=raw['source_states'][role,gi,mi,-1,2];assert np.tanh(ref).std()>1e-9
                np.testing.assert_array_equal(raw['written_fields'][role,gi,mi],project(np.tanh(ref)))
                modes.append(entry)
            np.testing.assert_array_equal(raw['source_states'][role,gi,0],source['generation_write_states'][life,ci,gi])
            assert packet(raw['written_fields'][role,gi,0])==source['outgoing'][life,ci,gi].tobytes()
            np.testing.assert_array_equal(raw['source_states'][role,gi,0,1],raw['source_states'][role,gi,1,1])
            assert modes[0]['noise_rng']==modes[1]['noise_rng'];generations.append(modes)
        writers.append(generations)
    nested(meta['writers'],writers)
    for ci,(role,kind) in enumerate(CASES):
        sms=[];rms=[]
        for gi in range(3):
            perm=generator(TAG,index,life,f'g{gi+1}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role,gi],perm)
            if kind in ('ideal','zero'):
                field=project(np.tanh(1.5*prior.prior.targets()[role])) if kind=='ideal' else np.zeros((16,16))
                incoming=packet(field);b=incoming;scores=np.zeros((2,16,16));entry=None
            else:
                mi=0 if kind.startswith('translated') else 1
                rr=1-role if kind.endswith('_wrong') else role
                field=raw['written_fields'][rr,gi,mi]
                if kind.endswith('_pre_shuffle'):field=field.ravel()[perm].reshape(16,16)
                incoming=packet(field);b,scores,entry=prior.prior.select(incoming,raw['guide'])
                if kind.endswith('_post_shuffle'):b=packet(unpack(b).ravel()[perm].reshape(16,16))
            assert raw['inputs'][ci,gi].tobytes()==incoming and raw['packets'][ci,gi].tobytes()==b
            error=float(abs(raw['scores'][ci,gi]-scores).max());assert error<=1e-12;score_max=max(score_max,error)
            path,rm=prior.read_trace(b,rt,rl,rb,generator(TAG,index,life,f'g{gi+1}:birth'),
                generator(TAG,index,life,f'g{gi+1}:read'),cfg,not kind.endswith('_off'),times=cfg.times,replay=replay)
            np.testing.assert_array_equal(raw['states'][ci,gi,0],path[0])
            if replay:reader_max=max(reader_max,compare(raw['states'][ci,gi],path))
            sms.append(entry);rms.append(rm)
        selectors.append(sms);readers.append(rms)
    nested(meta['selectors'],selectors);nested(meta['readers'],readers)
    aliases=[]
    for r in (0,1):
        for m in MODES:aliases.extend([((r,m+'_off'),(r,'zero')),((r,m+'_wrong'),(1-r,m))])
    aliases.append(((0,'zero'),(1,'zero')))
    for a,b in aliases:np.testing.assert_array_equal(raw['states'][CASES.index(a)],raw['states'][CASES.index(b)])
    values=observe(raw['states'],raw['targets'],CASES,cfg)
    metric_max=float(abs(raw['values']-values).max());assert metric_max<=1e-12
    return dict(full_life_replay=replay,writer_max_abs=writer_max,reader_max_abs=reader_max,
        selector_max_abs=score_max,metric_max_abs=metric_max,known_source_writers=6,new_aligned_writers=6,
        reader_paths=72,selector_decisions=60,exact_path_aliases=27,first_writer_step_aliases=6,
        translated_exact_replay=True,packet_lineage=True)

def check_block(raw,meta,cfg,source,source_paths,replay=False):
    assert set(meta)=={'index','config','source_sha256','lives'} and len(meta['lives'])==cfg.lives
    assert meta['source_sha256']=={str(x):sha256_file(x) for x in source_paths}
    nested(meta['config'],asdict(cfg));assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life
        proof=check_life({k:v[life] for k,v in raw.items()},record,cfg,source,replay)
        saved=record['replay'];assert saved['full_life_replay'] is True and set(saved)==set(proof)
        for k in proof:
            if k.endswith('_max_abs'):assert 0<=saved[k]<= (1e-10 if k in ('writer_max_abs','reader_max_abs') else 1e-12)
            elif k!='full_life_replay':assert saved[k]==proof[k]
    return True

def check_summary(summary,blocks,cfg):
    v=np.stack([b['values'] for b in blocks]);assert v.shape==(8,cfg.lives,24,3,len(cfg.times),12) and np.isfinite(v).all()
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in ('all',1,2,3):
            for a,b in PAIRS:
                effects=[]
                for role in (0,1):
                    ai,bi=CASES.index((role,a)),CASES.index((role,b))
                    e=(v[:,:,ai,:,-1,col]-v[:,:,ai,:,-1,col+1])-(v[:,:,bi,:,-1,col]-v[:,:,bi,:,-1,col+1])
                    effects.append(e.mean(axis=2) if stage=='all' else e[:,:,stage-1])
                for r,e in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=a+'_minus_'+b,stage=stage,role=r,observer=observer,**stats(e,draws)))
    get=lambda n,r='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(n,'all',r,'qualified'))
    positive=lambda n,r='both':get(n,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n:positive(n) and all(get(n,r)['mean']>0 for r in (0,1))
    disagreements=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    readable=bool(all(positive('ideal_minus_zero',r) for r in (0,1)) and all(d>0 for row in disagreements for d in row))
    content={m:bool(readable and all(positive(m+'_minus_zero',r) for r in (0,1)) and
        supported(m+'_minus_'+m+'_pre_shuffle') and supported(m+'_minus_'+m+'_post_shuffle')) for m in MODES}
    primary=get('aligned_minus_translated');directions=[get('aligned_minus_translated',r) for r in (0,1)]
    label='READOUT_NOT_QUALIFIED' if not readable else 'RENEWAL_ADDRESS_EFFECT_UNRESOLVED'
    if readable:
        if content['aligned'] and primary['pointwise_block_bootstrap_95'][0]>0 and all(x['mean']>0 for x in directions):label='ALIGNED_RENEWAL_WRITER_ADVANTAGE'
        elif content['translated'] and primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions):label='TRANSLATED_RENEWAL_WRITER_ADVANTAGE'
    expected=dict(schema='l20_renewal_address_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=readable,content_qualified=content,contrasts=rows,target_disagreement_cells=disagreements,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(prior.METRICS),cell_means=v.mean(axis=(0,1)).tolist(),
        test_blocks=list(range(74000,74008)),source_blocks=list(range(73000,73008)),blocks=8,lives_per_block=cfg.lives,
        stage_count=3,source_pairs=8*cfg.lives*6,known_source_writers=8*cfg.lives*6,new_aligned_writers=8*cfg.lives*6,
        reader_paths=8*cfg.lives*72,selector_decisions=8*cfg.lives*60,packet_bytes=2048,public_guide_bytes=4096,
        guide_sha256=GUIDE_SHA,new_guide_fits=0,source_noise_reused=True,source_starts_reused=True,
        new_renewal_cohort=False,fresh_founders=False,conditional_on_one_fitted_guide=True,
        supplied_groups_and_frame=True,learned_ontology=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,automatic_successor=False)
    nested(summary,expected);return True

if __name__=='__main__':
    from laws_confirmation.l20_renewal_address_run import main
    main()
