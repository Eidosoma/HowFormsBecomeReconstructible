"""Independent P02 provenance, native-boundary, forecast and aggregate audit."""
import ast
import time
import numpy as np
import analysis
import checks
import geometry
import models
import support as s


def provenance():
    files=s.verify_sources();submissions={};native={}
    for root in [s.SUB,s.RESIDUAL]:
        complete=s.read(root/'COMPLETE.json');s.require(complete['status']=='COMPLETE' and complete['verification_status']=='PASS','Submission incomplete')
        s.require(complete['final_snapshot_sha256']==s.sha(root/'FINAL_SNAPSHOT.json'),'Final snapshot binding')
        counts={}
        for name in ['definition_snapshot.json','FINAL_SNAPSHOT.json']:
            bindings=s.read(root/name)['files_sha256']
            for rel,digest in bindings.items():s.require(s.sha(root/rel)==digest,'Submitted snapshot file '+rel)
            counts[name]=len(bindings)
        submissions[root.name]=dict(final_snapshot_sha256=s.sha(root/'FINAL_SNAPSHOT.json'),verified_files=counts)
    configs={};trees={}
    for label in s.PACKAGES:
        done=s.read(s.native(label,'COMPLETE.json'));manifest=s.read(s.native(label,'manifest.json'));cfg=manifest['config'];configs[label]=cfg
        s.require(s.sha(s.native(label,'COMPLETE.json'))==s.CFG[label+'_complete_sha256'],'Native run binding')
        s.require(done['status']=='COMPLETE' and done['native_replay_passed'] and done['blocks_completed']==s.CFG['blocks'],'Native completion scope')
        s.require(len(done['receipts'])==8 and {r['block'] for r in done['receipts']}==set(s.CFG['blocks']),'Native receipt identities')
        for receipt in done['receipts']:
            name=f"cases_{receipt['block']:06d}.npz"
            s.require(receipt['status']=='COMPLETE' and receipt['case_sha256']==s.sha(s.native(label,name))==done['outputs_sha256'][name],'Block case binding')
        for rel,digest in manifest['code_sha256'].items():s.require(s.sha(s.native(label,'inputs/'+rel))==digest,'Native frozen implementation')
        for name in ['manifest.json','body_lineages.csv','terminal_lineages.csv',*[f'boundary_{b:06d}_g14.npz' for b in s.CFG['blocks']]]:
            if s.native(label,name).exists():s.require(s.sha(s.native(label,name))==done['outputs_sha256'][name],'Consumed native output '+name)
        native[label]=dict(complete_sha256=s.sha(s.native(label,'COMPLETE.json')),block_receipts=len(done['receipts']),
            saved_native_replay_passed=True,saved_scope=done['status_scope'],native_nonlinear_trajectories_replayed_by_TT007=0)
        tree=ast.parse(s.native(label,'inputs/dynamics.py').read_text());trees[label]={node.name:ast.dump(node,include_attributes=False) for node in tree.body if isinstance(node,ast.FunctionDef)}
    shared_functions=['stream','paired_founders','matched_cues','damage_masks','rebuild','assay','step','neighbors','incident','read_ports','score']
    for name in shared_functions:s.require(trees['spacing'][name]==trees['pulse'][name],'Common future dynamics differ: '+name)
    for name in ['config','cycle','pairing','blocks','branch_generation','terminal_generation','injuries']:
        s.require(configs['spacing'][name]==configs['pulse'][name],'Common native setting '+name)
    expected=[[],[3],[3,5,7,9,11,13],[3,9,10,11,12,13]]
    for history,generations in zip(s.CFG['histories'],expected,strict=True):
        s.require(configs['spacing']['tolerance_generations'][history]==generations,'Historical writer schedule')
        s.require(not set(generations)&set(range(14,33)),'Future tolerance event')
    s.require(configs['pulse']['schedules']['single_tolerance_rewrite']==dict(initial='tolerance_rewrite',later='exact_rewrite'),'Pulse policy')
    s.require(configs['spacing']['config']['writer_beta']==3 and configs['spacing']['config']['margin']==.25 and configs['spacing']['config']['side']==16,'Measurement constants')
    return dict(status='PASS',source_files_verified=len(files),submissions=submissions,native=native,
        identical_future_function_definitions=shared_functions,common_future_writer='O',
        dynamics_scope='Common-stream construction reviewed; no full new-arm nonlinear replay.',
        source_review_sha256=s.sha(s.HERE/'SOURCE_REVIEW.md'))


def native_tables(records):
    body=[r for r in s.table(s.native('spacing','body_lineages.csv')) if int(r['generation'])==14 and r['writer'] in s.CFG['histories']]
    terminal=[r for r in s.table(s.native('spacing','terminal_lineages.csv')) if r['injury']=='scattered' and r['writer'] in s.CFG['histories']]
    index={s.key(r):r for r in records};maximum=0.
    for name,rows in [('body',body),('terminal',terminal)]:
        ids=[(int(r['block']),r['writer'],int(r['founder']),int(r['recipient'])) for r in rows]
        s.require(len(ids)==len(set(ids))==512 and set(ids)==set(index),'Native table cohort '+name)
        for identity,raw in zip(ids,rows,strict=True):
            r=index[identity]
            if name=='body':
                s.require(raw['active_writer_policy']=='exact_rewrite','Boundary writer in table')
                pairs=[('success','current_pass'),('margin','current_margin'),('signed_transfer','signed_transfer'),('unsigned_access','unsigned_access')]
            else:pairs=[('success','terminal_success'),('margin','terminal_margin')]
            for field,target in pairs:maximum=max(maximum,s.close(float(raw[field]),r[target],label='Native '+name+' '+field))
    return dict(status='PASS',body_rows=len(body),terminal_rows=len(terminal),maximum_error=maximum)


def qualification(output):
    started=time.monotonic();rng=np.random.default_rng(704);measurements=[]
    for i in range(s.PLAN['qualification_contexts']):
        body=rng.normal(size=(2,16,16));mask=rng.random((16,16))<.09
        packet=geometry.capture(body,mask);measurements.append(geometry.transfers(packet,1 if i%2==0 else -1))
    records=checks.synthetic(705);y=np.array([r['terminal_success'] for r in records]);test=np.array([r['block']==s.CFG['blocks'][0] for r in records]);train=~test;fits=[]
    for model in s.CFG['models'][1:]:
        x,names=models.matrix(records,model);z,fit=models.fit(x,y,train,test);fits.append(dict(model=model['id'],maximum_gradient=fit['maximum_gradient'],iterations=len(fit['trace'])))
    seconds=time.monotonic()-started
    result=dict(status='PASS',classification='DISPOSABLE_SYNTHETIC_QUALIFICATION',compute_seconds=seconds,contexts=len(measurements),
        logistic_folds=len(fits),fits=fits,native_trajectories_generated=0,native_records_analyzed=0)
    s.dump(output/'qualification.json',result);return result


def audit(output,status):
    started=time.monotonic();status('source_provenance');sources=provenance();s.dump(output/'provenance.json',sources)
    status('native_boundary_reconstruction');records,diagnostics=geometry.reconstruct();models.validate(records)
    analysis.compare_csv(records,s.table(s.SUB/'results/records.csv'),list(s.KEYS));table_check=native_tables(records)
    maximum=max(abs(row[field]-saved[field]) for row,saved in zip(records,s.records(),strict=True) for field in row if field!='history')
    # Comparison above is keyed; this explicit order check binds the fitting matrix.
    s.require([s.key(r) for r in records]==[s.key(r) for r in s.records()],'Submitted record order differs')
    s.csv_write(output/'native_reconstructed_records.csv',records);s.csv_write(output/'capture_checks.csv',diagnostics)
    s.dump(output/'native_checks.json',dict(status='PASS',capture_packets=len(diagnostics),packet_bytes_each=4096,
        maximum_record_error=maximum,maximum_transfer_error=max(r['maximum_transfer_error'] for r in diagnostics),source_tables=table_check))
    status('independent_forecast_refits');submitted_records=s.records();predictions,fit_checks=models.saved_predictions(submitted_records,output)
    status('aggregate_and_residual_reconstruction');result=analysis.run(submitted_records,predictions,output)
    summary=dict(status='PASS',scientific_status='UNCONFIRMED_MIXED_DEVELOPMENT_EVIDENCE',source_files_verified=sources['source_files_verified'],
        record_count=len(records),capture_packets=len(diagnostics),saved_fit_records=len(fit_checks),independent_logistic_refits=40,history_rate_folds=8,
        predictions=len(predictions),score_rows=result['score_rows'],matched_pairs=result['pair_rows'],strict_pairs=result['matching']['subsets']['strict']['n'],
        matched_decision_rows=result['decision_rows'],maximum_record_error=maximum,
        maximum_transfer_error=max(r['maximum_transfer_error'] for r in diagnostics),
        maximum_saved_prediction_arithmetic_error=max(r['saved_arithmetic_error'] for r in fit_checks),
        maximum_independent_probability_error=max(r['maximum_refit_probability_error'] for r in fit_checks),
        maximum_independent_objective_difference=max(r['objective_difference'] for r in fit_checks),
        maximum_independent_fold_brier_difference=max(r['refit_brier_difference'] for r in fit_checks),
        primary_brier_improvement=result['forecasts']['comparisons'][0]['mean_brier_improvement'],
        independent_refit_primary_brier_improvement=result['forecasts']['comparisons'][0]['refit_mean_brier_improvement'],
        native_trajectories_generated=0,full_new_arm_dynamics_replayed=False,prospective_confirmation=False,seconds=time.monotonic()-started)
    s.dump(output/'audit.json',summary);return summary
