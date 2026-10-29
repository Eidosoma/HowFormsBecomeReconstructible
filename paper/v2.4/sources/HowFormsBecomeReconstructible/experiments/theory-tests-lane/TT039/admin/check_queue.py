"""Small isolated tests of queue state transitions; never launches a job."""
import importlib.util
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from common import *
spec=importlib.util.spec_from_file_location('tt039_controller',root/'admin/controller.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
directory=root/'checks/queue_controller_v1';directory.mkdir(parents=True,exist_ok=False)
fixture=directory/'fixture';fixture.mkdir()
write(fixture/'CURRENT_EXECUTION.json',dict(study='TT039',qualification='PASS'))
module.ROOT=fixture;module.STATE=fixture/'QUEUE_STATUS.json'
module.state('WAITING_FOR_CAPACITY',production_started=False)
assert read(fixture/'CURRENT_EXECUTION.json')['production_started'] is False
module.state('DETACHED_ASSAY_STARTED',pid=123)
assert read(fixture/'CURRENT_EXECUTION.json')['production_started'] is True
assert read(fixture/'CURRENT_EXECUTION.json')['qualification']=='PASS'
attempts=[];sleeps=[]
def available(name):
    attempts.append(name);return len(attempts)==2
module.available=available
original_sleep=module.time.sleep
try:
    module.time.sleep=lambda n:sleeps.append(n)
    assert module.wait_capacity('resource',module.time.monotonic()+90)=='resource_001.json'
    assert len(attempts)==2 and len(sleeps)==1 and sleeps[0]<=60
    try:module.wait_capacity('expired',module.time.monotonic()-1)
    except TimeoutError:pass
    else:raise AssertionError('expired queue admitted')
finally:module.time.sleep=original_sleep
write(directory/'COMPLETE.json',dict(status='PASS',completed_utc=now(),controller_sha256=sha(root/'admin/controller.py'),
    checks=['state updates preserve qualification','production state flag follows phase',
        'busy then available resource sequence','expired wait stops without launch'],
    new_dynamics=0,new_receiving_assays=0,jobs_launched=0))
print(dict(status='PASS',checks=4,jobs_launched=0))
