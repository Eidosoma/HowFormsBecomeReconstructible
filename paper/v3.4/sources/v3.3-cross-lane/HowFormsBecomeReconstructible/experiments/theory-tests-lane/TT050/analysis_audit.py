"""Independent CSV-based aggregation, paired harm and block-weight audit."""
from study import *
import csv, math

def audit(target):
    target=Path(target);result=read(target/'RESULTS.json');blocks=result['blocks'];cases={};count=0
    with (target/'CASES.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            key=tuple(int(row[x]) for x in ('block','source','founder','recipient','draw'))
            slot=(row['arm'],int(row['horizon']))
            if key not in cases:cases[key]={}
            assert slot not in cases[key];cases[key][slot]=row;count+=1
    assert len(cases)*len(LABELS)==count
    seed=int.from_bytes(hashlib.sha256(b'TT050/causal_analysis/v1').digest()[:16],'little')
    indices=np.random.Generator(np.random.PCG64(seed)).integers(0,len(blocks),size=(10000,len(blocks)))
    checked=0
    for panel,sources in [('mixture',{2,3}),('native',{0,1}),('all',{0,1,2,3})]:
        subset={k:v for k,v in cases.items() if k[1] in sources}
        for label,metrics in result['panels'][panel]['arms'].items():
            arm,hs=label.rsplit('_h',1);slot=(arm,int(hs))
            for metric,saved in metrics.items():
                vals=[float(v[slot][metric]) for v in subset.values()]
                assert saved['contexts']==len(vals)
                assert math.isclose(math.fsum(vals),saved['total'],abs_tol=2e-10)
                assert math.isclose(math.fsum(vals)/len(vals),saved['mean'],abs_tol=3e-15)
        for effect in result['panels'][panel]['effects']:
            horizon=effect['horizon'];coeff=effect['coefficients']
            for metric,saved in effect['metrics'].items():
                groups={b:[] for b in blocks};positive=negative=tied=0;table=[[0,0],[0,0]];feasible=[]
                treatment=next(a for a,c in coeff.items() if c==1);reference=next(a for a,c in coeff.items() if c==-1)
                for key,rows in subset.items():
                    x=float(rows[(treatment,horizon)][metric]);y=float(rows[(reference,horizon)][metric]);delta=x-y
                    groups[key[0]].append(delta);positive+=delta>0;negative+=delta<0;tied+=delta==0
                    if metric in ('both','opposite_rule_success'):table[int(y)][int(x)]+=1
                    if int(rows[(treatment,horizon)]['feasible']):feasible.append(delta)
                values=[math.fsum(groups[b])/len(groups[b]) for b in blocks]
                for a,b in zip(values,saved['block_values']):assert math.isclose(a,b,abs_tol=4e-15)
                assert math.isclose(math.fsum(values)/len(values),saved['estimate'],abs_tol=4e-15)
                assert [positive,negative,tied]==[saved[k] for k in ('positive_contexts','negative_contexts','tied_contexts')]
                if metric in ('both','opposite_rule_success'):assert table==saved['paired_table_reference_rows_treatment_columns']
                assert len(feasible)==saved['feasible_only']['contexts']
                if feasible:assert math.isclose(math.fsum(feasible)/len(feasible),saved['feasible_only']['mean'],abs_tol=4e-15)
                boot=sorted(math.fsum(values[i] for i in ids)/len(values) for ids in indices)
                def quantile(q):
                    pos=q*(len(boot)-1);i=int(pos);fraction=pos-i
                    return boot[i]+fraction*(boot[min(i+1,len(boot)-1)]-boot[i])
                expected=[quantile(.025),quantile(.975)]
                for a,b in zip(expected,saved['bootstrap_pointwise_95']):assert math.isclose(a,b,abs_tol=5e-15)
                bound=1 if metric in ('both','opposite_rule_success') else 4
                width=2*bound*math.sqrt(math.log(40)/(2*len(blocks)))
                center=math.fsum(values)/len(values);expected=[max(-bound,center-width),min(bound,center+width)]
                for a,b in zip(expected,saved['hoeffding_pointwise_95']):assert math.isclose(a,b,abs_tol=5e-15)
                checked+=1
    receipt=dict(status='PASS',utc=now(),case_rows=count,paired_metric_audits=checked,
        results_sha256=sha(target/'RESULTS.json'),cases_sha256=sha(target/'CASES.csv'),
        scalar_block_aggregation=True,independent_paired_tables=True,scalar_bootstrap_quantiles=True)
    write(target/'AUDIT.json',receipt);return receipt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('target');a=p.parse_args();print(json.dumps(audit(a.target)))
