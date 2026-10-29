#!/usr/bin/env python3
"""Known-Q regret accounting for immutable zero-, one- and two-update policies."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
from functools import lru_cache
import gzip
from hashlib import sha256
import importlib.util
from itertools import islice, product, zip_longest
import json
from math import prod
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-task-regret-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-second-feedback-v1/attempt-01'
PREVIOUS_SHA = 'c277bee40484ded7c1393a17da7df005314c9218f6095ca2ad0b110d1a187d37'
REPORT_SHA = '109940256d1efd321032f418ebe42a5bf0ab5ece49054f32920293a256026583'
HELPER_SHA = '13012ae27267ac4b816d2918ae0ee82bfd41156897284daf6934292b03e6b955'
LEDGER = PREVIOUS/'SECOND_TASK_TABLES.jsonl.gz'
ARMS = ('no_update','one_update','two_warnings','two_full')
METRICS = ('wrong_loss','reference_expense','excess_checking','unsafe_reporting','wrong_direction')
WARNINGS = ('agreement','disagreement')
PHASES = ('first','second','last_98')
DURATIONS = (1,1,98)
BLOCKS = ((0,0,0),(1,2,2),(1,2,3),(1,2,4))
CONTRASTS = {'one_minus_none':(1,0),'full_two_minus_one':(3,1),
             'full_two_minus_none':(3,0),'full_two_minus_warnings':(3,2)}
BASE,CAP = 400,64


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assert sha256((SOURCE/'check_fep_second_feedback.py').read_bytes()).hexdigest() == HELPER_SHA
S = module('frozen_second_feedback',SOURCE/'check_fep_second_feedback.py')
A,V,R = S.A,S.V,S.R
check,write,identity = S.check,S.write,S.identity


def score(code,q):
    rows = []
    for g in (0,1):
        act = R.C.ACTS[code][g]
        mass,better = q[g]+q[3-g],10*min(q[g],q[3-g])
        floor = min(mass,better)
        risk = 10*q[3-g if act == 0 else g]
        row = (0,mass,mass-floor,0,0) if act == 2 else (risk,0,0,better-floor,risk-better)
        check('regret','pointwise nonnegative identity',min(row) >= 0 and row[0]+row[1] == floor+sum(row[2:]))
        rows.append(row)
    return tuple(rows)


def oracle(q):
    parts,actions = {},{}
    for g,name in enumerate(WARNINGS):
        loss = (10*q[3-g],10*q[g],q[g]+q[3-g])
        parts[name] = F(min(loss),10*BASE)
        actions[name] = [a for a,x in enumerate(loss) if x == min(loss)]
    return dict(task_floor=sum(parts.values()),by_warning=parts,
                canonical_optimal_actions=actions,representative_actions=R.C.ACTS[R.program(q)],
                task_headroom=F(1,10)-sum(parts.values()))


def freeze(x):
    return tuple(freeze(y) for y in x) if isinstance(x,list) else x


def read_rows():
    with gzip.open(LEDGER,'rt') as saved, gzip.open(V.LEDGER,'rt') as post, gzip.open(A.DECISIONS,'rt') as choices:
        for lines in zip_longest(saved,post,choices):
            check('ledger','three ledgers have the same length',all(line is not None for line in lines))
            row,old,decision = (json.loads(line) for line in lines)
            check('ledger','counts and stopping multiplicities aligned',row[:6] == old[:6] and row[:5] == decision[:5])
            n,c,k = row[0],tuple(row[1:5]),tuple(int(x) for x in row[5])
            check('ledger','valid saved stops',n == sum(c) and 0 <= n <= CAP and min(k) >= 0 and any(k))
            signatures = []
            for s,raw in enumerate(row[6]):
                if not k[s]:
                    check('ledger','unreachable controller absent',raw is None and decision[5][s] is None)
                    signatures.append(None)
                    continue
                p = S.Program(*freeze(raw))
                check('ledger','program shapes',len(p.asks) == 2 and all(len(x) == 4 for x in (p.first_codes,p.first_joins,p.passive_codes,p.scopes))
                      and all(len(x) == 16 for x in (p.warning_codes,p.warning_joins,p.full_codes,p.full_joins)))
                check('ledger','unchanged initial table and purchases',p.initial == old[6][s] and p.asks == tuple(bool(x[2]) for x in decision[5][s]))
                allcodes = (p.initial,*p.first_codes,*p.passive_codes,*p.warning_codes,*p.full_codes)
                check('symmetry','all saved response tables symmetric',all(code in S.SYMMETRIC for code in allcodes))
                for e in range(4):
                    g = min(e,3-e); bought = p.asks[g]
                    check('retention','first label or coarsened observation preserved',
                        p.scopes[e] == ((e,) if bought else (g,3-g)) and
                        p.first_codes[e] == (old[10][e][s] if bought else old[8][g][s]) and
                        p.first_joins[e] == (old[11][e] if bought else old[9][g]) and p.passive_codes[e] == old[8][g][s])
                    check('retention','existing first references retained',R.C.ACTS[p.initial][e] != 2 or bought)
                    for f in range(4):
                        j = 4*e+f
                        check('retention','warning retains no second target',p.warning_codes[j] == p.warning_codes[4*e+3-f])
                        check('retention','unchecked second answer is not a label',S.ASK[p.first_codes[e]][f] or p.full_codes[j] == p.warning_codes[j])
                        if not bought:
                            check('retention','unchecked first answer is not a label',
                                p.warning_codes[j] == p.warning_codes[4*(3-e)+f] and p.full_codes[j] == p.full_codes[4*(3-e)+f])
                active = sum((2 if p.asks[min(y,3-y)] else R.C.ACTS[p.initial][y])*3**y for y in range(4))
                check('symmetry','effective first table symmetric',active in S.SYMMETRIC)
                signatures.append((p.initial,active,p.first_codes,p.warning_codes,p.full_codes))
            check('ledger','both controller slots present',len(signatures) == 2)
            yield c,k,tuple(signatures)


def dense_features(signature,q):
    initial,active,first,warnings,full = signature
    cache = {code:score(code,q) for code in set((initial,active,*first,*warnings,*full))}
    rows = [[[0]*5 for _ in (0,1)] for _ in range(5)]
    for b,code in enumerate((initial,active)):
        rows[b] = [[x*BASE**2 for x in row] for row in cache[code]]
    for e in range(4):
        for g in (0,1):
            for j,x in enumerate(cache[first[e]][g]):
                rows[2][g][j] += BASE*q[e]*x
        for f in range(4):
            for b,code in ((3,warnings[4*e+f]),(4,full[4*e+f])):
                for g in (0,1):
                    for j,x in enumerate(cache[code][g]):
                        rows[b][g][j] += q[e]*q[f]*x
    return tuple(x for block in rows for row in block for x in row)


@lru_cache(maxsize=2048)
def physical_features(signature):
    return {label:tuple((i,x) for i,x in enumerate(dense_features(signature,q)) if x)
            for label,q in R.TRUTHS.items()}


def fresh():
    return dict(mass=0,count=0,values=[0]*50)


def summarize(stat,q):
    den = BASE**CAP
    check('mass','stopped law normalized',stat['mass'] == den)
    n = F(stat['count'],den); o = oracle(q)
    blocks = []
    for b in range(5):
        warning = {}
        for g,name in enumerate(WARNINGS):
            row = dict(zip(METRICS,(F(x,10*den*BASE**3) for x in stat['values'][10*b+5*g:10*b+5*g+5])))
            row['task_floor'] = o['by_warning'][name]
            row['raw_loss'] = row['wrong_loss']+row['reference_expense']
            row['decision_regret'] = sum(row[k] for k in METRICS[2:])
            check('regret','integrated warning identity',row['raw_loss'] == row['task_floor']+row['decision_regret'] and min(row.values()) >= 0)
            warning[name] = row
        blocks.append(warning)
    arms = {}
    for a,name in enumerate(ARMS):
        phases = {phase:dict(tasks=duration,by_warning=blocks[b]) for phase,duration,b in zip(PHASES,DURATIONS,BLOCKS[a])}
        warnings = {warning:{key:sum(F(duration,100)*blocks[b][warning][key] for duration,b in zip(DURATIONS,BLOCKS[a]))
                    for key in blocks[0][warning]} for warning in WARNINGS}
        totals = {key:sum(row[key] for row in warnings.values()) for key in blocks[0]['agreement']}
        calibration = n/100000
        components = dict(calibration=calibration,**{key:totals[key] for key in METRICS[2:]})
        net = totals['raw_loss']+calibration
        gap = net-o['task_floor']
        check('regret','full cost equals floor plus all regret',gap == sum(components.values()) and gap >= 0)
        arms[name] = dict(net_loss=net,task_floor=o['task_floor'],raw_task_loss=totals['raw_loss'],
            wrong_loss=totals['wrong_loss'],reference_expense=totals['reference_expense'],
            calibration_expense=calibration,gap_to_known_Q=gap,components=components,
            by_warning=warnings,by_phase=phases,
            episode_expected_wrong_reports=100*totals['wrong_loss'],episode_expected_references=1000*totals['reference_expense'])
    contrasts = {}
    for label,(a,b) in CONTRASTS.items():
        after,before = arms[ARMS[a]],arms[ARMS[b]]
        delta = after['net_loss']-before['net_loss']
        parts = {key:after['components'][key]-before['components'][key] for key in after['components']}
        check('contrast','all signed changes retained',delta == sum(parts.values()) and parts['calibration'] == 0)
        contrasts[label] = dict(net_difference=delta,components=parts,
            by_warning={w:{key:after['by_warning'][w][key]-before['by_warning'][w][key] for key in after['by_warning'][w]} for w in WARNINGS})
    return dict(expected_calibrations=n,task_floor=o['task_floor'],task_headroom=o['task_headroom'],arms=arms,contrasts=contrasts)


def add_ratios(row):
    for arm in row['arms'].values():
        gap,headroom = arm['gap_to_known_Q'],row['task_headroom']
        advantage = F(1,10)-arm['net_loss']
        arm['net_advantage_over_always_reference'] = advantage
        arm['captured_headroom_fraction'] = advantage/headroom if headroom else None
        arm['gap_component_fractions'] = {key:value/gap if gap else None for key,value in arm['components'].items()}
        if headroom:
            check('bound','captured headroom cannot exceed supplied-information floor',advantage/headroom <= 1)


def average(rows):
    if isinstance(rows[0],dict):
        return {key:average([row[key] for row in rows]) for key in rows[0]}
    return sum(rows,F(0))/len(rows)


class Collector:
    def __init__(self):
        self.actual = {label:[fresh(),fresh()] for label in R.TRUTHS}
        self.powers = {label:[[x**n for n in range(CAP+1)] for x in q] for label,q in R.TRUTHS.items()}
        self.tails = [BASE**n for n in range(CAP+1)]
        self.rows,self.stopped = 0,0

    def row(self,c,k,signatures):
        n = sum(c)
        for s,signature in enumerate(signatures):
            if not k[s]:
                continue
            feats = physical_features(signature)
            for label in R.TRUTHS:
                mass = k[s]*prod(self.powers[label][e][c[e]] for e in range(4))*self.tails[CAP-n]
                if not mass:
                    continue
                stat = self.actual[label][s]
                stat['mass'] += mass; stat['count'] += n*mass
                for i,x in feats[label]:
                    stat['values'][i] += mass*x
            self.stopped += 1
        self.rows += 1

    def finish(self):
        return {label:{name:summarize(stats[s],R.TRUTHS[label]) for s,name in enumerate(V.NAMES)} for label,stats in self.actual.items()}


def direct_score(code,q):
    result = [[F(0)]*5 for _ in (0,1)]
    weights = [[F(0),F(0)] for _ in range(4)]
    for w,e in product((0,1),range(4)):
        y = e if w == 0 else 3-e
        weights[y][w] += F(q[e],2*BASE)
        a = R.C.ACTS[code][y]; g = min(y,3-y)
        result[g][0] += F(q[e],2*BASE)*int(a != 2 and a != w)
        result[g][1] += F(q[e],20*BASE)*int(a == 2)
    for y,(w0,w1) in enumerate(weights):
        probability = w0+w1
        if not probability:
            continue
        risks = (w1/probability,w0/probability)
        m = min(risks); best = min(m,F(1,10)); a = R.C.ACTS[code][y]; g = min(y,3-y)
        if a == 2:
            result[g][2] += probability*(F(1,10)-best)
        else:
            result[g][3] += probability*(m-best)
            result[g][4] += probability*(risks[a]-m)
    return tuple(tuple(x*10*BASE for x in row) for row in result)


def direct_histories(signature,q):
    initial,active,first,warnings,full = signature
    values = [[[0,0] for _ in PHASES] for _ in ARMS]
    def add(row,code,w,e,weight):
        y = e if w == 0 else 3-e; a = R.C.ACTS[code][y]
        row[0] += weight*10*int(a != 2 and a != w)
        row[1] += weight*int(a == 2)
    for w,e in product((0,1),range(4)):
        for a in range(4):
            add(values[a][0],initial if a == 0 else active,w,e,4*BASE**2*q[e])
        for v,f in product((0,1),range(4)):
            for a in range(4):
                add(values[a][1],initial if a == 0 else first[e],v,f,2*BASE*q[e]*q[f])
            codes = initial,first[e],warnings[4*e+f],full[4*e+f]
            for u,h in product((0,1),range(4)):
                for a,code in enumerate(codes):
                    add(values[a][2],code,u,h,q[e]*q[f]*q[h])
    return values


def qualify():
    start = perf_counter()
    controls = [(400,0,0,0),(0,0,0,400),(100,100,100,100),
                (360,0,0,40),(40,0,0,360),(359,0,0,41),(361,0,0,39)]
    laws = list(R.TRUTHS.values())+controls
    codes = sorted(S.SYMMETRIC)
    for q in laws:
        rows = {code:score(code,q) for code in codes}
        for code in codes:
            check('qualification','independent target/error regret decomposition',rows[code] == direct_score(code,q))
        floor = oracle(q)['task_floor']
        check('qualification','exhaustive known-Q task floor',floor == min(F(sum(row[0]+row[1] for row in scores),10*BASE) for scores in rows.values()))
        check('qualification','known-Q table has zero decision regret',all(sum(row[2:]) == 0 for row in rows[R.program(q)]))
    samples = []
    for c,k,programs in islice(read_rows(),4):
        samples.extend(p for p in programs if p is not None)
    for code in codes:
        samples.append((code,code,(code,)*4,(code,)*16,(code,)*16))
    for signature in samples:
        for q in laws:
            fast = dense_features(signature,q)
            direct = direct_histories(signature,q)
            for a in range(4):
                for phase,b in enumerate(BLOCKS[a]):
                    expected = [8*sum(fast[10*b+5*g+j] for g in (0,1)) for j in (0,1)]
                    check('qualification','three-target history weighting',direct[a][phase] == expected)
    check('qualification','reference tie carries zero excess',oracle((360,0,0,40))['canonical_optimal_actions']['agreement'] == [0,2])
    elapsed = perf_counter()-start
    physical_features.cache_clear(); begin = perf_counter(); collector = Collector()
    for c,k,p in islice(read_rows(),512):
        collector.row(c,k,p)
    bench = perf_counter()-begin; forecast = 90+4*bench*136499/512
    return dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),qualification_seconds=elapsed,
        symmetric_tables=len(codes),physical_and_control_laws=len(laws),history_programs=len(samples),
        benchmark_rows=512,benchmark_seconds=bench,forecast_main_seconds=forecast,requires_detached=forecast > 600,
        forecast_rule='90 seconds I/O plus four times full-workload 512-row rate')


def bridge(row,old,original):
    check('bridge','same calibration mean',row['expected_calibrations'] == F(old['expected_calibrations']['exact']))
    none = row['arms']['no_update']
    check('bridge','same original no-update cost',none['net_loss'] == F(old['no_update_net_loss']['exact']))
    check('bridge','same original error count',none['episode_expected_wrong_reports'] == 100*F(original['first_wrong_probability']['exact']))
    check('bridge','same original reference count',none['episode_expected_references'] == 100*F(original['first_reference_probability']['exact']))
    for arm,prior in (('one_update','frozen'),('two_warnings','warnings'),('two_full','full')):
        for key in ('net_loss','episode_expected_wrong_reports','episode_expected_references'):
            check('bridge','sealed outcome '+arm+' '+key,row['arms'][arm][key] == F(old['arms'][prior][key]['exact']))
    for label,prior in (('full_two_minus_one','full_minus_frozen'),('full_two_minus_none','full_minus_no_update'),('full_two_minus_warnings','full_minus_warnings')):
        check('bridge','sealed signed contrast',row['contrasts'][label]['net_difference'] == F(old['contrasts'][prior]['exact']))


def prepare(output,logline):
    check('integrity','previous manifest',identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
    check('integrity','previous report',identity(SOURCE/'FEP_SECOND_FEEDBACK_V1_REPORT.md')['sha256'] == REPORT_SHA)
    old = json.loads((PREVIOUS/'MANIFEST.json').read_text())
    preserved = list({x['path']:x for group in ('inputs','outputs','preserved') for x in old[group]}.values())
    V.verify(preserved); (output/'inputs').mkdir()
    files = [(SOURCE/name,name) for name in ('FEP_TASK_REGRET_V1.md','check_fep_task_regret.py',
        'FEP_SECOND_FEEDBACK_V1.md','FEP_SECOND_FEEDBACK_V1_REPORT.md','check_fep_second_feedback.py',
        'check_fep_active_verification.py','check_fep_verification_value.py','check_fep_reference_feedback.py',
        'check_fep_stopping_attribution.py')]
    files += [(PREVIOUS/'MANIFEST.json','second_MANIFEST.json'),(PREVIOUS/'RESULTS.json','second_RESULTS.json'),
              (V.PREVIOUS/'RESULTS.json','original_feedback_RESULTS.json')]
    inputs = []
    for p,name in files:
        inputs.append(identity(p)); shutil.copyfile(p,output/'inputs'/name)
        check('integrity','snapshot '+name,identity(output/'inputs'/name)['sha256'] == inputs[-1]['sha256'])
    inputs += [identity(p) for p in (LEDGER,V.LEDGER,A.DECISIONS)]
    write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,arms=ARMS,metrics=METRICS,
        phases=PHASES,durations=DURATIONS,truths=R.TRUTHS,post_result_analysis=True,new_gates=0,
        new_controllers=0,prior_wide_oracle_evaluation=False,known_Q_used_only_by_evaluator=True,
        prior_or_price_tuning=0,large_inputs_read_in_place=True))
    q = qualify(); write(output/'QUALIFICATION.json',q)
    logline(f'PREPARED: {q["checks"]} checks; qualification {q["qualification_seconds"]:.3f}s; main forecast {q["forecast_main_seconds"]:.1f}s; detached={q["requires_detached"]}')


def execute(output,logline):
    prep = json.loads((output/'PREPARATION.json').read_text()); qual = json.loads((output/'QUALIFICATION.json').read_text())
    for key,n in qual['groups'].items():
        R.C.COUNTS[key] += n
    V.verify(prep['inputs']+prep['preserved'])
    check('scope','first execution',not(output/'EXECUTION_STARTED.json').exists())
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    write(output/'EXECUTION_STARTED.json',dict(started_utc=started,forecast_main_seconds=qual['forecast_main_seconds']))
    collector = Collector()
    for c,k,programs in read_rows():
        collector.row(c,k,programs)
        if collector.rows % 40000 == 0:
            logline(f'Audited {collector.rows} frozen count rows')
    check('scope','all stopped policies',collector.rows == 136499 and collector.stopped == 259142)
    actual = collector.finish()
    old = json.loads((PREVIOUS/'RESULTS.json').read_text())
    original = json.loads((V.PREVIOUS/'RESULTS.json').read_text())
    aggregate = {}
    for name in V.NAMES:
        for label in R.TRUTHS:
            bridge(actual[label][name],old['truths'][label][name],original['truths'][label][name])
        avg = average([actual[label][name] for label in R.PANEL])
        original_panel = {
            key:dict(exact=str(sum(F(original['truths'][label][name][key]['exact']) for label in R.PANEL)/9))
            for key in ('first_wrong_probability','first_reference_probability')}
        bridge(avg,old['equal_panel_aggregate'][name],original_panel)
        add_ratios(avg); aggregate[name] = avg
        for label in R.TRUTHS:
            add_ratios(actual[label][name])
    oracles = {label:oracle(q) for label,q in R.TRUTHS.items()}
    write(output/'KNOWN_Q_FLOORS.json',oracles)
    for label,rows in actual.items():
        write(output/(label+'.json'),dict(Q=[F(x,BASE) for x in R.TRUTHS[label]],oracle=oracles[label],methods=rows))
    V.verify(prep['inputs']+prep['preserved'])
    summary = dict(checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS),count_rows=collector.rows,
        stopped_controller_rows=collector.stopped,panel_environments=9,excluded_shared_diagnostics=1,
        post_result_analysis=True,new_gates=0,new_controllers=0,policy_optimizations=0,
        prior_or_price_tuning=0,prior_wide_oracle_evaluation=False,cache=physical_features.cache_info()._asdict())
    write(output/'RESULTS.json',dict(summary=summary,known_Q_floors=oracles,truths=actual,equal_panel_aggregate=aggregate,
        prior_context='Original-prior outcomes remain in the preserved second-feedback record; no new prior-wide oracle calculation.'))
    wall = perf_counter()-start
    logline(f'COMPLETE: {summary["checks"]} checks; {wall:.3f}s; no changed policy or new gate')
    outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
    write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        main_wall_seconds=wall,main_cpu_seconds=process_time()-cpu,python=platform.python_version(),processes=1,
        inputs=prep['inputs'],outputs=outputs,preserved=prep['preserved'],summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('prepare','execute'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); output = args.output
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    if args.phase == 'prepare':
        output.mkdir(parents=True,exist_ok=False)
    elif not (output/'QUALIFICATION.json').exists() or (output/'FAILURE.json').exists():
        raise RuntimeError('Qualified, unfailed record required')
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(s+'\n')
        print(s,flush=True)
    try:
        logline(datetime.now(timezone.utc).isoformat()+' phase '+args.phase+'; one process; saved-policy regret audit')
        (prepare if args.phase == 'prepare' else execute)(output,logline)
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(phase=args.phase,checks=sum(R.C.COUNTS.values()),groups=dict(R.C.COUNTS)))
        raise


if __name__ == '__main__':
    main()
