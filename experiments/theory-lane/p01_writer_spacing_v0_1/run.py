"""Detached equal-count schedule pilot; replay, analyze and verify automatically."""
import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np

import dynamics as d
from analyze import analyze
from evidence import ROOT, check_assay, check_boundary, equal, native, pilot_arrays, save_npz, sha, stamp, verify_sources, verified_prior, write_json
from schedules import codes, reference_diagnostics, validate, verify_capture_and_measure
from verify import verify_tables, verify_native_diagnostics


def status(folder, value):
    temporary = folder/'STATUS.json.tmp'
    with temporary.open('w') as f:
        json.dump(dict(at_utc=stamp(), **value), f, indent=2, allow_nan=False)
        f.write('\n')
    temporary.replace(folder/'STATUS.json')


def check_code(manifest):
    for name, expected in manifest['code_sha256'].items():
        assert sha(ROOT/name) == expected, f'Frozen source changed: {name}'


def merge_controls(new, previous, axis, cfg, terminal=False):
    """O, reused T, reused P, new spaced, new cluster, optional erased."""
    equal(np.take(new, 0, axis), np.take(previous, 0, axis), 'original matches reused pilot')
    entries = [(new, 0), (previous, 1), (previous, 4), (new, 1), (new, 2)]
    if terminal:
        equal(np.take(new, 3, axis), np.take(previous, cfg['prior_erased_index'], axis), 'erased matches reused pilot')
        entries.append((new, 3))
    return np.stack([np.take(a, i, axis) for a, i in entries], axis=axis)


def merge_diagnostics(new, previous):
    equal(new[:, 0], previous[:, 0], 'original outgoing diagnostics match completed extraction')
    return np.stack((new[:, 0], previous[:, 1], previous[:, 2], new[:, 1], new[:, 2]), axis=1)


def check_pulse_prefix(raw, generation, block, cfg, prior, bindings):
    required = [(i, min(g for g in cfg['tolerance_generations'][name] if g > 3))
                for i, name in enumerate(cfg['simulated_writers'][1:], start=1)]
    applicable = [(i, first_extra) for i, first_extra in required if generation <= first_extra]
    if not applicable:
        return 0
    expected, _ = pilot_arrays(prior/f'boundary_{block:06d}_g{generation}.npz',
        ('masks', 'end', 'outgoing', 'mean_ports'), bindings)
    equal(raw['masks'], expected['masks'], 'shared pulse masks')
    checks = 1
    for index, first_extra in applicable:
        for field in ('end', 'mean_ports'):
            equal(raw[field][index], expected[field][2], 'body before first additional tolerance: '+field)
            checks += 1
        if generation < first_extra:
            equal(raw['outgoing'][index], expected['outgoing'][2], 'packet before first additional tolerance')
            checks += 1
    return checks


def run_block(folder, block, cfg, source, bindings, prior, prior_bindings, reference_transfer):
    started = time.perf_counter()
    prefix = f'boundary_{block:06d}'
    g3, _ = native(source/f'{prefix}_g3.npz', ('masks', 'end', 'outgoing', 'mean_ports'), bindings)
    g2, _ = native(source/f'{prefix}_g2.npz', ('outgoing',), bindings)
    equal(g2['outgoing'][0], g2['outgoing'][1], 'identical generation-2 parents')
    equal(g3['end'][0], g3['end'][1], 'common generation-3 body')
    equal(g3['mean_ports'][0], g3['mean_ports'][1], 'common initial expression')
    reference_path = source/f'cases_{block:06d}.npz'
    assert sha(reference_path) == bindings[reference_path.name]
    with np.load(reference_path, allow_pickle=False) as f:
        reference = {k: f[k] for k in ('body_correct', 'body_margin', 'assay_h32_correct', 'assay_h32_margin')}
    body = np.repeat(g3['end'][0:1], 3, axis=0)
    packets, statistics = d.capture(body, g3['masks'], d.policies_at(3, cfg), cfg['config'], cfg['tolerance'])
    equal(packets, g3['outgoing'][[0, 1, 1]], 'original and two identical first tolerance writes')
    initial = dict(masks=g3['masks'], end=body, outgoing=packets,
        mean_ports=np.repeat(g3['mean_ports'][0:1], 3, axis=0), **statistics)
    bodies, diagnostics, statistics_rows, event_codes = [], [], [], []
    checks = dict(original_boundary_arrays=0, original_scores=0, pulse_prefix_arrays=0,
        independent_capture_contexts=0, terminal_arrays=0, terminal_scores=0)
    generations = list(range(3, 33))
    for generation in generations:
        if generation == 3:
            raw = initial
        else:
            status(folder, dict(status='RUNNING', phase='renewal', block=block, generation=generation))
            raw = d.rebuild(packets, block, generation, d.policies_at(generation, cfg), cfg['config'], cfg['cycle'], cfg['tolerance'])
            expected, _ = native(source/f'{prefix}_g{generation}.npz', ('masks', 'birth', 'end', 'outgoing', 'mean_ports'), bindings)
            checks['original_boundary_arrays'] += check_boundary(raw, expected, (0,), (0,))
        raw['writer_codes'] = codes(generation, cfg)
        checks['pulse_prefix_arrays'] += check_pulse_prefix(raw, generation, block, cfg, prior, prior_bindings)
        transmission = verify_capture_and_measure(raw, generation, cfg)
        raw.update(transmission)
        checks['independent_capture_contexts'] += 3*4*4
        save_npz(folder/f'{prefix}_g{generation}.npz', raw)
        score = d.score(raw['mean_ports'], cfg['config']['margin'])
        equal(score['cue_correct'][:1], reference['body_correct'][generation-1, :1], 'original body correctness')
        equal(score['cue_margin'][:1], reference['body_margin'][generation-1, :1], 'original body margins')
        checks['original_scores'] += 2
        bodies.append(score)
        diagnostics.append(transmission)
        statistics_rows.append({k: raw[k] for k in ('newly_substituted_fraction', 'sign_flip_fraction')})
        event_codes.append(raw['writer_codes'])
        packets = raw['outgoing']
    recorded = np.stack(event_codes)
    equal(recorded.sum(axis=0), np.array([0, 6, 6], dtype=np.uint64), 'actual tolerance event counts')
    assert not recorded[11:].any(), 'Tolerance writer after generation 13'
    status(folder, dict(status='RUNNING', phase='terminal_assay', block=block, horizon=32))
    terminal = d.assay(packets, block, 32, cfg['config'], cfg['cycle'])
    expected, _ = native(source/f'assay_{block:06d}_h32.npz', ('masks', 'birth', 'end', 'mean_ports'), bindings)
    checks['terminal_arrays'] = check_assay(terminal, expected, (0, 3), (0, 35))
    terminal_score = d.score(terminal['mean_ports'], cfg['config']['margin'])
    for current, old in (('cue_correct', 'assay_h32_correct'), ('cue_margin', 'assay_h32_margin')):
        equal(terminal_score[current][[0, 3]], reference[old][[0, 35]], 'original and erased '+current)
    checks['terminal_scores'] = 4
    save_npz(folder/f'assay_{block:06d}_h32.npz', terminal)
    previous, _ = pilot_arrays(prior/f'cases_{block:06d}.npz',
        ('block', 'generations', 'body_both_pass', 'body_min_margin', 'assay_both_pass', 'assay_min_margin',
         'newly_substituted_fraction', 'sign_flip_fraction'), prior_bindings)
    equal(previous['block'], np.array(block), 'reused block')
    equal(previous['generations'], np.array(generations), 'reused generations')
    all_codes = np.stack((recorded[:, 0], np.ones(30, np.uint8),
        np.array([1]+[0]*29, np.uint8), recorded[:, 1], recorded[:, 2]), axis=1)
    data = dict(block=np.array(block), generations=np.array(generations), writer_codes=all_codes,
        body_both_pass=merge_controls(np.stack([s['both_pass'] for s in bodies]), previous['body_both_pass'], 1, cfg),
        body_min_margin=merge_controls(np.stack([s['min_margin'] for s in bodies]), previous['body_min_margin'], 1, cfg),
        assay_both_pass=merge_controls(terminal_score['both_pass'], previous['assay_both_pass'], 0, cfg, True),
        assay_min_margin=merge_controls(terminal_score['min_margin'], previous['assay_min_margin'], 0, cfg, True),
        **{k: merge_controls(np.stack([s[k] for s in statistics_rows]), previous[k], 1, cfg)
           for k in ('newly_substituted_fraction', 'sign_flip_fraction')},
        **{k: merge_diagnostics(np.stack([s[k] for s in diagnostics]), reference_transfer[k])
           for k in ('signed_transfer', 'unsigned_access')})
    case_hash = save_npz(folder/f'cases_{block:06d}.npz', data)
    receipt = dict(status='COMPLETE', block=block, seconds=time.perf_counter()-started, checks=checks,
        case_sha256=case_hash, original_replay_all_boundaries_and_terminal=True,
        schedule_prefixes_match_completed_pulse=True, all_branch_captures_independently_verified=True,
        new_schedule_tolerance_counts=recorded.sum(axis=0).tolist(), reused_controls_verified=True)
    write_json(folder/f'worker_{block:06d}.json', receipt)
    return receipt


def main(folder):
    started = time.perf_counter()
    try:
        manifest = json.loads((folder/'manifest.json').read_text())
        cfg = manifest['config']
        validate(cfg)
        check_code(manifest)
        source = verify_sources(cfg)
        prior, prior_complete = verified_prior(cfg)
        assert sha(folder/'raw_inputs.json') == manifest['raw_inputs_sha256']
        inputs = json.loads((folder/'raw_inputs.json').read_text())
        for name, digest in inputs['prior_files'].items():
            assert digest == prior_complete[name]
        reference = reference_diagnostics(cfg)
        receipts = []
        for block in cfg['blocks']:
            check_code(manifest)
            receipts.append(run_block(folder, block, cfg, source, inputs['native_files'], prior, inputs['prior_files'], reference[block]))
            print(f'Completed block {block}; original replay and schedule checks passed.', flush=True)
        status(folder, dict(status='RUNNING', phase='analysis'))
        summary = analyze(folder, cfg)
        verification = dict(**verify_tables(folder, cfg), **verify_native_diagnostics(folder, cfg))
        write_json(folder/'verification.json', verification)
        check_code(manifest)
        outputs = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
                   if p.is_file() and p.name not in ('COMPLETE.json', 'FAILED.json', 'STATUS.json', 'console.log')}
        complete = dict(status='COMPLETE', completed_at_utc=stamp(), seconds=time.perf_counter()-started,
            blocks_completed=cfg['blocks'], native_replay_passed=True, receipts=receipts,
            outputs_sha256=outputs, primary_result=summary['primary'],
            status_scope='Development schedule intervention; no predictor confirmation or full independent replay of new-arm dynamics.')
        write_json(folder/'COMPLETE.json', complete)
        status(folder, dict(status='COMPLETE', completed_at_utc=complete['completed_at_utc'],
            blocks_completed=cfg['blocks'], elapsed_seconds=complete['seconds']))
        print('COMPLETE: original replay, capture checks and independent result verification passed.', flush=True)
    except BaseException:
        write_json(folder/'FAILED.json', dict(status='FAILED', at_utc=stamp(), traceback=traceback.format_exc()))
        status(folder, dict(status='FAILED', detail='See FAILED.json; do not infer a scientific result.'))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    main(parser.parse_args().run.resolve())
