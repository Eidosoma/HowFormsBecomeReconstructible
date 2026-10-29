"""Acquisition-order selection, independent of forecasts and finish order."""
import hashlib
import json

from ff_common import P, require
import acquisition


def check_rows(block, rows, scientific):
    keys = [tuple(r['key']) for r in rows]
    require(len(keys) == len(set(keys)) and keys, 'Duplicate or absent boundary records')
    if scientific:
        expected = {(block,h,f,r) for h in P['acquisition']['histories'] for f in range(4) for r in range(4)}
        require(set(keys) == expected, 'All64 acquisition records required')
    for row in rows:
        require(row['key'] == [block,row['history'],row['founder'],row['recipient']] and row['block'] == block,
                'Acquisition identity mismatch')
        require(row['rule'] == (1 if row['founder']%2 == 0 else -1), 'Wrong task rule')
        require(row['current_pass'] in (0,1) and row['current_pass'] == int(row['boundary'][5]), 'Wrong expression class')
        digest = hashlib.sha256(json.dumps([P['selection']['namespace'],*row['key']],separators=(',',':')).encode()).hexdigest()
        require(digest == row['selection_hash'], 'Selection rank changed')


def select(rows):
    selected = acquisition.select(rows)
    # Separate direct implementation checks the inherited selection rule.
    independent = []
    for block in sorted({r['block'] for r in rows}):
        for c in (0,1):
            group = [r for r in rows if r['block'] == block and r['current_pass'] == c]
            positive = [r for r in group if r['rule'] == 1]
            negative = [r for r in group if r['rule'] == -1]
            if positive and negative:
                independent += [min(negative,key=lambda r:r['selection_hash']), min(positive,key=lambda r:r['selection_hash'])]
            else:
                independent += sorted(group,key=lambda r:r['selection_hash'])[:2]
    require(selected == independent, 'Independent selection differs')
    return selected


def cohort(attempts, spec):
    """Only complete ascending waves can be evaluated; preserve surplus records."""
    ids = sorted(attempts)
    require(ids == list(range(spec['first_block'], spec['first_block']+len(ids))), 'Missing or out-of-order attempt IDs')
    require(0 < len(ids) <= spec['maximum_attempts'] and len(ids)%spec['wave_size'] == 0,
            'Attempt cap or complete-wave requirement violated')
    eligible = [b for b in ids if {r['current_pass'] for r in attempts[b]} == {0,1}]
    retained = eligible[:spec['eligible_blocks']]
    if len(retained) == spec['eligible_blocks']:
        stop = ((retained[-1]-spec['first_block'])//spec['wave_size']+1)*spec['wave_size']
        require(len(ids) == stop, 'Acquisition continued beyond the first sufficient complete wave')
    return dict(complete=len(retained)==spec['eligible_blocks'], blocks=retained,
        attempted_blocks=ids, eligible_blocks=eligible,
        ineligible_blocks=[b for b in ids if b not in eligible], surplus_blocks=eligible[spec['eligible_blocks']:],
        rows=[r for b in retained for r in select(attempts[b])])
