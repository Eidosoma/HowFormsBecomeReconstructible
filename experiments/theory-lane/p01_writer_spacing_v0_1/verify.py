"""Independent result tables and dense-graph transfer checks; no simulator import."""
import argparse
import csv
import hashlib
from itertools import product
import json
import math
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=2e-13), (a, b)


def read_csv(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def verify_tables(folder, cfg):
    terminal = read_csv(folder/'terminal_lineages.csv')
    names = cfg['writers']+['erased']
    key = lambda r: (int(r['block']), r['writer'], int(r['founder']), int(r['recipient']), r['injury'])
    data = {key(r): r for r in terminal}
    expected = set(product(cfg['blocks'], names, range(4), range(4), cfg['injuries']))
    assert len(terminal) == len(data) == len(expected) and set(data) == expected
    for row in terminal:
        assert int(row['success']) == int(float(row['margin']) > cfg['config']['margin'])
        assert row['provenance'] == cfg['provenance'][row['writer']]
    result = json.loads((folder/'analysis.json').read_text())
    for name, digest in result['csv_sha256'].items():
        assert sha(folder/name) == digest
    for rate in result['rates']:
        group = [r for r in terminal if r['writer'] == rate['writer'] and r['injury'] == rate['injury']]
        assert rate['n'] == len(group) and rate['successes'] == sum(int(r['success']) for r in group)
        close(rate['mean_success'], rate['successes']/rate['n'])
        close(rate['mean_margin'], math.fsum(float(r['margin']) for r in group)/len(group))
        for b, p in zip(cfg['blocks'], rate['block_rates'], strict=True):
            assert p == sum(int(r['success']) for r in group if int(r['block']) == b)/16
    for contrast in result['comparisons']:
        total = dict(both_pass=0, rescued=0, harmed=0, both_fail=0)
        differences = []
        for fold in contrast['folds']:
            counts = dict.fromkeys(total, 0)
            b = fold['block']
            for f, r in product(range(4), repeat=2):
                injury = contrast['injury']
                a = int(data[b, contrast['candidate'], f, r, injury]['success'])
                reference = int(data[b, contrast['baseline'], f, r, injury]['success'])
                label = {(1, 1): 'both_pass', (1, 0): 'rescued', (0, 1): 'harmed', (0, 0): 'both_fail'}[a, reference]
                counts[label] += 1
            for k, v in counts.items():
                assert fold[k] == v
                total[k] += v
            assert fold['n'] == 16
            difference = (counts['rescued']-counts['harmed'])/16
            assert difference == fold['success_difference']
            differences.append(difference)
        assert total == contrast['paired_counts']
        close(sum(differences)/len(differences), contrast['mean_block_success_difference'])
        assert contrast['blocks_positive'] == sum(d > 0 for d in differences)
        assert contrast['blocks_zero'] == sum(d == 0 for d in differences)
        assert contrast['blocks_negative'] == sum(d < 0 for d in differences)
    primary = next(c for c in result['comparisons'] if c['injury'] == 'scattered' and
                   [c['candidate'], c['baseline']] == cfg['primary_contrast'])
    assert result['primary'] == primary
    assert result['tolerance_generations'] == cfg['tolerance_generations']

    histories = read_csv(folder/'body_lineages.csv')
    hkey = lambda r: (int(r['block']), int(r['generation']), r['writer'], int(r['founder']), int(r['recipient']))
    hd = {hkey(r): r for r in histories}
    expected = set(product(cfg['blocks'], range(3, 33), cfg['writers'], range(4), range(4)))
    assert len(histories) == len(hd) == len(expected) and set(hd) == expected
    for row in histories:
        g, w = int(row['generation']), row['writer']
        assert int(row['success']) == int(float(row['margin']) > .25)
        expected_action = 'tolerance_rewrite' if g in cfg['tolerance_generations'][w] else 'exact_rewrite'
        assert row['active_writer_policy'] == expected_action
    block_history = read_csv(folder/'generation_block_summaries.csv')
    hgroups = {(int(r['block']), int(r['generation']), r['writer']): r for r in block_history}
    assert len(hgroups) == len(block_history) == len(cfg['blocks'])*30*5
    for (b, g, w), row in hgroups.items():
        group = [hd[b, g, w, f, r] for f, r in product(range(4), repeat=2)]
        assert row['provenance'] == cfg['provenance'][w]
        assert row['active_writer_policy'] == group[0]['active_writer_policy']
        for out, source in (('success_fraction', 'success'), ('mean_margin', 'margin'),
                            ('signed_transfer', 'signed_transfer'), ('unsigned_access', 'unsigned_access')):
            close(row[out], math.fsum(float(r[source]) for r in group)/16)
    assert result['post_pulse_body_generation'] == 14
    for item in result['post_pulse_body']:
        group = [r for r in histories if r['writer'] == item['writer'] and int(r['generation']) == 14]
        assert item['successes'] == sum(int(r['success']) for r in group)
        assert item['n'] == len(group)
        for b, rate in zip(cfg['blocks'], item['block_rates'], strict=True):
            assert rate == sum(int(r['success']) for r in group if int(r['block']) == b)/16
    return dict(terminal_rows=len(terminal), body_rows=len(histories), paired_tables=True,
        actual_schedule_labels=True, post_pulse_body_separate_from_terminal=True,
        provenance_labels=True, strict_scoring=True, csv_hashes=True)


def verify_native_diagnostics(folder, cfg):
    import numpy as np
    p = np.zeros((3, 16, 16), bool)
    for j, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))):
        p[j, y:y+2, x:x+2] = True
    checked = 0
    block = cfg['blocks'][0]
    for g in (3, 4, 5, 9, 13, 14, 32):
        with np.load(folder/f'boundary_{block:06d}_g{g}.npz', allow_pickle=False) as saved:
            packets, signed, unsigned, events = (saved[k] for k in ('outgoing', 'signed_transfer', 'unsigned_access', 'writer_codes'))
        assert events.tolist() == [int(g in cfg['tolerance_generations'][w]) for w in cfg['simulated_writers']]
        for n, founder in product(range(3), (0, 1)):
            weights = np.frombuffer(packets[n, founder, 0].tobytes(), dtype='<f8').reshape(2, 16, 16)
            matrix = np.zeros((256, 256))
            for y, x in product(range(16), repeat=2):
                i = y*16+x
                for plane, yy, xx in ((0, y, (x+1) % 16), (1, (y+1) % 16, x)):
                    j = yy*16+xx
                    matrix[i, j] = matrix[j, i] = weights[plane, y, x]
            denominator = abs(matrix).sum(axis=1)
            transition = np.divide(matrix, denominator[:, None], out=np.zeros_like(matrix), where=denominator[:, None] > 0)
            rule = (1., -1.)[founder]
            for unsigned_flag in (False, True):
                operator = abs(transition) if unsigned_flag else transition
                value = np.zeros(256)
                value[p[0].ravel()] = 1
                for _ in range(64):
                    value = operator @ value
                    value[p[0].ravel()] = 1
                expected = min(value[p[1].ravel()].mean(), value[p[2].ravel()].mean()) if unsigned_flag else min(
                    rule*value[p[1].ravel()].mean(), -rule*value[p[2].ravel()].mean())
                close(expected, (unsigned if unsigned_flag else signed)[n, founder, 0])
            checked += 1
    return dict(dense_native_transfer_contexts=checked, both_task_directions_checked=True)


def main(folder):
    complete = json.loads((folder/'COMPLETE.json').read_text())
    assert complete['status'] == 'COMPLETE' and complete['native_replay_passed']
    assert not (folder/'FAILED.json').exists()
    for name, digest in complete['outputs_sha256'].items():
        assert sha(folder/name) == digest, name
    cfg = json.loads((folder/'manifest.json').read_text())['config']
    print(json.dumps(dict(**verify_tables(folder, cfg), **verify_native_diagnostics(folder, cfg)), indent=2))
    print('Completed output bindings and independent checks passed. Development result only.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    main(parser.parse_args().folder.resolve())
