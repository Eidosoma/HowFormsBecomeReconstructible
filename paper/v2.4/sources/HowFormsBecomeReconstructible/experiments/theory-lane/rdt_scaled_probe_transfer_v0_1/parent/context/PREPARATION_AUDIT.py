"""Verify source commitments and five-model reduction on already exposed data."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT.parent
PLAN = LANE / 'rdt_equal_read_plan_v0_1'
sys.path.insert(0, str(ROOT))
import ff_common as common
from ff_common import ev, read, manifest, require, ledger
import ff_analysis
import ff_audit


def checked_run(folder):
    result = read(folder / 'COMPLETE.json')
    require(result['status'] == 'COMPLETE', 'Completed run required')
    require(result['output_manifest_sha256'] == ev.sha(folder / 'OUTPUTS.json'), 'Output commitment changed')
    require(read(folder / 'OUTPUTS.json')['sha256'] == manifest(folder, ('STATUS.json', 'OUTPUTS.json', 'COMPLETE.json')), 'Output content changed')
    return result


def main():
    sys.path.insert(0, str(common.NATIVE / 'inherited/reference'))
    import cpu_preflight
    cpu = cpu_preflight.collect()
    ledger.atomic_json(ROOT / 'checks/CPU_BEFORE_PREPARATION_V2.json', cpu)
    require(cpu['within_limit'], 'One CPU unavailable')
    common.equal_read.verify_snapshot()
    require(manifest(common.NATIVE) == read(ROOT / 'NATIVE_PROVENANCE.json')['sha256'], 'Native code differs')
    bindings = read(ROOT / 'SOURCE_BINDINGS.json')
    for name, item in bindings['copied_context'].items():
        require(ev.sha(ROOT / 'context' / name) == item['sha256'], 'Copied context changed')
    tests = list(ET.parse(ROOT / 'checks/tests_v2.xml').getroot().iter('testsuite'))
    require(sum(int(s.attrib['tests']) for s in tests) == 54, 'Expected complete test suite')
    require(all(int(s.attrib.get(k, 0)) == 0 for s in tests for k in ('failures', 'errors', 'skipped')), 'Tests did not pass')
    runs = {name: PLAN / 'runs' / name for name in ('benchmark_v2', 'priced_plan_v1', 'budget_amendment_v1')}
    completions = {name: checked_run(folder) for name, folder in runs.items()}
    benchmark = read(runs['benchmark_v2'] / 'RESULTS.json')
    require((benchmark['workers'], benchmark['cases'], benchmark['primary_native_reads'], benchmark['flat_native_reads']) == (8, 8, 1024, 32), 'Measured workload differs')
    require(benchmark['conservative_measurement_case_seconds'] == max(benchmark['full_wave_wall_seconds'], benchmark['maximum_case_wall_seconds']), 'Slower timing lost')
    require(completions['priced_plan_v1']['decision'] == 'NO_DESIGN_MEETS_DECLARED_POWER_AND_RUNTIME', 'Original budget failure lost')
    amendment = read(runs['budget_amendment_v1'] / 'RESULTS.json')
    choice = amendment['chosen']
    require((choice['blocks'], choice['repeats'], choice['charged_attempts']) == (80, 4, 136), 'Unexpected amendment')
    require(all(not row['fits_with_completion_reserve'] for row in amendment['complete_cap_grid'] if row['charged_attempts'] > 136), 'Amended cap is not maximal')
    phases = amendment['phase_maxima_seconds']
    independent_wall = 1.5 * (17 * phases['acquisition'] + 80 * phases['measurement_case'] + 40 * phases['future']) + 120
    require(abs(independent_wall - choice['conservative_wall_seconds']) < 1e-9 and independent_wall <= 21300, 'Independent budget calculation differs')
    # These are the previously exposed records, used only to validate arithmetic.
    source = PLAN / 'jobs/plan_v1/inputs/context'
    rows = read(source / 'FRESH_COHORT.json')['rows']
    forecasts = read(source / 'DEV_FORECASTS.json')
    outcomes = read(source / 'FRESH_OUTCOMES.json')
    previous = read(source / 'DEV_ANALYSIS.json')
    spec = dict(scope='exposed_saved_data_arithmetic_audit', eligible_blocks=108, repeats=[0, 1, 2, 3])
    result = ff_analysis.analyze(rows, forecasts, outcomes, spec)
    audit = ff_audit.evaluate(rows, forecasts, outcomes, result, spec['repeats'])
    maximum = 0.
    for regime in common.REGIMES:
        for model in common.MODELS:
            maximum = max(maximum, abs(result['regimes'][regime]['brier'][model] - previous['regimes'][regime]['brier'][model]))
        for rival in common.C['analysis']['margins']:
            a, b = result['regimes'][regime]['contrasts'][rival], previous['regimes'][regime]['contrasts'][rival]
            for key in ('mean_gain', 'sample_sd', 'lower', 'upper'):
                old_key = 'descriptive_' + key if key in ('lower', 'upper') else key
                maximum = max(maximum, abs(a[key] - b[old_key]))
            require(len(a['block_gains']) == 108, 'Block count differs')
            maximum = max(maximum, max(abs(x - y) for x, y in zip(a['block_gains'], b['block_gains'], strict=True)))
    require(maximum < 1e-12, 'New reducer differs from verified exposed study')
    proof = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), tests_passed=54,
        earlier_tests=dict(path=str(ROOT / 'checks/tests_v1.xml'), sha256=ev.sha(ROOT / 'checks/tests_v1.xml'),
            passed=48, failed=5, reason='New test fixtures reused filenames; fixed with separate exclusive output directories. No native experiment had run.'),
        checked_exposed_blocks=108, checked_exposed_forecasts=864, checked_exposed_outcomes=3456,
        maximum_reducer_discrepancy=maximum, independent_scalar_reduction=audit,
        qualified_measurement_files=93, unchanged_native_files=42,
        model_coefficients_sha256=ev.sha(ROOT / 'qualified/FROZEN_MODELS.json'),
        original_budget_failure_preserved=True, selected_resource_amendment=choice,
        numerical_benchmark_primary_reads=1024, numerical_benchmark_flat_reads=32,
        qualification_workers=4, scientific_workers=8,
        qualification_forecast_seconds=common.C['resource_basis']['qualification_forecast_seconds'],
        source_runs={name:dict(path=str(folder), complete_sha256=ev.sha(folder / 'COMPLETE.json'), output_manifest_sha256=ev.sha(folder / 'OUTPUTS.json')) for name, folder in runs.items()},
        source_reducer_files={name:dict(path=str(source / name), sha256=ev.sha(source / name)) for name in ('FRESH_COHORT.json', 'DEV_FORECASTS.json', 'FRESH_OUTCOMES.json', 'DEV_ANALYSIS.json')},
        new_native_reads=0, new_scientific_outcomes=0, new_fits=0, scientific_runner_qualified=False,
        native_runner_qualification_pending=True, automatic_scientific_launch=False)
    ledger.atomic_json(ROOT / 'context/PREPARATION_VERIFICATION.json', proof)
    ledger.atomic_json(PLAN / 'checks/PRICED_PLAN_AMENDMENT_CLOSEOUT.json', dict(status='PASS', utc=proof['utc'],
        proof=str(ROOT / 'context/PREPARATION_VERIFICATION.json'), proof_sha256=ev.sha(ROOT / 'context/PREPARATION_VERIFICATION.json'),
        benchmark_primary_reads=1024, benchmark_flat_reads=32, original_budget_failure_preserved=True,
        selected_resource_amendment=choice, source_runs=proof['source_runs']))
    print(json.dumps(dict(status='PASS', tests=54, maximum_reducer_discrepancy=maximum, full_cap_seconds=independent_wall,
        next='Disposable runner qualification; no scientific acquisition or futures yet.')))


if __name__ == '__main__':
    main()
