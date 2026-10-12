"""Time duplicated known reads only; do not expose fresh scientific outcomes."""
import time
import traceback
import numpy as np
from common import ROOT,arrays,equal,read,sha,stamp,validate,write
from reader import generators,read_fixed


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    prepared=read(ROOT/'prepared/COMPLETE.json')
    assert prepared['config_sha256']==sha(ROOT/'config.json')
    for name,digest in prepared['code_sha256'].items():assert sha(ROOT/name)==digest,name
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    code={n:sha(ROOT/n) for n in ('common.py','reader.py','benchmark.py')}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),code_sha256=code))
    try:
        block=cfg['benchmark']['block'];name=f'cases_{block:06d}.npz'
        data=arrays(ROOT/'prepared'/name,prepared['outputs_sha256'][name])
        v=cfg['benchmark']['variants'];r=cfg['benchmark']['replicates']
        packets=np.repeat(data['packets'][:,0:1],v,axis=1)
        begin=time.perf_counter()
        raw=read_fixed(packets,data['original_masks'],data['founders'],data['recipients'],
            generators(cfg,block,range(r),original=True),cfg['reader'],[2048],cfg['settling_steps'])
        elapsed=time.perf_counter()-begin
        for ri in range(r):
            equal(raw['birth'][:,ri],data['original_birth'],'known reset')
            for vi in range(v):
                equal(raw['end'][0,:,vi,ri],data['original_end'],'known body')
                equal(raw['mean_ports'][0,:,vi,ri],data['original_mean_ports'],'known output')
        measured=len(packets)*v*r*2048
        scientific=64*2*4*16*2048
        replay=64*2048
        audit=8*2*4*2048
        forecast=1.5*elapsed*(scientific+replay+audit)/measured+180
        write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),
            code_sha256=code,measured_seconds=elapsed,measured_trajectories=len(packets)*v*r,
            forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            formula='1.5 * measured seconds * (scientific + known replay + independent audit cell-updates) / measured cell-updates + 180',
            byte_equal=True,new_scientific_outcomes=False))
        print(f'Known native replay passed; measured {elapsed:.2f}s; forecast {forecast/60:.2f} minutes; ceiling {cfg["forecast_ceiling_cpu_seconds"]/60:.0f} minutes.',flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
