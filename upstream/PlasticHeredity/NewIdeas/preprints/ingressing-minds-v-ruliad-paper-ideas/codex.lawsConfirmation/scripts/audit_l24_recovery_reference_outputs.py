"""Independent D090 interventions, recurrence, source aliases and pooling.

No production intervention/writer/observer/summary calls. Frozen D086 checker
supplies independent descendant physical replay and snapshot metrics.
"""
import hashlib

import numpy as np


LOCAL_NAMES=('intact_minus_baseline','R_baseline_minus_baseline','theta_baseline_minus_baseline',
    'intact_minus_R_baseline','intact_minus_theta_baseline','interaction','intact_minus_R_reversed','restored_minus_intact')
MODES=('intact','R_baseline','theta_baseline','R_reversed')
FOCAL=('theta_delta_rms_whole','theta_delta_projection_posterior','R_delta_rms_whole')


def close(a,b):
    assert np.shape(a)==np.shape(b) and np.isfinite(a).all() and np.isfinite(b).all()
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def observer(fields,target):
    flat=fields.reshape(2,11,256);result=np.empty((11,2,3,6))
    selections=([r*16+c for r in range(16) for c in range(12,16)],
        [r*16+c for r in range(16) for c in range(12)],list(range(256)))
    for region,indices in enumerate(selections):
        x=flat[:,:,indices];d=x-x[:,0:1];n=len(indices);goal=target.reshape(256)[indices]
        result[:,:,region]=np.stack((np.sqrt(np.sum(d*d,axis=-1)/n),np.sum(d*goal,axis=-1)/n,
            np.sum(d,axis=-1)/n,np.sum((x>0)!=(x[:,0:1]>0),axis=-1)/n,
            np.sqrt(np.sum(x*x,axis=-1)/n),np.sum(x,axis=-1)/n),axis=-1).swapaxes(0,1)
    return result


def check_writer(original,payload,window):
    source_start=window.times.index(window.active)
    onset=original['writer_states'][source_start][:,[0,1,3]]
    for key,value in (('input_base',original['input_base']),('targets',original['targets']),('onset',onset)):
        np.testing.assert_array_equal(payload[key],value)
    ref=[onset[0,0]];theta=[onset[1,0]]
    for history in (1,2):
        rb,rh=onset[0,0],onset[0,history];tb,th=onset[1,0],onset[1,history]
        ref.extend((rh,rb,rh,rb-(rh-rb),rh));theta.extend((th,th,tb,th,th))
    ref=np.array(ref);theta=np.array(theta);initial=np.stack((ref,theta))
    error=close(payload['initial_writer'],initial)
    np.testing.assert_array_equal(payload['restore_intermediate_R'],onset[0,[0,0]])
    # Exactly one field is changed in each ablation and both recorded halves
    # remain intact in restoration. The reversal is allowed roundoff only.
    for start,history in ((1,1),(6,2)):
        np.testing.assert_array_equal(payload['initial_writer'][0,start+1],onset[0,0])
        np.testing.assert_array_equal(payload['initial_writer'][1,start+1],onset[1,history])
        np.testing.assert_array_equal(payload['initial_writer'][0,start+2],onset[0,history])
        np.testing.assert_array_equal(payload['initial_writer'][1,start+2],onset[1,0])
        np.testing.assert_array_equal(payload['initial_writer'][:,start+4],onset[:,history])
    # Start the independent recurrence from the exact saved intervention:
    # the separately restated reversed-R construction was checked above.
    ref,theta=payload['initial_writer'].copy();saved=[];traces=[];proposals=[]
    times=tuple(t-window.active for t in window.times if t>=window.active)
    for tick in range(window.recovery+1):
        if tick:
            ref=.998*ref+.002*original['input_base']
            q=.9995*theta+.0005*np.tanh(ref)
            mean=q.sum(axis=(-2,-1),keepdims=True)/256;q=q-mean
            std=np.sqrt(np.sum(q*q,axis=(-2,-1),keepdims=True)/256);scale=.3/np.maximum(std,1e-9)
            theta=q*scale;proposals.append(np.stack((mean[:,0,0],std[:,0,0],scale[:,0,0]),axis=-1))
        fields=np.stack((ref,theta));traces.append(observer(fields,payload['targets'][1]))
        if tick in times:
            saved.append(fields)
            analytic=.998**tick*payload['initial_writer'][0]+(1-.998**tick)*payload['input_base']
            error=max(error,close(ref,analytic))
    error=max(error,close(payload['writer_states'],np.stack(saved)),close(payload['writer_trace'],np.stack(traces)),
        close(payload['proposal_details'],np.stack(proposals)))
    # The baseline, unchanged histories and restoration controls reproduce
    # all original saved recovery fields/observers exactly, not merely scores.
    for arm,source_arm in ((0,0),(1,1),(5,1),(6,3),(10,3)):
        np.testing.assert_array_equal(payload['writer_states'][:,:,arm],original['writer_states'][source_start:,:,source_arm])
        np.testing.assert_array_equal(payload['writer_trace'][:,arm],original['writer_trace'][window.active:,source_arm])
        np.testing.assert_array_equal(payload['proposal_details'][:,arm],original['proposal_details'][window.active:,source_arm])
    for arm in (2,7):
        np.testing.assert_array_equal(payload['writer_states'][:,0,arm],payload['writer_states'][:,0,0])
    return error


def check_packets(original,payload):
    records=payload['records'];assert records.shape==(11,16,16) and records.dtype==np.float64
    np.testing.assert_array_equal(records,payload['writer_states'][-1,1])
    for record in records:
        close(np.sqrt(np.sum(record*record)/256),.3);close(record.mean(),0.)
        assert np.isfinite(record).all()
    for arm,source_arm in ((0,10),(1,11),(5,11),(6,13),(10,13)):
        np.testing.assert_array_equal(records[arm],original['records'][source_arm])
    return True


def check_aliases(original,payload):
    raw,old=payload['descendants'],original['descendants'];assert raw.shape[4]==11
    np.testing.assert_array_equal(raw[0,0],raw[1,0]);np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not raw[:,0,2].any() and not raw[1,:,2].any()
    for arm in range(11):
        np.testing.assert_array_equal(raw[:,:,:,1,arm],old[:,:,:,1,10])
        np.testing.assert_array_equal(raw[:,0,:,0,arm],old[:,0,:,1,10])
        close(payload['values'][:,:,1,arm],original['values'][:,:,1,10])
    for arm,source_arm in ((0,10),(1,11),(5,11),(6,13),(10,13)):
        np.testing.assert_array_equal(raw[:,:,:,0,arm],old[:,:,:,0,source_arm])
        np.testing.assert_array_equal(payload['values'][:,:,0,arm],original['values'][:,:,0,source_arm])
    scores=payload['values']
    np.testing.assert_array_equal(scores[...,0,0]+scores[...,0,1],np.ones_like(scores[...,0,0]))
    np.testing.assert_array_equal(scores[...,1,0],scores[...,1,1]);np.testing.assert_array_equal(scores[...,1,3],scores[...,1,4])
    return True


def contrasts(v,start):
    b=v[...,0];joint=v[...,start];theta=v[...,start+1];ref=v[...,start+2]
    return (joint-b,theta-b,ref-b,joint-theta,joint-ref,joint-theta-ref+b,
        joint-v[...,start+3],v[...,start+4]-joint)


def verify_row(cases,row,indices):
    means=np.array([sum(block.ravel())/block.size for block in cases])
    close(row['block_means'],means);close(row['parent_means'],cases.mean(axis=-1))
    close(row['mean'],means.mean());close(row['minimum'],min(means));close(row['maximum'],max(means))
    close(row['pointwise_block_bootstrap_95'],np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5)))
    for prefix,x in (('',means),('paired_',cases)):
        assert row[prefix+'positive']==int(np.count_nonzero(x>1e-12))
        assert row[prefix+'tied']==int(np.count_nonzero(abs(x)<=1e-12))
        assert row[prefix+'negative']==int(np.count_nonzero(x< -1e-12))


def check_summary(blocks,summary,rows,writer_rows,growth):
    a=np.array([b['values'] for b in blocks]);trace=np.array([b['writer_trace'] for b in blocks])
    assert a.ndim==9 and a.shape[5]==11 and len(rows)==96 and len(writer_rows)==48 and len(growth)==8
    assert set(summary)=={'means','writer_means','proposal_details_means'}
    close(summary['means'],sum(np.sum(b,axis=(0,5)) for b in a)/(len(a)*a.shape[1]*a.shape[6]))
    for name,key in (('writer_means','writer_trace'),('proposal_details_means','proposal_details')):
        close(summary[name],sum(np.sum(b[key],axis=0) for b in blocks)/(len(blocks)*a.shape[1]))
    seed=hashlib.sha256(b'l24-recovery-reference-v1:block-bootstrap').digest()
    indices=np.random.default_rng(int.from_bytes(seed[:16],'little')).integers(0,len(a),(10000,len(a)))
    position=0
    for group,metric in enumerate((0,2,4)):
        for reader in range(2):
            for history,start in (('sustained',1),('late_pulse',6)):
                v=a[:,:,reader,-1,0,:,:,0,metric].swapaxes(-1,-2)
                for label,cases in zip(LOCAL_NAMES,contrasts(v,start)):
                    row=rows[position];position+=1
                    assert row['reader']==('native_T','theta_only')[reader] and row['label']==history+'_'+label
                    assert row['metric']==('damage_fidelity','damage_projection','damage_squared_error')[group]
                    verify_row(cases,row,indices)
    position=0
    for group,(field,region,metric) in enumerate(((1,2,0),(1,0,1),(0,2,0))):
        for history,start in (('sustained',1),('late_pulse',6)):
            for label,cases in zip(LOCAL_NAMES,contrasts(trace[:,:,-1,:,field,region,metric],start)):
                row=writer_rows[position];position+=1
                assert row['metric']==FOCAL[group] and row['label']==history+'_'+label
                verify_row(cases[...,None],row,indices)
    for group,(history,start) in enumerate((('sustained',1),('late_pulse',6))):
        for offset in range(4):
            row=growth[4*group+offset]
            assert row['arm']==history+'_'+MODES[offset] and row['metric']=='theta_delta_rms_whole_end_minus_start'
            cases=(trace[:,:,-1,start+offset,1,2,0]-trace[:,:,0,start+offset,1,2,0])[...,None]
            verify_row(cases,row,indices)
    return True
