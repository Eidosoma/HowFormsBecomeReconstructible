"""D167 qualified saved-stage audit; external, write-once execution and audit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import asymmetry_run as source, passive_stages as m, passive_stages_check as check

io=source.io;ROOT=source.ROOT;WS=source.WS
RUN='l20_extension1_passive_stages_v1_attempt1';OLD='l20_extension1_feature_support_v1_attempt1'
ENV='D167_DETACHED_STAGE'
COMPLETE='3d7e30319de5176b32ae6908fc894a9c5f6a9d09540d23376bc05bd8ca16a8ef'
AUDIT='63ef78549ebf56081aaf9e87138a5dfaefbc2fc05270981bab939f55ca3e05b4'
GUIDE='59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c'
IDS={'development':tuple(range(90000,90016)),'pilot':tuple(range(100000,100064))}
RAW={'development':'l20_extension1_heldout_v1_attempt1','pilot':source.PILOT}
EXTRA={'sites','permutation','input_strength','changed_sites'}
OUTPUTS=('stages.npz','summary.json','verification.json')
CONFIG=dict(amp_threshold=.2,generations=3,hold=1.2,lam=.001,lives=4,norm=.3,rescue_after=100,
    settle=120,source_steps=1000,steps=300,teaching=1000)


def science():
    return [WS/'passive-stages/PROTOCOL_V1.md',WS/'tests/test_passive_stages.py']+[
        WS/'src/l20_extension1'/f'{k}.py' for k in ('passive_stages','passive_stages_check','passive_stages_run')]


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def audit_path():return ROOT/'logs'/f'{RUN}_saved_audit_v1.json'


def raw_paths(co,index):
    assert co in IDS and type(index) is int and index in IDS[co]
    p=ROOT/'outputs'/RAW[co]/f'diagnostic_{index}.npz'
    return p,p.with_suffix('.json')


def source_inputs():
    seen={};run=ROOT/'runs'/OLD;out=ROOT/'outputs'/OLD
    receipt=ROOT/'logs'/f'{OLD}_saved_audit_v1.json';freeze=ROOT/'tmp'/f'{OLD}_freeze.json'
    source.bind(run/'COMPLETE.json',COMPLETE,seen);source.bind(receipt,AUDIT,seen)
    done=io.read_json(run/'COMPLETE.json');audit=io.read_json(receipt)
    assert done['status']=='COMPLETE' and audit['passes'] and audit['complete_sha256']==COMPLETE
    source.bind(freeze,done['freeze_sha256'],seen);source.bind(run/'MANIFEST.json',done['manifest_sha256'],seen)
    f=io.read_json(freeze);manifest=io.read_json(run/'MANIFEST.json')
    assert audit['freeze_sha256']==done['freeze_sha256']==manifest['freeze_sha256']
    assert manifest['input_sha256']==f['input_sha256'] and len(f['input_sha256'])==118
    assert set(done['output_sha256'])=={str(out/k) for k in ('support.npz','summary.json','verification.json')}
    for path,digest in {**f['input_sha256'],**done['output_sha256']}.items():source.bind(Path(path),digest,seen)
    pilot=ROOT/'runs'/source.PILOT
    pc=io.read_json(pilot/'COMPLETE.json');pm=io.read_json(pilot/'MANIFEST.json')
    pa=io.read_json(ROOT/'logs'/f'{source.PILOT}_saved_audit_v1.json')
    assert seen[str(pilot/'COMPLETE.json')]==pa['complete_sha256']
    assert pc['manifest_sha256']==seen[str(pilot/'MANIFEST.json')] and pa['passes']
    assert pa['all_cases_retained'] and pa['full_control_panel_retained']
    for co,ids in IDS.items():
        for index in ids:
            for path in raw_paths(co,index):
                values={mp[str(path)] for mp in (pc['output_sha256'],pm['input_sha256']) if str(path) in mp}
                assert len(values)==1,'unique previously audited raw binding required'
                source.bind(path,values.pop(),seen)
    fresh={p.resolve() for p in science()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        p=Path(file).resolve()
        if WS.parent in p.parents and p.suffix=='.py' and p not in fresh:
            assert str(p) in seen,'unbound imported repository code: '+str(p)
    return seen


def load_raw(path):
    with np.load(path,allow_pickle=False) as archive:
        assert len(archive.files)==len(set(archive.files)) and set(archive.files)==set(m.SHAPES)|EXTRA
        shared={'founder_packets','guide','initial_features'}
        result={k:archive[k] if k in shared else archive[k][:,:,:2].copy() for k in m.SHAPES}
    m.validate(result)
    for v in result.values():v.setflags(write=False)
    return result


def metadata(raw,meta,co,index):
    assert meta['index']==index and meta['config']==CONFIG and len(meta['lives'])==4
    tag='l20-extension1-'+('heldout-v1' if co=='development' else 'pilot64-v1')+':diagnostics:heldout'
    for life,item in enumerate(meta['lives']):
        assert (item['index'],item['life'],item['host']['index'])==(index,life,index)
        assert item['cohort']=='heldout' and item['tag']==tag and item['config']==CONFIG
        assert item['cases']==[[0,'translated'],[0,'aligned'],[1,'translated'],[1,'aligned']]
        assert item['branches']==['U0','U1','C1'] and item['guide_sha256']==GUIDE
        assert hashlib.sha256(raw['guide'][life].astype('<f8').tobytes()).hexdigest()==GUIDE
        assert item['diagnostic_to_lineage'] is False and item['predictor_has_parent_state'] is False
        assert item['replay']['full_dynamics_replayed'] is True and item['replay']['diagnostic_cycles']==12
        for g,cells in enumerate(item['cycles']):
            assert len(cells)==3
            for b in range(2):
                c=cells[b];mode='translated' if g%2==0 else 'aligned'
                assert c['trial']==b and c['mode']==mode and c['writer']['mode']==mode
                assert c['writer']['shift']==raw['shift'][life,g,b].tolist()
                assert c['writer']['theta_start_zero'] and c['writer']['theta_writing']
                for key in ('guide_access','incoming_packet_access','target_labels'):assert c['writer'][key] is False
                for key in ('reader','terminal_reader'):
                    r=c[key];assert r['enabled'] and not r['writing'] and r['gain']==0
                    assert r['packet_bytes']==2048 and not r['target_labels']
                    packet=raw['routed' if key=='reader' else 'terminal_packet'][life,g,b]
                    assert r['input_sha256']==hashlib.sha256(packet.tobytes()).hexdigest()
                assert c['reader']['birth_rng']!=c['terminal_reader']['birth_rng']
                for key in ('selector','terminal_selector'):
                    for access in ('outcome_access','source_state_access','target_label_access','historical_shift_access'):
                        assert c[key][access] is False
            assert cells[0]['reader']['birth_rng']!=cells[1]['reader']['birth_rng']


def feature_members(path,co):
    with np.load(path,allow_pickle=False) as archive:
        expected={'start','endpoint','targeted'}|({'block_ids','labels','futures'} if co=='development' else set())
        assert len(archive.files)==len(set(archive.files)) and set(archive.files)==expected
        if co=='development':assert archive['block_ids'].tolist()==list(IDS[co])
        start,endpoint=archive['start'],archive['endpoint']
    assert start.shape==(len(IDS[co]),4,4,7) and endpoint.shape==(len(IDS[co]),4,4,3,6)
    return start[...,:4],endpoint[...,:2,:]


def source_features(co):
    return feature_members(ROOT/'outputs'/(source.DEV if co=='development' else source.PILOT)/(
        'dataset.npz' if co=='development' else 'features.npz'),co)


def calculate(saved=None):
    arrays={};proofs=[]
    for co,ids in IDS.items():
        start,endpoint=source_features(co);collected=[]
        for j,index in enumerate(ids):
            a,b=raw_paths(co,index);raw=load_raw(a);meta=io.read_json(b);metadata(raw,meta,co,index)
            got=m.extract(raw) if saved is None else {k:saved[co+'_'+k][j] for k in ('fields','preference')}
            proof=check.block(raw,got,meta)
            first,last=m.endpoints(got)
            for copy in range(2):check.same(first[:,:,copy],start[j])
            check.same(last,endpoint[j]);collected.append(got);proofs.append(dict(cohort=co,index=index,**proof))
        for k in ('fields','preference'):arrays[co+'_'+k]=np.stack([v[k] for v in collected])
    return arrays,proofs


def bridge(arrays):
    old=io.read_json(ROOT/'outputs'/OLD/'summary.json')
    lookup={(r['group'],r['feature']):r for r in old['scalar_rows']};checked=0
    for co,ids in IDS.items():
        starts=[];ends=[]
        for j in range(len(ids)):
            a,b=m.endpoints({k:arrays[co+'_'+k][j] for k in ('fields','preference')});starts.append(a);ends.append(b)
        starts,ends=np.stack(starts),np.stack(ends)
        for g,group in enumerate(m.GROUPS):
            for k,name in enumerate(('own_best','best_margin','guide_margin','canonical_margin')):
                check.same(float(starts[:,:,g,0,k].mean()),lookup[(group,'start:'+name)][co+'_raw']['mean']);checked+=1
            for b,label in enumerate(('first:','second:passive:')):
                for k,name in enumerate(('own_best','best_margin','guide_margin','canonical_margin','preference','V_rms')):
                    check.same(float(ends[:,:,g,b,k].mean()),lookup[(group,label+name)][co+'_raw']['mean']);checked+=1
    return dict(passes=True,d166_aggregate_means=checked,all_saved_endpoint_values=True,outcomes_used=False)


def verify(arrays,summary,proofs):
    di,pi=(np.asarray(IDS[k],dtype=np.int64) for k in ('development','pilot'))
    return dict(passes=True,blocks=proofs,summary=check.summary(summary,arrays,di,pi),bridge=bridge(arrays),
        fields=122880,measurements=614400,preferences=10240,packet_routes=5120,
        maximum_measurement_error=max(r['max_measurement_error'] for r in proofs),
        outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0)


def qualification(path):
    path=io.require_beneath(path,ROOT/'logs');assert path.name.startswith('d167_') and path.suffix=='.xml' and not path.is_symlink()
    root=ET.parse(path).getroot();cases=root.findall('.//testcase')
    assert len(cases)>=30 and not any(root.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    names={c.get('name').split('[',1)[0] for c in cases}
    assert {'test_full_panel_roundtrip','test_loader_excludes_outcomes','test_stage_guard','test_corruption',
        'test_constant_fields','test_known_translation','test_copy_reversal','test_concentration','test_no_dynamics_or_fit'}<=names
    full=[c for c in cases if c.get('name')=='test_full_panel_roundtrip'];assert len(full)==1
    props={p.get('name'):p.get('value') for p in full[0].findall('./properties/property')}
    seconds=float(props['full_panel_seconds']);assert 0<seconds<600
    assert props['founders']=='80' and props['fields']=='122880' and props['summary_rows']=='1236'
    return dict(path=str(path),sha256=source.sha256_file(path),tests=len(cases),full_panel_seconds=seconds)


def freeze(report):
    source.resources();assert not freeze_path().exists() and not any(p.exists() for p in paths())
    proof=qualification(report);start=time.monotonic();inputs=source_inputs();elapsed=time.monotonic()-start
    inputs.update(io.hashes(science()+[Path(proof['path'])]));budget=3*proof['full_panel_seconds']+4*elapsed+120
    f=dict(schema='d167_passive_stages_freeze_v1',run=RUN,frozen_utc=source.utc_now(),input_sha256=inputs,
        qualification=proof,source_hash_seconds=elapsed,stage_budget_seconds=budget,must_detach=budget>600,
        environment=source.environment_manifest(),post_test_explanation=True,outcomes_used=False,new_fits=0,new_forecasts=0,
        new_dynamics=0,allowance=source.ALLOWANCE,reserve=source.RESERVE,
        automatic_polling=False,automatic_retry=False,automatic_successor=False,
        source_scope='D166 evidence closure and all 160 D162-audited diagnostic archives; no fresh physics or actual outcomes')
    io.write_json(freeze_path(),f,ROOT)
    return dict(status='FROZEN',inputs=len(inputs),tests=proof['tests'],stage_budget_seconds=budget,must_detach=budget>600)


def frozen():
    f=io.read_json(freeze_path());assert f['schema']=='d167_passive_stages_freeze_v1' and f['run']==RUN
    assert f['new_fits']==f['new_forecasts']==f['new_dynamics']==0 and f['outcomes_used'] is False
    assert f['allowance']==source.ALLOWANCE and f['reserve']==source.RESERVE
    budget=3*f['qualification']['full_panel_seconds']+4*f['source_hash_seconds']+120
    assert f['stage_budget_seconds']==budget and f['must_detach']==(budget>600)
    source.check_hashes(f['input_sha256']);seen=source_inputs()
    assert all(f['input_sha256'][k]==v for k,v in seen.items())
    assert all(f['input_sha256'][str(p)]==source.sha256_file(p) for p in science())
    env=source.environment_manifest()
    for k in ('python','numpy','thread_limits'):assert env[k]==f['environment'][k]
    return f


def stage_guard(f,stage):
    if f['must_detach']:
        assert os.environ.get(ENV)==stage,'forecast above ten minutes requires detached stage'
        assert os.getsid(0)==os.getpid() and not sys.stdin.isatty(),'new session/null input required'


def execute():
    source.resources();f=frozen();stage_guard(f,'execute');run,out=paths()
    assert not run.exists() and not out.exists(),'single use; preserve failures'
    run.mkdir();out.mkdir();start=time.monotonic()
    try:
        io.write_json(run/'MANIFEST.json',dict(started_utc=source.utc_now(),freeze_sha256=source.sha256_file(freeze_path()),
            input_sha256=f['input_sha256'],environment=source.environment_manifest(),outcomes_used=False),ROOT)
        arrays,proofs=calculate();di,pi=(np.asarray(IDS[k],dtype=np.int64) for k in ('development','pilot'))
        summary=m.summarize(arrays,di,pi);proof=verify(arrays,summary,proofs)
        io.write_npz(out/'stages.npz',arrays,ROOT);io.write_json(out/'summary.json',summary,ROOT)
        saved=io.load_npz(out/'stages.npz');check.same(saved,arrays)
        assert verify(saved,io.read_json(out/'summary.json'),proofs)==proof
        io.write_json(out/'verification.json',proof,ROOT);source.check_hashes(f['input_sha256'])
        assert {p.name for p in out.iterdir()}==set(OUTPUTS)
        hashes=io.hashes(out.iterdir());size=sum(Path(k).stat().st_size for k in hashes)
        assert size<source.ALLOWANCE;source.resources()
        done=dict(status='COMPLETE',completed_utc=source.utc_now(),seconds=time.monotonic()-start,
            freeze_sha256=source.sha256_file(freeze_path()),manifest_sha256=source.sha256_file(run/'MANIFEST.json'),
            output_sha256=hashes,output_bytes=size,outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',done,ROOT);return {k:v for k,v in done.items() if k!='output_sha256'}
    except Exception as exc:io.failure(run,exc,ROOT);raise


def audit():
    source.resources();f=frozen();stage_guard(f,'audit');run,out=paths();assert not audit_path().exists()
    start=time.monotonic();done=io.read_json(run/'COMPLETE.json');manifest=io.read_json(run/'MANIFEST.json')
    assert done['status']=='COMPLETE' and manifest['input_sha256']==f['input_sha256']
    assert done['freeze_sha256']==manifest['freeze_sha256']==source.sha256_file(freeze_path())
    assert done['manifest_sha256']==source.sha256_file(run/'MANIFEST.json')
    assert set(done['output_sha256'])=={str(out/k) for k in OUTPUTS}
    source.check_hashes(done['output_sha256']);arrays,proofs=calculate(io.load_npz(out/'stages.npz'))
    proof=verify(arrays,io.read_json(out/'summary.json'),proofs);check.same(proof,io.read_json(out/'verification.json'))
    source.check_hashes(f['input_sha256']);source.check_hashes(done['output_sha256'])
    result=dict(passes=True,checked_utc=source.utc_now(),seconds=time.monotonic()-start,
        complete_sha256=source.sha256_file(run/'COMPLETE.json'),freeze_sha256=done['freeze_sha256'],
        inputs=len(f['input_sha256']),outputs=len(done['output_sha256']),verification=proof,
        outcomes_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,source_scope=f['source_scope'],automatic_successor=False)
    io.write_json(audit_path(),result,ROOT);return {k:v for k,v in result.items() if k!='verification'}


def detach(stage):
    source.resources();f=frozen();assert stage in ('execute','audit');run,out=paths()
    if stage=='execute':assert not run.exists() and not out.exists()
    else:assert (run/'COMPLETE.json').is_file() and not audit_path().exists()
    log=ROOT/'logs'/f'{RUN}_{stage}.log';receipt=ROOT/'logs'/f'{RUN}_{stage}_launch.json'
    assert not log.exists() and not receipt.exists();env=dict(os.environ);env[ENV]=stage
    with log.open('x') as handle:
        child=subprocess.Popen([sys.executable,'-u','-m','l20_extension1.passive_stages_run',stage],
            stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,env=env,cwd=WS.parent)
    result=dict(launched_utc=source.utc_now(),pid=child.pid,stage=stage,log=str(log),startup='process created',
        completion=str(run/'COMPLETE.json' if stage=='execute' else audit_path()),
        stage_budget_seconds=f['stage_budget_seconds'],automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(receipt,result,ROOT);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('freeze','execute','audit','detach-execute','detach-audit'))
    parser.add_argument('--test-report',type=Path);args=parser.parse_args()
    if args.stage=='freeze':assert args.test_report is not None;result=freeze(args.test_report)
    elif args.stage.startswith('detach-'):result=detach(args.stage[7:])
    elif args.stage=='execute':result=execute()
    else:result=audit()
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':main()
