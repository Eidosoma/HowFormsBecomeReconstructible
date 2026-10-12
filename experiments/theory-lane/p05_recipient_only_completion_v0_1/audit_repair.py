"""Scalar reference reconstruction; imports neither repair nor the native reader."""
import hashlib
import json
import numpy as np
from common import equal


def rng(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def reconstruct(outgoing,incoming,common,original_mask,nodes,parts):
    observed=sorted(abs(float(x)) for x in outgoing.ravel() if x!=0)
    n=len(observed)
    magnitude=(observed[n//2] if n%2 else (observed[n//2-1]+observed[n//2])/2) if n else 0.
    result=np.repeat(outgoing[None],9,axis=0);result[0]=incoming;result[8]=0.
    full=np.zeros((2,16,16),bool);missing=[];signs=[];outside=0
    for axis in (0,1):
        for y in range(16):
            for x in range(16):
                yy,xx=(y,(x+1)%16) if axis==0 else ((y+1)%16,x)
                q=int(nodes[y,x])*int(nodes[yy,xx]);unavailable=original_mask[y,x] or original_mask[yy,xx]
                if unavailable:assert outgoing[axis,y,x]==0
                b=unavailable and incoming[axis,y,x]!=0;full[axis,y,x]=b
                if common[axis,y,x]:
                    assert b
                    result[2,axis,y,x]=abs(incoming[axis,y,x])*q
                if b:
                    result[3,axis,y,x]=incoming[axis,y,x]
                    result[4,axis,y,x]=abs(incoming[axis,y,x])*q
                    result[5,axis,y,x]=magnitude*q
                if outgoing[axis,y,x]==0:
                    missing.append((axis,y,x));signs.append(q);outside+=not unavailable
                    if magnitude>0:result[6,axis,y,x]=magnitude*q
    permutation=rng(parts).permutation(len(missing))
    if magnitude>0:
        for coordinate,idx in zip(missing,permutation):result[(7,*coordinate)]=magnitude*signs[idx]
    return result,full,magnitude,outside


def check_case(records,outgoing,incoming,common,mask,nodes,parts):
    expected,full,magnitude,outside=reconstruct(outgoing,incoming,common,mask,nodes,parts)
    equal(records,expected,'independent repair construction')
    for vi in range(2,8):equal(records[vi][outgoing!=0],outgoing[outgoing!=0],'observed weights preserved')
    equal(abs(records[3]),abs(records[4]),'own versus completed same unsigned record')
    equal(abs(records[6]),abs(records[7]),'recipient versus shuffled same unsigned record')
    equal(np.sort(records[6][outgoing==0]),np.sort(records[7][outgoing==0]),'same missing sign and magnitude multiset')
    return full,magnitude,outside
