"""Complete descriptive readout tables. No population intervals or forecasts."""
import json
from pathlib import Path

import numpy as np
import support as s


def run(output):
    output=Path(output);index=json.loads((output/'EVENTS.json').read_text());cfg=index['cfg'];contexts=index['contexts']
    collected=[]
    for entry in index['events']:
        with np.load(output/entry['path'],allow_pickle=False) as z:
            collected.append(z['mean_ports'].reshape(11,4,cfg['masks_per_context'],2,2,2))
    means=np.stack(collected);scored=[s.score(means[i],row['rule'],cfg['margin']) for i,row in enumerate(contexts)]
    arrays={k:np.stack([v[k] for v in scored]) for k in scored[0]}
    arrays['mean_ports']=means
    with (output/'observations.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    cat=arrays['category'];cue=arrays['cue_success'];am=arrays['ancestral_margin']
    blocks=sorted({row['block'] for row in contexts});rows=[];context_rows=[];contrasts=[]
    for p,name in enumerate(s.NAMES):
        for c,(condition,_,_) in enumerate(s.PLAN['assay_pairings']):
            y=cat[:,p,c];n=y.size;counts=np.bincount(y.ravel(),minlength=3)
            rows.append(dict(packet=name,assay_pairing=condition,assays=int(n),
                category_counts=dict(ancestral=int(counts[0]),opposite=int(counts[1]),neither=int(counts[2])),
                ancestral_rate=float((y==0).mean()),opposite_rate=float((y==1).mean()),
                cue_success_counts=cue[:,p,c].sum(axis=(0,1,2)).tolist(),
                mean_cue_margins=am[:,p,c].mean(axis=(0,1,2)).tolist(),
                mean_worst_cue_margin=float(am[:,p,c].min(axis=-1).mean()),
                duplicate_disagreements=int((y[:,:,0]!=y[:,:,1]).sum()),duplicate_pairs=int(y.shape[0]*y.shape[1])))
            for i,context in enumerate(contexts):
                yy=y[i]
                context_rows.append(dict(context_id=context['id'],block=context['block'],packet=name,assay_pairing=condition,
                    category_counts=np.bincount(yy.ravel(),minlength=3).tolist(),cue_success_counts=cue[i,p,c].sum(axis=(0,1)).tolist(),
                    duplicate_disagreements=int((yy[:,0]!=yy[:,1]).sum()),
                    mean_cue_margins=am[i,p,c].mean(axis=(0,1)).tolist()))
        baseline=cat[:,p,0]==0
        for c,(condition,_,_) in enumerate(s.PLAN['assay_pairings'][1:],start=1):
            current=cat[:,p,c]==0;block_rows=[]
            for block in blocks:
                take=[i for i,row in enumerate(contexts) if row['block']==block]
                before,after=baseline[take],current[take]
                block_rows.append(dict(block=block,contexts=len(take),assay_pairs=int(before.size),
                    difference=float(after.mean()-before.mean()),rescued=int((~before&after).sum()),harmed=int((before&~after).sum()),
                    both_pass=int((before&after).sum()),both_fail=int((~before&~after).sum()),
                    cue_difference=(cue[take,p,c].mean(axis=(0,1,2))-cue[take,p,0].mean(axis=(0,1,2))).tolist()))
            contrasts.append(dict(packet=name,contrast=condition+' minus matched',
                main_descriptive=condition=='independent_both' and p<9,
                mean_block_difference=float(np.mean([b['difference'] for b in block_rows])),
                rescued=int((~baseline&current).sum()),harmed=int((baseline&~current).sum()),blocks=block_rows))
    invariant=all(np.array_equal(means[:,:,c,:,:,0],means[:,:,0,:,:,0]) for c in range(1,4))
    if not invariant:raise ValueError('First cue changed across pairing conditions')
    summary=dict(study='TT005',mode=index['mode'],classification='DEVELOPMENT' if index['mode']=='pilot' else 'TECHNICAL_EXCLUSION',
        contexts=contexts,blocks=blocks,independent_block_count=len(blocks),packet_names=s.NAMES,assay_pairings=s.PLAN['assay_pairings'],
        masks_per_context=cfg['masks_per_context'],replicates_per_mask=2,paired_cue_assays=int(cat.size),native_rebuilds=0,
        first_cue_bit_identical_across_conditions=invariant,rows=rows,context_rows=context_rows,contrasts=contrasts,
        interval_method=None,inference_scope='Complete descriptive counts on fixed development packets; repeated assays and packet types are not independent source blocks.',
        selection_note='Fixed accepted identifiers; no selection or exclusion by new assay outcome.',
        rdt_verdict='NOT_A_CONFIRMATORY_TEST',native_forecast='ABSTAIN')
    s.dump(output/'summary.json',summary)
    report(output,summary)
    return summary


def report(output,summary):
    lines=['# TT005 repeated terminal readout', '',
        f"Status: {summary['classification']}; {summary['paired_cue_assays']} paired-cue assays, {summary['independent_block_count']} blocks. No rebuilding or record writing.", '',
        'A denotes strict expression of the original founder rule; B denotes the opposite rule; N denotes neither. Each cue must satisfy both signed-port margins >.25. Counts include every planned assay.', '',
        '| Packet history / writer | Terminal pairing | A / B / N | Cue + / cue − successes | Duplicate disagreements / pairs |',
        '| --- | --- | ---: | ---: | ---: |']
    for row in summary['rows']:
        v=row['category_counts'];q=row['cue_success_counts']
        lines.append(f"| {row['packet']} | {row['assay_pairing']} | {v['ancestral']} / {v['opposite']} / {v['neither']} | {q[0]} / {q[1]} | {row['duplicate_disagreements']} / {row['duplicate_pairs']} |")
    lines+=['','## Fully independent minus matched terminal pairing','',
        '| Packet history / writer | Mean block difference (points) | Rescued / harmed paired assays | Block differences (points) |',
        '| --- | ---: | ---: | --- |']
    for row in summary['contrasts']:
        if not row['main_descriptive']:continue
        blocks=', '.join(f"{b['block']}: {100*b['difference']:.2f}" for b in row['blocks'])
        lines.append(f"| {row['packet']} | {100*row['mean_block_difference']:.2f} | {row['rescued']} / {row['harmed']} | {blocks} |")
    lines+=['','All singly perturbed contrasts, per-context counts and continuous margins are retained in summary.json and observations.npz. The first cue is byte-identical across terminal conditions, as required by the shared-base construction.', '',
        'Changing cue dependence can change both-cue success without changing marginal cue probabilities. The experiment holds each inherited packet fixed. A changed joint score therefore does not alone establish loss of its stored rule. Duplicate assays share physical damage but redraw recipient state/noise; their disagreement is not an independent-fresh-damage statistic.', '',
        'These are descriptive results for fixed exposed packets. No confidence intervals, p-values, equivalence claim or full-model forecast qualification is issued. Full-model native forecasting remains ABSTAIN. Teaching and the histories that produced these packets retain their E051 definitions.', '',
        'Separate dynamics and scalar analysis audit results are retained in DYNAMICS_AUDIT.json and ANALYSIS_AUDIT.json. COMPLETE.json is required before treating this workflow as finished.']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rates=np.array([r['ancestral_rate'] for r in summary['rows']]).reshape(11,4)
    discord=np.array([r['duplicate_disagreements']/r['duplicate_pairs'] for r in summary['rows']]).reshape(11,4)
    fig,axes=plt.subplots(1,2,figsize=(13,7.4),layout='constrained')
    for ax,data,title in zip(axes,[rates,discord],['Ancestral both-cue success','Duplicate category disagreement']):
        im=ax.imshow(data,vmin=0,vmax=1,cmap='viridis',aspect='auto')
        ax.set_xticks(range(4),['matched','noise only','reset only','both'],rotation=20,ha='right')
        ax.set_yticks(range(11),s.NAMES,fontsize=8);ax.set_title(title)
        for i,j in np.ndindex(data.shape):ax.text(j,i,f'{data[i,j]:.2f}',ha='center',va='center',fontsize=9,color='black' if data[i,j]>.6 else 'white')
        fig.colorbar(im,ax=ax,shrink=.7)
    fig.suptitle(f"TT005 {summary['classification']}: fixed packets; descriptive repeated assays\n{summary['independent_block_count']} source blocks; no population intervals")
    fig.savefig(output/'readout.png',dpi=160);plt.close(fig)
