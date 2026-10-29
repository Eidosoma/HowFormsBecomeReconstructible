"""Exact joins and descriptive contrasts of retained receiving/body observations."""
from collections import defaultdict
import io
import itertools
import math
import time
import numpy as np
from common import *

KEYS = ('corruption', 'family', 'damage', 'body_source', 'arm', 'world')
RVALUES = ('original', 'incoming', 'outgoing', 'original_donor', 'incoming_donor', 'outgoing_donor')
RECIPIENT_METRICS = {
    'extra_writing': ('recipient', 3, 2),
    'short_vs_preservation': ('recipient', 2, 1),
    'full_vs_preservation': ('recipient', 3, 1),
    'short_vs_original': ('recipient', 2, 0),
    'full_vs_original': ('recipient', 3, 0),
    'realized_damage': ('recipient', 1, 0),
    'extra_donor_credit': ('donor', 2, 1),
}
BODY_METRICS = {
    'extra_writing': ('body', 2, 1),
    'short_vs_preservation': ('body', 1, 0),
    'full_vs_preservation': ('body', 2, 0),
}


def key(row, **changes):
    return tuple(changes.get(k, row[k]) for k in KEYS)


def validate_source(rows, bodies, config):
    expected = {(c, f, d, b, a, w) for c in range(config['corruptions'])
        for f in config['families'] for d in config['damage'] for b in BODIES for a in arms(b) for w in range(16)}
    body_map = {key(v): v for v in bodies}
    row_map = {key(v)+(v['draw'],): v for v in rows}
    assert len(body_map) == len(bodies) == len(expected) and set(body_map) == expected
    assert len(row_map) == len(rows) == len(expected)*config['draws']
    assert set(row_map) == {k+(d,) for k in expected for d in range(config['draws'])}
    histories = {}
    for b in bodies:
        assert b['block'] == config['block'] and b['message'] == b['world']//4 and b['replicate'] == b['world']%4
        assert b['injury_stratum'] in STRATA and b['eta'] == {'mix000':0., 'mix050':.5, 'mix100':1.}[b['damage']]
        assert b['budget'] == int(b['arm'].rsplit('_', 1)[1])
        assert b['donor_world'] == ((b['message']+2)%4)*4+b['replicate']
        for name in ('developed_score', 'repaired_score', 'repaired_donor_score', 'preserve_body', 'full_budget_body'):
            units(b[name])
        assert b['preserve_body'] == body_map[key(b, arm=SELECTED[0])]['repaired_score']
        assert b['full_budget_body'] == body_map[key(b, arm=SELECTED[2])]['repaired_score']
        k = (b['family'], b['world']); v = (b['developed_score'], b['injury_stratum'])
        assert histories.setdefault(k, v) == v
    for b in bodies:
        world = b['donor_world'] if b['body_source'] == 'foreign' else b['world']
        assert b['source_developed_score'] == (None if b['body_source'] == 'neutral' else histories[b['family'], world][0])
    incoming = {}; original = {}
    for r in rows:
        assert all(r[k] == v for k,v in body_map[key(r)].items())
        for name in RVALUES: units(r[name])
        assert r['effect'] == r['outgoing']-r['incoming']
        assert math.isfinite(r['incoming_margin']) and math.isfinite(r['outgoing_margin'])
        version = ('original' if r['damage'] == 'mix000' else r['damage']+'_incoming') if r['arm'] == SELECTED[0] else f'{r["damage"]}_{r["body_source"]}_{r["arm"]}'
        assert r['packet_version'] == version
        for body in BODIES:
            expected_score = row_map[key(r, body_source=body)+(r['draw'],)]['outgoing'] if r['arm'] in arms(body) else None
            assert r[body+'_outgoing'] == expected_score
        assert r['full_budget_outgoing'] == row_map[key(r, arm=SELECTED[2])+(r['draw'],)]['outgoing']
        k = (r['corruption'], r['family'], r['world'], r['draw'])
        v = tuple(r[x] for x in ('original', 'original_donor'))
        assert original.setdefault(k, v) == v
        k += (r['damage'],); v = tuple(r[x] for x in ('incoming', 'incoming_donor', 'incoming_margin'))
        assert incoming.setdefault(k, v) == v
        if r['arm'] == SELECTED[0]:
            assert r['outgoing'] == r['incoming'] and r['outgoing_donor'] == r['incoming_donor']
        if r['damage'] == 'mix000':
            assert r['incoming'] == r['original'] and r['incoming_donor'] == r['original_donor']
    return row_map


def pair_rows(row_map):
    pairs = []
    for k,r in sorted(row_map.items()):
        if r['body_source'] != 'own' or r['arm'] != SELECTED[0]: continue
        short = row_map[key(r, arm=SELECTED[1])+(r['draw'],)]
        full = row_map[key(r, arm=SELECTED[2])+(r['draw'],)]
        pairs.append(dict(block=r['block'], corruption=r['corruption'], family=r['family'], damage=r['damage'],
            world=r['world'], message=r['message'], draw=r['draw'],
            history='unique_pass' if r['developed_score'] == 1 else 'not_unique_pass',
            developed_units=units(r['developed_score']), injury=r['injury_stratum'],
            n_draws=1, body_repeats=1,
            recipient=[units(r['original']), units(r['incoming']), units(short['outgoing']), units(full['outgoing'])],
            donor=[units(r['incoming_donor']), units(short['outgoing_donor']), units(full['outgoing_donor'])],
            body=[units(r['repaired_score']), units(short['repaired_score']), units(full['repaired_score'])]))
    return pairs


def fold(rows, record=False):
    groups = defaultdict(list)
    fields = ('family', 'damage', 'world') if record else ('corruption', 'family', 'damage', 'world')
    for row in rows: groups[tuple(row[k] for k in fields)].append(row)
    result = []
    for _, values in sorted(groups.items()):
        first = values[0]
        for row in values:
            assert all(row[k] == first[k] for k in ('block', 'family', 'damage', 'world', 'message', 'history', 'injury', 'developed_units'))
        v = {k:first[k] for k in ('block', 'family', 'damage', 'world', 'message', 'history', 'injury', 'developed_units')}
        if not record: v['corruption'] = first['corruption']
        v['n_draws'] = sum(r['n_draws'] for r in values)
        for field in ('recipient', 'donor'):
            v[field] = [sum(r[field][i] for r in values) for i in range(len(first[field]))]
        if record:
            v['body'] = [sum(r['body'][i] for r in values) for i in range(3)]
            v['body_repeats'] = sum(r['body_repeats'] for r in values)
        else:
            assert len({r['draw'] for r in values}) == len(values)
            assert all(r['body'] == first['body'] and r['body_repeats'] == 1 for r in values)
            v['body'] = first['body']; v['body_repeats'] = 1
            v['receiving_draw_changes'] = {s:sum(sign(r['recipient'][3]-r['recipient'][2]) == s for r in values) for s in SIGNS}
            mean = (v['recipient'][3]-v['recipient'][2])/(12*v['n_draws'])
            radius = math.sqrt(2*math.log(40)/v['n_draws'])
            v['pointwise_conditional_change_interval_95'] = [max(-1., mean-radius), min(1., mean+radius)]
        assert v['recipient'][3]-v['recipient'][1] == (v['recipient'][2]-v['recipient'][1])+(v['recipient'][3]-v['recipient'][2])
        result.append(v)
    return result


def empty(n_draws, body_repeats, with_body):
    return dict(n=0, n_draws=n_draws, body_repeats=body_repeats,
        recipient=[0]*4, donor=[0]*3, body=[0]*3 if with_body else None,
        changes={k:{s:0 for s in SIGNS} for k in RECIPIENT_METRICS},
        body_changes={k:{s:0 for s in SIGNS} for k in BODY_METRICS} if with_body else None,
        preservation_transition={a+'|'+b:0 for a in SIGNS for b in SIGNS},
        recipient_body_joint={a+'|'+b:0 for a in SIGNS for b in SIGNS} if with_body else None,
        blocks={})


def add_observation(target, row, with_body):
    assert target['n_draws'] == row['n_draws'] and target['body_repeats'] == row['body_repeats']
    target['n'] += 1
    block = target['blocks'].setdefault(str(row['block']), dict(n=0, recipient=[0]*4, donor=[0]*3, body=[0]*3 if with_body else None))
    block['n'] += 1
    for field in ('recipient', 'donor')+ (('body',) if with_body else ()):
        for i,v in enumerate(row[field]): target[field][i] += v; block[field][i] += v
    for name,(field,after,before) in RECIPIENT_METRICS.items():
        target['changes'][name][sign(row[field][after]-row[field][before])] += 1
    r = row['recipient']; b = row['body']
    target['preservation_transition'][sign(r[2]-r[1])+'|'+sign(r[3]-r[1])] += 1
    if with_body:
        for name,(field,after,before) in BODY_METRICS.items():
            target['body_changes'][name][sign(row[field][after]-row[field][before])] += 1
        target['recipient_body_joint'][sign(r[3]-r[2])+'|'+sign(b[2]-b[1])] += 1


def aggregate(levels):
    result = {}
    for level,rows in zip(LEVELS, levels):
        body = level != LEVELS[0]
        for row in rows:
            cell = row['family']+'|'+row['damage']
            groups = result.setdefault(cell, {}).setdefault(level, {})
            for group in grouping(row):
                target = groups.setdefault(group, empty(row['n_draws'], row['body_repeats'], body))
                add_observation(target, row, body)
    return result


def merge(target, source):
    for cell,levels in source.items():
        for level,groups in levels.items():
            for group,value in groups.items():
                dest = target.setdefault(cell, {}).setdefault(level, {}).setdefault(group,
                    empty(value['n_draws'], value['body_repeats'], value['body'] is not None))
                assert (dest['n_draws'], dest['body_repeats']) == (value['n_draws'], value['body_repeats'])
                assert not set(dest['blocks']) & set(value['blocks'])
                dest['n'] += value['n']; dest['blocks'].update(value['blocks'])
                for field in ('recipient', 'donor', 'body'):
                    if value[field] is not None:
                        for i,v in enumerate(value[field]): dest[field][i] += v
                for field in ('changes', 'body_changes'):
                    if value[field] is not None:
                        for metric,v in value[field].items():
                            for s,n in v.items(): dest[field][metric][s] += n
                for field in ('preservation_transition', 'recipient_body_joint'):
                    if value[field] is not None:
                        for k,n in value[field].items(): dest[field][k] += n


def finish_group(value):
    n = value['n']; draws = value['n_draws']; body_repeats = value['body_repeats']
    result = dict(n=n, receiving_draws_per_observation=draws, body_observations_per_mean=body_repeats if value['body'] is not None else None,
        contributing_blocks=len(value['blocks']), recipient_levels=[x/(12*n*draws) for x in value['recipient']],
        donor_levels=[x/(12*n*draws) for x in value['donor']],
        body_levels=[x/(12*n*body_repeats) for x in value['body']] if value['body'] is not None else None,
        preservation_transition=value['preservation_transition'], recipient_body_joint=value['recipient_body_joint'])
    for field, metrics, change_field in (('recipient_effects', RECIPIENT_METRICS, 'changes'), ('body_effects', BODY_METRICS, 'body_changes')):
        if value[change_field] is None:
            result[field] = None; continue
        result[field] = {}
        for name,(data,after,before) in metrics.items():
            count = body_repeats if data == 'body' else draws
            pooled = (value[data][after]-value[data][before])/(12*n*count)
            blocks = {i:(v[data][after]-v[data][before])/(12*v['n']*count) for i,v in value['blocks'].items()}
            result[field][name] = dict(pooled_effect=pooled, equal_nonempty_block_effect=math.fsum(blocks.values())/len(blocks),
                changes=value[change_field][name], blocks=blocks, block_counts={i:v['n'] for i,v in value['blocks'].items()},
                block_changes={s:sum(sign(v)==s for v in blocks.values()) for s in SIGNS})
            assert sum(value[change_field][name].values()) == n
    assert sum(value['preservation_transition'].values()) == n
    if value['recipient_body_joint'] is not None: assert sum(value['recipient_body_joint'].values()) == n
    return result


def finish(value):
    return {cell:{level:{group:finish_group(groups[group]) if group in groups else dict(n=0, contributing_blocks=0)
        for group in GROUPS} for level,groups in levels.items()} for cell,levels in value.items()}


def context_table(rows, bodies, summary):
    result = {}
    for r in rows:
        k = '|'.join(r[x] for x in ('family', 'damage', 'body_source', 'arm'))
        v = result.setdefault(k, dict(n=0, original=0, incoming=0, outgoing=0,
            changes={s:0 for s in SIGNS}, record_deltas={}, body_n=0, body_incoming=0, body_outgoing=0, body_changes={s:0 for s in SIGNS}))
        v['n'] += 1
        for field in ('original', 'incoming', 'outgoing'): v[field] += units(r[field])
        delta = units(r['outgoing'])-units(r['incoming'])
        v['changes'][sign(delta)] += 1
        v['record_deltas'][r['world']] = v['record_deltas'].get(r['world'], 0)+delta
    for b in bodies:
        k = '|'.join(b[x] for x in ('family', 'damage', 'body_source', 'arm')); v = result[k]
        v['body_n'] += 1; v['body_incoming'] += units(b['preserve_body']); v['body_outgoing'] += units(b['repaired_score'])
        v['body_changes'][sign(units(b['repaired_score'])-units(b['preserve_body']))] += 1
    for k,v in result.items():
        family,damage,body,arm = k.split('|'); cell = summary['panel'][family][damage][body][arm]
        r = cell['receiving']['overall']; b = cell['body_vs_preservation']['overall']
        record_deltas = v.pop('record_deltas')
        v['record_changes'] = {s:sum(sign(x)==s for x in record_deltas.values()) for s in SIGNS}
        assert v['n'] == r['n'] and v['changes'] == r['pair_changes'] and v['record_changes'] == r['record_changes']
        assert v['body_n'] == b['n'] and v['body_changes'] == b['pair_changes']
        for name in ('incoming', 'outgoing'): assert abs(v[name]/(12*v['n'])-r[name]) <= 2e-15
        assert abs((v['outgoing']-v['incoming'])/(12*v['n'])-r['effect']) <= 2e-15
        assert abs(v['original']/(12*v['n'])-cell['receiving_vs_original']['overall']['incoming']) <= 2e-15
        for field in ('incoming', 'outgoing'): assert abs(v['body_'+field]/(12*v['body_n'])-b[field]) <= 2e-15
    return result


def check_prefix(short, full):
    assert set(short) == set(full) == {f's{t}_{field}' for t in (0,1,100,101,1000) for field in ('V','ema','R','theta')}
    for data in (short, full):
        assert all(v.shape == (16,16,16) and v.dtype == np.float64 and np.isfinite(v).all() for v in data.values())
    for t in (0,1,100):
        for field in ('V','ema','R','theta'):
            assert short[f's{t}_{field}'].tobytes() == full[f's{t}_{field}'].tobytes()
    for t in (101,1000): assert short[f's{t}_theta'].tobytes() == short['s100_theta'].tobytes()
    return dict(shared_checkpoint_arrays=12, short_gate_hold_arrays=2)


def prefixes(directory, config, custody):
    result = {}; zeros = {}
    for corruption,family,damage in itertools.product(range(config['corruptions']), config['families'], config['damage']):
        folder = directory/f'corruption_{corruption:02d}'/family/damage/'own'
        loaded = []; metadata = []
        for arm,budget in ((SELECTED[1],100),(SELECTED[2],1000)):
            m = custody.json(folder/(arm+'.json'))
            data = custody.data(folder/(arm+'_repair.npz'))
            assert digest(data) == m['files']['repair']
            with np.load(io.BytesIO(data), allow_pickle=False) as values:
                raw = {k:values[k].copy() for k in values.files}
            assert identities(raw) == m['arrays']['repair']
            for name,want in dict(block=config['block'], role=config['role'], corruption=corruption,
                family=family, damage=damage, body_source='own', arm=arm, memory='subtract', budget=budget).items(): assert m[name] == want
            assert m['metadata']['total_updates'] == 1000 and m['metadata']['write_updates'] == budget
            assert digest(raw['s0_theta'].tobytes()) == m['input_packet_sha256']
            assert digest(raw['s1000_theta'].tobytes()) == m['outgoing_sha256']
            if damage == 'mix000':
                z = (family, arm); assert zeros.setdefault(z, m['arrays']['repair']) == m['arrays']['repair']
            loaded.append(raw); metadata.append(m)
        assert metadata[0]['address'] == metadata[1]['address']
        assert metadata[0]['metadata']['rng_final'] == metadata[1]['metadata']['rng_final']
        assert metadata[0]['input_packet_sha256'] == metadata[1]['input_packet_sha256']
        proof = check_prefix(*loaded)
        result[f'{corruption}|{family}|{damage}'] = dict(**proof, records=16, paired_forcing=True,
            short_endpoint_sha256=metadata[0]['outgoing_sha256'], full_endpoint_sha256=metadata[1]['outgoing_sha256'])
    return result


def process(directory, custody):
    tick = time.monotonic()
    config = custody.json(directory/'CONFIG.json')
    assert config['config']['sweeps'] == config['readout']['sweeps'] == 1000
    assert config['config']['times'] == [0,1,100,101,1000]
    rows = custody.json(directory/'ROWS.json'); bodies = custody.json(directory/'BODIES.json')
    saved_summary = custody.json(directory/'SUMMARY.json')
    check = custody.json(directory/'SAVED_CHECK.json')
    assert check['status'] == 'PASS' and check['new_dynamics'] == 0
    row_map = validate_source(rows, bodies, config)
    context = context_table(rows, bodies, saved_summary)
    source_seconds = time.monotonic()-tick
    tick = time.monotonic(); prefix = prefixes(directory, config, custody); prefix_seconds = time.monotonic()-tick
    tick = time.monotonic()
    paired = pair_rows(row_map); cases = fold(paired); records = fold(cases, record=True)
    expected_cases = config['corruptions']*len(config['families'])*len(config['damage'])*16
    assert len(paired) == expected_cases*config['draws'] and len(cases) == expected_cases
    assert len(records)*config['corruptions'] == len(cases)
    assert all(v['n_draws'] == config['draws'] and v['body_repeats'] == 1 for v in cases)
    assert all(v['n_draws'] == config['draws']*config['corruptions'] and v['body_repeats'] == config['corruptions'] for v in records)
    stats = aggregate((paired, cases, records))
    # Independent reconciliation of the diagnostic marginal to TT028's signed short-minus-full contrast.
    for cell,levels in finish(stats).items():
        family,damage = cell.split('|'); original = saved_summary['panel'][family][damage]['own']
        for level in LEVELS:
            v = levels[level]['all']
            assert abs(v['recipient_effects']['extra_writing']['pooled_effect']+original[SELECTED[1]]['receiving_vs_full']['overall']['effect']) <= 2e-15
            assert abs(v['recipient_effects']['full_vs_preservation']['pooled_effect']-original[SELECTED[2]]['receiving']['overall']['effect']) <= 2e-15
            if level != LEVELS[0]:
                assert abs(v['body_effects']['extra_writing']['pooled_effect']+original[SELECTED[1]]['body_vs_full']['overall']['effect']) <= 2e-15
    analysis_seconds = time.monotonic()-tick
    return dict(config=config, pairs=paired, cases=cases, records=records, aggregate=stats, context=context,
        prefix_proof=prefix, verification=dict(status='PASS', source_rows=len(rows), source_bodies=len(bodies),
            paired_receiving_draws=len(paired), fixed_output_pairs=len(cases), record_positions=len(records),
            prefix_pairs=len(prefix), shared_checkpoint_arrays=12*len(prefix), short_gate_hold_arrays=2*len(prefix),
            all_controls_reconciled=len(context), new_dynamics=0, new_receiving_assays=0),
        timing=dict(source_seconds=source_seconds, prefix_seconds=prefix_seconds, analysis_seconds=analysis_seconds,
            source_row_bytes=(directory/'ROWS.json').stat().st_size+(directory/'BODIES.json').stat().st_size))
