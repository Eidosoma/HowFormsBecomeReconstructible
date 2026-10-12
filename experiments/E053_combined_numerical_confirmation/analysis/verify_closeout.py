"""Read-only scientific closeout on a user-requested status check."""
import argparse
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parents[1]; ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import check_inputs,dump,sha,utc
from E015_functional_inheritance.audit import verify


def main(inspected):
    assert inspected,'Inspect the scientific figure before closeout'
    result={}; all_hashes={}
    for name,blocks in (('fixture_v1',1),('benchmark_v1',1),('robustness_v1',32)):
        run=HERE/'runs'/name; m=verify(run)
        read=lambda p:json.loads(p.read_text())
        complete=read(run/'COMPLETE.json'); a=read(run/'INDEPENDENT_AUDIT.json'); s=read(run/'summary.json')
        assert len(m['inputs_sha256'])==25 and len(m['contract']['blocks'])==blocks
        assert len(complete['outputs_sha256'])==42*blocks+28
        assert a['status']=='PASS' and a['complete_sha256']==sha(run/'COMPLETE.json')
        assert a['audit_code_sha256']==sha(HERE/'audit.py') and a['summaries_checked']==len(s['statistics'])
        assert a['all_dynamics_channels_and_assays_replayed'] and a['all_mechanism_diagnostics_replayed']
        assert a['scientific_decision']==s['primary_decision']
        assert a['ten_single_stress_histories_byte_exact']==(name!='robustness_v1')
        fig=HERE/'figures'/name/'provenance.json'; p=read(fig)
        assert p['audit_sha256']==sha(run/'INDEPENDENT_AUDIT.json') and p['summary_sha256']==sha(run/'summary.json')
        assert p['plot_code_sha256']==sha(HERE/'plot.py')
        for rel,digest in p['outputs_sha256'].items(): assert sha(fig.parent/rel)==digest
        for file in (run/'COMPLETE.json',run/'INDEPENDENT_AUDIT.json',run/'summary.json',fig):
            all_hashes[str(file.relative_to(ROOT))]=sha(file)
        result[name]=dict(original_outputs_verified=len(complete['outputs_sha256']),
            status=s['status'],body_cue_observations=a['body_cue_observations'],terminal_cue_observations=a['terminal_cue_observations'])
    for name in ('benchmark_v1','robustness_v1'):
        job=HERE/'jobs'/name; check_inputs(job); status=json.loads((job/'status.json').read_text())
        assert status['status']=='COMPLETE'
        assert status['complete_sha256']==sha(HERE/'runs'/name/'COMPLETE.json')
        assert status['audit_sha256']==sha(HERE/'runs'/name/'INDEPENDENT_AUDIT.json')
    check_inputs(HERE/'analysis/freeze_v1')
    for rel,digest in json.loads((HERE/'SOURCE_DATA.json').read_text())['sha256'].items(): assert sha(ROOT/rel)==digest
    outcome=dict(status='PASS',utc=utc(),runs=result,evidence_sha256=all_hashes,figure_inspected=True,
        scientific_retained_bytes=sum(p.stat().st_size for p in (HERE/'runs/robustness_v1').rglob('*') if p.is_file()),
        free_bytes=shutil.disk_usage(HERE).free,code_sha256=sha(__file__),automatic_successor_started=False)
    dest=HERE/'analysis/closeout_v1.json'; assert not dest.exists(); dump(dest,outcome)
    print(json.dumps(outcome,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--figure-inspected',action='store_true'); main(p.parse_args().figure_inspected)
