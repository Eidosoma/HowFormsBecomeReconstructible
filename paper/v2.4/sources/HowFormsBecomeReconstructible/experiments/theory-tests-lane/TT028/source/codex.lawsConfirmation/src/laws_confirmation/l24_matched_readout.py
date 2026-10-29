"""D088: norm- and chord-matched weak messages around D086's clean record."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import importlib.util
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l24_descendant_pilot as source
from . import l24_signal_chain as trace
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_matched_readout_v1_attempt1'
RECORDS=('clean','actual','directed','directed_reversed','directed_shuffled','actual_reversed','actual_shuffled')
CONTRASTS=(('directed_minus_clean',2,0),('directed_minus_reversed',2,3),('directed_minus_shuffled',2,4),
           ('directed_minus_actual',2,1),('actual_minus_reversed',1,5),('actual_minus_shuffled',1,6),
           ('source_actual_minus_clean',1,0))
GEOMETRY_METRICS=('record_rms','delta_rms','record_mean','injury_projection','posterior_delta_energy_fraction','delta_max_abs')
SCIENCE=('src/laws_confirmation/l24_matched_readout.py','scripts/audit_l24_matched_readout_outputs.py',
         'tests/test_l24_matched_readout.py','scripts/run_l24_matched_readout.sh','protocols/L24_MATCHED_READOUT_V1.md')
WORKERS=4


def checker():
    spec=importlib.util.spec_from_file_location('d088_independent_checker',Path(__file__).resolve().parents[2]/SCIENCE[1])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def rms(x): return float(np.sqrt(np.mean(np.square(x))))


def tangent(b,direction):
    centered=direction-direction.mean()
    result=centered-b*(np.mean(centered*b)/np.mean(b*b))
    length=rms(result)
    if not np.isfinite(length) or length<=1e-12: raise ValueError('degenerate direction; no substitute or dropped parent')
    return result/length


def construct(original):
    b,actual=original['records'][:2];radius,distance=rms(b),rms(actual-b)
    if abs(b.mean())>1e-12 or abs(radius-.3)>1e-12 or not (0<distance<2*radius):
        raise ValueError('source baseline/radius/chord is outside the declared geometry')
    goal=original['records'][5]-original['records'][4];delta=actual-b
    perm=original['permutation']
    directions=np.stack((goal,goal.ravel()[perm].reshape(16,16),delta,delta.ravel()[perm].reshape(16,16)))
    units=np.stack([tangent(b,x) for x in directions])
    cosine=1-distance**2/(2*radius**2)
    amplitude=distance*np.sqrt(1-distance**2/(4*radius**2))
    move=lambda u:cosine*b+amplitude*u
    records=np.stack((b,actual,move(units[0]),move(-units[0]),move(units[1]),move(-units[2]),move(units[3])))
    reconstructed=move(units[2])
    direction=(original['targets'][1]-original['targets'][0])/2
    stats=[];available=[]
    for record in records:
        change=record-b;energy=float(np.sum(change**2));available.append(energy>0)
        stats.append((rms(record),rms(change),float(record.mean()),float(np.mean(change*direction)),
            float(np.sum(change[:,12:]**2)/energy) if energy>0 else 0.,float(np.max(abs(change)))))
    return dict(records=records,directions=directions,units=units,reconstructed_actual=reconstructed,
        geometry=np.array(stats),geometry_energy_available=np.array(available),
        geometry_parameters=np.array((radius,distance,cosine,amplitude)),targets=original['targets'].copy(),permutation=perm.copy())


def execute_parent(original,*,index,parent,cfg=source.CONFIG):
    check=checker();payload=construct(original)
    geometry_error=check.check_geometry(original,payload)
    old=source.checker();states=[];values=[];records=[]
    for reader in (0,1):
        raw,meta=source.descendants(tuple(source.encode(x) for x in payload['records']),
            index=index,parent=parent,reader=reader,cfg=cfg)
        meta['reader']=reader
        meta['replay_max_abs']=old.check_descendants(raw,payload['records'],source.context(index,cfg),parent,reader,meta)
        scores=source.measure(raw,payload['targets']);assert old.check_metrics(raw,payload['targets'],scores)
        states.append(raw);values.append(scores);records.append(meta)
    payload.update(descendants=np.stack(states),values=np.stack(values))
    assert check.check_anchors_and_aliases(original,payload)
    return payload,dict(parent=parent,passed=True,geometry_max_abs=geometry_error,source_anchors_exact=True,children=records)


def execute_block(root,index):
    path=root/'outputs'/source.RUN_ID/f'block_{index}.npz'
    with np.load(path,allow_pickle=False) as f: original=dict(f)
    metadata=json.loads(path.with_suffix('.json').read_text())
    assert trace.checker().source_block_check(original,metadata,index)
    pieces=[];records=[]
    for parent in range(4):
        payload,record=execute_parent({k:v[parent] for k,v in original.items()},index=index,parent=parent)
        pieces.append(payload);records.append(record)
    block={k:np.stack([p[k] for p in pieces]) for k in pieces[0]}
    out=root/'outputs'/RUN_ID;source.base.atomic_npz(out/f'block_{index}.npz',block,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
    record=dict(tissue=index,passed=True,parents=records,config=asdict(source.CONFIG))
    source.strict_json(out/f'block_{index}.json',record,root)
    assert json.loads((out/f'block_{index}.json').read_text())==json.loads(json.dumps(record))
    return record


def summarize(blocks):
    x=np.stack(blocks)
    resamples=source.rng(0,0,'block_bootstrap').integers(0,len(blocks),(10000,len(blocks)))
    rows=[]
    for metric in (0,2,4):
        for reader in (0,1):
            for name,positive,negative in CONTRASTS:
                cases=x[:,:,reader,-1,0,positive,:,0,metric]-x[:,:,reader,-1,0,negative,:,0,metric]
                means=cases.mean(axis=(1,2))
                row=dict(reader=source.READERS[reader],label=name,metric=source.METRICS[metric],
                    reused_source_contrast=name.startswith('source_'),mean=float(means.mean()),
                    minimum=float(means.min()),maximum=float(means.max()),block_means=means.tolist(),
                    parent_means=cases.mean(axis=-1).tolist(),
                    pointwise_block_bootstrap_95=np.quantile(means[resamples].mean(axis=1),(.025,.975)).tolist())
                for prefix,y in (('',means),('paired_',cases)):
                    for label,test in (('positive',y>1e-12),('tied',abs(y)<=1e-12),('negative',y< -1e-12)):
                        row[prefix+label]=int(test.sum())
                rows.append(row)
    return dict(means=x.mean(axis=(0,1,6))),rows


def contract():
    return dict(run_id=RUN_ID,decision='D088',law='L24',source_run=source.RUN_ID,trace_run=trace.RUN_ID,
        mode='MATCHED_WEAK_READOUT',tissues=list(source.TISSUES),disposable=source.DISPOSABLE,
        config=asdict(source.CONFIG),records=list(RECORDS),readers=list(source.READERS),
        regions=list(source.REGIONS),metrics=list(source.METRICS),contrasts=[list(x) for x in CONTRASTS],
        primary_reader='native_T',primary_time=500,primary_region='posterior',primary_metric='damage_fidelity',
        binary_rows=14,continuous_rows=28,source_only_binary_rows=2,summary_rows=42,
        continuous_metrics=['damage_projection','damage_squared_error'],positive_squared_error_is_worse=True,
        constructor='constant_norm_sphere_chord_with_centered_baseline_tangent_direction',
        radius='source_clean_record_RMS_point3',distance='per_parent_RMS_actual_minus_clean',
        directed_direction='source_known_damage_minus_known_clean',shuffle='source_saved_permutation_before_tangent_projection',
        geometry_metrics=list(GEOMETRY_METRICS),direction_order=['directed','directed_shuffled','actual','actual_shuffled'],
        geometry_parameter_order=['radius','distance','cosine','amplitude'],
        baseline_identical=True,global_RMS_and_delta_RMS_matched=True,regional_energy_matched=False,
        marginal_histogram_preserved_after_tangent_projection=False,optimal_reader_direction_claim=False,
        geometry_atol=1e-12,degenerate_tangent_floor=1e-12,degenerate_action='fail_no_substitution_or_drop',
        writer_rates_changed=False,parent_lives_generated=0,inherited_fields=['theta'],packet_bytes=2048,
        daughter_lives_evaluated=7168,daughter_lives_independently_replayed=7168,
        source_anchor_lives_in_evaluated_count=2048,new_control_condition_lives_in_evaluated_count=5120,
        source_anchor_panels=64,source_anchor_saved_snapshots=320,source_anchors_bit_exact=True,
        new_tissue_blocks=0,new_birth_randomness=False,source_outcomes_known=True,new_weak_outcomes_frozen_before_view=True,
        source_seed_tag=source.TAG,source_bootstrap_reused=True,bootstrap_resamples=10000,
        intervals='pointwise_95_whole_block_percentile_not_multiplicity_adjusted',
        saved_times=list(source.CONFIG.times),descendant_axes='parent,reader,time,field,onoff,record,draw,row,column',
        value_axes='parent,reader,time,onoff,record,draw,region,metric',
        means_axes='reader,time,onoff,record,region,metric',theta_frozen_in_descendant=True,
        scientific_pass_gate=None,automatic_followup=False,renewal_or_biological_claim=False,
        replay_atol=1e-10,metric_atol=1e-12,workers=4,max_cpus=4,
        reserve_bytes=source.RESERVE,output_allowance_bytes=source.ALLOWANCE,output_hashes=20)


def input_paths(root):
    out=root/'outputs'/trace.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        p=out/name;paths.append(p)
        paths.extend(Path(line.split('  ',1)[1]) for line in p.read_text().splitlines())
    paths += [root/'runs'/trace.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENCE,'reviews/L24_SIGNAL_CHAIN_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root,hashes):
    out=root/'outputs'/trace.RUN_ID;run=root/'runs'/trace.RUN_ID
    for name,count in (('input_hashes.sha256',191),('output_hashes.sha256',12)):
        rows=[line.split('  ',1) for line in (out/name).read_text().splitlines()]
        assert len(rows)==count and len({p for _,p in rows})==count
        for digest,path in rows: assert hashes[path]==digest,path
    status=json.loads((run/'STATUS.json').read_text());analysis=json.loads((out/'analysis.json').read_text())
    assert status['status']=='COMPLETE' and status['verified_saved_analysis'] and status['new_dynamics']==0
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    for key,value in trace.contract().items(): assert canonical_digest(analysis[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and json.loads((out/'verification.json').read_text())['passes']
    return trace.checker().source_manifest_check(root,hashes)


def freeze_path(root): return root/'tmp'/f'{RUN_ID}_freeze.json'


def timing_path(root): return root/'tmp'/f'{RUN_ID}_benchmark.json'


def freeze(root):
    source.preflight(root);path=freeze_path(root)
    if path.exists() or timing_path(root).exists(): raise FileExistsError('immutable freeze exists')
    hashes={str(p):sha256_file(p) for p in input_paths(root)};source_verified(root,hashes)
    source.strict_json(path,dict(frozen_utc=utc_now(),contract=contract(),input_sha256=hashes,new_full_duration_outcomes_seen=False),root)
    print(json.dumps(dict(status='FROZEN',input_hashes=len(hashes),freeze_sha256=sha256_file(path))),flush=True)


def frozen_inputs(root):
    record=json.loads(freeze_path(root).read_text())
    assert canonical_digest(record['contract'])==canonical_digest(contract()) and not record['new_full_duration_outcomes_seen']
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    assert hashes==record['input_sha256'],'frozen scientific input changed'
    source_verified(root,hashes);return hashes


def benchmark(root):
    cpus=source.preflight(root);path=timing_path(root);directory=root/'tmp'/f'{RUN_ID}_benchmark'
    if path.exists() or directory.exists(): raise FileExistsError('immutable benchmark exists')
    tick=time.monotonic();hashes=frozen_inputs(root);hash_seconds=time.monotonic()-tick
    directory.mkdir();tick=time.monotonic()
    with np.load(root/'tmp'/f'{source.RUN_ID}_benchmark'/'panel.npz',allow_pickle=False) as f: original=dict(f)
    payload,record=execute_parent(original,index=source.DISPOSABLE,parent=0)
    source.base.atomic_npz(directory/'panel.npz',payload,root)
    source.strict_json(directory/'verification.json',record,root)
    with np.load(directory/'panel.npz',allow_pickle=False) as saved:
        for key,value in payload.items(): np.testing.assert_array_equal(saved[key],value)
    seconds=time.monotonic()-tick;assert hashes==frozen_inputs(root)
    forecast=32*seconds+2*hash_seconds+180
    timing=dict(run_id=RUN_ID,passed=True,disposable=source.DISPOSABLE,config=asdict(source.CONFIG),records=list(RECORDS),
        completed_utc=utc_now(),parent_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,
        must_detach=forecast>600,forecast_does_not_credit_parallel_speedup=True,effects_not_reported=True,cpu_affinity=cpus,
        freeze_sha256=sha256_file(freeze_path(root)),input_sha256=hashes,
        benchmark_files={str(p):sha256_file(p) for p in sorted(directory.iterdir())})
    source.strict_json(path,timing,root)
    print(json.dumps({k:v for k,v in timing.items() if k not in ('input_sha256','benchmark_files')},indent=2),flush=True)
    return timing


def validate_timing(root,timing,hashes):
    assert timing['run_id']==RUN_ID and timing['passed'] and timing['effects_not_reported']
    assert timing['disposable']==source.DISPOSABLE and timing['records']==list(RECORDS)
    assert canonical_digest(timing['config'])==canonical_digest(asdict(source.CONFIG))
    assert timing['parent_seconds']>0 and timing['hash_seconds']>0
    assert timing['projected_seconds']==32*timing['parent_seconds']+2*timing['hash_seconds']+180
    assert timing['must_detach'] is (timing['projected_seconds']>600) and timing['forecast_does_not_credit_parallel_speedup']
    assert timing['input_sha256']==hashes and timing['freeze_sha256']==sha256_file(freeze_path(root))
    expected={str(root/'tmp'/f'{RUN_ID}_benchmark'/name) for name in ('panel.npz','verification.json')}
    assert set(timing['benchmark_files'])==expected
    for path,digest in timing['benchmark_files'].items(): assert sha256_file(Path(path))==digest,path
    return True


def prepare(root):
    run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('immutable run exists')
    cpus=source.preflight(root);hashes=frozen_inputs(root);timing=json.loads(timing_path(root).read_text())
    validate_timing(root,timing,hashes);hashes.update(timing['benchmark_files'])
    hashes.update({str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))})
    run.mkdir(parents=True);out.mkdir(parents=True)
    manifest=contract()|dict(prepared_utc=utc_now(),input_sha256=hashes,hash_contract=canonical_digest(hashes),
                            timing=timing,cpu_affinity=cpus,environment=environment_manifest())
    source.strict_json(run/'MANIFEST.json',manifest,root)
    atomic_text(out/'input_hashes.sha256',''.join(f'{hashes[p]}  {p}\n' for p in sorted(hashes)),root)
    source.strict_json(run/'STATUS.json',dict(status='PREPARED',run_id=RUN_ID),root)
    print(json.dumps(dict(status='PREPARED',input_hashes=len(hashes),estimated_seconds=timing['projected_seconds'])),flush=True)
    return manifest


def verify(root):
    run=root/'runs'/RUN_ID;m=json.loads((run/'MANIFEST.json').read_text())
    assert json.loads((run/'STATUS.json').read_text())['status']=='PREPARED'
    assert not (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for key,value in contract().items(): assert canonical_digest(m[key])==canonical_digest(value),key
    hashes=frozen_inputs(root);timing=json.loads(timing_path(root).read_text())
    assert timing==m['timing'];validate_timing(root,timing,hashes)
    expected=hashes|timing['benchmark_files']|{str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))}
    assert m['input_sha256']==expected and m['hash_contract']==canonical_digest(expected)
    assert (root/'outputs'/RUN_ID/'input_hashes.sha256').read_text()==''.join(f'{expected[p]}  {p}\n' for p in sorted(expected))
    return m


def detach(root):
    if not (root/'runs'/RUN_ID).exists(): prepare(root)
    manifest=verify(root);source.preflight(root);run=root/'runs'/RUN_ID;(run/'LAUNCH.lock').mkdir()
    logs=[root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout','stderr')]
    with logs[0].open('xb') as out,logs[1].open('xb') as err:
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_matched_readout','--external-root',str(root),'--run'],
            cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record=dict(run_id=RUN_ID,pid=child.pid,launched_utc=utc_now(),polling_owner='user',
                estimated_seconds=manifest['timing']['projected_seconds'],status=str(run/'STATUS.json'))
    source.strict_json(run/'LAUNCH.json',record,root);atomic_text(run/'RUN.pid',str(child.pid)+'\n',root)
    print(json.dumps(record,indent=2),flush=True);return record


def run_experiment(root):
    m=verify(root);run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if m['timing']['must_detach'] and not (run/'LAUNCH.lock').is_dir(): raise RuntimeError('detachment required over ten minutes')
    (run/'EXECUTION.lock').mkdir();start=time.monotonic()
    try:
        source.preflight(root);records={}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending={pool.submit(execute_block,root,t):t for t in source.TISSUES}
            try:
                for future in as_completed(pending):
                    t=pending[future];records[t]=future.result();source.preflight(root,starting=False)
                    source.strict_json(run/'STATUS.json',dict(status='RUNNING',run_id=RUN_ID,checked_blocks=len(records),updated_utc=utc_now()),root)
                    print(f'D088 block {t}: matched geometry, exact anchors and independent replays pass',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=[];old_values=[];geometry=[]
        for t in source.TISSUES:
            with np.load(out/f'block_{t}.npz',allow_pickle=False) as f: blocks.append(f['values']);geometry.append(f['geometry'])
            with np.load(root/'outputs'/source.RUN_ID/f'block_{t}.npz',allow_pickle=False) as f: old_values.append(f['values'])
        original_analysis=json.loads((root/'outputs'/source.RUN_ID/'analysis.json').read_text())
        with np.load(root/'outputs'/source.RUN_ID/'summary.npz',allow_pickle=False) as f:
            assert source.checker().check_summary(old_values,dict(f),original_analysis['focal'])
        summary,rows=summarize(blocks);check=checker();assert check.check_summary(blocks,summary,rows,original_analysis['focal'])
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as f: assert check.check_summary(blocks,dict(f),rows,original_analysis['focal'])
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,blocks=[records[t] for t in source.TISSUES],
            source_focal=original_analysis['focal'],geometry_means=np.stack(geometry).mean(axis=(0,1)).tolist())
        source.strict_json(out/'analysis.json',analysis,root)
        assert check.check_summary(blocks,summary,json.loads((out/'analysis.json').read_text())['summary'],original_analysis['focal'])
        for path,digest in m['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,geometry_checks=32,anchor_snapshot_batches=320,
            independently_replayed_daughter_lives=7168,independent_pool=True,source_pool_rechecked=True,input_hashes=len(m['input_sha256']),
            geometry_max_abs=max(p['geometry_max_abs'] for r in records.values() for p in r['parents']),
            replay_max_abs=max(c['replay_max_abs'] for r in records.values() for p in r['parents'] for c in p['children']),checked_utc=utc_now())
        source.strict_json(out/'verification.json',verification,root)
        paths=[out/f'block_{t}.{ext}' for t in source.TISSUES for ext in ('npz','json')]
        paths += [out/name for name in ('summary.npz','analysis.json','verification.json','input_hashes.sha256')]
        assert len(paths)==20;write_hash_manifest(paths,out/'output_hashes.sha256',root)
        assert source.checker().check_hashes(out/'output_hashes.sha256')==20
        total=sum(p.stat().st_size for p in paths);assert total<source.ALLOWANCE
        status=dict(status='COMPLETE',run_id=RUN_ID,completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
                    checked_blocks=8,verified_saved_analysis=True,output_bytes=total)
        source.strict_json(run/'STATUS.json',status,root);atomic_text(run/'COMPLETE',status['completed_utc']+'\n',root)
        print(json.dumps(status,indent=2),flush=True);return 0
    except Exception as error:
        source.strict_json(run/'STATUS.json',dict(status='FAILED',error=str(error),traceback=traceback.format_exc(),failed_utc=utc_now()),root)
        atomic_text(run/'FAILED',utc_now()+'\n',root);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--external-root',required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    for op in ('freeze','benchmark','prepare','detach','run'): group.add_argument('--'+op,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    for op in ('freeze','benchmark','prepare','detach','run'):
        if getattr(args,op):
            result=(run_experiment if op=='run' else globals()[op])(root)
            return result if isinstance(result,int) else 0


if __name__=='__main__': raise SystemExit(main())
