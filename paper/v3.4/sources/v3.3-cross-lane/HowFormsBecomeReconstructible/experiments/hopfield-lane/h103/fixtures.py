"""Boundary, numerical, control and decision fixtures before new cohort outcomes."""
from copy import deepcopy
import numpy as np
from h103 import model as m,audit,report

def rejects(fn):
    try:fn()
    except (AssertionError,ValueError,KeyError):return
    raise AssertionError('forbidden or corrupt input accepted')
def run():
    tests=[];tape=m.tapes('fixture',0);x=tape['acquisition_birth']
    from h101 import model as previous
    from h102 import model as calibration
    assert m.read is previous.read and m.write is previous.write and m.acquire is previous.acquire
    initial,acquisition=m.acquire(tape);expected,reference=previous.acquire(tape)
    audit.equal(initial,expected)
    for key in acquisition:audit.equal(acquisition[key],reference[key])
    sources=np.stack((initial,initial[::-1],np.zeros_like(initial)))
    current=calibration.assess(dict(base=tape['base'],records=sources,cues=tape['cues'],birth=tape['assay_birth'],
        orders=tape['assay_orders'],uniform=tape['assay_uniform']),(3,))
    audit.equal(current['injury_masks'][0],tape['assay_mask'])
    for draw in range(2):
        direct=m.read(dict(weights=m.effective(tape['base'],sources[:,:,None],tape['assay_mask'][draw]),
            birth=tape['assay_birth'][draw],orders=tape['assay_orders'][draw],clamp_indices=m.INPUT,clamp_values=tape['cues']))
        for key,axis in (('initial',0),('final',0),('trace',1),('fields',2),('energies',1)):
            audit.equal(direct[key],np.take(current[f'assay_d{draw}_'+key],0,axis=axis))
    tests.append('acquisition is unchanged gain four; gain-two current reads exactly match H102 for own, donor and erased records')
    test_record=np.ones((64,64));np.fill_diagonal(test_record,0)
    weights=m.effective(tape['base'],test_record,np.ones((64,64),dtype=bool))
    expected=tape['base']+test_record;expected[:8,8:]*=2;expected[8:,:8]*=2
    audit.equal(weights,expected)
    np.testing.assert_allclose(weights,audit.weights(tape['base'],test_record,np.ones((64,64),dtype=bool)),rtol=0,atol=2e-15)
    assert (m.ACQUISITION_GAIN,m.ASSESSMENT_GAIN,m.SUPPLYING_GAIN)==(4.,2.,2.)
    tests.append('both post-acquisition roles use the frozen gain-two operator with an intact base')
    assert not np.array_equal(m.tapes('development',0)['base'],previous.tapes('development',0)['base'])
    assert not np.array_equal(m.tapes('development',0)['base'],m.tapes('confirmation',0)['base'])
    tests.append('H103 networks and reserved confirmation streams are independent of H101 and each other')
    for centered in (False,True):
        j=m.write(dict(activity=x),centered);audit.equal(j,audit.writer(x,centered))
        assert np.array_equal(j,j.swapaxes(-1,-2)) and not np.diagonal(j,axis1=-2,axis2=-1).any()
    tests.append('both complete writers match independent integer products and retain symmetry/zero diagonal')
    constant=np.ones((2,8,64),dtype=np.int8)
    assert not m.write(dict(activity=constant),True).any()
    assert np.all(m.write(dict(activity=constant))[:,np.triu_indices(64,1)[0],np.triu_indices(64,1)[1]]==.125)
    tests.append('zero centered contrast stays zero; ordinary constant coactivity has no fallback branch')
    for key in ('target','incoming_record','assessment'):
        rejects(lambda key=key:m.write(dict(activity=x,**{key:tape['targets']})))
    tests.append('writer rejects targets, incoming records and assessment information')
    initial=m.write(dict(activity=x));records,selections,scales=m.interventions(initial,tape['priority'],tape['random_priority'],m.VARIANTS)
    for candidate in m.CANDIDATES:
        v=m.VARIANTS.index(candidate);r=m.VARIANTS.index('random_'+candidate);s=m.VARIANTS.index('strength_'+candidate)
        audit.equal((records[v]!=0).sum((-2,-1)),(records[r]!=0).sum((-2,-1)))
        np.testing.assert_allclose(np.linalg.norm(records[v],axis=(-2,-1)),np.linalg.norm(records[s],axis=(-2,-1)),atol=2e-13,rtol=0)
        assert not (records[v][selections[candidate]]!=0).any()
        audit.equal(records[v][~selections[candidate]],initial[~selections[candidate]])
    audit.equal(records[m.VARIANTS.index('donor')],initial[::-1]);assert not records[m.VARIANTS.index('erased')].any()
    tests.append('one-shot pruning preserves outside bytes, random count matches and attenuation preserves pruned norm')
    packet=dict(weights=m.effective(tape['base'],initial,np.ones_like(initial,dtype=bool)),birth=x,
        orders=tape['acquisition_orders'],clamp_indices=m.INPUT,clamp_values=tape['cues'])
    saved=m.read(packet)
    def replay(data):
        stats=dict(coordinate_decisions=0,field_arrays_checked=0,sweep_states_checked=0,reads_replayed=0,
            maximum_field_error=0.,maximum_energy_error=0.,minimum_boundary_distance=float('inf'))
        audit.replay(audit.weights(tape['base'],initial,np.ones_like(initial,dtype=bool)),x,packet['orders'],m.INPUT,tape['cues'],data,stats)
        return stats
    stats=replay(saved);bad={k:v.copy() for k,v in saved.items()};bad['fields'][0,10,0,0]+=.01
    rejects(lambda:replay(bad));bad={k:v.copy() for k,v in saved.items()};bad['trace'][1,0,0,10]*=-1
    rejects(lambda:replay(bad))
    tests.append('long-double replay agrees and rejects corrupted local fields or sweep trajectories')
    bad=dict(packet,target=tape['targets']);rejects(lambda:m.read(bad))
    tests.append('post-acquisition reader rejects task targets')
    values=np.full((16,len(m.VARIANTS),3,5),.5)
    for control in ('erased','donor'):values[:,m.VARIANTS.index(control)]=.1
    assert report.selection(values,m.VARIANTS)['selected'] is None
    weak=m.VARIANTS.index('weak25');values[:,weak,0,0]=.7;values[:,weak,0,1]=.3
    assert report.selection(values,m.VARIANTS)['selected']=='weak25'
    other=m.VARIANTS.index('weak50');values[:,other,0,0]=.75;values[:,other,0,1]=.4
    assert report.selection(values,m.VARIANTS)['selected']=='weak25'
    altered=values.copy();altered[:,:,:,2:]=0
    assert report.selection(altered,m.VARIANTS)['selected']=='weak25'
    values[:,weak,0,1]=.5;values[:,other,0,1]=.5
    assert report.selection(values,m.VARIANTS)['selected'] is None
    tests.append('selection requires present benefit and later cost, ranks fixed candidates and ignores longer-horizon outcomes')
    delta=dict(mean=[.1,-.1,0,0,0],lower=[.05,-.15,-.01,-.01,-.01],upper=[.15,-.05,.01,.01,.01])
    lag=dict(convergence=dict(lower=[-.01]*3,upper=[.01]*3),shift=dict(lower=[-.01]*5,upper=[.01]*5))
    regain=dict(lower=[-.1]*3,upper=[.1]*3)
    d=report.duration(delta,lag,regain,True)
    assert d['converged_by_g2'] and d['one_generation_delay_compatible'] and not d['cost_through_four_handoffs'] and not d['regained_g0_by_g2']
    lag['shift']['upper'][0]=.03;assert not report.duration(delta,lag,regain,True)['one_generation_delay_compatible']
    delta['upper'][2:]=[-.01]*3;assert report.duration(delta,lag,regain,True)['cost_through_four_handoffs']
    delta=dict(lower=[.1,-.2,.1,-.2,.1],upper=[.2,-.1,.2,-.1,.2]);assert report.duration(delta,lag,regain,True)['resolved_alternation']
    tests.append('delay, convergence, recovery, persistent cost and alternation remain separate decisions')
    return dict(passed=True,count=len(tests),tests=tests,engineering_only=True,new_cohort_outcomes=False,reference_update_decisions=stats['coordinate_decisions'])
