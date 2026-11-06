"""Frozen engineering test of an erased output decoder with explicit informative references."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h083.audit import Audit
from h093.fixtures import rejects
from h094 import dynamics,reference
from h095 import model as m
from h096.null_check import transport,STATE_FIELDS
from h097.audit import shifted_factor
from h098.workflow import FILES as PARENT_FILES,verify_parent
from h099 import calibration as c

PINS={'h095_fresh_context_v1':'7d0cc8ee0319c2037f01b197f293a10657806d19467bf18b17f86766aff5587f',
    'h098_precision_correction_v1':'529d7a12ce0071d0beeab123343edac5f0ffb9db84fa9e2ccfe52dd58e0f31fa'}
FILES=PARENT_FILES+['h099/PROTOCOL.md','h099/calibration.py','h099/engineering.py']
MODES=('retained','erased_no_reference','erased_reference_repair')
def read(path):return json.loads(Path(path).read_text())
def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k] for k in f.files}
def measured_reference(polarity):
    # Environment port only. The learner receives commands/measurements, never polarity.
    commands=np.stack((np.ones(48,dtype=np.int8),-np.ones(48,dtype=np.int8)))
    return dict(reference_commands=commands,measured_responses=commands*polarity,observed=np.ones((2,48),dtype=bool))
def fit(observed):
    return m.compile_record(m.complete(dict(observed_inputs=m.X[m.TRAIN],observed_outputs=observed)),'neural')
def decode(codebook,physical):return c.decode(dict(codebook=codebook,physical_responses=physical))
def scores(output,target,known):
    hits=(output==target).sum(-1);ok=(hits>=44)&known.all(-1)
    return dict(tasks=1,task_correct=int(ok.all()),queries=8,query_correct=int(ok.sum()),
        exact_queries=int(((hits==48)&known.all(-1)).sum()),correct_bits=int((output==target).sum()),
        bits=384,unresolved_bits=int((~known).sum()))

def information_checks(tape,polarity,out):
    packet=measured_reference(polarity);learned=c.learn(packet);np.testing.assert_array_equal(learned['signs'],polarity)
    assert learned['known'].all();erased=c.erase(learned);assert not erased['signs'].any() and not erased['known'].any()
    empty_packet={k:v[:0].copy() for k,v in packet.items()};unresolved=c.learn(empty_packet)
    assert not unresolved['known'].any() and not unresolved['signs'].any()
    partial={k:v.copy() for k,v in packet.items()};partial['observed'][:,24:]=False;partial['measured_responses'][:,24:]=0
    partial_fit=c.learn(partial);assert partial_fit['known'].sum()==24 and not partial_fit['signs'][24:].any()
    bad={k:v.copy() for k,v in packet.items()};bad['measured_responses'][1,0]*=-1;rejects(lambda:c.learn(bad))
    for key in ('polarity','true_labels','old_decoder'):rejects(lambda key=key:c.learn(dict(packet,**{key:polarity})))
    physical=tape['responses_own']*polarity;np.testing.assert_array_equal(decode(learned,physical)['values'],tape['responses_own'])
    assert not decode(unresolved,physical)['known'].any()
    # Every independent semantic sign can change without changing any physical task data.
    flips=np.ones((48,48),dtype=np.int8);np.fill_diagonal(flips,-1)
    for f in flips:
        other_target=tape['responses_own']*f;other_polarity=polarity*f
        np.testing.assert_array_equal(other_target*other_polarity,physical)
        assert np.any(other_target!=tape['responses_own'])
        assert np.any(measured_reference(other_polarity)['measured_responses']!=packet['measured_responses'])
    alternative=-tape['responses_own'];other_polarity=-polarity
    a,b=fit(physical[m.TRAIN]),fit((alternative*other_polarity)[m.TRAIN])
    for k in a:np.testing.assert_array_equal(a[k],b[k])
    evidence=dict(physical_responses=physical,target_world_a=tape['responses_own'],target_world_b=alternative,
        polarity_world_a=polarity,polarity_world_b=other_polarity,independent_sign_alternatives=flips,
        learned_signs=learned['signs'],erased_signs=erased['signs'],erased_known=erased['known'],
        partial_signs=partial_fit['signs'],partial_known=partial_fit['known'],**packet)
    with out.open('xb') as stream:np.savez_compressed(stream,**evidence)
    tests=['reference measurements recover all 48 calibration signs',
        'erasure removes every sign and validity bit; empty interaction remains unresolved',
        'partial reference coverage identifies only its 24 observed signs',
        'contradictory references and hidden-map/target/old-decoder arguments are rejected',
        '48 independent semantic-sign alternatives preserve physical codewords while changing correct interpretation',
        'opposite semantic worlds yield identical stored physical records; labelled references distinguish them']
    return dict(passed=True,count=len(tests),tests=tests,remaining_sign_ambiguities_without_references=48)

def audit_read(tape,record,data,g,b):
    raw=dict(tape,inputs=m.X);check=Audit();factor=shifted_factor(record['J'],check)
    ref={k:v.astype(np.longdouble) if k!='interaction_masks' else v for k,v in record.items()}
    reference.trajectory(raw,dict(generation=g,birth=b),record,data,ref,factor,check)
    return dict(checks=check.count,minimum_boundary_distance=check.boundary_minimum,
        maximum_field_error=check.max_field_error,maximum_pair_energy_error=check.max_pair_error)

def run(out):
    assert ROOT==out/'source';config=read(out/'config.json');lane=Path(config['lane_root']);start=time.perf_counter()
    state=dict(state='RUNNING',phase='admission',pid=os.getpid(),workers=0,started_utc=utc())
    def progress(**kw):
        state.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-start);save(out/'STATUS.json',state);print(json.dumps(state),flush=True)
    try:
        verify(out,'freeze.json');progress();admission=capacity(out/'admission.json',1,progress)
        progress(state='RUNNING',phase='parent_qualification',workers=1)
        assert config['python']==sys.version and config['numpy']==np.__version__
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        for name,pin in PINS.items():
            parent=lane/'runs'/name;assert checksum(parent/'checksums.json')==pin;verify(parent,'checksums.json')
            assert read(parent/'COMPLETE.json')['integrity_passed']
        receipt=lane/'.cache/h098_completion_verification_v1.json'
        assert checksum(receipt)==config['qualification_receipt_sha256'] and read(receipt)['passed']
        oldfiles=verify_parent(lane/'runs/h097_connection_loss_v1',lane/'.cache/h097_threshold_probe_v1/parent_inventory.json')
        for name in FILES:assert checksum(ROOT/name)==checksum(lane/name),name
        for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(lane/'runs/h098_precision_correction_v1/source'/name),name
        (out/'raw').mkdir();(out/'audits').mkdir();allrows=[];audits=[];information=[];record_error=0.;arrays=0
        for block in range(4):
            progress(phase='engineering',completed_blocks=block,total_blocks=4)
            source=load(out/'inputs'/f'engineering_{block:03d}.npz');polarity=source.pop('calibration_polarity')
            for key,value in m.tapes('engineering',block).items():np.testing.assert_array_equal(source[key],value)
            d=np.r_[np.ones(80,dtype=np.int8),polarity];physical_tape={k:v.copy() for k,v in source.items()}
            physical_tape['birth']*=d
            information.append(information_checks(source,polarity,out/'raw'/f'block_{block:03d}_information.npz'))
            founder_reference=measured_reference(polarity);founder_decoder=c.learn(founder_reference)
            for route in ('rewrite','copy'):
                for birth in range(4):
                    observed=source['responses_own'][m.TRAIN]*polarity
                    canonical=fit(decode(founder_decoder,observed)['values']);record=fit(observed)
                    prior_read=None
                    for generation in range(3):
                        prefix=f'b{block:03d}_{route}_birth{birth}_g{generation}'
                        if generation:
                            parent_observed=prior_read['pair_final'][m.TRAIN,0,80:].copy()
                            if route=='rewrite':
                                observed=parent_observed;record=fit(observed)
                                canonical=fit(decode(founder_decoder,observed)['values'])
                            else:
                                # Physical copying carries all coefficients but no erased decoder backup.
                                record={k:v.copy() for k,v in record.items()};canonical={k:v.copy() for k,v in canonical.items()}
                        else:parent_observed=observed.copy()
                        translated=transport(canonical,d)
                        for k in record:
                            delta=float(np.max(np.abs(record[k].astype(float)-translated[k].astype(float))));record_error=max(record_error,delta)
                            np.testing.assert_allclose(record[k],translated[k],rtol=0,atol=4e-14)
                        packet=dict(record=record,birth=physical_tape['birth'][generation,birth],observed_history=m.X,
                            **{'orders_'+p:physical_tape['orders_'+p][generation] for p in ('context','gap','query')})
                        physical=dynamics.read(packet)
                        original=dynamics.read(dict(packet,record=canonical,birth=source['birth'][generation,birth]))
                        references=measured_reference(polarity)
                        erased=c.erase(founder_decoder);recovered=c.learn(references)
                        empty_references={k:v[:0].copy() for k,v in references.items()};unknown=c.learn(empty_references)
                        assert not erased['signs'].any() and not unknown['known'].any()
                        for k in recovered:np.testing.assert_array_equal(recovered[k],founder_decoder[k])
                        books=dict(retained=founder_decoder,erased_no_reference=unknown,erased_reference_repair=recovered)
                        if generation==0:books={mode:founder_decoder for mode in MODES}
                        reader='pair' if generation==0 else 'ordinary';z=physical[reader+'_final'][:,0,80:]
                        outputs={mode:decode(book,z) for mode,book in books.items()}
                        flat=dict(parent_observed=parent_observed,writer_observed=observed,polarity=polarity,erased_signs=erased['signs'],erased_known=erased['known'],**references)
                        for label,values in (('physical',physical),('canonical',original),('record',record),('canonical_record',canonical)):
                            flat.update({label+'__'+k:v for k,v in values.items()})
                        for mode,book in books.items():flat.update({mode+'__decoder_'+k:v for k,v in book.items()})
                        for mode,decoded in outputs.items():flat.update({mode+'__'+k:v for k,v in decoded.items()})
                        path=out/'raw'/(prefix+'.npz')
                        with path.open('xb') as stream:np.savez_compressed(stream,**flat)
                        saved=load(path)
                        for key,value in flat.items():np.testing.assert_array_equal(saved[key],value);arrays+=1
                        # Full physical reader arrays are retained before strict replay or transport can fail.
                        for key,value in original.items():
                            expected=value*d if (key.split('_',1)[-1] in STATE_FIELDS or key in ('kick_fields','kick_after')) else value
                            if value.dtype.kind in 'biu':np.testing.assert_array_equal(physical[key],expected,err_msg=key)
                            else:np.testing.assert_allclose(physical[key],expected,rtol=0,atol=2e-11,err_msg=key)
                        a=audit_read(physical_tape,record,physical,generation,birth);b=audit_read(source,canonical,original,generation,birth)
                        checked=dict(passed=True,physical=a,canonical=b,raw_sha256=checksum(path));save(out/'audits'/(prefix+'.json'),checked);audits.append(checked)
                        for mode,decoded in outputs.items():
                            for panel,indices in m.PANELS.items():
                                row=dict(block=block,route=route,birth=birth,generation=generation,mode=mode,panel=panel,
                                    reader=reader,**scores(decoded['values'][indices],source['responses_own'][indices],decoded['known'][indices]),
                                    calibration_events=2 if generation==0 or mode=='erased_reference_repair' else 0,
                                    measured_calibration_bits=96 if generation==0 or mode=='erased_reference_repair' else 0,
                                    inherited_calibration_signs=48 if generation and mode=='retained' else 0,
                                    observed_task_responses=8 if generation==0 or route=='rewrite' else 0)
                                # Independent literal score recount, including unresolved values.
                                hits=[sum(int(x)==int(y) for x,y in zip(decoded['values'][q],source['responses_own'][q])) for q in indices]
                                valid=[all(bool(v) for v in decoded['known'][q]) for q in indices]
                                assert row['query_correct']==sum(v and h>=44 for h,v in zip(hits,valid))
                                assert row['task_correct']==int(all(v and h>=44 for h,v in zip(hits,valid)))
                                if generation and mode=='erased_no_reference':
                                    assert row['unresolved_bits']==384 and row['task_correct']==row['query_correct']==0
                                else:assert row['unresolved_bits']==0
                                allrows.append(row)
                        np.testing.assert_array_equal(outputs['retained']['values'],outputs['erased_reference_repair']['values'])
                        prior_read=physical
            save(out/f'block_{block:03d}_scores.json',[r for r in allrows if r['block']==block])
            progress(completed_blocks=block+1)
        assert len(audits)==96 and len(allrows)==576
        summary=[]
        for route in ('rewrite','copy'):
            for mode in MODES:
                for g in range(3):
                    for panel in m.PANELS:
                        rows=[r for r in allrows if (r['route'],r['mode'],r['generation'],r['panel'])==(route,mode,g,panel)]
                        assert len(rows)==16
                        summary.append(dict(route=route,mode=mode,generation=g,panel=panel,networks=4,
                            **{k:sum(r[k] for r in rows) for k in ('tasks','task_correct','queries','query_correct','exact_queries','correct_bits','bits','unresolved_bits')}))
        for name in FILES:assert checksum(ROOT/name)==checksum(lane/name),name
        verify(out,'freeze.json');assert checksum(receipt)==config['qualification_receipt_sha256']
        result=dict(passed=True,completed_utc=utc(),classification='ENGINEERING_LEARNED_OUTPUT_CALIBRATION',networks=4,
            actual_handoffs_per_lineage=2,physical_lineages=32,actual_handoffs=64,physical_reads=96,canonical_control_reads=96,
            numerical_checks=sum(r[level]['checks'] for r in audits for level in ('physical','canonical')),
            maximum_field_error=max(r[level]['maximum_field_error'] for r in audits for level in ('physical','canonical')),
            maximum_pair_energy_error=max(r[level]['maximum_pair_energy_error'] for r in audits for level in ('physical','canonical')),
            minimum_boundary_distance=min(r[level]['minimum_boundary_distance'] for r in audits for level in ('physical','canonical')),
            maximum_record_transport_error=record_error,saved_arrays_reloaded=arrays,score_rows=len(allrows),
            information_checks=information,reference_commands_per_repair=2,measured_values_per_repair=96,learned_polarity_bits=48,
            no_reference_interpretation='UNIDENTIFIABLE_WITHIN_DECLARED_BOUNDARY',adaptive_copy_receives_identical_references=True,
            reference_repair_equals_retained_decoder=True,summary=summary,old_H097_files_unchanged=oldfiles,
            original_H097_acceptance='FAILED',H098_numerical_qualification_preserved=True,H095_retention_result_preserved=True,
            fresh_confirmation=False,comparative_superiority_qualified=False,calibration_affects_recurrent_dynamics=False,
            capacity_wait_seconds=admission['wait_seconds'],elapsed_seconds=time.perf_counter()-start,next_campaign_launched=False)
        save(out/'result.json',result);save(out/'scores.json',allrows)
        progress(state='COMPLETE',phase='complete',workers=0,passed=True);save(out/'COMPLETE.json',state)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json']);verify(out,'checksums.json')
        dest=lane/'.cache/h099_closeout_v1.json';assert not dest.exists()
        save(dest,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),
            numerical_checks=result['numerical_checks'],classification=result['classification'],actual_handoffs=64,next_campaign_launched=False))
    except BaseException:
        progress(state='FAILED',workers=0,error=traceback.format_exc());save(out/'FAILED.json',state);raise

def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name=='h099_reader_calibration_v1'
    assert not any(p.exists() for p in (out,out.with_suffix('.log'),out.with_suffix('.pid'),ROOT/'.cache/h099_closeout_v1.json'))
    assert len(FILES)==len(set(FILES));out.mkdir();(out/'inputs').mkdir()
    bindings=[]
    for block in range(4):
        tape=m.tapes('engineering',block);key=json.dumps([99099,'engineering_calibration',block],separators=(',',':')).encode()
        gen=np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))
        tape['calibration_polarity']=gen.choice([-1,1],size=48).astype(np.int8)
        path=out/'inputs'/f'engineering_{block:03d}.npz'
        with path.open('xb') as f:np.savez_compressed(f,**tape)
        bindings.append(dict(block=block,path=str(path),sha256=checksum(path),cohort='exposed H095 engineering'))
    for name in FILES:
        dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    save(out/'input_bindings.json',bindings)
    receipt=ROOT/'.cache/h098_completion_verification_v1.json';assert read(receipt)['passed']
    save(out/'config.json',dict(experiment='H099',classification='ENGINEERING_LEARNED_OUTPUT_CALIBRATION',created_utc=utc(),lane_root=str(ROOT),
        python=sys.version,numpy=np.__version__,calibration_seed=99099,networks=4,births=4,generations=3,
        reference_commands=2,measured_values_per_repair=96,learned_sign_bits=48,
        calibration_is_only_vulnerable_component=True,body_loss=False,physical_polarity_changes_between_bodies=False,
        original_H097_acceptance='FAILED',qualification_receipt_sha256=checksum(receipt),parent_manifest_pins=PINS,
        numerical_threshold=1e-12,exclusion_margin=5e-14,field_energy_tolerance=2e-11,record_tolerance=4e-14,
        workers=1,numerical_threads=1,forecast_active_seconds=300,main_cohort=False,next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h099/engineering.py'),'--execute',str(out)]
    with out.with_suffix('.log').open('xb') as log:proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,forecast_active_seconds=300)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',type=Path);mode.add_argument('--execute',type=Path);args=parser.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    else:run(args.execute.resolve())
