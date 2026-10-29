"""Separate terminal body and fresh-recipient endpoints with all paired harms."""
from common import *

def units(x):
    a=np.asarray(x,dtype=float);assert np.isfinite(a).all()
    u=np.rint(a*12).astype(np.int16);near(u/12,a);assert np.isin(u,(0,3,4,6,12)).all();return u
def stats(delta):
    assert delta.ndim==4
    result=[delta.mean((0,1,2))/12]
    for x in (delta,delta.mean(1),delta.mean((0,1))):
        axes=tuple(range(x.ndim-1));result.extend(((x>0).sum(axes),(x<0).sum(axes),(x==0).sum(axes)))
    return np.stack(result,axis=-1)
def views(value):
    assert value.shape[2:4]==(16,4)
    out={'all_masks':value.mean(3)}
    out.update({'mask:'+m:value[:,:,:,mi] for mi,m in enumerate(MASKS)})
    for g,name in enumerate(GEOMETRIES):
        a=np.empty((*value.shape[:3],*value.shape[4:]),dtype=float)
        for w in range(16):
            ids=[m for m in range(4) if geometry(m,w)==g];assert len(ids)==(2 if g==2 else 1)
            a[:,:,w]=np.take(value[:,:,w],ids,axis=2).mean(2)
        out['geometry:'+name]=a
    return out
def joint(body_delta,recipient_delta):
    assert body_delta.ndim==recipient_delta.ndim==4 and body_delta.shape[1]==1
    b=body_delta[:,0];r=recipient_delta.mean(1)
    assert b.shape==r.shape
    out=np.zeros((4,2,3,3),dtype=np.int64)
    for resolution,(bb,rr) in enumerate(((b,r),(b.mean(0),r.mean(0)))):
        bs=np.sign(bb);rs=np.sign(rr);axes=tuple(range(bs.ndim-1))
        for bi,bv in enumerate((-1,0,1)):
            for ri,rv in enumerate((-1,0,1)):
                out[:,resolution,bi,ri]=((bs==bv)&(rs==rv)).sum(axes)
    return out
def reverse_stats(value):
    result=value.copy();result[...,0]*=-1
    for start in (1,4,7):result[...,start:start+3]=value[...,[start+1,start,start+2]]
    return result
def block(config,rows,bodies):
    cc,dd=config['corruptions'],config['draws'];families=config['families']
    result=dict(records=np.zeros(len(CONDITIONS),dtype=np.int32),source_records=np.zeros(len(SOURCE_CONTRASTS),dtype=np.int32))
    for name,shape in (
        ('recipient_levels',(len(CONDITIONS),len(ARMS),4)),('original_levels',(len(CONDITIONS),4)),
        ('body_levels',(len(CONDITIONS),len(ARMS),4)),('recipient_stats',(len(CONDITIONS),len(PAIRS),4,10)),
        ('body_stats',(len(CONDITIONS),len(PAIRS),4,10)),
        ('recipient_source_stats',(len(SOURCE_CONTRASTS),len(ARMS),4,10)),('body_source_stats',(len(SOURCE_CONTRASTS),len(ARMS),4,10)),
    ):
        result[name]=np.zeros(shape)
        if name.endswith('stats'):result[name][...,0]=np.nan
        else:result[name].fill(np.nan)
    result['joint_counts']=np.zeros((len(CONDITIONS),len(PAIRS),4,2,3,3),dtype=np.int64)
    cells={f:dict(r=np.full((cc,dd,16,4,3,len(ARMS),4),-1,dtype=np.int16),
        original=np.full((cc,dd,16,4,4),-1,dtype=np.int16),
        b=np.full((cc,1,16,4,3,len(ARMS),4),-1,dtype=np.int16),history=np.full(16,np.nan)) for f in families}
    seen={};seen_rows=set()
    for row in bodies:
        f=row['family'];c,w,m,o=row['corruption'],row['world'],MASKS.index(row['mask']),SOURCES.index(row['body_source'])
        k=(f,c,w,m,o);assert k not in seen;seen[k]=row;v=cells[f]
        assert row['block']==config['block'] and row['reset']=='uniform' and row['message']==w//4
        assert row['geometry']==GEOMETRIES[geometry(m,w)] and row['template_message']==m^1
        for bi,name in enumerate(BODY_FIELDS):v['b'][c,0,w,m,o,bi]=units(row[name])
        assert np.isnan(v['history'][w]) or v['history'][w]==row['developed_score']
        v['history'][w]=row['developed_score']
    for row in rows:
        f=row['family'];c,d,w,m,o=row['corruption'],row['draw'],row['world'],MASKS.index(row['mask']),SOURCES.index(row['body_source'])
        k=(f,c,d,w,m,o);assert k not in seen_rows;seen_rows.add(k);v=cells[f];b=seen[f,c,w,m,o]
        for key,val in b.items():
            if key not in BODY_FIELDS:assert row[key]==val
        for bi,name in enumerate(READER_FIELDS):v['r'][c,d,w,m,o,bi]=units(row[name])
        orig=units(row['original']);prev=v['original'][c,d,w,m]
        assert np.all(prev==-1) or np.array_equal(prev,orig);v['original'][c,d,w,m]=orig
    assert len(seen)==cc*len(families)*16*4*3 and len(seen_rows)==len(seen)*dd
    for f,v in cells.items():
        assert (v['r']>=0).all() and (v['original']>=0).all() and (v['b']>=0).all() and np.isfinite(v['history']).all()
        for oi in (1,2):exact(v['r'][:,:,:,:,0,0],v['r'][:,:,:,:,oi,0],'common preserved packet')
        rr,bb,oo=views(v['r']),views(v['b']),views(v['original'])
        groups={'all':np.ones(16,dtype=bool),'history:unique_pass':v['history']==1.,'history:other':v['history']!=1.}
        groups.update({f'message:{m}':np.arange(16)//4==m for m in range(4)})
        for group,keep in groups.items():
            if not keep.any():continue
            for view in VIEWS:
                r=rr[view][:,:,keep];b=bb[view][:,:,keep];orig=oo[view][:,:,keep]
                for oi,owner in enumerate(SOURCES):
                    j=INDEX['|'.join((f,group,view,owner))];result['records'][j]=int(keep.sum())
                    z=r[:,:,:,oi];body=b[:,:,:,oi]
                    result['recipient_levels'][j]=z.mean((0,1,2))/12
                    result['original_levels'][j]=orig.mean((0,1,2))/12
                    result['body_levels'][j]=body.mean((0,1,2))/12
                    for ti,(a,q) in enumerate(PAIRS):
                        rd=z[:,:,:,a]-z[:,:,:,q];bd=body[:,:,:,a]-body[:,:,:,q]
                        result['recipient_stats'][j,ti]=stats(rd);result['body_stats'][j,ti]=stats(bd)
                        tab=joint(bd,rd);result['joint_counts'][j,ti]=tab
                        for resolution,start in ((0,4),(1,7)):
                            np.testing.assert_array_equal(tab[:,resolution].sum(-1),result['body_stats'][j,ti][:,[start+1,start+2,start]])
                            np.testing.assert_array_equal(tab[:,resolution].sum(-2),result['recipient_stats'][j,ti][:,[start+1,start+2,start]])
                for oi,other in enumerate(SOURCES[1:],1):
                    j=SOURCE_INDEX['|'.join((f,group,view,'own_minus_'+other))]
                    result['source_records'][j]=int(keep.sum())
                    for bi in range(len(ARMS)):
                        result['recipient_source_stats'][j,bi]=stats(r[:,:,:,0,bi]-r[:,:,:,oi,bi])
                        result['body_source_stats'][j,bi]=stats(b[:,:,:,0,bi]-b[:,:,:,oi,bi])
    return result
def weighted(values,weights):
    shape=weights.shape+tuple(1 for _ in values.shape[2:]);w=weights.reshape(shape);present=w>0
    value=np.where(present,values,0)
    equal=np.divide(value.sum(0),present.sum(0),out=np.full_like(value[0],np.nan),where=present.sum(0)>0)
    pooled=np.divide((value*w).sum(0),w.sum(0),out=np.full_like(value[0],np.nan),where=w.sum(0)>0)
    return equal,pooled
def combine(blocks):
    out={}
    for name in ('records','source_records'):
        out['block_'+name]=np.stack([b[name] for b in blocks]);out[name]=out['block_'+name].sum(0)
    out['joint_counts_by_block']=np.stack([b['joint_counts'] for b in blocks])
    out['joint_counts']=out['joint_counts_by_block'].sum(0)
    for name in ('recipient_levels','original_levels','body_levels','recipient_stats','body_stats','recipient_source_stats','body_source_stats'):
        values=np.stack([b[name] for b in blocks]);weights=out['block_source_records' if name.endswith('source_stats') else 'block_records']
        if name.endswith('stats'):
            out[name+'_counts']=values[...,1:].sum(0);values=values[...,0]
        out[name+'_block_means']=values
        out[name+'_equal_block'],out[name+'_pooled_record']=weighted(values,weights)
    return out

def report(a,role):
    def idx(f,view='all_masks',source='own'):return INDEX['|'.join((f,'all',view,source))]
    def values(v):return ' / '.join(f'{100*x:.6f}' for x in v)
    def counts(v):return ' / '.join(str(int(x)) for x in v)
    lines=['# TT037: equal-budget early versus late writing','',
        'Exposed TT036 cases; new late-writing bodies and outgoing-packet assays. Controls and recipient environments are inherited and exactly paired. Every body evolves to update 1000. Early writes on 1–100; late writes on 901–1000. Both use 100 write updates.','',
        '| Family | Own-body geometry | Body credit: preserve / early / late / continuous (%) | Recipient credit: same order (%) |',
        '|---|---|---:|---:|']
    for f in FAMILIES:
        for view in ('all_masks',)+tuple('geometry:'+g for g in GEOMETRIES):
            j=idx(f,view)
            if a['records'][j]:lines.append(f"| {f} | {view} | {values(a['body_levels_equal_block'][j,:,0])} | {values(a['recipient_levels_equal_block'][j,:,0])} |")
    lines+=['','| Family | Source | Early minus late body (pp) | Body record gains / harms / ties | Early minus late packet (pp) | Packet record gains / harms / ties |',
        '|---|---|---:|---:|---:|---:|']
    for f in FAMILIES:
        for source in SOURCES:
            j=idx(f,source=source)
            if a['records'][j]:
                lines.append(f"| {f} | {source} | {100*a['body_stats_equal_block'][j,0,0]:+.6f} | {counts(a['body_stats_counts'][j,0,0,6:9])} | {100*a['recipient_stats_equal_block'][j,0,0]:+.6f} | {counts(a['recipient_stats_counts'][j,0,0,6:9])} |")
    lines+=['','| Family | Own-source comparison | Body change (pp) | Packet change (pp) |','|---|---|---:|---:|']
    for f in FAMILIES:
        j=idx(f)
        if a['records'][j]:
            for t,name in enumerate(COMPARISONS):
                lines.append(f"| {f} | {name} | {100*a['body_stats_equal_block'][j,t,0]:+.6f} | {100*a['recipient_stats_equal_block'][j,t,0]:+.6f} |")
    j=idx('residual')
    if a['records'][j]:
        lines+=['','Primary descriptive comparison: residual own-source all-mask target, early minus late. Joint record-mean counts:',
            '| Body change | Packet harms | Packet ties | Packet gains |','|---|---:|---:|---:|']
        tab=a['joint_counts'][j,0,0,1]
        for bi,label in enumerate(SIGNS):lines.append(f'| {label} | {tab[bi,0]} | {tab[bi,1]} | {tab[bi,2]} |')
    lines+=['','SUMMARY.npz retains every block, equal nonempty-block and pooled-record means, physical masks, geometry averages within records, both history groups, messages, four credits, source contrasts and all paired harms. Joint tables count each body once per fixed-output or record mean, never once per receiving draw. Every inherited control aggregate is reconciled to TT036.',
        'All new dynamics are independently replayed. No new independent recipient environments or population cases are acquired. This is descriptive timing development, with no significance verdict or selected policy. Early writing includes 900 post-write body updates; late writing includes none. The contrast cannot isolate waiting before writing from recovery afterward. It does not test uninterrupted body performance, serial heredity, optimal timing or damage-level generalization. TT028 primary and joint remain NOT_CONFIRMED.','']
    return '\n'.join(lines)

def summary(directory,role):
    blocks=[];proof={}
    for i in selected(role):
        p=directory/f'tissue_{i}';receipt=read(p/'COMPLETE.json')
        assert receipt['status']=='PASS';verify(receipt['outputs']);blocks.append(arrays(p/'AGGREGATE.npz'))
        for k,v in receipt['verification'].items():proof[k]=proof.get(k,0)+v
    value=combine(blocks);save(directory/'SUMMARY.npz',value)
    write(directory/'METADATA.json',dict(study='TT037',role=role,blocks=selected(role),conditions=CONDITIONS,
        source_contrasts=SOURCE_CONTRASTS,arms=ARMS,budgets=BUDGETS,windows=WINDOWS,body_endpoint=1000,
        credits=CREDITS,comparisons=COMPARISONS,stat_fields=STAT_FIELDS,joint_resolution=['fixed_output_mean','record_mean'],
        joint_body_sign=SIGNS,joint_recipient_sign=SIGNS,verification=proof,
        primary='residual|all|all_masks|own; early_minus_late; target; separate terminal body and packet endpoints; descriptive',
        source_population_exposed=True,controls_inherited=True,receiving_environments_inherited=True,
        new_independent_receiving_draws=0,new_receiving_assays=proof['new_receiving_assays']))
    with (directory/'REPORT.md').open('x') as f:f.write(report(value,role))
    assert report(arrays(directory/'SUMMARY.npz'),role)==(directory/'REPORT.md').read_text()
    return proof
