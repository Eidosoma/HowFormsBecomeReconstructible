"""One declared development pass; no new dynamics or fresh-cohort outcomes."""
import time
from pathlib import Path
import numpy as np
from common import ROOT,read,write,sha,arrays,save_arrays,equal,stamp
import warning
import audit_warning


def main():
    cfg=read(ROOT/'config.json');source=Path(cfg['development_run']);output=ROOT/'development'
    output.mkdir(exist_ok=False);started=time.process_time()
    bindings={str(source/'COMPLETE.json'):cfg['development_complete_sha256']}
    assert sha(source/'COMPLETE.json')==cfg['development_complete_sha256']
    receipt=read(source/'COMPLETE.json');frozen=read(ROOT/'DEVELOPMENT_FREEZE.json')
    for k,v in frozen['files_sha256'].items():assert sha(ROOT/k)==v,k
    columns={k:[] for k in ('features','failure','block','generation','arm','case')}
    native_cfg=read(source/'inputs/config.json');blocks=native_cfg['blocks']
    for b in blocks:
        path=source/f'continuation_{b:06d}.npz';digest=receipt['outputs_sha256'][path.name]
        bindings[str(path)]=digest;d=arrays(path,digest)
        target=np.repeat([1.,-1.,1.,-1.],4)[:,None,None]*np.array([[1.,-1.],[-1.,1.]])
        good=(d['port_windows'].mean(axis=1)*target).min(axis=(-2,-1))>.25
        equal(good,d['both_pass'],'development labels recomputed from saved raw windows')
        for gi in range(1,18):
            for arm in (0,1):
                assert not d['applied'][gi,arm].any()
                cases=np.flatnonzero(good[:gi,arm].all(axis=0))
                packets=d['incoming'][gi,arm,cases]
                x=warning.features(packets);other=audit_warning.features(packets)
                np.testing.assert_allclose(x,other,rtol=2e-13,atol=2e-15)
                n=len(cases)
                for k,v in dict(features=x,failure=~good[gi,arm,cases],block=np.full(n,b),
                    generation=np.full(n,gi+15),arm=np.full(n,arm),case=cases).items():columns[k].append(v)
    data={k:np.concatenate(v) for k,v in columns.items()}
    designs=dict(intercept=np.zeros((len(data['failure']),0)),generation=data['generation'][:,None],
                 missing_edge=data['features'][:,:1],six_record_features=data['features'])
    all_metrics={};models={};heldout={}
    for name,x in designs.items():
        predictions=np.zeros(len(x));folds={}
        for b in blocks:
            test=data['block']==b;train=~test
            assert not set(data['block'][train])&set(data['block'][test])
            fitted=warning.fit(x[train],data['failure'][train]);predictions[test]=warning.predict(fitted,x[test]);folds[str(b)]=fitted
        fitted=warning.fit(x,data['failure']);models[name]=dict(full=fitted,folds=folds)
        all_metrics[name]=warning.metrics(data['failure'],predictions);heldout['prediction_'+name]=predictions
    selected=models['six_record_features']['full'];scores=np.sort(warning.predict(selected,data['features']))
    write(output/'MODEL.json',dict(status='FROZEN_WARNING',at_utc=stamp(),feature_names=warning.NAMES,model=selected,
        calibration_sorted_scores=scores.tolist(),selection='Fixed before development, not selected by cross-validation rank.'))
    data_hash=save_arrays(output/'dataset.npz',dict(**data,**heldout))
    write(output/'FIT_DETAILS.json',models)
    result=dict(status='COMPLETE',at_utc=stamp(),new_scientific_outcomes=0,rows=len(scores),events=int(data['failure'].sum()),
        independent_blocks=len(blocks),feature_audit='all rows flat implementation agrees',metrics=all_metrics,
        events_by_block={str(b):int(data['failure'][data['block']==b].sum()) for b in blocks},
        events_by_arm={name:int(data['failure'][data['arm']==v].sum()) for v,name in ((0,'baseline'),(1,'one_time'))},
        cpu_seconds=time.process_time()-started,sources_sha256=bindings,design_freeze_sha256=sha(ROOT/'DEVELOPMENT_FREEZE.json'),
        outputs_sha256={'dataset.npz':data_hash,'MODEL.json':sha(output/'MODEL.json'),'FIT_DETAILS.json':sha(output/'FIT_DETAILS.json')})
    write(output/'COMPLETE.json',result)
    print(__import__('json').dumps({k:result[k] for k in ('rows','events','independent_blocks','metrics','cpu_seconds')},indent=2),flush=True)


if __name__=='__main__':main()
