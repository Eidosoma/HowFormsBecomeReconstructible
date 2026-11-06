"""Read-only E119 writer adapter; output stays in the theory-tests lane."""
from study import *
from instrument import record

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--body',required=True);p.add_argument('--selection',required=True)
    p.add_argument('--mapping',required=True,help='Original selected-set slot per body slot; -1 means empty')
    p.add_argument('--reference',required=True,help='Paired intact body slot per body slot')
    p.add_argument('--output',required=True)
    a=p.parse_args();body=load(a.body);selection=load(a.selection)['eligible']
    mapping=[int(x) for x in a.mapping.split(',')];reference=[int(x) for x in a.reference.split(',')]
    assert len(mapping)==len(reference)==len(body['incoming'])
    e=np.stack([np.zeros_like(selection[0]) if i==-1 else selection[i] for i in mapping])
    output=Path(a.output).resolve();assert output.is_relative_to(LANE),'Outputs belong to the theory-tests lane'
    output.parent.mkdir(parents=True,exist_ok=True)
    result=record(body['incoming'],body['incoming'][reference],e,body['masks'],body)
    save(output,result)
    write(output.with_suffix('.receipt.json'),dict(utc=now(),status='PASS',
        inputs={str(Path(x).resolve()):sha(x) for x in (a.body,a.selection)},output_sha256=sha(output),
        rng_used=False,trajectories_changed=False,reference=reference,mapping=mapping))
    print(json.dumps(dict(status='PASS',output=str(output))))

if __name__=='__main__':main()

