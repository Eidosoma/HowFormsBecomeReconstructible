"""Attenuate both axes symmetrically; one norm and scale per C/F pair."""
import math
import numpy as np
from E111_halfway_component_cross.model import validate_state, initial as original_initial, P
from E114_matched_component_amplitude.plan import COMPONENTS


def calculate(sources):
    x=np.stack([sources[o]['switch_state'] for o in ('O','N')]);count=x.shape[1]
    assert count%2==0;n=count//2;mask=sources['O']['used_masks']
    assert mask[:n].tobytes()==mask[n:].tobytes()
    for source in sources.values():validate_state(source['switch_state'],mask)
    # history x record x case x component x y x x
    md=np.stack(((x[:,:,0]+x[:,:,1])/2,(x[:,:,0]-x[:,:,1])/2),axis=2).reshape(2,2,n,2,16,16)
    delta=md[1]-md[0];free=(~mask[:n])&~P[0];norms=np.zeros((n,2));counts=free.sum((1,2))
    for j,c in np.ndindex(n,2):
        values=np.abs(delta[:,j,c][:,free[j]]).ravel()
        norms[j,c]=math.fsum(map(float,values))/len(values) if len(values) else 0.
    target=norms.min(1);scales=np.zeros_like(norms)
    np.divide(target[:,None],norms,out=scales,where=norms>0)
    assert np.isfinite(scales).all() and ((scales>=0)&(scales<=1)).all()
    return dict(source_md=md,free=free,free_cells=counts,original_sizes=norms,target=target,scales=scales)


def initial(sources,norm,component):
    assert component in COMPONENTS
    md=norm['source_md'];n=md.shape[2];scales=norm['scales'];assert scales.shape==(n,2)
    assert np.isfinite(scales).all() and ((scales>=0)&(scales<=1)).all()
    center=(md[0]+md[1])*.5;half=(md[1]-md[0])*.5;parts=[]
    for c,letter in enumerate(component):
        alpha=scales[:,c][None,:,None,None]
        z=center[:,:,c]+(1 if letter=='N' else -1)*alpha*half[:,:,c]
        # A zero range uses one identical midpoint, including signed-zero bits.
        z=np.where(alpha==0,center[:,:,c],z)
        z=np.where(alpha==1,md[int(letter=='N'),:,:,c],z)
        parts.append(z)
    state=np.stack((parts[0]+parts[1],parts[0]-parts[1]),axis=2).reshape(2*n,2,16,16)
    full=(scales==1).all(1);flat=np.tile(full,2)
    if component[0]==component[1]:state[flat]=sources[component[0]]['switch_state'][flat]
    validate_state(state,sources['O']['used_masks']);return state


def verify_sizes(sources,norm):
    n=len(norm['target']);states={c:initial(sources,norm,c) for c in COMPONENTS}
    actual=np.zeros((n,2,2));errors=np.zeros(n);leaks=np.zeros(n)
    for comp in (0,1):
        for other in 'ON':
            before=('O'+other) if comp==0 else (other+'O');after=('N'+other) if comp==0 else (other+'N')
            z=(states[after]-states[before]).reshape(2,n,2,16,16)
            expected=norm['source_md'][1,:,:,comp]-norm['source_md'][0,:,:,comp]
            expected=expected*norm['scales'][:,comp][None,:,None,None]
            for cue in (0,1):
                np.testing.assert_allclose(z[:,:,cue],expected*(1 if comp==0 or cue==0 else -1),rtol=0,atol=4e-15)
            changed=(z[:,:,0]+z[:,:,1])*.5 if comp==0 else (z[:,:,0]-z[:,:,1])*.5
            leakage=(z[:,:,0]-z[:,:,1])*.5 if comp==0 else (z[:,:,0]+z[:,:,1])*.5
            for j in range(n):
                vals=changed[:,j][:,norm['free'][j]]
                if vals.shape[1]:
                    each=np.array([math.fsum(map(float,abs(v)))/len(v) for v in vals]);size=float(each.mean())
                    errors[j]=max(errors[j],abs(size-norm['target'][j]));actual[j,comp]=each
                leaks[j]=max(leaks[j],float(abs(leakage[:,j]).max(initial=0)))
    assert errors.max(initial=0)<=4e-15 and leaks.max(initial=0)<=4e-15
    # Zero targets use exactly the same assembled state under all component labels.
    zero=np.tile(norm['target']==0,2)
    for state in states.values():assert state[zero].tobytes()==states['OO'][zero].tobytes()
    return dict(actual_sizes=actual,maximum_size_error=errors,maximum_component_leak=leaks)
