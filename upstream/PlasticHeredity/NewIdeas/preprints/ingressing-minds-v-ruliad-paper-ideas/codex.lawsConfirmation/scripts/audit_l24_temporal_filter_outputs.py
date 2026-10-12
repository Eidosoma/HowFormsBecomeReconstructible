"""Independent D089 input schedule, writer recurrence, geometry and pooling.

No calls to the production schedule, writer, observer, packet builder or pool.
D086's frozen checker supplies descendant physical replay and original metrics.
"""
import hashlib

import numpy as np


PAIRS=((1,0),(3,0),(2,0),(1,3),(3,2),(4,3),(1,5),(1,6),(3,7),(3,8))
LABELS=('sustained_minus_baseline','late_pulse_minus_baseline','early_pulse_minus_baseline',
    'sustained_minus_late_pulse','late_minus_early_pulse','dose_matched_minus_late_pulse',
    'sustained_minus_reversed','sustained_minus_shuffled','late_pulse_minus_reversed','late_pulse_minus_shuffled')


def close(a,b):
    assert np.shape(a)==np.shape(b) and np.isfinite(a).all() and np.isfinite(b).all()
    np.testing.assert_allclose(a,b,rtol=0,atol=1e-12)
    return float(np.max(abs(np.asarray(a)-np.asarray(b))))


def observer(fields,target):
    flat=fields.reshape(2,5,256);result=np.empty((5,2,3,6))
    selections=([r*16+c for r in range(16) for c in range(12,16)],
        [r*16+c for r in range(16) for c in range(12)],list(range(256)))
    for region,indices in enumerate(selections):
        x=flat[:,:,indices];d=x-x[:,0:1];n=len(indices);goal=target.reshape(256)[indices]
        result[:,:,region]=np.stack((np.sqrt(np.sum(d*d,axis=-1)/n),np.sum(d*goal,axis=-1)/n,
            np.sum(d,axis=-1)/n,np.sum((x>0)!=(x[:,0:1]>0),axis=-1)/n,
            np.sqrt(np.sum(x*x,axis=-1)/n),np.sum(x,axis=-1)/n),axis=-1).swapaxes(0,1)
    return result


def check_writer(original,payload,window):
    old=original['parent_states'];initial=old[0,3,2:4]
    base=old[0,3,0];delta=old[1,4,0]-base
    np.testing.assert_array_equal(old[0,:4],old[1,:4])
    expected_delta=np.zeros((16,16));expected_delta[:,12:]=-2*base[:,12:]
    np.testing.assert_array_equal(delta,expected_delta)
    for key,value in (('input_base',base),('input_delta',delta),('initial_writer',initial),
                      ('targets',original['targets']),('permutation',original['permutation'])):
        np.testing.assert_array_equal(payload[key],value)
    assert payload['schedule'].shape==(window.total,5)
    amplitudes=np.array([[0.,float(t<window.active),float(t<window.pulse),
        float(window.active-window.pulse<=t<window.active),
        window.pulse/window.active if t<window.active else 0.] for t in range(window.total)])
    np.testing.assert_array_equal(payload['schedule'],amplitudes)
    close(amplitudes.sum(axis=0),np.array([0,window.active,window.pulse,window.pulse,window.pulse],float))
    close(np.sum(amplitudes**2,axis=0),np.array([0,window.active,window.pulse,window.pulse,window.pulse**2/window.active],float))
    assert not amplitudes[window.active:].any()
    ref=np.repeat(initial[0,None],5,axis=0);theta=np.repeat(initial[1,None],5,axis=0)
    snapshots=[];traces=[];details=[];max_error=0.
    for t in range(window.total+1):
        if t:
            x=base+amplitudes[t-1,:,None,None]*delta
            ref=.998*ref+.002*x
            raw=.9995*theta+.0005*np.tanh(ref)
            mean=np.mean(raw,axis=(-2,-1),keepdims=True);q=raw-mean
            std=np.std(q,axis=(-2,-1),keepdims=True);scale=.3/np.maximum(std,1e-9)
            theta=q*scale;details.append(np.stack((mean[:,0,0],std[:,0,0],scale[:,0,0]),axis=-1))
        fields=np.stack((ref,theta));traces.append(observer(fields,payload['targets'][1]))
        if t in window.times:
            snapshots.append(fields)
            a=window.active;b=window.pulse;decay=.998
            step=lambda n,duration: (1-decay**min(max(n,0),duration))*decay**max(n-duration,0)
            weights=np.array([0,step(t,a),step(t,b),step(t-a+b,b),b/a*step(t,a)])
            max_error=max(max_error,close(payload['R_weights'][t],weights))
            analytic=decay**t*initial[0]+(1-decay**t)*base+weights[:,None,None]*delta
            max_error=max(max_error,close(ref,analytic))
    max_error=max(max_error,close(payload['writer_states'],np.stack(snapshots)),
        close(payload['writer_trace'],np.stack(traces)),close(payload['proposal_details'],np.stack(details)))
    weights=np.zeros(5);weight_rows=[weights]
    for a in amplitudes:
        weights=.998*weights+.002*a;weight_rows.append(weights)
    max_error=max(max_error,close(payload['R_weights'],np.stack(weight_rows)))
    # Independent source equation bridge: insert the original saved updated V.
    r0=old[:,4,2];th0=old[:,4,3];r1=r0+.002*(old[:,5,0]-r0)
    proposal=.9995*th0+.0005*np.tanh(r1);proposal-=proposal.mean(axis=(-2,-1),keepdims=True)
    th1=proposal*(.3/np.maximum(proposal.std(axis=(-2,-1),keepdims=True),1e-9))
    max_error=max(max_error,close(r1,old[:,5,2]),close(th1,old[:,5,3]))
    return max_error


def check_packets(payload,window):
    records=payload['records'].reshape(2,10,16,16);errors=[]
    np.testing.assert_array_equal(np.sort(payload['permutation']),np.arange(256))
    for end,tick in enumerate(window.boundaries):
        written=payload['writer_states'][window.times.index(tick),1];b=written[0]
        np.testing.assert_array_equal(records[end,:5],written)
        np.testing.assert_array_equal(records[end,9],payload['initial_writer'][1])
        radius=np.linalg.norm(b.ravel())/16
        for position,arm in enumerate((1,3)):
            raw=written[arm]-b;distance=np.linalg.norm(raw.ravel())/16
            assert 0<distance<2*radius
            angle=2*np.arcsin(distance/(2*radius));c,s=np.cos(angle),radius*np.sin(angle)
            units=[]
            for h in (raw,raw.ravel()[payload['permutation']].reshape(16,16)):
                x=h.ravel()-np.sum(h)/256;flat=b.ravel()
                x=x-flat*np.dot(x,flat)/np.dot(flat,flat)
                length=np.linalg.norm(x)/16;assert length>1e-12
                units.append((x/length).reshape(16,16))
            errors.append(close(payload['control_units'][end,position],np.array(units)))
            forward=c*b+s*units[0]
            errors.extend((close(forward,written[arm]),close(payload['reconstructed_written'][end,position],forward),
                close(records[end,5+2*position],c*b-s*units[0]),close(records[end,6+2*position],c*b+s*units[1])))
            for control in (5+2*position,6+2*position):
                errors.append(close(np.linalg.norm((records[end,control]-b).ravel())/16,distance))
        stats=[];flags=[];direction=(payload['targets'][1]-payload['targets'][0])/2
        for record in records[end]:
            q=record-b;total=np.dot(q.ravel(),q.ravel());quarter=q[:,12:].ravel();flags.append(total>0)
            errors.extend((close(np.linalg.norm(record.ravel())/16,.3),close(record.mean(),0.)))
            stats.append((np.linalg.norm(record.ravel())/16,np.linalg.norm(q.ravel())/16,record.sum()/256,
                np.dot(q.ravel(),direction.ravel())/256,np.dot(quarter,quarter)/total if total>0 else 0.,max(abs(q.ravel()))))
        errors.append(close(payload['geometry'][end],np.array(stats)))
        np.testing.assert_array_equal(payload['geometry_energy_available'][end],flags)
    return max(errors)


def check_aliases(original,payload):
    raw,old=payload['descendants'],original['descendants']
    assert raw.shape[4]==20
    np.testing.assert_array_equal(raw[0,0],raw[1,0]);np.testing.assert_array_equal(raw[:,0,0],raw[:,0,1])
    assert not raw[:,0,2].any() and not raw[1,:,2].any()
    for record in range(20):
        np.testing.assert_array_equal(raw[:,:,:,1,record],old[:,:,:,1,0])
        np.testing.assert_array_equal(raw[:,0,:,0,record],old[:,0,:,1,0])
        close(payload['values'][:,:,1,record],original['values'][:,:,1,0])
    np.testing.assert_array_equal(raw[:,:,:,0,9],raw[:,:,:,0,19])
    scores=payload['values']
    np.testing.assert_array_equal(scores[...,0,0]+scores[...,0,1],np.ones_like(scores[...,0,0]))
    np.testing.assert_array_equal(scores[...,1,0],scores[...,1,1]);np.testing.assert_array_equal(scores[...,1,3],scores[...,1,4])
    return True


def verify_row(cases,row,indices):
    means=np.array([sum(block.ravel())/block.size for block in cases])
    close(row['block_means'],means);close(row['parent_means'],cases.mean(axis=-1))
    close(row['mean'],means.mean());close(row['minimum'],min(means));close(row['maximum'],max(means))
    close(row['pointwise_block_bootstrap_95'],np.percentile(np.sum(means[indices],axis=1)/len(means),(2.5,97.5)))
    for prefix,x in (('',means),('paired_',cases)):
        assert row[prefix+'positive']==int(np.count_nonzero(x>1e-12))
        assert row[prefix+'tied']==int(np.count_nonzero(abs(x)<=1e-12))
        assert row[prefix+'negative']==int(np.count_nonzero(x< -1e-12))


def check_summary(blocks,summary,rows,writer_rows):
    a=np.array([b['values'] for b in blocks]);assert a.ndim==9 and a.shape[5]==20 and len(rows)==60 and len(writer_rows)==12
    assert set(summary)=={'means','writer_means','proposal_details_means','geometry_means','R_weights_means'}
    close(summary['means'],sum(np.sum(b,axis=(0,5)) for b in a)/(len(a)*a.shape[1]*a.shape[6]))
    for name,source_key in (('writer_means','writer_trace'),('proposal_details_means','proposal_details'),
                            ('geometry_means','geometry'),('R_weights_means','R_weights')):
        close(summary[name],sum(np.sum(b[source_key],axis=0) for b in blocks)/(len(blocks)*a.shape[1]))
    seed=hashlib.sha256(b'l24-temporal-filter-v1:block-bootstrap').digest()
    indices=np.random.default_rng(int.from_bytes(seed[:16],'little')).integers(0,len(a),(10000,len(a)))
    for group,metric in enumerate((0,2,4)):
        for reader in range(2):
            for pos,(positive,negative) in enumerate(PAIRS):
                row=rows[20*group+10*reader+pos]
                assert row['reader']==('native_T','theta_only')[reader] and row['label']==LABELS[pos]
                assert row['metric']==('damage_fidelity','damage_projection','damage_squared_error')[group]
                cases=np.array([[[b[p,reader,-1,0,10+positive,d,0,metric]-b[p,reader,-1,0,10+negative,d,0,metric]
                    for d in range(a.shape[6])] for p in range(a.shape[1])] for b in a])
                verify_row(cases,row,indices)
    for group,(field,region,metric) in enumerate(((1,2,0),(1,0,1),(0,2,0))):
        for arm in range(1,5):
            row=writer_rows[4*group+arm-1]
            assert row['label']==('theta_delta_rms_whole','theta_delta_projection_posterior','R_delta_rms_whole')[group]
            assert row['exposure']==('baseline','sustained','early_pulse','late_pulse','dose_matched_sustained')[arm]
            cases=np.array([[[b['writer_trace'][p,-1,arm,field,region,metric]] for p in range(a.shape[1])] for b in blocks])
            verify_row(cases,row,indices)
    return True
