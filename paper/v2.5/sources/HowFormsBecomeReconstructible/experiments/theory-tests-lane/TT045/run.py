"""Every fixed starting state crossed with every new paired future."""
from common import *
from sources import Source, configurations, identity
import analysis,audit,kernel,storage,time

def observe(ctx, raw):
    result = {}
    for t in TIMES:
        obs = reader.measure(ctx, raw[f's{t}_V'], ctx['readout'])[1]
        ref.scores(ctx['codes'], dict(obs, s1000_V=raw[f's{t}_V']), ctx['readout'])
        result.update({f's{t}_{k}': v for k, v in obs.items()})
    return result


def endpoints(body, world, mask):
    probabilities, margins = [], []
    for t in TIMES:
        probabilities.append(credit(body[f's{t}_probabilities'], world, mask))
        scores = body[f's{t}_scores'][world]
        margins.append([scores[k]-max(scores[j] for j in range(4) if j != k) for k in labels(world, mask)])
    return np.asarray(probabilities), np.asarray(margins)


def paired(branches, role):
    streams = {}
    for profile in PROFILES:
        assert len(branches[profile]) == initial_count(profile, role)
        for birth, by_future in enumerate(branches[profile]):
            assert len(by_future) == futures(role)
            for future, pair in enumerate(by_future):
                for packet, v in enumerate(pair):
                    m = v['metadata']; signature = (m['rng_start'], m['rng_final'], encoded({str(k):x for k,x in m['checkpoint_rng'].items()}))
                    if future in streams: assert streams[future] == signature, 'same future across all states and packets'
                    else: streams[future] = signature
                    assert m['profile'] == 'fresh' and m['feedback'] is False and m['c_m'] == 0
                    for k in KEYS: exact(v['initial'][k], by_future[0][packet]['initial'][k], 'restore same initial bytes for every future')
                    exact(v['initial']['theta'], branches['continuing'][0][0][packet]['initial']['theta'], 'same actual packet across states')
                for k in BODY_KEYS: exact(pair[0]['initial'][k], pair[1]['initial'][k], 'paired initial body')
    assert len(streams) == len({v[0] for v in streams.values()}) == futures(role)


def block(directory, index, role):
    assert index in selected(role)
    if role == 'development':
        frozen = read(ROOT/'FREEZE.json'); assert not frozen['new_production_outcomes_generated'] and frozen['blocks'] == list(BLOCKS)
    tick = time.monotonic(); directory = Path(directory); directory.mkdir(parents=True, exist_ok=False); (directory/'physical').mkdir()
    ctx = context(index); source = Source(index, role); nf = futures(role)
    seeds = read(ROOT/'SEEDS.json')['addresses'][role][str(index)]
    assert seeds == [future_address(role, index, k) for k in range(nf)]
    expected = read(ROOT/'LAYOUT.json')['groups'][role]['blocks'][str(index)]
    write(directory/'CONFIG.json', dict(study='TT045', block=index, role=role, profiles=PROFILES, arms=ARMS, times=TIMES,
        config=asdict(ctx['config']), readout=asdict(ctx['readout']), feedback_gain=0., rho=.002,
        actual_starting_states={p:initial_count(p, role) for p in PROFILES}, new_futures_per_fixed_state=nf,
        forcing_addresses=seeds, source_population_exposed=True, population_confirmation=False,
        storage='V/ema/R at all checkpoints, held theta once; lossless expansion to 24 raw arrays'))
    physical = {}; starts = {}; logical = []; cases = []
    data = {name:[] for name in (*PROFILES, *(p+'_margin' for p in PROFILES), 'original')}
    aliases = logical_count = 0; owners = dict.fromkeys(PROFILES, 0); by_profile = dict.fromkeys(PROFILES, 0)
    physical_seconds = 0.; physical_bytes = 0

    def continued(profile, addr, initial):
        nonlocal aliases, physical_seconds, physical_bytes
        h = identity(addr, initial); blob = state_bytes(initial); ih = digest(blob)
        if ih in starts: assert starts[ih] == blob
        else: starts[ih] = blob
        if h in physical:
            aliases += 1; value = physical[h]; assert value['initial_identity'] == ih
            return dict(name=value['name'], body=arrays(directory/(value['name']+'_body.npz')),
                        metadata=read(directory/(value['name']+'.json'))['metadata'], initial=initial)
        assert len(physical) < expected['physical']; batch_space(); start = time.monotonic()
        name = f'physical/continuation_{len(physical):05d}'
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, 'fresh', addr, False)
        body = observe(ctx, raw); proof = audit.replay(ctx, initial, 'fresh', addr, False, raw, meta, body)
        assert proof == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
        p = directory/(name+'.npz'); bp = directory/(name+'_body.npz'); storage.save_raw(p, raw); save(bp, body)
        write(p.with_suffix('.json'), dict(physical_identity=h, metadata=meta, proof=proof,
            files=dict(state=sha(p), body=sha(bp)), arrays=dict(expanded_state=identities(raw), packed_state=identities(storage.pack(raw)), body=identities(body)),
            stored_state_arrays=19, expanded_state_arrays=24, storage_lossless=True))
        retained = sum(x.stat().st_size for x in (p, bp, p.with_suffix('.json'))); assert retained <= BATCH_BYTES
        physical_bytes += retained; assert physical_bytes <= expected['physical']*BATCH_BYTES
        physical[h] = dict(name=name, initial_identity=ih); owners[profile] += 1; physical_seconds += time.monotonic()-start
        return dict(name=name, body=body, metadata=meta, initial=initial)

    for a in source.links.values():
        branches = {p:[[[None]*2 for _ in range(nf)] for _ in range(initial_count(p, role))] for p in PROFILES}
        for profile, birth, future, packet, addr, initial in configurations(source, a):
            branches[profile][birth][future][packet] = continued(profile, addr, initial)
            logical_count += 1; by_profile[profile] += 1
        paired(branches, role)
        logical.append(dict(damage=a['damage'], family=a['family'], mask=a['mask'], body_source=a['body_source'],
            profiles={p:[[[v['name'] for v in pair] for pair in by_future] for by_future in branches[p]] for p in PROFILES}))
        mi = MASKS.index(a['mask'])
        for w in range(16):
            old_index = source.lookup[(*key(a), w)]; old = source.cases[old_index]
            assert old['block'] == index and old['message'] == w//4 and old['replicate'] == w%4
            assert old['geometry'] == GEOMETRIES[geometry(mi, w)]; cases.append(dict(old))
            for profile in PROFILES:
                scores = []; margins = []
                for packet in (0, 1):
                    by_birth = [[endpoints(pair[packet]['body'], w, mi) for pair in by_future] for by_future in branches[profile]]
                    scores.append([[v[0] for v in one] for one in by_birth]); margins.append([[v[1] for v in one] for one in by_birth])
                data[profile].append(scores); data[profile+'_margin'].append(margins)
            data['original'].append(source.original[old_index])
    values = {k:np.asarray(v, dtype=np.float64) if k.endswith('_margin') else
              np.asarray(v, dtype=np.int16) if k == 'original' else analysis.units(v) for k,v in data.items()}
    assert len(physical) == expected['physical'] and logical_count == expected['logical']
    assert owners == expected['physical_owners'] and by_profile == expected['logical_by_profile']
    assert len(starts) == expected['distinct_initial_states_and_packets']
    assert digest(encoded(sorted(physical))) == expected['unique_starting_identity_sha256']
    assert len(cases) == 1152 and len(logical) == 72 and len(physical)+aliases == logical_count
    write(directory/'ALIASES.json', logical); write(directory/'CASES.json', cases); save(directory/'ENDPOINTS.npz', values)
    # Historical endpoints retain their original ordering, with their own case table.
    save(directory/'HISTORICAL_TT044.npz', source.historical); write(directory/'HISTORICAL_CASES.json', source.cases)
    start = time.monotonic(); local = analysis.local(values); save(directory/'LOCAL.npz', local)
    agg = analysis.block(cases, values); save(directory/'AGGREGATE.npz', agg)
    saved_values = arrays(directory/'ENDPOINTS.npz'); again = analysis.block(read(directory/'CASES.json'), saved_values)
    for k in agg: exact(agg[k], again[k], 'saved aggregation '+k)
    local_again = analysis.local(saved_values)
    for k in local: exact(local[k], local_again[k], 'saved local estimate '+k)
    analysis_seconds = time.monotonic()-start; verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    proof = dict(labelled_cases=len(cases), logical_continuations=logical_count, physical_continuations=len(physical),
        continuation_aliases=aliases, simulated_world_continuations=16*len(physical),
        continuing_physical=owners['continuing'], fresh_physical=owners['fresh'],
        independent_native_arrays=24*len(physical), body_scores_checked=6*len(physical),
        losslessly_stored_physical_packages=len(physical), inherited_original_rows=len(cases)*births(role),
        independent_block_future_banks=nf, max_native_error=0.)
    write(directory/'CHECK.json', dict(status='PASS', verification=proof, all_cases_retained=True,
        full_independent_replay=True, actual_starting_states={p:initial_count(p, role) for p in PROFILES},
        new_futures_per_fixed_state=nf, expanded_state_arrays_per_package=24, stored_state_arrays_per_package=19,
        physical_package_bytes=physical_bytes, physical_package_bound_bytes=expected['physical']*BATCH_BYTES))
    outputs = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    receipt = dict(status='PASS', block=index, seconds=time.monotonic()-tick, physical_seconds=physical_seconds,
        analysis_seconds=analysis_seconds, verification=proof, outputs=outputs,
        retained_bytes=sum(Path(p).stat().st_size for p in outputs))
    write(directory/'COMPLETE.json', receipt); space(); return receipt

