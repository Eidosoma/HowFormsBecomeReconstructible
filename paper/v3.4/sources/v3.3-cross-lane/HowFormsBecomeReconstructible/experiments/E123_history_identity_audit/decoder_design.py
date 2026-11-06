"""Finite E123 observer specification; no retained outcomes enter these choices."""
from __future__ import annotations
import hashlib
import numpy as np

BLOCKS=tuple(range(12000,12064))
FACTORS=(1,4)
CHECKPOINTS=(1,3,8,16,32,64,128,256)
TRAIN_HORIZONS=(16,256)
RIDGES=(1.,.1,.01,.001)
TEMPERATURES=(0.,1.,.5,2.,.25,4.,8.,16.)  # inverse temperatures
EPSILON=1e-6
EPSILON_SENSITIVITY=(1e-9,1e-3)
FIT_VIEWS=("record","body","joint")
OUTER_FOLDS=8
INNER_FOLDS=4
MAXITER=2000  # Uniform numerical-budget amendment; see DECODER_AMENDMENT_V2.md.
FTOL=1e-12
GTOL=1e-7
GRADIENT_LIMIT=1e-5


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fold_map(blocks=BLOCKS, outer=None):
    prefix="E123:outer:v1" if outer is None else f"E123:inner:v1:{outer}"
    n=OUTER_FOLDS if outer is None else INNER_FOLDS
    ordered=sorted(set(int(x) for x in blocks),key=lambda b:digest(f"{prefix}:{b}"))
    if len(ordered)<n:
        raise ValueError("Fewer independent groups than folds")
    return {b:i%n for i,b in enumerate(ordered)}


def shuffle_map(blocks=BLOCKS):
    return {int(b):sorted(range(4),key=lambda k:digest(f"E123:shuffle:v1:{b}:{k}")) for b in blocks}


def shuffled_labels(y, groups):
    mappings=shuffle_map(set(groups))
    return np.array([mappings[int(g)][int(label)] for g,label in zip(groups,y)],dtype=np.int64)


def bootstrap_indices(n=64, draws=10000):
    seed=int(digest("E123:bootstrap:v1")[:32],16)
    return np.random.Generator(np.random.PCG64(seed)).integers(0,n,size=(draws,n))


def split_manifest(blocks=BLOCKS):
    outer=fold_map(blocks)
    return dict(outer=outer,inner={f:fold_map([b for b in blocks if outer[b]!=f],f) for f in range(OUTER_FOLDS)},
                shuffled_training_labels=shuffle_map(blocks),unit="Independent source block")
