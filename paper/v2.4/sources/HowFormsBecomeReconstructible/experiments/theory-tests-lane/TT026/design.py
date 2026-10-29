"""One episode, fixed duration grid and paired fresh recipients."""
from dataclasses import replace
import hashlib
import json
from common import model

BUDGETS = (0, 1, 10, 100, 1000)
CORRECTED = tuple(f'corrected_{b:04d}' for b in BUDGETS)
ARMS = CORRECTED+('full_1000','zero_1000')
FULL = 'corrected_1000'
PRESERVE = 'corrected_0000'
FAMILIES = ('common','residual')
STRATA = ('positive_half_retained','negative_half_retained','both_polarities_retained')
ROLES = ('qualification','benchmark','development')
TAG = 'TT026_writing_window_v1'
def schedule(role):
    assert role in ROLES
    return (4,4) if role == 'development' else (1,2)
def configs(role):
    assert role in ROLES
    n = 5 if role == 'qualification' else 1000
    gates = {min(b,n) for b in BUDGETS}
    times = tuple(sorted({0,1,n} | gates | {min(n,g+1) for g in gates}))
    return (replace(model.CONFIG, replicates=4, sweeps=n, times=times),
            replace(model.READOUT, parents=4, draws=1, sweeps=n, times=(0,1,n)))
def options(arm, sweeps):
    assert arm in ARMS
    prefix, value = arm.rsplit('_',1)
    return ('subtract' if prefix == 'corrected' else prefix), min(int(value), sweeps)
def versions(): return ('initial',)+tuple(a for a in ARMS if a != PRESERVE)
def alias(arm):
    assert arm in ARMS
    return 'initial' if arm == PRESERVE else arm
def address(role, index, history, draw):
    if role not in ROLES or any(type(v) is not int or v < 0 for v in (index,history,draw)):
        raise ValueError('declared nonnegative receiving address required')
    material = json.dumps([TAG,role,index,history,draw], separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:16], 'little')
def expected(role, blocks):
    h,d = schedule(role); cfg,_ = configs(role)
    contexts = blocks*h*len(FAMILIES); repairs = contexts*len(ARMS); reads = contexts*d*len(versions())
    return dict(native_batches=repairs+reads, repair_batches=repairs, reader_batches=reads,
        individual_repairs=16*repairs, individual_assays=16*reads,
        native_arrays=repairs*len(cfg.times)*4+reads*12,
        saved_arrays=repairs*(len(cfg.times)*4+4)+reads*16,
        paired_rows=contexts*d*len(ARMS)*16, body_rows=repairs*16,
        legacy_control_arrays=contexts*(24 if role == 'qualification' else 36), max_native_error=0.)
