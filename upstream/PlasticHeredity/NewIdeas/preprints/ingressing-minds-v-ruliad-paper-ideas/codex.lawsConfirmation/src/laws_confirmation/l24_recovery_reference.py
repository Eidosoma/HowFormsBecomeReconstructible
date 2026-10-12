"""D090: intervene on recovery-onset R, preserving the already-written record."""
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
from . import l24_temporal_filter as previous
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_recovery_reference_v1_attempt1'
TAG='l24-recovery-reference-v1'
WORKERS=4
HISTORIES=('sustained','late_pulse')
MODES=('intact','R_baseline','theta_baseline','R_reversed','R_restored')
ARMS=('baseline',*(f'{h}_{m}' for h in HISTORIES for m in MODES))
# Linear endpoint contrasts. The interaction is F11-F01-F10+F00, not a
# claim that the writer or nonlinear descendant readout is additive.
CONTRASTS=tuple((h+'_'+name,tuple(terms)) for h,start in zip(HISTORIES,(1,6)) for name,terms in (
    ('intact_minus_baseline',((start,1),(0,-1))),
    ('R_baseline_minus_baseline',((start+1,1),(0,-1))),
    ('theta_baseline_minus_baseline',((start+2,1),(0,-1))),
    ('intact_minus_R_baseline',((start,1),(start+1,-1))),
    ('intact_minus_theta_baseline',((start,1),(start+2,-1))),
    ('interaction',((start,1),(start+1,-1),(start+2,-1),(0,1))),
    ('intact_minus_R_reversed',((start,1),(start+3,-1))),
    ('restored_minus_intact',((start+4,1),(start,-1)))))
WRITER_FOCAL=(('theta_delta_rms_whole',1,2,0),('theta_delta_projection_posterior',1,0,1),('R_delta_rms_whole',0,2,0))
SCIENCE=('src/laws_confirmation/l24_recovery_reference.py','scripts/audit_l24_recovery_reference_outputs.py',
    'tests/test_l24_recovery_reference.py','scripts/run_l24_recovery_reference.sh','protocols/L24_RECOVERY_REFERENCE_V1.md')


def checker():
    spec=importlib.util.spec_from_file_location('d090_independent_checker',Path(__file__).resolve().parents[2]/SCIENCE[1])
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def recovery_times(window=previous.WINDOW):
    return tuple(t-window.active for t in window.times if t>=window.active)


def intervention(onset):
    """onset axes: field (R,theta), source history (baseline,sustained,late)."""
    initial=np.repeat(onset[:,0:1],11,axis=1);intermediate=[]
    for history,start in ((1,1),(2,6)):
        initial[:,start:start+5]=onset[:,history:history+1]
        initial[0,start+1]=onset[0,0]
        initial[1,start+2]=onset[1,0]
        initial[0,start+3]=2*onset[0,0]-onset[0,history]
        initial[0,start+4]=onset[0,0]
        intermediate.append(initial[0,start+4].copy())
        initial[0,start+4]=onset[0,history]
    return initial,np.stack(intermediate)


def recover(original,window=previous.WINDOW):
    onset=original['writer_states'][window.times.index(window.active)][:,[0,1,3]].copy()
    initial,intermediate=intervention(onset)
    ref,theta=initial.copy();snapshots=[];traces=[];details=[]
    project=source.api()['project_theta']
    for tick in range(window.recovery+1):
        if tick:
            ref,theta,detail=previous.advance(ref,theta,original['input_base'],project);details.append(detail)
        fields=np.stack((ref,theta));traces.append(previous.observe(fields,original['targets'][1]))
        if tick in recovery_times(window): snapshots.append(fields)
    return dict(input_base=original['input_base'].copy(),onset=onset,initial_writer=initial,
        restore_intermediate_R=intermediate,writer_states=np.stack(snapshots),writer_trace=np.stack(traces),
        proposal_details=np.stack(details),targets=original['targets'].copy(),records=theta.copy())


def execute_parent(original,*,index,parent,cfg=source.CONFIG,window=previous.WINDOW):
    check=checker();old=source.checker();payload=recover(original,window)
    writer_error=check.check_writer(original,payload,window)
    assert check.check_packets(original,payload)
    descendants=[];values=[];children=[]
    for reader in (0,1):
        raw,meta=source.descendants(tuple(source.encode(r) for r in payload['records']),index=index,parent=parent,reader=reader,cfg=cfg)
        meta['reader']=reader
        meta['replay_max_abs']=old.check_descendants(raw,payload['records'],source.context(index,cfg),parent,reader,meta)
        scores=source.measure(raw,payload['targets']);assert old.check_metrics(raw,payload['targets'],scores)
        descendants.append(raw);values.append(scores);children.append(meta)
    payload.update(descendants=np.stack(descendants),values=np.stack(values))
    assert check.check_aliases(original,payload)
    return payload,dict(parent=parent,passed=True,writer_max_abs=writer_error,children=children)


def resamples(blocks):
    seed=int.from_bytes(hashlib.sha256((TAG+':block-bootstrap').encode()).digest()[:16],'little')
    return np.random.default_rng(seed).integers(0,blocks,(10000,blocks))


def difference(values,terms,axis):
    return sum(weight*np.take(values,arm,axis=axis) for arm,weight in terms)


def summarize(blocks):
    values=np.stack([b['values'] for b in blocks]);traces=np.stack([b['writer_trace'] for b in blocks])
    indices=resamples(len(blocks));rows=[];writer_rows=[];growth=[]
    for metric in (0,2,4):
        for reader in (0,1):
            for label,terms in CONTRASTS:
                cases=difference(values[:,:,reader,-1,0,:,:,0,metric],terms,2)
                rows.append(previous.pooled_row(cases,indices,reader=source.READERS[reader],label=label,metric=source.METRICS[metric]))
    for metric,field,region,column in WRITER_FOCAL:
        for label,terms in CONTRASTS:
            cases=difference(traces[:,:,-1,:,field,region,column],terms,2)[...,None]
            writer_rows.append(previous.pooled_row(cases,indices,metric=metric,label=label))
    for history,start in zip(HISTORIES,(1,6)):
        for offset in range(4):
            arm=start+offset
            cases=(traces[:,:,-1,arm,1,2,0]-traces[:,:,0,arm,1,2,0])[...,None]
            growth.append(previous.pooled_row(cases,indices,arm=ARMS[arm],metric='theta_delta_rms_whole_end_minus_start'))
    summary=dict(means=values.mean(axis=(0,1,6)),writer_means=traces.mean(axis=(0,1)),
        proposal_details_means=np.stack([b['proposal_details'] for b in blocks]).mean(axis=(0,1)))
    return summary,rows,writer_rows,growth


def contract():
    return dict(run_id=RUN_ID,decision='D090',law='L24',source_run=previous.RUN_ID,
        mode='RECOVERY_ONSET_REFERENCE_REPLACEMENT',tissues=list(source.TISSUES),disposable=source.DISPOSABLE,
        descendant_config=asdict(source.CONFIG),source_window=asdict(previous.WINDOW),
        recovery_times=list(recovery_times()),absolute_writer_times=[previous.WINDOW.active+t for t in recovery_times()],
        rho=.002,writer_rate=.0005,norm=.3,arms=list(ARMS),record_count=11,
        contrasts=[[label,[list(term) for term in terms]] for label,terms in CONTRASTS],
        writer_focal=[list(c) for c in WRITER_FOCAL],trace_metrics=list(previous.TRACE_METRICS),
        writer_trace_axes='parent,recovery_time,arm,field,region,metric',
        writer_state_axes='parent,checkpoint,field,arm,row,column',
        intervention_once_before_first_recovery_update=True,replacement='matched_baseline_R_not_zero',
        reverse_definition='2*baseline_R-exposed_R',reverse_R_norm_matched=False,
        rescue_is_exact_immediate_restore_alias=True,rescue_is_independent_evidence=False,
        primary_reader='native_T',primary_writer_boundary=1000,primary_descendant_time=500,
        primary_region='posterior',primary_metric='damage_fidelity',
        focal_causal_contrasts=['sustained_intact_minus_R_baseline','late_pulse_intact_minus_R_baseline'],
        binary_rows=32,continuous_rows=64,writer_rows=48,growth_rows=8,
        readers=list(source.READERS),regions=list(source.REGIONS),metrics=list(source.METRICS),
        positive_squared_error_is_worse=True,interaction_is_endpoint_dependent=True,
        body_feedback=False,parent_body_physics_simulated=False,new_full_parent_lives=0,
        new_exposure_histories=0,writer_recovery_trajectories_evaluated=352,independent_writer_replays=352,
        unique_writer_trajectories=288,source_unchanged_trajectories_in_count=96,rescue_aliases_in_count=64,
        new_intervention_trajectories=192,writer_steps_per_trajectory=500,
        descendant_lives_evaluated=11264,independent_descendant_replays=11264,
        source_off_anchor_lives_in_count=5632,source_on_anchor_or_rescue_lives_in_count=2560,
        new_tissue_blocks=0,new_birth_randomness=False,packet_bytes=2048,inherited_fields=['theta'],
        theta_frozen_in_descendant=True,targets_not_supplied_to_writer_or_reader=True,
        source_outcomes_known=True,new_recovery_intervention_outcomes_frozen_before_view=True,
        source_seed_tag=source.TAG,bootstrap_seed=TAG+':block-bootstrap',bootstrap_resamples=10000,
        intervals='pointwise_95_whole_block_percentile_not_multiplicity_adjusted',
        scientific_pass_gate=None,automatic_followup=False,renewal_or_biological_claim=False,
        fitness_or_semantic_selectivity_claim=False,writer_atol=1e-12,replay_atol=1e-10,metric_atol=1e-12,
        source_writer_aliases_bit_exact=True,source_child_aliases_bit_exact=True,
        workers=WORKERS,max_cpus=4,reserve_bytes=source.RESERVE,output_allowance_bytes=source.ALLOWANCE,output_hashes=20)


def input_paths(root):
    out=root/'outputs'/previous.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        path=out/name;paths.append(path)
        paths.extend(Path(line.split('  ',1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/previous.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/name for name in (*SCIENCE,'reviews/L24_TEMPORAL_FILTER_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root,hashes):
    out=root/'outputs'/previous.RUN_ID;run=root/'runs'/previous.RUN_ID
    for name,count in (('input_hashes.sha256',251),('output_hashes.sha256',20)):
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
        assert previous.checker().check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'])
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
        child=subprocess.Popen([sys.executable,'-m','laws_confirmation.l24_recovery_reference','--external-root',str(root),'--run'],
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
    assert metadata['window']==asdict(previous.WINDOW)
    pieces=[];parents=[]
    for parent in range(4):
        before={k:v[parent] for k,v in original.items()}
        assert metadata['parents'][parent]['parent']==parent and metadata['parents'][parent]['passed']
        assert previous.checker().check_packets(before,previous.WINDOW)<=1e-12
        assert not before['schedule'][previous.WINDOW.active:].any()
        payload,record=execute_parent(before,index=index,parent=parent)
        pieces.append(payload);parents.append(record)
    block={k:np.stack([p[k] for p in pieces]) for k in pieces[0]};out=root/'outputs'/RUN_ID
    source.base.atomic_npz(out/f'block_{index}.npz',block,root)
    with np.load(out/f'block_{index}.npz',allow_pickle=False) as saved:
        assert set(saved.files)==set(block)
        for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
    record=dict(tissue=index,passed=True,parents=parents,recovery_times=list(recovery_times()),descendant_config=asdict(source.CONFIG))
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
                    print(f'D090 block {tissue}: intervention, recovery replay, source aliases and descendant replay pass',flush=True)
            except Exception:
                for future in pending: future.cancel()
                raise
        blocks=[]
        for t in source.TISSUES:
            with np.load(out/f'block_{t}.npz',allow_pickle=False) as f:
                blocks.append({k:f[k] for k in ('values','writer_trace','proposal_details')})
        assert check_source_pools(root)
        summary,rows,writer_rows,growth=summarize(blocks);check=checker();assert check.check_summary(blocks,summary,rows,writer_rows,growth)
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as f: assert check.check_summary(blocks,dict(f),rows,writer_rows,growth)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,writer_summary=writer_rows,growth_summary=growth,
            blocks=[records[t] for t in source.TISSUES],source_pools_rechecked=True)
        source.strict_json(out/'analysis.json',analysis,root)
        saved_analysis=json.loads((out/'analysis.json').read_text())
        assert check.check_summary(blocks,summary,saved_analysis['summary'],saved_analysis['writer_summary'],saved_analysis['growth_summary'])
        for path,digest in manifest['input_sha256'].items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,writer_trajectories_replayed=352,source_writer_anchors_exact=True,restoration_aliases_exact=True,
            daughter_lives_independently_replayed=11264,source_off_anchors_exact=True,source_on_anchors_exact=True,source_pools_rechecked=True,
            independent_pool=True,input_hashes=len(manifest['input_sha256']),
            writer_max_abs=max(p['writer_max_abs'] for r in records.values() for p in r['parents']),
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
    """Read-only saved-state/hash/pool audit; no physical or writer recurrence."""
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
        with np.load(root/'outputs'/previous.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: before=dict(f)
        with np.load(out/f'block_{tissue}.npz',allow_pickle=False) as f: block=dict(f)
        for parent in range(4):
            original={k:v[parent] for k,v in before.items()};payload={k:v[parent] for k,v in block.items()}
            assert check.check_packets(original,payload) and check.check_aliases(original,payload)
            for position,t in enumerate(recovery_times()):
                observer_error=max(observer_error,check.close(check.observer(payload['writer_states'][position],payload['targets'][1]),payload['writer_trace'][t]))
            for reader in (0,1):
                assert source.checker().check_metrics(payload['descendants'][reader],payload['targets'],payload['values'][reader])
        blocks.append({k:block[k] for k in ('values','writer_trace','proposal_details')})
    assert check_source_pools(root)
    analysis=json.loads((out/'analysis.json').read_text())
    for key,value in contract().items(): assert canonical_digest(analysis[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and analysis['source_pools_rechecked']
    assert json.loads((out/'verification.json').read_text())['passes']
    with np.load(out/'summary.npz',allow_pickle=False) as f:
        assert check.check_summary(blocks,dict(f),analysis['summary'],analysis['writer_summary'],analysis['growth_summary'])
    assert source.checker().check_hashes(out/'input_hashes.sha256')==len(expected)
    assert source.checker().check_hashes(out/'output_hashes.sha256')==20
    result=dict(passed=True,read_only=True,input_hashes=len(expected),output_hashes=20,writer_observer_batches=160,
        child_snapshot_metric_batches=320,observer_max_abs=observer_error,source_pools_rechecked=True,
        rows_checked=[96,48,8],dynamics_or_writer_recurrences_replayed=0,elapsed_seconds=time.monotonic()-tick)
    print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__': raise SystemExit(main())
