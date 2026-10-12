"""Byte-exact native replay of every declared context; no new sampling."""
import time
import numpy as np
import native as n
import support as s


def replay(block,kind,reps,progress):
    cfg=s.config('approx');source=s.prepared('approx',block);saved=s.observed('approx',block)
    known=kind=='known';control=kind=='original';prefix='control_' if control else ''
    ids=[cfg['replicates'].index(rep) for rep in reps]
    masks=source['original_masks'] if known or control else source['masks'][:,ids]
    raw=n.read_packets(source['packets'][:,:1] if known else source['packets'],masks,source['founders'],source['recipients'],cfg,block,reps,[2048],original=known,progress=progress)
    if known:
        actual={'birth':raw['birth'][:,0],'end':raw['end'][0,:,0,0],'mean_ports':raw['mean_ports'][0,:,0,0]}
        expected={key:source['original_'+key] for key in actual}
        s.require(not n.scores(raw['mean_ports'],source['founders'])['both_pass'].any(),'Known failure enrollment retained')
    else:
        actual={key:raw[key] if key=='birth' else raw[key][0] for key in ['birth','end','port_windows','mean_ports']}
        intended=n.scores(raw['mean_ports'],source['founders']);opposite=n.scores(raw['mean_ports'],source['founders']^1)
        actual.update(min_margin=intended['min_margin'][0],both_pass=intended['both_pass'][0],opposite_margin=opposite['min_margin'][0],opposite_pass=opposite['both_pass'][0])
        axes=dict(birth=1,end=2,port_windows=3,mean_ports=2,min_margin=2,both_pass=2,opposite_margin=2,opposite_pass=2)
        expected={key:np.take(saved[prefix+key],[0] if control else ids,axis=axes[key]) for key in actual}
    for key,value in actual.items():s.equal(value,expected[key],f'Native {block}/{kind}/{key}')
    return dict(status='PASS',block=block,kind=kind,replicates=reps,cases=len(source['founders']),
        trajectories=len(source['founders'])*(1 if known else 9*len(reps)),arrays=len(actual),
        descriptors={key:s.descriptor(value) for key,value in actual.items()})


def benchmark(output,prep_seconds,check_seconds,progress):
    timings={};receipts={}
    for kind,reps in [('known',[0]),('original',[0]),('fresh',[0,1])]:
        progress('benchmark_'+kind,block=34006);start=time.monotonic()
        receipts[kind]=replay(34006,kind,reps,lambda step:progress('benchmark_'+kind,block=34006,step=step))
        timings[kind]=time.monotonic()-start
    forecast=2*(4*timings['known']+4*timings['original']+32*timings['fresh']+4*prep_seconds)+180
    result=dict(status='PASS',classification='DUPLICATED_COMPLETED_CONTEXTS_NOT_NEW_OUTCOMES',receipts=receipts,
        timings_seconds=timings,preparation_seconds=prep_seconds,technical_checks_seconds=check_seconds,
        forecast_seconds=forecast,maximum_seconds=10800,
        forecast_formula='2*(4*known + 4*original + 32*fresh_two_draws + 4*largest_block_preparation) + 180',
        performance_summary_inspected=False,capacity_pass=forecast<10800,automatic_polling=False)
    s.dump(output/'benchmark.json',result);s.require(result['capacity_pass'],'Forecast exceeds ceiling');return result


def audit(output,progress):
    totals=dict(known=0,original=0,fresh=0);arrays=0
    for block in s.config('approx')['blocks']:
        row=dict(block=block,status='PASS',receipts={},timings_seconds={})
        for kind,reps in [('known',[0]),('original',[0]),('fresh',list(range(16)))]:
            progress('replay_'+kind,block=block);start=time.monotonic()
            result=replay(block,kind,reps,lambda step:progress('replay_'+kind,block=block,step=step))
            row['receipts'][kind]=result;row['timings_seconds'][kind]=time.monotonic()-start
            totals[kind]+=result['trajectories'];arrays+=result['arrays']
        s.dump(output/f'replay_{block:06d}.json',row)
    s.require(totals==dict(known=64,original=576,fresh=9216) and arrays==152,'Every native context and array')
    result=dict(status='PASS',totals=totals,native_array_comparisons=arrays,blocks_completed=s.config('approx')['blocks'],
        comparison='Byte equality of dtype, shape and values',new_scientific_outcomes=False)
    s.dump(output/'NATIVE_AUDIT.json',result);return result
