"""Fixed-time body follow-up, within-arm changes and inherited packet evidence."""
from common import *
import analysis_core as core
units,stats,views,joint,reverse_stats,weighted=core.units,core.stats,core.views,core.joint,core.reverse_stats,core.weighted

def trajectory(config,rows,trajectories):
    aggregates=[]
    for t in SNAPSHOTS:
        bodies=[]
        for r in trajectories:
            assert set(r['body_by_time'])==set(map(str,SNAPSHOTS))
            assert set(r['body_by_time'][str(t)])==set(BODY_FIELDS)
            bodies.append({k:v for k,v in r.items() if k!='body_by_time'}|r['body_by_time'][str(t)])
        aggregates.append(core.block(config,rows,bodies))
    for a in aggregates[1:]:
        for k in ('records','source_records','original_levels','recipient_levels','recipient_stats','recipient_source_stats'):
            exact(a[k],aggregates[0][k],'held packet aggregate '+k)
    cc=config['corruptions'];families=config['families']
    cells={f:dict(delta=np.zeros((cc,1,16,4,3,4,4)),history=np.full(16,np.nan)) for f in families}
    seen=set()
    for r in trajectories:
        f,c,w,m,o=r['family'],r['corruption'],r['world'],MASKS.index(r['mask']),SOURCES.index(r['body_source'])
        key=(f,c,w,m,o);assert key not in seen;seen.add(key)
        first=np.stack([units(r['body_by_time'][str(START)][field]) for field in BODY_FIELDS])
        last=np.stack([units(r['body_by_time'][str(END)][field]) for field in BODY_FIELDS])
        cells[f]['delta'][c,0,w,m,o]=last-first
        old=cells[f]['history'][w];assert np.isnan(old) or old==r['developed_score']
        cells[f]['history'][w]=r['developed_score']
    assert len(seen)==cc*len(families)*16*4*3
    out=dict(records=np.zeros(len(CONDITIONS),dtype=np.int32),stats=np.zeros((len(CONDITIONS),4,4,10)))
    out['stats'][...,0]=np.nan
    for f,cell in cells.items():
        assert np.isfinite(cell['history']).all()
        vv=views(cell['delta'])
        groups={'all':np.ones(16,dtype=bool),'history:unique_pass':cell['history']==1.,'history:other':cell['history']!=1.}
        groups.update({f'message:{m}':np.arange(16)//4==m for m in range(4)})
        for group,keep in groups.items():
            if not keep.any():continue
            for view in VIEWS:
                value=vv[view][:,:,keep]
                for oi,source in enumerate(SOURCES):
                    j=INDEX['|'.join((f,group,view,source))];out['records'][j]=int(keep.sum())
                    for arm in range(4):out['stats'][j,arm]=stats(value[:,:,:,oi,arm])
    exact(out['records'],aggregates[0]['records'])
    near(out['stats'][...,0],aggregates[-1]['body_levels']-aggregates[0]['body_levels'])
    return aggregates,out

def combine_changes(blocks):
    counts=np.stack([b['records'] for b in blocks]);v=np.stack([b['stats'] for b in blocks])
    equal,pooled=weighted(v[...,0],counts)
    return dict(block_records=counts,records=counts.sum(0),block_means=v[...,0],counts=v[...,1:].sum(0),
        equal_block=equal,pooled_record=pooled)

def report(a,history,changes):
    def idx(f,view='all_masks',source='own'):return INDEX['|'.join((f,'all',view,source))]
    def vals(v):return ' / '.join(f'{100*x:.6f}' for x in v)
    def counts(v):return ' / '.join(str(int(x)) for x in v)
    lines=['# TT038: body follow-up after writing ends','',
        'All arms resume exact time-1000 states and original matched forcing. No arm writes after 1000. The primary body endpoint is 1900; packets and their matched recipient outcomes are inherited from TT037. Every score is fractional original-target recognition credit.','',
        '| Family | Body time | Own-body credit: preserve / early / late / full-then-hold (%) | Late minus preservation body (pp) |',
        '|---|---:|---:|---:|']
    for f in FAMILIES:
        j=idx(f)
        if not a['records'][j]:continue
        for ti,t in enumerate(SNAPSHOTS):
            levels=history['body_levels_equal_block'][ti,j,:,0]
            lines.append(f'| {f} | {t} | {vals(levels)} | {100*(levels[2]-levels[0]):+.6f} |')
    lines+=['','| Family | Own-body geometry | Body at 1900: late minus preservation (pp) | Record gains / harms / ties | Body at 1900: early minus late (pp) |',
        '|---|---|---:|---:|---:|']
    for f in FAMILIES:
        for view in ('all_masks',)+tuple('geometry:'+g for g in GEOMETRIES):
            j=idx(f,view)
            if a['records'][j]:lines.append(f"| {f} | {view} | {100*a['body_stats_equal_block'][j,1,0]:+.6f} | {counts(a['body_stats_counts'][j,1,0,6:9])} | {100*a['body_stats_equal_block'][j,0,0]:+.6f} |")
    lines+=['','| Family | Own-source arm | Within-body change 1900 minus 1000 (pp) | Record gains / harms / ties |','|---|---|---:|---:|']
    for f in FAMILIES:
        j=idx(f)
        if a['records'][j]:
            for arm,name in enumerate(ARMS):lines.append(f"| {f} | {name} | {100*changes['equal_block'][j,arm,0]:+.6f} | {counts(changes['counts'][j,arm,0,6:9])} |")
    lines+=['','| Family | Source | Body at 1900: late minus preservation (pp) | Inherited packet: late minus preservation (pp) |',
        '|---|---|---:|---:|']
    for f in FAMILIES:
        for owner in SOURCES:
            j=idx(f,source=owner)
            if a['records'][j]:lines.append(f"| {f} | {owner} | {100*a['body_stats_equal_block'][j,1,0]:+.6f} | {100*a['recipient_stats_equal_block'][j,1,0]:+.6f} |")
    j=idx('residual')
    if a['records'][j]:
        lines+=['','Primary late-minus-preservation joint record-mean counts; body at 1900, packet evidence inherited:',
            '| Body change | Packet harms | Packet ties | Packet gains |','|---|---:|---:|---:|']
        tab=a['joint_counts'][j,1,0,1]
        for bi,label in enumerate(SIGNS):lines.append(f'| {label} | {tab[bi,0]} | {tab[bi,1]} | {tab[bi,2]} |')
    lines+=['','SUMMARY.npz contains the fixed 1900 endpoint; CHECKPOINT_SUMMARY files retain earlier checkpoints. BODY_CHANGE_SUMMARY.npz retains paired within-arm 1900-minus-1000 changes. All summaries keep equal-block and pooled-record means, individual blocks, all strata, four credits, all gains/harms/ties and joint body/packet tables. Repeated receiving draws never multiply body counts.',
        'Every time-1000 aggregate exactly reproduces TT037. Every packet aggregate is unchanged at every time. Every new continuation is independently replayed; all packet bytes are held at every update. No fresh population or recipient evidence is acquired. The horizon is fixed at 1900 and does not establish indefinite stability, uninterrupted performance between checkpoints, equivalence, optimal timing, serial heredity or damage-level generalization. TT028 primary/joint and TT036 confirmation classifications are unchanged.','']
    return '\n'.join(lines)

def summary(directory,role):
    indices=selected(role);proof={}
    for i in indices:
        receipt=read(directory/f'tissue_{i}'/'COMPLETE.json');assert receipt['status']=='PASS';verify(receipt['outputs'])
        for k,v in receipt['verification'].items():proof[k]=proof.get(k,0)+v
    history={'body_levels_equal_block':[]}
    for t in SNAPSHOTS:
        values=[arrays(directory/f'tissue_{i}'/f'AGGREGATE_{t}.npz') for i in indices]
        a=core.combine(values);history['body_levels_equal_block'].append(a['body_levels_equal_block'])
        save(directory/('SUMMARY.npz' if t==END else f'CHECKPOINT_SUMMARY_{t}.npz'),a)
    history={k:np.stack(v) for k,v in history.items()};save(directory/'TRAJECTORY_LEVELS.npz',history)
    changes=combine_changes([arrays(directory/f'tissue_{i}'/'BODY_CHANGE.npz') for i in indices])
    save(directory/'BODY_CHANGE_SUMMARY.npz',changes)
    metadata=dict(study='TT038',role=role,blocks=indices,conditions=CONDITIONS,source_contrasts=SOURCE_CONTRASTS,
        arms=ARMS,original_writing_budgets=BUDGETS,original_writing_windows=WINDOWS,body_checkpoints=SNAPSHOTS,
        body_endpoint=END,followup_start=START,credits=CREDITS,comparisons=COMPARISONS,stat_fields=STAT_FIELDS,
        joint_resolution=['fixed_output_mean','record_mean'],joint_body_sign=SIGNS,joint_recipient_sign=SIGNS,
        within_arm_contrast='body_1900_minus_1000',primary='residual|all|all_masks|own; late_minus_preserve; body at 1900; target; descriptive',
        verification=proof,source_population_exposed=True,recipient_evidence_inherited=True,new_receiving_assays=0,new_independent_receiving_draws=0)
    write(directory/'METADATA.json',metadata)
    with (directory/'REPORT.md').open('x') as f:f.write(report(a,history,changes))
    assert report(arrays(directory/'SUMMARY.npz'),arrays(directory/'TRAJECTORY_LEVELS.npz'),arrays(directory/'BODY_CHANGE_SUMMARY.npz'))==(directory/'REPORT.md').read_text()
    return proof
