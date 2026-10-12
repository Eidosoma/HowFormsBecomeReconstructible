"""Native-score factorial panels; primary contrasts shown with family intervals."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import dump,sha,utc
from E057_fresh_capture_confirmation.plan import HERE,NAMES,HISTORIES,PRIMARY
from E056_sign_magnitude_substitution.plan import TIMES,ARMS
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(mode):
    run=HERE/'runs'/NAMES[mode];dest=HERE/'figures'/NAMES[mode]
    a=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert a['status']=='PASS' and a['complete_sha256']==sha(run/'COMPLETE.json')
    s=json.loads((run/'summary.json').read_text());stats=s['statistics']
    dest.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(3,2,figsize=(11,10),sharey=True)
    for h,history in enumerate(HISTORIES):
        for t,time in enumerate(TIMES):
            ax=axes[h,t];keys=[f'fresh/both/{history}/{time}/{a}/scattered' for a in ARMS[:4]]
            y=np.array([stats[k]['mean'] for k in keys])*100;b=np.array([stats[k]['interval'] for k in keys])*100
            ax.errorbar(range(4),y,yerr=np.maximum(0,np.stack((y-b[:,0],b[:,1]-y))),fmt='o',capsize=4)
            ax.set_xticks(range(4),('Unstressed','Disturbed','Restore\nsigns','Restore\nstrengths'),fontsize=9)
            ax.set_ylim(-3,103);ax.grid(alpha=.2);ax.set_title(history.replace('_',' ')+': '+time)
            ax.set_ylabel('Fresh-reader success (%)')
    fig.suptitle('E057: fresh confirmation of capture timing and strengths\n'+s['status']+'; scattered injury; pointwise 95% intervals',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.95))
    for ext in ('png','svg'):fig.savefig(dest/f'substitutions.{ext}',dpi=160)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5))
    keys=['primary/'+k for k in PRIMARY]
    y=np.array([stats[k]['mean'] for k in keys])*100;b=np.array([stats[k]['interval'] for k in keys])*100
    ax.errorbar(y,range(4),xerr=np.maximum(0,np.stack((y-b[:,0],b[:,1]-y))),fmt='o',capsize=4)
    ax.set_yticks(range(4),('Early pulse loss','Benefit of recovery before capture',
        'Restore strengths: pulse signs','Restore strengths: sham signs'))
    ax.axvline(0,color='gray',linestyle=':');ax.set_xlabel('Change in success (percentage points)')
    ax.set_title('Fresh shared-noise history, scattered injury\nFour primary contrasts; Bonferroni 98.75% intervals')
    ax.grid(alpha=.2);fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(dest/f'primary_contrasts.{ext}',dpi=160)
    plt.close(fig)
    dump(dest/'provenance.json',dict(utc=utc(),audit_sha256=sha(run/'INDEPENDENT_AUDIT.json'),
        summary_sha256=sha(run/'summary.json'),plot_code_sha256=sha(__file__),
        outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir()) if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=NAMES);main(p.parse_args().mode)
