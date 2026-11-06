#!/usr/bin/env python3
"""Save exact report derivations and completion provenance, after readback."""
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import re
import sys

sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-burst-alltiming-v1')
ATTEMPT = BASE / 'attempt-01'
REPORTING = BASE / 'reporting-2026-10-31-correction-01'
DOCUMENTS = ('FEP_BURST_ALLTIMING_V1_REPORT.md', 'README.md', 'NEXT_WORK.md',
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
    readback, manifest, freeze, candidate = [read(n) for n in
        ('READBACK.json', 'MANIFEST.json', 'FREEZE.json', 'CANDIDATE_FREEZE.json')]
    assert readback['passed'] and readback['manifest_sha256'] == sha(ATTEMPT / 'MANIFEST.json')
    for name, digest in freeze['inputs'].items():
        assert sha(name) == digest, name
    for name, digest in freeze['snapshots'].items():
        assert sha(ATTEMPT / 'inputs' / name) == digest, name
    for records in (manifest['outputs'], candidate['training_files']):
        for name, digest in records.items():
            assert sha(ATTEMPT / name) == digest, name
    report = (ROOT / DOCUMENTS[0]).read_text().lower()
    assert not re.search(r'\b(?:pending|in progress)\b', report)
    result, selection, schedules = [read(n) for n in ('RESULTS.json', 'SELECTION.json', 'SCHEDULES.json')]
    names = ('reliability', 'frozen_reliability', 'joint_mixture', 'fixed_pool', 'hybrid',
        'always', 'conservative', 'fixed_schedule', 'previous_reliability',
        'previous_frozen_reliability', 'matched_bayesian')
    fields = ('stable', 'B', 'R', 'J', 'odd_R', 'even_R')
    heldout = result['heldout_profiles']
    tables, onset_harms, decompositions = {}, {}, {}
    for label, case in result['cases'].items():
        tables[label] = {n: {k: F(case['policies'][n]['summary'][k]) for k in fields} for n in names}
        contrasts = case['comparisons']['hybrid']['worlds'][1:]
        onset_harms[label] = {k: [w['onset'] for w in contrasts if F(w[field]) > 0]
                             for k, field in [('full_worse', 'full'), ('recovery_worse', 'recovery')]}
        new = case['policies']['reliability']['summary']
        decompositions[label] = {}
        for reference in ('training_00', 'frozen_reliability', 'previous_reliability'):
            old = result['cases']['training_00']['policies']['reliability']['summary'] if reference == 'training_00' else case['policies'][reference]['summary']
            errors = F(new['stable_errors'])-F(old['stable_errors'])
            purchases = F(new['stable_purchases'])-F(old['stable_purchases'])
            difference = F(new['stable'])-F(old['stable'])
            assert difference == (errors+purchases/10)/10
            decompositions[label][reference] = dict(cost_difference=difference,
                error_difference=errors, purchase_difference=purchases)
    lower = {n: {k: sum(tables[a]['reliability'][k] < tables[a][n][k] for a in heldout)
                 for k in ('stable', 'B', 'R', 'J')} for n in names if n != 'reliability'}
    criteria = ('stable', 'always_recovery', 'hybrid_recovery')
    gate_counts = {n: {k: sum(result['cases'][a]['gates'][n][k] for a in heldout)
                      for k in criteria} for n in names}
    passing = {n: [a for a in heldout if all(result['cases'][a]['gates'][n][k] for k in criteria)] for n in names}
    mask = schedules['selected']['mask']
    summary = dict(primary_pass=result['primary_pass'], mechanism=result['mechanism'],
        passing_profiles=passing, selection=selection['selected'], feasible_vertices=len(selection['vertices']),
        fixed_schedule_tasks=[t for t in range(1, 11) if mask >> (t-1) & 1],
        fixed_schedule_mask=mask, fixed_schedule_training=schedules['selected']['training'],
        tables=tables, strict_lower_counts=lower, gate_counts=gate_counts, onset_harms=onset_harms,
        stable_cost_decompositions=decompositions,
        recovery_improvement_vs_previous={a: 1-tables[a]['reliability']['R']/tables[a]['previous_reliability']['R'] for a in heldout},
        budget_excess_fraction={a: tables[a]['reliability']['stable']/F(result['budget'])-1 for a in heldout},
        diagnostics={a: {n: result['cases'][a]['policies'][n]['summary'] for n in names} for a in heldout},
        onset_10={a: {n: result['cases'][a]['policies'][n]['worlds'][10] for n in names} for a in heldout},
        readback=readback, qualification=read('QUALIFICATION.json'), benchmark=read('BENCHMARK.json'),
        reproduction=read('REPRODUCTION.json'), main_seconds=manifest['wall_seconds'],
        sealed_bytes=sum(p.stat().st_size for p in ATTEMPT.rglob('*') if p.is_file()))
    REPORTING.mkdir(exist_ok=False)
    save(REPORTING / 'DERIVED_SUMMARY.json', summary)
    (REPORTING / 'documents').mkdir()
    for name in DOCUMENTS:
        (REPORTING / 'documents' / name).write_bytes((ROOT / name).read_bytes())
    (REPORTING / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    save(REPORTING / 'COMPLETION_PROVENANCE.json', dict(
        completed=datetime.now(timezone.utc).isoformat(), scientific_primary_pass=result['primary_pass'],
        previous_reporting_sha256=sha(BASE / 'reporting-2026-10-31' / 'COMPLETION_PROVENANCE.json'),
        presentation_correction='Constant-.4 B rounds to .095199918, not .095199917. Exact scientific outputs are unchanged; the original reporting snapshot is preserved.',
        heldout_profiles_passing=passing['reliability'], no_successor_launched=True,
        attempt=str(ATTEMPT), manifest_sha256=sha(ATTEMPT / 'MANIFEST.json'),
        readback_sha256=sha(ATTEMPT / 'READBACK.json'), candidate_freeze_sha256=sha(ATTEMPT / 'CANDIDATE_FREEZE.json'),
        reporting_preflight_failure={str(p.relative_to(BASE)): sha(p)
            for p in (BASE / 'reporting-preflight-failure-01').iterdir() if p.is_file()},
        derivation_source_sha256=sha(__file__), documents={n: sha(ROOT / n) for n in DOCUMENTS},
        outputs={str(p.relative_to(REPORTING)): sha(p) for p in REPORTING.rglob('*') if p.is_file()}))
    print(json.dumps(dict(reporting=str(REPORTING), primary_pass=result['primary_pass'],
        passing_profiles=passing['reliability'], assertions=readback['total_checks'],
        sealed_bytes=summary['sealed_bytes'], reporting_bytes=sum(p.stat().st_size for p in REPORTING.rglob('*') if p.is_file()),
        completion_sha256=sha(REPORTING / 'COMPLETION_PROVENANCE.json')), sort_keys=True))


if __name__ == '__main__':
    main()
