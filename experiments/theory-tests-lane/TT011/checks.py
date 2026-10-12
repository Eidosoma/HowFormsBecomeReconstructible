"""Meaningful positive, negative, ambiguity, corruption and scoring fixtures."""
import numpy as np
import arithmetic as a
import graph
import intake
import native as n
import scoring
import symmetry
import support as s


def run(output):
    results=dict(graph=graph.fixtures());results['scoring'],synthetic=scoring.fixtures()
    s.dump(output/'synthetic_analysis.json',synthetic)
    # Null/boolean checking prevents silently numericizing metadata or missing values.
    a.compare_tree({'a':[False,None,'x',1.]},{'a':[False,None,'x',1.]},'Heterogeneous fixture')
    failures=0
    for wrong in [{'a':[0,None,'x',1.]},{'a':[False,0,'x',1.]}]:
        try:a.compare_tree({'a':[False,None,'x',1.]},wrong,'Corrupted metadata')
        except ValueError:failures+=1
    s.require(failures==2,'Metadata corruption rejected')
    cfg=s.config('p05');old=s.prepared('p05',34000)
    baseline=intake.construct(old,old['donor_packets'],34000,cfg)
    reverse=np.arange(len(old['founders']))[::-1];permuted={k:old[k][reverse] for k in ['packets','original_masks','histories','founders','recipients']}
    actual=intake.construct(permuted,old['donor_packets'][reverse],34000,cfg)
    for key in baseline:s.equal(actual[key],baseline[key][reverse],'Record construction case-order invariance')
    zero=intake.construct(old,np.zeros_like(old['donor_packets']),34000,cfg)
    s.require(not zero['common_edges'].any() and not zero['common_magnitude_fraction'].any(),'Zero common support')
    for vi in [3,4,5,6]:s.equal(zero['packets'][:,vi],old['packets'][:,1],'Empty backup leaves outgoing')
    # One retained backup edge forces an identity permutation; it must not be rerolled.
    donor_weights=n.decode(old['donor_packets']);restricted=np.zeros_like(donor_weights)
    for case in range(len(restricted)):
        indices=np.flatnonzero(baseline['common_edges'][case]);s.require(len(indices)>0,'Fixture backup exists')
        j=int(indices[0]);restricted[case,0].flat[j]=donor_weights[case,0].flat[j];restricted[case,1].flat[j]=donor_weights[case,1].flat[j]
    singleton=intake.construct(old,n.encode(restricted),34000,cfg)
    s.require((singleton['common_nonzero_count']==1).all() and not singleton['scramble_sign_changes'].any(),'Identity permutation retained')
    s.equal(singleton['packets'][:,3],singleton['packets'][:,6],'Identity own and scramble')
    results['construction']=dict(case_order='PASS',zero_common_support='PASS',identity_permutation='PASS',metadata_corruptions_rejected=failures)
    results['symmetry']=symmetry.run()
    s.dump(output/'technical_checks.json',dict(status='PASS',checks=results));return results
