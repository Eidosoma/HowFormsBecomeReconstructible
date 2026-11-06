"""Independent anchored construction, archive reuse, sparse replay and inference checks."""
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
from E114_matched_component_amplitude.tests import synthetic_sources
from E105_cycle_input_control.inference import decision
from E113_component_threshold_diagnosis.measure import movement
from E115_original_anchor_components import data, model, audit, normalization, normalization_audit, experiment
from E115_original_anchor_components.plan import HERE, ROOT, BLOCKS, TECHNICAL, CONDITIONS, ORIGINAL_CONDITIONS, COMPONENTS, METRICS, PAIRS, PRIMARY, settings, full_component
from E115_original_anchor_components.run import code_paths, inventory


def reject(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError('Invalid input accepted')

def assembly():
    sources=synthetic_sources();norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources))
    checked=normalization.verify_sizes(sources,norm)
    assert norm['scales'][0,0]<1 and norm['scales'][0,1]==1
    assert norm['scales'][1,0]==1 and norm['scales'][1,1]<1
    np.testing.assert_allclose(checked['actual_sizes'].mean(2),np.repeat(norm['target'][:,None],2,axis=1),rtol=0,atol=4e-15)
    for c in COMPONENTS:assert normalization.initial(sources,norm,c).tobytes()==normalization_audit.initial(sources,norm,c).tobytes()
    revsources={'O':sources['N'],'N':sources['O']};rev=normalization.calculate(revsources)
    assert norm['scales'].tobytes()==rev['scales'].tobytes()
    for c in COMPONENTS:
        other=('N' if c[0]=='O' else 'O')+c[1]
        assert normalization.initial(sources,norm,c).tobytes()==normalization.initial(revsources,rev,other).tobytes()
    full=copy.deepcopy(norm);full['scales'][:]=1
    for c in COMPONENTS:assert normalization.initial(sources,full,c).tobytes()==original_initial(sources,full_component(c)).tobytes()
    for zero_component in ('both','m','d'):
        z=synthetic_sources();value=z['O']['switch_state'];value[:]=0;value[...,model.P[0]]=model.base.CUES.reshape(1,2,1)
        z['N']['switch_state']=value.copy()
        if zero_component!='both':
            free=(~z['N']['used_masks'])&~model.P[0]
            z['N']['switch_state'][:,0][free]=.25
            z['N']['switch_state'][:,1][free]=-.25 if zero_component=='m' else .25
        nz=normalization.calculate(z);data.equal(nz,normalization_audit.calculate(z));assert not nz['target'].any()
        normalization.verify_sizes(z,nz)
        for c in COMPONENTS:
            assert normalization.initial(z,nz,c).tobytes()==z[c[0]]['switch_state'].tobytes()
            assert normalization.initial(z,nz,c).tobytes()==normalization_audit.initial(z,nz,c).tobytes()
            for later in 'ON':assert (experiment.reuse_codes(nz,c+later)==ORIGINAL_CONDITIONS.index(c[0]*2+later)).all()
    signed=synthetic_sources()
    for source in signed.values():source['switch_state'][:,:,8,8]=-0.
    nz=normalization.calculate(signed);nz['scales'][:]=0;nz['target'][:]=0;normalization.verify_sizes(signed,nz)
    for c in COMPONENTS:
        assert normalization.initial(signed,nz,c).tobytes()==signed[c[0]]['switch_state'].tobytes()
        assert normalization.initial(signed,nz,c).tobytes()==normalization_audit.initial(signed,nz,c).tobytes()
    for problem in ('bound','dead','cue','nan'):
        z=copy.deepcopy(sources)
        if problem=='bound':z['N']['switch_state'][0,0,0,0]=2.1
        elif problem=='dead':z['N']['switch_state'][0,0,8,8]=.1
        elif problem=='cue':z['N']['switch_state'][...,model.P[0]]=0
        else:z['N']['switch_state'][0,0,0,0]=np.nan
        reject(lambda:normalization.calculate(z))
    bad=copy.deepcopy(norm);bad['scales'][0,0]=1.1;reject(lambda:normalization.initial(sources,bad,'OM'))
    bad=copy.deepcopy(norm);bad['target'][0]+=.01;reject(lambda:normalization.verify_sizes(sources,bad))
    return dict(both_attenuation_directions=True,original_anchors_and_unit_scale_targets_exact=True,
        scalar_states_exact=True,stream_label_symmetry=True,pair_mean_norm_matched=True,component_isolation=True,
        zero_targets_and_signed_zeros_exact=True,invalid_states_and_amplification_rejected=True)


def archive(task,draw):
    inter=data.arrays('benchmark',f'interventions_{task:06d}.npz')
    sources={o:data.arrays('benchmark',f'phase_assay_{task:06d}_r{draw}_{c}.npz') for o,c in (('O','ON'),('N','NO'))}
    return inter,sources


def resumption():
    task=TECHNICAL[0];draw=0;inter,sources=archive(task,draw);cfg=settings('benchmark')
    norm=normalization.calculate(sources);norm['scales'][:]=1
    archived=data.arrays('benchmark',f'component_scores_{task:06d}_r{draw}.npz')
    old=experiment.originals('benchmark',task,draw,inter,sources,cfg,archived);seen=set();checks=0
    for c in CONDITIONS:
        target=full_component(c[:2])+c[2]
        assembled,codes,rep=experiment.continuation(inter,sources,norm,old,task,draw,cfg,c)
        data.equal(assembled,old[target]);assert rep['evaluated_variant_draws']==0
        assert (codes==ORIGINAL_CONDITIONS.index(target)).all()
        if target in seen:continue
        seen.add(target);result=model.read_batch(inter,sources,norm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(inter,sources,norm,task,draw,cfg,c))
        experiment.validate_assay(result,inter,sources,norm,cfg,c)
        for k in assembled:assert result[k].tobytes()==assembled[k].tobytes()
        trace=(sources['O' if target=='OON' else 'N']['state_hashes'][cfg['switch_step']:]
            if target in ('OON','NNO') else data.arrays('benchmark',f'component_assay_{task:06d}_r{draw}_{target}.npz')['state_hashes'])
        assert result['state_hashes'].tobytes()==trace.tobytes();checks+=len(result['indices'])
    assert seen==set(ORIGINAL_CONDITIONS)
    bad=copy.deepcopy(old);bad['OOO']['initial_state'][0,0,0,0]+=.001
    reject(lambda:experiment.continuation(inter,sources,norm,bad,task,draw,cfg,'OBO'))
    bad=copy.deepcopy(archived);bad['mean_ports'][0,0,0,0,0]+=.001
    reject(lambda:experiment.originals('benchmark',task,draw,inter,sources,cfg,bad))
    return dict(all_eight_original_conditions_replayed_exactly=True,all_twelve_unit_scale_reuse_mappings=True,
        variant_continuations=checks,archive_state_and_port_corruption_rejected=True)


def partial_and_empty():
    task=TECHNICAL[0];draw=1;inter,sources=archive(task,draw);cfg=settings('benchmark')
    cfg['reader']['read_steps']=cfg['switch_step']+8;cfg['config']['observe_steps']=4
    norm=normalization.calculate(sources);n=len(norm['target']);normalization.verify_sizes(sources,norm)
    positions=np.array([0,n-1]);subinter,subs,take=experiment.subset(inter,sources,positions)
    assert 'state_hashes' not in subs['O'] and subs['O']['source_noise_hashes'].shape==sources['O']['source_noise_hashes'].shape
    assert int(inter['eligible'].sum())==n and int(subinter['eligible'].sum())==2
    subnorm=normalization.calculate(subs);data.equal(subnorm,normalization_audit.calculate(subs))
    checks=0
    for c in ('OMO','OMN','NMO','NMN'):
        result=model.read_batch(inter,sources,norm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(inter,sources,norm,task,draw,cfg,c));experiment.validate_assay(result,inter,sources,norm,cfg,c)
        small=model.read_batch(subinter,subs,subnorm,task,draw,cfg,c)
        data.equal(small,audit.read_batch(subinter,subs,subnorm,task,draw,cfg,c));experiment.validate_assay(small,subinter,subs,subnorm,cfg,c)
        for k in ('initial_state','end','mean_ports'):assert small[k].tobytes()==result[k][take].tobytes()
        assert small['late_ports'].tobytes()==result['late_ports'][:,take].tobytes()
        data.equal(model.score(result['mean_ports'],result['indices'],.25),audit.score(result['mean_ports'],result['indices'],.25));checks+=len(result['indices'])
        for field in ('absolute_steps','initial_state','noise_hashes'):
            bad=copy.deepcopy(result)
            if field=='initial_state':bad[field][0,0,0,0]+=.01
            else:bad[field].flat[0]+=1
            reject(lambda:experiment.validate_assay(bad,inter,sources,norm,cfg,c))
    empty,empty_sources,_=experiment.subset(inter,sources,[]);zero=normalization.calculate(empty_sources)
    data.equal(zero,normalization_audit.calculate(empty_sources));normalization.verify_sizes(empty_sources,zero)
    for c in CONDITIONS:
        result=model.read_batch(empty,empty_sources,zero,task,draw,cfg,c)
        data.equal(result,audit.read_batch(empty,empty_sources,zero,task,draw,cfg,c));experiment.validate_assay(result,empty,empty_sources,zero,cfg,c)
        assert result['state_hashes'].shape==(0,32) and result['late_ports'].shape==(4,0,2,2)
    # Mixed 0/1/partial codes must be deterministic and outcome-independent.
    mixed=copy.deepcopy(norm);mixed['scales'][:3,0]=[0,1,.5]
    for a in 'ON':
        codes=experiment.reuse_codes(mixed,a+'MO')
        assert list(codes[:3])==[ORIGINAL_CONDITIONS.index(a+a+'O'),ORIGINAL_CONDITIONS.index(full_component(a+'M')+'O'),-1]
    return dict(partial_eight_step_variant_continuations=checks,independent_replay=True,
        sparse_subset_endpoints_exact=True,no_false_full_batch_hashes=True,mixed_reuse_codes=True,
        empty_batch_no_updates=True,offset_initial_noise_corruption_rejected=True)


def effects():
    patterns=rng('E115','analytic_anchor').integers(0,2,(64,12,2));checked=0
    def row_for(values):
        row=dict(measured=True,full_size_excess=0.,midpoint_excess=0.)
        for h,c in enumerate(CONDITIONS):
            for metric in METRICS:
                row[c+'_C_'+metric]=float(values[h,0]);row[c+'_F_'+metric]=float(values[h,1]);row[c+'_delta_'+metric]=float(values[h,0]-values[h,1])
        pairs=[]
        for comp,anchor,later,before,after in PAIRS:
            p=dict(component=comp,fixed_other=anchor)
            for metric in METRICS:
                a=row[after+'_C_'+metric]-row[before+'_C_'+metric];b=row[after+'_F_'+metric]-row[before+'_F_'+metric]
                p.update({metric+'_'+k:v for k,v in movement(a,b).items()})
            pairs.append(p)
        experiment.add_effects(row,pairs);return row
    for bits in patterns:
        cube=(bits[:,0]-bits[:,1]).reshape(2,3,2)
        truth=float(np.abs(cube[:,1]-cube[:,0]).mean()-np.abs(cube[:,2]-cube[:,0]).mean())
        assert row_for(bits)[PRIMARY]==truth
        for flip in itertools.product((0,1),repeat=3):
            values=bits.reshape(2,3,2,2)
            for axis,active in zip((0,2,3),flip):
                if active:values=np.flip(values,axis=axis)
            assert row_for(values.reshape(12,2))[PRIMARY]==truth;checked+=1
    for original in rng('E115','full_scale_effect').integers(0,2,(64,8,2)):
        values=np.array([original[ORIGINAL_CONDITIONS.index(full_component(c[:2])+c[2])] for c in CONDITIONS])
        delta=(original[:,0]-original[:,1]).reshape(2,2,2)
        assert row_for(values)[PRIMARY]==float(abs(delta[1]-delta[0]).mean()-abs(delta[:,1]-delta[:,0]).mean())
    row=dict(measured=False,full_size_excess=0.,midpoint_excess=0.);experiment.add_effects(row,[])
    assert row[PRIMARY]==row['anchor_minus_midpoint']==0 and row['m_both_C_abs'] is None
    assert decision(dict(ci95=[0.,1.]))=='UNRESOLVED' and decision(dict(ci95=[-.1,0.]))=='UNRESOLVED'
    return dict(analytical_primary_patterns=64,label_reversals=checked,full_scale_original_effect_recovered=True,
        empty_rows_null_absolute_zero_contrast=True,strict_primary_decision=True)


def main():
    cap_cpus(1);folder=HERE/'analysis';folder.mkdir(exist_ok=True);attempt=1
    while (folder/f'tests_attempt_{attempt:03d}.json').exists():attempt+=1
    tick=time.monotonic();checks={};paths={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    try:
        resources=inventory(1);data.registry(all_files=True);assert set(BLOCKS).isdisjoint(TECHNICAL)
        for fn in (assembly,responses,conditional,resumption,partial_and_empty,effects):
            checks[fn.__name__]=dict(status='PASS',evidence=fn());print(fn.__name__+': PASS',flush=True)
        assert paths=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
        result=dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,checks=checks,
            inputs_sha256=paths,registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources)
    except BaseException:
        dump(folder/f'tests_attempt_{attempt:03d}.json',dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,
            checks=checks,inputs_sha256=paths,traceback=traceback.format_exc()));raise
    dump(folder/f'tests_attempt_{attempt:03d}.json',result);print(json.dumps(dict(status='PASS',seconds=result['seconds'])))


if __name__=='__main__':main()
