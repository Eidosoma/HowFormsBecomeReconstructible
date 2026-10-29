"""Boundary-only first-eligible selection and complete-cohort future barrier."""
from pathlib import Path
from sr_common import ROOT,P,np,native,ev,read,write,sha,digest,binding,stamp
import sr_acquire


def select_block(rows):
    selected=[]
    for history_class in (0,1):
        pool=sorted([r for r in rows if r['current_pass']==history_class],key=lambda r:r['selection_hash'])
        by_rule=[[r for r in pool if r['rule']==rule] for rule in (-1,1)]
        selected.extend([r[0] for r in by_rule] if all(by_rule) else pool[:2])
    eligible=len(selected)==4 and all(sum(r['current_pass']==h for r in selected)==2 for h in (0,1))
    return selected if eligible else []


def select_panel(attempts):
    ids=sorted(attempts)
    if ids!=list(range(len(ids))) or len(ids)%P['cohort']['wave_size'] or len(ids)>P['cohort']['maximum_attempts']:raise ValueError('Complete ordered8-block acquisition waves required')
    chosen={b:select_block(attempts[b]) for b in ids}
    eligible=[b for b in ids if chosen[b]]
    blocks=eligible[:P['cohort']['eligible_blocks']]
    return dict(complete=len(blocks)==P['cohort']['eligible_blocks'],attempted_blocks=ids,eligible_blocks=eligible,
                ineligible_blocks=[b for b in ids if b not in eligible],surplus_blocks=eligible[P['cohort']['eligible_blocks']:],
                blocks=blocks,rows=[r for b in blocks for r in chosen[b]])


def verify_selection(attempts,panel):
    # Separate scalar reconstruction of the rule and ordered selection.
    eligible=[];groups={}
    for block in sorted(attempts):
        selected=[]
        for label in [0,1]:
            group=[r for r in attempts[block] if r['current_pass']==label]
            left=sorted((r for r in group if r['rule']==-1),key=lambda r:r['selection_hash'])
            right=sorted((r for r in group if r['rule']==1),key=lambda r:r['selection_hash'])
            if left and right:selected.extend([left[0],right[0]])
            else:selected.extend(sorted(group,key=lambda r:r['selection_hash'])[:2])
        if len(selected)==4 and [sum(r['current_pass']==h for r in selected) for h in [0,1]]==[2,2]:
            eligible.append(block);groups[block]=selected
    wanted=eligible[:P['cohort']['eligible_blocks']]
    if panel['blocks']!=wanted or panel['rows']!=[r for b in wanted for r in groups[b]]:
        raise ArithmeticError('Independent first-eligible selection differs')
    if panel['eligible_blocks']!=eligible or panel['surplus_blocks']!=eligible[P['cohort']['eligible_blocks']:]:raise ArithmeticError('Eligible/surplus accounting differs')
    if panel['ineligible_blocks']!=[b for b in sorted(attempts) if b not in eligible]:raise ArithmeticError('Ineligible accounting differs')
    if panel['attempted_blocks']!=sorted(attempts) or panel['complete']!=(len(wanted)==P['cohort']['eligible_blocks']):raise ArithmeticError('Cohort completeness differs')
    return dict(status='PASS',attempted_blocks=len(attempts),selected_blocks=len(wanted),selected_packets=len(panel['rows']))


def seal_panel(run,attempted):
    run=Path(run)
    if (run/'scientific').exists() or (run/'scientific_SEAL.json').exists():raise ValueError('Future or seal exists before complete cohort')
    attempts={};refs=[]
    for block in attempted:
        folder=run/'acquisition'/f'b{block}'
        rows,receipt=sr_acquire.verify(folder,'scientific',block)
        attempts[block]=rows
        refs.append(dict(block=block,path=str(folder.relative_to(run)),commit_sha256=sha(folder/'COMMIT.json')))
    panel=select_panel(attempts);check=verify_selection(attempts,panel)
    if not panel['complete']:raise ValueError('Full48-block cohort not available; no scientific futures')
    panel.update(binding=binding(),acquisitions=refs,selection_audit=check,utc=stamp())
    write(run/'COHORT.json',panel)
    return panel


def target(block,run):
    run=Path(run);panel=read(run/'COHORT.json')
    if not panel['complete'] or panel['binding']!=binding() or block not in panel['blocks']:raise ValueError('Unsealed/incomplete target source')
    refs=[r for r in panel['acquisitions'] if r['block']==block]
    if len(refs)!=1:raise ValueError('Missing acquisition reference')
    folder=run/refs[0]['path']
    if sha(folder/'COMMIT.json')!=refs[0]['commit_sha256']:raise ValueError('Changed source acquisition')
    full,_=sr_acquire.verify(folder,'scientific',block)
    rows=[r for r in panel['rows'] if r['block']==block]
    if select_block(full)!=rows:raise ValueError('Boundary selection changed')
    commit=read(folder/'COMMIT.json');raw=ev.load(folder/'boundary.npz',commit['sha256']['boundary.npz'])
    histories=sr_acquire.ORIGINAL['acquisition']['histories'];packets=[]
    for row in rows:
        index=(histories.index(row['history']),row['founder'],row['recipient'])
        packet=native.decode(raw['outgoing'][index])
        if digest(packet)!=row['packet_sha256']:raise ValueError('Wrong source packet')
        aligned=raw['mean_ports'][index]*row['rule']*np.array([[1.,-1.],[-1.,1.]])
        if int(aligned.min()>.25)!=row['current_pass']:raise ValueError('Historical class differs')
        if not np.allclose(aligned.ravel(),row['boundary'][:4],rtol=0,atol=1e-12):raise ValueError('Boundary expression differs')
        packets.append(packet)
    if len(rows)!=4:raise ValueError('Four selected packets per target block required')
    return rows,np.stack(packets)


def synthetic(block):
    if block not in P['qualification_blocks']:raise ValueError('Undeclared disposable block')
    packets=[];rows=[]
    for i,(h,rule) in enumerate([(0,1),(0,-1),(1,1),(1,-1)]):
        if i in (0,3):packet=np.zeros((2,16,16),np.float64)
        else:
            field=np.ones((16,16),np.float64)
            field[native.PORTS[1]]=rule;field[native.PORTS[2]]=-rule
            packet=np.stack([.9*field*np.roll(field,-1,axis=axis) for axis in (1,0)])
        rows.append(dict(key=[block,'disposable_guard',i,0],block=block,history='disposable_guard',founder=i,recipient=0,
                         current_pass=h,rule=rule,selection_hash=f'{3-i:064x}',packet_sha256=digest(packet)))
        packets.append(packet)
    return rows,np.stack(packets)


def load(stage,block,run=None):
    if stage=='qualification':return synthetic(block)
    if stage=='scientific' and run is not None:return target(block,run)
    raise ValueError('Unknown or unbound source stage')
