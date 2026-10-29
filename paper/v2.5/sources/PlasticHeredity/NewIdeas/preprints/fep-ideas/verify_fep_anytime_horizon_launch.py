#!/usr/bin/env python3
"""Check the frozen horizon study without importing any policy or simulator."""
import argparse
import sys
sys.dont_write_bytecode=True
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from datetime import datetime,timezone

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
OUTPUT=parser.parse_args().output
assert OUTPUT.parent==Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-horizon-v1')
CHECKS=0

def check(ok,label):
    global CHECKS
    if not bool(ok):raise AssertionError(label)
    CHECKS+=1

def identity(path):
    path=Path(path);h=sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=h.hexdigest())

def main():
    start=perf_counter()
    mount=json.loads(subprocess.check_output(['findmnt','-J','-T','/mnt/bioIce1','-o','TARGET,SOURCE,FSTYPE'],text=True))['filesystems'][0]
    check(mount==dict(target='/mnt/bioIce1',source='/dev/sdc1',fstype='ext4'),'external mount')
    check(not (OUTPUT/'EXECUTION_STARTED.json').exists(),'main not started')
    check(not list(OUTPUT.glob('FAILURE*')) and not (OUTPUT/'FEASIBILITY_STOP.json').exists(),'no stopped preparation')
    prep,pop,seeds,qual,bench=[json.loads((OUTPUT/n).read_text()) for n in
        ('PREPARATION.json','POPULATION.json','SEEDS.json','QUALIFICATION.json','BENCHMARK.json')]
    for group in ('inputs','source_snapshots','preserved'):
        for rec in prep[group]:check(identity(rec['path'])==rec,group+' identity')
    check(len(prep['inputs'])==6 and len(prep['source_snapshots'])==4,'six inputs and four snapshots')
    for rec in prep['source_snapshots']:
        check(any(rec['sha256']==item['sha256'] and rec['bytes']==item['bytes'] for item in prep['inputs']),'matching source snapshot')
    previous=OUTPUT.parent.parent/'fep-anytime-change-v1/attempt-02'
    check(identity(previous/'MANIFEST.json')['sha256']=='ffef707794cc6f4f4149de2f09d11f368b23d4d48ae52ce4fe3468966b1b2573','unchanged completed reference')
    old=json.loads((previous/'POPULATION.json').read_text())
    for k,v in old.items():
        if k!='arms':check(pop[k]==v,'unchanged population/model '+k)
    check(pop['arms']==old['arms']+['CT1-anytime','CT4-anytime'] and len(pop['arms'])==12,'ten unchanged arms plus horizons')
    horizons={'CT1-anytime':1,'CT3-anytime':3,'CT4-anytime':4}
    check(pop['horizons']==prep['horizons']==horizons,'prospective horizons')
    check(pop['blocks_per_base']==prep['blocks_per_base']==256 and pop['primary']=='CT4-anytime','fixed sample and primary')
    check(len(pop['bases'])==27 and len(pop['conditions'])==43,'complete population')
    check(pop['learner_change_times']==list(range(1,101)) and pop['old_learner_change_times']==[26,51,76] and pop['unexpected_physical_times']==[13,38,63,88],'timing separation')
    check(pop['model_prior']==dict(no_change='1/2',per_time_kind='1/600',kinds=['G','A','B'],conditional_hazard='1/(201-t)',hypotheses=301),'unchanged prior')
    check(pop['coefficient_denominator']==144 and pop['post_scale']==34234200,'exact denominators')
    for name,co in pop['coefficients'].items():
        check(len(co)==43 and all(isinstance(x,int) and x>=0 for x in co) and sum(co)==144,'weights '+name)
        if name.endswith('_full'):check(co[0]==72,'half stable '+name)
        if name.startswith('supported_'):check(all(x==0 for x in co[19:]),'supported isolation '+name)
        if name.startswith('unexpected_'):check(all(x==0 for x in co[1:19]),'unexpected isolation '+name)
    all_seeds=set()
    for group,prefix in [('blocks','fep-anytime-horizon-v1'),('flip_blocks','fep-anytime-horizon-v1-transfer-flips')]:
        check(set(seeds[group])=={m['label'] for m in pop['bases']},'all seed strata')
        for label,values in seeds[group].items():
            check(len(values)==256,'seed stratum size')
            for block,value in enumerate(values):
                expected=str(int.from_bytes(sha256(f'{prefix}|20260924|{label}|{block}'.encode('ascii')).digest(),'big'))
                check(value==expected,'seed derivation');all_seeds.add(value)
    check(len(all_seeds)==13824,'unique main and flip seeds')
    for study,attempt in [('fep-anytime-change-v1','02'),('fep-unexpected-change-v1','01'),('fep-weak-prior-confirmation-v1','01'),
            ('fep-calibrated-change-v1','02'),('fep-changing-world-v1','01'),('fep-future-aware-checking-v1','01'),('fep-three-decision-checking-v1','01')]:
        old_seeds=json.loads((OUTPUT.parent.parent/study/f'attempt-{attempt}/SEEDS.json').read_text())
        values={x for group in ('blocks','flip_blocks') for row in old_seeds.get(group,{}).values() for x in row}
        check(not all_seeds.intersection(values),'prior cohort separation '+study)
    check(qual['status']=='PASS' and qual['new_policy_implementations']==2 and qual['old_arrays']==29,'qualification and old arrays')
    check(qual['inherited_filter'] and qual['three_step_bridge'] and qual['same_three_evaluator_fields']==15,'unchanged filter/evaluator bridge')
    check(qual['rational_cases']==15 and qual['fresh_one_four_worker_chunks']==4 and qual['horizons']==horizons,'rational and parallel references')
    check(bench['workers']==4 and bench['synthetic_blocks']==32 and bench['conditions_per_block']==43 and bench['arms']==12,'benchmark scope')
    check(bench['forecast_seconds']==120+3*bench['wall_seconds']*6912/32,'frozen forecast')
    check(bench['requires_detached']==(bench['forecast_seconds']>600),'detachment rule')
    check(bench['maximum_forecast_seconds']==14*86400 and bench['within_compute_bound'] and bench['forecast_seconds']<=14*86400,'prospective compute bound')
    check(prep['cpus']==[0,1,2,3] and all(r['cpus']==prep['cpus'] for r in bench['records']),'four CPU records')
    check(not (OUTPUT/'EXECUTION_STARTED.json').exists(),'still no main execution')
    source=Path(__file__).resolve();snapshot=OUTPUT/source.name
    check(not snapshot.exists() and not (OUTPUT/'PRELAUNCH.json').exists(),'new verifier records')
    shutil.copyfile(source,snapshot)
    result=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),assertions=CHECKS,wall_seconds=perf_counter()-start,
        source=identity(source),snapshot=identity(snapshot),verified_inputs=len(prep['inputs']),verified_snapshots=len(prep['source_snapshots']),
        verified_preserved=len(prep['preserved']),recomputed_seeds=len(all_seeds),main_started=False,policy_imported=False,
        preparation=identity(OUTPUT/'PREPARATION.json'),qualification=identity(OUTPUT/'QUALIFICATION.json'),benchmark=identity(OUTPUT/'BENCHMARK.json'))
    with (OUTPUT/'PRELAUNCH.json').open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
