"""Independent acquisition, source chain, body, substitution and inference replay."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus,dump,sha,utc
from E015_functional_inheritance.audit import verify,random,EXPECTED,pack,unpack
from E055_stress_capture_recovery import audit_model as pulse
from E056_sign_magnitude_substitution import audit_model as factorial
from E056_sign_magnitude_substitution.audit import independent_values as factorial_values
from E057_fresh_capture_confirmation import source_audit, data
from E057_fresh_capture_confirmation.plan import HERE,ROOT,NAMES,PRIMARY,HISTORIES,settings


def validate_settings(cfg):
    mode=cfg['mode']; science=mode=='scientific'; fixture=mode=='fixture'
    expected=dict(EXPECTED)
    if fixture:expected.update(recipients=2,teach_steps=12,capture_steps=6,observe_steps=4)
    elif not science:expected['recipients']=1
    assert cfg['config']==expected
    assert cfg['cycle']==dict(generations=32,read_steps=2048 if science else 24 if fixture else 128,
        settling_steps=1024 if science else 12 if fixture else 64,write_steps=8 if fixture else 128)
    R=4 if science else 2 if fixture else 1
    assert cfg['body']==dict(recipients=R,body_pre_steps=2048 if science else 16 if fixture else 128,
        body_settling_steps=1024 if science else 8 if fixture else 64,pulse_steps=32 if science else 4 if fixture else 8,
        recovery_steps=512 if science else 8 if fixture else 32,observe_steps=32 if science else 4 if fixture else 8,
        pulse_sites=64,pulse_amplitude=1.,dt=.2,noise=.02,birth_sd=.05,writer_beta=3.,margin=.25)
    assert cfg['reader']==dict(recipients=R,read_steps=2048 if science else 24 if fixture else 512,
        settling_steps=1024 if science else 12 if fixture else 256,observe_steps=4 if fixture else 32,
        dt=.2,noise=.02,birth_sd=.05,margin=.25,dtype='float64',normalization_floor=0.,
        cue_birth_correlation=1.,cue_noise_correlation=1.)
    assert cfg['blocks']==(list(range(38000,38032)) if science else [900041])
    assert cfg['primary']==['early_pulse_loss','timing_benefit','magnitude_on_pulse_signs','magnitude_on_sham_signs']
    assert cfg['histories']==['acquired','paired_rewrite','independent_rewrite']
    assert cfg['primary_confidence']==.9875 and cfg['primary_family_size']==4 and cfg['bootstrap_samples']==10000
    assert cfg['fresh_sources']==science and cfg['prior_cases_pooled'] is False


def added_cases(body,outgoing,source_ports,cfg):
    result={f'body_{k}':v for k,v in pulse.score(body['mean_ports'],cfg['body']['margin']).items()}
    result.update({f'source_{k}':v for k,v in pulse.score(np.array(source_ports),cfg['config']['margin']).items()})
    result['body_displacement']=np.abs(body['states'][:,1]-body['states'][:,0]).mean(axis=(-3,-2,-1))
    result['fallback_count']=outgoing['fallback'].sum(axis=(-3,-2,-1))
    for name in ('requested_squared','delivered_squared','clipping_count'):
        result['pulse_'+name]=body[name].mean(axis=-1)
    return result


def body_controls(body,outgoing,cfg):
    return dict(before_equal=bool(np.array_equal(body['states'][:,0,0],body['states'][:,1,0])),
        pulse_excludes_ports=bool(not (body['pulse_sites']&pulse.P.any(axis=0)).any()),
        pulse_excludes_absent=bool(not (body['pulse_sites']&body['masks']).any()),
        pulse_site_count=bool(np.all(body['pulse_sites'].sum(axis=(-2,-1))==cfg['body']['pulse_sites'])),
        protected_packets_equal=bool(np.array_equal(outgoing['packets'][:,4],outgoing['packets'][:,5])))


def worker(run,b,cfg):
    start=time.monotonic();reference=data.receipt(cfg['mode'])
    acquisition=data.load(run/f'acquisition_{b:06d}.npz')
    acquired,_=source_audit.source_record(acquisition,b,cfg['config'])
    if reference is not None:data.compare(acquisition,data.load(reference/f'source_{b:06d}.npz'))
    initial=acquired[:,None].repeat(cfg['config']['recipients'],axis=1)
    packets=np.stack((initial,initial));source_ports=[]
    for g in range(1,33):
        raw=source_audit.rebuild(packets,b,g,cfg['config'],cfg['cycle'])
        data.compare(raw,data.load(run/f'boundary_{b:06d}_g{g}.npz'))
        if reference is not None:data.legacy_boundary(reference,b,g,raw)
        source_ports.append(raw['mean_ports']);packets=raw['outgoing'].copy()
    records=np.empty((3,4,cfg['config']['recipients'],2,16,16))
    records[0]=unpack(initial);records[1:]=unpack(packets)
    source=dict(records=records,source_last_masks=raw['masks'])
    data.compare(source,data.load(run/f'source_{b:06d}.npz'))
    source_seconds=time.monotonic()-start;begin=time.monotonic()
    body=pulse.develop(records,b,cfg['body']);data.compare(body,data.load(run/f'body_{b:06d}.npz'))
    outgoing=pulse.transmit(body,cfg['body']);data.compare(outgoing,data.load(run/f'outgoing_{b:06d}.npz'))
    perturb_seconds=time.monotonic()-begin;begin=time.monotonic()
    packets=np.empty((3,2,2,*outgoing['packets'].shape[2:]),np.uint8)
    for t,p in np.ndindex(2,2):packets[:,t,p]=outgoing['packets'][:,2*t+p]
    paired=dict(packets=packets);data.compare(paired,data.load(run/f'paired_{b:06d}.npz'))
    inter=factorial.intervene(packets);data.compare(inter,data.load(run/f'interventions_{b:06d}.npz'))
    fresh=factorial.assay(inter['packets'],b,cfg['reader']);data.compare(fresh,data.load(run/f'assay_{b:06d}.npz'))
    cases,controls=factorial.diagnostics(paired,inter,fresh,cfg['reader'])
    cases.update(added_cases(body,outgoing,source_ports,cfg));data.compare(cases,data.load(run/f'cases_{b:06d}.npz'))
    controls.update(body_controls(body,outgoing,cfg));controls['pass']=all(v for k,v in controls.items() if k!='pass')
    receipt=json.loads((run/f'worker_{b}.json').read_text())
    assert receipt['controls']==controls and receipt['block']==b and receipt['legacy_32_boundaries_match']==(reference is not None)
    dump(run/f'audit_worker_{b}.json',dict(status='PASS',block=b,seconds=time.monotonic()-start,controls=controls,
        stage_seconds=dict(source=source_seconds,perturb=perturb_seconds,assay=time.monotonic()-begin),
        legacy_32_boundaries_match=reference is not None))


def independent_values(cases):
    out=factorial_values(cases)
    q=np.array([[[c['fresh_both'][1,t,a,1].mean() for a in range(4)] for t in range(2)] for c in cases])
    out['primary/early_pulse_loss']=q[:,0,0]-q[:,0,1]
    out['primary/timing_benefit']=(q[:,1,1]-q[:,1,0])-(q[:,0,1]-q[:,0,0])
    out['primary/magnitude_on_pulse_signs']=q[:,0,3]-q[:,0,1]
    out['primary/magnitude_on_sham_signs']=q[:,0,0]-q[:,0,2]
    for h,history in enumerate(HISTORIES):
        for metric in ('both','transfer','aligned_transfer','minimum_margin'):
            for p,treatment in enumerate(('sham','pulse')):
                for t,time in enumerate(('before','early','late')):
                    out[f'body/{metric}/{history}/{treatment}/{time}']=np.array([c['body_'+metric][h,p,t].mean() for c in cases])
            if h>0:
                for g in range(cases[0]['source_'+metric].shape[0]):
                    out[f'source/{metric}/{history}/g{g+1}']=np.array([c['source_'+metric][g,h-1].mean() for c in cases])
        for t,time in enumerate(('before','early','late')):
            out[f'body/displacement/{history}/{time}']=np.array([c['body_displacement'][h,t].mean() for c in cases])
        for metric in ('requested_squared','delivered_squared','clipping_count'):
            out[f'pulse/{metric}/{history}']=np.array([c['pulse_'+metric][h].mean() for c in cases])
        for a,arm in enumerate(('sham_early','pulse_early','sham_late','pulse_late')):
            out[f'capture/fallback/{history}/{arm}']=np.array([c['fallback_count'][h,a].mean() for c in cases])
    return out


def check_summary(summary,cases,controls,mode):
    values=independent_values(cases);stats=summary['statistics'];assert set(values)==set(stats)
    draws=random('E057','bootstrap','fresh_confirmation').integers(0,len(cases),(10000,len(cases)))
    for key,x in values.items():
        confidence=.9875 if key.startswith('primary/') else .95;tail=(1-confidence)/2
        expected=dict(mean=float(x.mean()),interval=np.quantile(x[draws].mean(axis=1),[tail,1-tail]).tolist(),
            confidence=confidence,block_means=x.tolist())
        assert set(expected)==set(stats[key])
        for name in expected:np.testing.assert_allclose(expected[name],stats[key][name],rtol=1e-13,atol=1e-13)
    ok=all(c['pass'] for c in controls);enabled=mode=='scientific' and ok;labels={}
    for name in PRIMARY:
        lo,hi=stats['primary/'+name]['interval']
        labels[name]=('POSITIVE_EFFECT' if lo>0 else 'NEGATIVE_EFFECT' if hi<0 else 'UNRESOLVED') if enabled else None
    passed=all(v=='POSITIVE_EFFECT' for v in labels.values()) if enabled else None
    status='TECHNICAL_ONLY' if mode!='scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else 'CONFIRMED' if passed else 'NOT_CONFIRMED'
    assert summary['status']==status and summary['primary_confirmed']==passed
    assert summary['primary_effects']==labels and summary['controls_pass']==ok and summary['controls_by_block']==controls
    assert summary['primary_family_size']==4 and summary['primary_confidence']==.9875
    assert summary['primary_history']=='paired_rewrite' and summary['primary_injury']=='scattered'
    assert summary['independent_blocks']==len(cases) and not summary['cohort_reused'] and not summary['prior_cases_pooled']
    assert summary['fresh_scientific_sources']==(mode=='scientific') and summary['prior_discovery_outcomes_seen']
    return len(values)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=NAMES)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int);a=p.parse_args()
    assert 1<=a.workers<=8;cap_cpus(a.workers);cfg=settings(a.mode);validate_settings(cfg)
    run=HERE/'runs'/NAMES[a.mode]
    if a.worker is not None:
        assert a.worker in cfg['blocks'];worker(run,a.worker,cfg);return
    start=time.monotonic();manifest=verify(run);contract=manifest['contract']
    assert contract['experiment']=='E057'
    for key,value in cfg.items():assert contract[key]==value,key
    assert not (run/'INDEPENDENT_AUDIT.json').exists()
    def launch(b):
        with (run/f'audit_worker_{b}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'audit.py'),'--mode',a.mode,'--workers',str(a.workers),'--worker',str(b)],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        return b
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for b in pool.map(launch,cfg['blocks']):print('Independently replayed block',b,flush=True)
    workers=[json.loads((run/f'audit_worker_{b}.json').read_text()) for b in cfg['blocks']]
    summary=json.loads((run/'summary.json').read_text())
    checked=check_summary(summary,[data.load(run/f'cases_{b:06d}.npz') for b in cfg['blocks']],
        [w['controls'] for w in workers],a.mode)
    verify(run);R=cfg['config']['recipients'];B=len(cfg['blocks'])
    dump(run/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,
        complete_sha256=sha(run/'COMPLETE.json'),audit_code_sha256=sha(__file__),summaries_checked=checked,
        all_acquisition_and_32_source_boundaries_replayed=True,all_sources_substitutions_assays_diagnostics_replayed=True,
        every_step_state_hashes_replayed=True,controls_pass=summary['controls_pass'],primary_effects=summary['primary_effects'],
        primary_confirmed=summary['primary_confirmed'],worker_seconds=[w['seconds'] for w in workers],
        terminal_cue_observations=B*30*4*R*2*3,source_body_cue_observations=B*32*2*4*R*2,
        perturb_body_cue_observations=B*3*2*3*4*R*2))


if __name__=='__main__':main()
