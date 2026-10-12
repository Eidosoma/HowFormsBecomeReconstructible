"""Frozen inputs and fixed statistical cases; no native simulation."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
PLAN=json.loads((HERE/'plan.json').read_text())
PATTERNS=np.array(list(itertools.product(range(3),repeat=3)),dtype=int)
sys.path.insert(0,str(HERE/'source/theory'))


def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def random(*parts):
    raw=json.dumps(list(parts),separators=(',',':')).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(raw).digest()[:16],'little')))


def verify_sources():
    m=json.loads((HERE/'source_manifest.json').read_text())
    for rel,h in m['files_sha256'].items():
        if sha(HERE/rel)!=h:raise ValueError('Source changed: '+rel)
    return m


def cases(mode):
    import two_mode
    if mode=='fixture':
        a=np.zeros(27,int);a[0]=16
        b=np.zeros(27,int);b[3]=128;b[10]=128
        return [dict(id='fixture_all_A',kind='technical',counts=a.tolist(),family=1,truth=None),
                dict(id='fixture_alternating',kind='technical',counts=b.tolist(),family=1,truth=None)]
    rows=[]
    if mode=='development':
        source=json.loads((HERE/'source/tt003/summary.json').read_text())
        with np.load(HERE/'source/tt003/observations.npz',allow_pickle=False) as observations:
            for case in source['cases']:
                for policy in ['full_rewrite','protected_copy']:
                    paths=observations[case['id']+'.'+policy]
                    codes=paths[:,0]*9+paths[:,1]*3+paths[:,2]
                    counts=np.bincount(codes,minlength=27)
                    if counts.tolist()!=case[policy]['pattern_counts']:raise ValueError('Native pattern table changed')
                    rows.append(dict(id=case['id']+'.'+policy,kind='native_development',counts=counts.tolist(),
                        family=PLAN['native_families'],truth=None,prior_fit=case[policy]['fit'],
                        source_packet_sha256=case['packet_sha256'],source_block=case['block']))
        for name,theta in PLAN['synthetic_parameters'].items():
            for n in PLAN['sample_sizes']:
                p=two_mode.pattern_probabilities(theta)
                count=random(*PLAN['random_namespace'],name,n).multinomial(n,p)
                rows.append(dict(id=f'synthetic_{name}_n{n}',kind='synthetic_model',counts=count.tolist(),family=1,truth=theta))
        for n in PLAN['sample_sizes']:
            counts=np.zeros(27,int);counts[3]=n//2;counts[10]=n//2
            rows.append(dict(id=f'alternating_n{n}',kind='constructed_misspecification',counts=counts.tolist(),family=1,truth=None))
        if len(rows)!=44:raise ValueError('Panel count changed')
    elif mode=='benchmark':
        specs=[('perfect',16),('two_transients',64),('two_transients',1024)]
        for name,n in specs:
            theta=PLAN['synthetic_parameters'][name]
            counts=random('TT006','excluded_benchmark',name,n).multinomial(n,two_mode.pattern_probabilities(theta))
            rows.append(dict(id=f'benchmark_{name}_n{n}',kind='technical',counts=counts.tolist(),family=1,truth=theta))
        counts=np.zeros(27,int);counts[3]=128;counts[10]=128
        rows.append(dict(id='benchmark_alternating_n256',kind='technical',counts=counts.tolist(),family=1,truth=None))
    else:raise ValueError('Unknown mode')
    return rows
