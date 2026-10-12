"""Independent D087 saved-state algebra/statistic checks; no simulator calls."""
import hashlib
import json
from pathlib import Path

import numpy as np

from laws_confirmation import l24_descendant_pilot as previous
from laws_confirmation.io import canonical_digest, sha256_file

LABELS=('body_immediately_after_injury','body_after_one_update','reference_after_one_update',
        'raw_record_after_one_update','projected_record_after_one_update','body_after_50_updates',
        'reference_after_50_updates','record_after_50_updates','final_record_delta_relative_to_point3',
        'actual_to_known_record_delta_ratio','first_step_tanh_rms_ratio','first_step_centering_rms_ratio',
        'first_step_normalization_rms_ratio','weighted_body_drive_relative_to_initial_injury')


def close(a,b):
    assert np.shape(a)==np.shape(b)
    assert np.isfinite(a).all() and np.isfinite(b).all()
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def size(x): return float(np.linalg.norm(np.ravel(x))/np.sqrt(np.size(x)))


def source_manifest_check(root,hashes):
    out=root/'outputs'/previous.RUN_ID;run=root/'runs'/previous.RUN_ID
    status=json.loads((run/'STATUS.json').read_text());manifest=json.loads((run/'MANIFEST.json').read_text())
    analysis=json.loads((out/'analysis.json').read_text());verification=json.loads((out/'verification.json').read_text())
    assert status['status']=='COMPLETE' and status['checked_blocks']==8 and status['verified_saved_analysis']
    assert (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for name,count in (('input_hashes.sha256',159),('output_hashes.sha256',20)):
        rows=[line.split('  ',1) for line in (out/name).read_text().splitlines()]
        assert len(rows)==count and len({p for _,p in rows})==count
        for digest,path in rows: assert hashes[path]==digest,path
    assert canonical_digest(manifest['input_sha256'])==manifest['hash_contract']
    for path,digest in manifest['input_sha256'].items(): assert hashes[path]==digest,path
    for item in (manifest,analysis):
        for key,value in previous.contract().items(): assert canonical_digest(item[key])==canonical_digest(value),key
    assert analysis['technical_checks_passed'] and verification['passes']
    assert verification['exact_source_bridges']==64 and verification['descendant_lives_replayed']==8192
    assert verification['input_hashes_unchanged'] and verification['saved_pool_verified']
    previous.source_verified(root,hashes)
    return True


def source_block_check(data,meta,tissue):
    assert meta['tissue']==tissue and meta['passes'] and len(meta['parents'])==4
    assert canonical_digest(meta['config'])==canonical_digest(previous.contract()['config'])
    assert data['parent_states'].shape==(4,2,7,4,16,16)
    assert data['descendants'].shape==(4,2,5,3,2,8,8,16,16)
    old=previous.checker();ctx=previous.context(tissue)
    for parent in range(4):
        payload={k:v[parent] for k,v in data.items()};record=meta['parents'][parent]
        assert record['parent']==parent
        assert old.check_aliases(payload)
        parents=[dict(states=payload['parent_states'][c],fresh=payload['fresh'],founder=payload['founder'],
                      zone=np.indices((16,16))[1]>=12) for c in (0,1)]
        assert old.check_records(payload['records'],payload['targets'],payload['permutation'],*parents,ctx,parent)
        assert record['parent_records'][0]['rng_final']==record['parent_records'][1]['rng_final']
        for result in record['parent_checks']:
            assert result['passed'] and result['replay_max_abs']<=1e-10
            bridge=result['source_bridge']
            for key in ('passed','exact_states','exact_metrics','exact_rng'): assert bridge[key]
            assert bridge['cycles']==1 and bridge['captured_stages']==7
        for reader in (0,1):
            child=record['children'][reader]
            assert child['reader']==reader and child['replay_max_abs']<=1e-10
            assert child['inherited_fields']==['theta'] and child['packet_unchanged'] and child['R_at_birth_zero']
            assert child['packet_sha256']==[hashlib.sha256(r.astype('<f8').tobytes()).hexdigest() for r in payload['records']]
            assert old.check_metrics(payload['descendants'][reader],payload['targets'],payload['values'][reader])
    return True


def check_parent(payload,result):
    states=payload['parent_states'];assert states.shape==(2,7,4,16,16)
    np.testing.assert_array_equal(states[0,:4],states[1,:4])
    np.testing.assert_array_equal(states[0,4,2:],states[1,4,2:])
    before=states[:,4];after=states[:,5]
    ref=before[:,2]+.002*(after[:,0]-before[:,2])
    errors=[close(after[:,2],ref)]
    proposal=.9995*before[:,3]+.0005*np.tanh(after[:,2])
    centered=np.array([x-np.mean(x) for x in proposal])
    scales=np.array([.3/max(float(x.std()),1e-9) for x in centered])
    predicted=centered*scales[:,None,None]
    errors.append(close(after[:,3],predicted))
    delta=lambda x:x[1]-x[0]
    shape=.5*(scales[0]+scales[1])*delta(centered)
    gain=.5*(scales[1]-scales[0])*(centered[1]+centered[0])
    expected_terms=np.array([delta(before[:,0]),delta(after[:,0]),delta(after[:,2]),
        delta(np.tanh(after[:,2])),delta(proposal),delta(centered),shape,gain,delta(after[:,3]),
        delta(states[:,6,2])/(1-.998**50),delta(states[:,6,3])])
    errors.append(close(result['terms'],expected_terms))
    errors.append(close(delta(after[:,2]),.002*delta(after[:,0])))
    errors.append(close(delta(proposal),.0005*delta(np.tanh(after[:,2]))))
    errors.append(close(shape+gain,delta(after[:,3])))
    details=np.array([[float(u.mean()),float(q.std()),s] for u,q,s in zip(proposal,centered,scales)])
    errors.append(close(result['projection_details'],details))
    trace=np.empty((7,5,3,9));direction=(payload['targets'][1]-payload['targets'][0])/2
    pixels=([r*16+c for r in range(16) for c in range(12,16)],
            [r*16+c for r in range(16) for c in range(12)],list(range(256)))
    for stage in range(7):
        for field in range(5):
            a,b=states[:,stage,field] if field<4 else np.tanh(states[:,stage,2])
            for region,indices in enumerate(pixels):
                c,d=a.ravel()[indices],b.ravel()[indices];x=d-c
                trace[stage,field,region]=[size(x),max(abs(x)),sum(x)/len(x),
                    np.dot(x,direction.ravel()[indices])/len(x),np.count_nonzero((c>0)!=(d>0))/len(x),
                    size(c),size(d),np.count_nonzero(abs(c)==2)/len(x),np.count_nonzero(abs(d)==2)/len(x)]
    errors.append(close(result['trace'],trace))
    v=np.array([size(expected_terms[i]) for i in (0,1,2,4,8)]+
        [size(states[1,6,f]-states[0,6,f]) for f in (0,2,3)]+[0.]*6)
    valid=np.ones(14,bool)
    pairs=((v[7],.3),(v[7],size(payload['records'][5]-payload['records'][4])),
        (size(expected_terms[3]),size(expected_terms[2])),(size(expected_terms[5]),size(expected_terms[4])),
        (size(expected_terms[8]),size(expected_terms[5])),(size(expected_terms[9]),size(expected_terms[0])))
    for j,(n,d) in enumerate(pairs,8): valid[j]=d>0;v[j]=n/d if d>0 else 0.
    errors.append(close(result['focal'],v));np.testing.assert_array_equal(result['valid'],valid)
    if valid[10]: assert v[10]<=1+1e-10  # tanh is 1-Lipschitz
    if valid[11]: assert v[11]<=1+1e-10  # orthogonal removal of uniform component
    child=np.empty((2,5,3,8));x=payload['values']
    for reader in range(2):
        for tick in range(5):
            for region in range(3):
                for metric in range(8):
                    child[reader,tick,region,metric]=sum(x[reader,tick,0,1,d,region,metric]-x[reader,tick,0,0,d,region,metric]
                        for d in range(x.shape[4]))/x.shape[4]
    errors.append(close(result['child_contrast'],child))
    return max(errors)


def check_summary(blocks,summary,rows):
    assert set(summary)=={'trace','projection_details','child_contrast'} and len(rows)==14
    for key in summary:
        expected=sum(sum(b[key]) for b in blocks)/(len(blocks)*blocks[0][key].shape[0])
        close(summary[key],expected)
    seed=int.from_bytes(hashlib.sha256(b'l24-signal-chain-audit-v1:block-bootstrap').digest()[:16],'little')
    indices=np.random.default_rng(seed).integers(0,len(blocks),(10000,len(blocks)))
    for column,(label,row) in enumerate(zip(LABELS,rows)):
        counts=[int(np.count_nonzero(b['valid'][:,column])) for b in blocks]
        available=all(n==len(b['valid']) for n,b in zip(counts,blocks))
        assert row['label']==label and row['available']==available and row['valid_parents_per_block']==counts
        names=('block_means','mean','observed_block_range','pointwise_block_bootstrap_95')
        if not available:
            assert all(row[name] is None for name in names)
        else:
            means=np.array([sum(b['focal'][:,column])/len(b['focal']) for b in blocks])
            close(row['block_means'],means);close(row['mean'],sum(means)/len(means))
            close(row['observed_block_range'],[min(means),max(means)])
            ci=np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5))
            close(row['pointwise_block_bootstrap_95'],ci)
    return True


def check_clock(rows):
    assert [row['updates'] for row in rows]==[1,50]
    for row in rows:
        ref=theta=direct=0.
        for _ in range(row['updates']):
            ref=.998*ref+.002
            theta=.9995*theta+.0005*ref
            direct=.9995*direct+.0005
        for key,value in (('R_unit_step_weight',ref),('theta_direct_unit_step_weight',direct),
                          ('theta_cascade_unit_step_weight',theta)):
            close(row[key],value)
    return True
