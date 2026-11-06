"""Scalar original-anchor state assembly independent of the vector constructor."""
import numpy as np
from E111_halfway_component_cross.audit import initial as full_initial
from E114_matched_component_amplitude.normalization_audit import calculate


def initial(sources,norm,component):
    assert len(component)==2 and component[0] in 'ON' and component[1] in 'BMD'
    a,k=component;anchor=sources[a]['switch_state'];n=len(anchor)//2
    if k=='B':return anchor.copy()
    b='N' if a=='O' else 'O';target=full_initial(sources,b+a if k=='M' else a+b)
    out=np.empty_like(anchor)
    for v,j,cue,y,x in np.ndindex(2,n,2,16,16):
        alpha=float(norm['scales'][j,int(k=='D')]);old=float(anchor[v*n+j,cue,y,x]);new=float(target[v*n+j,cue,y,x])
        out[v*n+j,cue,y,x]=old if alpha==0 else new if alpha==1 else old+alpha*(new-old)
    return out
