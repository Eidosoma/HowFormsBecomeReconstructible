"""Known-input benchmark and complete independent native replay."""
import time
import native as n
import scoring
import support as s

PLAN=s.read(s.HERE/'plan.json')


def known(block,progress=None):
    source=s.prepared('p04',block);cfg=s.config('p04')
    raw=n.read_packets(source['packets'][:,:1],source['original_masks'],source['founders'],source['recipients'],cfg,block,[0],[2048],original=True,progress=progress)
    fields={'birth':raw['birth'][:,0],'end':raw['end'][0,:,0,0],'mean_ports':raw['mean_ports'][0,:,0,0]}
    for field,value in fields.items():s.equal(value,source['original_'+field],'Known native '+field)
    return dict(status='PASS',cases=len(source['founders']),arrays=3,array_sha256={k:s.descriptor(v)['sha256'] for k,v in fields.items()})


def experimental(block,reps,progress=None):
    cfg=s.config('p04');source=s.prepared('p04',block)
    raw=n.replay('p04',block,source,cfg,reps,progress);result=n.compare_replay('p04',raw,s.observed('p04',block),reps,cfg)
    result.update(block=block,replicates=reps,trajectories=len(source['founders'])*12*len(reps),endpoint_scores=raw['both_pass'].size)
    return result


def benchmark(output,progress):
    timings={};receipts={};block=PLAN['benchmark_block'];s.require(len(s.prepared('p04',block)['founders'])==16,'Largest benchmark block')
    for kind in ['known','experimental']:
        progress('benchmark_'+kind,block=block);start=time.monotonic()
        callback=lambda step,kind=kind:progress('benchmark_'+kind,block=block,step=step)
        receipts[kind]=known(block,callback) if kind=='known' else experimental(block,PLAN['benchmark_replicates'],callback)
        timings[kind]=time.monotonic()-start
    progress('benchmark_full_scoring');_,scoring_receipt=scoring.run(output)
    forecast=2*(4*timings['known']+32*timings['experimental']+180)+120
    source_bytes=sum((s.HERE/name).stat().st_size for name in s.read(s.HERE/'SOURCE_RECEIPT.json')['files_sha256'])
    result=dict(status='PASS',classification='DUPLICATED_KNOWN_INPUT_TECHNICAL_BENCHMARK',timings_seconds=timings,receipts=receipts,scoring=scoring_receipt,
        forecast_seconds=forecast,forecast_formula=PLAN['forecast_formula'],runtime_capacity_pass=forecast<PLAN['maximum_forecast_seconds'],
        source_bytes=source_bytes,storage_required_bytes=PLAN['storage_reserve_bytes']+source_bytes+67108864,new_scientific_outcomes=False)
    s.dump(output/'benchmark.json',result);s.require(result['runtime_capacity_pass'],'Forecast exceeds ceiling');return result


def audit(output,progress):
    counts=dict(known=0,experimental=0,endpoint_scores=0);arrays=0
    for block in PLAN['blocks']:
        row=dict(status='PASS',block=block,timings_seconds={})
        for kind in ['known','experimental']:
            progress('replay_'+kind,block=block);start=time.monotonic()
            callback=lambda step,kind=kind:progress('replay_'+kind,block=block,step=step)
            result=known(block,callback) if kind=='known' else experimental(block,list(range(16)),callback)
            row[kind]=result;row['timings_seconds'][kind]=time.monotonic()-start;arrays+=result['arrays']
            counts[kind]+=result['cases'] if kind=='known' else result['trajectories']
            if kind=='experimental':counts['endpoint_scores']+=result['endpoint_scores']
        s.dump(output/f'replay_{block:06d}.json',row)
    s.require(counts==dict(known=64,experimental=12288,endpoint_scores=12288) and arrays==80,'Complete audit scope')
    return dict(status='PASS',blocks_completed=PLAN['blocks'],counts=counts,native_array_comparisons=arrays,native_comparison=PLAN['native_comparison'],new_scientific_outcomes=False)
