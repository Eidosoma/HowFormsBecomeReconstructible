"""Exposed fixtures only: acquisition, native renewal, repair, and four-arm reads."""
import copy
import time
import traceback
import numpy as np
import acquire
import audit_acquire
import audit_reader
import lineage_dynamics as dynamics
import serial
import policy
from audit_serial import audit_noise
from common import ROOT,read,write,sha,arrays,equal,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg);folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    bound={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),code_sha256=bound,config_sha256=sha(ROOT/'config.json')))
    try:
        timings={};known=arrays(ROOT/'sources/native_controls.npz');known_teaching=arrays(ROOT/'sources/teaching_controls.npz')
        t=time.process_time();teaching=acquire.teach(34000,cfg['development_config'])
        timings['known_teaching']=time.process_time()-t
        t=time.process_time();flat_teaching=audit_acquire.teach(34000,cfg['development_config'])
        timings['known_flat_teaching']=time.process_time()-t
        for key,value in teaching.items():
            equal(value,known_teaching['teach_'+key],'known teaching '+key);equal(value,flat_teaching[key],'flat teaching '+key)
        t=time.process_time()
        native=dynamics.rebuild(known['incoming'],34000,14,['exact_rewrite'],cfg['development_config'],cfg['cycle'],cfg['tolerance'])
        timings['known_history_renewal']=time.process_time()-t
        for key in ('birth','end','masks','mean_ports','outgoing'):equal(native[key],known[key],'native fixture '+key)
        matched=copy.deepcopy(cfg);matched['correlations']=[1.]
        packets=np.repeat(known['incoming'].reshape(1,16,4096),4,axis=0)
        t=time.process_time();new=serial.rebuild(packets,np.zeros((16,16,16),bool),34000,14,matched)
        timings['known_matched_four_arms']=time.process_time()-t
        for key in ('end','mean_ports','outgoing'):
            expected=known[key].reshape((1,16)+known[key].shape[3:])
            equal(new[key],np.repeat(expected,4,axis=0),'four-arm native '+key)
        equal(new['birth'],known['birth'].reshape(16,2,16,16),'known reset')
        equal(new['masks'],known['masks'].reshape(16,16,16),'known injury')
        old=arrays(ROOT/'sources/exposed_continuation_081000.npz')
        incoming=np.repeat(old['incoming'][0,0:1],4,axis=0)
        t=time.process_time();prepared,details=serial.prepare(incoming,np.ones((4,16),bool),cfg)
        timings['sixty_four_checked_repairs']=time.process_time()-t
        equal(prepared,np.repeat(old['prepared'][0,1:2],4,axis=0),'known first repair')
        exposed=copy.deepcopy(cfg);exposed['innovation_namespace']='P05_cue_noise_repair_v0_1'
        identity='P05_serial_repair_v0_1:81000'
        t=time.process_time();first=serial.rebuild(prepared,np.zeros((16,16,16),bool),identity,15,exposed)
        timings['known_independent_first']=time.process_time()-t
        for key in ('end','outgoing','mean_ports'):equal(first[key],np.repeat(old[key][0,1:2],4,axis=0),'known first read '+key)
        selection=[0,1,2,1];packets=old['prepared'][-1,selection]
        t=time.process_time();terminal=serial.rebuild(packets,old['masks'][-2],identity,32,exposed)
        timings['known_independent_terminal']=time.process_time()-t
        for key,value in terminal.items():
            expected=old[key][-1]
            if key=='port_windows':expected=expected[:,selection]
            elif key not in ('birth','masks','noise_moments'):expected=expected[selection]
            equal(value,expected,'known terminal '+key)
        t=time.process_time()
        flat=audit_reader.replay(packets[:,14],terminal['masks'][14],3,2,identity,0,exposed,original=True,generation=32,rhos=[0.]*4)
        timings['four_arm_flat_read']=time.process_time()-t
        equal(flat['end'][0],terminal['end'][:,14],'flat known body')
        equal(flat['port_windows'][0],terminal['port_windows'][:,:,14],'flat known windows')
        t=time.process_time();moments=audit_noise(identity,32,exposed)
        timings['noise_audit']=time.process_time()-t
        np.testing.assert_allclose(moments,terminal['noise_moments'],rtol=1e-13,atol=1e-8)
        t=time.process_time()
        policy.select(packets,np.ones((4,16),int),34000,16,cfg,read(ROOT/'development/MODEL.json'))
        timings['sixteen_warning_diagnostics']=time.process_time()-t
        renewal=max(timings[k] for k in ('known_matched_four_arms','known_independent_first','known_independent_terminal'))
        forecast=1.5*16*(timings['known_teaching']+timings['known_flat_teaching']+14*timings['known_history_renewal']
            +18*(renewal+timings['noise_audit'])+720/64*timings['sixty_four_checked_repairs']
            +5*timings['four_arm_flat_read']+17*timings['sixteen_warning_diagnostics'])+240
        result=dict(status='COMPLETE',at_utc=stamp(),code_sha256=bound,config_sha256=sha(ROOT/'config.json'),
            sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'),byte_equal=True,new_scientific_outcomes=0,
            measured_cpu_seconds=timings,forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * 16 * (teaching + flat teaching + 14 single-arm history renewals + 18 * (max four-arm renewal + noise audit) + 720/64 * 64 checked repairs + 5 four-arm flat reads + 17 warning batches) + 240')
        write(folder/'COMPLETE.json',result)
        assert result['within_ceiling'],'Forecast exceeds the frozen 180 CPU-minute ceiling'
        print(__import__('json').dumps(result,indent=2),flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
