"""Retain every case and independently verify paired harms at both endpoints."""
import csv
import json
import numpy as np
from common import dump

CONDITIONS=(('I0',0),('P0',4),('I1',9),('P1',13),('M1',18),('J1',22))
COMPARISONS=(('pruning_h0','I0','P0'),('pruning_h1','I1','P1'),
    ('magnitudes_h1','P1','M1'),('joint_h1','P1','J1'),
    ('signs_at_intact_magnitudes','M1','J1'),('intact_temporal','I0','I1'),('pruned_temporal','P0','P1'))


def rows_for(blocks,cases):
    rows=[]
    for block,case in zip(blocks,cases,strict=True):
        for arm in range(4):
            for founder,recipient in np.ndindex(case['both'].shape[1:]):
                row=dict(block=block,kind='native' if arm<2 else 'mixture',
                    history='sham' if arm%2==0 else 'pulse',founder=founder,recipient=recipient)
                for name,start in CONDITIONS:
                    loc=(start+arm,founder,recipient)
                    for metric in ('both','minimum_margin','transfer','aligned_transfer'):
                        v=case[metric][loc];row[f'{name}_{metric}']=int(v) if metric=='both' else float(v)
                    for c,label in enumerate(('plus','minus')):row[f'{name}_margin_{label}']=float(case['margin'][loc+(c,)])
                for name,a,b in COMPARISONS:row[name]=row[b+'_both']-row[a+'_both']
                rows.append(row)
    assert len(rows)==len(blocks)*4*cases[0]['both'].shape[1]*cases[0]['both'].shape[2]
    assert len({tuple(r[k] for k in ('block','kind','history','founder','recipient')) for r in rows})==len(rows)
    return rows


def summarize(rows):
    out={}
    for kind in ('native','mixture'):
        for history in ('pooled','sham','pulse'):
            selected=[r for r in rows if r['kind']==kind and (history=='pooled' or r['history']==history)]
            comparisons={}
            for name,a,b in COMPARISONS:
                gained=sum(r[a+'_both']==0 and r[b+'_both']==1 for r in selected)
                lost=sum(r[a+'_both']==1 and r[b+'_both']==0 for r in selected)
                comparisons[name]=dict(gained=gained,lost=lost,unchanged=len(selected)-gained-lost,
                    reference_successes=sum(r[a+'_both'] for r in selected),
                    treatment_successes=sum(r[b+'_both'] for r in selected),
                    mean_margin_change=sum(r[b+'_minimum_margin']-r[a+'_minimum_margin'] for r in selected)/len(selected),
                    mean_aligned_transfer_change=sum(r[b+'_aligned_transfer']-r[a+'_aligned_transfer'] for r in selected)/len(selected))
            table=[[0,0,0] for _ in range(3)]
            for r in selected:table[r['pruning_h0']+1][r['pruning_h1']+1]+=1
            out[kind+'_'+history]=dict(cases=len(selected),comparisons=comparisons,
                transition_order=['harm','unchanged','benefit'],h0_rows_h1_columns=table,
                immediate_benefit_later_harm=table[2][0],
                harmed_at_either_endpoint=sum(r['pruning_h0']<0 or r['pruning_h1']<0 for r in selected))
    return out


def audit(rows,counts,blocks,cases,summary):
    by_id={(r['block'],r['kind'],r['history'],r['founder'],r['recipient']):r for r in rows}
    starts={'I0':0,'P0':4,'I1':9,'P1':13,'M1':18,'J1':22}
    # Check all emitted cells directly against original arrays, including cue order.
    for block,case in zip(blocks,cases,strict=True):
        for arm,f,r in np.ndindex(4,4,case['both'].shape[2]):
            row=by_id[(block,('native','native','mixture','mixture')[arm],('sham','pulse')[arm%2],f,r)]
            for name,start in starts.items():
                loc=start+arm,f,r
                for metric in ('both','minimum_margin','transfer','aligned_transfer'):
                    assert row[name+'_'+metric]==case[metric][loc]
                assert row[name+'_margin_plus']==case['margin'][loc+(0,)]
                assert row[name+'_margin_minus']==case['margin'][loc+(1,)]
            for name,a,b in COMPARISONS:assert row[name]==int(case['both'][starts[b]+arm,f,r])-int(case['both'][starts[a]+arm,f,r])
    for kind,offset in (('native',0),('mixture',2)):
        for history in ('pooled','sham','pulse'):
            arms=[offset,offset+1] if history=='pooled' else [offset+int(history=='pulse')]
            arrays={name:np.stack([c['both'][[start+a for a in arms]] for c in cases]).astype(int).ravel() for name,start in starts.items()}
            q=counts[kind+'_'+history];assert q['cases']==arrays['I0'].size
            for name,a,b in COMPARISONS:
                delta=arrays[b]-arrays[a];result=q['comparisons'][name]
                assert result['gained']==np.count_nonzero(delta==1) and result['lost']==np.count_nonzero(delta==-1)
                assert result['unchanged']==np.count_nonzero(delta==0)
                assert result['reference_successes']==int(arrays[a].sum()) and result['treatment_successes']==int(arrays[b].sum())
                assert delta.mean()==summary['statistics'][f'effect/both/{history}/{kind}_{name}']['mean']
                for field,metric in (('mean_margin_change','minimum_margin'),('mean_aligned_transfer_change','aligned_transfer')):
                    expected=summary['statistics'][f'effect/{metric}/{history}/{kind}_{name}']['mean']
                    assert np.isclose(result[field],expected,rtol=0,atol=1e-14)
            d0=arrays['P0']-arrays['I0'];d1=arrays['P1']-arrays['I1']
            table=np.bincount((d0+1)*3+d1+1,minlength=9).reshape(3,3)
            np.testing.assert_array_equal(table,q['h0_rows_h1_columns'])
            assert q['harmed_at_either_endpoint']==int(np.count_nonzero((d0<0)|(d1<0)))
            assert q['immediate_benefit_later_harm']==int(np.count_nonzero((d0>0)&(d1<0)))


def export(run,blocks,cases,summary):
    rows=rows_for(blocks,cases);counts=summarize(rows)
    audit(rows,counts,blocks,cases,summary)
    path=run/'individual_effects.csv'
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Verify round-trip serialization as well as in-memory calculations.
    with path.open(newline='') as f:
        read=list(csv.DictReader(f))
    assert len(read)==len(rows)
    for row,other in zip(rows,read,strict=True):
        for k,value in row.items():assert (other[k] if isinstance(value,str) else type(value)(other[k]))==value
    dump(run/'individual_summary.json',counts)
    assert json.loads((run/'individual_summary.json').read_text())==counts
    return counts
