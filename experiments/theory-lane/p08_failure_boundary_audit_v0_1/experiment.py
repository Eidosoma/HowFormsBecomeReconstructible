"""Paired current-boundary interventions, exact factual and separate flat replays."""
import argparse
from collections import Counter
import hashlib
import os
import platform
import sys
import time
import traceback

import numpy as np
import audit_optimizer
import audit_reader
import lineage_dynamics as dynamics
from common import ROOT, arrays, equal, read, save_arrays, sha, stamp, status, validate, write
from read_case import replay
from repair import recipient_repair

OUTCOMES = ('rescue', 'both_fail', 'harm', 'both_pass')
DIAGNOSTICS = ('signs', 'candidate_costs', 'flips', 'final_improvable_nodes', 'cost',
               'initial_cost', 'winner', 'sweeps', 'selected_improvable_nodes')


def outcome(good):
    return 'rescue' if good[1] and not good[0] else 'harm' if good[0] and not good[1] else 'both_pass' if all(good) else 'both_fail'


def one(event, cfg, folder, i, known=False):
    source = arrays(ROOT / event['fixture'], event['fixture_sha256'])
    incoming = source['incoming']
    assert hashlib.sha256(incoming.tobytes()).hexdigest() == event['incoming_sha256']
    w = dynamics.decode(incoming)
    repaired, solution, magnitude = recipient_repair(w, cfg['optimizer'])
    separate = audit_optimizer.solve(audit_optimizer.independent_coupling(w),
        np.flatnonzero(dynamics.PORTS[0].ravel()), cfg['optimizer'])
    for key in DIAGNOSTICS:
        if isinstance(solution[key], np.ndarray):
            equal(solution[key], separate[key], 'separate optimizer ' + key)
        else:
            assert solution[key] == separate[key], key
    equal(repaired[w != 0], w[w != 0], 'repair preserves every nonzero weight')
    signs = solution['signs']
    edge_signs = np.stack((signs * np.roll(signs, -1, -1), signs * np.roll(signs, -1, -2)))
    equal(repaired[w == 0], (magnitude * edge_signs).astype(w.dtype)[w == 0], 'completed zero weights')
    packets = np.stack((incoming, dynamics.encode(repaired)))
    equal(packets[0], source['prepared'][0], 'factual prepared packet')
    if known:
        equal(packets, source['prepared'], 'both known prepared packets')
    identity = cfg['continuation_namespace'] + ':' + str(event['block'])
    case, generation = event['case'], event['generation']
    raw = replay(packets, source['mask'], case, identity, generation, cfg)
    flat = audit_reader.replay(packets, source['mask'], case // 4, case % 4,
        identity, 0, cfg, original=True, generation=generation, rhos=[0., 0.])
    equal(raw['birth'], source['birth'], 'factual reset')
    equal(raw['birth'], flat['birth'], 'separate reset')
    for key in ('end', 'mean_ports', 'port_windows'):
        equal(raw[key], flat[key][0], 'separate paired dynamics ' + key)
        factual = raw[key][:, :1] if key == 'port_windows' else raw[key][:1]
        equal(raw[key] if known else factual, source[key], 'saved factual dynamics ' + key)
    rule = 1. if (case // 4) % 2 == 0 else -1.
    aligned = raw['mean_ports'] * rule * np.array([[1., -1.], [-1., 1.]])
    margins = aligned.min(axis=(1, 2))
    good = margins > cfg['reader']['margin']
    equal(margins if known else margins[:1], source['min_margin'], 'saved margins')
    equal(good if known else good[:1], source['both_pass'], 'saved outcomes')
    result = outcome(good)
    if known:
        assert result == event['outcome'], 'known positive or negative control'
    else:
        assert not good[0] and result in ('rescue', 'both_fail')
    fields = dict(incoming=incoming, packets=packets, mask=source['mask'], **raw,
                  aligned_ports=aligned, min_margin=margins, both_pass=good,
                  magnitude=np.asarray(magnitude), **{'optimizer_' + k: np.asarray(solution[k]) for k in DIAGNOSTICS})
    name = f'context_{i:02d}.npz'
    digest = save_arrays(folder / name, fields)
    return dict(context=i, block=event['block'], case=case, generation=generation,
        history=event['history'], once_uninterrupted=event.get('once_uninterrupted'),
        incoming_sha256=event['incoming_sha256'], fixture=event['fixture'],
        no_repair_margin=float(margins[0]), repair_margin=float(margins[1]), outcome=result,
        added_edges=int(np.count_nonzero((w == 0) & (repaired != 0))),
        added_available_edges=int(np.count_nonzero((w == 0) & (repaired != 0) & dynamics.available_edges(source['mask']))),
        file=name, sha256=digest)


def summary(rows):
    return {name: sum(row['outcome'] == name for row in rows) for name in OUTCOMES}


def validate_freeze():
    manifest = read(ROOT / 'FROZEN.json')
    for name, digest in manifest['files_sha256'].items():
        assert sha(ROOT / name) == digest, 'Frozen input changed: ' + name
    return manifest


def main(mode):
    cfg = read(ROOT / 'source_config.json')
    validate(cfg)
    protocol = read(ROOT / 'PROTOCOL.json')
    selection = read(ROOT / 'SELECTION.json')
    if mode == 'run':
        validate_freeze()
        assert read(ROOT / 'qualification' / 'COMPLETE.json')['forecast_wall_seconds'] < 600
    folder = ROOT / ('qualification' if mode == 'qualify' else 'run')
    folder.mkdir(exist_ok=False)
    begin, cpu = time.monotonic(), time.process_time()
    write(folder / 'START.json', dict(at_utc=stamp(), pid=os.getpid(), mode=mode,
        python=platform.python_version(), numpy=np.__version__, selection_sha256=sha(ROOT / 'SELECTION.json'),
        frozen_sha256=sha(ROOT / 'FROZEN.json') if mode == 'run' else None,
        code_sha256={p.name: sha(p) for p in ROOT.glob('*.py')}))
    status(folder, status='RUNNING', contexts_completed=0)
    try:
        events = selection['known_controls'] if mode == 'qualify' else selection['events']
        rows, times = [], []
        for i, event in enumerate(events):
            start = time.monotonic()
            rows.append(one(event, cfg, folder, i, known=mode == 'qualify'))
            times.append(time.monotonic() - start)
            status(folder, status='RUNNING', contexts_completed=i + 1, total=len(events))
        result = dict(status='COMPLETE', at_utc=stamp(), mode=mode, rows=rows, counts=summary(rows),
            contexts=len(rows), primary_read_contexts=2 * len(rows), independent_flat_read_contexts=2 * len(rows),
            independent_optimizer_checks=len(rows), factual_contexts_checked=2 * len(rows) if mode == 'qualify' else len(rows),
            all_factual_and_independent_bytes_match=True, seconds=time.monotonic() - begin,
            cpu_seconds=time.process_time() - cpu, context_wall_seconds=times,
            source_complete_sha256=selection['source_complete_sha256'], selection_sha256=sha(ROOT / 'SELECTION.json'),
            by_history={h: summary([r for r in rows if r['history'] == h]) for h in cfg['histories']},
            by_generation={str(g): summary([r for r in rows if r['generation'] == g]) for g in sorted({r['generation'] for r in rows})},
            once_uninterrupted_subset=summary([r for r in rows if r['once_uninterrupted']]),
            interpretation=protocol['interpretation'], original_prospective_verdict='UNRESOLVED', automatic_successor=False)
        if mode == 'qualify':
            result['forecast_wall_seconds'] = 46 * max(times) * 1.5 + 30
            assert result['counts'] == dict(rescue=1, both_fail=0, harm=1, both_pass=0)
        else:
            assert len(rows) == 46 and result['counts']['rescue'] + result['counts']['both_fail'] == 46
            validate_freeze()
        result['files_sha256'] = {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'STATUS.json'}
        write(folder / 'COMPLETE.json', result)
        status(folder, status='COMPLETE', contexts_completed=len(rows), counts=result['counts'])
        print({k: result[k] for k in ('status', 'mode', 'contexts', 'counts', 'seconds', 'cpu_seconds')}, flush=True)
        if mode == 'qualify':
            print('Conservative 46-context forecast:', result['forecast_wall_seconds'], 'seconds', flush=True)
    except BaseException:
        write(folder / 'FAILED.json', dict(at_utc=stamp(), error=traceback.format_exc()))
        status(folder, status='FAILED')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('qualify', 'run'))
    main(parser.parse_args().mode)
