#!/usr/bin/env python3
"""Freeze the v0.14 selection and transcribe E041's reported figure values.

No campaign code is imported; no trajectories, statistics, or scientific audits
are rerun. Missing external artifacts are recorded, never replaced by fixtures.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORMS = ROOT / 'experiments'
CELL = ROOT.parent / 'PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/levin-cancer-gj-exploration'
DATA = ROOT / 'paper_assets/data/forms-cellular-v0.14.json'
CSV = ROOT / 'paper_assets/data/functional-renewal-e041-v1.csv'
PACKAGE = ROOT / 'paper_assets/data/forms-cellular-v0.14-source-records.zip'
RECORD = ROOT / 'reviews/V0.14_SOURCES.json'

FORM_RUNS = {
    'E023_receiver_compensation': 'receiver_v1',
    'E024_serial_compensation': 'serial_v1',
    'E025_rewriting_confirmation': 'confirmation_v1',
    'E026_restoration_intervention': 'restoration_v1',
    'E027_selective_renewal': 'selective_v1',
    'E028_precursor_rewriting': 'precursor_v1',
    'E029_maturing_renewal': 'maturing_v1',
    'E030_maturing_confirmation': 'confirmation_v1',
    'E031_renewal_durability': 'durability_v1',
    'E032_renewal_failure_diagnosis': 'diagnosis_v1',
    'E033_delayed_expression': 'expression_v1',
    'E034_settled_rebuilding': 'rebuilding_v1',
    'E035_cue_selective_capture': 'capture_v1',
    'E036_serial_cue_capture_v2': 'serial_v1',
    'E037_repair_support_diagnosis': 'diagnosis_v1',
    'E038_weak_bridge_capture': 'serial_v1',
    'E039_weak_bridge_confirmation': 'serial_v1',
    'E040_weak_bridge_durability': 'serial_v1',
    'E041_full_rewrite_confirmation': 'serial_v1',
    'E042_late_failure_diagnosis': 'diagnosis_v1',
    'E043_late_reader_timing': 'expression_v1',
    'E044_transition_diagnosis': 'diagnosis_v1',
    'E045_weakening_rollback': 'rollback_v1',
    'E046_failure_chronology': 'chronology_v1',
    'E047_onset_rollback': 'onset_v2',
}
CELL_STEMS = {
    'P17': 'PAPER_RENEWAL_MATURATION',
    'P18': 'PAPER_PREPARATION_TURNOVER',
    'P19': 'PAPER_PREPARATION_SUPPORT',
    'P20': 'PAPER_PREPARATION_LOCALIZATION',
    'P21': 'PAPER_PREPARATION_COMPONENTS',
    'P22': 'PAPER_RNA_TIMING_ROBUSTNESS',
    'P23': 'PAPER_PAUSE_TRANSMISSION',
    'P24': 'PAPER_PAUSE_DURABILITY',
    'P25': 'PAPER_NEIGHBOUR_FIRST_DRAW',
    'P26': 'PAPER_PAUSE_WINDOW',
    'P27': 'PAPER_PAUSE_BOUNDARY',
    'P28': 'PAPER_NUMERICAL_CONVERGENCE',
    'P29': 'PAPER_UPSTREAM_FORK_CONVERGENCE',
    'P30': 'PAPER_REFINED_PAUSE_BOUNDARY',
    'P31': 'PAPER_DELAYED_PAUSE_CONVERGENCE',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files, missing, checks, summaries = [], [], [], {}

    def add(path, member, study, role, required=False):
        if not path.is_file():
            missing.append({'path': str(path), 'study': study, 'role': role,
                            'symlink_target': str(path.readlink()) if path.is_symlink() else None})
            if required:
                raise FileNotFoundError(path)
            return
        files.append({'path': str(path), 'archive_member': member, 'study': study,
                      'role': role, 'bytes': path.stat().st_size, 'sha256': sha(path)})

    def check(path, expected, context):
        actual = sha(path) if path.is_file() else None
        status = 'match' if actual == expected else 'missing' if actual is None else 'mismatch'
        checks.append({'path': str(path), 'expected_sha256': expected,
                       'actual_sha256': actual, 'context': context, 'status': status})
        if status == 'mismatch':
            raise ValueError(f'Source binding mismatch: {path}')

    for folder, run in FORM_RUNS.items():
        study = folder[:4]
        base = FORMS / folder
        for name in ('README.md', 'PROTOCOL.md'):
            add(base / name, f'forms/{folder}/{name}', study, 'context_or_protocol', True)
        if study in {'E038', 'E041'}:
            for name in ('model.py', 'audit.py'):
                add(base / name, f'forms/{folder}/{name}', study, 'inspected_mechanism_source', True)
        runpath = base / 'runs' / run
        for name in ('REPORT.md', 'summary.json', 'COMPLETE.json', 'manifest.json', 'INDEPENDENT_AUDIT.json'):
            p = runpath / name
            add(p, f'forms/{folder}/runs/{run}/{name}', study, 'retained_result_or_metadata', name == 'REPORT.md')
        cp = runpath / 'COMPLETE.json'
        if cp.is_file():
            completion = json.loads(cp.read_text())
            outputs = completion.get('outputs_sha256', {})
            for name in ('REPORT.md', 'summary.json', 'manifest.json'):
                if name in outputs:
                    check(runpath / name, outputs[name], 'selected completion output binding')
        ap = runpath / 'INDEPENDENT_AUDIT.json'
        if ap.is_file():
            audit = json.loads(ap.read_text())
            if 'complete_sha256' in audit:
                check(cp, audit['complete_sha256'], 'saved audit binds completion; audit not rerun')
        # Keep native summaries when available, without substituting test fixtures.
        sp = runpath / 'summary.json'
        if sp.is_file() and study in {'E023', 'E025', 'E026', 'E046', 'E047'}:
            summaries[study] = json.loads(sp.read_text())

    for study, stem in CELL_STEMS.items():
        for suffix in ('_PROTOCOL.md', '_RESULTS.md'):
            add(CELL / (stem + suffix), f'cellular/{stem + suffix}', study,
                'protocol_or_report', suffix == '_PROTOCOL.md')
    for study, name in (
        ('P27', 'P27_NUMERICAL_STOP_REVIEW_2026-10-03.md'),
        ('P30', 'P30_NUMERICAL_STOP_REVIEW_2026-10-06.md'),
        ('P31', 'storage/p31-active.json'),
        ('P31', 'storage/p31-launch-integrity.json'),
    ):
        add(CELL / name, f'cellular/{name}', study, 'stop_or_launch_status', True)

    report = FORMS / 'E041_full_rewrite_confirmation/runs/serial_v1/REPORT.md'
    rows = []
    for line in report.read_text().splitlines():
        if not re.match(r'^\| \d+ \|', line):
            continue
        cells = [x.strip() for x in line.strip('|').split('|')]
        generation, policy = int(cells[0]), cells[1]
        for injury, cell in zip(('intact', 'scattered24', 'square9'), cells[2:5]):
            match = re.fullmatch(r'([\d.]+) \[([\d.]+), ([\d.]+)\]', cell)
            if match is None:
                raise ValueError(f'Unexpected report interval: {cell}')
            mean, low, high = map(float, match.groups())
            rows.append({'generation': generation, 'policy': policy, 'terminal_injury': injury,
                         'both_cues_percent': mean, 'ci95_low': low, 'ci95_high': high})
    assert len(rows) == 201  # Initial row plus eleven policies at six renewal horizons; three injuries.
    assert sorted({r['generation'] for r in rows}) == [0, 1, 3, 8, 16, 24, 32]
    # Full rewriting and its matched ablations are present in the reported panel.
    focal = next(r for r in rows if r['generation'] == 32 and r['policy'] == 'bridge_rewrite'
                 and r['terminal_injury'] == 'scattered24')
    assert focal['both_cues_percent'] == 83.59
    gain_match = re.search(r'Primary h32 gain: \*\*([\d.]+) \[([\d.]+), ([\d.]+)\]', report.read_text())
    assert gain_match
    gain = dict(zip(('mean', 'low', 'high'), map(float, gain_match.groups())))
    payload = {
        'version': 'v0.14', 'selection_date': '2026-10-08',
        'scope': 'Reviewed forms E023–E047; selected cellular P17–P30 reports and P31 launch status only.',
        'e041': {'source': str(report.relative_to(ROOT)), 'source_sha256': sha(report),
                 'endpoint': 'Both opposite cues correct under the normalized fresh terminal reader',
                 'units': 'percent of 512 lineages clustered in 32 independent blocks',
                 'intervals': 'Rounded original pointwise 95% whole-block bootstrap intervals, transcribed from REPORT.md',
                 'values': rows,
                 'primary_h32_gain_points': gain,
                 'qualification': 'FULL_REWRITING_QUALIFIED',
                 'durability': 'DURABLE_THROUGH_32_RENEWALS'},
        'available_native_summaries': summaries,
        'model_runs_performed': False, 'statistics_recomputed': False,
    }
    with CSV.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    DATA.write_text(json.dumps(payload, indent=2) + '\n')
    with zipfile.ZipFile(PACKAGE, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in files:
            data = Path(entry['path']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            archive.writestr(entry['archive_member'], data)
    with zipfile.ZipFile(PACKAGE) as archive:
        for entry in files:
            assert hashlib.sha256(archive.read(entry['archive_member'])).hexdigest() == entry['sha256']
    record = {
        'version': 'v0.14', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': payload['scope'], 'source_files': files, 'unavailable_selected_paths': missing,
        'source_checks': checks, 'model_runs_performed': False,
        'statistics_recomputed': False, 'original_scientific_audits_rerun': False,
        'limitations': ['Selected reports/protocols and metadata, not a full executable or raw-array archive.',
                       'Unavailable scientific summaries are not replaced with fixture/benchmark summaries.',
                       'New cellular raw runs remain at external paths unavailable in this checkout.',
                       'P19/P24 report links are unavailable; no separate outcome is promoted from their protocols.',
                       'P27/P30 stops and P31 launch do not supply completed onward-transmission results.'],
        'data': {'path': str(DATA.relative_to(ROOT)), 'sha256': sha(DATA)},
        'figure_csv': {'path': str(CSV.relative_to(ROOT)), 'sha256': sha(CSV)},
        'archive': {'path': str(PACKAGE.relative_to(ROOT)), 'sha256': sha(PACKAGE), 'members_verified': len(files)},
        'extractor_sha256': sha(Path(__file__)),
    }
    RECORD.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'source_files': len(files), 'checks': {s: sum(c['status'] == s for c in checks)
          for s in ('match', 'missing', 'mismatch')}, 'unavailable_paths': len(missing), 'figure_values': len(rows)}))


if __name__ == '__main__':
    main()
