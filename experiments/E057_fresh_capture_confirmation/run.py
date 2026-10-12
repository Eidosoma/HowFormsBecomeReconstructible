"""Acquire fresh records, rebuild 32 times, perturb/capture and substitute."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,check_inputs,dump,finish,new_run
from E055_stress_capture_recovery import model as pulse
from E056_sign_magnitude_substitution import model as factorial
from E057_fresh_capture_confirmation import source_model, data, inference
from E057_fresh_capture_confirmation.plan import HERE,ROOT,NAMES,settings
import numpy as np


def input_paths():
    external=('common.py','run_python.sh','RUN_POLICY.md','SOURCE_SNAPSHOT.json','SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py','E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py','E017_reader_timing/model.py','E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py','E022_reader_compensation/audit.py',
        'E054_record_interventions/model.py','E054_record_interventions/audit_model.py','E054_record_interventions/plan.py',
        'E055_stress_capture_recovery/model.py','E055_stress_capture_recovery/audit_model.py','E055_stress_capture_recovery/plan.py',
        'E056_sign_magnitude_substitution/model.py','E056_sign_magnitude_substitution/audit_model.py',
        'E056_sign_magnitude_substitution/plan.py','E056_sign_magnitude_substitution/inference.py',
        'E056_sign_magnitude_substitution/audit.py','E056_sign_magnitude_substitution/data.py')
    local=('PROTOCOL.md','SOURCE_DATA.json','plan.py','source_model.py','source_audit.py','data.py',
        'inference.py','run.py','audit.py','tests.py','workflow.py','plot.py','analysis/prepare.py')
    return [ROOT/p for p in external]+[HERE/p for p in local]


def block(run,b,cfg):
    start=time.monotonic(); reference=data.receipt(cfg['mode'])
    config=source_model.base.Config(**cfg['config']); R=config.recipients
    acquisition=source_model.acquisition.teach(b,config)
    data.save(run/f'acquisition_{b:06d}.npz',acquisition)
    if reference is not None:data.compare(acquisition,data.load(reference/f'source_{b:06d}.npz'))
    initial=acquisition['acquired'][1,:,None].repeat(R,axis=1)
    packets=initial[None].repeat(2,axis=0); source_ports=[]
    for g in range(1,cfg['cycle']['generations']+1):
        raw=source_model.rebuild(packets,b,g,config,cfg['cycle'])
        data.save(run/f'boundary_{b:06d}_g{g}.npz',raw)
        if reference is not None:data.legacy_boundary(reference,b,g,raw)
        source_ports.append(raw['mean_ports']);packets=raw['outgoing'].copy()
    records=np.concatenate((source_model.base.decode(initial)[None],source_model.base.decode(packets)))
    source=dict(records=records,source_last_masks=raw['masks'])
    data.save(run/f'source_{b:06d}.npz',source)
    source_seconds=time.monotonic()-start; begin=time.monotonic()
    body=pulse.develop(records,b,cfg['body']); outgoing=pulse.transmit(body,cfg['body'])
    data.save(run/f'body_{b:06d}.npz',body); data.save(run/f'outgoing_{b:06d}.npz',outgoing)
    perturb_seconds=time.monotonic()-begin; begin=time.monotonic()
    paired=dict(packets=np.stack((outgoing['packets'][:,:2],outgoing['packets'][:,2:4]),axis=1))
    inter=factorial.intervene(paired['packets']); fresh=factorial.assay(inter['packets'],b,cfg['reader'])
    cases,controls=factorial.diagnostics(paired,inter,fresh,cfg['reader'])
    cases.update({'body_'+k:v for k,v in pulse.score(body['mean_ports'],cfg['body']['margin']).items()})
    cases.update({'source_'+k:v for k,v in pulse.score(np.stack(source_ports),config.margin).items()})
    cases['body_displacement']=abs(body['states'][:,1]-body['states'][:,0]).mean(axis=(-3,-2,-1))
    cases['fallback_count']=outgoing['fallback'].sum(axis=(-3,-2,-1))
    for key in ('requested_squared','delivered_squared','clipping_count'):cases['pulse_'+key]=body[key].mean(axis=-1)
    controls.update(before_equal=bool(np.array_equal(body['states'][:,0,0],body['states'][:,1,0])),
        pulse_excludes_ports=bool(not body['pulse_sites'][...,pulse.P.any(axis=0)].any()),
        pulse_excludes_absent=bool(not (body['pulse_sites']&body['masks']).any()),
        pulse_site_count=bool((body['pulse_sites'].sum(axis=(-2,-1))==cfg['body']['pulse_sites']).all()),
        protected_packets_equal=bool(np.array_equal(outgoing['packets'][:,4],outgoing['packets'][:,5])))
    controls['pass']=all(v for k,v in controls.items() if k!='pass')
    for name,arrays in (('paired',paired),('interventions',inter),('assay',fresh),('cases',cases)):
        data.save(run/f'{name}_{b:06d}.npz',arrays)
    dump(run/f'worker_{b}.json',dict(block=b,seconds=time.monotonic()-start,controls=controls,
        stage_seconds=dict(source=source_seconds,perturb=perturb_seconds,assay=time.monotonic()-begin),
        legacy_32_boundaries_match=reference is not None,terminal_cue_observations=30*4*R*2*3,
        source_body_cue_observations=32*2*4*R*2,perturb_body_cue_observations=3*2*3*4*R*2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=NAMES)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int);a=p.parse_args()
    assert 1<=a.workers<=8;cap_cpus(a.workers)
    run=HERE/'runs'/NAMES[a.mode];cfg=settings(a.mode)
    if a.worker is not None:
        check_inputs(run);assert a.worker in cfg['blocks'];block(run,a.worker,cfg);return
    job=HERE/'jobs'/NAMES[a.mode];check_inputs(job);check_inputs(HERE/'analysis/freeze_v1')
    assert json.loads((job/'status.json').read_text())['stage']=='simulation'
    started=time.monotonic()
    new_run(run,input_paths(),dict(experiment='E057',**cfg,workers=a.workers,
        predecessor_evidence=json.loads((job/'manifest.json').read_text())['contract']['predecessor_evidence']))
    def launch(b):
        with (run/f'worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'run.py'),'--mode',a.mode,'--workers',str(a.workers),'--worker',str(b)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        return b
    try:
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for b in pool.map(launch,cfg['blocks']):print('Completed simulation block',b,flush=True)
        cases=[data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']]
        controls=[json.loads((run/f'worker_{b}.json').read_text())['controls'] for b in cfg['blocks']]
        summary=inference.analyze(cases,controls,a.mode);dump(run/'summary.json',summary)
        (run/'REPORT.md').write_text(inference.report(summary))
        finish(run,started,dict(experiment='E057',blocks_completed=len(cfg['blocks'])))
    except BaseException:
        dump(run/'FAILED.json',dict(traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
