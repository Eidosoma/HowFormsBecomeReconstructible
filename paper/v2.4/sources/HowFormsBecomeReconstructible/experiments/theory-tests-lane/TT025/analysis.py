"""Paired finite-panel summaries with explicit historical/recipient nesting."""
from collections import defaultdict
import itertools
import math
from common import *
import design

def average(v):
    values = list(v)
    return math.fsum(values)/len(values) if values else None
def counts(v):
    values = list(v)
    return dict(improved=sum(x > 0 for x in values), worsened=sum(x < 0 for x in values), tied=sum(x == 0 for x in values))
def effect(rows, cumulative=False):
    if not rows: return dict(n=0)
    before = 'initial' if cumulative else 'incoming'; change = 'cumulative_effect' if cumulative else 'effect'
    block = {str(i): average(r[change] for r in rows if r['block'] == i) for i in sorted({r['block'] for r in rows})}
    record_groups = defaultdict(list)
    for row in rows: record_groups[(row['block'], row['world'])].append(row)
    records = [dict(block=k[0], world=k[1], message=k[1]//4, replicate=k[1] % 4, draws=len(v),
        incoming=average(r[before] for r in v), outgoing=average(r['outgoing'] for r in v),
        effect=average(r[change] for r in v)) for k, v in sorted(record_groups.items())]
    result = dict(n=len(rows), incoming=average(r[before] for r in rows), outgoing=average(r['outgoing'] for r in rows),
        effect=average(r[change] for r in rows), blocks=block, equal_block_effect=average(block.values()),
        draw_changes=counts(r[change] for r in rows), record_changes=counts(r['effect'] for r in records), record_means=records)
    # Independent integer twelfths include native three-way tolerance ties.
    credit = lambda value: int(round(12*value))
    assert all(abs(credit(r[k])/12-r[k]) <= 2e-15 for r in rows for k in (before, 'outgoing'))
    integer_effect = sum(credit(r['outgoing'])-credit(r[before]) for r in rows)/(12*len(rows))
    assert abs(result['effect']-integer_effect) <= 2e-15
    assert abs(result['effect']-(result['outgoing']-result['incoming'])) <= 2e-15
    return result

def validate(rows, role, indices):
    histories, draws, cycles = design.schedule(role)
    keys = ('block', 'history', 'draw', 'family', 'arm', 'world', 'cycle')
    expected = set(itertools.product(indices, range(histories), range(draws), design.FAMILIES, design.ARMS, range(16), range(1, cycles+1)))
    actual = [tuple(r[k] for k in keys) for r in rows]
    assert len(actual) == len(set(actual)) == len(expected) and set(actual) == expected
    groups = defaultdict(list)
    initial_scores = {}; preservation = 0
    for row in rows:
        assert row['message'] == row['world']//4 and row['replicate'] == row['world'] % 4
        assert row['effect'] == row['outgoing']-row['incoming'] and row['cumulative_effect'] == row['outgoing']-row['initial']
        assert all(row[k] in (0., .25, 1/3, .5, 1.) for k in ('incoming', 'outgoing', 'initial'))
        key = tuple(row[k] for k in ('block', 'history', 'draw', 'family', 'world'))
        if key in initial_scores: assert initial_scores[key] == row['initial']
        else: initial_scores[key] = row['initial']
        groups[key+(row['arm'],)].append(row)
        if row['arm'] == 'zero_off':
            assert row['effect'] == row['cumulative_effect'] == 0.
            assert row['incoming_version'] == row['outgoing_version'] == 'initial'; preservation += 1
    for records in groups.values():
        records.sort(key=lambda r: r['cycle']); assert len(records) == cycles
        assert records[0]['incoming'] == records[0]['initial']
        for a, b in zip(records, records[1:]):
            assert a['outgoing'] == b['incoming'] and a['outgoing_version'] == b['incoming_version']
        assert abs(math.fsum(r['effect'] for r in records)-records[-1]['cumulative_effect']) <= 2e-15
        units = lambda v: int(round(12*v))
        assert sum(units(r['outgoing'])-units(r['incoming']) for r in records) == units(records[-1]['outgoing'])-units(records[0]['initial'])
    return dict(status='PASS', rows=len(rows), telescoping_chains=len(groups), zero_preservation_rows=preservation)

def conditional(rows):
    groups = defaultdict(list)
    keys = ('block', 'history', 'family', 'arm', 'world', 'cycle')
    for row in rows: groups[tuple(row[k] for k in keys)].append(row)
    result = []
    for key, values in sorted(groups.items()):
        assert len({r['draw'] for r in values}) == len(values)
        result.append(dict(zip(keys, key), draws=len(values), incoming=average(r['incoming'] for r in values),
            outgoing=average(r['outgoing'] for r in values), effect=average(r['effect'] for r in values),
            gains_harms_ties=counts(r['effect'] for r in values),
            individual_draws=[dict(draw=r['draw'], incoming=r['incoming'], outgoing=r['outgoing'], effect=r['effect']) for r in sorted(values, key=lambda r: r['draw'])]))
    return result

def summarize(rows, role, indices):
    proof = validate(rows, role, indices); histories, draws, cycles = design.schedule(role)
    families = {}
    for family in design.FAMILIES:
        arms = {}
        for arm in design.ARMS:
            selected = [r for r in rows if r['family'] == family and r['arm'] == arm]
            by_cycle = {}
            for g in range(1, cycles+1):
                subset = [r for r in selected if r['cycle'] == g]
                by_cycle[str(g)] = dict(overall=effect(subset),
                    messages={str(m): effect([r for r in subset if r['message'] == m]) for m in range(4)},
                    injury_strata={s: effect([r for r in subset if r['injury_stratum'] == s]) for s in design.STRATA},
                    developed_status={name: effect([r for r in subset if (r['developed_score'] == 1) == passed])
                        for name, passed in (('unique_pass', True), ('not_unique_pass', False))})
            terminal = [r for r in selected if r['cycle'] == cycles]
            arms[arm] = dict(cycles=by_cycle, final_minus_initial=effect(terminal, True))
        families[family] = dict(arms=arms)
    primary = families['residual']['arms']['subtract_on']['final_minus_initial']
    assert abs(primary['effect']-primary['equal_block_effect']) <= 2e-15
    return dict(classification='EXPOSED_CASE_PAIRED_RECEIVING_DEVELOPMENT', role=role, blocks=list(indices),
        historical_futures=histories, new_draws_per_packet=draws, cycles=cycles, arms=list(design.ARMS), families=families,
        primary='residual:subtract_on:final_minus_initial', primary_effect=primary['equal_block_effect'],
        primary_block_effects=primary['blocks'], verification=proof, significance_verdict=False,
        fresh_population_confirmation=False, native_repair_or_writing=False)

def summary(directory, role):
    indices = BLOCKS if role == 'development' else DISPOSABLE
    rows = [r for i in indices for r in read_json(directory/f'tissue_{i}/ROWS.json')]
    return summarize(rows, role, indices), conditional(rows)

def report(value):
    lines = ['# TT025 paired receiving results', '',
        'Descriptive development on exposed historical cases; new paired recipient draws. No fresh-population confirmation or significance gate.', '',
        f'Primary informative corrected final-minus-initial effect: {100*value["primary_effect"]:+.3f} percentage points.', '',
        '| Family | Policy | Initial | Final | Paired difference | Draw gains / harms / ties | Starting-record gains / harms / ties |',
        '| --- | --- | ---: | ---: | ---: | --- | --- |']
    def changes(x): return ' / '.join(str(x[k]) for k in ('improved', 'worsened', 'tied'))
    for family in design.FAMILIES:
        for arm in design.ARMS:
            v = value['families'][family]['arms'][arm]['final_minus_initial']
            lines.append(f'| {family} | {arm} | {100*v["incoming"]:.3f}% | {100*v["outgoing"]:.3f}% | {100*v["effect"]:+.3f} pp | {changes(v["draw_changes"])} | {changes(v["record_changes"])} |')
    for family in design.FAMILIES:
        for arm in design.ARMS:
            data = value['families'][family]['arms'][arm]
            lines += ['', f'## {family}: {arm}', '',
                '| Cycle | Incoming | Outgoing | Paired difference | Block effects (pp) | Gains / harms / ties |',
                '| ---: | ---: | ---: | ---: | --- | --- |']
            for g in range(1, value['cycles']+1):
                v = data['cycles'][str(g)]['overall']; block = ', '.join(f'{100*v["blocks"][str(i)]:+.3f}' for i in value['blocks'])
                lines.append(f'| {g} | {100*v["incoming"]:.3f}% | {100*v["outgoing"]:.3f}% | {100*v["effect"]:+.3f} pp | {block} | {changes(v["draw_changes"])} |')
    lines += ['', 'All block, message, current-injury and current-body-status summaries are retained in SUMMARY.json. CONDITIONAL.json retains every historical packet pair and each new draw. Existing body histories are descriptors; no new serial body endpoint is measured.', '',
        'Four recipient draws per historical packet are coarse conditional samples. Shared draws, versions, policies and historical futures are not independent population replication. Differences telescope under common recipients; preservation must equal zero. These contrasts measure replacing the packet in the receiving assay, not a counterfactual serial repair policy.', '']
    return '\n'.join(lines)
