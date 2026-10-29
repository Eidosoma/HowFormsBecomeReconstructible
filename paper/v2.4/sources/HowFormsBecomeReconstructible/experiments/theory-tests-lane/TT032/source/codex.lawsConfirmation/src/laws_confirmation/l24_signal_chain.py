"""D087: outcome-known algebra/observer audit of the saved D086 signal chain.

No historical or new simulator futures, trajectory interpolation, rate change,
or hypothetical offspring are evaluated here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import traceback

import numpy as np

from . import l24_descendant_pilot as source
from .io import atomic_text, canonical_digest, environment_manifest, external_root, sha256_file, utc_now, write_hash_manifest

RUN_ID='l24_signal_chain_audit_v1_attempt1'
TAG='l24-signal-chain-audit-v1'
SCIENCE=('src/laws_confirmation/l24_signal_chain.py','scripts/audit_l24_signal_chain_outputs.py',
         'tests/test_l24_signal_chain.py','scripts/run_l24_signal_chain.sh','protocols/L24_SIGNAL_CHAIN_AUDIT_V1.md')
FIELDS=(*source.FIELDS,'tanh_R')
TRACE_METRICS=('delta_rms','delta_max_abs','delta_mean','injury_projection','sign_disagreement',
               'clean_rms','damaged_rms','clean_clip_fraction','damaged_clip_fraction')
TERMS=('delta_V_postzap','delta_V_one_update','delta_R_one_update','delta_tanh_R_one_update',
       'delta_raw_theta_one_update','delta_centered_theta_one_update','projection_shape_term',
       'projection_gain_term','delta_projected_theta_one_update','weighted_body_drive_50','delta_theta_final')
LABELS=('body_immediately_after_injury','body_after_one_update','reference_after_one_update',
        'raw_record_after_one_update','projected_record_after_one_update','body_after_50_updates',
        'reference_after_50_updates','record_after_50_updates','final_record_delta_relative_to_point3',
        'actual_to_known_record_delta_ratio','first_step_tanh_rms_ratio','first_step_centering_rms_ratio',
        'first_step_normalization_rms_ratio','weighted_body_drive_relative_to_initial_injury')
RHO,LAMBDA,NORM,WINDOW=.002,.0005,.3,50
ALLOWANCE,RESERVE=64*1024**2,4*1024**3


def checker():
    path=Path(__file__).resolve().parents[2]/SCIENCE[1]
    spec=importlib.util.spec_from_file_location('d087_independent_checker',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def rms(x): return float(np.sqrt(np.mean(np.square(x))))


def delta_trace(states, targets):
    fields=np.concatenate((states,np.tanh(states[:,:,2:3])),axis=2)
    clean,damaged=fields;delta=damaged-clean
    direction=(targets[1]-targets[0])/2
    zone=np.indices((16,16))[1]>=12;regions=[]
    for mask in (zone,~zone,np.ones((16,16),bool)):
        c,d,x=clean[...,mask],damaged[...,mask],delta[...,mask]
        regions.append(np.stack((np.sqrt(np.mean(x*x,axis=-1)),np.max(abs(x),axis=-1),
            x.mean(axis=-1),(x*direction[mask]).mean(axis=-1),((c>0)!=(d>0)).mean(axis=-1),
            np.sqrt(np.mean(c*c,axis=-1)),np.sqrt(np.mean(d*d,axis=-1)),
            (abs(c)==2).mean(axis=-1),(abs(d)==2).mean(axis=-1)),axis=-1))
    return np.stack(regions,axis=-2)


def first_step(states):
    theta0=states[:,4,3];ref=states[:,5,2]
    proposal=(1-LAMBDA)*theta0+LAMBDA*np.tanh(ref)
    centered=proposal-proposal.mean(axis=(-2,-1),keepdims=True)
    scales=NORM/np.maximum(centered.std(axis=(-2,-1),keepdims=True),1e-9)
    projected=scales*centered
    d=lambda x:x[1]-x[0]
    shape_term=float(scales.mean())*d(centered)
    gain_term=float(scales[1,0,0]-scales[0,0,0])*centered.mean(axis=0)
    terms=np.stack((d(states[:,4,0]),d(states[:,5,0]),d(ref),d(np.tanh(ref)),d(proposal),
        d(centered),shape_term,gain_term,d(projected),
        d(states[:,6,2])/(1-(1-RHO)**WINDOW),d(states[:,6,3])))
    details=np.stack((proposal.mean(axis=(-2,-1)),centered.std(axis=(-2,-1)),scales[:,0,0]),axis=-1)
    return terms,details


def focal_values(states, records, terms):
    values=np.array([rms(terms[i]) for i in (0,1,2,4,8)]+
        [rms(states[1,6,f]-states[0,6,f]) for f in (0,2,3)]+[0.]*6)
    valid=np.ones(len(LABELS),bool)
    pairs=((values[7],NORM),(values[7],rms(records[5]-records[4])),
           (rms(terms[3]),rms(terms[2])),(rms(terms[5]),rms(terms[4])),
           (rms(terms[8]),rms(terms[5])),(rms(terms[9]),rms(terms[0])))
    for position,(numerator,denominator) in enumerate(pairs,8):
        valid[position]=denominator>0
        values[position]=numerator/denominator if valid[position] else 0.
    return values,valid


def analyze_parent(payload):
    states,records=payload['parent_states'],payload['records']
    terms,details=first_step(states)
    values,valid=focal_values(states,records,terms)
    # Only descriptive stored endpoint contrasts; no descendant dynamics.
    x=payload['values']  # reader,time,onoff,record,draw,region,metric
    child_contrast=(x[:,:,0,1]-x[:,:,0,0]).mean(axis=2)
    return dict(trace=delta_trace(states,payload['targets']),terms=terms,projection_details=details,
        focal=values,valid=valid,child_contrast=child_contrast)


def bootstrap_indices(blocks):
    seed=int.from_bytes(hashlib.sha256((TAG+':block-bootstrap').encode()).digest()[:16],'little')
    return np.random.default_rng(seed).integers(0,blocks,(10000,blocks))


def summarize(blocks):
    values=np.stack([b['focal'] for b in blocks]);valid=np.stack([b['valid'] for b in blocks])
    resamples=bootstrap_indices(len(blocks));rows=[]
    for column,label in enumerate(LABELS):
        ok=valid[:,:,column];v=values[:,:,column]
        row=dict(label=label,available=bool(ok.all()),valid_parents_per_block=ok.sum(axis=1).tolist(),
                 block_means=None,mean=None,observed_block_range=None,pointwise_block_bootstrap_95=None)
        # Do not silently drop or zero-fill a degenerate ratio in pooled inference.
        if ok.all():
            means=v.mean(axis=1)
            row.update(block_means=means.tolist(),mean=float(means.mean()),
                observed_block_range=[float(means.min()),float(means.max())],
                pointwise_block_bootstrap_95=np.quantile(means[resamples].mean(axis=1),(.025,.975)).tolist())
        rows.append(row)
    summary={key:np.stack([b[key] for b in blocks]).mean(axis=(0,1))
             for key in ('trace','projection_details','child_contrast')}
    return summary,rows


def clock_reference():
    rows=[]
    for n in (1,50):
        k=np.arange(1,n+1)
        rows.append(dict(updates=n,R_unit_step_weight=float(1-(1-RHO)**n),
            theta_direct_unit_step_weight=float(1-(1-LAMBDA)**n),
            theta_cascade_unit_step_weight=float(np.sum(LAMBDA*(1-LAMBDA)**(n-k)*(1-(1-RHO)**k)))))
    return rows


def contract():
    return dict(run_id=RUN_ID,decision='D087',law='L24',source_run=source.RUN_ID,
        mode='OUTCOME_KNOWN_SAVED_STATE_AUDIT',tissues=list(source.TISSUES),parents_per_block=4,
        fields=list(FIELDS),stages=list(source.STAGES),regions=list(source.REGIONS),metrics=list(TRACE_METRICS),
        terms=list(TERMS),summary_labels=list(LABELS),rho=RHO,writer_rate=LAMBDA,norm=NORM,window=WINDOW,
        trace_axes='parent,stage,field,region,metric',term_axes='parent,term,row,column',
        projection_axes='parent,condition,proposal_mean_centered_std_scale',
        child_contrast_axes='parent,reader,time,region,source_metric',
        intervals='10000_whole_block_bootstrap_percentile_pointwise_95',
        undefined_ratio_policy='zero_placeholder_with_valid_flag_and_no_pooled_inference_if_any_invalid',
        new_simulation_lives=0,historical_dynamics_replays=0,intermediate_steps_imputed=0,
        source_parent_controls_rechecked=32,source_descendant_snapshot_metrics_rechecked=320,
        initial_to_first_update_only_projection_decomposition=True,
        projection_terms='symmetric_average_scale_times_delta_shape_plus_delta_scale_times_average_shape',
        recovered_R_drive='exact_50_step_exponential_average_identity_not_a_reconstructed_trajectory',
        toy_clock_is_actual_life_model=False,actual_weak_signal_readout_calibrated=False,
        scientific_pass_gate=None,automatic_followup=False,workers=1,max_cpus=4,
        reserve_bytes=RESERVE,output_allowance_bytes=ALLOWANCE,output_hashes=12,
        algebra_atol=1e-12,observer_atol=1e-12)


def input_paths(root):
    out=root/'outputs'/source.RUN_ID;paths=[]
    for name in ('input_hashes.sha256','output_hashes.sha256'):
        path=out/name;paths.append(path)
        paths.extend(Path(line.split('  ',1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/source.RUN_ID/name for name in ('MANIFEST.json','STATUS.json','COMPLETE','LAUNCH.json')]
    ws=Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENCE,'reviews/L24_DESCENDANT_PILOT_2026-09-11.md')]
    return sorted(set(p.resolve() for p in paths))


def preflight(root):
    cpus=source.preflight(root,starting=False)
    if shutil.disk_usage(root).free<RESERVE+ALLOWANCE: raise RuntimeError('four GiB reserve plus 64 MiB required')
    return cpus


def freeze_path(root): return root/'tmp'/f'{RUN_ID}_freeze.json'


def freeze(root):
    cpus=preflight(root);path=freeze_path(root)
    if path.exists(): raise FileExistsError('immutable audit freeze already exists')
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    checker().source_manifest_check(root,hashes)
    record=dict(frozen_utc=utc_now(),contract=contract(),input_sha256=hashes,
                cpu_affinity=cpus,outcomes_known=True,source_trace_quantities_not_yet_computed=True)
    source.strict_json(path,record,root)
    print(json.dumps(dict(status='FROZEN',inputs=len(hashes),sha256=sha256_file(path))),flush=True)
    return record


def verify_freeze(root):
    frozen=json.loads(freeze_path(root).read_text())
    assert canonical_digest(frozen['contract'])==canonical_digest(contract())
    hashes={str(p):sha256_file(p) for p in input_paths(root)}
    assert hashes==frozen['input_sha256'],'frozen input changed'
    checker().source_manifest_check(root,hashes)
    return hashes


def run_audit(root):
    run,out=root/'runs'/RUN_ID,root/'outputs'/RUN_ID
    if run.exists() or out.exists(): raise FileExistsError('immutable audit already exists; no retries')
    cpus=preflight(root);hashes=verify_freeze(root)
    hashes[str(freeze_path(root))]=sha256_file(freeze_path(root))
    run.mkdir(parents=True);out.mkdir(parents=True);start=time.monotonic()
    try:
        manifest=contract()|dict(started_utc=utc_now(),input_sha256=hashes,cpu_affinity=cpus,
            environment=environment_manifest(),hash_contract=canonical_digest(hashes))
        source.strict_json(run/'MANIFEST.json',manifest,root)
        atomic_text(out/'input_hashes.sha256',''.join(f'{hashes[p]}  {p}\n' for p in sorted(hashes)),root)
        check=checker();blocks=[];source_values=[];source_analysis=json.loads((root/'outputs'/source.RUN_ID/'analysis.json').read_text())
        maxima=[]
        for i,tissue in enumerate(source.TISSUES):
            with np.load(root/'outputs'/source.RUN_ID/f'block_{tissue}.npz',allow_pickle=False) as f: data=dict(f)
            meta=json.loads((root/'outputs'/source.RUN_ID/f'block_{tissue}.json').read_text())
            assert meta==source_analysis['blocks'][i]
            check.source_block_check(data,meta,tissue)
            source_values.append(data['values']);rows=[]
            for parent in range(4):
                payload={k:v[parent] for k,v in data.items()};row=analyze_parent(payload)
                maxima.append(check.check_parent(payload,row));rows.append(row)
            block={k:np.stack([row[k] for row in rows]) for k in rows[0]}
            source.base.atomic_npz(out/f'block_{tissue}.npz',block,root)
            with np.load(out/f'block_{tissue}.npz',allow_pickle=False) as saved:
                for k,v in block.items(): np.testing.assert_array_equal(saved[k],v)
            blocks.append(block)
            source.strict_json(run/'STATUS.json',dict(status='RUNNING',checked_blocks=len(blocks),updated_utc=utc_now()),root)
        with np.load(root/'outputs'/source.RUN_ID/'summary.npz',allow_pickle=False) as saved:
            assert source.checker().check_summary(source_values,dict(saved),source_analysis['focal'])
        summary,rows=summarize(blocks);clock=clock_reference()
        assert check.check_summary(blocks,summary,rows) and check.check_clock(clock)
        source.base.atomic_npz(out/'summary.npz',summary,root)
        with np.load(out/'summary.npz',allow_pickle=False) as saved: assert check.check_summary(blocks,dict(saved),rows)
        analysis=contract()|dict(completed_utc=utc_now(),technical_checks_passed=True,summary=rows,
            clock_reference=clock,first_step_identity_max_abs=max(maxima),source_focal=source_analysis['focal'])
        source.strict_json(out/'analysis.json',analysis,root)
        assert check.check_summary(blocks,summary,json.loads((out/'analysis.json').read_text())['summary'])
        for path,digest in hashes.items(): assert sha256_file(Path(path))==digest,path
        verification=dict(passes=True,checked_blocks=8,first_step_checks=32,source_input_hashes=159,source_output_hashes=20,
            source_parent_controls=32,source_snapshot_metric_batches=320,new_dynamics=0,
            saved_statistics_and_pool_recomputed=True,first_step_identity_max_abs=max(maxima),checked_utc=utc_now())
        source.strict_json(out/'verification.json',verification,root)
        paths=[out/f'block_{t}.npz' for t in source.TISSUES]+[out/name for name in ('summary.npz','analysis.json','verification.json','input_hashes.sha256')]
        assert len(paths)==12
        write_hash_manifest(paths,out/'output_hashes.sha256',root)
        assert source.checker().check_hashes(out/'output_hashes.sha256')==12
        total=sum(p.stat().st_size for p in paths);assert total<ALLOWANCE
        status=dict(status='COMPLETE',run_id=RUN_ID,checked_blocks=8,completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start,verified_saved_analysis=True,output_bytes=total,new_dynamics=0)
        source.strict_json(run/'STATUS.json',status,root);atomic_text(run/'COMPLETE',status['completed_utc']+'\n',root)
        print(json.dumps(status,indent=2),flush=True)
        return 0
    except Exception as error:
        source.strict_json(run/'STATUS.json',dict(status='FAILED',error=str(error),traceback=traceback.format_exc()),root)
        atomic_text(run/'FAILED',utc_now()+'\n',root)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--external-root',required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--freeze',action='store_true');group.add_argument('--run',action='store_true')
    args=parser.parse_args();root=external_root(args.external_root)
    if args.freeze: freeze(root);return 0
    return run_audit(root)


if __name__=='__main__': raise SystemExit(main())
