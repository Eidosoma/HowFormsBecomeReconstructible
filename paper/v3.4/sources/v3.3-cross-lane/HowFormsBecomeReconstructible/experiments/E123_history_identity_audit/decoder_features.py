"""Target-blind, candidate-equivariant spatial features for E123 observers."""
from __future__ import annotations
from itertools import combinations
import numpy as np
from E123_history_identity_audit.interface import decode

BASE=("cosine","sign_agreement","mean_product","negative_mse","negative_mae",
      "residual_cosine","residual_sign_agreement","gradient_cosine","cosine_squared","signed_agreement_squared")
COMMON={"A_background","A_factor","D"}
RESOURCES={"setup":set(),"record":{"R"},"body":{"B"},"joint":{"R","B"},
           "outgoing":{"O"},"body_postwrite":{"B_postwrite"}}


def cosine(x,p):
    x=x.reshape(len(x),-1);p=p.reshape(len(p),-1)
    x=x-x.mean(axis=1,keepdims=True);p=p-p.mean(axis=1,keepdims=True)
    nx=np.linalg.norm(x,axis=1);np_=np.linalg.norm(p,axis=1)
    denominator=nx[:,None]*np_[None,:]
    valid=(nx[:,None]>1e-12)&(np_[None,:]>1e-12)
    # Per-row reduction gives identical inputs identical features regardless of
    # batch size; a BLAS matrix product can change reduction order with its shape.
    numerator=(x[:,None,:]*p[None,:,:]).sum(axis=-1)
    return np.divide(numerator,denominator,out=np.zeros_like(denominator),where=valid)


def channel_features(x,p,g):
    c=cosine(x,p)
    same=((x[:,None]>0)==(p[None]>0)).mean(axis=(-2,-1))
    difference=x[:,None]-p[None]
    gradient_x=np.concatenate([(np.roll(x,-1,a)-x).reshape(len(x),-1) for a in (-2,-1)],axis=1)
    gradient_p=np.concatenate([(np.roll(p,-1,a)-p).reshape(len(p),-1) for a in (-2,-1)],axis=1)
    return np.stack((c,same,(x[:,None]*p[None]).mean(axis=(-2,-1)),
        -(difference**2).mean(axis=(-2,-1)),-np.abs(difference).mean(axis=(-2,-1)),
        cosine(x-g,p-g),(((x-g)[:,None]>0)==((p-g)[None]>0)).mean(axis=(-2,-1)),
        cosine(gradient_x,gradient_p),c*c,(2*same-1)**2),axis=-1)


def build(inputs,view):
    """One block dictionary; R/O: N×bytes, B: N×3×16×16. Reject metadata."""
    if view not in RESOURCES or set(inputs)!=COMMON|RESOURCES[view]:
        raise ValueError("Only the exact declared resource whitelist may enter features")
    d=np.asarray(inputs["D"]);g=np.asarray(inputs["A_background"])
    if d.shape!=(4,16,16) or g.shape!=(16,16) or d.dtype!=np.float64 or g.dtype!=np.float64:
        raise ValueError("Native float64 dictionary/background required")
    factor=np.asarray(inputs["A_factor"])
    if factor.shape!=() or factor.dtype.kind not in "iu" or int(factor) not in (1,4):
        raise ValueError("Public factor must be the declared scalar integer")
    if not np.isfinite(d).all() or not np.isfinite(g).all():
        raise ValueError("Nonfinite context")
    if view=="setup":
        return np.empty((1,4,0)),np.zeros((1,4)),[]
    channels=[];names=[]
    if view in ("record","joint","outgoing"):
        key="O" if view=="outgoing" else "R"
        packet=np.asarray(inputs[key])
        if packet.ndim!=2:
            raise ValueError("Packets require an explicit case dimension")
        channels.append(decode(packet,int(factor)));names.append("record")
    if view in ("body","joint","body_postwrite"):
        key="B_postwrite" if view=="body_postwrite" else "B"
        body=np.asarray(inputs[key])
        if body.ndim!=4 or body.shape[1:]!=(3,16,16) or body.dtype!=np.float64 or not np.isfinite(body).all():
            raise ValueError("Native three-channel body batch required")
        channels.extend([body[:,i] for i in range(3)]);names.extend(("v","ema","ref"))
    if len({len(x) for x in channels})!=1:
        raise ValueError("Resources have different case counts")
    base=[channel_features(x,d,g) for x in channels]
    terms=base.copy();feature_names=[f"{name}:{term}" for name in names for term in BASE]
    for i,j in combinations(range(len(base)),2):
        terms.append((base[i][...,0]*base[j][...,0])[...,None])
        terms.append(((2*base[i][...,1]-1)*(2*base[j][...,1]-1))[...,None])
        feature_names.extend((f"{names[i]}*{names[j]}:cosine",f"{names[i]}*{names[j]}:signed_agreement"))
    features=np.concatenate(terms,axis=-1)
    scores=np.mean([a[...,0] for a in base],axis=0)
    if view=="joint":
        scores=.5*base[0][...,0]+.5*np.mean([a[...,0] for a in base[1:]],axis=0)
    assert np.isfinite(features).all() and len(feature_names)==features.shape[-1]
    return np.ascontiguousarray(features),scores,feature_names
