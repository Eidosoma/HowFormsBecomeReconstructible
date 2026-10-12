"""Independent D092 gate equations, source mappings, contrasts and timing.

No calls to production writer, observers, pooling, contrasts or fractions.
D086's frozen independent checker supplies child physics and snapshot metrics.
"""
import hashlib

import numpy as np

LABELS=('slow_unprotected_sustained_effect','slow_unprotected_pulse_effect',
    'fast_unprotected_sustained_effect','fast_unprotected_pulse_effect',
    'slow_protected_sustained_effect','slow_protected_pulse_effect',
    'fast_protected_sustained_effect','fast_protected_pulse_effect',
    'slow_sustained_cost','slow_pulse_reduction','fast_sustained_cost','fast_pulse_reduction',
    'fast_minus_slow_sustained_cost','fast_minus_slow_pulse_reduction',
    'slow_protected_minus_unprotected_baseline','fast_protected_minus_unprotected_baseline')
TIMING_LABELS=(LABELS[5],LABELS[7],LABELS[9],LABELS[11])

def close(a,b):
    assert np.shape(a)==np.shape(b) and np.isfinite(a).all() and np.isfinite(b).all()
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def observer(fields,target):
    result=np.empty((2,3,2,3,6))
    indices=([r*16+c for r in range(16) for c in range(12,16)],
        [r*16+c for r in range(16) for c in range(12)],list(range(256)))
    for speed in range(2):
        flat=fields[:,speed].reshape(2,3,256)
        for region,cells in enumerate(indices):
            x=flat[:,:,cells];d=x-x[:,0:1];n=len(cells);goal=target.ravel()[cells]
            result[speed,:,:,region]=np.stack((np.sqrt(np.sum(d*d,axis=-1)/n),np.sum(d*goal,axis=-1)/n,
                np.sum(d,axis=-1)/n,np.sum((x>0)!=(x[:,0:1]>0),axis=-1)/n,
                np.sqrt(np.sum(x*x,axis=-1)/n),np.sum(x,axis=-1)/n),axis=-1).swapaxes(0,1)
    return result



def check_writer(original,payload,window):
    for key in ('input_base','input_delta','initial_writer','targets','permutation'):
        np.testing.assert_array_equal(payload[key],original[key])
    base=original['input_base'];delta=np.zeros((16,16));delta[:,12:]=-2*base[:,12:]
    np.testing.assert_array_equal(payload['input_delta'],delta)
    amp=np.array([[0.,float(k<window.active),float(window.active-window.pulse<=k<window.active)] for k in range(window.total)])
    on=np.array([not window.active-window.pulse<=k<window.active for k in range(window.total)])
    np.testing.assert_array_equal(payload['schedule'],amp);np.testing.assert_array_equal(payload['write_enabled'],on)
    ref=np.array([original['initial_writer'][0]]*6);theta=np.array([original['initial_writer'][1]]*6)
    mix=np.array([.0005]*3+[.005]*3)[:,None,None];keep=np.array([.9995]*3+[.995]*3)[:,None,None]
    states=[];trace=[];details=[];weights=np.zeros(3);weight_rows=[weights];error=0.
    for tick in range(window.total+1):
        if tick:
            values=np.array([base+amp[tick-1,j]*delta for j in (0,1,2,0,1,2)])
            ref=.998*ref+.002*values
            if on[tick-1]:
                raw=keep*theta+mix*np.tanh(ref);mean=raw.sum(axis=(-2,-1),keepdims=True)/256
                q=raw-mean;std=np.sqrt(np.sum(q*q,axis=(-2,-1),keepdims=True)/256);scale=.3/np.maximum(std,1e-9)
                theta=q*scale
            else:
                mean=theta.sum(axis=(-2,-1),keepdims=True)/256
                std=np.sqrt(np.sum((theta-mean)**2,axis=(-2,-1),keepdims=True)/256)
                scale=np.ones((6,1,1))
            details.append(np.stack((mean[:,0,0],std[:,0,0],scale[:,0,0]),axis=-1).reshape(2,3,3))
            weights=.998*weights+.002*amp[tick-1];weight_rows.append(weights)
        fields=np.stack((ref,theta)).reshape(2,2,3,16,16)
        trace.append(observer(fields,payload['targets'][1]))
        if tick in window.times:
            states.append(fields)
            pulse=lambda n,h:(1-.998**min(max(n,0),h))*.998**max(n-h,0)
            analytic_weights=np.array([0,pulse(tick,window.active),pulse(tick-window.active+window.pulse,window.pulse)])
            error=max(error,close(weights,analytic_weights))
            analytic=.998**tick*original['initial_writer'][0]+(1-.998**tick)*base+analytic_weights[:,None,None]*delta
            for speed in (0,1): error=max(error,close(fields[0,speed],analytic))
    error=max(error,close(payload['writer_states'],np.stack(states)),close(payload['writer_trace'],np.stack(trace)),
        close(payload['proposal_details'],np.stack(details)),close(payload['R_weights'],np.stack(weight_rows)))
    np.testing.assert_array_equal(payload['R_weights'],original['R_weights'])
    np.testing.assert_array_equal(payload['writer_states'][:,0],original['writer_states'][:,0])
    np.testing.assert_array_equal(payload['writer_trace'][:,:,:,0],original['writer_trace'][:,:,:,0])
    for pos,tick in enumerate(window.times):
        if tick<=window.active-window.pulse:
            np.testing.assert_array_equal(payload['writer_states'][pos],original['writer_states'][pos])
    start,end=window.active-window.pulse,window.active
    np.testing.assert_array_equal(payload['writer_trace'][:start+1],original['writer_trace'][:start+1])
    np.testing.assert_array_equal(payload['proposal_details'][:start],original['proposal_details'][:start])
    np.testing.assert_array_equal(payload['writer_states'][window.times.index(start),1],payload['writer_states'][window.times.index(end),1])
    np.testing.assert_array_equal(payload['writer_trace'][start:end+1,:,:,1],
        np.repeat(payload['writer_trace'][start:start+1,:,:,1],end-start+1,axis=0))
    np.testing.assert_array_equal(payload['proposal_details'][start:end,:,:,2],np.ones((end-start,2,3)))
    early=payload['writer_states'][window.times.index(end),1]
    np.testing.assert_array_equal(early[:,0],early[:,2])
    return error


def check_packets(payload,window):
    assert payload['records'].shape==(12,16,16);error=0.
    for end,tick in enumerate(window.boundaries):
        np.testing.assert_array_equal(payload['records'][6*end:6*end+6],
            payload['writer_states'][window.times.index(tick),1].reshape(6,16,16))
    for packet in payload['records']:
        error=max(error,close(packet.sum()/256,0.),close(np.linalg.norm(packet.ravel())/16,.3))
    np.testing.assert_array_equal(payload['records'][0],payload['records'][2])
    np.testing.assert_array_equal(payload['records'][3],payload['records'][5])
    return error


def check_aliases(original,payload):
    raw,old=payload['descendants'],original['descendants'];assert raw.shape[4]==12
    np.testing.assert_array_equal(raw[0,0],raw[1,0]);np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not raw[:,0,2].any() and not raw[1,:,2].any()
    scores=payload['values'];assert scores.shape[3]==24
    for arm in range(12):
        np.testing.assert_array_equal(raw[:,:,:,1,arm],old[:,:,:,1,0])
        np.testing.assert_array_equal(raw[:,0,:,0,arm],old[:,0,:,1,0])
    for arm in range(24): np.testing.assert_array_equal(scores[:,:,1,arm],original['values'][:,:,1,0])
    np.testing.assert_array_equal(raw[:,:,:,0,2],raw[:,:,:,0,0])
    np.testing.assert_array_equal(raw[:,:,:,0,5],raw[:,:,:,0,3])
    for end in (0,1):
        np.testing.assert_array_equal(scores[:,:,:,12*end:12*end+6],original['values'][:,:,:,10*end:10*end+6])
    np.testing.assert_array_equal(scores[...,0,0]+scores[...,0,1],np.ones_like(scores[...,0,0]))
    np.testing.assert_array_equal(scores[...,1,0],scores[...,1,1]);np.testing.assert_array_equal(scores[...,1,3],scores[...,1,4])
    return True


def contrasts(v):
    us,up=v[...,1]-v[...,0],v[...,2]-v[...,0]
    uf,uq=v[...,4]-v[...,3],v[...,5]-v[...,3]
    ps,pp=v[...,7]-v[...,6],v[...,8]-v[...,6]
    pf,pq=v[...,10]-v[...,9],v[...,11]-v[...,9]
    cs,bs,cf,bf=us-ps,up-pp,uf-pf,uq-pq
    return (us,up,uf,uq,ps,pp,pf,pq,cs,bs,cf,bf,cf-cs,bf-bs,v[...,6]-v[...,0],v[...,9]-v[...,3])


def verify_row(cases,row,indices):
    means=np.array([sum(block.ravel())/block.size for block in cases])
    close(row['block_means'],means);close(row['parent_means'],cases.mean(axis=-1))
    close(row['mean'],means.mean());close(row['minimum'],min(means));close(row['maximum'],max(means))
    close(row['pointwise_block_bootstrap_95'],np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5)))
    for prefix,x in (('',means),('paired_',cases)):
        assert row[prefix+'positive']==int(np.count_nonzero(x>1e-12))
        assert row[prefix+'tied']==int(np.count_nonzero(abs(x)<=1e-12))
        assert row[prefix+'negative']==int(np.count_nonzero(x< -1e-12))



def check_summary(blocks,summary,rows,writer_rows,timing_rows,writer_timing,window):
    a=np.array([b['values'] for b in blocks]);trace=np.array([b['writer_trace'] for b in blocks])
    ref=np.array([b['reference_writer_trace'] for b in blocks])
    assert a.ndim==9 and a.shape[5]==24
    assert (len(rows),len(writer_rows),len(timing_rows),len(writer_timing))==(192,64,24,8)
    assert set(summary)=={'means','writer_means','proposal_details_means','R_weights_means'}
    close(summary['means'],sum(np.sum(b,axis=(0,5)) for b in a)/(len(a)*a.shape[1]*a.shape[6]))
    for name,key in (('writer_means','writer_trace'),('proposal_details_means','proposal_details'),('R_weights_means','R_weights')):
        close(summary[name],sum(np.sum(b[key],axis=0) for b in blocks)/(len(blocks)*a.shape[1]))
    seed=hashlib.sha256(b'l24-write-protection-v1:block-bootstrap').digest()
    indices=np.random.default_rng(int.from_bytes(seed[:16],'little')).integers(0,len(a),(10000,len(a)))
    position=0;wp=0;children={};writers={}
    for end,boundary in enumerate(window.boundaries):
        for group,metric in enumerate((0,2,4)):
            for reader in range(2):
                v=a[:,:,reader,-1,0,12*end:12*end+12,:,0,metric].swapaxes(-1,-2)
                for label,cases in zip(LABELS,contrasts(v)):
                    row=rows[position];position+=1;children[(boundary,reader,metric,label)]=cases
                    assert (row['boundary'],row['reader'],row['label'],row['metric'])==(
                        boundary,('native_T','theta_only')[reader],label,('damage_fidelity','damage_projection','damage_squared_error')[group])
                    verify_row(cases,row,indices)
        for name,region,column in (('theta_delta_rms_whole',2,0),('theta_delta_projection_posterior',0,1)):
            # Extract source/protected histories independently, preserving flat logical order.
            v=np.stack([x[:,:,boundary,s,h,1,region,column] for x in (ref,trace) for s in (0,1) for h in (0,1,2)],axis=-1)
            for label,cases in zip(LABELS,contrasts(v)):
                row=writer_rows[wp];wp+=1;writers[(boundary,name,label)]=cases[...,None]
                assert (row['boundary'],row['metric'],row['label'])==(boundary,name,label)
                verify_row(cases[...,None],row,indices)
    first,last=window.boundaries;position=0;wp=0
    for group,metric in enumerate((0,2,4)):
        for reader in range(2):
            for label in TIMING_LABELS:
                row=timing_rows[position];position+=1
                assert (row['earlier'],row['later'],row['reader'],row['metric'],row['label'])==(
                    first,last,('native_T','theta_only')[reader],('damage_fidelity','damage_projection','damage_squared_error')[group],label)
                verify_row(children[(last,reader,metric,label)]-children[(first,reader,metric,label)],row,indices)
    for name in ('theta_delta_rms_whole','theta_delta_projection_posterior'):
        for label in TIMING_LABELS:
            row=writer_timing[wp];wp+=1
            assert (row['earlier'],row['later'],row['metric'],row['label'])==(first,last,name,label)
            verify_row(writers[(last,name,label)]-writers[(first,name,label)],row,indices)
    return True


def check_fractions(rows,result,window):
    expected=[]
    for boundary in window.boundaries:
        for metric in ('damage_fidelity','damage_projection'):
            for speed in ('slow','fast'):
                for history in ('sustained','pulse'):
                    found={}
                    for protection in ('unprotected','protected'):
                        label=f'{speed}_{protection}_{history}_effect'
                        matches=[r for r in rows if (r['boundary'],r['reader'],r['metric'],r['label'])==(boundary,'native_T',metric,label)]
                        assert len(matches)==1;found[protection]=matches[0]['mean']
                    before,after=found['unprotected'],found['protected'];available=before>1e-12
                    ratio=after/before if available else None
                    expected.append(dict(boundary=boundary,metric=metric,speed=speed,history=history,
                        unprotected_effect=before,protected_effect=after,available=available,
                        retained_fraction=ratio,reduced_fraction=1-ratio if available else None))
    assert result==expected;return True

