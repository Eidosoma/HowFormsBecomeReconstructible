"""Detached fixed-cohort pilot; validate every control and analyze on completion."""
import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np

import dynamics as d
from analyze import analyze
from evidence import ROOT, check_assay, check_boundary, equal, native, save_npz, sha, stamp, verify_sources, write_json
from verify import verify_tables


def status(folder, value):
    temporary = folder/'STATUS.json.tmp'
    with temporary.open('w') as f:
        json.dump(dict(at_utc=stamp(), **value), f, indent=2, allow_nan=False)
        f.write('\n')
    temporary.replace(folder/'STATUS.json')


def check_code(manifest):
    for name, expected in manifest['code_sha256'].items():
        assert sha(ROOT/name) == expected, f'Frozen code changed: {name}'


def run_block(folder, block, cfg, source, bindings):
    started = time.perf_counter()
    prefix = f'boundary_{block:06d}'
    generation3, _ = native(source/f'{prefix}_g3.npz', ('masks', 'end', 'outgoing', 'mean_ports'), bindings)
    generation2, _ = native(source/f'{prefix}_g2.npz', ('outgoing',), bindings)
    equal(generation2['outgoing'][0], generation2['outgoing'][1], 'identical parent records at generation 2')
    equal(generation3['end'][0], generation3['end'][1], 'identical pre-intervention body')
    equal(generation3['mean_ports'][0], generation3['mean_ports'][1], 'identical pre-intervention expression')
    case_path = source/f'cases_{block:06d}.npz'
    assert sha(case_path) == bindings[case_path.name]
    with np.load(case_path, allow_pickle=False) as f:
        reference = {k: f[k] for k in ('body_correct', 'body_margin', 'assay_h32_correct', 'assay_h32_margin')}
    # Only this initial body is shared. Each policy later captures its own body.
    body = np.repeat(generation3['end'][0:1], 3, axis=0)
    packets, statistics = d.capture(body, generation3['masks'], cfg['writers'], cfg['config'], cfg['tolerance'])
    equal(packets[:2], generation3['outgoing'][:2], 'initial original/tolerance capture')
    initial = dict(masks=generation3['masks'], end=body, outgoing=packets,
        mean_ports=np.repeat(generation3['mean_ports'][0:1], 3, axis=0), **statistics)
    save_npz(folder/f'{prefix}_g3.npz', initial)
    bodies = []
    statistics_rows = []
    generations = list(range(cfg['branch_generation'], cfg['terminal_generation']+1))
    checks = dict(initial_shared_boundary=4, boundary_arrays=0, body_scores=0, assay_arrays=0, assay_scores=0)
    for generation in generations:
        if generation == cfg['branch_generation']:
            raw = initial
        else:
            status(folder, dict(status='RUNNING', phase='renewal', block=block, generation=generation))
            raw = d.rebuild(packets, block, generation, cfg['writers'], cfg['config'], cfg['cycle'], cfg['tolerance'])
            expected, _ = native(source/f'{prefix}_g{generation}.npz',
                ('masks', 'birth', 'end', 'mean_ports', 'outgoing'), bindings)
            checks['boundary_arrays'] += check_boundary(raw, expected)
            save_npz(folder/f'{prefix}_g{generation}.npz', raw)
        scores = d.score(raw['mean_ports'], cfg['config']['margin'])
        equal(scores['cue_correct'][:2], reference['body_correct'][generation-1, :2], 'body correct')
        equal(scores['cue_margin'][:2], reference['body_margin'][generation-1, :2], 'body margin')
        checks['body_scores'] += 4
        bodies.append(scores)
        statistics_rows.append({k: raw[k] for k in ('newly_substituted_fraction', 'sign_flip_fraction')})
        packets = raw['outgoing']
    status(folder, dict(status='RUNNING', phase='terminal_assay', block=block, horizon=32))
    terminal = d.assay(packets, block, 32, cfg['config'], cfg['cycle'])
    expected, _ = native(source/f'assay_{block:06d}_h32.npz', ('masks', 'birth', 'end', 'mean_ports'), bindings)
    checks['assay_arrays'] = check_assay(terminal, expected)
    terminal_scores = d.score(terminal['mean_ports'], cfg['config']['margin'])
    for current, old in [('cue_correct', 'assay_h32_correct'), ('cue_margin', 'assay_h32_margin')]:
        equal(terminal_scores[current][[0, 1, 3]], reference[old][[0, 1, 35]], 'terminal '+current)
    checks['assay_scores'] = 6
    save_npz(folder/f'assay_{block:06d}_h32.npz', terminal)
    data = dict(block=np.array(block), generations=np.array(generations),
        body_both_pass=np.stack([s['both_pass'] for s in bodies]),
        body_min_margin=np.stack([s['min_margin'] for s in bodies]),
        assay_both_pass=terminal_scores['both_pass'], assay_min_margin=terminal_scores['min_margin'],
        **{name: np.stack([s[name] for s in statistics_rows]) for name in statistics_rows[0]})
    case_hash = save_npz(folder/f'cases_{block:06d}.npz', data)
    receipt = dict(status='COMPLETE', block=block, seconds=time.perf_counter()-started,
        checks=checks, case_sha256=case_hash, magnitude_and_support_control_checked_at_every_capture=True,
        replay_all_original_tolerance_boundaries=True, replay_original_tolerance_erased_terminal=True)
    write_json(folder/f'worker_{block:06d}.json', receipt)
    return receipt


def main(folder):
    started = time.perf_counter()
    try:
        manifest = json.loads((folder/'manifest.json').read_text())
        cfg = manifest['config']
        check_code(manifest)
        source = verify_sources(cfg)
        assert sha(folder/'raw_inputs.json') == manifest['raw_inputs_sha256']
        bindings = json.loads((folder/'raw_inputs.json').read_text())['files']
        receipts = []
        for block in cfg['blocks']:
            check_code(manifest)
            receipts.append(run_block(folder, block, cfg, source, bindings))
            print(f'Completed block {block}; native control replay passed.', flush=True)
        status(folder, dict(status='RUNNING', phase='analysis'))
        summary = analyze(folder, cfg)
        verification = verify_tables(folder, cfg)
        write_json(folder/'verification.json', verification)
        check_code(manifest)
        outputs = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
                   if p.is_file() and p.name not in ('COMPLETE.json', 'FAILED.json', 'STATUS.json', 'console.log')}
        complete = dict(status='COMPLETE', completed_at_utc=stamp(), seconds=time.perf_counter()-started,
            blocks_completed=cfg['blocks'], native_replay_passed=True, receipts=receipts,
            outputs_sha256=outputs, primary_result=summary['primary'],
            status_scope='Development intervention; no general forecasting or full E051 audit claim.')
        write_json(folder/'COMPLETE.json', complete)
        status(folder, dict(status='COMPLETE', completed_at_utc=complete['completed_at_utc'],
            blocks_completed=cfg['blocks'], elapsed_seconds=complete['seconds']))
        print('COMPLETE: all native control replays passed; analysis and report saved.', flush=True)
    except BaseException:
        failed = dict(status='FAILED', at_utc=stamp(), traceback=traceback.format_exc())
        write_json(folder/'FAILED.json', failed)
        status(folder, dict(status='FAILED', detail='See FAILED.json; no scientific conclusion should be drawn.'))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    main(parser.parse_args().run.resolve())
