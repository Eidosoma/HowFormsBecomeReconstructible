"""Benchmark and full independent replay of both completed continuation studies."""
import time
import numpy as np
import checks
import dynamics as dyn
import intake
import provenance
import scoring
import support as s

def configs():return {label:intake.config(label) for label in ('serial','noise')}

def read_union(a,b,block,gi,cfg):
    expected=dyn.union(a,b,gi)
    packets=np.concatenate((a['prepared'][gi],b['prepared'][gi,2:]),axis=0)
    g=int(cfg['generations'][gi]);start=time.monotonic()
    actual=dyn.replay(packets,cfg['continuation_namespace']+':'+str(block),g,cfg,[1.,1.,1.,1.,.999,.999,0.,0.])
    receipt=dyn.compare(actual,expected,dyn.FIELDS,f'{block}/g{g}/all_eight_distinct_arms')
    error=float(np.max(abs(actual['noise_moments']-b['noise_moments'][gi])))
    s.require(np.allclose(actual['noise_moments'],b['noise_moments'][gi],rtol=1e-13,atol=1e-8),'Independent full forcing moments')
    s.equal(actual['noise_moments'][:,5],np.full(3,cfg['cycle']['read_steps']*2048,dtype=float),'Noise counted once per founder family')
    receipt.update(generation=g,unique_contexts=128,source_contexts=160,matched_overlap=32,
                   noise_moment_max_error=error,noise_moments_sha256=s.descriptor(actual['noise_moments'])['sha256'],
                   seconds=time.monotonic()-start)
    return receipt

def full_scoring(output,cfgs):
    receipts={};results={}
    for label in ('serial','noise'):
        panel={b:intake.load(label,b) for b in cfgs[label]['blocks']}
        result,receipt=scoring.analyze(panel,cfgs[label],label)
        s.dump(output/(label+'_analysis.json'),result);results[label]=result;receipts[label]=receipt
    total=dict(status='PASS',studies=receipts,raw_endpoints=sum(x['raw_endpoints'] for x in receipts.values()),
               dual_task_flags=sum(x['dual_task_flags'] for x in receipts.values()),new_scientific_cohort=False,
               duplicated_matched_endpoints=9216,independent_blocks=16)
    s.require(total['raw_endpoints']==46080 and total['dual_task_flags']==92160,'All source endpoints scored')
    s.dump(output/'SCORING_AUDIT.json',total);return results

def benchmark(output,cfg,progress):
    cfgs=configs();timings={};progress('source_provenance')
    t=time.monotonic();s.dump(output/'PROVENANCE_AUDIT.json',provenance.run());boundary=intake.boundaries();timings['provenance']=time.monotonic()-t
    progress('changed_code_qualification');checks.run(output,cfgs)
    known=s.arrays(s.HERE/'source/serial/inputs/sources/native_controls.npz')
    packets=np.repeat(known['incoming'],4,axis=0).reshape(4,16,4096)
    progress('known_native_archive');t=time.monotonic();observed=dyn.replay(packets,34000,14,cfgs['serial'])
    expected={}
    for k in ('masks','birth'):expected[k]=known[k].reshape(observed[k].shape)
    for k in ('end','outgoing','mean_ports'):expected[k]=np.repeat(known[k],4,axis=0).reshape(observed[k].shape)
    known_receipt=dyn.compare(observed,expected,tuple(expected),'known_34000_g14_four_branches');timings['known']=time.monotonic()-t
    block=81000;a=intake.load('serial',block);b=intake.load('noise',block)
    intake.structural(a,b,block,boundary['initial_packets'][0],boundary['previous_masks'][0],cfgs)
    progress('all_repairs_first_block');t=time.monotonic();optimizers=0;records=0;error=0.
    for label,d in [('serial',a),('noise',b)]:
        for gi in range(18):
            r=intake.check_generation(d,label,block,gi,cfgs[label]);optimizers+=r['optimizer_checks'];records+=r['construction_checks'];error=max(error,r['resource_max_error'])
    timings['whole_block_construction']=time.monotonic()-t;s.require(optimizers==1456 and records==2880,'Complete benchmark construction block')
    receipts=[]
    for gi in (0,17):
        progress('full_shape_replay_benchmark',generation=gi+15);receipts.append(read_union(a,b,block,gi,cfgs['noise']))
    timings['maximum_generation_replay']=max(x['seconds'] for x in receipts)
    progress('all_source_scoring_and_intervals');t=time.monotonic();full_scoring(output,cfgs);timings['all_scoring']=time.monotonic()-t
    forecast=1.5*16*(timings['whole_block_construction']+18*timings['maximum_generation_replay'])+timings['provenance']+timings['all_scoring']+300
    result=dict(status='PASS',timings_seconds=timings,forecast_seconds=forecast,maximum_seconds=cfg['maximum_forecast_seconds'],
                capacity_pass=forecast<cfg['maximum_forecast_seconds'],known_receipt=known_receipt,known_contexts=64,
                replay_receipts=receipts,unique_continuation_contexts=256,optimizer_checks=optimizers,constructed_records=records,
                resource_max_error=error,all_source_scoring_passed=True,full_native_replay_performed=False,new_scientific_cohort=False)
    s.dump(output/'benchmark.json',result);s.require(result['capacity_pass'],'Full audit exceeds frozen budget; preserve benchmark')
    return result

def audit(output,cfg,progress,benchmark):
    cfgs=configs();boundary=intake.boundaries()
    for name in ('TECHNICAL_CHECKS.json','PROVENANCE_AUDIT.json','SCORING_AUDIT.json','serial_analysis.json','noise_analysis.json'):
        with (output/name).open('xb') as f:f.write((benchmark/name).read_bytes())
    totals=dict(optimizer_checks=0,constructed_records=0,unique_contexts=0,source_contexts=0,matched_overlap=0,native_array_comparisons=0)
    max_error=0.;max_noise_error=0.
    for bi,block in enumerate(cfgs['serial']['blocks']):
        progress('block_enrollment_and_handoffs',block=block)
        a=intake.load('serial',block);b=intake.load('noise',block)
        structural=intake.structural(a,b,block,boundary['initial_packets'][bi],boundary['previous_masks'][bi],cfgs)
        records=[];calls=0;construction=0;start=time.monotonic()
        for gi in range(18):
            progress('independent_construction',block=block,generation=gi+15)
            for label,d in [('serial',a),('noise',b)]:
                r=intake.check_generation(d,label,block,gi,cfgs[label]);calls+=r['optimizer_checks'];construction+=r['construction_checks'];max_error=max(max_error,r['resource_max_error'])
            progress('complete_native_replay',block=block,generation=gi+15)
            receipt=read_union(a,b,block,gi,cfgs['noise']);records.append(receipt)
            for key in ('unique_contexts','source_contexts','matched_overlap'):totals[key]+=receipt[key]
            totals['native_array_comparisons']+=receipt['arrays'];max_noise_error=max(max_noise_error,receipt['noise_moment_max_error'])
        s.require(calls==1456 and construction==2880,'Every construction for block')
        totals['optimizer_checks']+=calls;totals['constructed_records']+=construction
        s.dump(output/f'replay_{block:06d}.json',dict(status='PASS',block=block,structural=structural,receipts=records,
            optimizer_checks=calls,constructed_records=construction,seconds=time.monotonic()-start))
    s.require(totals==dict(optimizer_checks=23296,constructed_records=46080,unique_contexts=36864,source_contexts=46080,
                          matched_overlap=9216,native_array_comparisons=1728),'Full audit coverage')
    s.dump(output/'NATIVE_AUDIT.json',dict(status='PASS',**totals,noise_contexts=288,all_native_states_byte_exact=True,
        full_native_replay_performed=True,max_noise_moment_error=max_noise_error,resource_max_error=max_error,
        source_functions_executed=False,new_scientific_cohort=False))
    import report
    return report.run(output)
