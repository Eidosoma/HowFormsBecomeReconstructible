"""Review all damage panels, retained hashes and independent primary row reductions."""
from pathlib import Path
import signal,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import analysis

RUN=ROOT/'runs/damage_v1'

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
            for offset,multiplier in ((0,1 if name.startswith('body_') else 4),(3,1),(6,1)):
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
    for resolution,offset,multiplier in ((0,3,1),(1,6,1)):
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

def main():
    tick=time.monotonic();complete=read(RUN/'COMPLETE.json');frozen=read(ROOT/'FREEZE.json')
    assert complete['status']=='COMPLETE' and complete['blocks']==list(BLOCKS)
    assert complete['inputs']==frozen['inputs']==inputs()
    assert complete['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert complete['environment']==frozen['environment'] and complete['cpus']==[6,7]
    assert complete['workers']==2 and complete['numerical_threads']==1
    assert not (RUN/'FAILED.json').exists() and not (ROOT/'QUEUE_FAILED.json').exists()
    assert not (RUN/'CONFIRMATION.json').exists() and not frozen['confirmatory']
    assert read(ROOT/'QUEUE_COMPLETE.json')['status']=='PASS'
    assert read(ROOT/'STARTUP_PERSISTENCE_CHECK.json')['status']=='PASS'
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_tt040_jobs']
    inspection=read(ROOT/'RESULT_INSPECTION.json')
    assert inspection['complete_sha256']==sha(RUN/'COMPLETE.json') and not inspection['interim_inspection']
    assert datetime.fromisoformat(inspection['recorded_utc'])>datetime.fromisoformat(complete['completed_utc'])
    assert datetime.fromisoformat(frozen['frozen_utc'])<datetime.fromisoformat(complete['started_utc'])
    assert frozen['blocks']==list(BLOCKS) and not frozen['new_production_outcomes_generated']
    assert frozen['source_population_exposed'] and frozen['source_population_reused']
    assert frozen['corruptions_per_block']==1 and frozen['draws_per_corruption']==4
    assert frozen['damage_levels']==list(DAMAGE) and frozen['mixture_weights']==MIX
    assert frozen['body_endpoint']==1900 and frozen['recipient_endpoint']==1000
    assert frozen['new_recipient_environments']==16
    verify(frozen['evidence']);manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence'])
    verify(complete['outputs'])
    assert read(ROOT/'RANDOMNESS.json')['namespace']==TAG
    metadata=read(RUN/'METADATA.json')
    for key,value in (('conditions',CONDITIONS),('source_contrasts',SOURCE_CONTRASTS),('arms',ARMS),
        ('original_writing_budgets',BUDGETS),('credits',CREDITS),('comparisons',COMPARISONS),
        ('stat_fields',STAT_FIELDS),('blocks',BLOCKS),('body_checkpoints',SNAPSHOTS),('damage_levels',DAMAGE)):
        assert metadata[key]==list(value),key
    assert metadata['mixture_weights']==MIX and metadata['role']=='development'
    assert metadata['source_population_reused'] and metadata['source_population_exposed']
    assert not metadata['recipient_evidence_inherited'] and not metadata['confirmatory']
    assert metadata['body_endpoint']==1900 and metadata['recipient_endpoint']==1000
    assert metadata['joint_body_sign']==metadata['joint_recipient_sign']==list(SIGNS)
    assert metadata['joint_resolution']==['fixed_output_mean','record_mean']
    assert metadata['primary']=='mix050; residual|all|all_masks|own; late_minus_preserve; target; body at 1900 and fresh recipient; descriptive'
    proof={};saved_rows={};saved_bodies={};configs={};source_files={}
    for index in BLOCKS:
        directory=RUN/f'tissue_{index}';block=read(directory/'COMPLETE.json');config=read(directory/'CONFIG.json')
        assert block['status']=='PASS' and block['block']==index
        assert all(complete['outputs'][p]==h for p,h in block['outputs'].items())
        for k,v in block['verification'].items():proof[k]=proof.get(k,0)+v
        assert config['block']==index and config['role']=='development'
        assert config['corruptions']==1 and config['draws']==4 and config['damage_levels']==list(DAMAGE)
        assert config['arms']==list(ARMS) and config['original_writing_windows']==[list(w) for w in WINDOWS]
        assert config['body_checkpoints']==list(SNAPSHOTS) and config['body_endpoint']==1900
        assert config['production_population_reused'] and not config['recipient_outcomes_reused']
        assert config['record_bytes']==2048 and config['readout']['sweeps']==1000
        used=read(directory/'USED_INPUTS.json');assert used==manifest['source_blocks'][str(index)]['files']
        verify(used);source_files.update(used)
        source=read(directory/'SOURCE_BASELINE.json');assert source['files']==used and source['source_population_reused']
        saved_rows[index]=read(directory/'ROWS.json');saved_bodies[index]=read(directory/'BODY_TRAJECTORY.json');configs[index]=config
        assert len(saved_rows[index])==4608 and len(saved_bodies[index])==1152
        assert set(r['damage'] for r in saved_rows[index])==set(r['damage'] for r in saved_bodies[index])==set(DAMAGE)
        assert all(r['incoming']==r['original'] for r in saved_rows[index] if r['damage']=='mix000')
    assert proof==metadata['verification']==complete['verification']
    expected=dict(labelled_cases=4608,body_checkpoint_observations=23040,paired_rows=18432,
        logical_repairs=1152,new_repair_batches=848,new_repair_worlds=13568,repair_aliases=304,
        new_reader_batches=2624,new_receiving_assays=41984,reader_aliases=3136,
        new_independent_receiving_draws=16,new_baseline_native_arrays=0,new_baseline_saved_arrays=0,
        inherited_baseline_saved_arrays=460,native_arrays_replayed=68800,saved_new_arrays=96304,
        body_scores_checked=4240,initial_state_arrays_checked=1152,intervention_arrays_checked=136,
        early_full_prefix_arrays_checked=3456,late_preserve_prefix_arrays_checked=5760,
        post1000_saved_packet_identities=4608,preserved_packet_identities=288,early_packet_identities=288,max_native_error=0.)
    assert proof==expected
    summaries={};histories={};changes={};row_checks=[];panels={};j=INDEX['residual|all|all_masks|own']
    for damage in DAMAGE:
        by_time={t:[] for t in SNAPSHOTS};change_blocks=[]
        for index in BLOCKS:
            directory=RUN/f'tissue_{index}'
            agg={t:arrays(directory/f'AGGREGATE_{damage}_{t}.npz') for t in SNAPSHOTS}
            for t in SNAPSHOTS:by_time[t].append(agg[t])
            for t in SNAPSHOTS[1:]:
                for key in ('records','source_records','original_levels','recipient_levels','recipient_stats','recipient_source_stats'):
                    exact(agg[t][key],agg[START][key],'packet invariance '+key)
            change=arrays(directory/f'BODY_CHANGE_{damage}.npz');change_blocks.append(change)
            exact(change['records'],agg[START]['records']);near(change['stats'][...,0],agg[END]['body_levels']-agg[START]['body_levels'])
            rows=[r for r in saved_rows[index] if r['damage']==damage and r['family']=='residual' and r['body_source']=='own']
            bodies=[r for r in saved_bodies[index] if r['damage']==damage and r['family']=='residual' and r['body_source']=='own']
            assert len(rows)==256 and len(bodies)==64
            recipient=np.zeros((1,4,16,4,4),dtype=np.int64)
            body={t:np.zeros((1,1,16,4,4),dtype=np.int64) for t in SNAPSHOTS};seen=set()
            for r in rows:
                c,d,w=r['corruption'],r['draw'],r['world'];key=(c,d,w,r['mask'])
                assert c==0 and 0<=d<4 and 0<=w<16 and r['mask'] in MASKS and key not in seen;seen.add(key)
                assert r['block']==index and r['reset']=='uniform'
                recipient[c,d,w]+=row_units([r[field] for field in READER_FIELDS])
            seen=set()
            for r in bodies:
                c,w=r['corruption'],r['world'];key=(c,w,r['mask'])
                assert c==0 and 0<=w<16 and r['mask'] in MASKS and key not in seen;seen.add(key)
                assert r['block']==index and r['reset']=='uniform'
                assert set(r['body_by_time'])==set(map(str,SNAPSHOTS))
                for t in SNAPSHOTS:
                    assert set(r['body_by_time'][str(t)])==set(BODY_FIELDS)
                    body[t][c,0,w]+=row_units([r['body_by_time'][str(t)][field] for field in BODY_FIELDS])
            rs=reduce_values(recipient,agg[START],'recipient',j)
            for t in SNAPSHOTS:
                bs=reduce_values(body[t],agg[t],'body',j)
                for ti in range(6):
                    for resolution in (0,1):
                        for credit in range(4):
                            bsign=bs[ti][resolution][...,credit];rsign=rs[ti][resolution][...,credit]
                            table=np.array([[int(((bsign==b)&(rsign==r)).sum()) for r in (-1,0,1)] for b in (-1,0,1)])
                            np.testing.assert_array_equal(table,agg[t]['joint_counts'][j,ti,credit,resolution])
            delta=body[END]-body[START]
            for arm in range(4):
                for credit in range(4):
                    d=delta[...,arm,credit];near(d.mean()/48,change['stats'][j,arm,credit,0])
                    counts=np.concatenate([count_signs(x) for x in (d,d.sum(1),d.sum((0,1)))])
                    np.testing.assert_array_equal(counts,change['stats'][j,arm,credit,1:])
            row_checks.append(dict(block=index,damage=damage,
                body_by_time_percent={str(t):(100*body[t].mean((0,1,2))/48).tolist() for t in SNAPSHOTS},
                fresh_recipient_percent=(100*recipient.mean((0,1,2))/48).tolist()))
        dest=RUN/('summary_'+damage);history=arrays(dest/'TRAJECTORY_LEVELS.npz');levels={}
        for ti,t in enumerate(SNAPSHOTS):
            a=arrays(dest/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'))
            audit_summary(by_time[t],a);levels[t]=a;exact(history['body_levels_equal_block'][ti],a['body_levels_equal_block'])
            if t!=START:
                for key in a:
                    if key.startswith(('recipient_','original_')):exact(a[key],levels[START][key])
        change=arrays(dest/'BODY_CHANGE_SUMMARY.npz')
        counts=np.stack([v['records'] for v in change_blocks]);values=np.stack([v['stats'] for v in change_blocks])
        np.testing.assert_array_equal(counts,change['block_records']);np.testing.assert_array_equal(counts.sum(0),change['records'])
        np.testing.assert_array_equal(values[...,0],change['block_means']);np.testing.assert_array_equal(values[...,1:].sum(0),change['counts'])
        for offset in (0,3,6):
            n=change['counts'][...,offset:offset+3].sum(-1)
            np.testing.assert_array_equal(n,np.broadcast_to(change['records'][:,None,None],n.shape))
        for k in range(len(CONDITIONS)):
            keep=counts[:,k]>0
            if keep.any():
                near(change['equal_block'][k],values[keep,k,...,0].mean(0))
                near(change['pooled_record'][k],np.average(values[keep,k,...,0],axis=0,weights=counts[keep,k]))
            else:assert np.isnan(change['equal_block'][k]).all() and np.isnan(change['pooled_record'][k]).all()
        near(change['equal_block'],levels[END]['body_levels_equal_block']-levels[START]['body_levels_equal_block'])
        summaries[damage]=levels[END];histories[damage]=history;changes[damage]=change;a=levels[END]
        if damage=='mix000':
            for suffix in ('equal_block','pooled_record','block_means'):
                exact(a['recipient_levels_'+suffix][...,0,:],a['original_levels_'+suffix])
        else:
            for key in a:
                if key.startswith('original_'):exact(a[key],summaries['mix000'][key])
        selected=['|'.join((f,g,v,o)) for f in FAMILIES for g in ('all','history:unique_pass','history:other')
            for v in ('all_masks',)+tuple('geometry:'+name for name in GEOMETRIES) for o in SOURCES]
        conditions={}
        for key in selected:
            k=INDEX[key]
            conditions[key]=dict(records=int(a['records'][k]),body=endpoint(a,key,'body'),
                fresh_recipient=endpoint(a,key,'recipient'),original_recipient_percent=float(100*a['original_levels_equal_block'][k,0]),
                body_trajectory_percent_by_arm={str(t):(100*levels[t]['body_levels_equal_block'][k,:,0]).tolist() for t in SNAPSHOTS},
                within_arm_change_pp=(100*change['equal_block'][k,:,0]).tolist(),
                joint_fixed_output_counts=a['joint_counts'][k,:,0,0].tolist(),joint_record_mean_counts=a['joint_counts'][k,:,0,1].tolist())
        panels[damage]=dict(conditions=conditions,primary_block_changes_pp={str(index):dict(
            body=float(100*a['body_stats_block_means'][n,j,1,0]),recipient=float(100*a['recipient_stats_block_means'][n,j,1,0]))
            for n,index in enumerate(BLOCKS)})
    assert analysis.report_all(summaries,histories,changes,'development')==(RUN/'REPORT.md').read_text()
    stamp=now()
    findings=dict(study='TT040',reviewed_utc=stamp,primary=metadata['primary'],blocks=BLOCKS,arms=ARMS,
        damage_levels=DAMAGE,mixture_weights=MIX,body_endpoint=1900,recipient_endpoint=1000,
        body_checkpoints=SNAPSHOTS,writing_windows=WINDOWS,source_population_exposed=True,source_population_reused=True,
        confirmatory=False,classification='DESCRIPTIVE_PARTIAL_PACKET_GAIN_WITH_BODY_COST_AND_INTACT_HARM',
        panels=panels,primary_saved_row_reductions=row_checks,
        interpretation=[
            'Half-mixed residual own-source late writing improves mean recipient credit by 1.5625 points while reducing body credit by 1.171875 points.',
            'Intact residual records lose 1.66015625 recipient points and 3.90625 body points under late writing versus preservation.',
            'Fully replaced residual records gain 13.18359375 recipient points and 6.640625 body points; this does not rescue the informative-record tradeoff.',
            'The primary partial-packet benefit varies across blocks and retains individual harms; this is not a general repair-without-cost result.',
        ],limitations=[
            'Four previously exposed source blocks, one corruption realization per block and four paired receiving conditions: development only.',
            'Half mixing is an amplitude weight, not a fraction of information erased; different damage panels share noise and recipients.',
            'Record positions, masks, sources and recipient draws are dependent; four source blocks are the population units.',
            'No hypothesis test, absence-of-harm, equivalence, noninferiority or fresh-population confirmation was specified.',
            'Sparse fixed body checkpoints do not establish uninterrupted or indefinite performance.',
            'No serial inheritance, adaptive policy, optimal timing or independent teaching-cue test was performed.',
        ],TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED',TT036_confirmation_unchanged=True,
        TT039_confirmation_unchanged=True,successor_started=False)
    # Convert empty descriptive strata to explicit nulls in JSON, retaining NaNs in the native arrays.
    def finite(value):
        if isinstance(value,dict):return {k:finite(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [finite(v) for v in value]
        if isinstance(value,float) and not np.isfinite(value):return None
        return value
    write(ROOT/'FINDINGS.json',finite(findings))
    write(ROOT/'CLOSEOUT.json',dict(status='PASS_ALL_OUTPUT_HASHES_AGGREGATES_AND_PRIMARY_ROWS',reviewed_utc=stamp,
        completed_utc=complete['completed_utc'],seconds=complete['seconds'],review_seconds=time.monotonic()-tick,
        blocks=len(BLOCKS),damage_panels=len(DAMAGE),verification=proof,completion_sha256=sha(RUN/'COMPLETE.json'),
        freeze_sha256=sha(ROOT/'FREEZE.json'),all_output_hashes_rechecked_in_this_review=True,
        output_files_rehashed=len(complete['outputs']),source_files_rehashed=len(source_files),
        source_file_hashes_checked=source_files,findings_sha256=sha(ROOT/'FINDINGS.json'),
        review_checks='Frozen input/evidence and every retained output hash; reused source hashes; all three damage panels and five checkpoints; block/global weights, counts, joint marginals and within-arm changes; independent integer primary saved-row reductions for all arms, credits and contrasts; intact-original identity and packet invariance; exact report regeneration.',
        full_physical_replay='Passed during acquisition; no physical dynamics rerun in closeout.',
        new_dynamics_in_review=0,new_receiving_assays_in_review=0,scientific_results_inspected=True,
        interim_scientific_inspection=False,successor_started=False))
    print(dict(status='PASS_REVIEW',blocks=4,panels=3,output_hashes=len(complete['outputs']),review_seconds=time.monotonic()-tick),flush=True)
    for damage,panel in panels.items():
        c=panel['conditions']['residual|all|all_masks|own']
        print(json.dumps(dict(damage=damage,body=c['body']['comparisons']['late_minus_preserve'],
            recipient=c['fresh_recipient']['comparisons']['late_minus_preserve'],blocks=panel['primary_block_changes_pp']),sort_keys=True),flush=True)

if __name__=='__main__':
    def expire(*_):raise TimeoutError('600-second completion review limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    try:main();signal.alarm(0)
    except BaseException as error:
        write(ROOT/'CLOSEOUT_REVIEW_FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc()));raise

