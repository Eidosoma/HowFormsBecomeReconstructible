"""A source-independent random ordering, paired across cue-noise regimes."""
import hashlib
import json
import numpy as np
from sr_common import P


def order(stage, block, generation):
    if stage not in P['stages'] or generation not in P['generations']:
        raise ValueError('Undeclared allocation context')
    payload=[P['namespace'],stage,int(block),0,int(generation),'promotion_subset']
    seed=int.from_bytes(hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed)).permutation(4)
