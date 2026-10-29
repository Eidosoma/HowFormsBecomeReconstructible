"""Verify retained completion, check result arithmetic, and record the lane handoff."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
import analysis
import design
import math
import os
import shutil
import signal
import time


def near(a,b):assert math.isclose(a,b,rel_tol=0,abs_tol=2e-13),(a,b)
def append(path,text):
    with path.open('a') as f:f.write('\n\n'+text.strip()+'\n')


def main():
    tick=time.monotonic();job=ROOT/'runs/reset_v1';dest=ROOT/'checks/completion_v1'
    dest.mkdir(parents=True,exist_ok=False)
    resources=read_json(ROOT/'COMPLETION_RESOURCE_CHECK.json')
    assert resources['admission_pass'] and 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(resources['recorded_utc'])).total_seconds()<180
    os.sched_setaffinity(0,{resources['cpus'][-1]})
    def expire(*_):raise TimeoutError('TT032 completion review 600-second limit')
    signal.signal(signal.SIGALRM,expire);signal.alarm(600)
    completed=read_json(job/'COMPLETE.json');frozen=read_json(ROOT/'FREEZE.json')
    assert completed['status']=='COMPLETE' and not (job/'FAILED.json').exists()
    assert completed['inputs']==frozen['inputs']==runtime_hashes()
    assert completed['freeze_sha256']==sha(ROOT/'FREEZE.json')
    verify(frozen['inputs']);verify(frozen['evidence']);verify(completed['outputs'])
    assert {str(p) for p in job.rglob('*') if p.is_file()}==set(completed['outputs'])|{str(job/'COMPLETE.json')}
    assert sum(Path(p).stat().st_size for p in completed['outputs'])==completed['retained_bytes']
    summary=read_json(job/'SUMMARY.json')
    assert summary['verification']==completed['verification'] and summary['blocks']==list(BLOCKS)
    assert all(completed['verification'][k]==v for k,v in design.expected('development',64).items())
    assert analysis.report(summary)==(job/'REPORT.md').read_text()
    cells=0;joints=0
    for family,groups in summary['cells'].items():
        assert groups['all']['records']==1024
        assert groups['history:unique_pass']['records']+groups['history:other']['records']==1024
        assert all(groups[f'message:{m}']['records']==256 for m in range(4))
        for group,g in groups.items():
            for category in analysis.CATEGORIES:
                for key,v in g[category].items():
                    n=v['records'];weights=v['block_record_counts'];assert n==g['records']==sum(weights.values())
                    assert v['blocks']==g['blocks']==len(weights)
                    joint=v['record_recipient_body_joint'];assert sum(joint.values())==n
                    for field,draws in (('recipient',4),('body',1)):
                        e=v[field];effects=e['block_effects'];assert set(effects)==set(weights)
                        assert all(-1<=x<=1 for x in effects.values())
                        near(e['equal_nonempty_block_effect'],sum(effects.values())/len(effects))
                        near(e['pooled_record_effect'],sum(effects[b]*weights[b] for b in weights)/n)
                        assert e['block_sign_counts']=={s:sum(analysis.sign(x)==s for x in effects.values()) for s in analysis.SIGNS}
                        for name,total in (('paired_counts',n*2*draws),('fixed_output_mean_counts',n*2),('record_mean_counts',n)):
                            assert sum(e[name].values())==total and all(type(x) is int and x>=0 for x in e[name].values())
                        for sign in analysis.SIGNS:
                            margin=sum(joint[sign+'|'+z] if field=='recipient' else joint[z+'|'+sign] for z in analysis.SIGNS)
                            assert margin==e['record_mean_counts'][sign]
                    if category=='conditions':
                        view,owner,reset,budget,credit=key.split('|')
                        preserved=g['conditions']['|'.join((view,owner,reset,'0',credit))]
                        for weighting,effect in (('equal_nonempty_block','equal_nonempty_block_effect'),('pooled_record','pooled_record_effect')):
                            near(v['recipient_mean'][weighting]-v['incoming_mean'][weighting],v['recipient'][effect])
                            near(v['body_mean'][weighting]-preserved['body_mean'][weighting],v['body'][effect])
                        for name in ('recipient_mean','body_mean','incoming_mean','original_mean'):
                            assert all(0<=x<=1 for x in v[name].values())
                    else:
                        parts=key.split('|');view=parts[0]
                        if category=='source_contrasts':
                            own,other=parts[1].split('_minus_');reset,budget,credit=parts[2:]
                            a=g['conditions']['|'.join((view,own,reset,budget,credit))]
                            b=g['conditions']['|'.join((view,other,reset,budget,credit))]
                        else:
                            owner=parts[1];a_reset,b_reset=parts[2].split('_minus_');budget,credit=parts[3:]
                            a=g['conditions']['|'.join((view,owner,a_reset,budget,credit))]
                            b=g['conditions']['|'.join((view,owner,b_reset,budget,credit))]
                        for field in ('recipient','body'):
                            for weighting,effect in (('equal_nonempty_block','equal_nonempty_block_effect'),('pooled_record','pooled_record_effect')):
                                near(a[field+'_mean'][weighting]-b[field+'_mean'][weighting],v[field][effect])
                    cells+=1;joints+=1
    findings=dict(study='TT032',recorded_utc=now(),scope='Descriptive reset intervention on all 64 exposed TT028 blocks; mix100 only.',
        source_records_per_family=1024,receiving_draws=4,credit='Fractional four-message recognition credit, averaged over paired recipients and masks within source record.',
        families={},uniform_neutral_template_average_is_structural=True,neutral_reversal_complement_identity=True,
        harms_retained=True,body_and_recipient_endpoints_separate=True,fresh_population_confirmation=False,
        serial_endpoint=False,TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED')
    for family,groups in summary['cells'].items():
        g=groups['all'];out={}
        for reset in design.RESETS:
            out[reset]=dict(conditions={owner:{credit:g['conditions'][f'all_masks|{owner}|{reset}|1000|{credit}']
                for credit in ('target','donor','template','opposite')} for owner in design.BODIES},
                source_contrasts={other:g['source_contrasts'][f'all_masks|own_minus_{other}|{reset}|1000|target'] for other in ('neutral','foreign')},
                geometry={geom:{owner:g['conditions'][f'geometry:{geom}|{owner}|{reset}|1000|target'] for owner in design.BODIES}
                    for geom in design.GEOMETRIES})
        out['history_group_records']={k:v['records'] for k,v in groups.items()}
        out['uniform_history_source_contrasts']={k:{other:v['source_contrasts'][f'all_masks|own_minus_{other}|uniform|1000|target'] for other in ('neutral','foreign')}
            for k,v in groups.items() if k.startswith('history:')}
        findings['families'][family]=out
    write_json(ROOT/'FINDINGS.json',findings)
    review=dict(status='PASS',recorded_utc=now(),seconds=time.monotonic()-tick,
        completed_run_sha256=sha(job/'COMPLETE.json'),freeze_sha256=sha(ROOT/'FREEZE.json'),
        summary_sha256=sha(job/'SUMMARY.json'),report_sha256=sha(job/'REPORT.md'),
        original_output_files_verified=len(completed['outputs']),retained_bytes=completed['retained_bytes'],
        verification=completed['verification'],aggregate_cells_checked=cells,joint_tables_checked=joints,
        source_and_reset_contrasts_checked=True,paired_harm_totals_checked=True,report_roundtrip_pass=True,
        frozen_inputs_unchanged=True,new_dynamics=0,new_receiving_assays=0,
        original_benchmark_failure_preserved=True,automatic_successor=False)
    write_json(dest/'COMPLETE.json',review);write_json(ROOT/'CLOSEOUT.json',review)
    # Preserve all previous handoff-bound files before administrative updates.
    prior=read_json(ROOT/'LAUNCH_HANDOFF.json');verify(prior['files'])
    archive=ROOT/'completion_handoff_inputs';archive.mkdir(exist_ok=False);manifest={}
    for original in list(prior['files'])+[str(ROOT/'LAUNCH_HANDOFF.json')]:
        p=Path(original);target=archive/p.relative_to(LANE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        assert sha(p)==sha(target);manifest[str(p)]=dict(snapshot=str(target),sha256=sha(p))
    write_json(archive/'MANIFEST.json',dict(files=manifest,recorded_utc=now()))
    status=read_json(ROOT/'CURRENT_EXECUTION.json');status.update(status='COMPLETE_VERIFIED',updated_utc=now(),
        completed_utc=completed['completed_utc'],actual_seconds=completed['seconds'],retained_bytes=completed['retained_bytes'],
        completed_blocks=64,live_workers=0,verification=completed['verification'],closeout='TT032/CLOSEOUT.json',
        findings='TT032/FINDINGS.json',report='TT032/runs/reset_v1/REPORT.md',
        production_effects_inspected=True,first_effect_review_utc=findings['recorded_utc'],post_startup_progress_polled=True,
        progress_polls_user_requested=True,automatic_polling=False,successor_started=False)
    (ROOT/'CURRENT_EXECUTION.json').write_bytes(serialized(status))
    def mean(f,r,o='own',credit='target',field='recipient_mean'):
        return 100*findings['families'][f][r]['conditions'][o][credit][field]['equal_nonempty_block']
    lines=['# TT032: completed spatial reset intervention','',
        f'**Complete and verified.** All 64 exposed source blocks finished at {completed["completed_utc"]}, in {completed["seconds"]/3600:.2f} hours on two single-thread workers.',
        f'Independent replay checked {completed["verification"]["native_arrays"]:,} native checkpoint arrays with zero discrepancies. Saved verification covered {completed["verification"]["saved_arrays"]:,} arrays; {completed["verification"]["actual_mask_arrays"]:,} arrays bridged exactly to TT028. The final review checked retained file hashes, all {cells:,} aggregate cells, source/reset contrasts, paired harms, joint body/recipient counts and report roundtrip.','',
        'Changing only the spatial memory offset has a large effect on the outgoing packet. A smaller message-specific body advantage remains under uniform reset, but it is strongly dependent on which target-relative half of the body survives. These are fractional recognition scores, not percentages of independent lineages or estimates of long-term capacity.','',
        '| Record family | Own body, corrected reset | Own body, uniform reset | Own body, reversed reset | Preserved replaced packet |',
        '|---|---:|---:|---:|---:|']
    for f in design.FAMILIES:lines.append(f'| {f} | {mean(f,"corrected"):.4f}% | {mean(f,"uniform"):.4f}% | {mean(f,"reversed"):.4f}% | 25.0000% |')
    lines+=['','The neutral body tracks the prescribed reset template at 99.987793% credit; reversal tracks the opposite template at the same rate. Uniform neutral template credit averaged across masks is structurally 25% once mask independence is verified. Neutral family/task duplicates and reversed/complemented-mask identities are not independent replications.','',
        '| Family | Uniform own − neutral (pp) | Uniform own − foreign (pp) | Own − foreign block gains / harms / ties | Own − foreign record-mean gains / harms / ties |',
        '|---|---:|---:|---|---|']
    for f in design.FAMILIES:
        c=findings['families'][f]['uniform']['source_contrasts'];v=c['foreign']['recipient']
        counts=lambda field:' / '.join(str(v[field][s]) for s in analysis.SIGNS)
        lines.append(f'| {f} | {100*c["neutral"]["recipient"]["equal_nonempty_block_effect"]:+.4f} | {100*v["equal_nonempty_block_effect"]:+.4f} | {counts("block_sign_counts")} | {counts("record_mean_counts")} |')
    lines+=['','The modest uniform-reset average hides a severe geometry dependence. Each row below retains all cases; the two mixed masks are averaged within each source record. The overall four-mask mean weights positive, negative and mixed geometry 1:1:2.','',
        '| Family | Positive target half retained | Negative target half retained | Both polarities retained |',
        '|---|---:|---:|---:|']
    for f in design.FAMILIES:
        vals=[100*findings['families'][f]['uniform']['geometry'][geom]['own']['recipient_mean']['equal_nonempty_block'] for geom in design.GEOMETRIES]
        lines.append(f'| {f} | {vals[0]:.4f}% | {vals[1]:.4f}% | {vals[2]:.4f}% |')
    lines+=['','For residual records under uniform reset, rewriting improves the recipient score by 6.451416 percentage points on average, while the body endpoint falls by 11.584473 points relative to matched preservation. Record-mean recipient changes are 635 gains, 322 harms and 67 ties. The own-minus-foreign comparison has 669 gains, 87 harms and 268 ties. These are different comparisons, with masks and receiving draws averaged inside records. A positive average does not make every rewrite helpful.','',
        'The intervention retained both record families, two saved corruption realizations, four physical masks, own/foreign/neutral bodies, matched 0/1,000 writing budgets and 1,000 body updates. Four fresh paired recipients assessed each packet. Incoming and unmodified-original references, all histories and messages, all masks, paired harms and separate body endpoints remain in the frozen results.','',
        '**Scope:** mechanism development on exposed TT028 cases with complete packet replacement. The result supports a strong contribution from spatial reset and a smaller, geometry-dependent body contribution under ablation. It does not establish general correction, serial durability, fresh-population confirmation or an autonomous policy. TT028 primary and joint claims remain NOT_CONFIRMED.','',
        'Before another serial-writing confirmation, the next useful diagnosis is the geometry dependence of the remaining body contribution under uniform reset, using the saved initial states and paired outcomes with all cases and harms retained. No successor or new dynamics has been started.','',
        'The initial excluded benchmark timeout is preserved. A scheduling-only revision passed all 30 qualification checks and verified identical scientific outputs before the full run. The production run completed without a failure. Prior handoff-bound documents are archived in completion_handoff_inputs.','',
        'See [frozen report](runs/reset_v1/REPORT.md), [full summary](runs/reset_v1/SUMMARY.json), [findings](FINDINGS.json), [closeout](CLOSEOUT.json), [protocol](PROTOCOL.md), and [current execution](CURRENT_EXECUTION.json).','']
    (ROOT/'README.md').write_text('\n'.join(lines))
    text=f'''[TT032 spatial reset intervention](TT032/README.md) is **complete and verified**: all 64 exposed blocks, finished {completed['completed_utc']} in {completed['seconds']/3600:.2f} hours. Independent replay checked 615,424 native arrays with zero discrepancies; saved checks covered 784,384 arrays. Retained hashes, all aggregate arithmetic, paired harms and report roundtrip passed final review.

Own-body original-message credit was 73.6542%, 34.4696%, 25.0061% in the common family and 77.7893%, 31.4514%, 25.0000% in the residual family for corrected, uniform and reversed resets respectively, against 25% balanced preserved replaced-packet credit. Neutral reset/opposite-template tracking was 99.987793%; uniform neutral average template credit is a scoring identity. Under uniform reset, own-minus-foreign gains were +6.1462 and +6.6711 percentage points, with all paired harms retained. The residual uniform own-body average conceals 100.0000%, 2.8076% and 11.4990% credit for positive-half, negative-half and mixed surviving geometry. The mixed-mask mean receives weight two in the four-mask average. Residual uniform rewriting also reduces the body endpoint by 11.5845 points relative to preservation despite its +6.4514-point recipient gain.

This supports a major reset contribution and a smaller geometry-dependent body contribution on the exposed cohort. It does not establish general correction or serial durability. TT028 primary/joint remain NOT_CONFIRMED. No successor has started. See [findings](TT032/FINDINGS.json), [closeout](TT032/CLOSEOUT.json) and the [frozen report](TT032/runs/reset_v1/REPORT.md).'''
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):append(LANE/name,text)
    intake=read_json(LANE/'prediction_intake_status.json');intake['spatial_reset_intervention']=status
    (LANE/'prediction_intake_status.json').write_bytes(serialized(intake))
    with (LANE/'exposure_register.jsonl').open('a') as f:f.write(json.dumps(dict(study='TT032',event='completed_reset_intervention_reviewed',recorded_utc=now(),
        first_effect_review_utc=findings['recorded_utc'],source_population_exposed=True,production_effects_inspected=True,
        freeze_sha256=sha(ROOT/'FREEZE.json'),fresh_population_confirmation=False,new_dynamics=0,successor_started=False),sort_keys=True)+'\n')
    previous=read_json(LANE/'TT031/CURRENT_EXECUTION.json');previous.update(updated_utc=now(),successor_status=status['status'])
    (LANE/'TT031/CURRENT_EXECUTION.json').write_bytes(serialized(previous))
    append(LANE/'TT031/README.md','The authorized [TT032 reset intervention](../TT032/README.md) is now complete and verified. It finds a large spatial-reset effect and a smaller, strongly geometry-dependent body contribution under uniform reset. TT031 frozen results and the archived prior handoff remain unchanged.')
    paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl','TT031/README.md','TT031/CURRENT_EXECUTION.json')]
    paths += [ROOT/n for n in ('README.md','CURRENT_EXECUTION.json','FINDINGS.json','CLOSEOUT.json','FREEZE.json','PROTOCOL.md',
        'checks/completion_v1/COMPLETE.json','completion_handoff_inputs/MANIFEST.json','runs/reset_v1/COMPLETE.json','runs/reset_v1/REPORT.md',
        'runs/reset_v1/SUMMARY.json','admin/complete.py')]
    verify(frozen['inputs']);verify(frozen['evidence'])
    write_json(ROOT/'COMPLETION_HANDOFF.json',dict(status='PASS',recorded_utc=now(),files={str(p):sha(p) for p in paths},
        prior_bound_documents_archived=True,frozen_inputs_unchanged=True,new_dynamics=0,successor_started=False))
    signal.alarm(0)
    print(dict(status='COMPLETE_VERIFIED',seconds=time.monotonic()-tick,aggregate_cells_checked=cells,retained_files_verified=len(completed['outputs']),
        completed_utc=completed['completed_utc'],run_hours=completed['seconds']/3600,successor_started=False),flush=True)


if __name__=='__main__':main()
