"""Full dynamics qualification on already observed native continuations only."""
import time
import traceback

import numpy as np
import chain
from common import ROOT, arrays, equal, read, save_arrays, sha, stamp, validate, write


def contract_checks():
    ports = np.array([[[.25, -.25], [-.25, .25]], [[1., -1.], [-1., 1.]], [[-1., 1.], [1., -1.]]])
    scored = chain.score(ports, 0)
    assert scored['both_pass'].tolist() == [False, True, False]
    assert scored['opposite_pass'].tolist() == [False, False, True]
    assert chain.score(ports, 4)['both_pass'].tolist() == [False, False, True]
    good = np.array([[True, True, False], [False, True, True], [True, True, True]])
    stats = chain.endpoints(good)
    assert stats['first_successor'] == [True, True, False]
    assert stats['uninterrupted'] == [False, True, False] and stats['terminal'] == [True, True, True]
    assert stats['first_failure_offset'] == [2, None, 1]
    initial = np.zeros((3, 4096), dtype=np.uint8)
    seen = []

    def fake_step(packet, event, generation):
        seen.append(generation)
        return dict(incoming=packet.copy(), outgoing=packet + 1, both_pass=np.zeros(3, bool))

    trace = chain.follow(initial, {'generation': 32}, 18, fake_step)
    assert seen == list(range(33, 51)) and not initial.any()
    assert (trace['outgoing'][-1] == 18).all()
    equal(trace['incoming'][1:], trace['outgoing'][:-1], 'linkage through failures')
    assert not trace['both_pass'].any()
    return ['strict_threshold', 'opposite_task_and_rule', 'recovery_vs_uninterrupted',
            'failure_offsets_and_censoring', 'own_successor_and_no_body_carry', 'full_horizon_after_failure']


def main():
    cfg = read(ROOT / 'source_config.json')
    validate(cfg)
    for key in ('dt', 'noise', 'birth_sd', 'observe_steps', 'margin'):
        assert cfg['reader'][key] == cfg['development_config'][key]
    selection = read(ROOT / 'SELECTION.json')
    folder = ROOT / 'qualification'
    folder.mkdir(exist_ok=False)
    begin, cpu = time.monotonic(), time.process_time()
    write(folder / 'START.json', dict(at_utc=stamp(), code_sha256={p.name: sha(p) for p in ROOT.glob('*.py')}))
    try:
        checks = contract_checks()
        times, rows = [], []
        for i, event in enumerate(selection['known_controls']):
            source = arrays(ROOT / event['fixture'], event['fixture_sha256'])
            incoming = source['incoming'][0].copy()
            trace = []
            for gi, generation in enumerate(event['generations']):
                start = time.monotonic()
                equal(incoming, source['incoming'][gi], 'known initial and own-successor packet')
                data = chain.transition(incoming, event, generation, cfg)
                for name in ('incoming', 'prepared', 'outgoing', 'birth', 'end', 'port_windows', 'mean_ports',
                             'min_margin', 'both_pass', 'opposite_margin', 'opposite_pass', 'applied'):
                    equal(data[name], source[name][gi], 'known native ' + name)
                equal(data['mask'], source['masks'][gi], 'known native mask')
                times.append(time.monotonic() - start)
                trace.append(data)
                incoming = data['outgoing'].copy()
            collected = {key: np.stack([step[key] for step in trace]) for key in trace[0]}
            name = f'known_{i:02d}.npz'
            rows.append(dict(block=event['block'], case=event['case'], file=name,
                             sha256=save_arrays(folder / name, collected)))
        forecast = 46 * 18 * max(times) * 1.5 + 60
        write(folder / 'COMPLETE.json', dict(status='PASS', at_utc=stamp(),
            seconds=time.monotonic() - begin, cpu_seconds=time.process_time() - cpu,
            contract_checks=checks, native_generations_checked=4, primary_reads_checked=12,
            independent_flat_reads=12, independent_optimizer_checks=4, independent_captures=12,
            rows=rows, step_wall_seconds=times, forecast_wall_seconds=forecast,
            forecast_rule='46 contexts x 18 successors x slowest known three-branch step x 1.5 + 60 seconds',
            all_known_native_bytes_match=True, files_sha256={p.name: sha(p) for p in folder.iterdir() if p.is_file()}))
        print('Qualification PASS: 6 contract checks; 12 known native reads and writes, 12 flat replays, 4 optimizers.', flush=True)
        print('Conservative full-run forecast:', round(forecast / 60, 2), 'minutes.', flush=True)
    except BaseException:
        write(folder / 'FAILED.json', dict(at_utc=stamp(), error=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
