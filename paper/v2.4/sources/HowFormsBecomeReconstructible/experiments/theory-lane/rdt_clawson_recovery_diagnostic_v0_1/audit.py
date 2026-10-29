"""Scalar endpoint, contingency-table and loss checks independent of vector reducers."""
import csv
import json
import math
import numpy as np
from analyze import ROOT, OUT, P, SOURCE, Source, sha, save


def scalar_states(windows, rule):
    output=[]
    for sample in np.asarray(windows).reshape(-1,32,1,2,2):
        means=[math.fsum(sample[:,0,i,j].tolist())/32*rule*sign
               for i,j,sign in [(0,0,1),(0,1,-1),(1,0,-1),(1,1,1)]]
        output.append(1 if all(x>.25 for x in means) else -1 if all(x<-.25 for x in means) else 0)
    return output


def counts(rows):
    c=[[[0,0],[0,0]],[[0,0],[0,0]]]
    for row in rows:
        for w,s,d in zip(row['writer'],row['successor'],row['direct32'],strict=True):
            c[w][s][d]+=1
    return c


def check_summary(expected,c):
    assert expected['counts_W_S_D']==c
    for label,states in [('all',[0,1]),('writer_fail',[0]),('writer_pass',[1])]:
        entries=[(s,d,c[w][s][d]) for w in states for s in (0,1) for d in (0,1)]
        n=sum(v for s,d,v in entries)
        succ=sum(s*v for s,d,v in entries); direct=sum(d*v for s,d,v in entries)
        v=expected[label]
        assert (v['n'],v['successor_successes'],v['direct_successes'])==(n,succ,direct)
        assert v['helped']==sum(k for s,d,k in entries if s==1 and d==0)
        assert v['harmed']==sum(k for s,d,k in entries if s==0 and d==1)
        for field,value in [('successor_rate',succ),('direct_rate',direct),('paired_benefit',succ-direct)]:
            assert v[field] is None if not n else abs(v[field]-value/n)<1e-12


def matrix_multiply(a,b):
    return [[math.fsum(a[i][k]*b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def matrix_power(a,n):
    v=[[1.,0.],[0.,1.]]
    while n:
        if n&1: v=matrix_multiply(v,a)
        a=matrix_multiply(a,a);n//=2
    return v


def audit():
    source=Source()
    ms=json.loads((OUT/'MEASUREMENTS.json').read_text())
    ts=json.loads((OUT/'TRAJECTORIES.json').read_text())
    result=json.loads((OUT/'RESULTS.json').read_text())
    seal=json.loads((OUT/'FORECAST_SEAL.json').read_text())
    assert sha(OUT/'MEASUREMENTS.json')==seal['measurements_sha256']
    assert len(ms)==64 and len(ts)==256
    probes_checked=0
    for m in ms:
        sr=source.read(m['case']+'/successor32.json')
        dr=source.read(m['case']+'/direct64.json')
        with source.array(m['case']+'/successor32.npz',sr['raw_sha256']) as s, source.array(m['case']+'/direct64.npz',dr['raw_sha256']) as d:
            wc=scalar_states(s['writer_windows'],m['rule'])
            sc=scalar_states(s['successor_windows'],m['rule'])
            dc=scalar_states(d['direct_windows'],m['rule'])
        assert wc==m['writer_classes'] and sc==m['successor_classes'] and dc[:32]==m['direct32_classes']
        assert [int(x==1) for x in wc]==m['writer']
        assert [int(x==1) for x in sc]==m['successor']
        assert [int(x==1) for x in dc]==m['direct64']
        c=counts([m]);check_summary(m['joint'],c)
        n0=sum(v for s in c[0] for v in s);n1=sum(v for s in c[1] for v in s)
        r=(sum(c[0][1])+.5)/(n0+1);e=(sum(c[1][0])+.5)/(n1+1);p0=(n1+.5)/33
        k=[[1-e,e],[r,1-r]]
        for h,p in enumerate(m['transition']['trajectory']):
            kh=matrix_power(k,h)
            assert abs(p-(p0*kh[0][0]+(1-p0)*kh[1][0]))<1e-12
        assert abs(m['probabilities']['transition64_jeffreys']-m['transition']['trajectory'][-1])<1e-12
        assert abs(m['probabilities']['raw_successor64_jeffreys']-(sum(m['successor'])+.5)/33)<1e-12
        assert abs(m['probabilities']['raw_direct64_jeffreys']-(sum(m['direct64'])+.5)/65)<1e-12
        probes_checked+=128
    by_key={tuple(m['key']):m['rule'] for m in ms}
    for name in sorted({t['source'] for t in ts}):
        receipt=source.read(name[:-4]+'.json')
        with source.array(name,receipt['raw_sha256']) as a:
            for t in [x for x in ts if x['source']==name]:
                classes=scalar_states(a['windows'][:,t['source_index']],by_key[tuple(t['key'])])
                assert classes==t['classes']
                bits=[int(v==1) for v in classes]
                assert bits==t['passed'] and int(all(bits))==t['uninterrupted'] and bits[-1]==t['terminal']
    mby={(tuple(m['key']),m['noise']):m for m in ms}
    brier_checks=0
    for noise,groups in result['cells'].items():
        for state,group in groups.items():
            selected=[m for m in ms if m['noise']==noise and (state=='balanced' or m['original_class']==int(state))]
            futures=[t for t in ts if t['noise']==noise and (state=='balanced' or t['original_class']==int(state))]
            check_summary(group['paired'],counts(selected))
            for block in P['scope']['blocks']:
                check_summary(group['founder_paired'][str(block)],counts([m for m in selected if m['block']==block]))
                check_summary(group['leave_one_founder_out_paired'][str(block)],counts([m for m in selected if m['block']!=block]))
            for model,v in group['models'].items():
                by_block=[]
                for b in P['scope']['blocks']:
                    ys=[t for t in futures if t['block']==b]
                    loss=math.fsum((mby[tuple(t['key']),noise]['probabilities'][model]-t['terminal'])**2 for t in ys)/len(ys)
                    by_block.append(loss)
                assert max(abs(x-y) for x,y in zip(by_block,v['founder_brier'],strict=True))<1e-12
                assert abs(math.fsum(by_block)/8-v['brier'])<1e-12
                brier_checks+=1
            for t in range(19):
                assert abs(group['observed_trajectory'][t]-sum(x['passed'][t] for x in futures)/len(futures))<1e-12
                assert abs(group['predicted_transition_trajectory'][t]-math.fsum(x['transition']['trajectory'][t] for x in selected)/len(selected))<1e-12
    # Previously audited forecasts must keep exactly their original scores.
    table_path=SOURCE.parents[1]/'closeout/v1/ALL_27_MODELS.csv'
    closeout=json.loads((table_path.parent/'COMPLETE.json').read_text())
    assert sha(table_path.parent/'COMPLETE.json')==P['source_closeout_sha256']
    assert sha(table_path)==closeout['table_sha256']
    with table_path.open() as f:
        old=list(csv.DictReader(f))
    for row in old:
        new=result['cells'][row['noise']][row['original_class']]['models'][row['model']]['brier']
        assert abs(new-float(row['brier']))<1e-12
    assert len(old)==162 and brier_checks==180 and probes_checked==8192
    receipt=dict(status='PASS',probe_readouts_checked=probes_checked,trajectory_readouts_checked=256*19,
        paired_probe_triples_checked=2048,scalar_model_cell_brier_checks=brier_checks,
        unchanged_fixed_model_cell_checks=len(old),matrix_forecast_checks=64*19,
        new_native_reads=0,new_outcomes=0,new_fits=0,audit_source_files=len(source.used))
    save('AUDIT.json',receipt)
    return receipt
