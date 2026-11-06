"""Analytic normalization, exact archived resumption, independent updates."""
import copy
import itertools
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus, dump, rng, sha, utc
from E111_halfway_component_cross.model import initial as original_initial
from E113_component_threshold_diagnosis.tests import responses, conditional
from E105_cycle_input_control.inference import decision
from E113_component_threshold_diagnosis.measure import movement
from E114_matched_component_amplitude import data, model, audit, normalization, normalization_audit, experiment
from E114_matched_component_amplitude.plan import HERE, ROOT, BLOCKS, TECHNICAL, CONDITIONS, COMPONENTS, METRICS, PAIRS, PRIMARY, settings
from E114_matched_component_amplitude.run import code_paths, inventory


def reject(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Invalid input accepted')


def synthetic_sources():
    n=2;mask=np.zeros((2*n,16,16),bool);mask[:,8,8]=True;sources={}
    changes_m=np.array([.75,.02,.25,.04]);changes_d=np.array([.05,.1,.2,.2])
    for h,o in enumerate('ON'):
        m=np.broadcast_to((.1+h*changes_m)[:,None,None],(2*n,16,16))
        d=np.broadcast_to((.15+h*changes_d)[:,None,None],(2*n,16,16))
        state=np.stack((m+d,m-d),axis=1).copy();state*=~mask[:,None]
        state[...,model.P[0]]=model.base.CUES.reshape(1,2,1)
        sources[o]=dict(switch_state=state,used_masks=mask.copy())
    return sources


def assembly():
    sources=synthetic_sources();norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources))
    matched=normalization.verify_sizes(sources,norm)
    assert norm['scales'][0,0]<1 and norm['scales'][0,1]==1
    assert norm['scales'][1,0]==1 and norm['scales'][1,1]<1
    assert matched['actual_sizes'][0,0,0]!=matched['actual_sizes'][0,1,0]
    np.testing.assert_allclose(matched['actual_sizes'].mean(2),np.repeat(norm['target'][:,None],2,axis=1),rtol=0,atol=4e-15)
    for c in COMPONENTS:
        assert normalization.initial(sources,norm,c).tobytes()==normalization_audit.initial(sources,norm,c).tobytes()
    reversed_sources={'O':sources['N'],'N':sources['O']};rev=normalization.calculate(reversed_sources)
    assert norm['scales'].tobytes()==rev['scales'].tobytes()
    for c in COMPONENTS:
        other=''.join('N' if a=='O' else 'O' for a in c)
        np.testing.assert_array_equal(normalization.initial(sources,norm,c),normalization.initial(reversed_sources,rev,other))
    full=copy.deepcopy(norm);full['scales'][:]=1
    for c in COMPONENTS:assert normalization.initial(sources,full,c).tobytes()==original_initial(sources,c).tobytes()
    for zero_component in ('both','m','d'):
        z=synthetic_sources()
        if zero_component=='both':z['N']['switch_state']=z['O']['switch_state'].copy()
        else:z['N']['switch_state']=original_initial(z,'ON' if zero_component=='m' else 'NO')
        nz=normalization.calculate(z);data.equal(nz,normalization_audit.calculate(z))
        # Exact dyadic fixture removes representational leakage from m/d reconstruction.
        if zero_component!='both':
            z=synthetic_sources();value=z['O']['switch_state'];value[:]=0;value[...,model.P[0]]=model.base.CUES.reshape(1,2,1)
            z['N']['switch_state']=value.copy()
            free=(~z['N']['used_masks'])&~model.P[0]
            z['N']['switch_state'][:,0][free]=.25
            z['N']['switch_state'][:,1][free]=-.25 if zero_component=='m' else .25
            nz=normalization.calculate(z);data.equal(nz,normalization_audit.calculate(z))
        assert not nz['target'].any();normalization.verify_sizes(z,nz)
        for c in COMPONENTS:assert normalization.initial(z,nz,c).tobytes()==normalization.initial(z,nz,'OO').tobytes()
    for problem in ('bound','dead','cue','nan'):
        z=copy.deepcopy(sources)
        if problem=='bound':z['N']['switch_state'][0,0,0,0]=2.1
        elif problem=='dead':z['N']['switch_state'][0,0,8,8]=.1
        elif problem=='cue':z['N']['switch_state'][...,model.P[0]]=0
        else:z['N']['switch_state'][0,0,0,0]=np.nan
        reject(lambda:normalization.calculate(z))
    bad=copy.deepcopy(norm);bad['scales'][0,0]=1.1;reject(lambda:normalization.initial(sources,bad,'NO'))
    bad=copy.deepcopy(norm);bad['target'][0]+=.01;reject(lambda:normalization.verify_sizes(sources,bad))
    signed=synthetic_sources()
    for source in signed.values():source['switch_state'][:,:,8,8]=-0.
    nz=normalization.calculate(signed);nz['scales'][:]=0;nz['target'][:]=0
    normalization.verify_sizes(signed,nz)
    for c in COMPONENTS:
        assert normalization.initial(signed,nz,c).tobytes()==normalization_audit.initial(signed,nz,c).tobytes()
        assert normalization.initial(signed,nz,c).tobytes()==normalization.initial(signed,nz,'OO').tobytes()
    return dict(scalar_normalization_and_states_exact=True,common_pair_scale=True,variant_norms_not_forced_equal=True,
        both_attenuation_directions=True,stream_label_symmetry=True,unit_scale_archived_states_exact=True,
        zero_targets_exact=True,invalid_states_and_amplification_rejected=True,corrupted_target_rejected=True,
        signed_zero_midpoint_exact=True)


def archive(task,draw):
    inter=data.arrays('benchmark',f'interventions_{task:06d}.npz')
    sources={o:data.arrays('benchmark',f'phase_assay_{task:06d}_r{draw}_{c}.npz') for o,c in (('O','ON'),('N','NO'))}
    return inter,sources


def resumption():
    task=TECHNICAL[0];draw=0;inter,sources=archive(task,draw);cfg=settings('benchmark')
    norm=normalization.calculate(sources);norm['scales'][:]=1;checks=0;hashes=0
    for c in CONDITIONS:
        result=model.read_batch(inter,sources,norm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(inter,sources,norm,task,draw,cfg,c))
        experiment.validate_assay(result,inter,sources,norm,cfg,c)
        if c in ('OON','NNO'):
            old=sources['O' if c=='OON' else 'N'];expected_hashes=old['state_hashes'][cfg['switch_step']:]
        else:
            old=data.arrays('benchmark',f'component_assay_{task:06d}_r{draw}_{c}.npz');expected_hashes=old['state_hashes']
        for k in ('end','late_ports','mean_ports','effective','denominator','coupling'):
            assert result[k].tobytes()==old[k].tobytes(),(c,k)
        assert result['state_hashes'].tobytes()==expected_hashes.tobytes()
        checks+=len(result['indices']);hashes+=len(result['state_hashes'])
    return dict(all_eight_full_scale_continuations_exact=True,variant_continuations=checks,state_hashes=hashes,
        independent_updates_exact=True,original_noise_ownership_and_offsets=True)


def matched_and_empty():
    task=TECHNICAL[0];draw=1;inter,sources=archive(task,draw);cfg=settings('benchmark')
    cfg['reader']['read_steps']=cfg['switch_step']+8;cfg['config']['observe_steps']=4
    norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources));normalization.verify_sizes(sources,norm)
    checked=0
    for c in CONDITIONS:
        result=model.read_batch(inter,sources,norm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(inter,sources,norm,task,draw,cfg,c));experiment.validate_assay(result,inter,sources,norm,cfg,c)
        data.equal(model.score(result['mean_ports'],result['indices'],.25),audit.score(result['mean_ports'],result['indices'],.25))
        checked+=len(result['indices'])
        bad=copy.deepcopy(result);bad['absolute_steps']+=1;reject(lambda:experiment.validate_assay(bad,inter,sources,norm,cfg,c))
        bad=copy.deepcopy(result);bad['initial_state'][0,0,0,0]+=.01;reject(lambda:experiment.validate_assay(bad,inter,sources,norm,cfg,c))
        bad=copy.deepcopy(result);bad['noise_hashes'][0,0]^=1;reject(lambda:experiment.validate_assay(bad,inter,sources,norm,cfg,c))
    # A genuinely empty witness batch runs no state updates.
    empty=copy.deepcopy(inter);empty['eligible'][:]=False;empty['witness'][:]=False;empty['common_magnitude'][:]=0
    for v in (1,2,3):empty['packets'][4*v:4*v+4]=empty['packets'][:4]
    model.structural(empty);audit.budget_checks(empty)
    for source in sources.values():
        for k in ('indices','used_masks','used_birth','effective','denominator','coupling','switch_state','end','mean_ports','boundary_counts','noise_hashes','state_hashes','source_noise_hashes'):
            source[k]=source[k][:0]
        source['late_ports']=source['late_ports'][:,:0]
    norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources));normalization.verify_sizes(sources,norm)
    for c in CONDITIONS:
        result=model.read_batch(empty,sources,norm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(empty,sources,norm,task,draw,cfg,c));experiment.validate_assay(result,empty,sources,norm,cfg,c)
        assert result['state_hashes'].shape==(0,32) and result['late_ports'].shape==(4,0,2,2)
    return dict(matched_eight_step_variant_continuations=checked,independent_steps_and_scores=True,
        bad_offset_initial_noise_rejected=True,empty_batch_no_updates=True)


def effects():
    patterns=rng('E114','analytic_factorial').integers(0,2,(64,8,2));checked=0
    for bits in patterns:
        def row_for(values):
            row=dict(measured=True,full_size_excess=0.)
            for h,c in enumerate(CONDITIONS):
                for metric in METRICS:
                    row[c+'_C_'+metric]=float(values[h,0]);row[c+'_F_'+metric]=float(values[h,1]);row[c+'_delta_'+metric]=float(values[h,0]-values[h,1])
            pairs=[]
            for comp,other,later,before,after in PAIRS:
                p=dict(component=comp)
                for metric in METRICS:
                    a=row[after+'_C_'+metric]-row[before+'_C_'+metric];b=row[after+'_F_'+metric]-row[before+'_F_'+metric]
                    p.update({metric+'_'+k:v for k,v in movement(a,b).items()})
                pairs.append(p)
            experiment.add_effects(row,pairs);return row
        base=row_for(bits);delta=bits[:,0]-bits[:,1];cube=delta.reshape(2,2,2)
        truth=float(np.abs(cube[1]-cube[0]).mean()-np.abs(cube[:,1]-cube[:,0]).mean());assert base[PRIMARY]==truth
        for flip in itertools.product((0,1),repeat=3):
            values=bits.reshape(2,2,2,2)
            for axis,active in enumerate(flip):
                if active:values=np.flip(values,axis=axis)
            assert row_for(values.reshape(8,2))[PRIMARY]==truth;checked+=1
    row=dict(measured=False,full_size_excess=0.);experiment.add_effects(row,[])
    assert row[PRIMARY]==0 and row['m_both_C_abs'] is None and row['m_both_contrast_abs']==0
    assert decision(dict(ci95=[0.,1.]))=='UNRESOLVED' and decision(dict(ci95=[-.1,0.]))=='UNRESOLVED'
    return dict(analytical_primary_patterns=64,axis_label_reversals=checked,empty_rows_zero_contrast_null_absolutes=True,strict_primary_decision=True)


def main():
    cap_cpus(1);folder=HERE/'analysis';folder.mkdir(exist_ok=True);attempt=1
    while (folder/f'tests_attempt_{attempt:03d}.json').exists():attempt+=1
    tick=time.monotonic();checks={};paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        resources=inventory(1);data.registry(all_files=True);assert set(BLOCKS).isdisjoint(TECHNICAL)
        for fn in (assembly,responses,conditional,resumption,matched_and_empty,effects):
            checks[fn.__name__]=dict(status='PASS',evidence=fn());print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=checks,
            inputs_sha256=paths,registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{attempt:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc()));raise
    dump(folder/f'tests_attempt_{attempt:03d}.json',result);print(json.dumps(dict(status='PASS',seconds=result['seconds'])))


if __name__=='__main__':main()
