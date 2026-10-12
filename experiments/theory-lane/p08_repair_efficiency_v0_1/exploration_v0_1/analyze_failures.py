"""Post-hoc timing and identical-incoming-state census; no new dynamics."""
import csv
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
RUN=ROOT.parent/'runs/prospective_v1'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def write(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    source=json.loads((RUN/'COMPLETE.json').read_text());manifest=json.loads((RUN/'manifest.json').read_text());cfg=manifest['config']
    assert sha(RUN/'COMPLETE.json')=='29d8dcbc4a2e5395784b17e561f36a27630e5719d8ce2ba77f78c42e76b950ca'
    write('START.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),status='EXPLORATORY_POSTHOC',source_complete_sha256=sha(RUN/'COMPLETE.json'),
        script_sha256=sha(Path(__file__)),questions=['When do the first later failures occur relative to repair?',
        'Which losses under six calls are absent under one call?',
        'Do saved branches with identical incoming bytes expose immediate repair harm or rescue under the shared injury/reset/noise?',
        'How often do failed branches recover without a new repair?'],new_dynamics_generated=0))
    names=cfg['variants'];generations=cfg['generations'];events=[];matched={};history_counts={};inputs={}
    phase={name:{str(k):dict(at_risk_reads=0,first_failures=0) for k in range(3)} for name in names}
    first_failures={name:Counter() for name in names};census=Counter();recovery={name:Counter() for name in names}
    for b in cfg['blocks']:
        path=RUN/f'continuation_{b:06d}.npz';digest=sha(path);assert digest==source['outputs_sha256'][path.name];inputs[path.name]=digest
        with np.load(path,allow_pickle=False) as raw:
            good=raw['both_pass'];opposite=raw['opposite_pass'];margin=raw['min_margin'];applied=raw['applied']
            incoming=raw['incoming'];prepared=raw['prepared'];spent=applied.sum(axis=0)
            assert np.array_equal(spent,np.broadcast_to(np.array([1,6,18])[:,None],(3,16)))
            alive=good.all(axis=0);history=cfg['histories'][cfg['history_by_block'][str(b)]]
            hc=history_counts.setdefault(history,Counter())
            groups=dict(six_loss=~alive[1]&alive[2],six_harm_vs_once=~alive[1]&alive[0],six_rescue_vs_once=alive[1]&~alive[0],once_loss=~alive[0]&alive[2])
            for label,selected in groups.items():census[label]+=int(selected.sum());hc[label]+=int(selected.sum())
            for vi,name in enumerate(names):
                for case in range(16):
                    if not good[0,vi,case]:continue
                    failures=np.flatnonzero(~good[:,vi,case]);fi=int(failures[0]) if len(failures) else None
                    for gi,g in enumerate(generations[1:],1):
                        if not good[:gi,vi,case].all():break
                        bucket=phase[name][str((g-15)%3)];bucket['at_risk_reads']+=1
                        bucket['first_failures']+=int(not good[gi,vi,case])
                    if fi is None:continue
                    g=generations[fi];first_failures[name][str(g)]+=1
                    later=np.flatnonzero(good[fi+1:,vi,case]);ri=fi+1+int(later[0]) if len(later) else None
                    same_once=bool(np.array_equal(incoming[fi,vi,case],incoming[fi,0,case]))
                    next_repair=next((gg for gg in cfg['repair_generations'][vi] if gg>g),None)
                    before_next=(ri is not None and (next_repair is None or generations[ri]<next_repair))
                    recovery[name]['failures']+=1;recovery[name]['ever_recovered']+=int(ri is not None)
                    recovery[name]['recovered_before_next_repair']+=int(before_next)
                    recovery[name]['terminal_recovered']+=int(good[-1,vi,case])
                    events.append(dict(block=b,history=history,case=case,variant=name,generation=g,phase=(g-15)%3,
                        repair_applied=bool(applied[fi,vi,case]),margin=float(margin[fi,vi,case]),opposite=bool(opposite[fi,vi,case]),
                        once_pass_same_generation=bool(good[fi,0,case]),once_uninterrupted=bool(alive[0,case]),
                        same_incoming_as_once=same_once,first_recovery_generation=generations[ri] if ri is not None else None,
                        recovered_before_next_repair=before_next,terminal_pass=bool(good[-1,vi,case]),
                        incoming_sha256=hashlib.sha256(incoming[fi,vi,case].tobytes()).hexdigest()))
            for left,right in ((0,1),(0,2),(1,2)):
                equal=np.all(incoming[:,left]==incoming[:,right],axis=-1)
                distinct=applied[:,left]!=applied[:,right]
                for gi,case in np.argwhere(equal&distinct):
                    gi=int(gi);case=int(case);g=generations[gi]
                    no,repair=(right,left) if applied[gi,left,case] else (left,right)
                    key=(b,case,g,hashlib.sha256(incoming[gi,no,case].tobytes()).hexdigest())
                    no_pass=bool(good[gi,no,case]);repair_pass=bool(good[gi,repair,case])
                    label='rescue' if repair_pass and not no_pass else 'harm' if no_pass and not repair_pass else ('both_pass' if no_pass else 'both_fail')
                    item=matched.setdefault(key,dict(block=b,history=history,case=case,generation=g,incoming_sha256=key[-1],
                        no_repair_pass=no_pass,repair_pass=repair_pass,no_repair_margin=float(margin[gi,no,case]),
                        repair_margin=float(margin[gi,repair,case]),outcome=label,comparisons=[]))
                    assert item['outcome']==label and item['no_repair_margin']==float(margin[gi,no,case]) and item['repair_margin']==float(margin[gi,repair,case])
                    assert np.array_equal(prepared[gi,no,case],incoming[gi,no,case])
                    item['comparisons'].append(dict(no_repair=names[no],repair=names[repair],
                        both_previously_uninterrupted=bool(good[:gi,no,case].all() and good[:gi,repair,case].all())))
    counts=Counter(x['outcome'] for x in matched.values());by_generation={};by_comparison={}
    for item in matched.values():
        by_generation.setdefault(str(item['generation']),Counter())[item['outcome']]+=1
        for comp in item['comparisons']:
            label=comp['repair']+'_versus_'+comp['no_repair'];bucket=by_comparison.setdefault(label,dict(all=Counter(),both_previously_uninterrupted=Counter()))
            bucket['all'][item['outcome']]+=1
            if comp['both_previously_uninterrupted']:bucket['both_previously_uninterrupted'][item['outcome']]+=1
    six_events=[e for e in events if e['variant']=='repairs_6'];harm_events=[e for e in six_events if e['once_uninterrupted']]
    details=dict(six_first_failures_by_phase=dict(Counter(str(e['phase']) for e in six_events)),
        six_first_failures_on_repair=sum(e['repair_applied'] for e in six_events),
        six_first_failures_opposite_task=sum(e['opposite'] for e in six_events),
        twenty_harm_first_failures_by_generation=dict(Counter(str(e['generation']) for e in harm_events)),
        twenty_harm_first_failures_by_phase=dict(Counter(str(e['phase']) for e in harm_events)),
        twenty_harm_identical_incoming_as_once=sum(e['same_incoming_as_once'] for e in harm_events))
    assert census==dict(six_loss=46,six_harm_vs_once=20,six_rescue_vs_once=92,once_loss=118)
    write('failure_events.json',events);write('identical_state_comparisons.json',list(matched.values()))
    with (ROOT/'failure_events.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(events[0]));writer.writeheader();writer.writerows(events)
    result=dict(status='EXPLORATORY_COMPLETE',at_utc=datetime.now(timezone.utc).isoformat(),source_complete_sha256=sha(RUN/'COMPLETE.json'),
        records=2112,blocks=132,census=census,history_counts=history_counts,first_failures_by_generation=first_failures,
        phase_at_risk_counts=phase,recovery=recovery,details=details,
        identical_incoming_states=dict(unique_contexts=len(matched),outcomes=counts,by_generation=by_generation,by_comparison=by_comparison),
        limitations=['All questions and selections are post-hoc on an exposed cohort.','Phase hazards are descriptive and mix generation, survival selection and repair history.',
        'Identical incoming packets plus shared injury/reset/noise isolate the effect of the current repair on that saved boundary, not the population effect of an alternative schedule.',
        'Contexts and repeated generations are clustered within blocks, not independent observations. No new significance tests or multiplicity-adjusted claims are made.',
        'The prospective doubled-efficiency verdict remains UNRESOLVED. No new dynamics or cohort are generated.'],
        new_dynamics_generated=0,inputs_sha256=inputs)
    write('findings.json',result)
    result.pop('inputs_sha256');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
