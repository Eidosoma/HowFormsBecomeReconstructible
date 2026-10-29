"""Reserve unexposed identities and bind the pre-acquisition confirmation."""
import re
import shutil
import subprocess
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from common import *
import design
import execute


def identity_pattern():
    return re.compile(r'(?<!\d)(?:'+ '|'.join(str(i) for i in BLOCKS) +r')(?!\d)')


def reserve():
    upstream=Path('/home/robert/Random-Replications/PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas')
    roots=[LANE.parent,upstream]
    command=['rg','--files','--hidden','-g','*.json','-g','*.jsonl','-g','*.py','-g','*.md','-g','*.txt',
             '-g','!**/.git/**','-g','!**/.cache/**','-g','!**/.venv/**',*[str(p) for p in roots]]
    result=subprocess.run(command,capture_output=True,text=True,check=True)
    pattern=identity_pattern();scanned={};excluded=[];collisions=[]
    for name in sorted(set(result.stdout.splitlines())):
        path=Path(name)
        if path.is_relative_to(ROOT):continue
        if path.stat().st_size>2*1024**2:excluded.append(str(path));continue
        data=path.read_bytes();scanned[str(path)]=hashlib.sha256(data).hexdigest()
        if pattern.search(str(path)) or pattern.search(data.decode(errors='replace')):collisions.append(str(path))
    value=dict(status='PASS' if not collisions else 'COLLISION',recorded_utc=now(),roots=[str(p) for p in roots],
        blocks=list(BLOCKS),numeric_match_rule='complete digit sequence',scanned_files_sha256=scanned,
        excluded_large_files=excluded,collisions=collisions,unavailable_historical_root='/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation',
        limitation='Bounded accessible metadata/code search; no independent custody or technical blinding.')
    write_json(ROOT/'RESERVATION.json',value)
    assert not collisions,collisions
    return value


def main():
    output=ROOT/'registration_attempts/v1';output.mkdir(parents=True,exist_ok=False)
    try:
        assert not (ROOT/'REGISTRATION.json').exists() and not (ROOT/'runs'/execute.PANEL).exists()
        inputs=runtime_hashes();source_check()
        qpath=ROOT/'checks'/execute.QUALIFICATION/'COMPLETE.json'
        bpath=ROOT/'runs'/execute.BENCHMARK/'COMPLETE.json'
        q,b=read_json(qpath),read_json(bpath)
        assert q['status']=='PASS' and b['status']=='COMPLETE'
        assert q['inputs']==b['inputs']==inputs
        assert q['environment']==b['environment']==execute.environment()
        verify(q['outputs']);verify(b['outputs'])
        assert b['blocks']==list(DISPOSABLE) and b['workers']==2
        forecast=b['seconds']*10*32;deadline=int(3*forecast+600)
        estimated_bytes=b['retained_bytes']*32*1.2
        assert forecast<16*3600 and deadline<48*3600
        assert estimated_bytes<execute.RUN_LIMIT
        assert shutil.disk_usage(ROOT).free>=execute.RUN_LIMIT+execute.RESERVE
        prior=LANE/'TT020';closed=read_json(prior/'CLOSEOUT.json')
        assert closed['status']=='PASS' and closed['completion_sha256']==sha(prior/'runs/audit_v1/COMPLETE.json')
        reservation=reserve()
        evidence={str(p):sha(p) for p in (qpath,bpath,ROOT/'RESERVATION.json',prior/'CLOSEOUT.json',prior/'runs/audit_v1/COMPLETE.json')}
        value=dict(study='TT021',registered_utc=now(),blocks=list(BLOCKS),inputs=inputs,evidence=evidence,
            environment=execute.environment(),cpus=b['cpus'],workers=2,numerical_threads=1,
            config=asdict(model.CONFIG),readout=asdict(model.READOUT),plan={k:asdict(v) for k,v in design.plan().items()},
            claims=design.claims(),per_claim_alpha=design.ALPHA,family_alpha=.05,primary='primary_capture_gain',
            population_units=64,records=1024,forecast_seconds=forecast,deadline_seconds=deadline,
            estimated_panel_bytes=estimated_bytes,run_byte_limit=execute.RUN_LIMIT,free_reserve=execute.RESERVE,
            prior_development_exposed=True,test_outcomes_generated=False,scientific_baseline_reuse=False,
            automatic_polling=False,automatic_retry=False,automatic_successor=False)
        write_json(ROOT/'REGISTRATION.json',value)
        write_json(output/'COMPLETE.json',dict(status='PASS',registered_utc=value['registered_utc'],registration_sha256=sha(ROOT/'REGISTRATION.json')))
        print(json.dumps(dict(status='REGISTERED',forecast_seconds=forecast,deadline_seconds=deadline,
            estimated_panel_bytes=estimated_bytes,scanned_files=len(reservation['scanned_files_sha256']),inputs=len(inputs)),sort_keys=True),flush=True)
    except BaseException as error:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
