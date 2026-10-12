"""D089: fixed-rate, input-clamped temporal filtering and fresh theta readout."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
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
from . import l24_matched_readout as previous
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_temporal_filter_v1_attempt1'
TAG='l24-temporal-filter-v1'
RHO,RATE,NORM,WORKERS=.002,.0005,.3,4
EXPOSURES=('baseline','sustained','early_pulse','late_pulse','dose_matched_sustained')
RECORDS=(*EXPOSURES,'sustained_reversed','sustained_shuffled','late_pulse_reversed','late_pulse_shuffled','initial_record')
CONTRASTS=(('sustained_minus_baseline',1,0),('late_pulse_minus_baseline',3,0),('early_pulse_minus_baseline',2,0),
    ('sustained_minus_late_pulse',1,3),('late_minus_early_pulse',3,2),('dose_matched_minus_late_pulse',4,3),
    ('sustained_minus_reversed',1,5),('sustained_minus_shuffled',1,6),('late_pulse_minus_reversed',3,7),('late_pulse_minus_shuffled',3,8))
TRACE_METRICS=('delta_rms','delta_target_projection','delta_mean','sign_disagreement','field_rms','field_mean')
WRITER_FOCAL=(('theta_delta_rms_whole',1,2,0),('theta_delta_projection_posterior',1,0,1),('R_delta_rms_whole',0,2,0))
SCIENCE=('src/laws_confirmation/l24_temporal_filter.py','scripts/audit_l24_temporal_filter_outputs.py',
    'tests/test_l24_temporal_filter.py','scripts/run_l24_temporal_filter.sh','protocols/L24_TEMPORAL_FILTER_V1.md')


@dataclass(frozen=True)
class Window:
    active: int=500
    pulse: int=50
    recovery: int=500

    def __post_init__(self):
        if not (self.active>=4 and 0<self.pulse<self.active//2 and self.recovery>self.pulse):
            raise ValueError('distinct exposure and recovery clocks required')

    @property
    def total(self): return self.active+self.recovery

    @property
    def times(self):
        return tuple(sorted({0,1,self.pulse,self.active//2,self.active-self.pulse,self.active,
            self.active+1,self.active+self.pulse,self.active+self.recovery//2,self.total}))

    @property
    def boundaries(self): return (self.active,self.total)


WINDOW=Window()


def checker():
    spec=importlib.util.spec_from_file_location('d089_independent_checker',Path(__file__).resolve().parents[2]/SCIENCE[1])
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def schedule(window=WINDOW):
    amplitudes=np.zeros((window.total,5))
    amplitudes[:window.active,1]=1
    amplitudes[:window.pulse,2]=1
    amplitudes[window.active-window.pulse:window.active,3]=1
    amplitudes[:window.active,4]=window.pulse/window.active
    return amplitudes


def advance(ref,theta,body_input,project):
    ref=ref+RHO*(body_input-ref)
    proposal=(1-RATE)*theta+RATE*np.tanh(ref)
    centered=proposal-proposal.mean(axis=(-2,-1),keepdims=True)
    std=centered.std(axis=(-2,-1))
    details=np.stack((proposal.mean(axis=(-2,-1)),std,NORM/np.maximum(std,1e-9)),axis=-1)
    return ref,project(proposal,NORM),details


def observe(fields,target):
    delta=fields-fields[:,0:1]
    zone=np.indices((16,16))[1]>=12;pieces=[]
    for mask in (zone,~zone,np.ones((16,16),bool)):
        x,d=fields[...,mask],delta[...,mask]
        pieces.append(np.stack((np.sqrt(np.mean(d*d,axis=-1)),(d*target[mask]).mean(axis=-1),
            d.mean(axis=-1),((x>0)!=(x[:,0:1]>0)).mean(axis=-1),
            np.sqrt(np.mean(x*x,axis=-1)),x.mean(axis=-1)),axis=-1))
    return np.stack(pieces,axis=-2).swapaxes(0,1)


def write_records(original,window=WINDOW):
    old=original['parent_states'];base=old[0,3,0].copy();delta=old[1,4,0]-base
    initial=old[0,3,2:4].copy();ref,theta=np.repeat(initial[:,None],5,axis=1)
    amplitudes=schedule(window);project=source.api()['project_theta']
    snapshots=[];traces=[];proposals=[];weights=[np.zeros(5)]
    for tick in range(window.total+1):
        if tick:
            ref,theta,detail=advance(ref,theta,base+amplitudes[tick-1,:,None,None]*delta,project)
            proposals.append(detail);weights.append((1-RHO)*weights[-1]+RHO*amplitudes[tick-1])
        fields=np.stack((ref,theta));traces.append(observe(fields,original['targets'][1]))
        if tick in window.times: snapshots.append(fields)
    return dict(input_base=base,input_delta=delta,initial_writer=initial,schedule=amplitudes,
        writer_states=np.stack(snapshots),writer_trace=np.stack(traces),proposal_details=np.stack(proposals),
        R_weights=np.stack(weights),targets=original['targets'].copy(),permutation=original['permutation'].copy())


def build_packets(payload,window=WINDOW):
    all_records=[];all_units=[];reconstructions=[];geometry=[];valid=[]
    for boundary in window.boundaries:
        written=payload['writer_states'][window.times.index(boundary),1]
        baseline=written[0];r=previous.rms(baseline);controls=[];units=[];forward=[]
        if abs(baseline.mean())>1e-12 or abs(r-NORM)>1e-12: raise ValueError('invalid writer baseline norm')
        for arm in (1,3):
            delta=written[arm]-baseline;distance=previous.rms(delta)
            if not 0<distance<2*r: raise ValueError('degenerate written change; no replacement or excluded case')
            raw=(delta,delta.ravel()[payload['permutation']].reshape(16,16))
            u=np.stack([previous.tangent(baseline,h) for h in raw]);units.append(u)
            c=1-distance**2/(2*r*r);s=distance*np.sqrt(1-distance**2/(4*r*r))
            controls.extend((c*baseline-s*u[0],c*baseline+s*u[1]));forward.append(c*baseline+s*u[0])
        records=np.concatenate((written,np.stack(controls),payload['initial_writer'][1:2]))
        rows=[];flags=[];direction=(payload['targets'][1]-payload['targets'][0])/2
        for record in records:
            change=record-baseline;energy=float(np.sum(change*change));flags.append(energy>0)
            rows.append((previous.rms(record),previous.rms(change),float(record.mean()),float(np.mean(change*direction)),
                float(np.sum(change[:,12:]**2)/energy) if energy>0 else 0.,float(np.max(abs(change)))))
        all_records.append(records);all_units.append(units);reconstructions.append(forward);geometry.append(rows);valid.append(flags)
    return dict(records=np.stack(all_records).reshape(20,16,16),control_units=np.array(all_units),
        reconstructed_written=np.array(reconstructions),geometry=np.array(geometry),geometry_energy_available=np.array(valid))


def execute_parent(original,*,index,parent,cfg=source.CONFIG,window=WINDOW):
    check=checker();old=source.checker();payload=write_records(original,window)
    writer_error=check.check_writer(original,payload,window)
    payload.update(build_packets(payload,window));geometry_error=check.check_packets(payload,window)
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


def pooled_row(cases,indices,**labels):
    means=cases.mean(axis=(1,2))
    row=labels|dict(mean=float(means.mean()),minimum=float(means.min()),maximum=float(means.max()),
        block_means=means.tolist(),parent_means=cases.mean(axis=-1).tolist(),
        pointwise_block_bootstrap_95=np.quantile(means[indices].mean(axis=1),(.025,.975)).tolist())
    for prefix,x in (('',means),('paired_',cases)):
        for name,test in (('positive',x>1e-12),('tied',abs(x)<=1e-12),('negative',x< -1e-12)):
            row[prefix+name]=int(test.sum())
    return row


def summarize(blocks):
    values=np.stack([b['values'] for b in blocks]);indices=resamples(len(blocks));rows=[];writer_rows=[]
    for metric in (0,2,4):
        for reader in (0,1):
            for name,positive,negative in CONTRASTS:
                cases=values[:,:,reader,-1,0,10+positive,:,0,metric]-values[:,:,reader,-1,0,10+negative,:,0,metric]
                rows.append(pooled_row(cases,indices,reader=source.READERS[reader],label=name,metric=source.METRICS[metric]))
    traces=np.stack([b['writer_trace'] for b in blocks])
    for label,field,region,metric in WRITER_FOCAL:
        for arm in range(1,5):
            cases=traces[:,:,-1,arm,field,region,metric,None]
            writer_rows.append(pooled_row(cases,indices,label=label,exposure=EXPOSURES[arm]))
    summary=dict(means=values.mean(axis=(0,1,6)),writer_means=traces.mean(axis=(0,1)))
    for key in ('proposal_details','geometry','R_weights'):
        summary[key+'_means']=np.stack([b[key] for b in blocks]).mean(axis=(0,1))
    return summary,rows,writer_rows


def contract():
    return dict(run_id=RUN_ID,decision='D089',law='L24',source_run=source.RUN_ID,previous_run=previous.RUN_ID,
        mode='FIXED_RATE_INPUT_CLAMP_TEMPORAL_FILTER',tissues=list(source.TISSUES),disposable=source.DISPOSABLE,
        descendant_config=asdict(source.CONFIG),window=asdict(WINDOW),writer_saved_times=list(WINDOW.times),
        writer_boundaries=list(WINDOW.boundaries),rho=RHO,writer_rate=RATE,norm=NORM,exposures=list(EXPOSURES),
        records=list(RECORDS),record_flattening='boundary_then_record',record_count=20,
        trace_metrics=list(TRACE_METRICS),geometry_metrics=list(previous.GEOMETRY_METRICS),
        trace_fields=['R','theta'],writer_trace_axes='parent,update,exposure,field,region,metric',
        writer_state_axes='parent,checkpoint,field,exposure,row,column',
        proposal_axes='parent,update,exposure,proposal_mean_centered_std_scale',
        readers=list(source.READERS),regions=list(source.REGIONS),metrics=list(source.METRICS),
        contrasts=[list(c) for c in CONTRASTS],writer_focal=[list(c) for c in WRITER_FOCAL],
        primary_reader='native_T',primary_writer_boundary=1000,primary_descendant_time=500,
        primary_region='posterior',primary_metric='damage_fidelity',binary_rows=20,continuous_rows=40,writer_rows=12,
        positive_squared_error_is_worse=True,body_feedback=False,parent_body_physics_simulated=False,
        input_definition='saved_preinjury_V_plus_amplitude_times_saved_postinjury_minus_preinjury_V',
        initial_writer='saved_preinjury_R_theta',peak_amplitude_matched_arms=[1,2,3],
        signed_integrated_input_matched_arms=[2,3,4],squared_integrated_input_matched_for_dose_control=False,
        no_utility_label_to_writer=True,utility_is_engineer_declared=True,fitness_or_semantic_selectivity_claim=False,
        new_full_parent_lives=0,new_counterfactual_writer_trajectories=160,independent_writer_replays=160,
        writer_steps_per_trajectory=1000,descendant_lives_evaluated=20480,independent_descendant_replays=20480,
        source_off_anchor_lives_in_count=10240,new_tissue_blocks=0,new_birth_randomness=False,
        packet_bytes=2048,inherited_fields=['theta'],theta_frozen_in_descendant=True,
        initial_record_control_is_writer_disabled=True,wrong_controls='norm_and_chord_matched_reversal_shuffle_of_sustained_and_late',
        wrong_control_regional_energy_histogram_matched=False,degenerate_action='fail_without_substitution_or_exclusion',
        source_outcomes_known=True,new_temporal_outcomes_frozen_before_view=True,source_seed_tag=source.TAG,
        bootstrap_seed=TAG+':block-bootstrap',bootstrap_resamples=10000,
        intervals='pointwise_95_whole_block_percentile_not_multiplicity_adjusted',
        scientific_pass_gate=None,automatic_followup=False,renewal_or_biological_claim=False,
        writer_atol=1e-12,geometry_atol=1e-12,replay_atol=1e-10,metric_atol=1e-12,
        workers=WORKERS,max_cpus=4,reserve_bytes=source.RESERVE,output_allowance_bytes=source.ALLOWANCE,output_hashes=20)


def input_paths(root):
    out=root/'outputs'/previous.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        path=out/name;paths.append(path)
        paths.extend(Path(line.split('  ',1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/previous.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/name for name in (*SCIENCE,'reviews/L24_MATCHED_READOUT_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root,hashes):
    out=root/'outputs'/previous.RUN_ID;run=root/'runs'/previous.RUN_ID
    for name,count in (('input_hashes.sha256',217),('output_hashes.sha256',20)):
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
    old_blocks=[];newer_blocks=[]
    for tissue in source.TISSUES:
        with np.load(root/'outputs'/source.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: old_blocks.append(f['values'])
        with np.load(root/'outputs'/previous.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: newer_blocks.append(f['values'])
    old=json.loads((root/'outputs'/source.RUN_ID/'analysis.json').read_text())
    newer=json.loads((root/'outputs'/previous.RUN_ID/'analysis.json').read_text())
    with np.load(root/'outputs'/source.RUN_ID/'summary.npz',allow_pickle=False) as f:
        assert source.checker().check_summary(old_blocks,dict(f),old['focal'])
    with np.load(root/'outputs'/previous.RUN_ID/'summary.npz',allow_pickle=False) as f:
        assert previous.checker().check_summary(newer_blocks,dict(f),newer['summary'],old['focal'])
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
    with np.load(root/'tmp'/f'{source.RUN_ID}_benchmark'/'panel.npz',allow_pickle=False) as f: original=dict(f)
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
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_temporal_filter','--external-root',str(root),'--run'],
            cwd=Path(__file__).resolve().parents[2],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
    record=dict(run_id=RUN_ID,pid=child.pid,launched_utc=utc_now(),polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'],status=str(run/'STATUS.json'))
    source.strict_json(run/'LAUNCH.json',record,root);atomic_text(run/'RUN.pid',str(child.pid)+'\n',root)
    print(json.dumps(record,indent=2),flush=True);return record


def execute_block(root,index):
    path=root/'outputs'/source.RUN_ID/f'block_{index}.npz'
    with np.load(path,allow_pickle=False) as f: original=dict(f)
    metadata=json.loads(path.with_suffix('.json').read_text())
    assert previous.trace.checker().source_block_check(original,metadata,index)
    pieces=[];parents=[]
    for parent in range(4):
        payload,record=execute_parent({k:v[parent] for k,v in original.items()},index=index,parent=parent)
        pieces.append(payload);parents.append(record)
    block={k:np.stack([p[k] for p in pieces]) for k in pieces[0]};out=root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz',block,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
    record=dict(tissue=index,passed=True,parents=parents,window=asdict(WINDOW),descendant_config=asdict(source.CONFIG))
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
                    print(f'D089 block {tissue}: schedule, writer replay, packet controls and descendant replay pass',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=[]
        for t in source.TISSUES:
            with np.load(out/f'block_{t}.npz',allow_pickle=False) as f:
                blocks.append({k:f[k] for k in ('values','writer_trace','proposal_details','geometry','R_weights')})
        assert check_source_pools(root)
        summary,rows,writer_rows=summarize(blocks);check=checker();assert check.check_summary(blocks,summary,rows,writer_rows)
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as f: assert check.check_summary(blocks,dict(f),rows,writer_rows)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,writer_summary=writer_rows,
            blocks=[records[t] for t in source.TISSUES],source_pools_rechecked=True)
        source.strict_json(out/'analysis.json',analysis,root)
        saved_analysis=json.loads((out/'analysis.json').read_text())
        assert check.check_summary(blocks,summary,saved_analysis['summary'],saved_analysis['writer_summary'])
        for path,digest in manifest['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,writer_trajectories_replayed=160,source_one_step_bridges=64,
            daughter_lives_independently_replayed=20480,source_off_anchors_exact=True,source_pools_rechecked=True,
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
    for op in ('freeze','benchmark','prepare','detach','run'): group.add_argument('--'+op,action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    for op in ('freeze','benchmark','prepare','detach','run'):
        if getattr(args,op):
            result=(run_experiment if op=='run' else globals()[op])(root)
            return result if isinstance(result,int) else 0


if __name__=='__main__': raise SystemExit(main())
