"""Paired reset/source contrasts; mask averages remain within starting records."""
from common import *
import design

SIGNS=('gain','harm','tie')
GROUPS=('all','history:unique_pass','history:other','message:0','message:1','message:2','message:3')
VIEWS=('all_masks',)+tuple('mask:'+m for m in design.MASKS)+tuple('geometry:'+g for g in design.GEOMETRIES)
CATEGORIES=('conditions','reset_contrasts','source_contrasts')
def units(values):
    a=np.asarray(values,dtype=float);assert np.isfinite(a).all()
    u=np.rint(a*12).astype(np.int16);assert np.max(np.abs(a-u/12),initial=0.)<2e-13 and np.isin(u,(0,3,4,6,12)).all()
    return u
def counts(a):
    a=np.asarray(a);return dict(gain=int((a>0).sum()),harm=int((a<0).sum()),tie=int((a==0).sum()))
def sign(x):return 'gain' if x>0 else 'harm' if x<0 else 'tie'
def endpoint(delta):
    assert delta.ndim==3 and delta.shape[2]>0
    return dict(effect=float(delta.mean()/12),paired_counts=counts(delta),
        fixed_output_mean_counts=counts(delta.mean(axis=1)),record_mean_counts=counts(delta.mean(axis=(0,1))))
def paired(recipient,body):
    assert recipient.shape[0]==body.shape[0] and recipient.shape[2]==body.shape[2]
    a=recipient.mean(axis=(0,1));b=body.mean(axis=(0,1));joint={f'{x}|{y}':0 for x in SIGNS for y in SIGNS}
    for x,y in zip(a,b):joint[sign(x)+'|'+sign(y)]+=1
    result=dict(records=len(a),recipient=endpoint(recipient),body=endpoint(body),record_recipient_body_joint=joint)
    for x,n in result['recipient']['record_mean_counts'].items():assert sum(joint[x+'|'+y] for y in SIGNS)==n
    for y,n in result['body']['record_mean_counts'].items():assert sum(joint[x+'|'+y] for x in SIGNS)==n
    return result


def tensors(directory):
    cfg=read_json(directory/'CONFIG.json');role=cfg['role'];cc,dd=design.schedule(role);check=read_json(directory/'CHECK.json')
    rows=read_json(directory/'ROWS.json');bodies=read_json(directory/'BODIES.json');expected=design.expected(role,1)
    assert len(rows)==expected['paired_rows'] and len(bodies)==expected['body_rows']
    cells={f:dict(out=np.full((cc,dd,16,4,3,3,2,4),np.nan),body=np.full((cc,1,16,4,3,3,2,4),np.nan),
        incoming=np.full((cc,dd,16,4,4),np.nan),original=np.full((cc,dd,16,4,4),np.nan),history=np.full(16,np.nan)) for f in design.families(role)}
    seen=set();body_map={}
    def positions(r):
        assert r['block']==cfg['block'] and r['damage']=='mix100'
        w=r['world'];assert r['message']==w//4 and r['replicate']==w%4 and r['donor_world']==((w//4+2)%4)*4+w%4
        assert r['budget']==design.budget(r['budget_label'],role)
        assert r['geometry']==check['geometries'][r['mask']][w] and r['actual_mask']==check['actual_masks'][r['family']][w]
        return (r['corruption'],w,design.MASKS.index(r['mask']),design.BODIES.index(r['body_source']),
            design.RESETS.index(r['reset']),design.BUDGETS.index(r['budget_label']))
    for r in bodies:
        c,w,m,o,q,b=positions(r);k=(r['family'],c,w,m,o,q,b);assert k not in body_map;body_map[k]=r
        v=cells[r['family']];v['body'][c,0,w,m,o,q,b]=r['credit'];h=v['history'][w]
        assert np.isnan(h) or h==r['developed_score'];v['history'][w]=r['developed_score']
    for r in bodies:
        c,w,m,o,q,b=positions(r);v=cells[r['family']]
        assert np.array_equal(r['preserve_credit'],v['body'][c,0,w,m,o,q,0])
        source_w=r['donor_world'] if r['body_source']=='foreign' else w
        assert r['source_developed_score']==(None if r['body_source']=='neutral' else v['history'][source_w])
    for r in rows:
        c,w,m,o,q,b=positions(r);draw=r['draw'];k=(r['family'],c,draw,w,m,o,q,b);assert k not in seen;seen.add(k)
        b_row=body_map[r['family'],c,w,m,o,q,b]
        assert all(r[k]==v for k,v in b_row.items() if k not in ('credit','preserve_credit'))
        assert r['effect']==[a-b for a,b in zip(r['outgoing'],r['incoming'])]
        v=cells[r['family']];v['out'][c,draw,w,m,o,q,b]=r['outgoing']
        for field in ('incoming','original'):
            current=v[field][c,draw,w,m];assert np.isnan(current).all() or np.array_equal(current,r[field])
            v[field][c,draw,w,m]=r[field]
    for v in cells.values():
        for k in v:v[k]=units(v[k])
        assert np.array_equal(v['out'][:,:,:,:,:,:,0,:],np.broadcast_to(v['incoming'][:,:,:,:,None,None,:],v['out'][:,:,:,:,:,:,0,:].shape))
    return cells,check


def geometry_view(value,geometries):
    result=np.empty((*value.shape[:3],3,*value.shape[4:]),dtype=float)
    for w in range(16):
        for gi,g in enumerate(design.GEOMETRIES):
            indices=[i for i,m in enumerate(design.MASKS) if geometries[m][w]==g]
            assert len(indices)==(2 if gi==2 else 1)
            result[:,:,w,gi]=np.take(value[:,:,w],indices,axis=2).mean(axis=2)
    return result


def views(value,geometries):
    result={'all_masks':value.mean(axis=3)}
    result.update({'mask:'+m:value[:,:,:,i] for i,m in enumerate(design.MASKS)})
    geo=geometry_view(value,geometries)
    result.update({'geometry:'+g:geo[:,:,:,i] for i,g in enumerate(design.GEOMETRIES)})
    return result


def block(directory):
    cells,check=tensors(directory);result={}
    for family,v in cells.items():
        vr=views(v['out'],check['geometries']);vb=views(v['body'],check['geometries'])
        vi=views(v['incoming'],check['geometries']);vo=views(v['original'],check['geometries'])
        selected={'all':np.ones(16,dtype=bool),'history:unique_pass':v['history']==12,'history:other':v['history']!=12}
        selected.update({f'message:{m}':np.arange(16)//4==m for m in range(4)})
        groups={}
        for group in GROUPS:
            keep=selected[group]
            if not keep.any():continue
            stats={k:{} for k in CATEGORIES}
            for view in VIEWS:
                r=vr[view][:,:,keep];b=vb[view][:,:,keep];inc=vi[view][:,:,keep];orig=vo[view][:,:,keep]
                for oi,owner in enumerate(design.BODIES):
                    for qi,variant in enumerate(design.RESETS):
                        for bi,budget in enumerate(design.BUDGETS):
                            for ti,credit_name in enumerate(design.CREDITS):
                                rr=r[:,:,:,oi,qi,bi,ti];bb=b[:,:,:,oi,qi,bi,ti]
                                stat=paired(rr-inc[:,:,:,ti],bb-b[:,:,:,oi,qi,0,ti])
                                stat.update(recipient_mean=float(rr.mean()/12),body_mean=float(bb.mean()/12),
                                    incoming_mean=float(inc[:,:,:,ti].mean()/12),original_mean=float(orig[:,:,:,ti].mean()/12))
                                stats['conditions']['|'.join((view,owner,variant,str(budget),credit_name))]=stat
                    for a,z in (('corrected','uniform'),('reversed','corrected'),('reversed','uniform')):
                        ai=design.RESETS.index(a);zi=design.RESETS.index(z)
                        for bi,budget in enumerate(design.BUDGETS):
                            for ti,credit_name in enumerate(design.CREDITS):
                                stat=paired(r[:,:,:,oi,ai,bi,ti]-r[:,:,:,oi,zi,bi,ti],b[:,:,:,oi,ai,bi,ti]-b[:,:,:,oi,zi,bi,ti])
                                stats['reset_contrasts']['|'.join((view,owner,a+'_minus_'+z,str(budget),credit_name))]=stat
                for other in ('foreign','neutral'):
                    oi=design.BODIES.index(other)
                    for qi,variant in enumerate(design.RESETS):
                        for bi,budget in enumerate(design.BUDGETS):
                            for ti,credit_name in enumerate(design.CREDITS):
                                stat=paired(r[:,:,:,0,qi,bi,ti]-r[:,:,:,oi,qi,bi,ti],b[:,:,:,0,qi,bi,ti]-b[:,:,:,oi,qi,bi,ti])
                                stats['source_contrasts']['|'.join((view,'own_minus_'+other,variant,str(budget),credit_name))]=stat
            groups[group]=dict(records=int(keep.sum()),**stats)
            # Balanced masks make uniform neutral template credit a scoring identity.
            for budget in design.BUDGETS:
                assert groups[group]['conditions'][f'all_masks|neutral|uniform|{budget}|template']['recipient_mean']==.25
                assert groups[group]['conditions'][f'all_masks|neutral|uniform|{budget}|template']['body_mean']==.25
        result[family]=groups
    return dict(block=read_json(directory/'CONFIG.json')['block'],cells=result,verification=check['verification'],
        source_population_exposed=True,physical_mask_means_stay_within_record=True)


def combine(stats,indices):
    weights=np.array([v['records'] for v in stats],dtype=float)
    result=dict(records=int(weights.sum()),blocks=len(stats),block_record_counts=dict(zip(map(str,indices),weights.astype(int).tolist())),
        record_recipient_body_joint={k:sum(s['record_recipient_body_joint'][k] for s in stats) for k in stats[0]['record_recipient_body_joint']})
    for field in ('recipient','body'):
        a=np.array([s[field]['effect'] for s in stats]);value=dict(equal_nonempty_block_effect=float(a.mean()),
            pooled_record_effect=float(np.average(a,weights=weights)),block_sign_counts=counts(a),block_effects=dict(zip(map(str,indices),a.tolist())))
        for kind in ('paired_counts','fixed_output_mean_counts','record_mean_counts'):
            value[kind]={s:sum(v[field][kind][s] for v in stats) for s in SIGNS}
        result[field]=value
    for field in ('recipient_mean','body_mean','incoming_mean','original_mean'):
        if field in stats[0]:
            a=[s[field] for s in stats];result[field]=dict(equal_nonempty_block=float(np.mean(a)),pooled_record=float(np.average(a,weights=weights)))
    return result


def summary(directory,role):
    blocks=[read_json(directory/f'tissue_{i}/SUMMARY.json') for i in design.indices(role)];result={}
    for family in design.families(role):
        groups={}
        for group in GROUPS:
            present=[(b['block'],b['cells'][family][group]) for b in blocks if group in b['cells'][family]]
            if not present:continue
            ids=[i for i,v in present];values=[v for i,v in present];g={}
            for category in CATEGORIES:
                assert all(set(v[category])==set(values[0][category]) for v in values)
                g[category]={key:combine([v[category][key] for v in values],ids) for key in sorted(values[0][category])}
            g.update(blocks=len(values),records=sum(v['records'] for v in values));groups[group]=g
        result[family]=groups
    proof={k:(0. if k=='max_native_error' else sum(b['verification'][k] for b in blocks)) for k in blocks[0]['verification']}
    for k,v in design.expected(role,len(blocks)).items():assert proof[k]==v
    return dict(study='TT032',role=role,blocks=list(design.indices(role)),cells=result,verification=proof,
        focused_damage='mix100',source_TT028_primary='NOT_CONFIRMED',source_TT028_joint='NOT_CONFIRMED',
        all_cases_and_paired_harms_retained=True,new_population_confirmation=False,serial_endpoint=False,
        fitted_policy=False,mean_offset_matched=True,physical_duplicates_not_independent=True,
        uniform_neutral_mask_average_is_structural=True)


def report(value):
    lines=['# TT032: spatial reset intervention','',
        'Exposed-case mechanism development, with complete packet replacement. TT028 primary and joint remain NOT_CONFIRMED.',
        'Every source and reset retains preservation, paired harms and separate body outcomes. All three reset offsets have the same spatial mean.',
        f'{design.schedule(value["role"])[1]} new paired receiving futures per packet; individual estimates remain coarse.','',
        '| Family | Reset | Neutral template credit | Neutral opposite-template credit | Own target credit | Foreign target / donor credit | Neutral target credit |',
        '|---|---|---:|---:|---:|---:|---:|']
    def level(f,owner,variant,credit,budget=1000,body=False):
        key=f'all_masks|{owner}|{variant}|{budget}|{credit}'
        return value['cells'][f]['all']['conditions'][key]['body_mean' if body else 'recipient_mean']['equal_nonempty_block']
    for family in design.families(value['role']):
        for variant in design.RESETS:
            vals=[100*level(family,o,variant,t) for o,t in (('neutral','template'),('neutral','opposite'),('own','target'),('foreign','target'),('foreign','donor'),('neutral','target'))]
            lines.append(f'| {family} | {variant} | {vals[0]:.6f} | {vals[1]:.6f} | {vals[2]:.6f} | {vals[3]:.6f} / {vals[4]:.6f} | {vals[5]:.6f} |')
    lines += ['','Neutral uniform template credit averaged over all four masks is 25% by balanced scoring after byte-verifying mask independence. It is not a new empirical null-test result. Repeated task labels, families, masks and exact-state aliases are not independent source records.','',
        '| Family | Source | Reset | Full − preservation: recipient / body (pp) | Record-mean recipient gains / harms / ties |',
        '|---|---|---|---:|---:|']
    for family in design.families(value['role']):
        for owner in design.BODIES:
            for variant in design.RESETS:
                v=value['cells'][family]['all']['conditions'][f'all_masks|{owner}|{variant}|1000|target']
                c=v['recipient']['record_mean_counts'];cs=' / '.join(str(c[s]) for s in SIGNS)
                lines.append(f'| {family} | {owner} | {variant} | {100*v["recipient"]["equal_nonempty_block_effect"]:+.6f} / {100*v["body"]["equal_nonempty_block_effect"]:+.6f} | {cs} |')
    lines += ['','SUMMARY.json retains every physical mask, within-record geometry mean, target/donor/template/opposite credit, both budgets, reset/source contrasts, paired harms, body/recipient joint outcomes, history/message groups, and block effects. ROWS.json and BODIES.json preserve all labelled cases; ALIASES.json identifies exact physical reuse.','',
        'Preservation comparisons at an individual physical mask remain available. Counts in the all-mask table refer to paired within-record four-mask means, not individual mask observations. Both mixed masks are averaged within each record. No arbitrary-message recovery, serial durability, or fresh-population claim is inferred from template tracking.','']
    return '\n'.join(lines)
