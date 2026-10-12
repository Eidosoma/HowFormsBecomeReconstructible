"""Read-only D173 qualification closeout; no fitting, simulation or array loading."""
import argparse
import json
from pathlib import Path
import re
from l20_extension1 import feedback_pulse_run as run, feedback_pulse_cold_audit as cold

HERE = Path(__file__).resolve().parent
PINS = {
    run.freeze_path(): 'df29a9df95bf78e84a84d1645a380fd36fed21383da3a799aab663b74bc2cf16',
    run.timing_path(): '72c80c5058357d30c9a980ec0ef0a34c60600929fafd196f0b359f4f8b6584b5',
    cold.support_path(): '1b96a51479725e5cd9b1ed98f8b6879b9c0d0126d8a5389c2b25b186be81af56',
    run.audit_path(): '86f26d7abf18a370f50f4d8214b859d025b1bd20d1f322d6533428df20fc8e8a',
}


def review():
    for path, digest in PINS.items():
        assert run.io.sha256_file(path) == digest
    frozen, timing, support = run.frozen(), run.timing(), cold.checked_support()
    audit = run.io.read_json(run.audit_path())
    assert audit['passes'] and audit['physical']['full_physics_replayed']
    assert audit['freeze_sha256'] == PINS[run.freeze_path()] and audit['benchmark_sha256'] == PINS[run.timing_path()]
    assert not audit['production_simulator_called'] and not audit['production_fitter_called']
    assert audit['actual_outcome_arrays_loaded'] == audit['actual_development_cases_simulated'] == 0
    assert len(frozen['input_sha256']) == 133 and frozen['qualification']['tests'] == 92 and support['tests'] == 8
    assert not support['physics_changed'] and not support['model_changed'] and not support['benchmark_rerun']
    rows = run.io.read_json(run.benchmark_dir() / 'disposable_514240.json')
    assert rows['index'] == 514240 and len(rows['lives']) == len(rows['proofs']) == 4
    assert all(p['full_physics_replayed'] and p['passes'] for p in rows['proofs'])
    assert sum(p['original_U1_reproductions'] for p in rows['proofs']) == 16
    assert audit['physical']['maximum_state_residual'] == 0
    assert audit['physical']['writer_paths'] == 32 and audit['physical']['reader_paths'] == 64
    assert audit['synthetic'] == timing['synthetic'] and timing['synthetic_fits'] == 192
    assert timing['synthetic']['fits']['models_checked'] == 192
    expected_budget = 32 * timing['physical_seconds'] + 2 * timing['synthetic_seconds'] + 4 * timing['source_hash_seconds'] + 120
    assert expected_budget == timing['conservative_development_and_audit_budget_seconds'] and expected_budget > 600
    files = [p for p in run.artifact_files() if '_documentation_' not in p.name]
    total = sum(p.stat().st_size for p in files)
    assert len(files) == 32 and total == 5652380
    reservation = timing['projected_aggregate_bytes'] + total - timing['retained_bytes_before_timing_receipt']
    assert reservation == 175438698 and reservation < run.ALLOWANCE
    report = (HERE / 'QUALIFICATION.md').read_text()
    for value in ('92', '8', '133', '4,454,175', '5,652,380', '988.39', '16.47', '175,438,698', '167.31',
                  f"{timing['seconds']:.2f}", f"{audit['seconds']:.2f}"):
        assert value in report, 'missing report fact: ' + value
    links = 0
    for filename in ('QUALIFICATION.md', 'README.md', 'WORKLOG.md', 'AUDIT_STARTUP_ADDENDUM_V1.md'):
        path = HERE / filename
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent / target.split('#')[0]).resolve().is_file()
                links += 1
    return dict(passes=True, checked_utc=run.io.utc_now(),
        anchor_sha256={str(p): digest for p, digest in PINS.items()},
        original_inputs=133, original_tests=92, supplemental_cold_tests=8,
        retained_artifact_sha256=run.io.hashes(files), retained_files_before_documentation_receipt=32,
        retained_bytes_before_documentation_receipt=total, conservative_budget_seconds=expected_budget,
        adjusted_reservation_bytes_before_documentation_receipt=reservation, local_links_checked=links,
        documentation_sha256=run.io.hashes([HERE / 'QUALIFICATION.md', Path(__file__)]),
        actual_development_cases_simulated=0, new_real_fits=0, actual_outcome_arrays_loaded=0,
        closeout_simulations=0, closeout_fits=0, prospective_evidence=False, automatic_successor=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    result = review()
    if args.receipt:
        assert args.receipt == run.ROOT / 'logs' / (run.RUN + '_documentation_v1.json')
        run.io.write_json(args.receipt, result)
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
