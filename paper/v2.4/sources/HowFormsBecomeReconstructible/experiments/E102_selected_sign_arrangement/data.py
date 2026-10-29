"""Pin E101 components, reconstruct provenance and retain all old endpoints."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump,sha,utc
from E083_reader_repeatability.data import save,load,equal
from E099_saved_body_capture.data import add_scores,export
from E099_saved_body_capture import model as capture_model, audit as capture_audit
from E100_saved_record_region_swap import model as region_model, audit as region_audit
from E101_cross_noise_components import model as component_model, audit as component_audit
from E102_selected_sign_arrangement.plan import (HERE,ROOT,PARENT,BLOCKS,TECHNICAL,STARTS,
    OLD098,OLD099,OLD100,OLD101,METRICS,CONTRASTS,settings,identity)

IDENTIFIERS=('task','arm','kind','history','founder','recipient','draw',
    'old_E098_draw','old_E099_draw','old_E100_draw','old_E101_draw')
LEGACY=(('old_E098_',OLD098),('old_E099_',OLD099),('old_E100_',OLD100),('old_E101_',OLD101))


def register():
    target=HERE/'SOURCE_DATA.json'; assert not target.exists()
    close=PARENT/'analysis/closeout_v1.json'; c=json.loads(close.read_text()); assert c['status']=='PASS'
    modes={}; receipts={str(close.relative_to(ROOT)):sha(close)}
    for mode,name,blocks in (('benchmark','benchmark_v1',TECHNICAL),('scientific','components_v1',BLOCKS)):
        run=PARENT/'runs'/name; complete=json.loads((run/'COMPLETE.json').read_text())
        assert complete['status']=='COMPLETE' and complete['controls_pass']
        assert json.loads((run/'manifest.json').read_text())['contract']['blocks']==list(blocks)
        if mode=='scientific': assert c['complete_sha256']==sha(run/'COMPLETE.json')
        names=[f'{tag}_{b:06d}.npz' for b in blocks for tag in
            ('source_writer','source_pruning','source_capture','source_regions','interventions')]
        names += [f'{tag}_{b:06d}_r{d}.npz' for b in blocks for d in (0,1)
                  for tag in ('old_E098_scores','old_E099_scores','old_E100_scores','scores')]
        names += ['summary.json']
        if mode=='benchmark': names += ['assay_9000980_r0.npz']
        hashes={}
        for n in names:
            h=sha(run/n); assert h==complete['outputs_sha256'][n],n; hashes[n]=h
        modes[mode]=dict(path=str(run.relative_to(ROOT)),blocks=list(blocks),files=hashes)
        for n in ('COMPLETE.json','CHECKS.json','manifest.json'):
            receipts[str((run/n).relative_to(ROOT))]=sha(run/n)
    dump(target,dict(utc=utc(),sources=modes,receipts=receipts,scientific_blocks=list(BLOCKS),
        excluded=list(TECHNICAL),old_outcomes_known=True,source_selection=False,new_source_blocks=0,
        new_terminal_outcomes_seen=False,prediction=settings('scientific')['prediction']))


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
    cfg=settings(mode); assert task in cfg['blocks']
    def get(name,local): return pinned(mode,name,run/local if run is not None else None)
    writer=get(f'source_writer_{task:06d}.npz',f'source_writer_{task:06d}.npz')
    pruning=get(f'source_pruning_{task:06d}.npz',f'source_pruning_{task:06d}.npz')
    capture=get(f'source_capture_{task:06d}.npz',f'source_capture_{task:06d}.npz')
    regions=get(f'source_regions_{task:06d}.npz',f'source_regions_{task:06d}.npz')
    saved=get(f'interventions_{task:06d}.npz',f'source_components_{task:06d}.npz')
    assert writer['incoming'][:9].tobytes()==pruning['packets'].tobytes()
    assert writer['incoming'][9:].tobytes()==pruning['packets'].tobytes()
    equal(capture,capture_model.intervene(writer,pruning,cfg['config']))
    equal(capture,capture_audit.intervene(writer,pruning,cfg['config']))
    equal(regions,region_model.intervene(capture)); equal(regions,region_audit.intervene(capture))
    equal(saved,component_model.intervene(regions)); equal(saved,component_audit.intervene(regions))
    scores=[]
    for exp in ('E098','E099','E100','E101'):
        prefix='scores' if exp=='E101' else 'old_'+exp+'_scores'
        scores.append({d:get(f'{prefix}_{task:06d}_r{d}.npz',f'old_{exp}_scores_{task:06d}_r{d}.npz') for d in (0,1)})
    return writer,saved,*scores


def rows(task,draw,cfg,scores,diagnostics,old_scores,prior_scores,region_scores,component_scores,writer_end,writer_window):
    out=[]
    for arm,f,r in np.ndindex(4,4,cfg['recipients']):
        row=dict(task=task,arm=arm,kind='native' if arm<2 else 'mixture',history='sham' if arm%2==0 else 'pulse',
                 founder=f,recipient=r,draw=draw,old_E098_draw=draw,old_E099_draw=draw,old_E100_draw=draw,old_E101_draw=draw)
        for name,start in STARTS.items():
            loc=start+arm,f,r; add_scores(row,name,scores,loc)
            for k,v in diagnostics.items(): row[name+'_'+k]=float(v[loc])
        for (prefix,starts),previous in zip(LEGACY,(old_scores,prior_scores,region_scores,component_scores)):
            for name,start in starts.items(): add_scores(row,prefix+name,previous,(start+arm,f,r))
        for name,start in (('I_pair',0),('P_pair',4),('I_ind',9),('P_ind',13)):
            for phase,s in (('end',writer_end),('window',writer_window)):
                add_scores(row,'source_writer_'+name+'_'+phase,s,(start+arm,f,r))
        for name,parts in CONTRASTS.items():
            for k in METRICS: row[name+'_'+k]=sum(coef*row[v+'_'+k] for v,coef in parts.items())
        for k in METRICS:
            assert abs(row['selected_transfer_'+k]-row['donor_sign_'+k]-row['magnitude_only_'+k])<3e-15
            assert abs(row['selected_transfer_'+k]-row['arrangement_advantage_'+k]-row['shuffled_transfer_'+k])<3e-15
            assert abs(row['donor_sign_'+k]-row['arrangement_advantage_'+k]-row['shuffle_sign_'+k])<3e-15
        out.append(row)
    return out


def erased_rows(task,draw,cfg,scores,diagnostics):
    out=[]
    for name,slot in (('paired_writer',16),('independent_writer',17)):
        for f,r in np.ndindex(4,cfg['recipients']):
            row=dict(task=task,draw=draw,stage=name,founder=f,recipient=r)
            add_scores(row,'erased',scores,(slot,f,r))
            for k,v in diagnostics.items(): row[k]=float(v[slot,f,r])
            out.append(row)
    return out


def averages(records):
    groups={}
    for r in records: groups.setdefault(identity(r),[]).append(r)
    out=[]
    for pair in groups.values():
        assert sorted(r['draw'] for r in pair)==[0,1]; row={}
        for key,value in pair[0].items():
            if key=='draw' or key.endswith('_draw'): continue
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
    scorekeys += [prefix+v+'_'+k for prefix,old in LEGACY for v in old for k in METRICS]
    fields=list(IDENTIFIERS)+['contrast','effect','event_kind']+scorekeys; out=[]
    for row in records:
        for name in CONTRASTS:
            effect=row[name+'_both']
            if effect==0: continue
            event={k:row[k] for k in IDENTIFIERS}; event.update(contrast=name,effect=effect,event_kind='gain' if effect>0 else 'harm')
            event.update({k:row[k] for k in scorekeys}); out.append(event)
    return out,fields
