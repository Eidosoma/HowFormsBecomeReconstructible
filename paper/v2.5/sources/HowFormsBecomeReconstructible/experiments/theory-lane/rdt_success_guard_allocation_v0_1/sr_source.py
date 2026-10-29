"""Verified exposed boundary packets; no new acquisition or outcome selection."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from sr_common import ROOT,P,np,native,ev,read,sha,digest,byte_equal


def panel():
    path=ROOT/'context/SOURCE_PANEL.json'
    if sha(path)!=P['source_panel_sha256']:raise ValueError('Source panel commitment differs')
    source=read(path);prior=read(ROOT/'context/previous_COHORT.json');complete=read(ROOT/'context/previous_COMPLETE.json')
    if sha(ROOT/'context/previous_COHORT.json')!=source['source_cohort_sha256'] or complete['cohort_sha256']!=source['source_cohort_sha256']:
        raise ValueError('Original cohort binding differs')
    if complete['inputs_sha256']!=source['source_input_manifest_sha256'] or complete['output_manifest_sha256']!=source['source_output_manifest_sha256']:
        raise ValueError('Original completion binding differs')
    ranked=sorted(prior['blocks'],key=lambda b:hashlib.sha256(json.dumps([P['namespace'],'source_block_selection',b],separators=(',',':')).encode()).hexdigest())
    blocks=sorted(ranked[:P['source_selected_blocks']])
    if blocks!=P['target_blocks'] or blocks!=source['blocks'] or source['hash_ranked_blocks']!=ranked:
        raise ValueError('Outcome-free block selection changed')
    expected=[r for b in blocks for r in prior['rows'] if r['block']==b]
    if source['rows']!=expected:raise ValueError('Original boundary rows changed')
    raw=ev.load(ROOT/'context/source_packets.npz',source['raw_sha256'])
    if raw['blocks'].tolist()!=blocks or raw['packets'].shape!=(21,4,2,16,16):raise ValueError('Boundary array coverage differs')
    if raw['packets'].dtype!=np.float64 or not np.isfinite(raw['packets']).all():raise ValueError('Finite binary64 boundary packets required')
    for i,b in enumerate(blocks):
        rows=[r for r in source['rows'] if r['block']==b]
        if len(rows)!=4 or [sum(r['current_pass']==h for r in rows) for h in (0,1)]!=[2,2]:raise ValueError('Original class balance differs')
        for j,r in enumerate(rows):
            if digest(raw['packets'][i,j])!=r['packet_sha256']:raise ValueError('Original packet bytes differ')
    return source,raw['packets']


def synthetic(block):
    if block not in P['qualification_blocks']:raise ValueError('Undeclared disposable block')
    packets=[];rows=[]
    for i,(h,rule) in enumerate([(0,1),(0,-1),(1,1),(1,-1)]):
        if i in (0,3):packet=np.zeros((2,16,16),np.float64)
        else:
            field=np.ones((16,16),np.float64)
            field[native.PORTS[1]]=rule;field[native.PORTS[2]]=-rule
            packet=np.stack([.9*field*np.roll(field,-1,axis=axis) for axis in (1,0)])
        rows.append(dict(key=[block,'disposable_allocation',i,0],block=block,history='disposable_allocation',founder=i,recipient=0,
                         current_pass=h,rule=rule,selection_hash=f'{3-i:064x}',packet_sha256=digest(packet)))
        packets.append(packet)
    return rows,np.stack(packets)


def load(stage,block,run=None):
    if stage=='qualification':return synthetic(block)
    if stage!='development' or block not in P['target_blocks']:raise ValueError('Undeclared source block')
    source,packets=panel();index=source['blocks'].index(block)
    return deepcopy([r for r in source['rows'] if r['block']==block]),packets[index].copy()
