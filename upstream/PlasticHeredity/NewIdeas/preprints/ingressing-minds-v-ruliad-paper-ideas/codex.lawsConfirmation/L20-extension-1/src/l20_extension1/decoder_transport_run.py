"""D165 write-once saved-rule transport and separately invoked saved audit."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import asymmetry_run as source, decoder_transport as m, decoder_transport_check as check

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_decoder_transport_v1_attempt1';OLD='l20_extension1_shared_decoder_v1_attempt1'
ENV='D165_DETACHED_STAGE'
COMPLETE='3a19e4d88f4008c0d0cde48f1bf9490b73486a686c0485375d6c2a9196818c31'
AUDIT='bf3bf0f55d7230ceae5431d574916e6524c9da533a177bb3c70a5265bc3935cb'
OUTPUTS=('RULE_SEAL.json','pilot_predictions.npz','pilot_raw.npz','FORECAST_SEAL.json',
         'SCORING_STARTED.json','summary.json','verification.json')


def science():
    return [WS/'decoder-transport/PROTOCOL_V1.md',WS/'tests/test_decoder_transport.py']+[
        WS/'src/l20_extension1'/f'{k}.py' for k in ('decoder_transport','decoder_transport_check','decoder_transport_run')]


def model_paths():return ROOT/'outputs'/OLD/'models.json',ROOT/'outputs'/source.DEV/'fits.json'
def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'


def source_inputs():
    seen={};old_run=ROOT/'runs'/OLD;old_out=ROOT/'outputs'/OLD
    receipt=ROOT/'logs'/f'{OLD}_saved_audit_v1.json';freeze=ROOT/'tmp'/f'{OLD}_freeze.json'
    source.bind(old_run/'COMPLETE.json',COMPLETE,seen);source.bind(receipt,AUDIT,seen)
    done=io.read_json(old_run/'COMPLETE.json');audit=io.read_json(receipt)
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==COMPLETE
    source.bind(freeze,done['freeze_sha256'],seen);source.bind(old_run/'MANIFEST.json',done['manifest_sha256'],seen)
    f=io.read_json(freeze);manifest=io.read_json(old_run/'MANIFEST.json')
    assert audit['freeze_sha256']==done['freeze_sha256']==manifest['freeze_sha256']
    assert manifest['input_sha256']==f['input_sha256'] and len(f['input_sha256'])==80
    names=('models.json','MODEL_SEAL.json','development_predictions.npz','development_raw.npz',
           'pilot_predictions.npz','pilot_raw.npz','FORECAST_SEAL.json','SCORING_STARTED.json','summary.json','verification.json')
    assert set(done['output_sha256'])=={str(old_out/k) for k in names}
    for path,digest in {**f['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    pilot_manifest=ROOT/'runs'/source.PILOT/'MANIFEST.json'
    assert str(pilot_manifest) in seen
    fits=model_paths()[1];source.bind(fits,io.read_json(pilot_manifest)['input_sha256'][str(fits)],seen)
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if WS.parent in path.parents and path.suffix=='.py' and path not in fresh:
            assert str(path) in seen,'unbound imported repository code: '+str(path)
    return seen


def forecasting_inputs():
    shared,cheap=(io.read_json(p) for p in model_paths());rules=m.registry(shared,cheap)
    assert [r['validation_block'] for r in rules]==list(range(90000,90016))
    with np.load(ROOT/'outputs'/source.DEV/'dataset.npz',allow_pickle=False) as d:
        features={k:d[k] for k in ('start','endpoint','targeted')};ids=d['block_ids']
    assert ids.tolist()==list(range(90000,90016)) and ids.dtype==np.int64
    pilot=io.load_npz(ROOT/'outputs'/source.PILOT/'features.npz')
    m.a.feature_matrices(features);m.a.feature_matrices(pilot);assert len(pilot['start'])==64
    dp=io.load_npz(ROOT/'outputs'/OLD/'development_predictions.npz')
    dr=io.load_npz(ROOT/'outputs'/OLD/'development_raw.npz')
    return dict(rules=rules,development_features=features,development_ids=ids,pilot_features=pilot,dp=dp,dr=dr)


def scored_inputs(d):
    dy=io.load_npz(ROOT/'outputs'/source.DEV/'dataset.npz')['futures']
    py=io.load_npz(ROOT/'outputs'/source.PILOT/'outcomes.npz')['outcomes']
    fp=io.load_npz(ROOT/'outputs'/OLD/'pilot_predictions.npz');fr=io.load_npz(ROOT/'outputs'/OLD/'pilot_raw.npz')
    return dict(dev=(d['dp'],d['dr'],dy,d['development_ids']),
                full=(fp,fr,py,np.arange(100000,100064,dtype=np.int64)),
                prior=io.read_json(ROOT/'outputs'/OLD/'summary.json'))


def verify(d,p,raw,summary,scored):
    dev=check.forecasts(d['rules'],d['development_features'],d['dp'],d['dr'],d['development_ids'])
    pilot=check.forecasts(d['rules'],d['pilot_features'],p,raw)
    scores=check.summary(summary,p,raw,**scored)
    return dict(passes=True,development=dev,pilot=pilot,scores=scores,new_fits=0,new_dynamics=0)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d165_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=40 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_panel_roundtrip','test_no_fit_or_outcome_interface','test_loss_not_ensemble',
            'test_model_corruption','test_two_copy_isolation','test_seal_corruption','test_stage_guard'}<=names
    full=[c for c in cases if c.get('name')=='test_full_panel_roundtrip'];assert len(full)==1
    props={p.get('name'):p.get('value') for p in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['new_fits']=='0' and props['saved_rules']=='240' and props['new_forecasts']=='835584'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def freeze(report):
    source.resources();assert not freeze_path().exists() and not any(p.exists() for p in paths())
    proof=qualification(report);start=time.monotonic();inputs=source_inputs();elapsed=time.monotonic()-start
    inputs.update(io.hashes(science()+[Path(proof['path'])]))
    budget=10*proof['full_panel_seconds']+4*elapsed+120
    value=dict(schema='d165_transport_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=elapsed,stage_budget_seconds=budget,must_detach=budget>600,
        environment=source.environment_manifest(),post_test_explanation=True,new_fits=0,saved_rules=240,new_forecasts=835584,
        new_dynamics=0,allowance=source.ALLOWANCE,reserve=source.RESERVE,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        source_scope='D164 consumed artifacts/code and prior full-audit provenance, plus pinned D157 cheap OOF rules; no raw-physics rerun')
    io.write_json(freeze_path(),value,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d165_transport_freeze_v1' and f['run']==RUN
    assert f['new_fits']==0 and f['saved_rules']==240 and f['new_forecasts']==835584
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


def rule_seal(out,freeze_sha):
    io.write_json(out/'RULE_SEAL.json',dict(sealed_utc=source.utc_now(),freeze_sha256=freeze_sha,
        saved_model_sha256=io.hashes(model_paths()),saved_rules=240,new_fits=0,
        calibration_ids=list(range(90000,90016)),cheap_target='future_mean',cheap_target_index=5,
        scoring_started=False,prospective_evidence=False),ROOT)


def forecast_seal(out,freeze_sha):
    io.write_json(out/'FORECAST_SEAL.json',dict(sealed_utc=source.utc_now(),freeze_sha256=freeze_sha,
        rule_seal_sha256=source.sha256_file(out/'RULE_SEAL.json'),
        forecast_sha256=io.hashes(out/k for k in OUTPUTS[1:3]),new_forecasts=835584,
        reconstructed_development_forecasts=13056,pilot_ids=list(range(100000,100064)),
        scoring_started=False,prospective_evidence=False),ROOT)


def check_seals(out,freeze_sha):
    rules=io.read_json(out/'RULE_SEAL.json');forecasts=io.read_json(out/'FORECAST_SEAL.json')
    started=io.read_json(out/'SCORING_STARTED.json')
    assert rules['freeze_sha256']==forecasts['freeze_sha256']==freeze_sha
    assert rules['saved_model_sha256']==io.hashes(model_paths())
    assert rules['saved_rules']==240 and rules['new_fits']==0
    assert rules['calibration_ids']==list(range(90000,90016)) and rules['cheap_target']=='future_mean' and rules['cheap_target_index']==5
    assert forecasts['new_forecasts']==835584 and forecasts['reconstructed_development_forecasts']==13056
    assert forecasts['pilot_ids']==list(range(100000,100064))
    assert forecasts['rule_seal_sha256']==source.sha256_file(out/'RULE_SEAL.json')
    assert set(forecasts['forecast_sha256'])=={str(out/k) for k in OUTPUTS[1:3]}
    source.check_hashes(forecasts['forecast_sha256'])
    assert rules['scoring_started'] is forecasts['scoring_started'] is False
    assert rules['prospective_evidence'] is forecasts['prospective_evidence'] is started['prospective_evidence'] is False
    assert started['forecast_seal_sha256']==source.sha256_file(out/'FORECAST_SEAL.json')
    assert datetime.fromisoformat(rules['sealed_utc'])<=datetime.fromisoformat(forecasts['sealed_utc'])<=datetime.fromisoformat(started['started_utc'])
    return dict(passes=True,saved_rules_before_scoring=True,forecasts_before_scoring=True,prospective_evidence=False)


def load_forecasts(out):return io.load_npz(out/'pilot_predictions.npz'),io.load_npz(out/'pilot_raw.npz')


def execute():
    source.resources();f=frozen();stage_guard(f,'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'single use; preserve failed attempts'
    run.mkdir();out.mkdir();start=time.monotonic();freeze_sha=source.sha256_file(freeze_path())
    try:
        io.write_json(run/'MANIFEST.json',dict(started_utc=source.utc_now(),freeze_sha256=freeze_sha,
            input_sha256=f['input_sha256'],environment=source.environment_manifest()),ROOT)
        d=forecasting_inputs();rule_seal(out,freeze_sha)
        dp,dr=m.forecasts(d['rules'],d['development_features'],d['development_ids'])
        for name in m.a.OBSERVERS:
            check.close(dp[name],d['dp'][name],2e-10);check.close(dr[name],d['dr'][name],2e-10)
        check.forecasts(d['rules'],d['development_features'],d['dp'],d['dr'],d['development_ids'])
        p,raw=m.forecasts(d['rules'],d['pilot_features']);check.forecasts(d['rules'],d['pilot_features'],p,raw)
        io.write_npz(out/'pilot_predictions.npz',p,ROOT);io.write_npz(out/'pilot_raw.npz',raw,ROOT)
        forecast_seal(out,freeze_sha)
        io.write_json(out/'SCORING_STARTED.json',dict(started_utc=source.utc_now(),
            forecast_seal_sha256=source.sha256_file(out/'FORECAST_SEAL.json'),prospective_evidence=False),ROOT)
        check_seals(out,freeze_sha);scored=scored_inputs(d);p,raw=load_forecasts(out)
        summary=m.summarize(p,raw,scored['dev'],scored['full'],d['development_ids'])
        proof=verify(d,p,raw,summary,scored);io.write_json(out/'summary.json',summary,ROOT)
        assert verify(d,*load_forecasts(out),io.read_json(out/'summary.json'),scored)==proof
        io.write_json(out/'verification.json',proof,ROOT)
        source.check_hashes(f['input_sha256']);check_seals(out,freeze_sha)
        assert {p.name for p in out.iterdir()}==set(OUTPUTS)
        hashes=io.hashes(out.iterdir());size=sum(Path(k).stat().st_size for k in hashes)
        assert size<source.ALLOWANCE;source.resources()
        done=dict(status='COMPLETE',completed_utc=source.utc_now(),seconds=time.monotonic()-start,
            freeze_sha256=freeze_sha,manifest_sha256=source.sha256_file(run/'MANIFEST.json'),
            output_sha256=hashes,output_bytes=size,new_fits=0,new_forecasts=835584,new_dynamics=0,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT);return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit():
    source.resources();f=frozen();stage_guard(f,'audit');run,out=paths();assert not audit_path().exists()
    start=time.monotonic();done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and manifest['input_sha256']==f['input_sha256']
    assert done['freeze_sha256']==manifest['freeze_sha256']==source.sha256_file(freeze_path())
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    assert set(done['output_sha256'])=={str(out/k) for k in OUTPUTS}
    source.check_hashes(done['output_sha256']);seals=check_seals(out,done['freeze_sha256'])
    d=forecasting_inputs();proof=verify(d,*load_forecasts(out),io.read_json(out/'summary.json'),scored_inputs(d))
    assert proof==io.read_json(out/'verification.json')
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-start,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,seals=seals,
        new_fits=0,new_forecasts=0,new_dynamics=0,source_scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return result


def detach(stage):
    source.resources();f=frozen();assert stage in ('execute','audit');run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists();env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.decoder_transport_run',stage],
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
