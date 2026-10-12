"""Task-matched residual ranking with a fixed native/target-graph ablation."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from E009_repair_selection import design as previous
from E010_record_strength.design import observe
import numpy as np

CFG=previous.CFG
IDS=tuple(range(10000,10064))
DEV_IDS=tuple(range(7000,7064))
BENCH_ID=900412
CONDITIONS=tuple(x["name"] for x in previous.CONDITIONS)
POLICIES=("graph","native","source","strongest","uniform")
DEV_SOURCE=ROOT/"E009_repair_selection/runs/prediction_v1"
DEV_TARGET=ROOT/"E009_repair_selection/runs/evaluation_v1"
make_source=previous.make_source
read=previous.read
BASE_NAMES=("A_own","A_foreign","A_resolved","A_neighbor","record_mean","record_abs",
    "record_rms","record_own_dot","record_foreign_dot","record_native_product",
    "A_soft_own","A_soft_foreign","A_native_product","A_native_own_dot",
    "A_native_foreign_dot","A_native_soft_own_change","A_native_soft_foreign_change")
GRAPH_NAMES=("record_graph_product_change","A_graph_product_change","A_graph_own_dot_change",
    "A_graph_foreign_dot_change","A_graph_soft_own_change","A_graph_soft_foreign_change")


def center_menu(x):return x-x.mean(axis=2,keepdims=True)


def native_mean(x):
    return (np.roll(x,1,-1)+np.roll(x,-1,-1)+np.roll(x,1,-2)+np.roll(x,-1,-2))/4


def graph_mean(x,neighbors):
    return x.reshape(*x.shape[:-2],256)[...,neighbors].mean(axis=-1).reshape(x.shape)


def features(source,raw_a,observed_a):
    field=previous.old.tissue.unpack(source["repair_packets"][:,4:])
    v=raw_a["end"][:,:,4:,0]
    signs=np.where(source["prototype"]>0,1.,-1.)
    own=signs[:,None];foreign=((signs.sum(axis=0)[None]-signs)/3)[:,None]
    fn=native_mean(field);vn=native_mean(v)
    df=graph_mean(field,source["graph_neighbors"])-fn
    dv=graph_mean(v,source["graph_neighbors"])-vn
    spatial=lambda x:x.mean(axis=(-2,-1))
    recipients=lambda x:spatial(x).mean(axis=1)
    def soft(values):
        scores=[]
        for f in range(4):
            z=(values[f,:,:,None]*signs[None,None]-.2)/.2
            agreements=(1/(1+np.exp(-z))).mean(axis=(0,3,4))
            scores.append(np.stack((agreements[:,f],(agreements.sum(axis=1)-agreements[:,f])/3),axis=-1))
        return np.array(scores)
    soft_v=soft(v)
    cent=lambda x:x-x.mean(axis=(-2,-1),keepdims=True)
    soft_n=soft(v+.2*cent(vn-v))-soft_v
    soft_g=soft(v+.2*cent(dv))-soft_v
    base=[observed_a[:,4:,j] for j in range(4)]
    base += [spatial(field),spatial(abs(field)),np.sqrt(spatial(field**2)),
        spatial(field*own),spatial(field*foreign),spatial(field*fn),soft_v[...,0],soft_v[...,1],
        recipients(v*vn),recipients(vn*own[:,None]),recipients(vn*foreign[:,None]),
        soft_n[...,0],soft_n[...,1]]
    graph=[spatial(field*df),recipients(v*dv),recipients(dv*own[:,None]),
        recipients(dv*foreign[:,None]),soft_g[...,0],soft_g[...,1]]
    return np.stack(base+graph,axis=-1)


def fit(x,y):
    x=x.reshape(-1,x.shape[-1]);y=y.reshape(-1)
    scale=np.sqrt((x*x).mean(axis=0));scale=np.where(scale<1e-12,1.,scale)
    z=x/scale
    beta=np.linalg.solve(z.T@z+len(z)*.01*np.eye(z.shape[1]),z.T@y)
    return dict(scale=scale.tolist(),coefficients=beta.tolist(),penalty=.01,rows=len(z))


def scores(x,a,models):
    # Accept a leading block dimension; every menu is centered independently.
    x=center_menu(x);a=center_menu(a)
    values=[]
    for name,columns in (("graph",23),("native",17)):
        model=models[name]
        values.append(a+(x[...,:columns]/np.array(model["scale"]))@np.array(model["coefficients"]))
    return np.stack((*values,a),axis=2)


def select(x,a,heuristic,models):
    predicted=scores(x,a,models)
    choices=np.concatenate((predicted.argmax(axis=3),heuristic[...,None]),axis=2)
    weights=np.zeros((*choices.shape[:2],5,8))
    for i in range(len(choices)):
        for f in range(4):
            for j in range(4):weights[i,f,j,choices[i,f,j]]=1.
    weights[:,:,4]=.125
    return dict(predicted=predicted,choices=choices,weights=weights)
