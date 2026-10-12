"""Supplemental, explicitly synthetic assay tables for nondegenerate scoring checks.

The short native fixture produced only N categories. These constructed port
arrays test mixed A/B/N, strict-threshold and repeated-pair accounting using the
already frozen implementation. They are not dynamics or scientific evidence.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent/'jobs/fixture_v1/inputs/TT005'
sys.path.insert(0,str(FROZEN))
import numpy as np
import support as s
import analyze
import analysis_audit


def main():
    output=HERE/'analysis_examples_v1';output.mkdir(exist_ok=False)
    folder=output/'events';folder.mkdir()
    contexts=[dict(id=f'engineered_{i}',block=900101+i//2,founder=i%2,recipient=0,rule=1 if i%2==0 else -1,
                   scientific_exclusion=True) for i in range(4)]
    entries=[];truth=np.empty((4,11,4,2,2),np.int8);cue_truth=np.empty((*truth.shape,2),bool)
    for i,context in enumerate(contexts):
        ports=np.empty((11,4,2,2,2,2))
        for p,c,m,r in np.ndindex(11,4,2,2):
            kinds=[(i+p+2*m+r)%4,(i+2*p+m+2*r+c)%4]
            for cue,kind in enumerate(kinds):
                magnitude=[.8,-.8,.25,.1][kind]
                signed=context['rule']*[1.,-1.][cue]*magnitude
                ports[p,c,m,r,cue]=[signed,-signed]
                cue_truth[i,p,c,m,r,cue]=kind==0
            truth[i,p,c,m,r]=0 if kinds==[0,0] else 1 if kinds==[1,1] else 2
        path=folder/(context['id']+'.npz')
        np.savez_compressed(path,mean_ports=ports.reshape(11,4,4,2,2))
        entries.append(dict(path=str(path.relative_to(output)),context_id=context['id']))
    s.dump(output/'EVENTS.json',dict(mode='fixture',cfg=s.config('fixture'),contexts=contexts,events=entries,
        note='Hand-constructed mean ports. Not a physical simulation; no dynamics audit is claimed.'))
    summary=analyze.run(output);audit=analysis_audit.audit(output)
    with np.load(output/'observations.npz',allow_pickle=False) as z:
        np.testing.assert_array_equal(z['category'],truth);np.testing.assert_array_equal(z['cue_success'],cue_truth)
    counts=np.bincount(truth.ravel(),minlength=3)
    assert (counts>0).all()
    assert any(r['duplicate_disagreements']>0 for r in summary['rows'])
    assert any(r['rescued']>0 for r in summary['contrasts']) and any(r['harmed']>0 for r in summary['contrasts'])
    for row in summary['rows']:
        p=s.NAMES.index(row['packet']);c=[v[0] for v in s.PLAN['assay_pairings']].index(row['assay_pairing'])
        expected={name:int(np.count_nonzero(truth[:,p,c]==k)) for k,name in enumerate(['ancestral','opposite','neither'])}
        assert row['category_counts']==expected
    sources={str(FROZEN/name):s.sha(FROZEN/name) for name in ['support.py','analyze.py','analysis_audit.py','plan.json']}
    report=dict(status='PASS',utc=s.utc(),scope='Synthetic analysis validation only; no native outcome generation.',
        category_counts=counts.tolist(),constructed_categories=int(truth.size),audited_contrasts=audit['paired_contrasts'],
        source_implementation_sha256=sources,validation_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs_sha256={str(p.relative_to(output)):s.sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
    s.dump(output/'VALIDATION.json',report)
    print(json.dumps({k:report[k] for k in ['status','scope','category_counts','constructed_categories','audited_contrasts']}))


if __name__=='__main__':main()
