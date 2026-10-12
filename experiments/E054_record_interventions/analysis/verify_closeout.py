"""Verify retained E054 evidence and emit one immutable closeout receipt."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, sha, utc
from E015_functional_inheritance.audit import verify


def read(path):
    return json.loads(path.read_text())


def main(figure_inspected):
    assert figure_inspected, 'Inspect the scientific figure before closeout'
    cap_cpus(1)
    destination = HERE / 'analysis/closeout_v1.json'
    assert not destination.exists(), 'Preserve the existing closeout receipt'
    frozen = read(HERE / 'analysis/freeze_v1/manifest.json')['inputs_sha256']
    check_inputs(HERE / 'analysis/freeze_v1')
    assert len(frozen) == 24
    evidence = {}
    runs = {}
    for name, blocks, observations in (
        ('fixture_v1', 1, 2640), ('benchmark_v1', 1, 1320),
        ('interventions_v1', 32, 168960),
    ):
        run = HERE / 'runs' / name
        manifest = verify(run)
        complete = read(run / 'COMPLETE.json')
        audit = read(run / 'INDEPENDENT_AUDIT.json')
        summary = read(run / 'summary.json')
        assert manifest['inputs_sha256'] == frozen
        assert len(manifest['contract']['blocks']) == blocks
        assert complete['blocks_completed'] == summary['independent_blocks'] == blocks
        assert len(complete['outputs_sha256']) == 6 * blocks + 27
        assert audit['status'] == 'PASS'
        assert audit['complete_sha256'] == sha(run / 'COMPLETE.json')
        assert audit['audit_code_sha256'] == sha(HERE / 'audit.py')
        assert audit['all_source_interventions_graphs_couplings_trajectories_scores_replayed']
        assert audit['summaries_checked'] == len(summary['statistics']) == 1632
        assert audit['terminal_cue_observations'] == observations
        assert audit['controls_pass'] and summary['controls_pass']
        assert all(c['pass'] for c in summary['controls_by_block'])
        assert summary['cohort_reused'] is True
        if name == 'interventions_v1':
            assert manifest['contract']['blocks'] == list(range(34000, 34032))
            assert summary['status'] == 'MECHANISTIC_FOLLOWUP'
            scientific_summary = summary
        else:
            assert summary['status'] == 'TECHNICAL_ONLY'
            assert all(v is None for v in summary['primary_classifications'].values())
        job = HERE / 'jobs' / name
        check_inputs(job)
        job_manifest = read(job / 'manifest.json')
        assert job_manifest['inputs_sha256'] == frozen
        for rel, digest in job_manifest['contract']['predecessor_evidence'].items():
            assert sha(ROOT / rel) == digest, rel
        status = read(job / 'status.json')
        assert status['status'] == 'COMPLETE'
        assert status['complete_sha256'] == sha(run / 'COMPLETE.json')
        assert status['audit_sha256'] == sha(run / 'INDEPENDENT_AUDIT.json')
        figure = HERE / 'figures' / name / 'provenance.json'
        provenance = read(figure)
        assert provenance['audit_sha256'] == sha(run / 'INDEPENDENT_AUDIT.json')
        assert provenance['summary_sha256'] == sha(run / 'summary.json')
        assert provenance['plot_code_sha256'] == sha(HERE / 'plot.py')
        for rel, digest in provenance['outputs_sha256'].items():
            assert sha(figure.parent / rel) == digest, rel
        for path in (run / 'COMPLETE.json', run / 'INDEPENDENT_AUDIT.json',
                     run / 'summary.json', figure, job / 'status.json'):
            evidence[str(path.relative_to(ROOT))] = sha(path)
        runs[name] = dict(original_outputs_verified=len(complete['outputs_sha256']),
                          summaries_verified=audit['summaries_checked'],
                          terminal_cue_observations=observations, status=summary['status'])
    ready = read(HERE / 'analysis/technical_v1.json')
    assert ready['status'] == 'PASS' and ready['inputs_sha256'] == frozen
    for rel, digest in ready['evidence_sha256'].items():
        assert sha(ROOT / rel) == digest, rel
    source = read(HERE / 'SOURCE_DATA.json')
    assert sha(ROOT / source['closeout']) == source['closeout_sha256']
    source_files = 0
    for panel in source['sources'].values():
        for rel, digest in panel['receipts'].items():
            assert sha(ROOT / rel) == digest, rel
        for rel, digest in panel['files'].items():
            assert sha(ROOT / panel['path'] / rel) == digest, rel
            source_files += 1
    result = dict(
        status='PASS', utc=utc(), experiment='E054', runs=runs,
        evidence_sha256=evidence, frozen_inputs_verified=len(frozen),
        original_source_files_verified=source_files, figure_inspected=True,
        controls_pass=scientific_summary['controls_pass'],
        primary_classifications=scientific_summary['primary_classifications'],
        cohort_reused=True, code_sha256=sha(Path(__file__)),
        scientific_retained_bytes=sum(p.stat().st_size for p in
                                     (HERE / 'runs/interventions_v1').rglob('*') if p.is_file()),
        free_bytes=shutil.disk_usage(HERE).free, automatic_successor_started=False,
    )
    with destination.open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure-inspected', action='store_true')
    main(parser.parse_args().figure_inspected)
