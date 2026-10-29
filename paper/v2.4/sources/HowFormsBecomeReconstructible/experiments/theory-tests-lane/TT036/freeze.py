"""Freeze qualified code, fresh identities and measured pipeline resource bounds."""
from common import *
import argparse,math
import execute

def main(qualification,benchmark):
    qp=ROOT/'checks'/qualification/'COMPLETE.json';bp=ROOT/'runs'/benchmark/'COMPLETE.json'
    q,b=read(qp),read(bp);code=inputs()
    assert q['status']=='PASS' and b['status']=='COMPLETE' and q['inputs']==b['inputs']==code
    assert b['environment']==execute.environment();verify(q['outputs']);verify(b['outputs'])
    verify(read(ROOT/'SOURCE_MANIFEST.json')['evidence'])
    reservation=read(ROOT/'RESERVATION.json');rng=read(ROOT/'RANDOMNESS.json')
    review=read(ROOT/'RESERVATION_REVIEW.json')
    assert review['status']=='PASS_NO_IDENTITY_COLLISION' and review['reservation_sha256']==sha(ROOT/'RESERVATION.json')
    assert rng['status']=='PASS' and reservation['blocks']==list(BLOCKS)
    assert not reservation['new_production_outcomes_generated'] and not rng['production_random_samples_generated']
    assert not any((ROOT/'runs').glob('*/tissue_360000*'))
    receipts=[read(ROOT/'runs'/benchmark/f'tissue_{i}'/'COMPLETE.json') for i in EXCLUDED]
    cc,dd,families=schedule('confirmation');repairs=cc*(8*len(families)+1)*3
    readers=cc*dd*(len(families)+1+2*(8*len(families)+1))
    baseline=max(r['source_seconds'] for r in receipts)
    repair=max(r['repair_seconds']/r['verification']['new_repair_batches'] for r in receipts)
    reader=max(r['reader_seconds']/r['verification']['new_reader_batches'] for r in receipts)
    other=max(r['seconds']-r['source_seconds']-r['repair_seconds']-r['reader_seconds'] for r in receipts)
    block=baseline+repairs*repair+readers*reader+8*other
    forecast=math.ceil(1.5*(32*block+32*b['summary_seconds']+256*b['final_custody_seconds']))
    assert forecast<24*3600,dict(forecast_seconds=forecast,reason='outside admitted 24-hour plan')
    storage_blocks=[]
    for i,r in zip(EXCLUDED,receipts):
        directory=ROOT/'runs'/benchmark/f'tissue_{i}';files=[p for p in directory.rglob('*') if p.is_file()]
        source_bytes=sum(p.stat().st_size for p in files if 'baseline' in p.parts)
        repair_bytes=sum(p.stat().st_size for p in files if p.name.startswith('repair_'))
        reader_bytes=sum(p.stat().st_size for p in files if p.name.startswith('reader_'))
        rest=sum(p.stat().st_size for p in files)-source_bytes-repair_bytes-reader_bytes
        storage_blocks.append(source_bytes+repairs*repair_bytes/r['verification']['new_repair_batches']+
            readers*reader_bytes/r['verification']['new_reader_batches']+8*rest)
    storage=math.ceil(1.25*max(storage_blocks)*64+2*1024**3);assert storage<execute.LIMIT,storage
    value=dict(study='TT036',frozen_utc=now(),inputs=code,evidence={str(p):sha(p) for p in (qp,bp)},
        environment=execute.environment(),cpus=b['cpus'],workers=2,numerical_threads=1,blocks=BLOCKS,
        run_name='confirmation_v1',forecast_seconds=forecast,deadline_seconds=min(48*3600,max(600,2*forecast)),
        forecast_output_bytes=storage,output_cap_bytes=execute.LIMIT,free_reserve_bytes=execute.RESERVE,
        forecast_method=dict(block_pairs=32,upper_repairs_per_block=repairs,upper_readers_per_block=readers,
            slower_baseline_seconds=baseline,slower_repair_batch_seconds=repair,slower_reader_batch_seconds=reader,
            slower_other_seconds=other,other_work_factor=8,summary_factor=32,final_custody_factor=256,slack=1.5,
            not_a_proven_runtime_bound=True),
        primary='residual|all|all_masks|own; 100_minus_1000; target; terminal body and fresh recipient co-primary',
        per_endpoint_alpha=ALPHA,family_alpha=.05,margin=0.,new_production_outcomes_generated=False,
        source_population_exposed=False,new_recipient_environments=64*cc*dd,writing_budgets=BUDGETS,body_endpoint=1000,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'FREEZE.json',value)
    print({k:v for k,v in value.items() if k not in ('inputs','evidence','blocks')},flush=True);return value
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--qualification',required=True);p.add_argument('--benchmark',required=True)
    a=p.parse_args();main(a.qualification,a.benchmark)
