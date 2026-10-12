"""Qualification of changed cohort, paired scoring and scientific decisions."""
import copy
import numpy as np
import analysis
import cohort
import engine
import lineage_audit as la
import native
import reader
import report
import statistics_block as st
import support as s


def reject(call,label):
    try:call()
    except ValueError:return
    raise ValueError('Undetected deliberate corruption: '+label)


def synthetic(cfg,kind):
    panel={}
    for i,block in enumerate(cfg['blocks']):
        yes=np.zeros((16,4,8),bool);opposite=yes.copy();initial=np.ones(16,bool)
        if kind=='negative':
            initial[:2]=False;yes[2:,0]=True;yes[:2,1]=True
            # Favorable failing-body and shuffled contrasts cannot replace an unfavorable all-record effect.
            yes[2:2+i%3,1,:4]=True;opposite[2:4,2]=True
        elif kind=='positive':
            yes[:,1]=True;yes[:i%3,0,:2]=True;yes[:i%2,2,:2]=True
        elif kind=='empty':pass
        else:raise ValueError(kind)
        panel[block]=dict(intended=yes,opposite=opposite,initial_pass=initial)
    return panel


def run(output):
    cfg=s.config();source=s.verify_sources();s.require(len(cfg['blocks'])==64 and len(set(cfg['blocks']))==64,'Fixed unique cohort')
    s.require(cfg['history_by_block']=={str(b):i%4 for i,b in enumerate(cfg['blocks'])},'Balanced histories')
    s.require(cfg['excluded_fixture'] not in cfg['blocks'],'Fixture excluded')
    s.require(cfg['primary_margins']==dict(recipient_minus_outgoing=.02,recipient_minus_shuffled=.05),'Frozen practical thresholds')
    for name in ['native.py','repair.py','optimizer.py']:
        s.require(s.sha(s.HERE/name)==s.read(s.HERE/'source/tt013/job.json')['inputs_sha256'][name],'Unchanged audited repair implementation')
    for name,old in [('lineage.py','native.py'),('lineage_audit.py','auditor.py')]:
        s.require(s.sha(s.HERE/name)==s.read(s.HERE/'source/tt008/job.json')['inputs_sha256'][old],'Unchanged audited lineage implementation')
    s.require(cohort.writer_code(14,0,cfg)==cohort.writer_code(14,1,cfg)==cohort.writer_code(14,2,cfg)==cohort.writer_code(14,3,cfg)==0,'Exact generation-14 writer')
    for h in range(4):s.require([g for g in range(1,15) if cohort.writer_code(g,h,cfg)]==cfg['tolerance_generations'][h],'Entire writer schedule')
    reject(lambda:cohort.identity(cfg['excluded_fixture'],cfg),'Fixture admission')
    reject(lambda:cohort.identity(81000,cfg),'Previously exposed admission')
    # Full data shape, short excluded dynamics, with exact implementation replay.
    small=copy.deepcopy(cfg);small['native_config'].update(teach_steps=12,capture_steps=6)
    small['native_cycle'].update(read_steps=48,settling_steps=24)
    seed=cfg['lineage_namespace']+':fixture';teach,first=engine.teaching(seed,small)
    packets=np.repeat(teach['acquired'][:,None],4,axis=1)[None];receipts=[first]
    for h in [0,2]:
        raw,receipt=engine.rebuild(packets,seed,13,h,small);receipts.append(receipt)
        bad={k:v.copy() for k,v in raw.items()};bad['outgoing'].flat[0]^=1
        reject(lambda:la.equal(bad,raw,'corrupted handoff'),'Corrupt native output')
    prepared,resources=cohort.construct(raw['outgoing'].reshape(16,4096),cfg['excluded_fixture'],2,cfg)
    s.require(np.all(prepared['masks'].sum(axis=(2,3))==24),'All fresh injuries')
    s.equal(prepared['masks'][0],prepared['masks'][4],'Native paired-founder masks')
    other,_=cohort.construct(raw['outgoing'].reshape(16,4096),cfg['excluded_fixture'],3,cfg)
    s.equal(prepared['packets'][:,1],other['packets'][:,1],'History label does not enter primary repair')
    zero,_=cohort.construct(np.zeros((16,4096),np.uint8),cfg['excluded_fixture'],0,cfg)
    s.require(not zero['packets'].any() and not zero['shuffled_sign_changes'].any(),'Zero input and unchanged shuffle retained')
    short=copy.deepcopy(cfg);short['budgets']=[64];short['settling_steps']=32
    raw,receipt=engine.assessment(prepared,cfg['excluded_fixture'],short);receipts.append(receipt)
    scored,error,distance=analysis.scalar_score(raw,prepared['founders'])
    damaged={k:v.copy() for k,v in raw.items()};damaged['both_pass'][0,0,0,0]^=True
    reject(lambda:analysis.scalar_score(damaged,prepared['founders']),'Altered success flag')
    thresholds=0
    for founder in range(4):
        for magnitude in [np.nextafter(.25,0),.25,np.nextafter(.25,1)]:
            for sign in [-1,1]:
                mean=(1 if founder%2==0 else -1)*sign*magnitude*np.array([[1.,-1.],[-1.,1.]])
                flags=reader.scores(mean.reshape(1,1,1,1,2,2),np.array([founder]),.25)
                s.require(bool(flags['both_pass'].item())==(magnitude>.25 and sign==1),'Strict threshold');thresholds+=1
    results={}
    for kind in ['negative','positive','empty']:
        result,rows,counts=analysis.summarize(synthetic(cfg,kind),cfg);results[kind]=result
        for name,c in counts.items():st.audit_bounds(np.array(c),cfg['primary_margins'][name],result['primary_effects'][name])
    failed=results['negative'];s.require(not failed['conjunction_pass'] and failed['primary_effects']['recipient_minus_outgoing']['mean']<0,'Negative primary retained')
    sub=failed['pre_repair_subgroups']['initially_failing']['rates']
    s.require(sub['recipient_completion']['intended_rate']==1 and sub['outgoing']['intended_rate']==0,'Favorable failed-body secondary is real')
    s.require('PRACTICAL_SUPERIORITY_UNSUPPORTED' in report.render(failed),'Failed conjunction reported')
    s.require(results['positive']['conjunction_pass'],'Positive practical gates')
    s.require(not results['empty']['conjunction_pass'] and results['empty']['primary_effects']['recipient_minus_outgoing']['method']=='Hoeffding zero-variance fallback','Zero variance gives no false precision')
    s.require(results['empty']['pre_repair_subgroups']['initially_failing']['records']==0 and results['empty']['pre_repair_subgroups']['initially_failing']['rates']['outgoing']['intended_rate'] is None,'Empty strata explicit')
    e=copy.deepcopy(results['positive']['primary_effects']['recipient_minus_outgoing']);e['lower_one_sided95']+=.1
    counts=analysis.summarize(synthetic(cfg,'positive'),cfg)[2]['recipient_minus_outgoing']
    reject(lambda:st.audit_bounds(np.array(counts),.02,e),'Corrupted confidence bound')
    omitted=synthetic(cfg,'negative');del omitted[cfg['blocks'][0]]
    reject(lambda:analysis.summarize(omitted,cfg),'Excluded block')
    s.dump(output/'synthetic_negative_analysis.json',failed)
    with (output/'synthetic_negative_report.md').open('x') as f:f.write('SYNTHETIC QUALIFICATION ONLY\n\n'+report.render(failed))
    result=dict(status='PASS',source_files_verified=len(source['files_sha256']),unchanged_prior_qualifications_reused=True,
        short_native_replay_receipts=receipts,strict_threshold_fixtures=thresholds,history_invariance=True,
        all_zero_and_unchanged_shuffle_retained=True,negative_primary_favorable_subgroup=True,
        independent_interval_and_bootstrap_checks=True,positive_and_zero_variance_decisions=True,empty_subgroups=True,
        invalid_enrollment_rejections=3,corrupt_native_rejections=2,corrupt_score_and_interval_rejections=2,
        synthetic_window_error=error,new_test_outcomes_generated=False)
    s.dump(output/'TECHNICAL_CHECKS.json',result);return result
