"""Six fixed first-episode counterfactuals, using TT022's paired environments."""
from dataclasses import replace
from common import model

ARMS = ('full_on','full_off','subtract_on','subtract_off','zero_on','zero_off')
FAMILIES = ('common','residual')
STRATA = ('positive_half_retained','negative_half_retained','both_polarities_retained')
CACHED = {'full_on':'capture','zero_off':'capture_once'}

def options(arm):
    assert arm in ARMS
    memory, toggle = arm.rsplit('_',1)
    return memory, toggle == 'on'

def configs(role):
    assert role in ('qualification','benchmark','development')
    n = {'qualification':5,'benchmark':100,'development':1000}[role]
    parents = 1 if role == 'qualification' else 4
    return (replace(model.CONFIG, replicates=parents, sweeps=n, times=(0,1,n)),
            replace(model.READOUT, parents=parents, draws=1, sweeps=n, times=(0,1,n)))

def futures(role): return {'qualification':1,'benchmark':2,'development':4}[role]

def comparisons():
    return dict(fill_vs_full_on=('subtract_on','full_on'), fill_vs_zero_on=('subtract_on','zero_on'),
        full_vs_zero_on=('full_on','zero_on'), full_writing=('full_on','full_off'),
        subtract_writing=('subtract_on','subtract_off'), zero_writing=('zero_on','zero_off'),
        fill_vs_full_off=('subtract_off','full_off'), fill_vs_zero_off=('subtract_off','zero_off'))
