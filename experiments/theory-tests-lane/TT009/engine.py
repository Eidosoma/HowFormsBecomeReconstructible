"""Complete native replay and a fixed retained-input runtime benchmark."""
import time
import native as n
import scoring
import support as s

PLAN=s.read(s.HERE/'plan.json')


def known(block,progress=None):
    source=s.prepared('fixed',block);cfg=s.config('fixed')
    raw=n.read_packets(source['packets'][:,:1],source['masks'],source['founders'],source['recipients'],cfg,block,[0],[2048],original=True,progress=progress)
    fields={'birth':raw['birth'][:,0],'end':raw['end'][0,:,0,0],'mean_ports':raw['mean_ports'][0,:,0,0]}
    for field,value in fields.items():s.equal(value,source['original_'+field],'Known original '+field)
    return dict(status='PASS',cases=len(source['founders']),arrays=len(fields),array_sha256={k:s.descriptor(v)['sha256'] for k,v in fields.items()})


def one(kind,block,reps,progress=None):
    cfg=s.config(kind);source=s.prepared(kind,block)
    raw=n.replay(kind,block,source,cfg,reps,progress)
    result=n.compare_replay(kind,raw,s.observed(kind,block),reps,cfg)
    result.update(block=block,replicates=reps,trajectories=len(source['founders'])*len(cfg['variants'])*len(reps)*(1 if kind=='fixed' else 2),endpoint_scores=int(raw['both_pass'].size))
    return result


def benchmark(output,progress):
    timings={};receipts={};block=PLAN['benchmark_block'];reps=PLAN['benchmark_replicates']
    s.require(len(s.prepared('fixed',block)['founders'])==PLAN['benchmark_cases'],'Benchmark case count')
    for label in ['known','fixed','transfer']:
        progress('benchmark_'+label);start=time.monotonic()
        callback=lambda step,label=label:progress('benchmark_'+label,block=block,step=step)
        receipts[label]=known(block,callback) if label=='known' else one(label,block,reps,callback)
        timings[label]=time.monotonic()-start
    progress('benchmark_full_scoring')
    scoring_receipts={kind:scoring.analyze(kind,output)[1] for kind in ['fixed','transfer']}
    forecast=2*(4*timings['known']+32*timings['fixed']+32*timings['transfer']+120)+120
    source_bytes=sum((s.HERE/name).stat().st_size for name in s.read(s.HERE/'SOURCE_RECEIPT.json')['files_sha256'])
    result=dict(status='PASS',classification='DUPLICATED_KNOWN_INPUT_TECHNICAL_BENCHMARK',timings_seconds=timings,receipts=receipts,scoring=scoring_receipts,
        forecast_seconds=forecast,forecast_formula=PLAN['forecast_formula'],runtime_capacity_pass=forecast<PLAN['maximum_forecast_seconds'],
        source_bytes=source_bytes,storage_required_bytes=PLAN['storage_reserve_bytes']+source_bytes+67108864,new_scientific_outcomes=False)
    s.dump(output/'benchmark.json',result);s.require(result['runtime_capacity_pass'],'Forecast exceeds ceiling');return result


def audit(output,progress):
    receipts=[];reps=list(range(16));counts=dict(known=0,fixed=0,transfer=0,endpoint_scores=0)
    for block in PLAN['blocks']:
        result=dict(block=block,status='PASS',timings_seconds={})
        for kind in ['known','fixed','transfer']:
            progress('replay_'+kind,block=block);started=time.monotonic()
            callback=lambda step,kind=kind:progress('replay_'+kind,block=block,step=step)
            r=known(block,callback) if kind=='known' else one(kind,block,reps,callback)
            result[kind]=r;result['timings_seconds'][kind]=time.monotonic()-started
            counts[kind]+=r['cases'] if kind=='known' else r['trajectories']
            if kind!='known':counts['endpoint_scores']+=r['endpoint_scores']
        s.dump(output/f'replay_{block:06d}.json',result);receipts.append(result)
    s.require(counts==dict(known=PLAN['known_original_trajectories'],fixed=PLAN['fixed_trajectories'],transfer=PLAN['transfer_trajectories'],endpoint_scores=PLAN['experimental_endpoint_scores']),'Complete replay scope')
    return dict(status='PASS',blocks_completed=PLAN['blocks'],counts=counts,native_array_comparisons=sum(sum(r[k]['arrays'] for k in ['known','fixed','transfer']) for r in receipts),
        native_comparison=PLAN['native_comparison'],new_scientific_outcomes=False)
