"""All saved versions in matched new receivers, with exact native replay."""
from dataclasses import asdict
import time
from common import *
import audit
import design
import kernel

def baseline(role, index, history, family):
    name = 'development' if role == 'development' else 'excluded'
    entry = read_json(ROOT/'BASELINE_MANIFEST.json')['rows'][f'{name}:{index}:{history}:{family}']
    for path, expected in entry['files'].items(): assert sha(ROOT/path) == expected
    base = ROOT/entry['directory']; packets = arrays(base/'packets.npz')
    meta = read_json(base/'PROVENANCE.json'); histories = read_json(base/'HISTORY.json')
    cycles = design.schedule(role)[2]
    assert set(packets) == set(design.versions(cycles)) and identities(packets) == meta['arrays']
    assert set(histories) == set(design.ARMS)
    for arm in design.ARMS:
        for g, route in enumerate(meta['routes'][arm], 1):
            assert route == dict(generation=g, incoming=design.alias(arm, g-1), outgoing=design.alias(arm, g),
                input_sha256=digest(packets[design.alias(arm, g-1)].tobytes()),
                outgoing_sha256=digest(packets[design.alias(arm, g)].tobytes()))
    return packets, histories

def rows(index, history, draw, family, packets, histories, measured, cycles):
    assert set(measured) == set(design.versions(cycles))
    result = []
    for arm in design.ARMS:
        for world in range(16):
            previous = float(measured['initial']['correctness'][world, 0]); initial = previous
            total = 0.
            for g in range(1, cycles+1):
                before = design.alias(arm, g-1); after = design.alias(arm, g)
                x = float(measured[before]['correctness'][world, 0]); y = float(measured[after]['correctness'][world, 0])
                assert x == previous; difference = y-x; total += difference
                assert abs(total-(y-initial)) <= 2e-15
                if arm == 'zero_off': assert before == after == 'initial' and difference == 0.
                h = histories[arm][world]
                result.append(dict(block=index, history=history, draw=draw, family=family, arm=arm, cycle=g,
                    world=world, message=world//4, replicate=world % 4,
                    incoming_version=before, outgoing_version=after, initial=initial, incoming=x, outgoing=y,
                    effect=difference, cumulative_effect=y-initial,
                    incoming_margin=float(measured[before]['margins'][world, 0]),
                    outgoing_margin=float(measured[after]['margins'][world, 0]),
                    developed_score=h['development'][g-1], repaired_score=h['repaired'][g-1],
                    injury_stratum=h['injury_strata'][g-1], historical_terminal=h['terminal'],
                    historical_uninterrupted_development=h['uninterrupted_development'],
                    historical_uninterrupted_repaired=h['uninterrupted_repaired']))
                previous = y
    return result

def block(directory, index, role):
    directory.mkdir(parents=True, exist_ok=False); tick = time.monotonic()
    cfg, rcfg = design.configs(role); histories_n, draws_n, cycles = design.schedule(role)
    ctx = model.source.context(index, cfg)
    write_json(directory/'CONFIG.json', dict(role=role, block=index, config=asdict(cfg), readout=asdict(rcfg),
        schedule=dict(histories=histories_n, draws=draws_n, cycles=cycles), arms=design.ARMS, families=design.FAMILIES))
    records = []; environments = {}; batches = 0; compared = 0
    for history in range(histories_n):
        sources = {family: baseline(role, index, history, family) for family in design.FAMILIES}
        for draw in range(draws_n):
            environment = None
            key = design.address(role, index, history, draw)
            assert key == audit.address(role, index, history, draw)
            for family in design.FAMILIES:
                packets, old = sources[family]; measured = {}
                target = directory/f'future_{history:02d}'/f'draw_{draw:02d}'/family
                target.mkdir(parents=True, exist_ok=False)
                for version in design.versions(cycles):
                    packet = packets[version].tobytes()
                    raw, metadata = kernel.read(ctx, packet, key, rcfg)
                    proof = audit.read(ctx, packet, rcfg, role, index, history, draw, raw, metadata, True)
                    env = audit.paired(raw, metadata)
                    if environment is None: environment = env
                    else: assert env == environment, 'paired receiving environment'
                    write_arrays(target/(version+'.npz'), raw)
                    write_json(target/(version+'.json'), dict(role=role, block=index, history=history, draw=draw,
                        family=family, version=version, address=key, metadata=metadata, proof=proof,
                        arrays=identities(raw), sha256=sha(target/(version+'.npz')), environment=env))
                    measured[version] = {k: raw[k] for k in ('correctness', 'margins')}
                    batches += 1; compared += proof['native_arrays']
                records.extend(rows(index, history, draw, family, packets, old, measured, cycles))
            assert environment['birth_sha256'] not in {x['birth_sha256'] for x in environments.values()}
            environments[f'{history}:{draw}'] = environment
    write_json(directory/'ROWS.json', records)
    proof = design.expected(role, 1)
    assert (batches, compared, len(records)) == (proof['native_batches'], proof['native_arrays'], proof['paired_rows'])
    write_json(directory/'CHECK.json', dict(proof, status='PASS', seconds=time.monotonic()-tick, environments=environments))
    checked = saved(directory)
    write_json(directory/'SAVED_CHECK.json', checked)
    return proof

def saved(directory):
    config = read_json(directory/'CONFIG.json'); role, index = config['role'], config['block']
    cfg, rcfg = design.configs(role); histories_n, draws_n, cycles = design.schedule(role)
    assert config == json.loads(serialized(dict(role=role, block=index, config=asdict(cfg), readout=asdict(rcfg),
        schedule=dict(histories=histories_n, draws=draws_n, cycles=cycles), arms=design.ARMS, families=design.FAMILIES)))
    ctx = model.source.context(index, cfg); records = []; environments = {}; count = 0
    for history in range(histories_n):
        for draw in range(draws_n):
            environment = None
            for family in design.FAMILIES:
                packets, old = baseline(role, index, history, family); measured = {}
                target = directory/f'future_{history:02d}'/f'draw_{draw:02d}'/family
                assert {p.name for p in target.iterdir()} == {v+s for v in design.versions(cycles) for s in ('.json', '.npz')}
                for version in design.versions(cycles):
                    path = target/(version+'.npz'); raw = arrays(path); meta = read_json(target/(version+'.json'))
                    assert sha(path) == meta['sha256'] and identities(raw) == meta['arrays']
                    for k, value in dict(role=role, block=index, history=history, draw=draw, family=family, version=version).items(): assert meta[k] == value
                    assert meta['address'] == audit.address(role, index, history, draw)
                    assert meta['proof']['native_arrays'] == 12 and meta['proof']['max_native_error'] == 0.
                    audit.read(ctx, packets[version].tobytes(), rcfg, role, index, history, draw, raw, meta['metadata'], False)
                    env = audit.paired(raw, meta['metadata']); assert env == meta['environment']
                    if environment is None: environment = env
                    else: assert env == environment
                    measured[version] = {k: raw[k] for k in ('correctness', 'margins')}; count += len(raw)
                records.extend(rows(index, history, draw, family, packets, old, measured, cycles))
            assert environment['birth_sha256'] not in {x['birth_sha256'] for x in environments.values()}
            environments[f'{history}:{draw}'] = environment
    assert records == read_json(directory/'ROWS.json')
    proof = read_json(directory/'CHECK.json'); assert proof['status'] == 'PASS' and proof['environments'] == environments
    expected = design.expected(role, 1)
    for k, v in expected.items(): assert proof[k] == v
    assert count == expected['saved_arrays']
    return dict(status='PASS', arrays=count, paired_rows=len(records), distinct_environments=len(environments), new_dynamics=0)
