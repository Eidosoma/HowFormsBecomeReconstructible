"""Known full-budget reads at the exact three-arm shape; no budget-curve outcomes."""
import copy
import time
import numpy as np
import audit_reader
import serial
from audit_serial import audit_noise
from common import ROOT,read,write,arrays,equal,stamp
from source_data import load


def main(folder,cfg):
    folder.mkdir(exist_ok=False);timings={};known=arrays(ROOT/'sources/native_controls.npz')
    matched=copy.deepcopy(cfg);matched['correlations']=[1.]
    packets=np.repeat(known['incoming'].reshape(1,16,4096),3,axis=0)
    t=time.process_time();native=serial.rebuild(packets,np.zeros((16,16,16),bool),34000,14,matched)
    timings['known_matched_three_arms']=time.process_time()-t
    for key in ('end','mean_ports','outgoing'):
        expected=known[key].reshape((1,16)+known[key].shape[3:])
        equal(native[key],np.repeat(expected,3,axis=0),'known native '+key)
    equal(native['birth'],known['birth'].reshape(16,2,16,16),'known reset')
    equal(native['masks'],known['masks'].reshape(16,16,16),'known injury')
    initial,previous,controls=load(82000)
    t=time.process_time();prepared,details=serial.prepare(np.repeat(initial[None],3,axis=0),np.ones((3,16),bool),cfg)
    timings['forty_eight_checked_repairs']=time.process_time()-t
    t=time.process_time();first=serial.rebuild(prepared,previous,serial.seed_identity(82000,cfg),15,cfg)
    timings['known_independent_first']=time.process_time()-t
    serial.check_first(dict(incoming=np.repeat(initial[None],3,axis=0),prepared=prepared,**details,**first,**serial.score(first['mean_ports'])),controls)
    packets=controls['prepared'][-1,[0,1,0]]
    t=time.process_time();last=serial.rebuild(packets,controls['masks'][-2],serial.seed_identity(82000,cfg),32,cfg)
    timings['known_independent_terminal']=time.process_time()-t
    for key,value in last.items():
        expected=controls[key][-1]
        if key=='port_windows':expected=expected[:,[0,1,0]]
        elif key not in ('birth','masks','noise_moments'):expected=expected[[0,1,0]]
        equal(value,expected,'known terminal '+key)
    t=time.process_time()
    flat=audit_reader.replay(packets[:,14],last['masks'][14],3,2,serial.seed_identity(82000,cfg),0,cfg,original=True,generation=32,rhos=[0.]*3)
    timings['three_arm_flat_read']=time.process_time()-t
    equal(flat['end'][0],last['end'][:,14],'flat body');equal(flat['port_windows'][0],last['port_windows'][:,:,14],'flat windows')
    t=time.process_time();noise=audit_noise(serial.seed_identity(82000,cfg),32,cfg)
    timings['noise_audit']=time.process_time()-t
    np.testing.assert_allclose(noise,last['noise_moments'],rtol=1e-13,atol=1e-8)
    renewal=max(timings[k] for k in ('known_matched_three_arms','known_independent_first','known_independent_terminal'))
    forecast=1.5*16*(18*(renewal+timings['noise_audit'])+160/48*timings['forty_eight_checked_repairs']+4*timings['three_arm_flat_read'])+240
    result=dict(status='COMPLETE',at_utc=stamp(),byte_equal=True,new_frequency_outcomes=0,measured_cpu_seconds=timings,
        forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
        formula='1.5 * 16 * (18 * (max three-arm renewal + noise audit) + 160/48 * 48 checked repairs + 4 three-arm flat reads) + 240')
    write(folder/'COMPLETE.json',result)
    assert result['within_ceiling'],'Measured forecast exceeds the frozen 120 CPU-minute ceiling'
    return result
