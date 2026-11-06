"""All-case paired effects; block-level uncertainty and explicit feasibility."""
from study import *
import csv

def contrasts():
    result=[]
    for h in (0,1):
        for a,b in [('P','I'),('C','I'),('C','P'),('C','L_native'),('C','L')]:result.append((h,{a:1,b:-1}))
        for location in ('C','L'):
            for a,b in [(location+'_flip',location),(location+'_flip_low',location+'_low'),
                (location+'_low',location),(location+'_flip_low',location+'_flip')]:result.append((h,{a:1,b:-1}))
        for suffix in ('_flip','_low','_flip_low'):
            result.append((h,{'C'+suffix:1,'L'+suffix:-1}))
    for a in ('P','C'):
        for x,y in [(a,a+'_O'),(a+'_S',a),(a+'_O',a+'_M'),(a+'_M',a),(a+'_O',a+'_S')]:result.append((1,{x:1,y:-1}))
    return result

def interval(values,radius_range,indices):
    n=len(values);mean=float(np.mean(values));lo,hi=np.quantile(np.mean(values[indices],axis=1),[.025,.975])
    radius=2*radius_range*np.sqrt(np.log(40)/(2*n))
    bounded=[max(-radius_range,mean-radius),min(radius_range,mean+radius)]
    return dict(estimate=mean,block_values=values.tolist(),bootstrap_pointwise_95=[float(lo),float(hi)],
        hoeffding_pointwise_95=bounded,zero_empirical_variation=bool(np.ptp(values)==0),blocks=n)

def analyze(run,blocks,technical=False):
    run=Path(run);target=run/'analysis';target.mkdir();scores=[];feasible=[];mechanisms=[];support=[];input_hashes={}
    fields=('both','minimum_margin','opposite_rule_success','aligned_transfer','cue0_margin','cue1_margin')
    with (target/'CASES.csv').open('x',newline='') as f:
        cols=['block','source','founder','recipient','draw','horizon','arm','feasible']+list(fields)
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for b in blocks:
            path=run/f'block_{b}';done=read(path/'COMPLETE.json');assert done['status']=='COMPLETE'
            for n,h in done['outputs'].items():assert sha(path/n)==h,str(path/n)
            input_hashes[str(path/'COMPLETE.json')]=sha(path/'COMPLETE.json')
            meta=load(path/'PREPARED.npz');r=meta['eligible'].shape[2];feasible.append(meta['feasible'])
            mechanisms.append(load(path/'MECHANISM_SUMMARY.npz'))
            support.append(load(path/'CAPTURE_CONTROLS.npz')['capture_support_disagreement'])
            current=[]
            for draw in (0,1):
                s=load(path/f'SCORES_{draw}.npz');s={k:v.reshape(len(LABELS),4,4,r) for k,v in s.items()}
                assert s['both'].tobytes()==((s['cue0_margin']>.25)&(s['cue1_margin']>.25)).tobytes()
                current.append(s)
                for slot,(a,h) in enumerate(LABELS):
                    for source_id,founder,recipient in np.ndindex(4,4,r):
                        loc=slot,source_id,founder,recipient
                        row=dict(block=b,source=source_id,founder=founder,recipient=recipient,draw=draw,
                            horizon=h,arm=a,feasible=int(meta['feasible'][source_id,founder,recipient]))
                        row.update({k:float(s[k][loc]) for k in fields});w.writerow(row)
            scores.append({k:np.stack([c[k] for c in current]) for k in fields})
    all_scores={k:np.stack([s[k] for s in scores]) for k in fields};feasible=np.stack(feasible)
    save(target/'SCORES.npz',all_scores);save(target/'FEASIBILITY.npz',dict(feasible=feasible))
    index={tuple(label):j for j,label in enumerate(LABELS)}
    seed=int.from_bytes(hashlib.sha256(b'TT050/causal_analysis/v1').digest()[:16],'little')
    rng=np.random.Generator(np.random.PCG64(seed));indices=rng.integers(0,len(blocks),size=(10000,len(blocks)))
    panels={}
    for name,sl in [('mixture',slice(2,4)),('native',slice(0,2)),('all',slice(0,4))]:
        arms={};effects=[];mask=feasible[:,sl]
        for slot,(a,h) in enumerate(LABELS):
            arms[f'{a}_h{h}']={}
            for metric in ('both','opposite_rule_success','minimum_margin'):
                values=all_scores[metric][:,:,slot,sl]
                arms[f'{a}_h{h}'][metric]=dict(total=float(values.sum()),contexts=int(values.size),
                    mean=float(values.mean()),block_values=values.mean(axis=(1,2,3,4)).tolist())
        for horizon,coeff in contrasts():
            effect=dict(horizon=horizon,coefficients=coeff,metrics={})
            for metric,bound in [('both',1),('opposite_rule_success',1),('minimum_margin',4),('aligned_transfer',4)]:
                values=sum(c*all_scores[metric][:,:,index[(a,horizon)],sl].astype(float) for a,c in coeff.items())
                means=values.mean(axis=(1,2,3,4));out=interval(means,bound,indices)
                out.update(positive_contexts=int((values>0).sum()),negative_contexts=int((values<0).sum()),
                    tied_contexts=int((values==0).sum()),contexts=int(values.size),
                    positive_record_means=int((values.mean(axis=1)>0).sum()),negative_record_means=int((values.mean(axis=1)<0).sum()))
                if metric in ('both','opposite_rule_success'):
                    positive=next(a for a,c in coeff.items() if c==1)
                    negative=next(a for a,c in coeff.items() if c==-1)
                    aa=all_scores[metric][:,:,index[(positive,horizon)],sl]
                    bb=all_scores[metric][:,:,index[(negative,horizon)],sl]
                    out['paired_table_reference_rows_treatment_columns']=[
                        [int(np.count_nonzero((bb==r)&(aa==c))) for c in (0,1)] for r in (0,1)]
                valid=np.broadcast_to(mask[:,None],values.shape)
                out['feasible_only']=dict(contexts=int(valid.sum()),mean=float(values[valid].mean()) if valid.any() else None,
                    block_values=[float(values[b][valid[b]].mean()) if valid[b].any() else None for b in range(len(blocks))],
                    definition='secondary, conditional on pre-assessment graph feasibility; no substitution for all cases')
                effect['metrics'][metric]=out
            effects.append(effect)
        panels[name]=dict(arms=arms,effects=effects,feasible_records=int(mask.sum()),records=int(mask.size))
    mechan={}
    for k in mechanisms[0]:
        a=np.stack([m[k] for m in mechanisms]).reshape(len(blocks),len(ARMS),4,4,-1)
        mechan[k]={kind:{arm:dict(mean=float(a[:,j,sl].mean()),block_values=a[:,j,sl].mean(axis=(1,2,3)).tolist())
            for j,arm in enumerate(ARMS)} for kind,sl in [('mixture',slice(2,4)),('native',slice(0,2))]}
    result=dict(status='AUTOMATED_ANALYSIS_COMPLETE_NOT_YET_REVIEWED',utc=now(),technical=technical,blocks=blocks,
        source_records_reused=True,terminal_draws=2,contexts_independent=False,panels=panels,mechanism=mechan,
        capture_support_disagreements=int(sum(np.count_nonzero(x) for x in support)),
        source_input_complete_hashes=input_hashes,confidence='pointwise approximate whole-block bootstrap and bounded Hoeffding',
        interpretation='One-rewrite causal development. No duration, unique-mediation, fresh-confirmation or composite positive verdict.')
    write(target/'RESULTS.json',result)
    lines=['# TT050 automated results — review pending','',result['interpretation'],'',
        f'{len(blocks)} source blocks; {feasible.size} records, all retained. Technical: {technical}.','',
        '| Arm | Immediate mixture success | Success after one rewrite |','|---|---:|---:|']
    for a in ARMS:
        x=panels['mixture']['arms'];lines.append(f"| {a} | {100*x[a+'_h0']['both']['mean']:.2f}% | {100*x[a+'_h1']['both']['mean']:.2f}% |")
    lines.extend(['','All gains, harms, opposite-task outcomes, margins, feasible-only descriptions, block values and uncertainty are in RESULTS.json and CASES.csv.',
        'Terminal nuisance draws are matched across arms and horizons. Writer injury is separate. No nonsignificant difference is treated as equivalence.'])
    with (target/'REPORT.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    write(target/'COMPLETE.json',dict(status='COMPLETE',utc=now(),inputs=input_hashes,
        outputs={p.name:sha(p) for p in target.iterdir() if p.is_file()}))
    from analysis_audit import audit
    audit(target)
    return dict(status='COMPLETE',blocks=len(blocks),records=int(feasible.size),technical=technical)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('blocks',nargs='+',type=int);p.add_argument('--technical',action='store_true')
    args=p.parse_args();print(json.dumps(analyze(args.run,args.blocks,args.technical)))
