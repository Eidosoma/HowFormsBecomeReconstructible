"""Original anchors, exact archived endpoint reuse, independently replayed new steps."""
import math
import time
import numpy as np
from E110_halfway_state_diagnosis.analysis import check_assay
from E111_halfway_component_cross.experiment import validate_sources, validate_assay as validate_original
from E111_halfway_component_cross.model import initial as original_initial
from E113_component_threshold_diagnosis import measure as describe, audit as describe_audit
from E115_original_anchor_components import data, model, audit, normalization, normalization_audit
from E115_original_anchor_components.plan import CONDITIONS, ORIGINAL_CONDITIONS, COMPONENTS, VARIANTS, METRICS, PAIRS, OUTPUT_METRICS, PRIMARY, PRIOR_PRIMARY, MIDPOINT_PRIMARY, NORM_KEYS, key, full_component

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
    row['anchor_minus_midpoint']=row[PRIMARY]-row['midpoint_excess']
    for metric in METRICS:
        if metric!='both':row['anchored_shared_minus_cue_delta_'+metric]=row['m_'+metric+'_contrast_abs']-row['d_'+metric+'_contrast_abs']
    for a in 'ON':
        for c in ('m','d'):
            part=[p for p in pairs if p['component']==c and p['fixed_other']==a]
            assert len(part)==(2 if row['measured'] else 0)
            row[a+'_'+c+'_both_contrast_abs']=math.fsum(p['both_contrast_abs'] for p in part)/2 if part else 0.
        row[a+'_excess']=row[a+'_m_both_contrast_abs']-row[a+'_d_both_contrast_abs']


def subset(inter,sources,positions):
    """Reader batching only; keep the complete scientific eligibility separately."""
    contexts=np.argwhere(inter['eligible']);n=len(contexts);positions=np.asarray(positions,dtype=int)
    assert len(set(positions))==len(positions) and ((positions>=0)&(positions<n)).all()
    positions=np.sort(positions);take=np.concatenate((positions,positions+n))
    selected=np.zeros_like(inter['eligible'])
    for j in positions:selected[tuple(contexts[j])]=True
    subinter=dict(inter,eligible=selected);subs={}
    for a,source in sources.items():
        subs[a]={k:source[k][take].copy() for k in ('indices','used_masks','effective','denominator','coupling','switch_state')}
        subs[a].update({k:source[k] for k in ('masks','source_births','source_noise_hashes')})
        if not len(positions):subs[a]['source_noise_hashes']=source['source_noise_hashes'][:0].copy()
    return subinter,subs,take


def reuse_codes(norm,condition):
    a,k,l=condition;n=len(norm['target']);base=ORIGINAL_CONDITIONS.index(a+a+l)
    if k=='B':return np.full(n,base,dtype=np.int16)
    alpha=norm['scales'][:,int(k=='D')]
    target=ORIGINAL_CONDITIONS.index(full_component(a+k)+l)
    return np.where(alpha==0,base,np.where(alpha==1,target,-1)).astype(np.int16)


def originals(mode,task,draw,inter,sources,cfg,archived):
    out={};n=len(model.read_indices(inter))//2
    for h,c in enumerate(ORIGINAL_CONDITIONS):
        if c in ('OON','NNO'):
            old=sources['O' if c=='OON' else 'N'];initial=old['switch_state']
        else:
            old=data.arrays(mode,f'component_assay_{task:06d}_r{draw}_{c}.npz')
            validate_original(old,inter,sources,task,draw,cfg,c);initial=old['initial_state']
        assert initial.tobytes()==original_initial(sources,c[:2]).tobytes()
        final=np.stack([old['end'][...,model.P[p]].mean(-1) for p in (1,2)],axis=-1)
        assert final.tobytes()==old['late_ports'][-1].tobytes()
        assert old['mean_ports'].tobytes()==archived['mean_ports'][h].reshape(2*n,2,2).tobytes()
        out[c]=dict(initial_state=initial,end=old['end'],mean_ports=old['mean_ports'],late_ports=old['late_ports'])
    return out


def continuation(inter,sources,norm,old,task,draw,cfg,c,run=None):
    """Reused rows point to immutable originals; only partial-scale rows evolve."""
    tick=time.monotonic();codes=reuse_codes(norm,c);n=len(codes);partial=np.flatnonzero(codes<0)
    assembled={k:np.empty_like(old[ORIGINAL_CONDITIONS[0]][k]) for k in ('initial_state','end','mean_ports','late_ports')}
    for h,original in enumerate(ORIGINAL_CONDITIONS):
        positions=np.flatnonzero(codes==h);take=np.concatenate((positions,positions+n))
        for k in assembled:
            if k=='late_ports':assembled[k][:,take]=old[original][k][:,take]
            else:assembled[k][take]=old[original][k][take]
    seconds=0.;boundary=0
    if len(partial):
        subinter,subs,take=subset(inter,sources,partial)
        subnorm=normalization.calculate(subs);data.equal(subnorm,normalization_audit.calculate(subs))
        for k in ('free','free_cells','original_sizes','target','scales'):assert subnorm[k].tobytes()==norm[k][partial].tobytes()
        assert subnorm['source_md'].tobytes()==norm['source_md'][:,:,partial].tobytes()
        t=time.monotonic();result=model.read_batch(subinter,subs,subnorm,task,draw,cfg,c)
        data.equal(result,audit.read_batch(subinter,subs,subnorm,task,draw,cfg,c));seconds=time.monotonic()-t
        validate_assay(result,subinter,subs,subnorm,cfg,c)
        for k in assembled:
            if k=='late_ports':assembled[k][:,take]=result[k]
            else:assembled[k][take]=result[k]
        boundary=int(result['boundary_counts'].sum())
        if run is not None:data.save(run/f'assay_{task:06d}_r{draw}_{c}.npz',result)
    expected=normalization.initial(sources,norm,c[:2]);scalar=normalization_audit.initial(sources,norm,c[:2])
    assert assembled['initial_state'].tobytes()==expected.tobytes()==scalar.tobytes()
    assert assembled['late_ports'].mean(0).tobytes()==assembled['mean_ports'].tobytes()
    return assembled,codes,dict(reader_seconds=seconds,evaluated_variant_draws=2*len(partial),
        reused_variant_draws=2*(n-len(partial)),boundary_counts=boundary,seconds=time.monotonic()-tick)


def block(mode,task,cfg,known,midpoint,run=None):
    tick=time.monotonic();inter=data.arrays(mode,f'interventions_{task:06d}.npz')
    witness=data.arrays(mode,f'witnesses_{task:06d}.npz');model.structural(inter);budgets=audit.budget_checks(inter)
    assert inter['witness'].tobytes()==witness['used_witness'].tobytes() and inter['eligible'].tobytes()==witness['eligible'].tobytes()
    idx=model.read_indices(inter);contexts=np.argwhere(inter['eligible']);n=len(contexts);lookup={tuple(x):j for j,x in enumerate(contexts)}
    weights=model.base.decode(inter['packets']);rows=[];pairs=[];reader_seconds=0.;checked=0;scalar_ports=0;zero_targets=0
    original_source_scores=0;boundary=0;max_error=0.;max_leak=0.;max_initial=0.;new_draws=0;reused=0
    if run is not None:
        for name in (f'interventions_{task:06d}.npz',f'witnesses_{task:06d}.npz'):
            with (run/name).open('xb') as f:f.write(data.raw(mode,'original',name))
    for draw in (0,1):
        sources={o:data.arrays(mode,f'phase_assay_{task:06d}_r{draw}_{label}.npz') for o,label in (('O','ON'),('N','NO'))}
        phase_cfg=dict(switch_step=cfg['switch_step'],read_steps=cfg['reader']['read_steps'])
        for o,label in (('O','ON'),('N','NO')):check_assay(sources[o],inter,weights,draw,phase_cfg,label)
        validate_sources(inter,sources,task,draw,cfg)
        norm=normalization.calculate(sources);data.equal(norm,normalization_audit.calculate(sources))
        stored=data.arrays(mode,f'normalization_{task:06d}_r{draw}.npz','midpoint')
        assert stored['indices'].tobytes()==contexts.tobytes()
        data.equal(norm,{k:stored[k] for k in norm})
        matched=normalization.verify_sizes(sources,norm);zero_targets+=int((norm['target']==0).sum())
        max_error=max(max_error,float(matched['maximum_size_error'].max(initial=0)))
        max_leak=max(max_leak,float(matched['maximum_component_leak'].max(initial=0)))
        archived=data.arrays(mode,f'component_scores_{task:06d}_r{draw}.npz');assert archived['indices'].tobytes()==contexts.tobytes()
        old=originals(mode,task,draw,inter,sources,cfg,archived)
        if run is not None:data.save(run/f'normalization_{task:06d}_r{draw}.npz',dict(indices=contexts,**norm,**matched))
        scored={};means={};results={};reused_codes=[]
        for c in CONDITIONS:
            result,codes,rep=continuation(inter,sources,norm,old,task,draw,cfg,c,run)
            reader_seconds+=rep['reader_seconds'];new_draws+=rep['evaluated_variant_draws'];reused+=rep['reused_variant_draws']
            boundary+=rep['boundary_counts'];results[c]=result;reused_codes.append(codes)
            score=model.score(result['mean_ports'],idx,.25);data.equal(score,audit.score(result['mean_ports'],idx,.25))
            scored[c]={k:v.reshape((2,n)+v.shape[1:]) for k,v in score.items()};means[c]=result['mean_ports'].reshape(2,n,2,2)
            max_initial=max(max_initial,float(abs(result['initial_state']).max(initial=0)))
        zero=np.tile(norm['target']==0,2)
        for a in 'ON':
            for k in 'MD':
                for l in 'ON':
                    for field in ('initial_state','end','mean_ports'):
                        assert results[a+k+l][field][zero].tobytes()==results[a+'B'+l][field][zero].tobytes()
        if run is not None:
            combined={k:np.stack([scored[c][k] for c in CONDITIONS]) for k in scored[CONDITIONS[0]]}
            data.save(run/f'scores_{task:06d}_r{draw}.npz',dict(indices=contexts,mean_ports=np.stack([means[c] for c in CONDITIONS]),reuse_codes=np.stack(reused_codes),**combined))
            data.save(run/f'assembled_{task:06d}_r{draw}.npz',dict(indices=contexts,
                **{k:np.stack([results[c][k] for c in CONDITIONS]) for k in ('initial_state','end','late_ports')}))
        affected=(inter['witness']&model.reader.surviving_edges(inter['injury_masks'][draw])).any((-3,-2,-1))
        for a,f,r in np.ndindex(inter['eligible'].shape):
            row=header(task,a,f,r,draw,inter,affected);ident=key(row);source=known[ident];previous=midpoint[ident]
            for flag in ('eligible','affected','erased'):assert row[flag]==(source[flag]=='True')==(previous[flag]=='True')
            row['full_size_excess']=float(source[PRIOR_PRIMARY]);row['midpoint_excess']=float(previous[MIDPOINT_PRIMARY])
            case_pairs=[];j=lookup.get((a,f,r));row.update({k:None for k in NORM_KEYS})
            if row['measured']:
                row.update(free_cells=int(norm['free_cells'][j]),original_m_size=float(norm['original_sizes'][j,0]),
                    original_d_size=float(norm['original_sizes'][j,1]),target_size=float(norm['target'][j]),
                    m_scale=float(norm['scales'][j,0]),d_scale=float(norm['scales'][j,1]),zero_target=bool(norm['target'][j]==0),
                    m_C_size=float(matched['actual_sizes'][j,0,0]),m_F_size=float(matched['actual_sizes'][j,0,1]),
                    d_C_size=float(matched['actual_sizes'][j,1,0]),d_F_size=float(matched['actual_sizes'][j,1,1]),
                    maximum_size_error=float(matched['maximum_size_error'][j]),maximum_component_leak=float(matched['maximum_component_leak'][j]))
                for k in ('original_m_size','original_d_size','target_size','m_scale','d_scale'):assert row[k]==float(previous[k])
                for h,c in enumerate(ORIGINAL_CONDITIONS):
                    for v,label in enumerate(VARIANTS):
                        prior,_=describe_audit.scalar_score(archived['mean_ports'][h,v,j],int(model.base.RULES[f]))
                        for metric in METRICS:
                            assert float(archived[metric][h,v,j])==float(source[c+'_'+label+'_'+metric])
                            np.testing.assert_allclose(prior[metric],float(source[c+'_'+label+'_'+metric]),rtol=2e-12,atol=3e-14)
                        assert prior['failure_class']==source[c+'_'+label+'_failure_class'];original_source_scores+=1
            for c in CONDITIONS:
                for v,label in enumerate(VARIANTS):
                    for metric in METRICS:row[c+'_'+label+'_'+metric]=float(scored[c][metric][v,j]) if row['measured'] else None
                    row[c+'_'+label+'_failure_class']=None
                    if not row['measured']:continue
                    sc,_=describe_audit.scalar_score(means[c][v,j],int(model.base.RULES[f]))
                    for metric in METRICS:np.testing.assert_allclose(row[c+'_'+label+'_'+metric],sc[metric],rtol=2e-12,atol=3e-14)
                    row[c+'_'+label+'_failure_class']=sc['failure_class'];scalar_ports+=1
                for metric in METRICS:row[c+'_delta_'+metric]=row[c+'_C_'+metric]-row[c+'_F_'+metric] if row['measured'] else 0.
                if row['measured'] and not row['affected']:
                    for field in ('initial_state','end','mean_ports'):assert results[c][field][j].tobytes()==results[c][field][j+n].tobytes()
                    assert results[c]['late_ports'][:,j].tobytes()==results[c]['late_ports'][:,j+n].tobytes()
            if row['measured']:
                for comp,anchor,later,before,after in PAIRS:
                    port_pair=np.stack((means[before][:,j],means[after][:,j]));value=describe.compare(port_pair,int(model.base.RULES[f]))
                    checked+=describe_audit.comparison(port_pair,int(model.base.RULES[f]),value)
                    pair=header(task,a,f,r,draw,inter,affected)
                    pair.update(component=comp,fixed_other=anchor,anchor=anchor,later=later,before_condition=before,after_condition=after,
                        target_size=row['target_size'],original_size=row['original_'+comp+'_size'],scale=row[comp+'_scale'],**value)
                    case_pairs.append(pair);pairs.append(pair)
            else:assert row['full_size_excess']==row['midpoint_excess']==0
            add_effects(row,case_pairs)
            if row['measured']:
                for comp,word in (('m','shared'),('d','cue')):
                    if row[comp+'_scale']!=1:continue
                    for metric in METRICS:
                        for v,term in (('C','C_abs'),('F','F_abs'),('delta','contrast_abs')):
                            np.testing.assert_allclose(row[comp+'_'+metric+'_'+term],float(source['pooled_gross_'+word+'_'+v+'_'+metric]),rtol=2e-12,atol=3e-14)
                if row['zero_target']:assert row[PRIMARY]==row['m_both_contrast_abs']==row['d_both_contrast_abs']==0
            rows.append(row)
    assert len(rows)==32*cfg['recipients'] and len(pairs)==16*n and {key(r) for r in rows}==set(known)
    assert new_draws+reused==48*n
    elapsed=time.monotonic()-tick
    return rows,pairs,dict(status='PASS',task=task,seconds=elapsed,reader_seconds=reader_seconds,
        static_seconds=max(0.,elapsed-reader_seconds),context_draw_rows=len(rows),eligible_context_draws=2*n,
        evaluated_variant_draws=new_draws,reused_variant_draws=reused,evaluated_variant_steps=new_draws*(cfg['reader']['read_steps']-cfg['switch_step']),
        component_comparisons=len(pairs),scalar_port_checks=scalar_ports,original_source_scores=original_source_scores,
        independent_comparison_values=checked,independent_signed_budget_values=budgets,zero_targets=zero_targets,
        maximum_size_error=max_error,maximum_component_leak=max_leak,max_abs_initial=max_initial,boundary_counts=boundary,
        boundary_counts_scope='new partial continuations only; archived phase counts never reinterpreted as late counts',
        all_new_steps_replayed=True,all_scales_independently_reconstructed=True,all_later_offsets_exact=True,
        all_noops_retained=True,all_original_endpoints_and_harms_retained=True,initial_clipping=False)


