"""Write-once development pipeline; no held-out generation, retries or successor."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation import l16_body_content_run as resource
from laws_confirmation import l15_repair_speed_run as u
from laws_confirmation.io import atomic_json, environment_manifest, sha256_file, utc_now, git_head
from . import diagnostics as p, predictor, audit

WORKERS = 6
SOURCE_SHA = '353e4c16236aae3ec6254e24d401ea7710f9578c75e69145bff28bfe6b97a415'
DETACHED_ENV = 'L20_EXTENSION1_DETACHED_STAGE'


def initialize():
    assert p.ROOT.resolve() == p.BASE.resolve()/'L20-extension-1'
    for name in ('logs','tmp/cache','runs','outputs','data'):
        (p.ROOT/name).mkdir(parents=True,exist_ok=True)
    preflight()
    print(json.dumps(dict(status='INITIALIZED',root=str(p.ROOT),heldout_outcomes=0)),flush=True)


def preflight(starting=True):
    cpus = resource.preflight(p.BASE,starting)
    assert p.ROOT.is_dir() and p.ROOT.resolve() == p.BASE.resolve()/'L20-extension-1'
    for name in ('TMPDIR','XDG_CACHE_HOME'):
        u.require_beneath(Path(os.environ[name]),p.ROOT)
    p.old.api()
    return cpus


def source_closure():
    run = p.BASE/'runs'/p.d140.RUN_ID; out = p.BASE/'outputs'/p.d140.RUN_ID
    assert sha256_file(run/'COMPLETE.json') == SOURCE_SHA and not (run/'FAILED.json').exists()
    complete = u.read_json(run/'COMPLETE.json'); manifest = u.read_json(run/'MANIFEST.json')
    assert complete['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == complete
    assert complete['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
    expected_env = environment_manifest() | dict(tmpdir=str(p.BASE/'tmp'),xdg_cache_home=str(p.BASE/'tmp/cache'))
    assert manifest['environment'] == expected_env  # Only temp/cache move into the isolated subtree.
    assert len(manifest['input_sha256']) == 1048 and len(complete['output_sha256']) == 19
    assert manifest['input_sha256'] == u.hashes([Path(x) for x in manifest['input_sha256']])
    assert complete['output_sha256'] == u.hashes([Path(x) for x in complete['output_sha256']])
    assert complete['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
    assert (out/'input_hashes.sha256').read_text() == u.hash_text(manifest['input_sha256'])
    assert (out/'output_hashes.sha256').read_text() == u.hash_text(complete['output_sha256'])
    paths = {Path(x) for x in (*manifest['input_sha256'],*complete['output_sha256'])}
    assert all(x in paths for spec in p.DEVELOPMENT+(p.DISPOSABLE,) for x in p.source_paths(*spec))
    paths.update((run/'MANIFEST.json',run/'STATUS.json',run/'COMPLETE.json',out/'output_hashes.sha256',
                  p.old.WS/'reviews/L20_FRESH_FOUNDERS_2026-09-16.md'))
    paths.update(p.WS/x for x in p.SCIENCE)
    return sorted(paths)


def report_proof(path):
    path = u.require_beneath(path,p.ROOT/'logs')
    assert not path.is_symlink() and path.name.startswith('d141_') and path.suffix == '.xml'
    tree = ET.parse(path).getroot(); cases = tree.findall('.//testcase')
    assert not any(tree.findall('.//'+k) for k in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases}) == len(cases)
    current = [c for c in cases if c.get('classname','').endswith('test_extension1')]
    names = {c.get('name','').split('[',1)[0] for c in current}
    required = {'test_full_disposable_life','test_source_records','test_shuffle_preserves_values','test_noise_pairing',
        'test_no_third_copy','test_no_parent_or_future_access','test_independent_checker','test_raw_corruption',
        'test_metadata_corruption','test_condition_order','test_independent_model','test_blocked_cv',
        'test_training_only_preprocessing','test_primary_score','test_model_corruption','test_external_roundtrip',
        'test_resource_guards','test_detachment_guard','test_heldout_guard','test_fresh_process_saved_audit',
        'test_long_stage_guard','test_reservation_guard','test_no_automatic_successor','test_source_closure'}
    required.add('test_model_artifact_and_summary')
    assert len(current) >= 40 and required <= names
    seconds = max(float(c.get('time','0')) for c in current if c.get('name') == 'test_full_disposable_life')
    assert seconds > 0
    return dict(path=str(path),tests=len(cases),new_tests=len(current),failed=0,skipped=0,
                full_life_seconds=seconds,benchmark_forecast=8*seconds+60)


def freeze_path(): return p.ROOT/'tmp'/f'{p.RUN_ID}_freeze.json'
def benchmark_dir(): return p.ROOT/'tmp'/f'{p.RUN_ID}_benchmark'
def timing_path(): return p.ROOT/'tmp'/f'{p.RUN_ID}_benchmark.json'
def log_path(stage): return p.ROOT/'logs'/f'{p.RUN_ID}_{stage}.log'
def lock_path(stage): return p.ROOT/'tmp'/f'{p.RUN_ID}_{stage}_launch.lock'
def block_name(spec): return f'{spec[0]}_{spec[1]}'
def output_names():
    return tuple(f'{block_name(s)}.{e}' for s in p.DEVELOPMENT for e in ('npz','json')) + ('models.json','development_summary.json','verification.json','input_hashes.sha256')
def contract():
    return p.contract() | dict(workers=6,detach_above_seconds=600,allowance_bytes=resource.ALLOWANCE,
        reserve_bytes=resource.RESERVE,source_complete_sha256=SOURCE_SHA,alphas=list(predictor.ALPHAS),
        output_files=list(output_names()),primary_bootstrap_draws=10000,primary_bootstrap_seed=14120260917,
        benchmark_forecast='8*full_disposable_life_test_seconds+60',
        development_forecast='16*checked_block_seconds+2*hash_seconds+180')


def freeze(report):
    preflight(); proof = report_proof(report)
    for path in (freeze_path(),benchmark_dir(),timing_path(),p.ROOT/'runs'/p.RUN_ID,p.ROOT/'outputs'/p.RUN_ID,
                 log_path('benchmark'),log_path('development'),lock_path('benchmark'),lock_path('development')):
        if path.exists(): raise FileExistsError(path)
    inputs = u.hashes(source_closure()+[report])
    f = dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),git_head=git_head(p.WS),heldout_outcomes_seen=0)
    u.write_json(freeze_path(),f,p.ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,heldout_outcomes_seen=0)),flush=True)


def frozen():
    f = u.read_json(freeze_path()); report = Path(f['test_proof']['path'])
    audit.nested(f['contract'],contract()); assert f['environment'] == environment_manifest()
    assert f['heldout_outcomes_seen'] == 0 and f['test_proof'] == report_proof(report)
    assert f['input_sha256'] == u.hashes(source_closure()+[report])
    return f


def detached_guard(stage,required):
    if required and os.environ.get(DETACHED_ENV) != stage:
        raise AssertionError('long stage requires detached execution')
    if DETACHED_ENV in os.environ:
        assert os.environ[DETACHED_ENV] == stage and os.getpid() == os.getsid(0)
        assert os.readlink('/proc/self/fd/0') == '/dev/null'
        assert all(os.readlink('/proc/self/fd/'+str(fd)) == str(log_path(stage)) for fd in (1,2))


def block_proof(meta,raw):
    rows = [m['replay'] for m in meta['lives']]
    return dict(cohort=meta['cohort'],index=meta['index'],full_life_replays=4,
        **{k:sum(r[k] for r in rows) for k in ('diagnostic_cycles','reader_paths','selectors')},
        max_abs=max(r[k] for r in rows for k in r if k.endswith('_max_abs')),
        uncompressed_bytes=sum(v.nbytes for v in raw.values()))


def checked_block(directory,spec):
    preflight(False)
    founders,guides,y,source = p.source_inputs(*spec)
    rows,entries = [],[]
    for life in range(4):
        raw,meta = p.simulate_life(*spec,life,founders[life],guides[life])
        meta['replay'] = audit.check_life(raw,meta,founders[life],guides[life],True)
        rows.append(raw); entries.append(meta)
    raw = {k:np.stack([r[k] for r in rows]) for k in rows[0]} | dict(outcomes=y)
    meta = source | dict(config=asdict(p.CONFIG),lives=entries)
    saved = u.save_pair(directory,block_name(spec),raw,meta,p.ROOT)
    assert audit.check_block(saved,u.read_json(directory/(block_name(spec)+'.json')))
    return block_proof(meta,raw)


def benchmark():
    preflight(); f = frozen(); detached_guard('benchmark',f['test_proof']['benchmark_forecast'] > 600)
    directory = benchmark_dir(); directory.mkdir(); start = time.monotonic()
    try:
        proof = checked_block(directory,p.DISPOSABLE)
        seconds = time.monotonic()-start; tick = time.monotonic(); frozen(); hashes = time.monotonic()-tick
        size = sum(x.stat().st_size for x in directory.iterdir())
        forecast = 16*seconds+2*hashes+180
        budget = 16*proof['uncompressed_bytes']+size+32*1024**2
        assert 0 < budget <= resource.ALLOWANCE
        t = dict(status='COMPLETE',completed_utc=utc_now(),qualification_pool=False,block=proof,
            checked_block_seconds=seconds,hash_seconds=hashes,projected_seconds=forecast,must_detach=forecast>600,
            projected_total_bytes=budget,benchmark_bytes=size,artifact_sha256=u.hashes(list(directory.iterdir())),
            freeze_sha256=sha256_file(freeze_path()))
        preflight(); u.write_json(timing_path(),t,p.ROOT); print(json.dumps(t,indent=2),flush=True)
    except Exception as error:
        u.failure(directory,error,p.ROOT); raise


def timing_checked():
    t = u.read_json(timing_path()); directory = benchmark_dir()
    assert t['status'] == 'COMPLETE' and t['qualification_pool'] is False
    assert t['freeze_sha256'] == sha256_file(freeze_path())
    assert {x.name for x in directory.iterdir()} == {block_name(p.DISPOSABLE)+'.npz',block_name(p.DISPOSABLE)+'.json'}
    assert t['artifact_sha256'] == u.hashes(list(directory.iterdir()))
    assert t['projected_seconds'] == 16*t['checked_block_seconds']+2*t['hash_seconds']+180
    assert t['must_detach'] == (t['projected_seconds']>600)
    assert t['benchmark_bytes'] == sum(x.stat().st_size for x in directory.iterdir())
    assert t['projected_total_bytes'] == 16*t['block']['uncompressed_bytes']+t['benchmark_bytes']+32*1024**2 <= resource.ALLOWANCE
    return t


def benchmark_audit():
    preflight(False); frozen(); t = timing_checked(); directory = benchmark_dir(); name = block_name(p.DISPOSABLE)
    raw = u.load_npz(directory/(name+'.npz')); meta = u.read_json(directory/(name+'.json'))
    assert audit.check_block(raw,meta) and t['block'] == block_proof(meta,raw)
    return dict(passes=True,new_dynamics=0,projected_seconds=t['projected_seconds'],projected_total_bytes=t['projected_total_bytes'])


def main_inputs():
    f = frozen(); timing_checked()
    return u.hashes([Path(x) for x in f['input_sha256']] + [freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def prepare():
    preflight(); inputs = main_inputs(); timing = timing_checked()
    run = p.ROOT/'runs'/p.RUN_ID; out = p.ROOT/'outputs'/p.RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('single-use development identity reserved')
    run.mkdir(); out.mkdir()
    manifest = dict(prepared_utc=utc_now(),contract=contract(),input_sha256=inputs,
                    environment=environment_manifest(),timing=timing,git_head=git_head(p.WS))
    u.write_json(run/'MANIFEST.json',manifest,p.ROOT)
    with (out/'input_hashes.sha256').open('x') as f: f.write(u.hash_text(inputs))
    atomic_json(run/'STATUS.json',dict(status='PREPARED',run_id=p.RUN_ID),p.ROOT)
    print(json.dumps(dict(status='PREPARED',inputs=len(inputs),forecast=timing['projected_seconds'])),flush=True)


def prepared():
    run = p.ROOT/'runs'/p.RUN_ID; out = p.ROOT/'outputs'/p.RUN_ID
    m = u.read_json(run/'MANIFEST.json')
    audit.nested(m['contract'],contract()); assert m['environment'] == environment_manifest()
    assert m['input_sha256'] == main_inputs() and m['timing'] == timing_checked()
    assert (out/'input_hashes.sha256').read_text() == u.hash_text(m['input_sha256'])
    return m


def assemble(blocks):
    initial = np.stack([r['initial_features'] for r in blocks]).reshape(256,4)
    probes = np.stack([r['diagnostic_features'] for r in blocks]).reshape(256,3,6)
    x = dict(starting_only=initial,passive=p.observer_features(initial,probes[:,0],probes[:,1]),
             challenge=p.observer_features(initial,probes[:,0],probes[:,2]))
    y = np.stack([r['outcomes'] for r in blocks]).reshape(256)
    groups = np.tile(np.arange(4,dtype=np.int64),64); ids = np.repeat(np.arange(16,dtype=np.int64),16)
    return x,y,groups,ids


def fit_models(blocks):
    x,y,groups,ids = assemble(blocks)
    initial = list(p.INITIAL_FEATURES)
    names = initial+['U0:'+n for n in p.CYCLE_FEATURES]+['second:'+n for n in p.CYCLE_FEATURES]
    models = dict(stage='DEVELOPMENT_ONLY',cohorts=[list(s) for s in p.DEVELOPMENT],
        feature_names=dict(starting_only=initial,passive=names,challenge=names),
        fits={k:predictor.select_and_fit(v,y,groups,ids) for k,v in x.items()},heldout_outcomes_seen=0)
    assert audit.check_models(models,blocks)
    return models


def summarize(models,blocks):
    _,y,groups,ids = audit.data(blocks)
    rows = {}
    for key,fit in models['fits'].items():
        predictions = np.asarray(fit['cv_predictions'])
        error = predictions-y
        rows[key] = dict(alpha=fit['model']['alpha'],cv_mse=float(np.mean(error**2)),cv_mae=float(np.mean(abs(error))),
            group_mse=[float(np.mean(error[groups==g]**2)) for g in range(4)],
            block_mse=[float(np.mean(error[ids==b]**2)) for b in range(16)])
    return dict(stage='DEVELOPMENT_ONLY',prospective_evidence=False,selection_affected_cv=True,
        independent_founder_blocks=16,cases=256,diagnostic_cycles=768,heldout_outcomes_seen=0,
        rows=rows,cv_mse_improvement=rows['passive']['cv_mse']-rows['challenge']['cv_mse'],
        interpretation='Development diagnostics only. No held-out forecast evidence or success claim.',
        automatic_successor=False)


def saved_audit(complete=True):
    preflight(False); manifest = prepared()
    run = p.ROOT/'runs'/p.RUN_ID; out = p.ROOT/'outputs'/p.RUN_ID
    assert {x.name for x in out.iterdir()} == set(output_names()) | ({'output_hashes.sha256'} if complete else set())
    blocks,proofs = [],[]
    for spec in p.DEVELOPMENT:
        name = block_name(spec); raw = u.load_npz(out/(name+'.npz')); meta = u.read_json(out/(name+'.json'))
        assert (meta['cohort'],meta['index']) == spec and audit.check_block(raw,meta)
        blocks.append(raw); proofs.append(block_proof(meta,raw))
    assert u.read_json(out/'verification.json') == proofs
    models = u.read_json(out/'models.json'); assert audit.check_models(models,blocks)
    assert audit.check_summary(u.read_json(out/'development_summary.json'),models,blocks)
    if complete:
        c = u.read_json(run/'COMPLETE.json')
        assert c['status'] == 'COMPLETE' and u.read_json(run/'STATUS.json') == c
        assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
        assert c['manifest_sha256'] == sha256_file(run/'MANIFEST.json')
        assert c['output_sha256'] == u.hashes([out/n for n in output_names()])
        assert (out/'output_hashes.sha256').read_text() == u.hash_text(c['output_sha256'])
        assert c['hash_file_sha256'] == sha256_file(out/'output_hashes.sha256')
        assert c['model_sha256'] == sha256_file(out/'models.json') and c['heldout_outcomes_seen'] == 0
    return dict(passes=True,input_hashes=len(manifest['input_sha256']),output_hashes=len(output_names()) if complete else 0,
        diagnostic_cycles=768,reader_paths=1536,selectors=1536,new_dynamics=0,heldout_outcomes_seen=0)


def execute():
    preflight(); m = prepared(); detached_guard('development',m['timing']['must_detach'])
    run = p.ROOT/'runs'/p.RUN_ID; out = p.ROOT/'outputs'/p.RUN_ID
    assert u.read_json(run/'STATUS.json')['status'] == 'PREPARED' and not (run/'FAILED.json').exists()
    (run/'EXECUTION.lock').mkdir(); start = time.monotonic()
    try:
        atomic_json(run/'STATUS.json',dict(status='RUNNING',run_id=p.RUN_ID,started_utc=utc_now()),p.ROOT)
        proofs = {}
        with ProcessPoolExecutor(max_workers=6,mp_context=multiprocessing.get_context('spawn')) as pool:
            futures = [pool.submit(checked_block,out,spec) for spec in p.DEVELOPMENT]
            for future in as_completed(futures):
                proof = future.result(); proofs[proof['cohort'],proof['index']] = proof
                print(json.dumps(dict(block_complete=[proof['cohort'],proof['index']])),flush=True)
        blocks = [u.load_npz(out/(block_name(s)+'.npz')) for s in p.DEVELOPMENT]
        models = fit_models(blocks)
        u.write_json(out/'models.json',models,p.ROOT)
        u.write_json(out/'development_summary.json',summarize(models,blocks),p.ROOT)
        u.write_json(out/'verification.json',[proofs[s] for s in p.DEVELOPMENT],p.ROOT)
        saved_audit(False); assert main_inputs() == m['input_sha256']; preflight(False)
        outputs = u.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as f: f.write(u.hash_text(outputs))
        size = sum(x.stat().st_size for x in out.iterdir()); assert size <= resource.ALLOWANCE
        c = dict(status='COMPLETE',stage='DEVELOPMENT_ONLY',run_id=p.RUN_ID,completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start,output_bytes=size,manifest_sha256=sha256_file(run/'MANIFEST.json'),
            output_sha256=outputs,hash_file_sha256=sha256_file(out/'output_hashes.sha256'),
            model_sha256=sha256_file(out/'models.json'),heldout_outcomes_seen=0,automatic_successor=False)
        u.write_json(run/'COMPLETE.json',c,p.ROOT); atomic_json(run/'STATUS.json',c,p.ROOT)
        print(json.dumps({k:v for k,v in c.items() if k != 'output_sha256'}),flush=True)
    except Exception as error:
        u.failure(run,error,p.ROOT); raise


def detach(stage):
    preflight()
    if stage == 'benchmark':
        frozen()
        if benchmark_dir().exists() or timing_path().exists(): raise FileExistsError('benchmark reserved')
    elif stage == 'development':
        prepared(); run = p.ROOT/'runs'/p.RUN_ID
        assert u.read_json(run/'STATUS.json')['status'] == 'PREPARED'
        assert not (run/'EXECUTION.lock').exists() and not (run/'FAILED.json').exists()
    else: raise ValueError('only benchmark or development can be detached')
    lock_path(stage).mkdir(); env = os.environ.copy(); env[DETACHED_ENV] = stage
    cmd = [sys.executable,'-m','l20_extension1.development_run','--benchmark' if stage == 'benchmark' else '--execute']
    with log_path(stage).open('xb') as f:
        child = subprocess.Popen(cmd,cwd=p.old.WS,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(status='DETACHED',stage=stage,pid=child.pid,log=str(log_path(stage)),
        automatic_polling=False,user_polls=True,automatic_retry=False,automatic_successor=False)),flush=True)


def main():
    if sys.flags.optimize: raise RuntimeError('assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--test-report',type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    for name in ('init','freeze','benchmark','benchmark-audit','prepare','execute','audit','detach-benchmark','detach-development'):
        choice.add_argument('--'+name,action='store_true')
    args = parser.parse_args()
    if args.freeze != (args.test_report is not None): parser.error('--test-report required only with --freeze')
    if args.init: initialize()
    elif args.freeze: freeze(args.test_report)
    elif args.benchmark: benchmark()
    elif args.benchmark_audit: print(json.dumps(benchmark_audit(),indent=2))
    elif args.prepare: prepare()
    elif args.execute: execute()
    elif args.audit: print(json.dumps(saved_audit(),indent=2))
    else: detach('benchmark' if args.detach_benchmark else 'development')


if __name__ == '__main__': main()
