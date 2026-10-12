"""Post-hoc response and cue-link diagnosis of the sealed H002 cohort."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import time
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent
LANE=HERE.parent
sys.path.insert(0,str(LANE))
import model as m

LABELS=('intended','opposite','same_response_to_both_cues','weak_or_mixed')


def categories(states):
    """Classify two cue trials; original output margins stay unchanged."""
    a=states[...,8:16].mean(axis=-1)
    b=states[...,16:24].mean(axis=-1)
    orientation=np.where((a>.5)&(b<-.5),1,np.where((a<-.5)&(b>.5),-1,0))
    rules=np.array([1,1,-1,-1])[:,None,None]
    intended=rules*np.array([-1,1])
    result=np.full(orientation.shape[:-1],3,dtype=np.int8)
    result[np.all(orientation==intended,axis=-1)]=0
    result[np.all(orientation==-intended,axis=-1)]=1
    result[(orientation[...,0]!=0)&(orientation[...,0]==orientation[...,1])]=2
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(LANE):raise ValueError('Keep output within lane')
    out.mkdir(parents=True,exist_ok=False)
    source=LANE/'runs/h002_development_v1'
    original=json.loads((source/'config.json').read_text())
    checksums=json.loads((source/'raw_sha256.json').read_text())
    started=time.perf_counter()
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    save('config.json',dict(classification='POST_HOC_DIAGNOSIS_OF_H002',source=str(source),
        seeds=original['seeds'],labels=LABELS,output_margin=.5,source_config_sha256=hashlib.sha256((source/'config.json').read_bytes()).hexdigest()))
    shutil.copyfile(__file__,out/'diagnose.py')
    save('STATUS.json',dict(state='RUNNING',completed_blocks=0))
    try:
        reader_labels=[];body_labels=[];cue_links=[];opposition=[];identities=[]
        for i,seed in enumerate(original['seeds']):
            path=source/f'function_{seed}.npz'
            if hashlib.sha256(path.read_bytes()).hexdigest()!=checksums[path.name]:
                raise RuntimeError('Source raw checksum mismatch')
            with np.load(path) as raw:
                reader=categories(raw['reader_states'])
                body=categories(raw['bodies'])
                assert np.array_equal(reader==0,raw['success'])
                assert np.array_equal(body==0,raw['body_success'])
                records=raw['records']
                # Dimensionless cue-output relation, +1 for the taught founder.
                rule=np.array([1,1,-1,-1])[:,None]
                cue=(records[..., :4,8:16].mean(axis=(-2,-1))-
                     records[..., :4,16:24].mean(axis=(-2,-1)))*32*rule
                opp=-64*records[...,8:16,16:24].mean(axis=(-2,-1))
                states=raw['bodies'].astype(float)
                relation=(states[...,8:16].mean(axis=-1)-states[...,16:24].mean(axis=-1))/2
                relation=(relation*np.array([-1,1])).mean(axis=-1)*rule
                # For a complete writer with four fixed input sites, the next
                # record's signed cue link equals the expressed relation.
                identities.append(bool(np.array_equal(cue[1:,:,0,0],relation[:,:,0,0])))
                reader_labels.append(reader);body_labels.append(body)
                cue_links.append(cue);opposition.append(opp)
                checkpoints=raw['checkpoints'].tolist();arms=raw['arms'].tolist()
                del records
            save('STATUS.json',dict(state='RUNNING',completed_blocks=i+1))
        readers=np.array(reader_labels);bodies=np.array(body_labels)
        cues=np.array(cue_links);opposition=np.array(opposition)
        np.savez_compressed(out/'diagnostics.npz',reader_category=readers,body_category=bodies,
            cue_link=cues,output_opposition=opposition,labels=np.array(LABELS),seeds=np.array(original['seeds']))
        res=dict(classification='POST_HOC_DIAGNOSIS_OF_H002',blocks=len(original['seeds']),
            cue_link_writer_identity=all(identities),checkpoints=checkpoints,panels={})
        for s,support in enumerate([8,4]):
            for w,writer in enumerate(['complete','retained']):
                for arm in ['renewal','foreign','protected_copy','damaged_copy']:
                    a=arms.index(arm);key=f'{support}/{writer}/{arm}'
                    rc=readers[:,: ,s,w,a];bc=bodies[:,:,s,w,a]
                    res['panels'][key]=dict(
                        reader_by_checkpoint={label:(rc==k).mean(axis=(0,2,3)).tolist() for k,label in enumerate(LABELS)},
                        body_by_generation={label:(bc==k).mean(axis=(0,2,3)).tolist() for k,label in enumerate(LABELS)},
                        cue_link_by_generation=cues[:,:,s,w,a].mean(axis=(0,2,3)).tolist(),
                        positive_cue_link_by_generation=(cues[:,:,s,w,a]>.1).mean(axis=(0,2,3)).tolist(),
                        negative_cue_link_by_generation=(cues[:,:,s,w,a]<-.1).mean(axis=(0,2,3)).tolist(),
                        near_zero_cue_link_by_generation=(abs(cues[:,:,s,w,a])<=.1).mean(axis=(0,2,3)).tolist(),
                        opposition_by_generation=opposition[:,:,s,w,a].mean(axis=(0,2,3)).tolist())
        if not all(identities):raise RuntimeError('Cue-link writer identity failed')
        save('summary.json',res)
        lines=['# H002 post-hoc functional diagnosis','',
            'These are descriptive analyses of existing H002 outcomes. No new cohort and no change to its failed gates.','',
            '| Support / writer / incoming record | Intended | Opposite | Same confident response to both cues | Weak/mixed |',
            '|---|---:|---:|---:|---:|']
        for key,panel in res['panels'].items():
            rates=[panel['reader_by_checkpoint'][label][-1] for label in LABELS]
            lines.append('| '+key+' | '+' | '.join(f'{100*x:.2f}%' for x in rates)+' |')
        lines.extend(['',
            'For a complete writer, the mean signed connection from the four input sites to the two output patches is exactly the mean expressed cue/output relation. This identity passed for every stored own-record boundary. If both cue trials produce the same output state, their contributions to these cue connections cancel. Correct and opposite conditional responses write opposite cue-link signs.',
            'This algebra and the saved trajectories motivate intervention; they do not by themselves distinguish a read failure from irreversible record loss.', ''])
        (out/'REPORT.md').write_text('\n'.join(lines))
        save('checksums.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='STATUS.json'})
        save('STATUS.json',dict(state='COMPLETE',elapsed_seconds=time.perf_counter()-started,completed_blocks=len(original['seeds'])))
        print(out/'REPORT.md',flush=True)
    except BaseException:
        save('STATUS.json',dict(state='FAILED',traceback=traceback.format_exc()))
        raise


if __name__=='__main__':main()
