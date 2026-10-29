"""All-case schedule, exact aliases and separate paired recipient namespace."""
from dataclasses import replace
import hashlib
import json
from common import model

ARMS = ('full_on', 'subtract_on', 'zero_on', 'zero_off')
WRITING = ARMS[:3]
FAMILIES = ('common', 'residual')
STRATA = ('positive_half_retained', 'negative_half_retained', 'both_polarities_retained')
TAG = 'TT025_paired_receiving_v1'
ROLES = ('qualification', 'benchmark', 'development')

def schedule(role):
    assert role in ROLES
    return (4, 4, 8) if role == 'development' else (1, 2, 2)  # history futures, new draws, cycles
def configs(role):
    assert role in ROLES
    sweeps = 5 if role == 'qualification' else 1000
    return replace(model.CONFIG, replicates=4, sweeps=sweeps, times=(0, 1, sweeps)), replace(model.READOUT, parents=4, draws=1, sweeps=sweeps, times=(0, 1, sweeps))
def versions(cycles): return ('initial',)+tuple(f'{arm}_{g:02d}' for arm in WRITING for g in range(1, cycles+1))
def alias(arm, generation):
    assert arm in ARMS and type(generation) is int and generation >= 0
    return 'initial' if generation == 0 or arm == 'zero_off' else f'{arm}_{generation:02d}'
def address(role, index, history, draw):
    if role not in ROLES or any(type(v) is not int or v < 0 for v in (index, history, draw)):
        raise ValueError('declared nonnegative recipient address required')
    raw = json.dumps([TAG, role, index, history, draw], separators=(',', ':')).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:16], 'little')
def expected(role, blocks):
    histories, draws, cycles = schedule(role)
    batches = blocks*histories*2*draws*len(versions(cycles))
    rows = blocks*histories*2*draws*4*16*cycles
    return dict(native_batches=batches, individual_assays=batches*16, native_arrays=batches*12,
                saved_arrays=batches*16, paired_rows=rows, max_native_error=0.)
