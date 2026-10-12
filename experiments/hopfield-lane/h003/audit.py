"""H003 retained-data boundary checks and terminal-reader replays."""
from pathlib import Path
import json
import numpy as np
from h003 import experiment as e


def audit(out):
    out=Path(out);config=json.loads((out/'config.json').read_text());checks=[]
    def check(label,value):
        checks.append(dict(label=label,passed=bool(value)))
        if not value:
            e.save(out/'audit.json',dict(passed=False,checks=checks))
            raise AssertionError(label)
    for name in ['freeze.json','raw_sha256.json']:
        for file,expected in json.loads((out/name).read_text()).items():
            check('sha256 '+file,e.checksum(out/file)==expected)
    for seed in config['seeds']:
        with np.load(out/f'function_{seed}.npz') as raw:
            records=raw['records'];bodies=raw['bodies'];masks=raw['damage'];arms=raw['arms'].tolist()
            prefix=str(seed)+' '
            check(prefix+'dimensions',records.shape==(17,4,9,4,4,64,64))
            check(prefix+'record symmetry',np.array_equal(records,records.swapaxes(-1,-2)))
            check(prefix+'zero diagonal',not np.diagonal(records,axis1=-2,axis2=-1).any())
            check(prefix+'mask symmetry',np.array_equal(masks,masks.swapaxes(-1,-2)))
            check(prefix+'zero mask diagonal',not np.diagonal(masks,axis1=-2,axis2=-1).any())
            check(prefix+'binary activity',np.isin(bodies,[-1,1]).all())
            check(prefix+'fixed cues',np.all(bodies[...,:4]==raw['cues'][:,None]))
            check(prefix+'shared starting records',all(np.array_equal(records[0,0],records[0,j]) for j in range(1,4)))
            for name in ['protected_copy','damaged_copy']:
                a=arms.index(name)
                check(prefix+name+' shared records',all(np.array_equal(records[:,0,a],records[:,j,a]) for j in range(1,4)))
            protected=arms.index('protected_copy')
            check(prefix+'protected packet unchanged',np.array_equal(records[:,:,protected],
                np.broadcast_to(raw['initial'][:,None],records[:,:,protected].shape)))
            for g,state in enumerate(bodies):
                state=state.astype(float)
                expected=(state[...,0,:,None]*state[...,0,None,:]+state[...,1,:,None]*state[...,1,None,:])/128
                diagonal=np.arange(64);expected[...,diagonal,diagonal]=0
                expected[:,arms.index('write_off')]=0
                expected[:,protected]=records[g,:,protected]
                a=arms.index('damaged_copy');expected[:,a]=records[g,:,a]*masks[g]
                a=arms.index('writer_scrambled');p=raw['permutation']
                expected[:,a]=expected[:,a][...,p,:][...,:,p]
                check(prefix+f'boundary {g+1} independent writer equations',np.array_equal(expected,records[g+1]))
            replay=e.read_all(records[-1],raw['base'],seed,('h003','assay',16))
            check(prefix+'terminal replay',np.array_equal(replay,raw['reader_states'][-1]))
            late=np.stack([e.read_one(records[-1,0],raw['base'],seed,('h003','assay',16),4.,e.INPUTS),
                           e.read_one(records[-1,0],raw['base'],seed,('h003','assay',16),1.,e.INPUTS,sweeps=32)])
            check(prefix+'late/long replays',np.array_equal(late,raw['late_states']))
            check(prefix+'protected sustained/late gain4 identity',np.array_equal(late[0,protected],raw['reader_states'][-1,2,protected]))
            for array,stored_metric,stored_success,stored_category in [
                (raw['reader_states'],raw['metric'],raw['success'],raw['reader_category']),
                (raw['late_states'],raw['late_metric'],raw['late_success'],raw['late_category'])]:
                metric,success=e.h001.score(array,'function',raw['founder'],raw['cues'])
                check(prefix+'reader endpoints',np.array_equal(metric,stored_metric) and np.array_equal(success,stored_success))
                check(prefix+'disjoint endpoint categories',np.array_equal(e.categories(array),stored_category) and np.array_equal(stored_category==0,stored_success))
            check(prefix+'body endpoints',np.array_equal(e.categories(bodies),raw['body_category']) and np.array_equal(raw['body_category']==0,raw['body_success']))
            for gain,sites in zip(e.GAINS,e.SITES):
                weight=e.effective_weights(raw['base'],records[-1,0,0,0,0],gain,sites)
                check(prefix+f'effective symmetry {gain}/{sites[0]}',np.array_equal(weight,weight.T) and not np.diag(weight).any())
    result=dict(passed=True,checks_count=len(checks),checks=checks)
    e.save(out/'audit.json',result)
    return result
