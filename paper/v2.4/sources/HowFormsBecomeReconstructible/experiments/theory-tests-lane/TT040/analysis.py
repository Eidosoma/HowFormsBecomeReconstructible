"""Fixed later body and fresh-recipient endpoints, all cases and paired harms."""
from common import *
import analysis_core as core
import trajectory_analysis
units,stats,views,joint,reverse_stats,weighted=core.units,core.stats,core.views,core.joint,core.reverse_stats,core.weighted
combine_changes=trajectory_analysis.combine_changes

def trajectory(config,rows,bodies):
    levels={r['damage'] for r in rows}|{r['damage'] for r in bodies}
    assert len(levels)==1 and levels<=set(DAMAGE),'damage levels must be reduced separately'
    return trajectory_analysis.trajectory(config,rows,bodies)
combine=core.combine

def report(a,history,changes,role):
    def idx(f,view='all_masks',source='own'):return INDEX['|'.join((f,'all',view,source))]
    def vals(v):return ' / '.join(f'{100*x:.6f}' for x in v)
    def counts(v):return ' / '.join(str(int(x)) for x in v)
    lines=['# TT040: packet-damage timing development','',
        f'Role: {role}. Exposed source states and matched fresh receiving conditions. All four schedules run to 1900 with writing off after 1000. Body and packet scores are separate fractional original-target recognition credits.',
        'This is descriptive development. Damage mixtures are kept separate. Half mixing is an amplitude weight, not a fraction of information erased. No significance verdict or confirmation claim.','',
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
    lines+=['','SUMMARY.npz retains the fixed 1900 endpoint. Earlier checkpoint summaries and BODY_CHANGE_SUMMARY.npz retain trajectories and within-arm changes. All preserve block values, equal nonempty-block and pooled-record estimates, all strata, four credits, paired gains/harms/ties and joint tables. Body counts are never multiplied by receiving draws.',
        'Every new body and recipient trajectory is independently replayed. Source states are restored from the completed, hash-bound TT039 evidence; source dynamics are not claimed as new. The packets at all follow-up checkpoints equal their update-1000 bytes, so their new recipient outcomes remain identical across body checkpoints. A mean benefit does not establish individual benefit, optimal timing, uninterrupted performance, indefinite stability, independent teaching cues, damage-level robustness or serial heredity. TT028 primary/joint and TT036/TT039 confirmation classifications remain unchanged. A zero observed loss does not establish harmlessness or noninferiority.','']
    return '\n'.join(lines)

def report_all(finals,histories,changes,role):
    lines=['# TT040: informative and damaged incoming records','',
        'Primary descriptive contrast: mix050, residual own source, all masks, late minus preservation. The intact and fully replaced panels remain separate. All four exposed development blocks are fixed by identity, with one corruption realization and four fresh receiving conditions per block. No hypothesis test or automatic policy selection.','']
    for damage in DAMAGE:
        a=finals[damage]
        lines+=['## '+damage+' (noise mixture weight '+str(MIX[damage])+')','',
            report(a,histories[damage],changes[damage],role).replace('# TT040: packet-damage timing development','')]
        lines+=['| Family | Unmodified-original recipient credit (%) |','|---|---:|']
        for family in FAMILIES:
            j=INDEX[family+'|all|all_masks|own']
            lines.append(f"| {family} | {100*a['original_levels_equal_block'][j,0]:.6f} |")
        lines+=['','Residual own-source all-mask block values:','',
            '| Block | Late minus preservation body (pp) | Fresh recipient (pp) |','|---:|---:|---:|']
        j=INDEX['residual|all|all_masks|own']
        for n,index in enumerate(selected(role)):
            lines.append(f"| {index} | {100*a['body_stats_block_means'][n,j,1,0]:+.6f} | {100*a['recipient_stats_block_means'][n,j,1,0]:+.6f} |")
        lines.append('')
    lines += ['The same receiving environment is paired across all three packet mixtures, schedules, families, masks and body sources within a draw. There are 16 new receiving conditions in development, not 48. Damage panels are dependent. Intact preservation and the original share one physical read because packet bytes and recipient addresses are identical. Four receiving conditions give coarse individual estimates; one corruption realization does not characterize its distribution. No automatic extension or successor.','']
    return '\n'.join(lines)

def summary(directory,role):
    indices=selected(role);proof={};finals={};histories={};changes={}
    for i in indices:
        receipt=read(directory/f'tissue_{i}'/'COMPLETE.json');assert receipt['status']=='PASS';verify(receipt['outputs'])
        for k,v in receipt['verification'].items():proof[k]=proof.get(k,0)+v
    original_reference=None
    for damage in DAMAGE:
        dest=directory/('summary_'+damage);dest.mkdir()
        history={'body_levels_equal_block':[]};packet_reference=None
        for t in SNAPSHOTS:
            a=combine([arrays(directory/f'tissue_{i}'/f'AGGREGATE_{damage}_{t}.npz') for i in indices])
            history['body_levels_equal_block'].append(a['body_levels_equal_block'])
            fields={k:v for k,v in a.items() if k.startswith(('recipient_','original_'))}
            if packet_reference is None:packet_reference=fields
            else:
                for k in fields:exact(fields[k],packet_reference[k],'same packet at each body time '+k)
            save(dest/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'),a)
        orig={k:v for k,v in a.items() if k.startswith('original_')}
        if original_reference is None:original_reference=orig
        else:
            for k in orig:exact(orig[k],original_reference[k],'original across damage levels '+k)
        if damage=='mix000':
            for suffix in ('equal_block','pooled_record','block_means'):
                exact(a['recipient_levels_'+suffix][...,0,:],a['original_levels_'+suffix],'intact preservation identity')
        history={k:np.stack(v) for k,v in history.items()};save(dest/'TRAJECTORY_LEVELS.npz',history)
        change=combine_changes([arrays(directory/f'tissue_{i}'/f'BODY_CHANGE_{damage}.npz') for i in indices])
        save(dest/'BODY_CHANGE_SUMMARY.npz',change);finals[damage]=a;histories[damage]=history;changes[damage]=change
    metadata=dict(study='TT040',role=role,blocks=indices,damage_levels=DAMAGE,mixture_weights=MIX,
        conditions=CONDITIONS,source_contrasts=SOURCE_CONTRASTS,arms=ARMS,original_writing_budgets=BUDGETS,
        original_writing_windows=WINDOWS,body_checkpoints=SNAPSHOTS,body_endpoint=END,recipient_endpoint=1000,
        followup_start=START,credits=CREDITS,comparisons=COMPARISONS,stat_fields=STAT_FIELDS,
        joint_resolution=['fixed_output_mean','record_mean'],joint_body_sign=SIGNS,joint_recipient_sign=SIGNS,
        within_arm_contrast='body_1900_minus_1000',
        primary='mix050; residual|all|all_masks|own; late_minus_preserve; target; body at 1900 and fresh recipient; descriptive',
        verification=proof,source_population_reused=role=='development',source_population_exposed=role=='development',
        recipient_evidence_inherited=False,confirmatory=False,
        new_receiving_assays=proof['new_receiving_assays'],new_independent_receiving_draws=proof['new_independent_receiving_draws'])
    write(directory/'METADATA.json',metadata)
    with (directory/'REPORT.md').open('x') as f:f.write(report_all(finals,histories,changes,role))
    restored={d:arrays(directory/('summary_'+d)/'SUMMARY.npz') for d in DAMAGE}
    rh={d:arrays(directory/('summary_'+d)/'TRAJECTORY_LEVELS.npz') for d in DAMAGE}
    rc={d:arrays(directory/('summary_'+d)/'BODY_CHANGE_SUMMARY.npz') for d in DAMAGE}
    assert report_all(restored,rh,rc,role)==(directory/'REPORT.md').read_text()
    return proof
