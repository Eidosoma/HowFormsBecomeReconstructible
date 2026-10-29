"""Unchanged archived interventions, all-case new baselines, complete histories."""
import hashlib
import time
import numpy as np
from common import rng
from E105_cycle_input_control.experiment import rows as old_rows
from E106_fresh_reader_sign_control import data,model,audit
from E106_fresh_reader_sign_control.plan import VARIANTS,METRICS,CONTRASTS


def prepare(mode,task):
    inter=data.arrays(mode,f'interventions_{task:06d}.npz')
    model.structural(inter);checks=audit.budget_checks(inter)
    diagnostics=data.arrays(mode,f'diagnostics_{task:06d}.npz')
    calculated=audit.diagnostics(inter)
    for k in diagnostics:np.testing.assert_allclose(diagnostics[k],calculated[k],rtol=2e-14,atol=2e-15,err_msg=k)
    masks=inter['injury_masks'];R=inter['eligible'].shape[2]
    for draw in (0,1):assert masks[draw].tobytes()==model.old.masks(task,R,f'E102_terminal_{draw}_injury',0).tobytes()
    return inter,diagnostics,dict(eligible=int(inter['eligible'].sum()),eligible_native=int(inter['eligible'][:2].sum()),
        eligible_mixture=int(inter['eligible'][2:].sum()),eligible_context_draws=2*int(inter['eligible'].sum()),
        evaluated_context_draws=2*inter['eligible'].size,evaluated_variant_draws=2*len(model.read_indices(inter)),
        affected_by_draw=[int((inter['witness']&model.reader.surviving_edges(m)).any(axis=(-3,-2,-1)).sum()) for m in masks],
        budget_values_checked=checks,packets_sha256=hashlib.sha256(inter['packets'].tobytes()).hexdigest(),
        witness_sha256=hashlib.sha256(inter['witness'].tobytes()).hexdigest(),
        common_sha256=hashlib.sha256(inter['common_magnitude'].tobytes()).hexdigest())


def assembled(inter,draw,fresh,scores):
    shape=inter['eligible'].shape
    expected=model.read_indices(inter);assert fresh['indices'].tobytes()==expected.tobytes()
    result={k:np.zeros((4,*shape,*v.shape[1:]),dtype=v.dtype) for k,v in scores.items()}
    present=np.zeros((4,*shape),bool)
    # D is evaluated everywhere; it is the only permitted source for identity aliases.
    for j,(variant,a,f,r) in enumerate(fresh['indices']):
        if variant!=0:continue
        present[0,a,f,r]=True
        for k in result:result[k][0,a,f,r]=scores[k][j]
    assert present[0].all()
    for k in result:
        for v in (1,2,3):result[k][v]=result[k][0]
    for j,loc in enumerate(map(tuple,fresh['indices'])):
        present[loc]=True
        for k in result:result[k][loc]=scores[k][j]
    for v in (1,2,3):assert np.array_equal(present[v],inter['eligible'])
    affected=(inter['witness']&model.reader.surviving_edges(inter['injury_masks'][draw])).any(axis=(-3,-2,-1))
    for k in result:
        for v in (1,2,3):assert result[k][v][~inter['eligible']].tobytes()==result[k][0][~inter['eligible']].tobytes()
    lookup={tuple(int(x) for x in loc):j for j,loc in enumerate(fresh['indices'])}
    for a,f,r in np.argwhere(inter['eligible']&~affected):
        baseline=lookup[(0,int(a),int(f),int(r))]
        for v in (1,2,3):
            j=lookup[(v,int(a),int(f),int(r))]
            assert fresh['end'][j].tobytes()==fresh['end'][baseline].tobytes(),'Erased-cycle state identity'
            for k in result:assert result[k][v,a,f,r].tobytes()==result[k][0,a,f,r].tobytes()
    assert np.array_equal(result['both'],result['minimum_margin']>.25)
    return result,affected,present


def freshness(fresh,task,draw,cfg,previous):
    assert fresh['masks'].tobytes()==previous['masks'].tobytes()
    R=cfg['recipients'];stream=rng('E077',task,f'E102_terminal_{draw}',0)
    before=cfg['config']['birth_sd']*model.base.paired_founders(stream.standard_normal((2,R,16,16)))
    assert before.tobytes()==previous['birth'].tobytes()
    old_noise=model.base.paired_founders(stream.standard_normal((2,R,16,16)))
    assert fresh['birth'].tobytes()!=before.tobytes()
    assert fresh['noise_hashes'][0].tobytes()!=model.old.digest(old_noise).tobytes()


def rows(task,draw,inter,scores,diagnostics,affected,previous_scores):
    out=old_rows(task,draw,inter,scores,diagnostics,affected)
    for row in out:
        a,f,r=(row[k] for k in ('arm','founder','recipient'));eligible=bool(inter['eligible'][a,f,r])
        row.update(evaluated=True,variants_evaluated=4 if eligible else 1,identity_variants_derived=not eligible)
        for v,label in enumerate(VARIANTS):
            for key in METRICS:row['previous_'+label+'_'+key]=float(previous_scores[key][v,a,f,r])
        for name,parts in CONTRASTS.items():
            for key in METRICS:row['previous_'+name+'_'+key]=sum(c*row['previous_'+v+'_'+key] for v,c in parts.items())
        for key in METRICS:row['repeat_change_'+key]=row['matched_arrangement_'+key]-row['previous_matched_arrangement_'+key]
    return out


def block(mode,task,cfg,run=None,expected=None):
    assert cfg['reader_stream']=='E106_fresh'
    started=time.monotonic();inter,diagnostics,inv=prepare(mode,task)
    if expected is not None:assert inv==expected
    if run is not None:
        # Exact pinned bytes make the unchanged intervention provenance explicit.
        for tag in ('interventions','diagnostics'):
            with (run/f'{tag}_{task:06d}.npz').open('xb') as f:f.write(data.raw(mode,f'{tag}_{task:06d}.npz'))
    records=[];reader_seconds=0.;assays={}
    for draw in (0,1):
        previous=data.arrays(mode,f'assay_{task:06d}_r{draw}.npz')
        previous_scores=data.arrays(mode,f'scores_{task:06d}_r{draw}.npz')
        tick=time.monotonic();fresh=model.read_batch(inter,task,draw,cfg)
        data.equal(fresh,audit.read_batch(inter,task,draw,cfg));reader_seconds+=time.monotonic()-tick
        score=model.score(fresh['mean_ports'],fresh['indices'],cfg['config']['margin'])
        data.equal(score,audit.score(fresh['mean_ports'],fresh['indices'],cfg['config']['margin']))
        freshness(fresh,task,draw,cfg,previous)
        scores,affected,present=assembled(inter,draw,fresh,score)
        records.extend(rows(task,draw,inter,scores,diagnostics,affected,previous_scores))
        if run is not None:
            data.save(run/f'assay_{task:06d}_r{draw}.npz',fresh)
            data.save(run/f'scores_{task:06d}_r{draw}.npz',dict(**scores,eligible=inter['eligible'],affected=affected,variant_evaluated=present))
        assays[draw]=fresh
    elapsed=time.monotonic()-started
    return records,dict(status='PASS',task=task,seconds=elapsed,reader_seconds=reader_seconds,static_seconds=max(0.,elapsed-reader_seconds),
        inventory=inv,evaluated_context_draws=inv['evaluated_context_draws'],eligible_context_draws=inv['eligible_context_draws'],
        evaluated_variant_draws=inv['evaluated_variant_draws'],evaluated_variant_steps=inv['evaluated_variant_draws']*cfg['reader']['read_steps'],
        identity_context_draws=len(records)-inv['eligible_context_draws'],context_draw_rows=len(records),
        every_new_step_independently_replayed=True,all_new_D_baselines=True,all_old_new_streams_distinct=True,
        all_constraints_verified=True,old_outcomes_cached=False,new_source_blocks=0,writer_dynamics_repeated=False),assays
