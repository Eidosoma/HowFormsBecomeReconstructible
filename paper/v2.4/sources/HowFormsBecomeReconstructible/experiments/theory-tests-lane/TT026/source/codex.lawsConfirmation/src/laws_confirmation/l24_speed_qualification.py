"""D091: a fixed tenfold writer-speed positive control, before protection."""
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
from . import l24_recovery_reference as previous
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_speed_qualification_v1_attempt1'
TAG='l24-speed-qualification-v1'
RATES=(.0005,.005)
SPEEDS=('slow','fast')
HISTORIES=('baseline','sustained','late_pulse')
RECORDS=('slow_baseline','slow_sustained','slow_late_pulse','fast_baseline','fast_sustained','fast_late_pulse',
    'fast_sustained_reversed','fast_sustained_shuffled','fast_late_pulse_reversed','fast_late_pulse_shuffled')
WORKERS=4
CONTRASTS=(('slow_sustained_effect',((1,1),(0,-1))),('slow_late_pulse_effect',((2,1),(0,-1))),
    ('fast_sustained_effect',((4,1),(3,-1))),('fast_late_pulse_effect',((5,1),(3,-1))),
    ('fast_minus_slow_sustained_effect',((4,1),(3,-1),(1,-1),(0,1))),
    ('fast_minus_slow_late_pulse_effect',((5,1),(3,-1),(2,-1),(0,1))),
    ('fast_sustained_minus_reversed',((4,1),(6,-1))),('fast_sustained_minus_shuffled',((4,1),(7,-1))),
    ('fast_late_pulse_minus_reversed',((5,1),(8,-1))),('fast_late_pulse_minus_shuffled',((5,1),(9,-1))),
    ('fast_minus_slow_baseline',((3,1),(0,-1))),('fast_sustained_minus_late_pulse',((4,1),(5,-1))))
WRITER_FOCAL=(('theta_delta_rms_whole',1,2,0),('theta_delta_projection_posterior',1,0,1))
QUALIFY_LABELS=tuple(c[0] for c in CONTRASTS[2:10])
SCIENCE=('src/laws_confirmation/l24_speed_qualification.py','scripts/audit_l24_speed_qualification_outputs.py',
    'tests/test_l24_speed_qualification.py','scripts/run_l24_speed_qualification.sh','protocols/L24_SPEED_QUALIFICATION_V1.md')


def checker():
    spec=importlib.util.spec_from_file_location('d091_independent_checker',Path(__file__).resolve().parents[2]/SCIENCE[1])
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def write_records(original,window=temporal.WINDOW):
    ref,theta=np.repeat(original['initial_writer'][:,None],6,axis=1)
    amplitudes=temporal.schedule(window)[:,[0,1,3]];rates=np.repeat(RATES,3)[:,None,None]
    project=source.api()['project_theta'];states=[];trace=[];details=[];weights=[np.zeros(3)]
    for tick in range(window.total+1):
        if tick:
            inputs=original['input_base']+amplitudes[tick-1,:,None,None]*original['input_delta']
            ref=ref+.002*(np.tile(inputs,(2,1,1))-ref)
            raw=(1-rates)*theta+rates*np.tanh(ref)
            centered=raw-raw.mean(axis=(-2,-1),keepdims=True);std=centered.std(axis=(-2,-1))
            details.append(np.stack((raw.mean(axis=(-2,-1)),std,.3/np.maximum(std,1e-9)),axis=-1).reshape(2,3,3))
            theta=project(raw,.3);weights.append(.998*weights[-1]+.002*amplitudes[tick-1])
        fields=np.stack((ref,theta)).reshape(2,2,3,16,16)
        trace.append(np.stack([temporal.observe(fields[:,speed],original['targets'][1]) for speed in (0,1)]))
        if tick in window.times: states.append(fields)
    payload={k:original[k].copy() for k in ('input_base','input_delta','initial_writer','targets','permutation')}
    return payload|dict(schedule=amplitudes,writer_states=np.stack(states),writer_trace=np.stack(trace),
        proposal_details=np.stack(details),R_weights=np.stack(weights))


def build_packets(payload,window=temporal.WINDOW):
    records=[];units=[];forward=[];geometry=[];valid=[];geo=temporal.previous
    for tick in window.boundaries:
        written=payload['writer_states'][window.times.index(tick),1].reshape(6,16,16)
        baseline=written[3];radius=geo.rms(baseline);controls=[];u_rows=[];reconstructed=[]
        if abs(baseline.mean())>1e-12 or abs(radius-.3)>1e-12: raise ValueError('invalid fast baseline norm')
        for arm in (4,5):
            delta=written[arm]-baseline;distance=geo.rms(delta)
            if not 0<distance<2*radius: raise ValueError('degenerate actual increment; no replacement or exclusion')
            u=np.stack([geo.tangent(baseline,h) for h in (delta,delta.ravel()[payload['permutation']].reshape(16,16))])
            c=1-distance**2/(2*radius**2);s=distance*np.sqrt(1-distance**2/(4*radius**2))
            controls.extend((c*baseline-s*u[0],c*baseline+s*u[1]));u_rows.append(u);reconstructed.append(c*baseline+s*u[0])
        packet=np.concatenate((written,controls));rows=[];flags=[]
        direction=(payload['targets'][1]-payload['targets'][0])/2
        for arm,record in enumerate(packet):
            baseline=packet[0 if arm<3 else 3];delta=record-baseline;energy=float(np.sum(delta*delta));flags.append(energy>0)
            rows.append((geo.rms(record),geo.rms(delta),float(record.mean()),float(np.mean(delta*direction)),
                float(np.sum(delta[:,12:]**2)/energy) if energy>0 else 0.,float(np.max(abs(delta)))))
        records.append(packet);units.append(u_rows);forward.append(reconstructed);geometry.append(rows);valid.append(flags)
    return dict(records=np.stack(records).reshape(20,16,16),control_units=np.array(units),
        reconstructed_written=np.array(forward),geometry=np.array(geometry),geometry_energy_available=np.array(valid))


def execute_parent(original,*,index,parent,cfg=source.CONFIG,window=temporal.WINDOW):
    check=checker();old=source.checker();payload=write_records(original,window)
    writer_error=check.check_writer(original,payload,window)
    payload.update(build_packets(payload,window));geometry_error=check.check_packets(original,payload,window)
    descendants=[];values=[];children=[]
    for reader in (0,1):
        raw,meta=source.descendants(tuple(source.encode(r) for r in payload['records']),index=index,parent=parent,reader=reader,cfg=cfg)
        meta['reader']=reader
        meta['replay_max_abs']=old.check_descendants(raw,payload['records'],source.context(index,cfg),parent,reader,meta)
        scores=source.measure(raw,payload['targets']);assert old.check_metrics(raw,payload['targets'],scores)
        descendants.append(raw);values.append(scores);children.append(meta)
    payload.update(descendants=np.stack(descendants),values=np.stack(values));assert check.check_aliases(original,payload)
    return payload,dict(parent=parent,passed=True,writer_max_abs=writer_error,geometry_max_abs=geometry_error,children=children)


def resamples(blocks):
    seed=int.from_bytes(hashlib.sha256((TAG+':block-bootstrap').encode()).digest()[:16],'little')
    return np.random.default_rng(seed).integers(0,blocks,(10000,blocks))


def summarize(blocks,window=temporal.WINDOW):
    values=np.stack([b['values'] for b in blocks]);traces=np.stack([b['writer_trace'] for b in blocks])
    indices=resamples(len(blocks));rows=[];writer_rows=[]
    for boundary,tick in enumerate(window.boundaries):
        for metric in (0,2,4):
            for reader in (0,1):
                for label,terms in CONTRASTS:
                    cases=previous.difference(values[:,:,reader,-1,0,10*boundary:10*boundary+10,:,0,metric],terms,2)
                    rows.append(temporal.pooled_row(cases,indices,boundary=tick,reader=source.READERS[reader],label=label,metric=source.METRICS[metric]))
        for metric,field,region,column in WRITER_FOCAL:
            flat=traces[:,:,tick,:,:,field,region,column].reshape(values.shape[0],values.shape[1],6)
            for label,terms in CONTRASTS[:6]:
                cases=previous.difference(flat,terms,2)[...,None]
                writer_rows.append(temporal.pooled_row(cases,indices,boundary=tick,metric=metric,label=label))
    summary=dict(means=values.mean(axis=(0,1,6)),writer_means=traces.mean(axis=(0,1)))
    for key in ('proposal_details','geometry','R_weights'):
        summary[key+'_means']=np.stack([b[key] for b in blocks]).mean(axis=(0,1))
    return summary,rows,writer_rows


def qualification(rows,window=temporal.WINDOW):
    result=[]
    for boundary in window.boundaries:
        criteria=[]
        for metric in ('damage_fidelity','damage_projection'):
            for label in QUALIFY_LABELS:
                matches=[r for r in rows if (r['boundary'],r['reader'],r['metric'],r['label'])==(boundary,'native_T',metric,label)]
                assert len(matches)==1;row=matches[0]
                criteria.append(dict(metric=metric,label=label,passed=row['positive']==8 and row['pointwise_block_bootstrap_95'][0]>0))
        result.append(dict(boundary=boundary,primary=boundary==window.total,
            stronger_readable_channel_qualified=all(c['passed'] for c in criteria),criteria=criteria))
    return result


def contract():
    return dict(run_id=RUN_ID,decision='D091',law='L24',source_run=temporal.RUN_ID,previous_run=previous.RUN_ID,
        mode='FIXED_SPEED_POSITIVE_CONTROL_BEFORE_PROTECTION',tissues=list(source.TISSUES),disposable=source.DISPOSABLE,
        descendant_config=asdict(source.CONFIG),window=asdict(temporal.WINDOW),writer_times=list(temporal.WINDOW.times),
        boundaries=list(temporal.WINDOW.boundaries),writer_rates=list(RATES),rho=.002,norm=.3,
        fast_rate_factor=10,fast_rate_outside_original_E70_u_range=True,
        histories=list(HISTORIES),speeds=list(SPEEDS),records=list(RECORDS),record_count=20,
        record_flattening='boundary_then_slow3_fast3_fast_wrong4',
        writer_state_axes='parent,checkpoint,field,speed,history,row,column',
        writer_trace_axes='parent,update,speed,history,field,region,metric',trace_metrics=list(temporal.TRACE_METRICS),
        geometry_metrics=list(temporal.previous.GEOMETRY_METRICS),geometry_baseline='each_records_own_speed_baseline',
        contrasts=[[label,[list(t) for t in terms]] for label,terms in CONTRASTS],writer_focal=[list(c) for c in WRITER_FOCAL],
        primary_reader='native_T',primary_writer_boundary=1000,primary_descendant_time=500,
        primary_region='posterior',primary_metric='damage_fidelity',binary_rows=48,continuous_rows=96,writer_rows=24,
        qualification_labels=list(QUALIFY_LABELS),qualification_metrics=['damage_fidelity','damage_projection'],
        qualification_rule='each_of_16_rows_all_8_blocks_positive_and_pointwise_CI_lower_above_zero',
        early_qualification_is_secondary=True,qualification_is_not_law_confirmation=True,automatic_followup=False,
        protection_arms=0,rate_search=False,body_feedback=False,parent_body_physics_simulated=False,
        new_full_parent_lives=0,writer_trajectories_evaluated=192,independent_writer_replays=192,
        source_writer_anchors_in_count=96,new_fast_writer_trajectories=96,writer_steps_per_trajectory=1000,
        descendant_lives_evaluated=20480,independent_descendant_replays=20480,source_off_anchor_lives_in_count=10240,
        source_on_anchor_lives_in_count=3072,new_tissue_blocks=0,new_birth_randomness=False,
        packet_bytes=2048,inherited_fields=['theta'],theta_frozen_in_descendant=True,
        wrong_controls='fast_baseline_norm_and_chord_matched_reversal_shuffle',wrong_control_regional_energy_matched=False,
        degenerate_action='fail_without_substitution_or_exclusion',source_outcomes_known=True,
        new_full_duration_speed_outcomes_frozen_before_view=True,source_seed_tag=source.TAG,
        readers=list(source.READERS),regions=list(source.REGIONS),metrics=list(source.METRICS),
        positive_squared_error_is_worse=True,utility_is_engineer_declared=True,targets_not_supplied_to_writer_or_reader=True,
        bootstrap_seed=TAG+':block-bootstrap',bootstrap_resamples=10000,
        intervals='pointwise_95_whole_block_percentile_not_multiplicity_adjusted',
        renewal_or_biological_claim=False,fitness_or_semantic_selectivity_claim=False,
        writer_atol=1e-12,geometry_atol=1e-12,replay_atol=1e-10,metric_atol=1e-12,
        source_writer_aliases_bit_exact=True,source_child_aliases_bit_exact=True,
        workers=WORKERS,max_cpus=4,reserve_bytes=source.RESERVE,output_allowance_bytes=source.ALLOWANCE,output_hashes=20)


def input_paths(root):
    out=root/'outputs'/previous.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        path=out/name;paths.append(path)
        paths.extend(Path(line.split('  ',1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/previous.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/name for name in (*SCIENCE,'reviews/L24_RECOVERY_REFERENCE_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root,hashes):
    out=root/'outputs'/previous.RUN_ID;run=root/'runs'/previous.RUN_ID
    for name,count in (('input_hashes.sha256',285),('output_hashes.sha256',20)):
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
            blocks.append({k:f[k] for k in ('values','writer_trace','proposal_details')})
    analysis=json.loads((root/'outputs'/previous.RUN_ID/'analysis.json').read_text())
    with np.load(root/'outputs'/previous.RUN_ID/'summary.npz',allow_pickle=False) as f:
        assert previous.checker().check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'],analysis['growth_summary'])
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
    with np.load(root/'tmp'/f'{temporal.RUN_ID}_benchmark'/'panel.npz',allow_pickle=False) as f: original=dict(f)
    payload,record=execute_parent(original,index=source.DISPOSABLE,parent=0)
    source.base.atomic_npz(directory/'panel.npz',payload,root);source.strict_json(directory/'verification.json',record,root)
    with np.load(directory/'panel.npz',allow_pickle=False) as saved:
        for key,value in payload.items(): np.testing.assert_array_equal(saved[key],value)
    seconds=time.monotonic()-tick;assert hashes==frozen_inputs(root)
    forecast=32*seconds+2*hash_seconds+180
    timing=dict(run_id=RUN_ID,passed=True,disposable=source.DISPOSABLE,contract_sha256=canonical_digest(contract()),
        completed_utc=utc_now(),parent_seconds=seconds,hash_seconds=hash_seconds,projected_seconds=forecast,
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
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_speed_qualification','--external-root',str(root),'--run'],
            cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record=dict(run_id=RUN_ID,pid=child.pid,launched_utc=utc_now(),polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'],status=str(run/'STATUS.json'))
    source.strict_json(run/'LAUNCH.json',record,root);atomic_text(run/'RUN.pid',str(child.pid)+'\n',root)
    print(json.dumps(record,indent=2),flush=True);return record


def execute_block(root,index):
    path=root/'outputs'/temporal.RUN_ID/f'block_{index}.npz'
    with np.load(path,allow_pickle=False) as f: original=dict(f)
    metadata=json.loads(path.with_suffix('.json').read_text())
    assert metadata['tissue']==index and metadata['passed'] and len(metadata['parents'])==4
    assert metadata['window']==asdict(temporal.WINDOW)
    pieces=[];parents=[]
    for parent in range(4):
        before={k:v[parent] for k,v in original.items()}
        assert metadata['parents'][parent]['parent']==parent and metadata['parents'][parent]['passed']
        assert temporal.checker().check_packets(before,temporal.WINDOW)<=1e-12
        payload,record=execute_parent(before,index=index,parent=parent)
        pieces.append(payload);parents.append(record)
    block={k:np.stack([p[k] for p in pieces]) for k in pieces[0]};out=root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz',block,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        assert set(saved.files)==set(block)
        for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
    record=dict(tissue=index,passed=True,parents=parents,window=asdict(temporal.WINDOW),writer_rates=list(RATES),descendant_config=asdict(source.CONFIG))
    source.strict_json(out/f'block_{index}.json',record,root)
    assert json.loads((out/f'block_{index}.json').read_text())==json.loads(json.dumps(record))
    return record

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
                    print(f'D091 block {tissue}: writer speed, source aliases, matched controls and child replay pass',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=[]
        for t in source.TISSUES:
            with np.load(out/f'block_{t}.npz',allow_pickle=False) as f:
                blocks.append({k:f[k] for k in ('values','writer_trace','proposal_details','geometry','R_weights')})
        assert check_source_pools(root)
        summary,rows,writer_rows=summarize(blocks);check=checker();assert check.check_summary(blocks,summary,rows,writer_rows,temporal.WINDOW)
        qualified=qualification(rows);assert check.check_qualification(rows,qualified,temporal.WINDOW)
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as f: assert check.check_summary(blocks,dict(f),rows,writer_rows,temporal.WINDOW)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,writer_summary=writer_rows,qualification=qualified,
            blocks=[records[t] for t in source.TISSUES],source_pools_rechecked=True)
        source.strict_json(out/'analysis.json',analysis,root)
        saved_analysis=json.loads((out/'analysis.json').read_text())
        assert check.check_summary(blocks,summary,saved_analysis['summary'],saved_analysis['writer_summary'],temporal.WINDOW)
        assert check.check_qualification(saved_analysis['summary'],saved_analysis['qualification'],temporal.WINDOW)
        for path,digest in manifest['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,writer_trajectories_replayed=192,source_writer_anchors_exact=True,R_unchanged_across_speeds=True,
            daughter_lives_independently_replayed=20480,source_off_anchors_exact=True,source_on_anchors_exact=True,source_pools_rechecked=True,
            independent_pool=True,input_hashes=len(manifest['input_sha256']),
            writer_max_abs=max(p['writer_max_abs'] for r in records.values() for p in r['parents']),
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
    for op in ('freeze','benchmark','prepare','detach','run','audit-saved'): group.add_argument('--'+op,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    if args.audit_saved: audit_saved(root);return 0
    for op in ('freeze','benchmark','prepare','detach','run'):
        if getattr(args,op):
            result=(run_experiment if op=='run' else globals()[op])(root)
            return result if isinstance(result,int) else 0


def audit_saved(root):
    """Read-only saved-state/hash/pool audit; no writer or child recurrence."""
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
    check=checker();blocks=[];observer_error=0.
    for tissue in source.TISSUES:
        with np.load(root/'outputs'/temporal.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: before=dict(f)
        with np.load(out/f'block_{tissue}.npz',allow_pickle=False) as f: block=dict(f)
        for parent in range(4):
            original={k:v[parent] for k,v in before.items()};payload={k:v[parent] for k,v in block.items()}
            assert check.check_packets(original,payload,temporal.WINDOW)<=1e-12
            assert check.check_aliases(original,payload)
            for position,t in enumerate(temporal.WINDOW.times):
                observer_error=max(observer_error,check.close(check.observer(payload['writer_states'][position],payload['targets'][1]),payload['writer_trace'][t]))
            for reader in (0,1):
                assert source.checker().check_metrics(payload['descendants'][reader],payload['targets'],payload['values'][reader])
        blocks.append({k:block[k] for k in ('values','writer_trace','proposal_details','geometry','R_weights')})
    assert check_source_pools(root)
    analysis=json.loads((out/'analysis.json').read_text())
    for key,value in contract().items(): assert canonical_digest(analysis[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and analysis['source_pools_rechecked']
    assert json.loads((out/'verification.json').read_text())['passes']
    with np.load(out/'summary.npz',allow_pickle=False) as f:
        assert check.check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'],temporal.WINDOW)
    assert check.check_qualification(analysis['summary'],analysis['qualification'],temporal.WINDOW)
    assert source.checker().check_hashes(out/'input_hashes.sha256')==len(expected)
    assert source.checker().check_hashes(out/'output_hashes.sha256')==20
    result=dict(passed=True,read_only=True,input_hashes=len(expected),output_hashes=20,writer_observer_batches=320,
        child_snapshot_metric_batches=320,observer_max_abs=observer_error,source_pools_rechecked=True,
        rows_checked=[144,24],qualification_criteria_checked=32,dynamics_or_writer_recurrences_replayed=0,elapsed_seconds=time.monotonic()-tick)
    print(json.dumps(result,indent=2),flush=True);return result

if __name__=='__main__': raise SystemExit(main())
