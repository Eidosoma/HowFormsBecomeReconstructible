"""Fixed later body and fresh-recipient endpoints, all cases and paired harms."""
from common import *
import analysis_core as core
import trajectory_analysis,inference
units,stats,views,joint,reverse_stats,weighted=core.units,core.stats,core.views,core.joint,core.reverse_stats,core.weighted
trajectory,combine_changes=trajectory_analysis.trajectory,trajectory_analysis.combine_changes
combine=core.combine

def report(a,history,changes,role):
    def idx(f,view='all_masks',source='own'):return INDEX['|'.join((f,'all',view,source))]
    def vals(v):return ' / '.join(f'{100*x:.6f}' for x in v)
    def counts(v):return ' / '.join(str(int(x)) for x in v)
    lines=['# TT039: fresh confirmation of late writing','',
        f'Role: {role}. Freshly generated source states and matched fresh receiving conditions. All four schedules run to 1900 with writing off after 1000. Body and packet scores are separate fractional original-target recognition credits.',
        'Only the confirmation cohort supplies confirmation evidence; excluded qualification and benchmark results do not.','',
        '| Family | Body time | Own-body credit: preserve / early / late / full-then-hold (%) | Late minus preservation body (pp) |',
        '|---|---:|---:|---:|']
    for f in FAMILIES:
        j=idx(f)
        if not a['records'][j]:continue
        for ti,t in enumerate(SNAPSHOTS):
            levels=history['body_levels_equal_block'][ti,j,:,0]
            lines.append(f'| {f} | {t} | {vals(levels)} | {100*(levels[2]-levels[0]):+.6f} |')
    lines+=['','| Family | Own-source packet credit: preserve / early / late / full-then-hold (%) |','|---|---:|']
    for f in FAMILIES:
        j=idx(f)
        if a['records'][j]:lines.append(f"| {f} | {vals(a['recipient_levels_equal_block'][j,:,0])} |")
    lines+=['','| Family | Own-body geometry | Body at 1900: late minus preservation (pp) | Body record gains / harms / ties | Packet late minus preservation (pp) | Packet record gains / harms / ties |',
        '|---|---|---:|---:|---:|---:|']
    for f in FAMILIES:
        for view in ('all_masks',)+tuple('geometry:'+g for g in GEOMETRIES):
            j=idx(f,view)
            if a['records'][j]:lines.append(f"| {f} | {view} | {100*a['body_stats_equal_block'][j,1,0]:+.6f} | {counts(a['body_stats_counts'][j,1,0,6:9])} | {100*a['recipient_stats_equal_block'][j,1,0]:+.6f} | {counts(a['recipient_stats_counts'][j,1,0,6:9])} |")
    lines+=['','| Family | Source | Comparison | Body at 1900 (pp) | Fresh-recipient packet (pp) |','|---|---|---|---:|---:|']
    for f in FAMILIES:
        for source in SOURCES:
            j=idx(f,source=source)
            if a['records'][j]:
                for ti,name in enumerate(COMPARISONS):lines.append(f"| {f} | {source} | {name} | {100*a['body_stats_equal_block'][j,ti,0]:+.6f} | {100*a['recipient_stats_equal_block'][j,ti,0]:+.6f} |")
    lines+=['','| Family | Own-source arm | Within-body change 1900 minus 1000 (pp) | Record gains / harms / ties |','|---|---|---:|---:|']
    for f in FAMILIES:
        j=idx(f)
        if a['records'][j]:
            for arm,name in enumerate(ARMS):lines.append(f"| {f} | {name} | {100*changes['equal_block'][j,arm,0]:+.6f} | {counts(changes['counts'][j,arm,0,6:9])} |")
    j=idx('residual')
    if a['records'][j]:
        lines+=['','Primary late-minus-preservation joint record-mean counts; body at 1900, fresh-recipient packet:',
            '| Body change | Packet harms | Packet ties | Packet gains |','|---|---:|---:|---:|']
        tab=a['joint_counts'][j,1,0,1]
        for bi,label in enumerate(SIGNS):lines.append(f'| {label} | {tab[bi,0]} | {tab[bi,1]} | {tab[bi,2]} |')
    if role=='confirmation':
        result=inference.results(a)
        lines+=['',f"Frozen joint decision: **{result['joint_classification']}**."]
        for endpoint,row in result['endpoints'].items():
            ci=row['interval'];lines.append(f"{endpoint}: mean {100*ci['mean']:+.6f} pp; one-sided alpha .025 lower bound {100*ci['lower_one_sided']:+.6f} pp; {row['classification']}.")
        lines+=['Bonferroni across the two co-primary outcomes; approximate paired-block Student-t coverage, zero-variance Hoeffding fallback, margin zero. CONFIRMATION.json retains both intervals and bounded sensitivities. Secondary panels cannot rescue the decision.']
    lines+=['','SUMMARY.npz retains the fixed 1900 endpoint. Earlier checkpoint summaries and BODY_CHANGE_SUMMARY.npz retain trajectories and within-arm changes. All preserve block values, equal nonempty-block and pooled-record estimates, all strata, four credits, paired gains/harms/ties and joint tables. Body counts are never multiplied by receiving draws.',
        'Every new source, body and recipient trajectory is independently replayed. The packets at all follow-up checkpoints equal their update-1000 bytes, so their new recipient outcomes remain identical across body checkpoints. A mean benefit does not establish individual benefit, optimal timing, uninterrupted performance, indefinite stability, independent teaching cues, damage-level robustness or serial heredity. TT028 primary/joint and TT036 confirmation classifications remain unchanged.','']
    return '\n'.join(lines)

def summary(directory,role):
    indices=selected(role);proof={}
    for i in indices:
        receipt=read(directory/f'tissue_{i}'/'COMPLETE.json');assert receipt['status']=='PASS';verify(receipt['outputs'])
        for k,v in receipt['verification'].items():proof[k]=proof.get(k,0)+v
    history={'body_levels_equal_block':[]};packet_reference=None
    for t in SNAPSHOTS:
        a=core.combine([arrays(directory/f'tissue_{i}'/f'AGGREGATE_{t}.npz') for i in indices])
        history['body_levels_equal_block'].append(a['body_levels_equal_block'])
        fields={k:v for k,v in a.items() if k.startswith(('recipient_','original_'))}
        if packet_reference is None:packet_reference=fields
        else:
            for k in fields:exact(fields[k],packet_reference[k],'same packets across body checkpoints '+k)
        save(directory/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'),a)
    history={k:np.stack(v) for k,v in history.items()};save(directory/'TRAJECTORY_LEVELS.npz',history)
    changes=combine_changes([arrays(directory/f'tissue_{i}'/'BODY_CHANGE.npz') for i in indices]);save(directory/'BODY_CHANGE_SUMMARY.npz',changes)
    metadata=dict(study='TT039',role=role,blocks=indices,conditions=CONDITIONS,source_contrasts=SOURCE_CONTRASTS,
        arms=ARMS,original_writing_budgets=BUDGETS,original_writing_windows=WINDOWS,body_checkpoints=SNAPSHOTS,
        body_endpoint=END,recipient_endpoint=1000,followup_start=START,credits=CREDITS,comparisons=COMPARISONS,stat_fields=STAT_FIELDS,
        joint_resolution=['fixed_output_mean','record_mean'],joint_body_sign=SIGNS,joint_recipient_sign=SIGNS,
        within_arm_contrast='body_1900_minus_1000',primary='residual|all|all_masks|own; late_minus_preserve; target; body at 1900 and fresh recipient co-primary',
        verification=proof,source_population_reused=False,source_population_exposed=role!='confirmation',recipient_evidence_inherited=False,
        new_receiving_assays=proof['new_receiving_assays'],new_independent_receiving_draws=proof['new_independent_receiving_draws'])
    write(directory/'METADATA.json',metadata)
    if role=='confirmation':write(directory/'CONFIRMATION.json',inference.results(a))
    with (directory/'REPORT.md').open('x') as f:f.write(report(a,history,changes,role))
    assert report(arrays(directory/'SUMMARY.npz'),arrays(directory/'TRAJECTORY_LEVELS.npz'),arrays(directory/'BODY_CHANGE_SUMMARY.npz'),role)==(directory/'REPORT.md').read_text()
    return proof
