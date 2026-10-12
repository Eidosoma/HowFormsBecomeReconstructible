#!/usr/bin/env python3
"""Extract published D135/D140 table values; no simulation or new inference."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estimate(cell):
    match = re.fullmatch(r'([+-]?\d+\.\d+)\s*\[\s*([+-]?\d+\.\d+),\s*([+-]?\d+\.\d+)\s*\]', cell.strip())
    if not match:
        raise ValueError(f'Unrecognized reported estimate: {cell}')
    mean, low, high = map(float, match.groups())
    assert low <= mean <= high
    return {'mean': mean, 'low': low, 'high': high}


def row(text, prefix):
    rows = [line for line in text.splitlines() if line.startswith('| ' + prefix + ' |')]
    if len(rows) != 1:
        raise ValueError(f'Expected one table row: {prefix}')
    return [cell.strip() for cell in rows[0].strip('|').split('|')]


def main():
    paths = {
        'D135': SOURCE / 'codex.lawsConfirmation/reviews/L20_SERIAL_ADDRESS_2026-09-16.md',
        'D140': SOURCE / 'codex.lawsConfirmation/reviews/L20_FRESH_FOUNDERS_2026-09-16.md',
        'P11_result': SOURCE / 'levin-cancer-gj-exploration/PAPER_EDITABLE_LINEAGE_RESULTS.md',
        'P11_protocol': SOURCE / 'levin-cancer-gj-exploration/PAPER_EDITABLE_LINEAGE_PROTOCOL.md',
    }
    hashes = {key: sha(path) for key, path in paths.items()}
    texts = {key: path.read_text() for key, path in paths.items()}
    entries = []
    for contrast, prefix in [('alignment', 'Aligned minus ordinary (primary only pooled)'),
                             ('copy', 'Aligned minus unchanged copy (secondary)')]:
        cells = row(texts['D135'], prefix)
        for role, cell in zip(('A', 'B', 'Pooled'), cells[1:]):
            entries.append(dict(campaign='D135', contrast=contrast, role=role,
                                primary=contrast == 'alignment' and role == 'Pooled', **estimate(cell)))
    cells = row(texts['D140'], 'D140, fresh founders')
    for role, cell in zip(('Pooled', 'A', 'B'), cells[1:]):
        entries.append(dict(campaign='D140', contrast='alignment', role=role,
                            primary=role == 'Pooled', **estimate(cell)))
    for role, label in [('Pooled', 'Pooled'), ('A', 'Pattern A'), ('B', 'Pattern B')]:
        entries.append(dict(campaign='D140', contrast='copy', role=role,
                            primary=False, **estimate(row(texts['D140'], label)[1])))
    assert len(entries) == 12
    lookup = {(e['campaign'], e['contrast'], e['role']): e for e in entries}
    assert lookup['D135', 'alignment', 'Pooled']['mean'] == 4.63
    assert lookup['D140', 'alignment', 'Pooled']['mean'] == 2.89
    # Check the old-cohort primary quoted in the replication report too.
    assert estimate(row(texts['D140'], 'D135, known founders')[1]) == {
        k: lookup['D135', 'alignment', 'Pooled'][k] for k in ('mean', 'low', 'high')}
    stages = [row(texts['P11_result'], label) for label in (
        'Before rewriting', 'Rewrite actual current carriers', 'After rewriting')]
    assert [s[1] for s in stages] == [s[2] for s in stages]
    assert 'All five registered stage gates pass.' in texts['P11_result']
    assert all(sha(path) == hashes[key] for key, path in paths.items()), 'Source changed during extraction'
    data = {
        'schema': 'forms_renewal_update_v1', 'selection_date': '2026-09-17',
        'source_type': 'Rounded estimates and intervals from completed report tables; no raw-array reanalysis',
        'unit': 'Qualified own-minus-alternative preference differences multiplied by 100',
        'interval': 'Reported pointwise 95% whole-block percentile bootstrap; no multiplicity adjustment',
        'sources': [{'id': key, 'path': str(path.relative_to(ROOT.parent)),
                     'sha256': hashes[key], 'bytes': path.stat().st_size} for key, path in paths.items()],
        'cohorts': {'D135': {'blocks': 8, 'lives_per_block': 4, 'roles': 2,
                            'status': 'Known founders; 75000-75007 maps to D132 73000-73007'},
                    'D140': {'blocks': 8, 'lives_per_block': 4, 'roles': 2,
                            'status': 'New founders 78000-78007; same guide and analysis'}},
        'estimates': entries,
        'P11': {'type': 'Protocol schematic with report-attributed outcomes',
                'stages': stages, 'all_five_gates_pass': True,
                'conditions': 'Externally supplied cells, cues, contacts and schedules; deterministic shared preparations'},
        'new_simulations': 0, 'new_statistical_tests': 0,
    }
    destination = ROOT / 'paper_assets/data'
    (destination / 'renewal-update-v1.json').write_text(json.dumps(data, indent=2) + '\n')
    with (destination / 'serial-alignment-v1.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)
    print('Extracted 12 reported contrasts and 3 P11 stage rows; sources unchanged.')


if __name__ == '__main__':
    main()
