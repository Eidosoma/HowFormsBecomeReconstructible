"""All paired receiving conditions, with independent replay of every trajectory."""
from common import *
from sources import Source, configurations, identity
import analysis, audit, kernel, time


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


def block(directory, index, role):
    assert index in selected(role)
    if role == 'development':
        frozen = read(ROOT/'FREEZE.json'); assert not frozen['new_production_outcomes_generated'] and frozen['blocks'] == list(BLOCKS)
    tick = time.monotonic(); directory = Path(directory); directory.mkdir(parents=True, exist_ok=False); (directory/'physical').mkdir()
    ctx = context(index); source = Source(index, role)
    write(directory/'CONFIG.json', dict(study='TT043', block=index, role=role, profiles=PROFILES, arms=ARMS, times=TIMES,
          config=asdict(ctx['config']), readout=asdict(ctx['readout']), feedback_gains=[0., .2], rho=.002,
          fresh_draws=draws(role), continuing_draws=1, source_population_exposed=True, new_independent_draws=0))
    physical = {}; logical = []; cases = []; data = {name: [] for name in (*PROFILES, *(p+'_margin' for p in PROFILES), 'original')}
    aliases = logical_count = anchors = anchor_scores = 0; profile_counts = dict.fromkeys(PROFILES, 0); fresh_on = 0
    physical_seconds = 0.

    def continued(profile, draw, feedback, addr, initial):
        nonlocal aliases, physical_seconds, fresh_on
        h = identity(profile, draw, feedback, addr, initial); blob = state_bytes(initial)
        if h in physical:
            aliases += 1; value = physical[h]; assert value['initial'] == blob
            return dict(name=value['name'], raw=arrays(directory/(value['name']+'.npz')),
                        body=arrays(directory/(value['name']+'_body.npz')), metadata=read(directory/(value['name']+'.json'))['metadata'])
        space(); start = time.monotonic(); name = f'physical/continuation_{len(physical):04d}'
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, profile, addr, feedback)
        body = observe(ctx, raw); proof = audit.replay(ctx, initial, profile, addr, feedback, raw, meta, body)
        assert proof == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
        p = directory/(name+'.npz'); bp = directory/(name+'_body.npz'); save(p, raw); save(bp, body)
        write(p.with_suffix('.json'), dict(physical_identity=h, metadata=meta, proof=proof,
              files=dict(state=sha(p), body=sha(bp)), arrays=dict(state=identities(raw), body=identities(body))))
        assert sum(x.stat().st_size for x in (p, bp, p.with_suffix('.json'))) <= 1024**2
        physical[h] = dict(name=name, initial=blob); physical_seconds += time.monotonic()-start; profile_counts[profile] += 1
        if profile == 'fresh' and feedback: fresh_on += 1
        return dict(name=name, raw=raw, body=body, metadata=meta)

    for a in source.links.values():
        branches = {p: [[None]*4 for _ in range(1 if p == 'continuing' else draws(role))] for p in PROFILES}
        for profile, draw, feedback, packet, addr, initial in configurations(source, a):
            v = continued(profile, draw, feedback, addr, initial); logical_count += 1
            checks, scores = source.anchors(a, profile, packet, draw, feedback, v['raw'], v['body'], v['metadata'])
            anchors += checks; anchor_scores += scores; branches[profile][draw][2*int(feedback)+packet] = v
        for profile in PROFILES:
            for one in branches[profile]:
                assert len({v['metadata']['rng_start'] for v in one}) == len({v['metadata']['rng_final'] for v in one}) == 1
                for k in BODY_KEYS:
                    for v in one[1:]: exact(one[0]['raw']['s0_'+k], v['raw']['s0_'+k], 'shared starting receiver')
        original = [source.original(a, draw) for draw in range(draws(role))]
        logical.append(dict(damage=a['damage'], family=a['family'], mask=a['mask'], body_source=a['body_source'],
                            source_repairs=[a['repairs'][i] for i in (0, 2)],
                            profiles={p: [[v['name'] for v in one] for one in branches[p]] for p in PROFILES}))
        mi = MASKS.index(a['mask'])
        for w in range(16):
            old = source.bodies[(*key(a), w)]
            assert old['block'] == index and old['message'] == w//4 and old['replicate'] == w%4
            assert old['geometry'] == GEOMETRIES[geometry(mi, w)]
            cases.append({k: v for k, v in old.items() if k not in ('repairs', 'body_by_time')})
            for profile in PROFILES:
                scores, margins = [], []
                for ai in range(4):
                    result = [endpoints(one[ai]['body'], w, mi) for one in branches[profile]]
                    scores.append([v[0] for v in result]); margins.append([v[1] for v in result])
                data[profile].append(scores); data[profile+'_margin'].append(margins)
            orig = np.stack([credit(p, w, mi) for p in original]); data['original'].append(orig)
            for draw in range(draws(role)):
                row = source.rows[((*key(a), w), draw)]
                exact(orig[draw], np.array(row['original']))
                for ai, field in ((0, 'incoming'), (1, 'after_late100')):
                    exact(np.asarray(data['fresh'][-1])[ai, draw, -1], np.array(row[field]), 'original fresh endpoint replay')
    values = {k: np.asarray(v, dtype=np.float64) if k.endswith('_margin') else analysis.units(v) for k, v in data.items()}
    assert values['continuing'].shape == (1152, 4, 1, 6, 4) and values['fresh'].shape == (1152, 4, draws(role), 6, 4)
    expected = read(ROOT/'LAYOUT.json')['groups'][role]['blocks'][str(index)]
    assert len(physical) == expected['physical'] and logical_count == expected['logical'] and profile_counts == expected['profiles']
    assert digest(encoded(sorted(physical))) == expected['unique_starting_identity_sha256']
    assert len(cases) == 1152 and len(logical) == 72 and len(physical)+aliases == logical_count
    write(directory/'ALIASES.json', logical); write(directory/'CASES.json', cases); save(directory/'ENDPOINTS.npz', values)
    start = time.monotonic(); agg = analysis.block(cases, values); save(directory/'AGGREGATE.npz', agg)
    again = analysis.block(read(directory/'CASES.json'), arrays(directory/'ENDPOINTS.npz'))
    for k in agg: exact(agg[k], again[k], 'saved aggregation '+k)
    analysis_seconds = time.monotonic()-start; verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    proof = dict(labelled_cases=len(cases), logical_continuations=logical_count, physical_continuations=len(physical),
                 continuation_aliases=aliases, simulated_world_continuations=16*len(physical),
                 continuing_physical=profile_counts['continuing'], fresh_physical=profile_counts['fresh'], fresh_feedback_on_physical=fresh_on,
                 independent_native_arrays=24*len(physical), body_scores_checked=6*len(physical),
                 saved_anchor_arrays_checked=anchors, saved_anchor_scores_checked=anchor_scores,
                 inherited_original_rows=len(cases)*draws(role), new_independent_future_draws=0, max_native_error=0.)
    write(directory/'CHECK.json', dict(status='PASS', verification=proof, independent_full_physical_replay=True, all_cases_retained=True))
    outputs = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    receipt = dict(status='PASS', block=index, seconds=time.monotonic()-tick, physical_seconds=physical_seconds,
                   analysis_seconds=analysis_seconds, verification=proof, outputs=outputs,
                   retained_bytes=sum(Path(p).stat().st_size for p in outputs))
    write(directory/'COMPLETE.json', receipt); space(); return receipt
