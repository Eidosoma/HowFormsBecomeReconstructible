"""Detached fixed-cohort pilot; validate every control and analyze on completion."""
import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np

import dynamics as d
from analyze import analyze
from evidence import ROOT, check_assay, check_boundary, equal, native, pilot_arrays, save_npz, sha, stamp, verify_sources, verified_prior, write_json
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


def merge_controls(new, prior, axis, terminal=False):
    """O, reused T, reused S, new M, new pulse, and terminal erased reference."""
    equal(np.take(new, 0, axis=axis), np.take(prior, 0, axis=axis), 'original matches prior pilot')
    entries = [(new, 0), (prior, 1), (prior, 2), (new, 1), (new, 2)]
    if terminal:
        equal(np.take(new, 3, axis=axis), np.take(prior, 3, axis=axis), 'erased matches prior pilot')
        entries.append((new, 3))
    return np.stack([np.take(array, index, axis=axis) for array, index in entries], axis=axis)


def run_block(folder, block, cfg, source, bindings, prior, prior_bindings):
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
    packets, statistics = d.capture(body, generation3['masks'], d.policies_at(3, cfg), cfg['config'], cfg['tolerance'])
    equal(packets[[0, 2]], generation3['outgoing'][:2], 'original and single tolerance pulse capture')
    initial = dict(masks=generation3['masks'], end=body, outgoing=packets,
        mean_ports=np.repeat(generation3['mean_ports'][0:1], 3, axis=0), **statistics)
    save_npz(folder/f'{prefix}_g3.npz', initial)
    bodies = []
    statistics_rows = []
    generations = list(range(cfg['branch_generation'], cfg['terminal_generation']+1))
    checks = dict(initial_shared_boundary=4, boundary_arrays=0, body_scores=0, assay_arrays=0, assay_scores=0,
                  pulse_generation4=0)
    for generation in generations:
        if generation == cfg['branch_generation']:
            raw = initial
        else:
            status(folder, dict(status='RUNNING', phase='renewal', block=block, generation=generation))
            raw = d.rebuild(packets, block, generation, d.policies_at(generation, cfg), cfg['config'], cfg['cycle'], cfg['tolerance'])
            expected, _ = native(source/f'{prefix}_g{generation}.npz',
                ('masks', 'birth', 'end', 'mean_ports', 'outgoing'), bindings)
            checks['boundary_arrays'] += check_boundary(raw, expected, (0,), (0,))
            if generation == 4:
                equal(raw['end'][2], expected['end'][1], 'pulse first successor reads tolerance packet')
                equal(raw['mean_ports'][2], expected['mean_ports'][1], 'pulse first successor expression')
                exact_capture, _ = d.capture(expected['end'][1:2], expected['masks'], ['exact_rewrite'],
                                             cfg['config'], cfg['tolerance'])
                equal(raw['outgoing'][2:3], exact_capture, 'pulse ends before generation-4 writing')
                checks['pulse_generation4'] = 3
            save_npz(folder/f'{prefix}_g{generation}.npz', raw)
        scores = d.score(raw['mean_ports'], cfg['config']['margin'])
        equal(scores['cue_correct'][:1], reference['body_correct'][generation-1, :1], 'original body correct')
        equal(scores['cue_margin'][:1], reference['body_margin'][generation-1, :1], 'original body margin')
        checks['body_scores'] += 2
        bodies.append(scores)
        statistics_rows.append({k: raw[k] for k in ('newly_substituted_fraction', 'sign_flip_fraction', 'magnitude_sign_fallback_fraction')})
        packets = raw['outgoing']
    status(folder, dict(status='RUNNING', phase='terminal_assay', block=block, horizon=32))
    terminal = d.assay(packets, block, 32, cfg['config'], cfg['cycle'])
    expected, _ = native(source/f'assay_{block:06d}_h32.npz', ('masks', 'birth', 'end', 'mean_ports'), bindings)
    checks['assay_arrays'] = check_assay(terminal, expected, (0, 3), (0, 35))
    terminal_scores = d.score(terminal['mean_ports'], cfg['config']['margin'])
    for current, old in [('cue_correct', 'assay_h32_correct'), ('cue_margin', 'assay_h32_margin')]:
        equal(terminal_scores[current][[0, 3]], reference[old][[0, 35]], 'terminal '+current)
    checks['assay_scores'] = 4
    save_npz(folder/f'assay_{block:06d}_h32.npz', terminal)
    prior_case, _ = pilot_arrays(prior/f'cases_{block:06d}.npz',
        ('block', 'generations', 'body_both_pass', 'body_min_margin', 'assay_both_pass', 'assay_min_margin',
         'newly_substituted_fraction', 'sign_flip_fraction'), prior_bindings)
    equal(prior_case['block'], np.array(block), 'reused block identity')
    equal(prior_case['generations'], np.array(generations), 'reused generation identity')
    data = dict(block=np.array(block), generations=np.array(generations),
        body_both_pass=merge_controls(np.stack([s['both_pass'] for s in bodies]), prior_case['body_both_pass'], 1),
        body_min_margin=merge_controls(np.stack([s['min_margin'] for s in bodies]), prior_case['body_min_margin'], 1),
        assay_both_pass=merge_controls(terminal_scores['both_pass'], prior_case['assay_both_pass'], 0, True),
        assay_min_margin=merge_controls(terminal_scores['min_margin'], prior_case['assay_min_margin'], 0, True),
        simulated_magnitude_sign_fallback_fraction=np.stack([s['magnitude_sign_fallback_fraction'] for s in statistics_rows]),
        **{name: merge_controls(np.stack([s[name] for s in statistics_rows]), prior_case[name], 1)
           for name in ('newly_substituted_fraction', 'sign_flip_fraction')})
    case_hash = save_npz(folder/f'cases_{block:06d}.npz', data)
    receipt = dict(status='COMPLETE', block=block, seconds=time.perf_counter()-started,
        checks=checks, case_sha256=case_hash, magnitude_and_support_control_checked_at_every_capture=True,
        replay_original_all_boundaries=True, replay_original_erased_terminal=True,
        reused_prior_controls_verified=True, pulse_schedule_checked=True)
    write_json(folder/f'worker_{block:06d}.json', receipt)
    return receipt


def main(folder):
    started = time.perf_counter()
    try:
        manifest = json.loads((folder/'manifest.json').read_text())
        cfg = manifest['config']
        check_code(manifest)
        source = verify_sources(cfg)
        prior, prior_complete_bindings = verified_prior(cfg)
        assert sha(folder/'raw_inputs.json') == manifest['raw_inputs_sha256']
        input_record = json.loads((folder/'raw_inputs.json').read_text())
        bindings, prior_bindings = input_record['native_files'], input_record['prior_files']
        for name, digest in prior_bindings.items():
            assert digest == prior_complete_bindings[name], name
        receipts = []
        for block in cfg['blocks']:
            check_code(manifest)
            receipts.append(run_block(folder, block, cfg, source, bindings, prior, prior_bindings))
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
            outputs_sha256=outputs, primary_results=summary['primaries'], factorial_result=summary['factorial'],
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
