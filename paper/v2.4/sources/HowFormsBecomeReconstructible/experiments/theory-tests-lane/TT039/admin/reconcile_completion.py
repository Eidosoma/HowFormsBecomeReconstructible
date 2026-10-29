"""Review fresh confirmation with independent integer rows and decision calculations."""
from pathlib import Path
import signal,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import analysis

RUN=ROOT/'runs/confirmation_v1'

def count_signs(value):
    return np.array([int((value>0).sum()),int((value<0).sum()),int((value==0).sum())])

def reduce_values(values,aggregate,endpoint,j):
    # Sum of four masks, in exact integer twelfths, for every credit.
    levels=values.mean((0,1,2))/48
    near(levels,aggregate[endpoint+'_levels'][j])
    signs=[]
    for ti,(left,right) in enumerate(PAIRS):
        delta=values[:,:,:,left]-values[:,:,:,right]
        near(delta.mean((0,1,2))/48,aggregate[endpoint+'_stats'][j,ti,:,0])
        for credit in range(4):
            d=delta[...,credit]
            counts=np.concatenate([count_signs(x) for x in (d,d.sum(1),d.sum((0,1)))])
            np.testing.assert_array_equal(counts,aggregate[endpoint+'_stats'][j,ti,credit,1:])
        signs.append((np.sign(delta.sum(1)),np.sign(delta.sum((0,1)))))
    return signs

def row_units(raw):
    raw=np.asarray(raw);units=np.rint(12*raw).astype(np.int64)
    near(units/12,raw);assert np.isin(units,(0,3,4,6,12)).all()
    return units

def audit_summary(blocks,a):
    for name in ('records','source_records'):
        counts=np.stack([b[name] for b in blocks])
        np.testing.assert_array_equal(counts,a['block_'+name])
        np.testing.assert_array_equal(counts.sum(0),a[name])
    for name in ('recipient_levels','original_levels','body_levels','recipient_stats','body_stats','recipient_source_stats','body_source_stats'):
        values=np.stack([b[name] for b in blocks])
        weights=a['block_source_records' if name.endswith('source_stats') else 'block_records']
        if name.endswith('stats'):
            totals=values[...,1:].sum(0)
            np.testing.assert_array_equal(totals,a[name+'_counts'])
            assert np.isfinite(totals).all() and (totals>=0).all()
            np.testing.assert_array_equal(totals,np.rint(totals))
            for offset,multiplier in ((0,2 if name.startswith('body_') else 8),(3,2),(6,1)):
                count=totals[...,offset:offset+3].sum(-1)
                np.testing.assert_array_equal(count,np.broadcast_to((weights.sum(0)*multiplier)[:,None,None],count.shape))
            values=values[...,0]
        np.testing.assert_array_equal(values,a[name+'_block_means'])
        for j in range(weights.shape[1]):
            keep=weights[:,j]>0
            if keep.any():
                near(a[name+'_equal_block'][j],values[keep,j].mean(0))
                near(a[name+'_pooled_record'][j],np.average(values[keep,j],axis=0,weights=weights[keep,j]))
            else:
                assert np.isnan(a[name+'_equal_block'][j]).all() and np.isnan(a[name+'_pooled_record'][j]).all()
    joint=np.stack([b['joint_counts'] for b in blocks])
    np.testing.assert_array_equal(joint,a['joint_counts_by_block'])
    np.testing.assert_array_equal(joint.sum(0),a['joint_counts']);assert (joint>=0).all()
    for resolution,offset,multiplier in ((0,3,2),(1,6,1)):
        table=a['joint_counts'][:,:,:,resolution]
        for endpoint,axis in (('body',-1),('recipient',-2)):
            np.testing.assert_array_equal(table.sum(axis),a[endpoint+'_stats_counts'][...,[offset+1,offset+2,offset]])
        np.testing.assert_array_equal(table.sum((-2,-1)),np.broadcast_to((a['records']*multiplier)[:,None,None],table.shape[:3]))

def endpoint(a,key,name):
    j=INDEX[key];levels=a[name+'_levels_equal_block'][j,:,0]
    changes=a[name+'_stats_equal_block'][j,:,0]
    near(changes,[levels[left]-levels[right] for left,right in PAIRS])
    contrasts={}
    for ti,label in enumerate(COMPARISONS):
        counts=a[name+'_stats_counts'][j,ti,0].astype(int)
        values=a[name+'_stats_block_means'][:,j,ti,0];values=values[np.isfinite(values)]
        contrasts[label]=dict(equal_block_change_pp=float(100*changes[ti]),
            pooled_record_change_pp=float(100*a[name+'_stats_pooled_record'][j,ti,0]),
            paired_counts=dict(zip(('gain','harm','tie'),map(int,counts[:3]))),
            fixed_output_mean_counts=dict(zip(('gain','harm','tie'),map(int,counts[3:6]))),
            record_mean_counts=dict(zip(('gain','harm','tie'),map(int,counts[6:9]))),
            block_counts=dict(zip(('gain','harm','tie'),map(int,count_signs(values)))))
    return dict(target_credit_percent_by_arm=(100*levels).tolist(),comparisons=contrasts)

def audit_decision(summary, saved):
    # Recompute from block values using NumPy reductions; do not call inference.py.
    from scipy.stats import t as student
    assert saved['comparison']=='late_minus_preserve' and saved['credit']=='target'
    assert saved['condition']=='residual|all|all_masks|own'
    assert saved['family_alpha']==.05 and saved['per_endpoint_alpha']==.025
    assert saved['population_units']==64 and saved['approximate_coverage']
    assert saved['secondary_results_cannot_rescue_primary'] and not saved['automatic_extension']
    assert saved['multiplicity']=='Bonferroni across two co-primary endpoints'
    j=INDEX[saved['condition']];computed={};passes=[]
    for name in ('body','recipient'):
        x=summary[name+'_stats_block_means'][:,j,1,0]
        assert x.shape==(64,) and np.isfinite(x).all() and (np.abs(x)<=1).all()
        mean=float(np.mean(x));se=float(np.std(x,ddof=1)/np.sqrt(64))
        bounded=float(np.sqrt(2*np.log(1/.025)/64))
        radius=float(student.ppf(.975,63))*se if se else bounded
        lower=max(-1.,mean-radius);upper=min(1.,mean+radius)
        expected=dict(n=64,mean=mean,standard_error=se,lower_one_sided=lower,alpha=.025,
            pointwise_two_sided_95=[lower,upper],hoeffding_lower_sensitivity=max(-1.,mean-bounded),
            method='approximate paired block Student-t' if se else 'bounded Hoeffding zero-variance fallback')
        row=saved['endpoints'][name];ci=row['interval'];assert set(ci)==set(expected)
        for k,v in expected.items():
            if isinstance(v,str):assert ci[k]==v
            else:near(ci[k],v)
        assert row['margin']==0
        passed=lower>0;passes.append(passed)
        assert row['classification']==('DIRECTIONAL_SUPERIORITY_PASS' if passed else 'NOT_CONFIRMED')
        computed[name]=dict(interval=expected,margin=0.,passed=passed,block_values=x.tolist())
    classification='CONFIRMED_JOINT_LATE_WRITING_BENEFIT' if all(passes) else 'NOT_CONFIRMED'
    assert saved['joint_classification']==classification
    return dict(joint_classification=classification,endpoints=computed,
        method='Independent NumPy mean/sample standard deviation and Student-t quantile; saved primary rows reconciled separately')

def main():
    tick=time.monotonic();complete=read(RUN/'COMPLETE.json');frozen=read(ROOT/'FREEZE.json')
    assert complete['status']=='COMPLETE' and complete['blocks']==list(BLOCKS)
    assert not (RUN/'FAILED.json').exists() and not (ROOT/'QUEUE_V2_FAILED.json').exists()
    assert complete['inputs']==frozen['inputs']==inputs()
    assert complete['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert read(ROOT/'QUEUE_V2_COMPLETE.json')['status']=='PASS'
    assert read(ROOT/'STARTUP_PERSISTENCE_CHECK.json')['status']=='PASS'
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_tt039_jobs']
    inspection=read(ROOT/'RESULT_INSPECTION.json')
    assert inspection['complete_sha256']==sha(RUN/'COMPLETE.json') and not inspection['interim_inspection']
    assert datetime.fromisoformat(inspection['recorded_utc'])>datetime.fromisoformat(complete['completed_utc'])
    assert datetime.fromisoformat(frozen['frozen_utc'])<datetime.fromisoformat(complete['started_utc'])
    assert frozen['blocks']==list(BLOCKS) and not frozen['new_production_outcomes_generated']
    assert frozen['primary']=='residual|all|all_masks|own; late_minus_preserve; target; body at 1900 and fresh recipient co-primary'
    assert frozen['body_endpoint']==1900 and frozen['recipient_endpoint']==1000
    assert frozen['family_alpha']==.05 and frozen['per_endpoint_alpha']==.025 and frozen['margin']==0
    assert not frozen['source_population_exposed'] and frozen['new_recipient_environments']==512
    assert complete['environment']==frozen['environment'] and complete['cpus']==[6,7]
    assert complete['workers']==2 and complete['numerical_threads']==1
    correction=read(ROOT/'corrections/metadata_timer_v1/CORRECTION.json')
    assert correction['original_failure_and_outputs_preserved']
    assert not correction['numerical_pipeline_changed'] and not correction['protocol_changed']
    assert sha(ROOT/'QUEUE_FAILED.json')==correction['failed_queue_sha256']
    assert sha(ROOT/'checks/qualification_v1/FAILED.json')==correction['failed_qualification_sha256']
    assert sha(ROOT/'qualify.py')==correction['new_qualify_sha256']
    assert sha(ROOT/'PROTOCOL.md')==correction['protocol_sha256']
    assert read(ROOT/'checks/qualification_v2/COMPLETE.json')['status']=='PASS'
    assert read(ROOT/'runs/benchmark_v1/COMPLETE.json')['status']=='COMPLETE'
    reservation=read(ROOT/'RESERVATION_REVIEW.json');rng=read(ROOT/'RANDOMNESS.json')
    assert reservation['unchanged_reserved_blocks']==list(BLOCKS)
    assert reservation['reservation_sha256']==sha(ROOT/'RESERVATION.json')
    assert reservation['status']=='PASS_NO_IDENTITY_COLLISION'
    assert rng['status']=='PASS' and rng['namespace']=='TT039_late_confirmation_v1'
    assert not rng['production_random_samples_generated']
    verify(frozen['evidence']);verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
    checked={}
    def bound(path):
        h=sha(path);assert h==complete['outputs'][str(path)],str(path);checked[str(path)]=h
    for name in ('REPORT.md','METADATA.json','RUNNING.json','SUMMARY.npz','TRAJECTORY_LEVELS.npz','BODY_CHANGE_SUMMARY.npz','CONFIRMATION.json'):
        bound(RUN/name)
    for t in SNAPSHOTS[:-1]:bound(RUN/f'CHECKPOINT_SUMMARY_{t}.npz')
    metadata=read(RUN/'METADATA.json')
    for key,value in (('conditions',CONDITIONS),('source_contrasts',SOURCE_CONTRASTS),('arms',ARMS),
        ('original_writing_budgets',BUDGETS),('credits',CREDITS),('comparisons',COMPARISONS),
        ('stat_fields',STAT_FIELDS),('blocks',BLOCKS),('body_checkpoints',SNAPSHOTS)):
        assert metadata[key]==list(value),key
    assert metadata['body_endpoint']==END and metadata['followup_start']==START
    assert metadata['original_writing_windows']==[list(w) for w in WINDOWS]
    assert metadata['joint_body_sign']==metadata['joint_recipient_sign']==list(SIGNS)
    assert metadata['joint_resolution']==['fixed_output_mean','record_mean']
    assert metadata['primary']==frozen['primary']
    assert metadata['recipient_endpoint']==1000 and metadata['role']=='confirmation'
    assert not metadata['source_population_exposed'] and not metadata['recipient_evidence_inherited']
    assert not metadata['source_population_reused']
    assert metadata['new_receiving_assays']==442368 and metadata['new_independent_receiving_draws']==512
    by_time={t:[] for t in SNAPSHOTS};change_blocks=[];proof={};row_checks=[]
    j=INDEX['residual|all|all_masks|own']
    for index in BLOCKS:
        directory=RUN/f'tissue_{index}'
        for name in ('COMPLETE.json','CONFIG.json','ROWS.json','BODY_TRAJECTORY.json','BODY_CHANGE.npz','USED_INPUTS.json'):
            bound(directory/name)
        block=read(directory/'COMPLETE.json');assert block['status']=='PASS' and block['block']==index
        assert all(complete['outputs'][p]==h for p,h in block['outputs'].items())
        for key,value in block['verification'].items():proof[key]=proof.get(key,0)+value
        config=read(directory/'CONFIG.json')
        assert config['block']==index and config['role']=='confirmation'
        assert config['corruptions']==2 and config['draws']==4 and config['arms']==list(ARMS)
        assert config['body_checkpoints']==list(SNAPSHOTS) and config['body_endpoint']==END
        assert config['original_writing_windows']==[list(w) for w in WINDOWS]
        assert not config['production_population_reused'] and not config['recipient_outcomes_reused']
        assert config['source_config']['sweeps']==1000 and config['config']['sweeps']==1900
        assert config['readout']['sweeps']==1000 and config['record_bytes']==2048
        assert read(directory/'USED_INPUTS.json')=={}
        aggregate={}
        for t in SNAPSHOTS:
            p=directory/f'AGGREGATE_{t}.npz';bound(p);aggregate[t]=arrays(p);by_time[t].append(aggregate[t])
        for t in SNAPSHOTS[1:]:
            for name in ('records','source_records','original_levels','recipient_levels','recipient_stats','recipient_source_stats'):
                exact(aggregate[t][name],aggregate[START][name],'unchanged packet '+name)
        change=arrays(directory/'BODY_CHANGE.npz');change_blocks.append(change)
        exact(change['records'],aggregate[START]['records'])
        near(change['stats'][...,0],aggregate[END]['body_levels']-aggregate[START]['body_levels'])

        # Independent saved-row reduction: all five times, four arms, four
        # credits and six contrasts in the prospectively specified condition.
        rows=[r for r in read(directory/'ROWS.json') if r['family']=='residual' and r['body_source']=='own']
        bodies=[r for r in read(directory/'BODY_TRAJECTORY.json') if r['family']=='residual' and r['body_source']=='own']
        assert len(rows)==512 and len(bodies)==128
        recipient=np.zeros((2,4,16,4,4),dtype=np.int64)
        body={t:np.zeros((2,1,16,4,4),dtype=np.int64) for t in SNAPSHOTS}
        seen=set()
        for r in rows:
            c,d,w=r['corruption'],r['draw'],r['world'];k=(c,d,w,r['mask'])
            assert r['block']==index and r['reset']=='uniform' and r['mask'] in MASKS
            assert 0<=c<2 and 0<=d<4 and 0<=w<16 and k not in seen;seen.add(k)
            recipient[c,d,w]+=row_units([r[field] for field in READER_FIELDS])
        seen=set()
        for r in bodies:
            c,w=r['corruption'],r['world'];k=(c,w,r['mask'])
            assert r['block']==index and r['reset']=='uniform' and r['mask'] in MASKS
            assert 0<=c<2 and 0<=w<16 and k not in seen;seen.add(k)
            assert set(r['body_by_time'])==set(map(str,SNAPSHOTS))
            for t in SNAPSHOTS:
                assert set(r['body_by_time'][str(t)])==set(BODY_FIELDS)
                body[t][c,0,w]+=row_units([r['body_by_time'][str(t)][field] for field in BODY_FIELDS])
        rs=reduce_values(recipient,aggregate[START],'recipient',j)
        for t in SNAPSHOTS:
            bs=reduce_values(body[t],aggregate[t],'body',j)
            for ti in range(len(PAIRS)):
                for resolution in (0,1):
                    for credit in range(4):
                        bsign=bs[ti][resolution][...,credit];rsign=rs[ti][resolution][...,credit]
                        table=np.array([[int(((bsign==b)&(rsign==r)).sum()) for r in (-1,0,1)] for b in (-1,0,1)])
                        np.testing.assert_array_equal(table,aggregate[t]['joint_counts'][j,ti,credit,resolution])
        delta=body[END]-body[START]
        for arm in range(4):
            for credit in range(4):
                d=delta[...,arm,credit]
                near(d.mean()/48,change['stats'][j,arm,credit,0])
                counts=np.concatenate([count_signs(x) for x in (d,d.sum(1),d.sum((0,1)))])
                np.testing.assert_array_equal(counts,change['stats'][j,arm,credit,1:])
        row_checks.append(dict(block=index,body_by_time_percent={str(t):(100*body[t].mean((0,1,2))/48).tolist() for t in SNAPSHOTS},
            fresh_recipient_percent=(100*recipient.mean((0,1,2))/48).tolist(),within_arm_change_pp=(100*delta.mean((0,1,2))/48).tolist()))
    assert proof==metadata['verification']==complete['verification']
    assert proof['labelled_cases']==49152 and proof['paired_rows']==196608
    assert proof['body_checkpoint_observations']==5*49152
    assert proof['baseline_native_arrays']==79*64 and proof['baseline_saved_arrays']==115*64
    assert proof['new_repair_batches']==8704 and proof['new_repair_worlds']==16*8704
    assert proof['new_reader_batches']==27648 and proof['new_receiving_assays']==16*27648
    assert proof['native_arrays_replayed']==79*64+44*8704+12*27648 and proof['body_scores_checked']==5*8704
    assert proof['saved_new_arrays']==115*64+64*8704+16*27648+16*64 and proof['max_native_error']==0
    assert proof['new_repair_batches']+proof['repair_aliases']==proof['logical_repairs']==12288
    assert proof['new_reader_batches']+proof['reader_aliases']==5*48*4*64
    assert proof['new_independent_receiving_draws']==512
    assert proof['initial_state_arrays_checked']==4*48*64
    assert proof['intervention_arrays_checked']==15*4*64
    assert proof['early_full_prefix_arrays_checked']==12*48*64
    assert proof['late_preserve_prefix_arrays_checked']==20*48*64
    assert proof['post1000_saved_packet_identities']==16*48*64
    assert proof['preserved_packet_identities']==proof['early_packet_identities']==48*64

    summaries={};history=arrays(RUN/'TRAJECTORY_LEVELS.npz')
    for ti,t in enumerate(SNAPSHOTS):
        a=arrays(RUN/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'))
        audit_summary(by_time[t],a);summaries[t]=a
        exact(history['body_levels_equal_block'][ti],a['body_levels_equal_block'])
        if t!=START:
            for name in a:
                if name.startswith(('recipient_','original_')):exact(a[name],summaries[START][name],name)
    changes=arrays(RUN/'BODY_CHANGE_SUMMARY.npz');counts=np.stack([v['records'] for v in change_blocks]);values=np.stack([v['stats'] for v in change_blocks])
    np.testing.assert_array_equal(counts,changes['block_records']);np.testing.assert_array_equal(counts.sum(0),changes['records'])
    np.testing.assert_array_equal(values[...,0],changes['block_means']);np.testing.assert_array_equal(values[...,1:].sum(0),changes['counts'])
    for offset,multiplier in ((0,2),(3,2),(6,1)):
        n=changes['counts'][...,offset:offset+3].sum(-1)
        np.testing.assert_array_equal(n,np.broadcast_to((changes['records']*multiplier)[:,None,None],n.shape))
    for k in range(len(CONDITIONS)):
        keep=counts[:,k]>0
        if keep.any():
            near(changes['equal_block'][k],values[keep,k,...,0].mean(0))
            near(changes['pooled_record'][k],np.average(values[keep,k,...,0],axis=0,weights=counts[keep,k]))
        else:
            assert np.isnan(changes['equal_block'][k]).all() and np.isnan(changes['pooled_record'][k]).all()
    near(changes['equal_block'],summaries[END]['body_levels_equal_block']-summaries[START]['body_levels_equal_block'])
    decision=audit_decision(summaries[END],read(RUN/'CONFIRMATION.json'))
    assert analysis.report(summaries[END],history,changes,'confirmation')==(RUN/'REPORT.md').read_text()

    stamp=now();a=summaries[END]
    selected=['|'.join((f,'all',view,source)) for f in FAMILIES for view in ('all_masks',)+tuple('geometry:'+g for g in GEOMETRIES) for source in SOURCES]
    selected+=['|'.join((f,group,'all_masks','own')) for f in FAMILIES for group in ('history:unique_pass','history:other')]
    conditions={}
    for key in selected:
        k=INDEX[key];within={}
        for arm,name in enumerate(ARMS):
            v=changes['block_means'][:,k,arm,0];v=v[np.isfinite(v)];c=changes['counts'][k,arm,0].astype(int)
            within[name]=dict(equal_block_change_pp=float(100*changes['equal_block'][k,arm,0]),
                pooled_record_change_pp=float(100*changes['pooled_record'][k,arm,0]),
                paired_counts=dict(zip(('gain','harm','tie'),map(int,c[:3]))),
                fixed_output_mean_counts=dict(zip(('gain','harm','tie'),map(int,c[3:6]))),
                record_mean_counts=dict(zip(('gain','harm','tie'),map(int,c[6:9]))),
                block_counts=dict(zip(('gain','harm','tie'),map(int,count_signs(v)))))
        conditions[key]=dict(records=int(a['records'][k]),body=endpoint(a,key,'body'),
            fresh_recipient=endpoint(a,key,'recipient'),body_trajectory_percent_by_arm={str(t):(100*summaries[t]['body_levels_equal_block'][k,:,0]).tolist() for t in SNAPSHOTS},
            within_arm_changes=within,joint_fixed_output_counts=a['joint_counts'][k,:,0,0].tolist(),joint_record_mean_counts=a['joint_counts'][k,:,0,1].tolist())
    findings=dict(study='TT039',reviewed_utc=stamp,primary=metadata['primary'],arms=ARMS,body_endpoint=END,
        recipient_endpoint=1000,body_checkpoints=SNAPSHOTS,original_writing_windows=WINDOWS,
        new_receiving_assays=proof['new_receiving_assays'],new_independent_receiving_draws=512,
        source_population_reused=False,recipient_evidence_inherited=False,interim_scientific_inspection=False,
        confirmation=read(RUN/'CONFIRMATION.json'),independent_decision_review=decision,
        source_summary=str(RUN/'SUMMARY.npz'),source_summary_sha256=sha(RUN/'SUMMARY.npz'),
        estimand='Original-target recognition credit, with fractional ties; not binary success.',
        primary_saved_row_reductions=row_checks,comparisons=conditions,
        joint_axes=dict(comparison=COMPARISONS,body_sign=SIGNS,recipient_sign=SIGNS),
        interpretation=[
            'Both frozen co-primary lower bounds exceed zero on the 64 newly generated source blocks.',
            'Residual own-source all-mask late minus preservation body credit at 1900 is +4.052734375 points; 389 record gains, 163 harms and 472 ties remain.',
            'Fresh-recipient credit improves by +14.4378662109375 points; 853 record gains, 91 harms and 80 ties remain.',
            'Late-body mean credit changes by -0.2197265625 points, versus -4.3212890625 for preservation; the later relative advantage mainly reflects preservation decline.',
            'The common family has the same average direction: +3.86962890625 body and +14.7064208984375 recipient points.',
            'Residual late minus early body credit at 1900 is +2.74658203125 points; early packets score +0.7537841796875 points above late packets.',
            'Negative-half-retained residual own-source means favor preservation by 3.02734375 body and 4.052734375 recipient points.',
        ],limitations=[
            'Confirmation uses approximate paired-block Student-t coverage with Bonferroni alpha .025 per endpoint and margin zero; no minimum practical gain was tested.',
            'The conservative distribution-free Hoeffding sensitivity lower bounds are below zero for both endpoints.',
            'Mean stability does not imply stability of individuals: late-body follow-up retains 354 gains, 352 harms and 318 ties among primary record means.',
            'A fixed 1900 endpoint and sparse intermediate checkpoints do not establish indefinite stability or uninterrupted performance.',
            'Packets were not rewritten after update 1000; four fresh receiving conditions per corruption were sampled, without further writing or descendants.',
            'Original post-write ages remain different across schedules; waiting and recovery are not isolated.',
            'The uniform-memory reset, replaced incoming packets, damage magnitude and source distribution restrict generalization.',
            'Record positions, masks, aliases and repeated recipient draws are dependent; independent population units remain the 64 source blocks.',
            'Identity and seed non-reuse checks are bounded local evidence, not independent custody or global proof of non-use.',
            'No optimal timing, adaptive warning policy, damage-level robustness or serial heredity was tested.',
        ],TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED',TT036_confirmation_unchanged=True,successor_started=False)
    write(ROOT/'FINDINGS.json',findings)
    write(ROOT/'CLOSEOUT.json',dict(status='PASS_RETAINED_RECEIPT_AGGREGATE_AND_PRIMARY_ROW_REVIEW',reviewed_utc=stamp,
        completed_utc=complete['completed_utc'],seconds=complete['seconds'],review_seconds=time.monotonic()-tick,blocks=64,verification=proof,
        completion_sha256=sha(RUN/'COMPLETE.json'),freeze_sha256=sha(ROOT/'FREEZE.json'),
        receipt_report_aggregate_and_primary_row_hashes_checked=checked,
        all_output_hashes_rechecked_in_this_review=False,
        review_checks='Frozen inputs/evidence, reserved fresh identities and recorded validation-only correction; all block receipts and all five checkpoint aggregates; all global weighting, counts and joint marginals; independent integer primary-row reductions for five times, four arms, four credits, six comparisons and within-arm changes; fresh packet invariance across body checkpoints; independent frozen co-primary decision/interval recomputation; exact report regeneration.',
        full_source_output_and_dynamics_checks='Passed during the frozen run; physical trajectories were not replayed again in this review.',
        new_dynamics_in_review=0,new_receiving_assays_in_review=0,scientific_results_inspected=True,
        findings_sha256=sha(ROOT/'FINDINGS.json'),successor_started=False))
    print(dict(status='PASS_REVIEW',blocks=64,review_seconds=time.monotonic()-tick,reviewed_artifacts=len(checked),joint_classification=decision['joint_classification']),flush=True)
    for f in FAMILIES:
        key=f+'|all|all_masks|own';c=conditions[key]
        print(json.dumps(dict(condition=key,body_percent=c['body']['target_credit_percent_by_arm'],
            late_minus_preserve=c['body']['comparisons']['late_minus_preserve'],within_arm=c['within_arm_changes']),sort_keys=True),flush=True)

if __name__=='__main__':
    def expire(*_):raise TimeoutError('600-second completion review limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    try:main();signal.alarm(0)
    except BaseException as error:
        write(ROOT/'CLOSEOUT_REVIEW_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc()));raise
