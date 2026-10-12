"""Known original-stream replay only; no new readout outcomes."""
import time
import traceback

import numpy as np

from common import ROOT,arrays,equal,read,sha,stamp,validate,write
from reader import generators,read_fixed,scores


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    prepared=read(ROOT/'prepared/COMPLETE.json')
    assert prepared['config_sha256']==sha(ROOT/'config.json')
    for name,digest in prepared['code_sha256'].items():
        assert sha(ROOT/name)==digest
    folder=ROOT/'benchmark';folder.mkdir(exist_ok=False)
    code={n:sha(ROOT/n) for n in ('common.py','reader.py','benchmark.py')}
    write(folder/'START.json',dict(status='RUNNING',created_at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),code_sha256=code))
    try:
        block=cfg['benchmark']['block']
        name=f'cases_{block:06d}.npz'
        source=arrays(ROOT/'prepared'/name,prepared['outputs_sha256'][name])
        packets=np.repeat(source['packets'][:,0:1],3,axis=1)
        random=generators(cfg,block,range(2),original=True)
        begin=time.perf_counter()
        raw=read_fixed(packets,source['masks'],source['founders'],source['recipients'],random,
                       cfg['reader'],[2048],cfg['settling_steps'])
        seconds=time.perf_counter()-begin
        for rep in range(2):
            equal(raw['birth'][:,rep],source['original_birth'],'known native birth')
            for variant in range(3):
                equal(raw['end'][0,:,variant,rep],source['original_end'],'known native endpoint')
                equal(raw['mean_ports'][0,:,variant,rep],source['original_mean_ports'],'known native mean ports')
        assert not scores(raw['mean_ports'],source['founders'],.25)['both_pass'].any()
        scientific_multiplier=(64/len(packets))*(16/2)*(4096/2048)
        replay_multiplier=(64/len(packets))*(1/2)*(1/3)
        forecast=1.5*seconds*(scientific_multiplier+replay_multiplier)+180
        receipt=dict(status='COMPLETE',completed_at_utc=stamp(),config_sha256=sha(ROOT/'config.json'),code_sha256=code,
            block=block,cases=len(packets),variants=3,replicates=2,budget=2048,byte_equal=True,
            measured_seconds=seconds,forecast_cpu_seconds=forecast,within_ceiling=forecast<=cfg['forecast_ceiling_cpu_seconds'],
            scientific_multiplier=scientific_multiplier,known_replay_multiplier=replay_multiplier,
            formula='1.5 * measured seconds * (scientific cell-update ratio + known-replay ratio) + 180',
            new_scientific_outcomes=False)
        write(folder/'COMPLETE.json',receipt)
        print(receipt,flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    main()
