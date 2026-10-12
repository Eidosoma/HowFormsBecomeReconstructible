"""Write-once D163 saved-data accounting and separately invoked saved audit."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import environment_manifest, sha256_file, utc_now
from . import asymmetry as a, asymmetry_check as check

WS=Path(__file__).resolve().parents[2]
ROOT=Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
RUN='l20_extension1_asymmetry_v1_attempt1'
PILOT='l20_extension1_pilot64_v1_attempt1'
PLAN='l20_extension1_confirmation_design_v1_attempt1'
TIED='l20_extension1_difference_ablation_dev_v1_attempt1'
DEV='l20_extension1_target_averaging_dev_v1_attempt1'
RESERVE=4*1024**3;ALLOWANCE=128*1024**2
ENV='D163_DETACHED_STAGE'
PINS={
    'runs/'+PILOT+'/COMPLETE.json':'d77470be6d251f4d42344a6acfe0173fe3a542b04be2649de6e998bcfd95da53',
    'logs/'+PILOT+'_saved_audit_v1.json':'822a61ccf5b8d26ff466a51cce226c12b20d0f5d5293778477e54a06323fd191',
    'outputs/'+PLAN+'/COMPLETE.json':'d84b61f0eb6ba109cb2822f23685ce068cdf21ce1a55fdf8cde1df5b3bdedfe1',
    'runs/'+TIED+'/COMPLETE.json':'5466b207c1abfd79e673a13b1534b70f4882849c099f57747170c02c33266ab4',
    'logs/'+TIED+'_saved_audit_v1.json':'cd587bf743b061d7388e7395a584663ecaef486b3e744317bb4078297cdf3272',
}


def science():
    return [WS/'asymmetry/PROTOCOL_V1.md',WS/'tests/test_asymmetry.py']+[
        WS/'src/l20_extension1'/f'{name}.py' for name in ('asymmetry','asymmetry_check','asymmetry_run')]


def resources():
    assert not sys.flags.optimize,'assertions required'
    cpus=sorted(os.sched_getaffinity(0))
    assert cpus and set(cpus)<=set(range(6)),'at most CPUs 0-5'
    assert ROOT.is_dir() and shutil.disk_usage(ROOT).free>=RESERVE+ALLOWANCE,'external free space'
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        assert os.environ.get(key)=='1',key+' must be one'
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    for key in ('TMPDIR','XDG_CACHE_HOME'):
        path=Path(os.environ.get(key,'/')).resolve()
        assert ROOT in path.parents and path.is_dir(),'external temporary/cache directories'
    return cpus


def bind(path,expected,seen):
    path=Path(path)
    assert path.is_file() and not path.is_symlink(),'regular pinned input: '+str(path)
    actual=sha256_file(path);assert actual==expected,'input drift: '+str(path)
    name=str(path.resolve())
    assert name not in seen or seen[name]==actual,'inconsistent source binding'
    seen[name]=actual


def check_hashes(mapping):
    assert mapping and all(Path(k).is_absolute() for k in mapping)
    current={}
    for path,digest in mapping.items():bind(Path(path),digest,current)
    assert current==mapping


def source_inputs():
    """Hash only consumed inputs and imported code; pin earlier full audit receipts."""
    seen={}
    for rel,digest in PINS.items():bind(ROOT/rel,digest,seen)
    pc=io.read_json(ROOT/'runs'/PILOT/'COMPLETE.json')
    pa=io.read_json(ROOT/'logs'/f'{PILOT}_saved_audit_v1.json')
    dc=io.read_json(ROOT/'outputs'/PLAN/'COMPLETE.json')
    tc=io.read_json(ROOT/'runs'/TIED/'COMPLETE.json')
    ta=io.read_json(ROOT/'logs'/f'{TIED}_saved_audit_v1.json')
    assert pc['status']==tc['status']=='COMPLETE' and dc['status']=='DESIGN_COMPLETE'
    for audit,key in ((pa,'runs/'+PILOT+'/COMPLETE.json'),(ta,'runs/'+TIED+'/COMPLETE.json')):
        assert audit['passes'] and audit['complete_sha256']==PINS[key]
    assert pa['all_cases_retained'] and pa['full_control_panel_retained'] and pa['new_dynamics']==0
    manifest_path=ROOT/'runs'/PILOT/'MANIFEST.json'
    bind(manifest_path,pc['manifest_sha256'],seen);pm=io.read_json(manifest_path)
    maps=[pc['output_sha256'],pm['input_sha256'],dc['source_sha256'],dc['output_sha256'],tc['output_sha256']]
    def old(path):
        values={row[str(path)] for row in maps if str(path) in row}
        assert len(values)==1,'unique recorded binding required: '+str(path)
        bind(path,values.pop(),seen)
    out=ROOT/'outputs'/PILOT
    for name in ('forecasts.npz','raw_forecasts.npz','features.npz','outcomes.npz','summary.json',
                 'verification.json','FORECAST_SEAL.json','OUTCOMES_STARTED.json'):old(out/name)
    for name in ('dataset.npz','predictions.npz','raw_predictions.npz'):old(ROOT/'outputs'/DEV/name)
    for name in ('tied_full.npz','tied_full_raw.npz'):old(ROOT/'outputs'/TIED/name)
    old(ROOT/'outputs'/PLAN/'planning.json')
    model=ROOT/'tmp'/f'{PILOT}_models.json';freeze=ROOT/'tmp'/f'{PILOT}_freeze.json'
    bind(model,pc['model_sha256'],seen)
    seal=io.read_json(out/'FORECAST_SEAL.json');started=io.read_json(out/'OUTCOMES_STARTED.json')
    bind(freeze,seal['freeze_sha256'],seen)
    assert pc['forecast_seal_sha256']==started['forecast_seal_sha256']==seen[str(out/'FORECAST_SEAL.json')]
    assert seal['actual_lineages_started']==0 and seal['ids']==list(range(100000,100064))
    assert seal['cases']==1024 and seal['forecasts']==52224 and seal['verification']['passes']
    assert datetime.fromisoformat(seal['sealed_utc'])<datetime.fromisoformat(started['started_utc'])
    assert seal['model_sha256']==pc['model_sha256']==pm['model_sha256']
    for name in ('features.npz','forecasts.npz','raw_forecasts.npz'):
        assert seal['file_sha256'][str(out/name)]==seen[str(out/name)]
    f=io.read_json(freeze);models=io.read_json(model)
    assert f['model_sha256']==pc['model_sha256'] and f['test_founders_generated']==0
    assert models['test_founders_generated']==0 and models['verification']['passes']
    assert models['fitted']['new_test_data_used'] is False
    assert models['fitted']['training_blocks']==list(range(90000,90016))
    assert models['fitted']['alphas']==list(a.ALPHAS)
    new={x.resolve() for x in science()}
    # Bind imported repository implementation to the earlier audited closure.
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if WS.parent in path.parents and path.suffix=='.py' and path not in new:old(path)
    return seen


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs')
    assert path.name.startswith('d163_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=35 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    required={'test_full64_panel','test_virtual_mean_is_loss_not_forecast','test_permutations',
              'test_roundtrip','test_stage_guard','test_source_bridge_corruption'}
    assert required<={c.get('name') for c in cases}
    full=[c for c in cases if c.get('name')=='test_full64_panel'];assert len(full)==1
    props={x.get('name'):x.get('value') for x in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['founders']=='64' and props['comparisons']=='277' and props['saved_forecasts']=='52224'
    return dict(path=str(path),sha256=sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'
def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN


def freeze(report):
    resources();assert not freeze_path().exists() and not any(x.exists() for x in paths()),'single-use stage'
    proof=qualification(report);start=time.monotonic();inputs=source_inputs();seconds=time.monotonic()-start
    inputs.update(io.hashes(science()+[Path(proof['path'])]))
    budget=10*proof['full_panel_seconds']+4*seconds+120
    value=dict(schema='d163_freeze_v1',run=RUN,frozen_utc=utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=seconds,stage_budget_seconds=budget,
        must_detach=budget>600,environment=environment_manifest(),new_fits=0,new_dynamics=0,
        post_test_explanation=True,allowance=ALLOWANCE,reserve=RESERVE,
        source_scope='consumed small artifacts and imported code; prior full audits pinned, not repeated',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(freeze_path(),value,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d163_freeze_v1' and f['run']==RUN
    assert f['allowance']==ALLOWANCE and f['reserve']==RESERVE
    check_hashes(f['input_sha256'])
    current=source_inputs()
    assert all(f['input_sha256'][k]==v for k,v in current.items())
    assert all(f['input_sha256'][str(p)]==sha256_file(p) for p in science())
    env=environment_manifest()
    for k in ('python','numpy','thread_limits'):assert env[k]==f['environment'][k]
    return f


def data():
    out=ROOT/'outputs'/PILOT
    p=io.load_npz(out/'forecasts.npz');raw=io.load_npz(out/'raw_forecasts.npz')
    features=io.load_npz(out/'features.npz');outcomes=io.load_npz(out/'outcomes.npz')
    assert set(outcomes)=={'outcomes'}
    models=io.read_json(ROOT/'tmp'/f'{PILOT}_models.json')['fitted']['models']
    d=io.load_npz(ROOT/'outputs'/DEV/'dataset.npz')
    dp=io.load_npz(ROOT/'outputs'/DEV/'predictions.npz');dr=io.load_npz(ROOT/'outputs'/DEV/'raw_predictions.npz')
    assert set(dp)==set(dr)==set(k for k in a.OBSERVERS if not k.startswith('tied:'))
    assert all(x.shape==(6,3,16,4,4) for x in (*dp.values(),*dr.values()))
    dp={k:v[5] for k,v in dp.items()};dr={k:v[5] for k,v in dr.items()}
    dp.update(io.load_npz(ROOT/'outputs'/TIED/'tied_full.npz'))
    dr.update(io.load_npz(ROOT/'outputs'/TIED/'tied_full_raw.npz'))
    assert np.array_equal(d['block_ids'],np.arange(90000,90016,dtype=np.int64))
    return dict(pilot=(p,raw,outcomes['outcomes'],np.arange(100000,100064,dtype=np.int64)),
                development=(dp,dr,d['futures'],d['block_ids']),features=features,models=models,
                pilot_source=io.read_json(out/'summary.json'),
                planning=io.read_json(ROOT/'outputs'/PLAN/'planning.json'))


def calculate(d):
    main=a.cohort(*d['pilot']);dev=a.cohort(*d['development'])
    models,arrays=a.model_accounting(d['features'],d['models'],*d['pilot'])
    return dict(schema='d163_saved_asymmetry_v1',pilot=main,development=dev,model_accounting=models,
        new_fits=0,new_dynamics=0,new_deployed_forecasts=0,post_test_explanation=True,
        source_primary_unchanged=True,prospective_evidence=False,automatic_successor=False),arrays


def verify(summary,arrays,d):
    assert summary['schema']=='d163_saved_asymmetry_v1'
    for k in ('new_fits','new_dynamics','new_deployed_forecasts'):assert summary[k]==0
    assert summary['post_test_explanation'] and summary['source_primary_unchanged']
    assert not summary['prospective_evidence'] and not summary['automatic_successor']
    return dict(passes=True,pilot=check.check_cohort(summary['pilot'],*d['pilot']),
        development=check.check_cohort(summary['development'],*d['development']),
        models=check.check_models(summary['model_accounting'],arrays,d['features'],d['models'],*d['pilot']),
        source_bridge=check.source_bridge(summary['pilot'],summary['development'],d['pilot_source'],d['planning']))


def stage_guard(f,stage):
    if f['must_detach']:
        assert os.environ.get(ENV)==stage,'forecast above ten minutes: detached stage required'
        assert os.getsid(0)==os.getpid() and not sys.stdin.isatty(),'new detached session required'


def execute():
    resources();f=frozen();stage_guard(f,'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'do not overwrite or retry a run'
    run.mkdir();out.mkdir();start=time.monotonic()
    try:
        io.write_json(run/'MANIFEST.json',dict(freeze_sha256=sha256_file(freeze_path()),
            started_utc=utc_now(),input_sha256=f['input_sha256'],environment=environment_manifest()),ROOT)
        d=data();summary,arrays=calculate(d);proof=verify(summary,arrays,d)
        io.write_json(out/'summary.json',summary,ROOT);io.write_npz(out/'model_parts.npz',arrays,ROOT)
        reread=verify(io.read_json(out/'summary.json'),io.load_npz(out/'model_parts.npz'),d)
        assert reread==proof
        io.write_json(out/'verification.json',proof,ROOT)
        check_hashes(f['input_sha256']);output=io.hashes(out.iterdir());size=sum(Path(p).stat().st_size for p in output)
        assert size<ALLOWANCE;resources()
        done=dict(status='COMPLETE',completed_utc=utc_now(),seconds=time.monotonic()-start,
            freeze_sha256=sha256_file(freeze_path()),manifest_sha256=sha256_file(run/'MANIFEST.json'),
            output_sha256=output,output_bytes=size,new_fits=0,new_dynamics=0,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT)
        return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit():
    resources();f=frozen();stage_guard(f,'audit');run,out=paths()
    assert not audit_path().exists(),'saved audit is write-once'
    start=time.monotonic();done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and manifest['input_sha256']==f['input_sha256']
    assert done['freeze_sha256']==manifest['freeze_sha256']==sha256_file(freeze_path())
    assert done['manifest_sha256']==sha256_file(run/'MANIFEST.json')
    assert set(done['output_sha256'])=={str(out/k) for k in ('summary.json','model_parts.npz','verification.json')}
    check_hashes(done['output_sha256'])
    d=data();s=io.read_json(out/'summary.json');arrays=io.load_npz(out/'model_parts.npz')
    proof=verify(s,arrays,d);assert proof==io.read_json(out/'verification.json')
    check_hashes(f['input_sha256']);check_hashes(done['output_sha256'])
    value=dict(passes=True,checked_utc=utc_now(),seconds=time.monotonic()-start,
        complete_sha256=sha256_file(run/'COMPLETE.json'),freeze_sha256=sha256_file(freeze_path()),
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,
        new_fits=0,new_dynamics=0,new_deployed_forecasts=0,
        scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),value,ROOT);return value


def detach(stage):
    resources();f=frozen();assert stage in ('execute','audit')
    run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists(),'single-use launch'
    env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.asymmetry_run',stage],
            stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,env=env,start_new_session=True,cwd=WS.parent)
    value=dict(launched_utc=utc_now(),pid=child.pid,stage=stage,log=str(log),startup='process created; no progress polling',
               stage_budget_seconds=f['stage_budget_seconds'],automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(receipt,value,ROOT);return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('freeze','execute','audit','detach-execute','detach-audit'))
    parser.add_argument('--test-report',type=Path);args=parser.parse_args()
    if args.stage=='freeze':
        assert args.test_report is not None;result=freeze(args.test_report)
    elif args.stage.startswith('detach-'):result=detach(args.stage[7:])
    elif args.stage=='execute':result=execute()
    else:result=audit()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':main()
