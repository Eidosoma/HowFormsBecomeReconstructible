"""Scalar outcome reconstruction and independent descriptive table accounting."""
import json
from pathlib import Path
import time

import numpy as np
import support as s


def close(a,b,label):
    if not np.allclose(a,b,rtol=0,atol=1e-14):raise ValueError('Analysis mismatch: '+label)


def audit(output):
    started=time.monotonic();output=Path(output)
    summary=json.loads((output/'summary.json').read_text());index=json.loads((output/'EVENTS.json').read_text())
    with np.load(output/'observations.npz',allow_pickle=False) as z:obs={k:z[k] for k in z.files}
    n=len(index['contexts']);m=index['cfg']['masks_per_context']
    expected_scope=dict(study='TT005',mode=index['mode'],contexts=index['contexts'],packet_names=s.NAMES,
        assay_pairings=s.PLAN['assay_pairings'],masks_per_context=m,replicates_per_mask=2,
        classification='DEVELOPMENT' if index['mode']=='pilot' else 'TECHNICAL_EXCLUSION',
        rdt_verdict='NOT_A_CONFIRMATORY_TEST',native_forecast='ABSTAIN')
    if any(summary[k]!=v for k,v in expected_scope.items()):raise ValueError('Summary contract differs')
    expected=np.empty((n,11,4,m,2),np.int8);passed=np.zeros((*expected.shape,2),bool)
    margins=np.empty_like(passed,dtype=float);opposite=np.empty_like(margins)
    for i,entry in enumerate(index['events']):
        with np.load(output/entry['path'],allow_pickle=False) as z:
            ports=z['mean_ports'].reshape(11,4,m,2,2,2)
        if not np.array_equal(ports,obs['mean_ports'][i]):raise ValueError('Mean-port export changed')
        rule=index['contexts'][i]['rule']
        for p,c,mask,rep in np.ndindex(11,4,m,2):
            for cue,stimulus in enumerate([1.,-1.]):
                left,right=ports[p,c,mask,rep,cue]
                sign=rule*stimulus
                a,b=min(sign*left,-sign*right),min(-sign*left,sign*right)
                margins[i,p,c,mask,rep,cue]=a;opposite[i,p,c,mask,rep,cue]=b
                passed[i,p,c,mask,rep,cue]=a>index['cfg']['margin']
            first,second=margins[i,p,c,mask,rep]
            rev_first,rev_second=opposite[i,p,c,mask,rep]
            expected[i,p,c,mask,rep]=0 if min(first,second)>.25 else 1 if min(rev_first,rev_second)>.25 else 2
    for name,arr in [('category',expected),('cue_success',passed),('ancestral_margin',margins),('opposite_margin',opposite)]:
        if obs[name].shape!=arr.shape or obs[name].dtype!=arr.dtype or obs[name].tobytes()!=arr.tobytes():raise ValueError('Scoring differs: '+name)
    if len(summary['rows'])!=44 or len(summary['context_rows'])!=n*44 or len(summary['contrasts'])!=33:
        raise ValueError('Incomplete tables')
    expected_pairs={(p,c[0]) for p in s.NAMES for c in s.PLAN['assay_pairings']}
    if {(r['packet'],r['assay_pairing']) for r in summary['rows']}!=expected_pairs:raise ValueError('Duplicate or missing pooled row')
    if {(r['context_id'],r['packet'],r['assay_pairing']) for r in summary['context_rows']}!={(ctx['id'],p,c) for ctx in index['contexts'] for p,c in expected_pairs}:
        raise ValueError('Duplicate or missing context row')
    if {(r['packet'],r['contrast']) for r in summary['contrasts']}!={(p,c[0]+' minus matched') for p in s.NAMES for c in s.PLAN['assay_pairings'][1:]}:
        raise ValueError('Duplicate or missing contrast')
    invariant=all(np.array_equal(obs['mean_ports'][:,:,c,:,:,0],obs['mean_ports'][:,:,0,:,:,0]) for c in range(1,4))
    if not invariant or summary['first_cue_bit_identical_across_conditions'] is not True:raise ValueError('First cue changed')
    by_id={row['id']:i for i,row in enumerate(index['contexts'])}
    for row in summary['rows']:
        p=s.NAMES.index(row['packet']);c=[v[0] for v in s.PLAN['assay_pairings']].index(row['assay_pairing'])
        counts=[0,0,0];cues=[0,0];disagreements=0;one=[];two=[];worst=[]
        for i,mask,rep in np.ndindex(n,m,2):
            counts[int(expected[i,p,c,mask,rep])]+=1
            for j in range(2):cues[j]+=int(passed[i,p,c,mask,rep,j])
            a,b=margins[i,p,c,mask,rep];one.append(a);two.append(b);worst.append(min(a,b))
        for i,mask in np.ndindex(n,m):disagreements+=int(expected[i,p,c,mask,0]!=expected[i,p,c,mask,1])
        if row['category_counts']!=dict(zip(['ancestral','opposite','neither'],counts)) or row['cue_success_counts']!=cues:
            raise ValueError('Count table differs')
        if (row['assays'],row['duplicate_disagreements'],row['duplicate_pairs'])!=(n*m*2,disagreements,n*m):raise ValueError('Repeat table differs')
        close(row['ancestral_rate'],counts[0]/(n*m*2),'A rate');close(row['opposite_rate'],counts[1]/(n*m*2),'B rate')
        close(row['mean_cue_margins'],[sum(one)/len(one),sum(two)/len(two)],'cue margins')
        close(row['mean_worst_cue_margin'],sum(worst)/len(worst),'worst margin')
    for row in summary['context_rows']:
        i=by_id[row['context_id']];p=s.NAMES.index(row['packet']);c=[v[0] for v in s.PLAN['assay_pairings']].index(row['assay_pairing'])
        values=[int(expected[i,p,c,mask,rep]) for mask,rep in np.ndindex(m,2)]
        counts=[values.count(k) for k in range(3)]
        cues=[sum(int(passed[i,p,c,mask,rep,j]) for mask,rep in np.ndindex(m,2)) for j in range(2)]
        d=sum(int(expected[i,p,c,mask,0]!=expected[i,p,c,mask,1]) for mask in range(m))
        if (row['block'],row['category_counts'],row['cue_success_counts'],row['duplicate_disagreements'])!=(index['contexts'][i]['block'],counts,cues,d):raise ValueError('Context table differs')
        close(row['mean_cue_margins'],[sum(margins[i,p,c,mask,rep,j] for mask,rep in np.ndindex(m,2))/(2*m) for j in range(2)],'context margins')
    blocks=sorted({v['block'] for v in index['contexts']})
    if summary['blocks']!=blocks or summary['independent_block_count']!=len(blocks):raise ValueError('Independent unit changed')
    for row in summary['contrasts']:
        p=s.NAMES.index(row['packet']);label=row['contrast'].removesuffix(' minus matched')
        c=[v[0] for v in s.PLAN['assay_pairings']].index(label)
        differences=[];rescued=harmed=0
        if len(row['blocks'])!=len(blocks) or row['main_descriptive']!=(c==3 and p<9):raise ValueError('Contrast scope differs')
        for block,saved in zip(blocks,row['blocks']):
            take=[i for i,v in enumerate(index['contexts']) if v['block']==block];tally=[0,0,0,0];cue_diff=[0,0]
            for i in take:
                for mask,rep in np.ndindex(m,2):
                    before=expected[i,p,0,mask,rep]==0;after=expected[i,p,c,mask,rep]==0
                    tally[0]+=int(not before and after);tally[1]+=int(before and not after)
                    tally[2]+=int(before and after);tally[3]+=int(not before and not after)
                    for j in range(2):cue_diff[j]+=int(passed[i,p,c,mask,rep,j])-int(passed[i,p,0,mask,rep,j])
            count=2*m*len(take);delta=(tally[0]-tally[1])/count
            expected_row=dict(block=block,contexts=len(take),assay_pairs=count,difference=delta,rescued=tally[0],harmed=tally[1],both_pass=tally[2],both_fail=tally[3],cue_difference=[v/count for v in cue_diff])
            if saved!=expected_row:raise ValueError('Block contrast differs')
            differences.append(delta);rescued+=tally[0];harmed+=tally[1]
        close(row['mean_block_difference'],sum(differences)/len(differences),'mean block difference')
        if (row['rescued'],row['harmed'])!=(rescued,harmed):raise ValueError('Paired contrast differs')
    if summary['paired_cue_assays']!=expected.size or summary['native_rebuilds']!=0 or summary['interval_method'] is not None:
        raise ValueError('Inference scope differs')
    report=dict(status='PASS',utc=s.utc(),seconds=time.monotonic()-started,scalar_cue_scores=int(passed.size),
        categories=int(expected.size),pooled_rows=44,context_rows=n*44,paired_contrasts=33,
        methods='Scalar port scoring; independent count, margin and paired-block contrast reconstruction; no production scoring imports.')
    s.dump(output/'ANALYSIS_AUDIT.json',report)
    return report
