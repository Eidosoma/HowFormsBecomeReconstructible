"""P10 registered common graph and externally scheduled contact windows."""
from paper_staged_relay_design import (ROOT,SOURCE,REVISION,digest,write_json,source_check,
    LOCAL_FILES as P9_FILES,execution_manifest as p9_manifest,input_paths as p9_inputs,replay_source)

PREDECESSOR=ROOT/'runs/paper-staged-relay-20260913T105705Z-5eayw91i'
LINEAGE='relay__rewritten_restored_E__sequential'
GRAPH=((0,1),(0,2),(1,3),(2,3),(1,4),(2,4),(1,5),(2,5))
FOUNDERS=('rewritten_restored_E','ordinary_M')
SCHEDULES=dict(sequential=((0,20000),(20000,40000),(40000,60000)),
    simultaneous=((0,20000),(0,20000),(0,20000)),
    overlap_25=((0,20000),(15000,35000),(30000,50000)),
    overlap_50=((0,20000),(10000,30000),(20000,40000)),
    gaps_10=((0,20000),(30000,50000),(60000,80000)),
    short_10=((0,10000),(20000,30000),(40000,50000)),
    uneven=((0,20000),(18000,38000),(41000,61000)))
PRIORITY=('simultaneous','overlap_50','overlap_25','uneven','gaps_10','short_10')
FIXED=dict(revision=REVISION,workers=2,worker_timeout_seconds=14400,total_budget_seconds=64800,
    algorithm='depol',power=60,kd=1.25e-14,teachers=3,pupils=3,maximum_rounds=6,
    contact_window=80000,hold_horizons=[10000,10000],round_horizon=100000,late_fraction=.95,
    graph=[list(e) for e in GRAPH],schedules={k:[list(w) for w in v] for k,v in SCHEDULES.items()},
    founders=list(FOUNDERS),lineage=LINEAGE,alternative_priority=list(PRIORITY),
    maximum_selected_schedules=2,replay_cases=2,calibration_cases=8,screen_cases=50,
    minimum_cases=10,screened_cases=60,maximum_cases=84,
    all_six_cells_evolve=True,external_schedule=True,automatic_follow_on=False,
    stop_rule='first_incomplete_three_M_round',source='actual_P9_round6_live_group',
    selection='eligible_sequential_plus_first_eligible_alternative_common_to_both_founders')
LOCAL_FILES=P9_FILES+[ROOT/'PAPER_CONTACT_SCHEDULE_PROTOCOL.md',ROOT/'configs/paper_contact_schedule_v1.json']+[
    ROOT/'scripts'/n for n in ('paper_contact_schedule_design.py','run_paper_contact_schedule.py',
        'analyze_paper_contact_schedule.py','run_paper_contact_schedule_detached.py','test_paper_contact_schedule.py')]


def make_case(kind,founder,schedule='sequential',route='open',fine=False):
    return dict(id='__'.join((kind,founder,schedule,route))+('__fine' if fine else ''),
                kind=kind,founder=founder,schedule=schedule,route=route,fine=fine)


def fixed_cases():
    out=[dict(id='replay__'+l,kind='replay',layout=l,source=replay_source(l)['id'],fine=False)
         for l in ('three_to_one','three_to_three')]
    for fine in (False,True):
        out.extend(make_case('calibration',h,'single',r,fine) for h,r in
                   [('ordinary_M','open'),('ordinary_M','rna'),('ordinary_M','cut'),('ordinary_E_sham','open')])
    for fine in (False,True):
        out.extend(make_case('screen',h,s,'open',fine) for h in FOUNDERS+('ordinary_E_sham',) for s in SCHEDULES)
        out.extend(make_case('screen',h,'sequential',r,fine) for h in FOUNDERS for r in ('rna','cut'))
    return out


def continuation_cases(selected):
    if len(selected)>2 or len(set(selected))!=len(selected) or any(s not in SCHEDULES for s in selected):
        raise ValueError('Invalid selected schedule list')
    return [make_case('continuation',h,s,r,fine) for fine in (False,True)
            for s in selected for h in FOUNDERS for r in ('open','rna','cut')]


def segments(schedule):
    intervals=((0,20000),(-1,-1),(-1,-1)) if schedule=='single' else SCHEDULES[schedule]
    end=20000 if schedule=='single' else 80000
    times=sorted({0,end}|{t for pair in intervals for t in pair if t>=0})
    return [(a,b,[i for i,(start,stop) in enumerate(intervals) if start<=a and b<=stop])
            for a,b in zip(times,times[1:])]


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered conditional 10-84 case P10 design')
    return config


def execution_manifest():
    result=p9_manifest(); result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES}); return result


def input_paths():
    result={'p9/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json')}
    result.update({'p9/inputs/'+n:PREDECESSOR/'inputs'/n for n in p9_inputs()})
    names=['result.json']+[f'r{r:02d}_{p}.npz' for r in range(1,7) for p in
        ('contact_1','contact_2','waiting_2','contact_3','waiting_3','isolated_1','isolated_2')]
    result.update({'p9/'+LINEAGE+'/'+n:PREDECESSOR/LINEAGE/n for n in names})
    return result
