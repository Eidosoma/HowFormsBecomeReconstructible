"""Unchanged E012 predictors; only the graph given to the decoy selector differs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from E012_graph_informed_repair import design as previous
import numpy as np

CFG=previous.CFG
IDS=tuple(range(11000,11128))
BENCH_ID=900513
WRONG_OFFSET=1000000
MODEL_PATH=ROOT/"E012_graph_informed_repair/runs/development_v1/models.json"
MODEL_SHA="259d4b401ca4bddc2f4c98dcfe64692018f3928c12d6f578114a7ffdced5d922"
POLICIES=("graph","native","source","strongest","wrong_graph","uniform")
PREDICTORS=("graph","native","source","wrong_graph")
CONDITIONS=previous.CONDITIONS
BASE_NAMES=previous.BASE_NAMES
GRAPH_NAMES=previous.GRAPH_NAMES
center_menu=previous.center_menu
observe=previous.observe
read=previous.read


def make_source(block,cfg=CFG):
    source=previous.make_source(block,cfg)
    wrong=previous.previous.old.rewire(WRONG_OFFSET+block)
    source.update({"wrong_"+key:value for key,value in wrong.items()})
    source["wrong_graph_seed"]=np.array(WRONG_OFFSET+block,dtype=np.int64)
    return source


def features_pair(source,raw_a,observed_a):
    actual=previous.features(source,raw_a,observed_a)
    substitute=dict(source);substitute["graph_neighbors"]=source["wrong_graph_neighbors"]
    wrong=previous.features(substitute,raw_a,observed_a)
    np.testing.assert_array_equal(actual[...,:17],wrong[...,:17])
    return actual,wrong


def select(actual,wrong,a,heuristic,models):
    original=previous.select(actual,a,heuristic,models)
    wrong_prediction=previous.scores(wrong,a,models)[:,:,0]
    predicted=np.concatenate((original["predicted"],wrong_prediction[:,:,None]),axis=2)
    choices=np.concatenate((original["choices"],wrong_prediction.argmax(axis=2)[:,:,None]),axis=2)
    weights=np.zeros((*choices.shape[:2],len(POLICIES),8))
    weights[:,:,:4]=original["weights"][:,:,:4]
    for i in range(len(choices)):
        for f in range(4):weights[i,f,4,choices[i,f,4]]=1.
    weights[:,:,5]=.125
    return dict(predicted=predicted,choices=choices,weights=weights)
