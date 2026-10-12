"""D118: source-accounted diagnostics of saved D117 states, no dynamics."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

from laws_confirmation import l20_three_rewrite_run as prior
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT, environment_manifest, git_head, utc_now

WS=prior.p.WS
RUN_ID='l20_reference_projection_audit_v1_attempt1'
SCIENCE=('scripts/audit_l20_reference_projection.py','tests/test_l20_reference_projection.py',
         'protocols/L20_REFERENCE_PROJECTION_AUDIT_V1.md')
KINDS=('rewrite','live','copy','write_off','read_off','wrong','lesion','rescue')
CASES=tuple((r,k) for r in (0,1) for k in KINDS)
BUDGET=16*1024**2


def field(x):
    x=np.asarray(x)
    if x.shape!=(16,16) or x.dtype!=np.float64 or not np.isfinite(x).all():
        raise ValueError('finite float64 16x16 field required')
    return x


def center(x): return x-x.mean()


def projection(x):
    x=field(x); c=center(x); scale=.3/max(float(c.std()),1e-9)
    return c*scale,scale


def score(x,targets,role):
    field(x)
    if targets.shape!=(2,16,16) or not np.isin(targets,[-1.,1.]).all() or role not in (0,1):
        raise ValueError('binary target pair and role required')
    own=float(((x>0)==(targets[role]>0)).mean())
    other=float(((x>0)==(targets[1-role]>0)).mean())
    margin=float((x*(targets[role]-targets[1-role])/2).mean())
    return own,own-other,margin


def transition(birth,read,write_birth,first,last,targets,role,kind):
    for state in (birth,read,write_birth,first,last):
        if state.shape!=(4,16,16) or state.dtype!=np.float64 or not np.isfinite(state).all():
            raise ValueError('complete finite states required')
    if kind not in KINDS: raise ValueError('declared condition required')
    np.testing.assert_array_equal(read[:3],write_birth[:3])
    erased=kind not in ('live','copy'); writing=kind not in ('copy','write_off')
    if erased: np.testing.assert_array_equal(write_birth[3],np.zeros((16,16)))
    else: np.testing.assert_array_equal(write_birth[3],read[3])
    old_R,new_V=write_birth[2],first[0]
    expected_R=old_R+.002*(new_V-old_R)
    reference_error=float(abs(first[2]-expected_R).max())
    np.testing.assert_allclose(first[2],expected_R,atol=1e-14,rtol=0)
    candidate=.999*write_birth[3]+.001*np.tanh(first[2])
    expected_theta,scale=projection(candidate) if writing else (write_birth[3],None)
    theta_error=float(abs(first[3]-expected_theta).max())
    np.testing.assert_allclose(first[3],expected_theta,atol=1e-14,rtol=0)
    floor=bool(center(candidate).std()<1e-9) if writing else None
    cancellation_error=None
    if erased and writing and not floor:
        unscaled,_=projection(np.tanh(first[2]))
        cancellation_error=float(abs(first[3]-unscaled).max())
        assert cancellation_error<=1e-14
    rank_preserved=None
    if writing:
        rank_preserved=bool(np.array_equal(np.argsort(candidate.ravel(),kind='stable'),np.argsort(first[3].ravel(),kind='stable')))
        assert rank_preserved
        np.testing.assert_array_equal(first[3]>0,center(candidate)>0)
    initial_part=(1-.002)**300*birth[2]
    history_part=read[2]-initial_part
    initial_margin=score(initial_part,targets,role)[2]
    history_margin=score(history_part,targets,role)[2]
    assert abs(initial_margin+history_margin-score(read[2],targets,role)[2])<1e-14
    old_R_projected,_=projection(np.tanh(old_R))
    persistence=.998*old_R; injection=.002*new_V
    ratio=float(injection.std()/persistence.std()) if persistence.std()>0 else None
    result=dict(erased=erased,writing=writing,reference_error=reference_error,theta_error=theta_error,
        projection_scale=scale,projection_floor_active=floor,lambda_cancellation_error=cancellation_error,
        rank_preserved=rank_preserved,birth_reference_coefficient=(1-.002)**300,
        retained_birth_std=float(initial_part.std()),read_body_history_std=float(history_part.std()),
        retained_birth_target_margin=initial_margin,read_body_history_target_margin=history_margin,
        first_old_R_term_std=float(persistence.std()),first_new_V_term_std=float(injection.std()),
        new_V_to_old_R_std_ratio=ratio,first_from_projected_prewrite_R_mae=float(abs(first[3]-old_R_projected).mean()),
        raw_candidate_std=float(center(candidate).std()) if writing else None,
        theta_change_after_first_mae=float(abs(last[3]-first[3]).mean()),
        theta_end_from_input_mae=float(abs(last[3]-birth[3]).mean()))
    for name,x in (('read_V',read[0]),('read_R',read[2]),('first_R',first[2]),
                   ('theta_first',first[3]),('theta_end',last[3])):
        own,pref,margin=score(x,targets,role)
        result.update({name+'_std':float(x.std()),name+'_own_sign':own,
            name+'_sign_preference':pref,name+'_target_margin':margin})
    return result


def passive_ema_check():
    """Record the restricted source graph, not a simulated EMA ablation."""
    files=(prior.p.ORIGIN/'ladder_web/src/ladder_web/engine.py',
           prior.p.ORIGIN/'blueprint_web/src/blueprint_web/engine.py',
           prior.p.ORIGIN/'writable_landlord/src/writable_landlord/pipeline.py')
    names=('ladder_step','blueprint_step','cascade_step'); result=[]
    for path,name in zip(files,names):
        function=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
        loads=[n for n in ast.walk(function) if isinstance(n,ast.Name) and n.id=='ema' and isinstance(n.ctx,ast.Load)]
        returns=[n.lineno for n in ast.walk(function) if isinstance(n,ast.Return)]
        assignments=[n for n in function.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='ema' for x in ast.walk(n.targets[0]))]
        assert len(loads)==2 and len(returns)==1 and len(assignments)==1
        assert sorted(n.lineno for n in loads)==sorted([assignments[0].lineno,returns[0]])
        result.append(dict(path=str(path),function=name,ema_load_lines=[n.lineno for n in loads]))
    return dict(passive_for_active_path=True,active_ladder_rung='A',source_rows=result,
                ablation_rollouts=0,scope='V/R/theta independent of auxiliary ema in the active source path')


def numeric_summary(rows):
    result={}
    for key in rows[0]:
        if key in ('index','life','role','generation','kind'): continue
        values=[r[key] for r in rows if type(r[key]) in (int,float)]
        if values:
            result[key]=dict(n=len(values),mean=float(np.mean(values)),minimum=float(min(values)),maximum=float(max(values)),
                block_means=[float(np.mean([r[key] for r in rows if r['index']==i and type(r[key]) in (int,float)])) for i in range(60000,60008)])
    return result


def analyze(root):
    directory=root/'outputs'/prior.p.RUN_ID; rows=[]
    for index in range(60000,60008):
        raw=prior.u.load_npz(directory/f'block_{index}.npz')
        meta=prior.u.read_json(directory/f'block_{index}.json')
        assert meta['index']==index and len(meta['lives'])==4
        for life,m in enumerate(meta['lives']):
            assert m['cases']==[list(c) for c in CASES] and m['times']==[0,1,100,101,300,301,600,1300]
            assert m['config']['read_steps']==300 and m['blueprint']['rho']==.002 and m['blueprint']['c_m']==.2
            for ci,(role,kind) in enumerate(CASES):
                for g in range(3):
                    s=raw['generation_states'][life,ci,g]
                    diagnostics=transition(s[0],s[4],raw['write_birth'][life,ci,g],s[5],s[-1],raw['targets'][life],role,kind)
                    rows.append(dict(index=index,life=life,role=role,kind=kind,generation=g+1,**diagnostics))
    assert len(rows)==1536 and len({(x['index'],x['life'],x['role'],x['kind'],x['generation']) for x in rows})==1536
    groups=[dict(role=role,kind=kind,generation=g,statistics=numeric_summary([r for r in rows if (r['role'],r['kind'],r['generation'])==(role,kind,g)]))
            for role,kind in CASES for g in (1,2,3)]
    firsts=[r for r in rows if r['kind']=='rewrite']
    summary=dict(schema='l20_reference_projection_audit_v1',decision='D118',post_hoc=True,new_trajectories=0,
        causal_ablation=False,independent_confirmation=False,new_qualification_gate=None,source_run=prior.p.RUN_ID,
        checked_transitions=len(rows),primary_transitions=len(firsts),groups=groups,
        primary=numeric_summary(firsts),read_off=numeric_summary([r for r in rows if r['kind']=='read_off']),
        enabled_projection_rows=sum(r['writing'] for r in rows),floor_active_rows=sum(r['projection_floor_active'] is True for r in rows),
        maxima={k:max(r[k] for r in rows if r[k] is not None) for k in ('reference_error','theta_error','lambda_cancellation_error')},
        ema=passive_ema_check(),intervals=None,unit='eight paired blocks; rows/stages are descriptive repeated observations',
        inferred_history='endpoint-derived weighted contribution, not an independently observed full V history',
        std_ratio_interpretation='magnitude ratio of correlated terms, not a causal/variance fraction')
    return rows,summary


def test_report(path,root):
    path=prior.u.require_beneath(path,root/'logs')
    assert path.name.startswith('d118_') and path.suffix=='.xml' and not path.is_symlink()
    tree=ET.parse(path).getroot(); cases=tree.findall('.//testcase')
    assert len(cases)>=20 and not any(tree.findall('.//'+x) for x in ('failure','error','skipped'))
    names={c.get('name','').split('[',1)[0] for c in cases}
    assert {'test_projection_matches_source','test_scale_invariance','test_floor_not_invariant','test_nonzero_theta_rate_matters',
        'test_passive_ema_source_graph','test_transition_corruption','test_reference_accounting','test_body_not_causal_fraction',
        'test_projection_permutation','test_no_production_dynamics'}<=names
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    return dict(path=str(path),tests=len(cases),failures=0,skipped=0)


def input_paths(root,report):
    m=prior.prepared(root); run=root/'runs'/prior.p.RUN_ID; out=root/'outputs'/prior.p.RUN_ID
    complete=prior.u.read_json(run/'COMPLETE.json')
    paths=[Path(x) for x in m['input_sha256']]+[Path(x) for x in complete['output_sha256']]
    paths+=[run/n for n in ('MANIFEST.json','COMPLETE.json','STATUS.json')]+[out/'output_hashes.sha256']
    paths+=[WS/n for n in SCIENCE]+[WS/'reviews/L20_THREE_BOUNDARY_REWRITE_2026-09-13.md',report]
    return sorted(set(paths))


def execute(root,report):
    prior.preflight(root); proof=test_report(report,root); path=root/'outputs'/RUN_ID
    if path.exists(): raise FileExistsError('write-once audit identity already exists')
    start=time.monotonic(); checked=prior.audit(root)
    inputs=prior.u.hashes(input_paths(root,report)); path.mkdir()
    try:
        prior.u.write_json(path/'INPUTS.json',dict(started_utc=utc_now(),input_sha256=inputs,test_proof=proof,
            source_audit=checked,environment=environment_manifest(),git_head=git_head(WS),known_outcomes=True,
            new_trajectories=0,post_hoc=True,workers=1,cpu_affinity=prior.preflight(root),output_budget=BUDGET),root)
        rows,summary=analyze(root)
        prior.u.write_json(path/'transitions.json',rows,root); prior.u.write_json(path/'summary.json',summary,root)
        assert prior.u.read_json(path/'transitions.json')==rows and prior.u.read_json(path/'summary.json')==summary
        assert inputs==prior.u.hashes(input_paths(root,report)); prior.preflight(root,False)
        outputs=prior.u.hashes(list(path.iterdir())); size=sum(x.stat().st_size for x in path.iterdir()); assert size<BUDGET
        prior.u.write_json(path/'COMPLETE.json',dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-start,
            output_sha256=outputs,output_bytes_without_sentinel=size,new_trajectories=0,automatic_successor=False),root)
        print(json.dumps(dict(status='COMPLETE',input_hashes=len(inputs),output_bytes_without_sentinel=size,
            elapsed_seconds=time.monotonic()-start,checked_transitions=len(rows),primary=summary['primary'],maxima=summary['maxima']),indent=2))
    except Exception as error:
        prior.u.failure(path,error,root); raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root',type=Path,default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument('--test-report',type=Path,required=True)
    args=parser.parse_args(); execute(args.external_root,args.test_report)
