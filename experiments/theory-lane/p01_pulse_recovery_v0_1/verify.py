"""Independent table reconstruction plus explicit dense native-graph checks.

Imports neither extractor, diagnostic core nor analysis implementation.
"""
import csv
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=2e-13), (a, b)


def matrix(weights):
    result = np.zeros((256, 256))
    for row, col in product(range(16), repeat=2):
        i = row*16+col
        for plane, y, x in ((0, row, (col+1) % 16), (1, (row+1) % 16, col)):
            j = y*16+x
            result[i, j] = result[j, i] = weights[plane, row, col]
    denominator = np.abs(result).sum(axis=1)
    return np.divide(result, denominator[:, None], out=np.zeros_like(result), where=denominator[:, None] > 0)


def main():
    cfg = read(HERE / 'config.json')
    folder = HERE / 'results'
    extraction = read(folder / 'EXTRACTION_COMPLETE.json')
    definition = read(HERE / 'definition_snapshot.json')
    assert extraction['status'] == 'COMPLETE' and not (folder / 'FAILED.json').exists()
    assert extraction['definition_snapshot_sha256'] == sha(HERE / 'definition_snapshot.json')
    for name, digest in definition['files_sha256'].items():
        assert sha(HERE / name) == digest, name
    for rel, digest in extraction['source_inputs_sha256'].items():
        assert sha(HERE.parent / rel) == digest, rel
    assert sha(folder / 'lineages.csv') == extraction['outputs_sha256']['lineages.csv']
    summary = read(folder / 'analysis.json')
    for name, digest in summary['csv_sha256'].items():
        assert sha(folder / name) == digest, name
    with (folder / 'lineages.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    key = lambda r: (int(r['block']), int(r['generation']), r['writer'], int(r['founder']), int(r['recipient']))
    data = {key(r): r for r in rows}
    expected = set(product(cfg['blocks'], cfg['generations'], cfg['writers'], range(4), range(4)))
    assert set(data) == expected and len(rows) == len(data) == 19200
    original, tolerance, _, _, pulse = cfg['writers']
    for (b, g, w, f, r), row in data.items():
        assert int(row['body_pass']) == int(float(row['body_margin']) > .25)
        assert int(row['terminal_success']) == int(float(row['terminal_margin']) > .25)
        active = ('tolerance_rewrite' if g == 3 else 'exact_rewrite') if w == pulse else w
        assert row['active_writer'] == active
        if active == original:
            assert float(row['reader_action_distance_same_body_original']) == 0
        if w == original:
            assert float(row['reader_distance_original']) == float(row['transfer_minus_original']) == 0
        if w == pulse and g in (3, 4):
            reference = data[b, g, tolerance, f, r]
            for metric in ('body_margin', 'body_pass', 'hypothetical_tolerance_substitution_fraction'):
                assert row[metric] == reference[metric]
            if g == 3:
                for metric in ('signed_transfer', 'unsigned_access', 'reader_distance_original'):
                    assert row[metric] == reference[metric]
        initial = data[b, 3, w, f, r]
        assert row['terminal_margin'] == initial['terminal_margin'] and row['terminal_success'] == initial['terminal_success']

    for curve in summary['curves']:
        g, w = curve['generation'], curve['writer']
        assert curve['body_successes'] == sum(int(data[b, g, w, f, r]['body_pass']) for b, f, r in product(cfg['blocks'], range(4), range(4)))
        for metric, stats in curve['metrics'].items():
            means = [math.fsum(float(data[b, g, w, f, r][metric]) for f, r in product(range(4), repeat=2))/16 for b in cfg['blocks']]
            for a, b in zip(means, stats['block_values'], strict=True):
                close(a, b)
            close(math.fsum(means)/8, stats['mean'])
    for contrast in summary['declared_recovery_comparisons']:
        first, last, w, metric = (contrast[k] for k in ('first_generation', 'last_generation', 'writer', 'metric'))
        changes = []
        for block in cfg['blocks']:
            change = math.fsum(float(data[block, last, w, f, r][metric])-float(data[block, first, w, f, r][metric])
                               for f, r in product(range(4), repeat=2))/16
            changes.append(change)
        for a, b in zip(changes, contrast['block_changes'], strict=True):
            close(a, b)
        close(math.fsum(changes)/8, contrast['mean_change'])
        assert contrast['blocks_decreased'] == sum(c < 0 for c in changes)
        assert contrast['blocks_increased'] == sum(c > 0 for c in changes)
    for comparison in summary['paired_body_comparisons']:
        total = dict(both_pass=0, rescued=0, harmed=0, both_fail=0)
        g, w = comparison['generation'], comparison['baseline']
        for fold in comparison['blocks']:
            b = fold['block']
            counts = dict.fromkeys(total, 0)
            for f, r in product(range(4), repeat=2):
                a, reference = int(data[b, g, pulse, f, r]['body_pass']), int(data[b, g, w, f, r]['body_pass'])
                label = {(1, 1): 'both_pass', (1, 0): 'rescued', (0, 1): 'harmed', (0, 0): 'both_fail'}[a, reference]
                counts[label] += 1
            assert counts == fold['paired_counts']
            for label in total:
                total[label] += counts[label]
            for metric, difference in fold['differences'].items():
                close(difference, math.fsum(float(data[b, g, pulse, f, r][metric])-float(data[b, g, w, f, r][metric])
                      for f, r in product(range(4), repeat=2))/16)
        assert comparison['paired_counts'] == total

    ids = list(product(cfg['blocks'], range(4), range(4)))
    for w, stats in summary['body_failure_and_terminal_success'].items():
        failures = [(b, f, r) for b, f, r in ids if any(not int(data[b, g, w, f, r]['body_pass']) for g in range(4, 33))]
        assert stats['ever_failed_body'] == len(failures)
        assert stats['never_failed_body'] == 128-len(failures)
        assert stats['terminal_successes'] == sum(int(data[b, 3, w, f, r]['terminal_success']) for b, f, r in ids)
        assert stats['failed_body_but_passed_terminal'] == sum(int(data[b, 3, w, f, r]['terminal_success']) for b, f, r in failures)
    harmed = [(b, f, r) for b, f, r in ids if int(data[b, 3, original, f, r]['terminal_success']) and not int(data[b, 3, pulse, f, r]['terminal_success'])]
    assert harmed == [(r['block'], r['founder'], r['recipient']) for r in summary['all_terminal_harmed_lineages']]

    # Sample fixed, fully specified contexts, all five policies. Build the full
    # 256-node matrix independently, rather than reusing roll-based diagnostics.
    input_port = np.zeros((16, 16), bool)
    input_port[7:9, 1:3] = True
    output_a = np.zeros((16, 16), bool)
    output_a[3:5, 10:12] = True
    output_b = np.zeros((16, 16), bool)
    output_b[11:13, 10:12] = True
    dense_checks = 0
    for g in (3, 4, 8, 16, 32):
        old = np.load((HERE / cfg['prior_run']) / f'boundary_034000_g{g}.npz', allow_pickle=False)
        new = np.load((HERE / cfg['pulse_run']) / f'boundary_034000_g{g}.npz', allow_pickle=False)
        packets = (new['outgoing'][0, 0, 0], old['outgoing'][1, 0, 0], old['outgoing'][2, 0, 0],
                   new['outgoing'][1, 0, 0], new['outgoing'][2, 0, 0])
        eligible = (~new['masks'][0, 0]) & (~input_port)
        weights = [np.frombuffer(p.tobytes(), dtype='<f8').reshape(2, 16, 16) for p in packets]
        matrices = [matrix(w) for w in weights]
        for writer, transition in zip(cfg['writers'], matrices, strict=True):
            row = data[34000, g, writer, 0, 0]
            close(abs(transition-matrices[0]).sum(axis=1)[eligible.ravel()].mean(), row['reader_distance_original'])
            for unsigned in (False, True):
                operator = abs(transition) if unsigned else transition
                v = np.zeros(256)
                v[input_port.ravel()] = 1
                for _ in range(64):
                    v = operator @ v
                    v[input_port.ravel()] = 1
                value = min(v[output_a.ravel()].mean(), (1 if unsigned else -1)*v[output_b.ravel()].mean())
                close(value, row['unsigned_access' if unsigned else 'signed_transfer'])
            dense_checks += 1
        old.close()
        new.close()
    result = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), lineage_rows=len(rows),
        timecourse_points=len(summary['curves']), recovery_contrasts=len(summary['declared_recovery_comparisons']),
        paired_body_comparisons=len(summary['paired_body_comparisons']), dense_native_graph_contexts=dense_checks,
        all_source_and_definition_hashes_verified=True, body_and_terminal_endpoints_kept_separate=True,
        pulse_schedule_and_shared_boundary_equalities_verified=True,
        source_sha256=sha(Path(__file__)), analysis_sha256=sha(folder / 'analysis.json'))
    with (folder / 'verification.json').open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
