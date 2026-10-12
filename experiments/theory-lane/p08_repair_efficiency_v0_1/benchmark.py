"""Full native budgets on exposed fixtures, before any prospective generation."""
import copy
import time
import numpy as np
import acquire
import audit_acquire
import audit_reader
import lineage_dynamics as dynamics
import serial
from audit_serial import audit_noise
from common import ROOT,read,write,arrays,equal,stamp,sha


def main(folder,cfg):
    folder.mkdir(exist_ok=False);timings={};known=arrays(ROOT/'sources/native_controls.npz')
    teaching=arrays(ROOT/'sources/teaching_controls.npz')
    t=time.process_time();new=acquire.teach(34000,cfg['development_config']);timings['known_teaching']=time.process_time()-t
    t=time.process_time();flat=audit_acquire.teach(34000,cfg['development_config']);timings['known_flat_teaching']=time.process_time()-t
    for key,value in new.items():
        equal(value,teaching['teach_'+key],'native teaching '+key);equal(value,flat[key],'flat teaching '+key)
    t=time.process_time();native=dynamics.rebuild(known['incoming'],34000,14,['exact_rewrite'],cfg['development_config'],cfg['cycle'],cfg['tolerance'])
    timings['known_history_renewal']=time.process_time()-t
    for key in ('birth','end','masks','mean_ports','outgoing'):equal(native[key],known[key],'known history '+key)
    matched=copy.deepcopy(cfg);matched['correlations']=[1.]
    packets=np.repeat(known['incoming'].reshape(1,16,4096),3,axis=0)
    t=time.process_time();native=serial.rebuild(packets,np.zeros((16,16,16),bool),34000,14,matched)
    timings['known_matched_three_arms']=time.process_time()-t
    for key in ('end','mean_ports','outgoing'):
        expected=known[key].reshape((1,16)+known[key].shape[3:]);equal(native[key],np.repeat(expected,3,axis=0),'known three-arm '+key)
    equal(native['birth'],known['birth'].reshape(16,2,16,16),'known reset');equal(native['masks'],known['masks'].reshape(16,16,16),'known injury')
    old=arrays(ROOT/'sources/known_continuation_082000.npz');lineage=arrays(ROOT/'sources/known_lineage_082000.npz')
    exposed=read(ROOT/'sources/known_config.json');previous=lineage['masks'][-1]
    incoming=np.repeat(old['incoming'][0,0:1],3,axis=0)
    t=time.process_time();prepared,details=serial.prepare(incoming,np.ones((3,16),bool),cfg)
    timings['forty_eight_checked_repairs']=time.process_time()-t
    t=time.process_time();first=serial.rebuild(prepared,previous,serial.seed_identity(82000,exposed),15,exposed)
    timings['known_independent_first']=time.process_time()-t
    serial.check_first(dict(incoming=incoming,prepared=prepared,**details,**first,**serial.score(first['mean_ports'])),old)
    selection=[0,2,4];packets=old['prepared'][-1,selection]
    t=time.process_time();last=serial.rebuild(packets,old['masks'][-2],serial.seed_identity(82000,exposed),32,exposed)
    timings['known_independent_terminal']=time.process_time()-t
    for key,value in last.items():
        expected=old[key][-1]
        if key=='port_windows':expected=expected[:,selection]
        elif key not in ('birth','masks','noise_moments'):expected=expected[selection]
        equal(value,expected,'known terminal '+key)
    t=time.process_time();flat=audit_reader.replay(packets[:,14],last['masks'][14],3,2,serial.seed_identity(82000,exposed),0,exposed,original=True,generation=32,rhos=[0.]*3)
    timings['three_arm_flat_read']=time.process_time()-t
    equal(flat['end'][0],last['end'][:,14],'flat body');equal(flat['port_windows'][0],last['port_windows'][:,:,14],'flat windows')
    t=time.process_time();noise=audit_noise(serial.seed_identity(82000,exposed),32,exposed);timings['noise_audit']=time.process_time()-t
    np.testing.assert_allclose(noise,last['noise_moments'],rtol=1e-13,atol=1e-8)
    renewal=max(timings[k] for k in ('known_matched_three_arms','known_independent_first','known_independent_terminal'))
    forecast=1.5*len(cfg['blocks'])*(timings['known_teaching']+timings['known_flat_teaching']+14*timings['known_history_renewal']+
        18*(renewal+timings['noise_audit'])+400/48*timings['forty_eight_checked_repairs']+5*timings['three_arm_flat_read'])+600
    result=dict(status='COMPLETE',at_utc=stamp(),byte_equal=True,new_test_outcomes=0,measured_cpu_seconds=timings,
        code_sha256={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))},config_sha256=sha(ROOT/'config.json'),
        forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
        formula='1.5 * Nblocks * (teaching + flat teaching + 14 history renewals + 18 * (max three-arm renewal + noise audit) + 400/48 * 48 checked repairs + 5 flat three-arm reads) + 600')
    write(folder/'COMPLETE.json',result)
    assert result['within_ceiling'],'Measured forecast exceeds the frozen 15 CPU-hour ceiling'
    return result
