"""Fixed schedule contract and independent capture/transfer diagnostics."""
import csv

import numpy as np

import diagnostic_core as core
from evidence import ROOT, equal, sha


def validate(cfg):
    assert cfg['blocks'] == list(range(34000, 34008))
    assert cfg['branch_generation'] == 3 and cfg['terminal_generation'] == 32
    assert cfg['simulated_writers'] == [cfg['writers'][i] for i in (0, 3, 4)]
    schedules = cfg['tolerance_generations']
    assert set(schedules) == set(cfg['writers'])
    for values in schedules.values():
        assert values == sorted(set(values)) and all(type(g) is int and 3 <= g <= 32 for g in values)
    assert schedules['exact_rewrite'] == []
    assert schedules['tolerance_rewrite'] == list(range(3, 33))
    assert schedules['single_tolerance_rewrite'] == [3]
    assert schedules['spaced_tolerance_rewrite'] == [3, 5, 7, 9, 11, 13]
    assert schedules['clustered_tolerance_rewrite'] == [3, 9, 10, 11, 12, 13]
    for name in cfg['simulated_writers'][1:]:
        assert len(schedules[name]) == cfg['new_schedule_tolerance_events'] == 6
        assert schedules[name][0] == cfg['first_tolerance_generation'] == 3
        assert schedules[name][-1] == cfg['last_tolerance_generation'] == 13
    assert cfg['original_writes_after_last_event'] == 32-13 == 19
    assert cfg['post_pulse_body_generation'] == 14 and cfg['diagnostic_steps'] == 64


def codes(generation, cfg):
    return np.array([int(generation in cfg['tolerance_generations'][w]) for w in cfg['simulated_writers']], np.uint8)


def verify_capture_and_measure(raw, generation, cfg):
    """Independent formula/order checks on the actual body and writer schedule."""
    body = raw['end'].reshape(48, 2, 16, 16)
    mask = np.broadcast_to(raw['masks'], (3, 4, 4, 16, 16)).reshape(48, 16, 16)
    pair = core.writer_pair(body, core.available_edges(mask), tolerance=cfg['tolerance'])
    actual_codes = codes(generation, cfg)
    old, tol = pair['exact'].reshape(3, 4, 4, 2, 16, 16), pair['tolerance'].reshape(3, 4, 4, 2, 16, 16)
    expected = np.stack([tol[i] if code else old[i] for i, code in enumerate(actual_codes)])
    packets = np.ascontiguousarray(expected, dtype='<f8').view(np.uint8).reshape(3, 4, 4, 4096)
    equal(raw['outgoing'], packets, 'independently computed scheduled captures')
    equal(raw['writer_codes'], actual_codes, 'recorded actual write events')
    p = np.zeros((3, 16, 16), bool)
    for i, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))):
        p[i, y:y+2, x:x+2] = True
    rows = core.normalized(expected.reshape(48, 2, 16, 16))
    rule = np.tile(np.repeat([1., -1., 1., -1.], 4), 3)
    signed = core.cue_transfer(rows, p[0], cfg['diagnostic_steps'])
    unsigned = core.cue_transfer(abs(rows), p[0], cfg['diagnostic_steps'])
    return dict(signed_transfer=core.minimum_task_transfer(signed, p, rule).reshape(3, 4, 4),
        unsigned_access=np.minimum(unsigned[..., p[1]].mean(axis=-1), unsigned[..., p[2]].mean(axis=-1)).reshape(3, 4, 4))


def reference_diagnostics(cfg):
    path = (ROOT/cfg['diagnostic_source']).resolve()
    assert sha(path) == cfg['diagnostic_source_sha256']
    result = {b: {k: np.full((30, 3, 4, 4), np.nan) for k in ('signed_transfer', 'unsigned_access')} for b in cfg['blocks']}
    selected = cfg['writers'][:3]
    seen = set()
    with path.open(newline='') as f:
        for row in csv.DictReader(f):
            if row['writer'] not in selected:
                continue
            b, g, founder, recipient = (int(row[k]) for k in ('block', 'generation', 'founder', 'recipient'))
            if b not in result:
                continue
            key = (b, g, row['writer'], founder, recipient)
            assert key not in seen
            seen.add(key)
            index = (g-3, selected.index(row['writer']), founder, recipient)
            for k in result[b]:
                result[b][k][index] = float(row[k])
    assert len(seen) == len(cfg['blocks'])*30*3*16
    assert all(np.isfinite(a).all() for metrics in result.values() for a in metrics.values())
    return result
