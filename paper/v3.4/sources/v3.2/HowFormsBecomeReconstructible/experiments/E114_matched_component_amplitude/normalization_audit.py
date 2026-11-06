"""Scalar construction independent of vector component assembly."""
import math
import numpy as np
from E105_cycle_input_control.audit import P


def calculate(sources):
    a=sources['O']['switch_state'];b=sources['N']['switch_state'];n=len(a)//2
    mask=sources['O']['used_masks'];md=np.zeros((2,2,n,2,16,16));sizes=np.zeros((n,2));counts=np.zeros(n,int)
    free=np.zeros((n,16,16),bool)
    for j in range(n):
        values=[[],[]]
        for y,x in np.ndindex(16,16):
            available=not mask[j,y,x] and not P[0,y,x];free[j,y,x]=available;counts[j]+=int(available)
            for v in (0,1):
                for h,state in enumerate((a,b)):
                    plus=float(state[v*n+j,0,y,x]);minus=float(state[v*n+j,1,y,x])
                    md[h,v,j,0,y,x]=(plus+minus)*.5;md[h,v,j,1,y,x]=(plus-minus)*.5
                if available:
                    for c in (0,1):values[c].append(abs(float(md[1,v,j,c,y,x])-float(md[0,v,j,c,y,x])))
        for c in (0,1):sizes[j,c]=math.fsum(values[c])/len(values[c]) if values[c] else 0.
    target=np.array([min(v) for v in sizes]);scales=np.zeros((n,2))
    for j,c in np.ndindex(n,2):scales[j,c]=target[j]/sizes[j,c] if sizes[j,c]>0 else 0.
    return dict(source_md=md,free=free,free_cells=counts,original_sizes=sizes,target=target,scales=scales)


def initial(sources,norm,component):
    assert len(component)==2 and set(component)<=set('ON')
    first=sources['O']['switch_state'];n=len(first)//2;out=np.zeros_like(first);md=norm['source_md'];scales=norm['scales']
    for v,j,cue,y,x in np.ndindex(2,n,2,16,16):
        parts=[]
        for c in (0,1):
            a=float(md[0,v,j,c,y,x]);b=float(md[1,v,j,c,y,x]);alpha=float(scales[j,c])
            if alpha==1:value=a if component[c]=='O' else b
            elif alpha==0:value=(a+b)*.5
            else:value=(a+b)*.5+(1 if component[c]=='N' else -1)*alpha*((b-a)*.5)
            parts.append(value)
        out[v*n+j,cue,y,x]=parts[0]+parts[1] if cue==0 else parts[0]-parts[1]
        if scales[j,0]==1 and scales[j,1]==1 and component[0]==component[1]:
            out[v*n+j,cue,y,x]=sources[component[0]]['switch_state'][v*n+j,cue,y,x]
    return out
