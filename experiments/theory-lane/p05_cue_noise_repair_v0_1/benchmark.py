"""Time six-arm known matched controls and noise diagnostics, no new cohort outcomes."""
import copy
import time
import traceback
import numpy as np
import audit_reader
from audit_serial import audit_noise
from common import ROOT,read,write,sha,arrays,equal,stamp,validate
from serial import rebuild,prepare,seed_identity


def main():
    cfg=read(ROOT/'config.json');validate(cfg);sources=read(ROOT/'sources/COMPLETE.json')
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    names=('benchmark.py','common.py','serial.py','lineage_dynamics.py','repair.py','optimizer.py',
           'audit_optimizer.py','audit_serial.py','audit_reader.py','reader.py','sign_graph.py','writer_audit.py')
    bound={n:sha(ROOT/n) for n in names}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),code_sha256=bound,config_sha256=sha(ROOT/'config.json')))
    try:
        timings={};matched=copy.deepcopy(cfg);matched['correlations']=[1.,1.,1.]
        known=arrays(ROOT/'sources/native_controls.npz')
        packets=np.repeat(known['incoming'].reshape(1,16,4096),6,axis=0)
        t=time.process_time();raw=rebuild(packets,np.zeros((16,16,16),bool),34000,14,matched)
        timings['native_six_arm_renewal']=time.process_time()-t
        for k in ('end','mean_ports','outgoing'):
            expected=np.repeat(known[k].reshape((1,16)+known[k].shape[3:]),6,axis=0)
            equal(raw[k],expected,'archival native '+k)
        equal(raw['birth'],known['birth'].reshape(16,2,16,16),'native birth')
        equal(raw['masks'],known['masks'].reshape(16,16,16),'native injury')
        t=time.process_time()
        audited=audit_reader.replay(packets[:,0],raw['masks'][0],0,0,34000,0,matched,original=True,generation=14)
        timings['six_arm_flat_read']=time.process_time()-t
        equal(audited['end'][0],raw['end'][:,0],'flat native body')
        equal(audited['port_windows'][0],raw['port_windows'][:,:,0],'flat native windows')
        exposed=arrays(ROOT/'sources/matched_081000.npz')
        boundary=arrays(ROOT/'sources/boundaries.npz')
        packets=np.concatenate([exposed['prepared'][0]]*3,axis=0)
        t=time.process_time()
        current=rebuild(packets,boundary['previous_masks'][0],seed_identity(81000,cfg),15,matched)
        timings['previous_six_arm_renewal']=time.process_time()-t
        for k in ('end','mean_ports','outgoing'):
            equal(current[k],np.concatenate([exposed[k][0]]*3,axis=0),'previous known control '+k)
        equal(current['port_windows'],np.concatenate([exposed['port_windows'][0]]*3,axis=1),'previous windows')
        equal(current['masks'],exposed['masks'][0],'previous masks')
        equal(current['birth'],exposed['birth'][0],'previous reset')
        # Only already exposed inputs are repaired; their new variants are not read.
        incoming=np.repeat(known['outgoing'].reshape(1,16,4096),6,axis=0)
        t=time.process_time();_,details=prepare(incoming,34000,15,cfg)
        timings['forty_eight_checked_repairs']=time.process_time()-t
        assert int(details['independent_optimizer_checks'])==48
        t=time.process_time();moment_reference=audit_noise(34000,14,matched)
        timings['noise_audit']=time.process_time()-t
        np.testing.assert_allclose(moment_reference,raw['noise_moments'],rtol=1e-13,atol=1e-8)
        # Bound actual three-correlation audit cost using Gaussian draws alone.
        t=time.process_time();audit_noise('synthetic_benchmark_only',14,cfg)
        timings['three_correlation_noise_audit']=time.process_time()-t
        renewal=max(timings['native_six_arm_renewal'],timings['previous_six_arm_renewal'])
        noise_check=max(timings['noise_audit'],timings['three_correlation_noise_audit'])
        forecast=1.5*16*(18*(renewal+timings['forty_eight_checked_repairs']+noise_check)+2*timings['six_arm_flat_read'])+300
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),code_sha256=bound,
            config_sha256=sha(ROOT/'config.json'),sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'),
            byte_equal=True,previous_matched_replay_byte_equal=True,new_continuation_outcomes=0,
            new_scientific_outcomes=False,measured_cpu_seconds=timings,forecast_cpu_seconds=forecast,
            within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * 16 * (18 * (max known six-arm renewal + 48 checked repairs + max noise audit) + 2 six-arm flat reads) + 300'))
        print('Known native and prior matched controls pass. Forecast %.2f CPU minutes; ceiling 180.'%(forecast/60),flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
