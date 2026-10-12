"""Independent reader and writer sign-coordinate checks on synthetic bodies."""
import numpy as np
import native as n
import support as s


def edge_signs(signs):
    signs=np.asarray(signs).reshape(256)
    return np.stack([signs*signs[n.RIGHT],signs*signs[n.DOWN]])


def native(weights,mask,seed,signs=None):
    cfg=dict(reader=dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32),settling_steps=1024,random_namespace='TT011_SYNTHETIC')
    class Draw:
        def __init__(self):self.rng=np.random.default_rng(seed)
        def standard_normal(self,size):
            s.require(size==2048,'Complete native noise panel')
            x=self.rng.standard_normal(size).reshape(8,256)
            if signs is not None:x=x*np.asarray(signs).reshape(1,256)
            return x.ravel()
    original=n.random_stream
    try:
        n.random_stream=lambda *parts:Draw()
        return n.read_packets(n.encode(weights.reshape(1,1,2,256)),mask[None],np.array([0]),np.array([0]),cfg,0,[0],[1536,2048])
    finally:n.random_stream=original


def writer(body,mask):
    body=body.reshape(2,256);x=np.tanh(3*body);contrast=(x[0]-x[1])/2
    q=np.stack([contrast*contrast[n.RIGHT],contrast*contrast[n.DOWN]])
    c=np.stack([(x[0]*x[0,n.RIGHT]+x[1]*x[1,n.RIGHT])/2,(x[0]*x[0,n.DOWN]+x[1]*x[1,n.DOWN])/2])
    available=n.available(mask);exact=np.where(available,np.where(q==0,c,q),0.)
    tolerance=np.where(available,np.where(abs(q)<=1e-4,c,q),0.)
    return dict(q=q,c=c,exact=exact,tolerance=tolerance,sign_restored=np.sign(exact)*abs(tolerance))


def run():
    trials=[];maximum=0.
    for seed in [41031,41032,41033]:
        rng=np.random.default_rng(seed);weights=rng.uniform(-1,1,(2,16,16));weights[rng.random(weights.shape)<.1]=0
        bits=rng.integers(0,2,256);bits[np.concatenate(n.PORTS)]=0;signs=1-2*bits
        mask=np.zeros((16,16),bool);mask.flat[rng.choice(n.ELIGIBLE,24,replace=False)]=True
        transform=weights.reshape(2,256)*edge_signs(signs)
        first=native(weights,mask,seed+1000);second=native(transform,mask,seed+1000,signs)
        errors={}
        for key in ['birth','end','port_windows','mean_ports']:
            expected=first[key]*signs.reshape(16,16) if key in ['birth','end'] else first[key]
            errors[key]=s.close(expected,second[key],1e-12,'Native coordinate symmetry '+key);maximum=max(maximum,errors[key])
        bad=native(transform,mask,seed+1000)
        bad_error=float(np.max(abs(first['end']*signs.reshape(16,16)-bad['end'])))
        s.require(bad_error>1e-5,'Untransformed-noise negative control')
        trials.append(dict(seed=seed,errors=errors,untransformed_noise_error=bad_error))
    output_signs=np.ones(256);output_signs[n.PORTS[1]]=-1
    changed=native(weights.reshape(2,256)*edge_signs(output_signs),mask,seed+1000,output_signs)
    s.close(first['mean_ports']*np.array([-1.,1.]),changed['mean_ports'],1e-12,'Unpinned output changes observable sign')
    output_error=float(np.max(abs(first['mean_ports']-changed['mean_ports'])));s.require(output_error>1e-5,'Output port negative control')
    input_signs=np.ones(256);input_signs[n.PORTS[0]]=-1
    bad=native(weights.reshape(2,256)*edge_signs(input_signs),mask,seed+1000,input_signs)
    input_error=float(np.max(abs(first['end']*input_signs.reshape(16,16)-bad['end'])))
    s.require(input_error>=2.,'Fixed input cue breaks unpinned input symmetry')
    rng=np.random.default_rng(212789);d=rng.uniform(-.25,.25,(16,16));m=rng.uniform(-.4,.4,(16,16))
    d[::3,::3]=0.;d[1::3,1::3]=1e-6;body=np.arctanh(np.stack([m+d,m-d]))/3
    signs=1-2*rng.integers(0,2,256);left=writer(body,mask);right=writer(body*signs.reshape(16,16),mask)
    writer_errors={key:s.close(value*edge_signs(signs),right[key],1e-15,'Writer covariance '+key) for key,value in left.items()}
    s.close(n.decode(n.recapture(body[None],mask[None]))[0],left['exact'],0.,'Previously audited original writer')
    live=n.available(mask);fallback=int((live&(left['q']==0)).sum());extra=int((live&(left['q']!=0)&(abs(left['q'])<=1e-4)).sum())
    s.require(fallback>0 and extra>0,'Both fallback branches exercised')
    # Check the recorded synthetic-source observations without importing its functions.
    source=s.read(s.HERE/'source/alignment/results/SYMMETRY.json')
    s.require(source['status']=='PASS' and source['exact_fallback_edges']==fallback and source['tolerance_additional_fallback_edges']==extra,'Source synthetic branch counts')
    for ours,theirs in zip(trials,source['reader_trials'],strict=True):
        s.require(ours['seed']==theirs['seed'],'Synthetic seed identity')
        for key in ours['errors']:s.close(ours['errors'][key],theirs['errors'][key],1e-12,'Source symmetry discrepancy')
        s.close(ours['untransformed_noise_error'],theirs['untransformed_noise_endpoint_error'],1e-12,'Source noise negative control')
    return dict(status='PASS',reader_trials=trials,maximum_conjugacy_error=maximum,output_unpinned_error=output_error,input_unpinned_error=input_error,
                writer_errors=writer_errors,exact_fallback_edges=fallback,tolerance_extra_fallback_edges=extra,
                synthetic_native_trajectories=11,new_saved_case_task_outcomes=0,
                scope='Coordinate symmetry with transformed birth and noise; marginal, not unchanged paired-noise equivalence.')
