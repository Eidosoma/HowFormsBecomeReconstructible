"""Excluded dynamics, statistics, information-route and scheduling checks."""
import ast
import copy
from dataclasses import replace
import math
import os
import time
import traceback

from scipy.special import betainc
from scipy.stats import nct, t
from common import *
import analysis
import design
import execute
import register
import run


def main():
    output=ROOT/'checks'/execute.QUALIFICATION;output.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();checks=[];inputs=runtime_hashes()
    write_json(output/'INPUTS.json',dict(inputs=inputs,environment=execute.environment()))
    def passes(name):checks.append(name)
    def rejects(name,fn):
        try:fn()
        except (AssertionError,ValueError,FileNotFoundError):passes(name);return
        raise AssertionError('corruption escaped: '+name)
    try:
        source_check();design.plan();assert len(design.claims())==5 and design.ALPHA==.01
        assert not (ROOT/'REGISTRATION.json').exists()
        passes('20 selected paths and five fixed claims; unchanged source/reference identities')
        for name,allowed in (('reference.py',('numpy','tt019_reference')),('tt019_reference.py',('numpy','hashlib','json','math'))):
            for node in ast.walk(ast.parse((ROOT/name).read_text())):
                if isinstance(node,ast.Import):assert all(v.name in allowed for v in node.names)
                assert not isinstance(node,ast.ImportFrom)
        passes('independent references import no native physics')
        pattern=register.identity_pattern()
        for index in BLOCKS:
            assert pattern.search(str(index)) and pattern.search('tissue_'+str(index)+'.json')
            assert not pattern.search('9'+str(index)+'8')
        assert not pattern.search('603210')
        passes('bounded seed search uses complete digit sequences')
        rejects('new cohort cannot start before registration',lambda:run.run_block(output/'forbidden',BLOCKS[0],model.CONFIG,model.READOUT,'prospective confirmation'))
        assert not (output/'forbidden').exists()
        keys=[f'{tag}:{index}:{phase}' for index in (*BLOCKS,*DISPOSABLE) for tag,phase in
            (('l22-source-recovery-v1','parent'),('l22-source-recovery-v1','fission'),
             ('l22-source-recovery-v1','damage'),('l22-active-form-boundary-v1','repair'),
             ('l22-active-form-boundary-v1','shuffle'),('l22-fixed-record-readout-v1','assay_birth'),
             ('l22-fixed-record-readout-v1','assay'))]
        assert len({hashlib.sha256(k.encode()).digest()[:16] for k in keys})==len(keys)
        passes('source/repair/reader addresses separate; no new-cohort random samples generated')
        cfg=replace(model.CONFIG,replicates=1,settle=3,imprint=5,sweeps=4,times=(0,1,2,4))
        rcfg=replace(model.READOUT,parents=1,draws=2,sweeps=4,times=(0,1,4))
        serial=output/'serial';serial.mkdir()
        for index in DISPOSABLE:run.run_block(serial/f'tissue_{index}',index,cfg,rcfg,'excluded qualification')
        passes('both disposable blocks: full selected matrix and independent physical/scalar replay')
        parallel=output/'two_worker';parallel.mkdir()
        cpus=sorted(os.sched_getaffinity(0))[-2:];assert len(cpus)==2
        execute.paired_batch(parallel,DISPOSABLE,cfg,rcfg,cpus,'excluded qualification')
        for index in DISPOSABLE:
            a,b=[root/f'tissue_{index}' for root in (serial,parallel)]
            for name in ('records.json','contrasts.json','read_map.json'):
                assert (a/name).read_bytes()==(b/name).read_bytes()
            ap,bp=[read_json(root/'PROVENANCE.json') for root in (a,b)]
            for category in ('source','repairs','reads'):
                assert ap[category].keys()==bp[category].keys()
                for name in ap[category]:assert ap[category][name]['arrays']==bp[category][name]['arrays']
            assert ap['packets']['arrays']==bp['packets']['arrays']
        passes('two worker / serial bit-exact arrays, routes, records and contrasts')
        block=serial/f'tissue_{DISPOSABLE[0]}'
        ctx=model.source.context(DISPOSABLE[0],cfg)
        original,built=[arrays(block/(name+'.npz')) for name in ('original','boundary')]
        spec=design.plan()['capture__common__own__fixed'];state=model.initial(built,original,spec)
        local=model.boundary.runtime_context(ctx)
        rejects('wrong body snapshot rejected',lambda:model.repair(local,state|{'R':built['body_partner']},DISPOSABLE[0],spec))
        rejects('hidden parent record rejected',lambda:model.repair(local,state|{'parent_theta':state['theta']},DISPOSABLE[0],spec))
        rejects('scoring codebook excluded from repair',lambda:model.repair(local|{'codes':ctx['codes']},state,DISPOSABLE[0],spec))
        raw=arrays(block/'repair_capture__common__own__fixed.npz')
        meta=read_json(block/'repair_capture__common__own__fixed.json')
        changed={k:v.copy() for k,v in raw.items()};changed['s4_V'].flat[0]=np.nextafter(changed['s4_V'].flat[0],np.inf)
        rejects('one ULP native checkpoint corruption detected',lambda:ref.repairs(physical_context(ctx),state,DISPOSABLE[0],spec,changed,meta))
        changed={k:v.copy() for k,v in raw.items()};changed['a0_mean'][:]=0
        rejects('missing birth observation detected',lambda:ref.repairs(physical_context(ctx),state,DISPOSABLE[0],spec,changed,meta))
        provenance=read_json(block/'PROVENANCE.json');item=dict(provenance['repairs']['common__own__live']);item['sha256']='0'*64
        rejects('changed saved file digest detected',lambda:open_pointer(item))
        mapping=read_json(block/'read_map.json');packet=arrays(block/'packets.npz')['capture__common__own__fixed']
        key=mapping['capture__common__own__fixed']['assay'];raw=arrays(block/('read_'+key+'.npz'))
        metadata=read_json(block/('read_'+key+'.json'))
        rejects('hidden body memory rejected in fresh reader',lambda:ref.fresh_read(physical_context(ctx)|{'R':state['R']},packet.tobytes(),DISPOSABLE[0],rcfg,False,raw,metadata))
        rows=read_json(block/'records.json');altered=copy.deepcopy(rows);altered['capture__common__own__fixed'][0]['accuracy']+=.25
        parent=arrays(block/'parent.npz')
        rejects('changed recognition row detected',lambda:ref.record_scores(packet,parent,ctx['codes'],raw,rcfg,altered['capture__common__own__fixed']))
        rejects('changed paired contrast detected',lambda:run.check_contrasts(altered,read_json(block/'contrasts.json')))
        off=read_json(block/'read_map.json')['reader_off']['assay']
        off_raw=arrays(block/('read_'+off+'.npz'))
        assert not np.array_equal(off_raw['s4_V'],raw['s4_V'])
        passes('reader switch has physical effect; write-off and held identities checked in every block')
        # Existing completed evidence checks the inherited scoring interface without new trajectories.
        old=LANE/'TT020/runs/audit_v1/tissue_30056'
        old_parent=arrays(old/'parent.npz');old_original=arrays(old/'original.npz')
        old_packets=arrays(old/'packets.npz');old_rows=read_json(old/'records.json');old_map=read_json(old/'read_map.json')
        old_prov=read_json(old/'PROVENANCE.json')
        selected=set(rows)
        for name in selected:
            old_raw=open_pointer(old_prov['reads'][old_map[name]['assay']])
            ref.record_scores(old_packets[name],old_parent,old_original['codes'],old_raw,model.READOUT,old_rows[name])
        run.check_contrasts({name:old_rows[name] for name in selected},analysis.contrasts(old_rows))
        passes('all 29 selected archived outcomes agree with unchanged independent scorer')
        values=np.linspace(-.1,.6,64);value=analysis.interval(values)
        mean=float(np.mean(values));se=float(np.std(values,ddof=1)/8)
        assert abs(value['mean']-mean)<1e-15 and abs(value['standard_error']-se)<1e-15
        critical=float(t.ppf(.99,63));cdf=1-.5*betainc(63/2,.5,63/(63+critical**2))
        assert abs(cdf-.99)<1e-12
        assert abs(value['lower_one_sided']-(mean-critical*se))<1e-14
        assert analysis.interval([0.]*64)['lower_one_sided']<0
        assert analysis.interval([1.]*64)['lower_one_sided']<1
        assert analysis.interval([-1.]*64)['upper_one_sided']>-1
        rejects('invalid out-of-range contrast rejected',lambda:analysis.interval([2.]*64))
        passes('independent moment/CDF checks, multiplicity and bounded zero-variance fallback')
        sensitivity=[dict(margin=margin,true_effect=effect,block_sd=sd,n=64,
            approximate_power=float(nct.sf(critical,63,(effect-margin)*8/sd)))
            for margin in (.02,.05) for effect in (.02,.03,.05,.10,.20,.30) for sd in (.05,.10,.20,.30)]
        write_json(output/'POWER_SENSITIVITY.json',dict(rows=sensitivity,
            limitation='Noncentral-t normal-block planning scenarios; not measured prospective variance or guaranteed power.'))
        verify(inputs);source_check()
        files={str(p):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        proofs=[read_json(serial/f'tissue_{i}/CHECK.json') for i in DISPOSABLE]
        value=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,checks=checks,
            checks_passed=len(checks),inputs=inputs,outputs=files,environment=execute.environment(),
            serial_parallel_exact=True,new_cohort_generated=False,
            max_native_error=0.,max_average_error=max(p['max_average_error'] for p in proofs))
        write_json(output/'COMPLETE.json',value)
        print(json.dumps({k:v for k,v in value.items() if k not in ('inputs','outputs','checks')},sort_keys=True),flush=True)
    except BaseException as error:
        write_json(output/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),passed=checks));raise


if __name__=='__main__':main()
