"""Independent terminal table verification; no NumPy or simulator import."""
import argparse
import csv
import hashlib
from itertools import product
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_tables(folder, cfg):
    with (folder/'terminal_lineages.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    names = cfg['writers']+['erased']
    keys = [(int(r['block']), r['writer'], int(r['founder']), int(r['recipient']), r['injury']) for r in rows]
    expected = set(product(cfg['blocks'], names, range(4), range(cfg['config']['recipients']), cfg['injuries']))
    assert len(keys) == len(expected) and set(keys) == expected
    data = dict(zip(keys, rows, strict=True))
    for row in rows:
        assert int(row['success']) == int(float(row['margin']) > cfg['config']['margin'])
    result = json.loads((folder/'analysis.json').read_text())
    assert sha(folder/'terminal_lineages.csv') == result['terminal_csv_sha256']
    assert sha(folder/'generation_block_summaries.csv') == result['history_csv_sha256']
    for rate in result['rates']:
        group = [r for r in rows if r['writer'] == rate['writer'] and r['injury'] == rate['injury']]
        assert rate['n'] == len(group)
        assert rate['successes'] == sum(int(r['success']) for r in group)
        assert abs(rate['mean_block_success']-rate['successes']/rate['n']) < 1e-14
        assert abs(rate['mean_margin']-sum(float(r['margin']) for r in group)/len(group)) < 1e-12
    for contrast in result['comparisons']:
        total = dict(both_pass=0, rescued=0, harmed=0, both_fail=0)
        differences = []
        for fold in contrast['folds']:
            counts = dict.fromkeys(total, 0)
            for founder, recipient in product(range(4), range(cfg['config']['recipients'])):
                common = (fold['block'], founder, recipient, contrast['injury'])
                b, f, r, injury = common
                candidate = int(data[b, contrast['candidate'], f, r, injury]['success'])
                baseline = int(data[b, contrast['baseline'], f, r, injury]['success'])
                label = {(1, 1): 'both_pass', (1, 0): 'rescued', (0, 1): 'harmed', (0, 0): 'both_fail'}[candidate, baseline]
                counts[label] += 1
            for name, value in counts.items():
                assert fold[name] == value
                total[name] += value
            assert fold['n'] == sum(counts.values())
            difference = (counts['rescued']-counts['harmed'])/fold['n']
            assert difference == fold['success_difference']
            differences.append(difference)
        assert total == contrast['paired_counts']
        assert abs(sum(differences)/len(differences)-contrast['mean_block_success_difference']) < 1e-14
        assert contrast['blocks_positive'] == sum(x > 0 for x in differences)
        assert contrast['blocks_zero'] == sum(x == 0 for x in differences)
        assert contrast['blocks_negative'] == sum(x < 0 for x in differences)
    primary = next(c for c in result['comparisons'] if c['injury'] == 'scattered' and
                   [c['candidate'], c['baseline']] == cfg['primary_contrast'])
    assert result['primary'] == primary
    return dict(terminal_rows=len(rows), primary_and_secondary_paired_tables=True,
                strict_scoring=True, csv_bindings=True, implementation='Python standard library')


def main(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    complete = json.loads((folder/'COMPLETE.json').read_text())
    assert complete['status'] == 'COMPLETE' and complete['native_replay_passed']
    for name, digest in complete['outputs_sha256'].items():
        assert sha(folder/name) == digest, name
    print(json.dumps(verify_tables(folder, manifest['config']), indent=2))
    print('All completed-run output bindings verified. Development result, not confirmation.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    main(parser.parse_args().folder.resolve())
