"""D164 qualified write-once fitting, forecast seal and separate saved audit."""
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
from . import asymmetry_run as source, shared_decoder as model, shared_decoder_check as check

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_shared_decoder_v1_attempt1';ENV='D164_DETACHED_STAGE'
COMPLETE='4afa03e6b33f644c8b56c967eee832ba1eb8d9c9724486b9fa168ab4f7bddba2'
AUDIT='968298055265b47002577dc1e38ff6667cf279750444fb3b5bacafcebb5fd4a3'
OUTPUTS=('models.json','MODEL_SEAL.json','development_predictions.npz','development_raw.npz',
         'pilot_predictions.npz','pilot_raw.npz','FORECAST_SEAL.json','SCORING_STARTED.json','summary.json','verification.json')


def science():
    return [WS/'shared-decoder/PROTOCOL_V1.md',WS/'tests/test_shared_decoder.py']+[
        WS/'src/l20_extension1'/f'{name}.py' for name in ('shared_decoder','shared_decoder_check','shared_decoder_run')]


def source_inputs():
    seen={};old_run,old_out=source.paths()
    source.bind(old_run/'COMPLETE.json',COMPLETE,seen);source.bind(source.audit_path(),AUDIT,seen)
    done=io.read_json(old_run/'COMPLETE.json');audit=io.read_json(source.audit_path())
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==COMPLETE
    source.bind(source.freeze_path(),done['freeze_sha256'],seen)
    source.bind(old_run/'MANIFEST.json',done['manifest_sha256'],seen)
    freeze=io.read_json(source.freeze_path());manifest=io.read_json(old_run/'MANIFEST.json')
    assert audit['freeze_sha256']==done['freeze_sha256']==manifest['freeze_sha256']
    assert manifest['input_sha256']==freeze['input_sha256'] and len(freeze['input_sha256'])==67
    assert set(done['output_sha256'])=={str(old_out/k) for k in ('summary.json','model_parts.npz','verification.json')}
    for path,digest in {**freeze['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if WS.parent in path.parents and path.suffix=='.py' and path not in fresh:
            assert str(path) in seen,'unbound imported repository code: '+str(path)
    return seen


def training():
    d=io.load_npz(ROOT/'outputs'/source.DEV/'dataset.npz')
    assert d['block_ids'].tolist()==list(range(90000,90016))
    features={k:d[k] for k in ('start','endpoint','targeted')}
    model.validate_training(features,d['futures'],d['block_ids'])
    return features,d['futures'],d['block_ids']


def pilot_features():
    f=io.load_npz(ROOT/'outputs'/source.PILOT/'features.npz')
    model.a.feature_matrices(f);assert len(f['start'])==64
    return f


def baselines(cohort):
    if cohort=='pilot':
        out=ROOT/'outputs'/source.PILOT
        p=io.load_npz(out/'forecasts.npz');raw=io.load_npz(out/'raw_forecasts.npz')
    elif cohort=='development':
        out=ROOT/'outputs'/source.DEV
        p={k:v[5] for k,v in io.load_npz(out/'predictions.npz').items()}
        raw={k:v[5] for k,v in io.load_npz(out/'raw_predictions.npz').items()}
    else:raise ValueError('declared cohort')
    return {k:p[k] for k in ('starting','one_copy')},{k:raw[k] for k in ('starting','one_copy')}


def scored_inputs():
    d=source.data();features,futures,ids=training()
    assert np.array_equal(futures,d['development'][2]) and np.array_equal(ids,d['development'][3])
    d.update(training_features=features,training_futures=futures,training_ids=ids,
             prior_summary=io.read_json(ROOT/'outputs'/source.RUN/'summary.json'))
    return d


def score(records,panels,d):
    return model.summarize(panels,{k:d[k] for k in ('development','pilot')})


def verify(records,panels,summary,d):
    models=check.check_models(records,d['training_features'],d['training_futures'],d['training_ids'])
    predictions={}
    for name,features,ids in (('development',d['training_features'],d['training_ids']),('pilot',d['features'],None)):
        p,raw=panels[name];diagnostic={k:v for k,v in p.items() if k not in ('starting','one_copy')}
        diagnostic_raw={k:raw[k] for k in diagnostic}
        predictions[name]=check.check_forecasts(records,features,diagnostic,diagnostic_raw,ids)
    scores=check.check_summary(summary,panels,{k:d[k] for k in ('development','pilot')},d['prior_summary'])
    bridge=source.check.source_bridge(d['prior_summary']['pilot'],d['prior_summary']['development'],d['pilot_source'],d['planning'])
    return dict(passes=True,models=models,predictions=predictions,scores=scores,source_bridge=bridge,new_dynamics=0)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d164_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=40 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_panel_roundtrip','test_whole_founder_exclusion','test_no_pilot_label_interface',
            'test_two_copy_isolation','test_direction_swap','test_seal_corruption','test_stage_guard'}<=names
    full=[c for c in cases if c.get('name')=='test_full_panel_roundtrip'];assert len(full)==1
    props={p.get('name'):p.get('value') for p in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['fitted_models']=='153' and props['new_forecasts']=='57600'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'


def freeze(report):
    source.resources();assert not freeze_path().exists() and not any(p.exists() for p in paths())
    proof=qualification(report);begin=time.monotonic();inputs=source_inputs();elapsed=time.monotonic()-begin
    inputs.update(io.hashes(science()+[Path(proof['path'])]))
    budget=10*proof['full_panel_seconds']+4*elapsed+120
    f=dict(schema='d164_shared_decoder_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=elapsed,stage_budget_seconds=budget,must_detach=budget>600,
        environment=source.environment_manifest(),post_test_development=True,new_fits=153,new_forecasts=57600,
        new_dynamics=0,allowance=source.ALLOWANCE,reserve=source.RESERVE,calibration=list(model.CALIBRATION),
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        source_scope='D163 consumed artifacts/code and prior full-audit provenance; unconsumed raw physics not repeated')
    io.write_json(freeze_path(),f,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d164_shared_decoder_freeze_v1' and f['run']==RUN
    assert f['calibration']==list(model.CALIBRATION) and f['new_fits']==153 and f['new_forecasts']==57600
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


def check_seals(out,freeze_sha):
    ms=io.read_json(out/'MODEL_SEAL.json');ps=io.read_json(out/'FORECAST_SEAL.json');started=io.read_json(out/'SCORING_STARTED.json')
    assert ms['models_sha256']==ps['models_sha256']==source.sha256_file(out/'models.json')
    assert ms['freeze_sha256']==ps['freeze_sha256']==freeze_sha
    assert ms['new_fits']==153 and ms['scoring_started'] is False and ms['prospective_evidence'] is False
    assert ms['training_blocks']==list(range(90000,90016)) and ms['calibration']==list(model.CALIBRATION)
    assert ps['new_forecasts']==57600 and ps['reused_forecasts']==7680 and ps['scoring_started'] is False
    assert ps['prospective_evidence'] is False and started['prospective_evidence'] is False
    assert ps['development_blocks']==list(range(90000,90016)) and ps['pilot_blocks']==list(range(100000,100064))
    assert set(ps['forecast_sha256'])=={str(out/k) for k in OUTPUTS[2:6]}
    source.check_hashes(ps['forecast_sha256'])
    assert started['forecast_seal_sha256']==source.sha256_file(out/'FORECAST_SEAL.json')
    assert datetime.fromisoformat(ms['sealed_utc'])<=datetime.fromisoformat(ps['sealed_utc'])<=datetime.fromisoformat(started['started_utc'])
    return dict(passes=True,models_before_scoring=True,forecasts_before_scoring=True,prospective_evidence=False)


def load_panels(out):
    return {k:(io.load_npz(out/(k+'_predictions.npz')),io.load_npz(out/(k+'_raw.npz'))) for k in ('development','pilot')}


def execute():
    source.resources();f=frozen();stage_guard(f,'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'single use; preserve failed attempts'
    run.mkdir();out.mkdir();start=time.monotonic();freeze_sha=source.sha256_file(freeze_path())
    try:
        io.write_json(run/'MANIFEST.json',dict(started_utc=source.utc_now(),freeze_sha256=freeze_sha,
                      input_sha256=f['input_sha256'],environment=source.environment_manifest()),ROOT)
        train,futures,ids=training();records=model.train(train,futures,ids)
        check.check_models(records,train,futures,ids)
        io.write_json(out/'models.json',records,ROOT)
        io.write_json(out/'MODEL_SEAL.json',dict(sealed_utc=source.utc_now(),models_sha256=source.sha256_file(out/'models.json'),
            freeze_sha256=freeze_sha,training_blocks=ids.tolist(),calibration=list(model.CALIBRATION),new_fits=153,
            scoring_started=False,prospective_evidence=False),ROOT)
        for name,features,fold_ids in (('development',train,ids),('pilot',pilot_features(),None)):
            p,raw=model.forecast(records,features,fold_ids);check.check_forecasts(records,features,p,raw,fold_ids)
            p,raw=model.with_baselines(p,raw,*baselines(name))
            io.write_npz(out/(name+'_predictions.npz'),p,ROOT);io.write_npz(out/(name+'_raw.npz'),raw,ROOT)
        io.write_json(out/'FORECAST_SEAL.json',dict(sealed_utc=source.utc_now(),freeze_sha256=freeze_sha,
            models_sha256=source.sha256_file(out/'models.json'),forecast_sha256=io.hashes(out/k for k in OUTPUTS[2:6]),
            development_blocks=ids.tolist(),pilot_blocks=list(range(100000,100064)),new_forecasts=57600,reused_forecasts=7680,
            scoring_started=False,prospective_evidence=False),ROOT)
        io.write_json(out/'SCORING_STARTED.json',dict(started_utc=source.utc_now(),
            forecast_seal_sha256=source.sha256_file(out/'FORECAST_SEAL.json'),prospective_evidence=False),ROOT)
        check_seals(out,freeze_sha);panels=load_panels(out);d=scored_inputs()
        summary=score(records,panels,d);proof=verify(records,panels,summary,d)
        io.write_json(out/'summary.json',summary,ROOT)
        assert verify(io.read_json(out/'models.json'),load_panels(out),io.read_json(out/'summary.json'),d)==proof
        io.write_json(out/'verification.json',proof,ROOT)
        source.check_hashes(f['input_sha256']);check_seals(out,freeze_sha)
        assert {p.name for p in out.iterdir()}==set(OUTPUTS)
        hashes=io.hashes(out.iterdir());size=sum(Path(k).stat().st_size for k in hashes)
        assert size<source.ALLOWANCE;source.resources()
        done=dict(status='COMPLETE',completed_utc=source.utc_now(),seconds=time.monotonic()-start,
            freeze_sha256=freeze_sha,manifest_sha256=source.sha256_file(run/'MANIFEST.json'),
            output_sha256=hashes,output_bytes=size,new_fits=153,new_forecasts=57600,new_dynamics=0,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT)
        return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit():
    source.resources();f=frozen();stage_guard(f,'audit');run,out=paths();assert not audit_path().exists()
    start=time.monotonic();done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and manifest['input_sha256']==f['input_sha256']
    assert done['freeze_sha256']==manifest['freeze_sha256']==source.sha256_file(freeze_path())
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    assert set(done['output_sha256'])=={str(out/k) for k in OUTPUTS}
    source.check_hashes(done['output_sha256']);seals=check_seals(out,done['freeze_sha256'])
    proof=verify(io.read_json(out/'models.json'),load_panels(out),io.read_json(out/'summary.json'),scored_inputs())
    assert proof==io.read_json(out/'verification.json')
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-start,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,seals=seals,
        new_fits=0,new_forecasts=0,independent_objectives_resolved=153,new_dynamics=0,
        source_scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return result


def detach(stage):
    source.resources();f=frozen();assert stage in ('execute','audit');run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists();env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.shared_decoder_run',stage],
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
