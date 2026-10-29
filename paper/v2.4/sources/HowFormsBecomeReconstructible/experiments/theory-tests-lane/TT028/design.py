"""Prospective sparse panel: own-body writers and matched source controls."""
from dataclasses import replace
import hashlib
import json
from common import model,BLOCKS,DISPOSABLE

TAG='TT028_conditional_correction_v1'
ROLES=('qualification','benchmark','confirmation')
FAMILIES=('common','residual')
BODIES=('own','foreign','neutral')
BUDGETS=(0,100,1000)
CORRECTED=tuple(f'corrected_{b:04d}' for b in BUDGETS)
ARMS=CORRECTED+('full_1000','zero_1000')
PRESERVE='corrected_0000'
FULL='corrected_1000'
DAMAGE=('mix000','mix050','mix100')
MIX=dict(zip(DAMAGE,(0.,.5,1.)))
STRATA=('positive_half_retained','negative_half_retained','both_polarities_retained')
INTERVENTION_ARRAYS=('original','noise','mix000','mix050','mix100','own_V','foreign_V','neutral_V','fresh','jitter','donor_indices')
PRIMARY='partial_correction'
ALPHA=.05/3
def arms(body):
    assert body in BODIES
    return ARMS if body=='own' else (PRESERVE,FULL)
def cells():return tuple((b,a) for b in BODIES for a in arms(b))
def indices(role):
    assert role in ROLES
    return BLOCKS if role=='confirmation' else DISPOSABLE
def schedule(role):
    assert role in ROLES
    return (2,8) if role=='confirmation' else (2,2) if role=='qualification' else (1,1)
def families(role):
    assert role in ROLES
    return ('residual',) if role=='benchmark' else FAMILIES
def damage_levels(role):
    assert role in ROLES
    return ('mix050',) if role=='benchmark' else DAMAGE
def configs(role):
    assert role in ROLES
    n=5 if role=='qualification' else 1000
    times=(0,1,2,3,5) if role=='qualification' else (0,1,100,101,1000)
    return (replace(model.CONFIG,replicates=4,sweeps=n,times=times),
        replace(model.READOUT,parents=4,draws=1,sweeps=n,times=(0,1,n)))
def options(arm,sweeps):
    assert arm in ARMS
    prefix,value=arm.rsplit('_',1)
    return ('subtract' if prefix=='corrected' else prefix),min(int(value),sweeps)
def incoming_version(damage):
    assert damage in DAMAGE
    return 'original' if damage=='mix000' else damage+'_incoming'
def alias(damage,body,arm):
    assert arm in arms(body)
    return incoming_version(damage) if arm==PRESERVE else f'{damage}_{body}_{arm}'
def versions(role):
    return ('original',)+tuple(incoming_version(d) for d in damage_levels(role) if d!='mix000')+tuple(
        alias(d,b,a) for d in damage_levels(role) for b,a in cells() if a!=PRESERVE)
def address(role,index,corruption,draw):
    assert role in ROLES and all(type(v) is int and v>=0 for v in (index,corruption,draw))
    data=json.dumps([TAG,role,index,corruption,draw],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:16],'little')
def corruption_seed(role,index,corruption):
    assert role in ROLES and all(type(v) is int and v>=0 for v in (index,corruption))
    data=json.dumps([TAG,'corruption',role,index,corruption],separators=(',',':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:16],'little')
def claims():
    return dict(partial_correction=dict(family='residual',damage='mix050',body='own',arm=FULL,endpoint='receiving',margin=.02),
        partial_body_specificity=dict(family='residual',damage='mix050',body='own',arm=FULL,endpoint='receiving_vs_foreign',margin=.05),
        full_replacement_correction=dict(family='residual',damage='mix100',body='own',arm=FULL,endpoint='receiving',margin=.05))
def expected(role,blocks):
    c,d=schedule(role);cfg,_=configs(role)
    contexts=blocks*c*len(families(role))
    repairs=contexts*len(damage_levels(role))*len(cells())
    reads=contexts*d*len(versions(role))
    baseline_native=blocks*(15+len(families(role))*(4*len(cfg.times)+12))
    baseline_saved=blocks*(27+len(families(role))*(4*len(cfg.times)+24))
    return dict(baseline_native_arrays=baseline_native,baseline_saved_arrays=baseline_saved,repair_batches=repairs,reader_batches=reads,native_batches=repairs+reads,
        individual_repairs=16*repairs,individual_assays=16*reads,
        native_arrays=baseline_native+repairs*len(cfg.times)*4+reads*12,
        intervention_arrays=contexts*len(INTERVENTION_ARRAYS),
        saved_arrays=baseline_saved+repairs*(len(cfg.times)*4+4)+reads*16+contexts*len(INTERVENTION_ARRAYS),
        paired_rows=repairs*d*16,body_rows=repairs*16,max_native_error=0.)
