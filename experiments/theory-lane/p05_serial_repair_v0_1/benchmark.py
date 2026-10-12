"""Replay already exposed block 34000 only; time native reads and known repair."""
import time
import traceback
import numpy as np
import audit_reader
from common import ROOT,read,write,sha,arrays,equal,stamp,validate
from serial import rebuild,prepare


def main():
    cfg=read(ROOT/'config.json');validate(cfg);sources=read(ROOT/'sources/COMPLETE.json')
    data=arrays(ROOT/'sources/native_controls.npz',sources['outputs_sha256']['native_controls.npz'])
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    names=('benchmark.py','common.py','serial.py','lineage_dynamics.py','repair.py','optimizer.py',
           'audit_optimizer.py','audit_reader.py','reader.py','sign_graph.py')
    bound={n:sha(ROOT/n) for n in names}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),code_sha256=bound,config_sha256=sha(ROOT/'config.json')))
    try:
        timings={}
        packets=np.repeat(data['incoming'].reshape(1,16,4096),4,axis=0)
        t=time.process_time();raw=rebuild(packets,34000,14,cfg);timings['four_branch_renewal']=time.process_time()-t
        for k in ('end','mean_ports','outgoing'):
            expected=np.repeat(data[k].reshape((1,16)+data[k].shape[3:]),4,axis=0)
            equal(raw[k],expected,'archival native renewal '+k)
        equal(raw['birth'],data['birth'].reshape(16,2,16,16),'native birth')
        equal(raw['masks'],data['masks'].reshape(16,16,16),'native injury')
        t=time.process_time()
        audited=audit_reader.replay(packets[:,0],raw['masks'][0],0,0,34000,0,cfg,original=True,generation=14)
        timings['four_branch_flat_read']=time.process_time()-t
        equal(audited['end'][0],raw['end'][:,0],'flat native body')
        equal(audited['port_windows'][0],raw['port_windows'][:,:,0],'flat windows')
        known=np.repeat(data['outgoing'].reshape(1,16,4096),4,axis=0)
        # This produces no new body: only repair a previously exposed record.
        t=time.process_time();prepared,details=prepare(known,34000,15,cfg)
        timings['forty_eight_checked_repairs']=time.process_time()-t
        equal(prepared[1],prepared[2],'matching first repairs')
        assert int(details['independent_optimizer_checks'])==48
        per_block=18*timings['four_branch_renewal']+(592/48)*timings['forty_eight_checked_repairs']+2*timings['four_branch_flat_read']
        forecast=1.5*16*per_block+240
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),code_sha256=bound,
            config_sha256=sha(ROOT/'config.json'),sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'),
            byte_equal=True,new_continuation_outcomes=0,new_scientific_outcomes=False,
            measured_cpu_seconds=timings,forecast_cpu_seconds=forecast,
            within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * 16 * (18 four-branch renewals + 592 checked repairs + 2 four-branch flat audits) + 240'))
        print('Known native checks passed. Forecast %.2f single-thread CPU minutes; ceiling 120.'%(forecast/60),flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
