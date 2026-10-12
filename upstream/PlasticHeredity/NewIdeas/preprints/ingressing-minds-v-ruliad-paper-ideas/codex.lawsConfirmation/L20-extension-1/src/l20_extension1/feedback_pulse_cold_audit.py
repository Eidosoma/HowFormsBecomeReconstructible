"""D173 audit-startup addendum; preserves the frozen physics/model/benchmark.

Only installs four already pinned configuration-package roots. No production
API/context, simulator or fitter is called to initialize the independent audit.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from . import feedback_pulse_run as run

FREEZE_SHA = 'df29a9df95bf78e84a84d1645a380fd36fed21383da3a799aab663b74bc2cf16'
BENCHMARK_SHA = '72c80c5058357d30c9a980ec0ef0a34c60600929fafd196f0b359f4f8b6584b5'
PACKAGES = ('voltage_web', 'setpoint_rewrite', 'ladder_web', 'blueprint_web')
SCIENCE = ('src/l20_extension1/feedback_pulse_cold_audit.py',
           'tests/test_feedback_pulse_cold_audit.py',
           'feedback-placement-challenge/AUDIT_STARTUP_ADDENDUM_V1.md')


def support_path():
    return run.ROOT / 'logs' / (run.RUN + '_cold_audit_freeze_v1.json')


def prepare():
    assert run.io.sha256_file(run.freeze_path()) == FREEZE_SHA
    assert run.io.sha256_file(run.timing_path()) == BENCHMARK_SHA
    f = run.frozen(); run.timing()
    paths, bound = [], {}
    for package in PACKAGES:
        directory = run.WS.parent / package / 'src'
        paths.append(str(directory))
        for filename in ('__init__.py', 'config.py'):
            path = directory / package / filename
            want = f['input_sha256'][str(path)]
            assert run.io.sha256_file(path) == want
            bound[str(path)] = want
    # The child of the original detached launcher inherits this same explicit
    # environment, so it does not depend on this process's warm module cache.
    for path in reversed(paths):
        if path not in sys.path:
            sys.path.insert(0, path)
    inherited = os.environ.get('PYTHONPATH', '').split(os.pathsep)
    os.environ['PYTHONPATH'] = os.pathsep.join(dict.fromkeys(paths + [p for p in inherited if p]))
    loaded = {}
    for package in PACKAGES:
        for suffix, filename in (('', '__init__.py'), ('.config', 'config.py')):
            name = package + suffix
            module = importlib.import_module(name)
            path = Path(module.__file__).resolve()
            expected = (run.WS.parent / package / 'src' / package / filename).resolve()
            assert path == expected, 'configuration package shadowing: ' + name
            assert run.io.sha256_file(path) == bound[str(expected)]
            loaded[name] = str(path)
    return dict(passes=True, package_files=loaded, package_sha256=bound,
        pythonpath=os.environ['PYTHONPATH'], production_context_called=False,
        production_simulator_called=False, production_fitter_called=False)


def freeze(xml, fixtures):
    run.resources(); run.io.external(xml); run.io.external(fixtures)
    assert xml.parent == run.ROOT / 'logs' and xml.name == 'd173_feedback_pulse_qualification_v2_cold.xml'
    assert fixtures.parent == run.ROOT / 'tmp' and fixtures.name == xml.stem
    tree = ET.parse(xml).getroot(); cases = tree.findall('.//testcase')
    assert len(cases) >= 8 and not any(tree.findall('.//' + key) for key in ('failure', 'error', 'skipped'))
    names = {case.get('name') for case in cases}
    assert {'test_original_cold_failure', 'test_cold_imports', 'test_full_cold_saved_audit',
            'test_imports_idempotent', 'test_changed_config_fails', 'test_shadowed_config_fails'} <= names
    proof = prepare()
    files = [run.WS / 'L20-extension-1' / p for p in SCIENCE] + [xml]
    fixture_files = [p for p in fixtures.rglob('*') if p.is_file() and not p.is_symlink()]
    assert fixture_files
    result = dict(status='FROZEN_AUDIT_STARTUP_ONLY', frozen_utc=run.io.utc_now(),
        original_freeze_sha256=FREEZE_SHA, original_benchmark_sha256=BENCHMARK_SHA,
        tests=len(cases), input_sha256=run.io.hashes(files), fixture_sha256=run.io.hashes(fixture_files),
        preparation=proof, physics_changed=False, model_changed=False, benchmark_rerun=False,
        actual_development_cases_simulated=0, actual_outcome_arrays_loaded=0, automatic_successor=False)
    run.io.write_json(support_path(), result)
    return {k: v for k, v in result.items() if k not in ('input_sha256', 'fixture_sha256')}


def checked_support():
    value = run.io.read_json(support_path())
    assert value['status'] == 'FROZEN_AUDIT_STARTUP_ONLY'
    assert value['original_freeze_sha256'] == FREEZE_SHA and value['original_benchmark_sha256'] == BENCHMARK_SHA
    run.io.verify_hashes(value['input_sha256']); run.io.verify_hashes(value['fixture_sha256'])
    for name in SCIENCE:
        path = run.WS / 'L20-extension-1' / name
        assert value['input_sha256'][str(path)] == run.io.sha256_file(path)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('check', 'freeze', 'audit', 'detach-audit'))
    parser.add_argument('--xml', type=Path); parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    if args.stage == 'freeze':
        if args.xml is None or args.fixtures is None:
            parser.error('freeze requires --xml and --fixtures')
        result = freeze(args.xml, args.fixtures)
    else:
        if args.xml is not None or args.fixtures is not None:
            parser.error('qualification arguments only on freeze')
        if args.stage == 'check':
            result = prepare()
        else:
            checked_support(); prepare()
            result = run.detach('audit-benchmark') if args.stage == 'detach-audit' else run.audit_benchmark()
            checked_support()
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
