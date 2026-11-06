#!/usr/bin/env python3
"""Derive report tables from verified outputs; snapshot completed local notes."""
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import sys

sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-learning-v1')
ATTEMPT = BASE / 'attempt-01'
REPORTING = BASE / 'reporting-2026-10-30'
DOCUMENTS = ('FEP_BURST_LEARNING_V1_REPORT.md', 'README.md', 'NEXT_WORK.md',
             'FEP_FOCUS_2026-09-17.md', 'PROJECT_PLAN_2026-09-17.md',
             'AGENTS.md', 'DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):
    return json.loads((ATTEMPT / name).read_text())


def save(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True, default=str)
        out.write('\n')


def main():
    assert Path('/mnt/bioIce1').is_mount()
    readback, manifest, freeze = [read(n) for n in ('READBACK.json', 'MANIFEST.json', 'FREEZE.json')]
    assert readback['passed'] and readback['manifest_sha256'] == sha(ATTEMPT / 'MANIFEST.json')
    for name, digest in freeze['inputs'].items():
        assert sha(name) == digest, name
    for name, digest in freeze['snapshots'].items():
        assert sha(ATTEMPT / 'inputs' / name) == digest, name
    for name, digest in manifest['outputs'].items():
        assert sha(ATTEMPT / name) == digest, name
    result, selection, schedules = [read(n) for n in ('RESULTS.json', 'SELECTION.json', 'SCHEDULES.json')]
    names = ('reliability', 'frozen_reliability', 'joint_mixture', 'fixed_pool', 'hybrid',
             'always', 'conservative', 'fixed_schedule', 'matched_bayesian')
    fields = ('stable', 'B', 'R', 'J', 'odd_R', 'even_R')
    tables, onset_harms, decompositions = {}, {}, {}
    for alpha, case in result['cases'].items():
        tables[alpha] = {n: {k: F(case['policies'][n]['summary'][k]) for k in fields} for n in names}
        contrasts = case['comparisons']['hybrid']['worlds'][1:]
        onset_harms[alpha] = {
            'full_worse': [w['onset'] for w in contrasts if F(w['full']) > 0],
            'recovery_worse': [w['onset'] for w in contrasts if F(w['recovery']) > 0],
            'R_excluding_onset_10': sum(F(w['recovery']) for w in case['policies']['reliability']['worlds'][1:10]) / 9,
        }
        new, old = [case['policies'][n]['summary'] for n in ('reliability', 'frozen_reliability')]
        errors = F(new['stable_errors']) - F(old['stable_errors'])
        purchases = F(new['stable_purchases']) - F(old['stable_purchases'])
        difference = F(new['stable']) - F(old['stable'])
        assert difference == (errors + purchases / 10) / 10
        decompositions[alpha] = dict(stable_cost_difference=difference, error_difference=errors,
                                     purchase_difference=purchases)
    holdout = result['test_alphas']
    lower = {n: {k: sum(tables[a]['reliability'][k] < tables[a][n][k] for a in holdout)
                 for k in ('stable', 'B', 'R', 'J')} for n in names if n != 'reliability'}
    gate_counts = {n: {k: sum(result['cases'][a]['gates'][n][k] for a in holdout)
                       for k in ('stable', 'always_recovery', 'hybrid_recovery')} for n in names}
    diagnostics = {a: {n: result['cases'][a]['policies'][n]['summary'] for n in names} for a in holdout}
    terminal = {a: {n: result['cases'][a]['policies'][n]['worlds'][10] for n in names} for a in holdout}
    mask = schedules['selected']['mask']
    summary = dict(primary_pass=result['primary_pass'], mechanism=result['mechanism'], selection=selection['selected'],
        feasible_vertices=len(selection['vertices']), fixed_schedule_mask=mask,
        fixed_schedule_tasks=[t for t in range(1, 11) if mask >> (t - 1) & 1],
        tables=tables, strict_lower_counts=lower, gate_counts=gate_counts,
        onset_harms=onset_harms, stable_cost_decomposition=decompositions,
        heldout_diagnostics=diagnostics, onset_10=terminal,
        mean_error_run={a: 1 / (F(19, 20) * (1 - F(a))) for a in holdout},
        readback=readback, qualification=read('QUALIFICATION.json'), benchmark=read('BENCHMARK.json'),
        main_seconds=manifest['wall_seconds'], sealed_bytes=sum(p.stat().st_size for p in ATTEMPT.rglob('*') if p.is_file()))
    REPORTING.mkdir(exist_ok=False)
    save(REPORTING / 'DERIVED_SUMMARY.json', summary)
    (REPORTING / 'documents').mkdir()
    for name in DOCUMENTS:
        (REPORTING / 'documents' / name).write_bytes((ROOT / name).read_bytes())
    (REPORTING / 'summarize_fep_burst_learning.py').write_bytes(Path(__file__).read_bytes())
    save(REPORTING / 'COMPLETION_PROVENANCE.json', dict(
        completed=datetime.now(timezone.utc).isoformat(), both_side_studies_complete=True,
        scientific_primary_pass=False, no_successor_launched=True,
        attempt=str(ATTEMPT), manifest_sha256=sha(ATTEMPT / 'MANIFEST.json'),
        readback_sha256=sha(ATTEMPT / 'READBACK.json'), candidate_freeze_sha256=sha(ATTEMPT / 'CANDIDATE_FREEZE.json'),
        derivation_source_sha256=sha(__file__), documents={n: sha(ROOT / n) for n in DOCUMENTS},
        outputs={str(p.relative_to(REPORTING)): sha(p) for p in REPORTING.rglob('*') if p.is_file()}))
    print(json.dumps(dict(reporting=str(REPORTING), primary_pass=result['primary_pass'],
        assertions=readback['total_checks'], sealed_bytes=summary['sealed_bytes'],
        reporting_bytes=sum(p.stat().st_size for p in REPORTING.rglob('*') if p.is_file()),
        completion_sha256=sha(REPORTING / 'COMPLETION_PROVENANCE.json')), sort_keys=True))


if __name__ == '__main__':
    main()
