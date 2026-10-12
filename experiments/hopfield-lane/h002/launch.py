"""Launch the frozen H002 development specification detached, without polling."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parent.parent


def main():
    out=ROOT/'runs/h002_development_v1'
    launch=ROOT/'runs/h002_development_v1_launch.json'
    log=ROOT/'runs/h002_development_v1.log'
    pid=ROOT/'runs/h002_development_v1.pid'
    if any(path.exists() for path in [out,launch,log,pid]):
        raise FileExistsError('Refusing to reuse a campaign destination')
    benchmark=json.loads((ROOT/'runs/h002_benchmark_v2/STATUS.json').read_text())
    audit=json.loads((ROOT/'runs/h002_benchmark_v2/audit.json').read_text())
    if benchmark['state']!='COMPLETE' or not audit['passed']:
        raise RuntimeError('Engineering benchmark did not pass')
    python=os.environ.get('FORMS_PYTHON', str(ROOT/'../../../PlasticHeredity/replicators.13.8.2026.codex/.venv/bin/python'))
    command=['bash',str(ROOT/'run_python.sh'),str(ROOT/'h002/experiment.py'),
             '--mode','development','--output',str(out)]
    names=['model.py','run.py','run_python.sh','h002/experiment.py','h002/analysis.py','h002/audit.py','h002/PROTOCOL.md','h002/launch.py']
    ledger={'state':'PREPARED','created_utc':datetime.now(timezone.utc).isoformat(),
        'command':command,'output':str(out),'log':str(log),'workers':1,'numerical_threads':1,
        'mode':'development','seeds':list(range(12000,12024)),'generations':16,
        'support':[8,4],'retention':[0.,.5],'damage_probability':.5,'python':str(Path(python).resolve()),
        'forecast_seconds':benchmark['elapsed_seconds']*24*8,
        'forecast_method':'Conservative linear scaling of complete 1-block / 2-replacement benchmark, including one-time plotting and all audits. No outcome-based sizing.',
        'policy':'../RUN_POLICY.md: detached above 600 seconds; no automatic status polling.',
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}}
    launch.write_text(json.dumps(ledger,indent=2)+'\n')
    with log.open('xb') as stream:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,
                                 stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    pid.write_text(str(process.pid)+'\n')
    ledger.update(state='LAUNCHED',pid=process.pid)
    launch.write_text(json.dumps(ledger,indent=2)+'\n')
    print(json.dumps({'state':'LAUNCHED','pid':process.pid,'log':str(log),
                      'status':str(out/'STATUS.json'),'forecast_minutes':ledger['forecast_seconds']/60}))


if __name__=='__main__':
    main()
