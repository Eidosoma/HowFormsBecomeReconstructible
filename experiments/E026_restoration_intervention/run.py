"""Append-only saved-packet intervention and complete paired reporting."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, finish, new_run, rng, sha, utc
from E026_restoration_intervention import model
import numpy as np

CSV_FIELDS = ('block','condition','receiver','founder','rule','lineage','cue','damage','arm','success','margin','output_A','output_B')
FOCAL = ('restoration_with_rebuilt_survivors', 'restoration_with_copied_survivors')


def load(path): return json.loads(path.read_text())


def input_paths():
    shared = ('common.py','run_python.sh','SOURCE_SNAPSHOT.json','SOURCE_LICENSE.txt',
        'E015_functional_inheritance/model.py','E015_functional_inheritance/audit.py',
        'E016_teaching_consistency/model.py','E017_reader_timing/model.py','E017_reader_timing/audit.py',
        'E022_reader_compensation/model.py','E022_reader_compensation/audit.py',
        'E023_receiver_compensation/model.py','E023_receiver_compensation/audit.py')
    return [ROOT/p for p in shared]+[HERE/p for p in ('model.py','run.py','audit.py','tests.py','plot.py','workflow.py','PROTOCOL.md','SOURCE_DATA.json')]


def source_spec(label):
    spec = load(HERE/'SOURCE_DATA.json')[label]
    return spec, type(model.CFG)(**spec['config']), model.Cycle(**spec['cycle'])


def source_packets(label, block):
    spec, cfg, cycle = source_spec(label)
    assert block in spec['blocks']
    source = ROOT/spec['path']
    check_inputs(source)
    for name,digest in spec['provenance_sha256'].items(): assert sha(source/name) == digest
    assert load(source/'INDEPENDENT_AUDIT.json')['status'] == 'PASS'
    for name,digest in spec['files'][str(block)].items(): assert sha(source/name) == digest, name
    masks = []; original = None; cumulative = None
    for generation in (1,2,3):
        with np.load(source/f'boundary_{block:06d}_g{generation}.npz',allow_pickle=False) as saved:
            outgoing, mask = saved['outgoing'], saved['renewal_mask']
        masks.append(mask)
        if original is None: original = outgoing[4].copy()
        np.testing.assert_array_equal(outgoing[4],original)
        alive = ~mask
        current = np.stack((alive & np.roll(alive,-1,-1),alive & np.roll(alive,-1,-2)),axis=-3)
        cumulative = current if cumulative is None else cumulative & current
        np.testing.assert_array_equal(model.base.decode(outgoing[5]),model.base.decode(original)*cumulative)
    intervention = model.construct(outgoing[5],outgoing[2],np.stack(masks))
    return intervention, source, cfg, cycle


def save_block(output, block):
    started = time.monotonic(); cap_cpus()
    label = load(output/'manifest.json')['contract']['source']
    intervention, source, cfg, cycle = source_packets(label,block)
    np.savez_compressed(output/f'intervention_{block:06d}.npz',**intervention)
    raw = model.assay(intervention['records'],block,3,cfg,cycle)
    with np.load(source/f'assay_{block:06d}_h3.npz',allow_pickle=False) as old:
        model.check_endpoints(raw,old)
    np.savez_compressed(output/f'assay_{block:06d}.npz',**raw)
    dump(output/f'worker_{block}.json',dict(block=block,seconds=time.monotonic()-started,
        source=label,source_files_sha256=load(HERE/'SOURCE_DATA.json')[label]['files'][str(block)],
        original_endpoint_packets_and_all_terminal_arrays_exact=True))


def statistics(x):
    x = np.asarray(x,dtype=float)
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    draws = rng('E026','bootstrap','restoration').integers(0,len(x),(10000,len(x)))
    return dict(mean=float(x.mean()),ci95=np.quantile(x[draws].mean(axis=1),[.025,.975]).tolist(),block_means=x.tolist())


def effects(values):
    """Last axis is the fixed four-packet order; retain conditional effects."""
    copy, added, removed, rebuilt = np.moveaxis(np.asarray(values),-1,0)
    return dict(total_gap=rebuilt-copy,
        restoration_with_copied_survivors=added-copy,
        restoration_with_rebuilt_survivors=rebuilt-removed,
        rewritten_survivors_without_restoration=removed-copy,
        rewritten_survivors_with_restoration=rebuilt-added,
        interaction=(rebuilt-removed)-(added-copy))


def create(output,label,workers):
    spec,cfg,cycle = source_spec(label)
    return new_run(output,input_paths(),dict(experiment='E026',source=label,blocks=spec['blocks'],
        config=asdict(cfg),cycle=asdict(cycle),gain=2.,conditions=model.CONDITIONS,
        receivers=model.RECEIVERS,panels=model.PANELS,workers=workers,
        mode='post_hoc_intervention' if label=='cohort' else 'technical_fixture' if label=='fixture' else 'technical'))


def analyze(output):
    contract = load(output/'manifest.json')['contract']
    spec,cfg,cycle = source_spec(contract['source']); ids = spec['blocks']
    technical = contract['source'] != 'cohort'
    collected = {key:[] for key in ('accuracy','both_cues','margin','rules')}
    with (output/'observations.csv').open('x',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=CSV_FIELDS); writer.writeheader()
        for block in ids:
            with np.load(output/f'assay_{block:06d}.npz',allow_pickle=False) as saved:
                success,margin,ports = model.score(saved['late_ports'],cfg)
            collected['accuracy'].append(success.mean(axis=(1,2,3)))
            collected['both_cues'].append(success.all(axis=3).mean(axis=(1,2)))
            collected['margin'].append(margin.mean(axis=(1,2,3)))
            collected['rules'].append(np.stack([success[:,[r,r+2]][...,0].mean(axis=(1,2,3)) for r in range(2)],axis=1))
            for k,(condition,receiver) in enumerate(model.PANELS):
                for f in range(4):
                    for r in range(cfg.recipients):
                        for c,cue in enumerate(model.CUES):
                            for d,damage in enumerate(model.DAMAGE):
                                for a,arm in enumerate(model.ARMS):
                                    ix = (k,f,r,c,d,a)
                                    writer.writerow(dict(block=block,condition=condition,receiver=receiver,founder=f,
                                        rule=int(model.RULES[f]),lineage=r,cue=int(cue),damage=damage,arm=arm,
                                        success=int(success[ix]),margin=float(margin[ix]),output_A=float(ports[ix+(0,)]),output_B=float(ports[ix+(1,)])))
    arrays = {k:np.asarray(v) for k,v in collected.items()}; groups = {}
    for k,(condition,receiver) in enumerate(model.PANELS):
        group = {metric:{damage:{arm:statistics(arrays[metric][:,k,d,a]) for a,arm in enumerate(model.ARMS)}
            for d,damage in enumerate(model.DAMAGE)} for metric in ('accuracy','both_cues','margin')}
        group['own_accuracy_by_rule'] = {str(rule):{damage:statistics(arrays['rules'][:,k,r,d])
            for d,damage in enumerate(model.DAMAGE)} for r,rule in enumerate((1,-1))}
        group['own_minus_control'] = {damage:{arm:statistics(arrays['accuracy'][:,k,d,0]-arrays['accuracy'][:,k,d,a])
            for a,arm in enumerate(model.ARMS) if a} for d,damage in enumerate(model.DAMAGE)}
        gates = {f'accuracy_rule_{rule}_{damage}':group['own_accuracy_by_rule'][str(rule)][damage]['ci95'][0]>.75
            for rule in (1,-1) for damage in model.DAMAGE}
        gates.update({f'advantage_{damage}_{arm}':group['own_minus_control'][damage][arm]['ci95'][0]>.10
            for damage in model.DAMAGE for arm in model.ARMS[1:]})
        group.update(gates=gates,all_original_gates_pass=all(gates.values()))
        groups.setdefault(receiver,{})[condition] = group
    contrasts = {}
    for ri,receiver in enumerate(model.RECEIVERS):
        contrasts[receiver] = {}
        for metric in ('accuracy','both_cues','margin'):
            for d,damage in enumerate(model.DAMAGE):
                for name,value in effects(arrays[metric][:,ri*4:ri*4+4,d,0]).items():
                    contrasts[receiver].setdefault(name,{}).setdefault(metric,{})[damage]=statistics(value)
    focal = {}
    for name in FOCAL:
        st = contrasts['local_strength'][name]['both_cues']['scattered']
        focal[name] = dict(statistics=st,lower_bound_above_zero=None if technical else st['ci95'][0]>0,
            lower_bound_above_010=None if technical else st['ci95'][0]>.10)
    summary = dict(experiment='E026',status='TECHNICAL_ONLY' if technical else 'RESTORATION_DIAGNOSTIC_COMPLETE',
        evidence_status='technical' if technical else 'post_hoc_saved_cohort_intervention',source=contract['source'],
        blocks=ids,founders=4*len(ids),lineages=4*cfg.recipients*len(ids),cfg=asdict(cfg),cycle=asdict(cycle),
        conditions=model.CONDITIONS,receivers=model.RECEIVERS,panels=model.PANELS,arms=model.ARMS,damage=model.DAMAGE,
        groups=groups,contrasts=contrasts,focal=focal,individual_observations=len(ids)*8*4*cfg.recipients*2*3*7,
        original_endpoint_replay_exact=True,new_teaching_or_renewal=False,new_independent_cohort=False,
        interval_scope='Post hoc pointwise 95% whole-block intervals; no equivalence inference',
        interpretation_scope='Effects of final-packet restoration and surviving values with recomputed receiving denominators')
    dump(output/'summary.json',summary); report(output,summary)


def report(output,s):
    def fmt(st):return f"{100*st['mean']:.2f} [{100*st['ci95'][0]:.2f}, {100*st['ci95'][1]:.2f}]"
    lines=['# E026 — restored connections versus surviving values','',f"**{s['status']}**",'',
        f"{len(s['blocks'])} existing blocks; {s['lineages']} lineages. All cases retained.",'',
        'Post hoc terminal-packet intervention; no new independent cohort or renewal simulation. Intervals are pointwise whole-block bootstrap intervals.','',
        '## Focused scattered-terminal effects with the normalized receiver','']
    for name,st in s['focal'].items():
        lines += [f"- {name}: **{fmt(st['statistics'])} percentage points**; lower bound >0: {st['lower_bound_above_zero']}; >10 points: {st['lower_bound_above_010']}."]
    lines += ['','## Both cues correct','', '| Receiver | Packet | Intact % [95%] | Scattered | Square | Original gates |','| --- | --- | --- | --- | --- | --- |']
    for receiver in s['receivers']:
        for condition in s['conditions']:
            group=s['groups'][receiver][condition]
            lines += [f"| {receiver} | {condition} | "+' | '.join(fmt(group['both_cues'][d]['own']) for d in s['damage'])+f" | {sum(group['gates'].values())}/24 |"]
    for receiver in s['receivers']:
        lines += ['',f'## Paired both-cue effects: {receiver}','', '| Contrast | Intact points [95%] | Scattered | Square |','| --- | --- | --- | --- |']
        for name,group in s['contrasts'][receiver].items():
            lines += [f'| {name} | '+' | '.join(fmt(group['both_cues'][d]) for d in s['damage'])+' |']
        for condition in s['conditions']:
            group=s['groups'][receiver][condition]
            lines += ['',f'### {condition}: individual-cue controls','', '| Arm | Intact % [95%] | Scattered | Square |','| --- | --- | --- | --- |']
            for arm in s['arms']:lines += [f'| {arm} | '+' | '.join(fmt(group['accuracy'][d][arm]) for d in s['damage'])+' |']
            lines += ['', 'Failed original gates: '+(', '.join(k for k,v in group['gates'].items() if not v) or 'none')+'.']
    lines += ['', 'The two unchanged endpoints must reproduce every saved terminal array exactly. Hybrids change only restored coordinates. Denominators are recomputed after intervention and all controls. A null interval does not establish absence or equivalence; final-packet effects do not identify the complete rebuilding history. No automatic successor.','']
    (output/'REPORT.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--benchmark',action='store_true');parser.add_argument('--worker',type=int)
    parser.add_argument('--workers',type=int,default=8);args=parser.parse_args();cap_cpus()
    assert 1<=args.workers<=12
    output=args.output.resolve();assert output.is_relative_to(HERE)
    if args.worker is not None:
        check_inputs(output);save_block(output,args.worker);return
    started=time.monotonic();label='benchmark' if args.benchmark else 'cohort'
    output=create(output,label,args.workers);ids=source_spec(label)[0]['blocks']
    def launch(block):
        with (output/f'worker_{block}.log').open('x') as log:
            subprocess.run([sys.executable,'-B',str(HERE/'run.py'),'--output',str(output),'--worker',str(block)],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=7200)
        return block
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for task in as_completed([pool.submit(launch,b) for b in ids]):print('Completed block',task.result(),flush=True)
        analyze(output);finish(output,started,dict(experiment='E026',blocks_completed=len(ids)))
        print('Complete:',output,flush=True)
    except BaseException:
        dump(output/'FAILED.json',dict(utc=utc(),traceback=traceback.format_exc()));raise


if __name__=='__main__':main()
