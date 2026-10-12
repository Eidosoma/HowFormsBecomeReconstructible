"""Timed known native controls only, with a bounded whole-run forecast."""
import time
import traceback
import numpy as np
import acquire
import audit_acquire
import audit_reader
import lineage_dynamics as dynamics
from cohort import construct
from reader import read_fixed,stream,decode
from common import ROOT,read,write,sha,arrays,equal,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg);known=read(ROOT/'known/COMPLETE.json')
    for path,digest in known['sources_sha256'].items():assert sha(path)==digest
    data=arrays(ROOT/'known/native_controls.npz',known['outputs_sha256']['native_controls.npz'])
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    names=('benchmark.py','common.py','acquire.py','audit_acquire.py','lineage_dynamics.py','cohort.py','repair.py','optimizer.py','audit_optimizer.py','audit_reader.py','reader.py','sign_graph.py')
    bound={name:sha(ROOT/name) for name in names}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),code_sha256=bound))
    try:
        b=cfg['known_block'];timings={}
        t=time.perf_counter();acq=acquire.teach(b,cfg['development_config']);timings['teaching']=time.perf_counter()-t
        t=time.perf_counter();other=audit_acquire.teach(b,cfg['development_config']);timings['teaching_audit']=time.perf_counter()-t
        for k,value in acq.items():equal(value,data['teach_'+k],'native teaching '+k);equal(value,other[k],'independent teaching '+k)
        t=time.perf_counter();raw=dynamics.rebuild(data['incoming'],b,14,['exact_rewrite'],cfg['development_config'],cfg['cycle'],cfg['tolerance']);timings['renewal']=time.perf_counter()-t
        for k in ('masks','birth','end','mean_ports','outgoing'):equal(raw[k],data[k],'known renewal '+k)
        packets=np.repeat(data['incoming'].reshape(16,1,4096),4,axis=1)
        masks=data['masks'].reshape(16,16,16);founders=np.repeat(np.arange(4),4);recipients=np.tile(np.arange(4),4)
        t=time.perf_counter()
        result=read_fixed(packets,masks,founders,recipients,[stream('E022',b,'develop',14) for _ in range(8)],cfg['reader'],cfg['budgets'],cfg['settling_steps'])
        timings['assessment']=time.perf_counter()-t
        for ri in range(8):
            equal(result['birth'][:,ri],data['birth'].reshape(16,2,16,16),'known assessment reset')
            for vi in range(4):
                equal(result['end'][0,:,vi,ri],data['end'].reshape(16,2,16,16),'known assessment body')
                equal(result['mean_ports'][0,:,vi,ri],data['mean_ports'].reshape(16,2,2),'known assessment means')
        t=time.perf_counter();audit=audit_reader.replay(packets[0],masks[0],0,0,b,0,cfg,original=True);timings['flat_four_record_read']=time.perf_counter()-t
        equal(audit['end'][0],result['end'][0,0,:,0],'known flat read')
        # Timing applies the frozen repair only to known development controls.
        t=time.perf_counter();construct(decode(data['outgoing'].reshape(16,4096)),cfg['blocks'][0],cfg);timings['sixteen_checked_repairs']=time.perf_counter()-t
        per_block=timings['teaching']+timings['teaching_audit']+14*timings['renewal']+timings['assessment']+timings['sixteen_checked_repairs']+2*timings['flat_four_record_read']
        forecast=1.5*16*per_block+180
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),code_sha256=bound,
            known_complete_sha256=sha(ROOT/'known/COMPLETE.json'),byte_equal=True,new_lineages_generated=0,new_scientific_outcomes=False,
            measured_seconds=timings,forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * 16 * (teaching + teaching audit + 14 renewals + assessment + 16 checked repairs + 2 four-record native audits) + 180'))
        print('Known native checks passed. Forecast %.2f minutes; ceiling 60 minutes.'%(forecast/60),flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
