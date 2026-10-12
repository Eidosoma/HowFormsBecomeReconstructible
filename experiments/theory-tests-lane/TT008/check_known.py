"""Historical schema coverage and deliberately damaged qualification fixtures.

These checks load already exposed sources; they do not simulate test blocks or
replace the full known-trajectory replay gate.
"""
from unittest.mock import patch
import numpy as np
import auditor as audit
import engine
import support as s


def must_reject(call,label):
    try:call()
    except ValueError:return
    raise AssertionError('Accepted damaged historical fixture: '+label)


def run():
    checks=[];rejections=[]
    for generation in [*range(3,33),None]:
        expected=engine.known_expected(generation)
        fields={'masks','end','mean_ports'}|({'outgoing'} if generation is not None else set())
        if generation!=3:fields.add('birth')
        s.require(set(expected)==fields,'Historical native schema coverage')
        # A fixture for comparison plumbing, not a simulated trajectory.
        fixture={k:v.copy() for k,v in expected.items()}
        if generation==3:fixture['birth']=np.zeros((4,4,2,16,16),dtype=np.float64)
        receipt=engine.check_known(fixture,generation)
        s.require(receipt['arrays']==len(fields),'Every retained native field compared')
        checks.append(dict(generation=generation,fields=sorted(fields),arrays=receipt['arrays'],
            historically_unretained_fields=receipt['historically_unretained_fields']))
        if generation not in (3,4,None):continue
        for field in fields:
            damaged={k:v.copy() for k,v in fixture.items()}
            value=damaged[field].flat[0]
            damaged[field].flat[0]=not value if damaged[field].dtype.kind=='b' else value+1
            label=f'{generation}/{field}'
            must_reject(lambda:engine.check_known(damaged,generation),label);rejections.append(label)
        missing={k:v for k,v in fixture.items() if k!='birth'}
        must_reject(lambda:engine.check_known(missing,generation),f'{generation}/missing_native_birth')
        rejections.append(f'{generation}/missing_native_birth')
    original_load=engine.load_arrays
    for generation,field in [(3,'masks'),(4,'birth'),(None,'birth')]:
        def omit(path):
            values=original_load(path);values.pop(field);return values
        with patch.object(engine,'load_arrays',side_effect=omit):
            must_reject(lambda:engine.known_expected(generation),f'{generation}/missing_saved_{field}')
        rejections.append(f'{generation}/missing_saved_{field}')
    # Historical g3 projection must never weaken the separate full native replay.
    fixture={k:v.copy() for k,v in engine.known_expected(4).items()}
    damaged={k:v.copy() for k,v in fixture.items()};damaged['birth'].flat[0]+=1
    must_reject(lambda:audit.equal(damaged,fixture,'independent_birth'),'independent_birth')
    rejections.append('independent_birth')
    return dict(status='PASS',historical_boundaries_and_assays=len(checks),
        historical_native_arrays=sum(r['arrays'] for r in checks),schema_checks=checks,
        deliberately_damaged_fixtures_rejected=rejections,full_known_replay_pass_claimed=False,
        new_test_blocks_generated=0)


if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2))
