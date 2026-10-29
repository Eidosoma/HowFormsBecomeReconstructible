"""Bounded, excluded qualification; no proposed acquisition identity is generated."""
import hashlib
import time
import numpy as np
import analysis
import core
import current_repair
import engine
import record_features
import report
import roll_dynamics as d
import serial
import serial_audit as audit
import support as s


class LegacyDraws:
    """Archived imposed inputs for regression, never available to scientific runs."""
    def __init__(self,cfg):
        prior=s.read(s.HERE/'source/design_reference/tt016_plan.json')
        identity=prior['continuation_namespace']+':16000000'
        self.base=d.stream('E022',identity,'develop',15)
        self.innovation=d.stream(prior['innovation_namespace'],identity,'innovation',15)
        self.masks=d.damage_masks(identity,'E022_renewal_g15',4)[:,:,1].reshape(16,16,16)
        self.birth=(cfg['birth_sd']*d.matched_cues(self.base.standard_normal((2,4,16,16)))).reshape(16,2,16,16)
        self.innovation.standard_normal((2,4,16,16))
        self.steps=0;self.digest=hashlib.sha256();self.moments=np.zeros((16,6))
        self.keys=np.full((16,5),'ARCHIVED_IMPOSED_INPUTS',dtype='U64')

    def noise(self):
        first=d.paired_founders(self.base.standard_normal((2,4,16,16)))
        second=d.paired_founders(self.innovation.standard_normal((2,4,16,16)))
        a=np.stack((first,second),axis=2).reshape(16,2,16,16);x,y=a[:,0],a[:,1]
        self.moments+=np.stack([x.sum(axis=(1,2)),y.sum(axis=(1,2)),(x*x).sum(axis=(1,2)),
            (y*y).sum(axis=(1,2)),(x*y).sum(axis=(1,2)),np.full(16,256.)],axis=1)
        self.digest.update(a.tobytes());self.steps+=1
        return a

    evidence=serial.Draws.evidence


def rejects(operation,label):
    try:operation()
    except (ValueError,AssertionError):return label
    raise ValueError('Corruption was not rejected: '+label)


def technical(output,cfg):
    checks=[];identity=cfg['excluded_namespace']+':allocation'
    dc=cfg['development_config'];cycle=dict(read_steps=64,settling_steps=32)
    packet=s.arrays(s.HERE/'source/known/tt016_enrollment.npz')['initial_packets'][0]
    incoming=np.broadcast_to(packet,(3,2,4096)).copy()
    raw=serial.read_packets(incoming,serial.Draws(identity,[0,1],15,dc),dc,cycle)
    expected=audit.read_packets(incoming,audit.Draws(identity,[0,1],15,dc),dc,cycle)
    audit.compare(raw,expected,'Short synthetic allocation regression')
    for future in (0,1):
        one=serial.read_packets(incoming[:,future:future+1],serial.Draws(identity,[future],15,dc),dc,cycle)
        for key in ('end','outgoing','mean_ports','available_edges','fallback_edges'):
            s.equal(one[key][:,0],raw[key][:,future],'Batch partition invariant '+key)
        s.equal(one['port_windows'][:,:,0],raw['port_windows'][:,:,future],'Batch invariant windows')
        for key in ('masks','birth','noise_moments','seed_keys'):
            s.equal(one[key][0],raw[key][future],'Batch invariant streams '+key)
    checks.append('Batch partition preserves exact per-future states, windows, packets and random sources')
    for key in ('end','outgoing','mean_ports'):
        s.equal(raw[key][0],raw[key][1],'Shared policy draws '+key)
    s.require(not np.array_equal(raw['birth'][0,0],raw['birth'][0,1]),'Distinct cue resets')
    s.require(not np.array_equal(raw['birth'][0],raw['birth'][1]),'Distinct future resets')
    terminal=serial.Draws(identity,[0,1],32,dc,True)
    regular=serial.Draws(identity,[0,1],32,dc)
    s.require(set(np.array(terminal.keys).ravel()).isdisjoint(np.array(regular.keys).ravel()),'Terminal source separation')
    checks.append('Direct policy pairing and distinct cue/future/terminal draws')
    for field in ('birth','masks','end','outgoing','noise_moments','seed_keys'):
        corrupt={k:v.copy() for k,v in raw.items()}
        a=corrupt[field]
        if a.dtype.kind=='b':a.flat[0]=not a.flat[0]
        elif a.dtype.kind=='U':a.flat[0]='CORRUPTED'
        elif a.dtype.kind=='f':a.flat[0]=np.nextafter(a.flat[0],np.inf)
        else:a.flat[0]^=1
        checks.append(rejects(lambda:audit.compare(corrupt,expected,field),'Corrupt '+field))
    checks.append(rejects(lambda:engine.handoff(raw['outgoing'][::-1].copy()^1,raw['outgoing']),'Corrupt successor'))
    target=np.array([[1.,-1.],[-1.,1.]])
    for margin in (np.nextafter(.25,0.),.25,np.nextafter(.25,1.)):
        means=np.broadcast_to(margin*target,(3,2,2,2)).copy()
        scored=serial.score(means,np.ones(2));s.require(np.all(scored['both_pass']==(margin>.25)),'Strict native threshold')
        audit.score(dict(mean_ports=means,port_windows=np.repeat(means[None],32,axis=0)),np.ones(2),scored)
    checks.append('Strict > .25 at exact threshold and adjacent binary64 values')
    checks.append(rejects(lambda:serial.score(np.full((3,2,2,2),np.nan),np.ones(2)),'Nonfinite scores'))
    checks.append(rejects(lambda:serial.Draws(identity,[0,0],15,dc),'Duplicate future identity'))
    zeros=np.zeros((3,1,4096),np.uint8)
    fixed,details=current_repair.prepare(zeros,15,cfg['optimizer']);s.equal(fixed,zeros,'Empty record remains empty')
    s.require(int(details['added_edges'].sum())==0 and int(details['independent_optimizer_checks'])==2,'Empty record full optimizer audit')
    checks.append('Empty record and exact repair schedule')
    # A later favorable body endpoint cannot rescue a negative fresh-record primary.
    rng=np.random.default_rng(2026101218)
    body=np.ones((64,64,3,18),bool);body[:,:,0,0]=False
    terminal=rng.random((64,64,3))<np.array([.85,.6,.3])
    panel=dict(body_success=body,terminal_success=terminal,body_opposite=np.zeros_like(body),terminal_opposite=np.zeros_like(terminal),
        repair_calls=np.broadcast_to(np.array([0,1,18]),(64,64,3)).copy())
    for key in ('added_edges','added_abs_weight','repair_cpu_seconds','audit_cpu_seconds'):panel[key]=np.zeros((64,64,3))
    rows=[dict(index=i,history_index=i%4,case=i//4,current_pass=i%2,record_id='SYNTHETIC:'+str(i)) for i in range(64)]
    forecasts=[dict(candidate=.8,expression_history=.6,expression_unsigned=.5) for _ in rows]
    result=analysis.summarize(panel,rows,forecasts,cfg)
    s.require(result['primary']['verdict']=='UNSUPPORTED' and result['population']['uninterrupted']['repeated_minus_untreated']['verdict']=='PASS','Endpoint-specific primary gate')
    s.require(result['independent_population_units']==64 and len(result['states'])==384,'State uncertainty family and independent units')
    s.require(result['split_halves']['uninterrupted/untreated']['overall_correlation'] is None,'Undefined split correlation retained')
    s.dump(output/'SYNTHETIC_ANALYSIS.json',result)
    report.run(output,result)
    (output/'REPORT.md').rename(output/'SYNTHETIC_REPORT.md')
    checks.append('Negative primary retained despite favorable body secondary; report renders separate endpoints')
    checks.append(rejects(lambda:analysis.summarize({**panel,'terminal_success':terminal[:63]},rows,forecasts,cfg),'Missing record'))
    import run as execution
    checks.append(rejects(lambda:execution.preflight('validation','unused'),'Unregistered scientific launch'))
    s.dump(output/'TECHNICAL_CHECKS.json',dict(status='PASS',checks=checks,classification='EXCLUDED_TECHNICAL_FIXTURES',
        synthetic_report_is_not_scientific_evidence=True,serial_steps_for_allocation_test=64))
    return checks


def run(output,cfg,progress):
    timings={};receipts={};sizes={};progress('technical_contract_checks')
    checks=technical(output,cfg)
    progress('archived_teaching_full_replay');start=time.monotonic()
    raw,receipts['teaching']=engine.teaching(34000,cfg)
    core.equal(raw,s.arrays(s.HERE/'source/known/teaching.npz'),'Archived teaching')
    s.save(output/'known_teaching.npz',raw)
    timings['teaching']=time.monotonic()-start;sizes['teaching']=(output/'known_teaching.npz').stat().st_size
    durations=[];bytesizes=[]
    for generation,history,slot in ((13,0,0),(13,2,1),(14,2,1)):
        progress('archived_preliminary_full_replay',generation=generation,history=history)
        before=s.arrays(s.HERE/f'source/known/g{generation-1}.npz');known=s.arrays(s.HERE/f'source/known/g{generation}.npz')
        start=time.monotonic();packets=before['outgoing'][slot:slot+1]
        raw,receipt=engine.preliminary(packets,34000,generation,history,cfg)
        expected={k:known[k] if k in ('masks','birth') else known[k][slot:slot+1] for k in raw}
        core.equal(raw,expected,'Archived exact/tolerance/post-pulse writer')
        name=f'known_g{generation}_h{history}.npz';s.save(output/name,dict(incoming=packets,**raw))
        durations.append(time.monotonic()-start);bytesizes.append((output/name).stat().st_size);receipts[name]=receipt
    timings['preliminary']=durations;sizes['preliminary']=max(bytesizes)
    progress('new_feature_extraction_against_archived_boundaries')
    known=s.arrays(s.HERE/'source/known/g14.npz');error=0.;feature_rows=[];start=time.monotonic()
    for history,slot in ((0,0),(2,1),(3,2)):
        for case in range(16):
            packet=known['outgoing'][slot].reshape(16,4096)[case];means=known['mean_ports'][slot].reshape(16,2,2)[case]
            row,pred,receipt=record_features.boundary(packet,means,history,case,cfg,cfg['excluded_namespace']+':features:'+str(history)+':'+str(case))
            expected=[known[name][slot].ravel()[case] for name in ('signed_transfer','unsigned_access')]
            error=max(error,s.close([row['signed_transfer'],row['unsigned_access']],expected,2e-13,'Archived TT008 transfer channels'))
            feature_rows.append(dict(**row,**pred))
    timings['features_48']=time.monotonic()-start
    s.csv_write(output/'archived_features.csv',feature_rows)
    receipts['features']=dict(status='PASS',records=48,maximum_error=error)
    progress('three_policy_kernel_against_archived_tt016')
    start=time.monotonic();known=s.arrays(s.HERE/'source/known/tt016_g15.npz');prepared=known['prepared'][4:7]
    raw=serial.read_packets(prepared,LegacyDraws(cfg['development_config']),cfg['development_config'],cfg['cycle'])
    ref=audit.read_packets(prepared,LegacyDraws(cfg['development_config']),cfg['development_config'],cfg['cycle'])
    receipts['legacy']=audit.compare(raw,ref,'Independent flat replay with archived imposed inputs')
    for key in ('end','outgoing','mean_ports','available_edges','fallback_edges'):s.equal(raw[key],known[key][4:7],'Archived three-policy '+key)
    for key in ('masks','birth'):s.equal(raw[key],known[key],'Archived reader '+key)
    s.equal(raw['port_windows'],known['port_windows'][:,4:7],'Archived observation windows')
    s.save(output/'archived_three_policy.npz',raw);timings['archived_three_policy']=time.monotonic()-start
    # Full-size benchmark with 16 independent futures restored from one exposed packet.
    packet=s.arrays(s.HERE/'source/known/tt016_enrollment.npz')['initial_packets'][0]
    identity=cfg['excluded_namespace']+':full_batch';incoming=np.broadcast_to(packet,(3,16,4096)).copy()
    durations=[];bytesizes=[]
    for generation in (15,16):
        progress('full_size_independent_future_benchmark',generation=generation)
        start=time.monotonic();prepared,details=current_repair.prepare(incoming,generation,cfg['optimizer'])
        raw,receipt=engine.checked_read(prepared,identity,range(16),generation,1,cfg)
        if generation==15:engine.first_step(prepared,raw)
        name=f'full_batch_g{generation}.npz';s.save(output/name,dict(incoming=incoming,prepared=prepared,**details,**raw))
        durations.append(time.monotonic()-start);bytesizes.append((output/name).stat().st_size);receipts[name]=receipt
        incoming=raw['outgoing']
    timings['full_size_continuation_with_repairs']=durations;sizes['continuation']=max(bytesizes)
    progress('full_size_fresh_terminal_benchmark');start=time.monotonic()
    raw,receipts['terminal']=engine.checked_read(incoming,identity,range(16),32,1,cfg,terminal=True)
    s.save(output/'full_batch_terminal.npz',dict(incoming=incoming,**raw))
    timings['full_size_terminal']=time.monotonic()-start;sizes['terminal']=(output/'full_batch_terminal.npz').stat().st_size
    # Use the production batch orchestrator for an entire 18-generation chain.
    start=time.monotonic();identity=cfg['excluded_namespace']+':complete_chain'
    panel=engine.batch(output/'complete_chain',packet,identity,[0,1],1,cfg,progress)
    audited,scope=analysis.verify_batch(output/'complete_chain',packet,identity,[0,1],1,cfg)
    for key in panel:s.equal(panel[key],audited[key],'End-to-end retained panel')
    s.require(scope['continuation_contexts']==108 and scope['terminal_contexts']==6 and scope['optimizer_checks']==38,'Full-chain integration scope')
    timings['complete_chain_and_retained_audit']=time.monotonic()-start
    receipts['complete_chain']=dict(status='PASS',**scope,all_generations_retained=True,
        failed_body_readouts=int((~panel['body_success']).sum()))
    progress('guaranteed_failed_body_continuation_fixture')
    short=dict(cfg,cycle=dict(read_steps=64,settling_steps=32),
        development_config=dict(cfg['development_config'],noise=0.,birth_sd=0.))
    zero_panel=engine.batch(output/'zero_noise_failure_fixture',np.zeros(4096,np.uint8),
        cfg['excluded_namespace']+':zero_noise_failure',[0],1,short,progress)
    s.require(not zero_panel['body_success'].any() and not zero_panel['terminal_success'].any(),'Guaranteed failed-body fixture')
    s.equal(zero_panel['repair_calls'],np.array([[0,1,18]]),'All repairs and successors retained after failure')
    receipts['guaranteed_failed_continuation']=dict(status='PASS',failed_body_readouts=54,
        classified_synthetic=True,reader_steps=64,noise=0.,birth_sd=0.)
    # File commitment, successor, and endpoint tampering are separately rejected.
    corrupt=panel['futures'].copy();corrupt[1]=0
    checks.append(rejects(lambda:s.equal(corrupt,np.arange(2),'Coverage'),'Repeated future in saved panel'))
    forecast=1.5*(64*(timings['teaching']+14*max(timings['preliminary'])+timings['features_48']/48)
        +256*(18*max(durations)+timings['full_size_terminal']))+900
    retained=2*(64*(sizes['teaching']+14*sizes['preliminary']+2097152)
        +256*(18*sizes['continuation']+sizes['terminal']))
    result=dict(status='PASS',classification='ARCHIVED_AND_EXCLUDED_TECHNICAL_QUALIFICATION',
        new_scientific_cohort=False,new_acquisition_blocks_generated=0,proposed_cohort_identities_used=False,
        timings_seconds=timings,forecast_seconds=forecast,maximum_forecast_seconds=cfg['maximum_forecast_seconds'],
        capacity_pass=forecast<cfg['maximum_forecast_seconds'],retained_evidence_forecast_bytes=retained,
        receipts=receipts,checks=checks,full_native_reader_steps=2048,short_synthetic_allocation_reader_steps=64,
        remaining_registration_prerequisites=['TT017 closeout review','identity reservation','final protocol registration'])
    s.dump(output/'qualification.json',result)
    s.require(result['capacity_pass'],'Measured full-work forecast exceeds unchanged 48-hour ceiling')
    return result
