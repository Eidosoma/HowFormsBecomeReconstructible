"""Benchmark only exposed reads at the exact single-arm shape; no withdrawal outcomes."""
import copy
import time
import traceback
import numpy as np
import audit_reader
from audit_serial import audit_noise
from common import ROOT,read,write,sha,arrays,equal,stamp,validate
from serial import rebuild,prepare,seed_identity,check_first,score


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    bound={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),code_sha256=bound,config_sha256=sha(ROOT/'config.json')))
    try:
        timings={};known=arrays(ROOT/'sources/native_controls.npz')
        matched=copy.deepcopy(cfg);matched['correlations']=[1.]
        t=time.process_time()
        native=rebuild(known['incoming'].reshape(1,16,4096),np.zeros((16,16,16),bool),34000,14,matched)
        timings['native_known_single_arm']=time.process_time()-t
        for key in ('end','mean_ports','outgoing'):
            equal(native[key],known[key].reshape((1,16)+known[key].shape[3:]),'known native '+key)
        equal(native['birth'],known['birth'].reshape(16,2,16,16),'known reset')
        equal(native['masks'],known['masks'].reshape(16,16,16),'known injury')
        controls=arrays(ROOT/'sources/controls_081000.npz');boundary=arrays(ROOT/'sources/boundaries.npz')
        t=time.process_time();prepared,details=prepare(boundary['initial_packets'][0][None],81000,15,cfg)
        timings['sixteen_checked_repairs']=time.process_time()-t
        t=time.process_time()
        first=rebuild(prepared,boundary['previous_masks'][0],seed_identity(81000,cfg),15,cfg)
        timings['known_independent_first']=time.process_time()-t
        check_first(dict(generation=np.array(15),incoming=boundary['initial_packets'][0][None],
            prepared=prepared,**details,**first,**score(first['mean_ports'])),controls)
        # A later baseline read uses its exposed prepared packet, not a withdrawn-repair successor.
        t=time.process_time()
        terminal=rebuild(controls['prepared'][-1,0:1],controls['masks'][-2],seed_identity(81000,cfg),32,cfg)
        timings['known_independent_terminal']=time.process_time()-t
        for key,value in terminal.items():
            expected=controls[key][-1]
            if key=='port_windows':expected=expected[:,0:1]
            elif key not in ('birth','masks','noise_moments'):expected=expected[0:1]
            equal(value,expected,'known later baseline '+key)
        t=time.process_time()
        flat=audit_reader.replay(controls['prepared'][-1,0:1,14],terminal['masks'][14],3,2,
            seed_identity(81000,cfg),0,cfg,original=True,generation=32,rhos=[0.])
        timings['single_arm_flat_read']=time.process_time()-t
        equal(flat['end'][0],terminal['end'][:,14],'flat known independent body')
        equal(flat['port_windows'][0],terminal['port_windows'][:,:,14],'flat known windows')
        t=time.process_time();moments=audit_noise(seed_identity(81000,cfg),32,cfg)
        timings['independent_noise_audit']=time.process_time()-t
        np.testing.assert_allclose(moments,terminal['noise_moments'],rtol=1e-13,atol=1e-8)
        renewal=max(timings[k] for k in ('native_known_single_arm','known_independent_first','known_independent_terminal'))
        forecast=1.5*16*(18*(renewal+timings['independent_noise_audit'])+timings['sixteen_checked_repairs']+4*timings['single_arm_flat_read'])+180
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),code_sha256=bound,
            config_sha256=sha(ROOT/'config.json'),sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'),
            byte_equal=True,first_repair_and_reconstruction_byte_equal=True,new_continuation_outcomes=0,
            new_scientific_outcomes=False,measured_cpu_seconds=timings,forecast_cpu_seconds=forecast,
            within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * 16 * (18 * (max known single-arm renewal + independent noise audit) + 16 checked repairs + 4 single-arm flat reads) + 180'))
        print('Known matched/independent reads and first repair agree byte for byte. Forecast %.2f CPU minutes; ceiling 60.'%(forecast/60),flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
