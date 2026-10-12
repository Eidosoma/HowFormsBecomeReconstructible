"""D130 independently restated selection, source/reader dynamics and inference."""
from dataclasses import asdict
from functools import lru_cache
import hashlib

import numpy as np

from laws_confirmation import l20_three_rewrite as old
from laws_confirmation.io import canonical_digest, sha256_file

prior = old.checker()
physics = prior.physics
compare, nested, generator = physics.compare, physics.nested, physics.generator
TAG = 'l20-blind-alignment-v1'
BASES=('native','blind','known','aligned','aligned_blind')
KINDS=('native','blind','known','aligned','aligned_blind','native_shuffle','blind_shuffle','known_shuffle',
    'aligned_shuffle','aligned_blind_shuffle','shuffle_blind','aligned_shuffle_blind','blind_sham','blind_off',
    'aligned_blind_off','native_off','known_off','ideal','ideal_shifted','ideal_blind','zero')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
MODES=('translated','aligned')
SELECTOR_INPUTS=('native','aligned','native_shuffle','aligned_shuffle','ideal_shifted','zero')
SELECTOR_RULE='family tie: identity abstention; otherwise lexicographically first maximizing shift, then inverse'
RECORD_RULE='project(tanh(R_final), .3); selector only permutes original packet values'
METRICS=prior.METRICS
packet,unpack,sha=prior.packet,prior.unpack,prior.sha
observe=prior.observe


def shifted(field,shift,inverse=True):
    dy,dx=(int(x) for x in shift);sign=1 if inverse else -1
    return np.asarray([[field[(y+sign*dy)%16,(x+sign*dx)%16]
        for x in range(16)] for y in range(16)],dtype=np.float64)


@lru_cache(maxsize=1)
def templates():
    return np.asarray([[[1. if y<8 else -1. for x in range(16)] for y in range(16)],
        [[1. if (x%8)<4 else -1. for x in range(16)] for y in range(16)]])


@lru_cache(maxsize=1)
def template_digest():
    library=np.stack([[shifted(t,np.asarray((y,x),dtype=np.int64),False)
        for y in range(16) for x in range(16)] for t in templates()]).reshape(2,16,16,16,16)
    return sha(library.astype('<f8').tobytes())


def select(supplied):
    """Independent FFT correlation and modular indexing; no production selector."""
    field=unpack(supplied);centered=field-field.mean();scale=np.sqrt(np.mean(centered**2))
    targets=templates()
    scores=np.stack([np.fft.ifft2(np.fft.fft2(centered)*np.conj(np.fft.fft2(t))).real/(256*scale)
        for t in targets]) if scale else np.zeros((2,16,16))
    maxima=np.asarray([np.max(x) for x in scores]);tie=bool(abs(maxima[0]-maxima[1])<=1e-12)
    family=-1 if tie else (0 if maxima[0]>maxima[1] else 1)
    candidates=np.abs(scores-np.max(scores))<=1e-12
    shift=np.zeros(2,dtype=np.int64)
    if not tie:
        candidates=np.zeros((2,16,16),dtype=bool)
        candidates[family]=abs(scores[family]-maxima[family])<=1e-12
        for y in range(16):
            for x in range(16):
                if candidates[family,y,x]:
                    shift=np.asarray((y,x),dtype=np.int64);break
            else: continue
            break
    output=packet(shifted(field,shift))
    meta=dict(input_sha256=sha(supplied),output_sha256=sha(output),inferred_family=family,
        chosen_forward_shift=shift.tolist(),family_maxima=maxima.tolist(),family_tie=tie,
        candidate_count=int(candidates.sum()),candidate_mask_sha256=sha(candidates.tobytes()),
        template_sha256=template_digest(),rule=SELECTOR_RULE,tie_atol=1e-12,
        inputs=['packet_bytes','fixed_public_templates'],target_label_access=False,historical_shift_access=False,
        source_state_access=False,reader_outcome_access=False,record_reprojected=False)
    return output,scores,meta


def source_metadata(random,mode,shift):
    return dict(noise_rng=canonical_digest(random.bit_generator.state),source_mode=mode,
        source_shift=shift.tolist(),writing=True,gain=.2,rho=.002,lam=.001,sigma=.3,
        theta_start_zero=True,target_labels=False,force_probes=False)


def replay_source(start,tissue,ladder,random,mode,shift,cfg):
    state=tuple(x[None].copy() for x in start);theta=np.zeros((1,16,16))
    saved=[np.stack((*state,theta))[:,0]]
    for t in range(1,cfg.source_steps+1):
        field=theta if mode=='aligned' else shifted(theta[0],shift,False)[None]
        state=physics.step(*state,field,tissue,ladder,.2,.002,random.standard_normal((1,16,16)))
        theta=prior.project(.999*theta+.001*np.tanh(state[2]))
        if t in cfg.source_times: saved.append(np.stack((*state,theta))[:,0])
    return np.stack(saved),source_metadata(random,mode,shift)


def check_life(raw,meta,cfg,source,replay=True):
    keys={'index','source_index','life','config','cases','times','source_times','tag','origin_tag',
        'source_start_checkpoint','source_start_reused','source_noise_reused','source_trajectories_new',
        'theta_start_zero','latent_theta_transmitted','source_shift_transmitted','record_rule','selector_rule',
        'selector_inputs','template_prior_supplied','learned_ontology','source_modes','source_context',
        'source_paths','selectors','tissue','ladder','blueprint','readers'}
    assert set(meta) in (keys,keys|{'replay'})
    index,life=meta['index'],meta['life']
    assert type(index) is int and index in (*range(71000,71008),514230)
    assert type(life) is int and 0<=life<cfg.lives
    assert meta['source_index']==(514217 if index==514230 else index-11000)
    nested(meta['config'],asdict(cfg));nested(meta['cases'],[list(c) for c in CASES])
    nested(meta['times'],list(cfg.times));nested(meta['source_times'],list(cfg.source_times))
    nested(meta['selector_inputs'],list(SELECTOR_INPUTS));nested(meta['source_modes'],list(MODES))
    assert meta['tag']==TAG and meta['origin_tag']=='l20-three-rewrite-v1'
    assert type(meta['source_start_checkpoint']) is int and meta['source_start_checkpoint']==300
    assert meta['record_rule']==RECORD_RULE and meta['selector_rule']==SELECTOR_RULE
    for key in ('source_start_reused','source_trajectories_new','theta_start_zero','template_prior_supplied'):
        assert meta[key] is True
    for key in ('source_noise_reused','latent_theta_transmitted','source_shift_transmitted','learned_ontology'):
        assert meta[key] is False
    shapes=dict(targets=(2,16,16),source_starts=(2,3,3,16,16),source_shifts=(3,2),
        source_states=(2,3,2,len(cfg.source_times),4,16,16),written_fields=(2,3,2,16,16),
        permutations=(2,3,256),selector_inputs=(2,3,6,2048),selector_outputs=(2,3,6,2048),
        selector_scores=(2,3,6,2,16,16),prepared_fields=(2,3,5,16,16),
        packets=(42,3,2048),states=(42,3,len(cfg.times),3,16,16),values=(42,3,len(cfg.times),12))
    assert set(raw)==set(shapes)
    for key,shape in shapes.items():
        dtype=np.uint8 if key in ('packets','selector_inputs','selector_outputs') else np.int64 if key in ('permutations','source_shifts') else np.float64
        assert raw[key].shape==shape and raw[key].dtype==dtype and np.isfinite(raw[key]).all()
    np.testing.assert_array_equal(raw['targets'],templates())
    np.testing.assert_array_equal(raw['targets'],source['targets'][life])
    sm=meta['source_context'];assert set(sm)=={'index','tissue','ladder','blueprint'} and sm['index']==meta['source_index']
    stissue,sladder,sbp=physics.parameters(sm)
    assert (stissue.sigma,sbp.rho,sbp.c_m)==(.3,.002,.2)
    source_maximum=0.;score_maximum=0.;source_records=[];selector_records=[];expected_packets={}
    for role in (0,1):
        generations=[];selections=[]
        for gi in range(3):
            code=int(generator(TAG,index,life,f'g{gi+1}:source_shift').integers(1,256))
            shift=np.asarray(divmod(code,16),dtype=np.int64);np.testing.assert_array_equal(raw['source_shifts'][gi],shift)
            start=source['generation_states'][life,8*role,gi,4,:3]
            np.testing.assert_array_equal(raw['source_starts'][role,gi],start)
            entries=[]
            for mi,mode in enumerate(MODES):
                np.testing.assert_array_equal(raw['source_states'][role,gi,mi,0],np.concatenate((start,np.zeros((1,16,16)))))
                random=generator(TAG,index,life,f'g{gi+1}:source')
                if replay:
                    path,entry=replay_source(start,stissue,sladder,random,mode,shift,cfg)
                    source_maximum=max(source_maximum,compare(raw['source_states'][role,gi,mi],path))
                else:
                    for _ in range(cfg.source_steps): random.standard_normal((1,16,16))
                    entry=source_metadata(random,mode,shift)
                ref=raw['source_states'][role,gi,mi,-1,2];candidate=np.tanh(ref)
                assert candidate.std()>1e-9
                np.testing.assert_array_equal(raw['written_fields'][role,gi,mi],prior.project(candidate))
                latent=raw['source_states'][role,gi,mi,1:,3]
                assert np.all(abs(latent.mean(axis=(-2,-1)))<1e-14)
                assert np.all(abs(latent.std(axis=(-2,-1))-.3)<1e-14)
                entries.append(entry)
            np.testing.assert_array_equal(raw['source_states'][role,gi,0,:2],raw['source_states'][role,gi,1,:2])
            generations.append(entries)
            perm=generator(TAG,index,life,f'g{gi+1}:shuffle:{role}').permutation(256)
            np.testing.assert_array_equal(raw['permutations'][role,gi],perm)
            native,aligned=(packet(f) for f in raw['written_fields'][role,gi])
            shuffle=lambda b:packet(unpack(b).reshape(256)[perm].reshape(16,16))
            ideal=packet(prior.project(np.tanh(1.5*templates()[role])));zero=packet(np.zeros((16,16)))
            inputs=(native,aligned,shuffle(native),shuffle(aligned),packet(shifted(unpack(ideal),shift,False)),zero)
            results=[select(b) for b in inputs]
            for slot,(supplied,(output,scores,record)) in enumerate(zip(inputs,results)):
                assert raw['selector_inputs'][role,gi,slot].tobytes()==supplied
                assert raw['selector_outputs'][role,gi,slot].tobytes()==output
                np.testing.assert_allclose(raw['selector_scores'][role,gi,slot],scores,rtol=0,atol=1e-12)
                score_maximum=max(score_maximum,float(abs(raw['selector_scores'][role,gi,slot]-scores).max()))
                np.testing.assert_array_equal(np.sort(unpack(supplied).ravel()),np.sort(unpack(output).ravel()))
            selections.append([x[2] for x in results])
            bases=dict(native=native,blind=results[0][0],known=packet(shifted(unpack(native),shift)),
                aligned=aligned,aligned_blind=results[1][0])
            np.testing.assert_array_equal(raw['prepared_fields'][role,gi],np.stack([unpack(bases[k]) for k in BASES]))
            for field in raw['prepared_fields'][role,gi]:
                assert abs(float(field.mean()))<1e-14 and abs(float(field.std())-.3)<1e-14
            packets=bases|{k+'_shuffle':shuffle(v) for k,v in bases.items()}
            packets.update(shuffle_blind=results[2][0],aligned_shuffle_blind=results[3][0],blind_sham=bases['blind'],
                ideal=ideal,ideal_shifted=inputs[4],ideal_blind=results[4][0],zero=zero)
            for kind in ('blind','aligned_blind','native','known'):packets[kind+'_off']=bases[kind]
            assert results[4][0]==ideal and results[5][0]==zero
            for kind,b in packets.items():expected_packets[role,kind,gi]=b
        source_records.append(generations);selector_records.append(selections)
    nested(meta['source_paths'],source_records);nested(meta['selectors'],selector_records)
    tissue,ladder,bp=physics.parameters(meta);maximum=0.;records=[]
    for ci,(role,kind) in enumerate(CASES):
        entries=[]
        for gi in range(3):
            supplied=raw['packets'][ci,gi].tobytes()
            assert supplied==expected_packets[role,kind,gi]
            random=generator(TAG,index,life,f'g{gi+1}:birth')
            v=.2*random.standard_normal((1,16,16));birth_rng=canonical_digest(random.bit_generator.state)
            state=(v,v.copy(),v.copy());saved=[np.stack(state)[:,0]]
            np.testing.assert_array_equal(raw['states'][ci,gi,0],saved[0])
            random=generator(TAG,index,life,f'g{gi+1}:read')
            field=unpack(supplied) if not kind.endswith('_off') else np.zeros((16,16))
            for t in range(1,cfg.steps+1):
                noise=random.standard_normal((1,16,16))
                if replay:
                    state=physics.step(*state,field,tissue,ladder,0.,bp.rho,noise)
                    if t in cfg.times:saved.append(np.stack(state)[:,0])
            if replay:maximum=max(maximum,compare(raw['states'][ci,gi],np.stack(saved)))
            entries.append(dict(birth_rng=birth_rng,read_rng=canonical_digest(random.bit_generator.state),
                input_sha256=sha(supplied),packet_bytes=2048,enabled=not kind.endswith('_off'),
                writing=False,gain=0.,target_labels=False))
        records.append(entries)
    nested(meta['readers'],records)
    aliases=[((r,'blind'),(r,'blind_sham')) for r in (0,1)]
    aliases += [((r,k+'_off'),(r,'zero')) for r in (0,1) for k in ('blind','aligned_blind','native','known')]
    aliases += [((r,'ideal_blind'),(r,'ideal')) for r in (0,1)]+[((0,'zero'),(1,'zero'))]
    for a,b in aliases:np.testing.assert_array_equal(raw['states'][CASES.index(a)],raw['states'][CASES.index(b)])
    values=observe(raw['states'],raw['targets'],CASES,cfg)
    np.testing.assert_allclose(raw['values'],values,atol=1e-12,rtol=0)
    return dict(full_life_replay=replay,dynamics_max_abs=maximum,source_max_abs=source_maximum,
        metric_max_abs=float(abs(raw['values']-values).max()),selector_max_abs=score_maximum,
        reader_paths=126,exact_path_aliases=39,source_pairs=6,new_source_writes=12,
        selector_decisions=36,packet_lineage_checked=True,fresh_reset=True,exact_signs=True)


def check_block(raw,meta,cfg,replay=True,root=None):
    from laws_confirmation import l20_blind_alignment as p
    from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT
    root=DEFAULT_EXTERNAL_ROOT if root is None else root
    assert set(meta)=={'index','config','source_sha256','lives'}
    index=meta['index'];assert type(index) is int and index in (*range(71000,71008),514230)
    nested(meta['config'],asdict(cfg));assert len(meta['lives'])==cfg.lives
    assert all(x.shape[0]==cfg.lives for x in raw.values())
    source,_=p.load_source(index,root)
    assert meta['source_sha256']=={str(x):sha256_file(x) for x in p.source_paths(index,root)}
    for life,row in enumerate(meta['lives']):
        assert row['index']==index and row['life']==life
        proof=row['replay']
        expected=dict(full_life_replay=True,dynamics_max_abs=proof['dynamics_max_abs'],
            source_max_abs=proof['source_max_abs'],metric_max_abs=proof['metric_max_abs'],selector_max_abs=proof['selector_max_abs'],
            reader_paths=126,exact_path_aliases=39,source_pairs=6,new_source_writes=12,selector_decisions=36,
            packet_lineage_checked=True,fresh_reset=True,exact_signs=True)
        nested(proof,expected)
        for key,tolerance in (('dynamics_max_abs',1e-10),('source_max_abs',1e-10),('metric_max_abs',1e-12),('selector_max_abs',1e-12)):
            assert 0<=proof[key]<=tolerance
        current=check_life({k:x[life] for k,x in raw.items()},row,cfg,source,replay)
        if replay:nested(proof,current)
    return True


def check_source(raw,meta,source):
    """Known D127 bridge; physics below and older independent reader verifier."""
    from laws_confirmation import l20_blind_alignment as p
    from laws_confirmation import l20_inverse_address as d128
    kept_raw={k:raw[k] for k in ('packets','states','targets')}
    kept_meta={k:v for k,v in meta.items() if k not in ('source_paths','source_context','replay')}
    assert set(raw)==set(kept_raw)|{'source_starts','source_shifts','source_states','written_fields'}
    reader=d128.checker().check_source(kept_raw,kept_meta,source)
    np.testing.assert_array_equal(raw['source_starts'],source['source_starts'][0])
    np.testing.assert_array_equal(raw['source_shifts'],source['source_shifts'][0])
    np.testing.assert_array_equal(raw['source_states'],source['source_states'][0][:,:,[1,0]])
    assert meta['source_context']['index']==514217
    tissue,ladder,bp=physics.parameters(meta['source_context']);assert (bp.rho,bp.c_m)==(.002,.2)
    maximum=0.;records=[]
    for r in (0,1):
        generations=[]
        for gi in range(3):
            entries=[]
            for mi,mode in enumerate(MODES):
                states,entry=replay_source(raw['source_starts'][r,gi],tissue,ladder,
                    generator('l20-source-translation-v1',514227,0,f'g{gi+1}:source'),mode,raw['source_shifts'][gi],p.CONFIG)
                maximum=max(maximum,compare(raw['source_states'][r,gi,mi],states))
                expected=prior.project(np.tanh(states[-1,2]))
                np.testing.assert_array_equal(raw['written_fields'][r,gi,mi],expected)
                ci=d128.checker().SOURCE_CASES.index((r,mode))
                assert packet(expected)==source['packets'][0,ci,gi].tobytes()
                entries.append(entry)
            generations.append(entries)
        records.append(generations)
    nested(meta['source_paths'],records)
    return reader|dict(known_source_writers=12,full_source_replay=True,source_max_abs=maximum)


def check_summary(summary, blocks, cfg):
    assert len(blocks) == 8
    values = np.stack([b['values'] for b in blocks])
    assert values.shape == (8, cfg.lives, 42, 3, len(cfg.times), 12) and np.isfinite(values).all()
    draws = generator(TAG, 0, 0, 'bootstrap').integers(0, 8, (10000, 8)); rows = []
    names=('blind_minus_native','known_minus_native','blind_minus_known','aligned_blind_minus_aligned',
        'blind_minus_aligned','native_minus_aligned','native_minus_native_shuffle','blind_minus_blind_shuffle',
        'known_minus_known_shuffle','aligned_minus_aligned_shuffle','aligned_blind_minus_aligned_blind_shuffle',
        'blind_minus_shuffle_blind','aligned_blind_minus_aligned_shuffle_blind','native_minus_zero','blind_minus_zero',
        'known_minus_zero','aligned_minus_zero','aligned_blind_minus_zero','ideal_minus_zero','ideal_blind_minus_ideal_shifted',
        'ideal_shifted_minus_zero','shuffle_blind_minus_native_shuffle','aligned_shuffle_blind_minus_aligned_shuffle',
        'specificity_gain','matched_specificity_gain','source_interaction')
    for observer, col in (('qualified', 0), ('sign', 2)):
        for stage in ('all', 1, 2, 3):
            for name in names:
                effects = []
                for role in (0, 1):
                    if name=='specificity_gain': weights={'blind':1,'blind_shuffle':-1,'native':-1,'native_shuffle':1}
                    elif name=='matched_specificity_gain': weights={'blind':1,'shuffle_blind':-1,'native':-1,'native_shuffle':1}
                    elif name=='source_interaction': weights={'blind':1,'native':-1,'aligned_blind':-1,'aligned':1}
                    else: weights=dict(zip(name.split('_minus_'),(1,-1)))
                    effect = np.zeros((8, cfg.lives, 3 if stage == 'all' else 1))
                    for kind, weight in weights.items():
                        ci = CASES.index((role, kind))
                        for slot, gi in enumerate(range(3) if stage == 'all' else (stage-1,)):
                            effect[:, :, slot] += weight*(values[:, :, ci, gi, -1, col]-values[:, :, ci, gi, -1, col+1])
                    effects.append(effect.mean(axis=-1))
                for role, effect in ((0, effects[0]), (1, effects[1]), ('both', (effects[0]+effects[1])/2)):
                    rows.append(dict(name=name, stage=stage, role=role, observer=observer, **prior.stats(effect, draws)))
    get = lambda name, role='both': next(r for r in rows if (r['name'], r['stage'], r['role'], r['observer']) == (name, 'all', role, 'qualified'))
    gates = [get('ideal_minus_zero', r) for r in (0, 1)]
    disagreements = [[int((b['targets'][l, 0] != b['targets'][l, 1]).sum()) for l in range(cfg.lives)] for b in blocks]
    instrument = all(r['pointwise_block_bootstrap_95'][0] > 0 for r in gates) and all(n > 0 for row in disagreements for n in row)
    qualifies = {}
    for kind in BASES:
        specific = get(kind+'_minus_'+kind+'_shuffle')
        qualifies[kind] = bool(instrument and specific['pointwise_block_bootstrap_95'][0] > 0 and all(
            get(kind+'_minus_'+kind+'_shuffle', r)['mean'] > 0 and get(kind+'_minus_zero', r)['pointwise_block_bootstrap_95'][0] > 0 for r in (0, 1)))
    matched={}
    for kind,other in (('blind','shuffle_blind'),('aligned_blind','aligned_shuffle_blind')):
        matched[kind]=bool(instrument and get(kind+'_minus_'+other)['pointwise_block_bootstrap_95'][0]>0
            and all(get(kind+'_minus_'+other,r)['mean']>0 for r in (0,1)))
    calibration_gates=[get('ideal_blind_minus_ideal_shifted',r) for r in (0,1)]
    calibration=bool(instrument and all(x['pointwise_block_bootstrap_95'][0]>0 for x in calibration_gates))
    primary=get('blind_minus_native');directions=[get('blind_minus_native',r) for r in (0,1)]
    label='READOUT_NOT_QUALIFIED' if not instrument else 'ALIGNMENT_CONTROL_NOT_QUALIFIED' if not calibration else 'BLIND_EFFECT_UNRESOLVED'
    if instrument and calibration:
        if primary['pointwise_block_bootstrap_95'][0]>0 and all(r['mean']>0 for r in directions):
            label='BLIND_ALIGNMENT_QUALIFIED' if qualifies['blind'] and matched['blind'] else 'BLIND_GAIN_WITHOUT_CONTENT_QUALIFICATION'
        elif primary['pointwise_block_bootstrap_95'][1]<0 and all(r['mean']<0 for r in directions):
            label='BLIND_HARM_DETECTED'
    expected=dict(schema='l20_blind_alignment_v1',label=label,primary=primary,directional_primary=directions,
        content_qualified=qualifies,matched_control_qualified=matched,readout_qualified=bool(instrument),calibration_qualified=calibration,
        readout_gates=gates,calibration_gates=calibration_gates,contrasts=rows,target_disagreement_cells=disagreements,
        cases=[list(c) for c in CASES],times=list(cfg.times),metrics=list(METRICS),
        cell_means=values.mean(axis=(0,1)).tolist(),reader_blocks=list(range(71000,71008)),source_blocks=list(range(60000,60008)),
        blocks=8,lives_per_block=cfg.lives,generations_reused=3,reader_paths=8*cfg.lives*126,
        packet_bytes=2048,reused_source_starts=True,new_renewal_cohort=False,new_source_writes=8*cfg.lives*12,
        source_start_checkpoint=300,source_steps=cfg.source_steps,source_times=list(cfg.source_times),
        source_noise_reused=False,template_prior_supplied=True,learned_ontology=False,
        record_rule=RECORD_RULE,selector_rule=SELECTOR_RULE,record_reprojected=False,source_shift_transmitted=False,
        known_shift_is_upper_bound=False,absolute_fidelity_gate=None,equivalence_test=False,
        secondary_intervals_multiplicity_adjusted=False)
    nested(summary,expected);return True


if __name__=='__main__':
    from laws_confirmation.l20_blind_alignment_run import main
    main(default_command='audit')
