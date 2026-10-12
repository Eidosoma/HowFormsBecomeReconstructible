"""D168 qualified write-once saved-feedback extraction and separate audit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import passive_stages_run as previous, passive_feedback as m, passive_feedback_check as check

source=previous.source;io=source.io;ROOT=source.ROOT;WS=source.WS;IDS=previous.IDS
RUN='l20_extension1_passive_feedback_v1_attempt1';OLD=previous.RUN;ENV='D168_DETACHED_STAGE'
COMPLETE='f77af997a198b1fae48ca9cbce96dfa64eb746ce635de08d8f777d7737a2aa99'
AUDIT='5e652602b46f3d84cacf6cc32d485387b95e6eb3610b82f222b9ccc9ce972d0d'
GEOMETRY='c9a4879486353f58783e62f809e2852940282a59f69a17c8f46fb917688c78f6'
OUTPUTS=('geometry.npz','summary.json','verification.json')


def science():
    return [WS/'passive-feedback/PROTOCOL_V1.md',WS/'tests/test_passive_feedback.py']+[
        WS/'src/l20_extension1'/f'{k}.py' for k in ('passive_feedback','passive_feedback_check','passive_feedback_run')]


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
    assert manifest['input_sha256']==f['input_sha256'] and len(f['input_sha256'])==291
    assert audit['verification']['measurements']==614400 and audit['verification']['summary']['all_cases_retained']
    assert set(done['output_sha256'])=={str(out/k) for k in ('stages.npz','summary.json','verification.json')}
    for path,digest in {**f['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    geo=ROOT/'analyses/d143_saved_geometry_v2';source.bind(geo/'COMPLETE.json',GEOMETRY,seen)
    gc=io.read_json(geo/'COMPLETE.json');assert gc['status']=='COMPLETE' and gc['new_dynamics']==0
    source.bind(geo/'FREEZE.json',gc['output_sha256']['FREEZE.json'],seen);gf=io.read_json(geo/'FREEZE.json')
    assert len(gf['analysis_inputs'])==4 and gf['qualification_tests']==77
    for path,digest in gf['analysis_inputs'].items():source.bind(Path(path),digest,seen)
    source.bind(Path(gf['qualification_report']),gf['qualification_sha256'],seen)
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        p=Path(file).resolve()
        if WS.parent in p.parents and p.suffix=='.py' and p not in fresh:
            assert str(p) in seen,'unbound imported repository code: '+str(p)
    return seen


def saved_stages():
    arrays=io.load_npz(ROOT/'outputs'/OLD/'stages.npz')
    previous.m.validate_panel(arrays,*[np.asarray(IDS[k],dtype=np.int64) for k in ('development','pilot')])
    return arrays


def calculate(saved=None):
    stages=saved_stages();arrays={};proofs=[]
    if saved is not None:assert set(saved)=={co+'_'+k for co in IDS for k in m.SHAPES}
    for co,ids in IDS.items():
        rows=[]
        for j,index in enumerate(ids):
            a,b=previous.raw_paths(co,index);raw=previous.load_raw(a);meta=io.read_json(b)
            previous.metadata(raw,meta,co,index)
            old={k:stages[co+'_'+k][j] for k in ('fields','preference')}
            got=m.extract(raw,old) if saved is None else {k:saved[co+'_'+k][j] for k in m.SHAPES}
            m.validate(got);proofs.append(dict(cohort=co,index=index,**check.block(raw,got,old)));rows.append(got)
        for k in m.SHAPES:arrays[co+'_'+k]=np.stack([r[k] for r in rows])
    return arrays,proofs


def parts(arrays):
    assert set(arrays)=={co+'_'+k for co in IDS for k in m.SHAPES}
    return [{k:arrays[co+'_'+k] for k in m.SHAPES} for co in ('development','pilot')]+[
        np.asarray(IDS[co],dtype=np.int64) for co in ('development','pilot')]


def bridge(summary):
    old=io.read_json(ROOT/'outputs'/OLD/'summary.json')
    field={(r['group'],r['stage'],r['metric']):r for r in old['field_rows']}
    pref={(r['group'],r['time']):r for r in old['preference_rows']};count=0
    for row in summary['mixture_rows']:
        co,g,name=row['cohort'],row['group'],row['response']
        if name.startswith('write_R_change:'):
            t=int(name.split(':')[1]);want=field[(g,f'write:{t}:R','own_best')][co]['gap_mean']-field[(g,'write:0:R','own_best')][co]['gap_mean']
        elif name=='final_preference':want=pref[(g,300)][co]['gap_mean']
        else:want=field[(g,'outgoing','own_best' if name=='outgoing_own' else 'guide_margin')][co]['gap_mean']
        check.same(row['gap'],want);count+=1
    assert count==56
    return dict(passes=True,d167_group_response_gaps=count,outcomes_used=False)


def verify(arrays,summary,proofs):
    return dict(passes=True,blocks=proofs,summary=check.summary(summary,*parts(arrays)),bridge=bridge(summary),
        geometry_values=66560,validity_flags=61440,responses=17920,diagnostic_copies=2560,
        maximum_error=max(p['max_error'] for p in proofs),outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d168_') and path.suffix=='.xml' and not path.is_symlink()
    root=ET.parse(path).getroot();cases=root.findall('.//testcase')
    assert len(cases)>=35 and not any(root.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_panel_roundtrip','test_all_legal_shifts','test_masked_zero','test_next_step_checkpoint',
        'test_mixture_cancellation','test_copy_reversal','test_empty_levels','test_corruption','test_stage_guard',
        'test_no_outcomes_or_dynamics'}<=names
    full=[c for c in cases if c.get('name')=='test_full_panel_roundtrip'];assert len(full)==1
    props={p.get('name'):p.get('value') for p in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['founders']=='80' and props['geometry_values']=='66560' and props['summary_rows']=='608'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def freeze(report):
    source.resources();assert not freeze_path().exists() and not any(p.exists() for p in paths())
    proof=qualification(report);start=time.monotonic();inputs=source_inputs();elapsed=time.monotonic()-start
    inputs.update(io.hashes(science()+[Path(proof['path'])]));budget=3*proof['full_panel_seconds']+4*elapsed+120
    f=dict(schema='d168_passive_feedback_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=elapsed,stage_budget_seconds=budget,must_detach=budget>600,
        environment=source.environment_manifest(),post_test_description=True,outcomes_used=False,new_fits=0,new_forecasts=0,
        new_dynamics=0,allowance=source.ALLOWANCE,reserve=source.RESERVE,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        source_scope='D167 audited closure plus D143 frozen geometry definitions; saved diagnostics only, no actual outcomes or new physics')
    io.write_json(freeze_path(),f,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d168_passive_feedback_freeze_v1' and f['run']==RUN
    assert f['new_fits']==f['new_forecasts']==f['new_dynamics']==0 and f['outcomes_used'] is False
    assert f['allowance']==source.ALLOWANCE and f['reserve']==source.RESERVE
    budget=3*f['qualification']['full_panel_seconds']+4*f['source_hash_seconds']+120
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
        arrays,proofs=calculate();summary=m.summarize(*parts(arrays));proof=verify(arrays,summary,proofs)
        io.write_npz(out/'geometry.npz',arrays,ROOT);io.write_json(out/'summary.json',summary,ROOT)
        saved=io.load_npz(out/'geometry.npz');check.same(saved,arrays)
        assert verify(saved,io.read_json(out/'summary.json'),proofs)==proof
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
    source.check_hashes(done['output_sha256']);arrays,proofs=calculate(io.load_npz(out/'geometry.npz'))
    proof=verify(arrays,io.read_json(out/'summary.json'),proofs);check.same(proof,io.read_json(out/'verification.json'))
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-start,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,
        outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,source_scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return {k:v for k,v in result.items() if k!='verification'}


def detach(stage):
    source.resources();f=frozen();assert stage in ('execute','audit');run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists();env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.passive_feedback_run',stage],
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
