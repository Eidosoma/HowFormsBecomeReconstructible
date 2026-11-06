"""Independent saved-data reductions, paired Monte Carlo errors, and custody.

No new physical futures. Production dynamics were independently replayed already.
"""
import itertools, os, signal, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis  # Only used to reproduce report text after independent reductions.


def counts(x):
    return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)


def integer(x):
    x = np.asarray(x); out = np.rint(x * 12).astype(np.int64)
    near(out / 12, x); assert np.isin(out, (0, 3, 4, 6, 12)).all()
    return out


def chosen_masks(view, world):
    if view == 'all_masks': return list(range(4))
    if view.startswith('mask:'): return [MASKS.index(view[5:])]
    y, x = np.indices((16, 16)); task = world // 4
    target = np.where((y if task < 2 else x) < 8, 1, -1) * (-1 if task % 2 else 1)
    choices = []
    for mask in range(4):
        keep = (y if mask < 2 else x) // 8 == mask % 2
        mean = target[keep].mean()
        label = 'positive_half_retained' if mean == 1 else 'negative_half_retained' if mean == -1 else 'both_polarities_retained'
        if label == view[9:]: choices.append(mask)
    assert choices
    return choices


def differences(x):
    a, b, c, d = [x[:, i] for i in range(4)]
    out = np.stack([b-a, d-c, c-a, d-b, d-a, b-c, d-c-b+a], axis=1)
    if np.issubdtype(out.dtype, np.integer):
        for left, right in ((out[:, 4], out[:, 0]+out[:, 3]), (out[:, 4], out[:, 2]+out[:, 1]),
                            (out[:, 6], out[:, 1]-out[:, 0]), (out[:, 6], out[:, 3]-out[:, 2])):
            np.testing.assert_array_equal(left, right)
    return out


def error_of_mean(x, axis):
    # Pairwise identity: sum_{i<j}(xi-xj)^2 / [K^2(K-1)] = sample variance / K.
    # This independently checks production's np.std(ddof=1)/sqrt(K) calculation.
    values = np.moveaxis(np.asarray(x, dtype=np.float64), axis, 0); k = len(values)
    assert k == 8
    total = np.zeros_like(values[0])
    for i in range(k):
        for j in range(i): total += (values[i]-values[j])**2
    return np.sqrt(total / (k*k*(k-1)))


def sign_joint(a, b):
    out = np.zeros((*a.shape[1:], 3, 3), dtype=np.int64)
    for i, j in itertools.product(range(3), repeat=2):
        out[..., i, j] = ((np.sign(a) == i-1) & (np.sign(b) == j-1)).sum(0)
    return out


def local_check(data, saved):
    expected = {}; entries = 0
    for p in PROFILES:
        for suffix in ('', '_margin'):
            x = data[p+suffix].astype(np.float64) / (1 if suffix else 12)
            delta = x[:, 1]-x[:, 0]
            expected[p+suffix+'_mean'] = x.sum(3)/8
            expected[p+suffix+'_mc_se'] = error_of_mean(x, 3)
            expected[p+suffix+'_packet_mean'] = delta.sum(2)/8
            expected[p+suffix+'_packet_mc_se'] = error_of_mean(delta, 2)
    assert set(expected) == set(saved)
    for k, value in expected.items(): near(saved[k], value); entries += value.size
    return entries


def reduce_block(cases, data, saved):
    lookup = {case_key(c): i for i, c in enumerate(cases)}
    assert len(lookup) == len(cases) == 192
    assert set(lookup) == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES, range(16)))
    populated = 0
    for j, condition in enumerate(CONDITIONS):
        damage, family, group, view, source = condition.split('|'); worlds = []
        for w in range(16):
            history = cases[lookup[damage, family, MASKS[0], source, w]]['developed_score']
            assert all(cases[lookup[damage, family, mask, source, w]]['developed_score'] == history for mask in MASKS)
            if group == 'all' or group == f'message:{w//4}' or (group == 'history:unique_pass' and history == 1) or (group == 'history:other' and history != 1): worlds.append(w)
        n = len(worlds); assert saved['records'][j] == n
        if not n:
            for array in saved.values():
                assert np.isnan(array[j]).all() if np.issubdtype(array.dtype, np.floating) else (array[j] == 0).all()
            continue
        ids = np.array([[lookup[damage, family, MASKS[m], source, w] for m in chosen_masks(view, w)] for w in worlds])
        m = ids.shape[1]; assert saved['mask_cases'][j] == n*m and saved['position_futures'][j] == n*8
        values = [data[p][ids].astype(np.int64) for p in PROFILES]
        assert [v.shape[3:5] for v in values] == [(1, 8), (4, 8)]
        # Exact common denominator of four births: C remains ONE actual state.
        summed = np.concatenate([v.sum((1, 3))*(4//v.shape[3]) for v in values], axis=1)
        delta = differences(summed)
        assert np.all(delta[:, (0, 1, 6), :, 0] == 0)
        injury = np.concatenate([v.sum((3, 4))*(4//v.shape[3]) for v in values], axis=2).reshape(-1, 4, 6, 4)
        future_delta = delta.transpose(0, 2, 1, 3, 4).reshape(-1, 7, 6, 4)
        margin = np.concatenate([data[p+'_margin'][ids].sum((1, 3))/v.shape[3] for p, v in zip(PROFILES, values)], axis=1)
        expected = {}
        for prefix, level, effect in (('', summed.sum(0)/(12*n*m*4), delta.sum(0)/(12*n*m*4)),
                                      ('margin_', margin.sum(0)/(n*m), differences(margin).sum(0)/(n*m))):
            expected['future_'+prefix+'levels'] = level
            expected['future_'+prefix+'effects'] = effect
            expected[prefix+'levels'] = level.sum(1)/8
            expected[prefix+'effects'] = effect.sum(1)/8
            expected[prefix+'level_mc_se'] = error_of_mean(level, 1)
            expected[prefix+'effect_mc_se'] = error_of_mean(effect, 1)
        temporal = summed[:, :, :, 5]-summed[:, :, :, 4]
        future_temporal = temporal.sum(0)/(12*n*m*4)
        expected.update(record_counts=counts(delta.sum(2)), case_counts=counts(differences(injury)),
            future_counts=counts(future_delta), timing_joint_record=sign_joint(delta.sum(2)[:, :, 4], delta.sum(2)[:, :, 5]),
            timing_joint_future=sign_joint(future_delta[:, :, 4], future_delta[:, :, 5]),
            temporal_change=future_temporal.sum(1)/8, temporal_mc_se=error_of_mean(future_temporal, 1),
            future_temporal_change=future_temporal, temporal_counts=counts(temporal.sum(2)),
            temporal_future_counts=counts(temporal.transpose(0, 2, 1, 3).reshape(-1, 4, 4)),
            original_levels=data['original'][ids].astype(np.int64).sum((0, 1, 2, 3))/(12*n*m*4*8))
        assert set(expected) | {'records', 'mask_cases', 'position_futures'} == set(saved)
        for name, value in expected.items():
            if np.issubdtype(saved[name].dtype, np.integer): np.testing.assert_array_equal(saved[name][j], value)
            else: near(saved[name][j], value)
        for field, count in (('timing_joint_record', 'record_counts'), ('timing_joint_future', 'future_counts')):
            np.testing.assert_array_equal(expected[field].sum(-1), expected[count][:, 4])
            np.testing.assert_array_equal(expected[field].sum(-2), expected[count][:, 5])
        populated += 1
    return populated


def global_check(run, blocks):
    saved = arrays(run/'SUMMARY.npz'); expected_keys = set(); weights = np.stack([b['records'] for b in blocks])
    for name in blocks[0]:
        stacked = np.stack([b[name] for b in blocks]); expected_keys.add('block_'+name)
        if np.issubdtype(stacked.dtype, np.integer):
            np.testing.assert_array_equal(saved['block_'+name], stacked)
            np.testing.assert_array_equal(saved[name], stacked.sum(0)); expected_keys.add(name); continue
        near(saved['block_'+name], stacked)
        if name.startswith('future_'): continue
        equal = np.full_like(stacked[0], np.nan); pooled = equal.copy()
        for j in range(len(CONDITIONS)):
            ok = weights[:, j] > 0
            if not ok.any(): continue
            v, w = stacked[ok, j], weights[ok, j].astype(float)
            if name.endswith('_mc_se'):
                equal[j] = np.sqrt(np.sum(v*v, axis=0))/len(w)
                pooled[j] = np.sqrt(np.tensordot(w*w, v*v, axes=1))/w.sum()
            else:
                equal[j] = v.sum(0)/len(w); pooled[j] = np.tensordot(w, v, axes=1)/w.sum()
        near(saved['equal_'+name], equal); near(saved['pooled_'+name], pooled)
        expected_keys.update(('equal_'+name, 'pooled_'+name))
    assert set(saved) == expected_keys and (run/'REPORT.md').read_text() == analysis.report(saved, 'confirmation')
    return saved


def writer_state_digest(state):
    arrays_by_name = {k: digest(f"{v.dtype}:{v.shape}:".encode()+v.tobytes(order='C')) for k,v in state.items()}
    return digest(json.dumps(arrays_by_name,sort_keys=True,separators=(',',':')).encode())


def source_custody(sub, index, cases):
    folder=sub/'source';baseline=folder/'baseline';source_values={};checked=0
    for name in ('before','parent','original','built','capture_residual','develop_residual','initial_residual'):
        path=baseline/(name+'.npz');raw=arrays(path);meta=read(path.with_suffix('.json'))
        assert meta['sha256']==sha(path) and meta['arrays']==identities(raw)
        source_values[name]=raw;checked+=len(raw)
    proof=read(baseline/'CHECK.json');assert proof['status']=='PASS' and not proof['source_population_reused']
    assert proof['families']==['residual'] and proof['all_cases_retained'] and proof['independently_replayed_during_acquisition']
    assert proof['baseline_saved_arrays']==checked
    exact(source_values['original']['codes'],codebook(),'source observer codebook')
    source=source_values['initial_residual'];developed=source_values['develop_residual']
    exact(source['incoming'],source_values['capture_residual']['s1000_theta'],'captured source packet')
    exact(source['developed_V'],developed['s1000_V'],'source developed body')
    for k in OBS_KEYS:exact(source['developed_'+k],developed[k],'source history '+k)
    history=read(baseline/'history_residual.json')
    for w,h in enumerate(history):assert h['world']==w and h['developed_score']==float(developed['correctness'][w,0])
    for c in cases:
        assert c['block']==index and c['corruption']==0 and c['family']=='residual' and c['body_source']=='own'
        assert c['message']==c['world']//4 and c['replicate']==c['world']%4
        assert c['developed_score']==history[c['world']]['developed_score']
    mixtures=arrays(folder/'MIXTURES.npz');meta=read(folder/'MIXTURES.json')
    assert meta['arrays']==identities(mixtures) and meta['sha256']==sha(folder/'MIXTURES.npz')
    exact(mixtures['original'],source['incoming'],'original incoming comparator')
    seed=int.from_bytes(hashlib.sha256(json.dumps(['TT046_damage_confirmation_v1','corruption','confirmation',index,0],separators=(',',':')).encode()).digest()[:16],'little')
    rng=np.random.Generator(np.random.PCG64(seed));draw=rng.standard_normal((4,16,16))
    noise=ref.project(np.concatenate([draw]*4),.3);exact(mixtures['noise'],noise,'independent corruption')
    for damage,eta in (('mix000',0.),('mix050',.5),('mix100',1.)):
        value=source['incoming'].copy() if eta==0 else ref.project((1-eta)*source['incoming']+eta*noise,.3)
        exact(mixtures[damage],value,'mixture '+damage)
    assert meta['metadata']['corruption_seed']==seed
    births_saved=[]
    for b in range(4):
        birth=arrays(folder/f'BIRTH_{b}.npz');record=read(folder/f'BIRTH_{b}.json')
        addr=birth_address('confirmation',index,b);independent=ref.Coupled(ref.READ_TAG,addr,'assay_birth',4)
        v=.2*independent.standard_normal((16,16,16));v-=v.mean(axis=(-2,-1),keepdims=True)
        exact(birth['V'],v,'saved fresh birth');exact(birth['ema'],v);exact(birth['R'],np.zeros_like(v))
        assert record['arrays']==identities(birth) and record['address']==addr and record['rng_final']==independent.digest()
        births_saved.append(birth)
    writers={};ctx=context(index);score_count=0
    raw_address=json.dumps(['TT022_serial_capture_v1',index,0,1,'fission'],separators=(',',':')).encode()
    addr=int.from_bytes(hashlib.sha256(raw_address).digest()[:16],'little');injury=ref.Coupled(ref.SOURCE_TAG,addr,'fission',4)
    axes=injury.integers(0,2,16);sides=injury.integers(0,2,16);grid=np.indices((16,16))
    kept=np.stack([grid[a]//8==s for a,s in zip(axes,sides)])
    jitter=ctx['tissue'].copy_jitter*injury.standard_normal((16,16,16))
    exact(mixtures['jitter'],jitter,'original injury jitter');exact(source['fresh'],~kept,'original injury mask')
    exact(source['injured_V'],np.where(kept,source['developed_V'],ctx['tissue'].resting)+jitter,'original source injury')
    assert meta['metadata']['fission_address']==addr and meta['metadata']['fission_rng_final']==injury.digest()
    for damage,mask in itertools.product(DAMAGE,MASKS):
        pair=[];mi=MASKS.index(mask);keep=np.indices((16,16))[mi//2]//8==mi%2
        initial_v=np.where(keep,source['developed_V'],ctx['tissue'].resting)+mixtures['jitter']
        for packet in (0,1):
            name=f'{damage}_{mask}_T{packet}';raw=arrays(folder/(name+'.npz'));body=arrays(folder/(name+'_body.npz'));info=read(folder/(name+'.json'))
            assert info['arrays']==dict(state=identities(raw),body=identities(body))
            assert info['files']==dict(state=sha(folder/(name+'.npz')),body=sha(folder/(name+'_body.npz')))
            assert info['proof']==dict(native_arrays=24,max_native_error=0.,rng_match=True)
            start=dict(V=initial_v,ema=np.zeros_like(initial_v),R=initial_v-ctx['tissue'].resting/2,theta=mixtures[damage])
            for k in KEYS:exact(raw['s0_'+k],start[k],'writer starting '+k)
            m=info['metadata'];assert m['input_sha256']==writer_state_digest(start)
            assert (m['write_start'],m['write_end'])==((0,0) if packet==0 else (901,1000))
            assert m['write_updates']==(0 if packet==0 else 100) and m['total_updates']==1000
            assert m['nonwriting_exact_checks']==(1000 if packet==0 else 900)
            for t in WRITER_TIMES:
                if packet==0 or t<=900:exact(raw[f's{t}_theta'],mixtures[damage],'saved nonwriting hold')
                observed={k:body[f's{t}_{k}'] for k in OBS_KEYS}
                ref.scores(codebook(),dict(observed,s1000_V=raw[f's{t}_V']),ctx['readout']);score_count+=1
            assert m['final_theta_sha256']==digest(raw['s1000_theta'].tobytes())
            pair.append((raw,info));writers[name]=raw
        assert pair[0][1]['metadata']['rng_final']==pair[1][1]['metadata']['rng_final']
        for t in (0,1,100,900):
            for k in KEYS:exact(pair[0][0][f's{t}_{k}'],pair[1][0][f's{t}_{k}'],'paired writer prefix')
    return writers,births_saved,checked,score_count


def endpoint_custody(index, sub, cases, data, outputs):
    lookup={case_key(c):i for i,c in enumerate(cases)};cache={};streams={};checked=original_checked=0
    writers,births_saved,source_arrays,writer_scores=source_custody(sub,index,cases)
    links=read(sub/'ALIASES.json');assert len(links)==12
    assert {key(a) for a in links}==set(itertools.product(DAMAGE,FAMILIES,MASKS,SOURCES))
    by_context={key(a):a for a in links}
    def get(name):
        if name not in cache:
            path=sub/(name+'_body.npz');body=arrays(path);info=read(sub/(name+'.json'))
            assert info['proof']==dict(native_arrays=24,body_scores=6,max_native_error=0.,rng_match=True)
            assert info['arrays']['body']==identities(body)
            assert info['files']==dict(state=outputs[str(sub/(name+'.npz'))],body=outputs[str(path)])
            assert info['storage_lossless'] and info['stored_state_arrays']==19 and info['expanded_state_arrays']==24
            packed,expanded=info['arrays']['packed_state'],info['arrays']['expanded_state']
            assert set(packed)=={'theta'}|{f's{t}_{k}' for t in TIMES for k in BODY_KEYS}
            assert set(expanded)=={f's{t}_{k}' for t in TIMES for k in KEYS}
            assert all(expanded[f's{t}_{k}']==packed['theta' if k=='theta' else f's{t}_{k}'] for t in TIMES for k in KEYS)
            m=info['metadata'];assert m['profile']=='fresh' and m['feedback'] is False and m['c_m']==0 and m['rho']==.002
            assert m['write_updates']==m['skipped_noise_fields']==0 and m['updates']==m['packet_hold_checks']==1000
            cache[name]=(body,info)
        return cache[name]
    for alias in links:
        k=key(alias);mi=MASKS.index(alias['mask']);ids=np.array([lookup[(*k,w)] for w in range(16)])
        labels=np.array([[w//4,(w//4+2)%4,mi^1,mi] for w in range(16)]);world=np.arange(16)[:,None]
        expected_names=[f'{alias["damage"]}_{alias["mask"]}_T{p}' for p in (0,1)]
        assert alias['source_writers']==expected_names;parent=[writers[n] for n in expected_names]
        for profile in PROFILES:
            assert len(alias['profiles'][profile])==(1 if profile=='continuing' else 4)
            for birth,by_future in enumerate(alias['profiles'][profile]):
                assert len(by_future)==8
                initial_body={k:parent[0]['s1000_'+k] for k in BODY_KEYS} if profile=='continuing' else births_saved[birth]
                starts=[dict(initial_body,theta=parent[p]['s1000_theta']) for p in (0,1)]
                hashes=[digest(state_bytes(s)) for s in starts];start_ids=[identities(s) for s in starts]
                for future,names in enumerate(by_future):
                    assert len(names)==2
                    for packet,name in enumerate(names):
                        body,info=get(name);meta=info['metadata'];assert meta['address']==future_address('confirmation',index,future)
                        assert meta['input_sha256']==hashes[packet] and meta['packet_sha256']==start_ids[packet]['theta']['sha256']
                        assert info['physical_identity']==digest(encoded(['assay',meta['address'],0])+state_bytes(starts[packet]))
                        for field in KEYS:assert info['arrays']['expanded_state']['s0_'+field]==start_ids[packet][field]
                        sig=(meta['rng_start'],meta['rng_final'],encoded(meta['checkpoint_rng']));assert streams.setdefault(future,sig)==sig
                        probability=[];margin=[]
                        for t in TIMES:
                            probability.append(body[f's{t}_probabilities'][world,labels])
                            scores=body[f's{t}_scores'];top=np.sort(scores,axis=1)[:,-2:]
                            other=np.where(labels==scores.argmax(axis=1)[:,None],top[:,:1],top[:,1:])
                            margin.append(scores[world,labels]-other)
                        np.testing.assert_array_equal(data[profile][ids,packet,birth,future],integer(np.stack(probability,axis=1)))
                        near(data[profile+'_margin'][ids,packet,birth,future],np.stack(margin,axis=1));checked+=16
        intact=by_context['mix000','residual',alias['mask'],'own']['profiles']['fresh']
        assert len(alias['original'])==4
        for birth,names in enumerate(alias['original']):
            assert len(names)==8
            for future,name in enumerate(names):
                assert name==intact[birth][future][0],'original must be the intact-preservation physical assay'
                body,_=get(name)
                np.testing.assert_array_equal(data['original'][ids,birth,future],integer(body['s1000_probabilities'][world,labels]))
                original_checked+=16
    assert len(cache)==read(sub/'CHECK.json')['verification']['physical_continuations']
    assert len(streams)==len({v[0] for v in streams.values()})==8
    return checked,original_checked,source_arrays,writer_scores


def confirmation_check(saved, observed):
    # Independent CDF inversion and pairwise variance; no inference.py reduction call.
    import math
    from scipy.special import stdtr
    def quantile(probability):
        lo,hi=0.,16.
        for _ in range(80):
            mid=(lo+hi)/2
            if stdtr(31,mid)<probability:lo=mid
            else:hi=mid
        return (lo+hi)/2
    critical=quantile(.9875);pointwise=quantile(.975);endpoint_values={}
    full=INDEX['mix100|residual|all|all_masks|own'];intact=INDEX['mix000|residual|all|all_masks|own']
    for ti,t in ((4,900),(5,1000)):
        a=saved['block_effects'][:,full,1,ti,0];b=saved['block_effects'][:,intact,1,ti,0]
        endpoint_values[f'full_{t}']=a;endpoint_values[f'full_minus_intact_{t}']=a-b
    assert set(observed['endpoints'])==set(endpoint_values);passed=[];verified={}
    for name,x in endpoint_values.items():
        bound=2 if 'minus_intact' in name else 1;assert len(x)==32 and (np.abs(x)<=bound).all()
        mean=float(x.sum()/32);se=math.sqrt(math.fsum(float((x[i]-x[j])**2) for i in range(32) for j in range(i))/(32*32*31))
        bounded=bound*math.sqrt(2*math.log(80)/32);radius=critical*se if se else bounded
        r95=pointwise*se if se else bound*math.sqrt(2*math.log(40)/32)
        clip=lambda v:max(-bound,min(bound,v));lower=clip(mean-radius)
        e=observed['endpoints'][name];ci=e['interval'];near(e['block_values'],x)
        expected=dict(mean=mean,standard_error=se,lower_one_sided=lower,alpha=.0125,
            pointwise_two_sided_95=[clip(mean-r95),clip(mean+r95)],hoeffding_lower_sensitivity=clip(mean-bounded))
        for k,v in expected.items():near(ci[k],v)
        assert ci['n']==32 and ci['range']==[-bound,bound]
        assert ci['method']==('approximate paired block Student-t' if se else 'bounded Hoeffding zero-variance fallback')
        classification='DIRECTIONAL_SUPERIORITY_PASS' if lower>0 else 'NOT_CONFIRMED'
        assert e['classification']==classification and e['margin']==0.;passed.append(lower>0)
        verified[name]=dict(**e,block_harm_tie_gain=[int((x<0).sum()),int((x==0).sum()),int((x>0).sum())])
    status='CONFIRMED_JOINT_DAMAGE_DEPENDENT_PACKET_BENEFIT' if all(passed) else 'NOT_CONFIRMED'
    assert observed['status']==status and observed['population_units']==32 and observed['family_alpha']==.05
    assert observed['per_endpoint_alpha']==.0125 and observed['approximate_coverage'] and observed['secondary_results_cannot_rescue_primary']
    assert observed['multiplicity']=='Bonferroni across four co-primary endpoints' and not observed['automatic_extension']
    return dict(status=status,endpoints=verified,critical_t_31_df_one_sided_0_0125=critical,
        independently_recomputed=True,approximate_coverage=True,hoeffding_sensitivity_confirms=all(e['interval']['hoeffding_lower_sensitivity']>0 for e in verified.values()))


def main():
    tick=time.monotonic();os.sched_setaffinity(0,{6});assert os.getpriority(os.PRIO_PROCESS,0)==0
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('600-second completion review deadline')));signal.alarm(600)
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs'] and read(ROOT/'COMPLETION_REVIEW_V2_RESOURCE.json')['admission_pass']
    run=ROOT/'runs/confirmation_v1';complete=read(run/'COMPLETE.json');frozen=read(ROOT/'FREEZE.json');manifest=read(ROOT/'SOURCE_MANIFEST.json')
    assert complete['status']=='COMPLETE' and complete['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert complete['seconds']<frozen['deadline_seconds'] and complete['inputs']==frozen['inputs']==inputs()
    inspection=read(ROOT/'RESULT_INSPECTION.json');assert inspection['complete_sha256']==sha(run/'COMPLETE.json')
    verify(frozen['evidence']);verify(complete['inputs']);verify(complete['outputs']);verify(manifest['evidence'])
    print(json.dumps(dict(status='ALL_OUTPUT_HASHES_VERIFIED',elapsed_seconds=time.monotonic()-tick)),flush=True)
    seeds=read(ROOT/'SEEDS.json');addresses=[]
    for role in ROLES:
        for index in selected(role):
            value=seeds['addresses'][role][str(index)]
            expected=dict(corruption=[corruption_seed(role,index,0)],birth=[birth_address(role,index,b) for b in range(births(role))],
                          future=[future_address(role,index,k) for k in range(futures(role))])
            assert value==expected
            for values in value.values():addresses+=values
    assert len(addresses)==len(set(addresses))==424 and not set(addresses)&set(seeds['native_addresses'])
    blocks=[];reduced=endpoints=original_endpoints=local_entries=source_arrays=writer_scores=0
    for index in BLOCKS:
        sub=run/f'tissue_{index}';observed=arrays(sub/'AGGREGATE.npz');cases=read(sub/'CASES.json');data=arrays(sub/'ENDPOINTS.npz')
        assert read(sub/'USED_INPUTS.json')=={},'production must use newly generated sources'
        config=read(sub/'CONFIG.json');assert config['block']==index and config['population_confirmation'] and not config['source_population_reused']
        assert config['addresses']==seeds['addresses']['confirmation'][str(index)]
        for p in PROFILES:
            assert data[p].shape==data[p+'_margin'].shape==(192,2,1 if p=='continuing' else 4,8,6,4)
            assert data[p].dtype==np.int16 and np.isin(data[p],(0,3,4,6,12)).all()
            assert data[p+'_margin'].dtype==np.float64 and np.isfinite(data[p+'_margin']).all()
        assert data['original'].shape==(192,4,8,4) and data['original'].dtype==np.int16
        n,o,s,w=endpoint_custody(index,sub,cases,data,complete['outputs']);endpoints+=n;original_endpoints+=o;source_arrays+=s;writer_scores+=w
        local_entries+=local_check(data,arrays(sub/'LOCAL.npz'));reduced+=reduce_block(cases,data,observed);blocks.append(observed)
        if (index-BLOCKS[0]+1)%4==0:
            print(json.dumps(dict(blocks_reviewed=index-BLOCKS[0]+1,elapsed_seconds=time.monotonic()-tick,status='REVIEWED')),flush=True)
    saved=global_check(run,blocks);primary=confirmation_check(saved,read(run/'CONFIRMATION.json'));panels={}
    for damage in DAMAGE:
        j=INDEX[f'{damage}|residual|all|all_masks|own'];contrasts={}
        for q,name in enumerate(COMPARISONS):
            block_values=saved['block_effects'][:,j,q,:,0]
            contrasts[name]=dict(by_time_pp=(100*saved['equal_effects'][j,q,:,0]).tolist(),
                conditional_mc_se_by_time_pp=(100*saved['equal_effect_mc_se'][j,q,:,0]).tolist(),
                block_effects_by_time_pp=(100*block_values).tolist(),
                block_harm_tie_gain_by_time=np.stack([(block_values<0).sum(0),(block_values==0).sum(0),(block_values>0).sum(0)],axis=-1).tolist(),
                record_harm_tie_gain_by_time=saved['record_counts'][j,q,:,0].tolist(),case_harm_tie_gain_by_time=saved['case_counts'][j,q,:,0].tolist(),
                position_future_harm_tie_gain_by_time=saved['future_counts'][j,q,:,0].tolist(),
                record_timing_sign_joint=saved['timing_joint_record'][j,q,0].tolist(),position_future_timing_sign_joint=saved['timing_joint_future'][j,q,0].tolist(),
                continuous_margin_by_time=saved['equal_margin_effects'][j,q,:,0].tolist(),
                continuous_margin_conditional_mc_se_by_time=saved['equal_margin_effect_mc_se'][j,q,:,0].tolist())
        panels[damage]=dict(contrasts=contrasts,levels_by_time_percent=(100*saved['equal_levels'][j,:,:,0]).tolist(),
            level_conditional_mc_se_by_time_pp=(100*saved['equal_level_mc_se'][j,:,:,0]).tolist(),
            temporal_change_900_to_1000_pp=(100*saved['equal_temporal_change'][j,:,0]).tolist(),temporal_harm_tie_gain=saved['temporal_counts'][j,:,0].tolist(),
            original_recipient_percent=float(100*saved['equal_original_levels'][j,0]))
    findings=dict(classification=primary['status'],primary=primary,confirmatory=True,blocks=BLOCKS,arms=ARMS,times=TIMES,signs=SIGNS,
        population='Fresh source recipe, residual packet family and own-body source; not other families or body substitutions.',
        primary_selected_from_TT045_development=True,population_units=32,source_positions=512,injury_cases_per_damage_panel=2048,
        actual_fixed_states=dict(continuing=1,fresh=4),new_futures_per_fixed_state=8,independent_block_future_banks=256,
        source_population_was_new=True,production_outcomes_now_exposed=True,full_state_future_crossing=True,
        mc_se_scope='Conditional on fixed source/states; population inference uses 32 block estimates, not futures or masks.',
        fixed_state_estimates_coarse=True,all_cases_and_paired_harms_retained=True,original_comparator='Intact preservation under the same new births/futures',
        reservation_scope=read(ROOT/'RESERVATION_REVIEW.json')['limitations'],panels=panels)
    write(ROOT/'FINDINGS.json',findings)
    closeout=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,complete_sha256=sha(run/'COMPLETE.json'),
        findings_sha256=sha(ROOT/'FINDINGS.json'),review_code_sha256=sha(__file__),confirmation_sha256=sha(run/'CONFIRMATION.json'),
        output_files_verified=len(complete['outputs']),condition_blocks_checked=len(BLOCKS)*len(CONDITIONS),
        populated_condition_blocks_independently_reduced=reduced,case_packet_state_future_endpoint_vectors_checked=endpoints,
        continuous_margin_entries_checked=endpoints*6*4,original_control_endpoint_vectors_checked=original_endpoints,
        local_estimate_entries_independently_checked=local_entries,source_saved_arrays_verified=source_arrays,writer_score_checkpoints_verified=writer_scores,
        all_summary_arrays_independently_reduced=True,paired_harms_and_timing_joints_verified=True,report_reproduced=True,
        primary_independently_verified=primary['status'],primary_critical_value_independently_inverted=True,primary_variance_independently_paired=True,
        actual_state_denominators_verified=True,squared_weight_conditional_mc_se_verified=True,source_writer_birth_packet_custody_verified=True,
        physical_replay='Every source, writer and receiving trajectory independently replayed during production; no dynamics rerun at closeout.',
        physical_verification=complete['verification'],qualification_serial_parallel_passed=read(ROOT/'runs/qualification_v1/COMPLETE.json')['serial_parallel_bitwise_equal'],
        production_serial_parallel_not_repeated=True,study_bytes_at_review=size(),free_bytes_at_review=shutil.disk_usage(ROOT).free)
    space();write(ROOT/'CLOSEOUT.json',closeout);signal.alarm(0);print(json.dumps(closeout),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException as error:
        write(ROOT/'COMPLETION_REVIEW_V2_FAILED.json',dict(status='FAILED',recorded_utc=now(),error=repr(error),traceback=traceback.format_exc()))
        raise

