"""Cold-process regression for the D173 independent-auditor import dependency."""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from l20_extension1 import feedback_pulse_cold_audit as cold


def child(code):
    env = dict(os.environ, PYTHONPATH='L20-extension-1/src:src')
    return subprocess.run([sys.executable, '-c', code], cwd=cold.run.WS, env=env,
        capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def test_original_cold_failure(tmp_path):
    result = child('from l20_extension1.feedback_pulse_run import audit_benchmark; audit_benchmark()')
    assert result.returncode != 0 and "No module named 'voltage_web'" in result.stderr
    cold.run.io.write_json(tmp_path / 'original_failure.json', dict(returncode=result.returncode,
        stdout=result.stdout, stderr=result.stderr, original_failure_reproduced=True))


def test_cold_imports():
    result = child('from l20_extension1.feedback_pulse_cold_audit import prepare; print(prepare()["passes"])')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'True'


def test_full_cold_saved_audit(tmp_path):
    output = str(tmp_path / 'independent_cold_audit.json')
    code = f'''
from pathlib import Path
from l20_extension1 import feedback_pulse_cold_audit as cold
run=cold.run
def forbid(*args,**kwargs): raise AssertionError('production entry point used by independent cold audit')
for name in ('context','api','write_streams','read_selected','route','generator'):
    setattr(run.pulse.old,name,forbid)
for name in ('applied','write_streams','simulate_life','cycle'):
    setattr(run.pulse,name,forbid)
for name in ('fit_observer','synthetic_panel','summarize'):
    setattr(run.model,name,forbid)
run.model.ridge.fit=forbid
run.model.tied.fit=forbid
cold.prepare()
run.audit_path=lambda:Path({output!r})
result=run.audit_benchmark()
assert result['passes'] and result['physical']['full_physics_replayed']
assert result['physical']['writer_paths']==32 and result['synthetic']['fits']['models_checked']==192
print('cold independent audit passed')
'''
    result = child(code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'cold independent audit passed'
    assert cold.run.io.read_json(Path(output))['passes']


def test_imports_idempotent():
    result = child('from l20_extension1.feedback_pulse_cold_audit import prepare; a=prepare(); b=prepare(); assert a==b; print("ok")')
    assert result.returncode == 0, result.stderr


def test_changed_config_fails(monkeypatch):
    original = cold.run.io.sha256_file
    def changed(path):
        return '0' * 64 if str(path).endswith('/voltage_web/config.py') else original(path)
    monkeypatch.setattr(cold.run.io, 'sha256_file', changed)
    with pytest.raises(AssertionError): cold.prepare()


def test_shadowed_config_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, 'voltage_web', SimpleNamespace(__file__='/tmp/untrusted-config.py'))
    with pytest.raises(AssertionError): cold.prepare()


@pytest.mark.parametrize('stage', ['execute', 'benchmark'])
def test_no_new_experiment_stage(monkeypatch, stage):
    monkeypatch.setattr(sys, 'argv', ['feedback_pulse_cold_audit', stage])
    with pytest.raises(SystemExit) as error: cold.main()
    assert error.value.code == 2
