"""D086: one-boundary theta-only descendant assay at the original E70 write rate."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l17_r_channel as base
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 sha256_file, utc_now, write_hash_manifest)

RUN_ID, TAG = 'l24_descendant_pilot_v1_attempt1', 'l24-descendant-pilot-v1'
OLD_ID = 'l24_slow_writing_germline_barrier_audit_v1_attempt2'
TISSUES, DISPOSABLE, WORKERS = tuple(range(32000, 32008)), 402089, 4
PACKAGES = (*base.PACKAGES, 'writable_landlord', 'assimilation', 'weismann')
FIELDS = ('V', 'ema', 'R', 'theta')
STAGES = ('birth', 'settled', 'post_fission', 'pre_zap', 'post_zap', 'one_after_zap', 'final')
RECORDS = ('clean', 'damaged', 'erased', 'native', 'known_clean', 'known_damage',
           'known_damage_shuffled', 'known_damage_reversed')
READERS = ('native_T', 'theta_only')
REGIONS = ('posterior', 'untouched', 'whole')
METRICS = ('damage_fidelity', 'clean_fidelity', 'damage_projection', 'clean_squared_error',
           'damage_squared_error', 'mean_V', 'rms_V', 'clip_fraction')
CONTRASTS = (('calibration_content_crossover', 5, 4), ('calibration_address', 5, 6),
             ('calibration_reversal', 5, 7), ('natural_damage_transmission', 1, 0))
SCIENCE = ('src/laws_confirmation/l24_descendant_pilot.py',
           'scripts/audit_l24_descendant_pilot_outputs.py', 'tests/test_l24_descendant_pilot.py',
           'scripts/run_l24_descendant_pilot.sh', 'protocols/L24_DESCENDANT_PILOT_V1.md')
RESERVE, ALLOWANCE = 4*1024**3, 512*1024**2


@dataclass(frozen=True)
class Config:
    parents: int = 4
    draws: int = 8
    settle: int = 120
    parent_steps: int = 500
    zap: int = 450
    child_steps: int = 500
    times: tuple = (0, 1, 50, 250, 500)
    norm: float = .3
    writer_rate: float = .0005

    def __post_init__(self):
        if not (self.parents > 0 and self.draws > 0 and self.settle > 0 and 0 < self.zap < self.parent_steps-1):
            raise ValueError('positive sample counts and distinct parent checkpoints required')
        if tuple(sorted(set(self.times))) != self.times or self.times[0] != 0 or self.times[-1] != self.child_steps:
            raise ValueError('ordered unique child checkpoints must include birth and final')
        if not (np.isfinite(self.norm) and self.norm > 0 and 0 < self.writer_rate < 1):
            raise ValueError('finite norm and rate inside (0,1) required')


CONFIG = Config()


def strict_json(path, value, root):
    atomic_text(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n', root)


def api():
    result = base.source_api()
    for package in PACKAGES:
        directory = str(base.sources_root()/package/'src')
        if directory not in sys.path:
            sys.path.insert(0, directory)
    from assimilation.pipeline import fission_with_mask
    from writable_landlord.pipeline import project_theta
    from weismann.config import WeismannConfig
    from weismann import pipeline as original
    return result | dict(fission_with_mask=fission_with_mask, project_theta=project_theta,
                         WeismannConfig=WeismannConfig, original=original)


def context(index, cfg=CONFIG):
    a = api(); rc = a['RewriteConfig']()
    return dict(index=index, config=cfg, api=a, tissue=a['tissue_config'](index, rc.coupling_band, rc),
                ladder=a['LadderConfig'](), bp=a['BlueprintConfig']())


def rng(index, parent, phase):
    address = f'{TAG}:{index}:{parent}:{phase}'.encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16], 'little'))


def checker():
    path = Path(__file__).resolve().parents[2]/SCIENCE[1]
    spec = importlib.util.spec_from_file_location('d086_independent_checker', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def parent_life(ctx, parent, damaged):
    cfg, a = ctx['config'], ctx['api']
    random = rng(ctx['index'], parent, 'parent')
    theta = a['project_theta'](a['make_thresholds'](ctx['tissue'])[None], cfg.norm)
    v = a['launch_pattern'](0, ctx['tissue'])[None]+ctx['tissue'].copy_jitter*random.standard_normal((1,16,16))
    ema, ref = v.copy(), v.copy()
    stages = []

    def save():
        stages.append(np.stack((v[0], ema[0], ref[0], theta[0])))

    def step():
        nonlocal v, ema, ref, theta
        v, ema, ref = a['blueprint_step'](v, ema, ref, theta, ctx['tissue'], ctx['ladder'], ctx['bp'], 'T', random)
        theta = a['project_theta']((1-cfg.writer_rate)*theta+cfg.writer_rate*np.tanh(ref), cfg.norm)

    save()
    for _ in range(cfg.settle): step()
    save(); founder = np.sign(v).copy()
    v, ref, fresh = a['fission_with_mask'](v, ref, ctx['tissue'], random)
    ema = v.copy(); save()
    zone = np.indices((16,16))[1] >= 12
    for t in range(cfg.parent_steps):
        if t == cfg.zap:
            save()
            if damaged:
                v = np.where(zone[None], -v, v)
                ema = v.copy()
            save()
        step()
        if t == cfg.zap: save()
    save()
    raw = dict(states=np.stack(stages), fresh=fresh[0], founder=founder[0], zone=zone)
    target = -np.sign(raw['states'][3,0])
    metrics = dict(fitness=float((((v > 0)==(founder > 0)) & (abs(v) > .2))[fresh].mean()),
                   leak=float(((v[0] > 0)==(target > 0))[zone].mean()) if damaged else None)
    return raw, dict(rng_final=canonical_digest(random.bit_generator.state), source_metrics=metrics)


def make_records(ctx, parent, clean, damaged):
    cfg = ctx['config']; project = ctx['api']['project_theta']
    good = np.where(clean['states'][3,0] > 0, 1., -1.)
    bad = np.where(clean['zone'], -good, good)
    known = project(np.tanh(1.5*np.stack((good,bad))), cfg.norm)
    permutation = rng(ctx['index'], parent, 'shuffle').permutation(256)
    native = project(ctx['api']['make_thresholds'](ctx['tissue'])[None], cfg.norm)[0]
    records = np.stack((clean['states'][-1,3], damaged['states'][-1,3], np.zeros((16,16)), native,
                        known[0], known[1], known[1].ravel()[permutation].reshape(16,16), -known[1]))
    return records, np.stack((good,bad)), permutation


def encode(record):
    if not isinstance(record, np.ndarray) or record.shape != (16,16) or record.dtype != np.float64 or not np.isfinite(record).all():
        raise ValueError('one finite float64 16x16 theta field required')
    return record.astype('<f8', copy=False).tobytes()


def decode(packet):
    if not isinstance(packet, bytes) or len(packet) != 2048:
        raise ValueError('only an immutable 2048-byte theta packet is accepted')
    field = np.frombuffer(packet, dtype='<f8').reshape(16,16)
    if not np.isfinite(field).all(): raise ValueError('nonfinite theta packet')
    return field


class SharedNoise:
    def __init__(self, generator, draws):
        self.generator, self.draws = generator, draws

    def standard_normal(self, shape):
        if tuple(shape[-3:]) != (self.draws,16,16): raise ValueError('unexpected descendant shape')
        return np.broadcast_to(self.generator.standard_normal((self.draws,16,16)), shape)


def descendants(packets, *, index, parent, reader, cfg=CONFIG):
    """The entire history-bearing input is one 2-KiB packet per independent field.

    Batch labels and target/parent states are absent. Public block/draw indices
    choose rulebook/randomness only; all conditions use identical birth/noise.
    """
    if not isinstance(packets, tuple) or not packets or reader not in range(2):
        raise ValueError('packet tuple and declared public reader required')
    ctx = context(index, cfg)
    theta = np.stack([decode(p) for p in packets]); theta.setflags(write=False)
    applied = np.stack((theta, np.zeros_like(theta)))[:, :, None]
    birth = .2*rng(index,parent,'child_birth').standard_normal((cfg.draws,16,16))
    birth -= birth.mean(axis=(-2,-1), keepdims=True)
    v = np.broadcast_to(birth, (2,len(packets),cfg.draws,16,16)).copy()
    ema, ref = v.copy(), np.zeros_like(v)
    random = SharedNoise(rng(index,parent,'child_future'), cfg.draws)
    bp = ctx['bp'] if reader == 0 else replace(ctx['bp'], c_m=0., rho=0.)
    states = []
    for t in range(cfg.child_steps+1):
        if t:
            v, ema, ref = ctx['api']['blueprint_step'](v,ema,ref,applied,ctx['tissue'],ctx['ladder'],bp,'T',random)
        if t in cfg.times: states.append(np.stack((v,ema,ref)))
    np.testing.assert_array_equal(theta,np.stack([decode(p) for p in packets]))
    return np.stack(states), dict(packet_sha256=[hashlib.sha256(p).hexdigest() for p in packets],
        rng_final=canonical_digest(random.generator.bit_generator.state), packet_unchanged=True,
        R_at_birth_zero=True, inherited_fields=['theta'])


def measure(states, targets):
    # time,field,onoff,record,draw,row,column -> time,onoff,record,draw,region,metric.
    v = states[:,0]; zone = np.indices((16,16))[1] >= 12
    result = []
    for mask in (zone,~zone,np.ones((16,16),bool)):
        x, good, bad = v[...,mask], targets[0,mask], targets[1,mask]
        result.append(np.stack((((x > 0)==(bad > 0)).mean(axis=-1),
            ((x > 0)==(good > 0)).mean(axis=-1), (x*bad).mean(axis=-1),
            np.square(x-good).mean(axis=-1), np.square(x-bad).mean(axis=-1),
            x.mean(axis=-1), np.sqrt(np.square(x).mean(axis=-1)), (abs(x)==2).mean(axis=-1)),axis=-1))
    return np.stack(result,axis=-2)


def execute_parent(ctx, parent, check):
    clean, cm = parent_life(ctx,parent,False); damaged, dm = parent_life(ctx,parent,True)
    parent_checks = [check.check_parent(raw,ctx,parent,damage,meta) for raw,damage,meta in ((clean,False,cm),(damaged,True,dm))]
    records,targets,permutation = make_records(ctx,parent,clean,damaged)
    assert check.check_records(records,targets,permutation,clean,damaged,ctx,parent)
    states,values,children = [],[],[]
    for reader in range(2):
        raw,record = descendants(tuple(encode(p) for p in records),index=ctx['index'],parent=parent,reader=reader,cfg=ctx['config'])
        record['reader'] = reader
        record['replay_max_abs'] = check.check_descendants(raw,records,ctx,parent,reader,record)
        scores = measure(raw,targets); check.check_metrics(raw,targets,scores)
        states.append(raw); values.append(scores); children.append(record)
    payload = dict(parent_states=np.stack((clean['states'],damaged['states'])), fresh=clean['fresh'],
        founder=clean['founder'], records=records, targets=targets, permutation=permutation,
        descendants=np.stack(states), values=np.stack(values))
    check.check_aliases(payload)
    record = dict(parent=parent, parent_checks=parent_checks, parent_records=[cm,dm], children=children)
    return payload,record


def execute_block(root,index):
    ctx,check = context(index),checker(); pieces=[]; records=[]
    for parent in range(CONFIG.parents):
        payload,record = execute_parent(ctx,parent,check);pieces.append(payload);records.append(record)
    payload = {k:np.stack([p[k] for p in pieces]) for k in pieces[0]}
    out = root/'outputs'/RUN_ID
    base.atomic_npz(out/f'block_{index}.npz',payload,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        assert set(saved.files)==set(payload)
        for key in payload: np.testing.assert_array_equal(saved[key],payload[key])
    record = dict(tissue=index,passes=True,config=asdict(CONFIG),parents=records,
        source_bridges=8,parent_replays=8,descendant_panels_replayed=8)
    strict_json(out/f'block_{index}.json',record,root)
    assert json.loads((out/f'block_{index}.json').read_text())==json.loads(json.dumps(record))
    return record


def summarize(blocks):
    # block,parent,reader,time,onoff,record,draw,region,metric.
    x = np.stack(blocks); focal=[]
    resamples=rng(0,0,'block_bootstrap').integers(0,len(blocks),(10000,len(blocks)))
    for reader in range(2):
        for name,positive,negative in CONTRASTS:
            cases=x[:,:,reader,-1,0,positive,:,0,0]-x[:,:,reader,-1,0,negative,:,0,0]
            block=cases.mean(axis=(1,2))
            row=dict(reader=READERS[reader],label=name,mean=float(block.mean()),
                minimum=float(block.min()),maximum=float(block.max()),block_means=block.tolist(),
                parent_means=cases.mean(axis=-1).tolist(),
                pointwise_block_bootstrap_95=np.quantile(block[resamples].mean(axis=1),(.025,.975)).tolist())
            for prefix,y in (('',block),('paired_',cases)):
                for label,condition in (('positive',y>1e-12),('tied',abs(y)<=1e-12),('negative',y< -1e-12)):
                    row[prefix+label]=int(condition.sum())
            focal.append(row)
    return dict(means=x.mean(axis=(0,1,6))),focal


def contract():
    return dict(run_id=RUN_ID,decision='D086',law='L24',stage='BOUNDARY_AND_READOUT_PILOT',
        config=asdict(CONFIG),tissues=list(TISSUES),disposable=DISPOSABLE,records=list(RECORDS),
        readers=list(READERS),stages=list(STAGES),fields=list(FIELDS),regions=list(REGIONS),
        metrics=list(METRICS),contrasts=[list(c) for c in CONTRASTS],focal_endpoints=8,
        primary_reader='native_T',primary_time=500,primary_region='posterior',primary_metric='damage_fidelity',
        seed_tag=TAG,workers=4,packet_bytes=2048,inherited_fields=['theta'],boundaries=1,
        theta_frozen_during_readout=True,R_V_ema_not_transmitted=True,parent_zaps=1,
        parent_conditions=['clean','damaged'],read_interventions=['on','off'],norm=.3,
        original_writer_rate=.0005,writer_speed_sweep=False,protection_factorial=False,
        child_damage=False,child_birth='centered_0.2_gaussian',child_R_birth='zero',
        native_T_rho=.002,native_T_c_m=.2,theta_only_rho=0.,theta_only_c_m=0.,
        source_life_fitness_cycles=1,source_bridge_lives=64,parent_lives=64,parent_replay_lives=64,
        descendant_lives=8192,descendant_replay_lives=8192,source_bridge_exact=True,
        full_independent_replay=True,replay_atol=1e-10,metrics_atol=1e-12,
        parent_state_axes='parent,condition,stage,field,row,column',
        descendant_axes='parent,reader,time,field,onoff,record,draw,row,column',
        value_axes='parent,reader,time,onoff,record,draw,region,metric',
        means_axes='reader,time,onoff,record,region,metric',
        scientific_pass_gate=None,automatic_followup=False,known_records_are_constructed=True,
        uncertainty='10000_block_bootstrap_percentile_pointwise_95_not_multiplicity_adjusted',
        no_biological_or_renewal_claim=True,source_outcome_known=True,
        reserve_bytes=RESERVE,output_allowance_bytes=ALLOWANCE,output_hashes=20)


def input_paths(root):
    out=root/'outputs'/OLD_ID
    old_manifest=out/'input_hashes.sha256'
    paths=[Path(line.split('  ',1)[1]) for line in old_manifest.read_text().splitlines()]
    status=json.loads((root/'runs'/OLD_ID/'STATUS.json').read_text())
    paths += [out/name for name in status['output_sha256']]
    paths += [root/'runs'/OLD_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENCE,'reviews/L24_SLOW_WRITING_GERMLINE_BARRIER_AUDIT_2026-09-03.md',
        'reviews/L23_EDGE_PHASE_CONTROL_2026-09-10.md','src/laws_confirmation/l17_r_channel.py',
        'src/laws_confirmation/io.py','src/laws_confirmation/__init__.py')]
    for package in PACKAGES:
        paths += list((base.sources_root()/package/'src').rglob('*.py'))
    return sorted(set(p.resolve() for p in paths))


def source_verified(root, hashes):
    out=root/'outputs'/OLD_ID;run=root/'runs'/OLD_ID
    status=json.loads((run/'STATUS.json').read_text())
    assert status['status']=='COMPLETE' and status['input_file_count']==108
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    assert len(status['output_sha256'])==8
    # Fixed audit identity, independent of the mutable old STATUS path.
    assert status['output_sha256']['audit.json']=='d5060eba59d755b9d497f96efee47ede11d050396ddb2cf5f50c5982a1b08571'
    assert status['output_sha256']['input_hashes.sha256']=='91fcbce96f70eb9b975a274ae49752a73b560c54ea26327d7642966ba78cc483'
    for name,digest in status['output_sha256'].items(): assert hashes[str(out/name)]==digest,name
    rows=[line.split('  ',1) for line in (out/'input_hashes.sha256').read_text().splitlines()]
    assert len(rows)==108 and len({p for _,p in rows})==108
    for digest,path in rows: assert hashes[path]==digest,path
    return True


def preflight(root, starting=True):
    assert external_root(root)==root.resolve()
    cpus=sorted(os.sched_getaffinity(0))
    if not cpus or len(cpus)>4 or not set(cpus)<=set(range(4)):
        raise RuntimeError('CPU affinity must be restricted to at most CPUs 0-3')
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        if os.environ.get(key)!='1': raise RuntimeError(f'{key}=1 required')
    if os.environ.get('PYTHONDONTWRITEBYTECODE')!='1': raise RuntimeError('disable local bytecode outputs')
    for key in ('TMPDIR','XDG_CACHE_HOME'):
        path=Path(os.environ.get(key,'/')).resolve()
        if root not in path.parents or not path.is_dir(): raise RuntimeError(f'external {key} required')
    if shutil.disk_usage(root).free < RESERVE+(ALLOWANCE if starting else 0):
        raise RuntimeError('insufficient external space: four GiB reserve plus 512 MiB allowance at launch')
    return cpus


def freeze_path(root): return root/'tmp'/f'{RUN_ID}_freeze.json'


def timing_path(root): return root/'tmp'/f'{RUN_ID}_benchmark.json'


def freeze(root):
    preflight(root)
    path=freeze_path(root)
    if path.exists() or timing_path(root).exists(): raise FileExistsError('immutable freeze already exists')
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    source_verified(root,hashes)
    record=dict(frozen_utc=utc_now(),contract=contract(),input_sha256=hashes,full_duration_new_outcomes_seen=False)
    strict_json(path,record,root)
    print(json.dumps(dict(status='FROZEN',input_hashes=len(hashes),freeze_sha256=sha256_file(path))),flush=True)
    return record


def frozen_inputs(root):
    record=json.loads(freeze_path(root).read_text())
    assert canonical_digest(record['contract'])==canonical_digest(contract())
    assert record['full_duration_new_outcomes_seen'] is False
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    assert record['input_sha256']==hashes,'frozen scientific input changed'
    source_verified(root,hashes)
    return hashes


def benchmark(root):
    cpus=preflight(root);path=timing_path(root)
    directory=root/'tmp'/f'{RUN_ID}_benchmark'
    if path.exists() or directory.exists(): raise FileExistsError('immutable benchmark already exists')
    tick=time.monotonic();hashes=frozen_inputs(root);hash_seconds=time.monotonic()-tick
    directory.mkdir()
    tick=time.monotonic()
    payload,record=execute_parent(context(DISPOSABLE),0,checker())
    base.atomic_npz(directory/'panel.npz',payload,root)
    strict_json(directory/'verification.json',record,root)
    with np.load(directory/'panel.npz',allow_pickle=False) as saved:
        for key in payload: np.testing.assert_array_equal(saved[key],payload[key])
    seconds=time.monotonic()-tick
    assert hashes==frozen_inputs(root)
    forecast=len(TISSUES)*CONFIG.parents*seconds+2*hash_seconds+180
    timing=dict(run_id=RUN_ID,passed=True,disposable=DISPOSABLE,completed_utc=utc_now(),
        config=asdict(CONFIG),effects_not_reported=True,parent_seconds=seconds,hash_seconds=hash_seconds,
        projected_seconds=forecast,must_detach=forecast>600,forecast_does_not_credit_parallel_speedup=True,
        cpu_affinity=cpus,input_sha256=hashes,freeze_sha256=sha256_file(freeze_path(root)),
        benchmark_files={str(p):sha256_file(p) for p in sorted(directory.iterdir())})
    strict_json(path,timing,root)
    print(json.dumps({k:v for k,v in timing.items() if k not in ('input_sha256','benchmark_files')},indent=2),flush=True)
    return timing


def validate_timing(root, timing, hashes):
    assert timing['run_id']==RUN_ID and timing['passed'] and timing['effects_not_reported']
    assert timing['disposable']==DISPOSABLE
    assert canonical_digest(timing['config'])==canonical_digest(asdict(CONFIG))
    assert timing['parent_seconds']>0 and timing['hash_seconds']>0
    assert timing['projected_seconds']==len(TISSUES)*CONFIG.parents*timing['parent_seconds']+2*timing['hash_seconds']+180
    assert timing['must_detach'] is (timing['projected_seconds']>600)
    assert timing['forecast_does_not_credit_parallel_speedup'] is True
    assert timing['input_sha256']==hashes
    assert timing['freeze_sha256']==sha256_file(freeze_path(root))
    expected={str(root/'tmp'/f'{RUN_ID}_benchmark'/p) for p in ('panel.npz','verification.json')}
    assert set(timing['benchmark_files'])==expected
    for p,digest in timing['benchmark_files'].items(): assert sha256_file(Path(p))==digest,p
    return True


def prepare(root):
    run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('immutable run already exists')
    cpus=preflight(root);hashes=frozen_inputs(root)
    timing=json.loads(timing_path(root).read_text());validate_timing(root,timing,hashes)
    hashes.update(timing['benchmark_files'])
    hashes.update({str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))})
    manifest=contract()|dict(prepared_utc=utc_now(),input_sha256=hashes,hash_contract=canonical_digest(hashes),
                            timing=timing,cpu_affinity=cpus,environment=environment_manifest())
    run.mkdir(parents=True);out.mkdir(parents=True)
    strict_json(run/'MANIFEST.json',manifest,root)
    atomic_text(out/'input_hashes.sha256',''.join(f'{hashes[p]}  {p}\n' for p in sorted(hashes)),root)
    strict_json(run/'STATUS.json',dict(status='PREPARED',run_id=RUN_ID),root)
    print(json.dumps(dict(status='PREPARED',input_hashes=len(hashes),estimated_seconds=timing['projected_seconds'])),flush=True)
    return manifest


def verify(root):
    run=root/'runs'/RUN_ID
    manifest=json.loads((run/'MANIFEST.json').read_text())
    assert json.loads((run/'STATUS.json').read_text())['status']=='PREPARED'
    assert not (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for key,value in contract().items(): assert canonical_digest(manifest[key])==canonical_digest(value),key
    inputs=frozen_inputs(root);timing=manifest['timing']
    assert timing==json.loads(timing_path(root).read_text())
    validate_timing(root,timing,inputs)
    expected=inputs|timing['benchmark_files']|{str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))}
    assert manifest['input_sha256']==expected and manifest['hash_contract']==canonical_digest(expected)
    assert (root/'outputs'/RUN_ID/'input_hashes.sha256').read_text()==''.join(f'{expected[p]}  {p}\n' for p in sorted(expected))
    return manifest


def detach(root):
    if not (root/'runs'/RUN_ID).exists(): prepare(root)
    manifest=verify(root);preflight(root)
    run=root/'runs'/RUN_ID;(run/'LAUNCH.lock').mkdir()
    logs=[root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout','stderr')]
    with logs[0].open('xb') as out,logs[1].open('xb') as err:
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_descendant_pilot',
            '--external-root',str(root),'--run'],cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record=dict(run_id=RUN_ID,pid=child.pid,launched_utc=utc_now(),polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'],status=str(run/'STATUS.json'),
        stdout_log=str(logs[0]),stderr_log=str(logs[1]))
    strict_json(run/'LAUNCH.json',record,root)
    atomic_text(run/'RUN.pid',str(child.pid)+'\n',root)
    print(json.dumps(record,indent=2),flush=True)
    return record


def run_experiment(root):
    manifest=verify(root);run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if manifest['timing']['must_detach'] and not (run/'LAUNCH.lock').is_dir():
        raise RuntimeError('detached execution required above ten minutes')
    (run/'EXECUTION.lock').mkdir();start=time.monotonic()
    try:
        preflight(root);records={}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending={pool.submit(execute_block,root,t):t for t in TISSUES}
            try:
                for future in as_completed(pending):
                    tissue=pending[future];records[tissue]=future.result();preflight(root,starting=False)
                    strict_json(run/'STATUS.json',dict(status='RUNNING',run_id=RUN_ID,
                        checked_blocks=len(records),updated_utc=utc_now()),root)
                    print(f'D086 block {tissue}: source bridges, independent replays and controls checked',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=[]
        for tissue in TISSUES:
            with np.load(out/f'block_{tissue}.npz',allow_pickle=False) as saved: blocks.append(saved['values'])
        summary,focal=summarize(blocks);check=checker()
        assert check.check_summary(blocks,summary,focal)
        base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as saved: assert check.check_summary(blocks,dict(saved),focal)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,focal=focal,
            scientific_verdict='NOT_CONFIRMED',blocks=[records[t] for t in TISSUES])
        strict_json(out/'analysis.json',analysis,root)
        assert check.check_summary(blocks,summary,json.loads((out/'analysis.json').read_text())['focal'])
        for path,digest in manifest['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,input_hashes_unchanged=True,input_hashes=len(manifest['input_sha256']),
            checked_blocks=8,parent_lives_replayed=64,exact_source_bridges=64,descendant_lives_replayed=8192,
            descendant_panels=64,descendant_snapshot_batches=320,saved_pool_verified=True,checked_utc=utc_now())
        strict_json(out/'verification.json',verification,root)
        paths=[out/f'block_{t}.{ext}' for t in TISSUES for ext in ('npz','json')]
        paths += [out/p for p in ('summary.npz','analysis.json','verification.json','input_hashes.sha256')]
        assert len(paths)==20
        write_hash_manifest(paths,out/'output_hashes.sha256',root)
        assert check.check_hashes(out/'output_hashes.sha256')==20
        total_bytes=sum(p.stat().st_size for p in paths)
        assert total_bytes<ALLOWANCE
        status=dict(status='COMPLETE',run_id=RUN_ID,completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            checked_blocks=8,verified_saved_analysis=True,output_bytes=total_bytes)
        strict_json(run/'STATUS.json',status,root);atomic_text(run/'COMPLETE',status['completed_utc']+'\n',root)
        print(json.dumps(status,indent=2),flush=True)
        return 0
    except Exception as error:
        status=dict(status='FAILED',run_id=RUN_ID,failed_utc=utc_now(),error=str(error),traceback=traceback.format_exc())
        strict_json(run/'STATUS.json',status,root);atomic_text(run/'FAILED',status['failed_utc']+'\n',root)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root',required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    for op in ('freeze','benchmark','prepare','detach','run'): group.add_argument('--'+op,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    for op in ('freeze','benchmark','prepare','detach','run'):
        if getattr(args,op):
            function=run_experiment if op=='run' else globals()[op]
            result=function(root)
            return result if isinstance(result,int) else 0


if __name__=='__main__': raise SystemExit(main())
