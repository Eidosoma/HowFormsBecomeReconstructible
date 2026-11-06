"""Keep H097's complete original audit, including its unmodified exclusion guard."""
import numpy as np
from h097 import audit as original
from h098 import model as m,compiler

def network(raw,graph,cohort,block,condition,precision):
    assert str(raw['writer_precision'])==precision and precision in compiler.PRECISIONS
    result=original.network(raw,graph,cohort,block,condition);checks=0;identity_count=0
    for node in graph['records']:
        pi=node['packet_index']
        if pi<0:continue
        expected=False
        if node['kind']=='neural':
            completion={k:raw['completion_'+k][pi] for k in ('masks','signs','outputs')};ideal=m.compile_record(completion,'neural')
            prior=m.get_record(raw,graph,node['parent_record'])['J'] if node['route']=='copy_repair' else ideal['J']
            g=node['generation']
            expected=bool(np.array_equal(raw['architecture_mask'][g],~np.eye(128,dtype=bool)) and raw['architecture_available'][g].all() and np.array_equal(prior,ideal['J']))
            if expected:
                for key,value in ideal.items():np.testing.assert_array_equal(m.get_record(raw,graph,node['id'])[key],value);checks+=1
                assert raw['compiler_iterations'][pi]==0 and raw['compiler_field_error'][pi]<=1e-24;identity_count+=1
        assert int(raw['compiler_identity_preserved'][pi])==int(expected);checks+=1
    return dict(result,numerical_checks=result['numerical_checks']+checks,identity_preserved_packets=identity_count,
        original_exclusion_guard_unchanged=True,precision=precision)
