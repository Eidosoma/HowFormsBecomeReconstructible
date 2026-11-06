"""Hash-bound reuse and accounting; the original scientific implementation is untouched."""
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


PLAN = read(ROOT / 'PLAN.json')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def science():
    source = Path(PLAN['source_inputs'])
    sys.path.insert(0, str(source))
    modules = {n: importlib.import_module('sr_' + n) for n in
               ['common', 'run', 'source', 'acquire', 'verification', 'analysis', 'scheduler']}
    need(modules['common'].ROOT.resolve() == source.resolve(), 'Wrong scientific module source')
    return modules


def verify_manifest(base, manifest, exact=False):
    base = Path(base)
    entries = manifest['sha256']
    for relative, expected in entries.items():
        rel = Path(relative)
        need(not rel.is_absolute() and '..' not in rel.parts, 'Unsafe manifest path')
        path = base / rel
        need(path.is_file() and not path.is_symlink(), 'Missing or linked committed file')
        need(path.resolve().is_relative_to(base.resolve()), 'Escaping manifest path')
        need(sha(path) == expected, 'Changed committed file: ' + relative)
    if exact:
        actual = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}
        need(actual == set(entries), 'Extra or missing source artifacts')
    return len(entries)


def remaining_budget(prior_wall, prior_target, combined=3600, target=3400):
    need(0 <= prior_target <= prior_wall < combined, 'Invalid prior charged time')
    need(prior_target < target, 'Original target allowance exhausted')
    return math.floor(min(combined - prior_wall, target - prior_target))


def timing_forecast(wave_seconds, waves=3):
    need(wave_seconds > 0 and waves == 3, 'Unexpected timing workload')
    return 180 + 1.5 * waves * wave_seconds + 180 + 120


def validate_partition(selected, imported, remaining):
    need(selected == list(range(16)), 'Original16-block cohort required')
    need(imported == list(range(4)), 'Exactly original completed blocks0..3 required')
    need(remaining == list(range(4, 16)), 'Exactly remaining blocks4..15 required')
    need(set(imported).isdisjoint(remaining) and imported + remaining == selected,
         'Repeated, omitted or substituted block')


def validate_complete_names(folder, blocks):
    folder = Path(folder)
    need({p.name for p in folder.iterdir()} == {f'n24_b{b}' for b in blocks},
         'Missing, extra or partial continuation directory')
    for block in blocks:
        unit = folder / f'n24_b{block}'
        need(not (unit / 'FAILED.json').exists(), 'Failed unit cannot be imported')
        complete = read(unit / 'COMPLETE.json')
        need(complete['status'] == 'COMPLETE_AUDITED', 'Uncommitted continuation')
        need(complete['stage'] == 'scientific' and complete['block'] == block
             and complete['injury'] == 24, 'Wrong continuation identity')


def verify_prior():
    source, old = Path(PLAN['source_inputs']), Path(PLAN['source_run'])
    bindings = [('source_input_manifest_sha256', source/'INPUTS.json'),
                ('source_protocol_sha256', source/'protocol.json'),
                ('source_stopped_manifest_sha256', Path(PLAN['source_stopped_manifest'])),
                ('source_closeout_sha256', Path(PLAN['source_closeout'])),
                ('source_failure_sha256', old/'FAILED.json'),
                ('source_qualification_sha256', old/'QUALIFICATION.json'),
                ('source_cohort_sha256', old/'COHORT.json'),
                ('source_policy_seal_sha256', old/'scientific_SEAL.json')]
    for key, path in bindings:
        need(sha(path) == PLAN[key], 'Prior binding changed: ' + key)
    ni = verify_manifest(source, read(source/'INPUTS.json'))
    no = verify_manifest(old, read(PLAN['source_stopped_manifest']), exact=True)
    need((ni, no) == (76, 503), 'Prior evidence coverage changed')
    p = read(source/'protocol.json')
    need(p['primary'] == PLAN['primary_contrast'], 'Primary scientific contrast changed')
    need((p['resource']['workers'], p['resource']['parent_reserve'], p['resource']['shared_limit'])
         == (PLAN['workers'], PLAN['parent_reserve'], PLAN['shared_thread_limit']) == (4, 1, 12),
         'Worker/resource contract changed')
    need(p['resource']['min_free_bytes'] == PLAN['minimum_free_bytes'] == 4000000000,
         'Disk reserve weakened')
    need(PLAN['maximum_combined_saved_bytes'] == p['resource']['max_saved_bytes'] == 3000000000,
         'Saved-data cap changed')
    validate_partition(PLAN['selected_blocks'], PLAN['imported_scientific_blocks'], PLAN['remaining_scientific_blocks'])
    expected_imports = ['acquisition','qualification_acquisition','qualification','COHORT.json',
        'QUALIFICATION.json','ACQUISITION_RELEASE.json','FUTURE_RELEASE.json',
        'scientific_SEAL.json','qualification_SEAL.json'] + [f'scientific/n24_b{b}' for b in range(4)]
    need(PLAN['import_paths'] == expected_imports, 'Unexpected source import set')
    validate_complete_names(old/'scientific', PLAN['imported_scientific_blocks'])
    failure = read(old/'FAILED.json')
    need(failure['traceback'].splitlines()[-1] == 'OSError: Required free disk reserve unavailable',
         'Wrong prior stopping cause')
    need(not any((old/n).exists() for n in ['COMPLETE.json', 'ANALYSIS.json', 'OUTCOMES.json']),
         'Source already has whole-panel results')
    need(failure['wall_seconds'] == PLAN['prior_wall_seconds'] and failure['capacity_wait_seconds'] == 0,
         'Prior charged work changed')
    start, release = read(old/'START.json'), read(old/'FUTURE_RELEASE.json')
    prior_target = failure['wall_seconds'] - ((release['target_deadline_epoch'] - 3400) - (start['deadline_epoch'] - 3600))
    need(abs(prior_target - PLAN['prior_target_wall_seconds']) < 1e-9, 'Prior target time omitted')
    need(PLAN['resume_hard_seconds'] == remaining_budget(failure['wall_seconds'], prior_target),
         'Changed remaining allowance')
    floor = max(read(old/'tasks/scientific_wave_0_COMPLETE.json')['wall_seconds'],
                p['resource']['historical_continuation_floor'])
    need(floor == PLAN['pricing']['guarded_wave_floor_seconds'], 'Changed timing floor')
    need(timing_forecast(floor) == PLAN['pricing']['forecast_including_all_reserves_seconds']
         and timing_forecast(floor) <= PLAN['resume_hard_seconds'], 'Remaining work does not fit')
    modules = science()
    need(modules['common'].verify_snapshot() == 76, 'Original native inputs changed')
    software = read(source/'SOFTWARE_QUALIFICATION.json')
    need(software['status'] == 'PASS' and software['tests_passed'] == 38, 'Original software unqualified')
    need(software['numpy_version'] == modules['common'].np.__version__ and software['python_version'] == sys.version,
         'Runtime differs from the original qualification')
    q = read(old/'QUALIFICATION.json')
    need(q['status'] == 'PASS' and q['binding'] == modules['common'].binding(), 'Native qualification absent')
    need(q['acquisition']['units'] == 2 and q['continuation']['units'] == 2, 'Qualification coverage differs')
    need(all(v > 0 for v in q['continuation']['policy_branch_coverage'].values()), 'Qualification branches missing')
    attempts = {}
    for block in PLAN['selected_blocks']:
        attempts[block], _ = modules['acquire'].verify(old/'acquisition'/f'b{block}', 'scientific', block)
    cohort = read(old/'COHORT.json')
    selection = modules['source'].verify_selection(attempts, cohort)
    need(cohort['complete'] and cohort['blocks'] == PLAN['selected_blocks'], 'Cohort changed')
    seal = read(old/'scientific_SEAL.json')
    need(seal['rows'] == cohort['rows'] and seal['policies'] == p['policies'], 'Policy or source seal changed')
    need(cohort['utc'] <= seal['utc'] <= release['utc'], 'Original future barrier missing')
    need(release['cohort_sha256'] == sha(old/'COHORT.json')
         and release['policy_seal_sha256'] == sha(old/'scientific_SEAL.json')
         and release['qualification_sha256'] == sha(old/'QUALIFICATION.json'), 'Original release changed')
    for block in PLAN['imported_scientific_blocks']:
        folder = old/'scientific'/f'n24_b{block}'
        unit = read(folder/'COMPLETE.json')
        need(unit['binding'] == modules['common'].binding()
             and unit['policy_seal_sha256'] == sha(old/'scientific_SEAL.json'), 'Imported unit binding differs')
        verify_manifest(folder, unit)
        audit = read(folder/'independent_AUDIT.json')
        need(audit['status'] == 'PASS' and audit['flat_reads'] == 380
             and audit['full_horizon_flat_policy_chains'] == 20, 'Full native/flat audit absent')
    return dict(status='PASS', utc=stamp(), original_input_files=ni, original_output_files=no,
                original_software_checks=38, selected_packets=selection['selected_packets'],
                imported_scientific_blocks=PLAN['imported_scientific_blocks'],
                remaining_scientific_blocks=PLAN['remaining_scientific_blocks'],
                native_qualification_reused=True, new_native_reads=0,
                prior_wall_seconds=PLAN['prior_wall_seconds'], resume_hard_seconds=PLAN['resume_hard_seconds'])


def import_sources(run):
    run = Path(run)
    old = Path(PLAN['source_run'])
    for relative in PLAN['import_paths']:
        source, target = old/relative, run/relative
        need(not target.exists(), 'Import would overwrite evidence')
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)
    manifest = read(PLAN['source_stopped_manifest'])['sha256']
    expected = {r: d for r, d in manifest.items()
                if any(r == base or r.startswith(base + '/') for base in PLAN['import_paths'])}
    verify_manifest(run, {'sha256': expected})
    return dict(status='PASS', utc=stamp(), source_run=str(old), files=len(expected), sha256=expected,
                copied_bytes=sum((run/r).stat().st_size for r in expected), new_native_reads=0)


def verify_controller():
    manifest = read(ROOT/'INPUTS.json')
    count = verify_manifest(ROOT, manifest)
    software = read(ROOT/'SOFTWARE_QUALIFICATION.json')
    need(software['status'] == 'PASS' and software['new_native_reads'] == 0, 'Resume controller unqualified')
    for relative, expected in software['source_sha256'].items():
        need(sha(ROOT/relative) == expected, 'Controller changed after qualification')
    return count


def cpu_receipt():
    ref = Path(PLAN['source_inputs'])/'native/inherited/reference'
    sys.path.insert(0, str(ref))
    spec = importlib.util.spec_from_file_location('resume_cpu_admission', ref/'cpu_preflight.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.collect()


def disk_check(run=None):
    old = Path(PLAN['source_run'])
    prior_bytes = sum(p.stat().st_size for p in old.rglob('*') if p.is_file())
    new_bytes = sum(p.stat().st_size for p in Path(run).rglob('*') if p.is_file()) if run else 0
    need(prior_bytes + new_bytes <= PLAN['maximum_combined_saved_bytes'], 'Combined saved-data cap exceeded')
    free = shutil.disk_usage(ROOT).free
    need(free >= PLAN['minimum_free_bytes'], 'Required free disk reserve unavailable')
    if run is None:
        need(free >= PLAN['minimum_free_bytes'] + PLAN['maximum_combined_saved_bytes'] - prior_bytes,
             'Insufficient room for reserve plus complete saved-data allowance')
    return dict(utc=stamp(), free_bytes=free, prior_run_bytes=prior_bytes, new_run_bytes=new_bytes,
                combined_saved_bytes=prior_bytes+new_bytes, minimum_free_bytes=PLAN['minimum_free_bytes'])


def report_budget_note(text, resumed_seconds):
    old = 'Qualification and the target share one absolute3600-second budget. No automatic retries, sample/budget extensions or successor studies.'
    need(text.count(old) == 1, 'Original report resource wording changed')
    return text.replace(old,
        'Resource resume1: original absolute deadlines expired and remain recorded. '
        f'Prior run {PLAN["prior_wall_seconds"]:.6f}s + resumed run at report generation {resumed_seconds:.6f}s '
        f'= {PLAN["prior_wall_seconds"]+resumed_seconds:.6f}s charged so far. '
        f'The new resumed deadline is fixed at {PLAN["resume_hard_seconds"]}s; both the3600-second total '
        'and3400-second target run-duration allowances are preserved. Final durations are in COMPLETE.json. '
        'Elapsed calendar pause and preparation/closeout are excluded and reported separately. '
        'The original16-block cohort and four completed continuations are retained. '
        'Original native qualification and38-check software qualification are reused under unchanged science hashes. '
        'Only orchestration has new software tests. Prior20904 full readers +9120 new =30024 total. '
        'No automatic retries, further resumes, sample changes or successor studies.')
