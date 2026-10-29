"""Excluded tests for retained-prefix custody and independently evolving branches."""
import argparse
import os
import shutil
import time
import traceback
from common import *
import analysis
import audit
import baseline
import design
import execute
import kernel
import run

def rejected(label,function,checks):
    try:function()
    except (AssertionError,ValueError,TypeError,FileNotFoundError):checks.append(label)
    else:raise AssertionError('not rejected: '+label)

def main(name):
    output=ROOT/'checks'/name;output.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    inputs=runtime_hashes();checks=[]
    write_json(output/'STARTED.json',dict(started_utc=now(),inputs=inputs,scientific_continuations_generated=False))
    execute.snapshot_code(output)
    try:
        assert source_check()==289 and baseline_check()==44
        checks.append('289 native source files, byte-identical TT023 adapter, independent references and all 44 copied source batches bound')
        rejected('scientific continuation blocked before freeze',lambda:run.run_block(output/'forbidden',BLOCKS[0],'development'),checks)
        assert design.ARMS==('full_on','subtract_on','zero_on','zero_off')
        assert design.expected('development',4)['native_arrays']==10752
        checks.append('four fixed policies and full serial work counts retained')
        serial=output/'serial';serial.mkdir()
        for index in DISPOSABLE:run.run_block(serial/f'tissue_{index}',index,'qualification')
        checks.append('all excluded two-cycle new contexts independently replayed and retained trajectories verified')
        parallel=output/'parallel';parallel.mkdir();cpus=sorted(os.sched_getaffinity(0))[-2:]
        execute.batch(parallel,DISPOSABLE,'qualification',cpus)
        matched=0
        for path in sorted(serial.rglob('*.npz')):
            assert identities(arrays(path))==identities(arrays(parallel/path.relative_to(serial)));matched+=1
        for path in serial.rglob('records.json'):assert path.read_bytes()==(parallel/path.relative_to(serial)).read_bytes()
        for index in DISPOSABLE:assert run.saved_check(serial/f'tissue_{index}')==run.saved_check(parallel/f'tissue_{index}')
        checks.append('serial/two-worker arrays, rows, source custody and paired environments agree exactly')
        cfg,rcfg=design.configs('qualification');index=DISPOSABLE[0];ctx=model.source.context(index,cfg)
        source=baseline.load(ctx,rcfg,'qualification',0,'residual')
        for i in DISPOSABLE:
            local=model.source.context(i,cfg)
            for family in design.FAMILIES:
                src=baseline.load(local,rcfg,'qualification',0,family)
                for arm in design.ARMS:
                    memory,write=design.options(arm)
                    for generation in ((1,2) if arm in design.CACHED else (1,)):
                        cache=baseline.components(src,arm,generation);raw=cache['values']['repair']
                        state={k:raw['s0_'+k].copy() for k in KEYS};before=identities(state)
                        observed,meta=kernel.repair(model.boundary.runtime_context(local),state,kernel.address(i,0,generation,'repair'),write)
                        assert identities(observed)==identities(raw) and meta['rng_final']==cache['repair_meta']['rng_final']
                        assert identities(state)==before
                        audit.repair(local,state['theta'].tobytes(),cache['values']['develop'][f's{cfg.sweeps}_V'],rcfg,
                            0,generation,memory,write,cache['values']['boundary'],cache['injury_meta'],observed,meta,
                            cache['values']['body'],observed[f's{cfg.sweeps}_theta'].tobytes(),True)
        checks.append('adapter reproduces both retained control cycles and each TT023 first repair exactly on every excluded batch')
        p=serial/f'tissue_{index}/future_00/residual/subtract_on'
        raw=arrays(p/'g02_repair.npz');meta=read_json(p/'g02.json');developed=arrays(p/'g02_develop.npz')
        boundary=arrays(p/'g02_boundary.npz');body=arrays(p/'g02_body.npz')
        incoming=developed['s0_theta'].tobytes();outgoing=raw[f's{cfg.sweeps}_theta'].tobytes()
        # Exercise a new development after a newly evolved packet, beyond cached generation two.
        for arm in design.NEW:
            path=serial/f'tissue_{index}/future_00/residual'/arm
            packet=arrays(path/'packets.npz')['final'].tobytes();memory,write=design.options(arm)
            third,rmeta=kernel.read(ctx,packet,rcfg,0,3,'develop')
            audit.read(ctx,packet,rcfg,0,3,'develop',third,rmeta,True)
            state,bound,bmeta=kernel.injure(ctx,packet,third[f's{cfg.sweeps}_V'],0,3,memory)
            repaired,pmeta=kernel.repair(model.boundary.runtime_context(ctx),state,kernel.address(index,0,3,'repair'),write)
            observed=kernel.body(ctx,repaired[f's{cfg.sweeps}_V'],rcfg)
            audit.repair(ctx,packet,third[f's{cfg.sweeps}_V'],rcfg,0,3,memory,write,bound,bmeta,
                repaired,pmeta,observed,repaired[f's{cfg.sweeps}_theta'].tobytes(),True)
            extra=output/f'third_cycle_{arm}';extra.mkdir()
            for label,value in dict(develop=third,boundary=bound,repair=repaired,body=observed).items():write_arrays(extra/(label+'.npz'),value)
            write_json(extra/'META.json',dict(read=rmeta,injury=bmeta,repair=pmeta,independent_replay=True))
            rejected('substituting an old comparator body in third-cycle injury rejected: '+arm,
                lambda:audit.injury(ctx,packet,developed[f's{cfg.sweeps}_V'],0,3,memory,bound,repaired,bmeta),checks)
        checks.append('both new arms evolve and independently replay an additional excluded third-cycle body and repair')
        state={k:raw['s0_'+k].copy() for k in KEYS};runtime=model.boundary.runtime_context(ctx);key=kernel.address(index,0,2,'repair')
        rejected('task codebook excluded from physical repair',lambda:kernel.repair(runtime|{'codes':ctx['codes']},state,key,True),checks)
        rejected('hidden ancestral body excluded from state',lambda:kernel.repair(runtime,state|{'parent':state['V']},key,True),checks)
        rejected('task labels excluded from initializer',lambda:kernel.initial(state['V'],state['theta'],boundary['fresh'],ctx['tissue'].resting,'subtract',labels=np.arange(4)),checks)
        changed={k:v.copy() for k,v in state.items()};changed['R'][boundary['fresh']]=0.
        rejected('clearing fresh-cell jitter instead of subtracting fill rejected',lambda:audit.initial(state['V'],state['theta'],boundary['fresh'],ctx['tissue'].resting,'subtract',changed),checks)
        badmask=boundary['fresh'].copy();badmask.flat[0]^=True
        rejected('malformed physical mask rejected',lambda:kernel.initial(state['V'],state['theta'],badmask,ctx['tissue'].resting,'subtract'),checks)
        wrong={k:v.copy() for k,v in boundary.items()};wrong['fresh']=~wrong['fresh']
        rejected('wrong half-sized injury mask rejected',lambda:audit.injury(ctx,incoming,developed[f's{cfg.sweeps}_V'],0,2,'subtract',wrong,raw,meta['injury']),checks)
        corrupt={k:v.copy() for k,v in raw.items()};corrupt['s1_V'].flat[0]=np.nextafter(corrupt['s1_V'].flat[0],np.inf)
        rejected('one-ULP new physical corruption rejected',lambda:audit.repair(ctx,incoming,developed[f's{cfg.sweeps}_V'],rcfg,0,2,
            'subtract',True,boundary,meta['injury'],corrupt,meta['repair'],body,outgoing,True),checks)
        rejected('malformed finite packet rejected',lambda:model.boundary.decode(incoming[:-8],cfg.replicates),checks)
        nonfinite=np.frombuffer(incoming,dtype=np.float64).copy();nonfinite[0]=np.nan
        rejected('nonfinite inherited packet rejected',lambda:model.boundary.decode(nonfinite.tobytes(),cfg.replicates),checks)
        contaminated={k:v.copy() for k,v in developed.items()};contaminated['s0_R'].flat[0]=1.
        rejected('ancestral memory in recipient rejected',lambda:audit.read(ctx,incoming,rcfg,0,2,'develop',contaminated,meta['read'],False),checks)
        rejected('wrong current packet at recipient rejected',lambda:audit.read(ctx,source['initial'],rcfg,0,2,'develop',developed,meta['read'],False),checks)
        mutant=output/'changed_row';shutil.copytree(p,mutant);data=read_json(mutant/'records.json');data[0]['terminal']=1.-data[0]['terminal']
        (mutant/'records.json').write_bytes(serialized(data))
        rejected('corrupted terminal row rejected',lambda:run.saved_chain(mutant,ctx,source,'subtract_on',0,2,rcfg),checks)
        mutant=output/'changed_route';shutil.copytree(p,mutant);value=read_json(mutant/'g02.json');value['input_sha256']='0'*64
        (mutant/'g02.json').write_bytes(serialized(value))
        rejected('wrong cross-cycle packet route rejected',lambda:run.saved_chain(mutant,ctx,source,'subtract_on',0,2,rcfg),checks)
        rejected('undeclared random phase rejected',lambda:kernel.address(index,0,1,'label'),checks)
        keys=[kernel.address(i,f,g,p) for i in (*BLOCKS,*DISPOSABLE) for f in range(4) for g in range(1,9) for p in design.PHASES]
        assert len(keys)==len(set(keys))
        assert all(kernel.address(i,f,g,p)==audit.address(i,f,g,p) for i in (*BLOCKS,*DISPOSABLE) for f in range(4) for g in range(1,9) for p in design.PHASES)
        samples=[]
        for f,g,p in ((0,1,'develop'),(1,1,'develop'),(0,2,'develop'),(0,2,'terminal')):
            rng=ref.old.Coupled(ref.old.READ_TAG,audit.address(index,f,g,p),'assay_birth',cfg.replicates)
            v=rng.standard_normal((4*cfg.replicates,16,16));samples.append(v.tobytes())
            assert all(np.array_equal(v[:cfg.replicates],v[m*cfg.replicates:(m+1)*cfg.replicates]) for m in range(4))
        assert len(set(samples))==4
        checks.append('original addresses independently reconstructed and excluded draws preserve pairing and stream separation')
        fake=run.rows([np.array([1.,.5,0.,1.])]*2,[np.array([1.,1.,0.,.5])]*2,np.array([0.,1.,1.,1.]),1,[['x']*4]*2)
        assert fake[0]['uninterrupted_development'] and fake[0]['terminal']==0.
        assert not fake[1]['uninterrupted_development'] and fake[1]['uninterrupted_repaired'] and not fake[3]['uninterrupted_repaired']
        checks.append('terminal success remains separate and ties fail uninterrupted endpoints')
        summary=analysis.summary(serial,'qualification');write_json(output/'SUMMARY.json',summary)
        assert analysis.report(summary)==analysis.report(read_json(output/'SUMMARY.json'))
        with (output/'REPORT.md').open('x') as stream:stream.write(analysis.report(summary))
        for family in design.FAMILIES:
            assert set(summary['families'][family]['arms'])==set(design.ARMS)
            assert set(summary['families'][family]['contrasts'])==set(design.comparisons())
        checks.append('all arms, six contrasts, three endpoints, strata and full summary/report roundtrip retained')
        verify(inputs);assert runtime_hashes()==inputs
        receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=inputs,
            outputs={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()},environment=execute.environment(),
            checks=checks,checks_passed=len(checks),matched_array_files=matched,serial_parallel_exact=True,
            max_native_error=0.,scientific_continuations_generated=False)
        write_json(output/'COMPLETE.json',receipt)
        write_json(ROOT/'QUALIFICATION.json',dict(status='PASS',path=str(output/'COMPLETE.json'),sha256=sha(output/'COMPLETE.json')))
        print(json.dumps({k:v for k,v in receipt.items() if k not in ('inputs','outputs')},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False));raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);main(parser.parse_args().name)
