"""Independent D091 equations, matched controls, aliases, pooling and gate.

No calls to production writer, packet geometry, observers, pools or gate.
Frozen D086 independently replays child physics and snapshot metrics.
"""
import hashlib

import numpy as np

LABELS=('slow_sustained_effect','slow_late_pulse_effect','fast_sustained_effect','fast_late_pulse_effect',
    'fast_minus_slow_sustained_effect','fast_minus_slow_late_pulse_effect','fast_sustained_minus_reversed',
    'fast_sustained_minus_shuffled','fast_late_pulse_minus_reversed','fast_late_pulse_minus_shuffled',
    'fast_minus_slow_baseline','fast_sustained_minus_late_pulse')


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
    np.testing.assert_array_equal(payload['schedule'],amp)
    ref=np.array([original['initial_writer'][0]]*6);theta=np.array([original['initial_writer'][1]]*6)
    mix=np.array([.0005,.0005,.0005,.005,.005,.005])[:,None,None]
    keep=np.array([.9995,.9995,.9995,.995,.995,.995])[:,None,None]
    states=[];trace=[];details=[];weights=np.zeros(3);weight_rows=[weights];error=0.
    for tick in range(window.total+1):
        if tick:
            values=np.array([base+amp[tick-1,j]*delta for j in (0,1,2,0,1,2)])
            ref=.998*ref+.002*values
            raw=keep*theta+mix*np.tanh(ref);mean=raw.sum(axis=(-2,-1),keepdims=True)/256
            q=raw-mean;std=np.sqrt(np.sum(q*q,axis=(-2,-1),keepdims=True)/256);scale=.3/np.maximum(std,1e-9)
            theta=q*scale;details.append(np.stack((mean[:,0,0],std[:,0,0],scale[:,0,0]),axis=-1).reshape(2,3,3))
            weights=.998*weights+.002*amp[tick-1];weight_rows.append(weights)
        fields=np.stack((ref,theta)).reshape(2,2,3,16,16);trace.append(observer(fields,payload['targets'][1]))
        if tick in window.times:
            states.append(fields)
            step=lambda n,h:(1-.998**min(max(n,0),h))*.998**max(n-h,0)
            analytic_weights=np.array([0,step(tick,window.active),step(tick-window.active+window.pulse,window.pulse)])
            error=max(error,close(weights,analytic_weights))
            analytic=.998**tick*original['initial_writer'][0]+(1-.998**tick)*base+analytic_weights[:,None,None]*delta
            for speed in (0,1): error=max(error,close(fields[0,speed],analytic))
    error=max(error,close(payload['writer_states'],np.stack(states)),close(payload['writer_trace'],np.stack(trace)),
        close(payload['proposal_details'],np.stack(details)),close(payload['R_weights'],np.stack(weight_rows)))
    np.testing.assert_array_equal(payload['writer_states'][:,:,0],original['writer_states'][:,:,[0,1,3]])
    np.testing.assert_array_equal(payload['writer_trace'][:,0],original['writer_trace'][:,[0,1,3]])
    np.testing.assert_array_equal(payload['proposal_details'][:,0],original['proposal_details'][:,[0,1,3]])
    np.testing.assert_array_equal(payload['writer_states'][:,0,0],payload['writer_states'][:,0,1])
    np.testing.assert_array_equal(payload['writer_trace'][:,:, :,0],np.repeat(payload['writer_trace'][:,0:1,:,0],2,axis=1))
    np.testing.assert_array_equal(payload['R_weights'],original['R_weights'][:,[0,1,3]])
    return error


def check_packets(original,payload,window):
    records=payload['records'].reshape(2,10,16,16);error=0.
    np.testing.assert_array_equal(np.sort(payload['permutation']),np.arange(256))
    for end,tick in enumerate(window.boundaries):
        written=payload['writer_states'][window.times.index(tick),1].reshape(6,16,16);b=written[3]
        np.testing.assert_array_equal(records[end,:6],written)
        radius=np.linalg.norm(b.ravel())/16
        for position,arm in enumerate((4,5)):
            raw=written[arm]-b;distance=np.linalg.norm(raw.ravel())/16;assert 0<distance<2*radius
            angle=2*np.arcsin(distance/(2*radius));c,s=np.cos(angle),radius*np.sin(angle);units=[]
            for h in (raw,raw.ravel()[payload['permutation']].reshape(16,16)):
                q=h.ravel()-h.sum()/256;flat=b.ravel();q=q-flat*np.dot(q,flat)/np.dot(flat,flat)
                length=np.linalg.norm(q)/16;assert length>1e-12;units.append((q/length).reshape(16,16))
            error=max(error,close(payload['control_units'][end,position],np.array(units)),
                close(payload['reconstructed_written'][end,position],c*b+s*units[0]),close(written[arm],c*b+s*units[0]),
                close(records[end,6+2*position],c*b-s*units[0]),close(records[end,7+2*position],c*b+s*units[1]))
            for arm in (6+2*position,7+2*position):
                error=max(error,close(np.linalg.norm((records[end,arm]-b).ravel())/16,distance))
        stats=[];flags=[];direction=(payload['targets'][1]-payload['targets'][0])/2
        for arm,record in enumerate(records[end]):
            baseline=records[end,0 if arm<3 else 3];q=record-baseline;total=np.dot(q.ravel(),q.ravel())
            flags.append(total>0);error=max(error,close(np.linalg.norm(record.ravel())/16,.3),close(record.mean(),0.))
            stats.append((np.linalg.norm(record.ravel())/16,np.linalg.norm(q.ravel())/16,record.sum()/256,
                np.dot(q.ravel(),direction.ravel())/256,np.sum(q[:,12:]**2)/total if total>0 else 0.,max(abs(q.ravel()))))
        error=max(error,close(payload['geometry'][end],np.array(stats)))
        np.testing.assert_array_equal(payload['geometry_energy_available'][end],flags)
        for arm,old_arm in ((0,0),(1,1),(2,3)):
            np.testing.assert_array_equal(records[end,arm],original['records'][10*end+old_arm])
    return error


def check_aliases(original,payload):
    raw,old=payload['descendants'],original['descendants'];assert raw.shape[4]==20
    np.testing.assert_array_equal(raw[0,0],raw[1,0]);np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not raw[:,0,2].any() and not raw[1,:,2].any()
    for arm in range(20):
        np.testing.assert_array_equal(raw[:,:,:,1,arm],old[:,:,:,1,0])
        np.testing.assert_array_equal(raw[:,0,:,0,arm],old[:,0,:,1,0])
        close(payload['values'][:,:,1,arm],original['values'][:,:,1,0])
    for end in (0,1):
        for arm,source_arm in ((0,0),(1,1),(2,3)):
            np.testing.assert_array_equal(raw[:,:,:,0,10*end+arm],old[:,:,:,0,10*end+source_arm])
            np.testing.assert_array_equal(payload['values'][:,:,0,10*end+arm],original['values'][:,:,0,10*end+source_arm])
    scores=payload['values']
    np.testing.assert_array_equal(scores[...,0,0]+scores[...,0,1],np.ones_like(scores[...,0,0]))
    np.testing.assert_array_equal(scores[...,1,0],scores[...,1,1]);np.testing.assert_array_equal(scores[...,1,3],scores[...,1,4])
    return True


def contrasts(v):
    slow_s=v[...,1]-v[...,0];slow_p=v[...,2]-v[...,0]
    fast_s=v[...,4]-v[...,3];fast_p=v[...,5]-v[...,3]
    basic=(slow_s,slow_p,fast_s,fast_p,fast_s-slow_s,fast_p-slow_p)
    if v.shape[-1]==6: return basic
    return (*basic,v[...,4]-v[...,6],v[...,4]-v[...,7],v[...,5]-v[...,8],v[...,5]-v[...,9],v[...,3]-v[...,0],v[...,4]-v[...,5])


def verify_row(cases,row,indices):
    means=np.array([sum(block.ravel())/block.size for block in cases])
    close(row['block_means'],means);close(row['parent_means'],cases.mean(axis=-1))
    close(row['mean'],means.mean());close(row['minimum'],min(means));close(row['maximum'],max(means))
    close(row['pointwise_block_bootstrap_95'],np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5)))
    for prefix,x in (('',means),('paired_',cases)):
        assert row[prefix+'positive']==int(np.count_nonzero(x>1e-12))
        assert row[prefix+'tied']==int(np.count_nonzero(abs(x)<=1e-12))
        assert row[prefix+'negative']==int(np.count_nonzero(x< -1e-12))


def check_summary(blocks,summary,rows,writer_rows,window):
    a=np.array([b['values'] for b in blocks]);trace=np.array([b['writer_trace'] for b in blocks])
    assert a.ndim==9 and a.shape[5]==20 and len(rows)==144 and len(writer_rows)==24
    assert set(summary)=={'means','writer_means','proposal_details_means','geometry_means','R_weights_means'}
    close(summary['means'],sum(np.sum(b,axis=(0,5)) for b in a)/(len(a)*a.shape[1]*a.shape[6]))
    for name,key in (('writer_means','writer_trace'),('proposal_details_means','proposal_details'),('geometry_means','geometry'),('R_weights_means','R_weights')):
        close(summary[name],sum(np.sum(b[key],axis=0) for b in blocks)/(len(blocks)*a.shape[1]))
    seed=hashlib.sha256(b'l24-speed-qualification-v1:block-bootstrap').digest()
    indices=np.random.default_rng(int.from_bytes(seed[:16],'little')).integers(0,len(a),(10000,len(a)))
    position=0;wp=0
    for end,boundary in enumerate(window.boundaries):
        for group,metric in enumerate((0,2,4)):
            for reader in range(2):
                v=a[:,:,reader,-1,0,10*end:10*end+10,:,0,metric].swapaxes(-1,-2)
                for label,cases in zip(LABELS,contrasts(v)):
                    row=rows[position];position+=1
                    assert row['boundary']==boundary and row['reader']==('native_T','theta_only')[reader] and row['label']==label
                    assert row['metric']==('damage_fidelity','damage_projection','damage_squared_error')[group]
                    verify_row(cases,row,indices)
        for name,region,column in (('theta_delta_rms_whole',2,0),('theta_delta_projection_posterior',0,1)):
            v=trace[:,:,boundary,:,:,1,region,column].reshape(a.shape[0],a.shape[1],6)
            for label,cases in zip(LABELS,contrasts(v)):
                row=writer_rows[wp];wp+=1
                assert (row['boundary'],row['metric'],row['label'])==(boundary,name,label)
                verify_row(cases[...,None],row,indices)
    return True


def check_qualification(rows,result,window):
    expected=[]
    for boundary in window.boundaries:
        criteria=[]
        for metric in ('damage_fidelity','damage_projection'):
            for label in LABELS[2:10]:
                row,=[r for r in rows if (r['boundary'],r['reader'],r['metric'],r['label'])==(boundary,'native_T',metric,label)]
                passed=all(x>1e-12 for x in row['block_means']) and row['pointwise_block_bootstrap_95'][0]>0
                criteria.append({'metric':metric,'label':label,'passed':passed})
        expected.append({'boundary':boundary,'primary':boundary==window.total,
            'stronger_readable_channel_qualified':all(c['passed'] for c in criteria),'criteria':criteria})
    assert result==expected;return True
