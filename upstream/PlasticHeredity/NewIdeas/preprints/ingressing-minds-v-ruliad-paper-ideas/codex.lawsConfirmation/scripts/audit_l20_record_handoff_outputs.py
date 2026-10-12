"""D139 independent endpoint addressing, record bytes, routing, reader physics and interaction."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation.io import sha256_file

prior=old.checker();physics=prior.physics
compare,nested,generator=physics.compare,physics.nested,physics.generator
project,packet,unpack,sha,observe,stats=prior.project,prior.packet,prior.unpack,prior.sha,prior.observe,prior.stats
TAG='l20-record-handoff-v1'
MODES=('instant_reference','instant_matched','theta_reference','theta_matched')
KINDS=MODES+tuple(m+'_'+k for k in ('pre_shuffle','post_shuffle','off','wrong') for m in MODES)+('ideal','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
PAIRS=(('theta_matched','theta_reference'),('instant_matched','instant_reference'),
    ('theta_matched','instant_matched'),('theta_reference','instant_reference'))+tuple(
    (m,m+'_'+k) for m in MODES for k in ('pre_shuffle','post_shuffle','off','wrong'))+tuple((m,'zero') for m in MODES)+(('ideal','zero'),)
CONTRASTS={a+'_minus_'+b:{a:1,b:-1} for a,b in PAIRS}|{
    'record_correction_interaction':{'theta_matched':1,'theta_reference':-1,'instant_matched':-1,'instant_reference':1},
    'pooled_theta_minus_instant':{'theta_matched':.5,'theta_reference':.5,'instant_matched':-.5,'instant_reference':-.5},
    'pre_shuffle_specificity_interaction':{'theta_matched':1,'theta_reference':-1,'instant_matched':-1,'instant_reference':1,
        'theta_matched_pre_shuffle':-1,'theta_reference_pre_shuffle':1,'instant_matched_pre_shuffle':1,'instant_reference_pre_shuffle':-1},
    'post_shuffle_specificity_interaction':{'theta_matched':1,'theta_reference':-1,'instant_matched':-1,'instant_reference':1,
        'theta_matched_post_shuffle':-1,'theta_reference_post_shuffle':1,'instant_matched_post_shuffle':1,'instant_reference_post_shuffle':-1}}
GUIDE_SHA='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'

def check_life(raw,meta,cfg,source,replay=True):
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(77000,77008),514239)
    assert type(life) is int and 0<=life<cfg.lives
    assert meta['source_index']==(514237 if index==514239 else index-1000)
    assert meta['tag']==TAG and meta['source_tag']=='l20-reference-handoff-v1'
    nested(meta['config'],asdict(cfg));nested(meta['cases'],[list(c) for c in CASES]);nested(meta['modes'],list(MODES))
    nested(meta['cells'],[['instant','reference'],['instant','matched'],['theta','reference'],['theta','matched']])
    nested(meta['times'],list(cfg.times))
    assert type(meta['source_checkpoint']) is int and meta['source_checkpoint']==1000
    assert meta['source_mode_indices']==[0,1] and meta['new_source_writes']==0
    for k in ('source_endpoints_reused','latent_theta_transmitted','source_theta_feedback','fresh_reader_streams','source_correction_uses_archived_birth'):assert meta[k] is True
    for k in ('fresh_founders','new_renewal_cohort','guide_refitted','theta_reprojected','target_labels_in_record'):assert meta[k] is False
    assert meta['record_rule']=='theta: saved bytes; instant: project(tanh(R_final), .3)' and meta['record_inputs']==['theta_final','R_final']
    assert (meta['public_guide_bytes'],meta['packet_bytes'])==(4096,2048)
    assert meta['guide_sha256']==sha(raw['guide'].astype('<f8').tobytes())==GUIDE_SHA
    keys={'index','source_index','life','config','tag','source_tag','cases','modes','cells','times','source_checkpoint','source_mode_indices',
        'source_endpoints_reused','new_source_writes','tissue','ladder','blueprint','selectors','readers','fresh_founders','new_renewal_cohort',
        'guide_refitted','latent_theta_transmitted','theta_reprojected','source_theta_feedback','fresh_reader_streams',
        'guide_sha256','public_guide_bytes','packet_bytes','record_rule','record_inputs','target_labels_in_record','source_correction_uses_archived_birth'}
    assert set(meta) in (keys,keys|{'replay'})
    shapes=dict(targets=(2,16,16),guide=(2,16,16),source_endpoints=(2,3,2,4,16,16),
        written_fields=(2,3,4,16,16),permutations=(2,3,256),inputs=(44,3,2048),packets=(44,3,2048),
        scores=(44,3,2,16,16),states=(44,3,len(cfg.times),3,16,16),values=(44,3,len(cfg.times),12))
    assert set(raw)==set(shapes)
    for k,shape in shapes.items():
        dtype=np.uint8 if k in ('inputs','packets') else np.int64 if k=='permutations' else np.float64
        assert raw[k].shape==shape and raw[k].dtype==dtype and np.isfinite(raw[k]).all()
    np.testing.assert_array_equal(raw['targets'],prior.prior.targets())
    np.testing.assert_array_equal(raw['targets'],source['targets'][life]);np.testing.assert_array_equal(raw['guide'],source['guide'][life])
    rt,rl,rb=physics.parameters(meta);assert (rt.sigma,rb.rho,rb.c_m)==(.3,.002,.2)
    ctx=old.context(index)
    for k in ('tissue','ladder','blueprint'):nested(meta[k],asdict(ctx['bp' if k=='blueprint' else k]))
    for role in (0,1):
        for gi in range(3):
            for hand in (0,1):
                endpoint=source['source_states'][life,role,gi,hand,3]
                np.testing.assert_array_equal(raw['source_endpoints'][role,gi,hand],endpoint)
                theta=endpoint[3];ref=endpoint[2]
                assert abs(float(theta.mean()))<1e-14 and abs(float(theta.std())-.3)<1e-14
                assert np.tanh(ref).std()>1e-9
                np.testing.assert_array_equal(raw['written_fields'][role,gi,hand],project(np.tanh(ref)))
                assert packet(raw['written_fields'][role,gi,hand])==packet(source['written_fields'][life,role,gi,hand])
                assert packet(raw['written_fields'][role,gi,hand+2])==packet(theta)
                for mi in (hand,hand+2):
                    field=raw['written_fields'][role,gi,mi]
                    assert abs(float(field.mean()))<1e-14 and abs(float(field.std())-.3)<1e-14
    reader_max=score_max=0.;selectors=[];readers=[]
    for ci,(role,kind) in enumerate(CASES):
        sms=[];rms=[]
        for gi in range(3):
            perm=generator(TAG,index,life,f'g{gi+1}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role,gi],perm)
            if kind in ('ideal','zero'):
                field=project(np.tanh(1.5*prior.prior.targets()[role])) if kind=='ideal' else np.zeros((16,16))
                incoming=packet(field);b=incoming;scores=np.zeros((2,16,16));entry=None
            else:
                mi=next(i for i,m in enumerate(MODES) if kind==m or kind.startswith(m+'_'))
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
    return dict(full_life_replay=replay,reader_max_abs=reader_max,selector_max_abs=score_max,metric_max_abs=metric_max,
        source_pairs=6,reused_writer_endpoints=12,new_source_writes=0,record_byte_bridges=24,
        reader_paths=132,selector_decisions=120,exact_path_aliases=51,packet_lineage=True,
        theta_exact_bytes=True,instant_exact_source_bytes=True)

def check_block(raw,meta,cfg,source,source_paths,replay=False):
    assert set(meta)=={'index','config','source_sha256','lives'} and len(meta['lives'])==cfg.lives
    assert meta['source_sha256']=={str(x):sha256_file(x) for x in source_paths}
    nested(meta['config'],asdict(cfg));assert all(x.shape[0]==cfg.lives for x in raw.values())
    for life,record in enumerate(meta['lives']):
        assert record['index']==meta['index'] and record['life']==life
        proof=check_life({k:v[life] for k,v in raw.items()},record,cfg,source,replay)
        saved=record['replay'];assert saved['full_life_replay'] is True and set(saved)==set(proof)
        for k in proof:
            if k.endswith('_max_abs'):assert 0<=saved[k]<= (1e-10 if k=='reader_max_abs' else 1e-12)
            elif k!='full_life_replay':assert saved[k]==proof[k]
    return True

def check_summary(summary,blocks,cfg):
    assert len(blocks)==8
    v=np.stack([b['values'] for b in blocks]);assert v.shape==(8,cfg.lives,44,3,len(cfg.times),12) and np.isfinite(v).all()
    draws=generator(TAG,0,0,'bootstrap').integers(0,8,(10000,8));rows=[]
    for observer,col in (('qualified',0),('sign',2)):
        for stage in ('all',1,2,3):
            for name,weights in CONTRASTS.items():
                effects=[]
                for role in (0,1):
                    e=np.zeros((8,cfg.lives,3))
                    for kind,weight in weights.items():
                        ci=CASES.index((role,kind))
                        e+=weight*(v[:,:,ci,:,-1,col]-v[:,:,ci,:,-1,col+1])
                    effects.append(e.mean(axis=2) if stage=='all' else e[:,:,stage-1])
                for r,e in ((0,effects[0]),(1,effects[1]),('both',(effects[0]+effects[1])/2)):
                    rows.append(dict(name=name,stage=stage,role=r,observer=observer,**stats(e,draws)))
    get=lambda n,r='both':next(x for x in rows if (x['name'],x['stage'],x['role'],x['observer'])==(n,'all',r,'qualified'))
    positive=lambda n,r='both':get(n,r)['pointwise_block_bootstrap_95'][0]>0
    supported=lambda n:positive(n) and all(get(n,r)['mean']>0 for r in (0,1))
    disagreements=[[int((b['targets'][l,0]!=b['targets'][l,1]).sum()) for l in range(cfg.lives)] for b in blocks]
    readable=bool(all(positive('ideal_minus_zero',r) for r in (0,1)) and all(d>0 for row in disagreements for d in row))
    content={m:bool(readable and all(positive(m+'_minus_zero',r) for r in (0,1)) and
        supported(m+'_minus_'+m+'_pre_shuffle') and supported(m+'_minus_'+m+'_post_shuffle')) for m in MODES}
    primary=get('record_correction_interaction');directions=[get('record_correction_interaction',r) for r in (0,1)]
    label='READOUT_NOT_QUALIFIED' if not readable else 'RECORD_CORRECTION_INTERACTION_UNRESOLVED'
    if readable and all(content.values()):
        if primary['pointwise_block_bootstrap_95'][0]>0 and all(x['mean']>0 for x in directions):label='THETA_CORRECTION_INTERACTION_POSITIVE'
        elif primary['pointwise_block_bootstrap_95'][1]<0 and all(x['mean']<0 for x in directions):label='THETA_CORRECTION_INTERACTION_NEGATIVE'
    cleanup={s:bool(content[s+'_matched'] and content[s+'_reference'] and supported(s+'_matched_minus_'+s+'_reference')) for s in ('instant','theta')}
    record_gain={h:bool(content['theta_'+h] and content['instant_'+h] and supported('theta_'+h+'_minus_instant_'+h)) for h in ('reference','matched')}
    expected=dict(schema='l20_record_handoff_v1',label=label,primary=primary,directional_primary=directions,
        readout_qualified=readable,content_qualified=content,cleanup_benefit_qualified=cleanup,theta_record_benefit_qualified=record_gain,
        contrasts=rows,target_disagreement_cells=disagreements,cases=[list(c) for c in CASES],times=list(cfg.times),
        metrics=list(prior.METRICS),cell_means=v.mean(axis=(0,1)).tolist(),
        test_blocks=list(range(77000,77008)),source_blocks=list(range(76000,76008)),blocks=8,lives_per_block=cfg.lives,
        stage_count=3,source_pairs=8*cfg.lives*6,reused_writer_endpoints=8*cfg.lives*12,new_source_writes=0,
        primary_packets=8*cfg.lives*24,reader_paths=8*cfg.lives*132,selector_decisions=8*cfg.lives*120,
        packet_bytes=2048,public_guide_bytes=4096,guide_sha256=GUIDE_SHA,new_guide_fits=0,
        new_renewal_cohort=False,fresh_founders=False,conditional_on_one_fitted_guide=True,
        supplied_groups_and_frame=True,learned_ontology=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False,automatic_successor=False,
        source_checkpoint=1000,theta_reprojected=False,source_theta_feedback=True,
        source_correction_uses_archived_birth=True,interaction_alone_is_not_positive_cleanup_or_theta_advantage=True)
    nested(summary,expected);return True

if __name__=='__main__':
    from laws_confirmation.l20_record_handoff_run import main
    main()
