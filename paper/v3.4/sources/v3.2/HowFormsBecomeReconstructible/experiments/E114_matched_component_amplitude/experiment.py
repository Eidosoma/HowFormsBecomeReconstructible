"""Only matched-amplitude continuations; every step independently replayed."""
import math
import time
import numpy as np
from E110_halfway_state_diagnosis.analysis import check_assay
from E111_halfway_component_cross.experiment import validate_sources
from E113_component_threshold_diagnosis import measure as describe, audit as describe_audit
from E114_matched_component_amplitude import data, model, audit, normalization, normalization_audit
from E114_matched_component_amplitude.plan import CONDITIONS, COMPONENTS, VARIANTS, METRICS, PAIRS, OUTPUT_METRICS, PRIMARY, PRIOR_PRIMARY, NORM_KEYS, key


def validate_assay(result,inter,sources,norm,cfg,condition):
    ref=sources['O'];idx=model.read_indices(inter);n=len(idx);split=cfg['switch_step'];stop=cfg['reader']['read_steps']
    assert result['indices'].tobytes()==idx.tobytes()
    assert result['initial_state'].tobytes()==normalization_audit.initial(sources,norm,condition[:2]).tobytes()
    assert result['source_states'].tobytes()==np.stack([sources[o]['switch_state'] for o in ('O','N')]).tobytes()
    for k in ('effective','denominator','coupling','masks','used_masks'):assert result[k].tobytes()==ref[k].tobytes(),k
    model.validate_state(result['initial_state'],result['used_masks']);model.validate_state(result['end'],result['used_masks'])
    assert result['late_ports'].mean(0).tobytes()==result['mean_ports'].tobytes()
    final=np.stack([result['end'][...,model.P[p]].mean(-1) for p in (1,2)],axis=-1)
    assert final.tobytes()==result['late_ports'][-1].tobytes()
    assert result['source_noise_hashes'].tobytes()==ref['source_noise_hashes'][split:stop].tobytes()
    assert result['noise_hashes'].tobytes()==ref['source_noise_hashes'][split:stop,int(condition[2]=='N')].tobytes()
    assert result['absolute_steps'].tobytes()==(np.arange(split,stop,dtype=np.int64) if n else np.empty(0,np.int64)).tobytes()
    assert result['state_hashes'].shape==((stop-split) if n else 0,32)
    if n:assert result['state_hashes'][-1].tobytes()==model.old.digest(result['end']).tobytes()


def header(task,a,f,r,draw,inter,affected):
    eligible=bool(inter['eligible'][a,f,r]);changed=bool(affected[a,f,r])
    return dict(task=task,arm=a,founder=f,recipient=r,draw=draw,
        kind='native' if a<2 else 'mixture',history='sham' if a%2==0 else 'pulse',
        eligible=eligible,affected=changed,erased=eligible and not changed,measured=eligible)


def add_effects(row,pairs):
    for comp in ('m','d'):
        part=[p for p in pairs if p['component']==comp]
        assert len(part)==(4 if row['measured'] else 0)
        for metric in METRICS:
            for term in OUTPUT_METRICS:
                value=math.fsum(p[metric+'_'+term] for p in part)/4 if part else (
                    0. if term in ('contrast_abs','contrast_signed') else None)
                row[comp+'_'+metric+'_'+term]=value
            if part:
                # Independently reconstruct gross and signed effects from condition endpoints.
                for v,term in (('C','C_abs'),('F','F_abs'),('delta','contrast_abs')):
                    vals=[]
                    for c,o,l,before,after in PAIRS:
                        if c==comp:vals.append(row[after+'_'+v+'_'+metric]-row[before+'_'+v+'_'+metric])
                    np.testing.assert_allclose(row[comp+'_'+metric+'_'+term],sum(abs(x) for x in vals)/4,rtol=2e-12,atol=3e-14)
    row[PRIMARY]=row['m_both_contrast_abs']-row['d_both_contrast_abs']
    row['change_in_excess']=row[PRIMARY]-row['full_size_excess']


def block(mode,task,cfg,known,sizes,run=None):
    tick=time.monotonic();inter=data.arrays(mode,f'interventions_{task:06d}.npz')
    witness=data.arrays(mode,f'witnesses_{task:06d}.npz');model.structural(inter);budgets=audit.budget_checks(inter)
    assert inter['witness'].tobytes()==witness['used_witness'].tobytes() and inter['eligible'].tobytes()==witness['eligible'].tobytes()
    idx=model.read_indices(inter);contexts=np.argwhere(inter['eligible']);n=len(contexts);lookup={tuple(x):j for j,x in enumerate(contexts)}
    weights=model.base.decode(inter['packets']);rows=[];pairs=[];reader_seconds=0.;checked=0;scalar_ports=0;zero_targets=0
    original_source_scores=0;boundary=0;max_error=0.;max_leak=0.;max_initial=0.
    if run is not None:
        for name in (f'interventions_{task:06d}.npz',f'witnesses_{task:06d}.npz'):
            with (run/name).open('xb') as f:f.write(data.raw(mode,'original',name))
    for draw in (0,1):
        sources={o:data.arrays(mode,f'phase_assay_{task:06d}_r{draw}_{label}.npz') for o,label in (('O','ON'),('N','NO'))}
        phase_cfg=dict(switch_step=cfg['switch_step'],read_steps=cfg['reader']['read_steps'])
        for o,label in (('O','ON'),('N','NO')):check_assay(sources[o],inter,weights,draw,phase_cfg,label)
        validate_sources(inter,sources,task,draw,cfg)
        norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources))
        matched=normalization.verify_sizes(sources,norm);zero_targets+=int((norm['target']==0).sum())
        max_error=max(max_error,float(matched['maximum_size_error'].max(initial=0)))
        max_leak=max(max_leak,float(matched['maximum_component_leak'].max(initial=0)))
        archived=data.arrays(mode,f'component_scores_{task:06d}_r{draw}.npz')
        assert archived['indices'].tobytes()==contexts.tobytes()
        if run is not None:data.save(run/f'normalization_{task:06d}_r{draw}.npz',dict(indices=contexts,**norm,**matched))
        scored={};means={};results={}
        for c in CONDITIONS:
            t=time.monotonic();result=model.read_batch(inter,sources,norm,task,draw,cfg,c)
            data.equal(result,audit.read_batch(inter,sources,norm,task,draw,cfg,c));reader_seconds+=time.monotonic()-t
            validate_assay(result,inter,sources,norm,cfg,c);results[c]=result
            score=model.score(result['mean_ports'],idx,.25);data.equal(score,audit.score(result['mean_ports'],idx,.25))
            scored[c]={k:v.reshape((2,n)+v.shape[1:]) for k,v in score.items()};means[c]=result['mean_ports'].reshape(2,n,2,2)
            max_initial=max(max_initial,float(abs(result['initial_state']).max(initial=0)));boundary+=int(result['boundary_counts'].sum())
            if run is not None:data.save(run/f'assay_{task:06d}_r{draw}_{c}.npz',result)
        affected=(inter['witness']&model.reader.surviving_edges(inter['injury_masks'][draw])).any((-3,-2,-1))
        zero=np.tile(norm['target']==0,2)
        for later in 'ON':
            for comp in COMPONENTS:
                for field in ('initial_state','end','mean_ports'):
                    assert results[comp+later][field][zero].tobytes()==results['OO'+later][field][zero].tobytes()
        if run is not None:
            combined={k:np.stack([scored[c][k] for c in CONDITIONS]) for k in scored[CONDITIONS[0]]}
            data.save(run/f'scores_{task:06d}_r{draw}.npz',dict(indices=contexts,mean_ports=np.stack([means[c] for c in CONDITIONS]),**combined))
        for a,f,r in np.ndindex(inter['eligible'].shape):
            row=header(task,a,f,r,draw,inter,affected);ident=key(row);source=known[ident];description=sizes[ident]
            for flag in ('eligible','affected','erased'):assert row[flag]==(source[flag]=='True')
            row['full_size_excess']=float(source[PRIOR_PRIMARY]);case_pairs=[];j=lookup.get((a,f,r))
            row.update({k:None for k in NORM_KEYS})
            if row['measured']:
                for c,word in enumerate(('m','d')):
                    np.testing.assert_allclose(norm['original_sizes'][j,c],float(description[word+'_free_mean_l1']),rtol=2e-12,atol=3e-14)
                row.update(free_cells=int(norm['free_cells'][j]),original_m_size=float(norm['original_sizes'][j,0]),
                    original_d_size=float(norm['original_sizes'][j,1]),target_size=float(norm['target'][j]),
                    m_scale=float(norm['scales'][j,0]),d_scale=float(norm['scales'][j,1]),zero_target=bool(norm['target'][j]==0),
                    m_C_size=float(matched['actual_sizes'][j,0,0]),m_F_size=float(matched['actual_sizes'][j,0,1]),
                    d_C_size=float(matched['actual_sizes'][j,1,0]),d_F_size=float(matched['actual_sizes'][j,1,1]),
                    maximum_size_error=float(matched['maximum_size_error'][j]),maximum_component_leak=float(matched['maximum_component_leak'][j]))
            for h,c in enumerate(CONDITIONS):
                for v,label in enumerate(VARIANTS):
                    for metric in METRICS:row[c+'_'+label+'_'+metric]=float(scored[c][metric][v,j]) if row['measured'] else None
                    row[c+'_'+label+'_failure_class']=None
                    if not row['measured']:continue
                    rule=int(model.base.RULES[f]);sc,_=describe_audit.scalar_score(means[c][v,j],rule)
                    for metric in METRICS:np.testing.assert_allclose(row[c+'_'+label+'_'+metric],sc[metric],rtol=2e-12,atol=3e-14)
                    row[c+'_'+label+'_failure_class']=sc['failure_class'];scalar_ports+=1
                    prior,_=describe_audit.scalar_score(archived['mean_ports'][h,v,j],rule)
                    for metric in METRICS:
                        assert float(archived[metric][h,v,j])==float(source[c+'_'+label+'_'+metric])
                        np.testing.assert_allclose(prior[metric],float(source[c+'_'+label+'_'+metric]),rtol=2e-12,atol=3e-14)
                    assert prior['failure_class']==source[c+'_'+label+'_failure_class'];original_source_scores+=1
                for metric in METRICS:row[c+'_delta_'+metric]=row[c+'_C_'+metric]-row[c+'_F_'+metric] if row['measured'] else 0.
                if row['measured'] and not row['affected']:
                    for field in ('initial_state','end','mean_ports'):
                        assert results[c][field][j].tobytes()==results[c][field][j+n].tobytes()
                    assert results[c]['late_ports'][:,j].tobytes()==results[c]['late_ports'][:,j+n].tobytes()
            if row['measured']:
                for comp,other,later,before,after in PAIRS:
                    port_pair=np.stack((means[before][:,j],means[after][:,j]));value=describe.compare(port_pair,int(model.base.RULES[f]))
                    checked+=describe_audit.comparison(port_pair,int(model.base.RULES[f]),value)
                    pair=header(task,a,f,r,draw,inter,affected)
                    pair.update(component=comp,fixed_other=other,later=later,before_condition=before,after_condition=after,
                        target_size=row['target_size'],original_size=row['original_'+comp+'_size'],scale=row[comp+'_scale'],**value)
                    case_pairs.append(pair);pairs.append(pair)
            else:assert row['full_size_excess']==0
            add_effects(row,case_pairs)
            if row['measured'] and row['zero_target']:
                assert row[PRIMARY]==0 and row['m_both_contrast_abs']==0 and row['d_both_contrast_abs']==0
            rows.append(row)
    expected=32*cfg['recipients'];assert len(rows)==expected and len(pairs)==16*n
    assert {key(r) for r in rows}==set(known)
    elapsed=time.monotonic()-tick;variant_draws=32*n
    return rows,pairs,dict(status='PASS',task=task,seconds=elapsed,reader_seconds=reader_seconds,
        static_seconds=max(0.,elapsed-reader_seconds),context_draw_rows=len(rows),eligible_context_draws=2*n,
        evaluated_variant_draws=variant_draws,evaluated_variant_steps=variant_draws*(cfg['reader']['read_steps']-cfg['switch_step']),
        component_comparisons=len(pairs),scalar_port_checks=scalar_ports,original_source_scores=original_source_scores,
        independent_comparison_values=checked,independent_signed_budget_values=budgets,zero_targets=zero_targets,
        maximum_size_error=max_error,maximum_component_leak=max_leak,max_abs_initial=max_initial,boundary_counts=boundary,
        all_new_steps_replayed=True,all_scales_independently_reconstructed=True,all_later_offsets_exact=True,
        all_noops_retained=True,all_original_endpoints_and_harms_retained=True,initial_clipping=False)
