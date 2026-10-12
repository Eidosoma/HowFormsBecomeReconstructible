"""Complete recovery after a preserved subprocess import-path failure."""
import json, shutil, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,finish,sha,utc
from E015_functional_inheritance.audit import verify
from E037_repair_support_diagnosis import diagnose
import numpy as np
cap_cpus(8);start=time.monotonic();freeze=HERE/'analysis/freeze_v1'
check_inputs(freeze)
failed=HERE/'analysis/recovery_status.json'
assert json.loads(failed.read_text())['status']=='FAILED'
preserved=HERE/'analysis/recovery_failure_v1.json';assert not preserved.exists()
shutil.copyfile(failed,preserved)
dump(HERE/'analysis/continuation_v1.json',dict(utc=utc(),code_sha256=sha(__file__),
    preserved_failure_sha256=sha(preserved),reason='Recovered support-check script assumes root on sys.path; execute it as a module from the experiment root. Numerical code and retained measurements are unchanged.'))
dest=HERE/'runs/diagnosis_v1';summary=json.loads((dest/'summary.json').read_text())
previous=json.loads((HERE/'analysis/original_selected_means.json').read_text())
assert json.loads(json.dumps(diagnose.selected(summary['series'])))==previous
result=subprocess.run([sys.executable,'-B','-m','E037_repair_support_diagnosis.support_check'],
    cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,check=True)
support=json.loads(result.stdout)
old=json.loads((HERE/'analysis/original_in_memory_receipts.json').read_text())['support']
for k,v in old.items():
    if k not in ('utc','seconds'):assert support[k]==v,k
dump(dest/'support_check.json',dict(artifact_persisted=True,result=support))
                # Plot native saved-record quantities; no new trajectories.
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
                style={0:('Standard + preserve','#2879B9'),2:('Cue contrast + preserve','#D65A31'),
                       3:('Cue contrast + rewrite','#9863B5'),8:('Damaged copying','#777777')}
                for c,(label,color) in style.items():
                    key=diagnose.CONDITIONS[c]
                    means=lambda kind,gens,field: [summary['series'][f'{kind}.g{g}.{key}.{field}']['mean'] for g in gens]
                    axes[0,0].plot(range(17),means('packet',range(17),'nonzero'),label=label,color=color)
                    axes[0,1].plot(range(2,17),np.array(means('repair',range(2,17),'returning_nonzero_rate'))*100,color=color)
                    if c<7:axes[1,0].plot(range(1,17),np.array(means('body',range(1,17),'both_correct'))*100,color=color)
                    axes[1,1].plot(diagnose.HORIZONS,np.array(means('terminal',diagnose.HORIZONS,'scattered.both_correct'))*100,'o-',color=color)
                for ax,title,ylabel in zip(axes.flat,
                    ('Connections retained','Connections restored when available again','Current-body function','Fresh-receiver function under scattered damage'),
                    ('Mean nonzero connections','Restored (%)','Both cues correct (%)','Both cues correct (%)')):
                    ax.set(title=title,xlabel='Replacement generation',ylabel=ylabel)
                    ax.grid(alpha=.2)
                axes[0,0].legend(fontsize=8)
                fig.suptitle('E037: saved E036 histories — descriptive diagnosis, no new simulations',fontsize=12)
                fig.savefig(dest/'diagnosis.png',dpi=150);fig.savefig(dest/'diagnosis.svg');plt.close(fig)
                text="""# E037 — missing repair under cue-only writing

The unchanged in-memory analysis was recovered and rerun on all 32 E036 blocks,
512 lineages, sixteen boundaries and all saved assay horizons. All previously
reported selected means reproduced exactly. No new trajectories ran.

Both contrast policies restored 0 of 572,280 connections that became physically
available after being absent in the preceding body. Standard policies restored
566,862 (99.05%), all initially weak (absolute weight <=0.5). Contrast-preserve
and cumulative-damage-copy nonzero masks matched at every coordinate in all
8,192 lineage-boundaries. Neither contrast policy filled any available exact
zero during generations 2–16.

In this apparatus, a returning cell has zero incident inherited weights. Paired
birth/noise and local reading make its activity identical under opposite cues.
Its cue difference is zero, so the pure difference-product writer cannot
reconnect it. This predicts an inability to regrow connections to those cells;
a rescue intervention has not yet tested whether fixing that limitation
improves durable function.

The standard-preserve chain retains mean 419.99 nonzero / 315.55 strong edges
at generation 16. Every output remains reachable through nonzero connections,
and 91.60% of records connect all outputs through strong edges, yet scattered
both-cue success is 56.64%. Its remaining loss cannot be explained by absent
graph paths alone; these graphs omit signs and strength and are not functional
sufficiency tests.

Measurements, block totals and 10,000-resample whole-block intervals are in
summary.json. All intervals are descriptive and pointwise. Connection
opportunities and boundaries are repeated observations, not independent
replicates. Per-block arrays are retained in measurements_*.npz.

Independent checks reproduce all measured quantities, source body/terminal
means and bootstrap intervals. This recovery preserves the original diagnostic
program hashes and the earlier in-memory receipts. It is a reproducibility
check on reused data, not a fresh scientific confirmation.

Next candidate: preserve strong inherited values; on available weak coordinates,
use cue-contrast capture when nonzero, otherwise ordinary coactivity. Compare
against pure contrast and delayed standard writing on fresh serial histories.
"""
                (dest/'REPORT.md').write_text(text)

dump(dest/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),**summary['validation'],
    source_complete_sha256=summary['source_complete_sha256'],analysis_code_sha256=sha(HERE/'diagnose.py'),
    no_new_trajectories=True,original_in_memory_means_reproduced=True,
    preserved_recovery_failure_sha256=sha(preserved),continuation_code_sha256=sha(__file__)))
finish(dest,start,dict(experiment='E037',mode='scientific',artifact_recovery=True))
check_inputs(freeze);finish(freeze,start)
receipts={}
for name in ('benchmark_v1','diagnosis_v1'):
    verify(HERE/'runs'/name)
    receipts[name]=dict(complete_sha256=sha(HERE/'runs'/name/'COMPLETE.json'),
        audit_sha256=sha(HERE/'runs'/name/'INDEPENDENT_AUDIT.json'))
dump(HERE/'analysis/closeout_v1.json',dict(status='PASS',utc=utc(),receipts=receipts,
    freeze_complete_sha256=sha(freeze/'COMPLETE.json'),preserved_failure_sha256=sha(preserved),
    continuation_code_sha256=sha(__file__),no_new_trajectories=True,
    original_analysis_code_unchanged=True,all_original_means_reproduced=True,
    available_bytes=shutil.disk_usage(ROOT).free))
dump(failed,dict(status='COMPLETE',utc=utc(),closeout_sha256=sha(HERE/'analysis/closeout_v1.json'),
    no_new_trajectories=True,preserved_failure='analysis/recovery_failure_v1.json'))
print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-start),indent=2),flush=True)
