"""D092: one fixed late theta-write hold at the two qualified speeds."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
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
from . import l24_temporal_filter as temporal
from . import l24_speed_qualification as previous
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_write_protection_v1_attempt1'
TAG='l24-write-protection-v1'
RATES=(.0005,.005)
SPEEDS=('slow','fast')
HISTORIES=('baseline','sustained','late_pulse')
RECORDS=tuple(s+'_'+h for s in SPEEDS for h in HISTORIES)
LOGICAL_RECORDS=tuple(g+'_'+r for g in ('unprotected','protected') for r in RECORDS)
PROTECTED_INDICES=tuple(range(6,12))+tuple(range(18,24))
SOURCE_INDICES=tuple(range(6))+tuple(range(10,16))
WORKERS=4
CONTRASTS=(
    ('slow_unprotected_sustained_effect',((1,1),(0,-1))),
    ('slow_unprotected_pulse_effect',((2,1),(0,-1))),
    ('fast_unprotected_sustained_effect',((4,1),(3,-1))),
    ('fast_unprotected_pulse_effect',((5,1),(3,-1))),
    ('slow_protected_sustained_effect',((7,1),(6,-1))),
    ('slow_protected_pulse_effect',((8,1),(6,-1))),
    ('fast_protected_sustained_effect',((10,1),(9,-1))),
    ('fast_protected_pulse_effect',((11,1),(9,-1))),
    ('slow_sustained_cost',((1,1),(0,-1),(7,-1),(6,1))),
    ('slow_pulse_reduction',((2,1),(0,-1),(8,-1),(6,1))),
    ('fast_sustained_cost',((4,1),(3,-1),(10,-1),(9,1))),
    ('fast_pulse_reduction',((5,1),(3,-1),(11,-1),(9,1))),
    ('fast_minus_slow_sustained_cost',((4,1),(3,-1),(10,-1),(9,1),(1,-1),(0,1),(7,1),(6,-1))),
    ('fast_minus_slow_pulse_reduction',((5,1),(3,-1),(11,-1),(9,1),(2,-1),(0,1),(8,1),(6,-1))),
    ('slow_protected_minus_unprotected_baseline',((6,1),(0,-1))),
    ('fast_protected_minus_unprotected_baseline',((9,1),(3,-1))))
DELAY_LABELS=tuple(CONTRASTS[i][0] for i in (5,7,9,11))
WRITER_FOCAL=(('theta_delta_rms_whole',1,2,0),('theta_delta_projection_posterior',1,0,1))
SCIENCE=('src/laws_confirmation/l24_write_protection.py','scripts/audit_l24_write_protection_outputs.py',
    'tests/test_l24_write_protection.py','scripts/run_l24_write_protection.sh','protocols/L24_WRITE_PROTECTION_V1.md')


def checker():
    spec=importlib.util.spec_from_file_location('d092_independent_checker',Path(__file__).resolve().parents[2]/SCIENCE[1])
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def write_records(original,window=temporal.WINDOW):
    ref,theta=np.repeat(original['initial_writer'][:,None],6,axis=1)
    amplitudes=temporal.schedule(window)[:,[0,1,3]]
    enabled=np.ones(window.total,dtype=bool);enabled[window.active-window.pulse:window.active]=False
    rates=np.repeat(RATES,3)[:,None,None]
    project=source.api()['project_theta'];states=[];trace=[];details=[];weights=[np.zeros(3)]
    for tick in range(window.total+1):
        if tick:
            inputs=original['input_base']+amplitudes[tick-1,:,None,None]*original['input_delta']
            ref=ref+.002*(np.tile(inputs,(2,1,1))-ref)
            raw=(1-rates)*theta+rates*np.tanh(ref) if enabled[tick-1] else theta
            centered=raw-raw.mean(axis=(-2,-1),keepdims=True);std=centered.std(axis=(-2,-1))
            scale=.3/np.maximum(std,1e-9) if enabled[tick-1] else np.ones(6)
            details.append(np.stack((raw.mean(axis=(-2,-1)),std,scale),axis=-1).reshape(2,3,3))
            if enabled[tick-1]: theta=project(raw,.3)
            weights.append(.998*weights[-1]+.002*amplitudes[tick-1])
        fields=np.stack((ref,theta)).reshape(2,2,3,16,16)
        trace.append(np.stack([temporal.observe(fields[:,speed],original['targets'][1]) for speed in (0,1)]))
        if tick in window.times: states.append(fields)
    payload={k:original[k].copy() for k in ('input_base','input_delta','initial_writer','targets','permutation')}
    return payload|dict(schedule=amplitudes,write_enabled=enabled,writer_states=np.stack(states),
        writer_trace=np.stack(trace),proposal_details=np.stack(details),R_weights=np.stack(weights))


def build_packets(payload,window=temporal.WINDOW):
    return np.stack([payload['writer_states'][window.times.index(t),1].reshape(6,16,16)
        for t in window.boundaries]).reshape(12,16,16)


def logical_values(original,protected):
    return np.concatenate([part for end in (0,1) for part in
        (original['values'][:,:,:,10*end:10*end+6],protected[:,:,:,6*end:6*end+6])],axis=3)


def execute_parent(original,*,index,parent,cfg=source.CONFIG,window=temporal.WINDOW):
    check=checker();old=source.checker();payload=write_records(original,window)
    writer_error=check.check_writer(original,payload,window)
    payload['records']=build_packets(payload,window);packet_error=check.check_packets(payload,window)
    descendants=[];values=[];children=[]
    for reader in (0,1):
        raw,meta=source.descendants(tuple(source.encode(r) for r in payload['records']),index=index,parent=parent,reader=reader,cfg=cfg)
        meta['reader']=reader
        meta['replay_max_abs']=old.check_descendants(raw,payload['records'],source.context(index,cfg),parent,reader,meta)
        scores=source.measure(raw,payload['targets']);assert old.check_metrics(raw,payload['targets'],scores)
        descendants.append(raw);values.append(scores);children.append(meta)
    payload.update(descendants=np.stack(descendants),values=logical_values(original,np.stack(values)))
    assert check.check_aliases(original,payload)
    return payload,dict(parent=parent,passed=True,writer_max_abs=writer_error,packet_max_abs=packet_error,children=children)


def resamples(blocks):
    seed=int.from_bytes(hashlib.sha256((TAG+':block-bootstrap').encode()).digest()[:16],'little')
    return np.random.default_rng(seed).integers(0,blocks,(10000,blocks))


def summarize(blocks,window=temporal.WINDOW):
    values=np.stack([b['values'] for b in blocks])
    trace=np.stack([b['writer_trace'] for b in blocks]);reference=np.stack([b['reference_writer_trace'] for b in blocks])
    indices=resamples(len(blocks));rows=[];writer_rows=[];timing_rows=[];writer_timing=[]
    difference=previous.previous.difference
    child_cases={};writer_cases={}
    for end,tick in enumerate(window.boundaries):
        for metric in (0,2,4):
            for reader in (0,1):
                for label,terms in CONTRASTS:
                    cases=difference(values[:,:,reader,-1,0,12*end:12*end+12,:,0,metric],terms,2)
                    child_cases[(tick,reader,metric,label)]=cases
                    rows.append(temporal.pooled_row(cases,indices,boundary=tick,reader=source.READERS[reader],label=label,metric=source.METRICS[metric]))
        for metric,field,region,column in WRITER_FOCAL:
            flat=np.concatenate([t[:,:,tick,:,:,field,region,column].reshape(values.shape[0],values.shape[1],6)
                for t in (reference,trace)],axis=2)
            for label,terms in CONTRASTS:
                cases=difference(flat,terms,2)[...,None];writer_cases[(tick,metric,label)]=cases
                writer_rows.append(temporal.pooled_row(cases,indices,boundary=tick,metric=metric,label=label))
    first,last=window.boundaries
    for metric in (0,2,4):
        for reader in (0,1):
            for label in DELAY_LABELS:
                cases=child_cases[(last,reader,metric,label)]-child_cases[(first,reader,metric,label)]
                timing_rows.append(temporal.pooled_row(cases,indices,earlier=first,later=last,reader=source.READERS[reader],
                    label=label,metric=source.METRICS[metric]))
    for metric,*_ in WRITER_FOCAL:
        for label in DELAY_LABELS:
            cases=writer_cases[(last,metric,label)]-writer_cases[(first,metric,label)]
            writer_timing.append(temporal.pooled_row(cases,indices,earlier=first,later=last,metric=metric,label=label))
    summary=dict(means=values.mean(axis=(0,1,6)),writer_means=trace.mean(axis=(0,1)))
    for key in ('proposal_details','R_weights'):
        summary[key+'_means']=np.stack([b[key] for b in blocks]).mean(axis=(0,1))
    return summary,rows,writer_rows,timing_rows,writer_timing


def fractions(rows,window=temporal.WINDOW):
    result=[]
    for boundary in window.boundaries:
        for metric in ('damage_fidelity','damage_projection'):
            for speed in SPEEDS:
                for history in ('sustained','pulse'):
                    def get(protection):
                        row,=[r for r in rows if (r['boundary'],r['reader'],r['metric'],r['label'])==
                            (boundary,'native_T',metric,speed+'_'+protection+'_'+history+'_effect')]
                        return row['mean']
                    before,after=get('unprotected'),get('protected');available=before>1e-12
                    ratio=after/before if available else None
                    result.append(dict(boundary=boundary,metric=metric,speed=speed,history=history,
                        unprotected_effect=before,protected_effect=after,available=available,
                        retained_fraction=ratio,reduced_fraction=1-ratio if available else None))
    return result


def contract():
    return dict(run_id=RUN_ID,decision='D092',law='L24',source_run=previous.RUN_ID,
        mode='FIXED_LATE_THETA_HOLD_WITH_LIVE_R_AND_REOPENING',
        tissues=list(source.TISSUES),disposable=source.DISPOSABLE,descendant_config=asdict(source.CONFIG),
        window=asdict(temporal.WINDOW),writer_times=list(temporal.WINDOW.times),boundaries=list(temporal.WINDOW.boundaries),
        writer_rates=list(RATES),rho=.002,norm=.3,hold_updates=[450,500],hold_theta_bit_exact=True,
        hold_projection_disabled=True,reopen_first_update=500,R_always_live=True,R_reset=False,
        histories=list(HISTORIES),speeds=list(SPEEDS),records=list(RECORDS),logical_records=list(LOGICAL_RECORDS),
        record_count=12,logical_record_count=24,record_flattening='boundary_then_speed_then_history',
        logical_record_flattening='boundary_then_protection_then_speed_then_history',
        protected_logical_indices=list(PROTECTED_INDICES),unprotected_source_indices=list(SOURCE_INDICES),
        writer_state_axes='parent,checkpoint,field,speed,history,row,column',
        writer_trace_axes='parent,update,speed,history,field,region,metric',trace_metrics=list(temporal.TRACE_METRICS),
        logical_values_axes='parent,reader,child_time,onoff,logical_record,draw,region,metric',
        descendant_snapshots_protected_only=True,source_snapshots_retained_in_frozen_source_files=True,
        contrasts=[[label,[list(t) for t in terms]] for label,terms in CONTRASTS],delay_labels=list(DELAY_LABELS),
        writer_focal=[list(c) for c in WRITER_FOCAL],primary_reader='native_T',primary_writer_boundary=1000,
        primary_descendant_time=500,primary_region='posterior',primary_metric='damage_fidelity',
        primary_contrast='fast_minus_slow_pulse_reduction',binary_rows=64,continuous_rows=128,writer_rows=64,
        child_timing_rows=24,writer_timing_rows=8,fraction_rows=16,fractions_are_descriptive_without_CI=True,
        fraction_denominator_min=1e-12,fractions_not_clipped=True,scientific_pass_gate=None,automatic_followup=False,
        fast_rate_outside_original_E70_u_range=True,clock_gate_engineer_scheduled=True,rate_or_window_search=False,
        source_outcomes_known=True,new_full_duration_protection_outcomes_frozen_before_view=True,
        body_feedback=False,parent_body_physics_simulated=False,new_full_parent_lives=0,new_tissue_blocks=0,
        writer_trajectories_evaluated=192,independent_writer_replays=192,source_writer_trajectories_regenerated=0,
        descendant_lives_evaluated=12288,independent_descendant_replays=12288,source_off_anchor_lives_in_count=6144,
        new_unprotected_descendant_evaluations=0,source_on_snapshot_metrics_reused=6144,
        packet_bytes=2048,inherited_fields=['theta'],theta_frozen_in_descendant=True,new_birth_randomness=False,
        source_seed_tag=source.TAG,new_wrong_content_packets=0,source_wrong_controls_not_new_protection_evidence=True,
        early_protected_pulse_equals_baseline_by_construction=True,renewal_or_biological_claim=False,
        fitness_or_semantic_selectivity_claim=False,utility_is_engineer_declared=True,
        targets_not_supplied_to_writer_or_reader=True,positive_squared_error_is_worse=True,
        readers=list(source.READERS),regions=list(source.REGIONS),metrics=list(source.METRICS),
        bootstrap_seed=TAG+':block-bootstrap',bootstrap_resamples=10000,
        intervals='pointwise_95_whole_block_percentile_not_multiplicity_adjusted',
        writer_atol=1e-12,packet_atol=1e-12,replay_atol=1e-10,metric_atol=1e-12,
        source_writer_prefix_and_R_aliases_bit_exact=True,source_child_aliases_bit_exact=True,
        workers=WORKERS,max_cpus=4,reserve_bytes=source.RESERVE,output_allowance_bytes=source.ALLOWANCE,
        benchmark_byte_forecast='32_panels_plus_16_MiB_metadata',output_hashes=20)


def input_paths(root):
    out=root/'outputs'/previous.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        path=out/name;paths.append(path)
        paths.extend(Path(line.split('  ',1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/previous.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/name for name in (*SCIENCE,'reviews/L24_SPEED_QUALIFICATION_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root,hashes):
    out=root/'outputs'/previous.RUN_ID;run=root/'runs'/previous.RUN_ID
    for name,count in (('input_hashes.sha256',319),('output_hashes.sha256',20)):
        rows=[line.split('  ',1) for line in (out/name).read_text().splitlines()]
        assert len(rows)==count and len({p for _,p in rows})==count
        for digest,path in rows: assert hashes[path]==digest,path
    status=json.loads((run/'STATUS.json').read_text());analysis=json.loads((out/'analysis.json').read_text())
    assert status['status']=='COMPLETE' and status['verified_saved_analysis']
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    for key,value in previous.contract().items(): assert canonical_digest(analysis[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and json.loads((out/'verification.json').read_text())['passes']
    return previous.source_verified(root,hashes)


def check_source_pools(root):
    assert previous.check_source_pools(root)
    blocks=[]
    for tissue in source.TISSUES:
        with np.load(root/'outputs'/previous.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f:
            blocks.append({k:f[k] for k in ('values','writer_trace','proposal_details','geometry','R_weights')})
    analysis=json.loads((root/'outputs'/previous.RUN_ID/'analysis.json').read_text())
    with np.load(root/'outputs'/previous.RUN_ID/'summary.npz',allow_pickle=False) as f:
        assert previous.checker().check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'],temporal.WINDOW)
    assert previous.checker().check_qualification(analysis['summary'],analysis['qualification'],temporal.WINDOW)
    assert analysis['qualification'][1]['stronger_readable_channel_qualified']
    return True

def freeze_path(root): return root/'tmp'/f'{RUN_ID}_freeze.json'


def timing_path(root): return root/'tmp'/f'{RUN_ID}_benchmark.json'


def freeze(root):
    source.preflight(root);path=freeze_path(root)
    if path.exists() or timing_path(root).exists(): raise FileExistsError('immutable scientific freeze exists')
    hashes={str(p):sha256_file(p) for p in input_paths(root)};source_verified(root,hashes)
    source.strict_json(path,dict(frozen_utc=utc_now(),contract=contract(),input_sha256=hashes,new_full_duration_outcomes_seen=False),root)
    print(json.dumps(dict(status='FROZEN',input_hashes=len(hashes),freeze_sha256=sha256_file(path))),flush=True)


def frozen_inputs(root):
    saved=json.loads(freeze_path(root).read_text())
    assert canonical_digest(saved['contract'])==canonical_digest(contract()) and not saved['new_full_duration_outcomes_seen']
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    assert hashes==saved['input_sha256'],'frozen scientific input changed'
    source_verified(root,hashes);return hashes


def benchmark(root):
    cpus=source.preflight(root);path=timing_path(root);directory=root/'tmp'/f'{RUN_ID}_benchmark'
    if path.exists() or directory.exists(): raise FileExistsError('immutable benchmark exists')
    tick=time.monotonic();hashes=frozen_inputs(root);hash_seconds=time.monotonic()-tick
    directory.mkdir();tick=time.monotonic()
    with np.load(root/'tmp'/f'{previous.RUN_ID}_benchmark'/'panel.npz',allow_pickle=False) as f: original=dict(f)
    payload,record=execute_parent(original,index=source.DISPOSABLE,parent=0)
    source.base.atomic_npz(directory/'panel.npz',payload,root);source.strict_json(directory/'verification.json',record,root)
    with np.load(directory/'panel.npz',allow_pickle=False) as saved:
        for key,value in payload.items(): np.testing.assert_array_equal(saved[key],value)
    seconds=time.monotonic()-tick;assert hashes==frozen_inputs(root)
    forecast=32*seconds+2*hash_seconds+180
    projected_bytes=32*(directory/'panel.npz').stat().st_size+16*1024**2
    assert projected_bytes<source.ALLOWANCE,'benchmark output forecast exceeds fixed allowance'
    timing=dict(run_id=RUN_ID,passed=True,disposable=source.DISPOSABLE,contract_sha256=canonical_digest(contract()),
        completed_utc=utc_now(),parent_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,
        projected_output_bytes=projected_bytes,
        must_detach=forecast>600,forecast_does_not_credit_parallel_speedup=True,effects_not_reported=True,cpu_affinity=cpus,
        freeze_sha256=sha256_file(freeze_path(root)),input_sha256=hashes,
        benchmark_files={str(p):sha256_file(p) for p in sorted(directory.iterdir())})
    source.strict_json(path,timing,root)
    print(json.dumps({k:v for k,v in timing.items() if k not in ('input_sha256','benchmark_files')},indent=2),flush=True)
    return timing


def validate_timing(root,timing,hashes):
    assert timing['run_id']==RUN_ID and timing['passed'] and timing['effects_not_reported']
    assert timing['disposable']==source.DISPOSABLE and timing['contract_sha256']==canonical_digest(contract())
    assert timing['parent_seconds']>0 and timing['hash_seconds']>0
    assert timing['projected_seconds']==32*timing['parent_seconds']+2*timing['hash_seconds']+180
    assert timing['must_detach'] is (timing['projected_seconds']>600) and timing['forecast_does_not_credit_parallel_speedup']
    assert timing['input_sha256']==hashes and timing['freeze_sha256']==sha256_file(freeze_path(root))
    expected={str(root/'tmp'/f'{RUN_ID}_benchmark'/name) for name in ('panel.npz','verification.json')}
    assert set(timing['benchmark_files'])==expected
    assert timing['projected_output_bytes']==32*(root/'tmp'/f'{RUN_ID}_benchmark'/'panel.npz').stat().st_size+16*1024**2
    assert timing['projected_output_bytes']<source.ALLOWANCE
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
    run=root/'runs'/RUN_ID;manifest=json.loads((run/'MANIFEST.json').read_text())
    assert json.loads((run/'STATUS.json').read_text())['status']=='PREPARED'
    assert not (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for key,value in contract().items(): assert canonical_digest(manifest[key])==canonical_digest(value),key
    hashes=frozen_inputs(root);timing=json.loads(timing_path(root).read_text())
    assert timing==manifest['timing'];validate_timing(root,timing,hashes)
    expected=hashes|timing['benchmark_files']|{str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))}
    assert manifest['input_sha256']==expected and manifest['hash_contract']==canonical_digest(expected)
    assert (root/'outputs'/RUN_ID/'input_hashes.sha256').read_text()==''.join(f'{expected[p]}  {p}\n' for p in sorted(expected))
    return manifest


def detach(root):
    if not (root/'runs'/RUN_ID).exists(): prepare(root)
    manifest=verify(root);source.preflight(root);run=root/'runs'/RUN_ID;(run/'LAUNCH.lock').mkdir()
    logs=[root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout','stderr')]
    with logs[0].open('xb') as out,logs[1].open('xb') as err:
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_write_protection','--external-root',str(root),'--run'],
            cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record=dict(run_id=RUN_ID,pid=child.pid,launched_utc=utc_now(),polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'],status=str(run/'STATUS.json'))
    source.strict_json(run/'LAUNCH.json',record,root);atomic_text(run/'RUN.pid',str(child.pid)+'\n',root)
    print(json.dumps(record,indent=2),flush=True);return record


def execute_block(root,index):
    path=root/'outputs'/previous.RUN_ID/f'block_{index}.npz'
    with np.load(path,allow_pickle=False) as f: original=dict(f)
    metadata=json.loads(path.with_suffix('.json').read_text())
    assert metadata['tissue']==index and metadata['passed'] and len(metadata['parents'])==4
    assert metadata['window']==asdict(temporal.WINDOW) and metadata['writer_rates']==list(RATES)
    pieces=[];parents=[]
    for parent in range(4):
        before={k:v[parent] for k,v in original.items()}
        assert metadata['parents'][parent]['parent']==parent and metadata['parents'][parent]['passed']
        payload,record=execute_parent(before,index=index,parent=parent)
        pieces.append(payload);parents.append(record)
    block={k:np.stack([p[k] for p in pieces]) for k in pieces[0]};out=root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz',block,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        assert set(saved.files)==set(block)
        for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
    record=dict(tissue=index,passed=True,parents=parents,window=asdict(temporal.WINDOW),
        writer_rates=list(RATES),hold_updates=[450,500],descendant_config=asdict(source.CONFIG))
    source.strict_json(out/f'block_{index}.json',record,root)
    assert json.loads((out/f'block_{index}.json').read_text())==json.loads(json.dumps(record))
    return record


def pooled_blocks(root):
    blocks=[]
    for t in source.TISSUES:
        with np.load(root/'outputs'/RUN_ID/f'block_{t}.npz',allow_pickle=False) as f:
            block={k:f[k] for k in ('values','writer_trace','proposal_details','R_weights')}
        with np.load(root/'outputs'/previous.RUN_ID/f'block_{t}.npz',allow_pickle=False) as f:
            block['reference_writer_trace']=f['writer_trace']
        blocks.append(block)
    return blocks


def run_experiment(root):
    manifest=verify(root);run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if manifest['timing']['must_detach'] and not (run/'LAUNCH.lock').is_dir(): raise RuntimeError('detachment required over ten minutes')
    (run/'EXECUTION.lock').mkdir();start=time.monotonic()
    try:
        source.preflight(root);records={}
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn')) as pool:
            pending={pool.submit(execute_block,root,t):t for t in source.TISSUES}
            try:
                for future in as_completed(pending):
                    tissue=pending[future];records[tissue]=future.result();source.preflight(root,starting=False)
                    source.strict_json(run/'STATUS.json',dict(status='RUNNING',run_id=RUN_ID,checked_blocks=len(records),updated_utc=utc_now()),root)
                    print(f'D092 block {tissue}: write hold/reopening, live R, source aliases and child replay pass',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=pooled_blocks(root);assert check_source_pools(root)
        summary,rows,writer_rows,timing_rows,writer_timing=summarize(blocks);check=checker()
        assert check.check_summary(blocks,summary,rows,writer_rows,timing_rows,writer_timing,temporal.WINDOW)
        ratios=fractions(rows);assert check.check_fractions(rows,ratios,temporal.WINDOW)
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as f:
            assert check.check_summary(blocks,dict(f),rows,writer_rows,timing_rows,writer_timing,temporal.WINDOW)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,
            writer_summary=writer_rows,timing_summary=timing_rows,writer_timing_summary=writer_timing,
            descriptive_fractions=ratios,blocks=[records[t] for t in source.TISSUES],source_pools_rechecked=True)
        source.strict_json(out/'analysis.json',analysis,root);saved=json.loads((out/'analysis.json').read_text())
        assert check.check_summary(blocks,summary,saved['summary'],saved['writer_summary'],saved['timing_summary'],saved['writer_timing_summary'],temporal.WINDOW)
        assert check.check_fractions(saved['summary'],saved['descriptive_fractions'],temporal.WINDOW)
        for path,digest in manifest['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,writer_trajectories_replayed=192,
            source_writer_prefix_exact=True,R_unchanged_and_live=True,hold_exact=True,reopened=True,
            daughter_lives_independently_replayed=12288,source_off_anchors_exact=True,
            source_logical_metric_aliases_exact=True,early_protected_pulse_baseline_alias_exact=True,
            source_pools_rechecked=True,independent_pool=True,input_hashes=len(manifest['input_sha256']),
            writer_max_abs=max(p['writer_max_abs'] for r in records.values() for p in r['parents']),
            packet_max_abs=max(p['packet_max_abs'] for r in records.values() for p in r['parents']),
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
    for op in ('freeze','benchmark','prepare','detach','run','audit-saved'): group.add_argument('--'+op,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    if args.audit_saved: audit_saved(root);return 0
    for op in ('freeze','benchmark','prepare','detach','run'):
        if getattr(args,op):
            result=(run_experiment if op=='run' else globals()[op])(root)
            return result if isinstance(result,int) else 0


def audit_saved(root):
    """Read-only saved arrays/hash/metric/pool audit; no recurrent dynamics."""
    tick=time.monotonic();source.preflight(root,starting=False)
    out=root/'outputs'/RUN_ID;run=root/'runs'/RUN_ID
    manifest=json.loads((run/'MANIFEST.json').read_text());status=json.loads((run/'STATUS.json').read_text())
    assert status['status']=='COMPLETE' and status['verified_saved_analysis']
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    hashes=frozen_inputs(root);validate_timing(root,manifest['timing'],hashes)
    expected=hashes|manifest['timing']['benchmark_files']|{str(p):sha256_file(p) for p in (freeze_path(root),timing_path(root))}
    assert manifest['input_sha256']==expected and manifest['hash_contract']==canonical_digest(expected)
    for key,value in contract().items(): assert canonical_digest(manifest[key])==canonical_digest(value),key
    assert source.checker().check_hashes(out/'input_hashes.sha256')==len(expected)
    assert (out/'input_hashes.sha256').read_text()==''.join(f'{expected[p]}  {p}\n' for p in sorted(expected))
    assert source.checker().check_hashes(out/'output_hashes.sha256')==20
    check=checker();observer_error=0.
    for tissue in source.TISSUES:
        with np.load(root/'outputs'/previous.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: before=dict(f)
        with np.load(out/f'block_{tissue}.npz',allow_pickle=False) as f: block=dict(f)
        for parent in range(4):
            original={k:v[parent] for k,v in before.items()};payload={k:v[parent] for k,v in block.items()}
            assert check.check_packets(payload,temporal.WINDOW)<=1e-12
            assert check.check_aliases(original,payload)
            for position,t in enumerate(temporal.WINDOW.times):
                observer_error=max(observer_error,check.close(check.observer(payload['writer_states'][position],payload['targets'][1]),payload['writer_trace'][t]))
            for reader in (0,1):
                scores=np.take(payload['values'][reader],PROTECTED_INDICES,axis=2)
                assert source.checker().check_metrics(payload['descendants'][reader],payload['targets'],scores)
    assert check_source_pools(root);analysis=json.loads((out/'analysis.json').read_text())
    for key,value in contract().items(): assert canonical_digest(analysis[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and analysis['source_pools_rechecked']
    assert json.loads((out/'verification.json').read_text())['passes']
    blocks=pooled_blocks(root)
    with np.load(out/'summary.npz',allow_pickle=False) as f:
        assert check.check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'],
            analysis['timing_summary'],analysis['writer_timing_summary'],temporal.WINDOW)
    assert check.check_fractions(analysis['summary'],analysis['descriptive_fractions'],temporal.WINDOW)
    assert source.checker().check_hashes(out/'input_hashes.sha256')==len(expected)
    assert source.checker().check_hashes(out/'output_hashes.sha256')==20
    result=dict(passed=True,read_only=True,input_hashes=len(expected),output_hashes=20,writer_observer_batches=320,
        child_snapshot_metric_batches=320,observer_max_abs=observer_error,source_pools_rechecked=True,
        rows_checked=[192,64,24,8],fractions_checked=16,dynamics_or_writer_recurrences_replayed=0,elapsed_seconds=time.monotonic()-tick)
    print(json.dumps(result,indent=2),flush=True);return result

if __name__=='__main__': raise SystemExit(main())

