"""Freeze qualified development design and measured bounded resource forecast."""
from common import *
import argparse,math
import execute

def main(qualification,benchmark):
    qp=ROOT/'checks'/qualification/'COMPLETE.json';bp=ROOT/'runs'/benchmark/'COMPLETE.json'
    q,b=read(qp),read(bp);code=inputs()
    assert q['status']=='PASS' and b['status']=='COMPLETE' and q['inputs']==b['inputs']==code
    assert b['environment']==execute.environment();verify(q['outputs']);verify(b['outputs'])
    manifest=read(ROOT/'SOURCE_MANIFEST.json');verify(manifest['evidence'])
    for index in BLOCKS:verify(manifest['source_blocks'][str(index)]['files'])
    rng=read(ROOT/'RANDOMNESS.json');assert rng['status']=='PASS' and rng['blocks']==list(BLOCKS)
    assert rng['source_population_exposed'] and not rng['new_production_outcomes_generated']
    assert not any((ROOT/'runs').glob('*/tissue_390100*'))
    receipts=[read(ROOT/'runs'/benchmark/f'tissue_{i}'/'COMPLETE.json') for i in EXCLUDED]
    cc,dd,families=schedule('development');f=len(families)
    states=2*(8*f+f)+(8*f+1)
    repairs=cc*states*4;readers=cc*dd*(2*f+1+3*states)
    source=max(r['source_seconds'] for r in receipts)
    repair=max(r['repair_seconds']/r['verification']['new_repair_batches'] for r in receipts)
    reader=max(r['reader_seconds']/r['verification']['new_reader_batches'] for r in receipts)
    other=max(r['seconds']-r['source_seconds']-r['repair_seconds']-r['reader_seconds'] for r in receipts)
    block=source+repairs*repair+readers*reader+4*other
    forecast=math.ceil(1.5*(2*block+2*b['summary_seconds']+4*b['final_custody_seconds']))
    assert forecast<12*3600,dict(forecast_seconds=forecast,reason='outside 12-hour plan')
    storage_blocks=[]
    for i,r in zip(EXCLUDED,receipts):
        directory=ROOT/'runs'/benchmark/f'tissue_{i}';files=[p for p in directory.rglob('*') if p.is_file()]
        source_bytes=sum(p.stat().st_size for p in files if 'baseline' in p.parts)
        repair_bytes=sum(p.stat().st_size for p in files if p.name.startswith('repair_'))
        reader_bytes=sum(p.stat().st_size for p in files if p.name.startswith('reader_'))
        rest=sum(p.stat().st_size for p in files)-source_bytes-repair_bytes-reader_bytes
        storage_blocks.append(source_bytes+repairs*repair_bytes/r['verification']['new_repair_batches']+
            readers*reader_bytes/r['verification']['new_reader_batches']+4*rest)
    storage=math.ceil(1.25*max(storage_blocks)*len(BLOCKS)+512*1024**2)
    assert storage<execute.LIMIT,dict(projected_output_bytes=storage,cap=execute.LIMIT)
    value=dict(study='TT040',frozen_utc=now(),inputs=code,evidence={str(p):sha(p) for p in (qp,bp)},
        environment=execute.environment(),cpus=b['cpus'],workers=2,numerical_threads=1,blocks=BLOCKS,
        block_selection='every sixteenth TT039 identity, not outcomes',run_name='damage_v1',
        forecast_seconds=forecast,deadline_seconds=min(24*3600,max(600,2*forecast)),
        forecast_output_bytes=storage,output_cap_bytes=execute.LIMIT,free_reserve_bytes=execute.RESERVE,
        forecast_method=dict(block_pairs=2,upper_repairs_per_block=repairs,upper_readers_per_block=readers,
            slower_source_seconds=source,slower_repair_batch_seconds=repair,slower_reader_batch_seconds=reader,
            slower_other_seconds=other,other_work_factor=4,summary_factor=2,final_custody_factor=4,slack=1.5,
            not_a_proven_runtime_bound=True),
        primary='mix050; residual|all|all_masks|own; late_minus_preserve; target; separate body and fresh-recipient endpoints; descriptive',
        damage_levels=DAMAGE,mixture_weights=MIX,source_population_exposed=True,source_population_reused=True,
        recipient_evidence_inherited=False,confirmatory=False,new_production_outcomes_generated=False,
        new_recipient_environments=len(BLOCKS)*cc*dd,corruptions_per_block=cc,draws_per_corruption=dd,
        writing_budgets=BUDGETS,writing_windows=WINDOWS,body_endpoint=END,body_checkpoints=SNAPSHOTS,recipient_endpoint=1000,
        automatic_polling=False,automatic_retry=False,automatic_successor=False)
    write(ROOT/'FREEZE.json',value)
    print({k:v for k,v in value.items() if k not in ('inputs','evidence','blocks')},flush=True);return value

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--qualification',required=True);p.add_argument('--benchmark',required=True)
    a=p.parse_args();main(a.qualification,a.benchmark)
