"""Excluded numerical qualification; preserve inputs and any failed attempt."""
import argparse
import os
import shutil
import time
import traceback
from common import *
import analysis
import audit
import design
import execute
import kernel
import run

def rejected(label,call,checks):
    try:call()
    except (AssertionError,ValueError,FileNotFoundError,TypeError):checks.append(label)
    else:raise AssertionError('not rejected: '+label)

def main(name):
    output=ROOT/'checks'/name;output.mkdir(parents=True,exist_ok=False);tick=time.monotonic();inputs=runtime_hashes();checks=[]
    write_json(output/'STARTED.json',dict(started_utc=now(),inputs=inputs,scientific_counterfactuals_generated=False))
    execute.snapshot_code(output)
    try:
        assert source_check()==289 and baseline_check()==44
        checks.append('byte-identical physical sources and all 44 checksum-bound source batches')
        rejected('scientific counterfactuals blocked before freeze',lambda:run.run_block(output/'forbidden',BLOCKS[0],'development'),checks)
        serial=output/'serial';serial.mkdir()
        for index in DISPOSABLE:run.run_block(serial/f'tissue_{index}',index,'qualification');run.saved_check(serial/f'tissue_{index}')
        checks.append('all excluded six-arm trajectories, independent physics, shared assays and saved rows pass')
        parallel=output/'parallel';parallel.mkdir();cpus=sorted(os.sched_getaffinity(0))[-2:]
        execute.batch(parallel,DISPOSABLE,'qualification',cpus)
        array_files=0
        for p in sorted(serial.rglob('*.npz')):
            assert identities(arrays(p))==identities(arrays(parallel/p.relative_to(serial)));array_files+=1
        for p in serial.rglob('records.json'):assert p.read_bytes()==(parallel/p.relative_to(serial)).read_bytes()
        for index in DISPOSABLE:run.saved_check(parallel/f'tissue_{index}')
        checks.append('serial/two-worker arrays and every record row agree exactly')
        cfg,rcfg=design.configs('qualification');index=DISPOSABLE[0];ctx=model.source.context(index,cfg)
        source=run.load_source('qualification',index,0,'residual',ctx,rcfg)
        original={k:v.copy() for k,v in source.items() if isinstance(v,np.ndarray)}
        states={m:kernel.initial(source['v'],source['theta'],source['fresh'],ctx['tissue'].resting,m) for m in ('full','subtract','zero')}
        for memory,state in states.items():audit.initial(source['v'],source['theta'],source['fresh'],ctx['tissue'].resting,memory,state)
        assert all(identities({k:states['full'][k]})==identities({k:states[m][k]}) for m in states for k in ('V','ema','theta'))
        assert len({state['R'].tobytes() for state in states.values()})==3
        assert states['subtract']['R'][~source['fresh']].tobytes()==source['v'][~source['fresh']].tobytes()
        assert np.array_equal(states['subtract']['R'][source['fresh']],source['v'][source['fresh']]-ctx['tissue'].resting)
        checks.append('only memory initialization changes; fill subtraction preserves body, retained cells and fresh jitter')
        for i in DISPOSABLE:
            local=model.source.context(i,cfg)
            for family in design.FAMILIES:
                src=run.load_source('qualification',i,0,family,local,rcfg)
                for arm in ('full_on','zero_off'):
                    memory,write=design.options(arm);state=kernel.initial(src['v'],src['theta'],src['fresh'],local['tissue'].resting,memory)
                    raw,metadata=kernel.repair(model.boundary.runtime_context(local),state,kernel.address(i,0,1,'repair'),write)
                    old=src[design.CACHED[arm]]
                    assert identities(raw)==identities(old['repair']) and metadata['rng_final']==old['first']['repair']['rng_final']
                    audit.repairs(local,src['v'],src['theta'],src['fresh'],memory,write,0,raw,metadata,True)
                    read,rmeta=kernel.read(local,raw[f's{cfg.sweeps}_theta'].tobytes(),rcfg,0)
                    assert identities(read)==identities(old['read']) and rmeta==old['second']['read']
                    audit.read(local,raw[f's{cfg.sweeps}_theta'].tobytes(),rcfg,0,read,rmeta,True)
        checks.append('new adapter exactly reproduces both retained original arms and readers on every excluded batch')
        assert all(np.array_equal(source[k],value) for k,value in original.items())
        checks.append('original input fields remain immutable')
        runtime=model.boundary.runtime_context(ctx);key=kernel.address(index,0,1,'repair')
        rejected('task labels forbidden at repair boundary',lambda:kernel.repair(runtime|{'codes':ctx['codes']},states['subtract'],key,True),checks)
        rejected('hidden parent forbidden in repair state',lambda:kernel.repair(runtime,states['subtract']|{'parent':source['v']},key,True),checks)
        rejected('task labels forbidden at initializer',lambda:kernel.initial(source['v'],source['theta'],source['fresh'],ctx['tissue'].resting,'subtract',labels=np.arange(4)),checks)
        bad=source['fresh'].copy();bad.flat[0]^=True
        rejected('malformed injury mask rejected',lambda:kernel.initial(source['v'],source['theta'],bad,ctx['tissue'].resting,'subtract'),checks)
        altered={k:v.copy() for k,v in source['capture']['boundary'].items()};altered['fresh']=~altered['fresh']
        rejected('wrong but half-sized physical mask rejected',lambda:audit.source(ctx,0,source['capture']['develop'][f's{cfg.sweeps}_V'],altered,
            source['capture']['repair'],source['capture_once']['repair'],source['capture']['first'],source['capture_once']['read'],source['capture_once']['second']['read'],rcfg),checks)
        p=serial/f'tissue_{index}/future_00/residual/subtract_on';meta=read_json(p/'META.json');raw=arrays(p/'repair.npz')
        raw['s1_V'].flat[0]=np.nextafter(raw['s1_V'].flat[0],np.inf)
        rejected('one-ULP new physical corruption rejected',lambda:audit.repairs(ctx,source['v'],source['theta'],source['fresh'],'subtract',True,0,raw,meta['repair'],True),checks)
        rejected('malformed finite packet rejected',lambda:model.boundary.decode(source['theta'].tobytes()[:-8],cfg.replicates),checks)
        read=arrays(p/'read.npz');badread={k:v.copy() for k,v in read.items()};badread['s0_R'].flat[0]=1.
        rejected('ancestral memory in fresh recipient rejected',lambda:audit.read(ctx,read['s0_theta'].tobytes(),rcfg,0,badread,meta['read'],False),checks)
        rejected('wrong incoming packet rejected',lambda:audit.read(ctx,source['theta'].tobytes(),rcfg,0,read,meta['read'],False),checks)
        mutant=output/'changed_row';shutil.copytree(p,mutant);rows=read_json(mutant/'records.json');rows[0]['recipient']=1.-rows[0]['recipient'];(mutant/'records.json').write_bytes(serialized(rows))
        rejected('changed saved receiving score rejected',lambda:run.saved_arm(mutant,ctx,source,'subtract_on',0,rcfg),checks)
        mutant=output/'changed_route';shutil.copytree(p,mutant);m=read_json(mutant/'META.json');m['read_address']+=1;(mutant/'META.json').write_bytes(serialized(m))
        rejected('changed receiving address rejected',lambda:run.saved_arm(mutant,ctx,source,'subtract_on',0,rcfg),checks)
        summary=analysis.summary(serial,'qualification');write_json(output/'SUMMARY.json',summary)
        report=analysis.report(summary)
        assert report==analysis.report(read_json(output/'SUMMARY.json'))
        with (output/'REPORT.md').open('x') as stream:stream.write(report)
        assert all(summary['families'][f]['contrasts']['fill_vs_full_off']['recipient']['difference']==0. for f in design.FAMILIES)
        checks.append('full summary/report JSON roundtrip and shared off-recipient identity pass')
        for i in (*BLOCKS,*DISPOSABLE):
            for future in range(4):
                for generation,phase in ((1,'repair'),(1,'fission'),(2,'develop')):
                    assert kernel.address(i,future,generation,phase)==audit.address(i,future,generation,phase)
        rejected('undeclared stochastic phase rejected',lambda:kernel.address(index,0,1,'task_label'),checks)
        checks.append('original paired addresses independently reconstructed; no new scientific seed namespace')
        verify(inputs);assert runtime_hashes()==inputs
        receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=inputs,
            outputs={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()},environment=execute.environment(),
            checks=checks,checks_passed=len(checks),matched_array_files=array_files,serial_parallel_exact=True,
            max_native_error=0.,scientific_counterfactuals_generated=False)
        write_json(output/'COMPLETE.json',receipt);write_json(ROOT/'QUALIFICATION.json',dict(status='PASS',path=str(output/'COMPLETE.json'),sha256=sha(output/'COMPLETE.json')))
        print(json.dumps({k:v for k,v in receipt.items() if k not in ('inputs','outputs')},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False));raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);main(parser.parse_args().name)
