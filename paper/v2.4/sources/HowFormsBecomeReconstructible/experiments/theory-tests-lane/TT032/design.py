"""Frozen full-replacement reset intervention on exposed starting records."""
from dataclasses import replace
import hashlib
import json
from common import model,BLOCKS,DISPOSABLE

TAG='TT032_spatial_reset_v1'
ROLES=('qualification','benchmark','development')
FAMILIES=('common','residual')
DAMAGE=('mix000','mix050','mix100')
MIX=dict(zip(DAMAGE,(0.,.5,1.)))
MASKS=('axis0_side0','axis0_side1','axis1_side0','axis1_side1')
BODIES=('own','foreign','neutral')
RESETS=('corrected','uniform','reversed')
BUDGETS=(0,1000)
CREDITS=('target','donor','template','opposite')
GEOMETRIES=('positive_half_retained','negative_half_retained','both_polarities_retained')
def indices(role):
    assert role in ROLES
    return BLOCKS if role=='development' else DISPOSABLE
def schedule(role):
    assert role in ROLES
    return (2,4) if role=='development' else (1,2) if role=='qualification' else (1,1)
def families(role):return FAMILIES if role=='development' else ('residual',)
def damages(role):return ('mix100',)
def configs(role):
    assert role in ROLES
    n=5 if role=='qualification' else 1000
    times=(0,1,2,3,5) if role=='qualification' else (0,1,100,101,1000)
    return (replace(model.CONFIG,replicates=4,sweeps=n,times=times),
        replace(model.READOUT,parents=4,draws=1,sweeps=n,times=(0,1,n)))
def budget(label,role):
    assert label in BUDGETS
    return 5 if role=='qualification' and label==1000 else label
def address(role,index,corruption,draw):
    assert role in ROLES and all(type(v) is int and v>=0 for v in (index,corruption,draw))
    data=json.dumps([TAG,role,index,corruption,draw],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:16],'little')
def expected(role,blocks):
    c,d=schedule(role);f=len(families(role));logical=blocks*c*f*4*3*3*2
    return dict(logical_repairs=logical,logical_reader_requests=blocks*c*f*d*(2+4*3*3),
        paired_rows=logical*d*16,body_rows=logical*16,
        actual_mask_bridges=blocks*c*f*3*2 if role=='development' else 0,
        actual_mask_arrays=blocks*c*f*3*2*24 if role=='development' else 0,
        receiving_environments=blocks*c*d,max_native_error=0.)
def upper(role,blocks):
    c,d=schedule(role);f=len(families(role))
    # All own/foreign states simulated directly; neutral exact aliases only.
    repairs=blocks*c*(f*48+10)
    readers=blocks*c*d*(f*25+6)
    return dict(repair_batches=repairs,reader_batches=readers,saved_arrays=24*repairs+16*readers)
