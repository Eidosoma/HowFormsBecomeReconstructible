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
    assert cfg['blocks']==list(range(81000,81016))
    assert cfg['cases_per_block']==16 and cfg['cohort_size']==256
    assert cfg['history_by_block']=={str(b):(b-81000)%4 for b in cfg['blocks']}
    assert cfg['generations']==list(range(15,33))
    assert cfg['start_generation']==15 and cfg['terminal_generation']==32
    assert cfg['variants']==[n+'_'+p for n in ['matched','noise_0999','noise_0'] for p in ['baseline','repeated']]
    assert cfg['correlations']==[1.,.999,0.] and cfg['noise_regimes']==['matched','noise_0999','noise_0']
    assert cfg['policies']==['baseline','repeated']
    assert cfg['cycle']==dict(read_steps=2048,settling_steps=1024,write_steps=128)
    assert cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25)
    assert cfg['budgets']==[2048] and cfg['settling_steps']==1024
    assert all(cfg['development_config'][key]==value for key,value in cfg['reader'].items())
    assert cfg['development_config']['writer_beta']==3. and cfg['tolerance']==1e-4
    assert cfg['injury_cells']==24
    assert cfg['optimizer']['starts']==16 and cfg['optimizer']['maximum_sweeps']==64
    assert cfg['optimizer']['seed']==2026101004
    assert cfg['continuation_namespace']=='P05_serial_repair_v0_1'
    assert cfg['innovation_namespace']=='P05_cue_noise_repair_v0_1'
    assert cfg['bootstrap_replicates']==20000 and cfg['bootstrap_seed']==2026101102
    assert cfg['workers']==cfg['numerical_threads']==1
    assert cfg['scientific_read_contexts']==27648 and cfg['scheduled_optimizer_calls']==13824
    assert cfg['new_mismatched_read_contexts']==18432 and cfg['matched_replay_read_contexts']==9216
    assert cfg['native_audit_generations']==[15,32]
    assert cfg['forecast_ceiling_cpu_seconds']==10800
    assert cfg['primary_contrast']=='noise_0_repeated_minus_baseline'
    assert cfg['contrasts']=={
        'matched_repeated_minus_baseline':[-1,1,0,0,0,0],
        'noise_0999_repeated_minus_baseline':[0,0,-1,1,0,0],
        'noise_0_repeated_minus_baseline':[0,0,0,0,-1,1],
        'noise_0999_repeated_minus_matched':[0,-1,0,1,0,0],
        'noise_0_repeated_minus_matched':[0,-1,0,0,0,1],
        'noise_0999_baseline_minus_matched':[-1,0,1,0,0,0],
        'noise_0_baseline_minus_matched':[-1,0,0,0,1,0],
        'noise_0999_gain_minus_matched':[1,-1,-1,1,0,0],
        'noise_0_gain_minus_matched':[1,-1,0,0,-1,1]}
    assert np.__version__==cfg['numpy_version']
    assert not cfg['automatic_polling'] and not cfg['automatic_successor']


