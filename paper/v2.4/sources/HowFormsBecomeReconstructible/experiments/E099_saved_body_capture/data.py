"""Pinned saved sources, unchanged historical endpoints and complete exports."""
import csv
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump,sha,utc
from E083_reader_repeatability.data import save,load,equal
from E099_saved_body_capture.plan import (HERE,ROOT,PARENT,BLOCKS,TECHNICAL,STARTS,OLD,
    METRICS,CONTRASTS,INTERACTIONS,settings,identity)

IDENTIFIERS=('task','arm','kind','history','founder','recipient','draw','old_E098_draw')


def register():
    target=HERE/'SOURCE_DATA.json'; assert not target.exists()
    close=PARENT/'analysis/closeout_v1.json'; c=json.loads(close.read_text()); assert c['status']=='PASS'
    modes={}; receipts={str(close.relative_to(ROOT)):sha(close)}
    for mode,name,blocks in (('benchmark','benchmark_v1',TECHNICAL),('scientific','confirmation_v1',BLOCKS)):
        run=PARENT/'runs'/name; complete=json.loads((run/'COMPLETE.json').read_text())
        assert complete['status']=='COMPLETE' and complete['controls_pass']
        assert json.loads((run/'manifest.json').read_text())['contract']['blocks']==list(blocks)
        if mode=='scientific': assert c['complete_sha256']==sha(run/'COMPLETE.json')
        names=[f'{tag}_{b:06d}.npz' for b in blocks for tag in ('writer','source_pruning')]
        names += [f'scores_{b:06d}_r{d}.npz' for b in blocks for d in (0,1)]
        names += ['summary.json']
        if mode=='benchmark': names += ['assay_9000980_r0.npz','terminal_packets_9000980.npz']
        hashes={}
        for n in names:
            h=sha(run/n); assert h==complete['outputs_sha256'][n],n; hashes[n]=h
        modes[mode]=dict(path=str(run.relative_to(ROOT)),blocks=list(blocks),files=hashes)
        for n in ('COMPLETE.json','CHECKS.json','manifest.json'):
            receipts[str((run/n).relative_to(ROOT))]=sha(run/n)
    dump(target,dict(utc=utc(),sources=modes,receipts=receipts,scientific_blocks=list(BLOCKS),
        excluded=list(TECHNICAL),old_outcomes_known=True,source_selection=False,new_source_blocks=0,
        new_terminal_outcomes_seen=False,prediction='P-ind H minus O positive AND P-ind H minus P-pair H positive'))


def verify_registry():
    r=json.loads((HERE/'SOURCE_DATA.json').read_text()); assert r['scientific_blocks']==list(BLOCKS)
    for path,h in r['receipts'].items(): assert sha(ROOT/path)==h,path
    return r


def pinned(mode,name,copy_to=None):
    source=verify_registry()['sources']['scientific' if mode=='scientific' else 'benchmark']
    raw=(ROOT/source['path']/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==source['files'][name],name
    if copy_to is not None:
        with Path(copy_to).open('xb') as f: f.write(raw)
    if name.endswith('.json'): return json.loads(raw)
    with np.load(io.BytesIO(raw),allow_pickle=False) as z: result={k:z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in result.values()); return result


def source(mode,task,run=None):
    assert task in settings(mode)['blocks']
    def get(name,local): return pinned(mode,name,run/local if run is not None else None)
    writer=get(f'writer_{task:06d}.npz',f'source_writer_{task:06d}.npz')
    pruning=get(f'source_pruning_{task:06d}.npz',f'source_pruning_{task:06d}.npz')
    old={d:get(f'scores_{task:06d}_r{d}.npz',f'old_scores_{task:06d}_r{d}.npz') for d in (0,1)}
    assert writer['incoming'][:9].tobytes()==pruning['packets'].tobytes()
    assert writer['incoming'][9:].tobytes()==pruning['packets'].tobytes()
    return writer,pruning,old


def add_scores(row,prefix,scores,loc):
    for k in METRICS: row[prefix+'_'+k]=float(scores[k][loc])
    for c in (0,1): row[prefix+f'_cue{c}_margin']=float(scores['margin'][loc+(c,)])
    for k in ('correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign','opposite_rule_success'):
        row[prefix+'_'+k]=int(scores[k][loc])


def rows(task,draw,cfg,scores,diagnostics,old_scores,writer_end,writer_window):
    out=[]
    for arm,f,r in np.ndindex(4,4,cfg['recipients']):
        row=dict(task=task,arm=arm,kind='native' if arm<2 else 'mixture',history='sham' if arm%2==0 else 'pulse',
                 founder=f,recipient=r,draw=draw,old_E098_draw=draw)
        for name,start in STARTS.items():
            loc=start+arm,f,r; add_scores(row,name,scores,loc)
            for k,v in diagnostics.items(): row[name+'_'+k]=float(v[loc])
        for name,start in OLD.items(): add_scores(row,'old_E098_'+name,old_scores,(start+arm,f,r))
        for name,start in (('I_pair',0),('P_pair',4),('I_ind',9),('P_ind',13)):
            for phase,s in (('end',writer_end),('window',writer_window)):
                add_scores(row,'source_writer_'+name+'_'+phase,s,(start+arm,f,r))
        for name,parts in CONTRASTS.items():
            for k in METRICS: row[name+'_'+k]=sum(coef*row[v+'_'+k] for v,coef in parts.items())
        for k in METRICS:
            assert abs(row['noise_pruned_H_'+k]-row['filter_pruned_'+k]-row['noise_pruned_O_'+k])<2e-15
        out.append(row)
    return out


def erased_rows(task,draw,cfg,scores,diagnostics):
    out=[]
    for name,slot in (('paired_writer',8),('independent_writer',17)):
        for f,r in np.ndindex(4,cfg['recipients']):
            row=dict(task=task,draw=draw,stage=name,founder=f,recipient=r)
            add_scores(row,'erased',scores,(slot,f,r))
            for k,v in diagnostics.items(): row[k]=float(v[slot,f,r])
            out.append(row)
    return out


def export(path,records,fields=None):
    fields=fields or list(records[0])
    with Path(path).open('x',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields); w.writeheader(); w.writerows(records)
    with Path(path).open(newline='') as stream:
        for a,b in zip(records,csv.DictReader(stream),strict=True):
            assert set(a)==set(b)
            for k,v in a.items(): assert b[k]==v if isinstance(v,str) else float(b[k])==v,k


def averages(records):
    groups={}
    for r in records: groups.setdefault(identity(r),[]).append(r)
    out=[]
    for pair in groups.values():
        assert sorted(r['draw'] for r in pair)==[0,1]; row={}
        for key,value in pair[0].items():
            if key in ('draw','old_E098_draw'): continue
            if key in IDENTIFIERS or key.startswith('source_writer_'):
                assert value==pair[1][key]; row[key]=value
            else: row[key]=(value+pair[1][key])/2
        for name in CONTRASTS:
            row[name+'_positive_draws']=sum(r[name+'_both']>0 for r in pair)
            row[name+'_negative_draws']=sum(r[name+'_both']<0 for r in pair)
        out.append(row)
    return out


def events(records):
    scorekeys=[v+'_'+k for v in STARTS for k in METRICS]
    scorekeys += ['old_E098_'+v+'_'+k for v in OLD for k in METRICS]
    fields=list(IDENTIFIERS)+['contrast','effect','event_kind']+scorekeys; out=[]
    for row in records:
        for name in CONTRASTS:
            effect=row[name+'_both']
            if effect==0: continue
            event={k:row[k] for k in IDENTIFIERS}; event.update(contrast=name,effect=effect,
                event_kind='interaction_contrast' if name in INTERACTIONS else 'gain' if effect>0 else 'harm')
            event.update({k:row[k] for k in scorekeys}); out.append(event)
    return out,fields
