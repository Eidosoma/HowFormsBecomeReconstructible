"""Audit retained H002 boundaries and replay independent terminal readers."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import experiment as e


def audit(out):
    out=Path(out)
    config=json.loads((out/'config.json').read_text())
    checks=[]
    def check(label, passed):
        checks.append({'label':label,'passed':bool(passed)})
        if not passed:
            (out/'audit.json').write_text(json.dumps({'passed':False,'checks':checks},indent=2)+'\n')
            raise AssertionError(label)
    for ledger in ['freeze.json','raw_sha256.json']:
        for name,expected in json.loads((out/ledger).read_text()).items():
            check('sha256 '+name,hashlib.sha256((out/name).read_bytes()).hexdigest()==expected)
    for seed in config['seeds']:
        for task in ['capture','function']:
            with np.load(out/f'{task}_{seed}.npz') as raw:
                label=f'{task}/{seed}'
                records=raw['records']; bodies=raw['bodies']; masks=raw['damage']
                arms=raw['arms'].tolist(); own=arms.index('renewal')
                check(label+' dimensions', records.shape==(config['generations']+1,2,2,9,4,4,64,64))
                check(label+' symmetric records',np.array_equal(records,records.swapaxes(-1,-2)))
                check(label+' zero diagonals',not np.diagonal(records,axis1=-2,axis2=-1).any())
                check(label+' symmetric masks',np.array_equal(masks,masks.swapaxes(-1,-2)))
                check(label+' zero mask diagonals',not np.diagonal(masks,axis1=-2,axis2=-1).any())
                check(label+' binary states',np.isin(bodies,[-1,1]).all())
                check(label+' same first bodies across writers',np.array_equal(bodies[0,:,0],bodies[0,:,1]))
                check(label+' same initial records across support',np.array_equal(records[0,0],records[0,1]))
                check(label+' same initial records across writers',np.array_equal(records[0,:,0],records[0,:,1]))
                for name in ['protected_copy','damaged_copy']:
                    index=arms.index(name)
                    check(label+' '+name+' across writers',np.array_equal(records[:,:,0,index],records[:,:,1,index]))
                    check(label+' '+name+' across cue support',np.array_equal(records[:,0,:,index],records[:,1,:,index]))
                for g,body in enumerate(bodies):
                    incoming=records[g]
                    surviving=incoming*masks[g]
                    protected=arms.index('protected_copy')
                    surviving[:,:,protected]=incoming[:,:,protected]
                    expected=np.zeros_like(incoming)
                    for s in range(2):
                        for w,retention in enumerate([0.,.5]):
                            for a,arm in enumerate(arms):
                                if arm=='protected_copy':
                                    value=incoming[s,w,a]
                                elif arm=='damaged_copy':
                                    value=surviving[s,w,a]
                                else:
                                    # Reconstruct directly from each stored cue trial.
                                    state=body[s,w,a].astype(float)
                                    value=sum(state[...,t,:,None]*state[...,t,None,:]
                                              for t in range(state.shape[-2]))/(64*state.shape[-2])
                                    diagonal=np.arange(64);value[...,diagonal,diagonal]=0
                                    if arm=='write_off':value.fill(0)
                                    if arm=='writer_scrambled':
                                        p=raw['permutation'];value=value[...,p,:][...,:,p]
                                    value=(1-retention)*value+retention*surviving[s,w,a]
                                expected[s,w,a]=value
                    check(label+f' boundary {g+1} exact equations',np.array_equal(expected,records[g+1]))
                    for s,support in enumerate([8,4]):
                        check(label+f' boundary {g+1} cue {support}',
                              np.all(body[s,...,:support]==raw['cues'][:,None]))
                replay=e.fresh_reader(records[-1],raw['base'],seed,(task,'h002_assay',config['generations']),raw['cues'])
                check(label+' terminal fresh-reader replay',np.array_equal(replay,raw['reader_states'][-1]))
                metric,success=e.h001.score(raw['reader_states'],task,raw['founder'],raw['cues'])
                check(label+' fresh-reader endpoints',np.array_equal(success,raw['success']) and np.array_equal(metric,raw['metric']))
                body_metric,body_success=e.h001.score(bodies,task,raw['founder'],raw['cues'])
                check(label+' body endpoints',np.array_equal(body_success,raw['body_success']) and np.array_equal(body_metric,raw['body_metric']))
                for s,w,founder,replicate in [(0,0,0,0),(1,1,3,3)]:
                    state=bodies[-1,s,w,own,founder,replicate]
                    if task=='capture':
                        score=sum(int(x)==int(y) for x,y in zip(state[0,8:],raw['founder'][founder,0,8:]))/56
                        correct=score>=.9
                    else:
                        scores=[]
                        for cue,row in zip(raw['cues'],state):
                            target=([1,1,-1,-1][founder])*cue
                            scores.extend([target*sum(int(x) for x in row[8:16])/8,
                                          -target*sum(int(x) for x in row[16:24])/8])
                        score=min(scores);correct=score>.5
                    check(label+f' scalar endpoint {s}/{w}',correct==bool(raw['body_success'][-1,s,w,own,founder,replicate]))
    result={'passed':True,'checks_count':len(checks),'checks':checks}
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    print(json.dumps({'passed':audit(sys.argv[1])['passed']}))
