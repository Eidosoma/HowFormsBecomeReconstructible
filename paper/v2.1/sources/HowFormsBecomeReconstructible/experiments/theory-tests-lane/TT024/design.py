"""Fixed four-condition continuation on exposed records and environments."""
from dataclasses import replace
from common import model

ARMS=('full_on','subtract_on','zero_on','zero_off')
FAMILIES=('common','residual')
STRATA=('positive_half_retained','negative_half_retained','both_polarities_retained')
CACHED=('full_on','zero_off')
NEW=('subtract_on','zero_on')
PHASES=('develop','fission','repair','terminal')

def options(arm):
    assert arm in ARMS
    memory,write=arm.rsplit('_',1)
    return memory,write=='on'
def configs(role):
    assert role in ('qualification','benchmark','development')
    n={'qualification':5,'benchmark':100,'development':1000}[role]
    parents=1 if role=='qualification' else 4
    return (replace(model.CONFIG,replicates=parents,sweeps=n,times=(0,1,n)),
            replace(model.READOUT,parents=parents,draws=1,sweeps=n,times=(0,1,n)))
def schedule(role):return {'qualification':(1,2),'benchmark':(2,2),'development':(4,8)}[role]
def comparisons():
    return dict(subtract_vs_full=('subtract_on','full_on'),subtract_vs_zero=('subtract_on','zero_on'),
        subtract_vs_preserve=('subtract_on','zero_off'),full_vs_zero=('full_on','zero_on'),
        full_vs_preserve=('full_on','zero_off'),zero_vs_preserve=('zero_on','zero_off'))
def expected(role,blocks):
    futures,generations=schedule(role);batches=blocks*futures*len(FAMILIES)
    repairs=batches*2*(generations-1);reads=batches*2*(generations-1)
    return dict(arm_batches=4*batches,new_repairs=repairs,new_reads=reads,
        retained_repairs=2*batches*(generations+1),reused_read_slots=2*batches*(generations+3),
        native_arrays=12*(repairs+reads),max_native_error=0.)
