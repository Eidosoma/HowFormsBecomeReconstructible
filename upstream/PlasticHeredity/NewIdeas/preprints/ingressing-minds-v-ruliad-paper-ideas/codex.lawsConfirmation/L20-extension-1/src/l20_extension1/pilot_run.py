"""D162 single-use 64-founder pilot; separate qualification/benchmark/launch gates."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
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
from laws_confirmation import l15_repair_speed_run as io
from laws_confirmation.io import sha256_file, utc_now, environment_manifest, atomic_json
from . import diagnostics as dev, development_run, confirmation_plan as planning, influence_run
from . import pilot_system as system, pilot_lineage_audit as lineage_check
from . import pilot_diagnostics as diagnostic, pilot_diagnostic_audit as diagnostic_check
from . import pilot_probe as probe, pilot_probe_audit as probe_check
from . import pilot_repeated as repeated, pilot_repeat_audit as repeated_check
from . import pilot_models as models, pilot_analysis as analysis, recovery_check

ROOT=dev.ROOT;WS=dev.WS;RUN='l20_extension1_pilot64_v1_attempt1'
WORKERS=6;ALLOWANCE=8*1024**3;RESERVE=4*1024**3
ENV='L20_PILOT64_DETACHED';READY='D162_READY_FD'
SOURCE='d84b61f0eb6ba109cb2822f23685ce068cdf21ce1a55fdf8cde1df5b3bdedfe1'
KINDS=('founder','diagnostic','targeted','lineage','repeated')
NEW_MODULES=('system','lineage_audit','diagnostics','diagnostic_audit','probe','probe_audit',
    'repeated','repeat_audit','models','analysis','run')


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def model_path():return ROOT/'tmp'/f'{RUN}_models.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def log_path(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    development_run.preflight(False)
    if sys.flags.optimize:raise RuntimeError('audit assertions required')
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external allowance and reserve required')


def contract():
    return dict(run=RUN,blocks=list(system.TISSUES),disposable=system.DISPOSABLE,primary_cases=1024,
        terminal_primary_outcomes=4096,diagnostic_cycles=6144,futures=4,workers=6,threads=1,
        alpha=.01,primary=['tied:sham_minus','tied:passive'],selected=models.SELECTED,models=51,
        namespace='l20-extension1-pilot64-v1',bootstrap_seed=16120260920,bootstrap_draws=20000,
        allowance=ALLOWANCE,reserve=RESERVE,all_forecasts_before_any_outcome=True,
        controls_future0_only=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)


def science_files():
    return [WS/'confirmation/PILOT64_PROTOCOL_V1.md',WS/'tests/test_pilot64.py',WS/'scripts/run_pilot64.sh']+[
        WS/'src/l20_extension1'/f'pilot_{k}.py' for k in NEW_MODULES]


def source_inputs():
    directory=ROOT/'outputs'/planning.RUN;c=io.read_json(directory/'COMPLETE.json')
    assert sha256_file(directory/'COMPLETE.json')==SOURCE and c['status']=='DESIGN_COMPLETE'
    expected={**c['source_sha256'],**c['output_sha256'],c['qualification']['path']:c['qualification']['sha256']}
    assert expected==io.hashes([Path(k) for k in expected])
    assert io.read_json(directory/'planning.json')['common_alpha']==.01
    files=[directory/'COMPLETE.json',*science_files()]
    return {**expected,**io.hashes(files)}


def collision_check():
    """Read retained scientific paths, not arbitrary numbers in test source text."""
    matches=[]
    for root in (ROOT/'outputs',ROOT/'tmp',ROOT.parent/'outputs',ROOT.parent/'tmp'):
        for kind in ('founder','lineage','diagnostic'):
            for path in root.glob('*/'+kind+'_1000*.npz'):
                try:index=int(path.stem.rsplit('_',1)[1])
                except ValueError:continue
                if index in system.TISSUES:matches.append(str(path))
    if matches:raise RuntimeError('proposed founder IDs already used: '+repr(matches))
    identity_keys={'founder_ids','founder_id','block_ids','blocks','test_blocks','founder_blocks','tissues','indices','ids'}
    def declared_ids(value,active=False):
        if isinstance(value,dict):
            return set().union(*(declared_ids(v,active or k in identity_keys) for k,v in value.items()))
        if isinstance(value,list):return set().union(*(declared_ids(v,active) for v in value))
        return {value} if active and type(value) is int else set()
    manifests=0
    for root in (ROOT/'runs',ROOT.parent/'runs'):
        for path in root.glob('*/MANIFEST.json'):
            if RUN in str(path):continue
            content=path.read_text();metadata=json.loads(content);manifests+=1
            if 'l20-extension1-pilot64-v1' in content:raise RuntimeError('namespace already used: '+str(path))
            if declared_ids(metadata)&set(system.TISSUES):raise RuntimeError('declared founder IDs already used: '+str(path))
    return dict(passes=True,founder_ids=list(system.TISSUES),namespace='l20-extension1-pilot64-v1',manifests_checked=manifests)


def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=35 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    required={'test_complete_disposable_life','test_full_source_adapter_contract','test_future0_bridge',
        'test_independent_models','test_original_label_isolation','test_feature_boundaries','test_control_normalization',
        'test_forecast_barrier','test_barrier_tampering','test_resource_guards','test_no_successor','test_roundtrip',
        'test_summary_corruption','test_saved_physics_corruption','test_phase_separation','test_startup_ack'}
    names={c.get('name','').split('[',1)[0] for c in cases};assert required<=names
    case=next(c for c in cases if c.get('name')=='test_complete_disposable_life')
    seconds=float(next(p.get('value') for p in case.findall('./properties/property') if p.get('name')=='complete_life_seconds'))
    assert seconds>0
    return dict(path=str(path),tests=len(cases),failures=0,complete_life_seconds=seconds,benchmark_forecast=4*seconds+180)


def training_data():
    data,_,_=influence_run.source_data();np.testing.assert_array_equal(data['block_ids'],np.arange(90000,90016,dtype=np.int64))
    return data


def freeze(report):
    resources();proof=qualification(report)
    if any(p.exists() for p in (freeze_path(),model_path(),timing_path(),benchmark_dir(),*paths())):raise FileExistsError('single-use pilot preparation')
    tick=time.monotonic();inputs=source_inputs();inputs.update(io.hashes([report]));collision=collision_check()
    data=training_data();fitted=models.fit_all(data);checked=models.check_models(fitted,data)
    assert inputs==io.hashes([Path(p) for p in inputs])
    io.write_json(model_path(),dict(fitted=fitted,verification=checked,source_sha256=inputs,
        sealed_utc=utc_now(),test_founders_generated=0),ROOT)
    value=dict(frozen_utc=utc_now(),contract=contract(),qualification=proof,input_sha256=inputs,
        environment=environment_manifest(),model_sha256=sha256_file(model_path()),collision_check=collision,
        source_hash_and_model_seconds=time.monotonic()-tick,test_founders_generated=0)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',models=51,inputs=len(inputs),benchmark_forecast=proof['benchmark_forecast'],
        model_sha256=value['model_sha256'],test_founders_generated=0)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    assert f['test_founders_generated']==0 and f['model_sha256']==sha256_file(model_path())
    expected=source_inputs();expected.update(io.hashes([Path(f['qualification']['path'])]))
    assert f['input_sha256']==expected and f['qualification']==qualification(Path(f['qualification']['path']))
    m=io.read_json(model_path());assert m['source_sha256']==expected and m['test_founders_generated']==0
    return f


def fitted_models():
    assert sha256_file(model_path())==io.read_json(freeze_path())['model_sha256']
    return io.read_json(model_path())['fitted']


def valid_ids(ids):
    ids=list(ids)
    if ids not in ([system.DISPOSABLE],list(system.TISSUES)):raise ValueError('whole fixed main cohort or disposable block only')
    return ids


def save_block(directory,kind,index,rows,metas):
    if kind not in KINDS or len(rows)!=4 or len(metas)!=4:raise ValueError('complete four-life block')
    raw={k:np.stack([r[k] for r in rows]) for k in rows[0]}
    io.write_npz(directory/f'{kind}_{index}.npz',raw,ROOT)
    io.write_json(directory/f'{kind}_{index}.json',dict(index=index,lives=metas,config=asdict(system.CONFIG)),ROOT)
    return sum(v.nbytes for v in raw.values())


def load_block(directory,kind,index):
    raw=io.load_npz(directory/f'{kind}_{index}.npz');meta=io.read_json(directory/f'{kind}_{index}.json')
    assert meta['index']==index and meta['config']==asdict(system.CONFIG) and len(meta['lives'])==4
    assert all(v.shape[0]==4 for v in raw.values());return raw,meta


def packets(source):return np.stack([np.frombuffer(system.encode(source['written_fields'][r,0]),np.uint8) for r in (0,1)])
def base_meta(meta):return {k:v for k,v in meta.items() if k!='replay'}


def replay_receipt(saved,current,flag):
    assert set(saved)==set(current) and saved[flag] is True
    for k,v in current.items():
        if k==flag:continue
        if k.endswith('_max_abs') or k=='max_abs':assert 0<=saved[k]<=1e-10
        elif k=='maxima':assert all(0<=x<=1e-10 for x in saved[k].values())
        else:recovery_check.same(saved[k],v)


def forecast_worker(directory,index):
    system.validate_index(index)
    if index!=system.DISPOSABLE:
        assert (paths()[0]/'EXECUTION.lock').is_dir();fitted_models()
        assert not (directory/'OUTCOMES_STARTED.json').exists()
    guide=system.load_guide(dev.BASE);cohort='disposable' if index==system.DISPOSABLE else 'heldout'
    sources=[];source_meta=[];plans=[]
    for life in range(4):
        source,meta=system.generate_founders(index,life)
        proof=lineage_check.prior.check_founders(source,meta,system.CONFIG,True,tag=system.TAG)
        meta['replay']=dict(**proof,full_dynamics_replayed=True)
        sources.append(source);source_meta.append(meta)
        _,plan=probe.candidates(packets(source),guide);plans.append(plan)
    size=save_block(directory,'founder',index,sources,source_meta)
    io.write_json(directory/f'packet_plan_{index}.json',dict(index=index,plans=plans,created_utc=utc_now()),ROOT)
    rows=[];metas=[];edited=[];edmeta=[]
    for life in range(4):
        raw,meta=diagnostic.simulate_life(cohort,index,life,packets(sources[life]),guide)
        meta['replay']=diagnostic_check.check_life(raw,meta,packets(sources[life]),guide,True)
        new,entry=probe.simulate_life((cohort,index),life,packets(sources[life]),guide,plans[life])
        proof=probe_check.check_life(new,entry,raw,meta,True);entry['replay']=dict(**proof,full_dynamics_replayed=True)
        rows.append(raw);metas.append(meta);edited.append(new);edmeta.append(entry)
    size+=save_block(directory,'diagnostic',index,rows,metas)+save_block(directory,'targeted',index,edited,edmeta)
    check_forecast_block(directory,index)
    return dict(index=index,uncompressed_bytes=size,diagnostic_cycles=96,full_physics_replayed=True)


def check_forecast_block(directory,index):
    s,sm=load_block(directory,'founder',index);d,dm=load_block(directory,'diagnostic',index);p,pm=load_block(directory,'targeted',index)
    guide=system.load_guide(dev.BASE);plans=io.read_json(directory/f'packet_plan_{index}.json')
    assert plans['index']==index and len(plans['plans'])==4
    for life in range(4):
        source={k:v[life] for k,v in s.items()};meta=sm['lives'][life]
        assert (meta['index'],meta['life'],meta['tag'])==(index,life,system.TAG)
        fp=lineage_check.prior.check_founders(source,base_meta(meta),system.CONFIG,False,tag=system.TAG)
        replay_receipt(meta['replay'],dict(**fp,full_dynamics_replayed=False),'full_dynamics_replayed')
        dr={k:v[life] for k,v in d.items()};pr={k:v[life] for k,v in p.items()}
        assert dm['lives'][life]['index']==index and dm['lives'][life]['life']==life
        proof=diagnostic_check.check_life(dr,dm['lives'][life],packets(source),guide,False)
        replay_receipt(dm['lives'][life]['replay'],proof,'full_dynamics_replayed')
        proof=probe_check.check_life(pr,pm['lives'][life],dr,dm['lives'][life],False)
        current=dict(**proof,full_dynamics_replayed=False);current['replayed_cycles']=12
        replay_receipt(pm['lives'][life]['replay'],current,'full_dynamics_replayed')
        assert [[c['plan'] for c in row] for row in pm['lives'][life]['cells']]==plans['plans'][life]
    measured=models.extract(d,p)
    return measured


def forecast_files(ids):
    return [f'{k}_{i}.{ext}' for i in ids for k in KINDS[:3] for ext in ('npz','json')]+[f'packet_plan_{i}.json' for i in ids]


def seal_forecasts(directory,ids):
    ids=valid_ids(ids);m=fitted_models();blocks=[check_forecast_block(directory,i) for i in ids]
    data={k:np.stack([b[k] for b in blocks]) for k in blocks[0]}
    p,raw=models.predict(m,data);proof=models.check_predictions(p,raw,m,data)
    io.write_npz(directory/'features.npz',data,ROOT);io.write_npz(directory/'forecasts.npz',p,ROOT)
    io.write_npz(directory/'raw_forecasts.npz',raw,ROOT)
    names=forecast_files(ids)+['features.npz','forecasts.npz','raw_forecasts.npz']
    seal=dict(sealed_utc=utc_now(),ids=ids,cases=len(ids)*16,forecasts=len(ids)*16*51,
        model_sha256=sha256_file(model_path()),freeze_sha256=sha256_file(freeze_path()),
        file_sha256=io.hashes([directory/n for n in names]),verification=proof,actual_lineages_started=0)
    io.write_json(directory/'FORECAST_SEAL.json',seal,ROOT)
    return sha256_file(directory/'FORECAST_SEAL.json')


def barrier(directory,seal_hash,index=None):
    assert sha256_file(directory/'FORECAST_SEAL.json')==seal_hash
    seal=io.read_json(directory/'FORECAST_SEAL.json');ids=valid_ids(seal['ids'])
    assert seal['cases']==16*len(ids) and seal['forecasts']==816*len(ids) and seal['actual_lineages_started']==0
    assert seal['model_sha256']==sha256_file(model_path()) and seal['freeze_sha256']==sha256_file(freeze_path())
    expected=seal['file_sha256'];names=forecast_files(ids)+['features.npz','forecasts.npz','raw_forecasts.npz']
    assert set(expected)=={str(directory/n) for n in names}
    if index is None:assert expected==io.hashes([Path(p) for p in expected])
    else:
        assert index in ids
        subset=[directory/f'founder_{index}.{ext}' for ext in ('npz','json')]+[directory/'forecasts.npz']
        assert io.hashes(subset)=={str(p):expected[str(p)] for p in subset}
    return seal


def outcome_worker(directory,index,seal_hash):
    seal=barrier(directory,seal_hash,index)
    started=io.read_json(directory/'OUTCOMES_STARTED.json')
    assert started['forecast_seal_sha256']==seal_hash and started['started_utc']>=seal['sealed_utc']
    sources,smeta=load_block(directory,'founder',index);guide=system.load_guide(dev.BASE)
    rows=[];entries=[];extra=[];extra_meta=[]
    for life in range(4):
        source={k:v[life] for k,v in sources.items()};meta=base_meta(smeta['lives'][life])
        raw,entry=system.simulate_life(index,life,guide,source,meta)
        entry['replay']=lineage_check.check_life(raw,entry,system.CONFIG,guide,True)
        rows.append(raw);entries.append(entry);parts=[];partmeta=[]
        for future in (1,2,3):
            r,m=repeated.simulate(index,life,future,packets(source),guide)
            m['replay']=repeated_check.check(r,m,packets(source),guide,True);parts.append(r);partmeta.append(m)
        extra.append({k:np.stack([r[k] for r in parts]) for k in parts[0]});extra_meta.append(partmeta)
    size=save_block(directory,'lineage',index,rows,entries)+save_block(directory,'repeated',index,extra,extra_meta)
    check_outcome_block(directory,index)
    return dict(index=index,uncompressed_bytes=size,primary_outcomes=64,full_physics_replayed=True)


def check_outcome_block(directory,index):
    s,sm=load_block(directory,'founder',index);raw,meta=load_block(directory,'lineage',index)
    extra,em=load_block(directory,'repeated',index);guide=system.load_guide(dev.BASE);y=np.empty((4,4,4))
    for life in range(4):
        source={k:v[life] for k,v in s.items()};r={k:v[life] for k,v in raw.items()};m=meta['lives'][life]
        assert (m['index'],m['life'])==(index,life)
        for key in system.FOUNDER_KEYS:np.testing.assert_array_equal(r['f_'+key],source[key])
        recovery_check.same(m['founder'],base_meta(sm['lives'][life]))
        proof=lineage_check.check_life(r,m,system.CONFIG,guide,False)
        replay_receipt(m['replay'],proof,'full_life_replay')
        for ci,(role,kind) in enumerate(repeated.CASES):
            v=r['terminal_states'][system.PROBES.index((role,kind)),-1,0]
            y[life,ci,0]=diagnostic_check.terminal_features(v,role)[0]
        assert len(em['lives'][life])==3
        for fi,future in enumerate((1,2,3)):
            er={k:v[life,fi] for k,v in extra.items()};entry=em['lives'][life][fi]
            assert (entry['index'],entry['life'],entry['future'])==(index,life,future)
            proof=repeated_check.check(er,entry,packets(source),guide,False)
            replay_receipt(entry['replay'],proof,'full_dynamics_replayed')
            for ci,(role,_) in enumerate(repeated.CASES):y[life,ci,future]=diagnostic_check.terminal_features(er['terminal_states'][ci,-1,0],role)[0]
    # Keep only small observation arrays for all-cohort scoring.
    control={k:raw[k] for k in ('values','terminal_values','targets')}
    return y,control


def score_saved(directory,ids):
    blocks=[check_outcome_block(directory,i) for i in ids];y=np.stack([b[0] for b in blocks]);controls=[b[1] for b in blocks]
    p=io.load_npz(directory/'forecasts.npz');raw=io.load_npz(directory/'raw_forecasts.npz')
    s=analysis.summarize(p,raw,y,ids);proof=analysis.check_summary(s,p,raw,y,ids)
    c=system.summarize(controls,ids=ids);assert lineage_check.check_summary(c,controls,system.CONFIG,ids=ids)
    return dict(prediction=s,controls=c),dict(prediction=proof,controls=True,saved_audit_new_dynamics=0),y


def ready(stage):
    descriptor=os.environ.pop(READY,None)
    if descriptor is not None:
        fd=int(descriptor)
        try:os.write(fd,json.dumps(dict(stage=stage,pid=os.getpid(),status='STARTED')).encode())
        except BrokenPipeError:pass
        finally:os.close(fd)


def detached_guard(required,stage):
    if required and os.environ.get(ENV)!='1':raise RuntimeError('forecast above ten minutes requires detached stage')
    if os.environ.get(ENV)=='1':
        assert os.getpid()==os.getsid(0) and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==log_path(stage)
        assert os.readlink('/proc/self/fd/2')==os.readlink('/proc/self/fd/1')


def benchmark():
    resources();f=frozen();detached_guard(f['qualification']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir();ready('benchmark');tick=time.monotonic()
    try:
        first=forecast_worker(directory,system.DISPOSABLE);seal=seal_forecasts(directory,[system.DISPOSABLE])
        barrier(directory,seal);io.write_json(directory/'OUTCOMES_STARTED.json',dict(started_utc=utc_now(),forecast_seal_sha256=seal),ROOT)
        second=outcome_worker(directory,system.DISPOSABLE,seal)
        summary,proof,y=score_saved(directory,[system.DISPOSABLE]);io.write_json(directory/'summary.json',summary,ROOT)
        io.write_json(directory/'verification.json',proof,ROOT);io.write_npz(directory/'outcomes.npz',dict(outcomes=y),ROOT)
        assert score_saved(directory,[system.DISPOSABLE])[0]==summary
        seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());raw_size=first['uncompressed_bytes']+second['uncompressed_bytes']
        forecast=1.25*64*seconds+2*hash_seconds+600;budget=2*64*raw_size+size+512*1024**2
        if budget>ALLOWANCE:raise RuntimeError('measured storage exceeds 8 GiB pilot gate')
        t=dict(status='COMPLETE',completed_utc=utc_now(),scientific_evidence=False,main_founders_generated=0,
            checked_block_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,must_detach=forecast>600,
            projected_bytes=budget,uncompressed_block_bytes=raw_size,benchmark_bytes=size,
            freeze_sha256=sha256_file(freeze_path()),artifact_sha256=io.hashes(list(directory.iterdir())),
            forecast_proof=first,outcome_proof=second,verification=proof,automatic_successor=False)
        io.write_json(timing_path(),t,ROOT);print(json.dumps({k:v for k,v in t.items() if k!='artifact_sha256'},indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def timing_checked():
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is False and t['main_founders_generated']==0
    assert t['freeze_sha256']==sha256_file(freeze_path()) and not (benchmark_dir()/'FAILED.json').exists()
    assert t['artifact_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['projected_seconds']==1.25*64*t['checked_block_seconds']+2*t['hash_seconds']+600
    assert t['projected_bytes']==2*64*t['uncompressed_block_bytes']+t['benchmark_bytes']+512*1024**2<=ALLOWANCE
    assert t['must_detach']==(t['projected_seconds']>600)
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(k) for k in f['input_sha256']]+[model_path(),freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def prepare():
    resources();frozen();t=timing_checked();run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use pilot already prepared')
    collision=collision_check();pin=inputs()
    run.mkdir();out.mkdir()
    m=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,environment=environment_manifest(),
        timing=t,collision_check=collision,model_sha256=sha256_file(model_path()),main_founders_generated=0)
    io.write_json(run/'MANIFEST.json',m,ROOT);atomic_json(run/'STATUS.json',dict(status='PREPARED',run=RUN),ROOT)
    print(json.dumps(dict(status='PREPARED',forecast_seconds=t['projected_seconds'],projected_bytes=t['projected_bytes'])),flush=True)


def prepared():
    m=io.read_json(paths()[0]/'MANIFEST.json');assert m['contract']==contract() and m['environment']==environment_manifest()
    assert m['input_sha256']==inputs() and m['model_sha256']==sha256_file(model_path()) and m['main_founders_generated']==0
    assert m['timing']==timing_checked();return m


def pool_phase(worker,directory,run,seal=None):
    done=[]
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
        jobs={pool.submit(worker,directory,i,*(() if seal is None else (seal,))):i for i in system.TISSUES}
        for future in as_completed(jobs):
            done.append(future.result());atomic_json(run/'STATUS.json',dict(status='FORECASTS' if seal is None else 'OUTCOMES',
                completed_blocks=sorted(d['index'] for d in done),updated_utc=utc_now()),ROOT)
    return sorted(done,key=lambda x:x['index'])


def output_names():
    return [f'{k}_{i}.{ext}' for i in system.TISSUES for k in KINDS for ext in ('npz','json')]+[
        f'packet_plan_{i}.json' for i in system.TISSUES]+['features.npz','forecasts.npz','raw_forecasts.npz',
        'FORECAST_SEAL.json','OUTCOMES_STARTED.json','outcomes.npz','summary.json','verification.json']


def saved_audit(final=True):
    resources(False);run,out=paths();m=prepared();seal_hash=sha256_file(out/'FORECAST_SEAL.json');seal=barrier(out,seal_hash)
    receipt=io.read_json(out/'OUTCOMES_STARTED.json');assert receipt['forecast_seal_sha256']==seal_hash
    assert receipt['started_utc']>=seal['sealed_utc']>=m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc']
    blocks=[check_forecast_block(out,i) for i in system.TISSUES]
    expected={k:np.stack([b[k] for b in blocks]) for k in blocks[0]};data=io.load_npz(out/'features.npz')
    for k in expected:np.testing.assert_array_equal(data[k],expected[k])
    p=io.load_npz(out/'forecasts.npz');raw=io.load_npz(out/'raw_forecasts.npz')
    pp=models.check_predictions(p,raw,fitted_models(),data)
    summary,proof,y=score_saved(out,list(system.TISSUES))
    recovery_check.same(io.read_json(out/'summary.json'),summary)
    np.testing.assert_array_equal(io.load_npz(out/'outcomes.npz')['outcomes'],y)
    assert io.read_json(out/'verification.json')['saved_checks']==proof
    if final:
        c=io.read_json(run/'COMPLETE.json');assert c==io.read_json(run/'STATUS.json') and not (run/'FAILED.json').exists()
        assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['status']=='COMPLETE'
        assert c['output_sha256']==io.hashes([out/n for n in output_names()])
        assert set(p.name for p in out.iterdir())==set(output_names())|{'output_hashes.sha256'}
        assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
        assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=len(output_names()),founders=64,
        primary_cases=1024,forecasts=pp['forecasts'],primary_outcomes=4096,new_dynamics=0,
        diagnostic_cycles=6144,full_control_panel_retained=True,all_cases_retained=True)


def execute():
    resources();m=prepared();t=m['timing'];detached_guard(t['must_detach'],'execute');run,out=paths()
    if any((run/n).exists() for n in ('EXECUTION.lock','COMPLETE.json','FAILED.json')):raise FileExistsError('single-use stage')
    assert io.read_json(run/'STATUS.json')['status']=='PREPARED'
    (run/'EXECUTION.lock').mkdir();ready('execute');tick=time.monotonic()
    try:
        forecasts=pool_phase(forecast_worker,out,run);seal=seal_forecasts(out,system.TISSUES);barrier(out,seal)
        io.write_json(out/'OUTCOMES_STARTED.json',dict(started_utc=utc_now(),forecast_seal_sha256=seal),ROOT)
        outcomes=pool_phase(outcome_worker,out,run,seal)
        summary,proof,y=score_saved(out,list(system.TISSUES))
        io.write_json(out/'summary.json',summary,ROOT);io.write_npz(out/'outcomes.npz',dict(outcomes=y),ROOT)
        io.write_json(out/'verification.json',dict(forecasts=forecasts,outcomes=outcomes,saved_checks=proof),ROOT)
        saved_audit(False);assert inputs()==m['input_sha256'];resources(False)
        indexed=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as f:f.write(io.hash_text(indexed))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',run=RUN,completed_utc=utc_now(),seconds=time.monotonic()-tick,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=indexed,
            hash_index_sha256=sha256_file(out/'output_hashes.sha256'),model_sha256=sha256_file(model_path()),
            forecast_seal_sha256=seal,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k!='output_sha256'},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),utc=utc_now()),ROOT);raise


def audit():
    t=timing_checked();detached_guard(t['must_detach'],'audit');ready('audit');tick=time.monotonic();proof=saved_audit()
    receipt=dict(**proof,checked_utc=utc_now(),seconds=time.monotonic()-tick,complete_sha256=sha256_file(paths()[0]/'COMPLETE.json'))
    io.write_json(ROOT/'logs'/f'{RUN}_saved_audit_v1.json',receipt,ROOT);print(json.dumps(receipt,indent=2),flush=True)


def detach(stage):
    resources()
    if stage=='benchmark':frozen();assert not benchmark_dir().exists() and not timing_path().exists()
    elif stage=='execute':prepared();assert io.read_json(paths()[0]/'STATUS.json')['status']=='PREPARED' and not (paths()[0]/'EXECUTION.lock').exists()
    elif stage=='audit':assert (paths()[0]/'COMPLETE.json').exists() and not (ROOT/'logs'/f'{RUN}_saved_audit_v1.json').exists()
    else:raise ValueError('one explicitly selected stage')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir();env=os.environ.copy();env[ENV]='1'
    readfd,writefd=os.pipe();env[READY]=str(writefd)
    command=[sys.executable,'-m','l20_extension1.pilot_run','--'+stage]
    try:
        with log_path(stage).open('xb') as log:
            child=subprocess.Popen(command,cwd=WS.parent,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=True,pass_fds=(writefd,))
    finally:os.close(writefd)
    readable,_,_=select.select([readfd],[],[],55);payload=os.read(readfd,4096) if readable else b'';os.close(readfd)
    ack=json.loads(payload) if payload else None
    if ack is not None:assert ack==dict(stage=stage,pid=child.pid,status='STARTED')
    receipt=dict(status='DETACHED',stage=stage,pid=child.pid,launched_utc=utc_now(),log=str(log_path(stage)),
        startup_acknowledged=ack is not None,automatic_polling=False,automatic_retry=False,automatic_successor=False,
        completion=str(timing_path() if stage=='benchmark' else paths()[0]/'COMPLETE.json'),
        failure=str(benchmark_dir()/'FAILED.json' if stage=='benchmark' else paths()[0]/'FAILED.json'))
    io.write_json(lock/'LAUNCH.json',receipt,ROOT);print(json.dumps(receipt,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--test-report',type=Path)
    choice=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','prepare','execute','audit','detach-benchmark','detach-execute','detach-audit'):
        choice.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze!=(args.test_report is not None):parser.error('test report only for freeze')
    if args.freeze:freeze(args.test_report)
    elif args.benchmark:benchmark()
    elif args.prepare:prepare()
    elif args.execute:execute()
    elif args.audit:audit()
    else:detach('benchmark' if args.detach_benchmark else 'execute' if args.detach_execute else 'audit')


if __name__=='__main__':main()
