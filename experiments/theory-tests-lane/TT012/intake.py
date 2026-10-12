"""Independent source binding, optimizer reconstruction, grafts and masks."""
from datetime import datetime
import ast
from pathlib import Path
import numpy as np
import arithmetic as a
import graph
import native as n
import optimizer as opt
import support as s

VARIANTS=['incoming','outgoing','common_own','same_unaligned','opposite_unaligned','same_aligned','opposite_aligned','completion','erased']
OPT_ARRAYS=['signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes']


def provenance():
    receipt=s.verify_sources();root=s.HERE/'source/approx';cfg=s.config('approx')
    s.require(cfg['blocks']==list(range(34000,34008)) and cfg['cases_per_block']==[7,11,9,4,4,4,16,9],'All enrolled cases')
    s.require(cfg['variants']==VARIANTS and cfg['replicates']==list(range(16)) and cfg['original_replicates']==[0],'All records and repetitions')
    s.require(cfg['budgets']==[2048] and cfg['primary_budget']==2048 and cfg['settling_steps']==1024,'Reader timing')
    s.require(cfg['reader']==dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),'Native numerical contract')
    s.require(cfg['injury_cells']==24 and cfg['bootstrap_replicates']==20000 and cfg['bootstrap_seed']==2026101004,'Sampling contract')
    s.require(cfg['optimizer']['starts']==16 and cfg['optimizer']['maximum_sweeps']==64 and cfg['optimizer']['seed']==2026101004,'Fixed optimizer budget')
    s.require(cfg['random_namespace']=='P05_approximate_alignment_v0_1' and cfg['numpy_version']==np.__version__,'Stream and environment')
    prediction=s.read(root/'inputs/PREDICTION.json');manifest=s.read(root/'run/manifest.json');done=s.read(root/'run/COMPLETE.json')
    s.require(manifest['config']==cfg,'Frozen config equality')
    s.require(prediction['protocol_sha256']==s.sha(root/'inputs/PROTOCOL.md') and prediction['config_sha256']==s.sha(root/'inputs/config.json'),'Prediction bindings')
    s.require(prediction['primary']['contrast']=={'same_aligned':.5,'opposite_aligned':.5,'same_unaligned':-.5,'opposite_unaligned':-.5},'Primary contrast unchanged')
    s.require(prediction['primary']['direction']=='positive' and prediction['primary']['effect_size_target'] is None,'Primary direction only')
    times=[prediction['at_utc'],manifest['at_utc'],s.read(root/'run/WORKER_STARTED.json')['at_utc'],done['at_utc']]
    dates=list(map(datetime.fromisoformat,times));s.require(dates==sorted(dates) and len(set(dates))==4,'Local prediction-freeze-start-completion chronology')
    prep=s.read(root/'inputs/prepared/COMPLETE.json');old=s.origin(Path(prep['source_prepared']).parent.parent/'COMPLETE.json')
    s.require(s.sha(old)==cfg['source_complete_sha256'],'Completed P05 source')
    # The exact bytes of the current source reader are those already bound by TT011.
    s.require(s.sha(root/'inputs/reader.py')=='0d9717638eb2b24c213d5b6f9f392d07f9bade259f6c4869da0d7312ded51532','Previously reviewed native reader identity')
    # Source functions are inspected as syntax/data, never imported or executed.
    tree=ast.parse((root/'inputs/optimizer.py').read_text())
    signatures={node.name:[arg.arg for arg in node.args.args] for node in tree.body if isinstance(node,ast.FunctionDef)}
    s.require(signatures['align']==['outgoing','donor','options'] and signatures['complete']==['outgoing','options'],'Source solver argument boundary')
    failures=[s.read(root/f'inputs/validation_attempt{i}/FAILURE.json') for i in (1,2)]
    s.require(all(row['status']=='FAILED' if 'status' in row else row['tests_failed']==1 for row in failures),'Source failures retained')
    return dict(status='PASS',sources=len(receipt['files_sha256']),source_bindings=len(receipt['bindings']),chronology=times,
        prior_inputs_verified=receipt['prior_inputs_verified'],prior_outputs_verified=receipt['prior_outputs_verified'],
        P05_antecedents_bound_to_TT011=receipt['P05_antecedents_bound_to_TT011'],source_code_executed=False,
        same_source_reader_as_TT011=True,source_validation_failures_retained=2,
        information_boundary='Algorithmic only; full containers are exposed. Donor alignment uses O,D, fixed ports and options. Completion uses O, input ports and options.',
        independent_fallback_supplement_recertification=False)


def solve_visible(outgoing_packet,donor_packets,options):
    outgoing=n.decode(outgoing_packet);donors=n.decode(donor_packets)
    results=[];max_local_error=0.
    for donor,pins in [(donors[0],opt.ALL_PINS),(donors[1],opt.ALL_PINS),(None,opt.INPUT_PINS)]:
        c=opt.coupling(outgoing,donor);sol=opt.solve(c,pins,options)
        max_local_error=max(max_local_error,opt.scalar_local_check(sol['signs'],c));results.append(sol)
    return results,max_local_error


def reconstruct(old,cfg,block):
    outgoing=n.decode(old['packets'][:,1]);donors=n.decode(old['donor_packets']);count=len(outgoing)
    # Missing own signs do not enter either solver. Decode I only after solving.
    solutions=[];local_error=0.
    for case in range(count):
        sol,err=solve_visible(old['packets'][case,1],old['donor_packets'][case],cfg['optimizer'])
        solutions.append(sol);local_error=max(local_error,err)
    incoming=n.decode(old['packets'][:,0]);rows=[];records=[];equiv=[];changes=[];certificates=[]
    available=n.available(old['original_masks'])
    common=(~available)&(incoming!=0)&(donors[:,0]!=0)&(donors[:,1]!=0)
    s.equal(common.reshape(count,2,16,16),old['common_edges'],'Common supplied support')
    s.require(not outgoing[~available].any(),'Outgoing has no unavailable edge')
    s.equal(old['donor_founders'],np.stack((old['founders']^2,old['founders']^3),axis=1),'Fixed donor identity')
    for case in range(count):
        weights=np.repeat(outgoing[case,None],9,axis=0);weights[0]=incoming[case];weights[8]=0.;k=common[case]
        signs=[np.sign(incoming[case]),np.sign(donors[case,0]),np.sign(donors[case,1])]
        for di,sol in enumerate(solutions[case]):
            g=sol['signs'].ravel();transform=(g[opt.U]*g[opt.V]).reshape(2,256)
            signs.append(transform*(np.sign(donors[case,di]) if di<2 else 1))
        for vi,edge_signs in enumerate(signs,2):weights[vi,k]=abs(incoming[case,k])*edge_signs[k]
        pairs=[];changed=[]
        for di in (0,1):
            x,y=weights[3+di].ravel(),weights[5+di].ravel();support=x!=0
            s.equal(abs(x),abs(y),'Unsigned aligned/unaligned hybrid')
            edges=[(int(u),int(v)) for u,v,on in zip(opt.U,opt.V,support) if on]
            rhs=(np.signbit(x[support])^np.signbit(y[support])).astype(int).tolist()
            matrix,values=graph.equations(edges,rhs,opt.ALL_PINS)
            exact=graph.eliminate(256,matrix,values);uf=graph.union_find(256,edges,rhs,opt.ALL_PINS)
            s.require(exact['ok']==uf['ok'] and exact['rank']==uf['rank'],'Independent hybrid gauge solvers')
            if not exact['ok']:graph.certificate(matrix,values,exact['witness'])
            pairs.append(exact['ok']);changed.append(int(np.count_nonzero(np.sign(x)!=np.sign(y))))
            certificates.append(dict(block=block,case=case,donor=di,equivalent=exact['ok'],coefficient_rank=exact['rank'],witness=exact['witness']))
        for di,sol in enumerate(solutions[case]):
            rows.append(dict(block=block,case=case,problem=['same','opposite','completion'][di],
                **{key:sol[key] for key in ['initial_cost','cost','total_weight','mismatch_fraction','winner','sweeps','selected_improvable_nodes']},
                backup_sign_changes=changed[di] if di<2 else None,hybrid_gauge_equivalent=str(pairs[di]) if di<2 else None))
        for vi in range(3,8):s.equal(abs(weights[vi]),abs(weights[2]),'All matched unsigned records')
        records.append(weights);equiv.append(pairs);changes.append(changed)
    packets=n.encode(np.stack(records));s.equal(packets[:,[0,1,2,3,4,8]],old['packets'][:,[0,1,3,4,5,7]],'All inherited controls')
    inherited=['block','histories','founders','recipients','original_masks','original_end','original_mean_ports','original_birth','donor_packets','donor_founders','common_edges']
    expected={key:old[key] for key in inherited}
    expected.update(packets=packets,masks=n.fresh_masks(cfg,block,old['founders'],old['recipients'],cfg['replicates']),
        replicates=np.array(cfg['replicates']),original_replicates=np.array(cfg['original_replicates']),
        hybrid_gauge_equivalent=np.array(equiv),backup_sign_changes=np.array(changes))
    for key in OPT_ARRAYS:expected['optimizer_'+key]=np.array([[sol[key] for sol in case] for case in solutions])
    return expected,rows,certificates,local_error


def run(output,blocks=None,progress=None):
    cfg=s.config('approx');selected=cfg['blocks'] if blocks is None else blocks
    prep=s.read(s.HERE/'source/approx/inputs/prepared/COMPLETE.json');panel={};rows=[];witnesses=[];fields=0;local_error=0.
    for block in selected:
        if progress:progress('independent_optimization',block=block)
        name=f'cases_{block:06d}.npz';old=s.arrays(s.origin(Path(prep['source_prepared'])/name));fixed=s.prepared('approx',block)
        expected,diagnostics,certs,error=reconstruct(old,cfg,block)
        s.require(set(expected)==set(fixed),'Prepared complete field schema')
        for key in expected:s.equal(expected[key],fixed[key],'Reconstructed preparation '+str(block)+'/'+key);fields+=1
        raw=s.observed('approx',block)
        for key in expected:s.equal(expected[key],raw[key],'Raw preserves preparation '+key)
        panel[block]=raw;rows.extend(diagnostics);witnesses.extend(certs);local_error=max(local_error,error)
    table=s.table(s.HERE/'source/approx/inputs/prepared/optimizer.csv')
    subset=[row for row in table if int(row['block']) in selected]
    temporary=output/'source_optimizer_subset.csv';s.csv_write(temporary,subset)
    a.compare_table(rows,temporary,['block','case','problem']);s.csv_write(output/'optimizer.csv',rows)
    s.dump(output/'hybrid_certificates.json',witnesses)
    donor_rows=[r for r in rows if r['problem']!='completion']
    totals=dict(problems=len(rows),independent_optimizer_checks=len(rows),donor_pairs=len(donor_rows),
        changed_backup_pairs=sum(r['backup_sign_changes']>0 for r in donor_rows),
        non_equivalent_hybrids=sum(r['hybrid_gauge_equivalent']=='False' for r in donor_rows),
        strict_objective_improvements=sum(r['cost']<r['initial_cost'] for r in donor_rows),
        selected_with_improving_single_flip=sum(r['selected_improvable_nodes']>0 for r in rows),
        maximum_sweeps_used=max(r['sweeps'] for r in rows))
    if blocks is None:
        source=s.read(s.HERE/'source/approx/inputs/prepared/FEASIBILITY.json')
        for key,value in totals.items():s.require(source[key]==value,'Source optimizer feasibility '+key)
        s.require(sum(len(d['founders']) for d in panel.values())==64,'Full enrolled panel')
    result=dict(status='PASS',blocks=list(selected),reconstructed_fields=fields,scalar_local_field_max_error=local_error,
        rational_objectives_checked=len(rows),whole_hybrid_certificates=len(witnesses),**totals)
    s.dump(output/'INTAKE_AUDIT.json',result);return panel,result
