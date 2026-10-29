"""Immutable files and array commitments for recipient-only completion."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def descriptor(a):
    return dict(shape=list(a.shape),dtype=a.dtype.str,sha256=hashlib.sha256(a.tobytes()).hexdigest())


def equal(a,b,label='array'):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), label


def save_arrays(path, values):
    index=np.frombuffer(json.dumps({k:descriptor(a) for k,a in values.items()},sort_keys=True).encode(),np.uint8)
    with Path(path).open('xb') as f:
        np.savez_compressed(f,**values,__index__=index)
    return sha(path)


def arrays(path, expected=None):
    data=Path(path).read_bytes()
    if expected is not None:
        assert hashlib.sha256(data).hexdigest()==expected,str(path)
    with np.load(io.BytesIO(data),allow_pickle=False) as f:
        index=json.loads(f['__index__'].tobytes())
        assert set(f.files)==set(index)|{'__index__'}
        result={k:f[k] for k in index}
    for k,a in result.items():
        assert descriptor(a)==index[k],(str(path),k)
        if a.dtype.kind=='f':
            assert np.isfinite(a).all()
    return result


def status(folder, **values):
    temporary=folder/'STATUS.json.tmp'
    with temporary.open('w') as f:
        json.dump(dict(at_utc=stamp(),**values),f,indent=2,allow_nan=False)
        f.write('\n')
    temporary.replace(folder/'STATUS.json')


def validate(cfg):
    assert cfg['blocks']==list(range(83000,83132))
    assert cfg['cases_per_block']==16 and cfg['cohort_size']==2112
    assert cfg['history_by_block']=={str(b):(b-83000)%4 for b in cfg['blocks']}
    assert cfg['generations']==list(range(15,33))
    assert cfg['variants']==['repairs_1','repairs_6','repairs_18']
    assert cfg['repair_budgets']==[1,6,18]
    assert cfg['repair_generations']==[[15],[15,18,21,24,27,30],list(range(15,33))]
    assert cfg['cycle']==dict(read_steps=2048,settling_steps=1024,write_steps=128)
    assert cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25)
    assert cfg['correlations']==[0.] and cfg['noise_regimes']==['independent']
    assert cfg['tolerance_generations']==[[],[3],[3,5,7,9,11,13],[3,9,10,11,12,13]]
    assert cfg['optimizer']['starts']==16 and cfg['optimizer']['maximum_sweeps']==64
    assert cfg['optimizer']['seed']==2026101004 and cfg['tolerance']==1e-4 and cfg['injury_cells']==24
    assert cfg['scheduled_optimizer_calls']==52800 and cfg['scientific_read_contexts']==114048
    assert cfg['simulated_read_contexts']==114048 and cfg['acquisition_lineage_read_contexts']==29568
    assert cfg['workers']==cfg['numerical_threads']==1 and cfg['forecast_ceiling_cpu_seconds']==54000
    assert cfg['primary_endpoint']=='uninterrupted' and cfg['confirmatory_claim']
    assert cfg['bootstrap_seed']==2026101110 and cfg['bootstrap_replicates']==20000
    assert cfg['primary_integer_coefficients']=={'continual_benefit':[-1,0,1],'double_call_efficiency':[-7,17,-10]}
    assert cfg['primary_divisors']=={'continual_benefit':1,'double_call_efficiency':17}
    assert cfg['primary_one_sided_alpha']==.05 and cfg['efficiency_multiplier']==2
    assert cfg['additional_repair_calls']==[0,5,17]
    assert cfg['lineage_namespace']=='P08_repair_efficiency_v0_1_acquisition'
    assert cfg['continuation_namespace']=='P08_repair_efficiency_v0_1_continuation'
    assert cfg['innovation_namespace']=='P08_repair_efficiency_v0_1_innovation'
    assert np.__version__==cfg['numpy_version']
    assert not cfg['automatic_polling'] and not cfg['automatic_successor']
