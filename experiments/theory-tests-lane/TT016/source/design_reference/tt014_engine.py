"""Every prospective trajectory receives a separate full native replay."""
import time
import numpy as np
import analysis
import cohort
import lineage
import lineage_audit as la
import native as flat
import reader
import support as s


def teaching(seed,cfg):
    raw=lineage.teaching(seed,cfg['native_config']);receipt=la.equal(raw,la.teaching(seed,cfg['native_config']),'teaching')
    return raw,receipt


def rebuild(packets,seed,generation,h,cfg):
    code=[cohort.writer_code(generation,h,cfg)]
    args=(packets,seed,generation,code,cfg['native_config'],cfg['native_cycle'],cfg['tolerance'])
    raw=lineage.rebuild(*args);receipt=la.equal(raw,la.rebuild(*args),f'g{generation}')
    receipt.update(generation=generation,writer_code=code[0]);return raw,receipt


def assessment(prepared,block,cfg,progress=None):
    packets=prepared['packets'];masks=prepared['masks'];founders=prepared['founders'];recipients=prepared['recipients']
    raw=reader.read_fixed(packets,masks,founders,recipients,reader.generators(cfg,block,cfg['replicates']),cfg['reader'],cfg['budgets'],cfg['settling_steps'])
    if progress:progress('independent_assessment_replay',block=block)
    reference=flat.read_packets(packets,masks,founders,recipients,cfg,block,cfg['replicates'],cfg['budgets'],progress=(lambda step:progress('independent_assessment_replay',block=block,step=step)) if progress else None)
    receipt=la.equal(raw,reference,'all_assessment_contexts')
    intended=reader.scores(raw['mean_ports'],founders,.25);opposite=reader.scores(raw['mean_ports'],founders^1,.25)
    for data,target in [(intended,flat.scores(reference['mean_ports'],founders)),(opposite,flat.scores(reference['mean_ports'],founders^1))]:
        s.equal(data['both_pass'],target['both_pass'],'Strict native flags');s.close(data['min_margin'],target['min_margin'],1e-12,'Native margins')
    raw.update(min_margin=intended['min_margin'],both_pass=intended['both_pass'],opposite_margin=opposite['min_margin'],opposite_pass=opposite['both_pass'])
    receipt.update(contexts=512);return raw,receipt


def initial_pass(mean_ports):
    means=mean_ports.reshape(16,2,2);founders=np.repeat(np.arange(4),4)
    return reader.scores(means[None,:,None,None],founders,.25)['both_pass'].reshape(16)


def benchmark(output,cfg,progress):
    timings={};receipts={};files={};progress('benchmark_known_teaching');start=time.monotonic()
    teach,receipts['teaching']=teaching(34000,cfg);la.equal(teach,s.arrays(s.HERE/'source/known/teaching.npz'),'retained_teaching')
    timings['teaching']=time.monotonic()-start;s.save(output/'known_teaching.npz',teach);files['teaching']=(output/'known_teaching.npz').stat().st_size
    renewals=[];sizes=[]
    # Exact and tolerance writer at generation 13, then the exact post-pulse writer.
    for generation,h,slot in [(13,0,0),(13,2,1),(14,2,1)]:
        before=s.arrays(s.HERE/f'source/known/g{generation-1}.npz');known=s.arrays(s.HERE/f'source/known/g{generation}.npz')
        packets=before['outgoing'][slot:slot+1];progress('benchmark_known_rebuild',generation=generation,history=h);start=time.monotonic()
        raw,receipt=rebuild(packets,34000,generation,h,cfg)
        expected={k:known[k] if k in ['birth','masks'] else known[k][slot:slot+1] for k in raw};la.equal(raw,expected,'retained_boundary')
        renewals.append(time.monotonic()-start);name=f'known_g{generation}_h{h}.npz';s.save(output/name,dict(incoming=packets,**raw));sizes.append((output/name).stat().st_size)
        receipts[name]=receipt
    timings['rebuild_max']=max(renewals);timings['rebuilds']=renewals
    known=s.arrays(s.HERE/'source/known/g14.npz');block=cfg['excluded_fixture'];progress('benchmark_checked_repairs');start=time.monotonic()
    prepared,resources=cohort.construct(known['outgoing'][0].reshape(16,4096),block,0,cfg)
    prepared['initial_pass']=initial_pass(known['mean_ports'][0]);timings['sixteen_repairs']=time.monotonic()-start
    s.save(output/'prepared.npz',prepared);s.csv_write(output/'resources.csv',resources)
    progress('benchmark_full_assessment');start=time.monotonic();raw,receipts['assessment']=assessment(prepared,block,cfg,progress)
    timings['assessment']=time.monotonic()-start;s.save(output/'assessment.npz',raw);analysis.scalar_score(raw,prepared['founders'])
    forecast=1.5*64*(timings['teaching']+14*timings['rebuild_max']+timings['assessment']+timings['sixteen_repairs'])+300
    retained=2*64*(files['teaching']+14*max(sizes)+(output/'prepared.npz').stat().st_size+(output/'assessment.npz').stat().st_size+131072)
    result=dict(status='PASS',classification='EXCLUDED_KNOWN_RECORDS_NO_TEST_COHORT',timings_seconds=timings,forecast_seconds=forecast,
        retained_evidence_forecast_bytes=retained,capacity_pass=forecast<cfg['maximum_forecast_seconds'],maximum_seconds=cfg['maximum_forecast_seconds'],
        receipts=receipts,native_assessment_contexts=512,known_rebuild_contexts=48,optimizer_problems=16,blocks_generated=0,new_test_outcomes_generated=False)
    s.dump(output/'benchmark.json',result);s.require(result['capacity_pass'],'Forecast exceeds frozen ceiling');return result


def validate(output,cfg,progress):
    registration=s.read(s.HERE/'REGISTRATION.json');s.require(registration['plan_sha256']==s.sha(s.HERE/'plan.json'),'Frozen prospective plan')
    receipts=[];folder_root=output/'blocks';folder_root.mkdir(exist_ok=False)
    for block in cfg['blocks']:
        folder=folder_root/str(block);folder.mkdir(exist_ok=False);seed=cohort.identity(block,cfg);h=cohort.history(block,cfg)
        progress('teaching',block=block);t=time.monotonic();teach,teach_receipt=teaching(seed,cfg);s.save(folder/'teaching.npz',teach)
        packets=np.repeat(teach['acquired'][:,None],4,axis=1)[None];renewals=[]
        for generation in range(1,15):
            progress('lineage_rebuild_and_replay',block=block,generation=generation)
            raw,receipt=rebuild(packets,seed,generation,h,cfg)
            name=f'generation_{generation:02d}.npz';s.save(folder/name,dict(incoming=packets,generation=np.array(generation),history=np.array(h),**raw))
            receipt.update(file=name,file_sha256=s.sha(folder/name));renewals.append(receipt);packets=raw['outgoing']
        progress('checked_repairs',block=block);prepared,resources=cohort.construct(packets.reshape(16,4096),block,h,cfg)
        prepared['initial_pass']=initial_pass(raw['mean_ports']);s.save(folder/'prepared.npz',prepared);s.csv_write(folder/'resources.csv',resources)
        s.dump(folder/'ENROLLMENT_SEAL.json',dict(utc=s.utc(),block=block,history=h,records=16,
            registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),boundary_sha256=s.sha(folder/'generation_14.npz'),
            prepared_sha256=s.sha(folder/'prepared.npz'),outgoing_sha256=s.descriptor(packets.reshape(16,4096))['sha256']))
        progress('fresh_assessment',block=block);s.dump(folder/'ASSESSMENT_STARTED.json',dict(utc=s.utc(),block=block,seal_sha256=s.sha(folder/'ENROLLMENT_SEAL.json')))
        raw,assay_receipt=assessment(prepared,block,cfg,progress);s.save(folder/'assessment.npz',raw)
        analysis.scalar_score(raw,prepared['founders'])
        receipt=dict(status='PASS',block=block,history=h,teaching=teach_receipt,rebuilds=renewals,assessment=assay_receipt,
            optimizer_checks=16,records=64,rebuild_contexts=224,assessment_contexts=512,seconds=time.monotonic()-t)
        s.dump(folder/'REPLAY_AUDIT.json',receipt);receipts.append(receipt)
    s.require(len(receipts)==64 and sum(x['rebuild_contexts'] for x in receipts)==14336 and sum(x['assessment_contexts'] for x in receipts)==32768,'Full fixed simulation scope')
    s.dump(output/'NATIVE_AUDIT.json',dict(status='PASS',blocks=64,teaching_replays=64,rebuild_contexts=14336,assessment_contexts=32768,
        optimizer_checks=1024,constructed_records=4096,all_native_states_byte_exact=True,automatic_successor=False))
    progress('complete_independent_scoring');result=analysis.run(output,cfg)
    import report
    return report.run(output,result)
