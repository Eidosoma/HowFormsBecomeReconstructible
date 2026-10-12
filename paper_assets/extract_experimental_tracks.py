#!/usr/bin/env python3
"""Package the v0.12 selection and copy native summaries; run no model or inference."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
IDEAS = WORKSPACE / 'PlasticHeredity/NewIdeas/preprints'
BRANCH = IDEAS / 'ingressing-minds-v-ruliad-paper-ideas'
L20 = BRANCH / 'codex.lawsConfirmation/L20-extension-1'
CELL = BRANCH / 'levin-cancer-gj-exploration'
FEP = IDEAS / 'fep-ideas'
EXTERNAL = Path('/mnt/bioIce1')
RUNS = [
    'E013_wiring_replication/runs/prediction_v1',
    'E013_wiring_replication/runs/evaluation_v1',
    'E014_long_renewal/runs/confirmation_v2',
    'E015_functional_inheritance/runs/feasibility_v1',
    'E016_teaching_consistency/runs/comparison_v1',
    'E017_reader_timing/runs/timing_v1',
    'E018_functional_renewal/runs/renewal_v1',
    'E019_capture_timing/runs/timing_v1',
    'E020_serial_capture/runs/renewal_v1',
    'E021_damaged_renewal/runs/damage_v1',
    'E022_reader_compensation/runs/compensation_v1',
]
L20_SUBS = [
    'stopping-time', 'packet-placement', 'competing-component',
    'recovery-prediction', 'targeted-prediction', 'group-sensitive-prediction',
    'matched-regularization', 'one-copy-baseline', 'mean-compression',
    'future-stability', 'target-averaging', 'training-influence', 'reading-components',
]
CELL_STUDIES = ['LINEAGE_RETURN', 'TISSUE_PERSISTENCE', 'TISSUE_DEPENDENCE', 'TURNOVER_LIMIT']
FEP_STUDIES = [
    'READER_PRESERVATION', 'RECORD_DEPENDENT_READER', 'READER_EVIDENCE',
    'CALIBRATION_TRANSFER', 'TRANSFER_CONTINUATION', 'HIDDEN_PREFERENCES',
    'VIABILITY_PREFERENCES', 'STRUCTURED_INFERENCE', 'DECISION_BOUNDARY',
    'LOCAL_RISK_BOUND', 'SIGNED_RISK_BOUND', 'LOCAL_RISK_CORRECTION',
    'DECISION_REGRET', 'SAFE_CAP_RELEASE',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    sources = {}
    checks = []
    unavailable = []
    payload = {'selection': 'v0.12 / 20 September 2026', 'experiments': {}, 'l20': {}, 'fep': {}}

    def add(path, expected=None, required=True):
        path = Path(path)
        if not path.is_file():
            unavailable.append(str(path))
            if required:
                raise FileNotFoundError(path)
            return None
        data = path.read_bytes()
        actual = sha(data)
        if expected is not None:
            checks.append({'path': str(path), 'expected': expected, 'actual': actual, 'passed': actual == expected})
            if actual != expected:
                raise ValueError(f'Frozen source mismatch: {path}')
        try:
            member = 'workspace/' + str(path.relative_to(WORKSPACE))
        except ValueError:
            member = 'external/' + str(path.relative_to(EXTERNAL))
        sources[member] = {'path': str(path), 'bytes': len(data), 'sha256': actual, 'data': data}
        return json.loads(data) if path.suffix == '.json' else data

    for rel in RUNS:
        run = ROOT/'experiments'/rel
        complete = add(run/'COMPLETE.json')
        audit = add(run/'INDEPENDENT_AUDIT.json')
        add(run/'COMPLETE.json', audit['complete_sha256'])
        manifest = add(run/'manifest.json')
        for name in ['REPORT.md', 'summary.json']:
            if name not in complete['outputs_sha256'] and rel.endswith('/prediction_v1'):
                continue
            value = add(run/name, complete['outputs_sha256'][name])
            if name == 'summary.json':
                payload['experiments'][rel] = value
        for name, expected in manifest.get('inputs_sha256', {}).items():
            path = run/'inputs'/name
            if path.suffix in {'.md', '.json', '.py', '.txt', '.yaml', '.yml'}:
                add(path, expected)
            elif not path.is_file():
                unavailable.append(str(path))
        add(ROOT/'experiments'/rel.split('/')[0]/'PROTOCOL.md')

    for sub in L20_SUBS:
        for name in ['RESULTS.md', 'PROTOCOL_V1.md']:
            add(L20/sub/name)
    external_l20 = EXTERNAL/'PlasticHeredity/codex.lawsConfirmation/L20-extension-1'
    for run_id in ['l20_extension1_competing_component_v1_attempt1',
                   'l20_extension1_reading_components_dev_v1_attempt1']:
        complete = add(external_l20/'runs'/run_id/'COMPLETE.json')
        add(external_l20/'runs'/run_id/'MANIFEST.json', complete.get('manifest_sha256'))
        output = external_l20/'outputs'/run_id
        payload['l20'][run_id] = add(output/'summary.json', complete.get('summary_sha256'))
        add(output/'verification.json')
        add(output/'output_hashes.sha256')

    for study in CELL_STUDIES:
        for kind in ['RESULTS', 'PROTOCOL']:
            add(CELL/f'PAPER_{study}_{kind}.md')

    for study in FEP_STUDIES:
        add(FEP/f'FEP_{study}_V1_REPORT.md')
        add(FEP/f'FEP_{study}_V1.md', required=False)
    for name in ['FEP_READER_PRESERVATION_REVIEW_2026-09-18.md',
                 'FEP_CALIBRATION_TRANSFER_REVIEW_2026-09-18.md',
                 'FEP_TRANSFER_CONTINUATION_REVIEW_2026-09-19.md',
                 'FEP_STRUCTURED_INFERENCE_TEST_DESIGN_V1.md',
                 'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json']:
        add(FEP/name)
    for study, attempt in [
        ('record-dependent-reader', 'attempt-01'), ('reader-evidence', 'attempt-01'),
        ('calibration-transfer', 'attempt-01'), ('transfer-continuation', 'attempt-01'),
        ('hidden-preferences', 'attempt-01'), ('viability-preferences', 'attempt-01'),
        ('structured-inference', 'main-attempt-01'), ('safe-cap-release', 'attempt-01'),
    ]:
        run = EXTERNAL/f'fep-ideas/formal-checks/fep-{study}-v1'/attempt
        add(run/'MANIFEST.json')
        result = add(run/'RESULTS.json')
        payload['fep'][study] = result
        for name in ['SPECIFICATION.md', 'CHECKER_SOURCE.py', 'CORE.json']:
            if (run/name).is_file():
                add(run/name)

    # Native probabilities and intervals are copied unchanged. Only display units
    # (probability -> percent) are converted when generating the measured table.
    table = []
    for rel, horizon, condition in [
        ('E020_serial_capture/runs/renewal_v1', '3', 'renewed'),
        ('E021_damaged_renewal/runs/damage_v1', '3', 'renewed'),
        ('E022_reader_compensation/runs/compensation_v1', '1', 'baseline'),
        ('E022_reader_compensation/runs/compensation_v1', '1', 'strength_compensated'),
    ]:
        group = payload['experiments'][rel]['groups'][horizon][condition]['both_cues']
        table.append({'run': rel, 'replacements': int(horizon), 'condition': condition,
                      'intact': group['intact']['own'], 'scattered': group['scattered']['own']})
    payload['functional_table'] = table
    payload['interpretation'] = {
        'native_units_retained': True, 'new_statistics': False,
        'cellular': 'P13-P16 retained reports/protocols only; no new raw-history verification.',
        'fep': 'Exact finite calculations and selected saved-belief evaluations, not independent tissue observations.',
        'excluded_outcomes': ['E023', 'P17', 'later unreviewed follow-ups'],
    }

    for name in ['EXPERIMENTAL_TRACKS_REVIEW_2026-09-20.md',
                 'EXPERIMENTAL_TRACKS_REVIEW_CHECKS_2026-09-20.json']:
        add(ROOT/'reviews'/name)
    out = ROOT/'paper_assets/data/experimental-tracks-v0.12.json'
    out.write_text(json.dumps(payload, indent=2)+'\n')
    archive = ROOT/'paper_assets/data/experimental-tracks-v0.12-source-records.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for member, item in sorted(sources.items()):
            z.writestr(member, item['data'])
    with zipfile.ZipFile(archive) as z:
        for member, item in sources.items():
            if sha(z.read(member)) != item['sha256']:
                raise ValueError(f'Archive readback mismatch: {member}')
    record = {
        'version': 'v0.12', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Explicit 20 September reviewed selection; text/metadata source package, not a standalone runnable dependency/raw-data archive.',
        'experiment_runs': RUNS, 'l20_studies': list(range(147,160)),
        'cellular_studies': ['P13','P14','P15','P16'], 'fep_studies': FEP_STUDIES,
        'model_or_inference_runs_performed': False, 'statistics_recomputed': False,
        'source_files': [{k:v for k,v in item.items() if k != 'data'} | {'archive_member': member}
                         for member,item in sorted(sources.items())],
        'source_checks': checks, 'unavailable': sorted(set(unavailable)),
        'data': {'path': str(out.relative_to(ROOT)), 'sha256': sha(out.read_bytes())},
        'archive': {'path': str(archive.relative_to(ROOT)), 'bytes': archive.stat().st_size,
                    'sha256': sha(archive.read_bytes()), 'roundtrip_verified': True},
        'extractor_sha256': sha(Path(__file__).read_bytes()),
    }
    (ROOT/'reviews/V0.12_SOURCES.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'source_files': len(sources), 'hash_checks': len(checks),
                      'unavailable': record['unavailable'], 'archive_bytes': archive.stat().st_size,
                      'functional_table': [{**r, 'intact': r['intact']['mean'],
                                            'scattered': r['scattered']['mean']} for r in table]}))


if __name__ == '__main__':
    main()
