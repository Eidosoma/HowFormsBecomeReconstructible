"""Reconcile retained completion receipts, aggregates and report; no new dynamics."""
from pathlib import Path
import os
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis,inference,math
from scipy.stats import ttest_1samp

run = ROOT / 'runs/confirmation_v1'
complete = read(run / 'COMPLETE.json')
frozen = read(ROOT / 'FREEZE.json')
assert complete['status'] == 'COMPLETE' and complete['blocks'] == list(BLOCKS)
assert not (run / 'FAILED.json').exists() and not (ROOT / 'QUEUE_FAILED.json').exists()
assert complete['inputs'] == frozen['inputs']
assert complete['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
assert read(ROOT / 'QUEUE_COMPLETE.json')['status'] == 'PASS'
assert read(ROOT / 'STARTUP_PERSISTENCE_CHECK.json')['status'] == 'PASS'
assert all(not p['still_tt036'] for p in read(ROOT / 'COMPLETION_PROCESS_CHECK.json')['processes'].values())
assert inputs()==frozen['inputs']
verify(frozen['evidence'])

checked = {}
def bound(path):
    h = sha(path)
    assert h == complete['outputs'][str(path)], str(path)
    checked[str(path)] = h

for name in ('REPORT.md', 'METADATA.json', 'RUNNING.json', 'SUMMARY.npz', 'INFERENCE.json'):
    bound(run / name)
metadata = read(run / 'METADATA.json')
for key, expected in (
    ('conditions', CONDITIONS), ('source_contrasts', SOURCE_CONTRASTS),
    ('budgets', BUDGETS), ('credits', CREDITS),
    ('comparisons', COMPARISONS), ('stat_fields', STAT_FIELDS), ('blocks', BLOCKS),
):
    assert metadata[key] == list(expected), key
assert metadata['body_endpoint'] == 1000
assert metadata['joint_body_sign'] == metadata['joint_recipient_sign'] == list(SIGNS)
assert metadata['joint_resolution'] == ['fixed_output_mean', 'record_mean']
assert metadata['verification'] == complete['verification']
assert metadata['primary'] == 'residual|all|all_masks|own; body at 1000; 100_minus_1000; target; co-primary body and recipient'

proof, blocks = {}, []
for index in BLOCKS:
    directory = run / f'tissue_{index}'
    bound(directory / 'COMPLETE.json')
    block = read(directory / 'COMPLETE.json')
    assert block['status'] == 'PASS' and block['block'] == index
    assert all(complete['outputs'][p] == h for p, h in block['outputs'].items())
    for key, value in block['verification'].items():
        proof[key] = proof.get(key, 0) + value
    bound(directory / 'AGGREGATE.npz')
    blocks.append(arrays(directory / 'AGGREGATE.npz'))
assert proof == complete['verification']
assert proof['labelled_cases'] == 49152 and proof['paired_rows'] == 196608
assert proof['max_native_error']==0
assert proof['new_receiving_assays']==16*proof['new_reader_batches']==303104
assert proof['new_independent_receiving_draws']==512
assert proof['new_repair_batches']+proof['repair_aliases']==proof['logical_repairs']==9216
assert proof['new_reader_batches']+proof['reader_aliases']==49152
assert proof['native_arrays_replayed']==proof['baseline_native_arrays']+20*proof['new_repair_batches']+12*proof['new_reader_batches']==362944
assert proof['prefix_arrays_checked']==12*3072
assert proof['preserved_packet_identities']==proof['stopped_packet_identities']==3072
assert proof['initial_state_arrays_checked']==4*3072 and proof['intervention_arrays_checked']==15*64*2*2
assert proof['saved_new_arrays']==proof['baseline_saved_arrays']+24*proof['new_repair_batches']+16*proof['new_reader_batches']+4*64*2*2
assert metadata['source_population_exposed'] is False and metadata['recipient_evidence_inherited'] is False

# Independently reconcile each retained block aggregate with the global summary.
# This checks reduction, weighting and count denominators without repeating assays.
a = arrays(run / 'SUMMARY.npz')
for name in ('records', 'source_records'):
    counts = np.stack([b[name] for b in blocks])
    np.testing.assert_array_equal(counts, a['block_' + name])
    np.testing.assert_array_equal(counts.sum(0), a[name])
for name in ('recipient_levels', 'original_levels', 'body_levels', 'recipient_stats', 'body_stats', 'recipient_source_stats', 'body_source_stats'):
    values = np.stack([b[name] for b in blocks])
    weights = a['block_source_records' if name.endswith('source_stats') else 'block_records']
    if name.endswith('stats'):
        totals = values[..., 1:].sum(0)
        np.testing.assert_array_equal(totals, a[name + '_counts'])
        assert np.isfinite(totals).all() and (totals >= 0).all()
        np.testing.assert_array_equal(totals, np.rint(totals))
        records = weights.sum(0)
        for offset, multiplier in ((0, 2 if name.startswith('body_') else 8), (3, 2), (6, 1)):
            n = totals[..., offset:offset + 3].sum(-1)
            expected = np.broadcast_to((records * multiplier)[:, None, None], n.shape)
            np.testing.assert_array_equal(n, expected)
        values = values[..., 0]
    np.testing.assert_array_equal(values, a[name + '_block_means'])
    for j in range(len(weights[0])):
        keep = weights[:, j] > 0
        if keep.any():
            near(a[name + '_equal_block'][j], values[keep, j].mean(0))
            near(a[name + '_pooled_record'][j], np.average(values[keep, j], axis=0, weights=weights[keep, j]))
        else:
            assert np.isnan(a[name + '_equal_block'][j]).all()
            assert np.isnan(a[name + '_pooled_record'][j]).all()
assert analysis.report(a, 'confirmation') == (run / 'REPORT.md').read_text()

joint = np.stack([b['joint_counts'] for b in blocks])
np.testing.assert_array_equal(joint, a['joint_counts_by_block'])
np.testing.assert_array_equal(joint.sum(0), a['joint_counts'])
assert (joint >= 0).all()
for resolution, offset, multiplier in ((0, 3, 2), (1, 6, 1)):
    table = a['joint_counts'][:, :, :, resolution]
    for endpoint, axis in (('body', -1), ('recipient', -2)):
        expected = a[endpoint + '_stats_counts'][..., [offset + 1, offset + 2, offset]]
        np.testing.assert_array_equal(table.sum(axis), expected)
    np.testing.assert_array_equal(
        table.sum((-2, -1)), np.broadcast_to((a['records'] * multiplier)[:, None, None], table.shape[:3]))

def endpoint(key, name):
    j = INDEX[key]
    levels = a[name + '_levels_equal_block'][j, :, 0]
    changes = a[name + '_stats_equal_block'][j, :, 0]
    near(changes, levels[[1, 1, 2]] - levels[[0, 2, 0]])
    contrasts = {}
    for ti, label in enumerate(COMPARISONS):
        counts = a[name + '_stats_counts'][j, ti, 0].astype(int)
        values = a[name + '_stats_block_means'][:, j, ti, 0]
        values = values[np.isfinite(values)]
        contrasts[label] = dict(
            equal_block_change_pp=float(100 * changes[ti]),
            pooled_record_change_pp=float(100 * a[name + '_stats_pooled_record'][j, ti, 0]),
            paired_counts=dict(zip(('gain', 'harm', 'tie'), map(int, counts[:3]))),
            fixed_output_mean_counts=dict(zip(('gain', 'harm', 'tie'), map(int, counts[3:6]))),
            record_mean_counts=dict(zip(('gain', 'harm', 'tie'), map(int, counts[6:9]))),
            block_counts=dict(gain=int((values > 0).sum()), harm=int((values < 0).sum()), tie=int((values == 0).sum())),
        )
    return dict(target_credit_percent_by_writing_budget=(100 * levels).tolist(), comparisons=contrasts)

# A separate reduction of primary saved rows uses integer credit sums, not the
# experiment's aggregation functions. All cases, masks and corruptions enter.
j=INDEX['residual|all|all_masks|own'];primary_checks=[]
for index,aggregate in zip(BLOCKS,blocks):
    directory=run/f'tissue_{index}'
    for name in ('CONFIG.json','ROWS.json','BODIES.json'):bound(directory/name)
    config=read(directory/'CONFIG.json')
    assert config['block']==index and config['role']=='confirmation' and config['corruptions']==2 and config['draws']==4
    body=[r for r in read(directory/'BODIES.json') if r['family']=='residual' and r['body_source']=='own']
    recipient=[r for r in read(directory/'ROWS.json') if r['family']=='residual' and r['body_source']=='own']
    assert len(body)==128 and len(recipient)==512
    signatures={};by_endpoint={};levels={}
    for name,rows,fields in (
        ('body',body,('preserve1000','stopped1000','body1000')),
        ('recipient',recipient,('incoming','after100','after1000')),
    ):
        total=np.zeros(3,dtype=np.int64);differences=np.zeros((2,16),dtype=np.int64);seen=set()
        for r in rows:
            assert r['block']==index and r['reset']=='uniform'
            key=(r['corruption'],r['world'],r['mask'])+((r['draw'],) if name=='recipient' else ())
            assert key not in seen;seen.add(key)
            raw=np.array([r[f][0] for f in fields]);u=np.rint(raw*12).astype(np.int64)
            near(u/12,raw);assert np.isin(u,(0,3,4,6,12)).all()
            total+=u;differences[r['corruption'],r['world']]+=u[1]-u[2]
        levels[name]=total/(12*len(rows));by_endpoint[name]=differences.sum()/(12*len(rows))
        near(levels[name],aggregate[name+'_levels'][j,:,0])
        near(by_endpoint[name],aggregate[name+'_stats'][j,1,0,0])
        signatures[name]=[np.sign(differences),np.sign(differences.sum(0))]
    for resolution in (0,1):
        tab=np.array([[int(((signatures['body'][resolution]==b)&(signatures['recipient'][resolution]==r)).sum())
            for r in (-1,0,1)] for b in (-1,0,1)],dtype=np.int64)
        np.testing.assert_array_equal(tab,aggregate['joint_counts'][j,1,0,resolution])
    primary_checks.append(dict(block=index,body_delta=by_endpoint['body'],recipient_delta=by_endpoint['recipient']))

registered=read(run/'INFERENCE.json');assert registered==inference.results(a)
assert registered['family_alpha']==.05 and registered['per_endpoint_alpha']==.025
assert registered['population_units']==64 and registered['comparison']=='100_minus_1000'
for name in ('body','recipient'):
    values=np.array([v[name+'_delta'] for v in primary_checks]);interval=registered['endpoints'][name]['interval']
    near(values,a[name+'_stats_block_means'][:,j,1,0])
    near(values.mean(),interval['mean']);near(values.std(ddof=1)/8,interval['standard_error'])
    independent=ttest_1samp(values,0.,alternative='greater').confidence_interval(confidence_level=.975)
    near(independent.low,interval['lower_one_sided'])
    two_sided=ttest_1samp(values,0.,alternative='two-sided').confidence_interval(confidence_level=.95)
    near([two_sided.low,two_sided.high],interval['pointwise_two_sided_95'])
    near(values.mean()-math.sqrt(2*math.log(40)/64),interval['hoeffding_lower_sensitivity'])
    expected='DIRECTIONAL_SUPERIORITY_PASS' if independent.low>0 else 'NOT_CONFIRMED'
    assert registered['endpoints'][name]['classification']==expected
assert registered['joint_classification']=='CONFIRMED_JOINT_STOPPING_BENEFIT'

stamp=now()
selected_keys=['|'.join((family,'all',view,source)) for family in FAMILIES
    for view in ('all_masks',)+tuple('geometry:'+g for g in GEOMETRIES) for source in SOURCES]
selected_keys+=['|'.join((family,group,'all_masks','own')) for family in FAMILIES
    for group in ('history:unique_pass','history:other')]
findings=dict(study='TT036',reviewed_utc=stamp,registered_inference=registered,primary=metadata['primary'],
    source_summary=str(run/'SUMMARY.npz'),source_summary_sha256=sha(run/'SUMMARY.npz'),
    writing_budgets=BUDGETS,body_endpoint=1000,primary_saved_row_reductions=primary_checks,
    estimand='Original-target recognition credit; fractional ties retained, not binary success.',
    comparisons={key:dict(records=int(a['records'][INDEX[key]]),body=endpoint(key,'body'),
        fresh_recipient=endpoint(key,'recipient'),joint_fixed_output_counts=a['joint_counts'][INDEX[key],:,0,0].tolist(),
        joint_record_mean_counts=a['joint_counts'][INDEX[key],:,0,1].tolist()) for key in selected_keys},
    joint_axes=dict(comparison=COMPARISONS,body_sign=SIGNS,recipient_sign=SIGNS),
    interpretation=[
        'The fixed 100-write rule passes both registered directional endpoints versus 1000 writes on 64 fresh source blocks.',
        'Residual own-source all-mask terminal body credit improves by 7.72705078125 percentage points; packet credit improves by 9.381103515625 points. All 64 block means are positive for each endpoint.',
        'Record means retain 474 body gains, 82 harms and 468 ties; packet means retain 725 gains, 209 harms and 90 ties.',
        'Joint record means retain 384 improvements in both endpoints, 39 declines in both, 80 opposing-direction tradeoffs and 521 with at least one tied endpoint.',
        'Against preservation, 100 writes gain 15.6982421875 packet points while losing 2.9296875 body points.',
        'Negative-half and mixed-half averages benefit, while positive-half retention loses both body and packet credit.',
    ],
    limitations=[
        'Inference is approximate paired-block Student-t, with Bonferroni alpha .025 per endpoint. The conservative bounded Hoeffding lower sensitivity bounds remain below zero for both endpoints.',
        'This confirms a directional average under uniform memory reset, full incoming-packet replacement and the specified source distribution; it establishes neither a practical threshold nor a universal stopping rule.',
        'Four receiving futures per fixed packet give coarse conditional information; body and packet outcomes remain separate endpoints.',
        'Record positions, exact aliases and receiving draws are dependencies, not additional independent source blocks.',
        'No optimal stopping time, uninterrupted body performance, serial continuation or long-term heredity benefit was tested.',
        'Bounded identity/address searches do not constitute independent custody or blinding. Native teaching and repair noise remain coupled across task messages.',
    ],TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED',successor_started=False)
write(ROOT/'FINDINGS.json',findings)
write(ROOT/'CLOSEOUT.json',dict(status='PASS_RETAINED_RECEIPT_AGGREGATE_AND_PRIMARY_ROW_REVIEW',reviewed_utc=stamp,
    completed_utc=complete['completed_utc'],seconds=complete['seconds'],blocks=64,verification=proof,
    completion_sha256=sha(run/'COMPLETE.json'),freeze_sha256=sha(ROOT/'FREEZE.json'),
    receipt_report_aggregate_and_primary_row_hashes_checked=checked,all_output_hashes_rechecked_in_this_review=False,
    review_checks='Frozen inputs and evidence, all block receipts/aggregates, proof totals, summary weighting and denominators, joint marginals, independent primary raw-row reduction and joint counts, registered inference via a separate confidence-interval call, exact report regeneration.',
    full_source_output_and_dynamics_checks='Passed during the completed frozen run; raw physical trajectories were not replayed again in this review.',
    new_dynamics_in_review=0,new_receiving_assays_in_review=0,scientific_results_inspected=True,
    registered_joint_classification=registered['joint_classification'],findings_sha256=sha(ROOT/'FINDINGS.json'),successor_started=False))

handoff=read(ROOT/'QUEUE_HANDOFF.json');verify(handoff['files'])
archive=ROOT/'completion_handoff_inputs';archive.mkdir(exist_ok=False)
paths=set(map(Path,handoff['files']))|{ROOT/n for n in ('QUEUE_HANDOFF.json','CURRENT_EXECUTION.json','QUEUE_STATUS.json')}
saved={}
for path in sorted(paths):
    dest=archive/path.relative_to(LANE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    h=sha(path);assert sha(dest)==h;saved[str(path)]=dict(snapshot=str(dest),sha256=h)
write(archive/'MANIFEST.json',dict(files=saved,archived_utc=stamp))
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt036-complete.pending');write(temp,value);os.replace(temp,path)

current=read(ROOT/'CURRENT_EXECUTION.json')
current.update(status='COMPLETE_REVIEWED',updated_utc=stamp,completed_utc=complete['completed_utc'],
    actual_seconds=complete['seconds'],completed_blocks=64,retained_bytes=complete['retained_bytes'],verification=proof,
    closeout='TT036/CLOSEOUT.json',findings='TT036/FINDINGS.json',report='TT036/runs/confirmation_v1/REPORT.md',
    registered_inference=registered,joint_decision_pending=False,processes_exited=True,no_active_jobs=True,
    scientific_results_inspected=True,new_production_outcomes_inspected=True,source_population_now_exposed=True,
    full_source_checks_passed_during_run=True,successor_started=False,
    next_step='Report completed confirmation and retained preservation/geometry tradeoffs; no successor launched')
replace_file(ROOT/'CURRENT_EXECUTION.json',current)
message=f"""
[TT036 fresh-cohort stopped-writing confirmation](TT036/README.md) is **complete
and reviewed**. All 64 fresh blocks finished at {complete['completed_utc']}
in **5 hours 18 minutes 43 seconds**, using two single-thread CPUs. All frozen
checks passed: 362,944 native arrays independently replayed, 512 new paired
receiving environments, 303,104 physical recipient assays, and all 196,608
labelled paired rows retained. Both job and controller have exited.

The registered joint criterion **CONFIRMED_JOINT_STOPPING_BENEFIT** passed.
For residual-family own-source all-mask original-target recognition:

| Writing updates | Terminal body credit | Fresh-recipient packet credit |
|---|---:|---:|
| 0: preservation | 43.09% | 25.00% |
| 100: stop writing, continue body | 40.16% | 40.70% |
| 1,000: continuous writing | 32.43% | 31.32% |

Stopping at 100 increases body credit by **7.7271 percentage points** and
packet credit by **9.3811 points** versus continuous writing. The respective
one-sided alpha .025 lower bounds are **6.9333 and 8.6488 points**; pointwise
95% intervals are **[6.9333, 8.5208]** and **[8.6488, 10.1134]**. All 64 block
means are positive for both endpoints. These are approximate paired-block
Student-t results with Bonferroni family alpha .05. Conservative bounded
Hoeffding sensitivity lower bounds remain negative (-26.23 / -24.57 points).

Paired harms remain: body record means have **474 gains / 82 harms / 468 ties**;
packet record means have **725 / 209 / 90**. Of 1,024 record means, **384**
improve on both endpoints, **39** decline on both, **48** improve the body while
harming the packet, **32** improve the packet while harming the body, and
**521** have at least one tied endpoint. These counts are descriptive.

Preservation remains a tradeoff: 100 writes gain **15.6982 packet points** but
lose **2.9297 body points** versus no writing. The common family shows the same
mean ordering (100 versus 1,000: +6.1890 body / +7.0160 packet points).
Residual negative-half and mixed-half retention benefit on both endpoints;
positive-half retention loses **2.2461 body / 12.5122 packet points**.

This fresh-cohort result supports the fixed stopping rule's average benefit
under uniform memory reset, fully replaced incoming packets and the stated
source/recipient distribution. It does not establish 100 updates as optimal,
universal benefit, uninterrupted body performance, or serial heredity.
Four recipient draws per fixed packet remain coarse conditional evidence.
TT028 primary and joint classifications remain NOT_CONFIRMED.

The review independently reduced the primary saved rows and reconciled all
block aggregates, weights, count denominators, joint tables, registered
inference and the report. Full physical replay and complete source/output
checks passed during acquisition and were not repeated in this review.
No successor has been started. See [report](TT036/runs/confirmation_v1/REPORT.md),
[registered inference](TT036/runs/confirmation_v1/INFERENCE.json),
[findings](TT036/FINDINGS.json) and [review scope](TT036/CLOSEOUT.json).
"""
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
(ROOT/'README.md').write_text('# TT036 — fresh-cohort stopped writing\n\n'+message.replace('(TT036/','(')+
    '\nPrior handoff documents are preserved in [the completion archive](completion_handoff_inputs/MANIFEST.json).\n')
with (PRIOR/'README.md').open('a') as f:f.write('\nTT036 is complete and reviewed: on 64 fresh blocks, the registered 100-versus-1,000-write joint comparison passed (+7.7271 body / +9.3811 fresh-recipient packet points). Preservation still has higher body credit, and paired harms and geometry reversals remain. See [TT036 findings](../TT036/README.md).\n')
successor=dict(study='TT036',status='COMPLETE_REVIEWED',current_execution='TT036/CURRENT_EXECUTION.json',
    closeout='TT036/CLOSEOUT.json',findings='TT036/FINDINGS.json',registered_joint_classification=registered['joint_classification'],successor_started=False)
predecessor=read(PRIOR/'CURRENT_EXECUTION.json');predecessor.update(authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',predecessor)
intake=read(LANE/'prediction_intake_status.json')
intake['stopped_writing_body_endpoint']['authorized_successor']=successor
intake['fresh_stopped_writing_confirmation'].update(successor,actual_seconds=complete['seconds'],verification=proof,
    registered_inference=registered,joint_decision_pending=False,scientific_results_inspected=True,
    source_population_now_exposed=True,processes_exited=True,new_receiving_assays=proof['new_receiving_assays'])
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT036',event='fresh_stopping_confirmation_completed_and_reviewed',recorded_utc=stamp,
        completion_sha256=sha(run/'COMPLETE.json'),closeout_sha256=sha(ROOT/'CLOSEOUT.json'),findings_sha256=sha(ROOT/'FINDINGS.json'),
        registered_joint_classification=registered['joint_classification'],fresh_source_blocks=64,source_population_now_exposed=True,
        scientific_results_inspected=True,interim_scientific_outcomes_inspected=False,new_receiving_environments=512,
        new_receiving_assays=303104,successor_started=False,TT028_primary='NOT_CONFIRMED'),sort_keys=True)+'\n')
bound_paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT035/README.md','TT035/CURRENT_EXECUTION.json')]+[ROOT/n for n in (
    'README.md','CURRENT_EXECUTION.json','FINDINGS.json','CLOSEOUT.json','COMPLETION_PROCESS_CHECK.json',
    'RESULT_INSPECTION.json','completion_handoff_inputs/MANIFEST.json','admin/reconcile_completion.py')]
write(ROOT/'COMPLETION_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,files={str(p):sha(p) for p in bound_paths},
    successor_started=False,review_scope='Frozen inputs, receipts, aggregates, independent primary saved-row reduction, joint tables, inference and report; full raw dynamics checks inherited from the completed run.'))
verify(read(ROOT/'COMPLETION_HANDOFF.json')['files'])
print(dict(status='COMPLETE_REVIEWED',blocks=64,seconds=complete['seconds'],reviewed_artifacts=len(checked),
    registered_joint_classification=registered['joint_classification'],new_dynamics_in_review=0,successor_started=False))

