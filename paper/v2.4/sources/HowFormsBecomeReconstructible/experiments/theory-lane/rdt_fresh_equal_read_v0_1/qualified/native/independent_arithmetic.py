"""Independent saved-evidence arithmetic audit; no study implementation imports."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def read(p):return json.loads(Path(p).read_text())


def load(p):
    with np.load(p,allow_pickle=False) as z:
        index=json.loads(z['__index__'].tobytes())
        assert set(z.files)==set(index)|{'__index__'}
        data={k:z[k] for k in index}
    for k,a in data.items():
        assert index[k]==dict(shape=list(a.shape),dtype=a.dtype.str,sha256=hashlib.sha256(a.tobytes()).hexdigest())
        assert a.dtype.kind!='f' or np.isfinite(a).all()
    return data


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def probability(boundary,extra,model):
    values=list(boundary)+([] if extra is None else [extra]);state=model['model']
    z=[(v-m)/s for v,m,s in zip(values,state['scaling']['mean'],state['scaling']['scale'],strict=True)]
    eta=state['coefficients'][0]+math.fsum(c*v for c,v in zip(state['coefficients'][1:],z,strict=True))
    return 1/(1+math.exp(-eta)) if eta>=0 else math.exp(eta)/(1+math.exp(eta))


def audit_run(inputs,run):
    inputs,run=Path(inputs),Path(run);p=read(inputs/'protocol.json');models=read(inputs/'FROZEN_MODELS.json')
    assert sha(inputs/'FROZEN_MODELS.json')==p['models']['sha256']
    for name,digest in read(inputs/'INPUTS.json')['sha256'].items():assert sha(inputs/name)==digest
    enrollment=read(run/'ENROLLMENT.json')['records'];selection=read(run/'SELECTION.json')['records']
    assert len(enrollment)==1024 and len({tuple(r['key']) for r in enrollment})==1024
    all_arrays=0;native_reads=0;flat_reads=0
    for block in p['acquisition']['blocks']:
        receipt=read(run/f'acquisition/acquisition_{block:06d}.json')
        assert receipt['max_generation']==14 and receipt['native_reads']==896 and receipt['flat_native_reads']==12
        assert receipt['teaching']['byte_exact'] and all(v['byte_exact'] for v in receipt['audits'])
        native_reads+=896;flat_reads+=12
        load(run/f'acquisition/teaching_{block:06d}.npz');all_arrays+=1
        for g in range(1,15):
            raw=load(run/f'acquisition/boundary_{block:06d}_g{g:02d}.npz');all_arrays+=1
            assert raw['outgoing'].shape==(4,4,4,4096)
        for row in [r for r in enrollment if r['block']==block]:
            h=p['acquisition']['histories'].index(row['history']);ix=(h,row['founder'],row['recipient'])
            packet=raw['outgoing'][ix]
            assert hashlib.sha256(packet.tobytes()).hexdigest()==row['packet_sha256']
            aligned=(raw['mean_ports'][ix]*row['rule']*np.array([[1,-1],[-1,1]])).ravel()
            assert np.array_equal(aligned,np.array(row['boundary'][:4]))
            assert row['current_pass']==int(min(aligned)>.25)==int(row['boundary'][5])
            rank=hashlib.sha256(json.dumps([p['selection']['namespace'],*row['key']],separators=(',',':')).encode()).hexdigest()
            assert rank==row['selection_hash']
    expected=[]
    for block in p['acquisition']['blocks']:
        for c in (0,1):
            rows=sorted([r for r in enrollment if r['block']==block and r['current_pass']==c],key=lambda r:r['selection_hash'])
            groups=[[r for r in rows if r['rule']==v] for v in (-1,1)]
            expected.extend([v[0] for v in groups] if all(groups) else rows[:2])
    assert selection==expected
    cases=read(run/'CASES.json');predictions=read(run/'FORECASTS.json');result=read(run/'ANALYSIS.json')
    assert len(cases)==len(predictions)==2*len(selection)
    by_key={tuple(r['key']):r for r in selection};rebuilt=[];maximum_error=0.
    for case,forecast in zip(cases,predictions,strict=True):
        assert case['key']==forecast['key'] and case['regime']==forecast['regime']
        row=by_key[tuple(case['key'])];path=run/'measurements'/case['source']
        assert sha(path.with_suffix('.npz'))==case['raw_sha256']
        raw=load(path.with_suffix('.npz'));all_arrays+=1
        receipt=read(path.with_suffix('.json'))
        assert receipt['native_reads']==144 and receipt['flat_native_reads']==6
        assert [r['probe'] for r in receipt['audits']]==[0,32] and all(r['byte_exact'] for r in receipt['audits'])
        native_reads+=144;flat_reads+=6
        assert np.array_equal(raw['probes'],np.arange(64)) and np.array_equal(raw['direct_probes'],np.r_[0:8,32:40])
        assert hashlib.sha256(raw['packet'].tobytes()).hexdigest()==row['packet_sha256']
        counts={}
        for branch,n in [('writer',64),('successor',64),('direct',16)]:
            windows=raw[branch+'_windows'];assert windows.shape==(n,32,1,2,2)
            mean=np.array([math.fsum(v)/32 for v in windows.transpose(0,2,3,4,1).reshape(-1,32)]).reshape(n,1,2,2)
            aligned=mean*row['rule']*np.array([[1.,-1.],[-1.,1.]])
            maximum_error=max(maximum_error,float(np.max(abs(aligned-raw[branch+'_aligned']))))
            assert maximum_error<=1e-12
            passed=(aligned.min(axis=(-1,-2))>.25).astype(np.uint8)
            assert np.array_equal(passed,raw[branch+'_passed'])
            counts[branch]=passed[:,0]
        q=[float(v.mean()) for v in counts['successor'].reshape(2,32)]
        d=[float(v.mean()) for v in counts['direct'].reshape(2,8)]
        assert q==forecast['q_rewrite'] and d==forecast['q_direct']
        values=dict(candidate=[probability(row['boundary'],v,models['candidate']) for v in q],
                    direct_rival=[probability(row['boundary'],v,models['direct_rival']) for v in d],
                    tt008=[probability(row['boundary'],None,models['tt008'])]*2)
        delta={}
        for model,values0 in values.items():
            assert np.allclose(values0,forecast['probabilities'][model],rtol=0,atol=1e-12)
            delta[model]=abs(values0[1]-values0[0])
            assert abs(delta[model]-forecast['differences'][model])<=1e-12
        rebuilt.append(dict(block=row['block'],current_pass=row['current_pass'],regime=case['regime'],differences=delta))
    coverage=all(sum(r['current_pass']==c for r in selection)>=24 and
                 len({r['block'] for r in selection if r['current_pass']==c})>=12 for c in (0,1))
    precision=True
    for model in models:
        if model not in ('candidate','direct_rival','tt008'):continue
        for regime in ('matched','independent'):
            for c in (0,1):
                values=[r['differences'][model] for r in rebuilt if r['regime']==regime and r['current_pass']==c]
                saved=result['groups'][model][regime][str(c)]
                assert saved['records']==len(values)
                if values:
                    q=float(np.quantile(values,.9))
                    assert abs(q-saved['p90'])<=1e-12 and abs(max(values)-saved['maximum'])<=1e-12
                    assert saved['exceedances']==sum(v>.1 for v in values)
                    if model=='candidate':precision &= q<=.10
                elif model=='candidate':precision=False
    decision='FRESH_PRECISION_COVERAGE_INSUFFICIENT' if not coverage else 'FRESH_PRECISION_SCREEN_PASS' if precision else 'FRESH_PRECISION_SCREEN_FAILED'
    assert result['decision']==decision and result['coverage']['passed']==coverage and result['candidate_precision_pass']==precision
    return dict(status='PASS',scientific_decision=decision,committed_raw_files_verified=all_arrays,
        fresh_boundary_records_checked=len(enrollment),selected_records_checked=len(selection),case_regimes_checked=len(cases),
        source_native_reads=native_reads,source_flat_audit_reads=flat_reads,
        maximum_independent_window_mean_error=maximum_error,
        selection_and_all_predictions_and_precision_gates_independently_verified=True,
        bootstrap_intervals_scope='Descriptive implementation checked by qualification; not independently recalculated here.',
        new_native_reads=0,new_model_fits=0,new_future_outcomes=0)
