"""Fixed all-cohort comparisons with stratified whole-block uncertainty."""
import csv
import numpy as np
from common import arrays,read,write


def csv_write(path,rows):
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summary(values,cfg):
    values=np.asarray(values,float);assert values.shape==(16,)
    random=np.random.Generator(np.random.PCG64(cfg['bootstrap_seed']))
    selections=[]
    for h in range(4):
        indices=np.array([i for i,b in enumerate(cfg['blocks']) if cfg['history_by_block'][str(b)]==h])
        selections.append(indices[random.integers(4,size=(cfg['bootstrap_replicates'],4))])
    interval=np.quantile(values[np.concatenate(selections,axis=1)].mean(axis=1),[.025,.975])
    return dict(mean=float(values.mean()),by_block={str(b):float(v) for b,v in zip(cfg['blocks'],values)},
        descriptive_stratified_block_bootstrap_95=interval.tolist(),positive_blocks=int((values>0).sum()),tied_blocks=int((values==0).sum()),negative_blocks=int((values<0).sum()))


def analyze(folder,cfg):
    panel={b:arrays(folder/f'reads_{b:06d}.npz') for b in cfg['blocks']};reads=[];blocks=[];resources=[]
    for b,d in panel.items():
        for case in range(16):
            resources.append(dict(block=b,case=case,history=int(d['histories'][case]),pre_repair_pass=int(d['pre_repair_pass'][case]),
                missing_edges=int(d['missing_edge_counts'][case]),imputed_magnitude=float(d['imputed_magnitudes'][case]),
                added_abs_weight=float(d['added_abs_weight'][case]),shuffled_sign_changes=int(d['shuffled_sign_changes'][case])))
        for vi,name in enumerate(cfg['variants']):
            good=d['both_pass'][:,vi];other=d['opposite_pass'][:,vi]
            blocks.append(dict(block=b,history=int(d['histories'][0]),variant=name,reads=good.size,intended=int(good.sum()),opposite=int(other.sum())))
            for case in range(16):
                for ri,rep in enumerate(cfg['replicates']):
                    ports=d['mean_ports'][case,vi,ri].ravel()
                    reads.append(dict(block=b,case=case,history=int(d['histories'][case]),founder=int(d['founders'][case]),recipient=int(d['recipients'][case]),
                        variant=name,replicate=rep,pre_repair_pass=int(d['pre_repair_pass'][case]),intended=int(good[case,ri]),opposite=int(other[case,ri]),
                        margin=float(d['min_margin'][case,vi,ri]),opposite_margin=float(d['opposite_margin'][case,vi,ri]),
                        **dict(zip(('plus_a','plus_b','minus_a','minus_b'),map(float,ports)))))
    for name,rows in [('reads',reads),('block_summaries',blocks),('resources',resources)]:csv_write(folder/(name+'.csv'),rows)
    rates={}
    for vi,name in enumerate(cfg['variants']):
        rates[name]={label:dict(**summary([d[field][:,vi].mean() for d in panel.values()],cfg),
            successes=sum(int(d[field][:,vi].sum()) for d in panel.values()),reads=2048)
            for label,field in [('intended','both_pass'),('opposite','opposite_pass')]}
    contrasts={name:summary([(d['both_pass'][:,left].astype(float)-d['both_pass'][:,right]).mean() for d in panel.values()],cfg)
        for name,left,right in [('completion_minus_outgoing',1,0),('completion_minus_shuffled',1,2)]}
    opposite=summary([(d['opposite_pass'][:,1].astype(float)-d['opposite_pass'][:,0]).mean() for d in panel.values()],cfg)
    paired={}
    for name,right in [('completion_vs_outgoing',0),('completion_vs_shuffled',2)]:
        x=np.concatenate([d['both_pass'][:,1] for d in panel.values()]);y=np.concatenate([d['both_pass'][:,right] for d in panel.values()])
        paired[name]=dict(left_only=int((x&~y).sum()),right_only=int((y&~x).sum()),both=int((x&y).sum()),neither=int((~x&~y).sum()),reads=x.size)
    subgroups={}
    for label,flag in [('body_pass',True),('body_fail',False)]:
        selected=[d['both_pass'][d['pre_repair_pass']==flag] for d in panel.values()]
        joined=np.concatenate(selected);n=len(joined)
        subgroups[label]=dict(records=n,reads_per_variant=n*8,
            successes={name:int(joined[:,vi].sum()) for vi,name in enumerate(cfg['variants'])},
            rates={name:float(joined[:,vi].mean()) if n else None for vi,name in enumerate(cfg['variants'])},
            completion_minus_outgoing=float((joined[:,1].astype(float)-joined[:,0]).mean()) if n else None)
    histories={}
    for hi,name in enumerate(cfg['histories']):
        selected=[d['both_pass'] for b,d in panel.items() if cfg['history_by_block'][str(b)]==hi]
        joined=np.concatenate(selected)
        histories[name]=dict(blocks=4,records=64,rates={v:float(joined[:,vi].mean()) for vi,v in enumerate(cfg['variants'])},
            completion_minus_outgoing=float((joined[:,1].astype(float)-joined[:,0]).mean()))
    result=dict(status='NEW_LINEAGE_ANALYSIS_COMPLETE',blocks=16,records=256,read_contexts=len(reads),rates=rates,contrasts=contrasts,
        primary_direction_observed=contrasts['completion_minus_outgoing']['mean']>0,opposite_task_primary_effect=opposite,
        paired_counts=paired,body_subgroups=subgroups,history_summaries=histories,fitted_parameters=0,
        interpretation='Frozen conventional repair on newly generated lineages within the same simulator; not unique RDT confirmation.')
    write(folder/'analysis.json',result);return result


def render(folder,cfg):
    a=read(folder/'analysis.json');assert read(folder/'VERIFICATION.json')['status']=='PASS'
    primary=a['contrasts']['completion_minus_outgoing'];lo,hi=primary['descriptive_stratified_block_bootstrap_95']
    judgment=('The primary directional forecast failed.' if primary['mean']<=0 else
        'The primary estimate is positive but its descriptive interval includes zero.' if lo<=0 else
        'The primary estimate and its descriptive interval are positive.')
    lines=['# Frozen repair on new lineages','',
        f"Completion minus outgoing success is {primary['mean']*100:+.2f} percentage points, with a descriptive 95% stratified block-bootstrap interval [{lo*100:+.2f}, {hi*100:+.2f}]. {judgment}",'',
        'All 256 records from 16 new blocks were retained. The repair was frozen before these lineages were generated. Four blocks represent each writer history; no records were selected for failure. The primary population is the full balanced cohort.','',
        '| Record | Intended success | Opposite success | Intended count |','|---|---:|---:|---:|']
    for name in cfg['variants']:
        r=a['rates'][name];lines.append(f"| {name} | {r['intended']['mean']*100:.2f}% | {r['opposite']['mean']*100:.2f}% | {r['intended']['successes']}/{r['intended']['reads']} |")
    lines+=['','Blocks are the inference units. Percentages weight all blocks equally; pooled counts have the same weighting here because every block has the same enrollment and draws.','',
        '| Prespecified contrast | Difference pp | Descriptive 95% interval pp | Blocks positive / tied / negative |','|---|---:|---:|---:|']
    for name,e in a['contrasts'].items():
        l,h=e['descriptive_stratified_block_bootstrap_95'];lines.append(f"| {name} | {e['mean']*100:+.2f} | [{l*100:+.2f}, {h*100:+.2f}] | {e['positive_blocks']} / {e['tied_blocks']} / {e['negative_blocks']} |")
    lines+=['','| Generation 14 body | Records | Outgoing success | Completion success | Difference pp |','|---|---:|---:|---:|---:|']
    for name,s in a['body_subgroups'].items():
        vals=['NA']*3 if not s['records'] else [f"{s['rates']['outgoing']*100:.2f}%",f"{s['rates']['recipient_completion']*100:.2f}%",f"{s['completion_minus_outgoing']*100:+.2f}"]
        lines.append(f"| {name} | {s['records']} | {' | '.join(vals)} |")
    lines+=['','Body subgroups are descriptive and cannot replace the primary comparison. Missing subgroups are explicit. History-specific means and paired rescue/harm counts are retained in analysis.json.','',
        'This evaluates one subsequent reconstruction under new injury and native matched cue noise. It does not test repeated repair. The surviving record already contains acquired information; the lattice, input ports, algorithm, reader and added edge resources remain supplied. A negative result rejects general benefit for this frozen rule and population, not every possible repair. A positive result supports conventional reconstruction and does not uniquely confirm RDT. No equivalence or noninferiority claim is specified.','',
        'Known teaching and renewal controls replayed exactly before launch. New teaching, all captures, all repair constructions, selected generation-14 and assessment reads, raw-window scores, CSV tables, block/history/subgroup summaries, paired counts and stratified bootstrap intervals were checked within this lane. Developmental damage uses the shared native generator; assessment masks are independently reconstructed. This is not external replication.','',
        'All teaching states, lineage boundaries, repair diagnostics, raw reads and input/output hashes are retained. No automatic successor is launched.','']
    with (folder/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
