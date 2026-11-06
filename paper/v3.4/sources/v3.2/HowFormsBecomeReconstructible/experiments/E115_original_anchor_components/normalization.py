"""Retain original anchors, with E114's unchanged pair-common norm and scales."""
import math
import numpy as np
from E111_halfway_component_cross.model import validate_state, initial as original_initial
from E114_matched_component_amplitude.normalization import calculate
from E115_original_anchor_components.plan import COMPONENTS, full_component


def initial(sources,norm,component):
    assert component in COMPONENTS
    a,k=component;anchor=sources[a]['switch_state'];n=len(anchor)//2
    scales=norm['scales'];assert scales.shape==(n,2)
    assert np.isfinite(scales).all() and ((scales>=0)&(scales<=1)).all()
    if k=='B':return anchor.copy()
    alpha=np.tile(scales[:,int(k=='D')],2)[:,None,None,None]
    target=original_initial(sources,full_component(component))
    state=anchor+alpha*(target-anchor)
    state=np.where(alpha==0,anchor,np.where(alpha==1,target,state))
    validate_state(state,sources['O']['used_masks']);return state


def verify_sizes(sources,norm):
    n=len(norm['target']);states={c:initial(sources,norm,c) for c in COMPONENTS}
    actual=np.zeros((2,n,2,2));errors=np.zeros(n);leaks=np.zeros(n)
    for h,a in enumerate('ON'):
        assert states[a+'B'].tobytes()==sources[a]['switch_state'].tobytes()
        for comp,k in enumerate('MD'):
            z=(states[a+k]-states[a+'B']).reshape(2,n,2,16,16)
            expected=(norm['source_md'][1,:,:,comp]-norm['source_md'][0,:,:,comp])*(1 if a=='O' else -1)
            expected=expected*norm['scales'][:,comp][None,:,None,None]
            for cue in (0,1):
                np.testing.assert_allclose(z[:,:,cue],expected*(1 if comp==0 or cue==0 else -1),rtol=0,atol=4e-15)
            changed=(z[:,:,0]+z[:,:,1])*.5 if comp==0 else (z[:,:,0]-z[:,:,1])*.5
            leakage=(z[:,:,0]-z[:,:,1])*.5 if comp==0 else (z[:,:,0]+z[:,:,1])*.5
            for j in range(n):
                vals=changed[:,j][:,norm['free'][j]]
                if vals.shape[1]:
                    each=np.array([math.fsum(map(float,abs(v)))/len(v) for v in vals]);actual[h,j,comp]=each
                    errors[j]=max(errors[j],abs(float(each.mean())-norm['target'][j]))
                leaks[j]=max(leaks[j],float(abs(leakage[:,j]).max(initial=0)))
            zero=np.tile(norm['scales'][:,comp]==0,2);full=np.tile(norm['scales'][:,comp]==1,2)
            assert states[a+k][zero].tobytes()==states[a+'B'][zero].tobytes()
            assert states[a+k][full].tobytes()==original_initial(sources,full_component(a+k))[full].tobytes()
    assert errors.max(initial=0)<=4e-15 and leaks.max(initial=0)<=4e-15
    return dict(anchor_actual_sizes=actual,actual_sizes=actual.mean(0),maximum_size_error=errors,maximum_component_leak=leaks)
