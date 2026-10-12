"""D169 write-once qualification/freeze/benchmark/intervention/fresh audit."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import json
import multiprocessing
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import passive_feedback_run as previous, address_swap as m, address_swap_check as check

source=previous.source;io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_address_swap_v1_attempt1';OLD=previous.RUN
COMPLETE='155f95991d4dc718ca6f0a16d0c7e0e8bd5d10de73670449bd363a689facd9e5'
AUDIT='a581f332021deb269ece4fc52cbd7486ec0a859c68d17b6b5a10eea8e870a23e'
IDS={k:v for k,v in m.IDS.items() if k!='disposable'}
ENV='D169_DETACHED_STAGE';READY='D169_READY_FD';WORKERS=6
ALLOWANCE=1024**3;RESERVE=4*1024**3


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'
def log_path(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def science():
    return [WS/'address-swap/PROTOCOL_V1.md',WS/'tests/test_address_swap.py']+[
        WS/'src/l20_extension1'/f'{k}.py' for k in ('address_swap','address_swap_check','address_swap_run')]


def resources():
    source.resources();assert shutil.disk_usage(ROOT).free>=RESERVE+ALLOWANCE


def raw_paths(co,index):
    m.tag(co,index)
    if co!='disposable':return previous.previous.raw_paths(co,index)
    p=ROOT/'tmp'/f'{source.PILOT}_benchmark'/f'diagnostic_{index}.npz'
    return p,p.with_suffix('.json')


def source_inputs():
    seen={};run=ROOT/'runs'/OLD;out=ROOT/'outputs'/OLD
    receipt=ROOT/'logs'/f'{OLD}_saved_audit_v1.json';freeze=ROOT/'tmp'/f'{OLD}_freeze.json'
    source.bind(run/'COMPLETE.json',COMPLETE,seen);source.bind(receipt,AUDIT,seen)
    done=io.read_json(run/'COMPLETE.json');audit=io.read_json(receipt)
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==COMPLETE
    source.bind(freeze,done['freeze_sha256'],seen);source.bind(run/'MANIFEST.json',done['manifest_sha256'],seen)
    f=io.read_json(freeze);manifest=io.read_json(run/'MANIFEST.json')
    assert audit['freeze_sha256']==done['freeze_sha256']==manifest['freeze_sha256']
    assert manifest['input_sha256']==f['input_sha256'] and len(f['input_sha256'])==311
    assert set(done['output_sha256'])=={str(out/k) for k in previous.OUTPUTS}
    for path,digest in {**f['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    # Audited pilot manifest binds the disposable diagnostic and original physics.
    pilot=ROOT/'runs'/source.PILOT/'MANIFEST.json'
    assert str(pilot) in seen
    pm=io.read_json(pilot)['input_sha256']
    for p in raw_paths('disposable',514240):source.bind(p,pm[str(p)],seen)
    m.old.context(514240)  # Resolve production code imports before closure checking.
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        p=Path(file).resolve()
        if WS.parent in p.parents and p.suffix=='.py' and p not in fresh and str(p) not in seen:
            assert str(p) in pm,'unbound imported repository code: '+str(p)
            source.bind(p,pm[str(p)],seen)
    return seen


def load_source(co,index):
    a,b=raw_paths(co,index);raw=previous.previous.load_raw(a);meta=io.read_json(b)
    if co!='disposable':previous.previous.metadata(raw,meta,co,index)
    else:
        assert meta['index']==index and meta['config']==previous.previous.CONFIG and len(meta['lives'])==4
        for life,row in enumerate(meta['lives']):
            assert (row['index'],row['life'],row['host']['index'])==(index,life,index)
            assert row['tag']==m.tag(co,index) and row['cohort']=='disposable'
            assert row['replay']['full_dynamics_replayed'] and row['replay']['diagnostic_cycles']==12
    return raw,meta


def life_source(raw,life):return {k:v[life] for k,v in raw.items()}


def checked_life(raw,meta,co,index,life):
    old=life_source(raw,life);start=old['read_states'][:,:,-1]
    got,entry=m.simulate_life(start,old['shift'],old['guide'],co,index,life)
    proof=check.check_life(got,entry,old,meta['lives'][life],True)
    return got,entry,proof


def block_paths(directory,co,index):
    p=directory/f'block_{co}_{index}.npz';return p,p.with_suffix('.json')


def saved_block(directory,co,index,replay):
    a,b=block_paths(directory,co,index);raw=io.load_npz(a);meta=io.read_json(b)
    m.validate(raw,4);original,om=load_source(co,index)
    assert meta['cohort']==co and meta['index']==index and len(meta['lives'])==len(meta['proofs'])==4
    for life in range(4):
        assert (meta['lives'][life]['cohort'],meta['lives'][life]['index'],meta['lives'][life]['life'])==(co,index,life)
        proof=check.check_life(life_source(raw,life),meta['lives'][life],life_source(original,life),om['lives'][life],replay)
        earlier=meta['proofs'][life]
        assert earlier['full_physics_replayed'] is True
        for key in ('writer_max_abs','reader_max_abs'):assert 0<=earlier[key]<=1e-10
        assert 0<=earlier['response_max_abs']<=2e-10
        if not replay:
            proof['full_physics_replayed']=True
            for k in ('writer_max_abs','reader_max_abs'):proof[k]=earlier[k]
        check.same(proof,earlier)
    return {k:raw[k] for k in ('response','q')},dict(cohort=co,index=index,passes=True,
        full_physics_replayed=bool(replay),writer_paths=64,reader_paths=64,original_paths_reproduced=32,
        aligned_swap_aliases=16,uncompressed_bytes=sum(v.nbytes for v in raw.values()),
        writer_max_abs=max(p['writer_max_abs'] for p in meta['proofs']),
        reader_max_abs=max(p['reader_max_abs'] for p in meta['proofs']))


def worker(directory,co,index,replay_only=False):
    resources();tick=time.monotonic()
    if not replay_only:
        raw,meta=load_source(co,index);rows=[];entries=[];proofs=[]
        for life in range(4):
            got,entry,proof=checked_life(raw,meta,co,index,life)
            rows.append(got);entries.append(entry);proofs.append(proof)
        arrays={k:np.stack([r[k] for r in rows]) for k in m.SHAPES}
        a,b=block_paths(directory,co,index);io.write_npz(a,arrays,ROOT)
        io.write_json(b,dict(cohort=co,index=index,lives=entries,proofs=proofs),ROOT)
        saved=io.load_npz(a)
        for k in arrays:np.testing.assert_array_equal(saved[k],arrays[k])
    values,proof=saved_block(directory,co,index,replay_only)
    proof['full_physics_replayed']=True
    return values,dict(**proof,seconds=time.monotonic()-tick)


def aggregate(rows):
    assert set(rows)=={(co,i) for co,ids in IDS.items() for i in ids}
    return {co:{k:np.stack([rows[co,i][0][k] for i in ids]) for k in ('response','q')} for co,ids in IDS.items()}


def bridge(panels):
    old=io.load_npz(ROOT/'outputs'/OLD/'geometry.npz');count=0
    for co in IDS:
        for c in range(2):
            check.same(panels[co]['response'][:,:,:,c,c],old[co+'_response'][:,:,:,c]);count+=1
        np.testing.assert_array_equal(panels[co]['q'],old[co+'_q'][...,0])
    return dict(passes=True,original_response_arrays=count,original_values=17920,actual_lineage_outcomes_used=False)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d169_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=30 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_complete_disposable_life','test_original_reproduction','test_aligned_control','test_checker_independence',
        'test_full_panel_accounting','test_factorial_identity','test_outcome_isolation','test_corruption',
        'test_stage_guard','test_roundtrip','test_startup_ack'}<=names
    case=next(c for c in cases if c.get('name')=='test_complete_disposable_life')
    props={p.get('name'):p.get('value') for p in case.findall('./properties/property')}
    seconds=float(props['complete_life_seconds']);assert 0<seconds<600 and props['writer_paths']=='16'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),complete_life_seconds=seconds,
        benchmark_budget_seconds=6*seconds+120)


def freeze(report):
    resources();assert not any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths()))
    proof=qualification(report);tick=time.monotonic();inputs=source_inputs();seconds=time.monotonic()-tick
    inputs.update(io.hashes(science()+[Path(proof['path'])]))
    f=dict(schema='d169_address_swap_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=seconds,environment=source.environment_manifest(),
        ids={k:list(v) for k,v in IDS.items()},workers=WORKERS,allowance=ALLOWANCE,reserve=RESERVE,
        actual_lineage_outcomes_used=False,new_founders=0,new_fits=0,new_forecasts=0,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(freeze_path(),f,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],benchmark_budget_seconds=proof['benchmark_budget_seconds'])


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d169_address_swap_freeze_v1' and f['run']==RUN
    assert f['ids']=={k:list(v) for k,v in IDS.items()} and f['workers']==WORKERS
    assert f['allowance']==ALLOWANCE and f['reserve']==RESERVE
    source.check_hashes(f['input_sha256']);seen=source_inputs()
    assert all(f['input_sha256'][k]==v for k,v in seen.items())
    assert all(f['input_sha256'][str(p)]==source.sha256_file(p) for p in science())
    assert f['qualification']==qualification(Path(f['qualification']['path']))
    env=source.environment_manifest()
    for k in ('python','numpy','thread_limits'):assert env[k]==f['environment'][k]
    return f


def stage_guard(required,stage):
    if required:assert os.environ.get(ENV)==stage,'forecast above ten minutes requires detached stage'
    if os.environ.get(ENV)==stage:
        assert os.getsid(0)==os.getpid() and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==log_path(stage)
        assert os.readlink('/proc/self/fd/2')==os.readlink('/proc/self/fd/1')


def ready(stage):
    value=os.environ.pop(READY,None)
    if value is not None:
        fd=int(value)
        try:os.write(fd,json.dumps(dict(stage=stage,pid=os.getpid(),status='STARTED')).encode())
        except BrokenPipeError:pass
        finally:os.close(fd)


def benchmark():
    resources();f=frozen();stage_guard(f['qualification']['benchmark_budget_seconds']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir();ready('benchmark');tick=time.monotonic()
    try:
        values,proof=worker(directory,'disposable',514240)
        # Full four-life data, independently saved-checked; duplicated algebra is
        # explicitly synthetic and never contributes to main scientific summaries.
        panels={co:{k:np.stack([v,v]) for k,v in values.items()} for co in IDS}
        ids={'development':[1,2],'pilot':[3,4]}
        summary=m.summarize(panels,ids);verification=check.check_summary(summary,panels,ids)
        io.write_json(directory/'summary.json',summary,ROOT);io.write_json(directory/'verification.json',verification,ROOT)
        assert check.check_summary(io.read_json(directory/'summary.json'),panels,ids)==verification
        seconds=time.monotonic()-tick;ht=time.monotonic();frozen();hash_seconds=time.monotonic()-ht
        budget=1.5*80*seconds+4*hash_seconds+180
        size=sum(p.stat().st_size for p in directory.iterdir());storage=2*80*proof['uncompressed_bytes']+64*1024**2
        assert storage<=ALLOWANCE,'measured storage exceeds fixed allowance'
        t=dict(status='COMPLETE',completed_utc=source.utc_now(),scientific_evidence=False,
            main_counterfactuals_generated=0,checked_block_seconds=seconds,source_hash_seconds=hash_seconds,
            stage_budget_seconds=budget,must_detach=budget>600,projected_bytes=storage,benchmark_bytes=size,
            uncompressed_block_bytes=proof['uncompressed_bytes'],freeze_sha256=source.sha256_file(freeze_path()),
            artifact_sha256=io.hashes(directory.iterdir()),block_proof=proof,summary_verification=verification,
            workers=WORKERS,parallel_credit_in_budget=False,automatic_successor=False)
        io.write_json(timing_path(),t,ROOT);return {k:v for k,v in t.items() if k!='artifact_sha256'}
    except Exception as exc:io.failure(directory,exc,ROOT);raise


def timing():
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is False
    assert t['main_counterfactuals_generated']==0 and not (benchmark_dir()/'FAILED.json').exists()
    assert t['freeze_sha256']==source.sha256_file(freeze_path())
    assert t['artifact_sha256']==io.hashes(benchmark_dir().iterdir())
    assert t['stage_budget_seconds']==1.5*80*t['checked_block_seconds']+4*t['source_hash_seconds']+180
    assert t['must_detach']==(t['stage_budget_seconds']>600)
    assert t['projected_bytes']==2*80*t['uncompressed_block_bytes']+64*1024**2<=ALLOWANCE
    return t


def input_map(f,t):return {**f['input_sha256'],**io.hashes([freeze_path(),timing_path(),*[Path(p) for p in t['artifact_sha256']]])}


def parallel(directory,replay_only):
    rows={}
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(worker,directory,co,index,replay_only):(co,index) for co,ids in IDS.items() for index in ids}
        for future in as_completed(futures):
            key=futures[future];rows[key]=future.result()
            print(json.dumps(dict(event='BLOCK_AUDITED' if replay_only else 'BLOCK_COMPLETE',
                cohort=key[0],index=key[1],completed=len(rows),total=80,seconds=rows[key][1]['seconds'])),flush=True)
    return rows


def expected_outputs(out):
    return {str(out/k) for k in ('responses.npz','summary.json','verification.json')}|{
        str(p) for co,ids in IDS.items() for index in ids for p in block_paths(out,co,index)}


def execute():
    resources();f=frozen();t=timing();stage_guard(t['must_detach'],'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'single use; preserve failures'
    run.mkdir();out.mkdir();tick=time.monotonic()
    try:
        inputs=input_map(f,t)
        io.write_json(run/'MANIFEST.json',dict(started_utc=source.utc_now(),input_sha256=inputs,
            freeze_sha256=source.sha256_file(freeze_path()),timing_sha256=source.sha256_file(timing_path()),
            environment=source.environment_manifest(),workers=WORKERS,actual_lineage_outcomes_used=False),ROOT)
        ready('execute');rows=parallel(out,False);panels=aggregate(rows)
        summary=m.summarize(panels,IDS);proof=dict(passes=True,summary=check.check_summary(summary,panels,IDS),
            bridge=bridge(panels),blocks=[rows[co,i][1] for co,ids in IDS.items() for i in ids],
            writer_paths=5120,reader_paths=5120,original_paths_reproduced=2560,aligned_swap_aliases=1280,
            all_cases_retained=True,actual_lineage_outcomes_used=False)
        packed={co+'_'+k:v for co,a in panels.items() for k,v in a.items()}
        io.write_npz(out/'responses.npz',packed,ROOT);io.write_json(out/'summary.json',summary,ROOT)
        io.write_json(out/'verification.json',proof,ROOT)
        saved=io.load_npz(out/'responses.npz')
        for k in packed:np.testing.assert_array_equal(saved[k],packed[k])
        assert check.check_summary(io.read_json(out/'summary.json'),panels,IDS)==proof['summary']
        assert {str(p) for p in out.iterdir()}==expected_outputs(out)
        hashes=io.hashes(out.iterdir());size=sum(Path(p).stat().st_size for p in hashes)
        assert size<=t['projected_bytes'] and size<ALLOWANCE;source.check_hashes(inputs);resources()
        done=dict(status='COMPLETE',completed_utc=source.utc_now(),seconds=time.monotonic()-tick,
            manifest_sha256=source.sha256_file(run/'MANIFEST.json'),freeze_sha256=source.sha256_file(freeze_path()),
            output_sha256=hashes,output_bytes=size,actual_lineage_outcomes_used=False,
            writer_paths=5120,reader_paths=5120,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT);return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit_saved():
    resources();f=frozen();t=timing();stage_guard(t['must_detach'],'audit');run,out=paths()
    assert not audit_path().exists();tick=time.monotonic()
    done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    assert done['freeze_sha256']==manifest['freeze_sha256']==source.sha256_file(freeze_path())
    assert manifest['timing_sha256']==source.sha256_file(timing_path()) and manifest['input_sha256']==input_map(f,t)
    assert set(done['output_sha256'])==expected_outputs(out)
    source.check_hashes(done['output_sha256']);ready('audit');rows=parallel(out,True);panels=aggregate(rows)
    packed=io.load_npz(out/'responses.npz')
    for co in IDS:
        for k in ('response','q'):np.testing.assert_array_equal(panels[co][k],packed[co+'_'+k])
    proof=check.check_summary(io.read_json(out/'summary.json'),panels,IDS);original=io.read_json(out/'verification.json')
    assert proof==original['summary'] and bridge(panels)==original['bridge']
    assert len(original['blocks'])==80
    for row,record in zip([rows[co,i][1] for co,ids in IDS.items() for i in ids],original['blocks']):
        check.same({k:v for k,v in row.items() if k!='seconds'},{k:v for k,v in record.items() if k!='seconds'})
    source.check_hashes(manifest['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-tick,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(manifest['input_sha256']),outputs=len(done['output_sha256']),full_physics_replayed=True,
        writer_paths=5120,reader_paths=5120,summary=proof,all_cases_retained=True,
        actual_lineage_outcomes_used=False,automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return result


def detach(stage):
    resources();f=frozen();assert stage in ('benchmark','execute','audit')
    run,out=paths()
    if stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    elif stage=='execute':timing();assert not run.exists() and not out.exists()
    else:timing();assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=log_path(stage);receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists()
    read_fd,write_fd=os.pipe();env=dict(os.environ);env[ENV]=stage;env[READY]=str(write_fd)
    try:
        with log.open('x') as handle:
            child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.address_swap_run',stage],
                stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,
                pass_fds=(write_fd,),env=env,cwd=WS.parent)
        os.close(write_fd);write_fd=None
        readable,_,_=select.select([read_fd],[],[],30)
        payload=os.read(read_fd,4096) if readable else b''
        ack=json.loads(payload) if payload else None
    finally:
        os.close(read_fd)
        if write_fd is not None:os.close(write_fd)
    budget=f['qualification']['benchmark_budget_seconds'] if stage=='benchmark' else timing()['stage_budget_seconds']
    result=dict(launched_utc=source.utc_now(),pid=child.pid,stage=stage,log=str(log),
        startup_ack=ack,stage_budget_seconds=budget,workers=1 if stage=='benchmark' else WORKERS,
        completion=str(timing_path() if stage=='benchmark' else run/'COMPLETE.json' if stage=='execute' else audit_path()),
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(receipt,result,ROOT)
    assert ack==dict(stage=stage,pid=child.pid,status='STARTED'),'startup unconfirmed; retain receipt and log, never auto retry'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('freeze','benchmark','execute','audit','detach-benchmark','detach-execute','detach-audit'))
    parser.add_argument('--test-report',type=Path);args=parser.parse_args()
    if args.stage=='freeze':assert args.test_report is not None;result=freeze(args.test_report)
    elif args.stage.startswith('detach-'):result=detach(args.stage[7:])
    elif args.stage=='benchmark':result=benchmark()
    elif args.stage=='execute':result=execute()
    else:result=audit_saved()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':main()
