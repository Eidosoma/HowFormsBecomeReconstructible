"""Full physical state-by-forcing crossover with independent equation replay."""
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


def paired(branches):
    def rng(v):
        m = v['metadata']; return m['rng_start'], m['rng_final'], encoded({str(k):x for k,x in m['checkpoint_rng'].items()})
    for cell in CELLS:
        for pair in branches[cell]:
            assert rng(pair[0]) == rng(pair[1])
            for k in BODY_KEYS: exact(pair[0]['raw']['s0_'+k], pair[1]['raw']['s0_'+k], 'packet pair initial receiver')
            for packet, v in enumerate(pair): exact(v['raw']['s0_theta'], branches['CC'][0][packet]['raw']['s0_theta'])
    for draw in range(len(branches['FF'])):
        for packet in (0, 1):
            cc, cf, fc, ff = [branches[c][0 if c == 'CC' else draw][packet] for c in CELLS]
            for k in BODY_KEYS:
                exact(cc['raw']['s0_'+k], cf['raw']['s0_'+k], 'C initial held across forcing')
                exact(fc['raw']['s0_'+k], ff['raw']['s0_'+k], 'F initial held across forcing')
            assert rng(cc) == rng(fc) and rng(cf) == rng(ff), 'forcing held across initial states'


def block(directory, index, role):
    assert index in selected(role)
    if role == 'development':
        frozen = read(ROOT/'FREEZE.json'); assert not frozen['new_production_outcomes_generated'] and frozen['blocks'] == list(BLOCKS)
    tick = time.monotonic(); directory = Path(directory); directory.mkdir(parents=True, exist_ok=False); (directory/'physical').mkdir()
    ctx = context(index); source = Source(index, role)
    write(directory/'CONFIG.json', dict(study='TT044', block=index, role=role, cells=CELLS, cell_factors=CELL_FACTORS, arms=ARMS, times=TIMES,
          config=asdict(ctx['config']), readout=asdict(ctx['readout']), feedback_gain=0., rho=.002,
          actual_indices={c:cell_draws(c, role) for c in CELLS}, paired_index=True,
          source_population_exposed=True, new_independent_draws=0))
    physical = {}; logical = []; cases = []; data = {name: [] for name in (*CELLS, *(c+'_margin' for c in CELLS), 'original')}
    aliases = logical_count = anchors = anchor_scores = 0
    owners = dict.fromkeys(CELLS, 0); cell_logical = dict.fromkeys(CELLS, 0); physical_seconds = 0.

    def continued(cell, force, addr, initial):
        nonlocal aliases, physical_seconds
        h = identity(force, addr, initial); blob = state_bytes(initial)
        if h in physical:
            aliases += 1; value = physical[h]; assert value['initial'] == blob
            return dict(name=value['name'], raw=arrays(directory/(value['name']+'.npz')),
                        body=arrays(directory/(value['name']+'_body.npz')), metadata=read(directory/(value['name']+'.json'))['metadata'])
        space(); start = time.monotonic(); name = f'physical/continuation_{len(physical):04d}'
        raw, meta = kernel.resume(model.boundary.runtime_context(ctx), initial, force, addr, False)
        assert meta['feedback'] is False and meta['c_m'] == 0 and meta['rho'] == .002
        body = observe(ctx, raw); proof = audit.replay(ctx, initial, force, addr, False, raw, meta, body)
        assert proof == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
        p = directory/(name+'.npz'); bp = directory/(name+'_body.npz'); save(p, raw); save(bp, body)
        write(p.with_suffix('.json'), dict(physical_identity=h, metadata=meta, proof=proof,
              files=dict(state=sha(p), body=sha(bp)), arrays=dict(state=identities(raw), body=identities(body))))
        assert sum(x.stat().st_size for x in (p, bp, p.with_suffix('.json'))) <= 1024**2
        physical[h] = dict(name=name, initial=blob); physical_seconds += time.monotonic()-start; owners[cell] += 1
        return dict(name=name, raw=raw, body=body, metadata=meta)

    for a in source.links.values():
        branches = {c: [[None]*2 for _ in range(cell_draws(c, role))] for c in CELLS}
        for cell, draw, packet, force, addr, initial in configurations(source, a):
            v = continued(cell, force, addr, initial); logical_count += 1; cell_logical[cell] += 1
            checks, scores = source.anchors(a, cell, packet, draw, v['raw'], v['body'], v['metadata'])
            anchors += checks; anchor_scores += scores; branches[cell][draw][packet] = v
        paired(branches)
        logical.append(dict(damage=a['damage'], family=a['family'], mask=a['mask'], body_source=a['body_source'],
                            cells={c: [[v['name'] for v in one] for one in branches[c]] for c in CELLS}))
        mi = MASKS.index(a['mask'])
        for w in range(16):
            old_index = source.lookup[(*key(a), w)]; old = source.cases[old_index]
            assert old['block'] == index and old['message'] == w//4 and old['replicate'] == w%4
            assert old['geometry'] == GEOMETRIES[geometry(mi, w)]; cases.append(dict(old))
            for cell in CELLS:
                scores, margins = [], []
                for packet in (0, 1):
                    result = [endpoints(one[packet]['body'], w, mi) for one in branches[cell]]
                    scores.append([v[0] for v in result]); margins.append([v[1] for v in result])
                data[cell].append(scores); data[cell+'_margin'].append(margins)
            data['original'].append(source.original[old_index])
    values = {k: np.asarray(v, dtype=np.float64) if k.endswith('_margin') else
              np.asarray(v, dtype=np.int16) if k == 'original' else analysis.units(v) for k, v in data.items()}
    expected = read(ROOT/'LAYOUT.json')['groups'][role]['blocks'][str(index)]
    assert len(physical) == expected['physical'] and logical_count == expected['logical']
    assert owners == expected['physical_owners'] and cell_logical == expected['logical_by_cell']
    assert digest(encoded(sorted(physical))) == expected['unique_starting_identity_sha256']
    assert len(cases) == 1152 and len(logical) == 72 and len(physical)+aliases == logical_count
    write(directory/'ALIASES.json', logical); write(directory/'CASES.json', cases); save(directory/'ENDPOINTS.npz', values)
    start = time.monotonic(); agg = analysis.block(cases, values); save(directory/'AGGREGATE.npz', agg)
    again = analysis.block(read(directory/'CASES.json'), arrays(directory/'ENDPOINTS.npz'))
    for k in agg: exact(agg[k], again[k], 'saved aggregation '+k)
    analysis_seconds = time.monotonic()-start; verify(source.c.used); write(directory/'USED_INPUTS.json', source.c.used)
    proof = dict(labelled_cases=len(cases), logical_continuations=logical_count, physical_continuations=len(physical),
                 continuation_aliases=aliases, simulated_world_continuations=16*len(physical),
                 **{c+'_physical':owners[c] for c in CELLS},
                 independent_native_arrays=24*len(physical), body_scores_checked=6*len(physical),
                 saved_anchor_arrays_checked=anchors, saved_anchor_scores_checked=anchor_scores,
                 inherited_original_rows=len(cases)*draws(role), new_independent_future_draws=0, max_native_error=0.)
    write(directory/'CHECK.json', dict(status='PASS', verification=proof, independent_full_physical_replay=True, all_cases_retained=True))
    outputs = {str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    receipt = dict(status='PASS', block=index, seconds=time.monotonic()-tick, physical_seconds=physical_seconds,
                   analysis_seconds=analysis_seconds, verification=proof, outputs=outputs,
                   retained_bytes=sum(Path(p).stat().st_size for p in outputs))
    write(directory/'COMPLETE.json', receipt); space(); return receipt
