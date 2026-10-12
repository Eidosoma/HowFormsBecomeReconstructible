"""D149 qualified competing-axis and matched-sham readouts; no auto successors."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
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
from laws_confirmation.io import atomic_json, environment_manifest, sha256_file, utc_now, git_head
from . import component_system as system, component_audit as audit
from . import component_analysis as analysis, component_analysis_check as independent
from . import repeated_run as predecessor

ROOT = system.ROOT
RUN_ID = 'l20_extension1_competing_component_v1_attempt1'
WORKERS, ALLOWANCE, RESERVE = 6, 2*1024**3, 4*1024**3
DETACHED_ENV = 'L20_COMPONENT_DETACHED'
SCIENCE = ('competing-component/PROTOCOL_V1.md', 'src/l20_extension1/component_system.py',
    'src/l20_extension1/component_audit.py', 'src/l20_extension1/component_analysis.py',
    'src/l20_extension1/component_analysis_check.py', 'src/l20_extension1/component_run.py',
    'tests/test_component.py', 'scripts/run_component.sh')


def paths(): return ROOT/'runs'/RUN_ID, ROOT/'outputs'/RUN_ID
def freeze_path(): return ROOT/'tmp'/f'{RUN_ID}_freeze.json'
def timing_path(): return ROOT/'tmp'/f'{RUN_ID}_benchmark.json'
def benchmark_dir(): return ROOT/'tmp'/f'{RUN_ID}_benchmark'
def log_path(stage='execute'): return ROOT/'logs'/f'{RUN_ID}_{stage}.log'


def preflight(starting=True):
    cpus = predecessor.preflight(False)
    if shutil.disk_usage(ROOT).free < RESERVE + (ALLOWANCE if starting else 0):
        raise RuntimeError('2 GiB allowance plus 4 GiB external reserve required')
    return cpus


def source_closure():
    review=system.SOURCE_RUN+'_saved_content_review_v1_attempt1'
    run,out=ROOT/'runs'/review,ROOT/'outputs'/review
    complete_sha='6aba18e05950a379fa3eb3de27f7e403147ec24c8025699cdf83d467fd58b7c2'
    assert sha256_file(run/'COMPLETE.json')==complete_sha
    c,m=io.read_json(run/'COMPLETE.json'),io.read_json(run/'MANIFEST.json')
    assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c and not (run/'FAILED.json').exists()
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==1703 and len(c['output_sha256'])==19
    assert m['input_sha256']==io.hashes([Path(p) for p in m['input_sha256']])
    assert c['output_sha256']==io.hashes([Path(p) for p in c['output_sha256']])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    files={Path(p) for p in (*m['input_sha256'],*c['output_sha256'])}
    files.update((run/'COMPLETE.json',run/'MANIFEST.json',run/'STATUS.json',out/'output_hashes.sha256'))
    main=ROOT/'runs'/system.SOURCE_RUN/'COMPLETE.json'
    assert main in files and sha256_file(main)==system.SOURCE_COMPLETE_SHA
    assert set(system.source_paths(system.DISPOSABLE))<=files
    note=ROOT/'logs/d148_content_review_saved_audit_v1.json'
    assert sha256_file(note)=='35d63f5d96ecf1eee9231adb02217afc8ca8c5ef8403e2af655f8bb7002a0263'
    checked=io.read_json(note);assert checked['passes'] and checked['new_dynamics']==0
    assert checked['complete_sha256']==complete_sha and checked['supplement_precedes_main']
    for name,key in (('placement_review_check','checker_sha256'),('placement_review_run','runner_sha256')):
        assert sha256_file(system.dev.WS/f'src/l20_extension1/{name}.py')==checked[key]
    supplement=ROOT/'logs/d148_content_review_prelaunch_supplement_v1.json'
    assert sha256_file(supplement)==checked['supplement_sha256']
    sp=io.read_json(supplement);test=system.dev.WS/'tests/test_placement_review_adverse.py'
    xml=ROOT/'logs/d148_content_review_adverse_qualification_a.xml'
    assert sha256_file(test)==sp['test_sha256'] and sha256_file(xml)==sp['xml_sha256']
    files.update((note,supplement,test,xml,system.dev.WS/'packet-placement/SAVED_STATE_REVIEW_V1.md'))
    files.update(system.dev.WS/p for p in SCIENCE)
    return sorted(files)


def output_names():
    return [f'block_{i}.{ext}' for i in system.BLOCKS for ext in ('npz','json')]+[
        'COMPONENT_PANEL_STARTED.json','CELL_PLAN.json','input_hashes.sha256','summary.json','verification.json']


def contract():
    return dict(run_id=RUN_ID,source_complete_sha256=system.SOURCE_COMPLETE_SHA,blocks=list(system.BLOCKS),
        cases=[list(c) for c in system.CASES],edits=list(system.EDITS),assay_steps=300,lives=4,noise_replicates=2,
        labelled_cells=12288,untouched=3072,max_new_assays=9216,record_host_pairs=128,independent_blocks=16,
        namespace=system.TAG,physics_namespace=system.PHYSICS_TAG,config=asdict(system.CONFIG),
        guide_sha256=system.old.GUIDE_SHA256,primary='B_intact_G2_attenuate_minus_sham_mean',
        bootstrap_seed=14920260919,bootstrap_draws=10000,workers=6,allowance_bytes=ALLOWANCE,reserve_bytes=RESERVE,
        detach_above_seconds=600,benchmark_forecast='4*full_disposable_life_test_seconds+90',
        main_forecast='16*checked_block_seconds*work_scale+2*hash_seconds+180',
        work_scale='max(1,max_main_block_new_assays/max(1,disposable_new_assays))',
        byte_budget='16*uncompressed_block_bytes+benchmark_bytes+128MiB',
        cell_plan_before_new_main_assays=True,cell_plan_in_freeze=True,new_founders=0,new_upstream_dynamics=0,
        refits=0,carrier_bytes=2048,independent_new_assay_replay=True,replayed_existing_assays=0,
        fresh_cohort=False,same_extended_history=True,new_independent_noise=False,autonomous_repair=False,
        analyst_supplied_edit=True,rerouted_after_edit=False,apparatus_gate='18_untouched_checks',
        dose='0.5*min(competing_RMS,residual_RMS)',invariant_tolerance=1e-12,output_files=output_names(),
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def qualification(report):
    io.require_beneath(report,ROOT/'logs')
    tree=ET.parse(report).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=40 and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    required={'test_full_disposable_life','test_algebra','test_degenerate','test_equal_dose','test_walsh_fallback',
        'test_matching','test_independent_replay','test_saved_no_dynamics','test_corruption','test_metadata_corruption',
        'test_condition_order','test_namespace_guard','test_sixteen_block_normalization','test_block_bootstrap',
        'test_complete_summary','test_primary_not_shape','test_constant_unresolved','test_external_roundtrip',
        'test_source_closure','test_resource_guards','test_detached_guard','test_startup_handshake',
        'test_no_automatic_successor','test_main_barrier','test_failure_receipt','test_schema_roundtrip',
        'test_no_source_mutation','test_assay_isolation','test_primary_g2_not_g3','test_control_gate_not_primary',
        'test_cold_benchmark_audit_initializes','test_existing_endpoints','test_independent_plan',
        'test_same_history_not_new_lineage','test_new_assay_replay_corruption','test_budget_scale',
        'test_no_reroute','test_threshold_boundary','test_transition_partition'}
    ours=[c for c in cases if c.get('classname','').endswith('test_component')]
    assert required<={c.get('name','').split('[',1)[0] for c in ours}
    seconds=max(float(c.get('time')) for c in ours if c.get('name')=='test_full_disposable_life')
    assert seconds>0
    return dict(path=str(report),tests=len(cases),failures=0,skipped=0,full_life_seconds=seconds,benchmark_forecast=4*seconds+90)


def build_cell_plan():
    plans=[system.block_plan(index) for index in system.BLOCKS]
    return dict(namespace=system.TAG,physics_namespace=system.PHYSICS_TAG,blocks=plans,
        labelled_cells=12288,untouched=3072,new_assays=sum(p['new_assays'] for p in plans),
        max_block_new_assays=max(p['new_assays'] for p in plans),new_outcome_access=False,
        source_outcomes_already_observed=True,new_founders=0,new_upstream_dynamics=0)


def freeze(report):
    preflight()
    for path in (freeze_path(),timing_path(),benchmark_dir(),*paths(),log_path(),log_path('benchmark')):
        if path.exists():raise FileExistsError(path)
    proof=qualification(report);inputs=io.hashes(source_closure()+[report])
    plan=build_cell_plan()
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),new_main_assays_generated=0,main_cell_plan=plan,git_head=git_head(system.old.WS))
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,
        planned_new_assays=plan['new_assays'],max_block_new_assays=plan['max_block_new_assays'])),flush=True)


def frozen():
    value=io.read_json(freeze_path())
    assert value['contract']==contract() and value['environment']==environment_manifest()
    report=Path(value['test_proof']['path']);assert value['test_proof']==qualification(report)
    assert value['input_sha256']==io.hashes(source_closure()+[report]) and value['new_main_assays_generated']==0
    plan=value['main_cell_plan']
    assert plan['new_outcome_access'] is False and plan['namespace']==system.TAG
    assert [p['index'] for p in plan['blocks']]==list(system.BLOCKS)
    assert plan['new_assays']==sum(p['new_assays'] for p in plan['blocks'])
    assert plan['max_block_new_assays']==max(p['new_assays'] for p in plan['blocks'])
    assert 0<=plan['new_assays']<=9216 and plan['labelled_cells']==12288
    return value


def load_block(directory,index):
    raw,meta=io.load_npz(directory/f'block_{index}.npz'),io.read_json(directory/f'block_{index}.json')
    assert set(meta)=={'index','config','source_sha256','lives'} and meta['index']==index
    assert meta['config']==asdict(system.CONFIG) and len(meta['lives'])==4
    assert meta['source_sha256']==io.hashes(system.source_paths(index))
    assert all(x.shape[0]==4 for x in raw.values())
    return raw,meta


def check_block(directory,index):
    raw,meta=load_block(directory,index);source,sm=system.load_source(index);new=0
    plan=next((p for p in cell_plan()['blocks'] if p['index']==index),None) if index!=system.DISPOSABLE else None
    for life in range(4):
        entry=meta['lives'][life];assert (entry['index'],entry['life'])==(index,life)
        original={k:v[life] for k,v in source.items()}
        current=audit.check_life({k:v[life] for k,v in raw.items()},entry,original,sm['lives'][life],False)
        if plan is not None:
            for n in (0,1):
                for ci in range(32):
                    for gi in range(3):
                        spec={k:v for k,v in entry['cells'][n][ci][gi].items() if k not in ('terminal_reader','assay_steps','carrier_bytes','assay_enters_lineage')}
                        assert spec==plan['cells'][life][n][ci][gi]
        saved=entry['replay'];assert saved['full_new_dynamics_replayed'] is True and set(saved)==set(current)
        assert saved['replayed_new_assays']==current['new_assays'] and saved['replayed_existing_assays']==0
        for k,v in current.items():
            if k.endswith('_max_abs'):assert type(saved[k]) is float and 0<=saved[k]<=1e-10
            elif k not in ('full_new_dynamics_replayed','replayed_new_assays'):assert saved[k]==v
        new+=current['new_assays']
    return dict(index=index,uncompressed_bytes=sum(v.nbytes for v in raw.values()),labelled_cells=768,
        untouched=192,new_assays=new,reused_labels=768-new,replayed_new_assays=new,
        replayed_existing_assays=0,new_founders=0,new_upstream_dynamics=0,full_new_dynamics_replayed=True)


def cell_plan():
    return io.read_json(freeze_path())['main_cell_plan']


def barrier(run,out,expected):
    assert sha256_file(run/'MANIFEST.json')==expected
    manifest=io.read_json(run/'MANIFEST.json');receipt=io.read_json(out/'COMPONENT_PANEL_STARTED.json')
    assert receipt['manifest_sha256']==expected and receipt['source_complete_sha256']==system.SOURCE_COMPLETE_SHA
    assert receipt['namespace']==system.TAG and receipt['cell_plan_sha256']==manifest['cell_plan_sha256']
    assert sha256_file(out/'CELL_PLAN.json')==manifest['cell_plan_sha256']
    assert io.read_json(out/'CELL_PLAN.json')==cell_plan()
    return receipt


def worker(directory,index,run=None,manifest_sha=None):
    if index!=system.DISPOSABLE:
        if run is None or manifest_sha is None:raise ValueError('frozen/prepared new-main-assay barrier required')
        barrier(run,directory,manifest_sha)
    source,sm=system.load_source(index);plan=system.block_plan(index,source,sm)
    if index!=system.DISPOSABLE:
        assert plan==next(p for p in cell_plan()['blocks'] if p['index']==index)
    lives=[];entries=[]
    for life in range(4):
        original={k:v[life] for k,v in source.items()}
        raw,meta=system.simulate_life(index,life,original,sm['lives'][life])
        meta['replay']=audit.check_life(raw,meta,original,sm['lives'][life],True)
        for n in (0,1):
            for ci in range(32):
                for gi in range(3):
                    e=meta['cells'][n][ci][gi]
                    assert {k:v for k,v in e.items() if k not in ('terminal_reader','assay_steps','carrier_bytes','assay_enters_lineage')}==plan['cells'][life][n][ci][gi]
        lives.append(raw);entries.append(meta)
    block={k:np.stack([r[k] for r in lives]) for k in lives[0]}
    meta=dict(index=index,config=asdict(system.CONFIG),source_sha256=io.hashes(system.source_paths(index)),lives=entries)
    assert sum(e['new_assays'] for e in entries)==plan['new_assays']
    io.write_npz(directory/f'block_{index}.npz',block,ROOT);io.write_json(directory/f'block_{index}.json',meta,ROOT)
    return check_block(directory,index)



def work_scale(disposable_new,plan):
    return max(1.,plan['max_block_new_assays']/max(1,disposable_new))


def detached_guard(required, stage='execute'):
    if required and os.environ.get(DETACHED_ENV) != '1':
        raise RuntimeError('forecast above ten minutes requires detached execution')
    if os.environ.get(DETACHED_ENV) == '1':
        assert os.getpid() == os.getsid(0)
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert Path(os.readlink('/proc/self/fd/1')) == log_path(stage)
        assert os.readlink('/proc/self/fd/2') == os.readlink('/proc/self/fd/1')


def signal_ready(stage):
    descriptor = os.environ.pop('D149_READY_FD', None)
    if descriptor is not None:
        fd = int(descriptor)
        try:
            os.write(fd, json.dumps(dict(stage=stage, pid=os.getpid(), status='STARTED')).encode())
        except BrokenPipeError:
            pass
        finally:
            os.close(fd)


def benchmark():
    preflight(); f = frozen()
    detached_guard(f['test_proof']['benchmark_forecast'] > 600, 'benchmark')
    directory = benchmark_dir(); directory.mkdir(); started = time.monotonic()
    try:
        signal_ready('benchmark')
        proof = worker(directory, system.DISPOSABLE)
        raw, meta = load_block(directory, system.DISPOSABLE)
        summary = analysis.summarize([raw]*16, [meta]*16)
        score_proof = independent.check(summary, [raw]*16, [meta]*16)
        io.write_json(directory/'score_fixture.json', dict(scientific_evidence=False, summary=summary, check=score_proof), ROOT)
        elapsed = time.monotonic()-started
        tick = time.monotonic(); frozen(); hashes_seconds = time.monotonic()-tick
        size = sum(p.stat().st_size for p in directory.iterdir())
        scale=work_scale(proof['new_assays'],f['main_cell_plan'])
        projected = 16*elapsed*scale+2*hashes_seconds+180
        budget = 16*proof['uncompressed_bytes']+size+128*1024**2
        assert 0 < budget <= ALLOWANCE
        value = dict(status='COMPLETE', completed_utc=utc_now(), disposable=system.DISPOSABLE,
            proof=proof, score_check=score_proof, work_scale=scale, checked_block_seconds=elapsed, hash_seconds=hashes_seconds,
            projected_seconds=projected, must_detach=projected > 600,
            uncompressed_block_bytes=proof['uncompressed_bytes'], benchmark_bytes=size,
            projected_total_bytes=budget, artifact_sha256=io.hashes(list(directory.iterdir())),
            freeze_sha256=sha256_file(freeze_path()), scientific_evidence=False, new_main_assays_generated=0)
        io.write_json(timing_path(), value, ROOT)
        print(json.dumps(value, indent=2), flush=True)
    except Exception as error:
        io.failure(directory, error, ROOT); raise


def timing_checked():
    value = io.read_json(timing_path())
    assert value['status'] == 'COMPLETE' and value['new_main_assays_generated'] == 0
    assert value['disposable'] == system.DISPOSABLE and value['scientific_evidence'] is False
    assert value['freeze_sha256'] == sha256_file(freeze_path())
    assert {p.name for p in benchmark_dir().iterdir()} == {f'block_{system.DISPOSABLE}.npz', f'block_{system.DISPOSABLE}.json' , 'score_fixture.json'}
    assert value['artifact_sha256'] == io.hashes(list(benchmark_dir().iterdir()))
    assert value['benchmark_bytes'] == sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert value['work_scale']==work_scale(value['proof']['new_assays'],cell_plan())
    assert value['projected_seconds'] == 16*value['checked_block_seconds']*value['work_scale']+2*value['hash_seconds']+180
    assert value['must_detach'] == (value['projected_seconds'] > 600)
    assert value['projected_total_bytes'] == 16*value['uncompressed_block_bytes']+value['benchmark_bytes']+128*1024**2 <= ALLOWANCE
    return value


def benchmark_audit():
    preflight(False);frozen();value=timing_checked();proof=check_block(benchmark_dir(),system.DISPOSABLE)
    raw,meta=load_block(benchmark_dir(),system.DISPOSABLE)
    fixture=io.read_json(benchmark_dir()/'score_fixture.json');assert fixture['scientific_evidence'] is False
    checked=independent.check(fixture['summary'],[raw]*16,[meta]*16)
    assert checked==fixture['check']==value['score_check'] and proof==value['proof']
    return dict(passes=True,disposable_lives=4,labelled_cells=768,new_assays=proof['new_assays'],
        replayed_new_assays=proof['new_assays'],replayed_existing_assays=0,new_founders=0,new_dynamics=0,indexed_artifacts=3)


def main_inputs():
    f = frozen(); timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']] + [freeze_path(), timing_path(), *benchmark_dir().iterdir()])


def prepare():
    preflight(); inputs=main_inputs(); timing=timing_checked(); benchmark_audit()
    run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use run already reserved')
    run.mkdir(); out.mkdir()
    io.write_json(out/'CELL_PLAN.json',cell_plan(),ROOT)
    manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=inputs,timing=timing,
        environment=environment_manifest(),affinity=sorted(os.sched_getaffinity(0)),
        free_bytes=shutil.disk_usage(ROOT).free,git_head=git_head(system.old.WS),
        cell_plan_sha256=sha256_file(out/'CELL_PLAN.json'),new_main_assays_generated=0)
    io.write_json(run/'MANIFEST.json',manifest,ROOT)
    with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(inputs))
    atomic_json(run/'STATUS.json',dict(status='PREPARED',run_id=RUN_ID),ROOT)
    print(json.dumps(dict(status='PREPARED',inputs=len(inputs),forecast_seconds=timing['projected_seconds'],
        must_detach=timing['must_detach'],projected_bytes=timing['projected_total_bytes'],
        cell_plan_sha256=manifest['cell_plan_sha256'])),flush=True)

def prepared():
    run,out=paths(); value=io.read_json(run/'MANIFEST.json')
    assert value['contract']==contract() and value['environment']==environment_manifest()
    assert value['input_sha256']==main_inputs() and value['timing']==timing_checked()
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(value['input_sha256'])
    assert value['cell_plan_sha256']==sha256_file(out/'CELL_PLAN.json')
    assert io.read_json(out/'CELL_PLAN.json')==cell_plan() and value['new_main_assays_generated']==0
    return value

def saved_audit(complete=True):
    preflight(False); manifest=prepared(); run,out=paths()
    assert {p.name for p in out.iterdir()}==set(output_names())|({'output_hashes.sha256'} if complete else set())
    start=barrier(run,out,sha256_file(run/'MANIFEST.json'))
    assert start['started_utc']>=manifest['prepared_utc']>=frozen()['frozen_utc']
    blocks=[]; records=[]; proofs=[]
    for index in system.BLOCKS:
        proofs.append(check_block(out,index))
        raw,meta=load_block(out,index); blocks.append(raw); records.append(meta)
    checked=independent.check(io.read_json(out/'summary.json'),blocks,records)
    assert io.read_json(out/'verification.json')==dict(blocks=proofs,statistics=checked)
    assert sum(p['new_assays'] for p in proofs)==cell_plan()['new_assays']
    if complete:
        receipt=io.read_json(run/'COMPLETE.json')
        assert receipt['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==receipt
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert receipt['manifest_sha256']==sha256_file(run/'MANIFEST.json')
        assert receipt['output_sha256']==io.hashes([out/n for n in output_names()])
        assert (out/'output_hashes.sha256').read_text()==io.hash_text(receipt['output_sha256'])
        assert receipt['hash_file_sha256']==sha256_file(out/'output_hashes.sha256')
        assert receipt['summary_sha256']==sha256_file(out/'summary.json') and receipt['source_complete_sha256']==system.SOURCE_COMPLETE_SHA
    return dict(passes=True,input_hashes=len(manifest['input_sha256']),indexed_outputs=len(output_names()),
        independent_blocks=16,record_host_pairs=128,labelled_cells=12288,untouched=3072,
        new_assays=cell_plan()['new_assays'],reused_labels=12288-cell_plan()['new_assays'],
        replayed_existing_assays=0,new_founders=0,new_dynamics=0)

def execute():
    run, out = paths()
    if any((run/name).exists() for name in ('COMPLETE.json', 'FAILED.json', 'EXECUTION.lock')):
        raise FileExistsError('single-use execution already started or closed')
    try:
        preflight(); m = prepared(); detached_guard(m['timing']['must_detach'])
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert {p.name for p in out.iterdir()} == {'input_hashes.sha256','CELL_PLAN.json'}
        (run/'EXECUTION.lock').mkdir(); began = time.monotonic()
        with (run/'RUN.pid').open('x') as stream: stream.write(str(os.getpid())+'\n')
        manifest_sha = sha256_file(run/'MANIFEST.json')
        io.write_json(out/'COMPONENT_PANEL_STARTED.json', dict(started_utc=utc_now(), manifest_sha256=manifest_sha,
            source_complete_sha256=system.SOURCE_COMPLETE_SHA, namespace=system.TAG,
            cell_plan_sha256=m['cell_plan_sha256']), ROOT)
        atomic_json(run/'STATUS.json', dict(status='COMPONENT', run_id=RUN_ID, started_utc=utc_now()), ROOT)
        signal_ready('execute')
        proofs = {}
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs = [pool.submit(worker, out, i, run, manifest_sha) for i in system.BLOCKS]
            try:
                for job in as_completed(jobs):
                    proof = job.result(); proofs[proof['index']] = proof
                    status = dict(status='COMPONENT', run_id=RUN_ID, completed_blocks=sorted(proofs),
                        total_blocks=16, updated_utc=utc_now())
                    atomic_json(run/'STATUS.json', status, ROOT); print(json.dumps(status), flush=True)
            except Exception:
                for job in jobs: job.cancel()
                raise
        blocks, records = zip(*(load_block(out, i) for i in system.BLOCKS))
        summary = analysis.summarize(blocks, records)
        checked = independent.check(summary, blocks, records)
        io.write_json(out/'summary.json', summary, ROOT)
        io.write_json(out/'verification.json', dict(blocks=[proofs[i] for i in system.BLOCKS], statistics=checked), ROOT)
        del blocks, records
        saved_audit(False); assert main_inputs() == m['input_sha256']; preflight(False)
        outputs = io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream: stream.write(io.hash_text(outputs))
        size = sum(p.stat().st_size for p in out.iterdir()); assert size <= ALLOWANCE
        receipt = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-began, output_bytes=size, manifest_sha256=manifest_sha,
            output_sha256=outputs, hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            summary_sha256=sha256_file(out/'summary.json'), source_complete_sha256=system.SOURCE_COMPLETE_SHA,
            automatic_retry=False, automatic_successor=False)
        io.write_json(run/'COMPLETE.json', receipt, ROOT); atomic_json(run/'STATUS.json', receipt, ROOT)
        print(json.dumps({k: v for k, v in receipt.items() if k != 'output_sha256'}), flush=True)
    except Exception as error:
        if run.is_dir() and not (run/'FAILED.json').exists():
            io.failure(run, error, ROOT)
            atomic_json(run/'STATUS.json', dict(status='FAILED', run_id=RUN_ID, failed_utc=utc_now(), error=str(error)), ROOT)
        raise


def detach(stage='execute'):
    preflight()
    if stage == 'execute':
        prepared(); run, out = paths()
        assert io.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert not any((run/n).exists() for n in ('EXECUTION.lock', 'FAILED.json', 'COMPLETE.json'))
    elif stage == 'benchmark':
        frozen(); assert not benchmark_dir().exists() and not timing_path().exists()
        run = ROOT/'tmp'
    else:
        raise ValueError('only declared benchmark or execution stage may detach')
    lock = ROOT/'tmp'/f'{RUN_ID}_{stage}_launch.lock'; lock.mkdir()
    env = os.environ.copy(); env[DETACHED_ENV] = '1'
    ready_read, ready_write = os.pipe(); env['D149_READY_FD'] = str(ready_write)
    command = [sys.executable, '-m', 'l20_extension1.component_run', '--'+stage]
    try:
        with log_path(stage).open('xb') as stream:
            child = subprocess.Popen(command, cwd=system.old.WS, env=env, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(ready_write,))
    finally:
        os.close(ready_write)
    readable, _, _ = select.select([ready_read], [], [], 55)
    acknowledgement = os.read(ready_read, 4096) if readable else b''; os.close(ready_read)
    ack = json.loads(acknowledgement) if acknowledgement else None
    if ack is not None: assert ack == dict(stage=stage, pid=child.pid, status='STARTED')
    receipt = dict(status='DETACHED', stage=stage, pid=child.pid, launched_utc=utc_now(), command=command,
        startup_acknowledged=ack is not None, log=str(log_path(stage)),
        progress=str(run/'STATUS.json') if stage == 'execute' else str(timing_path()),
        complete=str(run/'COMPLETE.json') if stage == 'execute' else str(timing_path()),
        failure=str(run/'FAILED.json') if stage == 'execute' else str(benchmark_dir()/'FAILED.json'),
        automatic_polling=False, automatic_retry=False, automatic_successor=False)
    io.write_json(lock/'LAUNCH.json', receipt, ROOT)
    if stage == 'execute': io.write_json(run/'LAUNCH.json', receipt, ROOT)
    print(json.dumps(receipt, indent=2), flush=True)


def main():
    if sys.flags.optimize: raise RuntimeError('audit assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-report', type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze', 'benchmark', 'benchmark-audit', 'prepare', 'execute', 'audit', 'detach', 'detach-benchmark'):
        choice.add_argument('--'+name, action='store_true')
    args = parser.parse_args()
    if args.freeze != (args.test_report is not None): parser.error('--test-report required only with --freeze')
    if args.freeze: freeze(args.test_report)
    elif args.benchmark: benchmark()
    elif args.benchmark_audit: print(json.dumps(benchmark_audit(), indent=2))
    elif args.prepare: prepare()
    elif args.execute: execute()
    elif args.audit: print(json.dumps(saved_audit(), indent=2))
    else: detach('benchmark' if args.detach_benchmark else 'execute')


if __name__ == '__main__': main()
