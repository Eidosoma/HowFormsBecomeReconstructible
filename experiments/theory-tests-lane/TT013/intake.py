"""Reconstruct every recipient-only repair, reference control and resource."""
from datetime import datetime
from pathlib import Path
import math
import numpy as np
import arithmetic as a
import boundary
import native as n
import repair
import support as s

VARIANTS=['incoming','outgoing','common_completion','full_own','full_completion','support_imputed','recipient_completion','recipient_shuffled','erased']
OPT_FIELDS=['signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes']
WEIGHTS=['common_added_abs_weight','full_added_abs_weight','imputed_support_added_abs_weight','recipient_added_abs_weight']


def provenance():
    receipt=s.verify_sources();base=s.HERE/'source/recipient';cfg=s.config('recipient');manifest=s.read(base/'run/manifest.json')
    s.require(cfg==manifest['config'],'Frozen configuration')
    s.require(cfg['blocks']==list(range(34000,34008)) and cfg['cases_per_block']==[7,11,9,4,4,4,16,9],'Complete enrolled panel')
    s.require(cfg['variants']==VARIANTS and cfg['replicates']==list(range(16)) and cfg['original_replicates']==[0],'All variants and assessment draws')
    s.require(cfg['budgets']==[2048] and cfg['primary_budget']==2048 and cfg['settling_steps']==1024,'Native timing')
    s.require(cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),'Native numeric law')
    s.require(cfg['injury_cells']==24 and cfg['numpy_version']==np.__version__,'Injury size and environment')
    s.require(cfg['random_namespace']=='P05_recipient_only_completion_v0_1' and cfg['bootstrap_seed']==2026101005 and cfg['bootstrap_replicates']==20000,'Sampling law')
    s.require(cfg['optimizer']['starts']==16 and cfg['optimizer']['maximum_sweeps']==64 and cfg['optimizer']['seed']==2026101004,'Unchanged optimizer effort')
    expected_completion=dict(support='every exactly zero outgoing edge on the fixed toroidal lattice',
        magnitude='median absolute nonzero outgoing weight; zero if none',preserve='all nonzero outgoing edges byte for byte',
        shuffle='fixed permutation of inferred signs over zero edges; same signs counts, magnitude and support')
    s.require(cfg['completion']==expected_completion,'Unchanged repair contract')
    prediction=s.read(base/'inputs/PREDICTION.json');p=prediction['primary']
    s.require(p['contrast']=='recipient_minus_outgoing' and p['left']=='recipient_completion' and p['right']=='outgoing' and p['direction']=='positive' and p['failure']=='point estimate <= 0','Original primary criterion')
    s.require(prediction['no_equivalence_margin'] and prediction['no_fitted_parameters'],'No invented equivalence criterion')
    times=[prediction['at_utc'],s.read(base/'inputs/prepared/COMPLETE.json')['at_utc'],manifest['at_utc'],s.read(base/'run/WORKER_STARTED.json')['at_utc'],s.read(base/'run/COMPLETE.json')['at_utc']]
    dates=list(map(datetime.fromisoformat,times));s.require(dates==sorted(dates) and len(set(dates))==len(dates),'Prediction/preparation/freeze/reader/completion chronology')
    prep=s.read(base/'inputs/prepared/COMPLETE.json')
    for name,digest in prep['code_sha256'].items():s.require(s.sha(base/'inputs'/name)==digest,'Prepared code commitment')
    s.require(prep['config_sha256']==s.sha(base/'inputs/config.json') and prep['protocol_sha256']==s.sha(base/'inputs/PROTOCOL.md'),'Preparation contract binding')
    old_complete=s.origin(Path(prep['source_prepared']).parent.parent/'COMPLETE.json')
    s.require(s.sha(old_complete)==cfg['source_complete_sha256'],'Antecedent completed source')
    prior=s.read(s.HERE/'source/tt012/job.json')
    for name in ['native.py','optimizer.py','support.py','arithmetic.py']:s.require(s.sha(s.HERE/name)==prior['inputs_sha256'][name],'Unchanged independent utility '+name)
    prior_checks=s.read(s.HERE/'source/tt012/TECHNICAL_CHECKS.json');s.require(prior_checks['status']=='PASS','Reused optimizer qualification')
    boundaries=boundary.run()
    exposure=s.read(base/'inputs/EXPOSURE_AND_DECISIONS.json')
    return dict(status='PASS',sources=len(receipt['files_sha256']),bindings=len(receipt['bindings']),chronology=times,
        prior_inputs_verified=receipt['prior_inputs_verified'],prior_outputs_verified=receipt['prior_outputs_verified'],
        antecedents_bound_to_TT012=receipt['antecedents_bound_to_TT012'],source_reuse_bindings=receipt['source_reuse_bindings'],
        source_functions_executed=False,source_declared_failed_validations=exposure['validation_failures_preserved'],
        reused_optimizer_exhaustive_fixtures=prior_checks['optimizer']['exhaustive_four_node_problems'],information_boundary=boundaries)


def reconstruct(old,cfg,block):
    count=len(old['founders']);solutions=[];primary=[];magnitudes=[]
    # All primary records are completed before historical controls are decoded.
    for case in range(count):
        fixed,solution,m=repair.from_saved(dict(packets=old['packets'][case]),cfg['optimizer'])
        primary.append(fixed);solutions.append(solution);magnitudes.append(m)
    outgoing=n.decode(old['packets'][:,1]);incoming=n.decode(old['packets'][:,0])
    records=[];full=[];outside=[];rows=[];shuffles=[]
    for case,solution in enumerate(solutions):
        f,r,h=map(int,(old['founders'][case],old['recipients'][case],old['histories'][case]))
        # Reusing this exact output is audited against TT012, not trusted as input.
        for key in OPT_FIELDS:
            saved=old['optimizer_'+key][case,2]
            s.equal(np.asarray(solution[key]),np.asarray(saved),'Reused completion solution '+key)
        missing=int(np.count_nonzero(outgoing[case]==0))
        permutation=n.random_stream(cfg['random_namespace'],int(block),'shuffle',h,f,r).permutation(missing)
        values,b,resource=repair.references(outgoing[case],incoming[case],old['common_edges'][case].reshape(2,256),
            old['original_masks'][case],solution,magnitudes[case],primary[case],permutation)
        records.append(values);full.append(b);outside.append(resource['missing_edges_outside_original_injury'])
        rows.append(dict(block=block,case=case,history=h,founder=f,recipient=r,**resource))
        shuffles.append(dict(block=block,case=case,permutation=permutation.tolist(),changed_signs=resource['shuffled_sign_changes']))
    packets=n.encode(np.stack(records));s.equal(packets[:,[0,1,2,8]],old['packets'][:,[0,1,7,8]],'Unchanged incoming/outgoing/common/erased controls')
    fields=['block','histories','founders','recipients','original_masks','original_end','original_mean_ports','original_birth','common_edges']
    expected={key:old[key] for key in fields}
    expected.update(packets=packets,masks=n.fresh_masks(cfg,block,old['founders'],old['recipients'],cfg['replicates']),
        replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),full_edges=np.array(full),
        outside_injury_missing_edges=np.array(outside),imputed_magnitudes=np.array(magnitudes))
    for key in OPT_FIELDS:expected['optimizer_'+key]=np.array([row[key] for row in solutions])
    return expected,rows,shuffles


def compare_resources(expected,actual):
    s.require(len(expected)==len(actual),'Every resource row')
    indexed={(int(row['block']),int(row['case'])):row for row in actual};s.require(len(indexed)==len(expected),'Unique resource cases')
    eps=np.finfo(float).eps;tiny=float(np.nextafter(0.,1.));max_error=0.;max_bound_fraction=0.
    for truth in expected:
        row=indexed[(truth['block'],truth['case'])];s.require(set(row)==set(truth),'Complete resource schema')
        for key,value in truth.items():
            observed=float(row[key])
            if key in WEIGHTS:
                error=abs(observed-value);bound=8*eps*max(abs(observed),abs(value))+4*tiny
                s.require(math.isfinite(observed) and error<=bound,'Resource sum rounding only '+key)
                max_error=max(max_error,error);max_bound_fraction=max(max_bound_fraction,error/bound if bound else 0.)
            else:s.require(observed==value,'Exact resource field '+key)
    return dict(resource_sum_max_error=max_error,resource_sum_max_bound_fraction=max_bound_fraction)


def run(output,blocks=None,progress=None):
    cfg=s.config('recipient');selected=cfg['blocks'] if blocks is None else blocks
    prior=s.read(s.HERE/'source/recipient/inputs/prepared/COMPLETE.json');panel={};rows=[];permutations=[];fields=0
    for block in selected:
        if progress:progress('independent_recipient_reconstruction',block=block)
        old=s.arrays(s.origin(Path(prior['source_prepared'])/f'cases_{block:06d}.npz'));saved=s.prepared('recipient',block)
        expected,resources,shuffles=reconstruct(old,cfg,block)
        s.require(len(old['founders'])==cfg['cases_per_block'][cfg['blocks'].index(block)],'No case exclusion')
        s.require(set(expected)==set(saved),'All prepared fields accounted for')
        raw=s.observed('recipient',block)
        for key,value in expected.items():
            s.equal(value,saved[key],f'Independent {block}/{key}');s.equal(value,raw[key],'Saved read preparation '+key);fields+=1
        panel[block]=raw;rows.extend(resources);permutations.extend(shuffles)
    table=s.table(s.HERE/'source/recipient/inputs/prepared/resources.csv')
    comparison=compare_resources(rows,[row for row in table if int(row['block']) in selected])
    totals=dict(problems=len(rows),independent_optimizer_checks=len(rows),independent_record_checks=9*len(rows),
        **{key:sum(row[key] for row in rows) for key in ['common_edges','full_backup_edges','recipient_missing_edges','missing_edges_outside_original_injury']},
        cases_with_extra_live_edges=sum(row['missing_edges_outside_original_injury']>0 for row in rows),
        cases_with_shuffled_changes=sum(row['shuffled_sign_changes']>0 for row in rows),
        selected_with_improving_single_flip=sum(row['selected_improvable_nodes']>0 for row in rows),
        maximum_sweeps_used=max(row['optimizer_sweeps'] for row in rows))
    if blocks is None:
        source=s.read(s.HERE/'source/recipient/inputs/prepared/FEASIBILITY.json')
        for key,value in totals.items():s.require(source[key]==value,'Prepared totals '+key)
        s.require(len(rows)==64,'All 64 recipient-only repairs')
    s.csv_write(output/'resources.csv',rows);s.dump(output/'permutations.json',permutations)
    result=dict(status='PASS',blocks=list(selected),reconstructed_fields=fields,**comparison,**totals)
    s.dump(output/'INTAKE_AUDIT.json',result);return panel,result
