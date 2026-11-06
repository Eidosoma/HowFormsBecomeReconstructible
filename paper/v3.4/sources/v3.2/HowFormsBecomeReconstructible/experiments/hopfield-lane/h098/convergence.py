"""Compare complete logical inheritance across solver precisions and preserve the intact anchor."""
import numpy as np
from h097 import model as m


def compare(left,lg,right,rg):
    counts=dict(record_arrays=0,discrete_reader_arrays=0,native_reader_arrays=0,logical_read_uses=0)
    for key in ('packet_outputs','completion_masks','completion_signs','completion_outputs'):
        np.testing.assert_array_equal(left[key],right[key],err_msg='precision convergence '+key)
    assert len(lg['records'])==len(rg['records'])==367
    maximum_j=maximum_float=0.
    for a,b in zip(lg['records'],rg['records']):
        assert {k:v for k,v in a.items() if k!='parent_read'}=={k:v for k,v in b.items() if k!='parent_read'}
        av,bv=m.get_record(left,lg,a['id']),m.get_record(right,rg,b['id'])
        for key in av:
            if a['kind']=='neural' and key=='J':maximum_j=max(maximum_j,float(np.max(np.abs(av[key]-bv[key]))))
            else:np.testing.assert_array_equal(av[key],bv[key],err_msg='precision record '+key);counts['record_arrays']+=1
    pairs=set()
    for group in ('lineages','locals','cases'):
        assert len(lg[group])==len(rg[group])
        for a,b in zip(lg[group],rg[group]):
            assert {k:v for k,v in a.items() if k!='read'}=={k:v for k,v in b.items() if k!='read'}
            pairs.add((a['read'],b['read']));counts['logical_read_uses']+=1
    covered=[set(),set()]
    for li,ri in sorted(pairs):
        ln,rn=lg['reads'][li],rg['reads'][ri]
        assert all(ln[k]==rn[k] for k in ('kind','generation','birth'))
        covered[0].add(li);covered[1].add(ri)
        av,bv=m.get_read(left,lg,li),m.get_read(right,rg,ri);assert av.keys()==bv.keys()
        for key in av:
            a,b=av[key],bv[key];assert a.shape==b.shape and a.dtype==b.dtype
            if ln['kind']!='neural':
                np.testing.assert_array_equal(a,b,err_msg='native precision invariance '+key);counts['native_reader_arrays']+=1
            elif a.dtype.kind in 'biu' or key.endswith('_feedback'):
                np.testing.assert_array_equal(a,b,err_msg='discrete precision convergence '+key);counts['discrete_reader_arrays']+=1
            else:
                assert np.isfinite(a).all() and np.isfinite(b).all()
                maximum_float=max(maximum_float,float(np.max(np.abs(a-b))))
    assert covered[0]==set(range(len(lg['reads']))) and covered[1]==set(range(len(rg['reads'])))
    return dict(passed=True,**counts,unique_read_pairs=len(pairs),maximum_coupling_difference=maximum_j,
        maximum_reader_float_difference=maximum_float,actual_packets_identical=True,completions_identical=True,
        all_logical_ancestry_matched=True,all_discrete_reader_arrays_identical=True,all_native_arrays_identical=True,
        candidate_solver_executions=int(left['compiler_fit_executed'].sum()),refined_solver_executions=int(right['compiler_fit_executed'].sum()),
        candidate_executed_iterations=int(np.sum(left['compiler_fit_executed']*left['compiler_iterations'])),
        refined_executed_iterations=int(np.sum(right['compiler_fit_executed']*right['compiler_iterations'])))


def intact_anchor(current,graph,archived,oldgraph):
    assert graph==oldgraph,'intact logical graph changed';checks=0
    for key,value in archived.items():
        if key.startswith('compiler_'):continue
        np.testing.assert_array_equal(current[key],value,err_msg='H097 intact anchor '+key);checks+=1
    return dict(passed=True,exact_arrays=checks,graph_equal=True,all_intact_physics_unchanged=True)
