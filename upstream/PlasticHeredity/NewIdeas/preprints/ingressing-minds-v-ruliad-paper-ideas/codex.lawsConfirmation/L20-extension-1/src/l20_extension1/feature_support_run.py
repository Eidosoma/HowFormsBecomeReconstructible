"""D166 qualified outcome-free feature audit; write-once stages and receipts."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import asymmetry_run as source, recovery_features as schema, feature_support as m, feature_support_check as check

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_feature_support_v1_attempt1';OLD='l20_extension1_decoder_transport_v1_attempt1'
ENV='D166_DETACHED_STAGE'
COMPLETE='c1d6fdc380e86408f1b6e088037b1598a258b16940dc3b769bccada5669159c9'
AUDIT='cbbf540b41608e77b97a6c2aff74505b54833704611517ab38e2b5950a730132'
OUTPUTS=('support.npz','summary.json','verification.json')


def science():
    return [WS/'feature-support/PROTOCOL_V1.md',WS/'tests/test_feature_support.py']+[
        WS/'src/l20_extension1'/f'{k}.py' for k in ('feature_support','feature_support_check','feature_support_run')]


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'


def source_inputs():
    seen={};run=ROOT/'runs'/OLD;out=ROOT/'outputs'/OLD
    receipt=ROOT/'logs'/f'{OLD}_saved_audit_v1.json';freeze=ROOT/'tmp'/f'{OLD}_freeze.json'
    source.bind(run/'COMPLETE.json',COMPLETE,seen);source.bind(receipt,AUDIT,seen)
    done=io.read_json(run/'COMPLETE.json');audit=io.read_json(receipt)
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==COMPLETE
    source.bind(freeze,done['freeze_sha256'],seen);source.bind(run/'MANIFEST.json',done['manifest_sha256'],seen)
    f=io.read_json(freeze);manifest=io.read_json(run/'MANIFEST.json')
    assert audit['freeze_sha256']==done['freeze_sha256']==manifest['freeze_sha256']
    assert manifest['input_sha256']==f['input_sha256'] and len(f['input_sha256'])==101
    expected=('RULE_SEAL.json','pilot_predictions.npz','pilot_raw.npz','FORECAST_SEAL.json','SCORING_STARTED.json','summary.json','verification.json')
    assert set(done['output_sha256'])=={str(out/k) for k in expected}
    for path,digest in {**f['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if WS.parent in path.parents and path.suffix=='.py' and path not in fresh:
            assert str(path) in seen,'unbound imported repository code: '+str(path)
    assert m.START==schema.INITIAL and m.END==schema.ENDPOINT
    assert schema.CASES==((0,'translated'),(0,'aligned'),(1,'translated'),(1,'aligned'))
    return seen


def features(path,development):
    # np.load is lazy: do not request actual labels/futures, even for validation.
    with np.load(path,allow_pickle=False) as archive:
        expected={'start','endpoint','targeted'}|({'labels','futures','block_ids'} if development else set())
        assert len(archive.files)==len(set(archive.files)) and set(archive.files)==expected
        result={k:archive[k] for k in ('start','endpoint','targeted')}
        ids=archive['block_ids'] if development else np.arange(100000,100064,dtype=np.int64)
    for v in result.values():v.setflags(write=False)
    ids.setflags(write=False)
    return result,ids


def data():
    d,di=features(ROOT/'outputs'/source.DEV/'dataset.npz',True)
    p,pi=features(ROOT/'outputs'/source.PILOT/'features.npz',False)
    assert di.tolist()==list(range(90000,90016)) and pi.tolist()==list(range(100000,100064))
    m.validate(d,di);m.validate(p,pi)
    return d,p,di,pi


def verify(arrays,summary,inputs):
    return dict(passes=True,arrays=check.check_arrays(arrays,*inputs),summary=check.summary(summary,arrays,*inputs),
                outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d166_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=35 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_panel_roundtrip','test_no_outcome_or_fit','test_excluded_founder','test_constant_dimensions',
            'test_pooled_reference','test_loader_excludes_outcomes','test_stage_guard','test_corruption'}<=names
    full=[c for c in cases if c.get('name')=='test_full_panel_roundtrip'];assert len(full)==1
    props={p.get('name'):p.get('value') for p in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['new_fits']=='0' and props['scalar_rows']=='292' and props['vector_rows']=='88'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def freeze(report):
    source.resources();assert not freeze_path().exists() and not any(p.exists() for p in paths())
    proof=qualification(report);start=time.monotonic();inputs=source_inputs();elapsed=time.monotonic()-start
    inputs.update(io.hashes(science()+[Path(proof['path'])]));budget=10*proof['full_panel_seconds']+4*elapsed+120
    f=dict(schema='d166_feature_support_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=elapsed,stage_budget_seconds=budget,must_detach=budget>600,
        environment=source.environment_manifest(),post_test_explanation=True,outcomes_used=False,new_fits=0,new_forecasts=0,
        new_dynamics=0,allowance=source.ALLOWANCE,reserve=source.RESERVE,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        source_scope='D165 qualified evidence/provenance hashes; support uses only saved pre-outcome feature members, no raw-physics rerun')
    io.write_json(freeze_path(),f,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d166_feature_support_freeze_v1' and f['run']==RUN
    assert f['new_fits']==f['new_forecasts']==f['new_dynamics']==0 and f['outcomes_used'] is False
    assert f['allowance']==source.ALLOWANCE and f['reserve']==source.RESERVE
    budget=10*f['qualification']['full_panel_seconds']+4*f['source_hash_seconds']+120
    assert f['stage_budget_seconds']==budget and f['must_detach']==(budget>600)
    source.check_hashes(f['input_sha256']);seen=source_inputs()
    assert all(f['input_sha256'][k]==v for k,v in seen.items())
    assert all(f['input_sha256'][str(p)]==source.sha256_file(p) for p in science())
    env=source.environment_manifest()
    for k in ('python','numpy','thread_limits'):assert env[k]==f['environment'][k]
    return f


def stage_guard(f,stage):
    if f['must_detach']:
        assert os.environ.get(ENV)==stage,'forecast above ten minutes requires detached stage'
        assert os.getsid(0)==os.getpid() and not sys.stdin.isatty(),'new session/null input required'


def execute():
    source.resources();f=frozen();stage_guard(f,'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'single use; preserve failures'
    run.mkdir();out.mkdir();start=time.monotonic()
    try:
        io.write_json(run/'MANIFEST.json',dict(started_utc=source.utc_now(),freeze_sha256=source.sha256_file(freeze_path()),
            input_sha256=f['input_sha256'],environment=source.environment_manifest(),outcomes_used=False),ROOT)
        inputs=data();arrays=m.calculate(*inputs);summary=m.summarize(arrays,*inputs);proof=verify(arrays,summary,inputs)
        io.write_npz(out/'support.npz',arrays,ROOT);io.write_json(out/'summary.json',summary,ROOT)
        assert verify(io.load_npz(out/'support.npz'),io.read_json(out/'summary.json'),inputs)==proof
        io.write_json(out/'verification.json',proof,ROOT);source.check_hashes(f['input_sha256'])
        assert {p.name for p in out.iterdir()}==set(OUTPUTS)
        hashes=io.hashes(out.iterdir());size=sum(Path(k).stat().st_size for k in hashes)
        assert size<source.ALLOWANCE;source.resources()
        done=dict(status='COMPLETE',completed_utc=source.utc_now(),seconds=time.monotonic()-start,
            freeze_sha256=source.sha256_file(freeze_path()),manifest_sha256=source.sha256_file(run/'MANIFEST.json'),
            output_sha256=hashes,output_bytes=size,outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT);return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit():
    source.resources();f=frozen();stage_guard(f,'audit');run,out=paths();assert not audit_path().exists()
    start=time.monotonic();done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and manifest['input_sha256']==f['input_sha256']
    assert done['freeze_sha256']==manifest['freeze_sha256']==source.sha256_file(freeze_path())
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    assert set(done['output_sha256'])=={str(out/k) for k in OUTPUTS}
    source.check_hashes(done['output_sha256'])
    proof=verify(io.load_npz(out/'support.npz'),io.read_json(out/'summary.json'),data())
    assert proof==io.read_json(out/'verification.json')
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-start,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,
        outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,source_scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return result


def detach(stage):
    source.resources();f=frozen();assert stage in ('execute','audit');run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists();env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.feature_support_run',stage],
            stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,env=env,cwd=WS.parent)
    result=dict(launched_utc=source.utc_now(),pid=child.pid,stage=stage,log=str(log),startup='process created',
        completion=str(run/'COMPLETE.json' if stage=='execute' else audit_path()),
        stage_budget_seconds=f['stage_budget_seconds'],automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(receipt,result,ROOT);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('freeze','execute','audit','detach-execute','detach-audit'))
    parser.add_argument('--test-report',type=Path);args=parser.parse_args()
    if args.stage=='freeze':assert args.test_report is not None;result=freeze(args.test_report)
    elif args.stage.startswith('detach-'):result=detach(args.stage[7:])
    elif args.stage=='execute':result=execute()
    else:result=audit()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':main()
